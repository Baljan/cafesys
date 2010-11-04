from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth.models import User, Group
from datetime import date
import baljan.models
from baljan.util import date_range
from django.contrib.webdesign import lorem_ipsum
from string import letters
from random import sample

def name():
    n = ''
    while len(n) < 5:
        n += lorem_ipsum.words(1, common=False)
    return n.capitalize()

GROUPS = (settings.WORKER_GROUP, settings.BOARD_GROUP,)

def creds():
    first = name()
    last = 'Dummy'
    uname = "%s%s" % (first[:3], last[:2])
    uname = uname.lower() + 'XYZ'
    email = "%s@dummy.se" % uname.lower()
    return uname, first, last, email

def randuser():
    while True:
        uname, first, last, email = creds()
        if User.objects.filter(username=uname).count() != 0:
            continue
        u = User(username=uname, first_name=first, last_name=last, email=email)
        u.set_password(uname)
        u.save()
        break
    return u


class Command(BaseCommand):
    args = ''
    help = 'Set up dummy data. Suitable for tests and demonstrations.'

    def handle(self, *args, **options):
        valid = True 
        if not valid:
            raise CommandError('Bad configuration: %s' % ', '.join(errs))
        
        today = date.today()

    today = date.today()

    user_count = 100

    wgroup, _ = Group.objects.get_or_create(name=settings.WORKER_GROUP)
    bgroup, _ = Group.objects.get_or_create(name=settings.BOARD_GROUP)

    created = [randuser() for i in range(max(0, user_count - User.objects.all().count()))]
    dummies = User.objects.filter(last_name__exact='Dummy')

    worker_count = int(0.7*len(dummies))
    board_count = int(0.1*len(dummies))
    for start, end, group in (
            (0, worker_count, wgroup),
            (worker_count, worker_count+board_count, bgroup)):
        for dummy in dummies[start:end]:
            if not group in dummy.groups.all():
                dummy.groups.add(group)
                dummy.save()

    for dummy in dummies[start:end]:
        if bgroup in dummy.groups.all():
            dummy.is_staff = True
            dummy.save()
    
    wdummies = dummies.filter(groups__name=settings.WORKER_GROUP)
    wprofs = baljan.models.Profile.objects.filter(user__groups__name=settings.WORKER_GROUP)
    bdummies = dummies.filter(groups__name=settings.BOARD_GROUP)
    bprofs = baljan.models.Profile.objects.filter(user__groups__name=settings.BOARD_GROUP)

    for w in wprofs:
        friends = sample(wprofs, 5)
        for f in friends:
            if f is not w and f not in w.friend_profiles.all():
                w.friend_profiles.add(f)
                w.save()
