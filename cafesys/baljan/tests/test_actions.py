from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.test import RequestFactory, TestCase
from django.urls import resolve

from cafesys.baljan.actions import categories_and_actions
from cafesys.baljan.models import Semester


class StaffPagesTestCase(TestCase):
    """Only users allowed to sign up see the job opening sign-up tab."""

    @classmethod
    def setUpTestData(cls):
        start = date.today() + timedelta(days=30)
        cls.semester = Semester.objects.create(
            name="VT2027",
            start=start,
            end=start + timedelta(days=100),
            signup_possible=True,
        )

    def tabs_for(self, group_names=(), superuser=False):
        user = User.objects.create(username="tester", is_superuser=superuser)
        groups = [Group.objects.get_or_create(name=name)[0] for name in group_names]
        signup = Permission.objects.get(codename="self_and_friend_signup")
        for group in groups:
            if group.name in (settings.WORKER_GROUP, settings.BOARD_GROUP):
                group.permissions.add(signup)
        user.groups.set(groups)

        request = RequestFactory().get("/staff")
        request.user = User.objects.get(pk=user.pk)  # drop the permission cache
        request.resolver_match = resolve("/staff")

        links, pages = categories_and_actions(request)
        return [page.text for page in pages], [link.text for link in links]

    def test_worker_keeps_job_opening_signup(self):
        pages, _ = self.tabs_for([settings.WORKER_GROUP])

        self.assertEqual(
            pages, ["Info", "Jobbpass VT2027", "Jobbplanering", "Personer och grupper"]
        )

    def test_user_without_a_group_cannot_reach_job_opening_signup(self):
        pages, links = self.tabs_for()

        self.assertEqual(pages, ["Info"])
        self.assertEqual(links, [])

    def test_board_inherits_the_worker_pages(self):
        pages, _ = self.tabs_for([settings.BOARD_GROUP])

        self.assertEqual(
            pages,
            [
                "Info",
                "Jobbpass VT2027",
                "Jobbplanering",
                "Personer och grupper",
                "Jobbsläpp VT2027",
                "Beställningar",
                "Veckoplanering",
            ],
        )
