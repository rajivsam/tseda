
import streamlit as st
from enum import Enum

class KMDS_Capture_Mode(Enum):
    GET_CAPTURE_MODE = 1
    DO_CREATE_NEW_KB = 2
    DO_UPDATE_KB = 3



def init_kmds_capture()->None:
    
    st.session_state.current_step = KMDS_Capture_Mode.GET_CAPTURE_MODE 

    return

def manage_kmds_capture_state():
    current_state = st.session_state.current_step

    if current_state == KMDS_Capture_Mode.GET_CAPTURE_MODE:
        do_capture_mode()
    elif current_state == KMDS_Capture_Mode.DO_CREATE_NEW_KB:
        do_create_new_kb()
    else:
        do_update_existing_kb()
    
    return

def do_capture_mode()->None:

    st.title("Select your knowledge capture mode")

    # Create a form using the 'with' notation
    with st.form("knowledge_capture_question_form"):

        
        # Form elements

        page_selection = st.radio(
        "What do you want to do?",
        ("Update an Existing Knowledge Base", "Create a new Knowledge Base"))
        
        # Every form must have a submit button
        submitted = st.form_submit_button("Submit")

    # This code block executes only after the form is submitted
    if submitted:
        if page_selection == "Update an Existing Knowledge Base":
            st.session_state.current_step = KMDS_Capture_Mode.DO_UPDATE_KB
        else:
            st.session_state.current_step = KMDS_Capture_Mode.DO_CREATE_NEW_KB
        manage_kmds_capture_state()
            
        
    return

def do_create_new_kb()->None:
    print("do_create_new_kb")

    return

def do_update_existing_kb()->None:
    print("do_update_existing_kb")


    return


init_kmds_capture()
manage_kmds_capture_state()



