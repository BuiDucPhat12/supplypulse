import streamlit as st

st.set_page_config(
    page_title="SupplyPulse",
    page_icon="📦",
    layout="wide",
)

pg = st.navigation([
    st.Page("pages/overview.py", title="Shortage Overview", icon="🔴"),
    st.Page("pages/simulation.py", title="Inventory Simulation", icon="📈"),
])
pg.run()
