"""Inhopp posted in Slack by personalansvarig, turned into shift sign-ups."""

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import partial
from logging import getLogger

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.sites.models import Site
from django.db import transaction

from .models import Located, PendingShiftSignup, Shift, ShiftSignup
from .tasks import post_slack_thread_message, send_mail_task

logger = getLogger(__name__)

HEADER_RE = re.compile(
    r"inhopp\s+(\d{1,2})/(\d{1,2})\s+(fm|lunch|em)\s+(baljan|byttan)"
    r"(?:\s*\((idag|imorgon)\))?",
    re.IGNORECASE,
)
LIU_ID_RE = re.compile(r"\b[a-z]{3,5}\d{3}\b")
SPANS = {"fm": 0, "lunch": 1, "em": 2}
LOCATIONS = {"baljan": Located.KARALLEN, "byttan": Located.STH_VALLA}


class InhoppParseError(ValueError):
    pass


@dataclass
class InhoppRequest:
    when: date
    span: int
    location: int
    in_ids: list
    out_ids: list
    warnings: list = field(default_factory=list)


@dataclass
class InhoppResult:
    added: list = field(default_factory=list)
    already: list = field(default_factory=list)
    pending: list = field(default_factory=list)
    removed: list = field(default_factory=list)
    not_on_shift: list = field(default_factory=list)


def parse_inhopp(text, today):
    header = HEADER_RE.search(text)
    if header is None:
        raise InhoppParseError(
            "hittade ingen rad som ser ut som `Inhopp 05/11 EM Baljan`."
        )

    day, month = int(header.group(1)), int(header.group(2))
    candidates = []
    for year in (today.year - 1, today.year, today.year + 1):
        try:
            candidates.append(date(year, month, day))
        except ValueError:
            pass
    if not candidates:
        raise InhoppParseError(f"{day}/{month} är inget giltigt datum.")
    # No year in the message: the date closest to today is the one meant.
    when = min(candidates, key=lambda d: abs((d - today).days))

    warnings = []
    relative = (header.group(5) or "").lower()
    expected = {"idag": today, "imorgon": today + timedelta(days=1)}.get(relative)
    if expected is not None and expected != when:
        warnings.append(f"{when:%Y-%m-%d} är inte {relative}.")

    in_ids, out_ids = [], []
    for line in text.splitlines():
        key, _sep, rest = line.partition(":")
        target = {"in": in_ids, "out": out_ids}.get(key.strip(" *_").lower())
        if target is None:
            continue
        for liu_id in LIU_ID_RE.findall(rest.lower()):
            if liu_id not in target:
                target.append(liu_id)

    if not in_ids and not out_ids:
        raise InhoppParseError("hittade inga liu-id på raderna `In:` och `out:`.")
    both = [liu_id for liu_id in in_ids if liu_id in out_ids]
    if both:
        raise InhoppParseError(f"står både in och ut: {', '.join(both)}.")

    return InhoppRequest(
        when=when,
        span=SPANS[header.group(3).lower()],
        location=LOCATIONS[header.group(4).lower()],
        in_ids=in_ids,
        out_ids=out_ids,
        warnings=warnings,
    )


def find_shift(request):
    return Shift.objects.filter(
        when=request.when,
        span=request.span,
        location=request.location,
        enabled=True,
    ).first()


def add_to_substitute_group(user):
    if user.groups.filter(
        name__in=(settings.WORKER_GROUP, settings.BOARD_GROUP)
    ).exists():
        return
    group, _created = Group.objects.get_or_create(name=settings.SUBSTITUTE_GROUP)
    user.groups.add(group)


def send_invite(liu_id, shift_name):
    domain = Site.objects.get_current().domain
    body = (
        f"Hej!\n\n"
        f"Du har blivit inbokad som inhoppare på {shift_name} i Baljan.\n\n"
        f"Du har inget konto på {domain} än. Logga in med ditt LiU-ID på "
        f"https://{domain}/ så läggs passet in på ditt konto. Du måste logga "
        f"in för att få gratis kaffe som inhoppare.\n"
    )
    send_mail_task.delay(
        f"Du är inbokad på {shift_name}",
        body,
        f"Baljan <{settings.DEFAULT_FROM_EMAIL}>",
        [f"{liu_id}@{settings.USER_EMAIL_DOMAIN}"],
        reply_to=[settings.REPLY_TO_EMAIL],
    )


@transaction.atomic
def apply_inhopp(
    shift, in_ids, out_ids, requested_by=None, slack_channel="", slack_thread_ts=""
):
    PendingShiftSignup.objects.filter(shift__when__lt=date.today()).delete()
    result = InhoppResult()

    for liu_id in out_ids:
        pending_deleted, _ = PendingShiftSignup.objects.filter(
            shift=shift, liu_id=liu_id
        ).delete()
        signups = ShiftSignup.objects.filter(shift=shift, user__username__iexact=liu_id)
        if signups.exists() or pending_deleted:
            signups.delete()
            result.removed.append(liu_id)
        else:
            result.not_on_shift.append(liu_id)

    for liu_id in in_ids:
        user = User.objects.filter(username__iexact=liu_id).first()
        if user is None:
            _pending, created = PendingShiftSignup.objects.get_or_create(
                shift=shift,
                liu_id=liu_id,
                defaults={
                    "requested_by": requested_by,
                    "slack_channel": slack_channel,
                    "slack_thread_ts": slack_thread_ts,
                },
            )
            if created:
                transaction.on_commit(partial(send_invite, liu_id, str(shift.name())))
            result.pending.append(liu_id)
            continue

        _signup, created = ShiftSignup.objects.get_or_create(shift=shift, user=user)
        (result.added if created else result.already).append(liu_id)
        add_to_substitute_group(user)

    return result


def format_result(result):
    sections = [
        ("✅ Inlagda", result.added),
        ("☑️ Stod redan på passet", result.already),
        (
            "✉️ Saknar konto, mejl skickat. Läggs in vid första inloggningen",
            result.pending,
        ),
        ("❌ Borttagna", result.removed),
        ("⚠️ Stod inte på passet", result.not_on_shift),
    ]
    return "\n".join(f"{label}: {', '.join(ids)}" for label, ids in sections if ids)


def claim_pending_signups(backend, response, user=None, *args, **kwargs):
    """Pipeline step: turn pending inhopp for this liu-id into sign-ups."""
    if user is None:
        return
    try:
        # Read from LiU, since new users get an anonymous username.
        liu_id = backend.get_user_details(response).get("username")
        if liu_id:
            _claim(liu_id, user)
    except Exception:
        # A failed claim must never block the login.
        logger.exception("could not claim pending inhopp")


@transaction.atomic
def _claim(liu_id, user):
    pending = PendingShiftSignup.objects.filter(liu_id__iexact=liu_id).select_related(
        "shift"
    )
    for claim in pending:
        if claim.shift.past():
            continue
        ShiftSignup.objects.get_or_create(shift=claim.shift, user=user)
        add_to_substitute_group(user)
        if claim.slack_channel and claim.slack_thread_ts:
            text = (
                f"✅ {claim.liu_id} har skapat konto och är nu inlagd på "
                f"{claim.shift.name()}."
            )
            transaction.on_commit(
                partial(
                    post_slack_thread_message.delay,
                    claim.slack_channel,
                    claim.slack_thread_ts,
                    text,
                )
            )
    pending.delete()
