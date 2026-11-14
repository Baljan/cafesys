from datetime import date, datetime, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cafesys.baljan import models, views

DAY = date(2098, 3, 10)  # a Monday


def at(day, hour, minute):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


def every_break(day):
    return [at(day, hour, 30 if hour == 12 else 5) for hour in range(8, 17)]


class CoffeeChallengeTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("gladiator")
        cls.other = User.objects.create_user("bystander")
        models.Profile.objects.filter(user__in=[cls.user, cls.other]).update(
            has_seen_consent=True
        )
        cls.challenge = models.CoffeeChallenge.objects.create(user=cls.user, date=DAY)

    def blipp(self, put_at, user=None, accepted=True):
        models.Order.objects.create(
            user=user or self.user, put_at=put_at, paid=0, accepted=accepted
        )

    def done(self):
        return [s["done"] for s in self.challenge.slots()]

    def test_nine_breaks_with_a_full_lunch_hour(self):
        self.assertEqual(len(models.CoffeeChallenge.SLOTS), 9)
        self.assertEqual(models.CoffeeChallenge.SLOTS[0], (time(8), time(8, 15)))
        self.assertEqual(models.CoffeeChallenge.SLOTS[4], (time(12), time(13)))
        self.assertEqual(models.CoffeeChallenge.SLOTS[-1], (time(16), time(16, 15)))

    def test_blipps_inside_breaks_are_ticked(self):
        self.blipp(at(DAY, 8, 0))
        self.blipp(at(DAY, 12, 59))
        self.blipp(at(DAY, 16, 14))
        self.assertEqual(
            self.done(), [True, False, False, False, True, False, False, False, True]
        )

    def test_blipps_outside_breaks_are_not(self):
        self.blipp(at(DAY, 7, 59))
        self.blipp(at(DAY, 8, 15))
        self.blipp(at(DAY, 9, 30))
        self.blipp(at(DAY, 13, 15))
        self.assertEqual(self.challenge.cups(), 0)

    def test_two_blipps_in_one_break_count_once(self):
        self.blipp(at(DAY, 10, 1))
        self.blipp(at(DAY, 10, 3))
        self.assertEqual(self.challenge.cups(), 1)

    def test_other_days_users_and_rejected_orders_do_not_count(self):
        self.blipp(at(DAY + timedelta(days=1), 8, 5))
        self.blipp(at(DAY, 8, 5), user=self.other)
        self.blipp(at(DAY, 9, 5), accepted=False)
        self.assertEqual(self.challenge.cups(), 0)

    def test_gladiator_only_after_every_break(self):
        for put_at in every_break(DAY)[:-1]:
            self.blipp(put_at)
        self.assertEqual(models.CoffeeChallenge.times_completed(self.user), 0)
        self.blipp(every_break(DAY)[-1])
        self.assertEqual(models.CoffeeChallenge.times_completed(self.user), 1)

    def test_every_completed_day_counts(self):
        later = DAY + timedelta(days=1)
        models.CoffeeChallenge.objects.create(user=self.user, date=later)
        for put_at in every_break(DAY) + every_break(later):
            self.blipp(put_at)
        self.assertEqual(models.CoffeeChallenge.times_completed(self.user), 2)

    def test_a_passed_break_without_blipp_fails_the_challenge(self):
        past = models.CoffeeChallenge.objects.create(
            user=self.user, date=date(2000, 3, 6)
        )
        for put_at in every_break(past.date)[:-1]:
            self.blipp(put_at)
        slots = past.slots()
        self.assertTrue(slots[-1]["missed"])
        self.assertFalse(any(s["missed"] for s in slots[:-1]))
        self.assertTrue(past.is_failed())

    def test_upcoming_breaks_are_not_missed(self):
        self.assertFalse(self.challenge.is_failed())

    def test_blipp_message_says_how_many_are_left(self):
        self.blipp(at(DAY, 8, 5))
        self.blipp(at(DAY, 9, 5))
        message = views._coffee_challenge_blipp_message(self.user, at(DAY, 9, 5))
        self.assertIn("2/9 – 7 kvar!", message)

    def test_blipp_message_when_failed(self):
        past = date(2000, 3, 6)
        models.CoffeeChallenge.objects.create(user=self.user, date=past)
        self.blipp(at(past, 9, 5))
        message = views._coffee_challenge_blipp_message(self.user, at(past, 9, 5))
        self.assertIn("Utmaning misslyckad – Du tar den nästa gång!", message)

    def test_blipp_message_when_completed(self):
        for put_at in every_break(DAY):
            self.blipp(put_at)
        message = views._coffee_challenge_blipp_message(self.user, at(DAY, 16, 5))
        self.assertIn("9/9 – du är en <b>Coffee Gladiator</b>!", message)

    def test_profile_shows_title_to_everyone(self):
        for put_at in every_break(DAY):
            self.blipp(put_at)
        self.client.force_login(self.other)
        resp = self.client.get("/user/%d" % self.user.id)
        self.assertContains(resp, "%s x1" % models.CoffeeChallenge.TITLE)

    def test_profile_has_challenge_button_only_for_self(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse("profile")), "Antar du utmaningen?")
        resp = self.client.get("/user/%d" % self.other.id)
        self.assertNotContains(resp, "Antar du utmaningen?")
        self.assertNotContains(resp, models.CoffeeChallenge.TITLE)


class CoffeeChallengeViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("challenger")
        cls.other = User.objects.create_user("snoop")
        models.Profile.objects.filter(user__in=[cls.user, cls.other]).update(
            has_seen_consent=True
        )

    def setUp(self):
        self.client.force_login(self.user)

    def next_weekday(self):
        day = timezone.localdate() + timedelta(days=1)
        while day.weekday() >= 5:
            day += timedelta(days=1)
        return day

    def test_accepting_creates_a_challenge(self):
        day = self.next_weekday()
        resp = self.client.post(reverse("coffee_challenge"), {"date": day.isoformat()})
        self.assertRedirects(
            resp, reverse("coffee_challenge_day", args=[day.isoformat()])
        )
        self.assertTrue(
            models.CoffeeChallenge.objects.filter(user=self.user, date=day).exists()
        )

    def test_rejects_past_weekend_and_duplicate_dates(self):
        day = self.next_weekday()
        models.CoffeeChallenge.objects.create(user=self.user, date=day)
        saturday = day + timedelta(days=(5 - day.weekday()))
        for bad in (date(2000, 1, 3), saturday, day):
            resp = self.client.post(
                reverse("coffee_challenge"), {"date": bad.isoformat()}
            )
            self.assertEqual(resp.status_code, 200)
        self.assertEqual(models.CoffeeChallenge.objects.count(), 1)

    def test_cannot_see_someone_elses_challenge(self):
        day = self.next_weekday()
        models.CoffeeChallenge.objects.create(user=self.other, date=day)
        for name in ("coffee_challenge_day", "coffee_challenge_status"):
            resp = self.client.get(reverse(name, args=[day.isoformat()]))
            self.assertEqual(resp.status_code, 404)

    def test_bad_date_is_404(self):
        resp = self.client.get(reverse("coffee_challenge_day", args=["inte-ett-datum"]))
        self.assertEqual(resp.status_code, 404)

    def test_status_json(self):
        day = self.next_weekday()
        models.CoffeeChallenge.objects.create(user=self.user, date=day)
        resp = self.client.get(
            reverse("coffee_challenge_status", args=[day.isoformat()])
        )
        self.assertEqual(
            resp.json(),
            {"cups": 0, "total": 9, "done": [False] * 9, "missed": [False] * 9},
        )

    def test_future_challenge_can_be_withdrawn(self):
        day = self.next_weekday()
        models.CoffeeChallenge.objects.create(user=self.user, date=day)
        self.client.post(reverse("coffee_challenge_delete", args=[day.isoformat()]))
        self.assertFalse(models.CoffeeChallenge.objects.exists())


class CoffeeChallengeBlippTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.good = models.Good.objects.create(title="Kaffe")
        models.GoodCost.objects.create(
            good=cls.good, cost=5, currency="SEK", from_date=date(2000, 1, 1)
        )
        cls.config = models.BlippConfiguration.objects.create(
            good=cls.good, token="testtoken"
        )
        cls.user = User.objects.create_user("blipper")
        models.Profile.objects.filter(user=cls.user).update(card_id=1234, balance=100)

    def blipp(self):
        return self.client.post(
            "/do-blipp",
            {"id": "1234"},
            HTTP_AUTHORIZATION="Token testtoken",
        )

    def test_blipp_without_challenge_is_unchanged(self):
        resp = self.blipp()
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("Kaffeutmaningen", resp.json()["message"])

    def test_blipp_shows_challenge_progress(self):
        models.CoffeeChallenge.objects.create(user=self.user, date=timezone.localdate())
        resp = self.blipp()
        self.assertEqual(resp.status_code, 200)
        self.assertIn("☕", resp.json()["message"])
        self.assertEqual(models.Order.objects.count(), 1)
