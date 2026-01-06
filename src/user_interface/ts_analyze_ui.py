import streamlit as st
from analysis_modes import AnalysisMode


def main():

    pages = {
        "Analysis": [
            st.Page("global_analysis.py", title="Global Analysis", default=True),
            st.Page("segment_analysis.py", title="Segment Analysis"),
           
        ],
        "Knowledge Base": [ st.Page("gemini_chat.py", title="Chatbot"),
        st.Page("kmds_capture.py", title="KMDS Capture")]
    
    }


    pg = st.navigation(pages)
    pg.run()

    return








if __name__ == "__main__":
    main()

