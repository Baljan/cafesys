# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand, CommandError

from ...models import Order


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

        orders = Order.objects.filter(put_at__range=(date_from, date_to)).order_by('put_at')
        print('time, paid')
        for order in orders:
            print('%s, %d' % (order.put_at.strftime('%Y-%m-%d %H:%M:%S'), order.paid))
