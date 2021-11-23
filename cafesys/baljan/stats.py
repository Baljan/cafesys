# -*- coding: utf-8 -*-
from datetime import datetime, date, timedelta
from logging import getLogger

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Count
from django.utils.translation import ugettext_lazy as _

from cafesys.baljan.templatetags.baljan_extras import display_name
from .models import Semester
from .util import year_and_week, week_dates, adjacent_weeks

log = getLogger(__name__)

ALL_INTERVALS = (
    "today",
    "yesterday",
    "this_week",
    "last_week",
    "this_semester",
    "total",
)
ALL_LOCATIONS = [None, 0, 1]


def top_consumers(start=None, end=None, simple=False, location=None):
    """`start` and `end` are dates. Returns top consumers in the interval with
    order counts annotated (num_orders). If `simple` is true the returned list
    consists of serializable data types only."""
    if start is None:
        start = datetime(1970, 1, 1, 0, 0)
    if end is None:
        end = datetime(2999, 1, 1, 0, 0)

    fmt = "%Y-%m-%d"
    key = "baljan.stats.start-%s.end-%s.location-%s" % (
        start.strftime(fmt),
        end.strftime(fmt),
        location,
    )
    top = cache.get(key)
    if top is None:
        filter_args = {
            "profile__show_profile": True,
            "order__put_at__gte": start,
            "order__put_at__lte": end,
        }

        if location is not None:
            filter_args["order__location"] = location

        top = (
            User.objects.filter(**filter_args)
            .annotate(
                num_orders=Count("order"),
            )
            .order_by("-num_orders")
        )

        quarter = 60 * 15  # seconds
        cache.set(key, top, quarter)

    if simple:
        simple_top = []
        for u in top:
            simple_top.append(
                {
                    "full_name": display_name(u),
                    "username": u.username,
                    "blipped": u.num_orders,
                }
            )
        return simple_top
    return top


def compute_stats_for_location(location):
    s = Stats()
    return [s.get_interval(i, location) for i in ALL_INTERVALS]


def get_cache_key(location):
    return "%s-%s" % (settings.STATS_CACHE_KEY, location)


class Meta(object):
    def __init__(self):
        self.classes = {}
        self.classes_ordered = []
        self.classes_i18n = {}
        self.class_members = {}
        for name, name_i18n in [
            ("board member", _("board member")),
            ("old board member", _("old board member")),
            ("worker", _("worker")),
            ("old worker", _("old worker")),
            ("normal user", _("normal user")),
        ]:
            self.classes[name] = {}
            self.classes_i18n[name] = name_i18n
            self.class_members[name] = []
            self.classes_ordered.append(name)

        self.intervals = []
        self.interval_keys = {}

    def compute_users(self):
        board_users = User.objects.filter(
            groups__name=settings.BOARD_GROUP).distinct()
        for user in board_users:
            self.classes["board member"][user] = True

        oldie_users = User.objects.filter(
            groups__name=settings.OLDIE_GROUP).distinct()
        for user in oldie_users:
            self.classes["old board member"][user] = True

        worker_users = User.objects.filter(
            groups__name=settings.WORKER_GROUP
        ).distinct()
        for user in worker_users:
            self.classes["worker"][user] = True

        old_worker_users = (
            User.objects.annotate(
                num_shiftsignups=Count("shiftsignup"),
            )
            .exclude(
                num_shiftsignups=0,
            )
            .distinct()
        )
        for user in old_worker_users:
            self.classes["old worker"][user] = True

        self.all_users = set(User.objects.all().distinct())
        for user in self.all_users:
            self.classes["normal user"][user] = True

        for user in self.all_users:
            self.class_members[self.user_class(user)].append(user)

    def compute_intervals(self):
        today = date.today()
        yesterday = today - timedelta(days=1)

        std_staff_classes = [
            "board member",
            "old board member",
            "worker",
        ]

        self.intervals.append(
            {
                "key": "today",
                "name": _("Today"),
                "staff classes": std_staff_classes,
                "dates": [today, today],
            }
        )

        self.intervals.append(
            {
                "key": "yesterday",
                "name": _("Yesterday"),
                "staff classes": std_staff_classes,
                "dates": [yesterday, yesterday],
            }
        )

        current_week_dates = week_dates(*year_and_week())
        self.intervals.append(
            {
                "key": "this_week",
                "name": _("This Week"),
                "staff classes": std_staff_classes,
                "dates": current_week_dates,
            }
        )

        last_week_dates = week_dates(*adjacent_weeks()[0])
        self.intervals.append(
            {
                "key": "last_week",
                "name": _("Last Week"),
                "staff classes": std_staff_classes,
                "dates": last_week_dates,
            }
        )

        sem_now = Semester.objects.current()
        if sem_now:
            self.intervals.append(
                {
                    "key": "this_semester",
                    "name": sem_now.name,
                    "staff classes": std_staff_classes,
                    "dates": list(sem_now.date_range()),
                }
            )
        else:
            try:
                sem_last = Semester.objects.old()[0]
                if sem_last:
                    self.intervals.append(
                        {
                            "key": "this_semester",
                            "name": sem_last.name,
                            "staff classes": std_staff_classes +
                            ["old worker"],
                            "dates": list(
                                sem_last.date_range()),
                        })
            except Exception as e:
                log.warning("could not fetch last semester: %s" % e)

        try:
            sem_last = Semester.objects.old()[0]
            if sem_last:
                self.intervals.append(
                    {
                        "key": "last_semester",
                        "name": sem_last.name,
                        "staff classes": std_staff_classes + ["old worker"],
                        "dates": list(sem_last.date_range()),
                    }
                )
        except Exception as e:
            log.warning("could not fetch last semester: %s" % e)

        self.intervals.append(
            {
                "key": "total",
                "name": _("Total"),
                "staff classes": std_staff_classes + ["old worker"],
                "dates": None,
            }
        )

        for interval in self.intervals:
            self.interval_keys[interval["key"]] = interval

    def compute(self):
        self.compute_users()
        self.compute_intervals()

    def user_class(self, user):
        for name in self.classes_ordered:
            if user in self.classes[name]:
                return name


class Stats(object):
    def __init__(self):
        self.meta = Meta()
        self.meta.compute()

    def get_interval(self, interval_key, location):
        interval = self.meta.interval_keys[interval_key]
        staff_users = set()
        for cls_name in interval["staff classes"]:
            staff_users |= set(self.meta.class_members[cls_name])
        normal_users = self.meta.all_users - staff_users

        limit = 15
        groups = []
        for title, users in [
            (_("Normal Users"), normal_users),
            (_("Staff"), staff_users),
        ]:
            top = User.objects.filter(
                id__in=[u.id for u in users],
                profile__show_profile=True,
            )

            filter_args = {}
            if interval["dates"]:
                dates = list(interval["dates"])
                filter_args["order__put_at__gte"] = dates[0]
                filter_args["order__put_at__lte"] = dates[-1] + \
                    timedelta(days=1)

            if location is not None:
                filter_args["order__location"] = location

            if filter_args:
                top = top.filter(**filter_args)

            top = top.annotate(num_orders=Count("order"),).order_by(
                "-num_orders"
            )[:limit]
            top = list(top)

            groups.append(
                {
                    "title": title,
                    "top_users": top,
                }
            )

        return {
            "name": interval["name"],
            "groups": groups,
            "empty": sum([len(g["top_users"]) for g in groups]) == 0,
        }
