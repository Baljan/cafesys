import time
from unittest import mock

from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings

from cafesys.baljan import google
from cafesys.baljan.models import SupportFilter

DAY_MS = 24 * 60 * 60 * 1000
LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


@override_settings(CACHES=LOCMEM)
class EnsureGmailWatchTestCase(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.now_ms = int(time.time() * 1000)
        self.service = mock.Mock()
        self.service.users().watch().execute.return_value = {
            "historyId": "500",
            "expiration": str(self.now_ms + 7 * DAY_MS),
        }
        self.service.users().watch.reset_mock()
        patcher = mock.patch.object(google, "setup_service", return_value=self.service)
        patcher.start()
        self.addCleanup(patcher.stop)

    def store(self, expiration_ms):
        cache.set(
            settings.GOOGLE_CACHE_KEY,
            {"expiration_time": expiration_ms, "history_id": 1},
            None,
        )

    def watched(self):
        return self.service.users().watch.called

    def test_starts_watch_without_config(self):
        google.ensure_gmail_watch()

        self.assertTrue(self.watched())
        config = cache.get(settings.GOOGLE_CACHE_KEY)
        self.assertEqual(config["history_id"], 500)
        self.assertEqual(config["expiration_time"], self.now_ms + 7 * DAY_MS)

    def test_renews_long_expired_watch(self):
        # Production had a watch that expired months ago stuck in the cache.
        self.store(self.now_ms - 200 * DAY_MS)

        google.ensure_gmail_watch()

        self.assertTrue(self.watched())
        self.assertEqual(cache.get(settings.GOOGLE_CACHE_KEY)["history_id"], 500)

    def test_renews_watch_expiring_within_a_day(self):
        self.store(self.now_ms + 2 * 60 * 60 * 1000)

        google.ensure_gmail_watch()

        self.assertTrue(self.watched())

    def test_keeps_watch_with_days_left(self):
        self.store(self.now_ms + 5 * DAY_MS)

        google.ensure_gmail_watch()

        self.assertFalse(self.watched())

    def test_cache_entry_expires_with_the_watch(self):
        with mock.patch.object(google.cache, "set") as cache_set:
            google.ensure_gmail_watch()

        timeout = cache_set.call_args.args[2]
        self.assertAlmostEqual(timeout, 7 * 24 * 60 * 60, delta=60)


@override_settings(CACHES=LOCMEM, SUPPORT_LIST_ID="1337.baljan.org")
class GetNewMessagesTestCase(TestCase):
    MAILS = {
        "group": {"Subject": "Kortet funkar inte", "List-ID": "<1337.baljan.org>"},
        "personal": {"Subject": "Middag ikväll?"},
        "other-group": {"Subject": "Styrelsemöte", "List-ID": "<styrelsen.baljan.org>"},
    }

    def setUp(self):
        cache.clear()
        cache.set(
            settings.GOOGLE_CACHE_KEY,
            {"expiration_time": int(time.time() * 1000) + DAY_MS, "history_id": 1},
            None,
        )
        service = mock.Mock()
        service.users().history().list().execute.return_value = {
            "history": [
                {
                    "messagesAdded": [
                        {"message": {"id": mail_id}} for mail_id in self.MAILS
                    ]
                }
            ]
        }
        service.users().messages().get.side_effect = lambda **kw: mock.Mock(
            execute=mock.Mock(return_value=self.message(kw["id"]))
        )
        patcher = mock.patch.object(google, "setup_service", return_value=service)
        patcher.start()
        self.addCleanup(patcher.stop)

    def message(self, mail_id):
        headers = {"From": "someone@example.com", **self.MAILS[mail_id]}
        return {
            "payload": {
                "headers": [{"name": k, "value": v} for k, v in headers.items()]
            },
            "internalDate": "1700000000000",
            "snippet": "Hej",
        }

    def test_only_mail_to_the_support_group(self):
        messages = google.get_new_messages(2)

        self.assertEqual([m["id"] for m in messages], ["group"])

    def test_support_filters_still_apply(self):
        SupportFilter.objects.create(type=SupportFilter.Type.SUBJECT, value="Kortet")

        self.assertEqual(google.get_new_messages(2), [])
