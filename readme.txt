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

------------------------------------------------------------------------
2. SEARCHING FOR PLAYERS
------------------------------------------------------------------------
You can search for multiple players at once by entering one name per line 
in the large text area at the top.

A. Name Search:
   Type the name (e.g., "John Smith").
   Format: "Surname, Forename" or "Forename Surname" both work.

B. PNUM Search (Player Number):
   If you know a player's ID, put it in square brackets.
   Example: "John Smith [12345]" or just "[12345]". 
   The system will ignore the name and use the ID for an exact match.

C. Club-only Search:
   To see all players in a specific club, use a semicolon (;).
   Example: "; Stirling" or "; ST"
   Example: "John; ST" (Searches for "John" specifically within Stirling)

------------------------------------------------------------------------
3. NAVIGATION & HISTORY
------------------------------------------------------------------------
- NAVIGATE: Use the "Previous" and "Next" buttons at the top to cycle 
  through your recent searches. This is useful for recalling a long list 
  of names you entered earlier.
- REFRESH: Click "Get Grading" to fetch fresh data for the current list.

------------------------------------------------------------------------
4. DATA OPTIONS
------------------------------------------------------------------------
Below the text area, use the checkboxes to choose what data to show:
- GENERAL: Toggle PNUM, Club, and Age visibility.
- GRADES: Choose which grades to display (Published vs Live) for 
  Standard, Allegro, and Blitz formats.

------------------------------------------------------------------------
5. UNDERSTANDING RESULTS
------------------------------------------------------------------------
The results table shows an icon next to each name:
- ✅ : Exact Match found.
- ⚠️ Multiple : More than one player found; please check the PNUM.
- ⚠️ PNUM Only : Matched specifically by the ID you provided.
- ❌ : Player not found.

METRICS: Look at the numbers above the table to see a tally of how many 
exact, possible, and missing results you have.

------------------------------------------------------------------------
6. COPYING TO CLIPBOARD
------------------------------------------------------------------------
Scroll to the bottom to find pre-formatted lists ready for copy-pasting 
into emails or tournament software.

- MULTI-LINE COPY: A list sorted by grading (highest at the top).
- SINGLE LINE COPY: A comma-separated list sorted alphabetically by name.

FORMAT: "Name [Pnum] (Grade)"
Note: The system automatically picks the "best" available grade based 
on what you have checked (Standard -> Allegro -> Blitz).

------------------------------------------------------------------------
7. CLUB REFERENCE
------------------------------------------------------------------------
Check the Sidebar (on the left) for a full list of Club Names and their 
corresponding codes. You can use either the name or the code in your 
searches.

========================================================================
Developed for Chess Scotland Users.
========================================================================
