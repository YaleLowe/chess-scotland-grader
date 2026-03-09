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
- PREVIOUS / NEXT: Use the buttons at the top to cycle through searches
  you have run during this session. Useful for switching between two
  team lists without retyping.
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
8. RUNNING TESTS
------------------------------------------------------------------------
A test suite is included. To run it (no internet connection required):

    pytest tests/

------------------------------------------------------------------------
9. PROJECT FILES
------------------------------------------------------------------------
  app.py            — Streamlit UI
  chess_grading.py  — Chess Scotland API client and search logic
  club_names.txt    — Club name to code mapping
  requirements.txt  — Python dependencies
  tests/            — Automated test suite
  CHANGELOG.md      — Version history
  CODE_REVIEW.md    — Code review notes
  FIX_PLAN.md       — Fix plan derived from the code review

========================================================================
Developed for Chess Scotland Users.
========================================================================
