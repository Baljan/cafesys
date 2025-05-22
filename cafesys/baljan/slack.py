from django.conf import settings
from django.core.exceptions import PermissionDenied
from cafesys.baljan.models import Located, PhoneLabel
from cafesys.baljan.phone import (
    is_valid_phone_number,
    get_user_by_number,
    remove_area_code,
)
from functools import wraps
from logging import getLogger
import hashlib
import hmac
import requests
import time

logger = getLogger(__name__)


def request_from_slack(request):
    if not settings.SLACK_SIGNING_SECRET:
        print("SLACK_SIGNING_SECRET not set. Returning...")
        return True

    request_body = request.body.decode("utf8")

    if (
        "X-Slack-Request-Timestamp" not in request.headers
        or "X-Slack-Signature" not in request.headers
    ):
        print("Missing Slack headers")
        return False

    timestamp = request.headers["X-Slack-Request-Timestamp"]
    signature = request.headers["X-Slack-Signature"]

    if not timestamp.isdigit():
        print("Timestamp is not valid")
        return False
    if abs(time.time() - int(timestamp)) > 60 * 5:
        # To prevent replay attacks
        print("Timestamp to old")
        return False

    sig_basestring = "v0:" + timestamp + ":" + request_body
    local_signature = (
        "v0="
        + hmac.new(
            settings.SLACK_SIGNING_SECRET.encode(),
            sig_basestring.encode(),
            hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(signature, local_signature)


def validate_slack(function=None):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if request_from_slack(request):
            return function(request, *args, **kwargs)
        raise PermissionDenied()

    return wrap


def handle_interactivity(data):
    new_message = {}

    for action in data["actions"]:
        action_id = action["action_id"]

        if action_id == "approve":
            user_id = data["user"]["id"]
            blocks = data["message"]["blocks"]

            blocks[len(blocks) - 1] = {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"<@{user_id}> tar den!"},
            }

            new_message["replace_original"] = True
            new_message["blocks"] = blocks
        if action_id == "remove":
            new_message["delete_original"] = True

    return new_message


def send_message(data, url, type="unknown message type"):
    slack_response = requests.post(
        url=url,
        json=data,
        headers={"Content-Type": "application/json"},
    )

    if slack_response.status_code != 200:
        logger.error(f"Unable to post {type} to Slack")


def generate_support_embed(message):
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "emoji": True,
                "text": "Nördar, vi har fått mejl:",
            },
        },
        {"type": "divider"},
    ]

    if "subject" in message:
        blocks.append(
            {
                "type": "rich_text",
                "elements": [
                    {
                        "type": "rich_text_section",
                        "elements": [
                            {
                                "type": "text",
                                "text": message["subject"],
                                "style": {"bold": True},
                            }
                        ],
                    }
                ],
            },
        )

    if "sender" in message:
        blocks.append(
            {
                "type": "rich_text",
                "elements": [
                    {
                        "type": "rich_text_section",
                        "elements": [
                            {
                                "type": "text",
                                "text": message["sender"],
                                "style": {"italic": True},
                            }
                        ],
                    }
                ],
            },
        )

    if "email_body" in message:
        blocks.append(
            {
                "type": "rich_text",
                "elements": [
                    {
                        "type": "rich_text_section",
                        "elements": [
                            {
                                "type": "text",
                                "text": message["email_body"],
                            }
                        ],
                    }
                ],
            },
        )

    if "date" in message:
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "<!date^%d^{date_long}|February 18th, 2014 at 6:39 AM PST>"
                        % (message["date"]),
                    }
                ],
            },
        )

    blocks.append(
        {"type": "divider"},
    )
    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Jag kan ta den!"},
                    "style": "primary",
                    "action_id": "approve",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Finns inget att ta :("},
                    "value": "remove",
                    "action_id": "remove",
                },
            ],
        }
    )

    return {"blocks": blocks}


def get_from_context(from_user):
    context = []

    if "groups" in from_user and from_user["groups"]:
        groups = from_user["groups"]
        context.append(
            {
                "type": "mrkdwn",
                "text": f"*{from_user['display_name']} tillhör {'grupperna' if len(groups) > 1 else 'gruppen'}:* {', '.join(groups)}",
            }
        )

    pl = PhoneLabel.objects.filter(
        phone_number=remove_area_code(from_user["phone"])
    ).first()
    if pl:
        context.append({"type": "mrkdwn", "text": f"*Numret är märkt som:* {pl.label}"})

    return context


def compile_slack_phone_message(phone_from, calls, location):
    """Compiles a message that can be posted to Slack after a call has been made"""

    call_from_user = _query_user(phone_from)

    recipients = [
        {"user": _query_user(call.get("to", "")), "status": call.get("state", "failed")}
        for call in calls
    ]

    location_str = (
        Located.LOCATION_CHOICES[location][1]
        if location < len(Located.LOCATION_CHOICES)
        else "Okänt café"
    )

    # outcome_str = 'blivit taget' if status == 'success' else 'missats'
    notification_text = f"Ett samtal till {location_str} från {call_from_user['formatted']} har inkommit."  # TODO: bring back: {outcome_str} av {call_to}.

    call_recipients_str = "\n".join(
        f"{'🟢' if r['status'] == 'success' else '🔴'} {r['user']['formatted']}"
        for r in recipients
    )
    context_elements = get_from_context(call_from_user)
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Nytt samtal till {location_str} från {call_from_user['formatted']}.",
            },
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Mottagare*\n{call_recipients_str}"},
        },
        {"type": "divider"},
    ]
    if len(context_elements):
        blocks.append({"type": "context", "elements": context_elements})

    return {"text": notification_text, "blocks": blocks}


def compile_slack_sms_message(_sms_from_number, message):
    """Compile a message that can be posted to Slack after a SMS has been
    received
    """
    sms_from_user = _query_user(_sms_from_number)
    pretext = f"Nytt SMS från {sms_from_user['formatted']}."
    notification_text = f'{pretext}\n"{message.strip()}"'

    context_elements = get_from_context(sms_from_user)
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": pretext}},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(f">{line}" for line in message.strip().split("\n")),
            },
        },
        {"type": "divider"},
    ]
    if len(context_elements):
        blocks.append({"type": "context", "elements": context_elements})

    return {"text": notification_text, "blocks": blocks}


def _query_user(phone):
    """
    Retrieves first name, last name and groups
    corresponding to a phone number from the database, if it exists.
    If multiple users have the same number, none will be queried
    """
    if not is_valid_phone_number(phone):
        return {"formatted": "dolt nummer", "phone": phone}

    formatted = f"<tel:{phone}|{phone}>"

    user = get_user_by_number(phone)
    if not user:
        return {"formatted": formatted, "phone": phone}

    display_name = (
        user.get_full_name() if user.get_full_name() != "" else user.get_username()
    )

    return {
        "formatted": f"{display_name} ({formatted})",
        "phone": phone,
        "display_name": display_name,
        "groups": [
            group.name if group.name[0] != "_" else group.name[1:]
            for group in user.groups.all()
        ],
    }
