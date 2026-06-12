import streamlit as st

st.set_page_config(
    page_title="SupplyPulse Cockpit",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

nav = st.navigation(
    [
        st.Page("views/overview.py", title="Shortage Overview", icon="🚨", default=True),
        st.Page("views/simulation.py", title="Inventory Simulation", icon="📈"),
        st.Page("views/vendors.py", title="Vendor Performance", icon="🚚"),
        st.Page("views/demand.py", title="Demand & Backlog", icon="📊"),
    ]
)

with st.sidebar:
    st.markdown("### 📦 SupplyPulse")
    st.caption("Supply chain cockpit — SAP ECC → dbt → Postgres")

nav.run()
