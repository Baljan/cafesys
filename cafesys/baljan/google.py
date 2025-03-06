import time
from googleapiclient.discovery import build
from google.oauth2 import service_account

from django.conf import settings

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

credentials = service_account.Credentials.from_service_account_info(
    info=settings.GOOGLE_SERVICE_ACCOUNT_INFO, 
    scopes=SCOPES, 
    subject="robot.nordsson@baljan.org"
)
service = build('gmail', 'v1', credentials=credentials)

LAST_WATCH_TIME = 0

def ensure_gmail_watch():
    global LAST_WATCH_TIME
    current_time = time.time()
    
    if current_time - LAST_WATCH_TIME > 50 * 60:
        response = service.users().watch(
                userId="me", 
                body={
                    'labelIds': ['INBOX'],
                    'topicName': "projects/nerdz-support-ticket/topics/support-webhook",
                }
            ).execute()
        
        print("Gmail watch renewed:", response)
        LAST_WATCH_TIME = current_time


def get_new_messages(service, history_id):
    response = service.users().history().list(userId="me", startHistoryId=history_id).execute()

    messages = []
    
    if "history" in response:
        for history in response["history"]:
            if "messagesAdded" in history:
                for message in history["messagesAdded"]:
                    message_id = message["message"]["id"]
                    print(f"New email received! Message ID: {message_id}")
                    messages.append(get_email_details(service, message_id))
    
    return messages

def get_email_details(service, message_id):
    message = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    
    headers = message["payload"]["headers"]

    data = { message_id }

    data["subject"] = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
    data["sender"] = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")

    # bodies = []

    # for part in message["payload"].get("parts", []):
    #     if part["mimeType"] == "text/plain":
    #         bodies.append(part["body"]["data"])

    # data["email_body"] = "\n\n".join(bodies)
    data["email_body"] = message["snippet"]

    return data

def generate_slack_message(message):
    title = "Nördar, vi har fått mejl!"

    blocks = [
		{
			"type": "header",
			"text": {
				"type": "plain_text",
				"text": title,
			}
		},
		{
			"type": "section",
			"fields": [
				{
					"type": "mrkdwn",
					"text": f"*Titel:* {message.get("subject")}"
				}
			]
		}, 
		{
			"type": "section",
			"fields": [
				{
					"type": "mrkdwn",
					"text": f"*Från:* {message.get("sender")}"
				}
			]
		},
		{
			"type": "section",
			"fields": [
				{
					"type": "mrkdwn",
					"text": message.get("email_body") 
				}
			]
		},
    ]

    return {"text": title, "blocks": blocks}


ensure_gmail_watch()
