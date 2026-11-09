"""Halaman geografi pelanggan."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts, ui
from src.analytics import city_summary, region_summary, state_summary
from src.context import current
from src.data import load_state_coordinates
from src.formatting import money, money_short, number, percent


def render() -> None:
    ctx = current()
    orders, customers = ctx["orders"], ctx["customers"]
    if orders.empty or customers.empty:
        ui.empty_state()

    states = state_summary(orders, customers)
    regions = region_summary(states)
    cities = city_summary(orders, top=15)
    coords = load_state_coordinates()

    total_revenue = states["pendapatan"].sum()
    total_customers = states["pelanggan"].sum()
    top = states.iloc[0]
    top_region = regions.iloc[0]
    threshold = 100 if (states["pelanggan"] >= 100).any() else 0
    reliable = states[states["pelanggan"] >= threshold]
    best_value = reliable.sort_values("nilai_pelanggan", ascending=False).iloc[0]
    best_repeat = reliable.sort_values("repeat_rate", ascending=False).iloc[0]

    ui.page_header(
        "Geografi",
        "Dari mana pelanggan berasal",
        "Sebaran pelanggan dan pendapatan menurut negara bagian, wilayah, dan kota. "
        "Gunakan peta untuk melihat konsentrasi, lalu tabel untuk membandingkan efisiensi tiap wilayah.",
        [f"<b>{len(states)}</b> negara bagian", "Basis: alamat pelanggan"],
    )

    ui.insight(
        f"<b>{top['negara_bagian']}</b> menampung {percent(top['pelanggan'] / total_customers)} pelanggan dan "
        f"{percent(top['porsi_pendapatan'])} pendapatan. Wilayah <b>{top_region['wilayah']}</b> mendominasi dengan "
        f"{percent(top_region['porsi'])} pendapatan. Ekspansi di luar wilayah ini membutuhkan biaya logistik yang lebih tinggi.",
        tone="info",
        label="Konsentrasi",
    )
    ui.insight(
        f"Negara bagian dengan nilai belanja per pelanggan tertinggi adalah <b>{best_value['negara_bagian']}</b> "
        f"({money(best_value['nilai_pelanggan'])} per pelanggan, minimal {number(threshold)} pelanggan). "
        f"Repeat rate tertinggi ada di <b>{best_repeat['negara_bagian']}</b> ({percent(best_repeat['repeat_rate'])}). "
        "Wilayah dengan basis pelanggan kecil perlu uji coba sebelum investasi besar.",
        tone="warning",
        label="Peluang",
    )

    st.write("")
    ui.kpi_row(
        [
            {"label": "Negara bagian", "value": number(len(states)), "sub": "dari 27 wilayah Brazil"},
            {"label": "Pendapatan wilayah teratas", "value": percent(top_region["porsi"]), "sub": top_region["wilayah"], "accent": "#3A6EA5"},
            {"label": "Nilai per pelanggan", "value": money(total_revenue / total_customers if total_customers else 0), "sub": "rata-rata nasional"},
            {"label": "Kota teratas", "value": cities.iloc[0]["city"], "sub": f"{money_short(cities.iloc[0]['pendapatan'])} pendapatan", "accent": "#D97706"},
        ]
    )

    st.write("")
    left, right = st.columns([1.55, 1], gap="medium")
    with left:
        with st.container(border=True):
            heading = st.columns([1.5, 1])
            with heading[0]:
                ui.section("Peta konsentrasi pelanggan", "Ukuran lingkaran menunjukkan jumlah pelanggan.", eyebrow="Peta")
            with heading[1]:
                metric_label = st.selectbox(
                    "Warna peta",
                    ["Pendapatan", "Pelanggan", "Nilai per pelanggan", "Repeat rate"],
                    label_visibility="collapsed",
                    key="geo_metric",
                )
            metric_map = {
                "Pendapatan": "pendapatan",
                "Pelanggan": "pelanggan",
                "Nilai per pelanggan": "nilai_pelanggan",
                "Repeat rate": "repeat_rate",
            }
            st.plotly_chart(
                charts.geo_bubble(states, coords, metric_map[metric_label]),
                width="stretch",
                config={"displayModeBar": False},
            )
            ui.note("Koordinat diambil dari rata-rata kode pos pelanggan pada dataset geolocation.")
    with right:
        with st.container(border=True):
            ui.section("Porsi pendapatan per wilayah", "Lima wilayah resmi Brazil.", eyebrow="Wilayah")
            st.plotly_chart(charts.region_bar(regions), width="stretch", config={"displayModeBar": False})
            ui.note(
                f"Sudeste dan Sul bersama menyumbang "
                f"{percent(regions[regions['wilayah'].isin(['Sudeste', 'Sul'])]['porsi'].sum())} pendapatan."
            )

    st.write("")
    with st.container(border=True):
        ui.section(
            "Perbandingan negara bagian",
            "Pelanggan, pendapatan, nilai belanja, dan loyalitas per negara bagian.",
            eyebrow="Tabel",
        )
        view = pd.DataFrame(
            {
                "Negara bagian": states["negara_bagian"],
                "Kode": states["state"],
                "Wilayah": states["wilayah"],
                "Pelanggan": states["pelanggan"].astype(int),
                "Pendapatan": states["pendapatan"].map(lambda v: money(v)),
                "Porsi": states["porsi_pendapatan"].map(lambda v: percent(v)),
                "AOV": states["aov"].map(lambda v: money(v)),
                "Nilai/pelanggan": states["nilai_pelanggan"].map(lambda v: money(v)),
                "Repeat rate": states["repeat_rate"].map(lambda v: percent(v) if pd.notna(v) else "-"),
            }
        )
        ui.table(
            view,
            numeric=["Pelanggan", "Pendapatan", "Porsi", "AOV", "Nilai/pelanggan", "Repeat rate"],
            max_height=430,
        )
        ui.note(
            "Negara bagian diurutkan menurut pendapatan. Dataset tidak memuat kanal akuisisi, sehingga "
            "'asal pelanggan' di sini berarti lokasi alamat pelanggan."
        )

    st.write("")
    left, right = st.columns([1.1, 1], gap="medium")
    with left:
        with st.container(border=True):
            ui.section("Kota dengan pendapatan terbesar", "Dua belas kota teratas.", eyebrow="Kota")
            st.plotly_chart(charts.city_bar(cities, top=12), width="stretch", config={"displayModeBar": False})
    with right:
        with st.container(border=True):
            ui.section("Rincian kota", "Sepuluh kota teratas menurut pendapatan.", eyebrow="Tabel")
            top_cities = cities.head(10).copy()
            view = pd.DataFrame(
                {
                    "Kota": top_cities["city"] + " (" + top_cities["state"] + ")",
                    "Pelanggan": top_cities["pelanggan"].astype(int),
                    "Pendapatan": top_cities["pendapatan"].map(lambda v: money(v)),
                    "AOV": top_cities["aov"].map(lambda v: money(v)),
                }
            )
            ui.table(
                view,
                numeric=["Pelanggan", "Pendapatan", "AOV"],
                max_height=390,
            )
