import math

from cafesys.baljan.models import Shift, ShiftCombination
from django.db import transaction

from cafesys.baljan.workdist.available_shift import AvailableShift
from cafesys.baljan.workdist.shift_assigner import ShiftAssigner


class WorkdistAdapter:
    def __init__(self, semester):
        self.assigner = ShiftAssigner()
        self.semester = semester
        self.cur_shift_index = 1
        self.leftpad_format = '03'  # 3 numbers left-padded with zeroes

    @classmethod
    def recreate_shift_combinations(cls, semester):
        adapter = WorkdistAdapter(semester)
        adapter.load_from_db()
        adapter.assign_shifts()
        adapter.store_in_db()

    def load_from_db(self):
        shifts = self.semester.shift_set.order_by('when')
        for shift in shifts:
            self.add_shift_from_db(shift)

    def assign_shifts(self):
        self.assigner.assign()

    @transaction.atomic
    def store_in_db(self):
        combinations = self.assigner.shift_combinations

        # Pad to the same length as the number representing the shift combination count
        max_shift_id = max(1, len(combinations))
        self.leftpad_format = '0%d' % (math.ceil(math.log(max_shift_id, 10)))

        self.semester.shiftcombination_set.all().delete()

        for combination in combinations:
            self.add_combination_to_db(combination)

    def add_shift_from_db(self, model_shift):
        if model_shift.span == 1:
            # Don't assign workers to the lunch shift
            return

        if not model_shift.enabled:
            # Don't assign works to disabled shifts
            return

        shift = AvailableShift(
            date=model_shift.when,
            location=model_shift.location,
            span=model_shift.span,
            exam_period=model_shift.exam_period,
            database_id=model_shift.id
        )

        self.assigner.all_shifts.append(shift)

    def add_combination_to_db(self, tmp_comb):
        shifts = []
        for shift in tmp_comb.shifts:
            shifts.append(Shift.objects.get(id=shift.database_id))

        comb = ShiftCombination(
            semester=self.semester,
            label=format(self.cur_shift_index, self.leftpad_format)
        )
        comb.save()

        # We must save the ShiftCombination before we can assign the shifts
        comb.shifts = shifts
        comb.save()

        self.cur_shift_index += 1
