"""Perhitungan RFM, risiko tidak aktif, loyalitas, dan agregasi dashboard."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import (
    PAYMENT_LABELS,
    REGION_ORDER,
    RFM_WEIGHTS,
    RISK_ORDER,
    SEGMENT_ACTION,
    SEGMENT_ORDER,
    STATE_NAMES,
    STATE_REGION,
)


# ---------------------------------------------------------------------------
# Skor RFM
# ---------------------------------------------------------------------------
def _quantile_score(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    """Skor 1-5 berbasis peringkat persentil; nilai kembar menerima skor sama."""
    ranks = series.rank(method="average", pct=True)
    score = np.ceil(ranks * 5).clip(1, 5).astype(int)
    if not higher_is_better:
        score = 6 - score
    return pd.Series(score, index=series.index)


def _frequency_score(orders: pd.Series) -> pd.Series:
    """Frekuensi dipetakan eksplisit karena 97% pelanggan hanya membeli sekali."""
    mapping = {1: 1, 2: 3}
    return orders.map(lambda n: mapping.get(n, 4 if n == 3 else 5)).astype(int)


def _segment(row) -> str:
    r, f, m = row["r_score"], row["f_score"], row["m_score"]
    if r >= 4 and f >= 4 and m >= 4:
        return "Juara"
    if r >= 3 and f >= 4:
        return "Loyal"
    if r >= 4 and f == 3:
        return "Berpotensi Loyal"
    if r >= 4 and f == 1:
        return "Pelanggan Baru"
    if r == 3 and f == 1:
        return "Menjanjikan"
    if r == 3 and f >= 3:
        return "Perlu Perhatian"
    if f >= 3 and m >= 3:
        return "Tidak Boleh Hilang"
    if m >= 4:
        return "Berisiko"
    if m == 3:
        return "Tidur"
    return "Hilang"


def _value_tier(percentile: pd.Series) -> pd.Series:
    return pd.Series(
        np.select(
            [percentile >= 0.99, percentile >= 0.90, percentile >= 0.80],
            ["VIP", "Utama", "Potensial"],
            default="Reguler",
        ),
        index=percentile.index,
    )


def _risk_band(score: pd.Series) -> pd.Series:
    return pd.Series(
        np.select(
            [score <= 35, score <= 55, score <= 75],
            ["Rendah", "Sedang", "Tinggi"],
            default="Kritis",
        ),
        index=score.index,
    )


def build_customers(orders: pd.DataFrame, snapshot: pd.Timestamp) -> pd.DataFrame:
    """Tabel satu baris per pelanggan unik beserta RFM, segmen, dan skor risiko."""
    if orders.empty:
        return pd.DataFrame()

    base = orders.groupby("customer_uid", as_index=False).agg(
        first_ts=("purchase_ts", "min"),
        last_ts=("purchase_ts", "max"),
        n_orders=("order_id", "nunique"),
        monetary=("payment_value", "sum"),
        n_items=("n_items", "sum"),
        avg_order_value=("payment_value", "mean"),
        avg_review=("review_score", "mean"),
        n_reviews=("review_score", "count"),
    )

    last = (
        orders.sort_values("purchase_ts")
        .drop_duplicates("customer_uid", keep="last")[["customer_uid", "city", "state", "zip_prefix"]]
    )
    base = base.merge(last, on="customer_uid", how="left")

    category_spend = (
        orders.groupby(["customer_uid", "main_category"], as_index=False)["payment_value"]
        .sum()
        .sort_values(["customer_uid", "payment_value"])
        .drop_duplicates("customer_uid", keep="last")[["customer_uid", "main_category"]]
        .rename(columns={"main_category": "favorite_category"})
    )
    payment_mix = (
        orders.groupby(["customer_uid", "payment_type"], as_index=False)["payment_value"]
        .sum()
        .sort_values(["customer_uid", "payment_value"])
        .drop_duplicates("customer_uid", keep="last")[["customer_uid", "payment_type"]]
        .rename(columns={"payment_type": "favorite_payment"})
    )
    base = base.merge(category_spend, on="customer_uid", how="left").merge(
        payment_mix, on="customer_uid", how="left"
    )

    delivered = orders[orders["is_delivered"]]
    delivery = delivered.groupby("customer_uid", as_index=False).agg(
        late_rate=("late", "mean"),
        avg_delivery_days=("delivery_days", "mean"),
        late_orders=("late", "sum"),
        delivered_orders=("order_id", "size"),
    )
    base = base.merge(delivery, on="customer_uid", how="left")

    # Jeda antar transaksi, hanya bermakna bagi pelanggan berulang.
    sequence = orders.sort_values(["customer_uid", "purchase_ts"]).drop_duplicates(
        ["customer_uid", "purchase_ts"]
    )
    gaps = sequence.groupby("customer_uid")["purchase_ts"].diff().dt.days
    interval = gaps.groupby(sequence["customer_uid"]).median()
    base["median_interval_days"] = base["customer_uid"].map(interval)

    base["recency"] = (snapshot - base["last_ts"]).dt.days.clip(lower=0)
    base["tenure_days"] = (base["last_ts"] - base["first_ts"]).dt.days
    base["is_repeat"] = base["n_orders"] > 1
    base["avg_order_value"] = base["monetary"] / base["n_orders"]

    base["r_score"] = _quantile_score(base["recency"], higher_is_better=False)
    base["f_score"] = _frequency_score(base["n_orders"])
    base["m_score"] = _quantile_score(base["monetary"], higher_is_better=True)
    base["rfm_score"] = base["r_score"] + base["f_score"] + base["m_score"]
    base["rfm_cell"] = (
        base["r_score"].astype(str) + base["f_score"].astype(str) + base["m_score"].astype(str)
    )
    base["segment"] = base.apply(_segment, axis=1)

    monetary_pct = base["monetary"].rank(method="average", pct=True)
    base["value_tier"] = _value_tier(monetary_pct)
    base["value_percentile"] = monetary_pct

    # Skor risiko: recency dominan, ditambah frekuensi, kepuasan, dan keterlambatan.
    global_late = delivered["late"].mean() if not delivered.empty else 0.0
    recency_component = base["recency"].clip(upper=365) / 365
    frequency_component = 1 - (base["f_score"] - 1) / 4
    satisfaction_component = (5 - base["avg_review"].fillna(3.5)) / 4
    delivery_component = base["late_rate"].fillna(global_late)

    base["risk_score"] = (
        100
        * (
            RFM_WEIGHTS["R"] * recency_component
            + RFM_WEIGHTS["F"] * frequency_component
            + RFM_WEIGHTS["S"] * satisfaction_component
            + RFM_WEIGHTS["D"] * delivery_component
        )
    ).round(1)
    base["risk_band"] = _risk_band(base["risk_score"])

    base["gap_ratio"] = base["recency"] / base["median_interval_days"].replace(0, np.nan)
    base["is_overdue"] = (base["n_orders"] >= 2) & (base["gap_ratio"] >= 2)

    base["segment"] = pd.Categorical(base["segment"], categories=SEGMENT_ORDER, ordered=True)
    base["risk_band"] = pd.Categorical(base["risk_band"], categories=RISK_ORDER, ordered=True)
    return base.reset_index(drop=True)


# ---------------------------------------------------------------------------
# KPI dan agregasi
# ---------------------------------------------------------------------------
def kpi_summary(orders: pd.DataFrame, customers: pd.DataFrame) -> dict:
    if orders.empty or customers.empty:
        return {}
    revenue = float(orders["payment_value"].sum())
    n_orders = int(orders["order_id"].nunique())
    n_customers = int(customers["customer_uid"].nunique())
    delivered = orders[orders["is_delivered"]]
    on_time = float((~delivered["late"]).mean()) if not delivered.empty else np.nan
    high_value = customers[customers["value_percentile"] >= 0.80]
    return {
        "revenue": revenue,
        "orders": n_orders,
        "customers": n_customers,
        "aov": revenue / n_orders if n_orders else 0,
        "repeat_rate": float(customers["is_repeat"].mean()),
        "avg_review": float(orders["review_score"].mean()),
        "review_response": float(orders["review_score"].notna().mean()),
        "on_time_rate": on_time,
        "high_value_customers": int(len(high_value)),
        "high_value_revenue": float(high_value["monetary"].sum()),
        "high_value_share": float(high_value["monetary"].sum() / revenue) if revenue else 0,
        "avg_orders": float(customers["n_orders"].mean()),
        "median_spend": float(customers["monetary"].median()),
        "avg_spend": float(customers["monetary"].mean()),
        "late_rate": float(delivered["late"].mean()) if not delivered.empty else np.nan,
        "avg_delivery_days": float(delivered["delivery_days"].mean()) if not delivered.empty else np.nan,
        "repeat_revenue_share": float(
            orders[orders["customer_uid"].isin(customers.loc[customers["is_repeat"], "customer_uid"])][
                "payment_value"
            ].sum()
            / revenue
        )
        if revenue
        else 0,
    }


def monthly_series(orders: pd.DataFrame) -> pd.DataFrame:
    """Pendapatan bulanan, dipisah pelanggan baru dan berulang."""
    if orders.empty:
        return pd.DataFrame()
    seq = orders.sort_values(["customer_uid", "purchase_ts"]).copy()
    seq["seq"] = seq.groupby("customer_uid").cumcount()
    seq["customer_type"] = np.where(seq["seq"] == 0, "Pelanggan baru", "Pelanggan berulang")
    grouped = (
        seq.groupby(["month", "customer_type"], observed=True)["payment_value"]
        .sum()
        .unstack(fill_value=0)
    )
    for column in ["Pelanggan baru", "Pelanggan berulang"]:
        if column not in grouped:
            grouped[column] = 0
    grouped = grouped[["Pelanggan baru", "Pelanggan berulang"]]
    grouped["Pendapatan"] = grouped.sum(axis=1)
    grouped["Pesanan"] = seq.groupby("month", observed=True)["order_id"].nunique()
    grouped["Pelanggan"] = seq.groupby("month", observed=True)["customer_uid"].nunique()
    full_range = pd.date_range(grouped.index.min(), grouped.index.max(), freq="MS")
    grouped = grouped.reindex(full_range, fill_value=0)
    grouped.index.name = "month"
    return grouped.reset_index()


def pareto_curve(customers: pd.DataFrame) -> pd.DataFrame:
    spend = customers["monetary"].sort_values(ascending=False).reset_index(drop=True)
    if spend.empty or spend.sum() == 0:
        return pd.DataFrame()
    cumulative = spend.cumsum() / spend.sum()
    rank_pct = (spend.index + 1) / len(spend)
    return pd.DataFrame({"rank_pct": rank_pct, "cumulative_share": cumulative})


def segment_summary(customers: pd.DataFrame) -> pd.DataFrame:
    summary = (
        customers.groupby("segment", observed=True)
        .agg(
            pelanggan=("customer_uid", "size"),
            pendapatan=("monetary", "sum"),
            recency=("recency", "median"),
            frekuensi=("n_orders", "mean"),
            nilai=("monetary", "median"),
            risiko=("risk_score", "mean"),
        )
        .reindex(SEGMENT_ORDER)
        .dropna(subset=["pelanggan"])
        .reset_index()
    )
    total_customers = summary["pelanggan"].sum()
    total_revenue = summary["pendapatan"].sum()
    summary["porsi_pelanggan"] = summary["pelanggan"] / total_customers if total_customers else 0
    summary["porsi_pendapatan"] = summary["pendapatan"] / total_revenue if total_revenue else 0
    summary["prioritas"] = summary["segment"].map(lambda s: SEGMENT_ACTION.get(s, ("", ""))[0])
    summary["tindakan"] = summary["segment"].map(lambda s: SEGMENT_ACTION.get(s, ("", ""))[1])
    return summary.sort_values("pendapatan", ascending=False)


def rfm_grid(customers: pd.DataFrame, metric: str = "pelanggan") -> pd.DataFrame:
    data = customers.copy()
    data["freq_bucket"] = np.select(
        [data["n_orders"] == 1, data["n_orders"] == 2, data["n_orders"] == 3],
        ["1 pesanan", "2 pesanan", "3 pesanan"],
        default="4+ pesanan",
    )
    if metric == "pendapatan":
        values, aggfunc = "monetary", "sum"
    else:
        values, aggfunc = "customer_uid", "count"
    pivot = data.pivot_table(
        index="r_score", columns="freq_bucket", values=values, aggfunc=aggfunc, fill_value=0
    )
    columns = ["1 pesanan", "2 pesanan", "3 pesanan", "4+ pesanan"]
    return pivot.reindex(index=[5, 4, 3, 2, 1], columns=columns, fill_value=0)


def state_summary(orders: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    state_orders = orders.groupby("state", as_index=False).agg(
        pendapatan=("payment_value", "sum"),
        pesanan=("order_id", "nunique"),
        pelanggan=("customer_uid", "nunique"),
    )
    state_orders["aov"] = state_orders["pendapatan"] / state_orders["pesanan"]
    state_orders["nilai_pelanggan"] = state_orders["pendapatan"] / state_orders["pelanggan"]
    repeat = (
        customers.groupby("state", as_index=False)
        .agg(repeat_rate=("is_repeat", "mean"), nilai_median=("monetary", "median"))
    )
    out = state_orders.merge(repeat, on="state", how="left")
    out["negara_bagian"] = out["state"].map(STATE_NAMES).fillna(out["state"])
    out["wilayah"] = out["state"].map(STATE_REGION).fillna("Lainnya")
    out["porsi_pendapatan"] = out["pendapatan"] / out["pendapatan"].sum()
    return out.sort_values("pendapatan", ascending=False).reset_index(drop=True)


def region_summary(states: pd.DataFrame) -> pd.DataFrame:
    region = (
        states.groupby("wilayah", as_index=False)
        .agg(
            pendapatan=("pendapatan", "sum"),
            pelanggan=("pelanggan", "sum"),
            pesanan=("pesanan", "sum"),
        )
        .set_index("wilayah")
        .reindex(REGION_ORDER)
        .dropna(how="all")
        .reset_index()
    )
    region["porsi"] = region["pendapatan"] / region["pendapatan"].sum()
    region["aov"] = region["pendapatan"] / region["pesanan"]
    return region.sort_values("pendapatan", ascending=False)


def city_summary(orders: pd.DataFrame, top: int = 15) -> pd.DataFrame:
    city = orders.groupby(["city", "state"], as_index=False).agg(
        pendapatan=("payment_value", "sum"),
        pelanggan=("customer_uid", "nunique"),
        pesanan=("order_id", "nunique"),
    )
    city["aov"] = city["pendapatan"] / city["pesanan"]
    return city.sort_values("pendapatan", ascending=False).head(top).reset_index(drop=True)


def payment_summary(orders: pd.DataFrame) -> pd.DataFrame:
    out = (
        orders.groupby("payment_type", as_index=False)
        .agg(pendapatan=("payment_value", "sum"), pesanan=("order_id", "nunique"))
        .sort_values("pendapatan", ascending=False)
    )
    out["label"] = out["payment_type"].map(PAYMENT_LABELS).fillna(out["payment_type"])
    out["porsi"] = out["pendapatan"] / out["pendapatan"].sum()
    return out


# ---------------------------------------------------------------------------
# Loyalitas
# ---------------------------------------------------------------------------
def _repeat_flags(orders: pd.DataFrame, snapshot: pd.Timestamp) -> pd.DataFrame:
    """Pesanan pertama tiap pelanggan dan status pembelian ulang dalam 90 hari."""
    seq = orders.sort_values(["customer_uid", "purchase_ts"]).copy()
    seq["seq"] = seq.groupby("customer_uid").cumcount()
    first = seq[seq["seq"] == 0].copy()
    deltas = seq["purchase_ts"] - seq.groupby("customer_uid")["purchase_ts"].transform("min")
    repeat_ids = set(seq.loc[deltas.dt.days.between(1, 90), "customer_uid"])
    first["repeat_90d"] = first["customer_uid"].isin(repeat_ids)
    first["observable"] = first["purchase_ts"] <= snapshot - pd.Timedelta(days=90)
    return first


def loyalty_kpis(orders: pd.DataFrame, customers: pd.DataFrame, snapshot: pd.Timestamp) -> dict:
    first = _repeat_flags(orders, snapshot)
    eligible = first[first["observable"]]
    intervals = customers.loc[customers["n_orders"] >= 2, "median_interval_days"].dropna()
    return {
        "repeat_rate": float(customers["is_repeat"].mean()),
        "repeat_90d": float(eligible["repeat_90d"].mean()) if not eligible.empty else np.nan,
        "repeat_90d_n": int(len(eligible)),
        "median_interval": float(intervals.median()) if not intervals.empty else np.nan,
        "avg_orders": float(customers["n_orders"].mean()),
        "new_customers": int(len(first)),
        "loyal_customers": int(customers["is_repeat"].sum()),
    }


def cohort_repeat(orders: pd.DataFrame, snapshot: pd.Timestamp) -> pd.DataFrame:
    first = _repeat_flags(orders, snapshot)
    first = first[first["observable"]].copy()
    first["cohort"] = first["purchase_ts"].dt.to_period("Q").astype(str)
    out = (
        first.groupby("cohort", as_index=False)
        .agg(pelanggan=("customer_uid", "size"), repeat_90d=("repeat_90d", "mean"))
    )
    return out.reset_index(drop=True)


def repeat_drivers(orders: pd.DataFrame, snapshot: pd.Timestamp) -> dict[str, pd.DataFrame]:
    """Tingkat pembelian ulang 90 hari menurut pengalaman pesanan pertama."""
    first = _repeat_flags(orders, snapshot)
    first = first[first["observable"]].copy()
    if first.empty:
        return {}

    def agg_by(frame: pd.DataFrame, column: str, order: list | None = None) -> pd.DataFrame:
        out = (
            frame.dropna(subset=[column])
            .groupby(column, observed=True, as_index=False)
            .agg(pelanggan=("customer_uid", "size"), repeat_90d=("repeat_90d", "mean"))
        )
        out = out[out["pelanggan"] >= 100]
        if order:
            out["_order"] = out[column].map({k: i for i, k in enumerate(order)})
            out = out.sort_values("_order").drop(columns="_order")
        return out

    first["review_group"] = first["review_score"].round().astype("Int64")
    first["delivery_group"] = pd.cut(
        first["delivery_days"],
        bins=[-1, 7, 14, 30, 1000],
        labels=["0-7 hari", "8-14 hari", "15-30 hari", ">30 hari"],
    )
    first["late_group"] = np.where(first["late"], "Terlambat", "Tepat waktu")
    first.loc[~first["is_delivered"], "late_group"] = np.nan
    first["item_group"] = np.where(first["n_items"] > 1, "2 item atau lebih", "1 item")

    value_bins = pd.qcut(first["payment_value"], 5, duplicates="drop")
    first["value_group"] = value_bins
    value_labels = {
        interval: f"R$ {interval.left:,.0f} - {interval.right:,.0f}".replace(",", ".")
        for interval in value_bins.cat.categories
    }

    drivers = {
        "Ulasan pesanan pertama": agg_by(first, "review_group", [1, 2, 3, 4, 5]),
        "Lama pengiriman": agg_by(first, "delivery_group", ["0-7 hari", "8-14 hari", "15-30 hari", ">30 hari"]),
        "Ketepatan pengiriman": agg_by(first, "late_group", ["Tepat waktu", "Terlambat"]),
        "Jumlah item": agg_by(first, "item_group", ["1 item", "2 item atau lebih"]),
        "Nilai pesanan pertama": agg_by(first, "value_group"),
        "Metode pembayaran": agg_by(first, "payment_type"),
    }
    drivers["Nilai pesanan pertama"][ "value_group" ] = drivers["Nilai pesanan pertama"]["value_group"].map(value_labels)
    drivers["Metode pembayaran"]["payment_type"] = drivers["Metode pembayaran"]["payment_type"].map(
        PAYMENT_LABELS
    ).fillna(drivers["Metode pembayaran"]["payment_type"])
    for key, frame in drivers.items():
        frame.rename(columns={frame.columns[0]: "kategori"}, inplace=True)
        frame.attrs["judul"] = key
    return drivers


def category_repeat(orders: pd.DataFrame, snapshot: pd.Timestamp, min_customers: int = 250) -> pd.DataFrame:
    first = _repeat_flags(orders, snapshot)
    first = first[first["observable"]]
    out = (
        first.groupby("main_category", as_index=False)
        .agg(pelanggan=("customer_uid", "size"), repeat_90d=("repeat_90d", "mean"))
        .query("pelanggan >= @min_customers")
        .sort_values("repeat_90d", ascending=False)
    )
    return out


def new_customers_monthly(orders: pd.DataFrame) -> pd.DataFrame:
    seq = orders.sort_values(["customer_uid", "purchase_ts"]).copy()
    seq["seq"] = seq.groupby("customer_uid").cumcount()
    out = (
        seq[seq["seq"] == 0]
        .groupby("month", observed=True)
        .agg(pelanggan_baru=("customer_uid", "size"))
        .reset_index()
    )
    return out


# ---------------------------------------------------------------------------
# Risiko
# ---------------------------------------------------------------------------
def risk_summary(customers: pd.DataFrame) -> pd.DataFrame:
    out = (
        customers.groupby("risk_band", observed=True)
        .agg(
            pelanggan=("customer_uid", "size"),
            pendapatan=("monetary", "sum"),
            recency=("recency", "median"),
        )
        .reindex(RISK_ORDER)
        .dropna(subset=["pelanggan"])
        .reset_index()
    )
    out["porsi_pelanggan"] = out["pelanggan"] / out["pelanggan"].sum()
    out["porsi_pendapatan"] = out["pendapatan"] / out["pendapatan"].sum()
    return out


def risk_priority(
    customers: pd.DataFrame, min_recency: int = 180, value_percentile: float = 0.80
) -> pd.DataFrame:
    threshold = customers["monetary"].quantile(value_percentile)
    pool = customers[
        (customers["recency"] >= min_recency)
        & (customers["monetary"] >= threshold)
        & (customers["risk_band"].isin(["Tinggi", "Kritis"]))
    ].copy()
    pool["prioritas"] = np.where(pool["value_percentile"] >= 0.95, "P1", "P2")
    pool["rekomendasi"] = np.where(
        pool["n_orders"] > 1,
        "Win-back personal: kontak langsung dan voucher nilai tinggi.",
        "Reaktivasi: penawaran kategori favorit dan pengingat terbatas.",
    )
    return pool.sort_values(["monetary", "recency"], ascending=[False, False]).reset_index(drop=True)


def risk_threshold_preview(customers: pd.DataFrame, min_recency: int, value_percentile: float) -> dict:
    threshold = customers["monetary"].quantile(value_percentile)
    pool = customers[(customers["recency"] >= min_recency) & (customers["monetary"] >= threshold)]
    return {
        "jumlah": int(len(pool)),
        "pendapatan": float(pool["monetary"].sum()),
        "porsi": float(pool["monetary"].sum() / customers["monetary"].sum()) if customers["monetary"].sum() else 0,
        "ambang_nilai": float(threshold),
        "recency": float(pool["recency"].median()) if not pool.empty else np.nan,
    }
