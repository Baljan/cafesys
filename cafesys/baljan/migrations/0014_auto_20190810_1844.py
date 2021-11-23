# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-08-10 18:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('baljan', '0013_auto_20190803_2130'),
    ]

    operations = [
        migrations.AddField(
            model_name='blippconfiguration',
            name='card_reader_long_endianess',
            field=models.CharField(choices=[('little', 'little endian'), ('big', 'big endian')], default='little',
                                   help_text='"Byte order" för långa RFID-nummer (mer än fyra bytes). Vissa läsare byter ordning för nummer längre än fyra bytes.', max_length=6, verbose_name='lång byte order'),
        ),
        migrations.AddField(
            model_name='blippconfiguration',
            name='card_reader_radix',
            field=models.IntegerField(choices=[(10, 'decimal'), (16, 'hexadecimal')],
                                      default=10, help_text='Talbas för kortläsarens output', verbose_name='Talbas'),
        ),
        migrations.AddField(
            model_name='blippconfiguration',
            name='card_reader_short_endianess',
            field=models.CharField(choices=[('little', 'little endian'), ('big', 'big endian')], default='little',
                                   help_text='"Byte order" för korta RFID-nummer (fyra bytes). Oftast "little endian".', max_length=6, verbose_name='kort byte order'),
        ),
    ]
