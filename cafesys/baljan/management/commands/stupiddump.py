# -*- coding: utf-8 -*-
from optparse import make_option
import os
import pickle
import collections

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from baljan.models import Order, Section, Semester, Shift


class Command(BaseCommand):
    args = 'OUTFILE'
    help = 'CSV dump of blips. '

    def handle(self, *args, **options):
        out_file = args[0]
        if os.path.exists(out_file):
            raise CommandError('File exists: %s' % out_file)

        orders = Order.objects.order_by('put_at')
        dump = []
        for order in orders:
            dump.append(str(order.put_at))
        with open(out_file, 'wp') as output:
            output.write("\n".join(dump))
        print "Finished pickling to %s" % out_file

