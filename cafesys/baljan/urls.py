# -*- coding: utf-8 -*-
from django.conf.urls import url
from django.urls import path
from django.views.generic import TemplateView

from . import views


urlpatterns = (
    path("", views.index),
    path("signup/delete/<int:pk>/<path:redir>", views.delete_signup, name='delete_signup'),
    path("callduty/delete/<int:pk>/<path:redir>", views.delete_callduty, name='delete_callduty'),
    path("tradable/toggle/<int:pk>/<path:redir>", views.toggle_tradable, name='toggle_tradable'),
    path("day/<slug:day>", views.day_shifts, name='day_shifts'),
    path("semester", views.current_semester, name='current_semester'),
    path("semester/<slug:name>", views.semester, name='semester'),
    path("semester/<slug:name>/<int:loc>", views.semester, name='located_semester'),
    path("admin-semester", views.admin_semester, name='admin_semester'),
    path("admin-semester/<slug:name>", views.admin_semester, name='admin_semester'),

    path("profile", views.profile, name='profile'),
    path("credits", views.credits, name='credits'),
    path("orders/<int:page_no>", views.orders, name='orders'),

    path("user/<int:who>", views.see_user),
    path("group/<str:group_name>", views.see_group, name='group'),
    path('search-person', views.search_person, name='search_person'),

    path('job-opening/<slug:semester_name>/projector', views.job_opening_projector, name='job_opening_projector'),
    path('job-opening/<slug:semester_name>', views.job_opening, name='job_opening'),

    path('call-duty/<int:year>/<int:week>', views.call_duty_week, name='call_duty_week'),
    path('call-duty', views.call_duty_week, name='call_duty_week'),

    path('price-list', views.price_list, name='price_list'),

    path('pdf/shift-combinations/<slug:sem_name>', views.shift_combinations_pdf, name='shift_combinations_pdf'),
    path('pdf/shift-combinations-form/<slug:sem_name>', views.shift_combination_form_pdf, name='shift_combination_form_pdf'),

    path('ical/user/<slug:private_key>/baljan.ics', views.user_calendar, name='user_calendar'),

    path('high-score/<int:year>/<int:week>/<int:location>', views.high_score, name='high_score'),
    path('high-score/<int:location>', views.high_score, name='high_score'),
    path('high-score', views.high_score, name='high_score'),

    path('bestallning', views.orderFromUs, name='order_from_us'),
    path('trade/take/<int:signup_pk>/<path:redir>', views.trade_take, name='take_signup'),
    path('trade/accept/<int:request_pk>/<path:redir>', views.trade_accept, name='accept_trade'),
    path('trade/deny/<int:request_pk>/<path:redir>', views.trade_deny, name='deny_trade'),

    path('incoming-ivr-call', views.incoming_ivr_call),
    path('incoming-call', views.incoming_call),
    path('post-call/<int:location>', views.post_call),
    path('post-call', views.post_call, {'location': 0}),
    path('incoming-sms', views.incoming_sms),
    path('consent', views.consent, name='consent'),
    path('do-blipp', views.do_blipp),
    path('integrity', views.integrity, name='integrity'),
    path('semester-shifts/<slug:sem_name>', views.semester_shifts, name='semester_shifts'),
    path('styrelsen', views.styrelsen, name='styrelsen'),
)
