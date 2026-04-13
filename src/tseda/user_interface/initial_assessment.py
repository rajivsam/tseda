"""Streamlit page for the initial time-series screening step."""

import streamlit as st
import pandas as pd

st.title("Initial Screening", anchor="initial-screening")

# Create the 2x2 grid using a ratio: [1, 3] makes the first column 1/3 the size of the second
row1_col1, row1_col2 = st.columns([1, 3], gap="medium",  vertical_alignment="bottom")
row2_col1, row2_col2 = st.columns(2)

# Row 1, Cell 1: Smaller File Uploader
with row1_col1:
    uploaded_file = st.file_uploader("Upload Data", type=['csv', 'xlsx'])

# Row 1, Cell 2: Larger Data Preview Table
with row1_col2:
    if uploaded_file is not None:
        try: 
            # Simple logic to handle both CSV and Excel
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
                
            st.write("Data Preview (First 5 rows):")
            st.table(df.head(), use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.info("Upload a file to see the preview here.")

# Row 2 (Optional placeholders)
with row2_col1:
    st.empty() # Keeps the layout consistent

with row2_col2:
    st.empty()
