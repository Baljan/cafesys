# -*- coding: utf-8 -*-
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase
from django.test.client import Client

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

    def test_login(self):
        c = Client()
        c.login(username='regular', password='regular')
        r = c.get('/calendar/')
        self.failUnlessEqual(r.context['SITE_NAME'], 'Pinax')
        c.logout()

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}

