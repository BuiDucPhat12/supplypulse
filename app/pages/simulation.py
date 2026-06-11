import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from db import get_shortage_report, get_inventory_simulation

st.title("Inventory Simulation")

# ── Material selector ──────────────────────────────────────────────────────
report = get_shortage_report()
report["label"] = (
    report["material_number"] + " | " + report["plant"] + " | " + report["status"]
)
options = report[["marc_id", "label"]].set_index("marc_id")["label"].to_dict()

selected_marc_id = st.selectbox(
    "Select Material",
    options=list(options.keys()),
    format_func=lambda x: options[x],
)

if not selected_marc_id:
    st.stop()

# ── Load simulation data ───────────────────────────────────────────────────
df = get_inventory_simulation(selected_marc_id)

if df.empty:
    st.warning("No simulation data for this material.")
    st.stop()

df["calendar_date"] = df["calendar_date"].astype(str)

# ── Summary strip ──────────────────────────────────────────────────────────
row = report[report["marc_id"] == selected_marc_id].iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Available Stock", int(row["available_stock"]))
c2.metric("Safety Stock", int(row["safety_stock"]))
c3.metric("Max Transit Time", f"{int(row['max_tt'])} days")
c4.metric("Red Days", int(row["red_days"]), delta_color="inverse")

st.divider()

# ── Build chart ────────────────────────────────────────────────────────────
fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    row_heights=[0.65, 0.35],
    vertical_spacing=0.08,
    subplot_titles=("Simulated Inventory", "Daily Consumption vs ASN"),
)

# Row 1 — inventory line
fig.add_trace(
    go.Scatter(
        x=df["calendar_date"],
        y=df["simulated_inventory_qty"],
        mode="lines",
        name="Inventory",
        line=dict(color="#1f77b4", width=2),
        fill="tozeroy",
        fillcolor="rgba(31,119,180,0.1)",
    ),
    row=1, col=1,
)

# Red zone — inventory below 0
red_df = df[df["simulated_inventory_qty"] < 0]
if not red_df.empty:
    fig.add_trace(
        go.Scatter(
            x=red_df["calendar_date"],
            y=red_df["simulated_inventory_qty"],
            mode="lines",
            name="Shortage Zone",
            line=dict(color="#d62728", width=2),
            fill="tozeroy",
            fillcolor="rgba(214,39,40,0.2)",
        ),
        row=1, col=1,
    )

# Zero reference line
fig.add_hline(y=0, line_dash="dash", line_color="red", row=1, col=1)

# Row 2 — daily bars
fig.add_trace(
    go.Bar(
        x=df["calendar_date"],
        y=df["daily_consumption"],
        name="Consumption",
        marker_color="#ff7f0e",
        opacity=0.7,
    ),
    row=2, col=1,
)
fig.add_trace(
    go.Bar(
        x=df["calendar_date"],
        y=df["daily_asn_qty"],
        name="ASN Arrival",
        marker_color="#2ca02c",
        opacity=0.7,
    ),
    row=2, col=1,
)

fig.update_layout(
    height=620,
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    barmode="group",
)
fig.update_yaxes(title_text="Qty", row=1, col=1)
fig.update_yaxes(title_text="Qty / Day", row=2, col=1)

st.plotly_chart(fig, use_container_width=True)
