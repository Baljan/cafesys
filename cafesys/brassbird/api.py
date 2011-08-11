# coding=utf-8
import json

from django.http import HttpResponse
from django.utils import translation

from piston.handler import BaseHandler
from piston.resource import Resource
from piston.emitters import Emitter
from piston.authentication import HttpBasicAuthentication

import glue

auth = HttpBasicAuthentication(realm="Brassbird")

class ItemResource(BaseHandler):
    allowed_methods = ('GET', )
    fields = ('name', 'description', )

    def respond(self, data):
        """
        Finalize data and return a response. Makes certain keys
        headers and removes them from the serialized representation.
        """
        for k, r in glue.headers:
            data.pop(k, None)
        resp = HttpResponse(json.dumps(data), 'application/json')
        for key, value in data.headers.items():
            resp[key] = value
        return resp

    def read(self, request):
        items = glue.items()
        return self.respond(items)


item_resource = Resource(
    handler=ItemResource, 
    #authentication=auth,
)
