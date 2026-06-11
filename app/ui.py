"""Design system dùng chung cho mọi page: palette, plotly template, CSS."""

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

PALETTE = {
    "bg": "#0b1220",
    "card": "#111a2c",
    "border": "#1e293b",
    "text": "#e2e8f0",
    "muted": "#94a3b8",
    "inventory": "#38bdf8",
    "shortage": "#f87171",
    "safety": "#fbbf24",
    "consumption": "#fb923c",
    "asn": "#34d399",
    "good": "#34d399",
    "warn": "#fbbf24",
    "bad": "#f87171",
}


def setup() -> None:
    """Gọi đầu mỗi page: đăng ký plotly template + CSS cho metric cards."""
    template = go.layout.Template(
        layout=dict(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=PALETTE["text"], family="sans-serif"),
            xaxis=dict(gridcolor=PALETTE["border"], zerolinecolor=PALETTE["border"]),
            yaxis=dict(gridcolor=PALETTE["border"], zerolinecolor=PALETTE["border"]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified",
            margin=dict(l=10, r=10, t=40, b=10),
        )
    )
    pio.templates["supplypulse"] = template
    pio.templates.default = "supplypulse"

    st.markdown(
        f"""
        <style>
        [data-testid="stMetric"] {{
            background: {PALETTE["card"]};
            border: 1px solid {PALETTE["border"]};
            border-radius: 12px;
            padding: 16px 20px;
        }}
        [data-testid="stMetricLabel"] {{
            color: {PALETTE["muted"]};
        }}
        h1 {{
            letter-spacing: -0.02em;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, caption: str) -> None:
    st.title(title)
    st.caption(caption)


def status_color(status: str) -> str:
    return PALETTE["bad"] if status == "Shortage" else PALETTE["good"]
