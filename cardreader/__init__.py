# -*- coding: utf-8 -*-

from urllib2 import urlopen, HTTPError

class CardReader(object):
    def __init__(self, 
            translator=None,
            reader=None,
            ):
        self.keep_running = True
        self.translator = translator
        self.reader = reader

    def got_card(self, card_no):
        user_id = self.translator(card_no)
        print "Got card: ", card_no, user_id

        if user_id is None:
            # TODO: Log that an invalid card was shown.
            return 

        # TODO: HTTP GET to the terminal server, to bind the current order to
        # the user.
        base_url = 'http://localhost:8000'
        url = base_url + '/terminal/trig-tag-shown/' + user_id

        try:
            f = urlopen(url)
            response = f.read()
            print "Got response", response
            if response == 'OK':
                pass
            elif response == 'PENDING':
                pass
        except HTTPError:
            # TODO: Log error.
            pass
    
    def run(self):
        self.reader(self)


if __name__ == '__main__':
    import stimuli
    try:
        cr = CardReader(translator=stimuli.id_for, 
                reader=stimuli.card_reader_runner)
        cr.run()
    except KeyboardInterrupt:
        cr.keep_running = False
        raise
