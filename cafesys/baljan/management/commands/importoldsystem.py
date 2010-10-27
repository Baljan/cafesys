from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth.models import User, Group
import MySQLdb
import MySQLdb.cursors
from datetime import date
from baljan.models import Profile, Semester, ShiftSignup, Shift
from baljan.models import OnCallDuty
from baljan.util import get_logger
import re

log = get_logger('baljan.migration')

manual_board = []

class Import(object):
    def __init__(self):
        # Make sure that all needed settings and such are configured.
        settingfmt = 'OLD_SYSTEM_MYSQL_%s'
        valid = True
        errs = []
        for setting in (
                'LOGIN',
                'PASSWORD',
                'DB',
                'HOST',
                ):
            full_setting = settingfmt % setting
            if hasattr(settings, full_setting):
                pass
            else:
                valid = False
                errs.append("missing setting %s" % full_setting)
        
        if not valid:
            raise CommandError('Bad configuration: %s' % ', '.join(errs))

        def s(setting):
            return getattr(settings, settingfmt % setting.upper())
        self._db = MySQLdb.connect(
                user=s('login'),
                passwd=s('password'),
                host=s('host'),
                db=s('db'))

        self.enc = 'latin-1'

    def _cursor(self):
        return self._db.cursor(cursorclass=MySQLdb.cursors.DictCursor)

    def _decode(self, s):
        return s.decode(self.enc)

    def get_user_dicts(self, user_id=None):
        c = self._cursor()
        if user_id is None:
            c.execute('''
SELECT user.*, person.* FROM user INNER JOIN person ON person.id=user.id
''')

            fetched = c.fetchall()
            return fetched
        else:
            c.execute('''
SELECT user.*, person.* FROM user INNER JOIN person ON person.id=user.id WHERE person.id=%d
''' % user_id)
            fetched = c.fetchone()
            return fetched

    def _get_phone(self, user_dict):
        c = self._cursor()
        c.execute('''
SELECT nummer FROM telefon WHERE persid=%d
''' % user_dict['id'])
        phone = c.fetchone()
        if phone: # validate
            trial = re.sub("[^0-9]", "", phone['nummer'])[:10]
            phone = None
            if trial.startswith('07'): # only cells
                phone = trial
        return phone

    def setup_users(self):
        user_dicts = self.get_user_dicts()
        decode = self._decode
        created_count, existing_count, skipped = 0, 0, []
        username_pattern = re.compile("^[a-z]{2,5}[0-9]{3,3}$")
        for ud in user_dicts:
            uname = decode(ud['login']).lower()
            if username_pattern.match(uname) is None:
                skipped.append(uname)
                continue

            u, created = User.objects.get_or_create(
                    username=uname,
                    first_name=decode(ud['fnamn']),
                    last_name=decode(ud['enamn']))

            u.email = u"%s@%s" % (
                decode(ud['login']).lower(), settings.USER_EMAIL_DOMAIN)
            u.set_unusable_password()
            u.save()

            p = u.get_profile()
            p.mobile_phone = self._get_phone(ud)
            p.save()
            if created:
                log.info('created: %r %r' % (u, p))
                created_count += 1
            else:
                log.info('existing: %r %r' % (u, p))
                existing_count += 1

        log.info('%d/%d/%d user(s) created/existing/skipped' % (
            created_count, existing_count, len(skipped)))
        if len(skipped):
            log.warning('skipped: %s' % ", ".join(skipped))

    def get_shift_dicts(self):
        c = self._cursor()
        c.execute('''SELECT * FROM persbok''')
        fetched = c.fetchall()
        return fetched

    def setup_shifts(self):
        shift_dicts = self.get_shift_dicts()
        decode = self._decode
        created_count, existing_count, skipped = 0, 0, []
        for sd in shift_dicts:
            day = sd['dag']
            sem = Semester.objects.for_date(day)
            if sem is None: # automatically create semester
                spring = day.month < 8
                if spring:
                    name = "VT%s" % day.year
                    start = date(day.year, 1, 1)
                    end = date(day.year, 7, 1)
                else:
                    name = "HT%s" % day.year
                    start = date(day.year, 8, 1)
                    end = date(day.year, 12, 24)
                sem = Semester(name=name, start=start, end=end)
                log.info('created %r' % sem)
                sem.save()

            ud = self.get_user_dicts(user_id=sd['persid'])
            if ud is None:
                skipped.append("user %s" % sd['persid'])
                continue

            uname = decode(ud['login']).lower()
            shift = Shift.objects.get(
                    when=day,
                    early=sd['em'] == 1,
                    semester=sem)
            signup, created = ShiftSignup.objects.get_or_create(
                    shift=shift,
                    user=User.objects.get(username=uname),
                    )

            if created:
                log.info('created: %r' % signup)
                created_count += 1
            else:
                log.info('existing: %r' % signup)
                existing_count += 1

        log.info('%d/%d/%d shift(s) created/existing/skipped' % (
            created_count, existing_count, len(skipped)))
        if len(skipped):
            log.warning('skipped: %s' % ", ".join(skipped))

    def get_oncall_dicts(self):
        c = self._cursor()
        c.execute('''SELECT * FROM jour''')
        return c.fetchall()

    def setup_oncallduties(self):
        oncall_dicts = self.get_oncall_dicts()
        decode = self._decode
        created_count, existing_count, skipped = 0, 0, []
        for oc in oncall_dicts:
            day = oc['dag']
            sem = Semester.objects.for_date(day)
            ud = self.get_user_dicts(user_id=oc['persid'])
            if ud is None:
                skipped.append("user %s" % oc['persid'])
                continue

            uname = decode(ud['login']).lower()
            shift = Shift.objects.get(
                    when=day,
                    early=oc['pass'] == 0,
                    semester=sem)
            oncall, created = OnCallDuty.objects.get_or_create(
                    shift=shift,
                    user=User.objects.get(username=uname),
                    )

            if created:
                log.info('created: %r' % oncall)
                created_count += 1
            else:
                log.info('existing: %r' % oncall)
                existing_count += 1

        log.info('%d/%d/%d call duty shift(s) created/existing/skipped' % (
            created_count, existing_count, len(skipped)))
        if len(skipped):
            log.warning('skipped: %s' % ", ".join(skipped))

    def setup_current_workers_and_board(self):
        sem = Semester.objects.for_date(date.today())
        if sem is None:
            return

        wgroup = Group.objects.get(name__exact=settings.WORKER_GROUP)
        bgroup = Group.objects.get(name__exact=settings.BOARD_GROUP)

        workers = User.objects.filter(shiftsignup__shift__semester=sem).distinct()
        for worker in workers:
            if not wgroup in worker.groups.all():
                worker.groups.add(wgroup)

        board_members = User.objects.filter(oncallduty__shift__semester=sem).distinct()
        for board_member in board_members:
            board_member.is_staff = True
            if not bgroup in board_member.groups.all():
                board_member.groups.add(bgroup)
            board_member.save()

        log.info('found %d/%d board/worker member(s)' % (
            len(board_members), len(workers)))

    def manual_board(self):
        bgroup = Group.objects.get(name__exact=settings.BOARD_GROUP)
        for uname in manual_board:
            user = User.objects.get(username=uname)
            user.is_staff = True
            if not bgroup in user.groups.all():
                user.groups.add(bgroup)
            user.save()


class Command(BaseCommand):
    args = ''
    help = """Import data from the old version of the system. There must be a running MySQL 
server. See OLD_SYSTEM_* settings.
"""

    def handle(self, *args, **options):
        imp = Import()
        #imp.setup_users()
        #imp.setup_shifts()
        #imp.setup_oncallduties()
        #imp.setup_current_workers_and_board()
        #imp.manual_board()
