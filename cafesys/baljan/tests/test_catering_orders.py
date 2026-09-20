from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import resolve, reverse

from cafesys.baljan.actions import categories_and_actions
from cafesys.celery import app as celery_app
from cafesys.baljan.models import CateringOrder, CateringOrderEmail, Semester
from cafesys.baljan.tasks import (
    remove_old_catering_orders,
    send_catering_order_board_decision_email,
    send_catering_order_decision_email,
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
            [("kaffe", 20), ("kebab (ljust bröd)", 3)],
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
        order.approve(user=user, message="Vi ses!", notify=False)
        order.refresh_from_db()
        self.assertEqual(order.status, CateringOrder.Status.APPROVED)
        self.assertEqual(order.handled_by, user)
        self.assertEqual(order.staff_message, "Vi ses!")
        self.assertIsNotNone(order.handled_at)

    def test_deny_records_who_decided(self):
        user = User.objects.create(username="board-member")
        order = make_order()
        order.deny(user=user, message="Stängt den dagen", notify=False)
        order.refresh_from_db()
        self.assertEqual(order.status, CateringOrder.Status.DENIED)
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

    def test_the_list_can_be_filtered_by_status(self):
        make_order()
        make_order(orderer="Bertil B", status=CateringOrder.Status.APPROVED)
        client = self.board_client()

        approved = client.get(reverse("catering_orders"), {"status": "approved"})
        self.assertEqual(approved.context["paginator"].count, 1)
        self.assertContains(approved, "Bertil B")

        pending = client.get(reverse("catering_orders"), {"status": "pending"})
        self.assertEqual(pending.context["paginator"].count, 1)

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
                {"task": "approve", "staff_message": "Vi ses på fredag!"},
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
                {"task": "deny", "staff_message": "Tyvärr stängt."},
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
                {"task": "status", "status": "delivered"},
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
                {"task": "status", "status": "cancelled"},
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
                {"task": "approve", "staff_message": "Vi ses på fredag!"},
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
        data = {"task": task, "staff_message": "Vi ses på fredag!"}
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
                    {"task": "status", "status": status},
                )
        self.assertEqual(mail.outbox, [])

    def test_a_pending_order_is_not_reported(self):
        order = make_order()
        send_catering_order_board_decision_email(order.pk)
        self.assertEqual(mail.outbox, [])

    def test_a_deleted_order_does_not_raise(self):
        send_catering_order_board_decision_email(9999)
        self.assertEqual(mail.outbox, [])
