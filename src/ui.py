"""Komponen tampilan: CSS, kartu KPI, judul halaman, dan filter sidebar."""

from __future__ import annotations

import html
from datetime import date

import pandas as pd
import streamlit as st

from .config import (
    ACCENT,
    BORDER,
    FAINT,
    INK,
    MUTED,
    PRIMARY,
    PRIMARY_SOFT,
    SEGMENT_ORDER,
)
from .formatting import money_short, number, percent

CSS = f"""
<style>
:root {{
  --ink: {INK};
  --muted: {MUTED};
  --faint: {FAINT};
  --border: {BORDER};
  --primary: {PRIMARY};
  --primary-soft: {PRIMARY_SOFT};
  --accent: {ACCENT};
}}

html, body, [class*="css"] {{
  font-family: 'Source Sans 3', 'Segoe UI', system-ui, -apple-system, sans-serif;
}}

[data-testid="stAppViewContainer"] {{
  background: #F5F7F9;
}}

[data-testid="stHeader"] {{
  background: rgba(245, 247, 249, 0.85);
  backdrop-filter: blur(6px);
}}

.block-container {{
  padding-top: 1.6rem;
  padding-bottom: 3.5rem;
  max-width: 1360px;
}}

[data-testid="stSidebar"] {{
  background: #FFFFFF;
  border-right: 1px solid {BORDER};
}}

[data-testid="stSidebar"] .block-container {{
  padding-top: 1rem;
}}

[data-testid="stSidebarNav"] a {{
  border-radius: 8px;
  padding: 0.28rem 0.55rem;
  color: {MUTED};
}}

[data-testid="stSidebarNav"] a:hover {{
  background: #F1F6F4;
  color: {INK};
}}

[data-testid="stSidebarNav"] a[aria-current="page"] {{
  background: #F2F5F3;
  color: {PRIMARY};
  font-weight: 700;
  box-shadow: inset 2px 0 0 {PRIMARY};
}}

[data-testid="stSidebarNav"] a[aria-current="page"] span {{
  color: {PRIMARY};
}}

[data-testid="stSidebar"] hr {{
  margin: 0.9rem 0;
  border-color: {BORDER};
}}

/* Kartu berbingkai */
div[data-testid="stVerticalBlockBorderWrapper"] {{
  background: #FFFFFF;
  border: 1px solid {BORDER};
  border-radius: 8px;
  box-shadow: none;
}}

div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlockBorderWrapper"] {{
  box-shadow: none;
}}

/* Judul halaman */
.page-head {{
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 24px;
  margin: 0 0 18px 0;
  padding-bottom: 14px;
  border-bottom: 1px solid {BORDER};
}}

.page-eyebrow {{
  font-size: 0.68rem;
  letter-spacing: 0.13em;
  text-transform: uppercase;
  color: {PRIMARY};
  font-weight: 700;
  margin-bottom: 6px;
}}

.page-head h1 {{
  font-size: 1.72rem;
  line-height: 1.2;
  margin: 0 0 6px 0;
  color: {INK};
  letter-spacing: -0.02em;
  font-weight: 700;
}}

.page-head p {{
  margin: 0;
  color: {MUTED};
  font-size: 0.9rem;
  line-height: 1.45;
  max-width: 760px;
}}

.page-meta {{
  text-align: right;
  font-size: 0.72rem;
  color: {FAINT};
  line-height: 1.5;
  white-space: nowrap;
}}

.page-meta b {{
  color: {MUTED};
  font-weight: 600;
}}

/* KPI */
.kpi {{
  background: #FFFFFF;
  border: 1px solid {BORDER};
  border-radius: 8px;
  padding: 13px 15px 12px 15px;
  height: 100%;
  min-height: 104px;
  box-shadow: none;
}}

.kpi-label {{
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  color: {MUTED};
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 6px;
}}

.kpi-dot {{
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--kpi-accent, {PRIMARY});
  display: inline-block;
}}

.kpi-value {{
  font-size: 1.58rem;
  font-weight: 700;
  color: {INK};
  line-height: 1.15;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}}

.kpi-sub {{
  font-size: 0.72rem;
  color: {FAINT};
  margin-top: 5px;
  line-height: 1.35;
}}

/* Judul bagian */
.sec {{
  margin: 6px 0 8px 0;
}}

.sec-eyebrow {{
  font-size: 0.64rem;
  letter-spacing: 0.11em;
  text-transform: uppercase;
  color: {FAINT};
  font-weight: 700;
  margin-bottom: 2px;
}}

.sec h3 {{
  font-size: 1.02rem;
  margin: 0;
  color: {INK};
  font-weight: 700;
  letter-spacing: -0.01em;
}}

.sec p {{
  margin: 3px 0 0 0;
  color: {MUTED};
  font-size: 0.8rem;
  line-height: 1.4;
}}

/* Insight */
.insight {{
  background: #FFFFFF;
  border: 1px solid {BORDER};
  border-left: 3px solid var(--tone, {PRIMARY});
  border-radius: 10px;
  padding: 11px 15px;
  margin: 2px 0 4px 0;
  font-size: 0.84rem;
  color: {INK};
  line-height: 1.5;
}}

.insight .tag {{
  display: inline-block;
  font-size: 0.6rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--tone, {PRIMARY});
  margin-right: 8px;
}}

.insight b {{
  font-weight: 700;
}}

.note {{
  font-size: 0.72rem;
  color: {FAINT};
  line-height: 1.5;
  margin-top: 5px;
}}

.side-label {{
  font-size: 0.62rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: {FAINT};
  font-weight: 700;
  margin: 2px 0 6px 0;
}}

.side-note {{
  font-size: 0.68rem;
  color: {FAINT};
  line-height: 1.45;
  padding: 8px 0 2px 0;
}}

.pill {{
  display: inline-block;
  font-size: 0.66rem;
  font-weight: 700;
  color: {PRIMARY};
  letter-spacing: 0.02em;
}}

/* Streamlit widgets */
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stDateInput label {{
  font-size: 0.72rem;
  color: {MUTED};
  font-weight: 600;
}}

div[data-testid="stDataFrame"] {{
  border: 1px solid {BORDER};
  border-radius: 10px;
  overflow: hidden;
}}

.tbl-wrap {{
  overflow: auto;
  border: 1px solid {BORDER};
  border-radius: 10px;
  background: #FFFFFF;
}}

table.tbl {{
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 0.78rem;
}}

table.tbl thead th {{
  position: sticky;
  top: 0;
  z-index: 1;
  background: #F7FAF9;
  color: {MUTED};
  font-size: 0.66rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  font-weight: 700;
  text-align: left;
  padding: 9px 11px;
  border-bottom: 1px solid {BORDER};
  white-space: nowrap;
}}

table.tbl tbody td {{
  padding: 8px 11px;
  border-bottom: 1px solid #F0F2F5;
  color: {INK};
  vertical-align: top;
  white-space: nowrap;
}}

table.tbl tbody tr:last-child td {{
  border-bottom: none;
}}

table.tbl tbody tr:hover td {{
  background: #FAFCFB;
}}

table.tbl td.num, table.tbl th.num {{
  text-align: right;
  font-variant-numeric: tabular-nums;
}}

table.tbl td.wrap {{
  white-space: normal;
  min-width: 240px;
  line-height: 1.4;
}}

table.tbl td.long {{
  white-space: normal;
  min-width: 320px;
  line-height: 1.4;
}}

.stButton > button, .stDownloadButton > button {{
  border-radius: 9px;
  font-weight: 600;
  font-size: 0.82rem;
}}

.stDownloadButton > button {{
  border: 1px solid {BORDER};
}}

[data-testid="stExpander"] {{
  border: 1px solid {BORDER};
  border-radius: 10px;
  background: #FFFFFF;
}}

[data-testid="stExpander"] summary {{
  font-size: 0.82rem;
  color: {MUTED};
}}

[data-testid="stTabs"] button {{
  font-size: 0.84rem;
  font-weight: 600;
}}

[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
  background-color: {PRIMARY};
}}

.label-dot {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.72rem;
  font-weight: 700;
  color: {INK};
}}

.label-dot i {{
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ink-dot, {PRIMARY});
  display: inline-block;
  flex: none;
}}

/* Tag pilihan widget dibuat netral, tanpa latar berwarna */
[data-baseweb="tag"] {{
  background: #EEF1F4 !important;
  color: {INK} !important;
  border-radius: 6px !important;
}}

[data-baseweb="tag"] span,
[data-baseweb="tag"] svg {{
  color: {INK} !important;
  fill: {INK} !important;
}}

@media (max-width: 720px) {{
  .page-head {{ flex-direction: column; align-items: flex-start; gap: 8px; }}
  .page-meta {{ text-align: left; white-space: normal; }}
  .kpi-value {{ font-size: 1.35rem; }}
}}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def page_header(eyebrow: str, title: str, description: str, meta_lines: list[str] | None = None) -> None:
    meta = ""
    if meta_lines:
        meta = '<div class="page-meta">' + "<br>".join(meta_lines) + "</div>"
    st.markdown(
        f"""
        <div class="page-head">
          <div>
            <div class="page-eyebrow">{html.escape(eyebrow)}</div>
            <h1>{html.escape(title)}</h1>
            <p>{description}</p>
          </div>
          {meta}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, description: str | None = None, eyebrow: str | None = None) -> None:
    desc_html = f"<p>{description}</p>" if description else ""
    st.markdown(
        f'<div class="sec"><h3>{html.escape(title)}</h3>{desc_html}</div>',
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, sub: str = "", accent: str | None = None) -> str:
    accent_style = f"--kpi-accent:{accent};" if accent else ""
    return f"""
    <div class="kpi" style="{accent_style}">
      <div class="kpi-label"><span class="kpi-dot"></span>{html.escape(label)}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-sub">{sub}</div>
    </div>
    """


def kpi_row(items: list[dict], columns: int | None = None) -> None:
    count = columns or len(items)
    cols = st.columns(count, gap="medium")
    for index, item in enumerate(items):
        with cols[index % count]:
            st.markdown(
                kpi_card(
                    item.get("label", ""),
                    item.get("value", "-"),
                    item.get("sub", ""),
                    item.get("accent"),
                ),
                unsafe_allow_html=True,
            )


def insight(text: str, tone: str = "info", label: str = "Insight") -> None:
    color = {"info": PRIMARY, "warning": ACCENT, "danger": "#C2414F", "neutral": MUTED}.get(tone, PRIMARY)
    st.markdown(
        f'<div class="insight" style="--tone:{color}"><span class="tag">{html.escape(label)}</span>{text}</div>',
        unsafe_allow_html=True,
    )


def note(text: str) -> None:
    st.markdown(f'<div class="note">{text}</div>', unsafe_allow_html=True)


def table(
    frame: pd.DataFrame,
    numeric: list[str] | None = None,
    wrap: list[str] | None = None,
    long: list[str] | None = None,
    max_height: int = 420,
) -> None:
    """Tabel HTML ringan tanpa ketergantungan pyarrow."""
    if frame.empty:
        st.info("Tidak ada data untuk ditampilkan.")
        return
    numeric_cols = set(numeric or [])
    wrap_cols = set(wrap or [])
    long_cols = set(long or [])
    header = "".join(
        f'<th class="{"num" if col in numeric_cols else ""}">{html.escape(str(col))}</th>'
        for col in frame.columns
    )
    rows = []
    for _, row in frame.iterrows():
        cells = []
        for col in frame.columns:
            value = row[col]
            if value is None or (isinstance(value, float) and pd.isna(value)):
                text = ""
            else:
                text = html.escape(str(value))
            classes = "num" if col in numeric_cols else ("long" if col in long_cols else ("wrap" if col in wrap_cols else ""))
            cells.append(f'<td class="{classes}">{text}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    st.markdown(
        f'<div class="tbl-wrap" style="max-height:{max_height}px">'
        f'<table class="tbl"><thead><tr>{header}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def sidebar_filters(
    min_date: date,
    max_date: date,
    state_options: list[str],
    payment_options: list[tuple[str, str]],
    category_options: list[str],
) -> dict:
    with st.sidebar:
        st.markdown('<div class="side-label">Filter analisis</div>', unsafe_allow_html=True)

        if st.button("Atur ulang filter", use_container_width=True, key="filter_reset"):
            for key in (
                "filter_dates",
                "filter_states",
                "filter_payments",
                "filter_categories",
                "filter_delivery",
                "filter_segments",
            ):
                st.session_state.pop(key, None)
            st.rerun()

        date_range = st.date_input(
            "Periode transaksi",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            format="DD/MM/YYYY",
            key="filter_dates",
        )
        if isinstance(date_range, tuple):
            start, end = (date_range[0], date_range[1]) if len(date_range) > 1 else (date_range[0], date_range[0])
        else:
            start = end = date_range

        selected_states = st.multiselect(
            "Negara bagian",
            options=state_options,
            default=[],
            placeholder="Semua negara bagian",
            help="Kosongkan untuk menampilkan seluruh Brazil.",
            key="filter_states",
        )

        selected_payments = st.multiselect(
            "Tipe pembayaran",
            options=[value for value, _ in payment_options],
            default=[],
            placeholder="Semua tipe",
            format_func=dict(payment_options).get,
            key="filter_payments",
        )

        selected_categories = st.multiselect(
            "Kategori produk",
            options=category_options,
            default=[],
            placeholder="Semua kategori",
            help="Kategori utama tiap pesanan, yaitu kategori bernilai terbesar.",
            key="filter_categories",
        )

        delivery_choice = st.selectbox(
            "Performa pengiriman",
            options=["Semua", "Tepat waktu", "Terlambat"],
            index=0,
            key="filter_delivery",
        )
        delivery = {"Tepat waktu": "ontime", "Terlambat": "late"}.get(delivery_choice)

        selected_segments = st.multiselect(
            "Segmen RFM",
            options=SEGMENT_ORDER,
            default=[],
            placeholder="Semua segmen",
            help="Disaring dua tahap: segmen dihitung ulang setelah filter lain diterapkan.",
            key="filter_segments",
        )

        st.markdown(
            '<div class="side-note">Segmen RFM dan skor risiko dihitung ulang dari transaksi '
            "yang lolos filter. Karena itu, memilih kategori, tipe pembayaran, atau performa "
            "pengiriman mengubah komposisi segmen. Tanggal analisis tetap 4 September 2018 "
            "agar recency dapat dibandingkan.</div>",
            unsafe_allow_html=True,
        )
        st.divider()
        st.markdown(
            '<div class="side-note"><b>Sumber</b><br>Olist Brazilian E-Commerce Public Dataset '
            "(Kaggle), 99.441 pesanan pada 2016-2018.</div>",
            unsafe_allow_html=True,
        )
    return {
        "start": start,
        "end": end,
        "states": selected_states,
        "payments": selected_payments,
        "categories": selected_categories,
        "delivery": delivery,
        "segments": selected_segments,
    }


def format_delta(value: float, decimals: int = 1) -> str:
    return f"{'+' if value >= 0 else ''}{number(value * 100, decimals)} poin"


def empty_state(message: str = "Tidak ada transaksi pada filter ini.") -> None:
    st.warning(message)
    st.stop()
