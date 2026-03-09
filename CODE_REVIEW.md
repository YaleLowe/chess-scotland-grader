# Code Review: Chess Scotland Grading Lookup

**Date:** 2026-03-09
**Reviewer:** Claude Code
**Scope:** Full project review — `app.py`, `chess_grading.py`, supporting files, project structure.

---

## Summary

The app is functional and covers its core use case well. The UI is sensibly laid out, the search logic handles several non-trivial input formats, and the copy-to-clipboard feature addresses the primary user need. However, the codebase shows signs of iterative patching without cleanup, and there are a number of bugs (one critical), architectural weaknesses, and maintainability issues that would cause problems as the project grows or if anything in the external site changes.

---

## Critical Bugs

### 1. Duplicate `get_player_grading` function definition (`chess_grading.py:182` and `chess_grading.py:270`)

The function is defined twice in the same file. The first definition (lines 182–193) is an incomplete stub that initialises a session and then returns nothing (implicit `None`). The second definition (lines 270–366) is the real implementation.

Python silently uses the second definition, so the app currently works. But:

- The stub is dead code that is never executed — it is confusing to any reader.
- The `# --- Club Lookup Logic ---` block (lines 195–268) sits between the two definitions, which breaks the natural reading flow.
- If the stub were ever moved below the real function, the whole lookup feature would silently stop working.

**Root cause:** Looks like the function was written once as a placeholder, the club lookup helpers were added in between, and then the real function was written again below without removing the stub.

---

## Significant Bugs

### 2. `import re` inside a loop (`app.py:123`)

```python
for line in raw_lines:
    line = line.strip()
    if not line: continue
    import re          # <-- re-imported on every loop iteration
    pnum_match = re.search(r'\[(\d+)\]', line)
```

`import re` should be at the top of the file with the other imports. Python caches modules so this does not cause a crash, but it is semantically wrong, adds a redundant lookup on every iteration, and is a misleading pattern that suggests the developer may not have noticed it was inside the loop.

### 3. `get_text_safe` helper defined inside a loop (`chess_grading.py:160`)

```python
for row in rows:
    ...
    def get_text_safe(tag):   # <-- redefined on every iteration
        ...
```

The function is redefined on every iteration of the `for row in rows` loop. It should be defined once at module level or at least outside the loop.

### 4. CLI `__main__` block is broken (`chess_grading.py:368`)

```python
names = [n.strip() for n in raw_input.split(',') if n.strip()]
results = get_player_grading(names)
```

`get_player_grading` expects a list of query dicts:
```python
{'raw': str, 'name': str, 'club': str, 'is_single': bool}
```

Passing a plain list of strings will cause a `KeyError` or `TypeError` immediately. The CLI mode is entirely non-functional.

### 5. Hardcoded relative path for `club_names.txt` (`chess_grading.py:204`, `chess_grading.py:226`)

```python
with open('club_names.txt', 'r', encoding='utf-8') as f:
```

This resolves relative to the **current working directory** at runtime, not the script's location. If the app is ever run from a different directory (e.g. `streamlit run chess_grading/app.py` from the parent folder), club data silently fails to load and the sidebar is empty with no error shown to the user.

---

## Architectural Issues

### 6. `get_clubs_list()` reads the file twice (`chess_grading.py:198–233`)

`load_club_data()` reads `club_names.txt` into `CLUB_DATA` (with lowercased keys). Then `get_clubs_list()` opens and reads the same file independently a second time to get the properly-cased display names — because `CLUB_DATA` discarded the original casing.

The comment on line 221 even acknowledges the problem:
```
# We want the original casing. Since we didn't store it in CLUB_DATA...
# Let's adjust load_club_data to store a separate display list or just re-read here since it's one-off for UI.
```

The "just re-read" shortcut was taken but never revisited. `CLUB_DATA` should store both the lookup key and the display name.

### 7. No session/token caching between searches

`get_session_and_token()` makes an HTTP GET to `https://www.chessscotland.com/grading` on every call to `get_player_grading`. Since `get_player_grading` is called once per "Get Grading" button press, this means every search incurs an extra round-trip to fetch the CSRF token before the actual queries begin. For large player lists, this extra latency is noticeable. The session and token could be cached in `st.session_state` with a TTL.

### 8. Unbounded session-state cache (`app.py:25–26`)

```python
if "player_cache" not in st.session_state:
    st.session_state.player_cache = {}
```

The player cache grows for the lifetime of the browser session with no eviction policy or size cap. A user doing many searches over a long session accumulates all results indefinitely. For a personal tool this is unlikely to be a problem today, but it is worth noting.

### 9. Cache key is the exact raw input string

The cache key is the literal text the user typed (e.g. `"John Smith"`). Minor variations like `"john smith"` or `"John  Smith"` (double space) produce separate cache entries and trigger a new network fetch. Normalising the key (e.g. stripping and lowercasing) before caching would improve cache hit rates.

---

## Code Quality Issues

### 10. Silent network failures presented as "Not Found"

In `chess_grading.py`, if `get_session_and_token()` fails (network error, site down), the function returns `{}`. Back in `app.py`, an empty result list displays the player as `❌ (Not Found)`. The user has no way to tell whether a player genuinely does not exist or whether the network request silently failed. The failure should be surfaced with an `st.error(...)` message.

Similarly, `search_player()` catches all `requests.RequestException` and returns `None` silently (line 82), turning network errors into invisible "no results".

### 11. Positional HTML parsing is fragile (`chess_grading.py:138–145`)

```python
all_tds = row.find_all('td')
if len(all_tds) > 2:
    potential_club = all_tds[2]
    if not potential_club.has_attr('data-column'):
        club = potential_club.get_text(strip=True)
```

The club column is found by position (`all_tds[2]`) and the absence of a `data-column` attribute. All other columns use the `data-column` attribute directly. If Chess Scotland ever changes their table layout — adds a column, reorders columns, or adds `data-column="club"` — club data silently disappears or shows wrong data. The comment on lines 105–116 acknowledges this uncertainty but it was never resolved.

### 12. Alphabetical single-line copy sorts the full formatted string, not just the name

```python
alpha_sorted_lines = sorted([str(item['text']) for item in copy_items])
```

Each `item['text']` is the full formatted string, e.g. `"John Smith [12345] (1650)"`. Sorting these strings alphabetically sorts by the entire string content, meaning entries starting with `"[`" or `"(`" could sort before names. More importantly, names beginning with a lower-case letter would sort after all upper-case names. For a name-sorted list, sorting by the extracted name component would be more correct.

### 13. Metrics labelling is ambiguous

- **"Exact Matches"** counts rows where status is `✅` or `⚠️ PNUM Only`.
- **"Possible Matches"** counts **all** unique valid player rows (including `⚠️ Multiple`).

The label "Possible Matches" is confusing — it sounds like it should mean uncertain matches, but it actually means the total number of players found. "Total Players Found" or "Total Results" would be clearer. There is also a discrepancy: the comment at line 200 says `count_possible` is "Exact + Multiple", but after the deduplication recalculation (line 309) it counts all valid rows including `⚠️ PNUM Only`.

### 14. `print` used for error reporting throughout `chess_grading.py`

There are multiple `print(...)` calls used for error output:
- `print(f"Error connecting to main page: {e}")` (line 25)
- `print("Error: Could not find CSRF token on main page.")` (line 33)
- `print("Failed to initialize session.")` (line 279)

These print to the terminal but are invisible to the user in the Streamlit UI. Errors should either be returned to the caller and surfaced via `st.error()`, or use Python's `logging` module.

### 15. `⚠️ PNUM Only` status logic checks only `matches[0]` (`app.py:242`)

```python
if matches[0].get('is_pnum_only_match'):
    status_icon = "⚠️ PNUM Only"
```

The code only checks the first match to determine if a result came from a PNUM search. This works in practice (PNUM searches return one result), but is brittle — if a PNUM search somehow returned multiple results, only `matches[0]` would be tagged `is_pnum_only_match` because of how the tagging is done in the app (lines 181–184), and the logic would still work for the wrong reason.

---

## Project Structure Issues

### 16. Debug/test scripts committed to the repo

Two debug scripts remain in the project root:
- `reproduce_issue.py` — a script to manually verify club display logic
- `verify_phase4.py` — a script to test `get_club_code`

The CHANGELOG even notes that `test_parsing.py` was "replaced by `reproduce_issue.py` for focused debugging." These files clutter the root directory. They are not a substitute for a proper test suite and should either be moved to a `tests/` directory and formalised with `pytest`, or deleted.

### 17. No proper test suite

The two files above are ad-hoc scripts, not automated tests. There is no `pytest` or `unittest` setup, no test for the PNUM extraction regex, no test for the name normalisation logic (`Surname, Forename` → `Forename Surname`), and no test for the deduplication logic. The `verify_phase4.py` comment even notes that integration testing is done "manually via walkthrough."

### 18. No version pinning in `requirements.txt`

```
streamlit
requests
beautifulsoup4
pandas
```

No version constraints. A breaking change in any of these libraries (especially `streamlit`, which has a history of breaking UI API changes) would silently break the app on a fresh install.

### 19. No `lxml` parser specified for BeautifulSoup

BeautifulSoup falls back to Python's built-in `html.parser` when no parser is specified. `lxml` is significantly faster, particularly for parsing repeated HTML snippets from the API. Adding `lxml` to `requirements.txt` and specifying it in the `BeautifulSoup(...)` call would improve performance.

---

## Minor Issues

### 20. `is_pnum_only_match` flag set in `app.py`, not in `chess_grading.py`

The flag `is_pnum_only_match` is injected into match dicts in `app.py` (lines 181–184) after the data comes back from `chess_grading.py`. This is a leaky separation of concerns — UI logic is being retrofitted into data objects. The cleaner approach would be for `chess_grading.py` to include a `match_type` field in its returned data.

### 21. `CLUB_DATA` is a module-level global with a lazy-load pattern

`CLUB_DATA = {}` at module level with `if CLUB_DATA: return` as a guard is a simple memoisation pattern, but it means the data persists across all invocations in a process. This is fine for Streamlit's execution model but would cause issues in a multi-tenant or testing context where the data needs to be reloaded or mocked.

### 22. `get_club_code` treats all 2-character inputs as codes

```python
if len(query) == 2:
    return query.upper()
```

Any 2-character string is unconditionally treated as a club code, even if it is not a valid club. This means `"AB"` always returns `"AB"` regardless of whether `AB` (Aberdeenshire resident) is intended. If a user types a 2-letter name fragment to search for, it will be misinterpreted as a club code. There is no validation against the actual list of known codes.

---

## What Works Well

- **Input flexibility**: The parser handles multiple formats gracefully — `Surname, Forename`, `Forename Surname`, `[PNUM]`, `; Club`, and combinations. This is the core UX challenge and it is solved well.
- **Caching**: Using `st.session_state` to avoid re-fetching already-looked-up players is a good performance choice.
- **Club display**: Expanding club codes to `CODE (Full Name)` is a good UX improvement over raw codes.
- **Deduplication**: The logic to prefer `✅` over `⚠️ Multiple` when the same player appears from different input lines is correct.
- **User Guide**: `readme.txt` is clear and covers the non-obvious features (PNUM search, club-only search, semicolon syntax).
- **CHANGELOG**: Maintained and accurate.

---

## Priority Summary

| Priority | Issue |
|---|---|
| Critical | #1 — Duplicate function definition |
| High | #4 — Broken CLI mode |
| High | #5 — Hardcoded relative file path |
| High | #10 — Silent network failures shown as "Not Found" |
| Medium | #2 — `import re` inside loop |
| Medium | #3 — `get_text_safe` defined inside loop |
| Medium | #6 — File read twice in `get_clubs_list` |
| Medium | #11 — Fragile positional HTML parsing |
| Medium | #12 — Alphabetical sort on full string |
| Medium | #17 — No test suite |
| Medium | #18 — No version pinning |
| Low | #7 — No CSRF token caching |
| Low | #8 — Unbounded cache |
| Low | #13 — Misleading metric labels |
| Low | #14 — `print` for error reporting |
| Low | #16 — Debug scripts in root |
| Low | #19 — No `lxml` parser |
| Low | #20–22 — Minor design issues |
