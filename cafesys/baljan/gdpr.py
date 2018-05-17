from django.shortcuts import redirect
from django.urls import reverse, resolve

from cafesys.baljan.models import LegalConsent

AUTOMATIC_LIU_DETAILS = 'automatic_liu_details'


def legal_social_details(backend, strategy, details, response, user, *args, **kwargs):
    if not LegalConsent.is_present(user, AUTOMATIC_LIU_DETAILS):
        # This is the first time the user has logged in, or the user has not
        # approved any automatic storage of LiU details: generate a unique name.

        return {
            'details': {
                'username': generate_anonymous_username(user)
            }
        }
    else:
        # The user has given their consent to storing their personal details
        # given from LiU ADFS. If this is their first time logging in after
        # giving their consent we must explicitly change the username here,
        # as python-social-auth will not change this "protected" field themselves.

        details = {'details': dict(backend.get_user_details(response), **details)}
        username = details['details']['username']

        # Only update the username if it has changed!
        if user.username != username:
            user.username = details['details']['username']
            strategy.storage.user.changed(user)

        return details


def revoke_automatic_liu_details(user):
    LegalConsent.revoke(user, AUTOMATIC_LIU_DETAILS)
    user.username = generate_anonymous_username(user)
    user.first_name = ''
    user.last_name = ''
    user.email = ''
    user.profile.card_id = None

    user.profile.save()
    user.save()


def generate_anonymous_username(user):
    return 'User' + str(user.id)


class ConsentRedirectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated() and not user.profile.has_seen_consent:
            current_url = resolve(request.path_info).url_name
            if current_url != 'consent' and current_url != 'logout':
                return redirect(reverse('consent'))

        return self.get_response(request)
