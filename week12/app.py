# app.py — entry point: config + CSS applied ONCE for every page
# BBD principle: page titles are QUESTIONS, not topic labels
import streamlit as st

st.set_page_config(page_title="London Airbnb Analytics", page_icon="🏠",
                   layout="wide", initial_sidebar_state="expanded")

# Custom CSS — applied once here (app.py runs on every page switch)
st.markdown("""
<style>
.block-container { padding-top: 1.5rem; padding-bottom: 0; }
[data-testid='metric-container'] {
    background: #F8F9FA; border: 1px solid #E9ECEF;
    padding: 1rem; border-radius: 8px;
}
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

pg = st.navigation([
    st.Page("pages/01_market.py",
            title="Is London Airbnb expensive right now?",   icon="🏠"),
    st.Page("pages/02_drilldown.py",
            title="Which neighbourhoods drive the premium?", icon="📍"),
    st.Page("pages/03_demand.py",
            title="Where is guest demand strongest?",        icon="🔥"),
])
pg.run()

# Run with: streamlit run app.py
