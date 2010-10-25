# -*- coding: iso-8859-15 -*-
"""login_year_view FunkLoad test

$Id: $
"""
import unittest
from funkload.FunkLoadTestCase import FunkLoadTestCase
from webunit.utility import Upload
from funkload.utils import Data
#from funkload.utils import xmlrpc_get_credential

class LoginYearView(FunkLoadTestCase):
    """XXX

    This test use a configuration file LoginYearView.conf.
    """

    def setUp(self):
        """Setting up test."""
        self.logd("setUp")
        self.server_url = self.conf_get('main', 'url')
        # XXX here you can setup the credential access like this
        # credential_host = self.conf_get('credential', 'host')
        # credential_port = self.conf_getInt('credential', 'port')
        # self.login, self.password = xmlrpc_get_credential(credential_host,
        #                                                   credential_port,
        # XXX replace with a valid group
        #                                                   'members')

    def test_login_year_view(self):
        # The description should be set in the configuration file
        server_url = self.server_url
        # begin of test ---------------------------------------------

        # /tmp/tmpsf2X99_funkload/watch0014.request
        self.get(server_url + "/calendar/2010/",
            description="Get /calendar/2010/")
        # /tmp/tmpsf2X99_funkload/watch0017.request
        self.get(server_url + "/calendar/2011/",
            description="Get /calendar/2011/")
        # /tmp/tmpsf2X99_funkload/watch0020.request
        self.get(server_url + "/calendar/2008",
            description="Get /calendar/2008")
        # /tmp/tmpsf2X99_funkload/watch0024.request
        self.get(server_url + "/account/logout/",
            description="Get /account/logout/")

        # end of test -----------------------------------------------

    def tearDown(self):
        """Setting up test."""
        self.logd("tearDown.\n")



if __name__ in ('main', '__main__'):
    unittest.main()
