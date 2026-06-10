"""Tests for the scoresheet PDF builder."""
import re

import pytest

from scoresheet_pdf import build_scoresheet_pdf, _layout_factor, _latin1


def _row(bd, colour_h="", colour_a=""):
    return {
        'bd': bd,
        'h_forename': 'John', 'h_surname': 'Smith',
        'h_pnum': '1234', 'h_rating': '1500', 'h_colour': colour_h,
        'result': '-',
        'a_colour': colour_a,
        'a_forename': 'Anna', 'a_surname': 'Jones',
        'a_pnum': '5678', 'a_rating': '1600',
    }


def _rounds(n_rounds, n_boards, labelled=False):
    return [
        {'label': f"Round {r + 1}" if labelled else None,
         'rows': [_row(b + 1) for b in range(n_boards)]}
        for r in range(n_rounds)
    ]


def _build(rounds):
    return build_scoresheet_pdf(
        title="Chess Scoresheet: Standard",
        date_str="10 June 2026",
        venue="Stirling Chess Club",
        home_team="Team 1",
        away_team="Team 2",
        rounds=rounds,
        home_captain="John Smith",
        away_captain="Anna Jones",
    )


def _page_count(pdf_bytes):
    # Each page object carries "/Type /Page"; "/Type /Pages" is the root node.
    return len(re.findall(rb"/Type\s*/Page[^s]", pdf_bytes))


class TestBuildScoresheetPdf:
    def test_returns_pdf_bytes(self):
        out = _build(_rounds(1, 4))
        assert isinstance(out, bytes)
        assert out.startswith(b"%PDF")

    def test_single_round_fits_one_page(self):
        assert _page_count(_build(_rounds(1, 8))) == 1

    def test_four_round_all_play_all_fits_one_page(self):
        assert _page_count(_build(_rounds(4, 4, labelled=True))) == 1

    def test_large_all_play_all_breaks_cleanly_across_pages(self):
        out = _build(_rounds(8, 8, labelled=True))
        assert out.startswith(b"%PDF")
        assert _page_count(out) > 1

    def test_blank_rows_and_missing_keys(self):
        out = _build([{'label': None, 'rows': [{'bd': 1}, {}]}])
        assert out.startswith(b"%PDF")

    def test_non_latin1_characters_do_not_crash(self):
        rounds = [{'label': None, 'rows': [dict(_row(1), h_forename="Łukasz")]}]
        out = _build(rounds)
        assert out.startswith(b"%PDF")

    def test_qr_image_fits_on_single_page(self):
        from PIL import Image
        qr = Image.new("1", (57, 57), 1)
        out = build_scoresheet_pdf(
            title="Chess Scoresheet: Standard", date_str="10 June 2026",
            venue="Stirling", home_team="A", away_team="B",
            rounds=_rounds(1, 8), home_captain="", away_captain="",
            qr_image=qr)
        assert out.startswith(b"%PDF")
        assert _page_count(out) == 1

    def test_qr_with_scaled_all_play_all_still_one_page(self):
        from PIL import Image
        qr = Image.new("1", (57, 57), 1)
        out = build_scoresheet_pdf(
            title="Chess Scoresheet: All Play All Allegro",
            date_str="10 June 2026", venue="Stirling",
            home_team="A", away_team="B",
            rounds=_rounds(4, 4, labelled=True),
            home_captain="", away_captain="", qr_image=qr)
        assert _page_count(out) == 1


class TestLayoutFactor:
    def test_single_round_full_size(self):
        assert _layout_factor(_rounds(1, 6)) == (1.0, False)

    def test_four_rounds_shrink_to_one_page(self):
        factor, multi_page = _layout_factor(_rounds(4, 4, labelled=True))
        assert 0.65 <= factor < 1.0
        assert multi_page is False

    def test_too_tall_switches_to_multi_page_at_full_size(self):
        factor, multi_page = _layout_factor(_rounds(8, 8, labelled=True))
        assert factor == 1.0
        assert multi_page is True

    def test_empty_rounds(self):
        assert _layout_factor([]) == (1.0, False)


class TestLatin1:
    @pytest.mark.parametrize("value,expected", [
        (None, ""),
        ("", ""),
        (123, "123"),
        ("José", "José"),
        ("Łukasz", "?ukasz"),
    ])
    def test_conversion(self, value, expected):
        assert _latin1(value) == expected
