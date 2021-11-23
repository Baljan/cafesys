from logging import getLogger

from cafesys.baljan.models import Shift, Located
from cafesys.baljan.workdist.workdist_adapter import WorkdistAdapter

logger = getLogger(__name__)


def semester_post_save(sender, instance, created, **kwargs):
    if not created:
        # Don't do this for updates to a semester instance. Since the editing of date fields is
        # disabled we will only receive updates to the signup_possible field, which we don't
        # need to handle.
        return

    # Create one shift for every weekday
    sem = instance
    weekend = (5, 6)
    created_count = 0
    for day in sem.date_range():
        if day.weekday() in weekend:
            continue

        for early_or_lunch_or_late in (0, 1, 2):
            for location, name in Located.LOCATION_CHOICES:
                obj, created = Shift.objects.get_or_create(
                    semester=sem,
                    span=early_or_lunch_or_late,
                    when=day,
                    location=location
                )
                if created:
                    created_count += 1
    logger.info('%s: %d shifts added, signups=%s' %
                (sem.name, created_count, sem.signup_possible))

    WorkdistAdapter.recreate_shift_combinations(sem)
