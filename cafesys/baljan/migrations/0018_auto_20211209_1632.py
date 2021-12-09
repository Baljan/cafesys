# Generated by Django 3.2.8 on 2021-12-09 16:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('baljan', '0017_auto_20211121_1753'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='card_cache',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='card_id',
            field=models.BigIntegerField(blank=True, db_index=True, help_text='card ids can be manually set', null=True, unique=True, verbose_name='LiU-kortnummer'),
        ),
    ]
