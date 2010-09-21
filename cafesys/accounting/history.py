from terminal.models import Order
from liu.models import BalanceCode

def student_orders(student):
    return Order.objects.filter(student=student)

def student_codes(student):
    return BalanceCode.objects.filter(used_by=student)
