# -*- coding: utf-8 -*-

__author__ = 'Simon Pantzare'

from subprocess import Popen
import os

url='http://localhost:8000/terminal' # FIXME: adapt to settings

class Kiosk(object):
    def start(self):
        raise NotImplementerError('not available in base class')

    def quit(self):
        raise NotImplementerError('not available in base class')

class OperaKiosk(Kiosk):
    def start(self):
        self._p = Popen([
            'opera', 
            '--personaldir', 
            os.path.join(os.path.dirname(__file__), 'opera-personal-dir'),
            '-kioskmode',
            url,
            ])

    def quit(self):
        self._p.terminate()


def _find_chrome_window():
    from Xlib.display import Display
    from Xlib import X, Xatom
    from Xlib.protocol import event
    display = Display()
    name = display.get_atom('WM_NAME', 1)
    root = display.screen().root

    class FoundItException(Exception):
        def __init__(self, msg, window):
            self.window = window

    def searcher(parent):
        children = parent.query_tree().children
        for child in children:
            prop = child.get_property(name, Xatom.STRING, 0, 1024)
            if prop and 0 < len(prop.value):
                if prop.value == 'cafesys terminal': # FIXME: make dynamic
                    raise FoundItException('found', child)
            searcher(child)
    try:
        searcher(root)
    except FoundItException, e:
        return e.window


class ChromeKiosk(Kiosk): # TODO: Not working.
    user_dir = 'chrome-user-dir'

    def __init__(self):
        self._p = None

    def start(self):
        self._p = Popen([
            'google-chrome', 
            '--user-data-dir=%s' % os.path.join(os.path.dirname(__file__), self.user_dir),
            '--app=%s' % url,
            '--name=cafesys-kiosk',
            ])
        pid = self._p.pid

        window = None
        while not window:
            window = _find_chrome_window()

        while True:
            display = Display()
            focus = display.get_input_focus().focus
            focus.send_event(event.KeyPress(
                detail=32, #95
                time=X.CurrentTime,
                root=display,
                window=focus,
                child=X.NONE,
                state=0,
                same_screen=1,
                root_x=1,
                root_y=1,
                event_x=1,
                event_y=1,
                ))
            print 'event sent'

    def quit(self):
        self._p.terminate()

if __name__ == '__main__':
    from time import sleep
    k = OperaKiosk()
    k.start()
    sleep(5)
    k.quit()
