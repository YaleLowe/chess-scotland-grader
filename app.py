import re

import streamlit as st
import pandas as pd
from chess_grading import get_player_grading, get_clubs_list

st.set_page_config(
    page_title="Chess Scotland Grading Lookup",
    page_icon="♟️",
    layout="wide"
)

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

st.title("♟️ Chess Scotland Grading Lookup")
st.markdown("Enter a list of player names below to retrieve their grading information.")

# --- 1. Top: Input Section ---

# History Navigation
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
        if query in st.session_state.search_history:
            st.session_state.search_history.remove(query)
        st.session_state.search_history.append(query)
        st.session_state.history_index = len(st.session_state.search_history) - 1


with hist_col1:
    st.button("◀️ Previous", on_click=on_prev, disabled=(st.session_state.history_index <= 0))

with hist_col2:
    st.button("Next ▶️", on_click=on_next, disabled=(st.session_state.history_index >= len(st.session_state.search_history) - 1))

names_input = st.text_area(
    "Player Names (one per line)\nFormat: 'Name [PNUM]' or 'Name; Club'",
    height=150,
    placeholder="e.g.\nNathanael Loch\nSmith, John [12345] (Grading ignored)\n; ST (for just members of club stirling)",
    key="current_search_query"
)

# --- 2. Middle: Options (Landscape) ---
st.subheader("Data Options")

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
        raw_lines = names_input.split('\n')

        parsed_queries = []
        valid_raw_lines = []

        for line in raw_lines:
            line = line.strip()
            if not line:
                continue

            pnum_match = re.search(r'\[(\d+)\]', line)

            if pnum_match:
                pnum = pnum_match.group(1)
                parsed_queries.append({
                    'raw': line,
                    'pnum': pnum,
                    'name': '',
                    'club': '',
                    'is_single': False,
                })
            else:
                parts = line.split(';', 1)
                name_part = parts[0].strip()
                club_part = parts[1].strip() if len(parts) > 1 else ""

                # Strip existing grading info in parentheses
                name_part = re.sub(r'\(.*?\)', '', name_part).strip()

                # Normalise "Surname, Forename" -> "Forename Surname"
                if ',' in name_part:
                    n_parts = name_part.split(',', 1)
                    if len(n_parts) == 2:
                        name_part = f"{n_parts[1].strip()} {n_parts[0].strip()}"

                if not name_part and not club_part:
                    continue

                is_single = len(name_part.split()) == 1 if name_part else False

                parsed_queries.append({
                    'raw': line,
                    'name': name_part,
                    'club': club_part,
                    'is_single': is_single,
                })
            valid_raw_lines.append(line)

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
