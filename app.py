import re
from datetime import date

import streamlit as st
import pandas as pd
from chess_grading import get_player_grading, get_clubs_list, parse_queries, clean_input_text
from scoresheet_pdf import build_scoresheet_pdf
from match_email import (RESULT_OPTIONS, build_match_email, compute_totals,
                         format_points)
from match_link import build_match_url, decode_match, make_qr_image

# Public URL the printed QR code points at. The ?m= payload itself works on
# any host running the app (e.g. http://localhost:8501/?m=... when testing).
APP_BASE_URL = "https://scotgrades.streamlit.app/"

DATE_FORMAT_OPTIONS = ["2026 March 30", "30 March 2026", "30/03/2026",
                       "30/03/26"]

st.set_page_config(
    page_title="Chess Scotland Grading Lookup",
    page_icon="♟️",
    layout="wide"
)

# Streamlit stacks every st.columns row vertically once the viewport is
# narrower than 640px, even when the row's content would fit side by side.
# Rows wrapped in a container keyed "hflex_*" keep their column ratios on
# phones; rows keyed "hfit_*" instead shrink each column to its content
# width. Layouts above 640px are unaffected.
st.markdown("""
    <style>
    /* Square icon buttons (sort / move-up / captain): trim the wide default
       button padding so the icon always fits. When it doesn't fit, the left
       padding holds and the overflow clips on the right, shoving the icon
       off-centre in narrow columns. */
    div[class*="st-key-sort_"] button,
    div[class*="st-key-up_"] button,
    div[class*="st-key-cap_"] button {
        padding-left: 1px !important;
        padding-right: 1px !important;
        min-width: 0 !important;
    }
    /* w/b and result dropdowns: slim the inner padding and the chevron /
       clear icons. The defaults (12px text padding plus a 32px chevron
       block) eat more than the whole box in a squeezed window, hiding the
       selected W/B and the result text entirely. */
    div[class*="st-key-colour_"] [data-baseweb="select"] > div > div:first-child,
    div[class*="st-key-result_"] [data-baseweb="select"] > div > div:first-child {
        padding-left: 4px !important;
        padding-right: 0 !important;
    }
    div[class*="st-key-colour_"] [data-baseweb="select"] > div > div:last-child,
    div[class*="st-key-result_"] [data-baseweb="select"] > div > div:last-child {
        padding-right: 2px !important;
    }
    div[class*="st-key-colour_"] svg[data-baseweb="icon"],
    div[class*="st-key-result_"] svg[data-baseweb="icon"] {
        width: 1rem;
        height: 1rem;
    }
    /* The w/b boxes drop the chevron entirely and centre the letter: in a
       squeezed window there is no room for both, and a chevron that only
       appears on wide monitors would make the box change shape with screen
       size. The box still opens on tap/click. */
    div[class*="st-key-colour_"] [data-baseweb="select"] > div > div:last-child {
        display: none;
    }
    div[class*="st-key-colour_"] [data-baseweb="select"] > div > div:first-child {
        padding-left: 0 !important;
        justify-content: center;
        text-align: center;
    }
    @media (max-width: 640px) {
        div[class*="st-key-hflex"] div[data-testid="stHorizontalBlock"],
        div[class*="st-key-hfit"] div[data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap;
        }
        div[class*="st-key-hflex"] div[data-testid="stHorizontalBlock"]
                > div[data-testid="stColumn"] {
            min-width: 0 !important;
        }
        div[class*="st-key-hfit"] div[data-testid="stHorizontalBlock"]
                > div[data-testid="stColumn"] {
            min-width: 0 !important;
            width: auto !important;
            flex: 0 0 auto !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# --- Load Club Data for UI ---
CLUBS = get_clubs_list()
CLUB_MAP = {c['code']: c['name'] for c in CLUBS}  # Code -> Name

# --- Sidebar: Club Reference ---
with st.sidebar:
    st.header("ℹ️ Club Reference")
    st.markdown("Use these codes or names to filter by club.")
    if CLUBS:
        club_df = pd.DataFrame(CLUBS)
        st.dataframe(club_df, hide_index=True, use_container_width=True)


# --- Session State Initialisation ---
if "player_cache" not in st.session_state:
    st.session_state.player_cache = {}
if "active_names" not in st.session_state:
    st.session_state.active_names = []
if "search_history" not in st.session_state:
    st.session_state.search_history = []
if "history_index" not in st.session_state:
    st.session_state.history_index = -1
if "current_search_query" not in st.session_state:
    st.session_state.current_search_query = ""
if "home_team_name" not in st.session_state:
    st.session_state.home_team_name = "Team 1"
if "away_team_name" not in st.session_state:
    st.session_state.away_team_name = "Team 2"
if "home_players" not in st.session_state:
    st.session_state.home_players = []
if "away_players" not in st.session_state:
    st.session_state.away_players = []
if "home_captain" not in st.session_state:
    st.session_state.home_captain = None
if "away_captain" not in st.session_state:
    st.session_state.away_captain = None
if "teams_signature" not in st.session_state:
    st.session_state.teams_signature = None
if "venue" not in st.session_state:
    st.session_state.venue = ""
if "match_date" not in st.session_state:
    st.session_state.match_date = date.today()
if "tournament_type" not in st.session_state:
    st.session_state.tournament_type = "Standard"
if "blank_counter" not in st.session_state:
    st.session_state.blank_counter = 0


# --- Match link prefill (?m= payload from the scoresheet QR code) ---
def _grading_stub(name, pnum, rating):
    """Synthesised cache entry for a player restored from a match link.

    The link doesn't record which rating category the value came from, so
    it is restored as the Standard published grade (the default column).
    """
    return {
        'name': name, 'pnum': pnum, 'club': '', 'age': '',
        'standard_published': rating, 'standard_live': '',
        'allegro_published': '', 'allegro_live': '',
        'blitz_published': '', 'blitz_live': '',
        'match_type': 'name',
    }


def _apply_match_payload(p):
    names = []
    team_ids = {'hp': [], 'ap': []}
    blank_n = 0
    for key in ('hp', 'ap'):
        for entry in p.get(key) or []:
            if not entry:  # blank row on the sheet
                blank_n += 1
                team_ids[key].append(f"__blank_{blank_n}")
                continue
            name, pnum, rating = (list(entry) + ['', '', ''])[:3]
            st.session_state.player_cache[name] = [
                _grading_stub(name, pnum, rating)]
            names.append(name)
            team_ids[key].append(pnum or name)
    st.session_state.blank_counter = blank_n
    st.session_state.active_names = names
    st.session_state.home_players = team_ids['hp']
    st.session_state.away_players = team_ids['ap']
    # Matches the signature the scoresheet section derives from the results,
    # so the restored team split isn't reset by the auto-split logic.
    st.session_state.teams_signature = tuple(
        pid for pid in team_ids['hp'] + team_ids['ap']
        if not str(pid).startswith("__blank_"))
    st.session_state.home_captain = p.get('hc') or None
    st.session_state.away_captain = p.get('ac') or None
    st.session_state.home_team_name = p.get('hn') or "Team 1"
    st.session_state.away_team_name = p.get('an') or "Team 2"
    st.session_state.venue = p.get('vn', '')
    if p.get('d'):
        try:
            st.session_state.match_date = date.fromisoformat(p['d'])
        except ValueError:
            pass
    st.session_state.tournament_type = ("All Play All Allegro"
                                        if p.get('t') == 'A' else "Standard")
    opts = p.get('o') or [1, 1, 1]
    st.session_state.sheet_fill_pnums = bool(opts[0])
    st.session_state.sheet_fill_ratings = bool(opts[1])
    st.session_state.sheet_fill_colours = bool(opts[2])
    df_idx = p.get('df', 0)
    if isinstance(df_idx, int) and 0 <= df_idx < len(DATE_FORMAT_OPTIONS):
        st.session_state.date_format_choice = DATE_FORMAT_OPTIONS[df_idx]
    for i, ch in enumerate(p.get('cr', '')):
        if ch in "WB":
            st.session_state[f"colour_r{i}"] = ch
    for i, ch in enumerate(p.get('cb', '')):
        if ch in "WB":
            st.session_state[f"colour_r0_b{i}"] = ch


_link_token = st.query_params.get("m")
if _link_token and not st.session_state.get("match_link_loaded"):
    st.session_state.match_link_loaded = True
    try:
        _link_payload = decode_match(_link_token)
    except ValueError:
        _link_payload = None
    if isinstance(_link_payload, dict) and _link_payload.get('v') == 1:
        _apply_match_payload(_link_payload)
        st.success("Match setup loaded from the scoresheet link — scroll "
                   "down to the Scoresheet Maker to enter results.")
    else:
        st.warning("This match link couldn't be read — it may be damaged "
                   "or from a newer version of the app.")
    st.query_params.clear()

st.title("♟️ Chess Scotland Grading Lookup")
st.markdown("Enter a list of player names below to retrieve their grading information.")

# --- 1. Top: Input Section ---

# History Navigation
with st.container(key="hfit_history"):
    hist_col1, hist_col2, _ = st.columns([1, 1, 8])


def on_prev():
    if st.session_state.history_index > 0:
        st.session_state.history_index -= 1
        st.session_state.current_search_query = st.session_state.search_history[st.session_state.history_index]


def on_next():
    if st.session_state.history_index < len(st.session_state.search_history) - 1:
        st.session_state.history_index += 1
        st.session_state.current_search_query = st.session_state.search_history[st.session_state.history_index]


def update_history():
    query = st.session_state.current_search_query.strip()
    if query:
        # Clean the input and write it back to the text area
        cleaned = clean_input_text(query)
        st.session_state.current_search_query = cleaned

        if cleaned in st.session_state.search_history:
            st.session_state.search_history.remove(cleaned)
        st.session_state.search_history.append(cleaned)
        st.session_state.history_index = len(st.session_state.search_history) - 1


with hist_col1:
    st.button(":material/arrow_back:", key="hist_prev",
              help="Previous search",
              on_click=on_prev,
              disabled=(st.session_state.history_index <= 0))

with hist_col2:
    st.button(":material/arrow_forward:", key="hist_next",
              help="Next search",
              on_click=on_next,
              disabled=(st.session_state.history_index >= len(st.session_state.search_history) - 1))

names_input = st.text_area(
    "Player Names (one per line)\nFormat: 'Name [PNUM]' or 'Name; Club' or 'Club:' for group",
    height=150,
    placeholder="e.g.\nNathanael Loch\nSmith, John [12345]\n; ST (club-only search)\nst:\nPlayer One\nPlayer Two\ngr:\nPlayer Three",
    key="current_search_query"
)

# --- 2. Middle: Options (Landscape) ---
st.subheader("Data Options")

with st.container(key="hflex_options"):
    opt_col1, opt_col2, opt_col3, opt_col4 = st.columns(4)

with opt_col1:
    st.markdown("**General**")
    show_pnum = st.checkbox("Pnum", value=True)
    show_club = st.checkbox("Club", value=False)
    show_age = st.checkbox("Age", value=False)

with opt_col2:
    st.markdown("**Standard**")
    show_std_pub = st.checkbox("Published (Std)", value=True)
    show_std_live = st.checkbox("Live (Std)", value=False)

with opt_col3:
    st.markdown("**Allegro**")
    show_alg_pub = st.checkbox("Published (Alg)", value=False)
    show_alg_live = st.checkbox("Live (Alg)", value=False)

with opt_col4:
    st.markdown("**Blitz**")
    show_blitz_pub = st.checkbox("Published (Blitz)", value=False)
    show_blitz_live = st.checkbox("Live (Blitz)", value=False)

# --- Action ---
if st.button("Get Grading", type="primary", on_click=update_history):
    if not names_input.strip():
        st.warning("Please enter at least one name.")
        st.session_state.active_names = []
    else:
        parsed_queries, valid_raw_lines = parse_queries(names_input)

        if not parsed_queries:
            st.warning("No valid names found.")
            st.session_state.active_names = []
        else:
            missing_queries = [
                q for q in parsed_queries
                if q['raw'] not in st.session_state.player_cache
            ]

            if missing_queries:
                with st.spinner(f"Fetching data for {len(missing_queries)} new players..."):
                    new_results = get_player_grading(missing_queries)

                if not new_results and missing_queries:
                    st.error("Could not connect to Chess Scotland. Check your internet connection and try again.")
                else:
                    st.session_state.player_cache.update(new_results)

            st.session_state.active_names = valid_raw_lines

# --- Display Section ---
if st.session_state.active_names:
    results_map = {name: st.session_state.player_cache.get(name, []) for name in st.session_state.active_names}

    flat_data = []
    count_confident = 0
    count_total = 0
    count_none = 0

    for input_name, matches in results_map.items():
        if matches and isinstance(matches[0], dict) and matches[0].get('invalid_query'):
            count_none += 1
            flat_data.append({
                "Match Status": "⚠️ Ignored",
                "Name": f"{input_name} (Min 3 chars required)",
                "Pnum": "", "Club": "", "Age": "",
                "Live (Std)": "", "Published (Std)": "",
                "Live (Alg)": "", "Published (Alg)": "",
                "Live (Blitz)": "", "Published (Blitz)": "",
            })

        elif not matches:
            count_none += 1
            flat_data.append({
                "Match Status": "❌",
                "Name": f"{input_name} (Not Found)",
                "Pnum": "", "Club": "", "Age": "",
                "Live (Std)": "", "Published (Std)": "",
                "Live (Alg)": "", "Published (Alg)": "",
                "Live (Blitz)": "", "Published (Blitz)": "",
            })
        else:
            for match in matches:
                row = match.copy()

                # Determine match status icon
                if row.get('match_type') == 'pnum':
                    status_icon = "⚠️ PNUM Only"
                elif len(matches) > 1:
                    status_icon = "⚠️ Multiple"
                else:
                    status_icon = "✅"

                # Format club codes: "ST" -> "ST (Stirling)"
                c_code_raw = row.get('club', '')
                c_parts = [c.strip() for c in c_code_raw.split(',') if c.strip()]
                c_display_parts = []
                for code in c_parts:
                    if code in CLUB_MAP:
                        c_display_parts.append(f"{code} ({CLUB_MAP[code]})")
                    else:
                        c_display_parts.append(code)
                c_display = ", ".join(c_display_parts)

                flat_data.append({
                    "Match Status": status_icon,
                    "Name": row.get('name', ''),
                    "Pnum": row.get('pnum', ''),
                    "Club": c_display,
                    "Age": row.get('age', ''),
                    "Live (Std)": row.get('standard_live', ''),
                    "Published (Std)": row.get('standard_published', ''),
                    "Live (Alg)": row.get('allegro_live', ''),
                    "Published (Alg)": row.get('allegro_published', ''),
                    "Live (Blitz)": row.get('blitz_live', ''),
                    "Published (Blitz)": row.get('blitz_published', ''),
                })

    # --- Deduplication: prefer ✅ over ⚠️ Multiple for the same player ---
    unique_data = {}
    placeholders = []

    for row in flat_data:
        if "⚠️ Ignored" in row['Match Status'] or "❌" in row['Match Status']:
            placeholders.append(row)
            continue

        pnum = row.get('Pnum')
        name = row.get('Name')
        key = str(pnum) if pnum else name

        if key in unique_data:
            existing = unique_data[key]
            current_is_confident = row['Match Status'] in ("✅", "⚠️ PNUM Only")
            existing_is_confident = existing['Match Status'] in ("✅", "⚠️ PNUM Only")
            if current_is_confident and not existing_is_confident:
                unique_data[key] = row
        else:
            unique_data[key] = row

    flat_data = list(unique_data.values()) + placeholders

    # --- Recalculate tallies on deduplicated data ---
    for row in unique_data.values():
        count_total += 1
        if row['Match Status'] in ("✅", "⚠️ PNUM Only"):
            count_confident += 1
    count_none = len(placeholders)

    # --- Result Tallies ---
    with st.container(key="hflex_tallies"):
        t_col1, t_col2, t_col3 = st.columns(3)
    t_col1.metric("Confident Matches", count_confident)
    t_col2.metric("Total Players Found", count_total)
    t_col3.metric("Not Found / Invalid", count_none)

    if flat_data:
        df = pd.DataFrame(flat_data)

        # Convert grade columns to numeric for proper sorting
        grade_cols = [
            "Published (Std)", "Live (Std)",
            "Published (Alg)", "Live (Alg)",
            "Published (Blitz)", "Live (Blitz)",
        ]
        for col in grade_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        cols_to_show = ["Match Status", "Name"]
        if show_pnum: cols_to_show.append("Pnum")
        if show_club: cols_to_show.append("Club")
        if show_age: cols_to_show.append("Age")
        if show_std_pub: cols_to_show.append("Published (Std)")
        if show_std_live: cols_to_show.append("Live (Std)")
        if show_alg_pub: cols_to_show.append("Published (Alg)")
        if show_alg_live: cols_to_show.append("Live (Alg)")
        if show_blitz_pub: cols_to_show.append("Published (Blitz)")
        if show_blitz_live: cols_to_show.append("Live (Blitz)")

        final_df = df[[c for c in cols_to_show if c in df.columns]]
        st.dataframe(final_df, use_container_width=True, hide_index=True)

        # --- Copy Functionality ---
        st.divider()
        st.subheader("Copy to Clipboard")
        st.caption("Copy formatted lists for emails or tournaments.")

        priority_list = [
            ('standard_published', show_std_pub),
            ('standard_live', show_std_live),
            ('allegro_published', show_alg_pub),
            ('allegro_live', show_alg_live),
            ('blitz_published', show_blitz_pub),
            ('blitz_live', show_blitz_live),
        ]

        flat_key_map = {
            'standard_published': "Published (Std)",
            'standard_live': "Live (Std)",
            'allegro_published': "Published (Alg)",
            'allegro_live': "Live (Alg)",
            'blitz_published': "Published (Blitz)",
            'blitz_live': "Live (Blitz)",
        }

        copy_items = []

        for row in flat_data:
            if "⚠️ Ignored" in str(row['Match Status']) or "❌" in str(row['Match Status']):
                continue

            raw_name = row.get('Name', '')
            pnum = row.get('Pnum', '')

            # Normalise "Surname, Forename" -> "Forename Surname" for display
            display_name = raw_name
            if ',' in raw_name:
                n_parts = raw_name.split(',', 1)
                if len(n_parts) == 2:
                    display_name = f"{n_parts[1].strip()} {n_parts[0].strip()}"

            # Pick the highest-priority visible grade
            grade = ""
            sort_val = -1
            for key, is_checked in priority_list:
                if is_checked:
                    raw_val = row.get(flat_key_map[key], '')
                    if raw_val and str(raw_val).strip():
                        grade = str(raw_val)
                        try:
                            sort_val = int(grade)
                        except ValueError:
                            pass
                        break

            parts = [display_name]
            if show_pnum and pnum:
                parts.append(f"[{pnum}]")
            if grade:
                parts.append(f"({grade})")

            copy_items.append({
                'text': " ".join(parts),
                'name': display_name,
                'sort_val': sort_val,
            })

        c1, c2 = st.columns(2)

        with c1:
            st.markdown("##### Multi-line Copy")
            copy_items.sort(key=lambda x: x['sort_val'], reverse=True)
            multiline_text = "\n".join(item['text'] for item in copy_items)
            st.code(multiline_text, language="text")

        with c2:
            st.markdown("##### Single Line Copy")
            # Sort alphabetically by name only, not the full formatted string
            alpha_sorted = sorted(copy_items, key=lambda x: x['name'].lower())
            singleline_text = ", ".join(item['text'] for item in alpha_sorted)
            st.code(singleline_text, language="text")

        # --- Scoresheet Maker ---
        st.divider()
        st.subheader("Scoresheet Maker")

        TOURNAMENT_TYPES = ["Standard", "All Play All Allegro"]
        st.selectbox(
            "Tournament Type",
            options=TOURNAMENT_TYPES,
            key="tournament_type",
        )
        tournament_type = st.session_state.tournament_type

        with st.expander("Sheet Options — pre-filled fields and date format"):
            st.caption("Unticked fields are left blank on the printout, "
                       "to be filled in by hand on the day.")
            with st.container(key="hflex_sheetopts"):
                so_col1, so_col2, so_col3 = st.columns(3)
            sheet_fill_pnums = so_col1.checkbox(
                "PNUMs", value=True, key="sheet_fill_pnums")
            sheet_fill_ratings = so_col2.checkbox(
                "Ratings", value=True, key="sheet_fill_ratings")
            sheet_fill_colours = so_col3.checkbox(
                "Colours (w/b)", value=True, key="sheet_fill_colours",
                help="All Play All: pre-fill alternating colours each round. "
                     "Untick to enter the drawn colours per round in the "
                     "Results section instead. Standard matches use the "
                     "per-board colour boxes next to the results.")
            df_col, _ = st.columns([1, 2])
            date_format_choice = df_col.selectbox(
                "Date format (scoresheet & email)",
                DATE_FORMAT_OPTIONS,
                key="date_format_choice",
            )

        def _format_match_date(d, style):
            if d is None:
                return ""
            if style == "2026 March 30":
                return f"{d.year} {d:%B} {d.day}"
            if style == "30 March 2026":
                return f"{d.day} {d:%B} {d.year}"
            if style == "30/03/2026":
                return d.strftime("%d/%m/%Y")
            return d.strftime("%d/%m/%y")

        # Build per-player metadata (display string + numeric rating for sorting).
        # Keyed by stable id (pnum, falling back to name) so checkbox toggles
        # don't reset the user's team assignments / order / captains.
        def _abbreviate(full_name):
            parts = full_name.strip().split()
            if len(parts) < 2:
                return full_name
            return f"{parts[0][0]}. {parts[-1]}"

        def _split_name(full_name):
            parts = full_name.strip().split()
            if not parts:
                return "", ""
            if len(parts) == 1:
                return "", parts[0]
            return " ".join(parts[:-1]), parts[-1]

        player_data = {}
        valid_player_ids = []
        for row in unique_data.values():
            raw_name = row.get('Name', '') or ''
            pnum = str(row.get('Pnum', '') or '')
            normalised = raw_name
            if ',' in raw_name:
                n_parts = raw_name.split(',', 1)
                if len(n_parts) == 2:
                    normalised = f"{n_parts[1].strip()} {n_parts[0].strip()}"
            abbrev = _abbreviate(normalised)
            forename, surname = _split_name(normalised)

            grade = ""
            grade_int = -1
            for key, is_checked in priority_list:
                if is_checked:
                    raw_val = row.get(flat_key_map[key], '')
                    if raw_val and str(raw_val).strip():
                        grade = str(raw_val).strip()
                        try:
                            grade_int = int(grade)
                        except ValueError:
                            pass
                        break

            label_parts = [abbrev]
            if pnum:
                label_parts.append(f"[{pnum}]")
            if grade:
                label_parts.append(f"({grade})")
            display = " ".join(label_parts)

            player_id = pnum or normalised
            player_data[player_id] = {
                'display': display,
                'rating': grade_int,
                'rating_str': grade,
                'forename': forename,
                'surname': surname,
                'full_name': normalised,
                'pnum': pnum,
            }
            valid_player_ids.append(player_id)

        # Reset team rosters when the underlying player set changes (by id).
        # Blank rows added by the user persist across resets — only real players
        # are re-split.
        sig = tuple(valid_player_ids)
        if st.session_state.teams_signature != sig:
            home_blanks = [pid for pid in st.session_state.home_players
                           if str(pid).startswith("__blank_")]
            away_blanks = [pid for pid in st.session_state.away_players
                           if str(pid).startswith("__blank_")]
            mid = (len(valid_player_ids) + 1) // 2
            st.session_state.home_players = valid_player_ids[:mid] + home_blanks
            st.session_state.away_players = valid_player_ids[mid:] + away_blanks
            st.session_state.home_captain = None
            st.session_state.away_captain = None
            st.session_state.teams_signature = sig

        # Register blank rows in player_data so rendering and HTML generation
        # can look them up like real players.
        for pid in set(st.session_state.home_players + st.session_state.away_players):
            if str(pid).startswith("__blank_") and pid not in player_data:
                player_data[pid] = {
                    'display': '(blank)',
                    'rating': -1,
                    'rating_str': '',
                    'forename': '',
                    'surname': '',
                    'full_name': '',
                    'pnum': '',
                }

        def _pairing_placeholder(h_pid, a_pid, budget=24):
            """Grey 'Home - Away' text shown in an empty result box.

            The server can't measure the box's true pixel width, so the
            label is fitted to a character budget sized for the narrowest
            realistic box instead, dropping detail until it fits: ratings
            first, then pnums, then forenames shrink to initials, then
            surnames alone, and as a last resort the surnames are trimmed
            with '...'. The browser ellipsises anything still too wide.
            """
            def variants(pid):
                d = player_data.get(pid, {}) if pid else {}
                full = d.get('full_name', '')
                if not full:
                    return ["—"] * 5
                pnum = f" [{d['pnum']}]" if d.get('pnum') else ""
                rating = f" ({d['rating_str']})" if d.get('rating_str') else ""
                return [f"{full}{pnum}{rating}", f"{full}{pnum}", full,
                        _abbreviate(full), d.get('surname') or full]

            def trim(text, allow):
                if len(text) <= allow:
                    return text
                return text[:max(allow - 3, 1)] + "..."

            h_variants, a_variants = variants(h_pid), variants(a_pid)
            for h_txt, a_txt in zip(h_variants, a_variants):
                if len(h_txt) + len(a_txt) + 3 <= budget:
                    return f"{h_txt} - {a_txt}"

            # Surnames alone still don't fit: split the budget between the
            # sides, letting a short surname donate its spare room.
            h_txt, a_txt = h_variants[-1], a_variants[-1]
            total = budget - 3
            half = total // 2
            if len(h_txt) <= half:
                h_allow, a_allow = len(h_txt), total - len(h_txt)
            elif len(a_txt) <= total - half:
                h_allow, a_allow = total - len(a_txt), len(a_txt)
            else:
                h_allow, a_allow = half, total - half
            return f"{trim(h_txt, h_allow)} - {trim(a_txt, a_allow)}"

        v_col, d_col = st.columns([3, 1])
        with v_col:
            st.text_input("Venue", key="venue", placeholder="e.g. Stirling Chess Club")
        with d_col:
            st.date_input("Date", key="match_date")

        def _render_team(side, name_key, players_key, captain_key,
                         other_players_key, other_captain_key):
            with st.container(key=f"hflex_teamname_{side}"):
                name_col, sort_col = st.columns([6, 1])
            with name_col:
                st.text_input(f"{side} Team Name", key=name_key,
                              label_visibility="collapsed")
            with sort_col:
                # Material icons, not emoji: colour emoji glyphs (🔽/⬆️) sit
                # off-centre in their advance width, so they look misaligned
                # in a small square button. Icon-font glyphs centre exactly.
                if st.button(":material/sort:", key=f"sort_{side}",
                             help="Sort by rating (highest first)",
                             use_container_width=True):
                    st.session_state[players_key].sort(
                        key=lambda pid: player_data.get(pid, {}).get('rating', -1),
                        reverse=True,
                    )
                    st.rerun()

            players = st.session_state[players_key]
            for idx, pid in enumerate(list(players)):
                is_blank = str(pid).startswith("__blank_")
                with st.container(key=f"hflex_player_{side}_{idx}"):
                    star_col, name_col, up_col = st.columns([1, 6, 1])
                if is_blank:
                    star_col.markdown("&nbsp;", unsafe_allow_html=True)
                    if name_col.button("✕  (blank — fill in on the day)",
                                       key=f"name_{side}_{pid}",
                                       use_container_width=True,
                                       help="Remove this blank row"):
                        players.remove(pid)
                        st.rerun()
                else:
                    is_captain = st.session_state[captain_key] == pid
                    label = player_data.get(pid, {}).get('display', pid)
                    if star_col.button(":material/star:",
                                       key=f"cap_{side}_{pid}",
                                       type="primary" if is_captain
                                       else "secondary",
                                       use_container_width=True,
                                       help="Unset captain" if is_captain
                                       else "Set as captain"):
                        st.session_state[captain_key] = None if is_captain else pid
                        st.rerun()
                    if name_col.button(label, key=f"name_{side}_{pid}",
                                       use_container_width=True,
                                       help="Move to other team"):
                        players.remove(pid)
                        st.session_state[other_players_key].append(pid)
                        if st.session_state[captain_key] == pid:
                            st.session_state[captain_key] = None
                        st.rerun()
                if up_col.button(":material/arrow_upward:",
                                 key=f"up_{side}_{pid}",
                                 use_container_width=True,
                                 help="Move up one board (wraps to bottom)"):
                    if idx == 0:
                        players.append(players.pop(0))
                    else:
                        players[idx - 1], players[idx] = players[idx], players[idx - 1]
                    st.rerun()

            if st.button("➕ Add Blank Player", key=f"add_blank_{side}",
                         use_container_width=True,
                         help="Add a blank row for a player to be filled in later"):
                st.session_state.blank_counter += 1
                players.append(f"__blank_{st.session_state.blank_counter}")
                st.rerun()

        is_all_play_all = tournament_type == "All Play All Allegro"

        _RESULT_HELP = ("Home score first. D = default (absent player): "
                        "'D - 1' home player absent, '1 - D' away player "
                        "absent, 'D - D' both absent (scored as a draw).")

        # Standard matches get a Result column between the two team boxes,
        # one box per board. All Play All results are entered per round below.
        if is_all_play_all:
            home_col, away_col = st.columns(2)
            mid_col = None
        else:
            home_col, mid_col, away_col = st.columns([5, 3, 5])

        with home_col:
            with st.container(border=True):
                st.caption("Home")
                _render_team("Home", "home_team_name",
                             "home_players", "home_captain",
                             "away_players", "away_captain")
        if mid_col is not None:
            with mid_col:
                with st.container(border=True):
                    with st.container(key="hflex_rescap"):
                        cap_c, cap_r = st.columns([1, 2])
                    cap_c.caption("Home w/b")
                    cap_r.caption("Result")
                    st.markdown("&nbsp;", unsafe_allow_html=True)
                    n_result_rows = max(len(st.session_state.home_players),
                                        len(st.session_state.away_players), 1)
                    for b in range(n_result_rows):
                        h_pid = (st.session_state.home_players[b]
                                 if b < len(st.session_state.home_players)
                                 else None)
                        a_pid = (st.session_state.away_players[b]
                                 if b < len(st.session_state.away_players)
                                 else None)
                        h_disp = player_data.get(h_pid, {}).get('display', '—') if h_pid else '—'
                        a_disp = player_data.get(a_pid, {}).get('display', '—') if a_pid else '—'
                        with st.container(key=f"hflex_resrow_{b}"):
                            c_col, r_col = st.columns([1, 2])
                        c_col.selectbox(f"Board {b + 1} home colour",
                                        ["", "W", "B"],
                                        key=f"colour_r0_b{b}",
                                        label_visibility="collapsed",
                                        help="Home player's colour on this "
                                             "board; away gets the opposite.")
                        r_col.selectbox(f"Board {b + 1} result", RESULT_OPTIONS,
                                        key=f"result_r0_b{b}",
                                        index=None,
                                        placeholder=_pairing_placeholder(h_pid, a_pid),
                                        label_visibility="collapsed",
                                        help=f"{h_disp}  vs  {a_disp}. "
                                             f"{_RESULT_HELP}")
        with away_col:
            with st.container(border=True):
                st.caption("Away")
                _render_team("Away", "away_team_name",
                             "away_players", "away_captain",
                             "home_players", "home_captain")

        # --- Pairings (shared by results entry, the PDF, and the email) ---
        def _full_name(pid):
            d = player_data.get(pid, {})
            return f"{d.get('forename', '')} {d.get('surname', '')}".strip()

        home_ids = list(st.session_state.home_players)
        away_ids = list(st.session_state.away_players)
        n_boards = max(len(home_ids), len(away_ids), 1)
        h_padded = home_ids + [None] * (n_boards - len(home_ids))
        a_padded = away_ids + [None] * (n_boards - len(away_ids))

        n_rounds = n_boards if is_all_play_all else 1
        title_text = f"Chess Scoresheet: {tournament_type}"

        _OPP_COLOUR = {"W": "B", "B": "W", "": ""}

        def _round_colours(round_idx):
            # All Play All round colours as (home, away). Auto: away has White
            # in round 1, alternating every round. Manual (auto unticked): the
            # colour drawn for the away team each round; home is the opposite.
            if not is_all_play_all:
                return ("", "")
            if sheet_fill_colours:
                return ("B", "W") if round_idx % 2 == 0 else ("W", "B")
            away = st.session_state.get(f"colour_r{round_idx}", "")
            return (_OPP_COLOUR[away], away)

        def _board_colours(round_idx, board_idx):
            # Standard matches: colour entered per board (home player's
            # colour; away gets the opposite). All Play All: round-level.
            if is_all_play_all:
                return _round_colours(round_idx)
            home = st.session_state.get(f"colour_r0_b{board_idx}", "")
            return (home, _OPP_COLOUR[home])

        def _pairings_for_round(round_idx):
            pairs = []
            for b in range(n_boards):
                if is_all_play_all:
                    h_pid = h_padded[(b - round_idx) % n_boards]
                else:
                    h_pid = h_padded[b]
                pairs.append((h_pid, a_padded[b]))
            return pairs

        pairings = [_pairings_for_round(r) for r in range(n_rounds)]

        # --- Build downloadable scoresheet PDF ---
        def _build_round_rows(round_idx):
            rows = []
            for b, (h_pid, a_pid) in enumerate(pairings[round_idx]):
                home_colour, away_colour = _board_colours(round_idx, b)
                h = player_data.get(h_pid, {}) if h_pid else {}
                a = player_data.get(a_pid, {}) if a_pid else {}
                rows.append({
                    'bd': b + 1,
                    'h_forename': h.get('forename', ''),
                    'h_surname': h.get('surname', ''),
                    'h_pnum': h.get('pnum', '') if sheet_fill_pnums else '',
                    'h_rating': h.get('rating_str', '') if sheet_fill_ratings else '',
                    'h_colour': home_colour,
                    'result': '-',
                    'a_colour': away_colour,
                    'a_forename': a.get('forename', ''),
                    'a_surname': a.get('surname', ''),
                    'a_pnum': a.get('pnum', '') if sheet_fill_pnums else '',
                    'a_rating': a.get('rating_str', '') if sheet_fill_ratings else '',
                })
            return rows

        if is_all_play_all:
            rounds = [{'label': f"Round {r + 1}", 'rows': _build_round_rows(r)}
                      for r in range(n_rounds)]
        else:
            rounds = [{'label': None, 'rows': _build_round_rows(0)}]

        match_date = st.session_state.match_date
        date_str = _format_match_date(match_date, date_format_choice)

        # --- Match link + QR code (reloads this setup in the app) ---
        def _payload_player(pid):
            if str(pid).startswith("__blank_"):
                return 0
            d = player_data.get(pid, {})
            return [d.get('full_name', ''), d.get('pnum', ''),
                    d.get('rating_str', '')]

        link_payload = {
            'v': 1,
            't': 'A' if is_all_play_all else 'S',
            'd': match_date.isoformat() if match_date else '',
            'vn': st.session_state.venue or '',
            'hn': st.session_state.home_team_name or '',
            'an': st.session_state.away_team_name or '',
            'hp': [_payload_player(pid) for pid in home_ids],
            'ap': [_payload_player(pid) for pid in away_ids],
            'hc': st.session_state.home_captain or '',
            'ac': st.session_state.away_captain or '',
            'o': [int(sheet_fill_pnums), int(sheet_fill_ratings),
                  int(sheet_fill_colours)],
            'df': DATE_FORMAT_OPTIONS.index(date_format_choice),
        }
        if is_all_play_all and not sheet_fill_colours:
            drawn = "".join(st.session_state.get(f"colour_r{r}", "") or "-"
                            for r in range(n_rounds))
            if drawn.strip("-"):
                link_payload['cr'] = drawn
        if not is_all_play_all:
            drawn = "".join(st.session_state.get(f"colour_r0_b{b}", "") or "-"
                            for b in range(n_boards))
            if drawn.strip("-"):
                link_payload['cb'] = drawn

        match_url = build_match_url(APP_BASE_URL, link_payload)

        pdf_bytes = build_scoresheet_pdf(
            title=title_text,
            date_str=date_str,
            venue=st.session_state.venue or "",
            home_team=st.session_state.home_team_name or "",
            away_team=st.session_state.away_team_name or "",
            rounds=rounds,
            home_captain=_full_name(st.session_state.home_captain),
            away_captain=_full_name(st.session_state.away_captain),
            qr_image=make_qr_image(match_url),
        )

        file_date = match_date.strftime("%Y-%m-%d") if match_date else "match"
        st.write("")
        st.download_button(
            "⬇️ Download Scoresheet (PDF)",
            data=pdf_bytes,
            file_name=f"scoresheet_{file_date}.pdf",
            mime="application/pdf",
            type="primary",
        )
        st.caption("A4 landscape PDF — open it and print at 100% scale, "
                   "from any device.")

        with st.expander("Match link & QR code"):
            st.caption(
                "The QR code printed beside the signatures on the scoresheet "
                "opens this link. Scanning it (or opening the link) reloads "
                "this match setup — teams, boards, venue, date and options — "
                "on any device, ready for entering results after the match. "
                "Results and anything written on by hand aren't included."
            )
            st.code(match_url, language="text")

        # --- Results entry for All Play All (one column per round) ---
        # Rendered after the download button: the sheet can be printed before
        # any results exist, so the download comes first on the page.
        if is_all_play_all:
            st.markdown("##### Results")
            st.caption(_RESULT_HELP)
            if not sheet_fill_colours:
                st.caption("Auto colours are off — pick the colour drawn for "
                           "the away team each round (home gets the opposite).")
            round_cols = st.columns(n_rounds)
            for r, round_col in enumerate(round_cols):
                with round_col:
                    home_colour, away_colour = _round_colours(r)
                    suffix = f" ({home_colour}/{away_colour})" if home_colour else ""
                    st.markdown(f"**Round {r + 1}{suffix}**")
                    if not sheet_fill_colours:
                        st.selectbox("Away colour", ["", "W", "B"],
                                     key=f"colour_r{r}",
                                     help="Colour drawn for the away team in "
                                          "this round; home plays the opposite.")
                    for b in range(n_boards):
                        h_pid, a_pid = pairings[r][b]
                        h_disp = player_data.get(h_pid, {}).get('display', '?') if h_pid else '—'
                        a_disp = player_data.get(a_pid, {}).get('display', '?') if a_pid else '—'
                        st.selectbox(f"Bd {b + 1}", RESULT_OPTIONS,
                                     key=f"result_r{r}_b{b}",
                                     index=None,
                                     placeholder=_pairing_placeholder(h_pid, a_pid),
                                     help=f"{h_disp}  vs  {a_disp}")

        # --- Match Email ---
        st.divider()
        st.subheader("Match Email")
        st.caption("Enter the board results above, then copy this summary "
                   "for the results email group. Unentered results appear "
                   "as '_' to fill in.")

        def _email_player(pid):
            if not pid:
                return None
            d = player_data.get(pid, {})
            return {
                'name': d.get('full_name', ''),
                'pnum': d.get('pnum', ''),
                'rating': d.get('rating_str', ''),
            }

        email_rounds = []
        for r in range(n_rounds):
            home_colour, away_colour = _round_colours(r)
            pairs = []
            for b, (h_pid, a_pid) in enumerate(pairings[r]):
                # All Play All colours live in the round header; Standard
                # colours are written per player on each board line.
                h_col, a_col = ("", "") if is_all_play_all else _board_colours(r, b)
                pairs.append({
                    'home': _email_player(h_pid),
                    'away': _email_player(a_pid),
                    'result': st.session_state.get(f"result_r{r}_b{b}") or "",
                    'home_colour': h_col,
                    'away_colour': a_col,
                })
            email_rounds.append({
                'colours': f"{home_colour}/{away_colour}" if home_colour else None,
                'pairs': pairs,
            })

        _, computed_total, n_missing = compute_totals(email_rounds)
        computed_str = (f"{format_points(computed_total[0])} - "
                        f"{format_points(computed_total[1])}")

        fs_col, _ = st.columns([1, 2])
        final_input = fs_col.text_input(
            "Final score (home - away)",
            key="final_score_input",
            placeholder=f"auto-filled: {computed_str}" if n_missing == 0
            else "e.g. 9.5 - 6.5",
            help="Leave blank to use the total of the entered board results.",
        )

        final_override = None
        if final_input.strip():
            m = re.match(r"^\s*(\d+(?:\.5)?)\s*[-–]\s*(\d+(?:\.5)?)\s*$",
                         final_input)
            if not m:
                st.warning("Couldn't read the final score — enter it like "
                           "'9.5 - 6.5'.")
            else:
                final_override = (float(m.group(1)), float(m.group(2)))
                if n_missing == 0 and final_override != computed_total:
                    st.warning(
                        f"Something doesn't add up: the board results total "
                        f"{computed_str}, but the final score entered is "
                        f"{format_points(final_override[0])} - "
                        f"{format_points(final_override[1])}. Check the "
                        f"results or the final score."
                    )
        if n_missing:
            st.info(f"{n_missing} board result(s) not entered yet.")

        email_text = build_match_email(
            home_team=st.session_state.home_team_name or "Home",
            away_team=st.session_state.away_team_name or "Away",
            date_str=date_str,
            rounds=email_rounds,
            is_all_play_all=is_all_play_all,
            final_score=final_override,
        )
        st.code(email_text, language="text")
