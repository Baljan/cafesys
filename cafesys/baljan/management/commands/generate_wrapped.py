# -*- coding: utf-8 -*-
import json
import time

# from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db.models import (
    Avg,
    Count,
    DurationField,
    Exists,
    ExpressionWrapper,
    F,
    OuterRef,
    Window,
)
from django.db.models.functions import Lag, TruncDate, TruncWeek

from ...models import Located, Order, Semester, User


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

    def handle(self, *args, **options):
        start_time = time.time()
        semester_name = options["semester"]

        try:
            semester = Semester.objects.get(name=semester_name)
        except Semester.DoesNotExist:
            raise CommandError("could not find semester named %s" % semester_name)

        if "user" in options and options["user"] is not None:
            user_name = options["user"]

            try:
                users = [User.objects.get(username=user_name)]
            except User.DoesNotExist:
                raise CommandError("could not find user named %s" % user_name)
        else:
            users = User.objects.annotate(num_orders=Count("order")).filter(
                num_orders__gt=1,
                order__put_at__gte=semester.start,
                order__put_at__lte=semester.end,
            )

        worker_group = Group.objects.get(name=settings.WORKER_GROUP)

        all_orders_of_sem = Order.objects.filter(
            put_at__gte=semester.start, put_at__lte=semester.end
        )

        scoreboard = dict()
        scoreboard_data = (
            all_orders_of_sem.annotate(date=TruncDate("put_at"))
            .values("date", "user")
            .annotate(
                count=Count("date"),
                is_worker=Exists(worker_group.user_set.filter(id=OuterRef("user__id"))),
            )
            .values("date", "user", "count", "is_worker")
            .order_by("date", "-count")
        )

        out_data = []

        #                           /--> top
        # This goes date -> group --+--> by_user
        #                           \--> by_count
        for entry in scoreboard_data:
            d = entry["date"]
            w = entry["is_worker"]
            if d not in scoreboard:
                branches = dict(
                    regular=dict(by_user=dict(), by_count=dict(), top=[]),
                    worker=dict(by_user=dict(), by_count=dict(), top=[]),
                )

                scoreboard[d] = branches

            target = scoreboard[d]["worker"] if w else scoreboard[d]["regular"]

            if len(target["top"]) < 15:
                target["top"].append(entry["user"])

            target["by_user"][entry["user"]] = entry["count"]

            if entry["count"] not in target["by_count"]:
                target["by_count"][entry["count"]] = []

            target["by_count"][entry["count"]].append(entry["user"])

        for user in users:
            print("Processing %s..." % (user.username))
            is_worker = user.groups.filter(name=settings.WORKER_GROUP).exists()

            wrapped_data = dict(username=user.username, is_worker=is_worker)

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

            for date, data in scoreboard.items():
                target = data["worker"] if is_worker else data["regular"]

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
            items = list(scoreboard.items())
            streak = dict(start=None, end=None, duration=0)
            start, end, duration = None, None, 0

            i = 0
            while i < len(items):
                date, data = items[i]

                on_scoreboard = (
                    user.id in data["worker" if is_worker else "regular"]["top"]
                )

                if on_scoreboard:
                    start = date
                    j = i

                    while j < len(items):
                        on_scoreboard = (
                            user.id
                            in items[j][1]["worker" if is_worker else "regular"]["top"]
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
                None
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
                name=Located.LOCATION_CHOICES[fav_cafe_data["location"]][1],
                n_orders=fav_cafe_data["count"],
            )

            # Ökad konsumption under tenta-p?
            # Average blipp per vecka
            wrapped_data["week_avg"] = round(
                user_orders.annotate(week=TruncWeek("put_at"))
                .values("week")
                .annotate(count=Count("week"))
                .values("week", "count")
                .aggregate(avg=Avg("count"))["avg"],
                3,
            )

            out_data.append(wrapped_data)

        out_file = open("data.jsonl", "w")
        out_file.write(json.dumps(out_data, indent=4, default=str, ensure_ascii=False))
        out_file.close()
        print("Wrote file in %f secs" % (time.time() - start_time))
