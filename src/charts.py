"""Grafik Plotly dengan gaya visual yang konsisten."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .config import (
    ACCENT,
    BORDER,
    CHART_SEQUENCE,
    FAINT,
    GRID,
    INK,
    MUTED,
    PRIMARY,
    RED,
    REGION_ORDER,
    RISK_COLORS,
    SEGMENT_COLORS,
    STATE_NAMES,
)
from .formatting import compact, money, money_short, number, percent, short_id

FONT = "'Source Sans 3', 'Segoe UI', system-ui, sans-serif"


def _base(fig: go.Figure, height: int = 320, legend: bool = False) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=16, t=18, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=12, color=INK),
        hoverlabel=dict(bgcolor="white", bordercolor=BORDER, font=dict(family=FONT, size=12)),
        showlegend=legend,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0,
            font=dict(size=11, color=MUTED),
            bgcolor="rgba(0,0,0,0)",
        ),
        bargap=0.32,
        hovermode="closest",
    )
    fig.update_xaxes(
        showgrid=False,
        linecolor=BORDER,
        linewidth=1,
        tickfont=dict(size=11, color=MUTED),
        zeroline=False,
        ticks="",
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=GRID,
        griddash="dot",
        linecolor="rgba(0,0,0,0)",
        tickfont=dict(size=11, color=MUTED),
        zeroline=False,
        ticks="",
    )
    return fig


# ---------------------------------------------------------------------------
# Ringkasan
# ---------------------------------------------------------------------------
def revenue_trend(monthly: pd.DataFrame) -> go.Figure:
    data = monthly.copy()
    data["ma3"] = data["Pendapatan"].rolling(3, min_periods=1).mean()
    fig = go.Figure()
    fig.add_bar(
        x=data["month"],
        y=data["Pelanggan baru"] / 1e6,
        name="Pelanggan baru",
        marker_color="#9AD1C7",
        marker_line_width=0,
        customdata=np.stack([data["Pelanggan baru"], data["Pelanggan berulang"]], axis=-1),
        hovertemplate="<b>%{x|%b %Y}</b><br>Pelanggan baru: R$ %{customdata[0]:,.0f}<extra></extra>",
    )
    fig.add_bar(
        x=data["month"],
        y=data["Pelanggan berulang"] / 1e6,
        name="Pelanggan berulang",
        marker_color=PRIMARY,
        marker_line_width=0,
        customdata=data["Pelanggan berulang"],
        hovertemplate="<b>%{x|%b %Y}</b><br>Pelanggan berulang: R$ %{customdata:,.0f}<extra></extra>",
    )
    fig.add_scatter(
        x=data["month"],
        y=data["ma3"] / 1e6,
        mode="lines",
        name="Rata-rata 3 bulan",
        line=dict(color=ACCENT, width=2.4, shape="spline", smoothing=0.6),
        hovertemplate="Rata-rata 3 bulan: R$ %{y:.2f} jt<extra></extra>",
    )
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title=dict(text="juta R$", font=dict(size=10, color=FAINT)), tickformat=".1f")
    fig.update_xaxes(tickformat="%b %y", dtick="M2")
    return _base(fig, height=330, legend=True)


def segment_donut(summary: pd.DataFrame, top: int = 5) -> go.Figure:
    data = summary.sort_values("pendapatan", ascending=False)
    if len(data) > top:
        head = data.head(top)
        rest = data.iloc[top:]
        other = pd.DataFrame(
            {
                "segment": ["Segmen lainnya"],
                "pelanggan": [rest["pelanggan"].sum()],
                "pendapatan": [rest["pendapatan"].sum()],
                "porsi_pendapatan": [rest["porsi_pendapatan"].sum()],
            }
        )
        data = pd.concat([head, other], ignore_index=True)
    fig = go.Figure(
        go.Pie(
            labels=data["segment"],
            values=data["pendapatan"],
            hole=0.62,
            sort=False,
            domain=dict(x=[0.0, 0.6], y=[0.05, 0.95]),
            marker=dict(colors=[SEGMENT_COLORS.get(s, "#B7BEC9") for s in data["segment"]], line=dict(color="white", width=2)),
            textinfo="none",
            customdata=np.stack([data["pelanggan"], data["porsi_pendapatan"]], axis=-1),
            hovertemplate="<b>%{label}</b><br>Pendapatan: R$ %{value:,.0f}<br>Pelanggan: %{customdata[0]:,.0f}<br>Porsi: %{customdata[1]:.1%}<extra></extra>",
        )
    )
    total = data["pendapatan"].sum()
    fig.add_annotation(
        text=f"<span style='font-size:10.5px;color:{MUTED}'>Total</span><br><b style='font-size:16px;color:{INK}'>{money_short(total)}</b>",
        x=0.30,
        y=0.5,
        showarrow=False,
    )
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="v", x=0.64, y=0.5, xanchor="left", yanchor="middle", font=dict(size=10.5)),
        margin=dict(l=0, r=0, t=10, b=0),
    )
    return _base(fig, height=340)


def state_bar(states: pd.DataFrame, metric: str = "pendapatan", top: int = 10) -> go.Figure:
    data = states.nlargest(top, metric).sort_values(metric)
    labels = data["negara_bagian"]
    values = data[metric]
    if metric == "pendapatan":
        x = values / 1e6
        text = [money_short(v) for v in values]
        axis_title = "juta R$"
        hover = "<b>%{y}</b><br>Pendapatan: R$ %{customdata:,.0f}<extra></extra>"
    elif metric == "repeat_rate":
        x = values * 100
        text = [percent(v) for v in values]
        axis_title = "% pelanggan berulang"
        hover = "<b>%{y}</b><br>Repeat rate: %{x:.1f}%<extra></extra>"
    else:
        x = values
        text = [compact(v) for v in values]
        axis_title = "pelanggan"
        hover = "<b>%{y}</b><br>Pelanggan: %{customdata:,.0f}<extra></extra>"

    colors = [PRIMARY if i == len(data) - 1 else "#B9D9D2" for i in range(len(data))]
    fig = go.Figure(
        go.Bar(
            x=x,
            y=labels,
            orientation="h",
            marker_color=colors,
            marker_line_width=0,
            text=text,
            textposition="outside",
            textfont=dict(size=10.5, color=MUTED),
            cliponaxis=False,
            customdata=values,
            hovertemplate=hover,
        )
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID, griddash="dot", title=dict(text=axis_title, font=dict(size=10, color=FAINT)), range=[0, max(x) * 1.28 if len(x) else 1])
    fig.update_yaxes(showgrid=False, tickfont=dict(size=11.5, color=INK))
    fig.update_layout(bargap=0.35, margin=dict(l=4, r=70, t=10, b=4))
    return _base(fig, height=max(280, 30 * len(data) + 40))


def payment_donut(payments: pd.DataFrame) -> go.Figure:
    data = payments.sort_values("pendapatan", ascending=False)
    fig = go.Figure(
        go.Pie(
            labels=data["label"],
            values=data["pendapatan"],
            hole=0.6,
            domain=dict(x=[0.02, 0.62], y=[0.05, 0.95]),
            marker=dict(colors=CHART_SEQUENCE[: len(data)], line=dict(color="white", width=2)),
            textinfo="percent",
            textfont=dict(size=11, color="white"),
            hovertemplate="<b>%{label}</b><br>R$ %{value:,.0f}<br>%{percent}<extra></extra>",
        )
    )
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="v", x=0.66, y=0.5, xanchor="left", yanchor="middle", font=dict(size=10.5)),
        margin=dict(l=0, r=0, t=10, b=0),
    )
    return _base(fig, height=300)


# ---------------------------------------------------------------------------
# Pelanggan
# ---------------------------------------------------------------------------
def pareto(curve: pd.DataFrame, share_20: float) -> go.Figure:
    data = curve
    fig = go.Figure()
    fig.add_scatter(
        x=data["rank_pct"] * 100,
        y=data["cumulative_share"] * 100,
        mode="lines",
        line=dict(color=PRIMARY, width=2.6),
        fill="tozeroy",
        fillcolor="rgba(14,124,107,0.10)",
        hovertemplate="Peringkat %{x:.0f}% pelanggan<br>%{y:.1f}% pendapatan<extra></extra>",
    )
    fig.add_shape(type="line", x0=20, x1=20, y0=0, y1=share_20 * 100, line=dict(color=ACCENT, width=1.5, dash="dot"))
    fig.add_shape(type="line", x0=0, x1=20, y0=share_20 * 100, y1=share_20 * 100, line=dict(color=ACCENT, width=1.5, dash="dot"))
    fig.add_annotation(
        x=22,
        y=share_20 * 100,
        text=f"20% teratas → {percent(share_20)} pendapatan",
        showarrow=False,
        font=dict(size=11, color=ACCENT),
        xanchor="left",
        bgcolor="rgba(255,255,255,0.85)",
    )
    fig.update_xaxes(title=dict(text="% pelanggan (diurutkan dari belanja terbesar)", font=dict(size=10, color=FAINT)), ticksuffix="%")
    fig.update_yaxes(title=dict(text="% pendapatan kumulatif", font=dict(size=10, color=FAINT)), ticksuffix="%", range=[0, 102])
    return _base(fig, height=320)


def spend_distribution(customers: pd.DataFrame) -> go.Figure:
    bins = [0, 50, 100, 200, 500, 1000, np.inf]
    labels = ["<50", "50-100", "100-200", "200-500", "500-1.000", ">1.000"]
    bucket = pd.cut(customers["monetary"], bins=bins, labels=labels, right=False)
    counts = bucket.value_counts().reindex(labels).fillna(0)
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=counts.values,
            marker_color=[PRIMARY if i < len(labels) - 1 else ACCENT for i in range(len(labels))],
            marker_line_width=0,
            text=[compact(v) for v in counts.values],
            textposition="outside",
            textfont=dict(size=10.5, color=MUTED),
            cliponaxis=False,
            customdata=(counts.values / counts.sum()),
            hovertemplate="Belanja R$ %{x}<br>%{y:,.0f} pelanggan (%{customdata:.1%})<extra></extra>",
        )
    )
    fig.update_yaxes(title=dict(text="pelanggan", font=dict(size=10, color=FAINT)), tickformat="~s")
    fig.update_xaxes(title=dict(text="nilai belanja (R$)", font=dict(size=10, color=FAINT)))
    fig.update_layout(margin=dict(l=4, r=8, t=22, b=8))
    return _base(fig, height=300)


def customer_spend_timeline(orders: pd.DataFrame) -> go.Figure:
    data = orders.sort_values("purchase_ts")
    cumulative = data["payment_value"].cumsum()
    fig = go.Figure(
        go.Scatter(
            x=data["purchase_ts"],
            y=cumulative,
            mode="lines+markers",
            line=dict(color=PRIMARY, width=2.4, shape="hv"),
            marker=dict(size=7, color=PRIMARY, line=dict(color="white", width=1.5)),
            hovertemplate="%{x|%d %b %Y}<br>Kumulatif: R$ %{y:,.0f}<extra></extra>",
        )
    )
    lo, hi = data["purchase_ts"].min(), data["purchase_ts"].max()
    pad = max(hi - lo, pd.Timedelta(days=45)) * 0.5
    top = float(cumulative.max()) if len(cumulative) else 1.0
    fig.update_xaxes(
        range=[lo - pad, hi + pad],
        tickformat="%b %Y",
        title=dict(text="tanggal pesanan", font=dict(size=10, color=FAINT)),
    )
    fig.update_yaxes(
        range=[0, top * 1.15 or 1],
        title=dict(text="belanja kumulatif (R$)", font=dict(size=10, color=FAINT)),
        tickformat="~s",
    )
    return _base(fig, height=240)


# ---------------------------------------------------------------------------
# RFM
# ---------------------------------------------------------------------------
def rfm_heatmap(grid: pd.DataFrame, metric: str = "pelanggan", r_labels: dict[int, str] | None = None) -> go.Figure:
    values = grid.values.astype(float)
    y_labels = [r_labels.get(int(r), f"R{r}") if r_labels else f"R{r}" for r in grid.index]
    if metric == "pendapatan":
        text = [[money_short(v) if v else "-" for v in row] for row in values]
        hover = "%{y} / %{x}<br>R$ %{z:,.0f}<extra></extra>"
    else:
        text = [[number(v, 0) if v else "-" for v in row] for row in values]
        hover = "%{y} / %{x}<br>%{z:,.0f} pelanggan<extra></extra>"
    fig = go.Figure(
        go.Heatmap(
            z=values,
            x=[str(c) for c in grid.columns],
            y=y_labels,
            colorscale=[[0, "#F7FAF9"], [0.5, "#BFE0D8"], [1, PRIMARY]],
            showscale=False,
            text=text,
            texttemplate="%{text}",
            textfont=dict(size=11, color=INK),
            hovertemplate=hover,
            xgap=3,
            ygap=3,
        )
    )
    fig.update_xaxes(title=dict(text="Frequency (jumlah pesanan)", font=dict(size=10, color=FAINT)), side="bottom")
    fig.update_yaxes(title=dict(text="Recency (kebaruan)", font=dict(size=10, color=FAINT)), autorange="reversed")
    return _base(fig, height=350)


def segment_treemap(summary: pd.DataFrame) -> go.Figure:
    data = summary[summary["pendapatan"] > 0].sort_values("pendapatan", ascending=False)
    fig = go.Figure(
        go.Treemap(
            labels=data["segment"],
            parents=[""] * len(data),
            values=data["pendapatan"],
            marker=dict(
                colors=[SEGMENT_COLORS.get(s, MUTED) for s in data["segment"]],
                line=dict(color="white", width=2),
            ),
            text=[f"{percent(p)} · {number(n, 0)} pelanggan" for p, n in zip(data["porsi_pendapatan"], data["pelanggan"])],
            textinfo="label+text",
            textfont=dict(size=12, color="white"),
            hovertemplate="<b>%{label}</b><br>Pendapatan: R$ %{value:,.0f}<extra></extra>",
            tiling=dict(pad=3),
        )
    )
    return _base(fig, height=380)


def segment_scatter(customers: pd.DataFrame, sample: int = 4000) -> go.Figure:
    data = customers
    if len(data) > sample:
        data = data.sample(sample, random_state=42)
    fig = go.Figure()
    for segment in [s for s in SEGMENT_COLORS if s in set(data["segment"].astype(str))]:
        subset = data[data["segment"].astype(str) == segment]
        fig.add_scatter(
            x=subset["recency"],
            y=subset["monetary"].clip(lower=1),
            mode="markers",
            name=segment,
            marker=dict(size=5, color=SEGMENT_COLORS[segment], opacity=0.55, line=dict(width=0)),
            hovertemplate=f"<b>{segment}</b><br>Recency: %{{x}} hari<br>Belanja: R$ %{{y:,.0f}}<extra></extra>",
        )
    fig.update_yaxes(type="log", title=dict(text="nilai belanja (R$, skala log)", font=dict(size=10, color=FAINT)), tickformat="~s")
    fig.update_xaxes(title=dict(text="hari sejak transaksi terakhir", font=dict(size=10, color=FAINT)))
    fig.update_layout(margin=dict(l=8, r=10, t=40, b=8))
    return _base(fig, height=360, legend=True)


# ---------------------------------------------------------------------------
# Geografi
# ---------------------------------------------------------------------------
def geo_bubble(states: pd.DataFrame, coords: pd.DataFrame, metric: str = "pendapatan") -> go.Figure:
    data = states.merge(coords, left_on="state", right_on="state", how="inner")
    if data.empty:
        return _base(go.Figure(), height=420)

    size = data["pelanggan"].clip(lower=1)
    sizeref = 2.0 * size.max() / (46**2)
    top_labels = set(data.nlargest(6, "pendapatan")["state"])
    text = [row["state"] if row["state"] in top_labels else "" for _, row in data.iterrows()]
    if metric == "repeat_rate":
        color_values = data["repeat_rate"]
        colorscale = [[0, "#E8F0EE"], [1, PRIMARY]]
        colorbar = dict(title=dict(text="repeat", font=dict(size=10)), tickformat=".1%", thickness=8, len=0.6)
        hovertemplate = "<b>%{customdata[0]}</b><br>Pelanggan: %{customdata[1]:,.0f}<br>Repeat: %{customdata[2]:.1%}<extra></extra>"
    elif metric == "nilai_pelanggan":
        color_values = data["nilai_pelanggan"]
        colorscale = [[0, "#FDF3E3"], [1, ACCENT]]
        colorbar = dict(title=dict(text="R$/pelanggan", font=dict(size=10)), tickformat="~s", thickness=8, len=0.6)
        hovertemplate = "<b>%{customdata[0]}</b><br>Pelanggan: %{customdata[1]:,.0f}<br>Nilai/pelanggan: R$ %{customdata[2]:,.0f}<extra></extra>"
    else:
        color_values = data["pendapatan"]
        colorscale = [[0, "#E8F0EE"], [1, PRIMARY]]
        colorbar = dict(title=dict(text="R$", font=dict(size=10)), tickformat="~s", thickness=8, len=0.6)
        hovertemplate = "<b>%{customdata[0]}</b><br>Pendapatan: R$ %{customdata[1]:,.0f}<br>Pelanggan: %{customdata[2]:,.0f}<extra></extra>"

    custom = np.stack(
        [data["negara_bagian"], data["pelanggan"], data["nilai_pelanggan"], data["repeat_rate"], data["pendapatan"]],
        axis=-1,
    )
    # Urutan customdata disesuaikan tiap mode lewat template di bawah.
    if metric == "repeat_rate":
        custom = np.stack([data["negara_bagian"], data["pelanggan"], data["repeat_rate"]], axis=-1)
    elif metric == "nilai_pelanggan":
        custom = np.stack([data["negara_bagian"], data["pelanggan"], data["nilai_pelanggan"]], axis=-1)
    else:
        custom = np.stack([data["negara_bagian"], data["pendapatan"], data["pelanggan"]], axis=-1)

    fig = go.Figure(
        go.Scattergeo(
            lat=data["lat"],
            lon=data["lng"],
            mode="markers+text",
            text=text,
            textposition="top center",
            textfont=dict(size=10, color=MUTED, family=FONT),
            marker=dict(
                size=size,
                sizemode="area",
                sizeref=sizeref,
                sizemin=7,
                color=color_values,
                colorscale=colorscale,
                cmin=color_values.min(),
                cmax=color_values.max(),
                colorbar=colorbar,
                line=dict(color="white", width=1.2),
                opacity=0.9,
            ),
            customdata=custom,
            hovertemplate=hovertemplate,
        )
    )
    fig.update_geos(
        scope="south america",
        projection_type="mercator",
        center=dict(lat=-15, lon=-53),
        lataxis_range=[-34, 6],
        lonaxis_range=[-74, -33],
        showland=True,
        landcolor="#EDF2F0",
        showcountries=True,
        countrycolor="#FFFFFF",
        showcoastlines=True,
        coastlinecolor="#DDE5E2",
        showframe=False,
        bgcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(margin=dict(l=0, r=0, t=4, b=0))
    return _base(fig, height=440)


def city_bar(cities: pd.DataFrame, top: int = 12) -> go.Figure:
    data = cities.head(top).sort_values("pendapatan")
    labels = data["city"] + " · " + data["state"]
    fig = go.Figure(
        go.Bar(
            x=data["pendapatan"] / 1e6,
            y=labels,
            orientation="h",
            marker_color=[PRIMARY if i == len(data) - 1 else "#B9D9D2" for i in range(len(data))],
            marker_line_width=0,
            text=[money_short(v) for v in data["pendapatan"]],
            textposition="outside",
            textfont=dict(size=10.5, color=MUTED),
            cliponaxis=False,
            customdata=np.stack([data["pelanggan"], data["aov"]], axis=-1),
            hovertemplate="<b>%{y}</b><br>Pendapatan: R$ %{x:.2f} jt<br>Pelanggan: %{customdata[0]:,.0f}<br>AOV: R$ %{customdata[1]:,.0f}<extra></extra>",
        )
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID, griddash="dot", title=dict(text="juta R$", font=dict(size=10, color=FAINT)), range=[0, (data["pendapatan"].max() / 1e6) * 1.55])
    fig.update_yaxes(showgrid=False, tickfont=dict(size=11, color=INK))
    fig.update_layout(bargap=0.35, margin=dict(l=4, r=14, t=10, b=4))
    return _base(fig, height=max(300, 28 * len(data) + 40))


def region_bar(regions: pd.DataFrame) -> go.Figure:
    data = regions.sort_values("pendapatan", ascending=True)
    fig = go.Figure(
        go.Bar(
            x=data["porsi"] * 100,
            y=data["wilayah"],
            orientation="h",
            marker_color=[PRIMARY if i == len(data) - 1 else "#B9D9D2" for i in range(len(data))],
            marker_line_width=0,
            text=[f"{percent(p)} · {money_short(v)}" for p, v in zip(data["porsi"], data["pendapatan"])],
            textposition="outside",
            textfont=dict(size=10.5, color=MUTED),
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Porsi: %{x:.1f}%<extra></extra>",
        )
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID, griddash="dot", ticksuffix="%", range=[0, max(data["porsi"] * 100) * 1.85])
    fig.update_yaxes(showgrid=False, tickfont=dict(size=11.5, color=INK))
    fig.update_layout(margin=dict(l=4, r=12, t=10, b=4))
    return _base(fig, height=250)


# ---------------------------------------------------------------------------
# Risiko
# ---------------------------------------------------------------------------
def risk_bar(risk: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=risk["risk_band"].astype(str),
            y=risk["pelanggan"],
            marker_color=[RISK_COLORS.get(b, MUTED) for b in risk["risk_band"].astype(str)],
            marker_line_width=0,
            text=[f"{compact(n)} · {percent(p)}" for n, p in zip(risk["pelanggan"], risk["porsi_pendapatan"])],
            textposition="outside",
            textfont=dict(size=10.5, color=MUTED),
            cliponaxis=False,
            customdata=np.stack([risk["pendapatan"], risk["recency"]], axis=-1),
            hovertemplate="<b>%{x}</b><br>Pelanggan: %{y:,.0f}<br>Pendapatan: R$ %{customdata[0]:,.0f}<br>Recency median: %{customdata[1]:.0f} hari<extra></extra>",
        )
    )
    fig.update_yaxes(title=dict(text="pelanggan", font=dict(size=10, color=FAINT)), tickformat="~s")
    fig.update_layout(margin=dict(l=4, r=8, t=26, b=6))
    return _base(fig, height=290)


def recency_histogram(customers: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Histogram(
            x=customers["recency"],
            xbins=dict(start=0, end=750, size=30),
            marker_color=PRIMARY,
            marker_line_width=0,
            opacity=0.9,
            hovertemplate="%{x} hari<br>%{y} pelanggan<extra></extra>",
        )
    )
    for threshold, label, color in [(90, "90 hari", "#9AD1C7"), (180, "180 hari", ACCENT), (365, "365 hari", RED)]:
        fig.add_shape(type="line", x0=threshold, x1=threshold, y0=0, y1=1, yref="paper", line=dict(color=color, width=1.4, dash="dot"))
        fig.add_annotation(x=threshold, y=1.02, yref="paper", text=label, showarrow=False, font=dict(size=10, color=color), xanchor="left")
    fig.update_xaxes(title=dict(text="hari sejak transaksi terakhir", font=dict(size=10, color=FAINT)))
    fig.update_yaxes(title=dict(text="pelanggan", font=dict(size=10, color=FAINT)), tickformat="~s")
    return _base(fig, height=300)


def risk_scatter(priority: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for band in ["Tinggi", "Kritis"]:
        subset = priority[priority["risk_band"].astype(str) == band]
        if subset.empty:
            continue
        fig.add_scatter(
            x=subset["recency"],
            y=subset["monetary"],
            mode="markers",
            name=band,
            marker=dict(size=7, color=RISK_COLORS[band], opacity=0.65, line=dict(width=0)),
            text=[short_id(v) for v in subset["customer_uid"]],
            hovertemplate="<b>%{text}</b><br>%{x} hari<br>R$ %{y:,.0f}<extra></extra>",
        )
    fig.update_yaxes(type="log", title=dict(text="nilai belanja (R$)", font=dict(size=10, color=FAINT)), tickformat="~s")
    fig.update_xaxes(title=dict(text="hari sejak transaksi terakhir", font=dict(size=10, color=FAINT)))
    return _base(fig, height=320, legend=True)


# ---------------------------------------------------------------------------
# Loyalitas
# ---------------------------------------------------------------------------
def cohort_line(cohort: pd.DataFrame) -> go.Figure:
    data = cohort.copy()
    fig = go.Figure(
        go.Scatter(
            x=data["cohort"],
            y=data["repeat_90d"] * 100,
            mode="lines+markers",
            line=dict(color=PRIMARY, width=2.4),
            marker=dict(size=7, color=PRIMARY, line=dict(color="white", width=1.5)),
            customdata=data["pelanggan"],
            hovertemplate="Kohort %{x}<br>Repeat 90 hari: %{y:.2f}%<br>%{customdata:,.0f} pelanggan<extra></extra>",
        )
    )
    fig.update_yaxes(title=dict(text="% beli ulang ≤90 hari", font=dict(size=10, color=FAINT)), ticksuffix="%", rangemode="tozero")
    fig.update_xaxes(title=dict(text="kuartal transaksi pertama", font=dict(size=10, color=FAINT)))
    return _base(fig, height=290)


def driver_bar(frame: pd.DataFrame, highlight_max: bool = True) -> go.Figure:
    data = frame.sort_values("repeat_90d")
    if data.empty:
        return _base(go.Figure(), height=120)
    colors = ["#B9D9D2"] * len(data)
    if highlight_max and len(data):
        colors[-1] = ACCENT
    fig = go.Figure(
        go.Bar(
            x=data["repeat_90d"] * 100,
            y=data["kategori"].astype(str),
            orientation="h",
            marker_color=colors,
            marker_line_width=0,
            text=[percent(v, 2) for v in data["repeat_90d"]],
            textposition="outside",
            textfont=dict(size=10.5, color=MUTED),
            cliponaxis=False,
            customdata=data["pelanggan"],
            hovertemplate="<b>%{y}</b><br>Repeat 90 hari: %{x:.2f}%<br>%{customdata:,.0f} pelanggan<extra></extra>",
        )
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID, griddash="dot", ticksuffix="%", range=[0, max(data["repeat_90d"] * 100) * 1.35 + 0.2])
    fig.update_yaxes(showgrid=False, tickfont=dict(size=10.5, color=INK))
    fig.update_layout(bargap=0.4, margin=dict(l=4, r=42, t=10, b=4))
    return _base(fig, height=max(190, 28 * len(data) + 36))
