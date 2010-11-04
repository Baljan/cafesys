# -*- coding: utf-8 -*-

import baljan.actions

def actions(request):
    return {'action_categories': baljan.actions.categories_and_actions(request)}
