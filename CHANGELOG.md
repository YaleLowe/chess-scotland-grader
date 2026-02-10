# Changelog

All notable changes to this project will be documented in this file.

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
