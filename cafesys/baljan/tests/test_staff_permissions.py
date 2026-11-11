from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase
from django.urls import reverse

from cafesys.baljan import models


class SignupPermissionTestCase(TestCase):
    """Applying for and trading shifts needs self_and_friend_signup."""

    @classmethod
    def setUpTestData(cls):
        start = date.today() + timedelta(days=1)
        cls.semester = models.Semester.objects.create(
            name="VT2099",
            start=start,
            end=start + timedelta(days=60),
            signup_possible=True,
        )
        cls.shift = models.Shift.objects.filter(semester=cls.semester).first()
        combination = models.ShiftCombination.objects.create(
            semester=cls.semester, label="A1"
        )
        combination.shifts.add(cls.shift)

        workers = Group.objects.get_or_create(name=settings.WORKER_GROUP)[0]
        workers.permissions.add(
            Permission.objects.get(codename="self_and_friend_signup")
        )

        cls.worker = cls._user("worker", workers)
        cls.regular = cls._user("regular")

    @staticmethod
    def _user(username, group=None):
        user = User.objects.create_user(username)
        user.profile.has_seen_consent = True
        user.profile.save()
        if group:
            user.groups.add(group)
        return user

    def _toggle(self, user):
        signup = models.ShiftSignup.objects.create(shift=self.shift, user=user)
        self.client.force_login(user)
        self.client.post(reverse("toggle_tradable", args=(signup.pk, "staff")))
        signup.refresh_from_db()
        return signup.tradable

    def _apply(self, user):
        self.client.force_login(user)
        self.client.post(
            reverse("semester_shifts", args=(self.semester.name,)),
            {"workable-A1": "on", "priority-A1": "0"},
        )
        return models.WorkableShift.objects.filter(user=user).exists()

    def test_user_without_permission_cannot_make_shift_tradable(self):
        self.assertFalse(self._toggle(self.regular))

    def test_user_without_permission_does_not_see_trade_buttons(self):
        models.ShiftSignup.objects.create(shift=self.shift, user=self.regular)
        self.client.force_login(self.regular)

        response = self.client.get(
            reverse("day_shifts", args=(self.shift.when.isoformat(),))
        )

        self.assertNotContains(response, "Gör bytbar")

    def test_worker_can_make_shift_tradable(self):
        self.assertTrue(self._toggle(self.worker))

    def test_toggle_tradable_rejects_get(self):
        signup = models.ShiftSignup.objects.create(shift=self.shift, user=self.worker)
        self.client.force_login(self.worker)

        response = self.client.get(
            reverse("toggle_tradable", args=(signup.pk, "staff"))
        )

        self.assertEqual(response.status_code, 405)

    def test_user_without_permission_cannot_apply_for_shifts(self):
        self.assertFalse(self._apply(self.regular))

    def test_worker_can_apply_for_shifts(self):
        self.assertTrue(self._apply(self.worker))
