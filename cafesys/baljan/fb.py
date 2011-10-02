# coding=utf-8
import requests
from django.core.urlresolvers import reverse
import util

GRAPH_URL = u'https://graph.facebook.com/'

def url(path):
    return u"%s%s" % (GRAPH_URL, path)

def good_url(good):
    return u'http://%s%s' % (
        util.current_site().domain, 
        reverse('facebook_good', args=(good.pk,)),
    )
