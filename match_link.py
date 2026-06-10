"""Match links: the scoresheet setup encoded into a shareable URL + QR code.

The match setup (teams, players, venue, date, sheet options) is serialised
to compact JSON, zlib-compressed, and base64url-encoded into the `m` query
parameter of the app URL. The scoresheet PDF carries that URL as a QR code:
scanning the printed sheet reopens the app with everything prefilled, ready
for results entry. There is no server-side storage — the link *is* the data,
so it works on any host that runs the app (including localhost).
"""

import base64
import json
import zlib

import qrcode


def encode_match(payload):
    """dict -> URL-safe token."""
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    packed = base64.urlsafe_b64encode(zlib.compress(raw.encode("utf-8"), 9))
    return packed.decode("ascii").rstrip("=")


def decode_match(token):
    """URL-safe token -> dict. Raises ValueError on anything malformed."""
    try:
        padded = token + "=" * (-len(token) % 4)
        raw = zlib.decompress(base64.urlsafe_b64decode(padded.encode("ascii")))
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError("Invalid match link token") from exc


def build_match_url(base_url, payload):
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}m={encode_match(payload)}"


def make_qr_image(url):
    """Render the URL as a QR code; returns a PIL image for the PDF.

    Low error correction keeps the module count down so the code stays
    easily scannable at the ~22mm size printed on the scoresheet.
    """
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L,
                       border=2)
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").get_image()
