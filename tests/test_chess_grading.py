"""
Tests for chess_grading.py

Run with: pytest tests/
Network calls are mocked throughout; no internet connection is required.
"""

import pytest
from unittest.mock import patch, MagicMock

import chess_grading
from chess_grading import (
    get_text_safe,
    parse_results,
    get_club_code,
    get_clubs_list,
    get_player_grading,
    parse_queries,
    clean_input_text,
    _clean_name,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_HTML = """
<table>
  <tr>
    <td class="screen_large screen_medium" data-column="pnum">12345</td>
    <td class="left_align" data-column="name">Loch, Nathanael</td>
    <td class="screen_large">ST</td>
    <td data-column="status">A</td>
    <td data-column="standard_published">1650</td>
    <td data-column="standard_live">1680</td>
    <td data-column="allegro_published"></td>
    <td data-column="allegro_live"></td>
    <td data-column="blitz_published">&mdash;</td>
    <td data-column="blitz_live"></td>
  </tr>
  <tr>
    <td class="screen_large screen_medium" data-column="pnum">99999</td>
    <td class="left_align" data-column="name">Smith, John</td>
    <td class="screen_large">ED</td>
    <td data-column="status">J15</td>
    <td data-column="standard_published">900</td>
    <td data-column="standard_live">920</td>
    <td data-column="allegro_published"></td>
    <td data-column="allegro_live"></td>
    <td data-column="blitz_published"></td>
    <td data-column="blitz_live"></td>
  </tr>
</table>
"""


# ---------------------------------------------------------------------------
# get_text_safe
# ---------------------------------------------------------------------------

class TestGetTextSafe:
    def test_returns_empty_for_none(self):
        assert get_text_safe(None) == ""

    def test_returns_text_from_tag(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<td>1650</td>", 'lxml')
        assert get_text_safe(soup.find('td')) == "1650"

    def test_returns_empty_for_dash(self):
        from bs4 import BeautifulSoup
        for dash in ['-', '—', '&mdash;']:
            soup = BeautifulSoup(f"<td>{dash}</td>", 'lxml')
            assert get_text_safe(soup.find('td')) == ""

    def test_returns_empty_for_blank(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<td></td>", 'lxml')
        assert get_text_safe(soup.find('td')) == ""


# ---------------------------------------------------------------------------
# parse_results
# ---------------------------------------------------------------------------

class TestParseResults:
    def test_empty_html_returns_empty_list(self):
        assert parse_results("") == []
        assert parse_results(None) == []

    def test_parses_player_fields(self):
        results = parse_results(SAMPLE_HTML)
        assert len(results) == 2

        player = results[0]
        assert player['pnum'] == "12345"
        assert player['name'] == "Loch, Nathanael"
        assert player['club'] == "ST"
        assert player['age'] == "Adult"
        assert player['standard_published'] == "1650"
        assert player['standard_live'] == "1680"

    def test_blitz_dash_returns_empty_string(self):
        results = parse_results(SAMPLE_HTML)
        assert results[0]['blitz_published'] == ""

    def test_junior_age_strips_j_prefix(self):
        results = parse_results(SAMPLE_HTML)
        assert results[1]['age'] == "15"

    def test_no_surname_filter_applied(self):
        # parse_results must NOT filter by name — all rows from backend are kept
        results = parse_results(SAMPLE_HTML)
        names = [r['name'] for r in results]
        assert "Loch, Nathanael" in names
        assert "Smith, John" in names


# ---------------------------------------------------------------------------
# get_club_code
# ---------------------------------------------------------------------------

class TestGetClubCode:
    def setup_method(self):
        # Reset CLUB_DATA before each test and reload from actual file
        chess_grading.CLUB_DATA = {}
        chess_grading.load_club_data()

    def test_two_char_known_code_uppercase(self):
        assert get_club_code("ST") == "ST"

    def test_two_char_known_code_lowercase(self):
        assert get_club_code("st") == "ST"

    def test_two_char_unknown_string_falls_through_to_name_match(self):
        # "XX" is not a known code; should return "" since no name matches either
        result = get_club_code("XX")
        assert result == ""

    def test_exact_name_match(self):
        assert get_club_code("Stirling") == "ST"

    def test_exact_name_match_case_insensitive(self):
        assert get_club_code("stirling") == "ST"

    def test_partial_name_match(self):
        # "Stir" is a substring of "Stirling"
        assert get_club_code("Stir") == "ST"

    def test_partial_match_prefers_shorter_name(self):
        # "Stirling" should match "Stirling" (ST) over "Stirling University" (SU)
        assert get_club_code("Stirling") == "ST"

    def test_empty_query_returns_empty(self):
        assert get_club_code("") == ""

    def test_no_match_returns_empty(self):
        assert get_club_code("ZZZNoSuchClub") == ""


# ---------------------------------------------------------------------------
# get_clubs_list
# ---------------------------------------------------------------------------

class TestGetClubsList:
    def setup_method(self):
        chess_grading.CLUB_DATA = {}

    def test_returns_list_of_dicts(self):
        clubs = get_clubs_list()
        assert isinstance(clubs, list)
        assert len(clubs) > 0

    def test_entries_have_name_and_code(self):
        clubs = get_clubs_list()
        for club in clubs:
            assert 'name' in club
            assert 'code' in club

    def test_stirling_present(self):
        clubs = get_clubs_list()
        codes = [c['code'] for c in clubs]
        assert 'ST' in codes

    def test_display_name_properly_cased(self):
        clubs = get_clubs_list()
        names = [c['name'] for c in clubs]
        assert 'Stirling' in names  # Not 'stirling'


# ---------------------------------------------------------------------------
# get_player_grading — routing logic (mocked network)
# ---------------------------------------------------------------------------

class TestGetPlayerGrading:
    """Tests that the correct API calls are made for each query type."""

    def _make_session_mock(self):
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {'html': SAMPLE_HTML}
        mock_response.raise_for_status.return_value = None
        mock_session.post.return_value = mock_response
        return mock_session

    @patch('chess_grading.get_session_and_token')
    def test_pnum_search_sends_pnum_field(self, mock_init):
        mock_session = self._make_session_mock()
        mock_init.return_value = (mock_session, 'fake_token')

        queries = [{'raw': 'test [12345]', 'pnum': '12345', 'name': '', 'club': '', 'is_single': False}]
        result = get_player_grading(queries)

        call_kwargs = mock_session.post.call_args
        payload = call_kwargs[1]['files']
        assert payload['pnum'] == (None, '12345')
        assert payload['forename'] == (None, '')
        assert payload['surname'] == (None, '')

    @patch('chess_grading.get_session_and_token')
    def test_pnum_result_has_match_type_pnum(self, mock_init):
        mock_session = self._make_session_mock()
        mock_init.return_value = (mock_session, 'fake_token')

        queries = [{'raw': '[12345]', 'pnum': '12345', 'name': '', 'club': '', 'is_single': False}]
        result = get_player_grading(queries)

        for match in result['[12345]']:
            assert match.get('match_type') == 'pnum'

    @patch('chess_grading.get_session_and_token')
    def test_multiword_name_tries_all_permutations(self, mock_init):
        mock_session = self._make_session_mock()
        mock_init.return_value = (mock_session, 'fake_token')

        queries = [{'raw': 'nat loc', 'name': 'nat loc', 'club': '', 'is_single': False}]
        get_player_grading(queries)

        # Should make 2 calls: (forename=loc, surname=nat) and (forename=nat, surname=loc)
        assert mock_session.post.call_count == 2
        payloads = [call[1]['files'] for call in mock_session.post.call_args_list]
        forenames = {p['forename'][1] for p in payloads}
        surnames = {p['surname'][1] for p in payloads}
        assert forenames == {'nat', 'loc'}
        assert surnames == {'nat', 'loc'}

    @patch('chess_grading.get_session_and_token')
    def test_single_token_makes_two_requests(self, mock_init):
        mock_session = self._make_session_mock()
        mock_init.return_value = (mock_session, 'fake_token')

        queries = [{'raw': 'Loch', 'name': 'Loch', 'club': '', 'is_single': True}]
        get_player_grading(queries)

        assert mock_session.post.call_count == 2

    @patch('chess_grading.get_session_and_token')
    def test_name_result_has_match_type_name(self, mock_init):
        mock_session = self._make_session_mock()
        mock_init.return_value = (mock_session, 'fake_token')

        queries = [{'raw': 'nat loc', 'name': 'nat loc', 'club': '', 'is_single': False}]
        result = get_player_grading(queries)

        for match in result['nat loc']:
            assert match.get('match_type') == 'name'

    @patch('chess_grading.get_session_and_token')
    def test_short_name_returns_invalid_marker(self, mock_init):
        mock_session = self._make_session_mock()
        mock_init.return_value = (mock_session, 'fake_token')

        # "Xq" is 2 chars and not a known club code, so it must hit the min-3-chars guard
        queries = [{'raw': 'Xq', 'name': 'Xq', 'club': '', 'is_single': True}]
        result = get_player_grading(queries)

        assert result['Xq'] == [{'invalid_query': True}]

    @patch('chess_grading.get_session_and_token')
    def test_failed_session_returns_empty_dict(self, mock_init):
        mock_init.return_value = (None, None)

        queries = [{'raw': 'John Smith', 'name': 'John Smith', 'club': '', 'is_single': False}]
        result = get_player_grading(queries)

        assert result == {}


# ---------------------------------------------------------------------------
# _clean_name
# ---------------------------------------------------------------------------

class TestCleanName:
    def test_strips_parenthesised_content(self):
        assert _clean_name("John Smith (1513)") == "John Smith"

    def test_strips_leading_numbers_and_period(self):
        assert _clean_name("1. John Smith") == "John Smith"

    def test_strips_all_numbers_outside_brackets(self):
        assert _clean_name("3 John Smith 42") == "John Smith"

    def test_normalises_surname_forename(self):
        assert _clean_name("Smith, John") == "John Smith"

    def test_removes_commas_and_special_chars(self):
        assert _clean_name("John! Smith@") == "John Smith"

    def test_preserves_hyphens_and_apostrophes(self):
        assert _clean_name("O'Brien-Smith") == "O'Brien-Smith"

    def test_collapses_whitespace(self):
        assert _clean_name("  John   Smith  ") == "John Smith"

    def test_complex_example(self):
        assert _clean_name("1. Smith, John (1513)") == "John Smith"

    def test_empty_string(self):
        assert _clean_name("") == ""


# ---------------------------------------------------------------------------
# parse_queries
# ---------------------------------------------------------------------------

class TestParseQueries:
    def test_simple_name(self):
        queries, lines = parse_queries("John Smith")
        assert len(queries) == 1
        assert queries[0]['name'] == "John Smith"
        assert queries[0]['club'] == ""

    def test_pnum_in_brackets(self):
        queries, lines = parse_queries("[12345]")
        assert len(queries) == 1
        assert queries[0]['pnum'] == "12345"

    def test_pnum_with_name(self):
        queries, lines = parse_queries("John Smith [12345]")
        assert queries[0]['pnum'] == "12345"

    def test_semicolon_club(self):
        queries, lines = parse_queries("John Smith; st")
        assert queries[0]['name'] == "John Smith"
        assert queries[0]['club'] == "st"

    def test_colon_sets_sticky_club(self):
        queries, lines = parse_queries("st:\nJohn Smith\nJane Doe")
        assert len(queries) == 2
        assert queries[0]['club'] == "st"
        assert queries[1]['club'] == "st"

    def test_colon_override(self):
        queries, lines = parse_queries("st:\nJohn Smith\ngr:\nJane Doe")
        assert queries[0]['club'] == "st"
        assert queries[1]['club'] == "gr"

    def test_colon_with_name_on_same_line(self):
        queries, lines = parse_queries("st: John Smith")
        assert len(queries) == 1
        assert queries[0]['name'] == "John Smith"
        assert queries[0]['club'] == "st"

    def test_semicolon_overrides_sticky(self):
        queries, lines = parse_queries("st:\nJohn Smith; gr")
        assert queries[0]['club'] == "gr"

    def test_dirty_input_cleaned(self):
        queries, lines = parse_queries("1. John Smith (1513)")
        assert queries[0]['name'] == "John Smith"

    def test_empty_lines_skipped(self):
        queries, lines = parse_queries("\n\nJohn Smith\n\n")
        assert len(queries) == 1

    def test_club_only_search_with_semicolon(self):
        queries, lines = parse_queries("; ST")
        assert len(queries) == 1
        assert queries[0]['name'] == ""
        assert queries[0]['club'] == "ST"

    def test_is_single_flag(self):
        queries, _ = parse_queries("Loch")
        assert queries[0]['is_single'] is True
        queries2, _ = parse_queries("John Smith")
        assert queries2[0]['is_single'] is False

    def test_colon_directive_not_in_valid_lines(self):
        queries, lines = parse_queries("st:\nJohn Smith")
        assert len(lines) == 1
        assert lines[0] == "John Smith"

    def test_sticky_club_applies_to_pnum(self):
        queries, _ = parse_queries("st:\n[12345]")
        assert queries[0]['pnum'] == "12345"
        assert queries[0]['club'] == "st"

    def test_multiple_colon_groups(self):
        text = "st:\nAlice\nBob\ngr:\nCharlie\nDave"
        queries, _ = parse_queries(text)
        assert len(queries) == 4
        assert queries[0]['club'] == "st"
        assert queries[1]['club'] == "st"
        assert queries[2]['club'] == "gr"
        assert queries[3]['club'] == "gr"


# ---------------------------------------------------------------------------
# clean_input_text
# ---------------------------------------------------------------------------

class TestCleanInputText:
    def test_strips_leading_number_and_rating(self):
        assert clean_input_text("1. Nathanael Loch (1513)") == "Nathanael Loch"

    def test_normalises_surname_forename(self):
        assert clean_input_text("Smith, John") == "John Smith"

    def test_preserves_colon_directive(self):
        assert clean_input_text("st:") == "st:"

    def test_preserves_colon_with_name(self):
        assert clean_input_text("st: 1. John Smith (1513)") == "st: John Smith"

    def test_preserves_semicolon_club(self):
        assert clean_input_text("John Smith; st") == "John Smith; st"

    def test_preserves_pnum_brackets(self):
        assert clean_input_text("[12345]") == "[12345]"

    def test_strips_name_from_pnum_line(self):
        # PNUM lines keep only the bracket
        assert clean_input_text("John Smith [12345]") == "[12345]"

    def test_multiline_cleaning(self):
        raw = "st:\n1. John Smith (1513)\n2. Jane Doe (900)"
        expected = "st:\nJohn Smith\nJane Doe"
        assert clean_input_text(raw) == expected

    def test_empty_lines_removed(self):
        assert clean_input_text("\n\nJohn Smith\n\n") == "John Smith"

    def test_complex_mixed_input(self):
        raw = "st:\n1. Smith, John (1513)\n[12345]\ngr:\nJane Doe; ed"
        expected = "st:\nJohn Smith\n[12345]\ngr:\nJane Doe; ed"
        assert clean_input_text(raw) == expected
