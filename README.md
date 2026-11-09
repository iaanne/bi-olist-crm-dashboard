# CRM Insight - Dashboard Olist

Dashboard Business Intelligence interaktif untuk menganalisis pelanggan pada
**Olist Brazilian E-Commerce Public Dataset**. Dibangun dengan Streamlit dan menjawab
enam pertanyaan bisnis melalui tujuh halaman.

Aplikasi ini sudah memuat seluruh dataset di dalam folder `archive/`, jadi bisa langsung
dijalankan tanpa mengunduh apa pun.

## Menjalankan lokal

```bash
pip install -r requirements.txt
streamlit run app.py
```

Dashboard terbuka di `http://localhost:8501`.

## Halaman

| Halaman | Isi |
|---|---|
| Ringkasan | KPI utama, tren pendapatan bulanan, komposisi pembayaran |
| Pelanggan | Peringkat pelanggan, tier nilai, pencarian pelanggan |
| Segmentasi RFM | Matriks Recency x Frequency, buku strategi per segmen |
| Geografi | Peta sebaran pelanggan, peringkat negara bagian dan kota |
| Risiko tidak aktif | Skor risiko 0-100 dan band risiko |
| Loyalitas & strategi | Retensi, kohort, pemicu pembelian ulang |
| Metodologi | Sumber data, definisi metrik, aturan pembersihan, keterbatasan |

## Filter analisis

Filter di bilah samping berlaku untuk seluruh halaman:

- Periode transaksi
- Negara bagian
- Tipe pembayaran
- Kategori produk, yaitu kategori bernilai terbesar pada tiap pesanan
- Performa pengiriman, tepat waktu atau terlambat
- Segmen RFM, disaring dua tahap

Tombol **Atur ulang filter** mengembalikan semua pilihan ke awal.

## Pertanyaan bisnis yang dijawab

1. Siapa pelanggan terbaik dan berapa nilai transaksinya?
2. Dari mana pelanggan berasal?
3. Berapa nilai transaksi setiap pelanggan?
4. Pelanggan mana yang berpotensi tidak aktif?
5. Bagaimana meningkatkan loyalitas pelanggan?
6. Strategi pemasaran apa yang perlu diterapkan?

## Metode ringkas

- **Kunci pelanggan** memakai `customer_unique_id`, bukan `customer_id`, karena satu
  pelanggan dapat muncul sebagai beberapa `customer_id`.
- **Segmentasi RFM**: Recency dan Monetary dibagi menjadi skor 1 sampai 5 memakai
  kuantil. Frequency memakai pemetaan eksplisit karena sekitar 97% pelanggan hanya
  membeli sekali. Kombinasi skor dipetakan ke sepuluh segmen.
- **Skor risiko** 0 sampai 100 menggabungkan recency (55%), frequency (15%), kepuasan
  (15%), dan keterlambatan pengiriman (15%). Band risiko: Rendah (<=35), Sedang (<=55),
  Tinggi (<=75), Kritis (>75).
- **Tanggal analisis** tetap pada 4 September 2018 agar recency dapat dibandingkan.
- Pesanan berstatus `canceled` dan `unavailable` dikeluarkan, menyisakan 98.207 pesanan
  sah dan 94.990 pelanggan unik.

## Struktur

```
app.py                 Titik masuk, navigasi, dan filter sidebar
requirements.txt       Dependensi dashboard
requirements-dev.txt   Dependensi tambahan untuk membangun laporan dan notebook
rfm_analisis.ipynb     Notebook analisis RFM, output sudah tertanam
laporan/               Laporan PDF tujuh halaman dan skrip pembangunnya
notebook/              Skrip pembangun notebook RFM
archive/               Sembilan berkas CSV sumber Olist
src/
  config.py            Palet warna, pemetaan segmen, negara bagian, bobot skor
  data.py              Pemuatan dan penyatuan CSV menjadi tabel tingkat pesanan
  analytics.py         Agregasi, RFM, skor risiko, metrik loyalitas
  charts.py            Seluruh figur Plotly
  formatting.py        Format angka, mata uang R$, persen, tanggal
  context.py           Konteks analisis per kombinasi filter
  ui.py                CSS, komponen KPI, tabel HTML, filter sidebar
views/                 Tujuh halaman dashboard
```

## Membangun ulang laporan dan notebook

Kedua berkas hasil sudah tersedia di repo. Kalau perlu dibuat ulang:

```bash
pip install -r requirements-dev.txt
python3 laporan/build_laporan.py
python3 notebook/build_rfm_notebook.py
```

Dependensi tambahannya sengaja dipisah ke `requirements-dev.txt` agar build Streamlit
Cloud tetap ringan.

## Catatan teknis

- Tabel ditampilkan sebagai HTML ringan agar tidak bergantung pada `pyarrow`.
- Tema visual diatur lewat `src/config.py` dan `.streamlit/config.toml`.
- Navigasi memakai `st.navigation` sehingga setiap halaman punya URL sendiri, misalnya
  `/pelanggan` dan `/segmentasi`.

## Sumber data

[Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
(93.000 lebih pesanan pada 2016-2018).
