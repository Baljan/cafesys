from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from cafesys.baljan import dashboard, models, tasks

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
DAY = date(2098, 3, 10)  # a Monday
BALJAN = models.Located.KARALLEN
BYTTAN = models.Located.STH_VALLA


def at(day, hour, minute=0):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


@override_settings(CACHES=LOCMEM)
class SkarmTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        models.Semester.objects.create(
            name="VT2098", start=date(2098, 1, 15), end=date(2098, 6, 1)
        )
        cls.user = User.objects.create_user("kund")

    def setUp(self):
        cache.clear()

    def blipp(self, put_at, location=BALJAN, accepted=True, n=1):
        models.Order.objects.bulk_create(
            models.Order(
                user=self.user,
                put_at=put_at,
                location=location,
                paid=0,
                accepted=accepted,
            )
            for _ in range(n)
        )

    def full_days(self, count, before=DAY):
        """Normal days before `before`, busy enough to count in averages."""
        for i in range(1, count + 1):
            self.blipp(at(before - timedelta(days=i), 15, 30), n=dashboard.FULL_DAY)

    def live(self, now):
        return dashboard.payload(now, use_cache=False)["today"]

    def semester(self, now):
        return dashboard.payload(now, use_cache=False)["semester"]

    def test_live_break_counts_per_cafe(self):
        self.blipp(at(DAY, 10, 2), n=3)
        self.blipp(at(DAY, 10, 5), location=BYTTAN)
        self.blipp(at(DAY, 10, 6), accepted=False)
        self.blipp(at(DAY, 9, 59))

        today = self.live(at(DAY, 10, 7))

        self.assertEqual(
            today["rush"],
            {
                "start": "10:00",
                "end": "10:15",
                "lunch": False,
                "live": True,
                "counts": {"baljan": 3, "byttan": 1},
            },
        )
        self.assertEqual(today["totals"], {"baljan": 4, "byttan": 1})
        self.assertEqual(today["open"], {"baljan": True, "byttan": True})

    def test_shows_last_break_for_a_while_after_it_ended(self):
        self.blipp(at(DAY, 16, 10), n=2)
        rush = self.live(at(DAY, 16, 40))["rush"]
        self.assertEqual((rush["start"], rush["live"]), ("16:00", False))
        self.assertEqual(rush["counts"]["baljan"], 2)
        self.assertIsNone(self.live(at(DAY, 17, 0))["rush"])

    def test_lunch_break_is_the_whole_hour(self):
        self.blipp(at(DAY, 12, 50))
        rush = self.live(at(DAY, 12, 55))["rush"]
        self.assertEqual(
            (rush["end"], rush["lunch"], rush["live"]), ("13:00", True, True)
        )
        self.assertEqual(rush["counts"]["baljan"], 1)

    def test_no_break_before_the_first_one(self):
        self.assertIsNone(self.live(at(DAY, 7, 30))["rush"])

    def test_closed_on_weekends(self):
        saturday = DAY + timedelta(days=5)
        self.assertEqual(
            self.live(at(saturday, 11))["open"], {"baljan": False, "byttan": False}
        )

    def test_semester_record_ignores_lunch_and_keeps_the_first_tie(self):
        self.full_days(5)
        self.blipp(at(DAY - timedelta(days=4), 12, 30), n=60)
        self.blipp(at(DAY - timedelta(days=3), 14, 1), location=BYTTAN, n=7)
        self.blipp(at(DAY - timedelta(days=2), 9, 3), n=7)

        sem = self.semester(at(DAY, 8))

        self.assertEqual(sem["name"], "VT2098")
        self.assertFalse(sem["ended"])
        self.assertEqual(sem["total"], 5 * dashboard.FULL_DAY + 74)
        self.assertEqual(
            (sem["record"]["n"], sem["record"]["cafe"], sem["record"]["start"]),
            (7, "byttan", "14:00"),
        )
        avgs = {b["hour"]: b["avg"] for b in sem["rhythm"]}
        self.assertNotIn(12, avgs)
        self.assertEqual(avgs[9], round(7 / 5))

    def test_today_does_not_skew_the_averages(self):
        self.full_days(5)
        self.blipp(at(DAY, 10, 1), n=100)
        sem = self.semester(at(DAY, 10, 10))
        self.assertEqual({b["hour"]: b["avg"] for b in sem["rhythm"]}[10], 0)
        self.assertEqual(sem["record"]["n"], 100)

    def test_no_averages_early_in_the_semester(self):
        self.full_days(4)
        self.blipp(at(DAY - timedelta(days=5), 9, 1), n=3)  # a quiet day
        sem = self.semester(at(DAY, 10))
        self.assertEqual(sem["total"], 4 * dashboard.FULL_DAY + 3)
        self.assertIsNone(sem["record"])
        self.assertIsNone(sem["rhythm"])

    def test_between_semesters_shows_the_last_one(self):
        self.blipp(at(date(2098, 5, 20), 9, 1))
        sem = self.semester(at(date(2098, 7, 1), 10))
        self.assertEqual((sem["name"], sem["ended"], sem["total"]), ("VT2098", True, 1))

    def test_without_blipps_there_is_nothing_to_show(self):
        data = dashboard.payload(at(DAY, 10), use_cache=False)
        self.assertIsNone(data["semester"])
        self.assertIsNone(data["top"])
        self.assertEqual(data["today"]["totals"], {"baljan": 0, "byttan": 0})

    def test_cached_data_endpoint_does_not_touch_the_database(self):
        url = reverse("skarm_data")
        self.client.get(url)
        with self.assertNumQueries(0):
            self.client.get(url)

    def test_endpoints(self):
        self.assertEqual(self.client.get(reverse("skarm")).status_code, 200)
        self.assertContains(
            self.client.get(reverse("skarm") + "?topplista=0"), "showTop: false"
        )
        data = self.client.get(reverse("skarm_data")).json()
        self.assertEqual([c["key"] for c in data["cafes"]], ["baljan", "byttan"])

    def test_preview_time_is_ignored_in_production(self):
        data = self.client.get(reverse("skarm_data") + "?nu=2000-01-01T10:00").json()
        self.assertNotIn("2000", data["generated"])


@override_settings(CACHES=LOCMEM)
class SkarmTopTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        today = date.today()
        models.Semester.objects.create(
            name="HT2099",
            start=today - timedelta(days=3),
            end=today + timedelta(days=3),
        )
        people = [
            ("anna", "Anna Maria", "Lind", 9),
            ("bo", "Bo", "", 9),
            ("ingen", "", "", 8),
            ("dold", "Dold", "Person", 7),
            ("styr", "Styr", "Else", 6),
            ("cia", "Cia", "Ek", 4),
            ("dan", "Dan", "Ek", 3),
        ]
        now = timezone.now()
        for username, first, last, count in people:
            user = User.objects.create_user(username, first_name=first, last_name=last)
            models.Order.objects.bulk_create(
                models.Order(user=user, put_at=now, paid=0) for _ in range(count)
            )
        models.Profile.objects.filter(user__username="dold").update(show_profile=False)
        board, _ = Group.objects.get_or_create(name=settings.BOARD_GROUP)
        board.user_set.add(User.objects.get(username="styr"))

    def setUp(self):
        cache.clear()

    def test_ranks_count_only_the_people_shown(self):
        tasks.update_stats()
        top = dashboard.payload()["top"]
        self.assertEqual(top["name"], "HT2099")
        self.assertEqual(
            sorted((p["rank"], p["name"], p["count"]) for p in top["people"]),
            [(1, "Anna L.", 9), (1, "Bo", 9), (2, "Cia E.", 4)],
        )

    def test_no_top_list_before_stats_are_computed(self):
        self.assertIsNone(dashboard.payload()["top"])
