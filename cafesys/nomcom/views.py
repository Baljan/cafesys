# -*- coding: utf-8 -*-
from django.shortcuts import render_to_response
from django.template import RequestContext

def apply_board(request):
    rows = [[{
            'class': 'error',
            'span': 4,
            'title': u'Ordförande',
            'desc': u'Styr och ställer.',
        }, {
            'class': 'error',
            'span': 4,
            'title': u'Vice ordförande',
            'desc': u'Brukar vara någon som suttit länge.',
        }, {
            'class': 'error',
            'span': 4,
            'title': u'Kassör',
            'desc': u'Bokföring och budget.',
        }, {
            'class': 'success',
            'span': 4,
            'title': u'Sekreterare',
            'desc': u'Skriver protokoll.',
        }], [{
            'class': 'error',
            'span': 4,
            'title': u'Nörd',
            'desc': u'IT ska fungera.',
        }, {
            'class': 'error',
            'span': 4,
            'title': u'Inköpschef',
            'desc': u'Så att det finns kaffe och klägg.',
        }, {
            'class': 'success',
            'span': 4,
            'title': u'Personalis',
            'desc': u'Kommunicerar med personalen. Ordnar personalsläpp.',
        }, {
            'class': 'error',
            'span': 4,
            'title': u'Infognurgla',
            'desc': u'Gör affischer.',
        }], [{
            'class': 'error',
            'span': 4,
            'title': u'Partypiff',
            'desc': u'Arrangerar personalfest.',
        }, {
            'class': 'error',
            'span': 4,
            'title': u'Partypaff',
            'desc': u'Arrangerar personalfest.',
        }, {
            'class': 'error',
            'span': 4,
            'title': u'Partypuff',
            'desc': u'Arrangerar personalfest.',
        }, {
            'class': 'success',
            'span': 4,
            'title': u'Möbel+termos',
            'desc': u'Det finns många möbler och termosar i Baljan.',
        }], [{
            'class': 'error',
            'span': 4,
            'title': u'Jochen',
            'desc': u'Så att det kommer mackor.',
        }, {
            'class': 'error',
            'span': 4,
            'title': u'Kulhjul',
            'desc': u'Ordnar aktiviteter för styrelsen.',
        }, {
            'class': 'error',
            'span': 4,
            'title': u'Kulfyrkant',
            'desc': u'Ordnar aktiviteter för styrelsen.',
        }, {
            'class': 'error',
            'span': 4,
            'title': u'Roomie',
            'desc': u'Så att kontoret är fint.',
        }], [{
            'class': 'warning',
            'span': 4,
            'title': u'Pyssling',
            'desc': u'Håller ordning i förråd och andra utrymmen.',
        }, {
            'class': 'error',
            'span': 4,
            'title': u'Syssling',
            'desc': u'Håller ordning i förråd och andra utrymmen.',
        }]
    ]
    return render_to_response('nomcom/apply_board.html', {
        'post_rows': rows,
        }, context_instance=RequestContext(request))
