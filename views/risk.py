"""Halaman risiko pelanggan tidak aktif."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts, ui
from src.analytics import kpi_summary, risk_priority, risk_summary, risk_threshold_preview
from src.context import current
from src.formatting import money, money_short, number, percent, short_id


def render() -> None:
    ctx = current()
    orders, customers = ctx["orders"], ctx["customers"]
    if orders.empty or customers.empty:
        ui.empty_state()

    k = kpi_summary(orders, customers)
    risk = risk_summary(customers)
    high_risk = customers[customers["risk_band"].isin(["Tinggi", "Kritis"])]
    overdue = customers[customers["is_overdue"]]
    high_risk_revenue = float(high_risk["monetary"].sum())
    revenue_share = high_risk_revenue / customers["monetary"].sum() if customers["monetary"].sum() else 0

    ui.page_header(
        "Risiko",
        "Pelanggan mana yang berpotensi tidak aktif",
        "Skor risiko 0-100 menggabungkan recency, frekuensi, kepuasan, dan keterlambatan pengiriman. "
        "Skor membantu memisahkan pelanggan yang membutuhkan tindakan segera dari yang masih aman.",
        [f"<b>{number(len(high_risk))}</b> pelanggan berisiko tinggi", "Ambang recency dapat diatur"],
    )

    ui.insight(
        f"<b>{number(len(high_risk))}</b> pelanggan berisiko tinggi atau kritis membawa "
        f"<b>{money_short(high_risk_revenue)}</b> ({percent(revenue_share)} pendapatan historis). "
        f"Recency median kelompok ini {number(high_risk['recency'].median(), 0)} hari. "
        "Angka ini menunjukkan ukuran basis yang perlu diaktifkan kembali, bukan prediksi churn.",
        tone="danger",
        label="Ukuran risiko",
    )
    ui.insight(
        f"Ada <b>{number(len(overdue))}</b> pelanggan berulang yang jeda transaksinya sudah dua kali "
        f"kebiasaan mereka sendiri. Kelompok ini sinyal paling kuat karena pola belanjanya diketahui, "
        f"dengan median {number(overdue['median_interval_days'].median(), 0) if not overdue.empty else 0} hari antar transaksi.",
        tone="warning",
        label="Sinyal perilaku",
    )

    st.write("")
    ui.kpi_row(
        [
            {"label": "Risiko tinggi + kritis", "value": number(len(high_risk)), "sub": f"{percent(len(high_risk) / len(customers))} pelanggan", "accent": "#C2414F"},
            {"label": "Pendapatan terkait", "value": money_short(high_risk_revenue), "sub": f"{percent(revenue_share)} dari pendapatan", "accent": "#D97706"},
            {"label": "Recency median", "value": f"{number(high_risk['recency'].median(), 0)} hari", "sub": "kelompok berisiko tinggi"},
            {"label": "Berulang yang overdue", "value": number(len(overdue)), "sub": "jeda >= 2x kebiasaan", "accent": "#7A5AF8"},
        ]
    )

    st.write("")
    left, right = st.columns([1, 1.25], gap="medium")
    with left:
        with st.container(border=True):
            ui.section("Sebaran band risiko", "Jumlah pelanggan dan porsi pendapatan.", eyebrow="Distribusi")
            st.plotly_chart(charts.risk_bar(risk), width="stretch", config={"displayModeBar": False})
    with right:
        with st.container(border=True):
            ui.section("Recency seluruh pelanggan", "Semakin ke kanan, semakin lama tidak bertransaksi.", eyebrow="Recency")
            st.plotly_chart(charts.recency_histogram(customers), width="stretch", config={"displayModeBar": False})
            ui.note("Garis putus-putus menandai ambang 90, 180, dan 365 hari.")

    st.write("")
    with st.container(border=True):
        ui.section(
            "Simulator prioritas reaktivasi",
            "Tentukan sendiri batas recency dan kelas nilai. Daftar di bawah langsung menyesuaikan.",
            eyebrow="Aksi",
        )
        controls = st.columns([1.2, 1.2, 1], gap="large")
        with controls[0]:
            min_recency = st.slider("Minimal hari sejak transaksi terakhir", 30, 540, 180, step=30)
        with controls[1]:
            value_pct = st.slider(
                "Minimal persentil belanja pelanggan (%)",
                50,
                99,
                80,
                step=5,
                help="Contoh: 80 berarti hanya pelanggan pada 20% teratas menurut nilai belanja.",
            )
        preview = risk_threshold_preview(customers, min_recency, value_pct / 100)
        with controls[2]:
            st.metric("Ambang nilai belanja", money(preview["ambang_nilai"]))

        c1, c2, c3, c4 = st.columns(4, gap="medium")
        c1.metric("Pelanggan sasaran", number(preview["jumlah"]))
        c2.metric("Pendapatan historis", money_short(preview["pendapatan"]))
        c3.metric("Porsi pendapatan", percent(preview["porsi"]))
        c4.metric("Recency median", f"{number(preview['recency'], 0)} hari" if pd.notna(preview["recency"]) else "-")

        priority = risk_priority(customers, min_recency=min_recency, value_percentile=value_pct / 100)
        if priority.empty:
            st.info("Tidak ada pelanggan yang memenuhi kombinasi ambang tersebut.")
        else:
            view = pd.DataFrame(
                {
                    "Prioritas": priority["prioritas"],
                    "ID pelanggan": priority["customer_uid"].map(short_id),
                    "Kota": priority["city"],
                    "Negara bagian": priority["state"],
                    "Pesanan": priority["n_orders"].astype(int),
                    "Total belanja": priority["monetary"].map(lambda v: money(v)),
                    "Recency (hari)": priority["recency"].astype(int),
                    "Skor risiko": priority["risk_score"].map(lambda v: number(v, 1)),
                    "Segmen": priority["segment"].astype(str),
                    "Rekomendasi": priority["rekomendasi"],
                }
            )
            ui.table(
                view.head(20),
                numeric=["Pesanan", "Total belanja", "Recency (hari)", "Skor risiko"],
                long=["Rekomendasi"],
                max_height=min(560, 60 + 34 * min(20, len(view))),
            )
            st.download_button(
                "Unduh daftar lengkap (CSV)",
                data=priority[
                    [
                        "customer_uid",
                        "city",
                        "state",
                        "n_orders",
                        "monetary",
                        "recency",
                        "risk_score",
                        "segment",
                        "risk_band",
                        "prioritas",
                        "rekomendasi",
                    ]
                ].to_csv(index=False).encode("utf-8"),
                file_name="prioritas_reaktivasi.csv",
                mime="text/csv",
                icon=":material/download:",
            )
            ui.note(
                f"Menampilkan 20 dari {number(len(priority))} pelanggan. File CSV memuat seluruh daftar sasaran. "
                "Prioritas P1 diberikan kepada pelanggan di atas persentil nilai ke-95."
            )

    st.write("")
    with st.container(border=True):
        ui.section(
            "Pelanggan berulang yang melewati kebiasaan",
            "Mereka pernah membeli lebih dari sekali, tetapi jeda terakhir sudah dua kali jeda normalnya.",
            eyebrow="Sinyal kuat",
        )
        if overdue.empty:
            st.info("Tidak ada pelanggan berulang yang melewati dua kali jeda kebiasaannya pada filter ini.")
        else:
            table = overdue.sort_values("monetary", ascending=False).head(12)
            view = pd.DataFrame(
                {
                    "ID pelanggan": table["customer_uid"].map(short_id),
                    "Kota": table["city"],
                    "Negara bagian": table["state"],
                    "Pesanan": table["n_orders"].astype(int),
                    "Total belanja": table["monetary"].map(lambda v: money(v)),
                    "Jeda biasa": table["median_interval_days"].map(lambda v: f"{number(v, 0)} hari"),
                    "Jeda sekarang": table["recency"].map(lambda v: f"{number(v, 0)} hari"),
                    "Kelipatan": table["gap_ratio"].map(lambda v: f"{number(v, 1)}x"),
                }
            )
            ui.table(
                view,
                numeric=["Pesanan", "Total belanja", "Jeda biasa", "Jeda sekarang", "Kelipatan"],
                max_height=min(500, 60 + 34 * len(view)),
            )

    st.write("")
    with st.container(border=True):
        ui.section("Peta pelanggan prioritas", "Recency tinggi dengan nilai belanja besar ada di kanan atas.", eyebrow="Visual")
        pool = risk_priority(customers, min_recency=min_recency, value_percentile=value_pct / 100)
        if pool.empty:
            st.info("Tidak ada pelanggan pada kombinasi filter ini.")
        else:
            st.plotly_chart(
                charts.risk_scatter(pool.head(1500)),
                width="stretch",
                config={"displayModeBar": False},
            )

    with st.expander("Bagaimana skor risiko dihitung?"):
        st.markdown(
            """
Skor berkisar 0-100 dengan bobot berikut:

| Komponen | Bobot | Cara hitung |
|---|---|---|
| Recency | 55% | hari sejak transaksi terakhir dibagi 365, dibatasi maksimal 1 |
| Frequency | 15% | kebalikan skor frekuensi (F1 = paling berisiko) |
| Kepuasan | 15% | (5 - rata-rata rating) / 4; tanpa rating dianggap netral 3,5 |
| Keterlambatan | 15% | proporsi pesanan yang tiba melewati estimasi |

Band: Rendah <= 35, Sedang <= 55, Tinggi <= 75, Kritis > 75.

Skor ini heuristik dan dapat dijelaskan, bukan model prediktif yang dilatih pada label churn.
Dataset berakhir September 2018 sehingga tidak tersedia periode masa depan untuk mengukur churn
secara langsung. Karena itu, skor dipakai untuk memprioritaskan tindakan, bukan meramalkan
probabilitas berhenti secara pasti.
            """
        )
