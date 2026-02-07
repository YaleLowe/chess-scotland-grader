import requests
from bs4 import BeautifulSoup
import sys
import json

# Configuration
BASE_URL = "https://www.chessscotland.com/grading"
API_URL = "https://www.chessscotland.com/handle-form"

def get_session_and_token():
    """
    Visits the main page to initialize cookies and scrape the dynamic CSRF token.
    """
    session = requests.Session()
    # Mimic a real browser
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': BASE_URL
    })

    try:
        response = session.get(BASE_URL, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error connecting to main page: {e}")
        return None, None

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the hidden input with name="_csrf_token"
    token_input = soup.find('input', {'name': '_csrf_token'})
    if not token_input:
        print("Error: Could not find CSRF token on main page.")
        return None, None
        
    return session, token_input['value']

def search_player(session, csrf_token, forename, surname, club=""):
    """
    Sends the specific XHR request to the handle-form endpoint.
    """
    # Headers specifically for the AJAX request
    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Origin': 'https://www.chessscotland.com',
    }
    
    # We use the 'files' parameter to force multipart/form-data encoding
    # format: 'field_name': (None, 'field_value')
    payload = {
        '_csrf_token': (None, csrf_token),
        'action': (None, 'search_players'),
        'forename': (None, forename),
        'surname': (None, surname),
        'pnum': (None, ''),
        'gender': (None, ''),
        'club': (None, club),
        'fide_fed': (None, ''),
        'min_age': (None, ''),
        'max_age': (None, ''),
    }

    try:
        response = session.post(API_URL, headers=headers, files=payload, timeout=10)
        response.raise_for_status()
        
        # The server usually returns JSON containing an HTML snippet
        try:
            data = response.json()
            # Sometimes the HTML is in a key called 'html', 'data', or just returned raw
            # Based on standard behavior for this type of backend:
            if isinstance(data, dict) and 'html' in data:
                return data['html']
            elif isinstance(data, str): 
                # If it returns a raw string of HTML
                return data
        except json.JSONDecodeError:
            # Fallback: maybe it returned raw HTML directly
            return response.text
            
    except requests.RequestException as e:
        return None
        
    return None

def parse_results(html_content, surname_filter=None):
    """
    Parses the returned HTML snippet using the exact data-columns found.
    Returns a list of dictionaries containing player details.
    """
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    rows = soup.find_all('tr')
    
    results = []
    
    for row in rows:
        # Extract fields using data attributes
        pnum_tag = row.find('td', {'data-column': 'pnum'})
        name_tag = row.find('td', {'data-column': 'name'})
        club_tag = row.find('td', class_='screen_large') # Club often doesn't have data-column, but is class 'screen_large'
        # Note: In the provided snippet, club is just <td class="screen_large">ST</td>. 
        # But we must be careful not to grab the WRONG screen_large td if there are others.
        # Based on structure: Pnum, Name, Club, Status
        
        # To be safer with Club, let's look at the logical order or specific unique attributes if possible.
        # The prompt snippet shows:
        # <td class="screen_large screen_medium" data-column="pnum">...</td>
        # <td class="left_align" data-column="name" ...>...</td>
        # <td class="screen_large">ST</td>  <-- Club
        # <td data-column="status">A</td>
        
        # Let's try finding all tds and indexing if data-column is missing, but using data-column is safer where available.
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
            
            # Optional: Strict filtering by surname to remove partial matches if desired
            if surname_filter and surname_filter.lower() not in name.lower():
                continue

            # Extract Club: explicit finding or fallback
            club = ""
            # Finding the td that comes after name might be a good strategy if no data-column
            # The structure is specific: Pnum, Name, Club, Status
            all_tds = row.find_all('td')
            # Assuming standard table layout from snippet
            if len(all_tds) > 2:
                 # Check if the 3rd column is indeed Club (it has class screen_large and no data-column in snippet)
                 # But let's verify if it's not status (which has data-column="status")
                 potential_club = all_tds[2]
                 if not potential_club.has_attr('data-column'):
                     club = potential_club.get_text(strip=True)

            # Status -> Age conversion
            raw_status = status_tag.get_text(strip=True) if status_tag else ""
            age = raw_status
            if raw_status == 'A':
                age = "Adult"
            elif raw_status == 'NEW':
                age = "New"
            elif raw_status == 'J?':
                age = "Junior"
            elif raw_status.startswith('J') and raw_status[1:].isdigit():
                age = raw_status[1:] # Remove 'J', keep number

            # Helper to get text safe
            def get_text_safe(tag):
                if not tag: return ""
                txt = tag.get_text(strip=True)
                if txt in ['&mdash;', '—', '', '-']: return ""
                return txt

            player_data = {
                "pnum": pnum,
                "name": name,
                "club": club,
                "age": age,
                "standard_published": get_text_safe(std_pub_tag),
                "standard_live": get_text_safe(std_live_tag),
                "allegro_published": get_text_safe(alg_pub_tag),
                "allegro_live": get_text_safe(alg_live_tag),
                "blitz_published": get_text_safe(blitz_pub_tag),
                "blitz_live": get_text_safe(blitz_live_tag)
            }
            results.append(player_data)
                
    return results

def get_player_grading(queries):
    """
    Main API function to get grading for a list of queries.
    Each query is a dict: {'raw': str, 'name': str, 'club': str, 'is_single': bool}
    Returns a dictionary mapping 'raw' input line to a list of found player dictionaries.
    """
    session, csrf_token = get_session_and_token()
    
    if not session or not csrf_token:
        print("Failed to initialize session.")
        return {}


# --- Club Lookup Logic ---
CLUB_DATA = {}

def load_club_data():
    """Loads club names and abbreviations from club_names.txt"""
    global CLUB_DATA
    if CLUB_DATA: return # Already loaded
    
    try:
        with open('club_names.txt', 'r', encoding='utf-8') as f:
            for line in f:
                if ',' in line:
                    parts = line.split(',')
                    # Format: "Club Name, AB"
                    # Store: "club name" -> "AB"
                    fullname = parts[0].strip()
                    abbrev = parts[1].strip()
                    CLUB_DATA[fullname.lower()] = abbrev
    except FileNotFoundError:
        print("Warning: club_names.txt not found. Club lookup will be limited.")

def get_clubs_list():
    """Returns a list of {'name': name, 'code': code} for UI display."""
    load_club_data()
    # CLUB_DATA is name_lower -> code. 
    # We want the original casing. Since we didn't store it in CLUB_DATA (we stored lower keys),
    # we should probably re-read or adjust load_club_data.
    # Actually, simpler: just read the file again or store proper casing in CLUB_DATA?
    # Let's adjust load_club_data to store a separate display list or just re-read here since it's one-off for UI.
    clubs = []
    try:
        with open('club_names.txt', 'r', encoding='utf-8') as f:
            for line in f:
                if ',' in line:
                    parts = line.split(',')
                    clubs.append({'name': parts[0].strip(), 'code': parts[1].strip()})
    except FileNotFoundError:
        pass
    return clubs

def get_club_code(query):
    """
    Resolves a club query string to a 2-letter code.
    Strategy:
    1. If 2 chars, assume code (case-insensitive).
    2. Exact name match.
    3. Substring match (input is substring of club name).
       Prioritize shortest club name match (e.g. "Stirling" -> "ST" over "Stirling Univ")
    """
    if not query: return ""
    query = query.strip()
    
    # 1. 2-Char Check: Always treat as code
    if len(query) == 2:
        return query.upper()
    
    load_club_data()
    q_lower = query.lower()
    
    # 2. Exact Match
    if q_lower in CLUB_DATA:
        return CLUB_DATA[q_lower]
        
    # 3. Substring Match
    # Find all keys that contain query
    matches = [k for k in CLUB_DATA.keys() if q_lower in k]
    
    if matches:
        # Sort by length to find "best" match (e.g. "Stirling" vs "Stirling University")
        matches.sort(key=len)
        best_match = matches[0]
        return CLUB_DATA[best_match]
        
    return "" # No match found

def get_player_grading(queries):
    """
    Main API function to get grading for a list of queries.
    Each query is a dict: {'raw': str, 'name': str, 'club': str, 'is_single': bool}
    Returns a dictionary mapping 'raw' input line to a list of found player dictionaries.
    """
    session, csrf_token = get_session_and_token()
    
    if not session or not csrf_token:
        print("Failed to initialize session.")
        return {}

    results_map = {}
    
    # Ensure data loaded
    load_club_data()
    
    for query in queries:
        raw_key = query['raw'] # Use the original line as the key
        name_part = query['name']
        club_raw = query.get('club', '')
        is_single = query.get('is_single', False)
        
        # Resolve Club Code
        club_code = ""
        # Check 1: Explicit club part
        if club_raw:
            club_code = get_club_code(club_raw)
        
        # Check 2: Implicit Club Code (if name is just 2 chars and no club specified)
        # "ST" -> name="ST", club="" -> Treat as Club Code "ST", Name=""
        if not club_code and is_single and len(name_part) == 2:
             club_code = name_part.upper()
             name_part = "" # Clear name to avoid searching for "ST" player

        # --- Name Length Constraint ---
        # Rule: Name must be >= 3 chars, UNLESS name is empty (Pure Club Search)
        matches = []
        is_invalid = False
        
        if name_part and len(name_part) < 3:
            # Name too short
            is_invalid = True
        else:
            # Execute Search
            
            # Case A: Club Search Only (Name is empty)
            if not name_part and club_code:
                 # Search for all players in club? checking if backend supports empty name
                 # Based on form, usually requires at least one field. Club is a field.
                 html = search_player(session, csrf_token, forename="", surname="", club=club_code)
                 matches = parse_results(html)
            
            # Case B: Standard Name Search
            elif name_part:
                if is_single:
                    # Smart Search: Try Forename then Surname
                    html_1 = search_player(session, csrf_token, forename=name_part, surname="", club=club_code)
                    res_1 = parse_results(html_1) 
                    
                    html_2 = search_player(session, csrf_token, forename="", surname=name_part, club=club_code)
                    res_2 = parse_results(html_2)
                    
                    # Merge and Dedup
                    seen_pnums = set()
                    for p in res_1 + res_2:
                        if p['pnum'] not in seen_pnums:
                            matches.append(p)
                            seen_pnums.add(p['pnum'])
                else:
                    # Standard Search
                    parts = name_part.strip().split()
                    lname = parts[-1]
                    fname = " ".join(parts[:-1])
                    
                    html_response = search_player(session, csrf_token, fname, lname, club=club_code)
                    matches = parse_results(html_response, surname_filter=lname)

        if is_invalid:
             # Add a special marker for invalid query
             # We reuse the player dict structure but mark it?
             # Or just handle it in app.py? 
             # Let's return a special "Invalid" object/list to signal app.py
             # We'll use a specific dict structure that app.py can recognize
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
        
        print(f"Searching for: {names}...")
        results = get_player_grading(names)
        
        print(json.dumps(results, indent=2))
