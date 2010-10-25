# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template


urlpatterns = patterns("baljan.views",
    url(r"^$", 'index'),
    #url(r"^semesters$", 'semesters'),
    url(r"^signup/delete/(\d+)/(.*)$", 'delete_signup'),
    url(r"^callduty/delete/(\d+)/(.*)$", 'delete_callduty'),
    url(r"^tradable/toggle/(\d+)/(.*)$", 'toggle_tradable'),
    url(r"^semester/$", 'current_semester'),
    url(r"^day/(?P<day>[0-9-]+)$", 'day_shifts'),
    url(r"^semester/(?P<name>\w+)$", 'semester'),
    url(r"^profile$", 'profile'),
    url(r"^user/(.*)$", 'see_user'),
    url(r"^group/(.*)$", 'see_group', name='group'),
    url(r"^friend-request/toggle/([a-zA-Z0-9_]+)/(.*)$", 'toggle_friend_request'),
    url(r"^friend-request/accept-from/([a-zA-Z0-9_]+)/(.*)$", 'accept_friend_request_from'),
    url(r"^friend-request/deny-from/([a-zA-Z0-9_]+)/(.*)$", 'deny_friend_request_from'),
    url(r"^become-worker$", direct_to_template, {
        "template": "baljan/become_worker.html",
    }, name='become_worker'), 
    url(r"^become-worker/toggle/(.*)$", 'toggle_become_worker_request'),
    url(r'search-person', 'search_person'),

    url(r'trade/take/(\d+)/(.*)', 'trade_take', name='take_signup'),
    url(r'trade/accept/(\d+)/(.*)', 'trade_accept', name='accept_trade'),
    url(r'trade/deny/(\d+)/(.*)', 'trade_deny', name='deny_trade'),
)
