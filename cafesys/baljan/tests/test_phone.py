from datetime import date, timedelta
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings

from cafesys.baljan import phone
from cafesys.baljan.models import (
    IncomingCallFallback,
    Located,
    Semester,
    Shift,
    ShiftSignup,
)


@override_settings(VERIFY_46ELKS_IP=False)
class PhoneMenuTestCase(TestCase):
    """The board hears its own IVR menu; everyone else keeps today's."""

    @classmethod
    def setUpTestData(cls):
        cls.board_user = cls._create_user(
            "boardie", "0701111111", group=settings.BOARD_GROUP
        )
        cls.regular_user = cls._create_user("regular", "0702222222")

        # With no OnCallDuty rows, the duty list is the fallback list alone,
        # regardless of what time of day the tests run.
        fallback_user = cls._create_user("fallback", "0703333333")
        IncomingCallFallback.objects.create(user=fallback_user, priority=1)

    @staticmethod
    def _create_user(username, mobile_phone, group=None):
        user = User.objects.create(username=username)
        user.profile.mobile_phone = mobile_phone
        user.profile.save()
        if group:
            user.groups.add(Group.objects.get_or_create(name=group)[0])
        return user

    def ivr_response(self, from_number):
        return self.client.post("/incoming-ivr-call", {"from": from_number}).json()

    def call_response(self, from_number, **extra):
        return self.client.post("/incoming-call", {"from": from_number, **extra}).json()

    # Menu selection

    def test_board_member_gets_board_menu(self):
        self.assertEqual(phone.menu_for(self.board_user).audio, "ivr-styrelsen.mp3")

    def test_regular_member_and_unknown_caller_get_default_menu(self):
        self.assertIs(phone.menu_for(self.regular_user), phone.MENUS["default"])
        self.assertIs(phone.menu_for(None), phone.MENUS["default"])

    def test_missing_recording_falls_back_to_default(self):
        self.assertEqual(phone._existing_audio("does-not-exist.mp3"), "ivr.mp3")
        self.assertEqual(phone._existing_audio("ivr.mp3"), "ivr.mp3")

    def test_board_caller_hears_board_audio(self):
        # _existing_audio keeps this green until ivr-styrelsen.mp3 is recorded.
        expected = phone._existing_audio("ivr-styrelsen.mp3")
        response = self.ivr_response("+46701111111")
        self.assertTrue(response["ivr"].endswith("/static/audio/phone/" + expected))

    def test_regular_caller_hears_default_audio(self):
        response = self.ivr_response("+46702222222")
        self.assertTrue(response["ivr"].endswith("/static/audio/phone/ivr.mp3"))

    # Board keys

    def test_board_key_1_connects_smorgasfiket(self):
        with mock.patch.object(phone, "SMORGASFIKET_PHONE", "+46101010101"):
            response = self.call_response("+46701111111", result="1")
        self.assertEqual(response["connect"], "+46101010101")
        self.assertNotIn("whenhangup", response)

    def test_board_key_2_connects_teddys(self):
        with mock.patch.object(phone, "TEDDYS_PHONE", "+46202020202"):
            response = self.call_response("+46701111111", result="2")
        self.assertEqual(response["connect"], "+46202020202")
        self.assertNotIn("whenhangup", response)

    def test_board_key_3_calls_baljan_workers(self):
        semester = Semester.objects.create(
            name="HT2026",
            start=date.today() - timedelta(days=30),
            end=date.today() + timedelta(days=30),
        )
        shift = Shift.objects.create(
            semester=semester, when=date.today(), span=0, location=Located.KARALLEN
        )
        worker = self._create_user("worker", "0704444444")
        ShiftSignup.objects.create(shift=shift, user=worker)

        with mock.patch.object(phone, "_get_current_shift_span", return_value=0):
            response = self.call_response("+46701111111", result="3")

        self.assertEqual(response["connect"], "+46704444444")
        self.assertIn("whenhangup", response)

    # The default menu must be untouched

    def test_regular_key_1_still_reaches_duty(self):
        response = self.call_response("+46702222222", result="1")
        self.assertEqual(response["connect"], "+46703333333")
        self.assertIn("whenhangup", response)

    def test_regular_key_3_without_permission_replays_menu(self):
        response = self.call_response("+46702222222", result="3")
        self.assertIn("ivr", response)
        self.assertNotIn("connect", response)

    # Error paths

    def test_invalid_key_replays_the_callers_own_menu(self):
        response = self.call_response("+46701111111", result="9")
        self.assertIn("ivr", response)
        expected = phone._existing_audio("ivr-styrelsen.mp3")
        self.assertTrue(response["ivr"].endswith("/static/audio/phone/" + expected))

    def test_failed_ivr_routes_to_duty_for_everyone(self):
        response = self.call_response("+46701111111", result="failed", why="timeout")
        self.assertEqual(response["connect"], "+46703333333")
        self.assertIn("whenhangup", response)

    def test_call_without_ivr_routes_to_duty(self):
        response = self.call_response("+46702222222")
        self.assertEqual(response["connect"], "+46703333333")
