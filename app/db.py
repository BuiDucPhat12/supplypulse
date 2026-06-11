import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

engine = create_engine(
    f"postgresql+psycopg2://"
    f"{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}"
    f"/{os.getenv('POSTGRES_DB')}"
)


@st.cache_data
def get_shortage_report() -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(
            text("SELECT * FROM analytics.mart_shortage_report ORDER BY red_days DESC"),
            conn,
        )


@st.cache_data
def get_inventory_simulation(marc_id: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(
            text(
                "SELECT * FROM analytics.mart_inventory_simulation"
                " WHERE marc_id = :mid ORDER BY calendar_date"
            ),
            conn,
            params={"mid": marc_id},
        )
