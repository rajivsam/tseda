
import streamlit as st
from enum import Enum

import kmds
from kmds.ontology.kmds_ontology import *
from kmds.tagging.tag_types import ExploratoryTags
from owlready2 import *
from kmds.utils.path_utils import get_package_kb_path
from kmds.ontology.intent_types import IntentType
from pathlib import Path
import os

class KMDS_Capture_Mode(Enum):
    GET_CAPTURE_MODE = 1
    DO_CREATE_NEW_KB = 2
    DO_UPDATE_KB = 3


def click_load_KMDS_file_btn() -> None:


    return


def handle_capture_mode_decision(decision: str) -> None:
    if decision == "Create a new Knowledge Base":
        st.session_state.current_step = KMDS_Capture_Mode.DO_CREATE_NEW_KB.value
    else:
        st.session_state.current_step = KMDS_Capture_Mode.DO_UPDATE_KB.value
    

    return

def click_update_existing_kb_btn() -> None:
    st.session_state.current_step = KMDS_Capture_Mode.DO_UPDATE_KB.value

    return

def click_create_new_kb_btn(observations: str, file_name: str, file_dir: str) -> None:

    st.session_state.current_step = KMDS_Capture_Mode.DO_CREATE_NEW_KB.value

    exp_obs_list = []
    observation_count :int = 1
    e1 = ExploratoryObservation(namespace=onto)

    e1.finding = observations
    e1.finding_sequence = observation_count
    e1.exploratory_observation_type = ExploratoryTags.DATA_QUALITY_OBSERVATION.value
    e1.intent = IntentType.DATA_UNDERSTANDING.value
    exp_obs_list.append(e1)



    kaw = KnowledgeExtractionExperimentationWorkflow("coffee_prices_modeling", namespace=onto)
    kaw.has_exploratory_observations = exp_obs_list

    full_file_path = os.path.join(file_dir, file_name)

    KNOWLEDGE_BASE = full_file_path
    onto.save(file=KNOWLEDGE_BASE, format="rdfxml")

    return

def click_go_to_new_kb_btn() -> None:
    st.session_state.current_step = KMDS_Capture_Mode.DO_CREATE_NEW_KB.value

    return






def init_kmds_capture()->None:

    if "current_step" not in st.session_state:
        st.session_state.current_step = KMDS_Capture_Mode.GET_CAPTURE_MODE.value
    
    return

def manage_kmds_capture_state():
    current_state = st.session_state.current_step

    if current_state == KMDS_Capture_Mode.GET_CAPTURE_MODE.value:
        do_capture_mode()
    elif current_state == KMDS_Capture_Mode.DO_CREATE_NEW_KB.value:
        do_create_new_kb()
    else:
        do_update_existing_kb()
    
    return

def do_capture_mode()->None:


    st.title("Select your knowledge capture mode")

    # Create a form using the 'with' notation
    with st.container():

        
        # Page elements

        page_selection = st.radio(
        "What do you want to do?",
        ("Update an Existing Knowledge Base", "Create a new Knowledge Base"))
        
    
        st.button("Ok", on_click=handle_capture_mode_decision, args=(page_selection,))
    

            
        
    return

@st.dialog("Error", width="small")
def error_dialog(error_message):
    st.error(error_message, icon="🚨")
    st.write("Incorrect path, please correct the issue and try again.")
    
    if st.button("OK"):
        st.rerun() # Closes the dialog and reruns the main app script

def validate_directory()->None:

    dir_entered = st.session_state["file_dir"]
    directory_path = Path(dir_entered)

    if not directory_path.exists():
        error_dialog("The directory path is incorrect!")

    return



def do_create_new_kb()->None:


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

def do_update_existing_kb()->None:
    print("do_update_existing_kb")

    with st.container():
        st.title("Upload existing KMDS file")

        st.session_state.start_analysis_btn_disabled = True 
        uploaded_file = st.file_uploader("Choose a KMDS file")
        upload_done = uploaded_file is not None
        if uploaded_file is not None:

            # Can be used wherever a "file-like" object is accepted:
            try:
                pass

            except Exception as e:
                st.write("Please upload a valid CSV file.")
                #st.error(f"Error reading the file: {e}")
        
        col1, col2 = st.columns(2)

        with col1:
            st.button("Update Knowledge Base", on_click=click_update_existing_kb_btn, disabled=not upload_done, key="update_kb_btn")
        with col2:
            st.button("Create New KMDS Knowledge Base", on_click= click_go_to_new_kb_btn)
     


    return






init_kmds_capture()
manage_kmds_capture_state()



