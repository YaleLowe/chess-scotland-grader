# Fix Plan: Chess Scotland Grading Lookup

**Date:** 2026-03-09
**Based on:** `CODE_REVIEW.md` + redundant `surname_filter` analysis

Issues are grouped by file and ordered so that earlier fixes do not conflict with later ones within the same file. Priorities are marked: 🔴 Critical · 🟠 High · 🟡 Medium · 🟢 Low.

---

## File: `chess_grading.py`

### Fix 1 — Remove the duplicate `get_player_grading` stub 🔴
**Issue #1 from review.**

Lines 182–193 contain an incomplete, dead first definition of `get_player_grading`. Delete it entirely. The real implementation at lines 270–366 is the one Python uses and should be kept unchanged. After deletion, the file order should be:

1. Imports
2. Constants (`BASE_URL`, `API_URL`)
3. `get_session_and_token()`
4. `search_player()`
5. `parse_results()`
6. Club helpers (`CLUB_DATA`, `load_club_data()`, `get_clubs_list()`, `get_club_code()`)
7. `get_player_grading()` — one definition only
8. `if __name__ == "__main__":` block

---

### Fix 2 — Remove the redundant `surname_filter` from `parse_results` 🟠
**Issue from redundancy analysis.**

`parse_results` accepts a `surname_filter` parameter and re-checks client-side whether the filter string appears in the returned player name. The backend already filters by surname before returning results, making this check redundant. Additionally, the substring check runs against the full name string (not just the surname), so it can pass false positives where the filter token matches the forename instead.

- Remove the `surname_filter` parameter from `parse_results`.
- Remove the `if surname_filter and ... continue` block (line 131).
- Remove the `surname_filter=lname` argument passed in `get_player_grading` (line 354).

---

### Fix 3 — Move `get_text_safe` outside the loop 🟡
**Issue #3 from review.**

`get_text_safe` is a plain helper function defined inside `for row in rows:` in `parse_results`, causing it to be redefined on every iteration.

Move the function definition to module level, just above `parse_results`.

---

### Fix 4 — Fix the broken `__main__` CLI block 🟠
**Issue #4 from review.**

The `__main__` block calls `get_player_grading(names)` where `names` is a list of plain strings. The function expects a list of query dicts with keys `raw`, `name`, `club`, `is_single`. This causes an immediate `KeyError` if the script is run directly.

Update the CLI block to construct the correct dict format from the user's input. A minimal fix:

```python
queries = []
for n in names:
    queries.append({
        'raw': n,
        'name': n,
        'club': '',
        'is_single': len(n.split()) == 1
    })
results = get_player_grading(queries)
```

---

### Fix 5 — Replace hardcoded relative path with a path relative to the script 🟠
**Issue #5 from review.**

`open('club_names.txt', ...)` resolves relative to the current working directory. Replace with a path anchored to the script file so it works regardless of where Streamlit is launched from:

```python
import os
_DIR = os.path.dirname(os.path.abspath(__file__))
CLUB_FILE = os.path.join(_DIR, 'club_names.txt')
```

Use `CLUB_FILE` in both `load_club_data()` and `get_clubs_list()`.

---

### Fix 6 — Eliminate the double file read in `get_clubs_list` 🟡
**Issue #6 from review.**

`load_club_data()` stores only lowercased keys so `get_clubs_list()` is forced to re-read the file to get properly cased display names.

Change `CLUB_DATA` to store both the display name and the code. Suggested structure:

```python
# Before: CLUB_DATA = {fullname_lower: abbrev}
# After:  CLUB_DATA = {fullname_lower: {'code': abbrev, 'display': fullname}}
```

Update `load_club_data()` accordingly. Update `get_club_code()` to use `entry['code']`. Rewrite `get_clubs_list()` to build the list from `CLUB_DATA` directly, removing the second file read.

---

### Fix 7 — Validate 2-character club codes against the known list 🟢
**Issue #22 from review.**

`get_club_code` treats any 2-character string as a valid club code unconditionally, even if it is not in `club_names.txt`. After Fix 6, the known codes are available. Add a validation step:

```python
if len(query) == 2:
    q_upper = query.upper()
    # Check it's actually a known code before returning it
    known_codes = {v['code'] for v in CLUB_DATA.values()}
    if q_upper in known_codes:
        return q_upper
    # Fall through to name matching if not a known code
```

---

### Fix 8 — Use `print` → `logging` for error output 🟢
**Issue #14 from review.**

Replace bare `print(...)` error calls with Python's `logging` module so severity levels are preserved and output can be configured:

```python
import logging
logger = logging.getLogger(__name__)
# Replace: print(f"Error connecting to main page: {e}")
# With:    logger.error("Error connecting to main page: %s", e)
```

Apply to all three error prints: the connection error (line 25), the missing CSRF token (line 33), and the failed session (line 279).

---

### Fix 9 — Add version pinning to `requirements.txt` 🟡
**Issue #18 from review.**

Pin all dependencies to their current compatible versions to prevent silent breakage on a fresh install. Check installed versions with `pip freeze` and update the file, e.g.:

```
streamlit>=1.30,<2.0
requests>=2.31,<3.0
beautifulsoup4>=4.12,<5.0
pandas>=2.0,<3.0
lxml>=5.0,<6.0
```

---

### Fix 10 — Add `lxml` as the BeautifulSoup parser 🟢
**Issue #19 from review.**

Add `lxml` to `requirements.txt` (done in Fix 9 above). Change both `BeautifulSoup(...)` calls to specify the parser explicitly:

```python
# Before:
soup = BeautifulSoup(html_content, 'html.parser')
# After:
soup = BeautifulSoup(html_content, 'lxml')
```

Apply to both calls: in `get_session_and_token()` (line 28) and in `parse_results()` (line 95).

---

## File: `app.py`

### Fix 11 — Move `import re` to the top of the file 🟡
**Issue #2 from review.**

`import re` appears inside the `for line in raw_lines:` loop (line 123). Move it to the top of `app.py` with the other imports.

---

### Fix 12 — Surface network errors to the user 🟠
**Issue #10 from review.**

When `get_player_grading` returns `{}` (session initialisation failed), the current code silently produces an empty result set with every player shown as ❌. The user cannot distinguish a network failure from genuine "not found" results.

After the call to `get_player_grading`, check for total failure:

```python
new_results = get_player_grading(missing_queries)
if not new_results and missing_queries:
    st.error("Could not connect to Chess Scotland. Check your internet connection and try again.")
else:
    st.session_state.player_cache.update(new_results)
```

For individual queries that silently return `[]` due to a mid-batch network error (from `search_player` returning `None`), this is harder to distinguish from "no results". A future improvement would be for `chess_grading.py` to return a distinct sentinel for network errors vs. genuine no-results.

---

### Fix 13 — Fix alphabetical sort in Single Line Copy to sort by name only 🟡
**Issue #12 from review.**

The current sort:
```python
alpha_sorted_lines = sorted([str(item['text']) for item in copy_items])
```
Sorts the fully formatted strings (e.g. `"John Smith [12345] (1650)"`), not by name alone. Extract just the name for the sort key:

```python
alpha_sorted_lines = [
    item['text'] for item in
    sorted(copy_items, key=lambda x: x['text'].split('[')[0].split('(')[0].strip().lower())
]
```

---

### Fix 14 — Clarify result metric labels 🟢
**Issue #13 from review.**

The "Possible Matches" label is confusing — it actually means the total number of valid unique players found, not uncertain matches specifically. Rename:

- `"Exact Matches"` → `"Confident Matches"` (status ✅ or ⚠️ PNUM Only)
- `"Possible Matches"` → `"Total Players Found"` (all unique valid rows)
- `"Non-existent/Invalid"` → `"Not Found / Invalid"` (minor wording tidy)

---

### Fix 15 — Move `is_pnum_only_match` tagging into `chess_grading.py` 🟢
**Issue #20 from review.**

Currently `app.py` injects `is_pnum_only_match` into the returned match dicts after the fact. This is UI logic leaking into data objects. Instead, have `chess_grading.py` include a `match_type` field in the returned dicts:

```python
# In get_player_grading, PNUM case:
for m in matches:
    m['match_type'] = 'pnum'
# For standard searches, set match_type = 'name'
```

In `app.py`, check `match.get('match_type') == 'pnum'` instead of `match.get('is_pnum_only_match')`. Remove the post-hoc tagging loop (lines 181–184 of `app.py`).

---

## Project Structure

### Fix 16 — Delete or formalise the debug scripts 🟡
**Issue #16 from review.**

`reproduce_issue.py` and `verify_phase4.py` are ad-hoc debug scripts in the project root. They should not remain as loose files. Two options:

**Option A (Recommended):** Convert them into proper tests using `pytest`.
- Create a `tests/` directory.
- Move and rewrite the logic as `tests/test_club_logic.py`.
- Add `pytest` to `requirements.txt`.
- The club display logic from `reproduce_issue.py` and the `get_club_code` tests from `verify_phase4.py` make good unit tests.

**Option B:** Delete them. They tested one-off bugs that are now fixed.

---

### Fix 17 — Add a proper test suite 🟡
**Issue #17 from review.**

Beyond converting the existing scripts (Fix 16), add tests for the logic that has had the most bugs:

- Name normalisation: `"Smith, John"` → `"John Smith"`
- PNUM extraction regex: `"John Smith [12345]"` → pnum `"12345"`
- `is_single` detection
- Deduplication logic (pnum-keyed dedup)
- `get_club_code` with full/partial/2-char inputs
- `parse_results` with sample HTML fixture

Use `pytest` with `unittest.mock` to patch `get_session_and_token` and `search_player` so no network calls are needed in tests.

---

## Deferred / Out of Scope

The following issues from the review are noted but not included in this plan as they are either too speculative to fix without live testing, or are design trade-offs rather than bugs:

- **Fix 7 (session/token caching):** Caching the CSRF token in `st.session_state` would save one HTTP round-trip per search. Deferred because it requires understanding the token TTL on the Chess Scotland server.
- **Fix 8 (unbounded cache):** Adding a max cache size (e.g. evict oldest entries beyond 500) is a safe improvement but low priority for a personal tool.
- **Fix 9 (cache key normalisation):** Normalising cache keys to lowercase/stripped values is a minor efficiency gain. Low risk to defer.
- **Issue #11 (fragile positional HTML parsing):** The club column `all_tds[2]` positional parse is fragile but can only be properly fixed by inspecting a live response from the Chess Scotland API. Flag for revisiting if club data ever stops appearing.

---

## Execution Order

If implementing all fixes in one session, apply them in this order to avoid conflicts:

1. Fix 1 (remove duplicate function) — structural change, do first
2. Fix 3 (move `get_text_safe` out of loop) — also structural
3. Fix 6 (consolidate `CLUB_DATA`) — before Fix 7 which depends on it
4. Fix 7 (validate 2-char codes) — depends on Fix 6
5. Fix 5 (fix file path) — independent but best done while touching `load_club_data`
6. Fix 2 (remove `surname_filter`) — independent
7. Fix 4 (fix CLI block) — independent
8. Fix 8 (logging) — independent
9. Fix 10 (lxml) + Fix 9 (requirements.txt) — do together
10. Fix 11 (move `import re`) — trivial, app.py
11. Fix 12 (surface network errors) — app.py
12. Fix 13 (sort fix) — app.py
13. Fix 14 (metric labels) — app.py
14. Fix 15 (move `match_type`) — spans both files, do last
15. Fix 16 + 17 (tests) — do after all code changes are stable
