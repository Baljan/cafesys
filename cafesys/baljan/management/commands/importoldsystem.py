from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth.models import User
import MySQLdb
from datetime import date
from baljan.models import Profile
from baljan.util import get_logger
import re

log = get_logger('baljan.migration')

def _assoc(cursor, data):
    desc = cursor.description
    d = {}
    for name, value in zip(desc, data):
        d[name[0]] = value
    return d

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
        return self._db.cursor()

    def _decode(self, s):
        return s.decode(self.enc)

    def get_user_dicts(self):
        c = self._cursor()
        c.execute('''
SELECT user.*, person.* FROM user INNER JOIN person ON person.id=user.id
''')

        fetched = c.fetchall()
        return [_assoc(c, cols) for cols in fetched]

    def _get_phone(self, user_dict):
        c = self._cursor()
        c.execute('''
SELECT nummer FROM telefon WHERE persid=%d
''' % user_dict['id'])
        phone = c.fetchone()
        if phone: # validate
            trial = re.sub("[^0-9]", "", phone[0])[:10]
            phone = None
            if trial.startswith('07'): # only cells
                phone = trial
        return phone

    def setup_users(self):
        user_dicts = self.get_user_dicts()
        decode = self._decode
        created_count, existing_count = 0, 0
        for ud in user_dicts:
            u, created = User.objects.get_or_create(
                    username=decode(ud['login']).lower(),
                    first_name=decode(ud['fnamn']),
                    last_name=decode(ud['enamn']))

            u.email = decode(ud['login']).lower() + u"@student.liu.se"
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
        log.info('%d/%d user(s) created/existing' % (created_count, existing_count))


class Command(BaseCommand):
    args = ''
    help = """Import data from the old version of the system. There must be a running MySQL 
server. See OLD_SYSTEM_* settings.
"""

    def handle(self, *args, **options):
        imp = Import()
        imp.setup_users()
