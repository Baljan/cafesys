# -*- coding: utf-8 -*-
from pulp import LpProblem, LpMinimize, lpSum, LpVariable, LpStatus, LpInteger
from pulp import allcombinations, value
from math import floor, ceil

work_pairs = range(20)

SHIFTS = ['morning', 'afternoon', 'exam']
COSTS = {
    'morning': 5.0,
    'afternoon': 4.75,
    'exam': 1.5 * 5.0,
}

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
        shift_vars = LpVariable.dicts("Shift", SHIFTS, 0, cat=LpInteger)
        prob += lpSum([COSTS[i] * shift_vars[i] for i in SHIFTS]), "cost of combination"
        prob += lpSum([COSTS[i] * shift_vars[i] for i in SHIFTS]) >= target, "not too good"
        prob += lpSum([shift_vars[i] for i in SHIFTS]) >= total_low, "low TOTAL"
        prob += lpSum([shift_vars[i] for i in SHIFTS]) <= total_high, "high TOTAL"

        for shift, low, high in zip(SHIFTS, lows, highs):
            prob += lpSum([shift_vars[shift]]) >= low, "low %s" % shift
            prob += lpSum([shift_vars[shift]]) <= high, "high %s" % shift

        prob.solve()

        if LpStatus[prob.status] == 'Undefined':
            next_grace = req - 0.1
            assert 0.0 < next_grace 
            return _recurse(work_pairs, mae, next_grace)
        
        new_mae = [0, 0, 0]
        for v in prob.variables():
            for pos, name in [
                    (0, 'morning'),
                    (1, 'afternoon'),
                    (2, 'exam'),
                    ]:
                if v.name == 'Shift_' + name:
                    new_mae[pos] = mae[pos] - v.varValue

        return (prob, work_pairs - 1) + tuple(new_mae)
    
    return _recurse(work_pairs, mae)


if __name__ == '__main__':
    solutions = []
    work_pairs = 23
    m, a, e = 43, 37, 11
    while work_pairs != 0:
        prob, work_pairs, m, a, e = allocate_shifts_for_one_pair(work_pairs, m, a, e)
        solutions.append(prob)

    print "SOLUTIONS"
    for i, prob in enumerate(solutions):
        print "%d. %r value=%.2f %s" % (
            i,
            [v.varValue for v in prob.variables()],
            value(prob.objective),
            LpStatus[prob.status],
        )
