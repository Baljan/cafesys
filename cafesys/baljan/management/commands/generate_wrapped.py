# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta
import json
import time as timer

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
from django.db.models.functions import ExtractHour, ExtractIsoWeekDay, Lag, TruncDate
from django.utils import timezone

from cafesys.baljan import stats
from cafesys.baljan.models import (
    OnCallDuty,
    Order,
    Purchase,
    Semester,
    ShiftSignup,
    User,
    Wrapped,
)


def semester_bounds(semester):
    """Half-open datetime bounds [start, end + 1 day) covering the semester,
    in local time."""
    tz = timezone.get_current_timezone()
    return (
        datetime.combine(semester.start, time.min, tzinfo=tz),
        datetime.combine(semester.end + timedelta(1), time.min, tzinfo=tz),
    )


def online_cards(user, semester):
    """Coffee cards bought online (Stripe) during the semester. Only counts,
    never amounts."""
    start, end = semester_bounds(semester)
    purchases = Purchase.objects.filter(user=user, made__gte=start, made__lt=end)
    by_product = {
        row["product__name"]: row["count"]
        for row in purchases.values("product__name").annotate(count=Count("id"))
    }
    return dict(count=sum(by_product.values()), by_product=by_product)


def previous_semester(user, semester):
    """Blipps during the same kind of semester the year before, e.g. HT2025 for
    HT2026. None if that semester doesn't exist."""
    prev_name = "%s%d" % (semester.name[:2], int(semester.name[2:]) - 1)
    try:
        prev = Semester.objects.get(name=prev_name)
    except Semester.DoesNotExist:
        return None

    start, end = semester_bounds(prev)
    n_orders = Order.objects.filter(
        user=user, put_at__gte=start, put_at__lt=end
    ).count()
    return dict(semester=prev.name, n_orders=n_orders)


def time_of_day(user_orders):
    """Blipps per hour of the day (local time) and per weekday (0 = Monday)."""
    hours = [0] * 24
    for row in (
        user_orders.annotate(hour=ExtractHour("put_at"))
        .values("hour")
        .annotate(count=Count("id"))
    ):
        hours[row["hour"]] = row["count"]

    weekdays = [0] * 7
    for row in (
        user_orders.annotate(weekday=ExtractIsoWeekDay("put_at"))
        .values("weekday")
        .annotate(count=Count("id"))
    ):
        weekdays[row["weekday"] - 1] = row["count"]

    return dict(
        hours=hours,
        weekdays=weekdays,
        fav_hour=hours.index(max(hours)),
        fav_weekday=weekdays.index(max(weekdays)),
    )


def shifts(user, semester, until):
    """Worked shifts (up to and including `until`) during the semester."""
    signups = ShiftSignup.objects.filter(
        user=user,
        shift__semester=semester,
        shift__enabled=True,
        shift__when__lte=until,
    )
    by_span = dict(morning=0, lunch=0, afternoon=0)
    span_keys = {0: "morning", 1: "lunch", 2: "afternoon"}
    for row in signups.values("shift__span").annotate(count=Count("id")):
        by_span[span_keys[row["shift__span"]]] = row["count"]

    on_call = OnCallDuty.objects.filter(
        user=user, shift__semester=semester, shift__when__lte=until
    ).count()

    return dict(
        count=sum(by_span.values()),
        by_span=by_span,
        exam_period=signups.filter(shift__exam_period=True).count(),
        on_call=on_call,
    )


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
        start_time = timer.time()
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

        sem_start, sem_end = semester_bounds(semester)
        all_orders_of_sem = Order.objects.filter(
            put_at__gte=sem_start, put_at__lt=sem_end
        )
        today = timezone.localdate()

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

        top = stats.compute_stats(
            interval="this_semester", limit=None, is_wrapped=True
        )["groups"]

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
            wrapped_data["week_avg"] = round(5 * len(user_orders) / semester_length, 1)

            wrapped_data["online_cards"] = online_cards(user, semester)
            wrapped_data["previous"] = previous_semester(user, semester)
            wrapped_data["time_of_day"] = time_of_day(user_orders)
            wrapped_data["shifts"] = (
                shifts(user, semester, until=today) if is_staff else None
            )

            kwargs = dict(user=user, data=wrapped_data, semester=semester)

            if not dry_run:
                existing = Wrapped.objects.filter(semester=semester, user=user)
                if existing.exists():
                    existing.update(data=wrapped_data)
                else:
                    Wrapped.objects.create(**kwargs)
            else:
                print(json.dumps(kwargs, indent=4, default=str))

        print("Finished processing in %f secs" % (timer.time() - start_time))
