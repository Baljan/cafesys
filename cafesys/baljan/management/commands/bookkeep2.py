# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from ...bookkeep import get_bookkeep_data

class Command(BaseCommand):
    help = 'Show customer debt for year.'

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument(
            'year',
            type=int
        )

    def handle(self, *args, **options):
        year = options['year']
        print(get_bookkeep_data(year))