from terminal.models import Order
from datetime import datetime
from django.conf import settings
from datetime import datetime, timedelta

def orders_from(student, with_cooldowns=True):
    if with_cooldowns:
        return Order.objects.filter(student=student)
    return Order.objects.filter(student=student, in_cooldown=False)


def last_order_from(student, with_cooldowns=True):
    orders = orders_from(student, with_cooldowns).order_by('-when')[0:1]
    if len(orders) == 0:
        return None
    return orders[0]


def make_order(student, order):
    """Make order for student. This function will extrapolate the cost if the
    student is a worker or board member.
    """
    worker_cooldown_seconds = settings.WORKER_COOLDOWN_SECONDS 
    worker_max_cost_reduce = settings.WORKER_MAX_COST_REDUCE 
    now = datetime.now()

    total_cost = 0
    for order_item in order.orderitem_set.all():
        item = order_item.item
        count = order_item.count
        total_cost += count * item.cost

    orders_to_fetch = 2
    last_orders = orders_from(student, 
            with_cooldowns=False).order_by('-when')[0:orders_to_fetch]

    previous_order = None
    if len(last_orders) == orders_to_fetch:
        previous_order = last_orders[1]

    if previous_order is None:
        # Set to a really big value if no previous orders have been made.
        since_previous_order = timedelta(50)
        print "previous_order None"
    else:
        since_previous_order = now - previous_order.when

    if student.is_regular():
        to_reduce = 0
    elif student.is_board_member():
        to_reduce = total_cost
    elif student.is_worker():
        to_reduce = worker_max_cost_reduce
        if since_previous_order.days == 0:
            if since_previous_order.seconds < worker_cooldown_seconds:
                to_reduce = 0
                order.in_cooldown = True
                order.save()

    student.balance -= max(0, total_cost - to_reduce)
    student.save()
