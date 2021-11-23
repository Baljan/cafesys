import math

from cafesys.baljan.workdist.temporary_shift_combination import (
    TemporaryShiftCombination,
)


class ShiftAssigner:
    def __init__(self, shifts_per_combination=4):
        self.all_shifts = []
        self.shift_combinations = []
        self.shifts_per_combination = shifts_per_combination

    def assign_to_best_combination(self, shift):
        # Always assign to combinations with the fewest number of shifts
        # already assigned
        used_combinations = self.select_from_smallest_number_of(
            self.shift_combinations, lambda x: len(x.shifts)
        )

        if shift.exam_period:
            # Don't assign more than one exam period shift before every
            # combination has at least one
            used_combinations = (
                self.select_combinations_with_smallest_number_of_exam_period_shifts(
                    used_combinations
                )
            )

        self.assign_to_best_combination_in_list(shift, used_combinations)

    def assign_to_best_combination_in_list(self, shift, combinations):
        # 1. Try to assign with exact match
        for comb in combinations:
            if not comb.contains_shift_of_kind(shift):
                self.assign_shift_to_combination(shift, comb)
                return

        # 2. Try to assign with other day
        for comb in combinations:
            if not comb.contains_shift_at_same_day(shift):
                self.assign_shift_to_combination(shift, comb)
                print("Assigned sub-optimal shift (" + str(id(comb)) + ")")
                return

        # 3. Indicate failure (should never happen)
        raise Exception(
            "Impossible to assign shifts without assigning two shifts at the same day"
        )

    def assign_shift_to_combination(self, shift, comb):
        # Move combination to end of list to get an even distribution of dates
        self.shift_combinations.remove(comb)
        self.shift_combinations.append(comb)

        comb.shifts.append(shift)

    def select_combinations_with_smallest_number_of_exam_period_shifts(
        self, combinations
    ):
        return self.select_from_smallest_number_of(
            combinations, lambda x: x.number_of_shifts_in_exam_period()
        )

    def select_from_smallest_number_of(self, collection, f):
        segments = {}
        for item in collection:
            num = f(item)

            segment = segments.get(num)
            if segment is None:
                segment = []
                segments[num] = segment

            segment.append(item)

        return segments[min(segments.keys())]

    def assign(self):
        num_combinations = math.ceil(
            len(self.all_shifts) / self.shifts_per_combination)

        for i in range(num_combinations):
            self.shift_combinations.append(TemporaryShiftCombination(i))

        for shift in self.all_shifts:
            self.assign_to_best_combination(shift)
