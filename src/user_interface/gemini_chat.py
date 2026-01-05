import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()   

# Configure the Google API key (using secrets management is recommended)
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("Google Generative AI Chatbot")

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
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(user_input)
    ai_response = response.text

    # Add AI message to session state and display
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    with st.chat_message("assistant"):
        st.markdown(ai_response)
