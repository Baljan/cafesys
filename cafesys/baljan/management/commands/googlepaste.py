# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.core.paginator import Paginator

from logging import getLogger

log = getLogger(__name__)


class Command(BaseCommand):
    help = "Utility for updating email addresses in a Google group."
    _page_size = 25

    def add_arguments(self, parser):
        parser.add_argument(
            "-n",
            "--page-size",
            type=int,
            action="store",
            metavar="PAGE_SIZE",
            dest="page_size",
            default=self._page_size,
            help="Page size (default: %s)" % self._page_size,
        )
        parser.add_argument(
            "-g",
            "--group",
            type=str,
            action="store",
            metavar="GROUP",
            dest="group",
            default=settings.WORKER_GROUP,
            help="Worker group (default: %s)" % settings.WORKER_GROUP,
        )

    def handle(self, *args, **options):
        page_size = int(options["page_size"])
        try:
            group = Group.objects.get(name__exact=options["group"])
        except Group.DoesNotExist:
            raise CommandError("bad group: %s" % options["group"])

        all_emails = [settings.CONTACT_EMAIL]
        all_emails.extend(
            list(
                group.user_set.distinct()
                .order_by("email")
                .values_list("email", flat=True)
            )
        )
        paginator = Paginator(all_emails, page_size)
        pages = [paginator.page(p).object_list for p in paginator.page_range]
        for i, emails in enumerate(pages):
            print("\n".join(emails))
            input(
                "\n\nHit return to show next page... (%s of %s)" % (i + 1, len(pages))
            )
            print(chr(27) + "[2J")
