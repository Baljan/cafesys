from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import RequestFactory, TestCase
from django.urls import resolve

from cafesys.baljan.actions import categories_and_actions
from cafesys.baljan.models import Semester


class StaffPagesTestCase(TestCase):
    """The Personal tab bar must not leak shift sign-up to substitutes."""

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
        user.groups.set(
            [Group.objects.get_or_create(name=name)[0] for name in group_names]
        )

        request = RequestFactory().get("/staff")
        request.user = User.objects.get(pk=user.pk)  # drop the permission cache
        request.resolver_match = resolve("/staff")

        links, pages = categories_and_actions(request)
        return [page.text for page in pages], [link.text for link in links]

    def test_substitute_sees_info_and_work_planning_only(self):
        pages, links = self.tabs_for([settings.SUBSTITUTE_GROUP])

        self.assertEqual(pages, ["Info", "Jobbplanering"])
        self.assertIn("Jobbarguide Baljan", links)

    def test_substitute_cannot_reach_job_opening_signup(self):
        pages, _ = self.tabs_for([settings.SUBSTITUTE_GROUP])

        self.assertNotIn("Jobbpass VT2027", pages)

    def test_worker_keeps_job_opening_signup(self):
        pages, _ = self.tabs_for([settings.WORKER_GROUP])

        self.assertEqual(
            pages, ["Info", "Jobbpass VT2027", "Jobbplanering", "Personer och grupper"]
        )

    def test_worker_who_is_also_substitute_is_treated_as_a_worker(self):
        pages, _ = self.tabs_for([settings.WORKER_GROUP, settings.SUBSTITUTE_GROUP])

        self.assertIn("Jobbpass VT2027", pages)
        self.assertIn("Personer och grupper", pages)

    def test_user_without_a_group_is_unaffected(self):
        pages, links = self.tabs_for()

        self.assertEqual(pages, ["Info", "Jobbpass VT2027"])
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
                "Veckoplanering",
            ],
        )
