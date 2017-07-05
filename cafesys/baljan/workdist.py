# -*- coding: utf-8 -*-
import itertools
from logging import getLogger
from math import ceil, floor
from sys import maxsize

from django.contrib.auth.models import User
from django.db.models import Count
from pulp import GLPK_CMD
from pulp import LpProblem, LpMinimize, lpSum, LpVariable, LpStatus, LpInteger

from baljan.models import Shift, ShiftCombination

log = getLogger(__name__)

AM, LUNCH, PM = 0, 1, 2
SPANS = (AM, LUNCH, PM)

SHIFTS = ['morning', 'afternoon', 'exam']
COSTS = {
    'morning': 5.0,
    'afternoon': 4.75,
    'exam': 1.5 * 5.0,
}


def flatten(lol):
    return list(itertools.chain.from_iterable(lol))


class Ring(object):
    """http://code.activestate.com/recipes/52246-implementing-a-circular-data-structure-using-lists/
    """

    def __init__(self, l):
        if not len(l):
            raise Exception("ring must have at least one element")
        self._data = l

    def __repr__(self):
        return repr(self._data)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, i):
        return self._data[i]

    def turn(self):
        old_first = self._data.pop(0)
        self._data.append(old_first)

    def first(self):
        return self._data[0]

    def last(self):
        return self._data[-1]


class PairAlloc(object):
    CANNOT_TAKE = -1
    NOTHING_ASSIGNED = maxsize

    class Empty(Exception):
        pass

    def __init__(self, solution):
        self.shifts = []
        for pos, name in enumerate(SHIFTS):
            setattr(self, name, solution[pos])

    def tolist(self):
        return [getattr(self, n) for n in SHIFTS]

    def is_free(self):
        return self.sum() == 0

    def sum(self):
        return sum(self.tolist())

    def can_take(self, shift):
        can = self.assign_to(shift, dry=True) is not None
        return can

    def assign_to(self, shift, dry=False):
        """Assign pair to shift. Return `self` on success, or `None`."""
        try:
            if shift.exam_period:
                if self.exam <= 0:
                    raise self.Empty()
                else:
                    if not dry:
                        self.exam -= 1
            else:
                for span, field in zip([0, 2], SHIFTS[:-1]): # FIXME: brittle
                    if shift.span != span:
                        continue
                    avail = getattr(self, field)
                    if avail <= 0:
                        raise self.Empty()
                    else:
                        if not dry:
                            setattr(self, field, avail - 1)

            if not dry:
                self.shifts.append(shift)
            return self
        except self.Empty:
            return None

    def is_free(self):
        """True if all shifts are totally free, not a single sign-up."""
        return len([sh for sh in self.shifts if sh.signups().count() != 0]) == 0

    def is_taken(self):
        return not self.is_free()

    def taken_by(self):
        users = User.objects.filter(
                shiftsignup__shift__in=self.shifts).distinct().order_by(
                        'first_name', 'last_name')
        return users

    def distance_to(self, shift):
        if not self.can_take(shift):
            return self.CANNOT_TAKE
        if len(self.shifts) == 0:
            return self.NOTHING_ASSIGNED

        tigered = flatten(list(zip(
            self.shifts,
            [shift] * len(self.shifts)
        )))
        handicap = 0
        return handicap + abs(min(shift_distances(tigered)).days)

    def __str__(self):
        return "".join(str(self.tolist()).split())


def allocate_shifts_for_one_pair(work_pairs, avail_mornings, avail_afternoons, avail_exams):
    """
    `work_pairs` is the number of work pairs left to distribute, the other
    arguments are the number of shifts available.
    """
    mae = (avail_mornings, avail_afternoons, avail_exams)
    def _recurse(work_pairs, mae, grace=None):
        req = grace or 1.0

        demands = {
            'morning': mae[0],
            'afternoon': mae[1],
            'exam': mae[2],
        }
        total_avg = float(sum([demands[i] for i in SHIFTS])) / work_pairs
        total_low, total_high = floor(total_avg), ceil(total_avg)
        work_pair_count = work_pairs
        avgs = [float(demands[i]) / work_pair_count for i in SHIFTS]
        lows = [floor(a) for a in avgs]
        highs = [ceil(a) for a in avgs]

        target = req * total_avg * float(sum([COSTS[i] for i in SHIFTS])) / len(SHIFTS)

        prob = LpProblem("Work Distribution", LpMinimize)
        var_prefix = "shift"
        shift_vars = LpVariable.dicts(var_prefix, SHIFTS, 0, cat=LpInteger)
        prob += lpSum([COSTS[i] * shift_vars[i] for i in SHIFTS]), "cost of combination"
        prob += lpSum([COSTS[i] * shift_vars[i] for i in SHIFTS]) >= target, "not too good"
        prob += lpSum([shift_vars[i] for i in SHIFTS]) >= total_low, "low TOTAL"
        prob += lpSum([shift_vars[i] for i in SHIFTS]) <= total_high, "high TOTAL"

        for shift, low, high in zip(SHIFTS, lows, highs):
            prob += lpSum([shift_vars[shift]]) >= low, "low %s" % shift
            prob += lpSum([shift_vars[shift]]) <= high, "high %s" % shift

        prob.solve(GLPK_CMD(msg=0))

        if not LpStatus[prob.status] == 'Optimal':
            next_grace = req - 0.1
            assert 0.0 < next_grace
            return _recurse(work_pairs, mae, next_grace)

        new_mae = [0, 0, 0]
        solution = [0, 0, 0]
        for v in prob.variables():
            for pos, name in enumerate(SHIFTS):
                if v.name == "%s_%s" % (var_prefix, name):
                    solution[pos] = v.varValue
                    new_mae[pos] = mae[pos] - solution[pos]

        return (PairAlloc(solution), work_pairs - 1) + tuple(new_mae)

    return _recurse(work_pairs, mae)


def shifts_for_semester(sem):
    """
    Shifts in semester that are subject to work scheduling.
    """
    return Shift.objects.annotate(
        num_shiftsignups=Count('shiftsignup'),
    ).filter(
            semester=sem,
            enabled=True,
            num_shiftsignups=0,
    ).exclude(
        span=LUNCH,
    ).distinct()


def shift_distances(shifts):
    if len(shifts) < 2:
        return 0
    def dates(shifts):
        return [sh.when for sh in shifts]
    return map(lambda a, b: a-b, dates(shifts[:-1]), dates(shifts[1:]))


class PairAllocRing(object):
    class Empty(Exception):
        pass

    class Unsolvable(Exception):
        pass

    def __init__(self, allocs):
        self.ring = Ring(allocs)
        self._pair_pool = self.ring._data

    def max_distance_to(self, shift):
        dists = []
        for alloc in self._pair_pool:
            dist = alloc.distance_to(shift)
            if dist == PairAlloc.CANNOT_TAKE:
                pass
            else:
                if dist == PairAlloc.NOTHING_ASSIGNED:
                    return PairAlloc.NOTHING_ASSIGNED
                dists.append((alloc, dist))

        dists.sort(key=lambda x: x[1])
        if len(dists) == 0:
            raise self.Empty()
        return dists[-1][1]

    def turn_to_distance(self, dist, shift):
        firstdist = self.ring.first().distance_to(shift)
        assert dist != PairAlloc.CANNOT_TAKE

        pool = self._pair_pool
        bad = lambda a, b: a != b
        if dist != PairAlloc.NOTHING_ASSIGNED:
            bad = lambda a, b: a > b

        while self.ring.first() not in pool or bad(dist, firstdist):
            self.ring.turn()
            firstdist = self.ring.first().distance_to(shift)

        return self

    def assign_and_turn(self, shift, turn_to_max=True):
        """Assign shift to the first pair that can take it. Returns the
        pair alloc object that the shift was assigned to on success. Raises
        `self.Empty` if no pair can take the shift.
        """
        spins = 0
        allocs = len(self.ring)

        pairalloc = self.ring.first()
        max_dist = self.max_distance_to(shift)
        while not pairalloc.can_take(shift):
            if turn_to_max:
                dist = max_dist
                if max_dist != PairAlloc.NOTHING_ASSIGNED:
                    dist = max_dist * 0.5
                self.turn_to_distance(dist, shift)
            else:
                self.ring.turn()
            pairalloc = self.ring.first()
            spins += 1
            if turn_to_max:
                pass
            else:
                if spins == allocs:
                    log.error('work pair/shift mismatch', exc_auto=True)
                    raise self.Empty()

        pairalloc.assign_to(shift)
        self.ring.turn()
        return pairalloc

    def assign_all(self, shifts):
        pair_sums = []
        for pair in self.ring._data:
            pair_sums.append((pair, pair.sum()))
        pair_sums.sort(key=lambda x: x[1])
        top_sum = pair_sums[-1][1]

        pools = []
        for i in range(0, top_sum):
            pools.append([p for p, s in pair_sums if s==top_sum-i])
        pools.reverse()

        shifts_left = list(shifts)
        pair_shifts = {}
        for pool in pools:
            self._pair_pool = pool
            untreated = []
            for shift in shifts_left:
                try:
                    pair = self.assign_and_turn(shift)
                    if pair not in pair_shifts:
                        pair_shifts[pair] = []
                    pair_shifts[pair].append(shift)
                except self.Empty:
                    untreated.append(shift)
            shifts_left = untreated

        if len(shifts_left) != 0:
            msg = "could not place all shifts"
            log.error(msg)
            raise self.Unsolvable(msg)

        listed = []
        for pair, shifts in list(pair_shifts.items()):
            listed.append(pair)
        listed.sort(key=lambda x: x.label)
        self._pair_pool = self.ring._data
        return listed

    def all_free(self):
        return len([a for a in self.ring if a.is_free()]) == len(self.ring)


class LabeledPairAlloc(PairAlloc):
    @staticmethod
    def from_pairalloc(label, alloc):
        return LabeledPairAlloc(label, alloc.tolist())

    @staticmethod
    def from_db(comb):
        solution = [0, 0, 0]
        for i, span in ((0, AM), (1, PM)):
            solution[i] = comb.shifts.filter(span=span, exam_period=False).count()
        solution[2] = comb.shifts.filter(exam_period=True).count()
        lpa = LabeledPairAlloc(comb.label, solution)
        for sh in comb.shifts.order_by('when', 'span'):
            assert lpa.assign_to(sh) is not None
        return lpa

    def __init__(self, label, solution):
        super(LabeledPairAlloc, self).__init__(solution)
        self.label = label

    def save(self):
        shifts = self.shifts
        if not len(shifts):
            return

        sem = shifts[0].semester
        assert sum([1 if sh.semester == sem else 0 for sh in shifts]) \
                == len(shifts)

        comb, created = ShiftCombination.objects.get_or_create(
            semester=sem,
            label=self.label,
        )
        comb.shifts = shifts
        comb.save()

        verb = "saved"
        if created:
            verb = "created"
        log.info('%s %r' % (verb, comb))

    def __str__(self):
        return "%s=%s" % (self.label, super(LabeledPairAlloc, self).__str__())


class Scheduler(object):
    class Unsolvable(PairAllocRing.Unsolvable):
        pass

    def __init__(self, sem, target_pair_shift_count=3):
        self.sem = sem
        self.shifts = shifts_for_semester(sem).order_by('when', 'span')
        self.target_pair_shift_count = target_pair_shift_count

    def span_counts(self):
        """Returns a list of shift type counts. Order specified by the `SHIFTS`
        constant.
        """
        counts = []
        for span in SPANS:
            counts.append(self.shifts.filter(span=span, exam_period=False).count())
        m, a = counts[0], counts[-1] # skip lunch (overlaps for workers)
        e = self.shifts.filter(exam_period=True).count()
        return m, a, e

    def needed_pairs(self):
        assert self.target_pair_shift_count != 0
        return max(self.shifts.count() // self.target_pair_shift_count, 1)

    def pair_allocs(self):
        work_pairs = self.needed_pairs()
        m, a, e = self.span_counts()
        allocs = []
        label = 0
        while work_pairs != 0:
            alloc, work_pairs, m, a, e = allocate_shifts_for_one_pair(
                    work_pairs, m, a, e)
            allocs.append(LabeledPairAlloc.from_pairalloc("%02d" % label, alloc))
            label += 1
        return allocs

    def pair_alloc_ring(self):
        allocs = self.pair_allocs()
        return PairAllocRing(allocs)

    def pairs(self):
        alloc_ring = self.pair_alloc_ring()
        try:
            return alloc_ring.assign_all(self.shifts)
        except alloc_ring.Unsolvable:
            raise self.Unsolvable("could not assign all shifts")

    def _dbcombs(self):
        return ShiftCombination.objects.filter(semester=self.sem).order_by('label')

    def pairs_from_db(self):
        combs = self._dbcombs()
        if combs.count() == 0:
            self.save()
            combs = self._dbcombs()

        pairs = []
        for comb in combs:
            pairs.append(LabeledPairAlloc.from_db(comb))
        return pairs


    def clear_db(self):
        combs = self._dbcombs()
        combs.delete()
        log.info('cleared combinations for %r' % self.sem)


    def save(self, clear_db=True):
        if clear_db:
            self.clear_db()
        if len(self.shifts):
            pairs = self.pairs()
            for pair in pairs:
                pair.save()
            log.info('saved pairs for %r' % self.sem)
        else:
            log.info('no pairs to save for %r' % self.sem)
