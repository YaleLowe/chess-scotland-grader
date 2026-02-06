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

def search_player(session, csrf_token, forename, surname):
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
        'club': (None, ''),
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

            status = status_tag.get_text(strip=True) if status_tag else ""

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
                "status": status,
                "standard_published": get_text_safe(std_pub_tag),
                "standard_live": get_text_safe(std_live_tag),
                "allegro_published": get_text_safe(alg_pub_tag),
                "allegro_live": get_text_safe(alg_live_tag),
                "blitz_published": get_text_safe(blitz_pub_tag),
                "blitz_live": get_text_safe(blitz_live_tag)
            }
            results.append(player_data)
                
    return results

def get_player_grading(names_list):
    """
    Main API function to get grading for a list of names.
    Returns a dictionary mapping input name to a list of found player dictionaries.
    """
    session, csrf_token = get_session_and_token()
    
    if not session or not csrf_token:
        print("Failed to initialize session.")
        return {}

    results_map = {}
    
    for full_name in names_list:
        parts = full_name.strip().split()
        if len(parts) < 2:
            # Handle single names or empty? currently skipping
            results_map[full_name] = []
            continue
        
        # Logic: Last word is surname
        lname = parts[-1]
        fname = " ".join(parts[:-1])
        
        html_response = search_player(session, csrf_token, fname, lname)
        matches = parse_results(html_response, surname_filter=lname)
        results_map[full_name] = matches
        
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
