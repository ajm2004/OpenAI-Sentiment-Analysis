import streamlit as st
import pandas as pd
from streamlit_shortcuts import button, add_keyboard_shortcuts

# Configure full screen width
st.set_page_config(page_title="Data Labelling Application", layout="wide")

# Hardcoded password and file path
PASSWORD = "f20aa5"
FILE = "Data/labelled_data_1.csv"

def update_label(label):
    """Callback to update the manual label, advance the index, and write to CSV."""
    idx = st.session_state.index  # current record index
    st.session_state.df.at[idx, "m_label_1"] = label
    st.session_state.index = idx + 1
    st.session_state.df.to_csv(FILE, index=False)

def main():
    # --- Authentication ---
    # auth_container = st.empty()
    # if not st.session_state.get("authenticated", False):
    #     password = auth_container.text_input("Enter Password", type="password", key="password_input")
    #     if password:
    #         if password == PASSWORD:
    #             st.session_state.authenticated = True
    #             auth_container.empty()  # Remove the password input after correct entry.
    #         else:
    #             st.error("Incorrect password!")
    #             st.stop()
    #     else:
    #         st.info("Please enter your password to continue.")
    #         st.stop()

    # Now that the user is authenticated, show the title toggle
    show_title = st.sidebar.checkbox("Show Title", value=True)
    if show_title:
        st.title("Data Labelling Application")

    # --- Sidebar: Mode Selection ---
    mode = st.sidebar.selectbox("Select Mode", ["Full manually labelling", "Contradiction Resolution"])
    if mode == "Contradiction Resolution":
        st.write("TODO")
        return

    # --- Load CSV from Default File ---
    try:
        df = pd.read_csv(FILE,engine='pyarrow')
    except Exception as e:
        st.error(f"Error reading CSV file '{FILE}': {e}")
        st.stop()

    # Check for required column.
    if "Cleaned Text" not in df.columns:
        st.error("CSV file must contain a 'Cleaned Text' column.")
        st.stop()

    # Add m_label_1 column if missing.
    if "m_label_1" not in df.columns:
        df["m_label_1"] = ""

    # --- Session State Setup ---
    if "df" not in st.session_state:
        st.session_state.df = df.copy()
        # Start at the first record with no manual label.
        not_labelled = st.session_state.df.index[
            (st.session_state.df["m_label_1"].isna()) | (st.session_state.df["m_label_1"] == "")
        ]
        st.session_state.index = int(not_labelled[0]) if len(not_labelled) > 0 else 0

    # Work with session state DataFrame and index.
    df = st.session_state.df
    index = st.session_state.index
    total_records = len(df)

    # --- Sidebar: Jump-to-Record Control (1-indexed) ---
    jump_index = st.sidebar.number_input(
        "Jump to record (1-indexed)",
        min_value=1,
        max_value=total_records,
        value=index + 1,
        step=1,
        key="jump_input"
    )
    # Update index if jump index is changed.
    if jump_index - 1 != index:
        st.session_state.index = jump_index - 1
        index = st.session_state.index

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
        # .stVerticalBlock{
        #     gap: 0 !important;
        #     }

        
        </style>
        """,
        unsafe_allow_html=True,
    )

    # --- Grid Layout: Left - Text Areas; Right - Label Buttons ---
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("### Original Text:")
        if "text" in df.columns:
            st.text_area("Original Text", value=str(df.iloc[index]["text"]), height=150, disabled=True)
        else:
            st.write("No original text available.")
        
        st.markdown("### Cleaned Text:")
        st.text_area("Cleaned Text", value=str(df.iloc[index]["Cleaned Text"]), height=150, disabled=True)
    with col_right:
        st.markdown("### Automated Label:")
        label_mapping = {1: "Positive", 0: "Neutral", -1: "Negative"}
        automated_label = "None"
        if "label_1" in df.columns and pd.notna(df.iloc[index]["label_1"]) and df.iloc[index]["label_1"] != "":
            raw_label = df.iloc[index]["label_1"]
            automated_label = label_mapping.get(raw_label, str(raw_label))
        st.markdown(f"##### Label: {automated_label}")
        if "score_1" in df.columns:
            score = df.iloc[index]["score_1"]
            if pd.notna(score):
                st.markdown(f"##### Score: {score:.3f}")
            else:
                st.markdown("##### Score: None")

        # Seperator
        st.markdown("---")
                
        st.markdown("### Manual Label:")
        manual_label_text = (
            df.iloc[index]["m_label_1"]
            if pd.notna(df.iloc[index]["m_label_1"]) and df.iloc[index]["m_label_1"] != ""
            else "None"
        )
        emoji_map = {
            "Positive": "😊",
            "Neutral": "😐", 
            "Negative": "😞",
            "Irrelevant": "❌",
            "None": "❓"
        }
        emoji = emoji_map.get(manual_label_text, "❓")
        st.markdown(f"##### {manual_label_text} {emoji}")
        


    st.markdown("### Select a label:")
    # Create a horizontal layout with columns
    cols = st.columns(4)
    
    with cols[0]:
        button("Positive 😊", on_click=update_label, args=("Positive",), key="btn_positive", shortcut="1")
    with cols[1]:    
        button("Neutral 😐", on_click=update_label, args=("Neutral",), key="btn_neutral", shortcut="2")
    with cols[2]:
        button("Negative 😞", on_click=update_label, args=("Negative",), key="btn_negative", shortcut='3')
    with cols[3]:
        button("Irrelevant ❌", on_click=update_label, args=("Irrelevant",), key="btn_irrelevant", shortcut='4')

    # --- Display Automated and Manual Labels in a Two-Column Grid ---
    
        

    # --- Completion ---
    if index >= total_records:
        st.success("Labelling complete!")
        st.write("Below is your updated DataFrame:")
        st.dataframe(df)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Labelled CSV",
            data=csv,
            file_name="labelled_data.csv",
            mime="text/csv",
        )

if __name__ == "__main__":
    main()
