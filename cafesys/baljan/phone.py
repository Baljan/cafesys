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
from logging import getLogger
from collections import Counter
from functools import wraps

from django.conf import settings
from django.core.exceptions import PermissionDenied, MultipleObjectsReturned, ObjectDoesNotExist

from cafesys.baljan.models import IncomingCallFallback, Located, OnCallDuty, ShiftSignup, User
from .util import week_dates, year_and_week

logger = getLogger(__name__)

tz = pytz.timezone(settings.TIME_ZONE)

# Mapping from working hours to shift indexes
DUTY_CALL_ROUTING = {
    (time(7, 0, 0, tzinfo=tz), time(10, 0, 0, tzinfo=tz)): 0,
    (time(10, 0, 0, tzinfo=tz), time(13, 0, 0, tzinfo=tz)): 1,
    (time(13, 0, 0, tzinfo=tz), time(18, 0, 0, tzinfo=tz)): 2,
}
WORKER_CALL_ROUTING = {
    (time(7, 0, 0, tzinfo=tz), time(12, 15, 0, tzinfo=tz)): 0,
    (time(12, 15, 0, tzinfo=tz), time(17, 0, 0, tzinfo=tz)): 2,
}

# IP addresses used by 46Elks
ELKS_IPS = ["176.10.154.199", "85.24.146.132", "185.39.146.243", "2001:9b0:2:902::199"]

# Map the keystrokes from IVR to a location
IVR_KEY_MAPPING = {
    # {ivr_key}: ({Location}, {call_workers}, {required_permission}) 
    1: (Located.KARALLEN, False, None),
    2: (Located.STH_VALLA, False, None),
    3: (Located.KARALLEN, True, "baljan.view_profile"),
    4: (Located.STH_VALLA, True, "baljan.view_profile")
}


# Utility functions
def _time_in_range(start, end, x):
    """Return true if x is in the range [start, end]"""

    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end

def _get_current_shift_span(routing):
    current_time = datetime.now(tz).time()
    current_span = None
    for time_range, shift_index in routing.items():
        if _time_in_range(time_range[0], time_range[1], current_time):
            current_span = shift_index

    return current_span


# Get lists of numbers

def _get_fallback_numbers():
    """Retrieves the list of fallback phone numbers from the database"""
    return [
        x.user.profile.mobile_phone
        for x in IncomingCallFallback.objects.all().select_related("user__profile")
    ]

def _get_week_duty_phone_numbers():
    """Returns the phone number for every staff on duty this week"""
    dates = week_dates(*year_and_week())
    oncall = OnCallDuty.objects.filter(shift__when__in=dates)

    user_ids = [x.user_id for x in oncall]
    # count occurrences of every user_id in oncall
    unique_user_ids_ordered = [x[0] for x in Counter(user_ids).most_common(3)]

    users = User.objects.filter(id__in=unique_user_ids_ordered).select_related(
        "profile"
    )

    users_sorted = sorted(users, key=lambda x: unique_user_ids_ordered.index(x.id))

    return [x.profile.mobile_phone for x in users_sorted]

def _get_current_duty_phone_numbers(location=Located.KARALLEN):
    """
    Returns the phone number for every staff on duty at the moment,
    prioritizing the given location, or None if outside office hours.
    """
    current_span = _get_current_shift_span(DUTY_CALL_ROUTING)

    # If outside on-call hours
    if current_span is None:
        return None

    # Get users who are currently on call (in any café)
    oncall = (
        OnCallDuty.objects.filter(shift__span=current_span, shift__when=date.today())
        .select_related("user__profile")
        .select_related("shift")
    )

    # Within working hours but nobody is on call (could for example be weekend)
    if len(oncall) == 0:
        return None

    # Sort oncall based on location id. Current location first.
    oncall_sorted = sorted(oncall, key=lambda x: abs(x.shift.location - location))

    return [x.user.profile.mobile_phone for x in oncall_sorted]

def _get_current_worker_phone_numbers(location=Located.KARALLEN):
    current_span = _get_current_shift_span(WORKER_CALL_ROUTING)
    
    if current_span is None:
        return None

    workers = (
        ShiftSignup.objects.filter(shift__span=current_span, shift__when=date.today(), shift__location=location)
        .select_related("user__profile")
        )

    if len(workers) == 0:
        return None

    return [signup.user.profile.mobile_phone for signup in workers]


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

    if phone[0] == "+":
        return phone
    else:
        return "+46" + phone[1:]


def request_from_46elks(request):
    """
    Validates that a request comes from 46elks
    by looking at the clients IP-address
    """

    if not settings.VERIFY_46ELKS_IP:
        return True

    client_IP = request.META.get("REMOTE_ADDR")
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if x_forwarded_for:
        client_IP = x_forwarded_for.split(",")[0]

    return client_IP in ELKS_IPS

def validate_46elks(function=None):
    @wraps(function)
    def wrap(request, *args, **kwargs):
            if request_from_46elks(request):
                return function(request, *args, **kwargs)
            raise PermissionDenied()
    return wrap

def get_from_user(function=None):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        from_number = request.POST.get('from', '')
        request.from_user = get_user_by_number(from_number)
        return function(request, *args, **kwargs)
            
    return wrap

def get_user_by_number(phone):
    if not is_valid_phone_number(phone):
        return None
    try:
        return User.objects.get(profile__mobile_phone=remove_area_code(phone))
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        return None

def is_valid_phone_number(phone):
    """Checks whether the given phone number is valid. Works with both numbers
    that begin with 0 or that are E.164 formatted. Assumes a fixed min- and max
    length of 4 and 14 respectively for the subscriber part of the number which
    may not be in line with the current standards.
    """

    return match(r"^(\+[0-9]{1,3}|0)[0-9]{4,14}$", phone) is not None

def remove_area_code(phone):
    """
    Removes the area code (+46) from the given phone number
    and replaces it with 0
    """

    if not phone.startswith("+46"):
        return phone
    else:
        return "0" + phone[3:]

def _compile_duty_number_list(location=Located.KARALLEN):
    phone_numbers = []
    current_duty_phone_numbers = _get_current_duty_phone_numbers(location=location)

    # Check if we are within office hours
    if current_duty_phone_numbers is not None:
        _append(phone_numbers, current_duty_phone_numbers)
        _append(phone_numbers, _get_week_duty_phone_numbers())

    # Always append the fallback numbers
    _append(phone_numbers, _get_fallback_numbers())

    return phone_numbers[:4]  # Never try more than four numbers


def _compile_worker_number_list(location=Located.KARALLEN):
    phone_numbers = []
    current_worker_numbers = _get_current_worker_phone_numbers(location=location)

    if current_worker_numbers:
        _append(phone_numbers, current_worker_numbers)
        return [",".join(phone_numbers)]
    return []

def _build_46elks_response(phone_numbers):
    """Builds a response message compatible with 46elks.com"""

    if phone_numbers:
        data = {
            "connect": phone_numbers[0],
            "callerid": "+46766860043",
        }

        busy = _build_46elks_response(phone_numbers[1:])
        if busy:
            data["timeout"] = "20"
            data["busy"] = busy
            data["failed"] = busy

        return data
    else:
        return {}


def compile_ivr_response(request):
    # TODO: reverse url
    next_url = request.build_absolute_uri("/incoming-call")
    audio_url = request.build_absolute_uri("/static/audio/phone/ivr.mp3")
    if settings.SOCIAL_AUTH_REDIRECT_IS_HTTPS:
        next_url = next_url.replace("http://", "https://")
        audio_url = audio_url.replace("http://", "https://")

    return {
        "ivr": audio_url,
        "digits": "1",
        "timeout": "10",
        "repeat": "3",
        "next": next_url,
    }


def compile_incoming_call_response(request):
    """
    Compiles a response message to an incoming call. The algorithm for this
    response is found in the file header.
    """

    ivr_key = request.POST.get("result", None)
    call_workers = False
    if ivr_key is not None:
        if ivr_key == "failed":
            why = request.POST["why"]
            logger.error("46elks IVR request failed, [why: %s]" % (why,))

            # We can't know which location the caller was trying to reach,
            # default route the call to Kårallen.
            location = Located.KARALLEN
        else:
            ivr_key = int(ivr_key[0])
                
            location, call_workers, required_permission = IVR_KEY_MAPPING.get(ivr_key, (None, None, None))

            user_has_permission = not required_permission or (required_permission and request.from_user and request.from_user.has_perm(required_permission))
            if location is None or not user_has_permission:
                # Replay IVR message if an invalid key is pressed, or insufficient permissions of caller
                return compile_ivr_response(request)
    else:
        # Route calls that did not go through the IVR to Kårallen
        location = Located.KARALLEN

    phone_numbers = _compile_worker_number_list(location=location) if call_workers else _compile_duty_number_list(location=location)
    response = _build_46elks_response(phone_numbers)

    if response:
        # Attach 'whenhangup' to top of call chain
         # TODO: reverse url
        hangup_url = request.build_absolute_uri("/post-call/{}".format(location))
        if settings.SOCIAL_AUTH_REDIRECT_IS_HTTPS:
            hangup_url = hangup_url.replace("http://", "https://")

        response["whenhangup"] = hangup_url

    return response
