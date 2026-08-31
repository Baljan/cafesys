"""Give the substitute ("inhoppare") group access to the staff pages.

Substitutes get the Personal link and a read-only work planning tab, but must
not be able to sign up for shifts, so they deliberately do not get
`self_and_friend_signup`.

The staff link used to be gated on `self_and_friend_signup`; workers and the
board therefore need the new `staff_access` permission to keep it.
"""

from django.conf import settings
from django.db import migrations

STAFF_ACCESS = "staff_access"
VIEW_SHIFTSIGNUP = "view_shiftsignup"


def _permissions(apps):
    """Look up the permissions we hand out.

    `staff_access` is created by the post_migrate signal, which runs after all
    migrations, so it may not exist yet when this runs. Create it the same way
    django.contrib.auth.management.create_permissions does.
    """
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    profile_ct, _ = ContentType.objects.get_or_create(
        app_label="baljan", model="profile"
    )
    staff_access, _ = Permission.objects.get_or_create(
        codename=STAFF_ACCESS,
        content_type=profile_ct,
        defaults={"name": "Can access the staff pages"},
    )

    shiftsignup_ct, _ = ContentType.objects.get_or_create(
        app_label="baljan", model="shiftsignup"
    )
    view_shiftsignup, _ = Permission.objects.get_or_create(
        codename=VIEW_SHIFTSIGNUP,
        content_type=shiftsignup_ct,
        defaults={"name": "Can view shift signup"},
    )

    return staff_access, view_shiftsignup


def forwards(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    staff_access, view_shiftsignup = _permissions(apps)

    for group_name in (
        settings.BOARD_GROUP,
        settings.WORKER_GROUP,
        settings.SUBSTITUTE_GROUP,
    ):
        group, _ = Group.objects.get_or_create(name=group_name)
        group.permissions.add(staff_access)

    # Without this, Semester.objects.visible_to_user() narrows the work planning
    # page down to semesters the user has shifts in, which is none of them for a
    # substitute.
    substitutes, _ = Group.objects.get_or_create(name=settings.SUBSTITUTE_GROUP)
    substitutes.permissions.add(view_shiftsignup)


def backwards(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    staff_access, view_shiftsignup = _permissions(apps)

    for group in Group.objects.filter(
        name__in=(
            settings.BOARD_GROUP,
            settings.WORKER_GROUP,
            settings.SUBSTITUTE_GROUP,
        )
    ):
        group.permissions.remove(staff_access)

    for group in Group.objects.filter(name=settings.SUBSTITUTE_GROUP):
        group.permissions.remove(view_shiftsignup)


class Migration(migrations.Migration):
    dependencies = [
        ("baljan", "0029_alter_profile_options"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
