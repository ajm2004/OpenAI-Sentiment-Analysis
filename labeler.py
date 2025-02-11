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

def update_label(label):
    """Callback to update the manual label, advance the index, and write to CSV."""
    idx = st.session_state.index  # current record index
    label_map = {"Positive": 1, "Neutral": 0, "Negative": -1, "Irrelevant": 4}
    st.session_state.df.at[idx, "m_label_1"] = label_map.get(label, "None")
    st.session_state.index = idx + 1
    st.session_state.df.to_csv(FILE, index=False)

def sidebar_controls():
    global FILE  # move this to the start of the function
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
        except Exception as e:
            st.error(f"Error reading CSV file '{FILE}': {e}")
            st.stop()
        if "Cleaned Text" not in df_new.columns:
            st.error("CSV file must contain a 'Cleaned Text' column.")
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
    if mode == "Contradiction Resolution":
        st.write("TODO")
        st.stop()

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
        value=st.session_state.index + 1
    )
    if jump - 1 != st.session_state.index:
        st.session_state.index = jump - 1

def main_screen():
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
        st.markdown("### Cleaned Text:")
        st.text_area("Cleaned Text", value=str(df.iloc[index]["Cleaned Text"]), height=150, disabled=True)
        st.markdown("### Original Text:")
        if "text" in df.columns:
            st.text_area("Original Text", value=str(df.iloc[index]["text"]), height=150, disabled=True)
        else:
            st.write("No original text available.")
    with col_right:
        st.markdown("##### Automated Label:")
        label_mapping = {1: "Positive", 0: "Neutral", -1: "Negative"}
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
            4: "Irrelevant ❌",
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
    if "Cleaned Text" not in df.columns:
        st.error("CSV file must contain a 'Cleaned Text' column.")
        st.stop()
    if "m_label_1" not in df.columns:
        df["m_label_1"] = ""
    if "df" not in st.session_state:
        st.session_state.df = df.copy()
        not_labelled = st.session_state.df.index[(st.session_state.df["m_label_1"].isna()) | (st.session_state.df["m_label_1"] == "")]
        st.session_state.index = int(not_labelled[0]) if len(not_labelled) > 0 else 0

    sidebar_controls()
    main_screen()

if __name__ == "__main__":
    main()
