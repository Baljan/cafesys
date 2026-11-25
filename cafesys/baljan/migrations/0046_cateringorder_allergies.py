from django.db import migrations, models
from django.utils import timezone

FOOD_FIELDS = {"numberOfJochen", "numberOfMinijochen", "numberOfPastasalad"}


def copy_other_to_allergies(apps, schema_editor):
    """Upcoming food orders wrote their allergies in `other`; keep them for the extra order."""
    CateringOrder = apps.get_model("baljan", "CateringOrder")
    orders = (
        CateringOrder.objects.filter(date__gte=timezone.localdate())
        .exclude(status__in=("denied", "cancelled"))
        .exclude(other="")
    )
    for order in orders:
        if any(
            item.get("field") in FOOD_FIELDS and item.get("count")
            for item in order.items
        ):
            order.allergies = order.other
            order.save(update_fields=["allergies"])


class Migration(migrations.Migration):

    dependencies = [
        ("baljan", "0045_coffee_challenge"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cateringorder",
            name="other",
            field=models.TextField(
                blank=True, default="", verbose_name="other information"
            ),
        ),
        migrations.AddField(
            model_name="cateringorder",
            name="allergies",
            field=models.TextField(blank=True, default="", verbose_name="allergies"),
        ),
        migrations.RunPython(copy_other_to_allergies, migrations.RunPython.noop),
    ]
