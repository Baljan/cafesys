from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template



urlpatterns = patterns("",
    url(r"^$", direct_to_template, {"template": "terminal/terminal.html"}, name="terminal"),
    url(r"^order-info$", 'terminal.views.order_count_and_last_balance'),
)
