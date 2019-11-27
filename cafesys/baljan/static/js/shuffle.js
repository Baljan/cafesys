function randint(l, u) {
    /**
     * Return a random integer between l (inlcusive) and u (exclusive)
     * 
     * Runtime: O(1)
     */
    if (u < l) {
        throw new Error(`The supplied bounds are mixed up: u = ${u}, l = ${l}`);
    }

    return l + Math.floor((u - l) * Math.random());
}

function objToArr(obj) {
    /**
     * Convert an object to an array of objects consisting of keys and values
     * 
     * Runtime: O(n), where n is the number of keys in obj
     */
    return Object.keys(obj).map(k => { return { key: k, value: obj[k] } });
}

function swap(obj, a, b) {
    /**
     * Swap the values of the keys a, b in the object obj
     * 
     * Runtime: O(1)
     */
    let tmp = obj[a];
    obj[a] = obj[b];
    obj[b] = tmp;
}

function shuffle(collection, l, u, step) {
    /**
     * Shuffle the elements in collection between l (inclusive) and u
     * (exclusive) in chunks of size step
     * 
     * Runtime: O(n), where n = u - l
     */
    if (u > collection.length) {
        throw new Error(`Upper bound ${u} is too high, should be no larger `+
                        `than ${collection.length}`);
    }
    if (l < 0) {
        throw new Error(`Lower bound ${l} is too low, should be no smaller than 0`);
    }
    if (u < l) {
        throw new Error(`The supplied bounds are mixed up: u = ${u}, l = ${l}`);
    }
    if (step < 1) {
        throw new Error(`The supplied step size is too small: ${step}, ` +
                        `should be at least 1`);
    }
    if (u - l < step) {
        throw new Error(`There are not enough elements to shuffle: ${u - l}, ` +
                        `at least ${step} required`);
    }

    for (let count = u - step; count > l; count -= step) {
        let j = randint(l, Math.floor(count / step) + 1) * step;
        for (let i = 0; i < step; i++) {
            swap(collection, count + i, j + i);
        }
    }
}

function shuffleShifts(shifts, numCafes) {
    /**
     * Shuffle shifts in an appropriate manner
     * 
     * Runtime: O(n), where n is the number of shifts
     */
    // Shuffle the shifts between cafés
    for (let i = 0; i < shifts.length - numCafes; i += numCafes) {
        shuffle(shifts, i, i + numCafes, 1);
    }

    // Shuffle the shifts in batches of size numCafes
    shuffle(shifts, 0, shifts.length, numCafes);
}


function distribute(personShifts, numCafes) {
    /**
     * Distribute shifts randomly such that every person gets their wanted
     * number of shifts and no clashes between cafés occur
     * 
     * Runtime: O(m*n*log(n)), where m is the number of shifts and n is the
     *  number of people
     */
    if (numCafes < 1) {
        throw new Error(`Not enough cafés: ${numCafes}, should be at least 1`);
    }

    let counts = objToArr(personShifts);
    let totalShifts = counts.reduce((acc, cur) => acc + cur.value, 0);
    // Sort people in descending order of number of shifts, break ties randomly
    let sortFunc = (a, b) => b.value - a.value || randint(-1, 2);
    counts.sort(sortFunc);
    if (counts.length < numCafes) {
        // There are not enough people to work at the different cafés
        throw new Error(`There are not enough people to work: ${counts.length}, ` +
                        `at least ${numCafes} required`);
    }
    if (counts[0].value > totalShifts / numCafes) {
        // One person will have to work at multiple different cafés at the
        // same time
        throw new Error(`At least one person has too many shifts: ${counts[0].key} ` +
                        `has ${counts[0].value} shifts`);
    }
    if (totalShifts % numCafes !== 0) {
        // The shifts can't be distributed equally between the different cafés
        throw new Error(`Unable to distribute ${totalShifts} between ${numCafes} ` +
                        `cafés`);
    }


    let ret = [];
    while (counts.length >= numCafes) {
        // Add a random person
        let i = randint(numCafes - 1, counts.length);
        ret.push(counts[i].key);
        if (--counts[i].value === 0) {
            counts.splice(i, 1);
        }

        // Add numCafés - 1 of the people with the most shifts to fill up the
        // rest of the cafés
        let j = 0;
        while (j < numCafes - 1 && 0 < counts.length) {
            ret.push(counts[j].key);
            if (--counts[j].value === 0) {
                counts.splice(j, 1);
                j = Math.min(j, counts.length - 1);
            } else {
                ++j;
            }
        }

        // Keep the counts sorted to easily retrieve the people with the most
        // shifts left
        counts.sort(sortFunc);
    }

    shuffleShifts(ret, numCafes);

    return ret;
}