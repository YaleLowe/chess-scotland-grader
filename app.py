import streamlit as st
import pandas as pd
from chess_grading import get_player_grading

st.set_page_config(
    page_title="Chess Scotland Grading Lookup",
    page_icon="♟️",
    layout="wide"
)

st.title("♟️ Chess Scotland Grading Lookup")
st.markdown("Enter a list of player names below to retrieve their grading information.")

# --- 1. Top: Input Section ---
names_input = st.text_area(
    "Player Names (one per line or comma-separated)", 
    height=150, 
    placeholder="e.g.\nNathanael Loch\nAndrew Greet"
)

# --- 2. Middle: Options (Landscape) ---
st.subheader("Data Options")

# Create 4 columns for options to make it landscape
opt_col1, opt_col2, opt_col3, opt_col4 = st.columns(4)

with opt_col1:
    st.markdown("**General**")
    show_pnum = st.checkbox("Pnum", value=True) # Changed default to True as useful for copy
    show_club = st.checkbox("Club", value=True)
    show_status = st.checkbox("Status", value=False)

with opt_col2:
    st.markdown("**Standard**")
    show_std_live = st.checkbox("Live (Std)", value=True)
    show_std_pub = st.checkbox("Published (Std)", value=False)

with opt_col3:
    st.markdown("**Allegro**")
    show_alg_live = st.checkbox("Live (Alg)", value=False)
    show_alg_pub = st.checkbox("Published (Alg)", value=False)

with opt_col4:
    st.markdown("**Blitz**")
    show_blitz_live = st.checkbox("Live (Blitz)", value=False)
    show_blitz_pub = st.checkbox("Published (Blitz)", value=False)

# --- Action ---
if st.button("Get Grading", type="primary"):
    if not names_input.strip():
        st.warning("Please enter at least one name.")
    else:
        # Normalize input: split by newlines or commas
        raw_names = names_input.replace(',', '\n').split('\n')
        names_list = [n.strip() for n in raw_names if n.strip()]
        
        if not names_list:
            st.warning("No valid names found.")
            st.stop()

        with st.spinner(f"Fetching data for {len(names_list)} players..."):
            results_map = get_player_grading(names_list)
        
        # Flatten results
        flat_data = []
        for input_name, matches in results_map.items():
            if not matches:
                # Not Found
                placeholder = {
                    "Match Status": "❌",
                    "Name": f"{input_name} (Not Found)",
                    "Pnum": "", "Club": "", "Status": "",
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
                        "Status": row.get('status', ''),
                        "Live (Std)": row.get('standard_live', ''),
                        "Published (Std)": row.get('standard_published', ''),
                        "Live (Alg)": row.get('allegro_live', ''),
                        "Published (Alg)": row.get('allegro_published', ''),
                        "Live (Blitz)": row.get('blitz_live', ''),
                        "Published (Blitz)": row.get('blitz_published', ''),
                        # Internal use for logic if needed, but display_row is what goes to DF
                    }
                    flat_data.append(display_row)
        
        if flat_data:
            df = pd.DataFrame(flat_data)
            
            # --- Sorting Logic ---
            # Convert grade columns to numeric for proper sorting
            grade_cols = [
                "Live (Std)", "Published (Std)", 
                "Live (Alg)", "Published (Alg)", 
                "Live (Blitz)", "Published (Blitz)"
            ]
            
            # We want to keep the DataFrame numeric for sorting, but maybe display formatted?
            # Streamlit displays NaNs as empty or <NA>, which is fine.
            # "UG" or empty strings will turn into NaN with errors='coerce'
            for col in grade_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # Select Columns to Show
            # Default Order: Match | Name | Pnum | Club | Status | ...
            cols_to_show = ["Match Status", "Name"]
            if show_pnum: cols_to_show.append("Pnum")
            if show_club: cols_to_show.append("Club")
            if show_status: cols_to_show.append("Status")
            
            if show_std_live: cols_to_show.append("Live (Std)")
            if show_std_pub: cols_to_show.append("Published (Std)")
            
            if show_alg_live: cols_to_show.append("Live (Alg)")
            if show_alg_pub: cols_to_show.append("Published (Alg)")
            
            if show_blitz_live: cols_to_show.append("Live (Blitz)")
            if show_blitz_pub: cols_to_show.append("Published (Blitz)")
            
            # Filter columns
            final_df = df[[c for c in cols_to_show if c in df.columns]]
            
            # Display Table
            st.dataframe(final_df, use_container_width=True, hide_index=True)
            
            # --- Copy Functionality ---
            st.divider()
            st.subheader("Copy to Clipboard")
            
            # Generate the formatted strings
            copy_lines = []
            
            # We iterate over the ORIGINAL flat_data (list of dicts) before numeric conversion 
            # so we have granular control over the data, OR we can use the DataFrame row.
            # Using the DataFrame `final_df` is risky because we might have converted to NaNs.
            # Let's use `flat_data` but filter by `cols_to_show` logic essentially.
            
            for row in flat_data:
                # Skip "Not Found" rows for copy usually? Or include them?
                # User example showed valid players. Let's exclude ones with "❌" match status for cleanliness?
                # Or perhaps include them so user knows what's missing. User didn't specify.
                # Assuming valid players only for the email format.
                if "❌" in row["Match Status"]:
                    continue
                    
                name = row["Name"]
                pnum = row["Pnum"]
                
                # Grade Logic
                # "Nathanael Loch [30187] (1515)"
                # Priority: Published (Std) > Live (Std) > None
                # BUT ONLY IF CHECKED
                
                grade_val = ""
                
                # Check 1: Is Published (Std) checked and does it exist?
                if show_std_pub and row.get("Published (Std)"):
                     grade_val = row.get("Published (Std)")
                # Check 2: Else if Live (Std) checked and exists?
                elif show_std_live and row.get("Live (Std)"):
                     grade_val = row.get("Live (Std)")
                
                # Construct string
                # <Name> [<Pnum>] (<Grade>)
                # If no grade selected/found: <Name> [<Pnum>]
                
                line = f"{name} [{pnum}]"
                if grade_val:
                    line += f" ({grade_val})"
                
                copy_lines.append(line)
            
            if copy_lines:
                c1, c2 = st.columns(2)
                
                with c1:
                    st.markdown("##### Multiline Copy")
                    multiline_text = "\n".join(copy_lines)
                    st.code(multiline_text, language="text")
                    
                with c2:
                    st.markdown("##### Single Line Copy")
                    singleline_text = " ".join(copy_lines)
                    st.code(singleline_text, language="text")
            
            else:
                st.info("No valid player data to copy.")

        else:
            st.error("No data found.")
