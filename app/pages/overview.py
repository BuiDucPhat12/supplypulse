import streamlit as st
from db import get_shortage_report

st.title("Shortage Overview")

df = get_shortage_report()

# ── Filters ────────────────────────────────────────────────────────────────
col_f1, col_f2 = st.columns(2)
plants = ["All"] + sorted(df["plant"].dropna().unique().tolist())
selected_plant = col_f1.selectbox("Plant", plants)
selected_status = col_f2.selectbox("Status", ["All", "Shortage", "No Shortage"])

if selected_plant != "All":
    df = df[df["plant"] == selected_plant]
if selected_status != "All":
    df = df[df["status"] == selected_status]

# ── KPI cards ──────────────────────────────────────────────────────────────
total = len(df)
shortage_count = (df["status"] == "Shortage").sum()
pct = round(shortage_count / total * 100, 1) if total else 0

k1, k2, k3 = st.columns(3)
k1.metric("Total Materials", total)
k2.metric("In Shortage", shortage_count)
k3.metric("% At Risk", f"{pct}%")

st.divider()

# ── Table ──────────────────────────────────────────────────────────────────
def highlight_shortage(row):
    color = "background-color: #ffd6d6" if row["status"] == "Shortage" else ""
    return [color] * len(row)

display_cols = [
    "material_number", "plant", "available_stock", "safety_stock",
    "max_tt", "red_days", "min_qty_in_tt_gr", "status",
]

st.dataframe(
    df[display_cols].style.apply(highlight_shortage, axis=1),
    use_container_width=True,
    height=500,
)
