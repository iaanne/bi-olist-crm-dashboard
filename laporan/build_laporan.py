"""Membangun laporan PDF dashboard CRM Olist.

Jalankan dengan: python3 laporan/build_laporan.py
Keluaran:        laporan/Laporan_CRM_Olist.pdf

Angka dihitung dari modul src yang sama dengan dashboard agar konsisten.
"""

from __future__ import annotations

import base64
import io
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.analytics import (
    cohort_repeat,
    city_summary,
    kpi_summary,
    loyalty_kpis,
    monthly_series,
    pareto_curve,
    payment_summary,
    region_summary,
    repeat_drivers,
    risk_summary,
    segment_summary,
    state_summary,
)
from src.config import (
    BORDER,
    CHART_SEQUENCE,
    GRID,
    INK,
    MUTED,
    PAYMENT_LABELS,
    PRIMARY,
    RED,
    RISK_COLORS,
    SEGMENT_COLORS,
)
from src.context import build_context
from src.data import load_orders, snapshot_date, valid_orders
from src.formatting import date_id, money, money_short, number, percent

OUT_DIR = BASE / "laporan"
PDF_PATH = OUT_DIR / "Laporan_CRM_Olist.pdf"

ACCENT = "#D97706"
BLUE = "#3A6EA5"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.edgecolor": BORDER,
        "axes.labelcolor": MUTED,
        "axes.titlecolor": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)


# ---------------------------------------------------------------------------
# Gambar
# ---------------------------------------------------------------------------
def _save(fig) -> str:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _clean(ax, y_grid: bool = True) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y" if y_grid else "x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def fig_monthly(monthly: pd.DataFrame) -> str:
    data = monthly[monthly["Pesanan"] >= 30].copy()
    labels = [f"{d.month:02d}/{str(d.year)[2:]}" for d in data["month"]]
    fig, ax = plt.subplots(figsize=(7.2, 2.9))
    ax.bar(labels, data["Pelanggan baru"], color=PRIMARY, label="Pelanggan baru", width=0.7)
    ax.bar(
        labels,
        data["Pelanggan berulang"],
        bottom=data["Pelanggan baru"],
        color=ACCENT,
        label="Pelanggan berulang",
        width=0.7,
    )
    ax.set_ylabel("Pendapatan (R$)")
    ax.set_ylim(0, float(data["Pendapatan"].max()) * 1.24)
    ax.set_title("Pendapatan bulanan menurut jenis pelanggan", loc="left", fontweight="bold")
    step = max(1, round(len(labels) / 12))
    ax.set_xticks(range(0, len(labels), step))
    ax.set_xticklabels(labels[::step], rotation=45, ha="right", fontsize=7.5)
    ax.legend(frameon=False, ncol=2, loc="upper left")
    _clean(ax)
    return _save(fig)


def fig_pareto(curve: pd.DataFrame) -> str:
    step = max(1, len(curve) // 400)
    data = curve.iloc[::step]
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    ax.plot(data["rank_pct"] * 100, data["cumulative_share"] * 100, color=PRIMARY, linewidth=2.2)
    ax.fill_between(data["rank_pct"] * 100, data["cumulative_share"] * 100, color=PRIMARY, alpha=0.10)
    ax.axvline(20, color=RED, linewidth=1, linestyle="--")
    share20 = float(curve.iloc[int(len(curve) * 0.2) - 1]["cumulative_share"]) * 100
    ax.annotate(
        f"20% teratas\n= {share20:.1f}% pendapatan",
        xy=(20, share20),
        xytext=(34, 30),
        fontsize=8,
        color=RED,
        arrowprops=dict(arrowstyle="->", color=RED, lw=0.8),
    )
    ax.set_xlabel("Persentil pelanggan")
    ax.set_ylabel("Pendapatan kumulatif (%)")
    ax.set_title("Kurva Pareto", loc="left", fontweight="bold")
    _clean(ax)
    return _save(fig)


def fig_segments(segments: pd.DataFrame) -> str:
    data = segments.sort_values("pendapatan")
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    colors = [SEGMENT_COLORS.get(str(s), PRIMARY) for s in data["segment"]]
    ax.barh(data["segment"].astype(str), data["pendapatan"] / 1_000_000, color=colors)
    for y, value in enumerate(data["pendapatan"] / 1_000_000):
        ax.text(value + 0.02, y, f"{value:.2f}", va="center", fontsize=7.5, color=MUTED)
    ax.set_xlabel("Pendapatan (juta R$)")
    ax.set_title("Pendapatan menurut segmen RFM", loc="left", fontweight="bold")
    _clean(ax, y_grid=False)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    return _save(fig)


def fig_regions(regions: pd.DataFrame) -> str:
    data = regions.sort_values("porsi", ascending=False)
    fig, ax = plt.subplots(figsize=(7.2, 2.3))
    ax.bar(data["wilayah"], data["porsi"] * 100, color=BLUE, width=0.6)
    for x, value in enumerate(data["porsi"] * 100):
        ax.text(x, value + 0.8, f"{value:.1f}%", ha="center", fontsize=8, color=MUTED)
    ax.set_ylabel("Porsi pendapatan (%)")
    ax.set_title("Pendapatan menurut wilayah Brazil", loc="left", fontweight="bold")
    _clean(ax)
    return _save(fig)


def fig_spend(customers: pd.DataFrame) -> str:
    spend = customers["monetary"]
    bins = np.logspace(np.log10(max(spend.min(), 1)), np.log10(spend.max()), 34)
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    ax.hist(spend, bins=bins, color=PRIMARY, alpha=0.9)
    ax.set_xscale("log")
    ax.set_xlabel("Belanja per pelanggan (R$, skala log)")
    ax.set_ylabel("Jumlah pelanggan")
    median = spend.median()
    ax.axvline(median, color=RED, linewidth=1.2, linestyle="--")
    ax.annotate(
        f"median {money(median)}",
        xy=(median, ax.get_ylim()[1] * 0.7),
        xytext=(median * 3, ax.get_ylim()[1] * 0.78),
        fontsize=8,
        color=RED,
    )
    ax.set_title("Sebaran nilai belanja", loc="left", fontweight="bold")
    _clean(ax)
    return _save(fig)


def fig_risk(risk: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    colors = [RISK_COLORS.get(str(b), MUTED) for b in risk["risk_band"]]
    ax.bar(risk["risk_band"].astype(str), risk["pelanggan"], color=colors)
    for x, value in enumerate(risk["pelanggan"]):
        ax.text(x, value, number(value), ha="center", va="bottom", fontsize=8, color=MUTED)
    ax.set_ylabel("Jumlah pelanggan")
    ax.set_title("Sebaran band risiko", loc="left", fontweight="bold")
    _clean(ax)
    return _save(fig)


def fig_cohort(cohort: pd.DataFrame) -> str:
    labels = [f"Q{s[-1]} {s[:4][2:]}" for s in cohort["cohort"]]
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    ax.plot(labels, cohort["repeat_90d"] * 100, marker="o", color=PRIMARY, linewidth=2)
    ax.set_ylabel("Pembelian ulang <=90 hari (%)")
    ax.set_xlabel("Kuartal transaksi pertama")
    ax.set_title("Retensi per kohort", loc="left", fontweight="bold")
    ax.tick_params(axis="x", labelsize=7.5)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    _clean(ax)
    return _save(fig)


def fig_delivery(drivers: dict[str, pd.DataFrame]) -> str:
    frame = drivers.get("Lama pengiriman")
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    if frame is not None and not frame.empty:
        ax.bar(frame["kategori"].astype(str), frame["repeat_90d"] * 100, color=BLUE)
        for x, value in enumerate(frame["repeat_90d"] * 100):
            ax.text(x, value, f"{value:.1f}", ha="center", va="bottom", fontsize=8, color=MUTED)
    ax.set_ylabel("Pembelian ulang <=90 hari (%)")
    ax.set_title("Repeat menurut lama pengiriman", loc="left", fontweight="bold")
    _clean(ax)
    return _save(fig)


def fig_rfm(grid: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(3.6, 2.8))
    values = grid.values.astype(float)
    im = ax.imshow(values, cmap="BuGn", aspect="auto")
    limit = values.max() if values.max() else 1
    ax.set_xticks(range(len(grid.columns)))
    ax.set_xticklabels(grid.columns, rotation=30, ha="right", fontsize=7.5)
    ax.set_yticks(range(len(grid.index)))
    ax.set_yticklabels([f"R{int(i)}" for i in grid.index], fontsize=7.5)
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            if values[i, j] > 0:
                dark = values[i, j] / limit > 0.55
                ax.text(
                    j,
                    i,
                    number(values[i, j]),
                    ha="center",
                    va="center",
                    fontsize=6.5,
                    color="white" if dark else INK,
                )
    ax.set_title("Matriks Recency x Frequency", loc="left", fontweight="bold")
    ax.grid(False)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    fig.colorbar(im, ax=ax, shrink=0.8).ax.tick_params(labelsize=6.5)
    return _save(fig)


# ---------------------------------------------------------------------------
# Tabel HTML
# ---------------------------------------------------------------------------
def table(headers: list[str], rows: list[list[str]], numeric: list[int] | None = None) -> str:
    numeric = numeric or []
    head = "".join(
        f'<th class="{"num" if i in numeric else ""}">{h}</th>' for i, h in enumerate(headers)
    )
    body = []
    for row in rows:
        cells = "".join(
            f'<td class="{"num" if i in numeric else ""}">{cell}</td>' for i, cell in enumerate(row)
        )
        body.append(f"<tr>{cells}</tr>")
    return f'<table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table>'


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def collect() -> dict:
    valid = valid_orders(load_orders())
    lo = valid["purchase_ts"].min().date()
    hi = valid["purchase_ts"].max().date()
    ctx = build_context(lo, hi, [])
    orders, customers = ctx["orders"], ctx["customers"]
    snapshot = ctx["snapshot"]

    return {
        "orders": orders,
        "customers": customers,
        "snapshot": snapshot,
        "period": (valid["purchase_ts"].min(), valid["purchase_ts"].max()),
        "k": kpi_summary(orders, customers),
        "segments": segment_summary(customers),
        "states": state_summary(orders, customers),
        "regions": region_summary(state_summary(orders, customers)),
        "cities": city_summary(orders, top=10),
        "payments": payment_summary(orders),
        "risk": risk_summary(customers),
        "lk": loyalty_kpis(orders, customers, snapshot),
        "cohort": cohort_repeat(orders, snapshot),
        "drivers": repeat_drivers(orders, snapshot),
        "curve": pareto_curve(customers),
        "monthly": monthly_series(orders),
        "top_customers": customers.sort_values("monetary", ascending=False).head(10),
    }


def build_html(d: dict) -> str:
    k = d["k"]
    segments = d["segments"]
    states = d["states"]
    regions = d["regions"]
    cities = d["cities"]
    payments = d["payments"]
    risk = d["risk"]
    lk = d["lk"]
    curve = d["curve"]
    monthly = d["monthly"]
    customers = d["customers"]

    share20 = float(curve.iloc[int(len(curve) * 0.2) - 1]["cumulative_share"])
    high_risk = risk[risk["risk_band"].isin(["Tinggi", "Kritis"])]
    high_risk_n = int(high_risk["pelanggan"].sum())
    high_risk_rev = float(high_risk["pendapatan"].sum())
    repeat_rev = k["repeat_revenue_share"]

    from src.analytics import rfm_grid

    rfm_counts = rfm_grid(customers, "pelanggan")

    # KPI grid
    kpis = [
        ("Pendapatan", money_short(k["revenue"]), "seluruh pesanan sah"),
        ("Pesanan", number(k["orders"]), "status cancel dan unavailable dikeluarkan"),
        ("Pelanggan unik", number(k["customers"]), "kunci customer_unique_id"),
        ("Nilai pesanan rata-rata", money(k["aov"]), "average order value"),
        ("Repeat rate", percent(k["repeat_rate"]), "pelanggan dengan lebih dari satu pesanan"),
        ("Rating rata-rata", number(k["avg_review"], 2) + " / 5", "ulasan pesanan"),
        ("Tepat waktu", percent(k["on_time_rate"]), "dari pesanan terkirim"),
        ("Pelanggan bernilai tinggi", number(k["high_value_customers"]), f"{percent(k['high_value_share'])} pendapatan"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-sub">{sub}</div></div>'
        for label, value, sub in kpis
    )

    # 3.1 pelanggan terbaik
    top = d["top_customers"]
    top_rows = [
        [
            str(r["customer_uid"])[:10].upper(),
            r["city"],
            str(r["state"]),
            number(int(r["n_orders"])),
            money(r["monetary"]),
            money(r["avg_order_value"]),
            "Ya" if r["is_repeat"] else "Tidak",
            str(r["segment"]),
        ]
        for _, r in top.iterrows()
    ]
    seg_rows = [
        [
            str(r["segment"]),
            number(r["pelanggan"]),
            percent(r["porsi_pelanggan"]),
            money(r["pendapatan"]),
            percent(r["porsi_pendapatan"]),
            r["tindakan"],
        ]
        for _, r in segments.iterrows()
    ]

    state_rows = [
        [
            str(r["negara_bagian"]),
            str(r["state"]),
            str(r["wilayah"]),
            number(r["pelanggan"]),
            money(r["pendapatan"]),
            percent(r["porsi_pendapatan"]),
            money(r["nilai_pelanggan"]),
            percent(r["repeat_rate"]),
        ]
        for _, r in states.head(10).iterrows()
    ]
    city_rows = [
        [r["city"], str(r["state"]), number(r["pelanggan"]), money(r["pendapatan"]), money(r["aov"])]
        for _, r in cities.iterrows()
    ]

    tier_counts = customers["value_tier"].value_counts()
    tier_rows = [
        [tier, number(int(tier_counts.get(tier, 0))), percent(tier_counts.get(tier, 0) / len(customers))]
        for tier in ["VIP", "Utama", "Potensial", "Reguler"]
    ]

    risk_rows = [
        [
            str(r["risk_band"]),
            number(r["pelanggan"]),
            percent(r["porsi_pelanggan"]),
            money(r["pendapatan"]),
            percent(r["porsi_pendapatan"]),
            number(r["recency"]) + " hari",
        ]
        for _, r in risk.iterrows()
    ]

    pay_rows = [
        [r["label"], number(r["pesanan"]), money(r["pendapatan"]), percent(r["porsi"])]
        for _, r in payments.iterrows()
    ]

    playbook_rows = []
    for _, r in segments.iterrows():
        playbook_rows.append(
            [
                str(r["segment"]),
                r["prioritas"],
                r["tindakan"],
                number(r["pelanggan"]),
                money(r["pendapatan"]),
            ]
        )

    figs = {
        "monthly": fig_monthly(monthly),
        "pareto": fig_pareto(curve),
        "segments": fig_segments(segments),
        "regions": fig_regions(regions),
        "spend": fig_spend(customers),
        "risk": fig_risk(risk),
        "cohort": fig_cohort(d["cohort"]),
        "delivery": fig_delivery(d["drivers"]),
        "rfm": fig_rfm(rfm_counts),
    }

    def img(name: str) -> str:
        return f'<img src="data:image/png;base64,{figs[name]}" />'

    first_ts, last_ts = d["period"]

    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8" />
<title>Laporan CRM Olist</title>
<style>
{_CSS}
</style>
</head>
<body>

<section class="cover">
  <div class="cover-eyebrow">Tugas Business Intelligence</div>
  <h1>Dashboard CRM Olist</h1>
  <p class="cover-sub">Analisis pelanggan pada Olist Brazilian E-Commerce Public Dataset</p>
  <div class="cover-meta">
    <div><span>Periode data</span><b>{date_id(first_ts)} - {date_id(last_ts)}</b></div>
    <div><span>Tanggal analisis</span><b>{date_id(d['snapshot'])}</b></div>
    <div><span>Pesanan sah</span><b>{number(k['orders'])}</b></div>
    <div><span>Pelanggan unik</span><b>{number(k['customers'])}</b></div>
  </div>
</section>

<h2>1. Pendahuluan</h2>
<p>Olist adalah salah satu pasar daring terbesar di Brazil. Dataset publiknya memuat
riwayat pesanan dari 2016 sampai 2018, lengkap dengan data pelanggan, produk,
pembayaran, ulasan, dan pengiriman. Laporan ini merangkum hasil dashboard CRM yang
dibangun untuk membaca perilaku pelanggan pada data tersebut.</p>

<p>Tujuan analisis adalah menjawab enam pertanyaan bisnis:</p>
<ol class="q">
  <li>Siapa pelanggan terbaik dan berapa nilai transaksinya?</li>
  <li>Dari mana pelanggan berasal?</li>
  <li>Berapa nilai transaksi setiap pelanggan?</li>
  <li>Pelanggan mana yang berpotensi tidak aktif?</li>
  <li>Bagaimana meningkatkan loyalitas pelanggan?</li>
  <li>Strategi pemasaran apa yang perlu diterapkan?</li>
</ol>

<h3>Sumber data</h3>
<p>Analisis memakai sembilan berkas CSV Olist yang saling terhubung, mencakup
{number(99441)} pesanan. Setelah pesanan berstatus <em>canceled</em> dan
<em>unavailable</em> dikeluarkan, tersisa <b>{number(k['orders'])}</b> pesanan sah dan
<b>{number(k['customers'])}</b> pelanggan unik.</p>

<h3>Metode ringkas</h3>
<ul>
  <li><b>Kunci pelanggan.</b> Analisis memakai <code>customer_unique_id</code>, bukan
  <code>customer_id</code>, karena satu pelanggan dapat muncul sebagai beberapa
  <code>customer_id</code>.</li>
  <li><b>Segmentasi RFM.</b> Recency dan Monetary dibagi menjadi skor 1 sampai 5
  memakai kuantil. Frequency memakai pemetaan eksplisit karena sekitar 97% pelanggan
  hanya membeli sekali. Kombinasi skor dipetakan ke sepuluh segmen.</li>
  <li><b>Skor risiko.</b> Skor 0 sampai 100 menggabungkan recency (55%), frequency
  (15%), kepuasan (15%), dan keterlambatan pengiriman (15%). Band: Rendah sampai 35,
  Sedang sampai 55, Tinggi sampai 75, Kritis di atas 75.</li>
  <li><b>Tanggal analisis.</b> Tetap pada {date_id(d['snapshot'])} agar recency dapat
  dibandingkan.</li>
</ul>
<p class="note">Semua nilai dalam Real Brazil (R$), disajikan dengan pemisah angka
gaya Indonesia.</p>

<h2>2. Ringkasan KPI</h2>
<div class="kpi-grid">{kpi_html}</div>

<h3>Pendapatan bulanan</h3>
{img('monthly')}
<p class="note">Bulan dengan kurang dari 30 pesanan disembunyikan, sehingga lonjakan
awal 2016 yang tipis tidak mengacaukan grafik.</p>

<h3>Komposisi pembayaran</h3>
{table(['Metode', 'Pesanan', 'Pendapatan', 'Porsi'], pay_rows, numeric=[1, 2, 3])}

<h2>3. Jawaban pertanyaan bisnis</h2>

<h3>3.1 Siapa pelanggan terbaik dan berapa nilai transaksinya?</h3>
<p>Pelanggan bernilai terbesar mencapai <b>{money(float(d['top_customers'].iloc[0]['monetary']))}</b>
dari {int(d['top_customers'].iloc[0]['n_orders'])} pesanan. Namun belanja pelanggan
sangat miring: 20% pelanggan teratas menyumbang <b>{percent(share20)}</b> pendapatan,
sedangkan rata-rata belanja seluruh pelanggan hanya <b>{money(k['avg_spend'])}</b>
dengan median <b>{money(k['median_spend'])}</b>.</p>
<div class="two">
  <div>{img('pareto')}</div>
  <div>{img('spend')}</div>
</div>
<p><b>Sepuluh pelanggan dengan nilai belanja terbesar</b></p>
{table(['ID', 'Kota', 'Negara bagian', 'Pesanan', 'Belanja', 'Nilai/pesanan', 'Berulang', 'Segmen'], top_rows, numeric=[3, 4, 5])}

<h3>3.2 Dari mana pelanggan berasal?</h3>
<p>Pelanggan terkonsentrasi di wilayah tenggara. {states.iloc[0]['negara_bagian']}
menampung {percent(states.iloc[0]['pelanggan'] / k['customers'])} pelanggan dan
<b>{percent(states.iloc[0]['porsi_pendapatan'])}</b> pendapatan. Lima negara bagian
teratas secara bersama menyumbang
<b>{percent(states.head(5)['pendapatan'].sum() / k['revenue'])}</b> pendapatan.</p>
{img('regions')}
{table(['Negara bagian', 'Kode', 'Wilayah', 'Pelanggan', 'Pendapatan', 'Porsi', 'Nilai/pelanggan', 'Repeat rate'], state_rows, numeric=[3, 4, 5, 6, 7])}
<p><b>Kota dengan pendapatan terbesar</b></p>
{table(['Kota', 'Negara bagian', 'Pelanggan', 'Pendapatan', 'Nilai/pesanan'], city_rows, numeric=[2, 3, 4])}

<h3>3.3 Berapa nilai transaksi setiap pelanggan?</h3>
<p>Median belanja per pelanggan <b>{money(k['median_spend'])}</b>, sementara rata-rata
<b>{money(k['avg_spend'])}</b>. Jarak keduanya menunjukkan adanya sejumlah kecil
pelanggan bernilai sangat tinggi. Sebaran nilai belanja membentuk ekor panjang ke kanan.</p>
{table(['Tier nilai', 'Pelanggan', 'Porsi'], tier_rows, numeric=[1, 2])}
<p class="note">Tier dibentuk dari persentil belanja: VIP (1% teratas), Utama (10%),
Potensial (20%), dan Reguler sisanya.</p>

<h3>3.4 Pelanggan mana yang berpotensi tidak aktif?</h3>
<p>Sebanyak <b>{number(high_risk_n)}</b> pelanggan berada di band risiko tinggi atau
kritis, membawa <b>{money_short(high_risk_rev)}</b> pendapatan historis
(<b>{percent(high_risk_rev / k['revenue'])}</b> dari total). Kelompok ini prioritas
untuk kampanye reaktivasi.</p>
<div class="two">
  <div>{img('risk')}</div>
  <div>{img('rfm')}</div>
</div>
{table(['Band risiko', 'Pelanggan', 'Porsi pelanggan', 'Pendapatan', 'Porsi pendapatan', 'Recency median'], risk_rows, numeric=[1, 2, 3, 4, 5])}

<h3>3.5 Bagaimana meningkatkan loyalitas pelanggan?</h3>
<p>Repeat rate hanya <b>{percent(lk['repeat_rate'])}</b>, dan pelanggan berulang
menyumbang <b>{percent(repeat_rev)}</b> pendapatan. Artinya pertumbuhan saat ini lebih
bergantung pada akuisisi daripada retensi. Median jeda antar transaksi pelanggan
berulang sekitar <b>{number(lk['median_interval'])} hari</b>. Pembelian ulang dalam 90
hari, yang dihitung hanya pada pelanggan dengan masa pengamatan penuh, sebesar
<b>{percent(lk['repeat_90d'])}</b>.</p>
<div class="two">
  <div>{img('cohort')}</div>
  <div>{img('delivery')}</div>
</div>
<p class="note">Hubungan pengiriman cepat dengan pembelian ulang bersifat asosiatif,
bukan sebab akibat.</p>

<h3>3.6 Strategi pemasaran apa yang perlu diterapkan?</h3>
<p>Setiap segmen RFM dipetakan ke prioritas dan tindakan. Tabel berikut menjadi buku
strategi per segmen, diurutkan menurut pendapatan yang dibawa.</p>
{img('segments')}
{table(['Segmen', 'Prioritas', 'Tindakan', 'Pelanggan', 'Pendapatan'], playbook_rows, numeric=[3, 4])}
<p class="note">Kanal dan taktik bersifat praktik umum, bukan hasil pengujian pada
dataset, karena data tidak memuat riwayat kampanye.</p>

<h2>4. Kesimpulan</h2>
<ol class="concl">
  <li>Pendapatan historis mencapai <b>{money_short(k['revenue'])}</b> dari
  {number(k['orders'])} pesanan sah dan {number(k['customers'])} pelanggan, dengan
  nilai pesanan rata-rata {money(k['aov'])}.</li>
  <li>Pendapatan sangat terkonsentrasi: 20% pelanggan teratas menyumbang
  {percent(share20)}. Menjaga kelompok ini lebih berharga daripada mengejar
  pertumbuhan pelanggan secara merata.</li>
  <li>Repeat rate hanya {percent(k['repeat_rate'])} dan menyumbang {percent(repeat_rev)}
  pendapatan. Retensi adalah celah terbesar, bukan akuisisi.</li>
  <li>Sebanyak {number(high_risk_n)} pelanggan berisiko tinggi atau kritis, dengan
  {money_short(high_risk_rev)} pendapatan yang perlu diselamatkan.</li>
  <li>Wilayah tenggara, terutama {states.iloc[0]['negara_bagian']}, mendominasi
  pendapatan, sehingga ekspansi ke wilayah lain perlu memperhitungkan biaya logistik.</li>
  <li>Urutan tindakan yang disarankan: selamatkan pelanggan bernilai tinggi yang mulai
  hilang, dorong pembelian kedua pada pelanggan baru, lalu kembangkan program loyalitas
  berjenjang untuk pelanggan berulang.</li>
</ol>

<h3>Keterbatasan</h3>
<ul>
  <li>Data berakhir pada {date_id(last_ts)}, tanpa periode masa depan, sehingga churn
  tidak dapat diukur langsung.</li>
  <li>Repeat rate rendah membuat segmen Juara dan Loyal otomatis kecil. Ini karakter
  pasar, bukan kesalahan segmentasi.</li>
  <li>Dataset tidak memuat kontak pelanggan maupun kanal akuisisi.</li>
  <li>Skor risiko bersifat heuristik untuk memprioritaskan tindakan, bukan model
  prediktif yang dilatih pada label churn.</li>
</ul>

</body>
</html>"""


_CSS = """
@page {
  size: A4;
  margin: 1.6cm 1.6cm 1.5cm 1.6cm;
  @bottom-right { content: counter(page); color: #98A2B3; font-size: 8pt; }
  @bottom-left { content: "Laporan CRM Olist"; color: #98A2B3; font-size: 8pt; }
}
* { box-sizing: border-box; }
body {
  font-family: "Noto Sans", "DejaVu Sans", sans-serif;
  color: #0B1F2A;
  font-size: 9.5pt;
  line-height: 1.5;
}
h1 { font-size: 26pt; margin: 0 0 6px 0; letter-spacing: -0.5px; }
h2 {
  font-size: 14pt;
  margin: 26px 0 8px 0;
  padding-bottom: 5px;
  border-bottom: 1px solid #E4E8EE;
  color: #0B1F2A;
}
h3 { font-size: 11pt; margin: 18px 0 6px 0; color: #0E7C6B; }
p { margin: 6px 0; }
ul, ol { margin: 6px 0; padding-left: 20px; }
li { margin: 3px 0; }
ol.q { list-style: decimal; }
ol.concl { list-style: decimal; }
code {
  font-family: "DejaVu Sans Mono", monospace;
  background: #F1F4F6;
  padding: 1px 4px;
  border-radius: 4px;
  font-size: 8.5pt;
}
.note { color: #667085; font-size: 8.5pt; }
.cover {
  border-bottom: 3px solid #0E7C6B;
  padding-bottom: 18px;
  margin-bottom: 8px;
}
.cover-eyebrow {
  text-transform: uppercase;
  letter-spacing: 2px;
  font-size: 8.5pt;
  font-weight: 700;
  color: #0E7C6B;
  margin-bottom: 10px;
}
.cover-sub { color: #667085; font-size: 12pt; margin: 0 0 18px 0; }
.cover-meta { display: flex; flex-wrap: wrap; gap: 8px 26px; }
.cover-meta div { font-size: 9pt; }
.cover-meta span { display: block; color: #98A2B3; font-size: 7.5pt; text-transform: uppercase; letter-spacing: 1px; }
.cover-meta b { color: #0B1F2A; }
.kpi-grid { display: flex; flex-wrap: wrap; gap: 10px; margin: 10px 0; }
.kpi {
  border: 1px solid #E4E8EE;
  border-radius: 8px;
  padding: 9px 12px;
  width: 31.5%;
  min-width: 31.5%;
}
.kpi-label { text-transform: uppercase; letter-spacing: 0.6px; font-size: 7pt; color: #667085; font-weight: 700; }
.kpi-value { font-size: 15pt; font-weight: 700; color: #0B1F2A; margin-top: 2px; }
.kpi-sub { font-size: 7.5pt; color: #98A2B3; margin-top: 2px; }
.two { display: flex; gap: 12px; align-items: flex-start; margin: 8px 0; }
.two > div { flex: 1; }
img { width: 100%; height: auto; display: block; margin: 6px 0; }
table { width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 8pt; }
th {
  background: #F7FAF9;
  color: #667085;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  font-size: 6.8pt;
  text-align: left;
  padding: 6px 7px;
  border-bottom: 1px solid #E4E8EE;
}
td { padding: 5px 7px; border-bottom: 1px solid #F0F2F5; vertical-align: top; }
th.num, td.num { text-align: right; white-space: nowrap; }
tr { page-break-inside: avoid; }
h2, h3 { page-break-after: avoid; }
"""


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    d = collect()
    html = build_html(d)
    (OUT_DIR / "laporan.html").write_text(html, encoding="utf-8")

    from weasyprint import HTML

    HTML(string=html, base_url=str(OUT_DIR)).write_pdf(str(PDF_PATH))
    print(f"PDF dibuat: {PDF_PATH}")


if __name__ == "__main__":
    main()
