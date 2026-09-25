# -*- coding: utf-8 -*-
import os
from xml.sax.saxutils import escape

from django.contrib.sites.models import Site
from django.urls import reverse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, TTFError
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.platypus import (
    KeepInFrame,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from django.utils.translation import gettext as _

from cafesys.baljan.models import EXTRA_ORDER_SHEET

A8 = (74 * mm, 52 * mm)
paper_size = A8
pad = 3 * mm

DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M"

assets_folder = os.path.join("cafesys", "baljan", "assets")

title_font = ("Lobster", 16)
font = ("Helvetica", 16)
small_font = ("Helvetica", 7)
code_font = ("Courier-Bold", 16)

try:
    pdfmetrics.registerFont(
        TTFont("Lobster", os.path.join(assets_folder, "Lobster-Regular.ttf"))
    )
    title_font = ("Lobster", 20)
except TTFError:
    title_font = ("Helvetica", 16)


def draw_balance_code_card(c: canvas.Canvas, balance_code):
    w, h = paper_size
    column_width = (w - 3 * pad) / 2
    center_col1 = pad + (column_width / 2)
    center_col2 = w - center_col1

    code = balance_code
    series = code.refill_series

    current_site = Site.objects.get_current()
    code_path = reverse("credits", kwargs={"code": code.code})
    code_url_qr = qr.QrCode(
        f"https://{current_site}{code_path}",
        height=column_width,
        width=column_width,
        qrBorder=0,
    )
    code_url_qr.drawOn(c, w - column_width - pad, h - column_width - pad)

    logo_width = column_width * 0.6
    logo_height = logo_width * 0.782  # hard coded aspect ratio
    c.drawImage(
        os.path.join(assets_folder, "logo_black.png"),
        pad,
        pad,
        width=logo_width,
        height=logo_height,
    )

    c.setFont(*code_font)
    c.drawCentredString(center_col2, 3 * pad, code.code)

    c.setFont(*title_font)
    c.drawCentredString(center_col1, h * 0.75, "Kaffekort")

    value_height = 0.6
    add_to_group = series.add_to_group
    if add_to_group:
        c.setFont(*small_font)
        c.drawCentredString(center_col1, h * 0.57, add_to_group.name.lstrip("_"))
        value_height = 0.63

    c.setFont(*font)
    c.drawCentredString(center_col1, h * value_height, f"{code.value} {code.currency}")

    c.setFont(*small_font)
    c.drawCentredString(
        center_col1,
        h * 0.5,
        _("expires no sooner than %s") % series.least_valid_until.strftime(DATE_FORMAT),
    )
    c.drawCentredString(center_col1, h * 0.43, "baljan.org")
    c.drawCentredString(center_col2, pad, f"{series.pk}.{code.pk}")

    c.showPage()


def refill_series(file_object, list_of_series, name: str):
    c = canvas.Canvas(file_object, pagesize=A8)
    for series in list_of_series:
        balance_codes = series.balancecode_set.all().order_by("pk")
        for balance_code in balance_codes:
            draw_balance_code_card(c, balance_code)

    c.setTitle(name)
    c.save()
    return c


EXTRA_ORDER_CUSTOMERS_PER_PAGE = 9
EXTRA_ORDER_INFO = (
    "Samtliga Baguetter med fyllningar är laktosfria. Gäller även smör. "
    "Går att få glutenfria frallor, ej baguetter. "
    "Glutenfri pastasallad = sallad utan pasta"
)


def extra_order_sheet(orders):
    """Smorgasfiket's order sheet as rows of counts, one column per order."""
    counts = [
        {item["field"]: item.get("count") or 0 for item in order.items}
        for order in orders
    ]

    def row(label, fields):
        per_order = [sum(c.get(f, 0) for f in fields) for c in counts]
        return {"label": label, "counts": per_order, "total": sum(per_order)}

    sections = [
        {"title": title, "rows": [row(label, [field]) for field, label, _ in rows]}
        for title, rows in EXTRA_ORDER_SHEET
    ]
    sums = [
        row(f"Sum {title}", [field for field, _, _ in rows])
        for title, rows in EXTRA_ORDER_SHEET
    ]
    by_bread = {}
    for _title, rows in EXTRA_ORDER_SHEET:
        for field, _label, bread in rows:
            if bread:
                by_bread.setdefault(bread, []).append(field)
    bread = [
        row("Ljus baguette", by_bread["ljus"]),
        row("Mörk baguette", by_bread["mörk"]),
        row("Fralla", by_bread["fralla"]),
    ]
    return {
        "columns": [
            f"{order.date:%d/%m} {order.association} ({order.orderer})"
            for order in orders
        ],
        "sections": sections,
        "sums": sums,
        "bread": bread,
    }


def _extra_order_table(sheet, start, stop, with_total, entered_by, width):
    head = getSampleStyleSheet()["BodyText"].clone("head", fontSize=7, leading=8)

    def cells(entry, blank_zero):
        shown = entry["counts"][start:stop]
        values = ["" if blank_zero and n == 0 else n for n in shown]
        return [entry["label"], *values] + ([entry["total"]] if with_total else [])

    columns = sheet["columns"][start:stop]
    n_cols = len(columns) + 1 + with_total
    header = ["Datum/Kund", *[Paragraph(escape(c), head) for c in columns]]
    data = [header + (["Sum"] if with_total else [])]
    shaded = [0]

    for section in sheet["sections"]:
        shaded.append(len(data))
        data.append([section["title"]] + [""] * (n_cols - 1))
        data += [cells(r, blank_zero=True) for r in section["rows"]]

    entered = Paragraph(escape(entered_by), head)
    data.append(["Inlagd av", *[entered] * len(columns)] + ([""] if with_total else []))
    for title, rows in (("SUMMERING", sheet["sums"]), ("Bröd", sheet["bread"])):
        shaded.append(len(data))
        data.append([title] + [""] * (n_cols - 1))
        data += [cells(r, blank_zero=False) for r in rows]

    style = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    for r in shaded:
        style += [
            ("BACKGROUND", (0, r), (-1, r), colors.HexColor("#d9e2f3")),
            ("FONT", (0, r), (-1, r), "Helvetica-Bold", 8),
        ]
    if with_total:
        style.append(("FONT", (-1, 1), (-1, -1), "Helvetica-Bold", 8))

    label, total = 38 * mm, 12 * mm
    customer = min(30 * mm, (width - label - total) / max(len(columns), 1))
    col_widths = [label] + [customer] * len(columns) + ([total] if with_total else [])
    return Table(data, colWidths=col_widths, style=TableStyle(style), repeatRows=1)


def _extra_order_box(title, paragraphs, width, style):
    return Table(
        [[Paragraph(title, style)], *[[p] for p in paragraphs]],
        colWidths=[width],
        style=[
            ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9e2f3")),
        ],
    )


def extra_order_week(file_object, week, orders, allergies, entered_by):
    """The week's extra order to Smorgasfiket; `allergies` maps order pk to text."""
    styles = getSampleStyleSheet()
    body = styles["BodyText"].clone("box", fontSize=8, leading=10)
    bold = body.clone("box_title", fontName="Helvetica-Bold")
    title = f"EXTRABESTÄLLNING - SEKTIONSCAFÉ BALJAN - vecka {week}"
    doc = SimpleDocTemplate(
        file_object,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=title,
    )
    side_width = 70 * mm
    gap = 6 * mm
    table_width = doc.width - side_width - gap
    side_height = doc.height - 15 * mm
    sheet = extra_order_sheet(orders)

    story = []
    per_page = EXTRA_ORDER_CUSTOMERS_PER_PAGE
    starts = range(0, max(len(orders), 1), per_page)
    for start in starts:
        stop = start + per_page
        written = [
            Paragraph(escape(text).replace("\n", "<br/>"), body)
            for order in orders[start:stop]
            if (text := allergies.get(order.pk, "").strip())
        ]
        side = [
            _extra_order_box(
                "Info", [Paragraph(EXTRA_ORDER_INFO, body)], side_width, bold
            ),
            Spacer(1, 4 * mm),
            _extra_order_box(
                "Allergier (OBS! Utöver ordinarie mackor/sallader)",
                written or [Paragraph("Inga", body)],
                side_width,
                bold,
            ),
        ]
        table = _extra_order_table(
            sheet, start, stop, start == starts[-1], entered_by, table_width
        )
        story += [
            Paragraph(title, styles["Heading2"]),
            Table(
                [[table, KeepInFrame(side_width, side_height, side, mode="shrink")]],
                colWidths=[table.minWidth() + gap, side_width],
                hAlign="LEFT",
                style=[
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ],
            ),
        ]
        if start != starts[-1]:
            story.append(PageBreak())

    doc.build(story)
