# -*- coding: utf-8 -*-

class CardReader(object):
    def __init__(self, 
            card_translator=None,
            reader=None,
            ):
        self.keep_running = True
        self.card_translator = card_translator
        self.reader = reader

    def got_card(self, card_no):
        user_id = self.card_translator(card_no)
        print "Got card: ", card_no, user_id
    
    def run(self):
        self.reader(self)


if __name__ == '__main__':
    import stimuli
    try:
        cr = CardReader(card_translator=stimuli.id_for, 
                reader=stimuli.card_reader_runner)
        cr.run()
    except KeyboardInterrupt:
        cr.keep_running = False
        raise
