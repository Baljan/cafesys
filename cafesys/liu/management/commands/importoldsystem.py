from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth.models import User
from liu.models import Student
from cal.models import Shift, ScheduledMorning, ScheduledAfternoon
from cal.models import MorningShift, AfternoonShift
import MySQLdb

class Command(BaseCommand):
    args = ''
    help = 'Import data from the old version of the system.'

    def handle(self, *args, **options):
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
        db = MySQLdb.connect(
                user=s('login'),
                passwd=s('password'),
                host=s('host'),
                db=s('db'))

        c = db.cursor()
        c.execute('''SELECT login, id FROM user''')

        enc = 'latin-1'
        uid_to_liu_id = {}
        fetched = c.fetchall()
        for liu_id, uid in fetched:
            uid_to_liu_id[int(uid)] = liu_id.decode(enc)
        
        print "Importing %d users." % len(uid_to_liu_id.keys())

        emailfmt = '%s@student.liu.se'
        skipped = 0
        failed = 0
        for uid, liu_id in uid_to_liu_id.items():
            prevs = len(Student.objects.filter(liu_id=liu_id))
            if prevs == 0:
                pass # OK
            elif prevs == 1:
                skipped += 1
                continue # user already exists
            else:
                assert True==False

            c = db.cursor()
            c.execute('SELECT fnamn, enamn FROM person WHERE id=%d LIMIT 1' % int(uid))
            try:
                first_name, last_name = c.fetchone()
                first_name = first_name.decode(enc)
                last_name = last_name.decode(enc)
                print "Found", first_name, last_name
            except TypeError:
                first_name, last_name = None, None

            try:
                user = User.objects.create_user(liu_id, emailfmt % liu_id, password=None)
                user.first_name = first_name
                user.last_name = last_name
                user.save()
                student = Student(user=user, liu_id=liu_id)
                student.save()
            except:
                # FIXME: Figure out exactly what went wrong here.
                failed += 1
        
        if skipped != 0:
            print "Skipped importing %d users because they already existed." % skipped
        if failed != 0:
            print "Failed importing %d users." % skipped 

        # Import workers and the schedule.
        for uid, liu_id in uid_to_liu_id.items():
            c = db.cursor()
            c.execute('SELECT dag, em FROM persbok WHERE persid=%d' % uid)
            shifts = c.fetchall()
            if len(shifts) == 0:
                continue # not a worker

            student = Student.objects.get(liu_id=liu_id)
            for day, is_afternoon in shifts:
                Shift.add_to(day)
                if is_afternoon:
                    shift = AfternoonShift.objects.get(day=day)
                    sched = ScheduledAfternoon(shift=shift, student=student)
                    sched.save()
                else:
                    shift = MorningShift.objects.get(day=day)
                    sched = ScheduledMorning(shift=shift, student=student)
                    sched.save()

                # TODO: Possibly make a worker of the student. Depends on how
                # long ago the shift was.

