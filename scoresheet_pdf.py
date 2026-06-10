"""Generates the match scoresheet as an A4 landscape PDF.

Layout mirrors the original printable HTML sheet: title/date/venue header,
team names over their halves of the board table, one table per round
(BD | Forename Surname PNUM Rating w/b | Result | w/b Forename Surname PNUM
Rating), a round-total box under the Result column, a final-score box after
the last round, and captain signature lines at the bottom.

If the sheet is too tall for one page, the whole layout (row heights, gaps
and font sizes) is scaled down by a single factor. Below a readability
floor it switches to multi-page output instead, breaking only between
rounds and keeping the signature block together.
"""

from fpdf import FPDF

_PAGE_W, _PAGE_H = 297, 210  # A4 landscape, mm
_MARGIN = 10
_AVAIL_W = _PAGE_W - 2 * _MARGIN
_AVAIL_H = _PAGE_H - 2 * _MARGIN

# Relative column widths, scaled to fill the printable width exactly.
_COL_REL = [10, 42, 42, 18, 16, 9, 16, 9, 42, 42, 18, 16]
_HEADERS = ["BD", "Forename", "Surname", "PNUM", "Rating", "w/b", "Result",
            "w/b", "Forename", "Surname", "PNUM", "Rating"]
_ROW_KEYS = ["bd", "h_forename", "h_surname", "h_pnum", "h_rating", "h_colour",
             "result", "a_colour", "a_forename", "a_surname", "a_pnum",
             "a_rating"]

# Base block heights in mm (at layout factor 1.0).
_TOP_H = 8 + 2 + 4 + 7 + 2   # title line + gap, divider gap, teams line + gap
_SIG_H = 4 + 7 + 3 + 7       # leading gap, captain row, spacing, signature row
_ROUND_TITLE_H = 7
_HEADER_ROW_H = 6
_ROW_H = 7.5
_ROUND_GAP = 2
_QR_SIZE = 22                # match-link QR code, kept full size to scan well

# Smallest acceptable layout factor before rows/fonts become too cramped
# to write results in by hand.
_MIN_FACTOR = 0.65


def _latin1(value):
    # The Helvetica core font only supports latin-1; replace anything else.
    return str(value or "").encode("latin-1", "replace").decode("latin-1")


def _round_height(rnd, is_last, factor=1.0):
    h = (_ROUND_TITLE_H if rnd.get("label") else 0) + _HEADER_ROW_H
    h += (len(rnd["rows"]) + 1) * _ROW_H  # board rows + round-total box
    h += _ROW_H if is_last else _ROUND_GAP  # final-score row / gap to next
    return h * factor


def _sig_height(has_qr):
    """Signature block height; tall enough for the QR code when present."""
    return max(_SIG_H, 4 + _QR_SIZE) if has_qr else _SIG_H


def _layout_factor(rounds, has_qr=False):
    """Return (factor, multi_page) for the given rounds.

    factor < 1 shrinks the header and round tables onto one page; the
    signature block (and QR code) always stays at full size so signatures
    remain writable and the QR stays scannable. multi_page=True means
    full-size layout flowing over several pages instead.
    """
    needed = _TOP_H + sum(
        _round_height(rnd, i == len(rounds) - 1)
        for i, rnd in enumerate(rounds)
    )
    avail = _AVAIL_H - _sig_height(has_qr)
    if needed <= avail:
        return 1.0, False
    factor = avail / needed
    if factor >= _MIN_FACTOR:
        return factor, False
    return 1.0, True


def build_scoresheet_pdf(title, date_str, venue, home_team, away_team,
                         rounds, home_captain, away_captain, qr_image=None):
    """Build the scoresheet and return the PDF as bytes.

    rounds: list of {'label': str or None, 'rows': [dict]} where each row
    dict carries the keys in _ROW_KEYS (missing keys render blank).
    qr_image: optional PIL image (the match-link QR code), printed at the
    bottom-right beside the signatures.
    """
    pdf = FPDF(orientation="landscape", format="A4")
    pdf.set_margins(_MARGIN, _MARGIN, _MARGIN)
    pdf.set_auto_page_break(True, margin=_MARGIN)
    pdf.add_page()

    f, multi_page = _layout_factor(rounds, has_qr=qr_image is not None)

    def font(style, size):
        pdf.set_font("Helvetica", style, size * f)

    scale = _AVAIL_W / sum(_COL_REL)
    col_w = [w * scale for w in _COL_REL]
    row_h = _ROW_H * f

    # --- Header: title left, date/venue right ---
    font("B", 15)
    pdf.cell(_AVAIL_W - 130, 8 * f, _latin1(title))
    font("B", 10)
    pdf.cell(12, 8 * f, "Date:")
    font("", 10)
    pdf.cell(48, 8 * f, _latin1(date_str), border="B", align="C")
    pdf.cell(8, 8 * f, "")
    font("B", 10)
    pdf.cell(16, 8 * f, "Venue:")
    font("", 10)
    pdf.cell(0, 8 * f, _latin1(venue), border="B", align="C")
    pdf.ln(10 * f)

    # --- Thick divider ---
    y = pdf.get_y()
    pdf.set_line_width(0.8)
    pdf.line(_MARGIN, y, _PAGE_W - _MARGIN, y)
    pdf.set_line_width(0.2)
    pdf.set_y(y + 4 * f)

    # --- Team names, aligned over their halves of the table ---
    home_half_w = sum(col_w[:8])
    font("", 11)
    pdf.cell(14, 7 * f, "Home:")
    font("B", 11)
    pdf.cell(home_half_w - 14 - 6, 7 * f, _latin1(home_team), border="B")
    pdf.cell(6, 7 * f, "")
    font("", 11)
    pdf.cell(14, 7 * f, "Away:")
    font("B", 11)
    pdf.cell(0, 7 * f, _latin1(away_team), border="B")
    pdf.ln(9 * f)

    # --- Rounds ---
    result_x = _MARGIN + sum(col_w[:6])
    for r_idx, rnd in enumerate(rounds):
        is_last = r_idx == len(rounds) - 1

        # In multi-page mode break before a round that won't fit whole.
        if multi_page and pdf.get_y() + _round_height(rnd, is_last) > _PAGE_H - _MARGIN:
            pdf.add_page()

        if rnd.get("label"):
            font("B", 12)
            pdf.cell(0, _ROUND_TITLE_H * f, _latin1(rnd["label"]))
            pdf.ln(_ROUND_TITLE_H * f)

        font("B", 8)
        pdf.set_fill_color(232)
        for w, head in zip(col_w, _HEADERS):
            pdf.cell(w, _HEADER_ROW_H * f, head, border=1, align="C", fill=True)
        pdf.ln(_HEADER_ROW_H * f)

        for row in rnd["rows"]:
            for w, key in zip(col_w, _ROW_KEYS):
                text = _latin1(row.get(key))
                if key == "bd":
                    pdf.set_fill_color(244)
                    font("B", 9)
                    pdf.cell(w, row_h, text, border=1, align="C", fill=True)
                elif key == "result":
                    font("B", 9)
                    pdf.cell(w, row_h, text or "-", border=1, align="C")
                else:
                    font("", 9)
                    pdf.cell(w, row_h, text, border=1, align="C")
            pdf.ln(row_h)

        # Round total: a single box under the Result column.
        pdf.set_x(result_x)
        pdf.set_fill_color(244)
        font("B", 9)
        pdf.cell(col_w[6], row_h, "-", border=1, align="C", fill=True)
        pdf.ln(row_h)

        if is_last:
            font("B", 10)
            pdf.cell(sum(col_w[:6]), row_h, "Final Score  ", align="R")
            pdf.set_fill_color(244)
            pdf.cell(col_w[6], row_h, "", border=1, fill=True)
            pdf.ln(row_h)
        else:
            pdf.ln(_ROUND_GAP * f)

    # --- Captain names, signature lines, and match-link QR code ---
    # Drawn at full size regardless of the layout factor: signatures must
    # stay writable and the QR code must stay scannable.
    if multi_page and pdf.get_y() + _sig_height(qr_image is not None) > _PAGE_H - _MARGIN:
        pdf.add_page()
    pdf.ln(4)
    y0 = pdf.get_y()

    sig_avail = _AVAIL_W
    if qr_image is not None:
        pdf.image(qr_image, x=_PAGE_W - _MARGIN - _QR_SIZE, y=y0,
                  w=_QR_SIZE, h=_QR_SIZE)
        sig_avail -= _QR_SIZE + 6

    block_w = (sig_avail - 20) / 2
    blocks = [
        (_MARGIN, "Home Captain:", home_captain),
        (_MARGIN + block_w + 20, "Away Captain:", away_captain),
    ]
    for x, label, name in blocks:
        pdf.set_xy(x, y0)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(30, 7, label)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(block_w - 30, 7, _latin1(name), border="B")
        pdf.set_xy(x, y0 + 10)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(30, 7, "Signature:")
        pdf.cell(block_w - 30, 7, "", border="B")

    return bytes(pdf.output())
