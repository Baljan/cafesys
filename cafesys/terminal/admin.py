# -*- coding: utf-8 -*-
from django.contrib import admin
from models import Item, Order, OrderItem, TagShown

class OrderAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'when', 'student')
    search_fields = ('student__liu_id', 'orderitem__item__title')
    list_filter = ('when', )

for cls in [
        Item,
        (Order, OrderAdmin),
        TagShown,
        ]:
    if isinstance(cls, tuple):
        admin.site.register(*cls)
    else:
        admin.site.register(cls)
