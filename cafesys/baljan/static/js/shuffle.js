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

function distributeNormal(counts, numCafes, sortFunc) {
    /**
     * Distribute shifts completely randomly
    */
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

    // Shuffle the shifts between cafés
    for (let i = 0; i < ret.length - numCafes; i += numCafes) {
        shuffle(ret, i, i + numCafes, 1);
    }

    // Shuffle the shifts in batches of size numCafes
    shuffle(ret, 0, ret.length, numCafes);

    return ret;
}

function distributeDays(counts, numCafes, sortFunc, totalShifts, shiftsPerDayAndCafe, preferOneCafe) {
    /**
     * Distribute shifts randomly but try to give each person as many whole
     * days as possible.
     */
    let ret = new Array(totalShifts);

    // iterate over cafes
    for (let i = 0; i < numCafes; ++i) {
        // iterate over week
        for (let j = 0; j < totalShifts && counts.length > 0; j += numCafes) {
            ret[i+j] = counts[0].key;
            if(--counts[0].value === 0) {
                counts.sort(sortFunc);
                counts.pop();
            }
        }
    }

    // There are three shifts in a day
    // Shuffle between days but keep the distribution within the day
    shuffle(ret, 0, ret.length, 3*numCafes);

    // Shuffle the shifts within the day but between cafes
    for (let i = 0; i < ret.length; i += numCafes*shiftsPerDayAndCafe) {
        if (preferOneCafe && randint(0,2) === 0) {
            for (let j = 0; j < numCafes*shiftsPerDayAndCafe; j += numCafes) {
                swap(ret, i+j, i+j+1);
            }
        } else if (!preferOneCafe) {
            for (let j = 0; j < numCafes*shiftsPerDayAndCafe; j += numCafes) {
                if (randint(0, 2) === 0) {
                    swap(ret, i+j, i+j+1);
                }
            }
        }
    }

    return ret;
}


function distribute(personShifts, numCafes, shiftsPerDayAndCafe, preferWholeDays, preferOneCafe) {
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

    let counts = personShifts.map(e => {return {key: e.key, value: e.value};})
                             .filter(e => e.value > 0);
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
    if (totalShifts <= 0) {
        // There are no shifts to distribute
        throw new Error(`There are no shifts to distribute`);
    }

    return (preferWholeDays ?
            distributeDays(counts, numCafes, sortFunc, totalShifts, shiftsPerDayAndCafe, preferOneCafe)
            :
            distributeNormal(counts, numCafes, sortFunc)
            );
}