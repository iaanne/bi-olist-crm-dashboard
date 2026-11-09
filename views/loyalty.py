"""Halaman loyalitas dan strategi pemasaran."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts, ui
from src.analytics import (
    category_repeat,
    cohort_repeat,
    kpi_summary,
    loyalty_kpis,
    repeat_drivers,
    segment_summary,
)
from src.context import current
from src.formatting import money, money_short, number, percent

PLAYBOOK = {
    "Juara": ("Email + komunitas", "Repeat rate, referral"),
    "Loyal": ("Email + bundling", "AOV, jumlah kategori per pesanan"),
    "Berpotensi Loyal": ("Email otomatis", "Konversi pembelian ketiga"),
    "Pelanggan Baru": ("Email onboarding + WhatsApp", "Repeat 90 hari"),
    "Menjanjikan": ("Email + retargeting", "Konversi pembelian kedua"),
    "Perlu Perhatian": ("WhatsApp personal", "Reaktivasi 30 hari"),
    "Tidak Boleh Hilang": ("Kontak langsung + voucher", "Pendapatan dipulihkan"),
    "Berisiko": ("Retargeting + voucher bertingkat", "Reaktivasi 60 hari"),
    "Tidur": ("Email massal", "Tingkat reaktivasi"),
    "Hilang": ("Kanal berbiaya rendah", "Biaya per reaktivasi"),
}


def _driver_block(frame: pd.DataFrame, title: str, subtitle: str) -> None:
    with st.container(border=True):
        ui.section(title, subtitle, eyebrow="Pemicu")
        st.plotly_chart(charts.driver_bar(frame), width="stretch", config={"displayModeBar": False})


def render() -> None:
    ctx = current()
    orders, customers = ctx["orders"], ctx["customers"]
    if orders.empty or customers.empty:
        ui.empty_state()

    snapshot = ctx["snapshot"]
    lk = loyalty_kpis(orders, customers, snapshot)
    drivers = repeat_drivers(orders, snapshot)
    cohort = cohort_repeat(orders, snapshot)
    categories = category_repeat(orders, snapshot)
    segments = segment_summary(customers)
    k = kpi_summary(orders, customers)

    ui.page_header(
        "Loyalitas & strategi",
        "Bagaimana meningkatkan loyalitas dan strategi apa yang dipakai",
        "Ukur retensi dengan pembelian ulang, cari pemicu yang bisa dikendalikan perusahaan, "
        "lalu terjemahkan temuan menjadi rencana aksi per segmen.",
        [f"<b>{percent(lk['repeat_rate'])}</b> repeat rate", "Jendela ukur 90 hari"],
    )

    delivery = drivers.get("Lama pengiriman")
    fast_rate = slow_rate = None
    if delivery is not None and not delivery.empty:
        fast = delivery[delivery["kategori"].astype(str) == "0-7 hari"]
        slow = delivery[delivery["kategori"].astype(str) == ">30 hari"]
        fast_rate = float(fast["repeat_90d"].iloc[0]) if not fast.empty else None
        slow_rate = float(slow["repeat_90d"].iloc[0]) if not slow.empty else None

    ui.insight(
        f"Repeat rate hanya <b>{percent(lk['repeat_rate'])}</b>, dan <b>{percent(lk['repeat_90d'])}</b> pelanggan "
        f"membeli lagi dalam 90 hari. Median jeda antar transaksi pelanggan berulang adalah "
        f"<b>{number(lk['median_interval'], 0)} hari</b>, jadi jendela pembelian kedua yang realistis adalah 30-45 hari pertama.",
        tone="info",
        label="Jendela loyalitas",
    )
    if fast_rate and slow_rate:
        ui.insight(
            f"Pengalaman pesanan pertama berkaitan dengan pembelian ulang: pengiriman 0-7 hari menghasilkan "
            f"repeat 90 hari <b>{percent(fast_rate, 2)}</b>, sedangkan pengiriman di atas 30 hari hanya "
            f"<b>{percent(slow_rate, 2)}</b> ({number(fast_rate / slow_rate, 1)}x). "
            "Selisih absolutnya kecil, tetapi arahnya konsisten dan bisa dikendalikan operasional.",
            tone="warning",
            label="Pemicu",
        )

    st.write("")
    ui.kpi_row(
        [
            {"label": "Repeat rate", "value": percent(lk["repeat_rate"]), "sub": f"{number(lk['loyal_customers'])} pelanggan berulang", "accent": "#0E7C6B"},
            {"label": "Beli ulang <= 90 hari", "value": percent(lk["repeat_90d"]), "sub": f"dari {number(lk['repeat_90d_n'])} pelanggan teramati", "accent": "#3A6EA5"},
            {"label": "Median jeda transaksi", "value": f"{number(lk['median_interval'], 0)} hari", "sub": "pelanggan berulang"},
            {"label": "Pesanan per pelanggan", "value": number(lk["avg_orders"], 2), "sub": f"{percent(k['repeat_revenue_share'])} pendapatan dari pelanggan berulang", "accent": "#7A5AF8"},
        ]
    )

    st.write("")
    left, right = st.columns([1.1, 1], gap="medium")
    with left:
        with st.container(border=True):
            ui.section(
                "Pembelian ulang menurut kohort",
                "Pelanggan dikelompokkan menurut kuartal transaksi pertama.",
                eyebrow="Retensi",
            )
            st.plotly_chart(charts.cohort_line(cohort), width="stretch", config={"displayModeBar": False})
            ui.note(
                "Kuartal 2018Q2 hanya memuat pelanggan yang bertransaksi sampai 6 Juni 2018, yaitu batas "
                "agar setiap pelanggan punya waktu 90 hari untuk diamati."
            )
    with right:
        with st.container(border=True):
            ui.section(
                "Kategori dengan pembelian ulang tertinggi",
                "Minimal 250 pelanggan per kategori, 90 hari pengamatan.",
                eyebrow="Kategori",
            )
            if categories.empty:
                st.info("Data kategori tidak cukup pada filter ini.")
            else:
                top_categories = categories.head(10).rename(columns={"main_category": "kategori"})
                st.plotly_chart(
                    charts.driver_bar(top_categories), width="stretch", config={"displayModeBar": False}
                )
                ui.note("Kategori dipilih dari item bernilai terbesar pada pesanan pertama.")

    st.write("")
    ui.section(
        "Pemicu pembelian ulang",
        "Setiap grafik membandingkan tingkat pembelian ulang 90 hari menurut karakteristik pesanan pertama. "
        "Hanya pelanggan yang punya cukup waktu pengamatan yang dihitung.",
        eyebrow="Analisis",
    )
    if not drivers:
        st.info("Tidak cukup data untuk analisis pemicu pada filter ini.")
    else:
        items = [(title, frame) for title, frame in drivers.items() if not frame.empty]
        if not items:
            st.info("Tidak ada pemicu dengan cukup pengamatan pada filter ini.")
        for start in range(0, len(items), 3):
            cols = st.columns(3, gap="medium")
            for col, (title, frame) in zip(cols, items[start : start + 3]):
                with col:
                    _driver_block(frame, title, f"{number(frame['pelanggan'].sum())} pelanggan")

    st.write("")
    with st.container(border=True):
        ui.section(
            "Buku strategi per segmen",
            "Prioritas, tindakan, kanal, dan indikator keberhasilan. Angka mengikuti filter aktif.",
            eyebrow="Rencana",
        )
        table = segments.copy()
        table["kanal"] = table["segment"].map(lambda s: PLAYBOOK.get(str(s), ("", ""))[0])
        table["kpi"] = table["segment"].map(lambda s: PLAYBOOK.get(str(s), ("", ""))[1])
        view = pd.DataFrame(
            {
                "Segmen": table["segment"].astype(str),
                "Pelanggan": table["pelanggan"].astype(int),
                "Pendapatan": table["pendapatan"].map(lambda v: money(v)),
                "Prioritas": table["prioritas"],
                "Tindakan": table["tindakan"],
                "Kanal": table["kanal"],
                "KPI": table["kpi"],
            }
        )
        ui.table(
            view,
            numeric=["Pelanggan", "Pendapatan"],
            wrap=["Tindakan", "Kanal", "KPI"],
            max_height=440,
        )
        st.download_button(
            "Unduh buku strategi (CSV)",
            data=view.to_csv(index=False).encode("utf-8"),
            file_name="strategi_segmen.csv",
            mime="text/csv",
            icon=":material/download:",
        )
        ui.note(
            "Kanal pemasaran adalah rekomendasi praktik, bukan hasil analisis dataset. Dataset Olist tidak "
            "mencatat kanal akuisisi atau riwayat kampanye."
        )

    st.write("")
    ui.section("Tiga prioritas 90 hari", "Dipilih dari kombinasi ukuran pendapatan dan tingkat risiko.", eyebrow="Eksekusi")
    risky = segments[segments["segment"].astype(str) == "Berisiko"]
    new = segments[segments["segment"].astype(str) == "Pelanggan Baru"]
    champions = segments[segments["segment"].astype(str) == "Juara"]

    cards = [
        (
            "Pulihkan pelanggan bernilai",
            f"{number(int(risky['pelanggan'].sum()) if not risky.empty else 0)} pelanggan",
            f"{percent(float(risky['porsi_pendapatan'].sum()) if not risky.empty else 0)} pendapatan historis",
            "Kampanye win-back bertingkat: voucher kecil untuk nilai menengah, kontak personal untuk nilai tertinggi. "
            "Ukur reaktivasi 60 hari dan pendapatan yang kembali.",
            "#D97706",
        ),
        (
            "Kunci pembelian kedua",
            f"{number(int(new['pelanggan'].sum()) if not new.empty else 0)} pelanggan baru",
            f"{percent(float(new['porsi_pendapatan'].sum()) if not new.empty else 0)} pendapatan",
            "Onboarding 30 hari: rekomendasi kategori pelengkap, pengingat hari ke-14 dan ke-30, "
            "serta insentif pembelian kedua yang kedaluwarsa.",
            "#3A6EA5",
        ),
        (
            "Lindungi pelanggan juara",
            f"{number(int(champions['pelanggan'].sum()) if not champions.empty else 0)} pelanggan",
            f"{percent(float(champions['porsi_pendapatan'].sum()) if not champions.empty else 0)} pendapatan",
            "Program loyalitas berjenjang dengan akses awal, layanan prioritas, dan referral. "
            "Jaga pengalaman pengiriman karena kelompok ini paling sensitif terhadap keterlambatan.",
            "#0E7C6B",
        ),
    ]
    cols = st.columns(3, gap="medium")
    for col, (title, audience, value, action, color) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="kpi" style="--kpi-accent:{color};min-height:210px">
                  <div class="kpi-label"><span class="kpi-dot"></span>{title}</div>
                  <div class="kpi-value" style="font-size:1.15rem">{audience}</div>
                  <div class="kpi-sub" style="margin-bottom:8px">{value}</div>
                  <div style="font-size:.76rem;color:#667085;line-height:1.5">{action}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.write("")
    with st.container(border=True):
        ui.section("Urutan eksekusi", "Empat langkah dengan dependensi yang jelas.", eyebrow="Roadmap")
        steps = [
            ("Minggu 1-2", "Bersihkan dan siapkan daftar sasaran", "Ekspor segmen Berisiko dan pelanggan baru, lengkapi kontak, dan uji ukuran sampel."),
            ("Minggu 3-6", "Jalankan kampanye pembelian kedua", "Fokus pada pelanggan baru berumur 14-45 hari dengan kategori pelengkap."),
            ("Minggu 5-10", "Aktifkan win-back bertingkat", "Mulai dari nilai tertinggi, ukur respons per tier, hentikan kanal yang mahal bila respons rendah."),
            ("Minggu 11-12", "Evaluasi dan kunci pembelajaran", "Bandingkan repeat 90 hari dan pendapatan per sasaran dengan kelompok kontrol."),
        ]
        cols = st.columns(4, gap="medium")
        for i, (period, title, desc) in enumerate(steps):
            with cols[i]:
                st.markdown(
                    f'<div style="font-size:.65rem;font-weight:700;color:#0E7C6B;letter-spacing:.08em">{period}</div>'
                    f'<div style="font-weight:700;color:#0B1F2A;font-size:.86rem;margin:3px 0 4px 0">{title}</div>'
                    f'<div style="color:#667085;font-size:.75rem;line-height:1.45">{desc}</div>',
                    unsafe_allow_html=True,
                )
