# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-03-20 10:34
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('baljan', '0005_auto_20180307_2142'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='mobile_phone',
            field=models.CharField(blank=True, db_index=True, max_length=10, null=True, verbose_name='mobile phone number'),
        ),
    ]
