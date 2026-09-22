from datetime import date, timedelta
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import resolve, reverse

from cafesys.baljan.actions import categories_and_actions
from cafesys.celery import app as celery_app
from cafesys.baljan.models import CateringOrder, CateringOrderEmail, Semester
from cafesys.baljan import google
from cafesys.baljan.views import CATERING_TABS as TAB_KEYS
from cafesys.baljan.tasks import (
    remove_old_catering_orders,
    send_catering_order_board_decision_email,
    send_catering_order_decision_email,
    send_catering_order_receipt_email,
    sync_catering_order_calendar,
)


def next_weekday(days_ahead=7):
    day = date.today() + timedelta(days=days_ahead)
    while day.weekday() in (5, 6):
        day += timedelta(days=1)
    return day


def make_order(**kwargs):
    defaults = {
        "orderer": "Anna Andersson",
        "orderer_email": "anna@example.com",
        "orderer_phone": "0700000000",
        "association": "Testsektionen",
        "date": next_weekday(),
        "pickup": CateringOrder.LUNCH,
        "other": "Ingen laktos",
        "items": [
            {"field": "numberOfCoffee", "label": "kaffe", "count": 20, "group": None},
            {"field": "numberOfTea", "label": "te", "count": 0, "group": None},
            {"field": "numberOfJochen", "label": "Jochen", "count": 3, "group": None},
            {
                "field": "numberOfKebabjochen",
                "label": "kebab (ljust bröd)",
                "count": 3,
                "group": "Jochen",
            },
        ],
    }
    defaults.update(kwargs)
    return CateringOrder.objects.create(**defaults)


def order_payload(**overrides):
    """A submission the public form accepts.

    `org` and the whole pickup block are required, so a smaller payload silently
    fails validation and stores nothing.
    """
    data = {
        "orderer": "Anna Andersson",
        "ordererEmail": "anna@example.com",
        "phoneNumber": "0700000000",
        "association": "Testsektionen",
        "org": "5566778899",
        "pickupName": "Bo Bosson",
        "pickupEmail": "bo@example.com",
        "pickupNumber": "0700000001",
        "numberOfCoffee": 20,
        "pickup": "2",
        "date": next_weekday().isoformat(),
        "other": "Ingen laktos tack",
    }
    data.update(overrides)
    return data


def only_to(address):
    """The one message in the outbox addressed to `address`.

    A decision now mails both the orderer and the board, so indexing the outbox
    says nothing about which message you got hold of.
    """
    found = [message for message in mail.outbox if message.to == [address]]
    assert len(found) == 1, "expected one mail to %s, got %s" % (address, len(found))
    return found[0]


class CateringOrderModelTestCase(TestCase):
    def test_ordered_items_drops_empty_lines(self):
        order = make_order()
        self.assertEqual(
            [(item["label"], item["count"]) for item in order.ordered_items()],
            [("kaffe", 20), ("Jochen", 3), ("kebab (ljust bröd)", 3)],
        )

    def test_new_orders_are_pending(self):
        order = make_order()
        self.assertTrue(order.is_pending)
        self.assertFalse(order.is_decided)

    def test_every_status_is_labelled_in_swedish(self):
        self.assertEqual(
            [label for _value, label in CateringOrder.Status.choices],
            ["Väntar", "Godkänd", "Nekad", "Avbeställd", "Levererad", "Fakturerad"],
        )

    def test_pickup_window_follows_the_chosen_slot(self):
        order = make_order(pickup=CateringOrder.MORNING)
        start, end = order.pickup_window()
        self.assertEqual((start.hour, start.minute), (7, 30))
        self.assertEqual((end.hour, end.minute), (8, 0))

    def test_approve_records_who_decided(self):
        user = User.objects.create(username="board-member")
        order = make_order()
        order.approve(
            user=user, handled_by_name="Kalle K", message="Vi ses!", notify=False
        )
        order.refresh_from_db()
        self.assertEqual(order.status, CateringOrder.Status.APPROVED)
        self.assertEqual(order.handled_by, user)
        self.assertEqual(order.handled_by_name, "Kalle K")
        self.assertEqual(order.staff_message, "Vi ses!")
        self.assertIsNotNone(order.handled_at)

    def test_deny_records_who_decided(self):
        user = User.objects.create(username="board-member")
        order = make_order()
        order.deny(
            user=user,
            handled_by_name="Kalle K",
            message="Stängt den dagen",
            notify=False,
        )
        order.refresh_from_db()
        self.assertEqual(order.status, CateringOrder.Status.DENIED)
        self.assertEqual(order.handled_by_name, "Kalle K")
        self.assertTrue(order.is_decided)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CateringOrderEmailTestCase(TestCase):
    def test_approval_email_carries_the_details_and_an_invite(self):
        order = make_order(
            status=CateringOrder.Status.APPROVED, staff_message="Hämta vid disken."
        )
        send_catering_order_decision_email(order.pk)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, [order.orderer_email])
        self.assertIn("godkänd", message.subject)
        self.assertIn(str(order.pk), message.subject)

        html = message.alternatives[0][0]
        self.assertIn("Hämta vid disken.", html)
        self.assertIn("kaffe", html)
        self.assertIn("Ingen laktos", html)

        kinds = [content_type for _name, _c, content_type in message.attachments]
        self.assertIn("text/calendar", kinds)

    def test_html_body_is_text_so_django_can_encode_it(self):
        """Django 5 rejects a bytes alternative, which silently broke sending."""
        order = make_order(status=CateringOrder.Status.APPROVED)
        send_catering_order_decision_email(order.pk)
        self.assertIsInstance(mail.outbox[0].alternatives[0][0], str)

    def test_denial_email_has_no_invite(self):
        order = make_order(
            status=CateringOrder.Status.DENIED, staff_message="Vi har stängt."
        )
        send_catering_order_decision_email(order.pk)

        message = mail.outbox[0]
        self.assertIn("nekad", message.subject)
        self.assertIn("Vi har stängt.", message.alternatives[0][0])
        self.assertEqual(message.attachments, [])

    def test_pending_orders_are_not_mailed_about(self):
        order = make_order()
        send_catering_order_decision_email(order.pk)
        self.assertEqual(mail.outbox, [])

    def test_a_deleted_order_does_not_raise(self):
        send_catering_order_decision_email(999999)
        self.assertEqual(mail.outbox, [])

    def test_a_sent_email_is_logged(self):
        order = make_order(
            status=CateringOrder.Status.APPROVED, staff_message="Hämta vid disken."
        )
        send_catering_order_decision_email(order.pk)

        logged = order.emails.get()
        self.assertEqual(logged.kind, CateringOrderEmail.Kind.APPROVED)
        self.assertEqual(logged.to_email, order.orderer_email)
        self.assertEqual(logged.body, "Hämta vid disken.")
        self.assertIn(str(order.pk), logged.subject)

    def test_the_history_keeps_both_decisions_oldest_first(self):
        order = make_order(status=CateringOrder.Status.DENIED)
        send_catering_order_decision_email(order.pk)
        order.status = CateringOrder.Status.APPROVED
        order.save()
        send_catering_order_decision_email(order.pk)

        self.assertEqual(
            [email.kind for email in order.emails.all()],
            [CateringOrderEmail.Kind.DENIED, CateringOrderEmail.Kind.APPROVED],
        )

    def test_nothing_is_logged_when_no_email_is_sent(self):
        order = make_order()
        send_catering_order_decision_email(order.pk)
        self.assertFalse(order.emails.exists())

    def test_an_empty_staff_message_is_stored_as_empty(self):
        order = make_order(status=CateringOrder.Status.APPROVED)
        send_catering_order_decision_email(order.pk)
        self.assertEqual(order.emails.get().body, "")

    def test_the_log_goes_away_with_the_order(self):
        order = make_order(status=CateringOrder.Status.APPROVED)
        send_catering_order_decision_email(order.pk)
        order.delete()
        self.assertFalse(CateringOrderEmail.objects.exists())


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class OrderFormTestCase(TestCase):
    """The public form must persist the order as well as mail the board."""

    @classmethod
    def setUpTestData(cls):
        today = date.today()
        Semester.objects.create(
            name="HT26",
            start=today - timedelta(days=30),
            end=today + timedelta(days=120),
        )

    def payload(self, **overrides):
        data = {
            "orderer": "Anna Andersson",
            "ordererEmail": "anna@example.com",
            "phoneNumber": "0700000000",
            "association": "Testsektionen",
            "org": "5566778899",
            "pickupName": "Bo Bosson",
            "pickupEmail": "bo@example.com",
            "pickupNumber": "0700000001",
            "numberOfCoffee": 20,
            "numberOfTea": 5,
            "numberOfJochen": 3,
            "numberOfKebabjochen": 3,
            "pickup": "2",
            "date": next_weekday().isoformat(),
            "other": "Ingen laktos tack",
            "orderSum": "480",
        }
        data.update(overrides)
        return data

    def test_submitting_stores_the_order(self):
        response = self.client.post(reverse("order_from_us"), self.payload())
        self.assertEqual(response.status_code, 302)

        order = CateringOrder.objects.get()
        self.assertEqual(order.orderer, "Anna Andersson")
        self.assertEqual(order.association, "Testsektionen")
        self.assertEqual(order.org_number, "5566778899")
        self.assertEqual(order.pickup_name, "Bo Bosson")
        self.assertEqual(order.pickup, CateringOrder.LUNCH)
        self.assertEqual(order.displayed_sum, "480")
        self.assertTrue(order.is_pending)

    def test_the_stored_snapshot_keeps_labels_and_counts(self):
        self.client.post(reverse("order_from_us"), self.payload())
        order = CateringOrder.objects.get()
        self.assertEqual(
            [(item["label"], item["count"]) for item in order.ordered_items()],
            [("kaffe", 20), ("te", 5), ("Jochen", 3), ("kebab (ljust bröd)", 3)],
        )

    def test_the_board_still_gets_its_email(self):
        self.client.post(reverse("order_from_us"), self.payload())
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["bestallning@baljan.org"])
        self.assertIn(str(CateringOrder.objects.get().pk), message.subject)
        kinds = [content_type for _name, _c, content_type in message.attachments]
        self.assertIn("text/calendar", kinds)

    def test_the_board_mail_links_to_the_order(self):
        """Straight into the page the decision is taken on."""
        self.client.post(reverse("order_from_us"), self.payload())
        order = CateringOrder.objects.get()
        html = mail.outbox[0].alternatives[0][0]
        self.assertIn(order.board_url(), html)
        self.assertIn(order.get_absolute_url(), html)

    def test_values_too_wide_for_their_column_are_rejected_as_form_errors(self):
        """Not as a DataError from Postgres halfway through the view.

        Django's own field defaults are wider than the columns on CateringOrder:
        EmailField allows 320 against a 254 column, and orderSum had no limit at
        all against displayed_sum's 32.
        """
        too_wide = {
            "orderSum": "9" * 200,
            "ordererEmail": "a" * 285 + "@example.com",
            "pickupEmail": "b" * 285 + "@example.com",
        }
        for field, value in too_wide.items():
            with self.subTest(field=field):
                response = self.client.post(
                    reverse("order_from_us"), self.payload(**{field: value})
                )
                self.assertEqual(response.status_code, 200)
                self.assertFalse(CateringOrder.objects.exists())

    def test_line_breaks_are_rejected_before_they_reach_a_mail_header(self):
        """`orderer` and `association` end up in the subject line.

        Django raises BadHeaderError rather than letting a Bcc through, but that
        happens inside send(), after the order has already been written. A
        crafted submission should not get that far.
        """
        for field in ("orderer", "association"):
            with self.subTest(field=field):
                response = self.client.post(
                    reverse("order_from_us"),
                    self.payload(**{field: "Anna Andersson\nBcc: evil@example.com"}),
                )
                self.assertEqual(response.status_code, 200)
                self.assertFalse(CateringOrder.objects.exists())
                self.assertEqual(mail.outbox, [])

    def test_a_weekend_is_rejected_and_nothing_is_stored(self):
        saturday = date.today()
        while saturday.weekday() != 5:
            saturday += timedelta(days=1)
        response = self.client.post(
            reverse("order_from_us"), self.payload(date=saturday.isoformat())
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CateringOrder.objects.exists())


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CateringCentralTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        today = date.today()
        Semester.objects.create(
            name="HT26",
            start=today - timedelta(days=30),
            end=today + timedelta(days=120),
        )
        cls.permission = Permission.objects.get(codename="manage_catering_orders")

    def make_user(self, username, with_permission):
        user = User.objects.create(username=username)
        if with_permission:
            group, _ = Group.objects.get_or_create(name=settings.BOARD_GROUP)
            group.permissions.add(self.permission)
            user.groups.add(group)
        profile = user.profile
        profile.has_seen_consent = True
        profile.save()
        return user

    def setUp(self):
        """Run queued mail inline.

        The decision email is queued with transaction.on_commit and dispatched
        through Celery. Neither fires by itself inside a test transaction, so
        both are made synchronous here and the posts below are wrapped in
        captureOnCommitCallbacks.
        """
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True
        self.addCleanup(setattr, celery_app.conf, "task_always_eager", False)
        self.addCleanup(setattr, celery_app.conf, "task_eager_propagates", False)

    def board_client(self):
        self.client.force_login(self.make_user("board", with_permission=True))
        return self.client

    def test_the_board_group_gets_the_permission_from_the_migration(self):
        group = Group.objects.get(name=settings.BOARD_GROUP)
        self.assertTrue(
            group.permissions.filter(codename="manage_catering_orders").exists()
        )

    def test_the_list_is_closed_to_users_without_the_permission(self):
        self.client.force_login(self.make_user("outsider", with_permission=False))
        self.assertEqual(self.client.get(reverse("catering_orders")).status_code, 403)

    def test_the_detail_page_is_closed_too(self):
        order = make_order()
        self.client.force_login(self.make_user("outsider", with_permission=False))
        response = self.client.get(reverse("catering_order", args=[order.pk]))
        self.assertIn(response.status_code, (302, 403))

    def test_the_board_sees_the_orders(self):
        order = make_order()
        response = self.board_client().get(reverse("catering_orders"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["pending_count"], 1)
        self.assertContains(response, order.orderer)

    def test_a_tab_can_still_be_searched(self):
        """The filters narrow the tab; they do not escape it."""
        make_order()
        make_order(orderer="Bertil B", status=CateringOrder.Status.APPROVED)
        client = self.board_client()

        # next_weekday() is a week out, so the approved order is upcoming.
        hit = client.get(
            reverse("catering_orders"),
            {"tab": "kommande", "association": "Testsektionen"},
        )
        self.assertEqual(hit.context["paginator"].count, 2)
        self.assertContains(hit, "Bertil B")

        miss = client.get(
            reverse("catering_orders"), {"tab": "kommande", "association": "Ada"}
        )
        self.assertEqual(miss.context["paginator"].count, 0)

    def test_the_history_tab_can_be_filtered_by_status(self):
        make_order(orderer="Bertil B", status=CateringOrder.Status.DENIED)
        make_order()
        client = self.board_client()

        denied = client.get(
            reverse("catering_orders"), {"tab": "historik", "status": "denied"}
        )
        self.assertEqual(denied.context["paginator"].count, 1)
        self.assertContains(denied, "Bertil B")

    def test_the_edit_form_is_filled_from_the_stored_order(self):
        order = make_order()
        response = self.board_client().get(reverse("catering_order", args=[order.pk]))
        initial = response.context["form"].initial
        self.assertEqual(initial["orderer"], order.orderer)
        self.assertEqual(initial["numberOfCoffee"], 20)
        self.assertEqual(initial["numberOfKebabjochen"], 3)
        self.assertEqual(initial["pickup"], str(order.pickup))

    def test_the_detail_page_renders_every_control(self):
        order = make_order()
        response = self.board_client().get(reverse("catering_order", args=[order.pk]))
        for task in ("approve", "deny", "save", "note", "status"):
            self.assertContains(response, 'value="%s"' % task)
        self.assertContains(response, order.orderer_email)
        self.assertContains(response, "kebab (ljust bröd)")
        self.assertContains(response, "badge bg-")

    def test_approving_mails_the_orderer(self):
        order = make_order()
        client = self.board_client()
        mail.outbox = []

        with self.captureOnCommitCallbacks(execute=True):
            response = client.post(
                reverse("catering_order", args=[order.pk]),
                {
                    "task": "approve",
                    "staff_message": "Vi ses på fredag!",
                    "handled_by_name": "Kalle Karlsson",
                },
            )
        self.assertEqual(response.status_code, 302)

        order.refresh_from_db()
        self.assertEqual(order.status, CateringOrder.Status.APPROVED)
        self.assertEqual(order.handled_by.username, "board")

        # Two mails now: the orderer's, and the answer in the board's thread.
        self.assertEqual(len(mail.outbox), 2)
        to_orderer = only_to(order.orderer_email)
        self.assertIn("Vi ses på fredag!", to_orderer.alternatives[0][0])

    def test_denying_mails_the_orderer(self):
        order = make_order()
        client = self.board_client()
        mail.outbox = []

        with self.captureOnCommitCallbacks(execute=True):
            client.post(
                reverse("catering_order", args=[order.pk]),
                {
                    "task": "deny",
                    "staff_message": "Tyvärr stängt.",
                    "handled_by_name": "Kalle Karlsson",
                },
            )
        order.refresh_from_db()
        self.assertEqual(order.status, CateringOrder.Status.DENIED)
        self.assertIn("Tyvärr stängt.", only_to(order.orderer_email).alternatives[0][0])

    def test_editing_rewrites_the_order_without_mailing(self):
        order = make_order()
        client = self.board_client()
        mail.outbox = []

        data = {
            "task": "save",
            "orderer": "Anna Andersson",
            "ordererEmail": "anna@example.com",
            "phoneNumber": "0700000000",
            "association": "Nya sektionen",
            "org": "5566778899",
            "pickupName": "Bo Bosson",
            "pickupEmail": "bo@example.com",
            "pickupNumber": "0700000001",
            "numberOfCoffee": 50,
            "numberOfTea": 5,
            "pickup": "1",
            "date": next_weekday(14).isoformat(),
            "other": "Ändrad text",
            "orderSum": "900",
        }
        with self.captureOnCommitCallbacks(execute=True):
            response = client.post(reverse("catering_order", args=[order.pk]), data)
        self.assertEqual(response.status_code, 302)

        order.refresh_from_db()
        self.assertEqual(order.association, "Nya sektionen")
        self.assertEqual(order.pickup, CateringOrder.MORNING)
        self.assertEqual(order.other, "Ändrad text")
        counts = {item["field"]: item["count"] for item in order.items}
        self.assertEqual(counts["numberOfCoffee"], 50)
        self.assertEqual(mail.outbox, [])

    def test_an_invalid_edit_leaves_the_order_alone(self):
        order = make_order()
        client = self.board_client()
        response = client.post(
            reverse("catering_order", args=[order.pk]),
            {"task": "save", "orderer": "x"},
        )
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.orderer, "Anna Andersson")

    def test_the_internal_note_is_saved_without_mailing(self):
        order = make_order()
        client = self.board_client()
        mail.outbox = []

        with self.captureOnCommitCallbacks(execute=True):
            client.post(
                reverse("catering_order", args=[order.pk]),
                {"task": "note", "staff_note": "Ring innan leverans."},
            )
        order.refresh_from_db()
        self.assertEqual(order.staff_note, "Ring innan leverans.")
        self.assertEqual(mail.outbox, [])

    def test_a_later_status_is_internal_and_sends_no_mail(self):
        order = make_order(status=CateringOrder.Status.APPROVED)
        client = self.board_client()
        mail.outbox = []

        with self.captureOnCommitCallbacks(execute=True):
            client.post(
                reverse("catering_order", args=[order.pk]),
                {
                    "task": "status",
                    "status": "delivered",
                    "handled_by_name": "Kalle Karlsson",
                },
            )
        order.refresh_from_db()
        self.assertEqual(order.status, CateringOrder.Status.DELIVERED)
        self.assertEqual(mail.outbox, [])

    def test_an_order_can_be_cancelled_without_mailing(self):
        """A cancellation comes from the orderer, so they need no telling."""
        order = make_order(status=CateringOrder.Status.APPROVED)
        client = self.board_client()
        mail.outbox = []

        with self.captureOnCommitCallbacks(execute=True):
            client.post(
                reverse("catering_order", args=[order.pk]),
                {
                    "task": "status",
                    "status": "cancelled",
                    "handled_by_name": "Kalle Karlsson",
                },
            )
        order.refresh_from_db()
        self.assertEqual(order.status, CateringOrder.Status.CANCELLED)
        self.assertEqual(order.get_status_display(), "Avbeställd")
        self.assertEqual(mail.outbox, [])

    def test_the_page_shows_the_history_after_a_decision(self):
        order = make_order()
        client = self.board_client()

        with self.captureOnCommitCallbacks(execute=True):
            client.post(
                reverse("catering_order", args=[order.pk]),
                {
                    "task": "approve",
                    "staff_message": "Vi ses på fredag!",
                    "handled_by_name": "Kalle Karlsson",
                },
            )

        response = client.get(reverse("catering_order", args=[order.pk]))
        self.assertContains(response, "Skickade mail")
        self.assertContains(response, "Godkännande")
        self.assertContains(response, order.orderer_email)
        self.assertContains(response, "Vi ses på fredag!")

    def test_the_page_says_so_when_nothing_has_been_sent(self):
        order = make_order()
        response = self.board_client().get(reverse("catering_order", args=[order.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inget mail har skickats till beställaren än.")

    def test_an_unknown_status_is_refused(self):
        order = make_order()
        response = self.board_client().post(
            reverse("catering_order", args=[order.pk]),
            {"task": "status", "status": "nonsense"},
        )
        self.assertEqual(response.status_code, 400)

    def test_an_unknown_task_is_refused(self):
        order = make_order()
        response = self.board_client().post(
            reverse("catering_order", args=[order.pk]), {"task": "nonsense"}
        )
        self.assertEqual(response.status_code, 400)


class CateringNavigationTestCase(TestCase):
    """The tab only renders if the view name is whitelisted in ctx.py."""

    def test_the_board_gets_an_orders_tab(self):
        user = User.objects.create(username="board")
        group, _ = Group.objects.get_or_create(name=settings.BOARD_GROUP)
        user.groups.add(group)

        request = type("R", (), {})()
        request.user = user
        request.resolver_match = resolve(reverse("catering_orders"))
        _links, pages = categories_and_actions(request)

        self.assertIn("Beställningar", [action.text for action in pages])

    def test_a_worker_does_not(self):
        user = User.objects.create(username="worker")
        group, _ = Group.objects.get_or_create(name=settings.WORKER_GROUP)
        user.groups.add(group)

        request = type("R", (), {})()
        request.user = user
        request.resolver_match = resolve(reverse("catering_orders"))
        _links, pages = categories_and_actions(request)

        self.assertNotIn("Beställningar", [action.text for action in pages])


class CateringRetentionTestCase(TestCase):
    def test_orders_older_than_two_years_are_removed(self):
        recent = make_order()
        old = make_order(orderer="Gammal Beställare")
        CateringOrder.objects.filter(pk=old.pk).update(
            made=old.made - timedelta(days=365 * 3)
        )

        removed = remove_old_catering_orders()

        self.assertEqual(removed, 1)
        self.assertEqual(list(CateringOrder.objects.all()), [recent])


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CateringContactAddressTestCase(TestCase):
    """Orderers are pointed at the orders inbox, never at the board's."""

    def orderer_mails(self, order):
        return [m for m in mail.outbox if m.to == [order.orderer_email]]

    def test_the_receipt_points_at_the_orders_inbox(self):
        order = make_order()
        send_catering_order_receipt_email(order.pk)
        message = only_to(order.orderer_email)
        self.assertEqual(message.reply_to, [settings.CATERING_EMAIL])
        html = message.alternatives[0][0]
        self.assertIn(settings.CATERING_EMAIL, html)
        self.assertNotIn(settings.CONTACT_EMAIL, html)

    def test_the_decision_mails_do_too(self):
        for status in (CateringOrder.Status.APPROVED, CateringOrder.Status.DENIED):
            with self.subTest(status=status):
                mail.outbox = []
                order = make_order(status=status)
                send_catering_order_decision_email(order.pk)
                message = only_to(order.orderer_email)
                self.assertEqual(message.reply_to, [settings.CATERING_EMAIL])
                self.assertNotIn(settings.CONTACT_EMAIL, message.alternatives[0][0])

    def test_the_public_page_does_too(self):
        """Only the page's own contact line.

        The site-wide footer lists every Baljan address, the board's included,
        so the whole document is the wrong thing to assert on.
        """
        order = make_order()
        html = self.client.get(order.get_public_url()).content.decode()
        start = html.index("Behöver något ändras")
        sentence = html[start : html.index("uppge", start)]
        self.assertIn(settings.CATERING_EMAIL, sentence)
        self.assertNotIn(settings.CONTACT_EMAIL, sentence)

    def test_the_board_mail_carries_no_contact_line(self):
        """It lands in the orders inbox; naming that address is a loop."""
        order = make_order(status=CateringOrder.Status.APPROVED)
        send_catering_order_board_decision_email(order.pk)
        html = only_to(settings.CATERING_EMAIL).alternatives[0][0]
        self.assertNotIn("Har du frågor?", html)
        self.assertIn("Sektionscafé Baljan", html)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CateringOrderPublicPageTestCase(TestCase):
    """The orderer's own page, reached with the token from their mail."""

    def test_every_order_gets_its_own_token(self):
        first, second = make_order(), make_order()
        self.assertNotEqual(first.access_token, second.access_token)
        self.assertGreaterEqual(len(first.access_token), 32)

    def test_the_page_needs_no_login(self):
        order = make_order()
        response = self.client.get(order.get_public_url())
        self.assertEqual(response.status_code, 200)

    def test_a_wrong_token_is_not_found(self):
        make_order()
        response = self.client.get(
            reverse("catering_order_status", kwargs={"token": "nonsense"})
        )
        self.assertEqual(response.status_code, 404)

    def test_the_page_shows_the_order(self):
        order = make_order(
            items=[
                {
                    "field": "numberOfCoffee",
                    "label": "kaffe",
                    "count": 20,
                    "group": None,
                },
                {
                    "field": "numberOfJochen",
                    "label": "Jochen",
                    "count": 3,
                    "group": None,
                },
                {
                    "field": "numberOfKebabjochen",
                    "label": "kebab (ljust bröd)",
                    "count": 3,
                    "group": "Jochen",
                },
            ]
        )
        response = self.client.get(order.get_public_url())
        self.assertContains(response, "kaffe")
        self.assertContains(response, "kebab (ljust bröd)")
        self.assertContains(response, "Ingen laktos")
        self.assertContains(response, "Väntar")

    def test_the_internal_note_never_reaches_the_orderer(self):
        order = make_order(staff_note="Ring leverantören om mjölken")
        response = self.client.get(order.get_public_url())
        self.assertNotContains(response, "Ring leverantören om mjölken")

    def test_the_message_appears_only_once_the_order_is_decided(self):
        order = make_order(staff_message="Hämta vid disken.")
        self.assertNotContains(
            self.client.get(order.get_public_url()), "Hämta vid disken."
        )

        order.status = CateringOrder.Status.APPROVED
        order.save()
        self.assertContains(
            self.client.get(order.get_public_url()), "Hämta vid disken."
        )

    def test_the_page_asks_not_to_be_indexed(self):
        order = make_order()
        response = self.client.get(order.get_public_url())
        self.assertIn("noindex", response["X-Robots-Tag"])
        self.assertEqual(response["Referrer-Policy"], "no-referrer")

    def test_the_calendar_is_served_from_the_same_token(self):
        order = make_order(status=CateringOrder.Status.APPROVED)
        response = self.client.get(
            reverse("catering_order_calendar", kwargs={"token": order.access_token})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/calendar")
        self.assertIn("BEGIN:VCALENDAR", response.content.decode())

    def test_the_decision_mails_carry_the_link(self):
        for status in (CateringOrder.Status.APPROVED, CateringOrder.Status.DENIED):
            mail.outbox = []
            order = make_order(status=status)
            send_catering_order_decision_email(order.pk)
            self.assertIn(order.get_public_url(), mail.outbox[0].alternatives[0][0])


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CateringReceiptTestCase(TestCase):
    """Submitting now also tells the orderer that the order arrived."""

    @classmethod
    def setUpTestData(cls):
        today = date.today()
        Semester.objects.create(
            name="HT26",
            start=today - timedelta(days=30),
            end=today + timedelta(days=120),
        )

    def setUp(self):
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True
        self.addCleanup(setattr, celery_app.conf, "task_always_eager", False)
        self.addCleanup(setattr, celery_app.conf, "task_eager_propagates", False)

    def submit(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("order_from_us"), order_payload())
        return CateringOrder.objects.get()

    def test_the_orderer_gets_a_receipt_with_the_link(self):
        order = self.submit()
        receipt = only_to(order.orderer_email)
        self.assertIn(str(order.pk), receipt.subject)
        html = receipt.alternatives[0][0]
        self.assertIn(order.get_public_url(), html)
        self.assertIn("kaffe", html)

    def test_the_receipt_carries_no_invite(self):
        """Nothing is booked until the board says yes."""
        order = self.submit()
        self.assertEqual(only_to(order.orderer_email).attachments, [])

    def test_the_receipt_is_logged(self):
        order = self.submit()
        logged = CateringOrderEmail.objects.get(order=order)
        self.assertEqual(logged.kind, CateringOrderEmail.Kind.RECEIVED)
        self.assertEqual(logged.to_email, order.orderer_email)

    def test_the_board_still_gets_its_own_mail(self):
        self.submit()
        self.assertEqual(len(only_to(settings.CATERING_EMAIL).attachments), 1)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CateringBoardThreadTestCase(TestCase):
    """A decision answers in the mail thread the order arrived in."""

    @classmethod
    def setUpTestData(cls):
        today = date.today()
        Semester.objects.create(
            name="HT26",
            start=today - timedelta(days=30),
            end=today + timedelta(days=120),
        )
        cls.permission = Permission.objects.get(codename="manage_catering_orders")

    def setUp(self):
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True
        self.addCleanup(setattr, celery_app.conf, "task_always_eager", False)
        self.addCleanup(setattr, celery_app.conf, "task_eager_propagates", False)

        user = User.objects.create(username="board")
        group, _ = Group.objects.get_or_create(name=settings.BOARD_GROUP)
        group.permissions.add(self.permission)
        user.groups.add(group)
        profile = user.profile
        profile.has_seen_consent = True
        profile.save()
        self.client.force_login(user)

    def submit(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("order_from_us"), order_payload())
        return CateringOrder.objects.get()

    def decide(self, order, task, **extra):
        mail.outbox = []
        data = {
            "task": task,
            "staff_message": "Vi ses på fredag!",
            "handled_by_name": "Kalle Karlsson",
        }
        data.update(extra)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("catering_order", args=[order.pk]), data)
        order.refresh_from_db()
        return only_to(settings.CATERING_EMAIL)

    def test_submitting_records_the_thread(self):
        order = self.submit()
        board_mail = only_to(settings.CATERING_EMAIL)
        self.assertTrue(order.board_message_id)
        self.assertEqual(order.board_message_id, board_mail.extra_headers["Message-ID"])
        self.assertEqual(order.board_subject, board_mail.subject)

    def test_approving_answers_in_that_thread(self):
        order = self.submit()
        thread_id = order.board_message_id
        subject = order.board_subject

        answer = self.decide(order, "approve")
        self.assertEqual(answer.subject, "Re: %s" % subject)
        self.assertEqual(answer.extra_headers["In-Reply-To"], thread_id)
        self.assertEqual(answer.extra_headers["References"], thread_id)

        html = answer.alternatives[0][0]
        self.assertIn("godkänd", html)
        self.assertIn("board", html)
        self.assertIn("Vi ses på fredag!", html)
        self.assertIn(order.get_absolute_url(), html)

    def test_a_reply_from_the_thread_reaches_the_orderer(self):
        order = self.submit()
        answer = self.decide(order, "approve")
        self.assertEqual(answer.reply_to, [order.orderer_email])

    def test_denying_threads_too(self):
        order = self.submit()
        thread_id = order.board_message_id
        answer = self.decide(order, "deny")
        self.assertEqual(answer.extra_headers["In-Reply-To"], thread_id)
        self.assertIn("nekad", answer.alternatives[0][0])

    def test_an_edited_order_keeps_the_original_subject(self):
        """Gmail splits a thread whose subject moved, References or not."""
        order = self.submit()
        subject = order.board_subject

        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                reverse("catering_order", args=[order.pk]),
                order_payload(
                    task="save",
                    orderer="Bo Bosson",
                    ordererEmail="bo@example.com",
                    association="Annan sektion",
                    numberOfCoffee=5,
                    pickup="1",
                    date=next_weekday(14).isoformat(),
                ),
            )
        order.refresh_from_db()
        self.assertEqual(order.association, "Annan sektion")

        answer = self.decide(order, "approve")
        self.assertEqual(answer.subject, "Re: %s" % subject)

    def test_an_order_without_a_thread_is_still_reported(self):
        """Orders from before the id was stored: no threading, but a mail."""
        order = make_order(status=CateringOrder.Status.APPROVED)
        mail.outbox = []
        send_catering_order_board_decision_email(order.pk)

        answer = only_to(settings.CATERING_EMAIL)
        self.assertNotIn("In-Reply-To", answer.extra_headers)
        self.assertIn(str(order.pk), answer.subject)

    def test_the_later_bookkeeping_states_tell_nobody(self):
        order = self.submit()
        mail.outbox = []
        for status in ("delivered", "invoiced", "cancelled"):
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(
                    reverse("catering_order", args=[order.pk]),
                    {
                        "task": "status",
                        "status": status,
                        "handled_by_name": "Kalle Karlsson",
                    },
                )
        self.assertEqual(mail.outbox, [])

    def test_a_pending_order_is_not_reported(self):
        order = make_order()
        send_catering_order_board_decision_email(order.pk)
        self.assertEqual(mail.outbox, [])

    def test_a_deleted_order_does_not_raise(self):
        send_catering_order_board_decision_email(9999)
        self.assertEqual(mail.outbox, [])


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    GOOGLE_CALENDAR_ID="testkalender@group.calendar.google.com",
)
class CateringCalendarTestCase(TestCase):
    """Approved orders are mirrored into the shared orders calendar."""

    @classmethod
    def setUpTestData(cls):
        today = date.today()
        Semester.objects.create(
            name="HT26",
            start=today - timedelta(days=30),
            end=today + timedelta(days=120),
        )
        cls.permission = Permission.objects.get(codename="manage_catering_orders")

    def setUp(self):
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True
        self.addCleanup(setattr, celery_app.conf, "task_always_eager", False)
        self.addCleanup(setattr, celery_app.conf, "task_eager_propagates", False)

        # Stand in for Google at the module boundary, the way test_phone does.
        self.upsert = mock.patch.object(
            google, "upsert_event", return_value="evt-1"
        ).start()
        self.delete = mock.patch.object(google, "delete_event").start()
        self.addCleanup(mock.patch.stopall)

    def board_client(self):
        user = User.objects.create(username="board")
        group, _ = Group.objects.get_or_create(name=settings.BOARD_GROUP)
        group.permissions.add(self.permission)
        user.groups.add(group)
        profile = user.profile
        profile.has_seen_consent = True
        profile.save()
        self.client.force_login(user)
        return self.client

    def decide(self, order, task, **extra):
        data = {"task": task, "handled_by_name": "Kalle Karlsson"}
        data.update(extra)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("catering_order", args=[order.pk]), data)
        order.refresh_from_db()
        return order

    def test_approving_writes_an_event_and_keeps_its_id(self):
        order = make_order()
        self.board_client()
        order = self.decide(order, "approve")

        self.assertEqual(self.upsert.call_count, 1)
        calendar_id, event_id, body = self.upsert.call_args[0]
        self.assertEqual(calendar_id, settings.GOOGLE_CALENDAR_ID)
        self.assertEqual(event_id, "")
        self.assertEqual(order.calendar_event_id, "evt-1")

        self.assertIn(order.association, body["summary"])
        self.assertIn(order.orderer_phone, body["description"])
        self.assertIn("Ingen laktos", body["description"])
        self.assertEqual(body["location"], "Baljan")
        self.assertEqual(body["start"]["timeZone"], settings.TIME_ZONE)

    def test_approving_again_moves_the_same_event(self):
        order = make_order()
        self.board_client()
        self.decide(order, "approve")
        self.decide(order, "approve")

        self.assertEqual(self.upsert.call_count, 2)
        self.assertEqual(self.upsert.call_args[0][1], "evt-1")
        self.assertEqual(self.delete.call_count, 0)

    def test_editing_an_approved_order_moves_the_event(self):
        order = make_order()
        self.board_client()
        self.decide(order, "approve")
        self.upsert.reset_mock()

        later = next_weekday(21)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                reverse("catering_order", args=[order.pk]),
                order_payload(task="save", date=later.isoformat()),
            )

        self.assertEqual(self.upsert.call_count, 1)
        self.assertEqual(self.upsert.call_args[0][1], "evt-1")
        self.assertIn(
            later.strftime("%Y-%m-%d"), self.upsert.call_args[0][2]["summary"]
        )

    def test_denying_takes_the_event_away(self):
        order = make_order()
        self.board_client()
        self.decide(order, "approve")
        order = self.decide(order, "deny")

        self.delete.assert_called_once_with(settings.GOOGLE_CALENDAR_ID, "evt-1")
        self.assertEqual(order.calendar_event_id, "")

    def test_cancelling_takes_it_away_too(self):
        order = make_order()
        self.board_client()
        self.decide(order, "approve")
        order = self.decide(order, "status", status="cancelled")

        self.delete.assert_called_once_with(settings.GOOGLE_CALENDAR_ID, "evt-1")
        self.assertEqual(order.calendar_event_id, "")

    def test_the_later_bookkeeping_states_keep_the_event(self):
        order = make_order()
        self.board_client()
        self.decide(order, "approve")
        order = self.decide(order, "status", status="delivered")

        self.assertEqual(self.delete.call_count, 0)
        self.assertEqual(order.calendar_event_id, "evt-1")

    def test_a_pending_order_is_not_in_the_calendar(self):
        make_order()
        self.assertEqual(self.upsert.call_count, 0)

    def test_google_failing_does_not_fell_the_decision(self):
        """The status and the mails stand even when the calendar does not.

        eager_propagates is turned off for this one: it makes a failing task
        raise in whoever queued it, which a real worker never does. Production
        only ever calls .delay() from an on_commit hook.
        """
        celery_app.conf.task_eager_propagates = False
        self.upsert.side_effect = RuntimeError("Google är nere")
        order = make_order()
        self.board_client()

        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                reverse("catering_order", args=[order.pk]),
                {
                    "task": "approve",
                    "staff_message": "Vi ses!",
                    "handled_by_name": "Kalle Karlsson",
                },
            )

        order.refresh_from_db()
        self.assertEqual(order.status, CateringOrder.Status.APPROVED)
        self.assertEqual(order.calendar_event_id, "")
        self.assertIn("Vi ses!", only_to(order.orderer_email).alternatives[0][0])

    def test_the_purge_takes_the_events_with_it(self):
        order = make_order(
            status=CateringOrder.Status.APPROVED, calendar_event_id="evt-old"
        )
        CateringOrder.objects.filter(pk=order.pk).update(
            made=order.made - timedelta(days=365 * 3)
        )

        removed = remove_old_catering_orders()

        self.assertEqual(removed, 1)
        self.delete.assert_called_once_with(settings.GOOGLE_CALENDAR_ID, "evt-old")

    def test_a_stubborn_event_does_not_stop_the_purge(self):
        order = make_order(
            status=CateringOrder.Status.APPROVED, calendar_event_id="evt-old"
        )
        CateringOrder.objects.filter(pk=order.pk).update(
            made=order.made - timedelta(days=365 * 3)
        )
        self.delete.side_effect = RuntimeError("Google är nere")

        self.assertEqual(remove_old_catering_orders(), 1)
        self.assertFalse(CateringOrder.objects.exists())


class CateringCalendarOffTestCase(TestCase):
    """With no calendar configured, nothing reaches Google at all."""

    @override_settings(GOOGLE_CALENDAR_ID="")
    def test_nothing_is_called(self):
        with mock.patch.object(google, "setup_calendar_service") as service:
            order = make_order(status=CateringOrder.Status.APPROVED)
            sync_catering_order_calendar(order.pk)
        self.assertEqual(service.call_count, 0)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CateringHandlerNameTestCase(TestCase):
    """A decision has to carry the name of the person who took it.

    The board shares one account across shifts, so `handled_by` says which
    login was used and nothing about who was standing there.
    """

    @classmethod
    def setUpTestData(cls):
        today = date.today()
        Semester.objects.create(
            name="HT26",
            start=today - timedelta(days=30),
            end=today + timedelta(days=120),
        )
        cls.permission = Permission.objects.get(codename="manage_catering_orders")

    def setUp(self):
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True
        self.addCleanup(setattr, celery_app.conf, "task_always_eager", False)
        self.addCleanup(setattr, celery_app.conf, "task_eager_propagates", False)

        user = User.objects.create(username="delat-styrelsekonto")
        group, _ = Group.objects.get_or_create(name=settings.BOARD_GROUP)
        group.permissions.add(self.permission)
        user.groups.add(group)
        profile = user.profile
        profile.has_seen_consent = True
        profile.save()
        self.user = user
        self.client.force_login(user)

    def decide(self, order, data):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse("catering_order", args=[order.pk]), data)

    def test_the_typed_name_is_stored_beside_the_account(self):
        order = make_order()
        self.decide(
            order, {"task": "approve", "staff_message": "", "handled_by_name": "Anna A"}
        )
        order.refresh_from_db()
        self.assertEqual(order.handled_by_name, "Anna A")
        self.assertEqual(order.handled_by, self.user)
        self.assertEqual(order.handled_by_label, "Anna A")

    def test_the_buttons_are_not_disabled(self):
        """Pressing one is how the reminder is asked for."""
        order = make_order()
        response = self.client.get(reverse("catering_order", args=[order.pk]))
        self.assertNotContains(response, "disabled")

    def test_a_decision_without_a_name_is_refused(self):
        order = make_order()
        response = self.decide(order, {"task": "approve", "staff_message": ""})
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertTrue(order.is_pending)
        self.assertEqual(mail.outbox, [])
        self.assertContains(response, "Skriv ditt namn")

    def test_a_name_of_only_spaces_is_refused(self):
        order = make_order()
        self.decide(
            order, {"task": "approve", "staff_message": "", "handled_by_name": "   "}
        )
        order.refresh_from_db()
        self.assertTrue(order.is_pending)

    def test_the_typed_message_survives_a_missing_name(self):
        """Nobody should have to write their message twice."""
        order = make_order()
        response = self.decide(
            order, {"task": "approve", "staff_message": "Vi ses på fredag!"}
        )
        self.assertContains(response, "Vi ses på fredag!")

    def test_the_name_is_never_prefilled(self):
        """The whole point: a shared account must not sign for a person."""
        order = make_order(handled_by_name="Anna A")
        response = self.client.get(reverse("catering_order", args=[order.pk]))
        field = response.context["decision_form"]["handled_by_name"]
        self.assertFalse(field.value())

    def test_the_page_carries_the_hooks_behind_the_reminder(self):
        """The reminder itself is JavaScript and out of reach of this client.

        What can be pinned is that the ids it hangs off, the `required`
        attribute that stands in for it without JavaScript, and the text it
        reveals are all actually rendered.
        """
        order = make_order()
        response = self.client.get(reverse("catering_order", args=[order.pk]))
        for hook in (
            'id="catering-handled-by-name"',
            'id="catering-approve"',
            'id="catering-deny"',
            'id="catering-status-handled-by-name"',
            'id="catering-status-submit"',
            'name="handled_by_name"',
            "required",
            "invalid-feedback",
            "Skriv ditt namn innan du godkänner eller nekar.",
            "Skriv ditt namn innan du ändrar statusen.",
        ):
            with self.subTest(hook=hook):
                self.assertContains(response, hook)

    def test_a_status_change_needs_a_name_too(self):
        order = make_order(status=CateringOrder.Status.APPROVED)
        self.decide(order, {"task": "status", "status": "delivered"})
        order.refresh_from_db()
        self.assertEqual(order.status, CateringOrder.Status.APPROVED)

    def test_a_status_change_overwrites_the_name_with_the_new_one(self):
        """`handled_by` is overwritten either way, so the name must follow.

        Keeping the older name would leave the pair describing two different
        people doing two different things.
        """
        order = make_order()
        self.decide(
            order, {"task": "approve", "staff_message": "", "handled_by_name": "Anna A"}
        )
        self.decide(
            order,
            {"task": "status", "status": "delivered", "handled_by_name": "Bo B"},
        )
        order.refresh_from_db()
        self.assertEqual(order.handled_by_name, "Bo B")

    def test_an_unknown_status_is_refused_before_the_name_is_checked(self):
        """A tampered request is a 400, a forgotten name is not."""
        order = make_order()
        response = self.client.post(
            reverse("catering_order", args=[order.pk]),
            {"task": "status", "status": "nonsense"},
        )
        self.assertEqual(response.status_code, 400)

    def test_the_page_names_the_person_and_keeps_the_account(self):
        order = make_order()
        self.decide(
            order, {"task": "approve", "staff_message": "", "handled_by_name": "Anna A"}
        )
        response = self.client.get(reverse("catering_order", args=[order.pk]))
        self.assertContains(response, "Anna A")
        self.assertContains(response, "konto: delat-styrelsekonto")

    def test_the_board_mail_names_the_person(self):
        order = make_order()
        self.decide(
            order, {"task": "approve", "staff_message": "", "handled_by_name": "Anna A"}
        )
        html = only_to(settings.CATERING_EMAIL).alternatives[0][0]
        self.assertIn("Anna A", html)

    def test_an_order_from_before_the_field_still_shows_the_account(self):
        order = make_order(handled_by=self.user, handled_by_name="")
        self.assertEqual(order.handled_by_label, "delat-styrelsekonto")
        response = self.client.get(reverse("catering_order", args=[order.pk]))
        self.assertEqual(response.status_code, 200)

    def test_an_undecided_order_names_nobody(self):
        self.assertEqual(make_order().handled_by_label, "")

    def test_the_public_page_never_shows_who_decided(self):
        order = make_order()
        self.decide(
            order, {"task": "approve", "staff_message": "", "handled_by_name": "Anna A"}
        )
        order.refresh_from_db()
        # Logged out: the orderer reads this page with a token, not an account,
        # and the navbar would otherwise print the staff username back at us.
        self.client.logout()
        page = self.client.get(order.get_public_url())
        self.assertNotContains(page, "Anna A")
        self.assertNotContains(page, "delat-styrelsekonto")


class CateringCalendarDescriptionTestCase(TestCase):
    """What a calendar entry says about an order.

    One function feeds all four consumers: the Google event, the invite on the
    board's mail, the invite on the approval mail, and the public .ics.
    """

    def description(self, order):
        from cafesys.baljan import ical

        return ical.catering_order_description(order)

    def test_sub_types_are_nested_under_their_group(self):
        text = self.description(make_order())
        self.assertIn("Antal Jochen: 3", text)
        self.assertIn("  - kebab (ljust bröd): 3", text)

    def test_a_sub_type_never_looks_like_a_separate_item(self):
        """The bug: "Antal pastasallad: 50" beside "Antal grekisk: 10"."""
        self.assertNotIn("Antal kebab (ljust bröd)", self.description(make_order()))

    def test_the_nesting_survives_stripped_leading_whitespace(self):
        """Why the dash is there and not just the indent.

        Google's mobile clients and some iCal unfolders eat leading spaces, so
        a line that only says "kebab: 3" once de-indented would read as its own
        item again.
        """
        lines = [line.lstrip() for line in self.description(make_order()).splitlines()]
        self.assertIn("- kebab (ljust bröd): 3", lines)

    def test_a_group_with_no_count_still_lists_its_children(self):
        """No invented total: the orderer never typed one."""
        order = make_order(
            items=[
                {
                    "field": "numberOfPastasalad",
                    "label": "pastasallad",
                    "count": 0,
                    "group": None,
                },
                {
                    "field": "numberOfGrekisk",
                    "label": "grekisk",
                    "count": 5,
                    "group": "pastasallad",
                },
            ]
        )
        text = self.description(order)
        self.assertIn("pastasallad:", text)
        self.assertIn("  - grekisk: 5", text)
        self.assertNotIn("Antal pastasallad", text)

    def test_empty_groups_are_left_out(self):
        self.assertNotIn("te", self.description(make_order()).splitlines()[4])

    def test_it_names_who_approved(self):
        order = make_order(
            status=CateringOrder.Status.APPROVED, handled_by_name="Anna A"
        )
        self.assertIn("Godkänd av: Anna A", self.description(order))

    def test_an_undecided_order_names_nobody(self):
        """The board's invite is built before anyone has decided anything."""
        self.assertNotIn("Godkänd av", self.description(make_order()))

    def test_the_fixture_matches_what_the_form_really_stores(self):
        """Every sub-type needs its parent row, or grouped_items drops it.

        `_catering_items()` always writes the parent. A fixture that does not
        would make the nesting tests above pass while proving nothing.
        """
        items = make_order().items
        parents = {item["label"] for item in items if not item["group"]}
        for item in items:
            if item["group"]:
                self.assertIn(item["group"], parents)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CateringOrderTabsTestCase(TestCase):
    """The board's list, once there are more orders than fit on a screen."""

    @classmethod
    def setUpTestData(cls):
        today = date.today()
        Semester.objects.create(
            name="HT26",
            start=today - timedelta(days=30),
            end=today + timedelta(days=200),
        )
        cls.permission = Permission.objects.get(codename="manage_catering_orders")

    def setUp(self):
        user = User.objects.create(username="styrelsen")
        group, _ = Group.objects.get_or_create(name=settings.BOARD_GROUP)
        group.permissions.add(self.permission)
        user.groups.add(group)
        profile = user.profile
        profile.has_seen_consent = True
        profile.save()
        self.client.force_login(user)

    def listing(self, **params):
        return self.client.get(reverse("catering_orders"), params)

    def orderers(self, response):
        return [order.orderer for order in response.context["orders"]]

    def test_the_default_tab_is_the_one_that_needs_work(self):
        make_order(orderer="Väntar")
        make_order(orderer="Klar", status=CateringOrder.Status.APPROVED)
        response = self.listing()
        self.assertEqual(response.context["tab"], "att-behandla")
        self.assertEqual(self.orderers(response), ["Väntar"])

    def test_an_overdue_order_comes_first(self):
        """Nobody answered it. That is the most urgent thing on the page."""
        make_order(orderer="Nästa månad", date=date.today() + timedelta(days=30))
        make_order(orderer="Förra veckan", date=date.today() - timedelta(days=7))
        self.assertEqual(
            self.orderers(self.listing())[0],
            "Förra veckan",
        )

    def test_the_week_tab_holds_only_the_next_seven_days(self):
        today = date.today()
        make_order(orderer="Idag", date=today)
        make_order(orderer="Om sex dagar", date=today + timedelta(days=6))
        make_order(orderer="Om sju dagar", date=today + timedelta(days=7))
        self.assertEqual(
            self.orderers(self.listing(tab="denna-vecka")),
            ["Idag", "Om sex dagar"],
        )

    def test_the_upcoming_tab_starts_where_the_week_ends(self):
        today = date.today()
        make_order(orderer="Om sex dagar", date=today + timedelta(days=6))
        make_order(orderer="Om sju dagar", date=today + timedelta(days=7))
        make_order(orderer="Om en månad", date=today + timedelta(days=30))
        self.assertEqual(
            self.orderers(self.listing(tab="kommande")),
            ["Om sju dagar", "Om en månad"],
        )

    def test_the_history_tab_holds_the_past_and_the_dead(self):
        today = date.today()
        make_order(orderer="Igår", date=today - timedelta(days=1))
        make_order(
            orderer="Nekad",
            date=today + timedelta(days=3),
            status=CateringOrder.Status.DENIED,
        )
        make_order(orderer="Kommande", date=today + timedelta(days=3))
        self.assertCountEqual(
            self.orderers(self.listing(tab="historik")), ["Igår", "Nekad"]
        )

    def test_a_dead_order_never_shows_up_as_work(self):
        make_order(
            orderer="Avbeställd",
            date=date.today() + timedelta(days=2),
            status=CateringOrder.Status.CANCELLED,
        )
        self.assertEqual(self.orderers(self.listing(tab="denna-vecka")), [])
        self.assertEqual(self.orderers(self.listing(tab="kommande")), [])

    def test_the_tabs_may_overlap(self):
        """Not a partition: the counts are not meant to sum to the total."""
        make_order(date=date.today() + timedelta(days=1))
        counts = self.listing().context["tabs"]
        by_key = {tab["key"]: tab["count"] for tab in counts}
        self.assertEqual(by_key["att-behandla"], 1)
        self.assertEqual(by_key["denna-vecka"], 1)

    def test_every_tab_carries_all_four_counts(self):
        make_order()
        tabs = self.listing(tab="historik").context["tabs"]
        self.assertEqual([tab["key"] for tab in tabs], [key for key, _ in TAB_KEYS])
        self.assertTrue(any(tab["active"] for tab in tabs))

    def test_the_counts_take_one_query(self):
        from cafesys.baljan.views import catering_tab_counts

        make_order()
        with self.assertNumQueries(1):
            catering_tab_counts(date.today())

    def test_the_counts_ignore_the_search_box(self):
        """A badge that moves as you type stops measuring the workload."""
        make_order()
        response = self.listing(association="finns-inte")
        self.assertEqual(response.context["paginator"].count, 0)
        by_key = {tab["key"]: tab["count"] for tab in response.context["tabs"]}
        self.assertEqual(by_key["att-behandla"], 1)

    def test_an_unknown_tab_falls_back_to_the_default(self):
        """A stale bookmark should land somewhere useful, not on a 404."""
        response = self.listing(tab="nonsens")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["tab"], "att-behandla")

    def test_filtering_stays_on_the_tab(self):
        response = self.listing(tab="historik")
        self.assertContains(response, 'name="tab" value="historik"')

    def test_the_tab_links_keep_the_search(self):
        response = self.listing(tab="historik", association="Testsektionen")
        self.assertContains(response, "association=Testsektionen")

    def test_the_list_names_who_handled_each_order(self):
        make_order(
            status=CateringOrder.Status.APPROVED,
            handled_by_name="Anna A",
            date=date.today() - timedelta(days=1),
        )
        self.assertContains(self.listing(tab="historik"), "Anna A")

    def test_a_pickup_two_days_out_is_flagged(self):
        make_order(date=date.today() + timedelta(days=2))
        self.assertContains(self.listing(), "Hämtas om 2 dagar")

    def test_a_far_off_pickup_is_not_flagged(self):
        make_order(date=date.today() + timedelta(days=30))
        self.assertNotContains(self.listing(), "Hämtas om")

    def test_an_overdue_order_is_flagged_as_late(self):
        make_order(date=date.today() - timedelta(days=3))
        self.assertContains(self.listing(), "Försenad 3 dagar")

    def test_a_decided_order_is_never_flagged(self):
        """A near date is a plan once it has been answered, not a problem."""
        make_order(
            date=date.today() + timedelta(days=1), status=CateringOrder.Status.APPROVED
        )
        self.assertNotContains(self.listing(tab="denna-vecka"), "Hämtas")

    def test_days_until_pickup_counts_from_today(self):
        order = make_order(date=date.today() + timedelta(days=4))
        self.assertEqual(order.days_until_pickup, 4)

    def test_days_until_pickup_is_negative_for_the_past(self):
        order = make_order(date=date.today() - timedelta(days=2))
        self.assertEqual(order.days_until_pickup, -2)

    def test_paging_keeps_the_tab_and_the_search(self):
        """The old pagination links dropped every parameter but the page."""
        # paginate_by=50 with paginate_orphans=10, so 60 rows still fit on
        # one page and would prove nothing.
        for index in range(65):
            make_order(orderer="Best %s" % index, date=date.today() - timedelta(days=1))
        response = self.listing(tab="historik", association="Testsektionen")
        self.assertContains(response, "tab=historik")
        self.assertContains(response, "association=Testsektionen")
        self.assertContains(response, "page=2")


class PaginationTagTestCase(TestCase):
    """The page links are shared with the user's own order history.

    They were changed so the catering tabs and filters survive a page turn;
    this is here so the other consumer is not quietly broken by that.
    """

    def test_the_users_own_orders_still_page(self):
        from cafesys.baljan.models import Order

        user = User.objects.create(username="blippare")
        profile = user.profile
        profile.has_seen_consent = True
        profile.save()
        self.client.force_login(user)

        # paginate_by=50 with paginate_orphans=10.
        Order.objects.bulk_create([Order(user=user, paid=10) for _ in range(65)])

        response = self.client.get(reverse("orders"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "page=2")
