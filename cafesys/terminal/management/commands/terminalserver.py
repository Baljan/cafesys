# coding=utf-8

from Queue import Queue
from threading import Thread

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.conf import settings

import tornado.ioloop
import tornado.web
import tornado.websocket

insert_queue = Queue()


class CardInsertsHandler(tornado.web.RequestHandler):

    def post(self):
        insert_queue.put('foo')
        self.write("card read")


def insert_worker(ws):
    while True:
        data = insert_queue.get()
        ws.write_message(data)
        print "write to ws: %r" % data
        insert_queue.task_done()


class EventHandler(tornado.websocket.WebSocketHandler):

    def open(self):
        print "event web socket opened"
        self.thread = Thread(target=insert_worker, args=(self,))
        self.thread.daemon = True
        self.thread.start()
        print "thread started"

    def on_message(self, message):
        print "ws message in: %r" % message

    def on_close(self):
        print "event web socket closed"
        if hasattr(self, 'thread'):
            self.thread.join()


app = tornado.web.Application([
    (r'/card_inserts', CardInsertsHandler),
    (r'/events', EventHandler),
])

class Command(BaseCommand):
    args = ''
    help = 'Run terminal server.'

    def handle(self, *args, **options):
        app.listen(settings.TERMINAL_TORNADO_PORT)
        tornado.ioloop.IOLoop.instance().start()

