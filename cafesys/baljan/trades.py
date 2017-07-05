# -*- coding: utf-8 -*-
from datetime import date

from django.db.models import Q

from baljan.models import ShiftSignup, Shift, TradeRequest


def _requests(user, wanted):
    if wanted:
        su = 'wanted_signup'
        su_other = 'offered_signup'
    else:
        su = 'offered_signup'
        su_other = 'wanted_signup'

    order = (
            'wanted_signup__shift__when',
            'offered_signup__shift__when',
            )
    today = date.today()
    filt = {
            "%s__user" % su: user,
            'wanted_signup__shift__when__gte': today,
            'offered_signup__shift__when__gte': today,
            }
    return TradeRequest.objects.filter(**filt).distinct().order_by(*order)

def requests_sent_to(user):
    return _requests(user, wanted=True)

def requests_sent_by(user):
    return _requests(user, wanted=False)


class TakeRequest(object):
    """Utility class for managing requests to take shifts. This class is not
    used for confirming requests. To accept requests, use `requests_sent_to` and
    `requests_sent_by` and `TradeRequest.accept` or `TradeRequest.deny`.
    """

    class Error(Exception):
        pass
    class BadOffer(Error):
        pass
    class BadSignup(Error):
        pass
    class BadUser(Error):
        pass
    class DoubleSignup(BadUser):
        pass

    def __init__(self, signup, requester, offered_signups=None):
        if not requester.has_perm('baljan.self_and_friend_signup'):
            raise self.BadUser()
        if requester == signup.user:
            raise self.DoubleSignup()
        if ShiftSignup.objects.filter( # prevent double bookings
                shift=signup.shift,
                user=requester):
            raise self.DoubleSignup()
        if not signup.tradable:
            raise self.BadSignup()
        self.signup = signup
        self.shift = self.signup.shift
        self.requester = requester
        self.offered_signups = []
        if offered_signups is not None:
            for ofs in offered_signups:
                self.add_offer(ofs)

    def add_offer(self, offered_signup):
        """
        Add offer to offered_signups. This method raises BadOffer if the offer
        is invalid. The method also makes sure that no duplicates exist in the
        offers. Returns the TakeRequest instance.
        """
        if self.valid_offer(offered_signup):
            if offered_signup in self.offered_signups:
                return self # do nothing

            self.offered_signups.append(offered_signup)
            return self
        else:
            raise self.BadOffer()

    def valid_offer(self, offered_signup):
        """Returns True if offered_signup is valid. """
        return offered_signup in self.can_offer()

    def can_offer(self):
        """Returns all possible signup offers."""
        double_shifts = Shift.objects.filter(shiftsignup__user=self.signup.user)
        user_signups = ShiftSignup.objects.filter(
                user=self.requester,
                shift__when__gte=date.today()).exclude(
                Q(shift=self.shift) | Q(shift__in=double_shifts))
        return user_signups

    def save(self):
        # Remove and add trade requests.
        current_trs = self._current_trade_requests()
        for tr in current_trs:
            if not tr.offered_signup in self.offered_signups:
                tr.delete()

        for ofs in self.offered_signups:
            tr, created = TradeRequest.objects.get_or_create(
                    wanted_signup=self.signup,
                    offered_signup=ofs)

    def _current_trade_requests(self):
        return TradeRequest.objects.filter(
                wanted_signup=self.signup,
                offered_signup__user=self.requester)

    def load(self):
        trs = self._current_trade_requests()
        for tr in trs:
            self.add_offer(tr.offered_signup)
