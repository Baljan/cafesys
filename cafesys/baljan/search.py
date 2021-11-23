# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Q


def for_person(terms, use_cache=True):
    cache_minutes = 30

    # Each term is cached.
    term_list = terms.lower().split()  # lower() for reusing cache keys
    all_term_hits = []  # will be a list of lists
    for term in term_list:
        k = "baljan.search.%s" % term

        c = cache.get(k) if use_cache else None
        if c is None:
            term_ids = [
                u.id
                for u in User.objects.filter(
                    Q(first_name__icontains=term)
                    | Q(last_name__icontains=term)
                    | Q(username__icontains=term)
                    | Q(groups__name__icontains=term)
                )
            ]
            all_term_hits.append(term_ids)
            cache.set(k, term_ids, cache_minutes * 60)
        else:
            all_term_hits.append(c)

    # Find the set of user ids that was found for every term.
    ids = set()
    if len(all_term_hits):
        ath = all_term_hits
        ids = set(ath[0]).intersection(*ath)

    hits = (
        User.objects.filter(
            pk__in=ids).order_by(
            "first_name",
            "last_name").distinct())
    return hits
