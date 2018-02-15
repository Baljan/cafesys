# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta

import sys
from time import sleep

from django.core.management.base import BaseCommand, CommandError

from ...models import Order

import gc


def queryset_iterator(queryset, chunksize=1000):
    """
    Iterate over a Django Queryset ordered by the primary key

    This method loads a maximum of chunksize (default: 1000) rows in it's
    memory at the same time while django normally would load all rows in it's
    memory. Using the iterator() method only causes it to not preload all the
    classes.

    Note that the implementation of the iterator does not support ordered query sets.
    """
    pk = 0
    last_pk = queryset.order_by('-pk')[0].pk
    queryset = queryset.order_by('pk')
    while pk < last_pk:
        for row in queryset.filter(pk__gt=pk)[:chunksize]:
            pk = row.pk
            yield row
        gc.collect()


class Command(BaseCommand):
    """
    Iterates through all orders between (and including) the two specified dates,
    printing the time of the blipp as well as how much was paid for the coffee.

    You might not want to run this command during working hours because of the
    performance implications.
    """

    help = 'Dump all blipps between two dates in CSV format.'

    def add_arguments(self, parser):
        parser.add_argument('date_from', type=lambda d: datetime.strptime(d, '%Y-%m-%d'))
        parser.add_argument('date_to', type=lambda d: datetime.strptime(d, '%Y-%m-%d'))

    def handle(self, *args, **options):
        date_from = options['date_from']
        date_to = options['date_to'] + timedelta(hours=23, minutes=59, seconds=59)

        orders = Order.objects.filter(put_at__range=(date_from, date_to))
        orders_queryset = queryset_iterator(orders)
        print('time, paid')

        iterations_since_sleep = 0
        for order in orders_queryset:
            print('%s, %d' % (order.put_at.strftime('%Y-%m-%d %H:%M:%S'), order.paid))
            iterations_since_sleep += 1

            if iterations_since_sleep >= 1000:
                iterations_since_sleep = 0
                sys.stdout.flush()
                sleep(0.05)
