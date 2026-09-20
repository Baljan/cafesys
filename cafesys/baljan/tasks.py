# -*- coding: utf-8 -*-
from celery import shared_task
from ..celery import app
from django.conf import settings

from django.core.cache import cache
from django.core.mail import EmailMessage
from logging import getLogger

logger = getLogger(__name__)


@app.task
def send_mail_task(title, body, from_email, to_emails, **kwargs):
    EmailMessage(title, body, from_email, to_emails, **kwargs).send()


@shared_task
def update_stats():
    from . import stats

    for location in stats.ALL_LOCATIONS:
        data = stats.compute_stats_for_location(location)
        cache.set(stats.get_cache_key(location), data, settings.STATS_CACHE_TTL)


@shared_task
def ensure_gmail_watch():
    from . import google

    google.ensure_gmail_watch()


@shared_task
def remove_old_users():
    """
    Dates to consider:
     - Last login
     - Last blipp
     - Last shift
     - Last refill
     - Balance (maybe)

    We remove all accounts that has not had any recorded activity for the last 7 years
    """

    from .models import Order, ShiftSignup, BalanceCode

    from django.utils import timezone
    from django.contrib.auth.models import User

    from dateutil.relativedelta import relativedelta

    seven_years_ago = timezone.now() - relativedelta(years=7)
    old_users = User.objects.filter(last_login__lt=seven_years_ago).all()

    for user in old_users:
        old_shift = (
            ShiftSignup.objects.filter(user=user)
            .values_list("shift__when", flat=True)
            .last()
        )
        old_blipp = (
            Order.objects.filter(user=user).values_list("put_at", flat=True).last()
        )
        old_refill = (
            BalanceCode.objects.filter(used_by=user)
            .values_list("used_at", flat=True)
            .last()
        )

        if not all(
            [
                old_shift and old_shift >= seven_years_ago.date(),
                old_blipp and old_blipp >= seven_years_ago,
                old_refill and old_refill >= seven_years_ago.date(),
            ]
        ):
            user.delete()


@app.task
def send_catering_order_decision_email(order_id):
    """Tell the orderer that the board has decided on their catering order.

    Only the primary key travels through the broker: the task serialiser is JSON,
    so the calendar attachment cannot be passed as an argument. It is rebuilt here
    from the stored order instead.
    """
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string

    from . import ical
    from .models import CateringOrder, CateringOrderEmail

    order = CateringOrder.objects.filter(pk=order_id).first()
    if order is None:
        logger.warning("catering order %s is gone, no email sent", order_id)
        return

    templates = {
        CateringOrder.Status.APPROVED: "baljan/email/order_approved.html",
        CateringOrder.Status.DENIED: "baljan/email/order_denied.html",
    }
    template = templates.get(order.status)
    if template is None:
        logger.warning(
            "catering order %s has status %r, no decision email to send",
            order_id,
            order.status,
        )
        return

    approved = order.status == CateringOrder.Status.APPROVED
    verb = "godkänd" if approved else "nekad"
    subject = (
        f"[Beställning {order.date.strftime('%Y-%m-%d')} "
        f"| {order.association} | #{order.pk}] Din beställning är {verb}"
    )

    html_content = render_to_string(
        template,
        {
            "order": order,
            "order_fields": order.ordered_items(),
            "CATERING_EMAIL": settings.CATERING_EMAIL,
        },
    )

    msg = EmailMultiAlternatives(
        subject,
        "",
        f"Baljan <{settings.DEFAULT_FROM_EMAIL}>",
        [order.orderer_email],
        reply_to=[settings.CATERING_EMAIL],
    )
    msg.attach_alternative(html_content, "text/html")

    if approved:
        msg.attach("event.ics", ical.for_catering_order(order), "text/calendar")

    msg.send()

    # Only now, once the message has left: a row means it was sent.
    CateringOrderEmail.objects.create(
        order=order,
        kind=(
            CateringOrderEmail.Kind.APPROVED
            if approved
            else CateringOrderEmail.Kind.DENIED
        ),
        subject=subject,
        to_email=order.orderer_email,
        body=order.staff_message or "",
    )
    logger.info("decision email for catering order %s sent", order_id)


@app.task
def send_catering_order_receipt_email(order_id):
    """Confirm to the orderer that their order arrived.

    This is the only mail that goes out before the board has decided anything,
    and it is where the orderer gets the link to their own status page: the
    token is never shown anywhere else.
    """
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string

    from .models import CateringOrder, CateringOrderEmail

    order = CateringOrder.objects.filter(pk=order_id).first()
    if order is None:
        logger.warning("catering order %s is gone, no receipt sent", order_id)
        return

    subject = (
        f"[Beställning {order.date.strftime('%Y-%m-%d')} "
        f"| {order.association} | #{order.pk}] Vi har tagit emot din beställning"
    )

    html_content = render_to_string(
        "baljan/email/order_received.html",
        {
            "order": order,
            "CATERING_EMAIL": settings.CATERING_EMAIL,
        },
    )

    msg = EmailMultiAlternatives(
        subject,
        "",
        f"Baljan <{settings.DEFAULT_FROM_EMAIL}>",
        [order.orderer_email],
        reply_to=[settings.CATERING_EMAIL],
    )
    msg.attach_alternative(html_content, "text/html")
    # No invite yet: nothing is booked until the board says yes.
    msg.send()

    CateringOrderEmail.objects.create(
        order=order,
        kind=CateringOrderEmail.Kind.RECEIVED,
        subject=subject,
        to_email=order.orderer_email,
    )
    logger.info("receipt for catering order %s sent", order_id)


@app.task
def send_catering_order_board_decision_email(order_id):
    """Answer in the board's own mail thread that the order has been decided.

    The order arrived as a mail to the catering address, and a decision taken on
    the website would otherwise leave that thread looking untouched. Replying to
    it keeps the inbox honest about what is still open.

    Not written to `CateringOrderEmail`: that model is the orderer's history, and
    the board's page lists it under "Skickade mail".
    """
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string

    from .models import CateringOrder

    order = CateringOrder.objects.filter(pk=order_id).first()
    if order is None:
        logger.warning("catering order %s is gone, board not told", order_id)
        return

    if order.status not in (
        CateringOrder.Status.APPROVED,
        CateringOrder.Status.DENIED,
    ):
        logger.warning(
            "catering order %s has status %r, nothing to tell the board",
            order_id,
            order.status,
        )
        return

    approved = order.status == CateringOrder.Status.APPROVED

    if order.board_subject:
        subject = "Re: %s" % order.board_subject
    else:
        # Orders placed before the subject was stored, or whose original mail
        # never left. Threading is lost; the message itself still is not.
        logger.warning(
            "catering order %s has no stored board subject, sending untailed",
            order_id,
        )
        subject = (
            f"[Beställning {order.date.strftime('%Y-%m-%d')} "
            f"| {order.association} | #{order.pk}] "
            f"{'Godkänd' if approved else 'Nekad'} från hemsidan"
        )

    headers = {}
    if order.board_message_id:
        headers["In-Reply-To"] = order.board_message_id
        headers["References"] = order.board_message_id

    html_content = render_to_string(
        "baljan/email/order_board_decision.html",
        # No contact address: this mail is already in the orders inbox.
        {"order": order, "approved": approved},
    )

    msg = EmailMultiAlternatives(
        subject,
        "",
        f"Baljan <{settings.DEFAULT_FROM_EMAIL}>",
        [settings.CATERING_EMAIL],
        headers=headers,
        # Same as the original mail, so a reply from the thread reaches the
        # person who ordered.
        reply_to=[order.orderer_email],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    logger.info("board told about the decision on catering order %s", order_id)


@shared_task
def remove_old_catering_orders():
    """Drop catering orders older than two years.

    The order form is public and collects the name, email address and phone
    number of people who are not members, so the rows are personal data with no
    owning account. Nothing else prunes them.
    """
    from django.utils import timezone

    from dateutil.relativedelta import relativedelta

    from .models import CateringOrder

    cutoff = timezone.now() - relativedelta(years=2)
    deleted, _ = CateringOrder.objects.filter(made__lt=cutoff).delete()
    if deleted:
        logger.info("removed %s old catering order(s)", deleted)
    return deleted
