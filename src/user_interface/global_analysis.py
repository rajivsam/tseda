
import streamlit as st
import pandas as pd
from matplotlib import pyplot as plt
from plotly.graph_objects import Figure
from visualization.series_kde_visualizer import SeriesKDEVisualizer
from visualization.series_visualizer import SeriesVisualizer
from change_point.change_point_estimator import ChangePointEstimator
from visualization.series_visualizer import SegmentedSeriesVisualizer
from series_stats.sampling_prop import SamplingProp




def init_global()->None:
    
    if "current_global_step" not in st.session_state:
        st.session_state.current_global_step= 1
    st.session_state.start_analysis_btn_disabled = True 
    

    return

def re_init_analysis_state() ->None:


    keys = list(st.session_state.keys())
    for key in keys:
        del st.session_state[key]
    

    return



def manage_global_state():
    current_state = st.session_state.current_global_step

    if current_state == 1:
        step_1()
    elif current_state == 2:
        step_2()
    else:
        step_3()
    
    return



def click_start_analysis_button():

    st.session_state.current_global_step= 2


    return

def click_run_change_point_analysis_button():
     st.session_state.current_global_step= 3

     return

def click_upload_segment_button() ->None:
    re_init_analysis_state()
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
                series = df["signal"]
                series.index  = df["date"]
                sp = SamplingProp(series)
                df_prop = sp.view_properties()
                st.subheader("Sampling Properties")
                st.write(df_prop)


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

        return



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


@st.dialog("Enter the penalty or accept the default for the change point estimator")
def input_parameters():
   
    penalty = st.number_input("penalty for change point estimator",min_value=0.0, max_value=50.0, step=0.1, key="psize", value = 2.0)
    model_options = ['rbf', 'l2', 'l1']

    #Create the selectbox
    model_to_use = st.selectbox(
    'Choose a model to use',  # This is the label (text above the box)
    model_options,             # These are the options
    index=0,             # Optional: sets the default to 'Banana' (index 1),
    key="CP_model"
    )
    
    if st.button("Submit"):
        st.session_state.PELT_penalty = st.session_state.psize
        st.rerun()
    

def step_3() -> None:
    df = st.session_state.get('df', None)
    if df is None:
        st.warning("No data available to visualize. Please upload a file first.")
        return
    
    with st.container():
    
        series = pd.Series(df.loc[:, "signal"])  # Assuming the signal is in a column named "signal"
        series.index  = df.loc[:, "date"]  # Assuming the date is in a column named "date"
        
        CP_params_defined = "PELT_penalty" in st.session_state and "CP_model" in st.session_state
        
        if not CP_params_defined:
            input_parameters()
        
        if CP_params_defined:
            cpe = ChangePointEstimator(series)
            input_penalty = st.session_state["PELT_penalty"]
            input_model = st.session_state["CP_model"]
            cpe.estimate_change_points(model_to_use = input_model, penalty_coeff = input_penalty)
            st.title("Step 3: Segment Series by Change Point Analysis")
            ssv = SegmentedSeriesVisualizer(cpe._df)
            fig = ssv.getVisualization()
            st.plotly_chart(fig, use_container_width=True)
            #st.write(cpe._df)
            output_csv = cpe._df.to_csv(index=False).encode('utf-8')
            col1, col2 = st.columns(2)
            with col1:      
                st.download_button('Save Segmented Series', output_csv, file_name="segmented_series.csv", mime='text/csv')
            with col2:
                st.button('Upload Segement', on_click=click_upload_segment_button, \
                    disabled=False)


    return

init_global()
manage_global_state()




