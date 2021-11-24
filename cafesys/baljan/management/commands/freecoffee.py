# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from ...models import Group


class Command(BaseCommand):
    help = "Shows all groups with free coffee permission."

    def handle(self, **options):
        self.stdout.write("")

        for perm in ["free_coffee_unlimited", "free_coffee_with_cooldown"]:
            groups = [x.name for x in Group.objects.filter(permissions__codename=perm)]

            self.stdout.write(f"Groups with free coffee from permission: {perm}")

            for group in groups:
                self.stdout.write(f"  {group}")

            self.stdout.write("")
