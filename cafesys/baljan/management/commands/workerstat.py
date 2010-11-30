from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from baljan.util import get_logger
from django.utils.translation import ugettext as _
from baljan.models import Semester
from django.contrib.auth.models import User, Permission, Group
from django.db.models import Count

class Command(BaseCommand):
    args = 'semester name'
    help = 'Show worker statistics for semestser.'

    def handle(self, *args, **options):
        if not len(args) == 1:
            raise CommandError('no semester name given')

        semester_name = args[0]
        try:
            semester = Semester.objects.get(name=semester_name)
        except:
            raise CommandError('could not find semester named %s' % semester_name)

        # FIXME: This can be done much faster.
        workers = list(User.objects.filter(shiftsignup__shift__semester=semester).distinct())
        workers.sort(key=lambda x: x.shiftsignup_set.all().count(), reverse=True)
        signup_counts = sorted(set([w.shiftsignup_set.all().count() for w in workers]), reverse=True)
        print "%d worker(s):" % len(workers)
        for signup_count in signup_counts:
            workers_with_count_signups = [w for w in workers 
                    if w.shiftsignup_set.all().count()==signup_count]
            print "%3d signup(s): %3d" % (signup_count, len(workers_with_count_signups))
