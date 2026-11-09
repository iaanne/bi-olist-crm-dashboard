"""Halaman pelanggan: peringkat nilai, profil, dan riwayat transaksi."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts, ui
from src.analytics import kpi_summary, pareto_curve
from src.config import RISK_COLORS, SEGMENT_COLORS
from src.context import current
from src.formatting import date_id, money, money_short, number, percent, short_id

STATUS_LABELS = {
    "delivered": "Terkirim",
    "shipped": "Dikirim",
    "canceled": "Batal",
    "unavailable": "Tidak tersedia",
    "invoiced": "Ditagih",
    "processing": "Diproses",
    "created": "Dibuat",
    "approved": "Disetujui",
}


def _badge(text: str, color: str) -> str:
    return f'<span class="label-dot" style="--ink-dot:{color}"><i></i>{text}</span>'


def render() -> None:
    ctx = current()
    orders, customers = ctx["orders"], ctx["customers"]
    if orders.empty or customers.empty:
        ui.empty_state()

    k = kpi_summary(orders, customers)
    curve = pareto_curve(customers)
    top_customer = customers.sort_values("monetary", ascending=False).iloc[0]

    ui.page_header(
        "Pelanggan",
        "Siapa pelanggan terbaik dan berapa nilai transaksinya",
        "Peringkat pelanggan menurut nilai belanja historis, distribusi nilai, serta profil "
        "lengkap seorang pelanggan beserta riwayat pesanannya.",
        [f"<b>{number(len(customers))}</b> pelanggan", "ID pelanggan bersifat pseudonim"],
    )

    top20 = curve.iloc[int(len(curve) * 0.2) - 1]["cumulative_share"] if len(curve) >= 5 else curve.iloc[-1]["cumulative_share"]
    ui.insight(
        f"Pelanggan dengan belanja terbesar mencapai <b>{money(top_customer['monetary'])}</b> dari "
        f"{int(top_customer['n_orders'])} pesanan. Rata-rata belanja pelanggan hanya "
        f"<b>{money(k['avg_spend'])}</b>, dan 20% teratas menyumbang {percent(top20)} pendapatan.",
        tone="info",
        label="Nilai pelanggan",
    )

    st.write("")
    ui.kpi_row(
        [
            {"label": "Belanja tertinggi", "value": money(top_customer["monetary"]), "sub": f"ID {short_id(top_customer['customer_uid'])}"},
            {"label": "Rata-rata belanja", "value": money(k["avg_spend"]), "sub": f"median {money(k['median_spend'])}"},
            {"label": "Pendapatan 20% teratas", "value": percent(top20), "sub": "kontribusi terhadap total", "accent": "#3A6EA5"},
            {"label": "Pelanggan bernilai tinggi", "value": number(k["high_value_customers"]), "sub": f"{percent(k['high_value_share'])} pendapatan", "accent": "#0E7C6B"},
        ]
    )

    st.write("")
    left, right = st.columns([1.25, 1], gap="medium")
    with left:
        with st.container(border=True):
            ui.section("Kurva Pareto nilai pelanggan", "Seberapa terkonsentrasi pendapatan pada pelanggan teratas.", eyebrow="Konsentrasi")
            st.plotly_chart(charts.pareto(curve, top20), width="stretch", config={"displayModeBar": False})
    with right:
        with st.container(border=True):
            ui.section("Distribusi nilai belanja", "Jumlah pelanggan pada setiap rentang belanja.", eyebrow="Sebaran")
            st.plotly_chart(charts.spend_distribution(customers), width="stretch", config={"displayModeBar": False})

    # --- Tabel pelanggan teratas -------------------------------------------
    st.write("")
    ui.section(
        "Peringkat pelanggan",
        "Klik satu baris untuk membuka profil dan riwayat transaksi pelanggan tersebut.",
        eyebrow="Daftar",
    )
    controls = st.columns([1.1, 1.1, 1.6], gap="medium")
    with controls[0]:
        metric_label = st.selectbox(
            "Urutkan menurut",
            ["Total belanja", "Jumlah pesanan", "Transaksi terbaru", "Rating rata-rata"],
            key="customer_metric",
        )
    with controls[1]:
        limit = st.slider("Jumlah baris", 10, 50, 15, step=5, key="customer_limit")
    with controls[2]:
        search = st.text_input(
            "Cari ID pelanggan atau kota",
            placeholder="Contoh: 861EFF47 atau sao paulo",
            key="customer_search",
        )

    metric_map = {
        "Total belanja": ("monetary", False),
        "Jumlah pesanan": ("n_orders", False),
        "Transaksi terbaru": ("recency", True),
        "Rating rata-rata": ("avg_review", False),
    }
    sort_col, ascending = metric_map[metric_label]
    pool = customers.copy()
    if search.strip():
        needle = search.strip().lower()
        pool = pool[
            pool["customer_uid"].str.lower().str.contains(needle, na=False)
            | pool["city"].str.lower().str.contains(needle, na=False)
        ]
    if pool.empty:
        st.info("Tidak ada pelanggan yang cocok dengan pencarian.")
        return
    ranked = pool.sort_values(sort_col, ascending=ascending, na_position="last").head(limit).reset_index(drop=True)

    view = pd.DataFrame(
        {
            "Peringkat": ranked.index + 1,
            "ID pelanggan": ranked["customer_uid"].map(short_id),
            "Kota": ranked["city"],
            "Negara bagian": ranked["state"],
            "Pesanan": ranked["n_orders"].astype(int),
            "Total belanja": ranked["monetary"].map(lambda v: money(v)),
            "AOV": ranked["avg_order_value"].map(lambda v: money(v)),
            "Recency (hari)": ranked["recency"].astype(int),
            "Segmen": ranked["segment"].astype(str),
            "Tier": ranked["value_tier"],
        }
    )
    ui.table(
        view,
        numeric=["Peringkat", "Pesanan", "Total belanja", "AOV", "Recency (hari)"],
        max_height=min(560, 50 + 34 * len(view)),
    )

    st.write("")
    labels = {
        uid: f"#{rank} · {short_id(uid)} · {money(spend)} · {city}, {state}"
        for rank, (uid, spend, city, state) in enumerate(
            zip(ranked["customer_uid"], ranked["monetary"], ranked["city"], ranked["state"]),
            start=1,
        )
    }
    selected_uid = st.selectbox(
        "Pilih pelanggan untuk membuka profil",
        options=ranked["customer_uid"].tolist(),
        format_func=lambda uid: labels.get(uid, uid),
        key="profile_select",
    )
    profile = customers.loc[customers["customer_uid"] == selected_uid].iloc[0]
    profile_orders = orders[orders["customer_uid"] == selected_uid].sort_values("purchase_ts", ascending=False)

    st.write("")
    with st.container(border=True):
        ui.section(
            "Profil pelanggan",
            "Identitas pseudonim, nilai historis, preferensi, dan seluruh pesanan.",
            eyebrow="Detail",
        )
        left, right = st.columns([1, 1.35], gap="large")
        with left:
            segment_color = SEGMENT_COLORS.get(str(profile["segment"]), "#667085")
            risk_color = RISK_COLORS.get(str(profile["risk_band"]), "#667085")
            st.markdown(
                f"""
                <div style="font-size:.72rem;color:#98A2B3;letter-spacing:.08em">CUSTOMER UNIQUE ID</div>
                <div style="font-family:ui-monospace,SFMono-Regular,monospace;font-size:1.02rem;color:#0B1F2A;font-weight:600;margin-bottom:8px">{profile['customer_uid']}</div>
                <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px">
                  {_badge(str(profile['segment']), segment_color)}
                  {_badge('Tier ' + str(profile['value_tier']), '#3A6EA5')}
                  {_badge('Risiko ' + str(profile['risk_band']), risk_color)}
                </div>
                <div style="font-size:.82rem;color:#667085;line-height:1.55">
                  {profile['city']}, {profile['state']} · kode pos {profile['zip_prefix']}<br>
                  Pelanggan sejak {date_id(profile['first_ts'])}<br>
                  Transaksi terakhir {date_id(profile['last_ts'])} ({int(profile['recency'])} hari lalu)
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.write("")
            m1, m2 = st.columns(2, gap="small")
            m1.metric("Total belanja", money(profile["monetary"]))
            m2.metric("Jumlah pesanan", int(profile["n_orders"]))
            m3, m4 = st.columns(2, gap="small")
            m3.metric("Rata-rata/pesanan", money(profile["avg_order_value"]))
            m4.metric("Rating rata-rata", f"{number(profile['avg_review'], 2)}" if pd.notna(profile["avg_review"]) else "-")
            st.markdown(
                f'<div class="note">Persentil nilai: <b>{percent(profile["value_percentile"])}</b> · '
                f'Kategori favorit: <b>{profile["favorite_category"]}</b> · '
                f'Pembayaran dominan: <b>{profile["favorite_payment"]}</b><br>'
                f'Skor risiko: <b>{number(profile["risk_score"], 1)}/100</b> · '
                f'Pengiriman terlambat: <b>{int(profile["late_orders"]) if pd.notna(profile["late_orders"]) else 0} dari '
                f'{int(profile["delivered_orders"]) if pd.notna(profile["delivered_orders"]) else 0}</b></div>',
                unsafe_allow_html=True,
            )
        with right:
            ui.section("Akumulasi belanja", "Setiap titik adalah satu pesanan.", eyebrow="Riwayat")
            st.plotly_chart(
                charts.customer_spend_timeline(profile_orders),
                width="stretch",
                config={"displayModeBar": False},
            )

        history = pd.DataFrame(
            {
                "Tanggal": profile_orders["purchase_ts"].dt.strftime("%d/%m/%Y"),
                "No. pesanan": profile_orders["order_id"].str[:10].str.upper(),
                "Status": profile_orders["status"].map(STATUS_LABELS).fillna(profile_orders["status"]),
                "Kategori utama": profile_orders["main_category"],
                "Item": profile_orders["n_items"].astype(int),
                "Nilai": profile_orders["payment_value"].map(lambda v: money(v)),
                "Rating": profile_orders["review_score"].map(lambda v: number(v, 1) if pd.notna(v) else "-"),
            }
        )
        ui.table(history, numeric=["Item", "Nilai", "Rating"], max_height=min(360, 50 + 34 * len(history)))
        ui.note(
            "Dataset Olist tidak memuat nama, email, atau nomor telepon. Pelanggan diidentifikasi "
            "lewat customer_unique_id yang sama untuk seluruh pesanan."
        )
