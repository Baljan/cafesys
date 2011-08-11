# coding=utf-8
from baljan.models import Good

capabilities = {
    'multiple_currencies': False,
}

defaults = {
    'currency': {
        'long': 'SEK',
        'short': ':-', 
        'position': 'append',
    }
}

def items():
    adapted = []
    goods = Good.objects.all()
    for good in goods:
        cost, currency = good.current_costcur()
        assert currency == defaults['currency']['long']
        adapted.append({
            'name': good.title,
            'description': good.description,
            'price': cost,
        })
    return adapted
