# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.auth.models import User, check_password
from liu.models import Student
import ldap
import re

def valid_username(username):
    return re.match('^[a-z]{5,5}[0-9]{3,3}$', username) is not None

class LDAPBackend(object):
    def authenticate(self, username=None, password=None):
        if not valid_username(username):
            # TODO: log
            return None

        ldap_bind_str = "uid=%s, ou=people, dc=student, dc=liu, dc=se" % username
        base = "ou=people,dc=student,dc=liu,dc=se"
        scope = ldap.SCOPE_SUBTREE
        filter = "uid=%s" % username
        ret = None
        try:
            l = ldap.initialize(settings.LDAP_SERVER)
            l.protocol_version = ldap.VERSION3
            l.simple_bind_s(ldap_bind_str, password)

            result_id = l.search(base, scope, filter, ret)
            result_type, result_data = l.result(result_id, 0)
        except ldap.LDAPError, e:
            # TODO: log
            return None

        #print result_id, result_type, result_data
        try:
            first_name = " ".join(result_data[0][1]['givenName'])
            last_name = " ".join(result_data[0][1]['sn'])
        except Exception, e:
            # TODO: log
            return None

        email = "%s@student.liu.se" % username
        
        try:
            user = User.objects.get(username__exact=username)
        except:
            user = User.objects.create_user(username, email, password=None)
            student = Student(user=user, liu_id=username)
            user.save()

        return user


    def get_user(self, user_id):
        # FIXME: This should possible be some LDAP lookup.
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
