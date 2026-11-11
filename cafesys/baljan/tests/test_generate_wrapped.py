from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase

from cafesys.baljan import models
from cafesys.baljan.management.commands.generate_wrapped import (
    online_cards,
    previous_semester,
    shifts,
    time_of_day,
)

STHLM = ZoneInfo("Europe/Stockholm")


def at(*args):
    return datetime(*args, tzinfo=STHLM)


class GenerateWrappedHelpersTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.prev = models.Semester.objects.create(
            name="HT2097", start=date(2097, 8, 19), end=date(2097, 12, 20)
        )
        cls.sem = models.Semester.objects.create(
            name="HT2098", start=date(2098, 8, 18), end=date(2098, 12, 19)
        )
        cls.user = User.objects.create_user("wrappeduser")
        cls.other = User.objects.create_user("otheruser")

    def order(self, put_at, user=None):
        return models.Order.objects.create(
            user=user or self.user, put_at=put_at, paid=9
        )

    def test_online_cards_counts_only_this_semester(self):
        yellow = models.Product.objects.create(
            product_id="prod_y",
            price_id="price_y",
            name="Gult kaffekort",
            styling="yellow",
            price=135,
            active=True,
        )
        blue = models.Product.objects.create(
            product_id="prod_b",
            price_id="price_b",
            name="Blått kaffekort",
            styling="blue",
            price=405,
            active=True,
        )

        def purchase(product, made, user=None, n=[0]):
            n[0] += 1
            p = models.Purchase.objects.create(
                product=product,
                user=user or self.user,
                session_id="cs_%d" % n[0],
                value=product.price,
                currency="SEK",
            )
            models.Purchase.objects.filter(pk=p.pk).update(made=made)

        purchase(yellow, at(2098, 9, 1, 10))
        purchase(yellow, at(2098, 12, 19, 23))  # last day counts
        purchase(blue, at(2098, 10, 1, 10))
        purchase(yellow, at(2097, 10, 1, 10))  # previous semester
        purchase(yellow, at(2098, 10, 1, 10), user=self.other)

        self.assertEqual(
            online_cards(self.user, self.sem),
            {"count": 3, "by_product": {"Gult kaffekort": 2, "Blått kaffekort": 1}},
        )
        self.assertEqual(
            online_cards(self.other, self.prev), {"count": 0, "by_product": {}}
        )

    def test_previous_semester(self):
        self.order(at(2097, 9, 1, 10))
        self.order(at(2097, 12, 20, 15))  # last day counts
        self.order(at(2098, 9, 1, 10))  # this semester, not counted

        self.assertEqual(
            previous_semester(self.user, self.sem),
            {"semester": "HT2097", "n_orders": 2},
        )
        self.assertEqual(
            previous_semester(self.other, self.sem),
            {"semester": "HT2097", "n_orders": 0},
        )
        self.assertIsNone(previous_semester(self.user, self.prev))

    def test_time_of_day_uses_local_time(self):
        self.order(at(2098, 9, 1, 8, 5))  # Monday
        self.order(at(2098, 9, 1, 8, 50))  # Monday
        self.order(at(2098, 9, 5, 14, 0))  # Friday

        result = time_of_day(models.Order.objects.filter(user=self.user))

        self.assertEqual(result["hours"][8], 2)
        self.assertEqual(result["hours"][14], 1)
        self.assertEqual(sum(result["hours"]), 3)
        self.assertEqual(result["weekdays"], [2, 0, 0, 0, 1, 0, 0])
        self.assertEqual(result["fav_hour"], 8)
        self.assertEqual(result["fav_weekday"], 0)

    def test_shifts_counts_worked_shifts_until_date(self):
        sem_shifts = models.Shift.objects.filter(semester=self.sem, enabled=True)
        sem_shifts.update(exam_period=False)
        morning = sem_shifts.filter(span=0).order_by("when", "location")
        afternoon = sem_shifts.filter(span=2).order_by("when", "location")
        self.assertTrue(morning.exists() and afternoon.exists())

        until = morning[1].when
        models.ShiftSignup.objects.create(shift=morning[0], user=self.user)
        models.ShiftSignup.objects.create(shift=morning[1], user=self.user)
        models.ShiftSignup.objects.create(shift=afternoon[0], user=self.user)
        # After `until`, not worked yet
        models.ShiftSignup.objects.create(
            shift=morning.filter(when__gt=until).first(), user=self.user
        )
        models.OnCallDuty.objects.create(shift=afternoon[0], user=self.user)

        exam = morning[0]
        exam.exam_period = True
        exam.save()

        result = shifts(self.user, self.sem, until=until)

        self.assertEqual(result["count"], 3)
        self.assertEqual(result["by_span"], {"morning": 2, "lunch": 0, "afternoon": 1})
        self.assertEqual(result["exam_period"], 1)
        self.assertEqual(result["on_call"], 1)
