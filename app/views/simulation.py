import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import ui
from db import get_inventory_simulation, get_shortage_report
from plotly.subplots import make_subplots

ui.setup()
ui.page_header(
    "📈 Inventory Simulation",
    "Tồn kho mô phỏng 120 ngày: stock − backlog − consumption lũy kế + ASN lũy kế",
)

# ── Material selector (pre-select từ Overview nếu có) ──────────────────────
report = get_shortage_report()
report["label"] = report["material_number"] + " | " + report["plant"] + " | " + report["status"]
options = report.set_index("marc_id")["label"].to_dict()
keys = list(options.keys())

preselected = st.session_state.get("selected_marc_id")
index = keys.index(preselected) if preselected in keys else 0

selected_marc_id = st.selectbox(
    "Select material",
    options=keys,
    index=index,
    format_func=lambda x: options[x],
)

df = get_inventory_simulation(selected_marc_id)
if df.empty:
    st.warning("No simulation data for this material.")
    st.stop()

df["calendar_date"] = pd.to_datetime(df["calendar_date"])
row = report[report["marc_id"] == selected_marc_id].iloc[0]
end_of_tt = pd.to_datetime(row["end_of_tt_gr"])

# ── Summary strip ──────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Available Stock", f"{int(row['available_stock']):,}")
c2.metric("Safety Stock", f"{int(row['safety_stock']):,}")
c3.metric("Overdue Backlog", f"{int(row['overdue_backlog_qty']):,}")
c4.metric("Max Transit Time", f"{int(row['max_tt'])} d")
c5.metric(
    "Status",
    row["status"],
    delta=f"{int(row['red_days_in_tt'])} red days in TT" if row["status"] == "Shortage" else None,
    delta_color="inverse",
)

st.divider()

# ── Chart ──────────────────────────────────────────────────────────────────
fig = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    row_heights=[0.65, 0.35],
    vertical_spacing=0.08,
    subplot_titles=("Simulated Inventory", "Daily Consumption vs ASN Arrival"),
)

# TT window — vùng không thể can thiệp (hàng đang trên đường)
fig.add_vrect(
    x0=df["calendar_date"].min(),
    x1=end_of_tt,
    fillcolor=ui.PALETTE["safety"],
    opacity=0.06,
    line_width=0,
    row=1,
    col=1,
)
fig.add_vline(
    x=end_of_tt,
    line_dash="dot",
    line_color=ui.PALETTE["safety"],
    opacity=0.7,
    annotation_text="end of TT",
    annotation_font_color=ui.PALETTE["safety"],
)

fig.add_trace(
    go.Scatter(
        x=df["calendar_date"],
        y=df["simulated_inventory_qty"],
        mode="lines",
        name="Inventory",
        line=dict(color=ui.PALETTE["inventory"], width=2),
        fill="tozeroy",
        fillcolor="rgba(56,189,248,0.08)",
    ),
    row=1,
    col=1,
)

red_df = df[df["simulated_inventory_qty"] < 0]
if not red_df.empty:
    fig.add_trace(
        go.Scatter(
            x=red_df["calendar_date"],
            y=red_df["simulated_inventory_qty"],
            mode="lines",
            name="Shortage Zone",
            line=dict(color=ui.PALETTE["shortage"], width=2),
            fill="tozeroy",
            fillcolor="rgba(248,113,113,0.18)",
        ),
        row=1,
        col=1,
    )

# Safety stock reference — so sánh với mức an toàn, không chỉ với 0
fig.add_hline(
    y=float(row["safety_stock"]),
    line_dash="dash",
    line_color=ui.PALETTE["safety"],
    annotation_text="safety stock",
    annotation_font_color=ui.PALETTE["safety"],
    row=1,
    col=1,
)
fig.add_hline(y=0, line_dash="dash", line_color=ui.PALETTE["shortage"], row=1, col=1)

fig.add_trace(
    go.Bar(
        x=df["calendar_date"],
        y=df["daily_consumption"],
        name="Consumption",
        marker_color=ui.PALETTE["consumption"],
        opacity=0.75,
    ),
    row=2,
    col=1,
)
fig.add_trace(
    go.Bar(
        x=df["calendar_date"],
        y=df["daily_asn_qty"],
        name="ASN Arrival",
        marker_color=ui.PALETTE["asn"],
        opacity=0.75,
    ),
    row=2,
    col=1,
)

fig.update_layout(height=640, barmode="group")
fig.update_yaxes(title_text="Qty", row=1, col=1)
fig.update_yaxes(title_text="Qty / day", row=2, col=1)

st.plotly_chart(fig, width="stretch")
