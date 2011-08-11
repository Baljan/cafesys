# coding=utf-8
import json

from django.http import HttpResponse
from django.utils import translation
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth import authenticate, login
from django.core import serializers

from piston.handler import BaseHandler
from piston.resource import Resource
from piston.emitters import Emitter
from piston.authentication import HttpBasicAuthentication

from baljan.models import Good

auth = HttpBasicAuthentication(realm="Brassbird")


class CsrfExemptResource(Resource):
    """A Custom Resource that is csrf exempt"""

    def __init__(self, handler, *args, **kwargs):
        super(CsrfExemptResource, self).__init__(handler, *args, **kwargs)
        self.csrf_exempt = getattr(self.handler, 'csrf_exempt', True)


class ItemResource(BaseHandler):
    allowed_methods = ('GET', )
    fields = (
        'id', 'title', 'description', 
        'current_cost_dict',
    )
    model = Good

    def read(self, request, pk):
        if pk == '':
            items = Good.objects.all()
            return items
        return Good.objects.get(pk=int(pk))


item_resource = Resource(
    handler=ItemResource, 
    #authentication=auth,
)


class AuthResource(BaseHandler):
    allowed_methods = ('GET', 'POST')

    def read(self, request, action):
        return []

    def create(self, request, action):
        if action == 'login':
            return self.do_login(request)

    def do_login(self, request):
        uname = request.POST['username']
        passw = request.POST['password']
        user = authenticate(username=uname, password=passw)
        if user is None:
            return HttpResponse(status=200)
        if user.is_active:
            login(request, user)
            return {
                'user': user.username,
                'full_name': user.get_full_name(),
            }
        return HttpResponse(status=200)

auth_resource = CsrfExemptResource(
    handler=AuthResource, 
)

