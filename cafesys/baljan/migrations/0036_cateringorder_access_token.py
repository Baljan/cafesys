import cafesys.baljan.models
from django.db import migrations, models


def fill_access_tokens(apps, schema_editor):
    """Give every existing order its own token.

    A single AddField with a callable default would write the *same* value to
    every row, which the unique constraint added afterwards would then reject.
    """
    CateringOrder = apps.get_model("baljan", "CateringOrder")
    for order in CateringOrder.objects.filter(access_token__isnull=True):
        order.access_token = cafesys.baljan.models.generate_catering_access_token()
        order.save(update_fields=["access_token"])


class Migration(migrations.Migration):
    dependencies = [
        ("baljan", "0035_cateringorderemail"),
    ]

    operations = [
        migrations.AddField(
            model_name="cateringorder",
            name="access_token",
            field=models.CharField(
                max_length=64, null=True, verbose_name="access token"
            ),
        ),
        migrations.RunPython(fill_access_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="cateringorder",
            name="access_token",
            field=models.CharField(
                default=cafesys.baljan.models.generate_catering_access_token,
                max_length=64,
                unique=True,
                verbose_name="access token",
            ),
        ),
        migrations.AddField(
            model_name="cateringorder",
            name="board_message_id",
            field=models.CharField(
                blank=True, default="", max_length=255, verbose_name="board message id"
            ),
        ),
        migrations.AddField(
            model_name="cateringorder",
            name="board_subject",
            field=models.CharField(
                blank=True, default="", max_length=255, verbose_name="board subject"
            ),
        ),
        migrations.AlterField(
            model_name="cateringorderemail",
            name="kind",
            field=models.CharField(
                choices=[
                    ("received", "Kvittens"),
                    ("approved", "Godkännande"),
                    ("denied", "Nekande"),
                ],
                max_length=16,
                verbose_name="kind",
            ),
        ),
    ]
