# -*- coding: utf-8 -*-
from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from .models import Good, Order, OrderGood
from .pseudogroups import was_worker, was_board
from .util import get_logger


log = get_logger('baljan.orders')
prelog = get_logger('baljan.orders.pre')
rebatelog = get_logger('baljan.orders.rebate')

class Processed(object):
    default_reason = _("The order was processed.")

    def __init__(self, preorder, reason=None):
        self.free = preorder.free
        self.rebate = preorder.rebate
        self.preorder = preorder
        self.reason = self.default_reason if reason is None else reason

    def accepted(self):
        raise NotImplementedError()

    def create_order_and_update_balance(self):
        raise NotImplementedError()


class Denied(Processed):
    default_reason = _("The order was denied.")

    def accepted(self):
        return False


class Accepted(Processed):
    default_reason = _("The order was accepted.")

    def accepted(self):
        return True

    def create_order_and_update_balance(self):
        preorder = self.preorder
        paid, cur = preorder.costcur(silent=True)
        order = Order(
            put_at=preorder.put_date,
            user=preorder.user,
            paid=paid,
            currency=cur,
            accepted=True)
        order.save()
        profile = preorder.user.profile
        profile.balance -= paid
        assert profile.balance_currency == cur
        profile.save()
        for good, count in preorder.goods:
            og = OrderGood(
                    order=order,
                    good=good,
                    count=count)
            og.save()
        log.info('created order %r' % order)


class PreOrder(object):
    class Error(Exception):
        pass

    @staticmethod
    def from_group(user, goods, put_date=None):
        if put_date is None:
            put_date = datetime.now()

        using_cls = DefaultPreOrder
        for member_func, cls in [
                (was_board, BoardPreOrder),
                (was_worker, WorkerPreOrder),
                ]:
            if member_func(user, put_date):
                using_cls = cls
                break

        prelog.info('using %r for %r (group)' % (using_cls, user))
        return using_cls(user, goods, put_date)

    @staticmethod
    def from_perms(user, goods, put_date=None):
        if put_date is None:
            put_date = datetime.now()
        else:
            prelog.warning('permission-based does not take date into account')

        using_cls = DefaultPreOrder
        for perm, cls in [
                ('baljan.free_coffee_unlimited', BoardPreOrder),
                ('baljan.free_coffee_with_cooldown', WorkerPreOrder),
                ]:
            if user.has_perm(perm):
                using_cls = cls
                break

        prelog.info('using %r for %r (perms)' % (using_cls, user))
        return using_cls(user, goods, put_date)

    def __init__(self, user, goods, put_date=None):
        """The goods argument must look like

            [(<Good object>, 1),
             (<Good object>, 2),
             (<Good object>, 1)]

        where the second value in the tuples are counts.
        """
        self.user = user
        self.goods = goods
        self.rebate = 0
        self.free = False

        if put_date is None:
            self.put_date = datetime.now()
        else:
            self.put_date = put_date

        self._profilize()

    def _profilize(self):
        pass

    def _raw_costcur(self):
        if len(self.goods) == 0:
            raise self.Error('no goods')

        cost = 0
        cur = self.goods[0][0].costcur(self.put_date)[1]
        for good, count in self.goods:
            this_cost, this_cur = good.costcur(self.put_date)
            if cur != this_cur:
                raise self.Error('goods must have the same currency')
            cost += this_cost * count
        return cost, cur

    def _polished_costcur(self, silent=False):
        """Override in subclasses to provide rebates for certain groups of
        users."""
        raise NotImplementedError()

    def costcur(self, silent=False):
        return self._polished_costcur(silent)


class FreePreOrder(PreOrder):
    def _profilize(self):
        self.free = True

    def _polished_costcur(self, silent=False):
        raw_cost, cur = self._raw_costcur()
        self.rebate = raw_cost
        if not silent:
            rebatelog.info('%d %s rebate for %r (free)' % (raw_cost, cur, self.user))
        return (0, cur)


class BoardPreOrder(PreOrder):
    def _profilize(self):
        self.free = True

    def _polished_costcur(self, silent=False):
        raw_cost, cur = self._raw_costcur()
        self.rebate = raw_cost
        if not silent:
            rebatelog.info('%d %s rebate for %r (board)' % (raw_cost, cur, self.user))
        return (0, cur)


class WorkerPreOrder(PreOrder):
    def _polished_costcur(self, silent=False):
        raw_cost, cur = self._raw_costcur()
        cooldown = settings.WORKER_COOLDOWN_SECONDS

        start, end = self.put_date - relativedelta(seconds=cooldown), self.put_date
        if not silent:
            log.debug('recent in interval %s-%s' % (start, end))
        recent_orders = Order.objects.filter(
                user=self.user,
                put_at__gte=start,
                put_at__lte=end,
        )
        if len(recent_orders):
            in_cooldown = False
            if not silent:
                log.debug('raw cost: %s %s' % (raw_cost, cur))
            for recent_order in recent_orders:
                paid, this_cur = recent_order.paid_costcur()
                if cur != this_cur:
                    if not silent:
                        log.error('not the same currency!!!')
                    in_cooldown = True
                    break
                if paid < raw_cost:
                    in_cooldown = True
                    break
        else:
            in_cooldown = False

        if in_cooldown:
            if not silent:
                rebatelog.info('no rebate because of cooldown for %r (worker)' % self.user)
            cost = raw_cost
            rebate = 0
        else:
            cost = max(0, raw_cost - settings.WORKER_MAX_COST_REDUCE)
            rebate = raw_cost - cost
            if not silent:
                rebatelog.info('%d %s rebate for %r (worker)' % (
                    rebate, cur, self.user))

        if rebate == raw_cost:
            self.free = True
        self.rebate = rebate
        return (cost, cur)


class DefaultPreOrder(PreOrder):
    def _polished_costcur(self, silent=False):
        if not silent:
            rebatelog.debug('no rebate for %r' % self.user)
        return self._raw_costcur()


class Clerk(object):

    def process(self, preorder):
        user = preorder.user
        profile = user.profile
        balance = profile.balance
        balance_currency = profile.balance_currency

        cost, cur = preorder.costcur()
        if cur != balance_currency:
            denied = Denied(preorder, _("Mixed currencies."))
            return denied
        elif balance < cost:
            return Denied(preorder, _("Insufficient funds."))
        else:
            accepted =  Accepted(preorder)
            accepted.create_order_and_update_balance()

            return accepted


def default_goods():
    coffee = Good.objects.get(
        title__exact=settings.DEFAULT_ORDER_NAME,
        description__exact=settings.DEFAULT_ORDER_DESC,
    )
    return [(coffee, 1)]


def default_preorder(user, when=None):
    """Return a default preorder for `user`. If `when` is ungiven, the current
    time will be set as the order date. `default_goods` is called internally.
    The type of the preorder is determined based on the user's permissions."""
    goods = default_goods()
    preorder = PreOrder.from_perms(user, goods, when)
    return preorder
