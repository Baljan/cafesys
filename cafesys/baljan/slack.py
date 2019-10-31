from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from cafesys.baljan.models import Profile, Located
from logging import getLogger
from cafesys.baljan.phone import is_valid_phone_number

logger = getLogger(__name__)

def compile_slack_phone_message(phone_from, phone_to, status, location):
    """Compiles a message that can be posted to Slack after a call has been made
    """

    call_from_user = _query_user(phone_from)
    call_from = _format_caller(call_from_user, phone_from)

    call_to_user = _query_user(phone_to)
    call_to = _format_caller(call_to_user, phone_to)

    location_str = list(filter(lambda x: x[0] == location, Located.LOCATION_CHOICES))

    if not location_str:
        logger.error('Unknown café choice: %d' % (location,))
        location_str = 'Okänt café'
    else:
        location_str = location_str[0][1]

    fallback = 'Ett samtal till %s från %s har %s.' % (
        location_str,
        call_from,
        ('blivit taget av %s' if status == 'success' else 'missats av %s') % (call_to,),
    )

    fields = [
        {
            'title': 'Status',
            'value': 'Taget' if status == 'success' else 'Missat',
            'short': True
        },
        {
            'title': 'Café',
            'value': location_str,
            'short': True
        },
        {
            'title': 'Mottagare',
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
                'pretext': 'Nytt samtal från %s' % call_from,
                'fallback': fallback,
                'color': 'good' if status == 'success' else 'danger',
                'fields': fields
            }
        ]
    }


def compile_slack_sms_message(_sms_from, message):
    """Compile a message that can be posted to Slack after a SMS has been
    received
    """
    sms_from_user = _query_user(_sms_from)
    sms_from = _format_caller(sms_from_user, _sms_from)
    pretext = "Nytt SMS från %s" % (sms_from, )
    fallback =  "%s \n\"%s\"" % (pretext, message)

    return {
        'attachments': [
            {
                'pretext': pretext,
                'fallback': fallback,
                'color': 'warning',
                'text': message
            }
        ]
    }


def _query_user(phone):
    """
    Retrieves first name, last name and groups
    corresponding to a phone number from the database, if it exists.
    If multiple users have the same number, none will be queried
    """
    if not is_valid_phone_number(phone):
        return None

    try:
        user = Profile.objects.get(mobile_phone=_remove_area_code(phone)).user

        return {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'groups': [group.name if group.name[0] != '_' else
                       group.name[1:] for group in user.groups.all()]
        }
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        # Expected output for a lot of calls. Not an error.
        return None


def _format_caller(call_user, phone):
    """Formats caller information into a readable string"""
    # The phone number is private or not provided
    if not phone:
        return 'dolt nummer'

    if is_valid_phone_number(phone):
        # Set the phone number as a clickable link
        caller = '<tel:%s|%s>' % (phone, phone)
    else:
        caller = phone

    if call_user is not None:
        caller = '%s %s (%s)' % (
            call_user['first_name'],
            call_user['last_name'],
            caller
        )

    return caller


def _remove_area_code(phone):
    """
    Removes the area code (+46) from the given phone number
    and replaces it with 0
    """

    if not phone.startswith('+46'):
        return phone
    else:
        return '0' + phone[3:]
