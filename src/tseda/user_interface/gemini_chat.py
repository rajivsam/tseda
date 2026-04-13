"""Streamlit chat interface backed by the Google Gemini generative model."""

import streamlit as st
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

load_dotenv()   



# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("Research your analysis questions with Gemini Chatbot")

# Display past messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle user input
if user_input := st.chat_input("How can I help you today?"):
    # Add user message to session state and display
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Get AI response using the Gemini model
    API_KEY = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=API_KEY)

    response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=user_input,)

    #response = model.generate_content(user_input)
    ai_response = response.text

    # Add AI message to session state and display
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    with st.chat_message("assistant"):
        st.markdown(ai_response)
    
    client.close()
