"""
Functionality related to provide the virtual duty phone for Baljan.

Incoming calls are first routed to the current staff on duty. If they are
busy the call will be routed to the other staff that is on duty the current
week. If both members on duty are busy, or if a call is made outside of
office hours, the call will be routed to a backup list stored in the database.
"""
from datetime import datetime, date, time

from cafesys.baljan import planning
from cafesys.baljan.models import Shift, IncomingCallFallback

# Mapping from office hours to shift indexes
DUTY_CALL_ROUTING = {
    (time(7, 0, 0), time(12, 0, 0)): 0,
    (time(12, 0, 0), time(13, 0, 0)): 1,
    (time(13, 0, 0), time(18, 0, 0)): 2,
}


def compile_incoming_call_response():
    """
    Compiles a response message to an incoming call. The algorithm for this
    response is found in the file header.
    """

    phone_numbers = []
    current_duty_phone_numbers = _get_current_duty_phone_numbers()

    # Check if we are within office hours
    if current_duty_phone_numbers is not None:
        _append(phone_numbers, current_duty_phone_numbers)
        _append(phone_numbers, _get_week_duty_phone_numbers())

    # Always append the fallback numbers
    _append(phone_numbers, _get_fallback_numbers())

    return _build_46elks_response(phone_numbers)


def _get_fallback_numbers():
    """Retrieves the list of fallback phone numbers from the database"""

    return [x.user.profile.mobile_phone for x in IncomingCallFallback.objects.all()]


def _get_current_duty_phone_numbers():
    """
    Returns the phone number for every staff on duty at the moment,
    or None if outside office hours.
    """

    current_time = datetime.now().time()
    shifts_today = Shift.objects.filter(when=date.today())

    for time_range, shift_index in DUTY_CALL_ROUTING.items():
        if _time_in_range(time_range[0], time_range[1], current_time):
            on_callduty = shifts_today.filter(span=shift_index).first().on_callduty()
            return [x.profile.mobile_phone for x in on_callduty]

    return None


def _get_week_duty_phone_numbers():
    """Returns the phone number for every staff on duty this week"""

    plan = planning.BoardWeek.current_week()
    on_callduty = [item for sublist in plan.oncall() for item in sublist]

    return [x.profile.mobile_phone for x in on_callduty]


def _time_in_range(start, end, x):
    """Return true if x is in the range [start, end]"""

    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end


def _append(lst, element):
    """Appends the phone number of list of phone numbers to the given list lst"""

    if isinstance(element, list):
        for e in element:
            _append(lst, e)
    elif element is not None:
        element = _format_phone(element)
        if element not in lst:
            lst.append(element)


def _format_phone(phone):
    """Makes sure that the number starts with an area code (needed by 46elks API)"""

    if phone[0] == '+':
        return phone
    else:
        return '+46' + phone[1:]


def _build_46elks_response(phone_numbers):
    """Builds a response message compatible with 46elks.com"""

    if phone_numbers:
        data = {
            'connect': phone_numbers[0]
        }

        busy = _build_46elks_response(phone_numbers[1:])
        if busy:
            data['busy'] = busy

        return data
    else:
        return {}
