"""Tests for match link encoding/decoding and QR generation."""
import pytest
from PIL import Image

from match_link import (build_match_url, decode_match, encode_match,
                        make_qr_image)


SAMPLE = {
    'v': 1, 't': 'A', 'd': '2026-06-10',
    'vn': 'Stirling Chess Club',
    'hn': 'Stirling Wallace', 'an': 'Clackmannanshire',
    'hp': [['Nathanael Loch', '30187', '1581'], ['Leith Macrury', '', ''], 0],
    'ap': [['Glen Wilson', '29257', '1084'], 0, 0],
    'hc': '30187', 'ac': '',
    'o': [1, 1, 0], 'df': 0, 'cr': 'W-B',
}


class TestEncodeDecode:
    def test_round_trip(self):
        assert decode_match(encode_match(SAMPLE)) == SAMPLE

    def test_token_is_url_safe(self):
        token = encode_match(SAMPLE)
        assert all(c.isalnum() or c in "-_" for c in token)

    def test_unicode_names_survive(self):
        payload = dict(SAMPLE, hp=[['José Müller', '1', '900']])
        assert decode_match(encode_match(payload)) == payload

    @pytest.mark.parametrize("bad", ["", "not-a-token", "AAAA", "%%%"])
    def test_garbage_raises_value_error(self, bad):
        with pytest.raises(ValueError):
            decode_match(bad)

    def test_token_is_compact(self):
        # An 8-board match should stay well within easy QR territory.
        payload = dict(SAMPLE)
        payload['hp'] = [[f'Player Number{i}', str(30000 + i), '1500']
                         for i in range(8)]
        payload['ap'] = [[f'Opponent Number{i}', str(20000 + i), '1400']
                         for i in range(8)]
        assert len(encode_match(payload)) < 700


class TestBuildMatchUrl:
    def test_appends_query_param(self):
        url = build_match_url("https://scotgrades.streamlit.app/", SAMPLE)
        assert url.startswith("https://scotgrades.streamlit.app/?m=")

    def test_uses_ampersand_when_query_exists(self):
        url = build_match_url("https://example.com/?x=1", SAMPLE)
        assert "?x=1&m=" in url


class TestMakeQrImage:
    def test_returns_pil_image(self):
        url = build_match_url("https://scotgrades.streamlit.app/", SAMPLE)
        img = make_qr_image(url)
        assert isinstance(img, Image.Image)
        assert img.size[0] > 0
