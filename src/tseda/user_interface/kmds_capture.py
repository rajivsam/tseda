"""Streamlit knowledge-management capture UI for KMDS ontology workflows."""

import streamlit as st
from enum import Enum

import kmds
from kmds.ontology.kmds_ontology import *
from kmds.tagging.tag_types import ExploratoryTags
from owlready2 import *
from kmds.ontology.intent_types import IntentType
from pathlib import Path
import os
from tseda.dataloader.kmds_data_loader import KMDSDataLoader
from tseda.data_writers.kmds_writer import KMDSDataWriter

from dataclasses import dataclass
from kmds.utils.load_utils import *
import pandas as pd
from google import genai
from dotenv import load_dotenv

load_dotenv()


@dataclass
class TemplateData:
    start_of_series: str
    end_of_series: str
    num_samples: str
    num_change_points: str
    change_point_model: str
    segment_summary: str



class KMDS_Capture_Mode(Enum):
    GET_CAPTURE_MODE = 1
    DO_CREATE_NEW_KB = 2
    DO_UPDATE_KB = 3
    DO_EXPORT_KB = 4


def handle_capture_mode_decision(decision: str) -> None:
    """Update the session state step based on the user's mode selection.

    Args:
        decision: One of ``"Create a new Knowledge Base"``, ``"Export Knowledge Base"``,
            or any other string (treated as *Update Existing*).
    """
    if decision == "Create a new Knowledge Base":
        st.session_state.current_kmds_step = KMDS_Capture_Mode.DO_CREATE_NEW_KB.value
    elif decision == "Export Knowledge Base":
        st.session_state.current_kmds_step = KMDS_Capture_Mode.DO_EXPORT_KB.value
    else:
        st.session_state.current_kmds_step = KMDS_Capture_Mode.DO_UPDATE_KB.value
    

    return

def click_update_existing_kb_btn() -> None:
    """Transition the session state to the *Update Knowledge Base* step."""
    st.session_state.current_kmds_step = KMDS_Capture_Mode.DO_UPDATE_KB.value

    return

def click_create_new_kb_btn(observations: str, file_name: str, file_dir: str) -> None:
    """Create a new KMDS knowledge base with an initial exploratory observation.

    Args:
        observations: Plain-text observation to store in the new KB.
        file_name: Desired KB file name (without directory).
        file_dir: Target directory for the new KB file.
    """

    st.session_state.current_kmds_step = KMDS_Capture_Mode.DO_CREATE_NEW_KB.value

    exp_obs_list = []
    observation_count :int = 1
    e1 = ExploratoryObservation(namespace=onto)

    e1.finding = observations
    e1.finding_sequence = observation_count
    e1.exploratory_observation_type = ExploratoryTags.DATA_QUALITY_OBSERVATION.value
    e1.intent = IntentType.DATA_UNDERSTANDING.value
    exp_obs_list.append(e1)
    full_file_path = os.path.join(file_dir, file_name)


    kaw = KnowledgeExtractionExperimentationWorkflow(full_file_path, namespace=onto)
    kaw.has_exploratory_observations = exp_obs_list
    onto.save(file=full_file_path, format="rdfxml")


    return

def init_kmds_capture() -> None:
    """Initialize KMDS session-state keys if they have not been set yet."""

    if "current_kmds_step" not in st.session_state:
        st.session_state.current_kmds_step = KMDS_Capture_Mode.GET_CAPTURE_MODE.value
    if "use_template" not in st.session_state:
        st.session_state.use_template = False
    
    return

def manage_kmds_capture_state() -> None:
    """Dispatch to the correct Streamlit page based on the current capture step."""
    current_state = st.session_state.current_kmds_step

    if current_state == KMDS_Capture_Mode.GET_CAPTURE_MODE.value:
        do_capture_mode()
    elif current_state == KMDS_Capture_Mode.DO_CREATE_NEW_KB.value:
        do_create_new_kb()
    elif current_state == KMDS_Capture_Mode.DO_EXPORT_KB.value:
        export_KB()
    else:
        do_update_existing_kb()
    
    return

def click_export_kb_btn(file_name: str, file_dir: str, dest_dir: str, dest_file_name: str) -> None:
    """Export the KMDS knowledge base to a CSV file.

    Args:
        file_name: Source KB file name.
        file_dir: Directory containing the source KB file.
        dest_dir: Directory where the exported CSV will be written.
        dest_file_name: File name for the exported CSV.
    """

    full_file_path = os.path.join(file_dir, file_name)
    dest_full_file_path = os.path.join(dest_dir, dest_file_name)

    if not Path(full_file_path).exists():
        error_dialog("The KMDS file path is incorrect, please verify!")
    
    df = create_export_dataframe(full_file_path)
    df.to_csv(dest_full_file_path, index=False)

    return

def export_KB() -> None:
    """Render the Streamlit export-KB page and handle the export button click."""

    with st.container():
        st.title("Export KMDS Knowledge Base")

        file_name = st.text_input("KB File Name")
        file_dir = st.text_input("KB File directory", on_change=validate_directory, key="file_dir")

        dest_dir = st.text_input("Destination Directory", on_change=validate_directory, key="dest_dir")
        dest_file_name = st.text_input("Destination File Name")
        data_entered = len(file_name) > 0 and len(file_dir) > 0 and len(dest_dir) >0 and len(dest_file_name) >0
        st.button("Export Knowledge Base", on_click=click_export_kb_btn,\
            args=(file_name, file_dir, dest_dir, dest_file_name), disabled= not data_entered)
    return



def do_capture_mode() -> None:
    """Render the mode-selection page and route to the chosen sub-workflow."""

    st.title("Select your knowledge capture mode")

    # Create a form using the 'with' notation
    with st.container():

        
        # Page elements

        page_selection = st.radio(
        "What do you want to do?",
        ("Update an Existing Knowledge Base", "Create a new Knowledge Base", "Export Knowledge Base"))
        
        

        st.button("Ok", on_click=handle_capture_mode_decision, args=(page_selection,))
    
    

            
        
    return

@st.dialog("Error", width="small")
def error_dialog(error_message):
    st.error(error_message, icon="🚨")
    st.write("Incorrect path, please correct the issue and try again.")
    
    if st.button("OK"):
        st.rerun() # Closes the dialog and reruns the main app script

def validate_directory() -> None:
    """Validate the directory path stored in ``st.session_state["file_dir"]``."""

    dir_entered = st.session_state["file_dir"]
    directory_path = Path(dir_entered)

    if not directory_path.exists():
        error_dialog("The directory path is incorrect!")

    return



def do_create_new_kb() -> None:
    """Render the new-KB creation form and handle button click events."""

    with st.container():

        user_input = st.text_area("Input text here", height=150) # The label is "Input text here"
        file_name = st.text_input("File Name")
        file_dir = st.text_input("File directory", on_change=validate_directory, key="file_dir")

        data_entered = len(user_input) > 0 and len(file_name) > 0



        # Create multiple buttons with callbacks
        col1, col2 = st.columns(2)

        with col1:
            st.button("Update Existing Knowledge Base", on_click=click_update_existing_kb_btn)
        with col2:
            st.button("Create New KMDS Knowledge Base", on_click= click_create_new_kb_btn, args=(user_input, file_name, file_dir), disabled= not data_entered)


    
    return

def click_load_KnowledgeBase_btn(file_name: str, file_dir: str) -> None:
    full_file_path = os.path.join(file_dir, file_name)

    if not Path(full_file_path).exists():
        error_dialog("The KMDS file path is incorrect, please verify!")
    
    kmds_data_loader = KMDSDataLoader(full_file_path)
    exp_df = kmds_data_loader.load_exploratory_obs()

    st.session_state.exp_df = exp_df
    st.session_state.kb_file_path = full_file_path


    return


def click_add_to_kb_btn(obs: str) -> None:
    file_path = st.session_state.get("kb_file_path", None)
    kmds_writer = KMDSDataWriter(file_path)
    kmds_writer.add_exploratory_obs(obs, file_path)
    kmds_data_loader = KMDSDataLoader(file_path)
    exp_df = kmds_data_loader.load_exploratory_obs()

    st.session_state.exp_df = exp_df
    

    return
    

def enable_add_to_kb_btn() -> None:
    st.session_state.no_addl_facts_added = False


    return

def click_delete_from_kb_btn(obs: str) -> None:


    file_path = st.session_state.get("kb_file_path", None)
    kmds_writer = KMDSDataWriter(file_path)
    kmds_writer.delete_exploratory_obs(obs)
    kmds_data_loader = KMDSDataLoader(file_path)
    exp_df = kmds_data_loader.load_exploratory_obs()
    st.session_state.exp_df = exp_df
  

    return

def click_update_KB_entry_btn(obs: str, obs_seq: int) -> None:


    file_path = st.session_state.get("kb_file_path", None)
    kmds_writer = KMDSDataWriter(file_path)
    kmds_writer.update_exploratory_obs(obs, obs_seq)
    kmds_data_loader = KMDSDataLoader(file_path)
    exp_df = kmds_data_loader.load_exploratory_obs()
    st.session_state.exp_df = exp_df

    return

def create_export_dataframe(kmds_kb_path: str) -> pd.DataFrame:
    
    kmds_data_loader = KMDSDataLoader(kmds_kb_path)

    obs_df  = kmds_data_loader.export_all_observations()


    return obs_df





def do_update_existing_kb()->None:


    with st.container():
        st.title("Enter the location of your KMDS Knowledge Base")

        file_name = st.text_input("File Name")
        file_dir = st.text_input("File directory", on_change=validate_directory, key="file_dir")

        data_entered = len(file_dir) > 0 and len(file_name) > 0

        st.session_state.noselection = True

        st.subheader("Input your next finding below")
        user_input = st.text_area("Input text here", height=150, on_change=enable_add_to_kb_btn) # The label is "Input text here"
        st.session_state.no_addl_facts_added = len(user_input) > 0





        if "exp_df" in st.session_state:
            exp_df = st.session_state["exp_df"]
            styles = [dict(selector="td", props=[('white-space', 'pre-wrap'),\
                 ('word-wrap', 'break-word'), ('max-width', '480px')])]
            exp_df.style.set_table_styles(styles)

            selection_event = st.dataframe(exp_df, on_select="rerun", selection_mode="single-row", row_height=80)

                            # Check if any row is selected
            if selection_event.selection and selection_event.selection["rows"]:
                # Get the index of the selected row (positional index)
                selected_index = selection_event.selection["rows"][0]
                
                # Retrieve the actual row data using .iloc
                selected_row_data = exp_df.iloc[selected_index]
                st.session_state.noselection = False

                col1, col2 = st.columns(2)

                with col1:
                    st.button("Update KB", on_click=click_update_KB_entry_btn, args=(user_input,selected_row_data['finding_seq']),\
                         disabled= st.session_state.get("noselection", False))
                with col2:
                    st.button("Delete from KB", on_click=click_delete_from_kb_btn,\
                    args=(selected_row_data['finding_seq'],), disabled= False)



    
        coll1, col2, col3 = st.columns(3)
        with coll1:
        # You only need to load the KB if a load has not happened previously, in which case exp_df is in the session
            st.button("Load Knowledge Base", on_click=click_load_KnowledgeBase_btn,\
                args=(file_name, file_dir),disabled=not data_entered,key="load_kb_btn")
        with col2:

            st.button("Add to KB", on_click=click_add_to_kb_btn,\
                args=(user_input,), disabled= not st.session_state.get("no_addl_facts_added", False))
        with col3:
            st.button("Use a Template", disabled=not "kb_file_path" in st.session_state, on_click=click_use_template_btn)
        
        if st.session_state.get("use_template", False):
            show_template_form()
        

            


    return


def click_use_template_btn():
    st.session_state.use_template = True

def click_cancel_template_btn():
    st.session_state.use_template = False



def show_template_form():
    with st.container():
        st.text_input("Start of Series", key="start_of_series")
        st.text_input("End of Series", key="end_of_series")
        st.text_input("Number of Samples", key="num_samples")
        st.text_input("Number of Change Points", key="num_change_points")
        st.text_input("Model Used for Change Point Detection", key="change_point_model")
        st.text_area("Segment Summary", help="Summarize the results of singular spectrum analysis", key="segment_summary")

        def handle_template_submission():
            template_data = TemplateData(
                start_of_series=st.session_state.start_of_series,
                end_of_series=st.session_state.end_of_series,
                num_samples=st.session_state.num_samples,
                num_change_points=st.session_state.num_change_points,
                change_point_model=st.session_state.change_point_model,
                segment_summary=st.session_state.segment_summary,
            )
            
            # The processing logic
            prompt = f"""
            Based on the following information, provide a concise summary for an exploratory observation:
            - Start of Series: {template_data.start_of_series}
            - End of Series: {template_data.end_of_series}
            - Number of Samples: {template_data.num_samples}
            - Number of Change Points: {template_data.num_change_points}
            - Change Point Model: {template_data.change_point_model}
            - Segment Summary: {template_data.segment_summary}
            """
            
            # Call Gemini
            API_KEY = os.getenv("GEMINI_API_KEY")
            client = genai.Client(api_key=API_KEY)

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            summary = response.text
            client.close()
            
            # Add to KB
            file_path = st.session_state.get("kb_file_path")
            if file_path:
                kmds_writer = KMDSDataWriter(file_path)
                kmds_writer.add_exploratory_obs(summary, file_path)
                
                # Reload data to show update
                kmds_data_loader = KMDSDataLoader(file_path)
                exp_df = kmds_data_loader.load_exploratory_obs()
                st.session_state.exp_df = exp_df

            st.session_state.use_template = False

        col1, col2 = st.columns(2)
        with col1:
            st.button("Submit", on_click=handle_template_submission)
        with col2:
            st.button("Cancel", on_click=click_cancel_template_btn)






init_kmds_capture()
manage_kmds_capture_state()



