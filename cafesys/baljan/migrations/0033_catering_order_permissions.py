"""Let the board manage catering orders.

`manage_catering_orders` guards the order central, where incoming orders from the
public order form are approved, denied and edited. Only the board handles those,
so only `settings.BOARD_GROUP` gets it.
"""

from django.conf import settings
from django.db import migrations

MANAGE_CATERING_ORDERS = "manage_catering_orders"


def _permission(apps):
    """Look up the permission, creating it if the signal has not run yet.

    Model permissions are created by the post_migrate signal, which runs after
    every migration, so the row may not exist while this one is running. Create
    it the same way django.contrib.auth.management.create_permissions does.
    """
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type, _ = ContentType.objects.get_or_create(
        app_label="baljan", model="cateringorder"
    )
    permission, _ = Permission.objects.get_or_create(
        codename=MANAGE_CATERING_ORDERS,
        content_type=content_type,
        defaults={"name": "Can manage catering orders"},
    )
    return permission


def forwards(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    permission = _permission(apps)

    group, _ = Group.objects.get_or_create(name=settings.BOARD_GROUP)
    group.permissions.add(permission)


def backwards(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    permission = _permission(apps)

    for group in Group.objects.filter(name=settings.BOARD_GROUP):
        group.permissions.remove(permission)


class Migration(migrations.Migration):
    dependencies = [
        ("baljan", "0032_cateringorder"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
