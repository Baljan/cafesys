class AvailableShift:
    def __init__(self, date, location, span, exam_period, database_id):
        self.date = date
        self.location = location
        self.span = span
        self.exam_period = exam_period
        self.database_id = database_id

    def is_same_kind(self, o):
        return self.location == o.location \
               and self.span == o.span

    def __eq__(self, o):
        return self.location == o.location \
               and self.span == o.span \
               and self.exam_period == o.exam_period \
               and self.date == o.date

    def __str__(self):
        return '  ' + str(self.date) + ', ' + str(self.location) + ', ' + str(self.span) + ' (tenta-p = ' + str(self.exam_period) + ')'
