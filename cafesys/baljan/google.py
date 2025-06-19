from celery import signals
from datetime import datetime
from googleapiclient.http import HttpError
from googleapiclient.discovery import build
from google.oauth2 import service_account
from logging import getLogger
import time

from django.conf import settings
from django.core.cache import cache

from .models import SupportFilter

logger = getLogger(__name__)


def setup_service():
    creds = service_account.Credentials.from_service_account_info(
        info=settings.GOOGLE_SERVICE_ACCOUNT_INFO,
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        subject="tyrone@baljan.org",
    )
    service = build("gmail", "v1", credentials=creds)

    return service


@signals.worker_ready.connect
def ensure_gmail_watch(**kwargs):
    service = setup_service()
    config = cache.get(
        settings.GOOGLE_CACHE_KEY, {"expiration_time": 0, "history_id": None}
    )

    current_time = time.time()

    if current_time - config["expiration_time"] > 0:
        logger.debug("Ensuring Gmail watch...")
        try:
            response = (
                service.users()
                .watch(
                    userId="me",
                    body={
                        "topicName": settings.GOOGLE_PUBSUB_TOPIC,
                        "labelFilterAction": "include",
                    },
                )
                .execute()
            )
            if "historyId" in response and response["historyId"].isdigit():
                config["history_id"] = int(response["historyId"])

            if "expiration" in response and response["expiration"].isdigit():
                config["expiration_time"] = int(response["expiration"])

            logger.info(
                "Gmail watch renewed until %s"
                % (datetime.fromtimestamp(config["expiration_time"] / 1e3))
            )

            cache.set(
                settings.GOOGLE_CACHE_KEY,
                config,
                config["expiration_time"] - current_time,
            )
        except HttpError as e:
            logger.error(
                "Could not renew Gmail notification watch. Status code : {0}, reason : {1}".format(
                    e.status_code, e.error_details
                )
            )


def get_new_messages(new_history_id):
    messages = []
    config = cache.get(settings.GOOGLE_CACHE_KEY)
    service = setup_service()

    if config is None or config["history_id"] is None:
        logger.warning("Will not get messages due to HISTORY_ID being None.")
        return messages

    chosen_history_id = min(new_history_id, config["history_id"])

    try:
        response = (
            service.users()
            .history()
            .list(userId="me", startHistoryId=chosen_history_id)
            .execute()
        )

        if "history" not in response:
            return messages

        messagesAdded = [
            message  # ugly
            for history in response["history"]
            if "messagesAdded" in history
            for message in history["messagesAdded"]
        ]

        filters = SupportFilter.objects.all()

        for message in messagesAdded:
            message_id = message["message"]["id"]
            details = get_email_details(service, message_id)

            # This can be done by using aggregate and a PostgreSQLs POSITION function
            # to get check if a subject / sender can contain filter values.
            # But we get like one email a day rn so not worth it
            should_keep = all(
                [
                    (
                        filter.type == SupportFilter.Type.FROM
                        and filter.value not in details["sender"]
                    )
                    or (
                        filter.type == SupportFilter.Type.SUBJECT
                        and filter.value not in details["subject"]
                    )
                    for filter in filters
                ]
            )

            if should_keep and details is not None:
                messages.append(details)

        config["history_id"] = new_history_id
        cache.set(
            settings.GOOGLE_CACHE_KEY, config, config["expiration_time"] - time.time()
        )
    except HttpError as e:
        logger.error(
            "Could not get new message history. Status code: {0}, reason : {1}".format(
                e.status_code, e.error_details
            )
        )

    return messages


def get_email_details(service, message_id):
    message = None

    try:
        message = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
    except HttpError as e:
        logger.error(
            "Could not get specific message {0}, reason : {1}".format(
                message_id, e.error_details
            )
        )
        return None

    data = dict()

    data["id"] = message_id

    headers = message["payload"]["headers"]
    data["subject"] = next(
        (h["value"] for h in headers if h["name"] == "Subject"), "No Subject"
    )
    data["sender"] = next(
        (h["value"] for h in headers if h["name"] == "From"), "Unknown Sender"
    )

    if "internalDate" in message and message["internalDate"].isdigit():
        data["date"] = int(message["internalDate"]) / 1000

    if "snippet" in message and len(message["snippet"]) > 0:
        data["email_body"] = message["snippet"]

    return data
