# coding=utf-8

try:
    from importlib import import_module
except ImportError:
    from django.utils.importlib import import_module
from django.conf import settings
from django.utils.datastructures import SortedDict
from django.utils import translation

interface = import_module(getattr(settings, 'BRASSBIRD_INTERFACE'))

headers = [
    ('language', 'Content-Language'), 
]

class GlueDict(dict):

    def __init__(self, *args):
        dict.__init__(self, *args)
        self._headers = dict((k, r) for k, r in headers)
        self.headers = SortedDict()

    def __setitem__(self, key, val):
        assert key != 'headers', 'headers are special.'
        if key in self._headers:
            self.headers[self._headers[key]] = val
        dict.__setitem__(self, key, val)

    def __getitem__(self, key):
        if key in self._headers:
            return self.headers[self._headers[key]]
        return dict.__getitem__(self, key)


def items(*args, **kwargs):
    ret = GlueDict()

    if interface.capabilities['multiple_currencies']:
        pass
    else:
        ret['currency'] = interface.defaults['currency']

    ret['items'] = interface.items(*args, **kwargs)
    return ret
