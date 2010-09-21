from accounting import history
from liu.models import BalanceCode
from datetime import date

def keys(request):
    d = {
        'order_history': [],
        'code_history': [],
        'balance': None,
        'good_balance': None,
        }

    if request.user.is_authenticated():
        student = request.user.get_profile()
        d.update({
            'order_history': history.student_orders(student),
            'code_history': history.student_codes(student),
            'balance': student.balance,
            'positive_balance': 0 <= student.balance,
        })

    return d

class RefillError(Exception):
    pass

def refill(student, code_string):
    bc = BalanceCode.objects.filter(code=code_string)
    if len(bc) == 0:
        raise RefillError("Invalid code.")

    assert len(bc) == 1
    bc = bc[0]

    if bc.used_by is not None:
        raise RefillError("The code has already been used.")

    # FIXME: Maybe check how old a code is.

    # Code is OK. Update the student's balance and mark the code as used.
    student.balance += bc.value
    student.save()
    bc.used_by = student
    bc.used_at = date.today()
    bc.save()

    return student, bc
