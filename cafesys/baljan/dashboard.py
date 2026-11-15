"""Data for the wall screen at /skarm.

Everything is cached so the number of screens never affects the database:
today's numbers at most once per LIVE_TTL, semester numbers once per
SEMESTER_TTL, and the top list is read from the cache `tasks.update_stats`
already fills.
"""

from datetime import datetime, time, timedelta

from django.core.cache import cache
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.db.models.functions import ExtractHour, ExtractMinute, TruncDate
from django.utils import timezone
from django.utils.formats import date_format

from . import stats
from .models import CoffeeChallenge, Located, Order, Profile, Semester, Shift

LIVE_TTL = 15
SEMESTER_TTL = 30 * 60
TOP_TTL = 5 * 60

CAFES = (
    (Located.KARALLEN, "baljan", "Baljan"),
    (Located.STH_VALLA, "byttan", "Byttan"),
)
KEYS = {loc: key for loc, key, _ in CAFES}
LUNCH = 12
# How long the latest break stays on screen after it ended.
RUSH_LINGER = timedelta(minutes=45)
# Averages and records need this many normal days to mean anything.
MIN_DAYS = 5
# Fewer blipps than this is an event or a half day, not a normal open day.
FULL_DAY = 50


def _aware(day, t=time.min):
    return timezone.make_aware(datetime.combine(day, t))


def _zero():
    return {key: 0 for _, key, _ in CAFES}


def _in_slot(start, end):
    if end.hour > start.hour:
        return Q(hour__gte=start.hour, hour__lt=end.hour)
    return Q(hour=start.hour, minute__gte=start.minute, minute__lt=end.minute)


def _counts(start_day, end_day, *fields):
    """Accepted blipps from start_day up to and including end_day, counted
    per `fields`. `slot` is the start hour of the break in
    CoffeeChallenge.SLOTS, or -1 outside the breaks."""
    return (
        Order.objects.filter(
            accepted=True,
            put_at__gte=_aware(start_day),
            put_at__lt=_aware(end_day + timedelta(days=1)),
        )
        .annotate(
            day=TruncDate("put_at"),
            hour=ExtractHour("put_at"),
            minute=ExtractMinute("put_at"),
        )
        .annotate(
            slot=Case(
                *(
                    When(_in_slot(start, end), then=Value(start.hour))
                    for start, end in CoffeeChallenge.SLOTS
                ),
                default=Value(-1),
                output_field=IntegerField(),
            )
        )
        .values(*fields)
        .annotate(n=Count("id"))
    )


def _live(now):
    today = now.date()
    totals = _zero()
    hours = {h: _zero() for h in range(8, 17)}
    slots = {start.hour: _zero() for start, _ in CoffeeChallenge.SLOTS}
    for row in _counts(today, today, "location", "hour", "slot"):
        key = KEYS.get(row["location"])
        if key is None:
            continue
        totals[key] += row["n"]
        if row["hour"] in hours:
            hours[row["hour"]][key] += row["n"]
        if row["slot"] in slots:
            slots[row["slot"]][key] += row["n"]

    open_today = set(
        Shift.objects.filter(when=today, enabled=True).values_list(
            "location", flat=True
        )
    )

    rush = None
    for start, end in CoffeeChallenge.SLOTS:
        if _aware(today, start) > now:
            break
        rush = {
            "start": start.strftime("%H:%M"),
            "end": end.strftime("%H:%M"),
            "lunch": start.hour == LUNCH,
            "live": now < _aware(today, end),
            "counts": slots[start.hour],
        }
        rush_end = _aware(today, end)
    if rush and now >= rush_end + RUSH_LINGER:
        rush = None

    return {
        "day": date_format(today, "l j F"),
        "now_hour": now.hour,
        "open": {key: loc in open_today for loc, key, _ in CAFES},
        "totals": totals,
        "hours": [{"hour": h, **counts} for h, counts in hours.items()],
        "rush": rush,
    }


def _semester_for(today):
    return (
        Semester.objects.for_date(today)
        or Semester.objects.filter(end__lt=today).order_by("-start").first()
    )


def _semester(today):
    sem = _semester_for(today)
    if sem is None:
        return None

    rows = list(_counts(sem.start, min(sem.end, today), "day", "location", "slot"))

    totals = _zero()
    day_totals = {}
    for row in rows:
        key = KEYS.get(row["location"])
        if key is None:
            continue
        totals[key] += row["n"]
        day_totals[row["day"]] = day_totals.get(row["day"], 0) + row["n"]

    total = sum(totals.values())
    if total == 0:
        return None

    # Today is still running, so it can set a record but not skew the averages.
    full_days = {d for d, n in day_totals.items() if n >= FULL_DAY and d < today}
    record = None
    rhythm = None
    if len(full_days) >= MIN_DAYS:
        slot_sums = {}
        best = None
        for row in rows:
            if row["location"] not in KEYS or row["slot"] in (-1, LUNCH):
                continue
            if row["day"] in full_days:
                slot_sums[row["slot"]] = slot_sums.get(row["slot"], 0) + row["n"]
            # Ties go to the earliest day so the slide doesn't flip.
            rank = (row["n"], -row["day"].toordinal())
            if best is None or rank > best:
                best = rank
                record = {
                    "n": row["n"],
                    "cafe": KEYS[row["location"]],
                    "day": date_format(row["day"], "l j F"),
                    "start": f"{row['slot']:02d}:00",
                }
        rhythm = [
            {
                "hour": start.hour,
                "avg": round(slot_sums.get(start.hour, 0) / len(full_days)),
            }
            for start, _ in CoffeeChallenge.SLOTS
            if start.hour != LUNCH
        ]

    return {
        "name": sem.name,
        "ended": sem.end < today,
        "total": total,
        "totals": totals,
        "record": record,
        "rhythm": rhythm,
    }


def _short_name(user):
    first = user.first_name.strip().split(" ")[0]
    last = user.last_name.strip()
    if not first:
        return None
    return f"{first} {last[0]}." if last else first


def _top():
    """Top three regular customers of the semester, from the high score cache.

    Staff drink for free and are left out, as are people without a real name
    or who have hidden themselves from the high score list.
    """
    cached = cache.get(stats.get_cache_key(None))
    if not cached:
        return None
    _, intervals = cached
    semester = next((i for i in intervals if i["key"] == "this_semester"), None)
    if semester is None:
        return None

    candidates = semester["groups"][0]["top_users"]
    # The high score cache can be hours old, so re-check who still wants to be shown.
    visible = set(
        Profile.objects.filter(
            user_id__in=[u.id for u in candidates], show_profile=True
        ).values_list("user_id", flat=True)
    )

    people = []
    for user in candidates:
        name = _short_name(user)
        if not name or user.id not in visible:
            continue
        # Rank among the people shown, so skipped users leave no gaps.
        rank = 1
        if people:
            last = people[-1]
            rank = last["rank"] + (user.num_orders < last["count"])
        people.append({"rank": rank, "name": name, "count": user.num_orders})
        if len(people) == 3:
            break
    if not people:
        return None
    return {"name": str(semester["name"]), "people": people}


def _cached(key, ttl, compute, use_cache):
    value = cache.get(key) if use_cache else None
    if value is None:
        value = compute() or {}
        if use_cache:
            cache.set(key, value, ttl)
    return value


def payload(now=None, use_cache=True):
    now = timezone.localtime(now)
    today = now.date()

    live = _cached("baljan.skarm.live", LIVE_TTL, lambda: _live(now), use_cache)
    semester = _cached(
        f"baljan.skarm.semester.{today.isoformat()}",
        SEMESTER_TTL,
        lambda: _semester(today),
        use_cache,
    )
    # The high score cache is a multi-megabyte blob, so only unpack it rarely.
    top = _cached("baljan.skarm.top", TOP_TTL, _top, use_cache)

    return {
        "generated": now.isoformat(),
        "cafes": [{"key": key, "name": name} for _, key, name in CAFES],
        "today": live,
        "semester": semester or None,
        "top": top or None,
    }
