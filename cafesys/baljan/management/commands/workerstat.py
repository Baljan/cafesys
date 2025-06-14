# -*- coding: utf-8 -*-
from datetime import date

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from cafesys.baljan.templatetags.baljan_extras import detailed_name
from ...models import Semester


class Command(BaseCommand):
    help = "Show worker statistics for semestser."
    missing_args_message = "no semester name given."

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument("semester", type=str)
        # Named (optional) arguments
        parser.add_argument(
            "-n",
            "--names-limit",
            type=str,
            action="store",
            metavar="LIMIT",
            dest="names_limit",
            default="999",
            help='Do not show more than these many names for a "level."',
        )
        (
            parser.add_argument(
                "-u",
                "--upper-limit",
                type=str,
                action="store",
                metavar="UPPER",
                dest="upper_limit",
                default="999",
                help="Do not show workers with more shift signups.",
            ),
        )
        parser.add_argument(
            "-f",
            "--future-count",
            type=str,
            action="store",
            metavar="FUTURE",
            dest="future_count",
            default="",
            help="Show only users that have these many shifts in the future.",
        )
        parser.add_argument(
            "-t",
            "--type",
            type=str,
            action="store",
            metavar="TYPE",
            dest="type",
            default="text",
            help="Output type. Can be text or csv.",
        )

    def handle(self, *args, **options):
        semester_name = options["semester"]
        try:
            semester = Semester.objects.get(name=semester_name)
        except Semester.DoesNotExist:
            raise CommandError("could not find semester named %s" % semester_name)

        names_limit = int(options["names_limit"])
        upper_limit = int(options["upper_limit"])
        if options["future_count"] == "":
            future_count = None
        else:
            future_count = int(options["future_count"])
        today = date.today()

        # FIXME: This can be done much faster.
        workers = list(
            User.objects.filter(shiftsignup__shift__semester=semester).distinct()
        )
        workers.sort(key=lambda x: x.shiftsignup_set.all().count(), reverse=True)
        signup_counts = sorted(
            set([w.shiftsignup_set.all().count() for w in workers]), reverse=True
        )

        if options["type"] == "text":
            print("%d worker(s):" % len(workers))
        tot_count = 0
        indent = " " * 4
        for signup_count in signup_counts:
            workers_with_count_signups = [
                w for w in workers if w.shiftsignup_set.all().count() == signup_count
            ]
            c = len(workers_with_count_signups)
            tot_count += c
            if signup_count > upper_limit:
                continue
            if options["type"] == "text":
                print(
                    "%3d shift(s): %3d (%.2G%%)"
                    % (signup_count, c, 100.0 * c / len(workers))
                )
            if signup_count < names_limit:
                for w in workers_with_count_signups:
                    if future_count is not None:
                        if (
                            w.shiftsignup_set.filter(shift__when__gte=today).count()
                            != future_count
                        ):
                            continue
                    if options["type"] == "text":
                        readable = "%s%s" % (indent, detailed_name(w))
                    elif options["type"] == "csv":
                        readable = "%s,%s,%s,%s" % (
                            signup_count,
                            w.first_name,
                            w.last_name,
                            w.username,
                        )
                    else:
                        assert False, "bad type: %s" % options["type"]
                    print(readable)
            else:
                if options["type"] == "text":
                    print("%stoo many to print" % indent)

        assert tot_count == len(workers)
