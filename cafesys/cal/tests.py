# -*- coding: utf-8 -*-
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase
from django.test.client import Client
from liu.tests import LiuTestMixin
from mock import Mock
import ajax
from liu.models import Student
from models import Shift, MorningShift, AfternoonShift
from datetime import date

class SimpleTest(TestCase, LiuTestMixin):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

    year = 2020
    month = 1
    days = 3

    def _get_dates(self):
        return [date(self.year, self.month, d) for d in range(1,self.days+1)]

    def _test_add_working_days_as(self, username):
        user = Student.objects.get(liu_id=username).user
        request = Mock()
        request.user = user
        days = self._get_dates()
        ret = ajax.with_days(request, '/', 'add-shifts', 
                [d.strftime('date-%Y-%m-%d') for d in days])

        for cls in MorningShift, AfternoonShift:
            for d in days:
                shifts = cls.objects.filter(day=d)
                self.failUnlessEqual(len(shifts), 1)
            no_shift = cls.objects.filter(day=date(2020, 1, self.days+1))
            self.failUnlessEqual(len(no_shift), 0)

    def _test_remove_working_days_as(self, username):
        user = Student.objects.get(liu_id=username).user
        request = Mock()
        request.user = user
        days = self._get_dates()

        self._test_add_working_days_as(username)
        ret = ajax.with_days(request, '/', 'remove-shifts', 
                [d.strftime('date-%Y-%m-%d') for d in days])

        for cls in MorningShift, AfternoonShift:
            for d in days:
                shifts = cls.objects.filter(day=d)
                self.failUnlessEqual(len(shifts), 0)

    def test_add_working_days_ok(self):
        self._test_add_working_days_as('board')

    def test_remove_working_days_ok(self):
        self._test_remove_working_days_as('board')

    def _test_bad_add_remove(self, method):
        usernames = ['worker', 'regular']
        for username in usernames:
            self.assertRaises(AssertionError, lambda: method(username))

    def test_add_working_days_bad(self):
        self._test_bad_add_remove(self._test_add_working_days_as)

    def test_remove_working_days_bad(self):
        self._test_bad_add_remove(self._test_remove_working_days_as)


__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}

