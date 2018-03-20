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
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from cafesys.baljan import planning
from cafesys.baljan.models import Shift, IncomingCallFallback, Profile

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


def _build_46elks_response(phone_numbers):
    """Builds a response message compatible with 46elks.com"""

    if phone_numbers:
        post_call_URL = 'http://baljan.org/baljan/post-call?call_to=%s' % urlquote(phone_numbers[0])

        data = {
            'connect': phone_numbers[0],
            'callerid': '+46766860043',
            'success': post_call_URL
        }

        busy = _build_46elks_response(phone_numbers[1:])
        if busy:
            data['timeout'] = '20'
            data['busy'] = busy
            data['failed'] = busy
        else:
            data['busy'] = post_call_URL
            data['failed'] = post_call_URL


        return data
    else:
        return {}


def compile_slack_message(phone_from, phone_to, status):
    """Compiles a message that can be posted to Slack after a call has been made"""

    call_from_user = _query_user(phone_from)
    call_from = _format_caller(call_from_user, phone_from)

    call_to = _format_caller(_query_user(phone_to), phone_to)

    fallback = '%s har %s ett samtal från %s.' % (
        call_to,
        'tagit' if status == 'success' else 'missat',
        call_from
        )

    fields = [
        {
            'title': 'Status',
            'value': 'Taget' if status == 'success' else 'Missat',
            'short': True
        },
        {
            'title': 'Av',
            'value': call_to,
            'short': False
        }
    ]

    if call_from_user is not None and call_from_user['groups']:
        groups = call_from_user['groups']

        groups_str = '%s %s tillhör %s: %s.' % (
            call_from_user['first_name'],
            call_from_user['last_name'],
            'grupperna' if len(groups) > 1 else 'gruppen',
            ', '.join(groups)
            )

        fallback += '\n\n%s' % groups_str
        fields += [
            {
                'title': 'Grupper',
                'value': groups_str,
                'short': False
            }
        ]


    return {
    'attachments': [
            {
            'pretext' : 'Nytt samtal från %s' % call_from,
            'fallback': fallback,
            'color'   : 'good' if status == 'success' else 'danger',
            'fields'  : fields
            }
        ]
    }


def _query_user(phone):
    """
    Retrieves first name, last name and groups
    corresponding to a phone number from the database, if it exists.
    If multiple users have the same number, none will be queried
    """

    try:
        user = Profile.objects.get(mobile_phone=_remove_area_code(phone)).user

        return {
        'first_name': user.first_name,
        'last_name' : user.last_name,
        'groups'    : [group.name if group.name[0] != '_' else \
                        group.name[1:] for group in user.groups.all()]
        }
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        # Expected output for a lot of calls. Not an error.
        return None


def _format_caller(call_user, phone):
    """Formats caller information into a readable string"""

    caller = phone

    if call_user is not None:
        caller = '%s %s (%s)' % (
        call_user['first_name'],
        call_user['last_name'],
        phone
        )

    return caller


def request_from_46elks(request):
    """
    Validates that a request comes from 46elks
    by looking at the clients IP-address
    """

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
        return phone[:len(phone)-len(PHONE_EXTENSION)]
    else:
        return phone


def _remove_area_code(phone):
    """
    Removes the area code (+46) from the given phone number
    and replaces it with 0
    """

    if not phone.startswith('+46'):
        return phone
    else:
        return '0' + phone[3:]


def is_valid_phone_number(phone):
    """
    Checks whether the given phone number is a valid swedish phone number.
    Works with both mobile (+46/0 + 9) and landline (+46/0 + 7-9) numbers
    """

    return match(r'^(\+46|0)[0-9]{7,9}$', phone) is not None
