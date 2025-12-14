# -*- coding: utf-8 -*-
from datetime import timedelta
import json
import time

# from django.contrib.auth.models import User
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import (
    Count,
    DurationField,
    Exists,
    ExpressionWrapper,
    F,
    OuterRef,
    Window,
)
from django.db.models.functions import Lag, TruncDate

from cafesys.baljan import stats
from cafesys.baljan.models import Order, Semester, User, Wrapped


class Command(BaseCommand):
    help = "Generate Wrapped data for the semester given"
    missing_args_message = "no semester name given."

    def add_arguments(self, parser):
        parser.add_argument("semester", type=str)

        parser.add_argument(
            "-u",
            "--user",
            type=str,
            action="store",
            dest="user",
        )
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        start_time = time.time()
        semester_name = options["semester"]
        dry_run = (
            "dry_run" in options
            and options["dry_run"] is not None
            and options["dry_run"]
        )

        if dry_run:
            print("This is a dry run. Will not be inserting any day!")

        try:
            semester = Semester.objects.get(name=semester_name)
            a = (semester.end - semester.start).days
            semester_length = a - ((a // 7) * 2)
        except Semester.DoesNotExist:
            raise CommandError("could not find semester named %s" % semester_name)

        if "user" in options and options["user"] is not None:
            user_name = options["user"]

            try:
                users = [User.objects.get(username=user_name)]
            except User.DoesNotExist:
                raise CommandError("could not find user named %s" % user_name)
        else:
            users = (
                User.objects.filter(
                    order__put_at__gte=semester.start,
                    order__put_at__lte=semester.end + timedelta(1),
                    profile__show_profile=True,
                    # FIXME: All users should be able to view their wrapped,
                    # even those who dont want to be included in the scoreboard
                )
                .annotate(num_orders=Count("order"))
                .exclude(num_orders=0)
            )

        staff_groups = User.objects.filter(
            groups__name__in=[
                settings.WORKER_GROUP,
                settings.BOARD_GROUP,
                settings.OLDIE_GROUP,
            ]
        ).distinct()

        all_orders_of_sem = Order.objects.filter(
            put_at__gte=semester.start, put_at__lte=semester.end
        )

        stats_by_date = dict()
        scoreboard_data = (
            all_orders_of_sem.annotate(date=TruncDate("put_at"))
            .values("date", "user")
            .annotate(
                count=Count("date"),
                is_staff=Exists(staff_groups.filter(id=OuterRef("user__id"))),
            )
            .values("date", "user", "count", "is_staff")
            .order_by("date", "-count")
        )

        top = stats.compute_stats(interval="this_semester", limit=None)["groups"]

        a = len(top[0]["top_users"]) + len(top[1]["top_users"])
        b = len(users)

        assert a == b

        #                           /--> top
        # This goes date -> group --+--> by_user
        #                           \--> by_count
        # This is only to make it easier to search for values.
        # idk how else i would do it :|
        for entry in scoreboard_data:
            d = entry["date"]
            w = entry["is_staff"]
            if d not in stats_by_date:
                branches = dict(
                    regular=dict(by_user=dict(), by_count=dict(), top=[]),
                    worker=dict(by_user=dict(), by_count=dict(), top=[]),
                )

                stats_by_date[d] = branches

            target = stats_by_date[d]["worker"] if w else stats_by_date[d]["regular"]

            if len(target["top"]) < 15:
                target["top"].append(entry["user"])

            target["by_user"][entry["user"]] = entry["count"]

            if entry["count"] not in target["by_count"]:
                target["by_count"][entry["count"]] = []

            target["by_count"][entry["count"]].append(entry["user"])

        for user in users:
            print("Processing %s..." % (user.username))
            is_staff = staff_groups.filter(id=user.id).exists()

            wrapped_data = dict(
                is_staff=is_staff,
                overall_placement=(top[1 if is_staff else 0]["top_users"].index(user)),
            )

            # Hur mycket druckit
            user_orders = all_orders_of_sem.filter(user=user)

            wrapped_data["n_orders"] = user_orders.count()
            wrapped_data["caffeine_mg"] = round(2.2 * 110 * user_orders.count())

            # Vilken dag drakc mest, hur mycket
            most_purchases_by_date = (
                user_orders.annotate(date=TruncDate("put_at"))
                .values("date")
                .annotate(count=Count("date"))
                .values("date", "count")
                .order_by("-count")
            )

            most_purchases = dict(count=most_purchases_by_date[0]["count"], dates=[])

            for day in most_purchases_by_date:
                if day["count"] is not most_purchases["count"]:
                    break

                most_purchases["dates"].append(day["date"])

            wrapped_data["most_purchases"] = most_purchases

            # Bästa placering i topplistan
            p = dict(date=None, count=None, place=None, shared=None, other_dates=[])

            for date, data in stats_by_date.items():
                target = data["worker"] if is_staff else data["regular"]

                if user.id not in target["by_user"]:
                    continue

                count = target["by_user"][user.id]

                other_dates = []

                bigger_counts = list(
                    filter(lambda x: x > count, target["by_count"].keys())
                )

                place = len(bigger_counts)
                if p["place"] is not None:
                    if p["place"] < place:
                        continue
                    elif p["place"] == place:
                        if p["count"] < count:
                            p["other_dates"].append(p["date"])
                            p["date"] = date
                            p["count"] = count
                        else:
                            p["other_dates"].append(date)
                        continue

                shared = len(target["by_count"][count])

                p = dict(
                    date=date,
                    count=count,
                    place=place,
                    shared=shared - 1,
                    other_dates=other_dates,
                )

            wrapped_data["best_placement"] = p

            # Längsta streak på topplistan
            items = list(stats_by_date.items())
            streak = dict(start=None, end=None, duration=0)
            start, end, duration = None, None, 0

            i = 0
            while i < len(items):
                date, data = items[i]

                on_scoreboard = (
                    user.id in data["worker" if is_staff else "regular"]["top"]
                )

                if on_scoreboard:
                    start = date
                    j = i

                    while j < len(items):
                        # This still counts one day as a streak. This case will be
                        # handled on the frontend.
                        on_scoreboard = (
                            user.id
                            in items[j][1]["worker" if is_staff else "regular"]["top"]
                        )

                        if not on_scoreboard:
                            break

                        end = items[j][0]
                        j += 1

                    duration = j - i

                    if duration > streak["duration"]:
                        streak = dict(start=start, end=end, duration=duration)

                    i = j

                i += 1

            wrapped_data["longest_streak"] = streak

            # Kortaste tid mellan två koppar
            wrapped_data["shortest_delta"] = (
                None  # Only one blipp
                if len(user_orders) == 1
                else (
                    user_orders.annotate(
                        prev_put_at=Window(
                            expression=Lag("put_at"), order_by=F("put_at").asc()
                        )
                    )
                    .values("put_at", "prev_put_at")
                    .exclude(prev_put_at__isnull=True)
                    .annotate(
                        delta=ExpressionWrapper(
                            F("put_at") - F("prev_put_at"), output_field=DurationField()
                        )
                    )
                    .order_by("delta")
                    .first()["delta"]
                )
            )

            # Favortikafé, Byttan eller Baljan
            fav_cafe_data = (
                user_orders.values("location")
                .annotate(count=Count("location"))
                .values("location", "count")
                .order_by("-count")
                .first()
            )
            wrapped_data["fav_cafe"] = dict(
                id=fav_cafe_data["location"],
                n_orders=fav_cafe_data["count"],
            )

            # Ökad konsumption under tenta-p?
            # Average blipp per vecka
            wrapped_data["week_avg"] = round(len(user_orders) / semester_length, 3)

            kwargs = dict(user=user, data=wrapped_data, semester=semester)

            if not dry_run:
                existing = Wrapped.objects.filter(semester=semester, user=user)
                if existing.exists():
                    existing.update(data=wrapped_data)
                else:
                    Wrapped.objects.create(**kwargs)
            else:
                print(json.dumps(kwargs, indent=4, default=str))

        print("Finished processing in %f secs" % (time.time() - start_time))
