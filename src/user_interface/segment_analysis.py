import streamlit as st
import pandas as pd
from decomposition.ssa_decomposition import SSADecomposition
from typing import List
from matplotlib import pyplot as plt
import re
from visualization.series_visualizer import SeriesVisualizer


def init_segment()->None:
    """initialize the segment module
    """
    
    if 'seg_current_step' not in st.session_state:
        st.session_state.seg_current_step = 1

    st.session_state.seg_upload_btn_disabled = True 
    st.session_state.seg_visualization_btn_disabled = True 

    return

def manage_segment_state():
    """_summary_: Manage state for the segment module
    """
    current_state = st.session_state.seg_current_step


    if current_state == 1:
        upload_segment_file()
    if current_state == 2:
        run_ssa()
    if current_state == 3:
        run_segment_visualization()
    
    return


def click_run_SSA_button() -> None:
    """_summary_: Button handler for run ssa button click
    """
    st.session_state.seg_current_step = 2

    return

def click_seg_visualization_button() -> None:
    """_summary_Button handler for the segment visualization button
    """
    st.session_state.seg_current_step = 3

    return



def click_decomp_plot_button() ->None:
    st.session_state.seg_current_step = 2

    return

def click_upload_segment_button() ->None:
    st.session_state.seg_current_step = 1
    re_init_analysis_state()
    return

def re_init_analysis_state() ->None:
    st.session_state.seg_run_SSA_btn_disabled = True 
    st.session_state.seg_upload_btn_disabled = True
    st.session_state.seg_visualization_btn_disabled = True
    st.session_state.df_seg = None



def upload_segment_file()->None:


    with st.container():
        st.title("Step1: Upload Segmented Time Series Data")

        uploaded_file = st.file_uploader("Choose a file")
        if uploaded_file is not None:

            # Can be used wherever a "file-like" object is accepted:
            try:
                df = pd.read_csv(uploaded_file)
                df.columns=["date", "signal", "segment"]
                df["date"] = pd.to_datetime(df["date"])
                df["signal"] = pd.to_numeric(df["signal"], errors='coerce')
                st.subheader("Sample of data")
                
                st.session_state.seg_run_SSA_btn_disabled = False 
                st.session_state.seg_visualization_btn_disabled = False 
                segments = df["segment"].unique()
                option = st.selectbox("Select a segment to analyze",segments, index=0)
                sel_option = df.segment == option
                df = df[sel_option]
                edited_df = st.data_editor(df)
                st.session_state.df_seg = df
            except Exception as e:
                st.write("Please upload a valid CSV file.")
                st.error(f"Error reading the file: {e}")
                

            # layout the analysis option buttons in a row
            col1, col2 = st.columns(2)
            st.session_state.start_analysis_btn_disabled = False 
            st.session_state.seg_visualization_btn_disabled = False 
            with col1:
                st.button('Run SSA', on_click=click_run_SSA_button, \
                    disabled=st.session_state.get('seg_run_SSA_btn_disabled',False))
            with col2:
                st.button('Series Visualization', on_click=click_seg_visualization_button, \
                    disabled=st.session_state.get('seg_visualization_btn_disabled',False))

    return


def parse_number_string(numbers_string: str) -> List[int]:
    numbers_list = []
    try:
        # A simple split and conversion works for clean inputs
        # numbers_list = [int(x.strip()) for x in numbers_string.split(',')]
        
        # A more robust method using regex to handle various separators (commas, spaces, etc.) and potential non-numeric characters
        numbers_list = [int(i) for i in re.split("[^0-9-]", numbers_string) if i]
        
    except ValueError:
        st.error("Invalid input. Please ensure all values are valid integers.")

    return numbers_list

@st.dialog("Enter the window size for SSA")
def input_window_size():
    window_size = st.number_input("window size for SSA",min_value=0, max_value=50, step=1, key="wsize")
    if st.button("Submit"):
        st.session_state.ssa_window_size = st.session_state.wsize
        st.rerun()

def run_ssa() ->None:
    
    with st.container():
        st.title("Decompose Time Series Segment into Components")

        df = st.session_state.get('df_seg', None)

        st.subheader("SSA Decomposition")
        
        if "ssa_window_size" not in st.session_state:
            input_window_size()

        if st.session_state.get('ssa_window_size', False) > 0 :
            ws = st.session_state["wsize"]
            ssa = SSADecomposition(df,ws)
            st.subheader("Eigen decomposition, vector view")
            eig_decomp: plt.Figure  = ssa._ssa.plot(kind='vectors')[0]
            st.pyplot(eig_decomp)
            # The zero index on the RHS is take care of the fact that a tuple is returned and the first value is what is needed
            st.subheader("Eigen decomposition, size view")
            eig_plt: plt.Figure= ssa._ssa.plot(n_components=ssa._ssa._window -1, marker='o')[0] 
            st.pyplot(eig_plt)
            comp1 = st.text_input("Enter numbers separated by commas (e.g., 1, 2, 3)", key="comp1")
            comp2 = st.text_input("Enter numbers separated by commas (e.g., 1, 2, 3)", key="comp2")
            c1 = parse_number_string(comp1)
            c2 = parse_number_string(comp2)
            st.button('Plot Decomposition', on_click=click_decomp_plot_button)
            if len(c1) > 0 and len(c2) > 0:
                st.subheader("Component Decomposition")
                decomp_plt : plt.Figure = ssa.decomposition_plot(c1, c2)
                st.pyplot(decomp_plt)
            
            # layout the analysis option buttons in a row
            col1, col2 = st.columns(2)
            st.session_state.seg_upload_btn_disabled = False 
            st.session_state.seg_visualization_btn_disabled = False 
            with col1:
                st.button('Upload Segement', on_click=click_upload_segment_button, \
                    disabled=st.session_state.get('seg_upload_btn_disabled',False))
            with col2:
                st.button('Series Visualization', on_click=click_seg_visualization_button, \
                    disabled=st.session_state.get('seg_visualization_btn_disabled',False))     

        return

def run_segment_visualization() -> None:

    with st.container():
        st.title("Visualize Time Series Segment")

        df = st.session_state.get('df_seg', None)

        st.subheader("Series Plot")
        series = pd.Series(df.loc[:, "signal"])  # Assuming the signal is in a column named "signal"
        series.index  = df.loc[:, "date"]  # Assuming the date is in a column named "date"
        series_visualizer = SeriesVisualizer(series)
        series_fig = series_visualizer.getVisualization()
        st.plotly_chart(series_fig)
        st.subheader("Smoothed Plot")
        lowess_fig = series_visualizer.LowessVisualizer()
        st.plotly_chart(lowess_fig)
                # layout the analysis option buttons in a row
        col1, col2 = st.columns(2)
        st.session_state.seg_upload_btn_disabled = False 
        st.session_state.seg_visualization_btn_disabled = False 
        with col1:
            st.button('Run SSA', on_click=click_run_SSA_button, \
                disabled=st.session_state.get('start_analysis_btn_disabled',False))
        with col2:
            st.button('Upload Segement', on_click=click_upload_segment_button, \
                    disabled=st.session_state.get('seg_upload_btn_disabled',False))
 

    return
    

init_segment()
manage_segment_state()

