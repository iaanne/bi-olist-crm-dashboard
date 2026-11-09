"""Membangun notebook analisis RFM dengan output tertanam.

Jalankan dengan: python3 notebook/build_rfm_notebook.py
Keluaran:        rfm_analisis.ipynb

Lingkungan ini tidak punya kernel Jupyter. Setiap sel dijalankan di sini, lalu
output aslinya (stdout dan gambar) ditanamkan ke berkas notebook sehingga saat
dibuka hasilnya langsung terlihat.
"""

from __future__ import annotations

import base64
import contextlib
import io
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import nbformat as nbf

from src.analytics import build_customers, loyalty_kpis, rfm_grid, segment_summary
from src.data import load_orders, snapshot_date, valid_orders
from src.formatting import money, number, percent

OUT = BASE / "rfm_analisis.ipynb"


def md(text: str):
    return nbf.v4.new_markdown_cell(text.strip("\n"))


def _fig_to_png(fig) -> str:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=130, bbox_inches="tight")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


class Runner:
    """Menjalankan sel secara berurutan dan menangkap output sebenarnya."""

    def __init__(self) -> None:
        self.namespace: dict = {}
        self.count = 0

    def run(self, source: str) -> list:
        self.count += 1
        plt.close("all")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exec(compile(source, f"<cell-{self.count}>", "exec"), self.namespace)
        outputs: list = []
        text = buffer.getvalue()
        if text:
            outputs.append(nbf.v4.new_output("stream", name="stdout", text=text))
        for number_ in plt.get_fignums():
            outputs.append(
                nbf.v4.new_output(
                    "display_data",
                    data={"image/png": _fig_to_png(plt.figure(number_))},
                    metadata={},
                )
            )
        plt.close("all")
        cell = nbf.v4.new_code_cell(source.strip("\n"))
        cell.outputs = outputs
        cell.execution_count = self.count
        return cell

    def code(self, source: str):
        return self.run(source)


def build() -> None:
    runner = Runner()

    cells: list = []
    cells.append(
        md(
            """
# Analisis RFM Pelanggan Olist

Notebook ini menghitung segmentasi **RFM** (Recency, Frequency, Monetary) pada dataset
Olist Brazilian E-Commerce, lalu menafsirkan hasilnya. Angka di sini sama dengan yang
dipakai dashboard CRM, karena keduanya memakai modul `src` yang sama.

Jalankan dari akar proyek `W11`:

```bash
jupyter notebook rfm_analisis.ipynb
```

- **Recency**: jumlah hari sejak transaksi terakhir. Tanggal analisis tetap
  4 September 2018 agar nilai recency dapat dibandingkan.
- **Frequency**: jumlah pesanan pelanggan.
- **Monetary**: total nilai belanja pelanggan dalam Real Brazil (R$).
"""
        )
    )

    cells.append(md("## 1. Menyiapkan data"))
    cells.append(
        runner.code(
            """
import sys, pathlib
sys.path.insert(0, str(pathlib.Path.cwd()))

import pandas as pd
import matplotlib.pyplot as plt
from src.data import load_orders, valid_orders, snapshot_date
from src.analytics import build_customers, segment_summary, rfm_grid, loyalty_kpis
from src.formatting import money, number, percent

orders = valid_orders(load_orders())
snapshot = snapshot_date(load_orders())
customers = build_customers(orders, snapshot)

print(f"Tanggal analisis : {snapshot.date()}")
print(f"Pesanan sah      : {len(orders):,} pesanan")
print(f"Pelanggan unik   : {customers['customer_uid'].nunique():,}")
"""
        )
    )

    cells.append(
        md(
            """
## 2. Cara skor RFM dihitung

Recency dan Monetary dibagi menjadi skor 1 sampai 5 memakai **kuantil** (peringkat
persentil), sehingga tiap tingkat berisi porsi pelanggan yang kurang lebih sama.
Frequency tidak bisa memakai kuantil, karena sekitar 97% pelanggan hanya membeli satu
kali; kuantil akan menaruh hampir semua orang di satu tingkat. Karena itu Frequency
memakai pemetaan eksplisit:

| Jumlah pesanan | Skor F |
|---|---|
| 1 | F1 |
| 2 | F3 |
| 3 | F4 |
| 4 atau lebih | F5 |

Kombinasi ketiga skor dipetakan ke sepuluh segmen: Juara, Loyal, Berpotensi Loyal,
Pelanggan Baru, Menjanjikan, Perlu Perhatian, Tidak Boleh Hilang, Berisiko, Tidur, dan
Hilang.
"""
        )
    )

    cells.append(md("## 3. Contoh hasil per pelanggan"))
    cells.append(
        runner.code(
            """
cols = ["customer_uid", "recency", "n_orders", "monetary", "r_score", "f_score", "m_score", "segment"]
head = customers[cols].head(10).copy()
head["customer_uid"] = head["customer_uid"].str[:10].str.upper()
head["monetary"] = head["monetary"].map(money)
print(head.rename(columns={
    "customer_uid": "id", "recency": "recency_hari", "n_orders": "pesanan",
    "monetary": "belanja", "segment": "segmen",
}).to_string(index=False))
"""
        )
    )

    cells.append(
        md(
            """
## 4. Sebaran skor

Jumlah pelanggan pada tiap tingkat skor. Recency dan Monetary tersebar merata karena
memakai kuantil, sedangkan Frequency menumpuk di skor rendah karena rendahnya
pembelian ulang.
"""
        )
    )
    cells.append(
        runner.code(
            """
dist = pd.DataFrame({
    "skor": [1, 2, 3, 4, 5],
    "Recency":   [(customers["r_score"] == s).sum() for s in range(1, 6)],
    "Frequency": [(customers["f_score"] == s).sum() for s in range(1, 6)],
    "Monetary":  [(customers["m_score"] == s).sum() for s in range(1, 6)],
})
print(dist.to_string(index=False))
"""
        )
    )

    cells.append(
        md(
            """
## 5. Matriks Recency x Frequency

Warna dan angka menunjukkan jumlah pelanggan pada setiap kombinasi tingkat Recency
(baris) dan jumlah pesanan (kolom). Sel kanan atas berisi pelanggan paling aktif.
"""
        )
    )
    cells.append(
        runner.code(
            """
grid = rfm_grid(customers, "pelanggan")
fig, ax = plt.subplots(figsize=(6.2, 4))
image = ax.imshow(grid.values, cmap="BuGn", aspect="auto")
ax.set_xticks(range(len(grid.columns)), grid.columns, rotation=30, ha="right")
ax.set_yticks(range(len(grid.index)), [f"R{int(i)}" for i in grid.index])
for i in range(grid.shape[0]):
    for j in range(grid.shape[1]):
        value = grid.values[i, j]
        if value > 0:
            ax.text(j, i, f"{value:,.0f}", ha="center", va="center", fontsize=8,
                    color="white" if value / grid.values.max() > 0.55 else "#0B1F2A")
ax.set_title("Matriks Recency x Frequency")
plt.colorbar(image, ax=ax, shrink=0.85)
plt.tight_layout()
"""
        )
    )

    cells.append(md("## 6. Ringkasan per segmen"))
    cells.append(
        runner.code(
            """
seg = segment_summary(customers)[
    ["segment", "pelanggan", "porsi_pelanggan", "pendapatan", "porsi_pendapatan", "nilai", "risiko"]
].copy()
seg["pelanggan"] = seg["pelanggan"].map(lambda v: number(int(v)))
seg["porsi_pelanggan"] = seg["porsi_pelanggan"].map(percent)
seg["pendapatan"] = seg["pendapatan"].map(money)
seg["porsi_pendapatan"] = seg["porsi_pendapatan"].map(percent)
seg["nilai"] = seg["nilai"].map(money)
seg["risiko"] = seg["risiko"].map(lambda v: number(v, 1))
print(seg.rename(columns={"segment": "segmen", "nilai": "nilai_median", "risiko": "skor_risiko"}).to_string(index=False))
"""
        )
    )

    cells.append(
        md(
            """
## 7. Pendapatan menurut segmen

Diurutkan menurut pendapatan yang dibawa. Segmen Pelanggan Baru dan Berisiko
mendominasi pendapatan, tanda basis pelanggan yang masih muda dan mudah menguap.
"""
        )
    )
    cells.append(
        runner.code(
            """
segments = segment_summary(customers).sort_values("pendapatan")
ax = segments.set_index("segment")["pendapatan"].plot.barh(
    figsize=(6.4, 4), color="#0E7C6B", title="Pendapatan menurut segmen RFM"
)
ax.set_xlabel("Pendapatan (R$)")
ax.set_ylabel("")
plt.tight_layout()
"""
        )
    )

    cells.append(md("## 8. Sepuluh pelanggan dengan nilai belanja terbesar"))
    cells.append(
        runner.code(
            """
top = customers.sort_values("monetary", ascending=False).head(10)
top_view = pd.DataFrame({
    "id": top["customer_uid"].str[:10].str.upper(),
    "kota": top["city"],
    "negara_bagian": top["state"],
    "pesanan": top["n_orders"].astype(int),
    "belanja": top["monetary"].map(money),
    "nilai_pesanan": top["avg_order_value"].map(money),
    "segmen": top["segment"].astype(str),
})
print(top_view.to_string(index=False))
"""
        )
    )

    cells.append(md("## 9. Metrik loyalitas"))
    cells.append(
        runner.code(
            """
lk = loyalty_kpis(orders, customers, snapshot)
print(f"Repeat rate (lebih dari satu pesanan) : {percent(lk['repeat_rate'])}")
print(f"Pembelian ulang <=90 hari             : {percent(lk['repeat_90d'])} dari {number(lk['repeat_90d_n'])} pelanggan teramati")
print(f"Pesanan rata-rata per pelanggan       : {number(lk['avg_orders'], 2)}")
print(f"Jeda median antar transaksi           : {number(lk['median_interval'])} hari")
print(f"Pelanggan berulang                    : {number(lk['loyal_customers'])}")
"""
        )
    )

    # Nilai untuk markdown kesimpulan, diambil dari variabel yang sudah dijalankan.
    ns = runner.namespace
    customers = ns["customers"]
    orders = ns["orders"]
    snapshot = ns["snapshot"]
    median_spend = customers["monetary"].median()
    juara = int((customers["segment"] == "Juara").sum())
    loyal = int((customers["segment"] == "Loyal").sum())
    lk = loyalty_kpis(orders, customers, snapshot)
    snapshot_d = snapshot.date()

    cells.append(
        md(
            f"""
## 10. Kesimpulan

1. Belanja pelanggan sangat miring. Median belanja hanya {money(median_spend)}, tetapi
   sebagian kecil pelanggan bernilai sangat tinggi. 20% pelanggan teratas menyumbang
   sekitar 53,6% pendapatan.
2. Repeat rate hanya {percent(lk['repeat_rate'])}. Segmen Juara ({number(juara)} pelanggan)
   dan Loyal ({number(loyal)} pelanggan) otomatis kecil. Ini karakter pasar, bukan
   kesalahan segmentasi.
3. Karena pembelian ulang jarang, Frequency berupa pemetaan eksplisit lebih jujur
   daripada kuantil.
4. Prioritas tindakan: selamatkan pelanggan bernilai tinggi yang mulai hilang (segmen
   Tidak Boleh Hilang dan Berisiko), lalu dorong pembelian kedua pada pelanggan baru.

**Keterbatasan.** Data berakhir pada {snapshot_d} sehingga churn tidak dapat diukur
langsung. Skor RFM bersifat deskriptif untuk memprioritaskan tindakan, bukan model
prediktif.
"""
        )
    )

    nb = nbf.v4.new_notebook(cells=cells)
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    }
    nbf.write(nb, str(OUT))
    print(f"Notebook dibuat: {OUT}")


if __name__ == "__main__":
    build()
