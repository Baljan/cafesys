import time
from unittest import mock

from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from cafesys.baljan import google

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
