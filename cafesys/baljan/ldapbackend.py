# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.auth.models import User, check_password
from baljan.util import get_logger, get_or_create_user
import ldap
import re

log = get_logger('baljan.ldap')

def valid_username(username):
    return re.match('^[a-z]{2,5}[0-9]{3,3}$', username) is not None


def exists_in_ldap(username):
    return fetch_user(username, bind=False, create=False)


def search(username, password=None, bind=False):
    if not valid_username(username):
        log.error('invalid username %r' % username)
        return None

    base = "ou=people,dc=student,dc=liu,dc=se"
    uid_kw = "uid=%s" % username
    ldap_bind_str = "%s, %s" % (uid_kw, base)
    scope = ldap.SCOPE_SUBTREE
    ret = None
    try:
        l = ldap.initialize(settings.LDAP_SERVER)
        l.protocol_version = ldap.VERSION3
        if bind:
            l.simple_bind_s(ldap_bind_str, password)

        result_id = l.search(base, scope, uid_kw, ret)
        result_type, result_data = l.result(result_id, 0)
    except ldap.LDAPError, e:
        log.error('bad LDAP request')
        return None
    return result_data


def fetch_user(username, password=None, bind=False, create=True):
    """If the user does not exist in our own db, he or she will be added to it.
    If `bind` is false the password argument is ignored and only a search is
    performed inside this function, otherwise both bind and search are 
    performed. If `create` is false, True is returned instead of the actual 
    user if the search or bind+search finds a user (otherwise None)."""
    result_data = search(username, password, bind)
    if result_data is None:
        return None

    first_name, last_name = None, None
    try:
        first_name = " ".join(result_data[0][1]['givenName'])
        last_name = " ".join(result_data[0][1]['sn'])
    except Exception, e:
        log.error(e)
        return None

    if create:
        # FIXME: DRY.
        enc = 'utf-8'
        if first_name is not None:
            first_name = first_name.decode(enc)
        if last_name is not None:
            last_name = last_name.decode(enc)

        user, created = get_or_create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
        )

        if created:
            log.info('created %r' % user)
        else:
            log.info('fetched %r from directory' % user)
        return user
    return True


class LDAPBackend(object):
    def authenticate(self, username=None, password=None):
        return fetch_user(username, password, bind=True)

    def get_user(self, user_id):
        # FIXME: This should possibly be some LDAP lookup.
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
