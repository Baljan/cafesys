# -*- coding: utf-8 -*-

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from pyPdf import PdfFileWriter, PdfFileReader
from cStringIO import StringIO

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

    def save(self, file_object):
        c = canvas.Canvas(file_object, pagesize=A8)
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
        return c


def refill_series(file_object, list_of_series):
    out_pdf = PdfFileWriter()
    for series in list_of_series:
        balance_codes = series.balancecode_set.all().order_by('pk')
        for balance_code in balance_codes:
            card = RefillCard(balance_code)
            buf = StringIO()
            card.save(buf)
            buf.seek(0)
            pdfbuf = PdfFileReader(buf)
            out_pdf.addPage(pdfbuf.getPage(0))
    out_pdf.write(file_object)
    return out_pdf

