# Create your views here.
from django.http import HttpResponse
from random import randint
from django.utils import simplejson as json
from django.shortcuts import render_to_response
from django.template import RequestContext
from models import Item, Order, OrderItem, TagShown
from django.core.serializers import serialize
from django.views.decorators.csrf import csrf_exempt

def kiosk_view(request):
    items = Item.objects.all()
    return render_to_response('terminal/terminal.html', {
        'items': items,
        }, context_instance=RequestContext(request))

def item_info(request):
    items = serialize('json', Item.objects.all())
    return HttpResponse(items, mimetype='text/plain')

@csrf_exempt
def handle_pending(request):
    """Handle a pending order. This function will throw assertion errors if
    there are more than one pending order, or if there is no pending order at
    all.

    "Pending order" actually means that a student has shown their card to the
    RFID reader.
    """
    pending = TagShown.objects.filter(pending=True)
    assert len(pending) == 1
    pending = pending[0]
    student = pending.student
    
    order = Order(student=student)
    order.save()
    for html_id, count in request.POST.items():
        assert html_id.startswith('item-')
        item_id = int(html_id.split('-')[1])
        count = int(count)
        if count != 0:
            item = Item.objects.get(pk=item_id)
            order_item = OrderItem(order=order, item=item, count=count)
            order_item.save()

            student.balance -= count * item.cost

    student.save()
    pending.pending = False
    pending.save()

    resp = {
            'balance': student.balance,
            }

    return HttpResponse(json.dumps(resp), mimetype='text/plain')

def poll_pending_orders(request):
    """Return a JSON object with a "is_pending" property. If it is true, it
    means that a student has shown his card to the RFID reader and that his
    order is to be handled based on the order in the kiosk terminal.

    This function does not handle the order. The appropriate request will be
    made by the kiosk browser if "is_pending" is true.
    """
    is_pending = len(TagShown.objects.filter(pending=True)) != 0
    info = { 'is_pending': is_pending, }
    return HttpResponse(json.dumps(info), mimetype='text/plain')

def trig_tag_shown(request, liu_id):
    """Trigger that a student showed his tag. There may only be one pending
    order at a time. If there are any pending orders in the queue, the response
    will be 'PENDING' and the request will not be put on the queue. """
    is_pending = len(TagShown.objects.filter(pending=True)) != 0
    if is_pending:
        return HttpResponse('PENDING', mimetype='text/plain')
    shown = TagShown.from_liu_id(liu_id)
    shown.save()
    return HttpResponse('OK', mimetype='text/plain')
