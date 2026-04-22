# Changelog

All notable changes to this project will be documented in this file.

## [2026-04-22]

### Added
- **Scoresheet Maker**: New section below the copy boxes for setting up a Home vs Away match scoresheet. Includes editable team names (default `Team 1` / `Team 2`), a venue field, and a date field defaulting to today.
- **Team rosters**: Players from the current search are auto-split into Home (first half) and Away (second half). Each player row has three controls:
  - **Star (`☆` / `⭐`)** — set or clear team captain.
  - **Name button** — click to move the player to the other team.
  - **Up arrow (`⬆️`)** — move the player up one board, wrapping to the bottom from the top.
- **Sort by rating**: A `🔽` button at the top-right of each team box sorts that team's players by the currently-displayed rating (highest first).
- **Compact player labels**: Players in the team boxes are shown as `N. Loch [30187] (1515)` — first initial of the first forename, surname, PNUM in brackets, and the highest-priority visible rating in parens. Saves space on mobile.
- **Printable scoresheet**: A "Print Scoresheet" button opens the match scoresheet in a new browser tab (A4 landscape) and triggers the print dialog, which can save as PDF or send to a printer. Layout includes title/date/venue header, team names aligned over the home and away halves of a 12-column board table (BD, Forename, Surname, PNUM, Rating, w/b, Result, w/b, Forename, Surname, PNUM, Rating), pre-filled player data, captain name fields, and signature lines. Empty fields show writable underlines; result and total cells have a centred `-` to hint where to write the score.
- **Stable team identity**: Team membership, order, and captain are keyed by PNUM internally, so toggling rating checkboxes updates labels but does not reset the user's team setup.
- **`parse_queries`**: Moved from `app.py` into `chess_grading.py` and extended with sticky-club colon syntax (`st:` applies club `ST` to all following lines until overridden) and per-line semicolon overrides (`Name; club`).
- **`clean_input_text`**: Cleans the raw text-area input for display — strips parenthesised content, stray numbers, periods, and disallowed characters while preserving structural syntax (colons, semicolons, square brackets) and normalising `Surname, Forename` to `Forename Surname`.

### Improved
- **Multi-word name search**: Now tries each word as the surname (with the remainder as forename), catching both `John Smith` and `Smith John` style entries instead of always assuming the last token is the surname.
- **Tests**: Expanded `tests/test_chess_grading.py` to cover `parse_queries`, `clean_input_text`, and the multi-word search behaviour.

## [2026-03-09]

### Added
- **Test Suite**: Added `tests/test_chess_grading.py` with 29 pytest tests covering `get_text_safe`, `parse_results`, `get_club_code`, `get_clubs_list`, and `get_player_grading`. All network calls are mocked; no internet connection required to run.
- **Code Review & Fix Plan**: Added `CODE_REVIEW.md` and `FIX_PLAN.md` documenting identified issues and their resolutions.

### Improved
- **Search Logic**: Removed redundant client-side `surname_filter` post-processing in `parse_results`. The Chess Scotland backend already handles partial name matching natively; the client filter was duplicating this and could produce false positives.
- **Club Data**: `CLUB_DATA` now stores both the club code and the properly-cased display name, eliminating a second file read that `get_clubs_list` previously required.
- **Club Code Validation**: `get_club_code` now validates 2-character inputs against the known list before accepting them as codes, rather than treating any 2-char string as a valid code unconditionally.
- **Match Type Tagging**: Results from `chess_grading.py` now carry a `match_type` field (`'pnum'` or `'name'`) set at the source, removing the need for app.py to retrofit flags onto returned data.
- **Result Metrics**: Renamed metric labels for clarity — "Confident Matches", "Total Players Found", and "Not Found / Invalid".
- **Copy Sorting**: Single-line copy now sorts alphabetically by player name only, not by the full formatted string (which previously caused inconsistent ordering when grades or PNUMs were included).
- **Error Reporting**: Network failures now surface as a visible `st.error` message instead of silently showing all players as not found.
- **Dependencies**: Pinned all dependency versions in `requirements.txt`. Added `lxml` as the BeautifulSoup parser and `pytest` for testing.

### Fixed
- **Duplicate Function**: Removed the incomplete `get_player_grading` stub that was defined twice in `chess_grading.py`.
- **Broken CLI**: Fixed the `__main__` block in `chess_grading.py`, which was passing plain strings to `get_player_grading` instead of the required query dicts.
- **File Path**: `club_names.txt` is now located relative to the script file using `os.path.abspath(__file__)`, fixing a crash when the app was launched from a different working directory.
- **Loop-scoped Code**: Moved `get_text_safe` out of the `parse_results` row loop (it was being redefined on every iteration). Moved `import re` to the top of `app.py` (it was inside the input parsing loop).
- **Parser**: Specified `lxml` explicitly in all `BeautifulSoup(...)` calls instead of relying on the slower default `html.parser`.
- **Error Logging**: Replaced bare `print()` error calls in `chess_grading.py` with `logging.error` / `logging.warning`.

### Removed
- `reproduce_issue.py` and `verify_phase4.py`: Ad-hoc debug scripts deleted and replaced by the formal test suite.

## [2026-02-10]

### Added
- **Search History**: Implemented "Previous" and "Next" buttons to navigate through past search queries within the session.
- **PNUM Search**: Added support for direct player number searches using the `[PNUM]` format (e.g., `John Smith [12345]`).
- **Club-only Search**: Users can now search for all players in a club by prefixing the input with a semicolon (e.g., `; Stirling` or `; ST`).
- **Result Tallies**: Added metrics at the top of the results section to show the count of Exact Matches, Possible Matches, and Non-existent/Invalid queries.
- **Club Reference**: Added a sidebar table showing all club names and their abbreviations for quick reference.

### Improved
- **Input Parsing**: 
    - Automatically normalizes `Surname, Forename` to `Forename Surname`.
    - Handles semicolon-delimited club filters more robustly.
    - Improved name cleanup to ignore existing grading info in parentheses.
- **Copy to Clipboard**:
    - Refined the "Copy formatted lists" logic with a clear grade priority: Standard Published > Standard Live > Allegro Published > Allegro Live > Blitz Published > Blitz Live.
    - Respects visibility settings (e.g., hides PNUM if the checkbox is unchecked).
    - Sorts Multi-line Copy by grade (descending) and Single Line Copy alphabetically.
- **UI/UX**:
    - Enhanced club display in the results table to show `Code (FullName)` for better readability.
    - Set default sorting and numeric conversion for grade columns.
    - "Pnum" checkbox now defaults to visible.

### Fixed
- **UnboundLocalError**: Resolved an issue in `chess_grading.py` where `is_invalid` was referenced before assignment during PNUM searches.
- **Club Membership Display**: Fixed a bug where multiple club memberships (e.g., "DN, CW") were displayed as raw codes; they are now correctly expanded to full names.
- **Search Width**: Adjusted table layout to use the full container width.

### Removed
- `test_parsing.py`: Replaced by `reproduce_issue.py` for focused debugging.
