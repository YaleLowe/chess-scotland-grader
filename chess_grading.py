import re

import requests
from bs4 import BeautifulSoup
import json
import logging
import os

logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "https://www.chessscotland.com/grading"
API_URL = "https://www.chessscotland.com/handle-form"

# Path to club data file, relative to this script regardless of working directory
_DIR = os.path.dirname(os.path.abspath(__file__))
CLUB_FILE = os.path.join(_DIR, 'club_names.txt')


def get_session_and_token():
    """
    Visits the main page to initialise cookies and scrape the dynamic CSRF token.
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': BASE_URL
    })

    try:
        response = session.get(BASE_URL, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error("Error connecting to main page: %s", e)
        return None, None

    soup = BeautifulSoup(response.text, 'lxml')
    token_input = soup.find('input', {'name': '_csrf_token'})
    if not token_input:
        logger.error("Could not find CSRF token on main page.")
        return None, None

    return session, token_input['value']


def search_player(session, csrf_token, forename, surname, club="", pnum=""):
    """
    Sends the XHR request to the handle-form endpoint.
    """
    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Origin': 'https://www.chessscotland.com',
    }

    # 'files' parameter forces multipart/form-data encoding
    payload = {
        '_csrf_token': (None, csrf_token),
        'action': (None, 'search_players'),
        'forename': (None, forename),
        'surname': (None, surname),
        'pnum': (None, pnum),
        'gender': (None, ''),
        'club': (None, club),
        'fide_fed': (None, ''),
        'min_age': (None, ''),
        'max_age': (None, ''),
    }

    try:
        response = session.post(API_URL, headers=headers, files=payload, timeout=10)
        response.raise_for_status()

        try:
            data = response.json()
            if isinstance(data, dict) and 'html' in data:
                return data['html']
            elif isinstance(data, str):
                return data
        except json.JSONDecodeError:
            return response.text

    except requests.RequestException as e:
        logger.error("Search request failed: %s", e)
        return None

    return None


def get_text_safe(tag):
    """Returns clean text from a BeautifulSoup tag, or empty string for dash/empty values."""
    if not tag:
        return ""
    txt = tag.get_text(strip=True)
    if txt in ['&mdash;', '—', '', '-']:
        return ""
    return txt


def parse_results(html_content):
    """
    Parses the returned HTML snippet.
    Returns a list of player dicts. The backend handles all partial matching;
    no client-side name filtering is applied here.
    """
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'lxml')
    rows = soup.find_all('tr')
    results = []

    for row in rows:
        pnum_tag = row.find('td', {'data-column': 'pnum'})
        name_tag = row.find('td', {'data-column': 'name'})
        status_tag = row.find('td', {'data-column': 'status'})
        std_pub_tag = row.find('td', {'data-column': 'standard_published'})
        std_live_tag = row.find('td', {'data-column': 'standard_live'})
        alg_pub_tag = row.find('td', {'data-column': 'allegro_published'})
        alg_live_tag = row.find('td', {'data-column': 'allegro_live'})
        blitz_pub_tag = row.find('td', {'data-column': 'blitz_published'})
        blitz_live_tag = row.find('td', {'data-column': 'blitz_live'})

        if pnum_tag and name_tag:
            pnum = pnum_tag.get_text(strip=True)
            name = name_tag.get_text(strip=True)

            # Club column has no data-column attribute; locate by position
            club = ""
            all_tds = row.find_all('td')
            if len(all_tds) > 2:
                potential_club = all_tds[2]
                if not potential_club.has_attr('data-column'):
                    club = potential_club.get_text(strip=True)

            # Status field encodes age category
            raw_status = status_tag.get_text(strip=True) if status_tag else ""
            if raw_status == 'A':
                age = "Adult"
            elif raw_status == 'NEW':
                age = "New"
            elif raw_status == 'J?':
                age = "Junior"
            elif raw_status.startswith('J') and raw_status[1:].isdigit():
                age = raw_status[1:]
            else:
                age = raw_status

            results.append({
                "pnum": pnum,
                "name": name,
                "club": club,
                "age": age,
                "standard_published": get_text_safe(std_pub_tag),
                "standard_live": get_text_safe(std_live_tag),
                "allegro_published": get_text_safe(alg_pub_tag),
                "allegro_live": get_text_safe(alg_live_tag),
                "blitz_published": get_text_safe(blitz_pub_tag),
                "blitz_live": get_text_safe(blitz_live_tag),
            })

    return results


# --- Club Lookup Logic ---
# CLUB_DATA: {name_lower: {'code': str, 'display': str}}
CLUB_DATA = {}


def load_club_data():
    """Loads club names and codes from CLUB_FILE into CLUB_DATA (idempotent)."""
    global CLUB_DATA
    if CLUB_DATA:
        return
    try:
        with open(CLUB_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if ',' in line:
                    parts = line.split(',', 1)
                    fullname = parts[0].strip()
                    abbrev = parts[1].strip()
                    CLUB_DATA[fullname.lower()] = {'code': abbrev, 'display': fullname}
    except FileNotFoundError:
        logger.warning("club_names.txt not found at %s. Club lookup will be limited.", CLUB_FILE)


def get_clubs_list():
    """Returns a list of {'name': str, 'code': str} dicts for UI display."""
    load_club_data()
    return [{'name': v['display'], 'code': v['code']} for v in CLUB_DATA.values()]


def get_club_code(query):
    """
    Resolves a club query string to its 2-letter code.
    Strategy:
    1. If 2 chars and a known code, return it.
    2. Exact name match.
    3. Substring match — shortest club name wins.
    """
    if not query:
        return ""
    query = query.strip()

    load_club_data()

    # 1. 2-char shortcut: only treat as code if it matches a known code
    if len(query) == 2:
        q_upper = query.upper()
        known_codes = {v['code'] for v in CLUB_DATA.values()}
        if q_upper in known_codes:
            return q_upper
        # Fall through to name matching

    q_lower = query.lower()

    # 2. Exact name match
    if q_lower in CLUB_DATA:
        return CLUB_DATA[q_lower]['code']

    # 3. Substring match — prioritise shortest club name
    matches = [k for k in CLUB_DATA if q_lower in k]
    if matches:
        matches.sort(key=len)
        return CLUB_DATA[matches[0]]['code']

    return ""


def _clean_name(text):
    """
    Cleans a raw name string:
    - Strips parenthesised content (e.g. "(1513)")
    - Removes standalone numbers (e.g. leading "1.")
    - Removes all characters except letters, spaces, hyphens, and apostrophes
    - Normalises "Surname, Forename" -> "Forename Surname"
    - Collapses whitespace
    """
    # Remove parenthesised content
    text = re.sub(r'\(.*?\)', '', text)
    # Remove numbers (not inside square brackets — those are already extracted)
    text = re.sub(r'\d+', '', text)
    # Remove periods
    text = text.replace('.', '')
    # Normalise "Surname, Forename" before stripping commas
    if ',' in text:
        parts = text.split(',', 1)
        if len(parts) == 2 and parts[0].strip() and parts[1].strip():
            text = f"{parts[1].strip()} {parts[0].strip()}"
    # Remove all characters except letters, spaces, hyphens, apostrophes
    text = re.sub(r"[^a-zA-Z\s'\-]", '', text)
    # Collapse whitespace
    text = ' '.join(text.split())
    return text


def parse_queries(raw_text):
    """
    Parses the multi-line text input into a list of query dicts.

    Syntax per line:
      - Raw text is a player name.
      - [12345]        — PNUM search (square brackets).
      - Name; club     — semicolon sets club for this line only.
      - club:          — colon sets a "sticky" club for all following lines.
      - gr: Name       — colon with text after it sets sticky club AND parses the name.

    A new colon overrides the previous sticky club.

    Returns (parsed_queries, valid_raw_lines).
    """
    raw_lines = raw_text.split('\n')
    parsed_queries = []
    valid_raw_lines = []
    sticky_club = ""

    for line in raw_lines:
        line = line.strip()
        if not line:
            continue

        # --- Colon handling: sticky club directive ---
        if ':' in line:
            colon_idx = line.index(':')
            club_directive = line[:colon_idx].strip()
            remainder = line[colon_idx + 1:].strip()
            if club_directive:
                sticky_club = club_directive
            if not remainder:
                # Pure directive line (e.g. "st:"), no query to add
                continue
            # Remainder becomes the line to parse
            line = remainder

        # --- PNUM detection (square brackets) ---
        pnum_match = re.search(r'\[(\d+)\]', line)

        if pnum_match:
            pnum = pnum_match.group(1)
            parsed_queries.append({
                'raw': line,
                'pnum': pnum,
                'name': '',
                'club': sticky_club,
                'is_single': False,
            })
            valid_raw_lines.append(line)
            continue

        # --- Semicolon: per-line club override ---
        parts = line.split(';', 1)
        name_raw = parts[0].strip()
        club_part = parts[1].strip() if len(parts) > 1 else ""

        # Clean the name
        name_part = _clean_name(name_raw)

        # Determine effective club: explicit semicolon > sticky
        effective_club = club_part if club_part else sticky_club

        if not name_part and not effective_club:
            continue

        is_single = len(name_part.split()) == 1 if name_part else False

        parsed_queries.append({
            'raw': line,
            'name': name_part,
            'club': effective_club,
            'is_single': is_single,
        })
        valid_raw_lines.append(line)

    return parsed_queries, valid_raw_lines


def clean_input_text(raw_text):
    """
    Cleans raw multi-line input for display back in the text box.
    Preserves structural syntax (colons, semicolons, square brackets)
    while cleaning name portions using _clean_name.

    Returns the cleaned string with one entry per line.
    """
    raw_lines = raw_text.split('\n')
    cleaned_lines = []

    for line in raw_lines:
        line = line.strip()
        if not line:
            continue

        # Colon directive lines: keep as-is (e.g. "st:")
        if ':' in line:
            colon_idx = line.index(':')
            club_directive = line[:colon_idx].strip()
            remainder = line[colon_idx + 1:].strip()
            if not remainder:
                # Pure directive — keep it unchanged
                cleaned_lines.append(f"{club_directive}:")
                continue
            # Has a name after colon — clean the name part, reconstruct
            pnum_match = re.search(r'\[(\d+)\]', remainder)
            if pnum_match:
                cleaned_lines.append(f"{club_directive}: [{pnum_match.group(1)}]")
                continue
            parts = remainder.split(';', 1)
            name_clean = _clean_name(parts[0])
            club_suffix = f"; {parts[1].strip()}" if len(parts) > 1 else ""
            rebuilt = f"{club_directive}: {name_clean}{club_suffix}".strip()
            cleaned_lines.append(rebuilt)
            continue

        # PNUM line — keep only the bracket portion
        pnum_match = re.search(r'\[(\d+)\]', line)
        if pnum_match:
            cleaned_lines.append(f"[{pnum_match.group(1)}]")
            continue

        # Regular name line, possibly with semicolon club
        parts = line.split(';', 1)
        name_clean = _clean_name(parts[0])
        club_suffix = f"; {parts[1].strip()}" if len(parts) > 1 else ""

        result = f"{name_clean}{club_suffix}".strip()
        if result:
            cleaned_lines.append(result)

    return '\n'.join(cleaned_lines)


def get_player_grading(queries):
    """
    Main API function. Fetches grading for a list of query dicts.

    Each query dict must contain:
        'raw'      : str  — original input line, used as the result map key
        'name'     : str  — parsed player name
        'club'     : str  — optional club filter string
        'is_single': bool — True if name is a single token

    Optionally:
        'pnum'     : str  — player number for direct lookup

    Returns a dict mapping 'raw' -> list of player dicts.
    Each player dict includes a 'match_type' key: 'pnum' or 'name'.
    """
    session, csrf_token = get_session_and_token()
    if not session or not csrf_token:
        logger.error("Failed to initialise session.")
        return {}

    load_club_data()
    results_map = {}

    for query in queries:
        raw_key = query['raw']
        name_part = query['name']
        club_raw = query.get('club', '')
        is_single = query.get('is_single', False)

        matches = []
        is_invalid = False

        if query.get('pnum'):
            # PNUM search: backend does a direct lookup by player number
            html = search_player(session, csrf_token, forename="", surname="", club="", pnum=query['pnum'])
            matches = parse_results(html)
            for m in matches:
                m['match_type'] = 'pnum'

        else:
            # Resolve club code from the explicit club part
            club_code = ""
            if club_raw:
                club_code = get_club_code(club_raw)

            # Implicit club code: single 2-char token with no explicit club (e.g. "ST")
            if not club_code and is_single and len(name_part) == 2:
                resolved = get_club_code(name_part)
                if resolved:
                    club_code = resolved
                    name_part = ""

            if name_part and len(name_part) < 3:
                is_invalid = True
            else:
                if not name_part and club_code:
                    # Club-only search
                    html = search_player(session, csrf_token, forename="", surname="", club=club_code)
                    matches = parse_results(html)

                elif name_part:
                    if is_single:
                        # Ambiguous single token: try as forename and as surname, merge results
                        html_1 = search_player(session, csrf_token, forename=name_part, surname="", club=club_code)
                        res_1 = parse_results(html_1)
                        html_2 = search_player(session, csrf_token, forename="", surname=name_part, club=club_code)
                        res_2 = parse_results(html_2)

                        seen_pnums = set()
                        for p in res_1 + res_2:
                            if p['pnum'] not in seen_pnums:
                                matches.append(p)
                                seen_pnums.add(p['pnum'])
                    else:
                        # Multi-word: try each word as surname with the rest as forename.
                        # This catches both "John Smith" and "Smith John" style entries.
                        words = name_part.strip().split()
                        seen_pnums = set()
                        for i in range(len(words)):
                            surname = words[i]
                            forename = " ".join(words[:i] + words[i+1:])
                            html_response = search_player(session, csrf_token, forename, surname, club=club_code)
                            for p in parse_results(html_response):
                                if p['pnum'] not in seen_pnums:
                                    matches.append(p)
                                    seen_pnums.add(p['pnum'])

                    for m in matches:
                        m['match_type'] = 'name'

        if is_invalid:
            matches = [{'invalid_query': True}]

        results_map[raw_key] = matches

    return results_map


if __name__ == "__main__":
    print("--- Chess Scotland Grading Lookup ---")

    while True:
        try:
            raw_input = input("\nEnter names (comma separated) or 'q' to quit > ").strip()
        except EOFError:
            break

        if raw_input.lower() in ['q', 'quit', 'exit']:
            break
        if not raw_input:
            continue

        names = [n.strip() for n in raw_input.split(',') if n.strip()]
        queries = [
            {
                'raw': n,
                'name': n,
                'club': '',
                'is_single': len(n.split()) == 1,
            }
            for n in names
        ]

        print(f"Searching for: {names}...")
        results = get_player_grading(queries)
        print(json.dumps(results, indent=2))
