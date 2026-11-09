"""CRM Insight - dashboard Business Intelligence untuk data Olist.

Jalankan dengan: streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from src import ui
from src.config import ASSETS_DIR
from src.context import build_context
from src.data import load_orders, payment_label, valid_orders
from views import customers, geography, loyalty, methodology, overview, rfm, risk

st.set_page_config(
    page_title="CRM Insight | Olist",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

ui.inject_css()
st.logo(str(ASSETS_DIR / "logo.svg"), size="large")

pages = [
    st.Page(overview.render, title="Ringkasan", icon=":material/dashboard:", url_path="ringkasan", default=True),
    st.Page(customers.render, title="Pelanggan", icon=":material/people:", url_path="pelanggan"),
    st.Page(rfm.render, title="Segmentasi RFM", icon=":material/pie_chart:", url_path="segmentasi"),
    st.Page(geography.render, title="Geografi", icon=":material/public:", url_path="geografi"),
    st.Page(risk.render, title="Risiko tidak aktif", icon=":material/warning:", url_path="risiko"),
    st.Page(loyalty.render, title="Loyalitas & strategi", icon=":material/trending_up:", url_path="loyalitas"),
    st.Page(methodology.render, title="Metodologi", icon=":material/menu_book:", url_path="metodologi"),
]

navigation = st.navigation(pages)

raw = load_orders()
valid = valid_orders(raw)
min_date = valid["purchase_ts"].min().date()
max_date = valid["purchase_ts"].max().date()
state_options = sorted(valid["state"].dropna().unique())

payment_values = valid["payment_type"].dropna().value_counts().index.tolist()
payment_options = [(value, payment_label(value)) for value in payment_values]

category_options = (
    valid["main_category"].dropna().value_counts().index.tolist()
)

filters = ui.sidebar_filters(
    min_date,
    max_date,
    state_options,
    payment_options,
    category_options,
)
st.session_state["ctx"] = build_context(**filters)

navigation.run()
