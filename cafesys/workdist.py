# -*- coding: utf-8 -*-
from pulp import LpProblem, LpMinimize, lpSum, LpVariable, LpStatus, LpInteger
from pulp import allcombinations, value
from math import floor, ceil

work_pairs = range(20)

shifts = ['MORNING', 'AFTERNOON', 'EXAM']
costs = {
    'MORNING': 2,
    'AFTERNOON': 3,
    'EXAM': 7,
}

def allocate_shifts_for_one_pair(work_pairs, avail_mornings, avail_afternons, avail_exams):
    """
    `work_pairs` is the number of work pairs left to distribute, the other
    arguments are the number of shifts available.

    Returns the result (`LpProblem`) and a new three-tuple after one more work
    pair has been distributed among the shifts.
    """
    mae = (avail_mornings, avail_afternoons, avail_exams)
    def _recurse(work_pairs, mae, grace=None):
        req = 1.0 if grace is None else grace
        demands = {
            'MORNING': mae[0],
            'AFTERNOON': mae[1],
            'EXAM': mae[2],
        }
        total_avg = float(sum([demands[i] for i in shifts])) / work_pairs
        total_low, total_high = floor(total_avg), ceil(total_avg)
        work_pair_count = work_pairs
        avgs = [float(demands[i]) / work_pair_count for i in shifts]
        lows = [floor(a) for a in avgs]
        highs = [ceil(a) for a in avgs]

        target = req * total_avg * float(sum([costs[i] for i in shifts])) / len(shifts)

        prob = LpProblem("Work Distribution", LpMinimize) 
        shift_vars = LpVariable.dicts("Shift", shifts, 0, cat=LpInteger)
        prob += lpSum([costs[i] * shift_vars[i] for i in shifts]), "cost of combination"
        prob += lpSum([costs[i] * shift_vars[i] for i in shifts]) >= target, "not too good"
        prob += lpSum([shift_vars[i] for i in shifts]) >= total_low, "low TOTAL"
        prob += lpSum([shift_vars[i] for i in shifts]) <= total_high, "high TOTAL"
        for shift, low, high in zip(shifts, lows, highs):
            prob += lpSum([shift_vars[shift]]) >= low, "low %s" % shift
            prob += lpSum([shift_vars[shift]]) <= high, "high %s" % shift

        prob.solve()

        if LpStatus[prob.status] == 'Undefined':
            next_grace = req - 0.1
            assert 0 <= next_grace 
            return compute(work_pairs, tuple(mae), next_grace)
        
        new_mae = [0, 0, 0]
        for v in prob.variables():
            for pos, name in [
                    (0, 'MORNING'),
                    (1, 'AFTERNOON'),
                    (2, 'EXAM'),
                    ]:
                if v.name == 'Shift_' + name:
                    new_mae[pos] = mae[pos] - v.varValue

        return (prob, work_pairs) + tuple(new_mae)
    
    return _recurse(work_pairs, mae)

solutions = []
mae = (43, 37, 11)
work_pairs = 23
while work_pairs != 0:
    prob, mae, grace, target = compute(work_pairs, mae)
    solutions.append((prob, grace, target))
    work_pairs -= 1

print "SOLUTIONS"
for i, (prob, grace, target) in enumerate(solutions):
    print "%d. %r cost=%.2f grace=%.2f target=%.2f %s" % (
        i,
        [v.varValue for v in prob.variables()],
        value(prob.objective),
        grace,
        target,
        LpStatus[prob.status],
    )
