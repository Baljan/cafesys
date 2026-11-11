"""Undo 0030: substitutes get no staff page access, only what is set in admin."""

from django.db import migrations


def forwards(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    Permission.objects.filter(
        codename="staff_access", content_type__app_label="baljan"
    ).delete()

    view_shiftsignup = Permission.objects.filter(
        codename="view_shiftsignup", content_type__app_label="baljan"
    ).first()
    if view_shiftsignup:
        for group in Group.objects.filter(name="inhoppare"):
            group.permissions.remove(view_shiftsignup)


class Migration(migrations.Migration):
    dependencies = [
        ("baljan", "0042_oncallweek"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name="profile",
            options={
                "permissions": (
                    ("available_for_call_duty", "Available for call duty"),
                    ("free_coffee_unlimited", "Unlimited free coffee"),
                    ("free_coffee_with_cooldown", "Free coffee with cooldown"),
                    ("online_refill", "Online refill of coffee card balance"),
                ),
                "verbose_name": "profile",
                "verbose_name_plural": "profiles",
            },
        ),
    ]
