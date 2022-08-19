# -*- coding: utf-8 -*-
import os

from django.contrib.sites.models import Site
from django.urls import reverse
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr

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


def draw_balance_code_card(c: canvas.Canvas, balance_code):
    w, h = paper_size
    column_width = (w-3*pad)/2
    center_col1 = pad+(column_width/2)
    center_col2 = w-center_col1

    code = balance_code
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

    value_height = 0.6
    add_to_group = series.add_to_group
    if add_to_group:
        c.setFont(*small_font)
        c.drawCentredString(center_col1, h * 0.57, add_to_group.name.lstrip("_"))
        value_height = 0.63
    
    c.setFont(*font)
    c.drawCentredString(center_col1, h*value_height, f"{code.value} {code.currency}")

    c.setFont(*small_font)
    c.drawCentredString(center_col1, h*0.5,
            _('expires no sooner than %s') \
                % series.least_valid_until.strftime(DATE_FORMAT))
    c.drawCentredString(center_col1, h*0.43, "baljan.org")
    c.drawCentredString(center_col2, pad, f"{series.pk}.{code.pk}")
    
    c.showPage()


def refill_series(file_object, list_of_series, name: str):
    c = canvas.Canvas(file_object, pagesize=A8)
    for series in list_of_series:
        balance_codes = series.balancecode_set.all().order_by('pk')
        for balance_code in balance_codes:
            draw_balance_code_card(c, balance_code)

    c.setTitle(name)
    c.save()
    return c
