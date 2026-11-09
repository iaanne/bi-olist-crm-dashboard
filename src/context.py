"""Konteks data bersama untuk seluruh halaman."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from .analytics import build_customers
from .data import apply_filters, load_orders, snapshot_date, valid_orders


@st.cache_data(show_spinner=False)
def _customers(orders: pd.DataFrame, snapshot: pd.Timestamp) -> pd.DataFrame:
    return build_customers(orders, snapshot)


def build_context(
    start: date,
    end: date,
    states: list[str],
    payments: list[str] | None = None,
    categories: list[str] | None = None,
    delivery: str | None = None,
    segments: list[str] | None = None,
) -> dict:
    raw = load_orders()
    valid = valid_orders(raw)
    snapshot = snapshot_date(raw)
    orders = apply_filters(
        valid,
        pd.Timestamp(start),
        pd.Timestamp(end),
        states,
        payments,
        categories,
        delivery,
    )
    customers = _customers(orders, snapshot) if not orders.empty else pd.DataFrame()

    # Filter segmen bersifat dua tahap: segmen dihitung dari pesanan yang sudah
    # lolos filter lain, lalu pesanan disaring lagi menurut segmen pelanggannya.
    if segments and not customers.empty:
        keep = set(customers.loc[customers["segment"].isin(segments), "customer_uid"])
        orders = orders[orders["customer_uid"].isin(keep)].copy()
        customers = _customers(orders, snapshot) if not orders.empty else pd.DataFrame()

    return {
        "raw": raw,
        "valid": valid,
        "orders": orders,
        "customers": customers,
        "snapshot": snapshot,
    }


def current() -> dict:
    return st.session_state["ctx"]
