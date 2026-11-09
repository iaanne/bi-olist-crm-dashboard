"""Format angka gaya Indonesia untuk seluruh tampilan."""

from __future__ import annotations

import math


def _separators(text: str) -> str:
    return text


def number(value: float | int | None, decimals: int = 0) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def money(value: float | int | None, decimals: int = 0) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    return f"R$ {number(value, decimals)}"


def money_short(value: float | int | None) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    value = float(value)
    if abs(value) >= 1_000_000_000:
        return f"R$ {number(value / 1_000_000_000, 2)} M"
    if abs(value) >= 1_000_000:
        return f"R$ {number(value / 1_000_000, 2)} jt"
    if abs(value) >= 1_000:
        return f"R$ {number(value / 1_000, 0)} rb"
    return f"R$ {number(value, 0)}"


def percent(value: float | None, decimals: int = 1) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    return f"{number(value * 100, decimals)}%"


def compact(value: float | int | None, decimals: int = 1) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    value = float(value)
    if abs(value) >= 1_000_000:
        return f"{number(value / 1_000_000, decimals)} jt"
    if abs(value) >= 1_000:
        return f"{number(value / 1_000, decimals)} rb"
    return number(value, 0)


def days(value: float | int | None) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    return f"{number(value, 0)} hari"


def short_id(customer_uid: str, length: int = 10) -> str:
    text = str(customer_uid)
    return text[:length].upper()


_MONTHS_ID = [
    "Januari",
    "Februari",
    "Maret",
    "April",
    "Mei",
    "Juni",
    "Juli",
    "Agustus",
    "September",
    "Oktober",
    "November",
    "Desember",
]


def date_id(value) -> str:
    if value is None:
        return "-"
    return f"{value.day} {_MONTHS_ID[value.month - 1]} {value.year}"


def month_id(value) -> str:
    if value is None:
        return "-"
    return f"{_MONTHS_ID[value.month - 1][:3]} {value.year}"
