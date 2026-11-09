"""Halaman ringkasan eksekutif."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts, ui
from src.analytics import (
    kpi_summary,
    monthly_series,
    pareto_curve,
    payment_summary,
    segment_summary,
    state_summary,
)
from src.config import SEGMENT_ACTION
from src.context import current
from src.formatting import compact, date_id, money, money_short, number, percent


def render() -> None:
    ctx = current()
    orders, customers = ctx["orders"], ctx["customers"]
    if orders.empty or customers.empty:
        ui.empty_state()

    k = kpi_summary(orders, customers)
    states = state_summary(orders, customers)
    segments = segment_summary(customers)
    monthly = monthly_series(orders)
    curve = pareto_curve(customers)
    payments = payment_summary(orders)

    ui.page_header(
        "Ringkasan eksekutif",
        "Kinerja pelanggan dalam satu pandangan",
        "Satu halaman untuk menjawab siapa pelanggan terbaik, dari mana mereka berasal, "
        "seberapa besar nilai transaksinya, dan seberapa besar risiko kehilangan mereka.",
        [
            f"Data sampai <b>{date_id(ctx['snapshot'] - pd.Timedelta(days=1))}</b>",
            "Sumber: Olist Brazilian E-Commerce",
        ],
    )

    top_state = states.iloc[0]
    top5_share = states.head(5)["pendapatan"].sum() / states["pendapatan"].sum()
    ui.insight(
        f"<b>{top_state['negara_bagian']}</b> menyumbang {percent(top_state['porsi_pendapatan'])} pendapatan, "
        f"dan lima negara bagian teratas mencapai <b>{percent(top5_share)}</b>. "
        "Konsentrasi ini memudahkan alokasi anggaran pemasaran regional.",
        tone="info",
        label="Konsentrasi",
    )
    ui.insight(
        f"20% pelanggan dengan belanja terbesar menyumbang <b>{percent(curve.iloc[int(len(curve) * 0.2) - 1]['cumulative_share'])}</b> "
        f"pendapatan. Namun repeat rate hanya <b>{percent(k['repeat_rate'])}</b>, sehingga pertumbuhan "
        "lebih banyak bergantung pada akuisisi daripada retensi.",
        tone="warning",
        label="Retensi",
    )

    st.write("")
    ui.kpi_row(
        [
            {"label": "Pendapatan", "value": money_short(k["revenue"]), "sub": f"{number(k['orders'])} pesanan sah"},
            {"label": "Pelanggan unik", "value": number(k["customers"]), "sub": f"{number(k['avg_orders'], 2)} pesanan per pelanggan"},
            {"label": "Nilai pesanan rata-rata", "value": money(k["aov"]), "sub": f"median belanja {money(k['median_spend'])}"},
            {"label": "Repeat rate", "value": percent(k["repeat_rate"]), "sub": f"{number(k['customers'] * k['repeat_rate'])} pelanggan berulang", "accent": "#3A6EA5"},
        ]
    )
    st.write("")
    ui.kpi_row(
        [
            {
                "label": "Pelanggan bernilai tinggi",
                "value": number(k["high_value_customers"]),
                "sub": f"{percent(k['high_value_share'])} dari pendapatan (top 20%)",
                "accent": "#0E7C6B",
            },
            {
                "label": "Rating rata-rata",
                "value": f"{number(k['avg_review'], 2)} / 5",
                "sub": f"{percent(k['review_response'])} pesanan dinilai",
                "accent": "#2A9D8F",
            },
            {
                "label": "Pengiriman tepat waktu",
                "value": percent(k["on_time_rate"]),
                "sub": f"rata-rata {number(k['avg_delivery_days'], 1)} hari sampai",
                "accent": "#D97706",
            },
            {
                "label": "Pendapatan dari pelanggan berulang",
                "value": percent(k["repeat_revenue_share"]),
                "sub": "hanya dari 3% pelanggan",
                "accent": "#7A5AF8",
            },
        ]
    )

    st.write("")
    left, right = st.columns([1.65, 1], gap="medium")
    with left:
        with st.container(border=True):
            ui.section(
                "Tren pendapatan bulanan",
                "Pendapatan dipisah menurut pelanggan baru dan pelanggan yang sudah pernah membeli.",
                eyebrow="Waktu",
            )
            chart_data = monthly[monthly["Pesanan"] >= 30]
            st.plotly_chart(charts.revenue_trend(chart_data), width="stretch", config={"displayModeBar": False})
            ui.note("Bulan dengan kurang dari 30 pesanan (September dan Desember 2016) tidak ditampilkan.")
    with right:
        with st.container(border=True):
            ui.section("Komposisi pendapatan per segmen", "Sepuluh segmen RFM, diurutkan menurut pendapatan.", eyebrow="Segmen")
            st.plotly_chart(charts.segment_donut(segments), width="stretch", config={"displayModeBar": False})

    st.write("")
    left, right = st.columns([1.15, 1], gap="medium")
    with left:
        with st.container(border=True):
            ui.section("Negara bagian dengan pendapatan terbesar", "Delapan dari 27 negara bagian.", eyebrow="Geografi")
            st.plotly_chart(charts.state_bar(states, "pendapatan", top=8), width="stretch", config={"displayModeBar": False})
    with right:
        with st.container(border=True):
            ui.section("Segmen yang paling perlu ditangani", "Diurutkan menurut pendapatan yang dibawa.", eyebrow="Prioritas")
            table = segments.head(6).copy()
            view = pd.DataFrame(
                {
                    "Segmen": table["segment"].astype(str),
                    "Pelanggan": table["pelanggan"].astype(int),
                    "Porsi pendapatan": table["porsi_pendapatan"].map(lambda v: percent(v)),
                    "Prioritas": table["prioritas"],
                }
            )
            ui.table(view, numeric=["Pelanggan", "Porsi pendapatan"], max_height=320)
            priority = segments.iloc[0]
            ui.note(
                f"Segmen terbesar menurut pendapatan: <b>{priority['segment']}</b> "
                f"({percent(priority['porsi_pendapatan'])}). "
                f"Langkah yang disarankan: {SEGMENT_ACTION.get(priority['segment'], ('', ''))[1]}"
            )

    st.write("")
    with st.container(border=True):
        ui.section("Cara membaca dashboard ini", "Enam pertanyaan bisnis, enam halaman.", eyebrow="Navigasi")
        cols = st.columns(3, gap="medium")
        items = [
            ("Pelanggan terbaik", "Peringkat nilai historis, profil, dan riwayat transaksi.", "Halaman Pelanggan"),
            ("Asal pelanggan", "Sebaran negara bagian, kota, dan wilayah.", "Halaman Geografi"),
            ("Nilai transaksi", "Pareto, distribusi belanja, dan tier pelanggan.", "Halaman Pelanggan"),
            ("Risiko tidak aktif", "Skor risiko, pelanggan bernilai yang mulai hilang.", "Halaman Risiko"),
            ("Loyalitas", "Repeat rate, kohort, dan pemicu pembelian ulang.", "Halaman Loyalitas"),
            ("Strategi pemasaran", "Rencana aksi per segmen beserta KPI.", "Halaman Loyalitas"),
        ]
        for i, (title, desc, page) in enumerate(items):
            with cols[i % 3]:
                st.markdown(
                    f'<div style="padding:2px 0 14px 0"><div class="pill">{page}</div>'
                    f'<div style="font-weight:700;color:#0B1F2A;margin:6px 0 2px 0;font-size:.88rem">{title}</div>'
                    f'<div style="color:#667085;font-size:.76rem;line-height:1.4">{desc}</div></div>',
                    unsafe_allow_html=True,
                )
