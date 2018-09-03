"""
Functionality related to provide the virtual duty phone for Baljan.

Incoming calls are first routed to the current staff on duty. If they are
busy the call will be routed to the other staff that is on duty the current
week. If both members on duty are busy, or if a call is made outside of
office hours, the call will be routed to a backup list stored in the database.
"""
import pytz
from re import match
from datetime import date, datetime, time

from django.conf import settings
from django.utils.http import urlquote

from cafesys.baljan import planning
from cafesys.baljan.models import Shift, IncomingCallFallback

tz = pytz.timezone(settings.TIME_ZONE)

# Mapping from office hours to shift indexes
DUTY_CALL_ROUTING = {
    (time(7, 0, 0, tzinfo=tz), time(12, 0, 0, tzinfo=tz)): 0,
    (time(12, 0, 0, tzinfo=tz), time(13, 0, 0, tzinfo=tz)): 1,
    (time(13, 0, 0, tzinfo=tz), time(18, 0, 0, tzinfo=tz)): 2,
}

# IP addresses used by 46Elks
ELKS_IPS = ['62.109.57.12', '212.112.190.140', '176.10.154.199', '2001:9b0:2:902::199']

# Extension that is added to numbers calling Baljans 013-number
PHONE_EXTENSION = '239927'

# Maximum length of a phone number (+46 + 9 digits)
MAX_PHONE_LENGTH = 12


def _get_fallback_numbers():
    """Retrieves the list of fallback phone numbers from the database"""

    return [x.user.profile.mobile_phone for x in IncomingCallFallback.objects.all()]


def _get_current_duty_phone_numbers():
    """
    Returns the phone number for every staff on duty at the moment,
    or None if outside office hours.
    """

    current_time = datetime.now(tz).time()
    shifts_today = Shift.objects.filter(when=date.today())

    for time_range, shift_index in DUTY_CALL_ROUTING.items():
        if _time_in_range(time_range[0], time_range[1], current_time):
            current_shift = shifts_today.filter(span=shift_index).first()
            if current_shift is not None:
                on_callduty = current_shift.on_callduty()
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
    elif element:
        element = _format_phone(element)
        if element not in lst:
            lst.append(element)


def _format_phone(phone):
    """Makes sure that the number starts with an area code (needed by 46elks API)"""

    if phone[0] == '+':
        return phone
    else:
        return '+46' + phone[1:]


def request_from_46elks(request):
    """
    Validates that a request comes from 46elks
    by looking at the clients IP-address
    """

    if not settings.VERIFY_46ELKS_IP:
        return True

    client_IP = request.META.get('REMOTE_ADDR')
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        client_IP = x_forwarded_for.split(',')[0]

    return client_IP in ELKS_IPS


def remove_extension(phone):
    """
    Removes the extension that is added to numbers
    calling Baljans 013-number
    """

    if len(phone) > MAX_PHONE_LENGTH and phone.endswith(PHONE_EXTENSION):
        return phone[:len(phone) - len(PHONE_EXTENSION)]
    else:
        return phone


def is_valid_phone_number(phone):
    """
    Checks whether the given phone number is a valid swedish phone number.
    Works with both mobile (+46/0 + 9) and landline (+46/0 + 7-9) numbers
    """

    return match(r'^(\+46|0)[0-9]{7,9}$', phone) is not None


def _compile_number_list():
    phone_numbers = []
    current_duty_phone_numbers = _get_current_duty_phone_numbers()

    # Check if we are within office hours
    if current_duty_phone_numbers is not None:
        _append(phone_numbers, current_duty_phone_numbers)
        _append(phone_numbers, _get_week_duty_phone_numbers())

    # Always append the fallback numbers
    _append(phone_numbers, _get_fallback_numbers())

    return phone_numbers


def _build_46elks_response(phone_numbers):
    """Builds a response message compatible with 46elks.com"""

    if phone_numbers:
        data = {
            'connect': phone_numbers[0],
            'callerid': '+46766860043',
        }

        busy = _build_46elks_response(phone_numbers[1:])
        if busy:
            data['timeout'] = '20'
            data['busy'] = busy
            data['failed'] = busy

        return data
    else:
        return {}


def compile_incoming_call_response():
    """
    Compiles a response message to an incoming call. The algorithm for this
    response is found in the file header.
    """
    phone_numbers = _compile_number_list()
    response = _build_46elks_response(phone_numbers)
    
    if response:
        # Attach 'whenhangup' to top of call chain
        response['whenhangup'] = request.build_absolute_uri('/baljan/post-call')

    return response
