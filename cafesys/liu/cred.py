# -*- coding: utf-8 -*-

import ldap

SERVER = 'ldap://lukas-backend.unit.liu.se'
BIND = 'uid=%(username)s,ou=people,dc=student,dc=liu,dc=se'
SEARCH = ['sn', 'givenname', 'mail', 'postalAddress', 'liuStudentProgramCode',
        'liuUserStatus', 'liuPnr']

class LiuLdap(object):
    def __init__(self, connection, username, password):
        self.con = connection
        info = {
                'username': username,
                'password': password,
                }
        self.con.simple_bind(BIND % info, info['password'])


def main():
    import sys
    con = ldap.initialize(SERVER)
    ll = LiuLdap(con, sys.argv[1], sys.argv[2])


if __name__ == '__main__':
    main()
