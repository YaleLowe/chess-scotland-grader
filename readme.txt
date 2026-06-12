========================================================================
CHESS SCOTLAND GRADING LOOKUP - USER GUIDE
========================================================================

Welcome to the Chess Scotland Grading Lookup tool. This application is
designed to help you quickly find and format grading information for
players and teams.

------------------------------------------------------------------------
1. HOW TO START THE APP
------------------------------------------------------------------------
To run the application locally, open your terminal in the project
directory and run:

    python -m streamlit run app.py

A new tab will open in your web browser with the interface.

To install dependencies on a fresh machine:

    pip install -r requirements.txt

------------------------------------------------------------------------
2. SEARCHING FOR PLAYERS
------------------------------------------------------------------------
Enter one search per line in the large text area. Multiple formats
are supported and can be mixed freely.

A. Name Search:
   Type the player's name. Both name orders are accepted.
   Examples:
     Nathanael Loch
     Smith, John

   Partial names work — the Chess Scotland backend supports partial
   matching on both forename and surname fields.
   Example: "nat loc" will find "Nathanael Loch"

B. PNUM Search (Player Number):
   If you know a player's ID, put it in square brackets. The name
   is optional and will be ignored — only the ID is used.
   Examples:
     John Smith [12345]
     [12345]

C. Club Filter:
   Add a semicolon followed by a club name or code to restrict a
   name search to a specific club.
   Examples:
     John; ST        (searches for "John" within Stirling)
     John; Stirling  (same — full name or code both work)

D. Club-only Search:
   To list all players in a club, use just a semicolon with no name.
   Examples:
     ; Stirling
     ; ST

E. 2-Letter Club Code Shortcut:
   Typing a recognised 2-letter club code on its own will perform a
   club-only search automatically.
   Example: "ST" is equivalent to "; ST"

------------------------------------------------------------------------
3. NAVIGATION & HISTORY
------------------------------------------------------------------------
- PREVIOUS / NEXT: Use the arrow buttons at the top to cycle through
  searches you have run during this session. Useful for switching
  between two team lists without retyping.
- CACHING: Results are cached for the session. Re-submitting the same
  name does not make a new network request.
- REFRESH: To force a fresh fetch for a name, clear the cache by
  refreshing the browser tab, then search again.

------------------------------------------------------------------------
4. DATA OPTIONS
------------------------------------------------------------------------
Below the text area, use the checkboxes to choose what columns to show:

  GENERAL   — PNUM, Club, Age
  STANDARD  — Published grade, Live grade
  ALLEGRO   — Published grade, Live grade
  BLITZ     — Published grade, Live grade

"Pnum" is shown by default as it is needed for the copy format.

------------------------------------------------------------------------
5. UNDERSTANDING RESULTS
------------------------------------------------------------------------
The Match Status column shows one of four icons:

  ✅            — Single exact match found.
  ⚠️ Multiple  — More than one player found. Check the PNUM column
                  to identify the correct player.
  ⚠️ PNUM Only — Matched by the player number you provided.
  ❌            — No player found, or the query was invalid.

METRICS (above the table):
  Confident Matches  — Rows with ✅ or ⚠️ PNUM Only status.
  Total Players Found — All unique valid players returned.
  Not Found / Invalid — Queries with no result or fewer than 3 chars.

DEDUPLICATION: If the same player appears from two different input
lines (e.g. a name search and a PNUM search), only one row is kept.
A confident match (✅) always takes priority over ⚠️ Multiple.

------------------------------------------------------------------------
6. COPYING TO CLIPBOARD
------------------------------------------------------------------------
Scroll to the bottom to find pre-formatted lists ready for copy-pasting
into emails or tournament software.

  MULTI-LINE COPY  — One player per line, sorted by grade (highest
                     first). Use this for email team sheets.

  SINGLE LINE COPY — Comma-separated, sorted alphabetically by player
                     name. Use this for tournament entry forms.

FORMAT: "Forename Surname [Pnum] (Grade)"

The grade shown is the highest-priority visible grade based on your
checkbox selections: Standard Published > Standard Live > Allegro
Published > Allegro Live > Blitz Published > Blitz Live.

Unchecking "Pnum" removes the [Pnum] from the copy output.
If no grade column is checked, the grade is omitted entirely.

------------------------------------------------------------------------
7. CLUB REFERENCE
------------------------------------------------------------------------
The Sidebar (on the left) shows a full list of club names and their
2-letter codes. You can use either form in any search field.

------------------------------------------------------------------------
8. SCORESHEET MAKER
------------------------------------------------------------------------
Below the copy section, the Scoresheet Maker turns your search results
into a printable match scoresheet.

  TOURNAMENT TYPE — "Standard" (one round) or "All Play All Allegro"
                    (one round per board, with rotating pairings and
                    alternating colours).

  SHEET OPTIONS   — Choose which fields are pre-filled on the printout:
                    PNUMs, Ratings, and Colours (w/b). Untick a field
                    to leave it blank for filling in by hand on the day.

  TEAMS           — Click a player's name to move them to the other
                    team, the star to mark them as captain (the button
                    highlights for the current captain), and the arrow
                    to move them up a board. Blank rows can be added
                    for players to be named on the day.

  PRINTING        — The Download button saves the sheet as an A4
                    landscape PDF, ready to print at 100% scale from
                    any device. The layout shrinks automatically so
                    multi-round sheets fit on one page where possible;
                    very large sheets flow onto extra pages with whole
                    rounds kept together.

  DATE FORMAT     — Sheet Options includes a date format choice (e.g.
                    "2026 March 30" or "30/03/26") applied to both the
                    PDF scoresheet and the match email.

  RESULTS         — For Standard matches, enter each board's result in
                    the column between the two team boxes. For All Play
                    All, a results grid appears below the download button
                    with one column per round (so the sheet can be
                    printed before any results exist). Empty result boxes
                    show their pairing in grey (e.g. "Loch - Smith"),
                    trimmed to fit the box. Options (home score first):
                    1 - 0, 0.5 - 0.5, 0 - 1, plus defaults: "1 - D"
                    (away player absent), "D - 1" (home player absent),
                    "D - D" (both absent — scored as a draw). A present
                    player beats an absent one by default.

  COLOURS         — Standard matches have a w/b box per board (home
                    player's colour; away gets the opposite). For All
                    Play All with auto colours unticked, pick the colour
                    drawn for the away team in each round's column —
                    e.g. a WWBB draw means away plays White in rounds 1
                    and 2 then Black. Entered colours appear on both the
                    PDF scoresheet and in the match email.

  MATCH LINK / QR — Every scoresheet PDF carries a QR code beside the
                    signatures. Scanning it with any phone camera (or
                    opening the link from the "Match link & QR code"
                    expander) reopens the app with the whole match setup
                    prefilled — teams, board order, captains, venue,
                    date and options — ready for results entry after
                    the match. The link itself contains the data; no
                    account or upload is involved. Results and anything
                    written on by hand are not included.

  MATCH EMAIL     — Below the download button, a ready-to-copy results
                    email is generated in the club submission format:
                    a title line with the final score, round-by-round
                    result lines, round and cumulative scores, and
                    (absent) markers next to defaulted players. The
                    final score auto-fills from the entered results;
                    typing in a final score that does not match them
                    triggers a warning. Unentered results appear as "_"
                    for filling in before sending.

------------------------------------------------------------------------
9. RUNNING TESTS
------------------------------------------------------------------------
A test suite is included. To run it (no internet connection required):

    pytest tests/

------------------------------------------------------------------------
10. PROJECT FILES
------------------------------------------------------------------------
  app.py            — Streamlit UI
  chess_grading.py  — Chess Scotland API client and search logic
  scoresheet_pdf.py — Scoresheet PDF generator (fpdf2)
  match_email.py    — Match result email generator
  match_link.py     — Match link encoding + QR code generation
  example_emails.md — Real submission emails the template is based on
  club_names.txt    — Club name to code mapping
  requirements.txt  — Python dependencies
  tests/            — Automated test suite
  CHANGELOG.md      — Version history

========================================================================
Developed for Chess Scotland Users.
========================================================================
