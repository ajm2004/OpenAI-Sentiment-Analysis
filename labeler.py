import streamlit as st
import pandas as pd
import os
import glob
from streamlit_shortcuts import button, add_keyboard_shortcuts

# Configure full screen width
st.set_page_config(page_title="Data Labelling Application", layout="wide")

# Hardcoded password and file path
PASSWORD = "f20aa5"
FILE = ""  # default; will be overwritten in main()

def find_next_contradiction(df, current_index):
    """Find the next contradicting record after the given index."""
    def check_contradiction(row):
        label1 = str(row.get('label_1', '')).lower()
        label2 = str(row.get('label_2', '')).lower()
        manual_label_exists = pd.notna(row.get('m_label_1')) and row.get('m_label_1') != ""
        return pd.notna(label1) and pd.notna(label2) and label1 != label2 and not manual_label_exists

    for i in range(current_index + 1, len(df)):
        row = df.iloc[i]
        if 'label_1' in df.columns and 'label_2' in df.columns:
            if check_contradiction(row):
                return i
    return len(df) - 1  # If no more contradictions found

def update_label(label):
    """Callback to update the manual label, advance the index, and write to CSV."""
    idx = st.session_state.index  # current record index
    original_idx = st.session_state.df.index[idx]  # get the original index
    label_map = {"Positive": 1, "Neutral": 0, "Negative": -1, "Irrelevant": 2}
    
    # Read the complete original file
    full_df = pd.read_csv(FILE, engine='pyarrow')
    # Update the specific row in the complete dataset
    full_df.at[original_idx, "m_label_1"] = label_map.get(label, "None")
    # Save the complete dataset
    full_df.to_csv(FILE, index=False)
    
    # Update the working dataset
    st.session_state.df.at[idx, "m_label_1"] = label_map.get(label, "None")
    
    # Move to next record based on mode
    if st.session_state.current_mode == "Contradiction Resolution":
        next_idx = find_next_contradiction(st.session_state.df, idx)
        if next_idx >= len(st.session_state.df):
            st.success("All contradictions reviewed!")
        st.session_state.index = next_idx
    else:
        st.session_state.index = idx + 1 if idx + 1 < len(st.session_state.df) else len(st.session_state.df)

def sidebar_controls():
    global FILE
    # --- Sidebar: File Selection & Data Update ---
    csv_files = glob.glob(os.path.join("Data", "*.csv"))
    if not csv_files:
        st.error("No CSV files found in Data directory.")
        st.stop()
    selected_file = st.sidebar.selectbox(
        "Select CSV file",
        csv_files,
        index=csv_files.index(FILE) if FILE in csv_files else 0
    )
    FILE = selected_file

    if st.session_state.get("selected_file") != FILE:
        st.session_state.selected_file = FILE
        try:
            df_new = pd.read_csv(FILE, engine='pyarrow')
            if st.session_state.current_mode == "Contradiction Resolution":
                # Filter for contradictions between label_1 and label_2
                df_new = df_new[
                    (df_new['label_1'].notna()) & 
                    (df_new['label_2'].notna()) & 
                    (df_new['label_1'] != df_new['label_2'])
                ]
                if len(df_new) == 0:
                    st.warning("No contradictions found in this file!")
                    df_new = pd.read_csv(FILE, engine='pyarrow')  # Reset to full dataset
        except Exception as e:
            st.error(f"Error reading CSV file '{FILE}': {e}")
            st.stop()
        if "text" not in df_new.columns:
            st.error("CSV file must contain a 'text' column.")
            st.stop()
        if "m_label_1" not in df_new.columns:
            df_new["m_label_1"] = ""
        st.session_state.df = df_new.copy()
        not_labelled = st.session_state.df.index[
            (st.session_state.df["m_label_1"].isna()) | (st.session_state.df["m_label_1"] == "")
        ]
        st.session_state.index = int(not_labelled[0]) if len(not_labelled) > 0 else 0

    # --- Sidebar: Title Toggle ---
    # if st.sidebar.checkbox("Show Title", value=True):
    st.title("Data Labelling Application")

    # --- Sidebar: Mode Selection ---
    mode = st.sidebar.selectbox("Select Mode", ["Full manually labelling", "Contradiction Resolution"])
    if mode != st.session_state.get('current_mode'):
        st.session_state.current_mode = mode
        # When switching to contradiction mode, find first contradiction
        if mode == "Contradiction Resolution":
            try:
                contradictions = st.session_state.df[
                    (st.session_state.df['label_1'].notna()) & 
                    (st.session_state.df['label_2'].notna()) & 
                    (st.session_state.df['label_1'].astype(str).str.lower() != 
                     st.session_state.df['label_2'].astype(str).str.lower())
                ].index
                
                if len(contradictions) > 0:
                    # Find the first contradiction's position in the full dataset
                    st.session_state.index = find_next_contradiction(st.session_state.df, -1)
                    st.info(f"Found {len(contradictions)} contradictions")
                else:
                    st.warning("No contradictions found!")
                    st.session_state.index = 0
            except KeyError as e:
                st.error(f"Required column not found: {str(e)}")
                st.session_state.current_mode = "Full manually labelling"

    # --- Sidebar: Export Option ---
    if "df" in st.session_state:
        csv_data = st.session_state.df.to_csv(index=False).encode("utf-8")
        st.sidebar.download_button(label="Export CSV", data=csv_data, file_name="exported_data.csv", mime="text/csv")

    # --- Sidebar: Jump-to-Record Control (1-indexed) ---
    total_records = len(st.session_state.df)
    jump = st.sidebar.number_input(
        "Jump to record (1-indexed)",
        min_value=1,
        max_value=total_records,
        value=st.session_state.index + 1 if st.session_state.index < total_records else total_records
    )
    if jump - 1 != st.session_state.index:
        st.session_state.index = jump - 1

def display_full_labeling():
    df = st.session_state.df
    index = st.session_state.index
    total_records = len(df)
    st.write(f"Labeling record {index + 1} of {total_records}")

    # --- Base CSS and JavaScript for Button Navigation ---
    st.markdown(
        """
        <style>
        div.stButton > button {
            width: 100% !important;
            height: 50px !important;
            font-size: 20px !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        div.stButton > button:focus {
            box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.5) !important;
            outline: none !important;
        }
        .center-vertical {
            display: flex;
            flex-direction: column;
            gap: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # --- Grid Layout: Left (Text Areas) & Right (Labels) ---
    col_left, col_right = st.columns(2)
    with col_left:
        if "Cleaned Text" in df.columns:
            st.markdown("### Cleaned Text:")
            st.text_area("Cleaned Text", value=str(df.iloc[index]["Cleaned Text"]), height=150, disabled=True)
        st.markdown("### Original Text:")
        if "text" in df.columns:
            st.text_area("Original Text", value=str(df.iloc[index]["text"]), height=150, disabled=True)
        else:
            st.write("No original text available.")
    
    with col_right:
        st.markdown("##### Automated Label:")
        label_mapping = {1: "Positive", 0: "Neutral", -1: "Negative", 2: "Irrelevant"}
        raw = df.iloc[index].get("label_1", None)
        automated_label = label_mapping.get(raw, str(raw)) if pd.notna(raw) and raw != "" else "None"
        st.markdown(f"Label: {automated_label}")
        if "score_1" in df.columns:
            score = df.iloc[index]["score_1"]
            st.markdown(f"Score: {score:.3f}" if pd.notna(score) else "##### Score: None")

        st.markdown("---")

        st.markdown("##### Manual Label:")
        manual = df.iloc[index]["m_label_1"]
        manual_label_text = manual if pd.notna(manual) and manual != "" else "None"
        number_map = {
            1: "Positive 😊",
            0: "Neutral 😐",
            -1: "Negative 😞",
            2: "Irrelevant ❌",
            "None": "No label"
        }
        st.markdown(f"{number_map.get(manual_label_text, 'No label')}")

    # --- Label Selection Buttons ---
    st.markdown("### Select a label:")
    cols = st.columns(4)
    with cols[0]:
        button("Positive 😊", on_click=update_label, args=("Positive",), key="btn_positive", shortcut="1")
    with cols[1]:
        button("Neutral 😐", on_click=update_label, args=("Neutral",), key="btn_neutral", shortcut="2")
    with cols[2]:
        button("Negative 😞", on_click=update_label, args=("Negative",), key="btn_negative", shortcut="3")
    with cols[3]:
        button("Irrelevant ❌", on_click=update_label, args=("Irrelevant",), key="btn_irrelevant", shortcut="4")

    # --- Completion Check ---
    if index >= total_records:
        st.success("Labelling complete!")
        st.write("Below is your updated DataFrame:")
        st.dataframe(df)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(label="Download Labelled CSV", data=csv, file_name="labelled_data.csv", mime="text/csv")

def display_contradiction_resolution():
    df = st.session_state.df
    index = st.session_state.index
    total_records = len(df)
    
    # Check if current record is a contradiction
    is_contradiction = False
    if 'label_1' in df.columns and 'label_2' in df.columns:
        current_label = str(df.iloc[index].get('label_1', '')).lower()
        current_label2 = str(df.iloc[index].get('label_2', '')).lower()
        is_contradiction = (current_label != current_label2 and 
                          pd.notna(current_label) and 
                          pd.notna(current_label2))
    
    # Add visual indicator for contradictions
    status_color = "🔴" if is_contradiction else "⚪"
    st.write(f"{status_color} Reviewing record {index + 1} of {total_records}")

    # Apply the same CSS as full labeling mode
    st.markdown(
        """
        <style>
        div.stButton > button {
            width: 100% !important;
            height: 50px !important;
            font-size: 20px !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Main content area
    col_left, col_right = st.columns(2)
    
    with col_left:
        # Display Cleaned Text
        st.markdown("### Cleaned Text:")
        cleaned_text = str(df.iloc[index].get("Cleaned Text", "Field not available"))
        st.text_area("Cleaned Text", value=cleaned_text, height=150, disabled=True)

    with col_right:
        # Display Labels and Sentiment
        st.markdown("### Labels and Sentiment")
        
        # Automated Label (label_1)
        st.markdown("##### Automated Label 1:")
        label_mapping = {1: "Positive", 0: "Neutral", -1: "Negative", 2: "Irrelevant"}
        raw_label = df.iloc[index].get("label_1", None)
        automated_label = label_mapping.get(raw_label, str(raw_label)) if pd.notna(raw_label) else "Not available"
        st.markdown(f"Label: {automated_label}")

        # Sentiment Score
        sentiment = df.iloc[index].get("score_1", None)
        sentiment_text = f"{sentiment:.3f}" if pd.notna(sentiment) else "Not available"
        st.markdown(f"Score: {sentiment_text}")

        # Separator
        st.markdown("---")

        # Automated Label 2 (label_2)
        st.markdown("##### Automated Label 2:")
        raw_label_2 = df.iloc[index].get("label_2", None)
        automated_label_2 = label_mapping.get(raw_label_2, str(raw_label_2)) if pd.notna(raw_label_2) else "Not available"
        st.markdown(f"Label: {automated_label_2}")

        # Reason Field
        reason = df.iloc[index].get("Reason", "Not available")
        st.markdown(f"Reason: {reason}")

        # Separator
        st.markdown("---")

        # Manual Label
        st.markdown("##### Manual Label:")
        manual = df.iloc[index].get("m_label_1", None)
        number_map = {
            1: "Positive 😊",
            0: "Neutral 😐",
            -1: "Negative 😞",
            2: "Irrelevant ❌",
            "None": "No label"
        }
        manual_label = number_map.get(manual, "Not available") if pd.notna(manual) else "Not available"
        st.markdown(f"**{manual_label}**")

    # Label Selection Buttons
    st.markdown("### Update Label:")
    cols = st.columns(4)
    with cols[0]:
        button("Positive 😊", on_click=update_label, args=("Positive",), key="cr_btn_positive", shortcut="1")
    with cols[1]:
        button("Neutral 😐", on_click=update_label, args=("Neutral",), key="cr_btn_neutral", shortcut="2")
    with cols[2]:
        button("Negative 😞", on_click=update_label, args=("Negative",), key="cr_btn_negative", shortcut="3")
    with cols[3]:
        button("Irrelevant ❌", on_click=update_label, args=("Irrelevant",), key="cr_btn_irrelevant", shortcut="4")

    # Completion Check
    if index >= total_records:
        st.success("Review complete!")
        st.write("Below is your updated DataFrame:")

        # Fill the manual labels missing in the original dataset with label_1 if label_1 == label_2
        df['m_label_1'] = df.apply(lambda x: x['label_1'] if pd.isna(x['m_label_1']) and str(x['label_1']).lower() == str(x['label_2']).lower() else x['m_label_1'], axis=1)

        st.dataframe(df)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Reviewed CSV",
            data=csv,
            file_name="reviewed_data.csv",
            mime="text/csv"
        )

def main_screen():
    if st.session_state.current_mode == "Full manually labelling":
        display_full_labeling()
    else:
        display_contradiction_resolution()

def main():
    global FILE

    auth_container = st.empty()
    if not st.session_state.get("authenticated", False):
        password = auth_container.text_input("Enter Password", type="password", key="password_input")
        if password:
            if password == PASSWORD:
                st.session_state.authenticated = True
                auth_container.empty()  # Remove the password input after correct entry.
            else:
                st.error("Incorrect password!")
                st.stop()
        else:
            st.info("Please enter your password to continue.")
            st.stop()
    
    # --- Automatically load the first CSV if FILE is empty or does not exist ---
    if not FILE or not os.path.exists(FILE):
        csv_files = glob.glob(os.path.join("Data", "*.csv"))
        if not csv_files:
            st.error("No CSV files found in Data directory.")
            st.stop()
        FILE = csv_files[0]
    try:
        df = pd.read_csv(FILE, engine='pyarrow')
    except Exception as e:
        st.error(f"Error reading CSV file '{FILE}': {e}")
        st.stop()
    if "text" not in df.columns:
        st.error("CSV file must contain a 'text' column.")
        st.stop()
    if "m_label_1" not in df.columns:
        df["m_label_1"] = ""
    if "df" not in st.session_state:
        st.session_state.df = df.copy()
        not_labelled = st.session_state.df.index[(st.session_state.df["m_label_1"].isna()) | (st.session_state.df["m_label_1"] == "")]
        st.session_state.index = int(not_labelled[0]) if len(not_labelled) > 0 else 0

    if not hasattr(st.session_state, 'current_mode'):
        st.session_state.current_mode = "Full manually labelling"

    sidebar_controls()
    main_screen()

if __name__ == "__main__":
    main()
