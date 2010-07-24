# -*- coding: utf-8 -*-
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase
from django.test.client import Client
from models import Student

class LiuTestMixin(object):
    def _logged_in_client(self, username_and_password,
            is_worker=False, is_board_member=False):
        c = Client()
        c.login(username=username_and_password, password=username_and_password)
        return c


class SimpleTest(TestCase, LiuTestMixin):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

    def _login_test_with_params(self, username_and_password, is_regular=False,
            is_worker=False, is_board_member=False):
        c = Client()
        c.login(username=username_and_password, password=username_and_password)
        r = c.get('/calendar/')
        self.failUnlessEqual(r.context['is_regular'], is_regular)
        self.failUnlessEqual(r.context['is_worker'], is_worker)
        self.failUnlessEqual(r.context['is_board_member'], is_board_member)

    def test_login_as_regular(self):
        self._login_test_with_params('regular', is_regular=True)

    def test_login_as_worker(self):
        self._login_test_with_params('worker', is_worker=True)

    def test_login_as_board(self):
        self._login_test_with_params('board', is_worker=True, is_board_member=True)

    def test_request_to_become_worker(self):
        user = 'regular'
        student = Student.objects.get(liu_id=user)
        c = self._logged_in_client(user)

        r = c.post('/liu/request-become-worker/remove', follow=True)
        self.failUnlessEqual(student.wants_to_be_a_worker(), False)

        r = c.post('/liu/request-become-worker/add', follow=True)
        self.failUnlessEqual(student.wants_to_be_a_worker(), True)

        r = c.post('/liu/request-become-worker/remove', follow=True)
        self.failUnlessEqual(student.wants_to_be_a_worker(), False)


__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}

