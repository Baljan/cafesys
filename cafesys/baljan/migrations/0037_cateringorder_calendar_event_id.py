from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("baljan", "0036_cateringorder_access_token"),
    ]

    operations = [
        migrations.AddField(
            model_name="cateringorder",
            name="calendar_event_id",
            field=models.CharField(
                blank=True,
                default="",
                max_length=1024,
                verbose_name="calendar event id",
            ),
        ),
    ]
