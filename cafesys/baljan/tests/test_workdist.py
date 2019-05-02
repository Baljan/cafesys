import math

from django.test import TestCase

from cafesys.baljan.workdist.available_shift import AvailableShift
from cafesys.baljan.workdist.shift_assigner import ShiftAssigner


class WorkdistTestCase(TestCase):
    def test_fall_semester(self):
        assigner = ShiftAssigner()
        generate_shifts(assigner, [10, 34, 10, 34], prefix='Date ')
        assigner.assign()

        self.assertShiftAssignmentIsReasonable(assigner)

    def test_spring_semester(self):
        assigner = ShiftAssigner()
        generate_shifts(assigner, [10, 34, 10, 34, 10], prefix='Date ')
        assigner.assign()

        self.assertShiftAssignmentIsReasonable(assigner)

    def assertShiftAssignmentIsReasonable(self, assigner):
        self.assertPairDoesNotWorkTwiceOnSameDay(assigner.shift_combinations)
        self.assertMinimalAmountInExamPeriod(assigner.shift_combinations)
        self.assertEvenDistributionOfShiftTypes(assigner.shift_combinations)
        self.assertEvenDistributionOfNumberOfShifts(assigner.shift_combinations)
        self.assertEvenDistributionOverTheSemester(assigner.shift_combinations)

    # Inte samma dag
    def assertPairDoesNotWorkTwiceOnSameDay(self, shift_combinations):
        for combination in shift_combinations:
            dates = []
            for shift in combination.shifts:
                self.assertNotIn(shift.date, dates)
                dates += shift.date

    # Minimalt antal på tenta-p
    def assertMinimalAmountInExamPeriod(self, shift_combinations):
        num_combinations = len(shift_combinations)
        total_exam_shifts = 0
        max_exam_shifts_per_comb = 0

        for combination in shift_combinations:
            num_exam_shifts = 0
            for shift in combination.shifts:
                if shift.exam_period:
                    total_exam_shifts += 1
                    num_exam_shifts += 1

            if num_exam_shifts > max_exam_shifts_per_comb:
                max_exam_shifts_per_comb = num_exam_shifts

        theoretical_max = math.ceil(total_exam_shifts / num_combinations)
        self.assertFalse(max_exam_shifts_per_comb > theoretical_max)

    # En av varje shift-typ (FM Kår, FM STH, EM Kår, EM STH)
    def assertEvenDistributionOfShiftTypes(self, shift_combinations):
        max_num_same = 0

        for combination in shift_combinations:
            num_same = 0
            for shift in combination.shifts:
                for other_shift in combination.shifts:
                    if shift != other_shift:
                        if shift.is_same_kind(other_shift):
                            num_same += 1

            if num_same > max_num_same:
                max_num_same = num_same

        # It should be possible to distribute the shifts so that there are no more than 2 shifts of the same kind
        self.assertLessEqual(max_num_same, 2)

    # Jämnt antal (alla får 4 t.ex.)
    def assertEvenDistributionOfNumberOfShifts(self, shift_combinations):
        min_shift_count = None
        max_shift_count = None

        for combination in shift_combinations:
            shift_count = len(combination.shifts)

            if min_shift_count is None or shift_count < min_shift_count:
                min_shift_count = shift_count

            if max_shift_count is None or shift_count > max_shift_count:
                max_shift_count = shift_count

        # The min and max amount may only differ by one shift
        self.assertLessEqual(max_shift_count - min_shift_count, 1)

    # Bra distribution av tid
    def assertEvenDistributionOverTheSemester(self, shift_combinations):
        # TODO: Implement
        pass


def generate_shifts(instance, num_dates_list, karall=True, sth=True, prefix='Date 0'):
    exam_period = False
    date_index = 0
    for num_dates in num_dates_list:
        exam_period = not exam_period

        for i in range(num_dates):
            date = prefix + str(date_index)
            date_index += 1

            # NOTE: The shifts MUST be created in this order (with alternating location)

            if karall:
                instance.all_shifts.append(AvailableShift(date, 'Kårallen', 'Morning', exam_period))

            if sth:
                instance.all_shifts.append(AvailableShift(date, 'Studenthus Valla', 'Morning', exam_period))

            if karall:
                instance.all_shifts.append(AvailableShift(date, 'Kårallen', 'Afternoon', exam_period))

            if sth:
                instance.all_shifts.append(AvailableShift(date, 'Studenthus Valla', 'Afternoon', exam_period))
