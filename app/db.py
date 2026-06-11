import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()


@st.cache_resource
def get_engine():
    return create_engine(
        f"postgresql+psycopg2://"
        f"{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
        f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}"
        f"/{os.getenv('POSTGRES_DB')}"
    )


def _read(sql: str, params: dict | None = None) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


@st.cache_data(ttl=600)
def get_shortage_report() -> pd.DataFrame:
    return _read(
        "SELECT * FROM analytics.mart_shortage_report"
        " ORDER BY red_days_in_tt DESC, red_days DESC"
    )


@st.cache_data(ttl=600)
def get_inventory_simulation(marc_id: str) -> pd.DataFrame:
    return _read(
        "SELECT * FROM analytics.mart_inventory_simulation"
        " WHERE marc_id = :mid ORDER BY calendar_date",
        params={"mid": marc_id},
    )


@st.cache_data(ttl=600)
def get_vendor_performance() -> pd.DataFrame:
    return _read("SELECT * FROM analytics.mart_vendor_performance ORDER BY otd_rate ASC NULLS LAST")


@st.cache_data(ttl=600)
def get_consumption_trend() -> pd.DataFrame:
    return _read(
        "SELECT requirement_date, plant, SUM(daily_consumption) AS total_consumption"
        " FROM analytics.mart_consumption"
        " GROUP BY requirement_date, plant"
        " ORDER BY requirement_date"
    )


@st.cache_data(ttl=600)
def get_top_demand_materials(limit: int = 10) -> pd.DataFrame:
    return _read(
        "SELECT marc_id, MAX(material_number) AS material_number, MAX(plant) AS plant,"
        "       SUM(daily_consumption) AS total_demand"
        " FROM analytics.mart_consumption"
        " GROUP BY marc_id ORDER BY total_demand DESC LIMIT :lim",
        params={"lim": limit},
    )


@st.cache_data(ttl=600)
def get_backlog_by_plant() -> pd.DataFrame:
    return _read(
        "SELECT plant, SUM(overdue_backlog_qty) AS overdue_backlog_qty,"
        "       COUNT(*) FILTER (WHERE overdue_backlog_qty > 0) AS materials_with_backlog"
        " FROM analytics.mart_shortage_report"
        " GROUP BY plant ORDER BY plant"
    )
