from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template



urlpatterns = patterns("",
    url(r"^$", 'terminal.views.kiosk_view'),
    url(r"^order-info$", 'terminal.views.order_count_and_last_balance'),
    url(r"^item-info$", 'terminal.views.item_info'),
)
