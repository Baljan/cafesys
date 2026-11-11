from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from cafesys.baljan import models


class WrappedDataTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.old = models.Semester.objects.create(
            name="HT2097", start=date(2097, 8, 20), end=date(2097, 12, 20)
        )
        cls.new = models.Semester.objects.create(
            name="HT2098", start=date(2098, 8, 20), end=date(2098, 12, 20)
        )
        cls.user = User.objects.create_user("wrappeduser")
        cls.old_only = User.objects.create_user("oldonly")
        cls.other = User.objects.create_user("otheruser")
        models.Profile.objects.filter(
            user__in=[cls.user, cls.old_only, cls.other]
        ).update(has_seen_consent=True)

        models.Wrapped.objects.create(
            user=cls.user, semester=cls.old, data={"n_orders": 1}
        )
        models.Wrapped.objects.create(
            user=cls.user, semester=cls.new, data={"n_orders": 2}
        )
        models.Wrapped.objects.create(
            user=cls.old_only, semester=cls.old, data={"n_orders": 3}
        )
        models.Wrapped.objects.create(
            user=cls.other, semester=cls.new, data={"n_orders": 4}
        )

    def test_anonymous_gets_401(self):
        self.assertEqual(self.client.get(reverse("wrapped")).status_code, 401)

    def test_returns_latest_semester(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("wrapped"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"n_orders": 2, "semester": "HT2098"})

    def test_no_data_for_latest_semester_is_400(self):
        self.client.force_login(self.old_only)
        self.assertEqual(self.client.get(reverse("wrapped")).status_code, 400)
