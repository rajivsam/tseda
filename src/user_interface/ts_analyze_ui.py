import streamlit as st
from analysis_modes import AnalysisMode


def main():

    pages = {
        "Analysis": [
            st.Page("global_analysis.py", title="Global Analysis", default=True),
            st.Page("segment_analysis.py", title="Segment Analysis")
        ],
    
    }


    pg = st.navigation(pages)
    pg.run()

    return








if __name__ == "__main__":
    main()

