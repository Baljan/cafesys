from django.contrib import admin
from models import Item, Order, OrderItem, TagShown

admin.site.register(Item)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(TagShown)
