import plotly.graph_objects as go
import streamlit as st
import ui
from db import get_vendor_performance

ui.setup()
ui.page_header(
    "🚚 Vendor Performance",
    "OTD đo trên deliveries đã GR hoàn tất; late shipments từ SA chưa được ASN cover",
)

df = get_vendor_performance()
rated = df[df["otd_rate"].notna()].copy()

# ── KPI cards ──────────────────────────────────────────────────────────────
worst = rated.iloc[0] if not rated.empty else None
k1, k2, k3, k4 = st.columns(4)
k1.metric("Vendors Tracked", f"{len(df):,}")
k2.metric("Avg OTD", f"{rated['otd_rate'].mean():.0%}" if not rated.empty else "—")
k3.metric(
    "Worst OTD",
    f"{worst['otd_rate']:.0%}" if worst is not None else "—",
    delta=worst["vendor_name"] if worst is not None else None,
    delta_color="off",
)
k4.metric("Late Qty Due (total)", f"{int(df['late_qty_due'].sum()):,}")

st.divider()

col_left, col_right = st.columns([1, 1])

# ── Bar: 10 vendors OTD tệ nhất ────────────────────────────────────────────
with col_left:
    st.subheader("Bottom 10 — On-Time Delivery")
    bottom = rated.head(10).iloc[::-1]  # reverse để bar tệ nhất nằm trên cùng
    colors = [
        ui.PALETTE["bad"] if v < 0.6 else ui.PALETTE["warn"] if v < 0.85 else ui.PALETTE["good"]
        for v in bottom["otd_rate"]
    ]
    fig = go.Figure(
        go.Bar(
            x=bottom["otd_rate"],
            y=bottom["vendor_name"] + " (" + bottom["country"] + ")",
            orientation="h",
            marker_color=colors,
            text=[f"{v:.0%}" for v in bottom["otd_rate"]],
            textposition="outside",
        )
    )
    fig.update_layout(height=420, xaxis=dict(range=[0, 1.05], tickformat=".0%"))
    st.plotly_chart(fig, width="stretch")

# ── Scatter: OTD vs transit time, bubble = late qty ────────────────────────
with col_right:
    st.subheader("OTD vs Transit Time")
    fig2 = go.Figure(
        go.Scatter(
            x=rated["avg_transit_time_days"],
            y=rated["otd_rate"],
            mode="markers",
            marker=dict(
                size=(rated["late_qty_due"].astype(float) + 1) ** 0.5 / 2 + 6,
                color=rated["otd_rate"],
                colorscale=[
                    [0, ui.PALETTE["bad"]],
                    [0.7, ui.PALETTE["warn"]],
                    [1, ui.PALETTE["good"]],
                ],
                cmin=0.3,
                cmax=1.0,
                line=dict(width=0),
            ),
            customdata=rated[["vendor_name", "country", "late_qty_due"]],
            hovertemplate=(
                "<b>%{customdata[0]}</b> (%{customdata[1]})<br>"
                "OTD: %{y:.0%}<br>Avg TT: %{x} d<br>"
                "Late qty due: %{customdata[2]:,}<extra></extra>"
            ),
        )
    )
    fig2.update_layout(
        height=420,
        xaxis_title="Avg transit time (days)",
        yaxis=dict(title="OTD rate", tickformat=".0%"),
        hovermode="closest",
    )
    st.plotly_chart(fig2, width="stretch")

# ── Full table ─────────────────────────────────────────────────────────────
st.subheader("All Vendors")
st.dataframe(
    df[
        [
            "vendor_number",
            "vendor_name",
            "country",
            "otd_rate",
            "completed_delivery_lines",
            "on_time_lines",
            "late_shipment_lines",
            "late_qty_due",
            "avg_transit_time_days",
        ]
    ],
    width="stretch",
    height=420,
    hide_index=True,
    column_config={
        "vendor_number": st.column_config.TextColumn("Vendor #"),
        "vendor_name": st.column_config.TextColumn("Name"),
        "country": st.column_config.TextColumn("Country", width="small"),
        "otd_rate": st.column_config.ProgressColumn(
            "OTD", min_value=0.0, max_value=1.0, format="percent"
        ),
        "completed_delivery_lines": st.column_config.NumberColumn("Completed", format="%d"),
        "on_time_lines": st.column_config.NumberColumn("On Time", format="%d"),
        "late_shipment_lines": st.column_config.NumberColumn("Late Lines", format="%d"),
        "late_qty_due": st.column_config.NumberColumn("Late Qty Due", format="%d"),
        "avg_transit_time_days": st.column_config.NumberColumn("Avg TT (d)", format="%.1f"),
    },
)
