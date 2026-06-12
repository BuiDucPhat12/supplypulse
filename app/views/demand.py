import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import ui
from db import get_backlog_by_plant, get_consumption_trend, get_top_demand_materials

ui.setup()
ui.page_header(
    "📊 Demand & Backlog",
    "120-day future demand (mart_consumption) + overdue backlog by plant",
)

trend = get_consumption_trend()
trend["requirement_date"] = pd.to_datetime(trend["requirement_date"])
backlog = get_backlog_by_plant()
top = get_top_demand_materials(10)

# ── KPI cards ──────────────────────────────────────────────────────────────
k1, k2, k3 = st.columns(3)
k1.metric("Total Future Demand", f"{int(trend['total_consumption'].sum()):,}")
k2.metric("Total Overdue Backlog", f"{int(backlog['overdue_backlog_qty'].sum()):,}")
k3.metric("Materials w/ Backlog", f"{int(backlog['materials_with_backlog'].sum()):,}")

st.divider()

# ── Consumption trend (stacked by plant, weekly) ───────────────────────────
st.subheader("Demand Trend (weekly, by plant)")
weekly = (
    trend.set_index("requirement_date")
    .groupby("plant")
    .resample("W")["total_consumption"]
    .sum()
    .reset_index()
)
plant_colors = ["#38bdf8", "#34d399", "#fbbf24", "#f472b6"]
fig = go.Figure()
for i, plant in enumerate(sorted(weekly["plant"].unique())):
    sub = weekly[weekly["plant"] == plant]
    fig.add_trace(
        go.Bar(
            x=sub["requirement_date"],
            y=sub["total_consumption"],
            name=f"Plant {plant}",
            marker_color=plant_colors[i % len(plant_colors)],
        )
    )
fig.update_layout(height=380, barmode="stack", yaxis_title="Qty / week")
st.plotly_chart(fig, width="stretch")

col_left, col_right = st.columns([1, 1])

# ── Backlog by plant ───────────────────────────────────────────────────────
with col_left:
    st.subheader("Overdue Backlog by Plant")
    fig2 = go.Figure(
        go.Bar(
            x="Plant " + backlog["plant"],
            y=backlog["overdue_backlog_qty"],
            marker_color=ui.PALETTE["shortage"],
            text=backlog["overdue_backlog_qty"].astype(int).map("{:,}".format),
            textposition="outside",
        )
    )
    fig2.update_layout(height=360, yaxis_title="Qty")
    st.plotly_chart(fig2, width="stretch")

# ── Top demand materials ───────────────────────────────────────────────────
with col_right:
    st.subheader("Top 10 Materials by Demand")
    st.dataframe(
        top[["material_number", "plant", "total_demand"]],
        width="stretch",
        height=360,
        hide_index=True,
        column_config={
            "material_number": st.column_config.TextColumn("Material"),
            "plant": st.column_config.TextColumn("Plant", width="small"),
            "total_demand": st.column_config.ProgressColumn(
                "Total Demand",
                min_value=0,
                max_value=float(top["total_demand"].max() or 1),
                format="%d",
            ),
        },
    )
