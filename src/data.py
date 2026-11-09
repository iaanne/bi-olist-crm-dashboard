"""Pemuatan dan penyatuan dataset Olist menjadi satu tabel tingkat pesanan."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .config import ARCHIVE_DIR, BASE_DIR, PAYMENT_LABELS

CACHE_DIR = BASE_DIR / ".cache"
ORDERS_CACHE = CACHE_DIR / "orders_v2.pkl"
SOURCE_FILES = [
    "olist_orders_dataset.csv",
    "olist_customers_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_products_dataset.csv",
    "product_category_name_translation.csv",
]


def _sources_are_older_than_cache() -> bool:
    if not ORDERS_CACHE.exists():
        return False
    newest = max((ARCHIVE_DIR / name).stat().st_mtime for name in SOURCE_FILES)
    return ORDERS_CACHE.stat().st_mtime >= newest



def _path(name: str):
    return ARCHIVE_DIR / name


def _prepare_category(name: str | float | None) -> str:
    if not isinstance(name, str) or not name.strip():
        return "Tidak diketahui"
    return name.replace("_", " ").strip().capitalize()


@st.cache_data(show_spinner="Menyiapkan data pesanan...")
def load_orders() -> pd.DataFrame:
    """Gabungkan seluruh berkas sumber menjadi satu tabel tingkat pesanan."""
    if _sources_are_older_than_cache():
        try:
            return pd.read_pickle(ORDERS_CACHE)
        except Exception:
            pass

    orders = pd.read_csv(
        _path("olist_orders_dataset.csv"),
        dtype={"order_id": str, "customer_id": str},
        parse_dates=[
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    )
    orders = orders.rename(
        columns={
            "order_purchase_timestamp": "purchase_ts",
            "order_approved_at": "approved_ts",
            "order_delivered_carrier_date": "carrier_ts",
            "order_delivered_customer_date": "delivered_ts",
            "order_estimated_delivery_date": "estimated_ts",
            "order_status": "status",
        }
    )

    customers = pd.read_csv(
        _path("olist_customers_dataset.csv"),
        dtype={"customer_id": str, "customer_unique_id": str, "customer_zip_code_prefix": str},
    ).rename(
        columns={
            "customer_unique_id": "customer_uid",
            "customer_zip_code_prefix": "zip_prefix",
            "customer_city": "city",
            "customer_state": "state",
        }
    )
    customers["zip_prefix"] = customers["zip_prefix"].str.zfill(5)
    customers["city"] = customers["city"].str.title()

    items = pd.read_csv(
        _path("olist_order_items_dataset.csv"),
        dtype={"order_id": str, "product_id": str, "seller_id": str},
    )
    products = pd.read_csv(
        _path("olist_products_dataset.csv"), dtype={"product_id": str}
    )[["product_id", "product_category_name"]]
    translation = pd.read_csv(
        _path("product_category_name_translation.csv"), encoding="utf-8-sig"
    ).rename(columns={"product_category_name_english": "category_en"})
    products = products.merge(translation, on="product_category_name", how="left")
    products["category"] = products["category_en"].fillna(products["product_category_name"]).map(_prepare_category)
    items = items.merge(products[["product_id", "category"]], on="product_id", how="left")
    items["category"] = items["category"].fillna("Tidak diketahui")

    item_agg = items.groupby("order_id", as_index=False).agg(
        items_value=("price", "sum"),
        freight_value=("freight_value", "sum"),
        n_items=("order_item_id", "count"),
        n_sellers=("seller_id", "nunique"),
    )
    main_category = (
        items.sort_values(["order_id", "price"])
        .drop_duplicates("order_id", keep="last")[["order_id", "category"]]
        .rename(columns={"category": "main_category"})
    )

    payments = pd.read_csv(
        _path("olist_order_payments_dataset.csv"), dtype={"order_id": str}
    )
    payment_agg = payments.groupby("order_id", as_index=False).agg(
        payment_value=("payment_value", "sum"),
        n_payments=("payment_sequential", "max"),
        installments=("payment_installments", "max"),
    )
    main_payment = (
        payments.sort_values(["order_id", "payment_value"])
        .drop_duplicates("order_id", keep="last")[["order_id", "payment_type"]]
    )

    reviews = pd.read_csv(
        _path("olist_order_reviews_dataset.csv"), dtype={"order_id": str}
    )
    review_agg = reviews.groupby("order_id", as_index=False).agg(
        review_score=("review_score", "mean"),
        review_count=("review_id", "count"),
        has_comment=("review_comment_message", lambda s: s.notna().any()),
    )

    data = (
        orders.merge(customers, on="customer_id", how="left")
        .merge(item_agg, on="order_id", how="left")
        .merge(main_category, on="order_id", how="left")
        .merge(payment_agg, on="order_id", how="left")
        .merge(main_payment, on="order_id", how="left")
        .merge(review_agg, on="order_id", how="left")
    )

    data["payment_value"] = data["payment_value"].fillna(
        data["items_value"].fillna(0) + data["freight_value"].fillna(0)
    )
    data["payment_type"] = data["payment_type"].fillna("not_defined")
    data["main_category"] = data["main_category"].fillna("Tidak diketahui")
    data["n_items"] = data["n_items"].fillna(0).astype(int)
    data["installments"] = data["installments"].fillna(1).astype(int)

    data["is_delivered"] = (data["status"] == "delivered") & data["delivered_ts"].notna()
    data["late"] = (
        data["is_delivered"]
        & data["estimated_ts"].notna()
        & (data["delivered_ts"] > data["estimated_ts"])
    )
    data["delivery_days"] = (data["delivered_ts"] - data["purchase_ts"]).dt.days
    data["estimate_days"] = (data["estimated_ts"] - data["purchase_ts"]).dt.days

    data["month"] = data["purchase_ts"].dt.to_period("M").dt.to_timestamp()
    data["quarter"] = data["purchase_ts"].dt.to_period("Q").astype(str)
    data["year"] = data["purchase_ts"].dt.year

    data = data.sort_values("purchase_ts").reset_index(drop=True)
    CACHE_DIR.mkdir(exist_ok=True)
    data.to_pickle(ORDERS_CACHE)
    return data


def valid_orders(data: pd.DataFrame) -> pd.DataFrame:
    """Pesanan yang dihitung sebagai transaksi: bukan batal dan tidak kedaluwarsa."""
    return data[~data["status"].isin(["canceled", "unavailable"]) & data["purchase_ts"].notna()].copy()


def snapshot_date(data: pd.DataFrame) -> pd.Timestamp:
    """Tanggal analisis: satu hari setelah transaksi terakhir yang sah."""
    return valid_orders(data)["purchase_ts"].max().normalize() + pd.Timedelta(days=1)


def apply_filters(
    data: pd.DataFrame,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
    states: list[str] | None = None,
    payments: list[str] | None = None,
    categories: list[str] | None = None,
    delivery: str | None = None,
) -> pd.DataFrame:
    filtered = data
    if start is not None:
        filtered = filtered[filtered["purchase_ts"] >= pd.Timestamp(start)]
    if end is not None:
        filtered = filtered[filtered["purchase_ts"] < pd.Timestamp(end) + pd.Timedelta(days=1)]
    if states:
        filtered = filtered[filtered["state"].isin(states)]
    if payments:
        filtered = filtered[filtered["payment_type"].isin(payments)]
    if categories:
        filtered = filtered[filtered["main_category"].isin(categories)]
    if delivery == "late":
        filtered = filtered[filtered["late"]]
    elif delivery == "ontime":
        filtered = filtered[filtered["is_delivered"] & ~filtered["late"]]
    return filtered.copy()


@st.cache_data(show_spinner=False)
def load_geo_zip() -> pd.DataFrame:
    """Koordinat rata-rata per kode pos, sudah dibatasi ke wilayah Brazil."""
    geo = pd.read_csv(
        _path("olist_geolocation_dataset.csv"),
        usecols=[
            "geolocation_zip_code_prefix",
            "geolocation_lat",
            "geolocation_lng",
        ],
        dtype={"geolocation_zip_code_prefix": str},
    )
    geo = geo.rename(
        columns={
            "geolocation_zip_code_prefix": "zip_prefix",
            "geolocation_lat": "lat",
            "geolocation_lng": "lng",
        }
    )
    geo["zip_prefix"] = geo["zip_prefix"].str.zfill(5)
    geo = geo[
        geo["lat"].between(-34.0, 6.0) & geo["lng"].between(-74.0, -33.0)
    ]
    return geo.groupby("zip_prefix", as_index=False).agg(lat=("lat", "mean"), lng=("lng", "mean"))


@st.cache_data(show_spinner=False)
def load_state_coordinates() -> pd.DataFrame:
    """Titik tengah tiap negara bagian, dihitung dari koordinat kode pos pelanggan."""
    data = valid_orders(load_orders())
    geo = load_geo_zip()
    merged = data[["zip_prefix", "state"]].merge(geo, on="zip_prefix", how="inner")
    return (
        merged.groupby("state", as_index=False)
        .agg(lat=("lat", "mean"), lng=("lng", "mean"), n=("lat", "size"))
        .query("n >= 30")
    )


@st.cache_data(show_spinner=False)
def load_city_coordinates() -> pd.DataFrame:
    data = valid_orders(load_orders())
    geo = load_geo_zip()
    merged = (
        data[["zip_prefix", "city", "state"]]
        .drop_duplicates()
        .merge(geo, on="zip_prefix", how="inner")
    )
    return (
        merged.groupby(["state", "city"], as_index=False)
        .agg(lat=("lat", "mean"), lng=("lng", "mean"), n=("lat", "size"))
        .query("n >= 20")
    )


def payment_label(value: str) -> str:
    return PAYMENT_LABELS.get(value, str(value).replace("_", " ").capitalize())
