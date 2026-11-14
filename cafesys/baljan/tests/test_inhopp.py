from datetime import date, timedelta
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.test import SimpleTestCase, TestCase

from cafesys.baljan import inhopp, slack
from cafesys.baljan.models import (
    Located,
    PendingShiftSignup,
    Semester,
    Shift,
    ShiftSignup,
)

EXAMPLE = (
    "Inhopp 05/11 EM Baljan (Imorgon)\n"
    "In: :white_check_mark: hugra495, axery891\n"
    "out: :x: edvja946, olago318"
)


class ParseInhoppTestCase(SimpleTestCase):
    def test_example_message(self):
        parsed = inhopp.parse_inhopp(EXAMPLE, date(2026, 11, 4))

        self.assertEqual(parsed.when, date(2026, 11, 5))
        self.assertEqual(parsed.span, 2)
        self.assertEqual(parsed.location, Located.KARALLEN)
        self.assertEqual(parsed.in_ids, ["hugra495", "axery891"])
        self.assertEqual(parsed.out_ids, ["edvja946", "olago318"])
        self.assertEqual(parsed.warnings, [])

    def test_date_closest_to_today_across_new_year(self):
        parsed = inhopp.parse_inhopp(
            "Inhopp 02/01 FM Baljan\nIn: hugra495", date(2026, 12, 30)
        )

        self.assertEqual(parsed.when, date(2027, 1, 2))

    def test_warns_when_imorgon_does_not_match(self):
        parsed = inhopp.parse_inhopp(EXAMPLE, date(2026, 11, 1))

        self.assertEqual(len(parsed.warnings), 1)

    def test_byttan_lunch(self):
        parsed = inhopp.parse_inhopp(
            "*Inhopp 5/11 Lunch Byttan*\n*In:* HUGRA495", date(2026, 11, 4)
        )

        self.assertEqual(parsed.span, 1)
        self.assertEqual(parsed.location, Located.STH_VALLA)
        self.assertEqual(parsed.in_ids, ["hugra495"])

    def test_rejects_message_without_header(self):
        with self.assertRaises(inhopp.InhoppParseError):
            inhopp.parse_inhopp("Hej, någon som kan hoppa in?", date(2026, 11, 4))

    def test_rejects_message_without_liu_ids(self):
        with self.assertRaises(inhopp.InhoppParseError):
            inhopp.parse_inhopp("Inhopp 05/11 EM Baljan", date(2026, 11, 4))

    def test_rejects_same_liu_id_in_and_out(self):
        with self.assertRaises(inhopp.InhoppParseError):
            inhopp.parse_inhopp(
                "Inhopp 05/11 EM Baljan\nIn: hugra495\nOut: hugra495",
                date(2026, 11, 4),
            )


@mock.patch("cafesys.baljan.notifications.send_mail_task")
@mock.patch("cafesys.baljan.inhopp.send_mail_task")
class ApplyInhoppTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        start = date.today() + timedelta(days=30)
        cls.semester = Semester.objects.create(
            name="VT2028", start=start, end=start + timedelta(days=13)
        )
        # Semester creation auto-creates shifts for every weekday.
        cls.shift = (
            Shift.objects.filter(semester=cls.semester, span=2, location=0)
            .order_by("when")
            .first()
        )
        cls.worker = User.objects.create(username="worker1")
        cls.worker.groups.add(
            Group.objects.get_or_create(name=settings.WORKER_GROUP)[0]
        )
        cls.substitute = User.objects.create(username="eriba618")

    def apply(self, in_ids=(), out_ids=()):
        with self.captureOnCommitCallbacks(execute=True):
            return inhopp.apply_inhopp(
                self.shift,
                list(in_ids),
                list(out_ids),
                slack_channel="C1",
                slack_thread_ts="1.2",
            )

    def in_substitute_group(self, user):
        return user.groups.filter(name=settings.SUBSTITUTE_GROUP).exists()

    def test_substitute_is_signed_up_and_joins_substitute_group(self, invite, _notify):
        result = self.apply(in_ids=["ERIBA618"])

        self.assertEqual(result.added, ["ERIBA618"])
        self.assertTrue(
            ShiftSignup.objects.filter(shift=self.shift, user=self.substitute).exists()
        )
        self.assertTrue(self.in_substitute_group(self.substitute))
        invite.delay.assert_not_called()

    def test_worker_does_not_join_substitute_group(self, _invite, _notify):
        self.apply(in_ids=["worker1"])

        self.assertFalse(self.in_substitute_group(self.worker))

    def test_already_signed_up(self, _invite, _notify):
        ShiftSignup.objects.create(shift=self.shift, user=self.worker)

        result = self.apply(in_ids=["worker1"])

        self.assertEqual(result.already, ["worker1"])
        self.assertEqual(ShiftSignup.objects.filter(shift=self.shift).count(), 1)

    def test_unknown_liu_id_gets_pending_signup_and_invite(self, invite, _notify):
        result = self.apply(in_ids=["ghost999"])
        self.apply(in_ids=["ghost999"])

        self.assertEqual(result.pending, ["ghost999"])
        pending = PendingShiftSignup.objects.get(liu_id="ghost999")
        self.assertEqual(
            (pending.slack_channel, pending.slack_thread_ts), ("C1", "1.2")
        )
        self.assertFalse(User.objects.filter(username="ghost999").exists())
        invite.delay.assert_called_once()
        self.assertEqual(
            invite.delay.call_args.args[3],
            [f"ghost999@{settings.USER_EMAIL_DOMAIN}"],
        )

    def test_out_removes_signup_and_reports_missing(self, _invite, _notify):
        ShiftSignup.objects.create(shift=self.shift, user=self.worker)

        result = self.apply(out_ids=["worker1", "nobod123"])

        self.assertEqual(result.removed, ["worker1"])
        self.assertEqual(result.not_on_shift, ["nobod123"])
        self.assertFalse(ShiftSignup.objects.filter(shift=self.shift).exists())

    def test_out_removes_pending_signup(self, _invite, _notify):
        self.apply(in_ids=["ghost999"])

        result = self.apply(out_ids=["ghost999"])

        self.assertEqual(result.removed, ["ghost999"])
        self.assertFalse(PendingShiftSignup.objects.exists())


@mock.patch("cafesys.baljan.inhopp.post_slack_thread_message")
class ClaimPendingSignupsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        start = date.today() + timedelta(days=30)
        semester = Semester.objects.create(
            name="VT2028", start=start, end=start + timedelta(days=13)
        )
        cls.shift = Shift.objects.filter(semester=semester).order_by("when").first()

    def claim(self, user, liu_id):
        backend = mock.Mock()
        backend.get_user_details.return_value = {"username": liu_id}
        with self.captureOnCommitCallbacks(execute=True):
            inhopp.claim_pending_signups(backend, response={}, user=user)

    def test_new_user_without_email_claims_pending_signup(self, post):
        PendingShiftSignup.objects.create(
            shift=self.shift,
            liu_id="ghost999",
            slack_channel="C1",
            slack_thread_ts="1.2",
        )
        # New users get an anonymous username and no email until they consent.
        user = User.objects.create(username="anon-abc123")

        self.claim(user, "ghost999")

        self.assertTrue(
            ShiftSignup.objects.filter(shift=self.shift, user=user).exists()
        )
        self.assertTrue(user.groups.filter(name=settings.SUBSTITUTE_GROUP).exists())
        self.assertFalse(PendingShiftSignup.objects.exists())
        post.delay.assert_called_once()
        self.assertEqual(post.delay.call_args.args[:2], ("C1", "1.2"))

    def test_past_pending_signup_is_dropped(self, post):
        past_shift = Shift.objects.create(
            semester=self.shift.semester, when=date.today() - timedelta(days=1)
        )
        PendingShiftSignup.objects.create(shift=past_shift, liu_id="ghost999")
        user = User.objects.create(username="anon-abc123")

        self.claim(user, "ghost999")

        self.assertFalse(ShiftSignup.objects.filter(user=user).exists())
        self.assertFalse(PendingShiftSignup.objects.exists())
        post.delay.assert_not_called()

    def test_failure_does_not_block_login(self, _post):
        backend = mock.Mock()
        backend.get_user_details.side_effect = KeyError("username")

        with self.assertLogs("cafesys.baljan.inhopp", level="ERROR"):
            inhopp.claim_pending_signups(backend, response={}, user=mock.Mock())


class SlackPermissionTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create(
            username="kenny123", email="kenny@example.com"
        )
        cls.manager.user_permissions.add(
            *Permission.objects.filter(
                codename__in=("add_shiftsignup", "delete_shiftsignup")
            )
        )
        cls.worker = User.objects.create(username="worker1")

    def client_with_email(self, email):
        client = mock.Mock()
        client.users_info.return_value = {"user": {"profile": {"email": email}}}
        return client

    def test_matches_on_email(self):
        user = slack.django_user_for_slack(
            self.client_with_email("Kenny@example.com"), "U1"
        )

        self.assertEqual(user, self.manager)
        self.assertTrue(slack.can_manage_shifts(user))

    def test_falls_back_to_liu_id_for_student_email(self):
        email = f"worker1@{settings.USER_EMAIL_DOMAIN}"

        user = slack.django_user_for_slack(self.client_with_email(email), "U1")

        self.assertEqual(user, self.worker)
        self.assertFalse(slack.can_manage_shifts(user))

    def test_unknown_email_has_no_permission(self):
        user = slack.django_user_for_slack(
            self.client_with_email("x@example.com"), "U1"
        )

        self.assertIsNone(user)
        self.assertFalse(slack.can_manage_shifts(user))
