import time
from googleapiclient.http import HttpError
from googleapiclient.discovery import build
from google.oauth2 import service_account
from logging import getLogger
from django.conf import settings


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# FIXME: This needs to be moved or something else needs to be fixed
# This raises an error when running locally with docker since
# the docker env does not have access to the environment variables
# at "build" time, and google.oauth2 needs it. Works fine when
# running outside of docker and when building on heroku.
# I think theres a better way tho than just initializing them
# both to None and then assigning them a value inside of ensure_gmail_watch
credentials = service_account.Credentials.from_service_account_info(
    info=settings.GOOGLE_SERVICE_ACCOUNT_INFO,
    scopes=SCOPES,
    subject="robot.nordsson@baljan.org",
)
service = build("gmail", "v1", credentials=credentials)
logger = getLogger(__name__)

EXPIRATION_TIME = -1
HISTORY_ID = None


def ensure_gmail_watch():
    global EXPIRATION_TIME, HISTORY_ID
    current_time = time.time()

    if current_time - EXPIRATION_TIME > 0:
        print("Ensuring Gmail watch...")
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
                HISTORY_ID = int(response["historyId"])

            if "expiration" in response and response["expiration"].isdigit():
                EXPIRATION_TIME = int(response["expiration"])

            print(f"Gmail watch renewed until {EXPIRATION_TIME} with id {HISTORY_ID}")
        except HttpError as e:
            logger.error(
                "Could not renew Gmail notification watch. Status code : {0}, reason : {1}".format(
                    e.status_code, e.error_details
                )
            )
            HISTORY_ID = None
            EXPIRATION_TIME = -1


def get_new_messages(new_history_id):
    global HISTORY_ID

    messages = []

    if HISTORY_ID is None:
        logger.warning("Will not get messages due to HISTORY_ID being None.")
        return messages

    chosen_history_id = min(new_history_id, HISTORY_ID)

    print("Chosen", chosen_history_id)

    try:
        response = (
            service.users()
            .history()
            .list(userId="me", startHistoryId=chosen_history_id)
            .execute()
        )

        print("Response", response)

        if "history" not in response:
            return messages

        messagesAdded = [
            message  # ugly
            for history in response["history"]
            if "messagesAdded" in history
            for message in history["messagesAdded"]
        ]

        for message in messagesAdded:
            message_id = message["message"]["id"]
            details = get_email_details(message_id)

            if details is not None:
                messages.append(details)

        HISTORY_ID = new_history_id
    except HttpError as e:
        logger.error(
            "Could not get new message history. Status code: {0}, reason : {1}".format(
                e.status_code, e.error_details
            )
        )

    return messages


def get_email_details(message_id):
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
