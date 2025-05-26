import json
import stripe

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from .models import Product

stripe.api_key = settings.STRIPE_API_KEY

# TODO: idk if this is the right way to break this out.
# But I kinda refuse to put this in the big "views.py" file.
def handle_webhook(request: HttpRequest):
    payload = request.body
    event = None

    try:
        event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)

    # TODO: This should handle events like if someone cancelled
    # a checkout and stuff.
    if event.type == "checkout.session.completed":
        checkout_object = event.data.object
        checkout_id = checkout_object.id
        items = stripe.checkout.Session.list_line_items(checkout_id)

        for item in items:
            price_id = item.price.id
            quantity = item.quantity
            product = Product.objects.get(price_id__exact=price_id)
            print(product, quantity, price_id)
    else:
        print("Unhandled event type {}".format(event.type))
