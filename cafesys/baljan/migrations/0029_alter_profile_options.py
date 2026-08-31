from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("baljan", "0028_alter_semester_options_alter_legalconsent_user"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="profile",
            options={
                "permissions": (
                    ("available_for_call_duty", "Available for call duty"),
                    ("free_coffee_unlimited", "Unlimited free coffee"),
                    ("free_coffee_with_cooldown", "Free coffee with cooldown"),
                    ("online_refill", "Online refill of coffee card balance"),
                    ("staff_access", "Can access the staff pages"),
                ),
                "verbose_name": "profile",
                "verbose_name_plural": "profiles",
            },
        ),
    ]
