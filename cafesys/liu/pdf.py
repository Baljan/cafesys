# -*- coding: utf-8 -*-

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

if __name__ == '__main__':
    from pdfstimuli import gettext as _
else:
    from django.utils.translation import ugettext as _

A8 = (74 * mm, 52 * mm)
paper_size = A8
pad = 3 * mm

DATE_FORMAT = '%Y-%m-%d'

class RefillCard(object):
    def __init__(self, balance_code):
        self.balance_code = balance_code

    def save(self):
        c = canvas.Canvas("card.pdf", pagesize=A8)
        w, h = paper_size
        code = self.balance_code
        series = code.refill_series
        
        font = ('Helvetica', 12)
        footer_font = ('Helvetica', 8)
        code_font = ('Courier-Bold', 22)

        font_height = 9.8 # FIXME: how fetch programmatically?
        topmost_off = h-(pad+font_height)

        c.setFont(*font)
        c.drawString(pad, topmost_off, 'Baljan')
        c.drawRightString(w-pad, topmost_off, _('%d SEK') % code.value)
        
        c.setFont(*code_font)
        c.drawCentredString(w/2, h * 0.46, code.code)

        c.setFont(*footer_font)
        c.drawString(pad, pad, 
                _('expires no sooner than %s') \
                    % series.least_valid_until.strftime(DATE_FORMAT))
        c.drawRightString(w-pad, pad, '%d.%d' % (series.pk, code.pk))
        c.showPage()
        c.save()

if __name__ == '__main__':
    from pdfstimuli import dummy_balance_code
    rc = RefillCard(dummy_balance_code())
    rc.save()
