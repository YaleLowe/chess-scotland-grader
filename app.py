import streamlit as st
import pandas as pd
from chess_grading import get_player_grading

st.set_page_config(
    page_title="Chess Scotland Grading Lookup",
    page_icon="♟️",
    layout="wide"
)


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
            
            if not name_part: continue
            
            is_single = len(name_part.split()) == 1
            
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
    for input_name, matches in results_map.items():
        if matches and isinstance(matches[0], dict) and matches[0].get('invalid_query'):
            # Handle Invalid Query (Name < 3 chars)
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
            for match in matches:
                row = match.copy()
                
                # Determine match status
                status_icon = "✅"
                if len(matches) > 1:
                    status_icon = "⚠️ Multiple"

                display_row = {
                    "Match Status": status_icon,
                    "Name": row.get('name', ''),
                    "Pnum": row.get('pnum', ''),
                    "Club": row.get('club', ''),
                    "Age": row.get('age', ''),
                    "Live (Std)": row.get('standard_live', ''),
                    "Published (Std)": row.get('standard_published', ''),
                    "Live (Alg)": row.get('allegro_live', ''),
                    "Published (Alg)": row.get('allegro_published', ''),
                    "Live (Blitz)": row.get('blitz_live', ''),
                    "Published (Blitz)": row.get('blitz_published', ''),
                }
                flat_data.append(display_row)
    
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
        
        # Generate the formatted strings
        copy_items = []
        
        for row in flat_data:
            # Skip "Not Found" rows
            if "❌" in row["Match Status"]:
                continue
                
            raw_name = row["Name"]
            pnum = row["Pnum"]
            
            # 1. Format Name
            display_name = raw_name
            if ',' in raw_name:
                parts = raw_name.split(',', 1)
                if len(parts) == 2:
                    display_name = f"{parts[1].strip()} {parts[0].strip()}"
            
            # 2. Grade Logic
            # Priority: Published (Std) > Live (Std)
            grade_str = ""
            sort_val = -1
            
            if show_std_pub and row.get("Published (Std)"):
                    grade_str = row.get("Published (Std)")
            elif show_std_live and row.get("Live (Std)"):
                    grade_str = row.get("Live (Std)")
            
            if grade_str and str(grade_str).isdigit():
                sort_val = int(grade_str)
            
            line = f"{display_name} [{pnum}]"
            if grade_str:
                line += f" ({grade_str})"
            
            copy_items.append({
                'text': line,
                'sort_val': sort_val
            })
        
        if copy_items:
            # Sort descending by grade
            copy_items.sort(key=lambda x: x['sort_val'], reverse=True)
            
            sorted_lines = [item['text'] for item in copy_items]
            
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown("##### Multiline Copy (Sorted)")
                multiline_text = "\n".join(sorted_lines)
                st.code(multiline_text, language="text")
                
            with c2:
                st.markdown("##### Single Line Copy (Sorted)")
                singleline_text = ", ".join(sorted_lines)
                st.code(singleline_text, language="text")
        
        else:
            st.info("No valid player data to copy.")

    else:
        st.error("No data found.")
