from enum import Enum
import streamlit as st
import pandas as pd
from io import StringIO
from matplotlib import pyplot as plt
from plotly.graph_objects import Figure
from visualization.series_kde_visualizer import SeriesKDEVisualizer
from visualization.series_visualizer import SeriesVisualizer
from change_point.change_point_estimator import ChangePointEstimator
from visualization.series_visualizer import SegmentedSeriesVisualizer




def init_global()->None:
    
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 1

    st.session_state.start_analysis_btn_disabled = True 

    return


def manage_global_state():
    current_state = st.session_state.current_step

    if current_state == 1:
        step_1()
    elif current_state == 2:
        step_2()
    else:
        step_3()
    
    return



def click_start_analysis_button():
    st.session_state.current_step = 2

    return

def click_run_change_point_analysis_button():
     st.session_state.current_step = 3

     return




def step_1()->None:


    with st.container():
        st.title("Step1: Upload Time Series Data")

        st.session_state.start_analysis_btn_disabled = True 
        uploaded_file = st.file_uploader("Choose a file")
        if uploaded_file is not None:

            # Can be used wherever a "file-like" object is accepted:
            try:
                df = pd.read_csv(uploaded_file)
                df.columns=["date", "signal"]
                df["date"] = pd.to_datetime(df["date"])
                df["signal"] = pd.to_numeric(df["signal"], errors='coerce')
                st.subheader("Sample of data")
                st.write(df)
                st.session_state.df = df
                st.session_state.start_analysis_btn_disabled = False 
            except Exception as e:
                st.write("Please upload a valid CSV file.")
                #st.error(f"Error reading the file: {e}")


        st.button('Start Analysis', on_click=click_start_analysis_button, \
            disabled=st.session_state.get('start_analysis_btn_disabled',False))
    return


def step_2()->None:



    with st.container():
        st.title("Step 2: Visualize Density and Series - check for multiple modes")

        df = st.session_state.get('df', None)

        st.subheader("Kernel Density Estimate (KDE) Plot")
        fig : plt.Figure = get_kde_plot(df)
        st.pyplot(fig)
    
        #st.divider
        # 3. Place the second plot in the second column using 'with' notation
        
        st.subheader("Series Plot")
        fig2 : Figure = get_series_plot(df)
        st.plotly_chart(fig2)

        st.button('Run Change Points', on_click=click_run_change_point_analysis_button, \
            disabled=False)



def get_kde_plot(df: pd.DataFrame) -> plt.Figure:
    if df is None:
        st.warning("No data available to visualize. Please upload a file first.")
        return
    series = pd.Series(df.loc[:, "signal"])  # Assuming the signal is in a column named "signal"
    series.index  = df.loc[:, "date"]  # Assuming the date is in a column named "date"
    kde_visualizer = SeriesKDEVisualizer(series)
    plt_fig = kde_visualizer.KDEVisualizer()

    return plt_fig 

def get_series_plot(df: pd.DataFrame) -> plt.Figure:
    if df is None:
        st.warning("No data available to visualize. Please upload a file first.")
        return
    series = pd.Series(df.loc[:, "signal"])  # Assuming the signal is in a column named "signal"
    series.index  = df.loc[:, "date"]  # Assuming the date is in a column named "date"
    series_visualizer = SeriesVisualizer(series)
    plt_fig = series_visualizer.getVisualization()

    return plt_fig


def step_3() -> None:
    df = st.session_state.get('df', None)
    if df is None:
        st.warning("No data available to visualize. Please upload a file first.")
        return
    
    with st.container():
    
        series = pd.Series(df.loc[:, "signal"])  # Assuming the signal is in a column named "signal"
        series.index  = df.loc[:, "date"]  # Assuming the date is in a column named "date"
        cpe = ChangePointEstimator(series)
        cpe.estimate_change_points()
        st.title("Step 3: Segment Series by Change Point Analysis")
        ssv = SegmentedSeriesVisualizer(cpe._df)
        fig = ssv.getVisualization()
        st.plotly_chart(fig, use_container_width=True)
        #st.write(cpe._df)
        output_csv = cpe._df.to_csv(index=False).encode('utf-8')
        st.download_button('Save Segmented Series', output_csv, file_name="segmented_series.csv", mime='text/csv')

    return

init_global()
manage_global_state()




