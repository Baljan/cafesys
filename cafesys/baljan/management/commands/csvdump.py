# -*- coding: utf-8 -*-
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from baljan.models import Order


class Command(BaseCommand):
    args = ''
    help = 'Dump orders per month in CSV format.'

    def handle(self, *args, **options):
        valid = True
        if not valid:
            raise CommandError('invalid config')

        def datetime_to_month(dt):
            return date(dt.year, dt.month, 1)

        orders = Order.objects.all().order_by('put_at')
        current_day = None
        dates = []
        for o in orders:
            this_date = datetime_to_month(o.put_at)
            if current_day == this_date:
                pass
            else:
                current_day = this_date
                dates.append(this_date)

        years = sorted(set([d.year for d in dates]))
        months = sorted(set([d.month for d in dates]))

        order_counts = []
        for m in months:
            counts = []
            for y in years:
                counts.append(Order.objects.filter(
                    put_at__year=y,
                    put_at__month=m,
                ).count())
            order_counts.append((m, counts))

        print("month, %s" % ", ".join([str(y) for y in years]))
        for m, year_counts in reversed(order_counts):
            print("%d, %s" % (m, ", ".join([str(yc) for yc in year_counts])))
