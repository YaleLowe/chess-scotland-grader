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
CLUB_MAP = {c['code']: c['name'] for c in CLUBS} # Code -> Name

# --- Sidebar: Club Reference ---
with st.sidebar:
    st.header("ℹ️ Club Reference")
    st.markdown("Use these codes or names to filter by club.")
    if CLUBS:
        club_df = pd.DataFrame(CLUBS)
        st.dataframe(club_df, hide_index=True, use_container_width=True)


# --- Session State Initialization ---
if "player_cache" not in st.session_state:
    st.session_state.player_cache = {}
if "active_names" not in st.session_state:
    st.session_state.active_names = []

st.title("♟️ Chess Scotland Grading Lookup")
st.markdown("Enter a list of player names below to retrieve their grading information.")

# --- 1. Top: Input Section ---
names_input = st.text_area(
    "Player Names (one per line)\nOptional: Add comma to filter by club (e.g. 'Nathanael Loch, ST')", 
    height=150, 
    placeholder="e.g.\nNathanael Loch\nnat loc\nst (for just members of club stirling)"
)

# --- 2. Middle: Options (Landscape) ---
st.subheader("Data Options")

# Create 4 columns for options to make it landscape
opt_col1, opt_col2, opt_col3, opt_col4 = st.columns(4)

with opt_col1:
    st.markdown("**General**")
    show_pnum = st.checkbox("Pnum", value=True) # Changed default to True as useful for copy
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
if st.button("Get Grading", type="primary"):
    if not names_input.strip():
        st.warning("Please enter at least one name.")
        st.session_state.active_names = []
    else:
        # Normalize input: split by newlines ONLY
        raw_lines = names_input.split('\n')
        
        # Parse lines into query objects
        # Format: "Name, Club" or just "Name"
        parsed_queries = []
        valid_raw_lines = []
        
        for line in raw_lines:
            line = line.strip()
            if not line: continue
            
            parts = line.split(',', 1)
            name_part = parts[0].strip()
            club_part = parts[1].strip() if len(parts) > 1 else ""
            
            # Allow empty name IF club part exists (e.g. ", Stirling")
            if not name_part and not club_part: continue
            
            is_single = len(name_part.split()) == 1 if name_part else False
            
            parsed_queries.append({
                'raw': line,
                'name': name_part,
                'club': club_part,
                'is_single': is_single
            })
            valid_raw_lines.append(line)
        
        if not parsed_queries:
            st.warning("No valid names found.")
            st.session_state.active_names = []
        else:
            # Check what's missing from cache
            # Cache keys are the raw lines from input
            missing_queries = [
                q for q in parsed_queries 
                if q['raw'] not in st.session_state.player_cache
            ]
            
            if missing_queries:
                with st.spinner(f"Fetching data for {len(missing_queries)} new players..."):
                    new_results = get_player_grading(missing_queries)
                    st.session_state.player_cache.update(new_results)
            
            # Update active set to trigger display
            st.session_state.active_names = valid_raw_lines

# --- Display Section ---
if st.session_state.active_names:
    # Retrieve data from cache
    results_map = {name: st.session_state.player_cache.get(name, []) for name in st.session_state.active_names}
    
    # Flatten results
    flat_data = []
    
    count_exact = 0
    count_possible = 0 # Exact + Multiple
    count_none = 0 # None + Invalid
    
    for input_name, matches in results_map.items():
        if matches and isinstance(matches[0], dict) and matches[0].get('invalid_query'):
            # Handle Invalid Query (Name < 3 chars)
            count_none += 1
            placeholder = {
                "Match Status": "⚠️ Ignored",
                "Name": f"{input_name} (Min 3 chars required)",
                "Pnum": "", "Club": "", "Age": "",
                "Live (Std)": "", "Published (Std)": "",
                "Live (Alg)": "", "Published (Alg)": "",
                "Live (Blitz)": "", "Published (Blitz)": ""
            }
            flat_data.append(placeholder)
        
        elif not matches:
            # Not Found
            count_none += 1
            placeholder = {
                "Match Status": "❌",
                "Name": f"{input_name} (Not Found)",
                "Pnum": "", "Club": "", "Age": "",
                "Live (Std)": "", "Published (Std)": "",
                "Live (Alg)": "", "Published (Alg)": "",
                "Live (Blitz)": "", "Published (Blitz)": ""
            }
            flat_data.append(placeholder)
        else:
            # Matches Found
            if len(matches) == 1:
                count_exact += 1
            
            # Count ALL matches for "Possible Matches" (User definition: Total ✅ + Total ⚠️)
            count_possible += len(matches)
                
            for match in matches:
                row = match.copy()
                
                # Determine match status
                status_icon = "✅"
                if len(matches) > 1:
                    status_icon = "⚠️ Multiple"

                # Format Club: Code (Full Name)
                c_code = row.get('club', '')
                c_display = c_code
                if c_code in CLUB_MAP:
                     c_display = f"{c_code} ({CLUB_MAP[c_code]})"

                display_row = {
                    "Match Status": status_icon,
                    "Name": row.get('name', ''),
                    "Pnum": row.get('pnum', ''),
                    "Club": c_display, # Use formatted club
                    "Age": row.get('age', ''),
                    "Live (Std)": row.get('standard_live', ''),
                    "Published (Std)": row.get('standard_published', ''),
                    "Live (Alg)": row.get('allegro_live', ''),
                    "Published (Alg)": row.get('allegro_published', ''),
                    "Live (Blitz)": row.get('blitz_live', ''),
                    "Published (Blitz)": row.get('blitz_published', ''),
                }
                flat_data.append(display_row)
    
    # --- Deduplication Logic ---
    # Prioritize Exact Matches (✅) over Multiple (⚠️)
    unique_data = {}
    placeholders = []
    
    for row in flat_data:
        # Separate valid player rows from placeholders (Ignored/Not Found)
        if "⚠️ Ignored" in row['Match Status'] or "❌" in row['Match Status']:
            placeholders.append(row)
            continue
            
        pnum = row.get('Pnum')
        name = row.get('Name')
        # Use Pnum as key if exists, else Name (fallback)
        key = str(pnum) if pnum else name
        
        if key in unique_data:
            existing = unique_data[key]
            # Replace existing if current is ✅ and existing is NOT
            if "✅" in row['Match Status'] and "✅" not in existing['Match Status']:
                 unique_data[key] = row
            # Else keep existing (or overwriting doesn't matter if both same)
        else:
            unique_data[key] = row
            
    # Reconstruct flat_data with unique rows + placeholders
    flat_data = list(unique_data.values()) + placeholders
    
    # --- Recalculate Tallies on Unique Data ---
    # Only count valid rows for Exact/Possible
    count_exact = 0
    count_possible = 0
    
    for row in unique_data.values():
        count_possible += 1
        if "✅" in row['Match Status']:
            count_exact += 1
            
    # count_none tracks invalid queries from the loop, but we also have placeholders in flat_data
    # Let's count placeholders for consistency
    count_none = len(placeholders)

    # --- Result Tallies ---
    t_col1, t_col2, t_col3 = st.columns(3)
    t_col1.metric("Exact Matches", count_exact)
    t_col2.metric("Possible Matches", count_possible)
    t_col3.metric("Non-existent/Invalid", count_none)
    
    if flat_data:
        df = pd.DataFrame(flat_data)
        
        # --- Sorting Logic ---
        # Convert grade columns to numeric for proper sorting
        grade_cols = [
            "Published (Std)", "Live (Std)", 
            "Published (Alg)", "Live (Alg)", 
            "Published (Blitz)", "Live (Blitz)"
        ]
        
        for col in grade_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Select Columns to Show
        # Default Order: Match | Name | Pnum | Club | Age | Pub(Std) | Live(Std) ...
        cols_to_show = ["Match Status", "Name"]
        if show_pnum: cols_to_show.append("Pnum")
        if show_club: cols_to_show.append("Club")
        if show_age: cols_to_show.append("Age")
        
        # Swapped order: Published first
        if show_std_pub: cols_to_show.append("Published (Std)")
        if show_std_live: cols_to_show.append("Live (Std)")
        
        if show_alg_pub: cols_to_show.append("Published (Alg)")
        if show_alg_live: cols_to_show.append("Live (Alg)")
        
        if show_blitz_pub: cols_to_show.append("Published (Blitz)")
        if show_blitz_live: cols_to_show.append("Live (Blitz)")
        
        # Filter columns
        final_df = df[[c for c in cols_to_show if c in df.columns]]
        
        # Display Table
        st.dataframe(final_df, use_container_width=True, hide_index=True)
        
        # --- Copy Functionality ---
        st.divider()
        st.subheader("Copy to Clipboard")
        st.caption("Copy formatted lists for emails or tournaments.")
        
        # Generate Copy String
        # Format: "Name [Pnum] (Grade)"
        # Grade Priority: Std Pub > Std Live > Alg Pub > Alg Live > Blitz Pub > Blitz Live
        
        copy_items = []
        
        # Define Priority List of (Key, CheckboxState)
        priority_list = [
            ('standard_published', show_std_pub),
            ('standard_live', show_std_live),
            ('allegro_published', show_alg_pub),
            ('allegro_live', show_alg_live),
            ('blitz_published', show_blitz_pub),
            ('blitz_live', show_blitz_live)
        ]
        
        # Map keys to display names in 'row' dict (from flat_data)
        flat_key_map = {
            'standard_published': "Published (Std)",
            'standard_live': "Live (Std)",
            'allegro_published': "Published (Alg)",
            'allegro_live': "Live (Alg)",
            'blitz_published': "Published (Blitz)",
            'blitz_live': "Live (Blitz)"
        }

        # Iterate over flat_data
        for row in flat_data:
            # Skip placeholder rows
            if "⚠️ Ignored" in str(row['Match Status']) or "❌" in str(row['Match Status']):
                continue
                
            raw_name = row.get('Name', '')
            pnum = row.get('Pnum', '')
            
            # 1. Format Name: "Surname, Forename" -> "Forename Surname"
            display_name = raw_name
            if ',' in raw_name:
                n_parts = raw_name.split(',', 1)
                if len(n_parts) == 2:
                    display_name = f"{n_parts[1].strip()} {n_parts[0].strip()}"
            
            # Determine Grade to show
            grade = ""
            sort_val = -1
            
            for key, is_checked in priority_list:
                if is_checked:
                    raw_val = row.get(flat_key_map[key], '')
                    if raw_val and str(raw_val).strip():
                        grade = str(raw_val)
                        # Try to get numeric value for sorting
                        try:
                            sort_val = int(grade)
                        except ValueError:
                            pass
                        break
            
            # Build String
            # format: Name [Pnum] (Grade)
            parts = [display_name]
            
            if show_pnum and pnum:
                parts.append(f"[{pnum}]")
                
            if grade:
                parts.append(f"({grade})")
                
            copy_items.append({
                'text': " ".join(parts),
                'sort_val': sort_val
            })
            
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("##### Multi-line Copy")
            # Sort descending by grade
            copy_items.sort(key=lambda x: x['sort_val'], reverse=True)
            sorted_lines = [str(item['text']) for item in copy_items]
            multiline_text = "\n".join(sorted_lines)
            st.code(multiline_text, language="text")
            
        with c2:
            st.markdown("##### Single Line Copy (Sorted)")
            # Single line sorted alphabetically by name (text)
            alpha_sorted_lines = sorted([str(item['text']) for item in copy_items])
            singleline_text = ", ".join(alpha_sorted_lines) 
            st.code(singleline_text, language="text")

