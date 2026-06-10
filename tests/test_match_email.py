"""Tests for the match email builder."""
import pytest

from match_email import (RESULT_OPTIONS, build_match_email, compute_totals,
                         format_points)


def _p(name, pnum="", rating=""):
    return {'name': name, 'pnum': pnum, 'rating': rating}


def _pair(home, away, result):
    return {'home': home, 'away': away, 'result': result}


NL = _p("Nathanael Loch", "30187", "1581")
LM = _p("Leith Macrury")
IM = _p("Iain Macrury")
GW = _p("Glen Wilson", "29257", "1084")
AC = _p("Aidan Cameron", "33265")
RQ = _p("Roman Quinn", "32923")


def _example_one_rounds():
    """Example 1 from example_emails.md: 4-board all play all with two
    completely absent (unnamed) players, one on each team."""
    return [
        {'colours': 'B/W', 'pairs': [
            _pair(NL, GW, "1 - 0"),
            _pair(LM, AC, "0 - 1"),
            _pair(IM, RQ, "1 - 0"),
            _pair(None, None, "D - D"),
        ]},
        {'colours': 'W/B', 'pairs': [
            _pair(None, GW, "D - 1"),
            _pair(NL, AC, "1 - 0"),
            _pair(LM, RQ, "1 - 0"),
            _pair(IM, None, "1 - D"),
        ]},
        {'colours': 'B/W', 'pairs': [
            _pair(IM, GW, "0 - 1"),
            _pair(None, AC, "D - 1"),
            _pair(NL, RQ, "1 - 0"),
            _pair(LM, None, "1 - D"),
        ]},
        {'colours': 'W/B', 'pairs': [
            _pair(LM, GW, "0 - 1"),
            _pair(IM, AC, "1 - 0"),
            _pair(None, RQ, "D - 1"),
            _pair(NL, None, "1 - D"),
        ]},
    ]


class TestExampleOne:
    def test_full_email(self):
        text = build_match_email(
            "Stirling Wallace", "Clackmannanshire", "25/05/26",
            _example_one_rounds(), is_all_play_all=True)
        lines = text.splitlines()

        assert lines[0] == ("Stirling Wallace (home) 9.5 - 6.5 "
                            "Clackmannanshire (away), 25/05/26.")
        assert "Round 1 B/W:" in lines
        assert "Round 2 W/B:" in lines
        assert "Nathanael Loch [30187] (1581) 1 - 0 Glen Wilson [29257] (1084)" in lines
        assert "Leith Macrury (ung) 0 - 1 Aidan Cameron [33265] (ung)" in lines
        # Double default: both unnamed players shown as (absent), drawn.
        assert "(absent) 0.5 - 0.5 (absent)" in lines
        # Unnamed absent player loses to a present one.
        assert "(absent) 0 - 1 Glen Wilson [29257] (1084)" in lines
        assert "Iain Macrury (ung) 1 - 0 (absent)" in lines
        assert "Round 1 score: 2.5 - 1.5" in lines
        assert "Cumulative score: 2.5 - 1.5" in lines
        assert "Round 2 score: 3 - 1" in lines
        assert "Cumulative score: 5.5 - 2.5" in lines
        assert "Round 4 score: 2 - 2" in lines
        assert lines[-1] == "Final score: 9.5 - 6.5"

    def test_totals(self):
        per_round, total, missing = compute_totals(_example_one_rounds())
        assert total == (9.5, 6.5)
        assert missing == 0
        assert [(h, a) for h, a, _ in per_round] == [
            (2.5, 1.5), (3, 1), (2, 2), (2, 2)]


class TestNamedAbsentPlayers:
    def test_named_absent_player_gets_absent_marker(self):
        rounds = [{'colours': None, 'pairs': [_pair(NL, GW, "D - 1")]}]
        text = build_match_email("A", "B", "1/1/26", rounds,
                                 is_all_play_all=False)
        assert ("Nathanael Loch [30187] (1581) (absent) 0 - 1 "
                "Glen Wilson [29257] (1084)") in text

    def test_both_named_absent_players_draw(self):
        rounds = [{'colours': None, 'pairs': [_pair(LM, AC, "D - D")]}]
        text = build_match_email("A", "B", "1/1/26", rounds,
                                 is_all_play_all=False)
        assert ("Leith Macrury (ung) (absent) 0.5 - 0.5 "
                "Aidan Cameron [33265] (ung) (absent)") in text


class TestMissingResults:
    def test_blanks_rendered_and_title_has_no_score(self):
        rounds = [{'colours': 'B/W', 'pairs': [
            _pair(NL, GW, "1 - 0"),
            _pair(IM, RQ, ""),
        ]}]
        text = build_match_email("A", "B", "1/1/26", rounds,
                                 is_all_play_all=True)
        assert text.startswith("A (home) vs B (away), 1/1/26.")
        assert "Iain Macrury (ung) _ - _ Roman Quinn [32923] (ung)" in text
        assert "Round 1 score: _ - _" in text
        assert "Final score: _ - _" in text

    def test_final_override_used_despite_missing(self):
        rounds = [{'colours': None, 'pairs': [_pair(NL, GW, "")]}]
        text = build_match_email("A", "B", "1/1/26", rounds,
                                 is_all_play_all=True, final_score=(2.5, 1.5))
        assert text.startswith("A (home) 2.5 - 1.5 B (away), 1/1/26.")
        assert "Final score: 2.5 - 1.5" in text

    def test_unentered_unnamed_pairing_renders_blanks(self):
        rounds = [{'colours': None, 'pairs': [_pair(None, None, "")]}]
        text = build_match_email("A", "B", "1/1/26", rounds,
                                 is_all_play_all=False)
        assert "______ _ - _ ______" in text


class TestColours:
    def test_standard_per_board_colours_after_names(self):
        rounds = [{'colours': None, 'pairs': [
            dict(_pair(NL, GW, "1 - 0"), home_colour="B", away_colour="W"),
        ]}]
        text = build_match_email("A", "B", "1/1/26", rounds,
                                 is_all_play_all=False)
        assert ("Nathanael Loch [30187] (1581) (B) 1 - 0 "
                "Glen Wilson [29257] (1084) (W)") in text

    def test_defaulted_player_has_no_colour(self):
        rounds = [{'colours': None, 'pairs': [
            dict(_pair(NL, GW, "1 - D"), home_colour="W", away_colour="B"),
        ]}]
        text = build_match_email("A", "B", "1/1/26", rounds,
                                 is_all_play_all=False)
        assert ("Nathanael Loch [30187] (1581) (W) 1 - 0 "
                "Glen Wilson [29257] (1084) (absent)") in text

    def test_round_without_colours_has_plain_header(self):
        rounds = [{'colours': None, 'pairs': [_pair(NL, GW, "1 - 0")]}]
        text = build_match_email("A", "B", "1/1/26", rounds,
                                 is_all_play_all=True)
        assert "Round 1:" in text.splitlines()


class TestStandardFormat:
    def test_board_blocks(self):
        rounds = [{'colours': None, 'pairs': [
            _pair(NL, GW, "1 - 0"),
            _pair(IM, RQ, "0.5 - 0.5"),
        ]}]
        text = build_match_email("Stirling C", "Stirling E", "2026 March 30",
                                 rounds, is_all_play_all=False)
        lines = text.splitlines()
        assert lines[0] == ("Stirling C (home) 1.5 - 0.5 Stirling E (away), "
                            "2026 March 30.")
        assert lines[2] == "Board 1:"
        assert lines[3] == ("Nathanael Loch [30187] (1581) 1 - 0 "
                            "Glen Wilson [29257] (1084)")
        assert lines[4] == "Board 2:"
        assert lines[5] == ("Iain Macrury (ung) 0.5 - 0.5 "
                            "Roman Quinn [32923] (ung)")
        # Standard emails carry no round/final lines; title holds the score.
        assert "Final score" not in text


class TestFormatPoints:
    @pytest.mark.parametrize("value,expected", [
        (0.0, "0"), (1.0, "1"), (0.5, "0.5"), (2.5, "2.5"), (9.5, "9.5"),
        (3, "3"),
    ])
    def test_format(self, value, expected):
        assert format_points(value) == expected


def test_result_options_cover_all_outcomes():
    assert RESULT_OPTIONS == ["", "1 - 0", "0.5 - 0.5", "0 - 1",
                              "1 - D", "D - 1", "D - D"]
