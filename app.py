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

# Input Section
col1, col2 = st.columns([2, 1])

with col1:
    names_input = st.text_area(
        "Player Names (one per line or comma-separated)", 
        height=200, 
        placeholder="e.g.\nNathanael Loch\nAndrew Greet"
    )

with col2:
    st.subheader("Select Data Columns")
    
    # Checkbox groups
    show_pnum = st.checkbox("Pnum", value=False)
    show_club = st.checkbox("Club", value=True)
    show_status = st.checkbox("Status", value=False)
    
    st.markdown("**Standard**")
    show_std_live = st.checkbox("Live (Std)", value=True)
    show_std_pub = st.checkbox("Published (Std)", value=False)
    
    st.markdown("**Allegro**")
    show_alg_live = st.checkbox("Live (Alg)", value=False)
    show_alg_pub = st.checkbox("Published (Alg)", value=False)
    
    st.markdown("**Blitz**")
    show_blitz_live = st.checkbox("Live (Blitz)", value=False)
    show_blitz_pub = st.checkbox("Published (Blitz)", value=False)

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
            # Call the backend
            results_map = get_player_grading(names_list)
        
        # Flatten results for display
        flat_data = []
        for input_name, matches in results_map.items():
            if not matches:
                # Handle not found
                # Create a placeholder dict with just the searched name and error status
                placeholder = {"Input Name": input_name, "Name": "Not Found", "Match Status": "❌"}
                flat_data.append(placeholder)
            else:
                for match in matches:
                    # Clean up the match dictionary for display
                    row = match.copy()
                    
                    # Rename keys for nicer display headers
                    # Map backend keys to display keys if needed, or just use as is
                    # Let's map for clarity if we want specific headers
                    display_row = {
                        "Input Name": input_name,
                        "Pnum": row.get('pnum', ''),
                        "Name": row.get('name', ''),
                        "Club": row.get('club', ''),
                        "Status": row.get('status', ''),
                        "Live (Std)": row.get('standard_live', ''),
                        "Published (Std)": row.get('standard_published', ''),
                        "Live (Alg)": row.get('allegro_live', ''),
                        "Published (Alg)": row.get('allegro_published', ''),
                        "Live (Blitz)": row.get('blitz_live', ''),
                        "Published (Blitz)": row.get('blitz_published', ''),
                    }
                    
                    # Add match status if needed, or just rely on Name existence
                    if len(matches) > 1:
                        display_row["Match Status"] = "⚠️ Multiple Matches"
                    else:
                        display_row["Match Status"] = "✅"
                        
                    flat_data.append(display_row)
        
        if flat_data:
            df = pd.DataFrame(flat_data)
            
            # Determine which columns to show
            cols_to_show = ["Input Name", "Name", "Match Status"]
            if show_pnum: cols_to_show.append("Pnum")
            if show_club: cols_to_show.append("Club")
            if show_status: cols_to_show.append("Status")
            
            if show_std_live: cols_to_show.append("Live (Std)")
            if show_std_pub: cols_to_show.append("Published (Std)")
            
            if show_alg_live: cols_to_show.append("Live (Alg)")
            if show_alg_pub: cols_to_show.append("Published (Alg)")
            
            if show_blitz_live: cols_to_show.append("Live (Blitz)")
            if show_blitz_pub: cols_to_show.append("Published (Blitz)")
            
            # Filter and reorder dataframe
            # Only include columns that exist in data (to avoid errors if keys missing)
            valid_cols = [c for c in cols_to_show if c in df.columns]
            final_df = df[valid_cols]
            
            st.dataframe(final_df, use_container_width=True, hide_index=True)
            
            # CSV Download
            csv = final_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download CSV",
                csv,
                "chess_grading_results.csv",
                "text/csv",
                key='download-csv'
            )
        else:
            st.error("No data could be processed.")
