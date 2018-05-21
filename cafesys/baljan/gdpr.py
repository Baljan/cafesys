from django.shortcuts import redirect
from django.urls import reverse, resolve

from cafesys.baljan.models import LegalConsent

AUTOMATIC_LIU_DETAILS = 'automatic_liu_details'
AUTOMATIC_CARD_NR = 'automatic_card_number'
CACHE_CARD_NR = 'cache_card_number'

POLICIES = {
    AUTOMATIC_LIU_DETAILS: {
        'name': 'Automatisk hämtning av LiU-detaljer',
        'versions': ['/static/contract.pdf', '/static/guide.pdf']
    },
    AUTOMATIC_CARD_NR: {
        'name': 'Automatisk hämtning av LiU-kortnummer',
        'versions': ['/static/contract.pdf']
    },
    CACHE_CARD_NR: {
        'name': "Cachning av LiU-kortnummer",
        'versions': ['/static/contract.pdf']
    }
}


def latest_policy_version(policy_name):
    return len(POLICIES[policy_name]['versions'])


def get_policies(user):
    """
    Generates a dictionary of policies that the user has either
    consented to or not consented to. Only the latest policies
    that are not consented are included while all policies that
    have been consented and not revoked are always included.
    """
    consented_policies = LegalConsent.objects.filter(user=user, revoked=False)

    policies = {
        'consented': {},
        'not_consented': {}
    }
    for policy in consented_policies:
        policies['consented'][policy.policy_name] = {
            'name': POLICIES[policy.policy_name]['name'],
            'date_of_consent': policy.time_of_consent,
            'version': policy.policy_version,
            'pdf': POLICIES[policy.policy_name]['versions'][policy.policy_version - 1]
        }

    for policy in POLICIES:
        if not (policy in policies['consented'] and
                policies['consented'][policy]['version'] == latest_policy_version(policy)):
            policies['not_consented'][policy] = {
                'name': POLICIES[policy]['name'],
                'date_of_consent': '-',
                'version': latest_policy_version(policy),
                'pdf': POLICIES[policy]['versions'][-1]
            }

    return policies


def revoke_policy(user, policy_name):
    if policy_name == AUTOMATIC_LIU_DETAILS:
        revoke_automatic_liu_details(user)
    else:
        LegalConsent.revoke(user, policy_name)


def consent_to_policy(user, policy_name, policy_version):
    LegalConsent.create(user, policy_name, policy_version)


def legal_social_details(backend, strategy, details, response, user, *args, **kwargs):
    if not LegalConsent.is_present(user, AUTOMATIC_LIU_DETAILS):
        # This is the first time the user has logged in, or the user has not
        # approved any automatic storage of LiU details: generate a unique name.

        # Note that we must pass on the e-mail address here! This is needed for the step
        #   social_core.pipeline.social_auth.associate_by_email
        #
        # When recruiting new workers for the next semester we have the possibility to
        # automatically import users from Kobra, and in order to correctly tie them to
        # the correct account when logging in they need an email-value in the details
        # dictionary. We will later reset this value in the step
        #   cafesys.baljan.gdpr.clean_social_details
        #
        return {
            'details': {
                'username': generate_anonymous_username(user),
                'email': backend.get_user_details(response)['email']
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


def clean_social_details(details, user, *args, **kwargs):
    if not LegalConsent.is_present(user, AUTOMATIC_LIU_DETAILS):
        # We have temporarily set an e-mail address that we aren't allowed
        # to persistently store, so we clear it and continue.

        details['email'] = ''
        return {'details': details}

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
