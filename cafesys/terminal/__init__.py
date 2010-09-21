from terminal.models import Order
from datetime import datetime
from django.conf import settings
from dateutil.relativedelta import relativedelta

def orders_from(student):
    return Order.objects.filter(student=student)


def last_order_from(student):
    orders = orders_from(student).order_by('-when')[0:1]
    if len(orders) == 0:
        return None
    return orders[0]


def make_order(student, order):
    """Make order for student. This function will extrapolate the cost if the
    student is a worker or board member.
    """
    cooldown_minutes = settings.WORKER_FREE_COFFEE_COOLDOWN_MINUTES 
    now = datetime.now()

    total_cost = 0
    for order_item in order.orderitem_set.all():
        item = order_item.item
        count = order_item.count
        total_cost += count * item.cost

    if student.is_regular():
        pass # no adjusting of the order cost
    elif student.is_board_member():
        total_cost = 0
    elif student.is_worker():
        # TODO: Implement.
        pass

    student.balance -= total_cost
    student.save()
