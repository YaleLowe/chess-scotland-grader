# Changelog

All notable changes to this project will be documented in this file.

## [2026-06-10]

### Added
- **Sheet Options**: New "Sheet Options" expander in the Scoresheet Maker with toggles for which fields are pre-filled on the printout — **PNUMs**, **Ratings**, and **Colours (w/b)**. Unticked fields are left blank for filling in by hand on the day. Colours apply to All Play All Allegro sheets only (Standard sheets always leave w/b blank).
- **`scoresheet_pdf.py`**: New module that renders the scoresheet with `fpdf2`, plus a test suite (`tests/test_scoresheet_pdf.py`) covering layout fitting, page counts, blank rows, and non-latin-1 names.
- **Board results entry**: Standard matches get a Result column between the two team boxes (one dropdown per board); All Play All gets a results grid below the teams with one column per round. Options are `1 - 0`, `0.5 - 0.5`, `0 - 1`, and defaults `1 - D` / `D - 1` / `D - D`. Defaults score per the league convention: a present player beats an absent one 1 - 0; a double default is scored as a 0.5 - 0.5 draw.
- **Match Email generator (`match_email.py`)**: A new "Match Email" section below the PDF download renders a ready-to-copy results email in the club submission format (see `example_emails.md`): title line with final score, per-round result lines with `Name [pnum] (rating)` (or `(ung)` when unrated), round/cumulative scores, `Final score` after the last round, and `(absent)` markers beside defaulted players (named or not). Unentered results render as `_` to fill in. Covered by `tests/test_match_email.py`, including a full reconstruction of example 1.
- **Final score check**: The final score auto-fills from the entered board results; the user can type one in instead, and the app warns when it doesn't add up against the board results (and reports how many results are still missing).
- **Match link & QR code (`match_link.py`)**: The match setup (teams, players with PNUMs/ratings, board order, captains, venue, date, tournament type, sheet options, drawn colours) is compressed into the `?m=` query parameter of the app URL — no server-side storage, the link *is* the data. The scoresheet PDF prints this as a QR code beside the signatures: scanning the printed sheet with any phone camera reopens the app fully prefilled, ready for results entry. The same link is shown in a "Match link & QR code" expander for copying/bookmarking (and works on any host, e.g. localhost during development). A typical link is ~300 characters; corrupt or truncated links show a warning instead of crashing. Added `qrcode` to requirements and `tests/test_match_link.py`. The PDF signature block (and QR) now stays full size when the rest of the sheet shrinks to fit one page, so signatures stay writable and the QR stays scannable.
- **Manual colour entry**: Standard matches get a w/b dropdown per board (home player's colour; away inferred as the opposite). For All Play All with auto colours unticked, each round column in the Results grid gets an "Away colour" dropdown matching how colours are drawn for a whole team per round (e.g. a WWBB draw). Entered colours feed both the PDF's w/b cells and the email — round headers (`Round 1 B/W:`) for All Play All, `(B)`/`(W)` after player names for Standard. Defaulted players show no colour.
- **Date format option**: Sheet Options now has a date format selector — `2026 March 30` (default), `30 March 2026`, `30/03/2026`, `30/03/26` — applied to both the PDF scoresheet and the match email. (Previously the scoresheet was hardcoded to `30 March 2026`.)

### Changed
- **Scoresheet output is now a downloadable PDF**: The browser-print button (new tab + `window.print()`) is replaced by a "Download Scoresheet (PDF)" button that generates a deterministic A4 landscape PDF with `fpdf2`. Browser printing was the source of repeated platform quirks: mobile browsers ignore the landscape `@page` hint and split the sheet across pages, and Chromium's save-as-PDF clipped the rightmost table border when CSS scale transforms were involved. The generated PDF always fills the printable width exactly, shrinks the whole layout to keep multi-round All Play All sheets on one page where readable, and otherwise flows across pages breaking only between rounds (signature block kept together). Users print the PDF at 100% scale from any device.

### Removed
- **Stale review documents**: Deleted `CODE_REVIEW.md` and `FIX_PLAN.md` — working documents from the 2026-03-09 code review whose fixes have long been applied. Removed references to them from the readme and added `.pytest_cache/` to `.gitignore`.

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
