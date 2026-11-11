from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase

from cafesys.baljan import planning
from cafesys.baljan.models import OnCallDuty, OnCallWeek, Semester, Shift
from cafesys.baljan.util import week_dates, year_and_week


class CallDutyOverviewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        monday = date.today() - timedelta(days=date.today().weekday())
        cls.semester = Semester.objects.create(
            name="HT2099", start=monday, end=monday + timedelta(days=13)
        )
        cls.week1 = year_and_week(monday)
        cls.week2 = year_and_week(monday + timedelta(days=7))

        board = Group.objects.get_or_create(name=settings.BOARD_GROUP)[0]
        board.permissions.set(
            Permission.objects.filter(
                codename__in=[
                    "add_oncallduty",
                    "change_oncallduty",
                    "delete_oncallduty",
                ]
            )
        )
        cls.anna = User.objects.create(
            username="anna", first_name="Anna", last_name="A"
        )
        cls.bert = User.objects.create(
            username="bert", first_name="Bert", last_name="B"
        )
        cls.carl = User.objects.create(
            username="carl", first_name="Carl", last_name="C"
        )
        cls.thomas = User.objects.create(
            username="thomas", first_name="Thomas", last_name="T"
        )
        for user in (cls.anna, cls.bert, cls.carl, cls.thomas):
            user.groups.add(board)
        cls.anna.profile.has_seen_consent = True
        cls.anna.profile.save()

        # Creating the semester created its shifts. Anna, Bert and Carl are on
        # call during week 1 and Thomas covers one of the shifts.
        people = [cls.anna, cls.bert, cls.carl]
        for i, day in enumerate(week_dates(*cls.week1)[:5]):
            for span in (0, 2):
                shift = Shift.objects.get(when=day, span=span, location=0)
                user = cls.thomas if (i, span) == (0, 0) else people[(i + span) % 3]
                OnCallDuty.objects.create(shift=shift, user=user)

    def jour(self, yw):
        return planning.semester_weeks(self.semester)[
            [self.week1, self.week2].index(yw)
        ]["jour"]

    def planned_shifts(self):
        return sorted(OnCallDuty.objects.values_list("shift_id", "user_id"))

    def test_the_weeks_do_not_follow_the_shifts(self):
        planning.set_jour(*self.week2, 1, self.thomas)

        self.assertEqual(self.jour(self.week1), [None, None, None])
        self.assertEqual(self.jour(self.week2), [self.thomas, None, None])
        weeks = planning.semester_weeks(self.semester)
        self.assertEqual((weeks[0]["staffed"], weeks[1]["staffed"]), (10, 0))

    def test_swapping_weeks_does_not_touch_the_shifts(self):
        planning.set_jour(*self.week1, 1, self.anna)
        planning.set_jour(*self.week2, 2, self.thomas)
        before = self.planned_shifts()

        planning.move_jour((*self.week1, 1), (*self.week2, 2))

        self.assertEqual(self.jour(self.week1), [self.thomas, None, None])
        self.assertEqual(self.jour(self.week2), [None, self.anna, None])
        self.assertEqual(self.planned_shifts(), before)

    def test_move_to_an_empty_spot_and_within_a_week(self):
        planning.set_jour(*self.week1, 1, self.anna)

        planning.move_jour((*self.week1, 1), (*self.week2, 3))
        self.assertEqual(self.jour(self.week2), [None, None, self.anna])
        # A week with nobody left is removed
        self.assertFalse(OnCallWeek.objects.filter(week=self.week1[1]).exists())

        planning.move_jour((*self.week2, 3), (*self.week2, 1))
        self.assertEqual(self.jour(self.week2), [self.anna, None, None])

    def test_same_person_twice_in_a_week(self):
        planning.set_jour(*self.week1, 1, self.anna)
        planning.set_jour(*self.week2, 1, self.anna)

        with self.assertRaises(planning.OnCallWeekError):
            planning.set_jour(*self.week1, 2, self.anna)
        with self.assertRaises(planning.OnCallWeekError):
            planning.move_jour((*self.week1, 1), (*self.week2, 2))

        self.assertEqual(self.jour(self.week1), [self.anna, None, None])
        self.assertEqual(self.jour(self.week2), [self.anna, None, None])

    def test_views(self):
        self.client.force_login(self.anna)
        planning.set_jour(*self.week1, 1, self.thomas)

        response = self.client.get("/call-duty")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Thomas T")

        response = self.client.get("/call-duty/%d/%d" % self.week1)
        self.assertContains(response, 'href="/call-duty"')

        response = self.client.get("/call-duty?semester=HT2099")
        self.assertRedirects(response, "/call-duty")

        def update(**data):
            return self.client.post("/call-duty/update-week", data)

        response = update(
            action="set",
            year=self.week2[0],
            week=self.week2[1],
            slot=2,
            user=self.anna.pk,
        )
        self.assertEqual(
            response.json()["weeks"]["%d-%d" % self.week2]["jour"],
            [None, {"id": self.anna.pk, "name": "Anna A"}, None],
        )

        before = self.planned_shifts()
        response = update(
            action="move",
            from_year=self.week1[0],
            from_week=self.week1[1],
            from_slot=1,
            year=self.week2[0],
            week=self.week2[1],
            slot=2,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.jour(self.week1), [self.anna, None, None])
        self.assertEqual(self.jour(self.week2), [None, self.thomas, None])
        self.assertEqual(self.planned_shifts(), before)

        # Same person twice, someone outside the board and a bad spot
        response = update(
            action="set",
            year=self.week2[0],
            week=self.week2[1],
            slot=3,
            user=self.thomas.pk,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
        outsider = User.objects.create(username="outsider")
        response = update(
            action="set",
            year=self.week2[0],
            week=self.week2[1],
            slot=3,
            user=outsider.pk,
        )
        self.assertEqual(response.status_code, 400)
        response = update(
            action="set",
            year=self.week2[0],
            week=self.week2[1],
            slot=4,
            user=self.bert.pk,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(update(action="info", year=2026, week=1).status_code, 400)

        # Weeks that do not exist
        for year, week in ((2025, 53), (2026, 0), (2026, 99), (40000, 1)):
            response = update(
                action="set", year=year, week=week, slot=1, user=self.bert.pk
            )
            self.assertEqual(response.status_code, 400)
        self.assertFalse(OnCallWeek.objects.filter(jour_1=self.bert).exists())

    def test_requires_permission(self):
        outsider = User.objects.create(username="outsider")
        outsider.profile.has_seen_consent = True
        outsider.profile.save()
        self.client.force_login(outsider)

        response = self.client.post(
            "/call-duty/update-week",
            {
                "action": "set",
                "year": self.week2[0],
                "week": self.week2[1],
                "slot": 1,
                "user": outsider.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(OnCallWeek.objects.exists())
