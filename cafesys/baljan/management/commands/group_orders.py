from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from ...models import Semester, Order


class Command(BaseCommand):
    args = "group semester"
    help = "Command to retrieve all orders from a given group"

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError("invalid args (should be: %s)" % self.args)

        group = args[0]
        semester = args[1]

        try:
            group = Group.objects.get(name=group)
        except Group.DoesNotExist:
            raise CommandError("bad group: %s" % options["group"])

        try:
            semester = Semester.objects.get(name=semester)
        except Group.DoesNotExist:
            raise CommandError("bad semester: %s" % options["semester"])

        all_users = list(group.user_set.distinct().order_by("first_name"))

        start = semester.start
        end = semester.end

        user_order = []
        total_sum = 0
        for u in all_users:
            orders = len(
                Order.objects.filter(
                    user=u).filter(
                    made__gte=start,
                    made__lte=end))
            total_sum += orders
            user_order.append((u, orders))

        print(
            "\nTotal (free) orders by %s between %s and %s:"
            % (group.name, str(start), str(end))
        )
        print("Username\t#")
        print("------------------------------")

        for u, orders in user_order:
            print("%s:\t%i\torders" % (u.username, orders))

        print("------------------------------")
        print("Total:\t\t%i\torders" % total_sum)
        print(
            "Most orders: %s (%.1f %%)\n"
            % (
                str("i dont know who"),
                (max(b for (a, b) in user_order)) / float(total_sum) * 101,
            )
        )
