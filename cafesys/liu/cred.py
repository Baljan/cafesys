# -*- coding: utf-8 -*-

import ldap

SERVER = 'ldap://lukas-backend.unit.liu.se'
BIND = 'uid=%(username)s, ou=people, dc=student, dc=liu, dc=se'
SEARCH = ['sn', 'givenname', 'mail', 'postalAddress', 'liuStudentProgramCode',
        'liuUserStatus', 'liuPnr']

class LiuLdap(object):
    def __init__(self, connection, username, password):
        base = ""
        scope = ldap.SCOPE_SUBTREE
        ldap_filter = "cn=*emika803*"

        self.con = connection
        info = {
                'username': username,
                'password': password,
                }
        self.con.simple_bind(BIND % info, info['password'])
        ldap_result_id = self.con.search(base, scope, ldap_filter, None)
	#result_set = []
	while 1:
            result_type, result_data = self.con.result(ldap_result_id, 0)
            if (result_data == []):
                break
            else:
                if result_type == ldap.RES_SEARCH_ENTRY:
                    print result_data

        

def main():
    import sys
    con = ldap.initialize(SERVER)
    con.protocol_version = ldap.VERSION2
    ll = LiuLdap(con, "pabka760", "xfz8pk01")


if __name__ == '__main__':
    main()
