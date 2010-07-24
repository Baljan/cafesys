def keys(request):
    if request.user.is_authenticated():
        student = request.user.get_profile()
        return {
            'student': student,
            'is_regular': student.is_regular(),
            'is_worker': student.is_worker(),
            'is_board_member': student.is_board_member(),
            'student_shifts': student.scheduled_for(),
        }
    else:
        return {
            'student': None,
            'is_regular': False,
            'is_worker': False,
            'is_board_member': False,
            'student_shifts': [],
        }

def _is(request, what):
    info = keys(request)
    return info[what]

def is_regular(request):
    return _is(request, 'is_regular')

def is_worker(request):
    return _is(request, 'is_worker')

def is_board_member(request):
    return _is(request, 'is_board_member')
