# -*- coding: utf-8 -*-
import collections
import os
import pickle

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from ...models import Order, Section, Semester, Shift


class Command(BaseCommand):
    args = 'OUTFILE'
    help = 'Save a dump (pickled) suitable to use for data mining.'

    def handle(self, *args, **options):
        out_file = args[0]
        if os.path.exists(out_file):
            raise CommandError('File exists: %s' % out_file)

        user_related = ['profile__section']
        users = User.objects.select_related(
            *user_related).order_by('first_name')
        order_related = ['user']
        orders = Order.objects.select_related(
            *order_related).order_by('put_at')
        sections = Section.objects.order_by('name')
        semester_related = ['shift_set']
        semesters = Semester.objects.select_related(
            *semester_related).order_by('start')
        shift_related = ['semester',
                         'shiftsignup_set__user', 'oncallduty_set__user']
        shifts = Shift.objects.select_related(*shift_related).order_by('when')

        dump = {}
        dump['first_order'] = orders[0].put_at
        dump['latest_order'] = Order.objects.latest('put_at').put_at

        dump['users'] = []
        dump['user_orders'] = collections.defaultdict(list)
        dump['user_workshifts'] = collections.defaultdict(list)
        dump['user_oncallshifts'] = collections.defaultdict(list)
        dump['user_name'] = {}
        dump['user_section'] = {}

        dump['orders'] = []

        dump['sections'] = []

        dump['semesters'] = []
        dump['semester_name'] = {}
        dump['semester_startend'] = {}
        dump['semester_workers'] = collections.defaultdict(set)
        dump['semester_oncall'] = collections.defaultdict(set)
        dump['semester_shifts'] = collections.defaultdict(list)

        dump['shifts'] = []
        dump['shift_span'] = collections.defaultdict(list)
        dump['shift_date'] = {}
        dump['shift_workers'] = collections.defaultdict(list)
        dump['shift_oncall'] = collections.defaultdict(list)
        dump['shift_semester'] = {}

        for user in users:
            dump['users'].append(user.id)
            dump['user_name'][user.id] = user.first_name
            user_profile = user.profile
            if user_profile and user_profile.section:
                dump['user_section'][user.id] = user_profile.section.name
            else:
                dump['user_section'][user.id] = None
        print("Finished with users")

        for shift in shifts:
            dump['shifts'].append(shift.id)
            dump['shift_span'][shift.id] = shift.span
            dump['shift_date'][shift.id] = shift.when
            dump['shift_semester'][shift.id] = shift.semester.id
            dump['semester_shifts'][shift.semester.id].append(shift.id)
            for signup in shift.shiftsignup_set.order_by('user__id'):
                worker = signup.user
                dump['shift_workers'][shift.id].append(worker.id)
                dump['user_workshifts'][worker.id].append(shift.id)
                dump['semester_workers'][shift.semester.id].add(worker.id)
            for signup in shift.oncallduty_set.order_by('user__id'):
                oncall = signup.user
                dump['shift_oncall'][shift.id].append(oncall.id)
                dump['user_oncallshifts'][oncall.id].append(shift.id)
                dump['semester_oncall'][shift.semester.id].add(oncall.id)
        for set_key in ['semester_workers', 'semester_oncall']:
            for semester_id, user_set in list(dump[set_key].items()):
                dump[set_key][semester_id] = sorted(list(user_set))
        print("Finished with shifts")

        for semester in semesters:
            dump['semesters'].append(semester.id)
            dump['semester_name'][semester.id] = semester.name
            dump['semester_startend'][semester.id] = (
                semester.start, semester.end)
        print("Finished with semesters")

        for section in sections:
            dump['sections'].append(section.name)
        print("Finished with sections")

        for order in orders:
            dump['orders'].append(order.put_at)
            dump['user_orders'][order.user.id].append(order.put_at)
        print("Finished with orders")

        with open(out_file, 'wb') as output:
            pickle.dump(dump, output)
        print("Finished pickling to %s" % out_file)
