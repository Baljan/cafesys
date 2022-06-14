from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.conf import settings
from cafesys.baljan.models import User, Located
from logging import getLogger
from cafesys.baljan.phone import is_valid_phone_number
import requests

logger = getLogger(__name__)


def send_message(data, type="unknown message type"):
    if settings.SLACK_PHONE_WEBHOOK_URL:
        slack_response = requests.post(
            settings.SLACK_PHONE_WEBHOOK_URL,
            json=data,
            headers={"Content-Type": "application/json"},
        )

        if slack_response.status_code != 200:
            logger.warning(f"Unable to post {type} to Slack")


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

    if False:  # TODO: find phone number's labels
        context.append(
            {"type": "mrkdwn", "text": f"*Numret är märkt som:* Leverantör AB"}
        )

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
    notification_text = f'Ett samtal till {location_str} från {call_from_user["formatted"]} har inkommit.'  # TODO: bring back: {outcome_str} av {call_to}.

    call_recipients_str = "\n".join(
        f"{'🟢' if r['status'] == 'success' else '🔴'} {r['user']['formatted']}"
        for r in recipients
    )

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
        {"type": "context", "elements": get_from_context(call_from_user)},
    ]

    return {"text": notification_text, "blocks": blocks}


def compile_slack_sms_message(_sms_from_number, message):
    """Compile a message that can be posted to Slack after a SMS has been
    received
    """
    sms_from_user = _query_user(_sms_from_number)
    pretext = f"Nytt SMS från {sms_from_user['formatted']}"
    notification_text = f'{pretext}\n"{message}"'

    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": pretext}},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(f">{line}" for line in message.strip().split("\n")),
            },
        },
        {"type": "context", "elements": get_from_context(sms_from_user)},
    ]

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
    try:
        user = User.objects.get(profile__mobile_phone=_remove_area_code(phone))
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
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        # Expected output for a lot of calls. Not an error.
        return {"formatted": formatted, "phone": phone}


def _remove_area_code(phone):
    """
    Removes the area code (+46) from the given phone number
    and replaces it with 0
    """

    if not phone.startswith("+46"):
        return phone
    else:
        return "0" + phone[3:]
