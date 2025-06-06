class TemporaryShiftCombination:
    def __init__(self, index):
        self.index = index
        self.shifts = []

    def number_of_shifts_in_exam_period(self):
        return len([x for x in self.shifts if x.exam_period])

    def contains_shift_of_kind(self, other_shift):
        for shift in self.shifts:
            if shift.is_same_kind(other_shift):
                return True

        return False

    def contains_shift_at_same_day(self, other_shift):
        for shift in self.shifts:
            if shift.date == other_shift.date:
                return True

        return False

    def __str__(self):
        return (
            "ShiftCombination #"
            + str(id(self))
            + "\n"
            + "\n".join(map(lambda x: str(x), self.shifts))
        )
