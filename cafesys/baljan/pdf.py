# -*- coding: utf-8 -*-
# FIXME: This module could need some attention and polishing.

import os
from io import BytesIO
from datetime import datetime

from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import reverse
from PyPDF2 import PdfFileWriter, PdfFileReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, Paragraph, SimpleDocTemplate
from reportlab.graphics.barcode import qr

from .util import grouper

import pytz

from django.utils.translation import ugettext as _

A8 = (74 * mm, 52 * mm)
paper_size = A8
pad = 3 * mm

DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = '%Y-%m-%d %H:%M'

assets_folder = os.path.join("cafesys", "baljan", "assets")

title_font = ("Lobster", 16)
font = ('Helvetica', 16)
small_font = ('Helvetica', 7)
code_font = ('Courier-Bold', 16)

try:
    pdfmetrics.registerFont(TTFont('Lobster', os.path.join(assets_folder,'Lobster-Regular.ttf')))
    title_font = ("Lobster", 20)
except:
    title_font = ("Helvetica", 16)
class RefillCard(object):
    def __init__(self, balance_code):
        self.balance_code = balance_code

    def save(self, file_object):
        c = canvas.Canvas(file_object, pagesize=A8)
        w, h = paper_size
        column_width = (w-3*pad)/2
        center_col1 = pad+(column_width/2)
        center_col2 = w-center_col1

        code = self.balance_code
        series = code.refill_series

        current_site = Site.objects.get_current()
        code_path = reverse('credits', kwargs={'code': code.code})
        code_url_qr = qr.QrCode(f'https://{current_site}{code_path}', height=column_width, width=column_width, qrBorder=0)
        code_url_qr.drawOn(c, w-column_width-pad, h-column_width-pad)

        logo_width = column_width * 0.6
        logo_height = logo_width * 0.782 # hard coded aspect ratio
        c.drawImage(os.path.join(assets_folder,"logo_black.png"), pad, pad, width=logo_width, height=logo_height)

        c.setFont(*code_font)
        c.drawCentredString(center_col2, 3*pad, code.code)
  
        c.setFont(*title_font)
        c.drawCentredString(center_col1, h*0.75, "Kaffekort")
        c.setFont(*font)
        c.drawCentredString(center_col1, h*0.6, f"{code.value} {code.currency}")

        c.setFont(*small_font)
        c.drawCentredString(center_col1, h*0.5,
                _('expires no sooner than %s') \
                    % series.least_valid_until.strftime(DATE_FORMAT))
        c.drawCentredString(center_col1, h*0.43, "baljan.org")
        c.drawCentredString(center_col2, pad, f"{series.pk}.{code.pk}")
        
        c.showPage()
        c.save()
        return c


def refill_series(file_object, list_of_series):
    out_pdf = PdfFileWriter()
    for series in list_of_series:
        balance_codes = series.balancecode_set.all().order_by('pk')
        for balance_code in balance_codes:
            card = RefillCard(balance_code)
            buf = BytesIO()
            card.save(buf)
            buf.seek(0)
            pdfbuf = PdfFileReader(buf)
            out_pdf.addPage(pdfbuf.getPage(0))
    out_pdf.write(file_object)
    return out_pdf


def join_shifts(shifts):
    result = ''
    for i, shift in enumerate(shifts):
        if i == 2:
            result += ',\n'
        elif i > 0:
            result += ', '

        result += shift

    return result


def shift_combinations(file_object, semester,
        empty_cells=False, cell_title=None):
    if cell_title is None:
        cell_title = _("work shifts")

    # FIXME: DRY in this function.
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Left", alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="Center", alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="Right", alignment=TA_RIGHT))
    doc = SimpleDocTemplate(file_object)
    elems = []

    tz = pytz.timezone(settings.TIME_ZONE)
    now = datetime.now(tz)

    elems.append(
        Paragraph(_("Job Opening %s") % semester.name,
            styles['Heading1']))

    data = []
    data.append(
        ['#', cell_title, '#', cell_title],
    )

    combs = semester.shiftcombination_set.order_by('label')
    taken_indexes = []
    for i, (p1, p2) in enumerate(grouper(2, combs, None)):
        if p1.is_taken():
            taken_indexes.append((0, i))

        sh1 = [] if empty_cells else [str(sh.name_short()) for sh
                in p1.shifts.order_by('when')]

        if p2 is None:
            data.append([p1.label, join_shifts(sh1), '', ''])
        else:
            sh2 = [] if empty_cells else [str(sh.name_short()) for sh
                    in p2.shifts.order_by('when')]
            if p2.is_taken():
                taken_indexes.append((2, i))
            data.append([p1.label, join_shifts(sh1), p2.label, join_shifts(sh2)])

    bg_color = colors.black
    table_style = [
        ('GRID', (0, 0), (-1, -1), 0.15*mm, colors.black),
        ('FONT', (0, 0), (-1, -1), font[0]),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (0, -1), bg_color),
        ('BACKGROUND', (2, 0), (2, -1), bg_color),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.white),

        ('FONT', (0, 0), (-1, 0), "%s-Bold" % font[0]),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
    ]
    for col, row in taken_indexes:
        incl_header = row + 1
        table_style += [('TEXTCOLOR', (col, incl_header), (col, incl_header), bg_color)]
        table_style += [('TEXTCOLOR', (col+1, incl_header), (col+1, incl_header), colors.grey)]

    table = Table(data, style=table_style)
    elems.append(table)

    elems.append(
        Paragraph(_("document generated %s") % now.strftime(DATETIME_FORMAT),
            styles['Center']))

    doc.build(elems)
    return doc



def shift_combination_form(file_object, semester):
    pad = 30 # ugly way of getting enough room for text
    return shift_combinations(file_object, semester,
            empty_cells=True,
            cell_title=" "*pad + _("liu ids") + " "*pad,
    )
