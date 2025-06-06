from datetime import date

from django.test import TestCase

from cafesys.baljan.models import Semester
from cafesys.baljan.workdist.workdist_adapter import WorkdistAdapter


class WorkdistAdapterTestCase(TestCase):
    def test_basic_functionality(self):
        semester = Semester(
            start=date(year=2019, month=8, day=19),
            end=date(year=2019, month=12, day=20),
            name="HT2019",
        )
        semester.save()

        adapter = WorkdistAdapter(semester)
        adapter.load_from_db()
        adapter.assign_shifts()
        adapter.store_in_db()
