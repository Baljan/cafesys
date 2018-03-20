# -*- coding: utf-8 -*-
from django.conf.urls import url
from django.views.generic import TemplateView

from . import views


urlpatterns = (
    url(r"^$", views.index),
    url(r"^signup/delete/(\d+)/(.*)$", views.delete_signup, name='delete_signup'),
    url(r"^callduty/delete/(\d+)/(.*)$", views.delete_callduty, name='delete_callduty'),
    url(r"^tradable/toggle/(\d+)/(.*)$", views.toggle_tradable, name='toggle_tradable'),
    url(r"^semester/$", views.current_semester, name='current_semester'),
    url(r"^day/(?P<day>[0-9-]+)$", views.day_shifts, name='day_shifts'),
    url(r"^semester/(?P<name>\w+)$", views.semester, name='semester'),
    url(r"^admin-semester$", views.admin_semester, name='admin_semester'),
    url(r"^admin-semester/(\w+)$", views.admin_semester, name='admin_semester'),

    url(r"^profile$", views.profile, name='profile'),
    url(r"^credits$", views.credits, name='credits'),
    url(r"^orders/(\d+)$", views.orders, name='orders'),

    url(r"^user/(.*)$", views.see_user),
    url(r"^group/(.*)$", views.see_group, name='group'),
    url(r'search-person', views.search_person, name='search_person'),

    url(r'job-opening/(.+)/projector', views.job_opening_projector, name='job_opening_projector'),
    url(r'job-opening/(.+)', views.job_opening, name='job_opening'),

    url(r'call-duty/(\d+)/(\d+)', views.call_duty_week, name='call_duty_week'),
    url(r'call-duty', views.call_duty_week, name='call_duty_week'),

    url(r'price-list', views.price_list, name='price_list'),

    url(r'pdf/shift-combinations/(\w+)', views.shift_combinations_pdf, name='shift_combinations_pdf'),
    url(r'pdf/shift-combinations-form/(\w+)', views.shift_combination_form_pdf, name='shift_combination_form_pdf'),

    url(r'ical/user/(.+)/baljan.ics', views.user_calendar, name='user_calendar'),

    url(r'high-score/(\d+)/(\d+)', views.high_score, name='high_score'),
    url(r'high-score', views.high_score, name='high_score'),

    url(r'bestallning',views.orderFromUs, name='order_from_us'),
    url(r'trade/take/(\d+)/(.*)', views.trade_take, name='take_signup'),
    url(r'trade/accept/(\d+)/(.*)', views.trade_accept, name='accept_trade'),
    url(r'trade/deny/(\d+)/(.*)', views.trade_deny, name='deny_trade'),

    url(r'incoming-call', views.incoming_call),
    url(r'post-call', views.post_call),
)
