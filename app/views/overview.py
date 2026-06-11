import streamlit as st
import ui
from db import get_shortage_report

ui.setup()
ui.page_header(
    "🚨 Shortage Overview",
    "Materials at risk trong transit-time window — nguồn: mart_shortage_report",
)

df = get_shortage_report()

# ── Filters ────────────────────────────────────────────────────────────────
f1, f2, f3, f4 = st.columns([1, 1, 1, 2])
plants = ["All"] + sorted(df["plant"].dropna().unique().tolist())
abc_classes = ["All"] + sorted(df["abc_class"].dropna().unique().tolist())

selected_plant = f1.selectbox("Plant", plants)
selected_abc = f2.selectbox("ABC class", abc_classes)
selected_status = f3.selectbox("Status", ["All", "Shortage", "No Shortage"])
search = f4.text_input("Search material", placeholder="e.g. 100000123")

filtered = df
if selected_plant != "All":
    filtered = filtered[filtered["plant"] == selected_plant]
if selected_abc != "All":
    filtered = filtered[filtered["abc_class"] == selected_abc]
if selected_status != "All":
    filtered = filtered[filtered["status"] == selected_status]
if search:
    filtered = filtered[filtered["material_number"].str.contains(search, na=False)]

# ── KPI cards ──────────────────────────────────────────────────────────────
total = len(filtered)
shortage_count = int((filtered["status"] == "Shortage").sum())
pct = round(shortage_count / total * 100, 1) if total else 0.0
overdue_total = int(filtered["overdue_backlog_qty"].sum())

k1, k2, k3, k4 = st.columns(4)
k1.metric("Materials Tracked", f"{total:,}")
k2.metric("In Shortage", f"{shortage_count:,}")
k3.metric("% At Risk", f"{pct}%")
k4.metric("Overdue Backlog Qty", f"{overdue_total:,}")

st.divider()

# ── Table ──────────────────────────────────────────────────────────────────
display_cols = [
    "material_number",
    "plant",
    "abc_class",
    "status",
    "available_stock",
    "safety_stock",
    "overdue_backlog_qty",
    "max_tt",
    "red_days_in_tt",
    "red_days",
    "min_qty_in_tt_gr",
]

max_red = int(df["red_days"].max() or 1)

event = st.dataframe(
    filtered[display_cols],
    width="stretch",
    height=480,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "material_number": st.column_config.TextColumn("Material"),
        "plant": st.column_config.TextColumn("Plant", width="small"),
        "abc_class": st.column_config.TextColumn("ABC", width="small"),
        "status": st.column_config.TextColumn("Status"),
        "available_stock": st.column_config.NumberColumn("Available", format="%d"),
        "safety_stock": st.column_config.NumberColumn("Safety", format="%d"),
        "overdue_backlog_qty": st.column_config.NumberColumn("Overdue Backlog", format="%d"),
        "max_tt": st.column_config.NumberColumn("Max TT (d)", format="%d"),
        "red_days_in_tt": st.column_config.NumberColumn("Red in TT", format="%d"),
        "red_days": st.column_config.ProgressColumn(
            "Red Days / 120", min_value=0, max_value=max_red, format="%d"
        ),
        "min_qty_in_tt_gr": st.column_config.NumberColumn("Min Qty in TT", format="%d"),
    },
)

# ── Row select → Simulation page ───────────────────────────────────────────
if event.selection.rows:
    row = filtered.iloc[event.selection.rows[0]]
    st.session_state["selected_marc_id"] = row["marc_id"]
    st.page_link(
        "views/simulation.py",
        label=f"📈 Xem simulation cho {row['material_number']} @ {row['plant']}",
    )
