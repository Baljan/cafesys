from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template



urlpatterns = patterns("",
    url(r"^$", 'cal.views.worker_calendar'),
    url(r"^(?P<year>\d+)/(?P<month>.*)$", 'cal.views.worker_calendar'),
)
