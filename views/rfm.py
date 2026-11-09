"""Halaman segmentasi RFM."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts, ui
from src.analytics import rfm_grid, segment_summary
from src.config import SEGMENT_ACTION, SEGMENT_COLORS, SEGMENT_DESCRIPTION, SEGMENT_ORDER
from src.context import current
from src.formatting import money, money_short, number, percent, short_id


def render() -> None:
    ctx = current()
    customers = ctx["customers"]
    if customers.empty:
        ui.empty_state()

    segments = segment_summary(customers)
    champions = segments[segments["segment"] == "Juara"]
    risky = segments[segments["segment"] == "Berisiko"]
    repeat_count = int(customers["is_repeat"].sum())
    repeat_share = repeat_count / len(customers)

    ui.page_header(
        "Segmentasi",
        "Segmentasi RFM: siapa yang layak dipertahankan",
        "Recency (kebaruan), Frequency (frekuensi), dan Monetary (nilai) dibagi menjadi skor 1-5. "
        "Setiap sel kombinasi dipetakan ke satu segmen dengan tindakan pemasaran yang berbeda.",
        [f"<b>{number(len(customers))}</b> pelanggan", "Skor dihitung dari filter aktif"],
    )

    champion_share = float(champions["porsi_pendapatan"].sum()) if not champions.empty else 0
    risky_share = float(risky["porsi_pendapatan"].sum()) if not risky.empty else 0
    ui.insight(
        f"Hanya <b>{percent(repeat_share)}</b> pelanggan pernah membeli lebih dari sekali. "
        f"Segmen <b>Juara</b> dan <b>Loyal</b> berisi {number(int(champions['pelanggan'].sum()) if not champions.empty else 0)} pelanggan, "
        f"tetapi menyumbang {percent(champion_share)} pendapatan. Sebaliknya, segmen <b>Berisiko</b> "
        f"membawa {percent(risky_share)} pendapatan dan perlu dipulihkan.",
        tone="warning",
        label="Temuan",
    )

    st.write("")
    ui.kpi_row(
        [
            {
                "label": "Juara",
                "value": number(int(champions["pelanggan"].sum()) if not champions.empty else 0),
                "sub": f"{percent(champion_share)} pendapatan",
                "accent": "#0E7C6B",
            },
            {
                "label": "Pelanggan berulang",
                "value": number(repeat_count),
                "sub": f"{percent(repeat_share)} dari seluruh pelanggan",
                "accent": "#3A6EA5",
            },
            {
                "label": "Segmen berisiko",
                "value": number(int(risky["pelanggan"].sum()) if not risky.empty else 0),
                "sub": f"{percent(risky_share)} pendapatan menunggu dipulihkan",
                "accent": "#D97706",
            },
            {
                "label": "Recency median",
                "value": f"{number(customers['recency'].median(), 0)} hari",
                "sub": "sejak transaksi terakhir",
                "accent": "#7A5AF8",
            },
        ]
    )

    st.write("")
    left, right = st.columns([1.05, 1], gap="medium")
    with left:
        with st.container(border=True):
            heading = st.columns([1.4, 1])
            with heading[0]:
                ui.section("Matriks Recency x Frequency", "Warna dan angka menunjukkan ukuran sel.", eyebrow="Peta segmen")
            with heading[1]:
                metric_label = st.selectbox(
                    "Ukuran sel",
                    ["Pelanggan", "Pendapatan"],
                    label_visibility="collapsed",
                    key="rfm_metric",
                )
            metric = "pelanggan" if metric_label == "Pelanggan" else "pendapatan"
            grid = rfm_grid(customers, metric)
            medians = customers.groupby("r_score")["recency"].median()
            r_labels = {int(r): f"R{int(r)} · {int(v)} hr" for r, v in medians.items()}
            st.plotly_chart(
                charts.rfm_heatmap(grid, metric, r_labels),
                width="stretch",
                config={"displayModeBar": False},
            )
            ui.note("R5 = transaksi paling baru, R1 = paling lama. Frequency memakai jumlah pesanan sebenarnya.")
    with right:
        with st.container(border=True):
            ui.section("Pendapatan per segmen", "Luas kotak sebanding dengan pendapatan.", eyebrow="Kontribusi")
            st.plotly_chart(charts.segment_treemap(segments), width="stretch", config={"displayModeBar": False})

    st.write("")
    with st.container(border=True):
        ui.section(
            "Ringkasan seluruh segmen",
            "Ukuran, nilai, dan langkah pemasaran untuk setiap segmen.",
            eyebrow="Tabel keputusan",
        )
        table = segments.copy()
        view = pd.DataFrame(
            {
                "Segmen": table["segment"].astype(str),
                "Pelanggan": table["pelanggan"].astype(int),
                "Porsi pelanggan": table["porsi_pelanggan"].map(lambda v: percent(v)),
                "Pendapatan": table["pendapatan"].map(lambda v: money(v)),
                "Porsi pendapatan": table["porsi_pendapatan"].map(lambda v: percent(v)),
                "Recency median": table["recency"].map(lambda v: f"{number(v, 0)} hari"),
                "Frekuensi": table["frekuensi"].map(lambda v: number(v, 2)),
                "Nilai median": table["nilai"].map(lambda v: money(v)),
                "Prioritas": table["prioritas"],
                "Tindakan": table["tindakan"],
            }
        )
        ui.table(
            view,
            numeric=["Pelanggan", "Porsi pelanggan", "Pendapatan", "Porsi pendapatan", "Recency median", "Frekuensi", "Nilai median"],
            long=["Tindakan"],
            max_height=min(660, 64 + 46 * len(view)),
        )
        ui.note(
            "Pendapatan adalah total nilai pembayaran historis pelanggan pada segmen tersebut, bukan prediksi nilai masa depan."
        )

    st.write("")
    with st.container(border=True):
        ui.section("Detail segmen", "Pilih segmen untuk melihat komposisi dan pelanggan utamanya.", eyebrow="Eksplorasi")
        choice = st.selectbox(
            "Segmen",
            [s for s in SEGMENT_ORDER if s in set(customers["segment"].astype(str))],
            key="segment_detail",
        )
        subset = customers[customers["segment"].astype(str) == choice]
        summary_row = segments[segments["segment"].astype(str) == choice].iloc[0]
        ui.insight(
            f"<b>{choice}</b>: {SEGMENT_DESCRIPTION.get(choice, '')} "
            f"Langkah yang disarankan: {SEGMENT_ACTION.get(choice, ('', ''))[1]}",
            tone="info",
            label="Definisi",
        )
        m1, m2, m3, m4 = st.columns(4, gap="medium")
        m1.metric("Pelanggan", number(len(subset)))
        m2.metric("Pendapatan", money_short(subset["monetary"].sum()))
        m3.metric("Recency median", f"{number(subset['recency'].median(), 0)} hari")
        m4.metric("Nilai belanja median", money(subset["monetary"].median()))

        top = subset.sort_values("monetary", ascending=False).head(10)
        view = pd.DataFrame(
            {
                "ID pelanggan": top["customer_uid"].map(short_id),
                "Kota": top["city"],
                "Negara bagian": top["state"],
                "Pesanan": top["n_orders"].astype(int),
                "Total belanja": top["monetary"].map(lambda v: money(v)),
                "Recency (hari)": top["recency"].astype(int),
                "Risiko": top["risk_band"].astype(str),
            }
        )
        ui.table(
            view,
            numeric=["Pesanan", "Total belanja", "Recency (hari)"],
            max_height=min(420, 50 + 34 * len(view)),
        )

    st.write("")
    with st.expander("Lihat sebaran pelanggan antar segmen"):
        st.plotly_chart(
            charts.segment_scatter(customers),
            width="stretch",
            config={"displayModeBar": False},
        )
        ui.note("Ditampilkan sampel maksimal 4.000 pelanggan agar tetap ringan. Skala nilai belanja logaritmik.")

    with st.expander("Bagaimana skor dan segmen dihitung?"):
        st.markdown(
            """
**Recency** memakai peringkat persentil hari sejak transaksi terakhir; pelanggan paling baru mendapat R5.
**Monetary** memakai peringkat persentil total belanja; belanja terbesar mendapat M5.

**Frequency** tidak memakai kuantil biasa karena 97% pelanggan hanya membeli sekali, sehingga kuantil
akan menumpuk di satu nilai. Pemetaan yang dipakai: 1 pesanan = F1, 2 pesanan = F3, 3 pesanan = F4,
4 pesanan atau lebih = F5. Skor F2 tidak pernah muncul.

Aturan segmen, diperiksa berurutan:

| Segmen | Aturan |
|---|---|
| Juara | R>=4, F>=4, M>=4 |
| Loyal | R>=3, F>=4 |
| Berpotensi Loyal | R>=4, F=3 |
| Pelanggan Baru | R>=4, F=1 |
| Menjanjikan | R=3, F=1 |
| Perlu Perhatian | R=3, F>=3 |
| Tidak Boleh Hilang | R<=2, F>=3, M>=3 |
| Berisiko | R<=2, M>=4 |
| Tidur | R<=2, M=3 |
| Hilang | sisanya |

Segmentasi dihitung ulang setiap filter berubah, sehingga jumlah pelanggan dapat berbeda dari
tampilan tanpa filter.
            """
        )
