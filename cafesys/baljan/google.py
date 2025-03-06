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
                    'topicName': "projects/nerdz-support-ticket/subscriptions/support-webhook-sub",
                }
            ).execute()
        
        print("Gmail watch renewed:", response)
        LAST_WATCH_TIME = current_time

ensure_gmail_watch()
