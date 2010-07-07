from django.db import models
from datetime import datetime

class Item(models.Model):
    title = models.CharField(max_length=50)
    description = models.CharField(max_length=100)
    cost = models.IntegerField()
    initial_count = models.IntegerField(default=0)
    img_path = models.CharField(max_length=200)

    def __str__(self):
        return "%s - %s (%g SEK)" % (self.title, self.description, self.cost)

class Order(models.Model):
    datetime = models.DateTimeField(default=datetime.now)
    user = models.ForeignKey('auth.User')

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="item_set")
    item = models.ForeignKey(Item)
    count = models.IntegerField(default=0)
