from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template

urlpatterns = patterns("",
    url(r"^$", 'terminal.views.kiosk_view'),
    url(r"^poll-pending-orders$", 'terminal.views.poll_pending_orders'),
    url(r"^item-info$", 'terminal.views.item_info'),
    url(r"^handle-pending$", 'terminal.views.handle_pending'),
    url(r"^trig-tag-shown/(?P<liu_id>[a-z0-9]+)$", 'terminal.views.trig_tag_shown'),
)
