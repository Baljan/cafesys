from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from cafesys.baljan.models import Profile


def compile_slack_message(phone_from, status):
    """Compiles a message that can be posted to Slack after a call has been made."""

    call_from_user = _query_user(phone_from)
    call_from = _format_caller(call_from_user, phone_from)

    fallback = 'Ett samtal från %s har %s.' % (
        call_from,
        'blivit taget' if status == 'success' else 'missats',
    )

    fields = [
        {
            'title': 'Status',
            'value': 'Taget' if status == 'success' else 'Missat',
            'short': True
        },
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

    # Set the phone number as a clickable link
    caller = '<tel:%s|%s>' % (phone, phone)

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
