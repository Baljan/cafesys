# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Utility for updating email addresses in a Google group using a csv file."
    _worker_email = "jobbare@baljan.org"
    _CSV_HEAD = "Group Email [Required],Member Email,Member Type,Member Role"

    def add_arguments(self, parser):
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
        parser.add_argument(
            "-e",
            "--email",
            type=str,
            action="store",
            dest="google_group_email",
            default=self._worker_email,
            help="Google group email (default: %s)" % self._worker_email,
        )
        parser.add_argument(
            "-t",
            "--type",
            type=str,
            action="store",
            dest="member_type",
            default="USER",
            help="Google group member type (default: USER)",
        )
        parser.add_argument(
            "-r",
            "--role",
            type=str,
            action="store",
            dest="member_role",
            default="MEMBER",
            help="Google group member role (default: MEMBER)",
        )

    def handle(self, *args, **kwargs):
        try:
            group = Group.objects.get(name__exact=kwargs["group"])
        except Group.DoesNotExist:
            raise CommandError("bad group: %s" % kwargs["group"])

        all_emails = [settings.CONTACT_EMAIL]
        all_emails.extend(
            list(
                group.user_set.distinct()
                .order_by("email")
                .values_list("email", flat=True)
            )
        )

        print(self._CSV_HEAD)
        for member_email in all_emails:
            print(
                ",".join(
                    (
                        kwargs["google_group_email"],
                        member_email,
                        kwargs["member_type"],
                        kwargs["member_role"],
                    )
                )
            )
