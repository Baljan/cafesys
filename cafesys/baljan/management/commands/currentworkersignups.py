# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth.models import User
from csv import writer, QUOTE_MINIMAL
from sys import stdout
from django.db.models import Count


class Command(BaseCommand):
    help = ('Command for retrieving the number of signups and semesters that '
            'all current workers have signed up for in csv format.')

    def add_arguments(self, parser):
        parser.add_argument('-f',
                            '--format',
                            type=str,
                            action='store',
                            metavar='FORMAT',
                            dest='format',
                            choices=('csv', 'tsv'),
                            default='csv',
                            help=('Format to use.\n'
                                  'Available choices are: "csv", "tsv".\n'
                                  '(default: "csv")'))

    def handle(self, *args, **options):
        delimiter = ',' if options['format'] == 'csv' else '\t'
        fieldnames = ('first name', 'last name', 'liu-id', 'signups',
                      'semesters')
        csv_writer = writer(stdout,
                            delimiter=delimiter,
                            quotechar='"',
                            quoting=QUOTE_MINIMAL)

        workers = User.objects.filter(groups__name=settings.WORKER_GROUP)\
            .annotate(
            num_signups=Count('shiftsignup', distinct=True),
            num_semesters=Count(
                'shiftsignup__shift__semester', distinct=True)
        )
        rows = ((worker.first_name, worker.last_name, worker.username,
                 worker.num_signups, worker.num_semesters)
                for worker in workers)

        csv_writer.writerow(fieldnames)
        csv_writer.writerows(rows)
