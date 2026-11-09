"""Halaman metodologi, definisi metrik, dan keterbatasan."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import ui
from src.context import current
from src.formatting import number, percent


def render() -> None:
    ctx = current()
    customers = ctx["customers"]
    orders = ctx["orders"]

    ui.page_header(
        "Metodologi",
        "Definisi, asumsi, dan batas analisis",
        "Bagian ini menjelaskan bagaimana angka dihitung, aturan pembersihan data, dan hal-hal yang "
        "tidak boleh disimpulkan dari dashboard.",
        [f"<b>{number(len(orders))}</b> pesanan sah", f"<b>{number(len(customers))}</b> pelanggan"],
    )

    ui.section("Sumber data", "Sembilan berkas publik Olist yang saling terhubung.", eyebrow="Data")
    sources = [
        ("olist_orders_dataset.csv", "99.441", "Status, waktu pesanan, waktu pengiriman, estimasi tiba"),
        ("olist_customers_dataset.csv", "99.441", "customer_id, customer_unique_id, kota, negara bagian, kode pos"),
        ("olist_order_items_dataset.csv", "112.650", "Item, harga, ongkos kirim, penjual, produk"),
        ("olist_order_payments_dataset.csv", "103.886", "Nilai bayar, metode, cicilan"),
        ("olist_order_reviews_dataset.csv", "104.719", "Skor ulasan dan komentar"),
        ("olist_products_dataset.csv", "32.951", "Kategori produk"),
        ("product_category_name_translation.csv", "71", "Terjemahan kategori ke bahasa Inggris"),
        ("olist_geolocation_dataset.csv", "1.000.163", "Koordinat per kode pos"),
        ("olist_sellers_dataset.csv", "3.095", "Data penjual (tidak dipakai di dashboard pelanggan)"),
    ]
    ui.table(
        pd.DataFrame(
            {
                "Berkas": [row[0] for row in sources],
                "Baris": [row[1] for row in sources],
                "Isi yang dipakai": [row[2] for row in sources],
            }
        ),
        wrap=["Isi yang dipakai"],
        max_height=380,
    )

    st.write("")
    ui.section("Definisi metrik", "Semua angka mengikuti filter periode dan negara bagian.", eyebrow="Kamus")
    st.markdown(
        """
| Metrik | Definisi |
|---|---|
| Pendapatan | Jumlah `payment_value` pesanan yang tidak berstatus batal atau tidak tersedia |
| Pesanan sah | Pesanan dengan status selain `canceled` dan `unavailable` |
| Pelanggan unik | Jumlah `customer_unique_id` berbeda, bukan `customer_id` |
| AOV | Pendapatan dibagi jumlah pesanan |
| Repeat rate | Proporsi pelanggan dengan dua pesanan sah atau lebih |
| Repeat 90 hari | Proporsi pelanggan yang membeli lagi dalam 90 hari setelah pesanan pertama, hanya untuk pelanggan yang sudah teramati 90 hari |
| Recency | Hari sejak transaksi terakhir sampai tanggal analisis 4 September 2018 |
| Pelanggan bernilai tinggi | 20% pelanggan dengan total belanja terbesar |
| Tier | VIP (top 1%), Utama (top 10%), Potensial (top 20%), Reguler |
| Pelanggan overdue | Pelanggan berulang yang jeda terakhirnya minimal dua kali median jeda transaksinya sendiri |
        """
    )

    st.write("")
    ui.section(
        "Mengapa customer_unique_id?",
        "Satu pelanggan dapat muncul sebagai beberapa customer_id.",
        eyebrow="Kunci data",
    )
    st.markdown(
        """
Pada Olist, `customer_id` dibuat untuk setiap pesanan, sedangkan `customer_unique_id` menandai orang
yang sama. Dataset memiliki 99.441 `customer_id` tetapi hanya 96.096 `customer_unique_id`. Jika analisis
memakai `customer_id`, setiap pelanggan akan terlihat sebagai pembeli sekali dan repeat rate menjadi nol.
Dashboard ini memakai `customer_unique_id` untuk semua analisis pelanggan.
        """
    )

    st.write("")
    ui.section("Aturan pembersihan", "Keputusan yang memengaruhi angka.", eyebrow="Kualitas data")
    st.markdown(
        """
- Pesanan berstatus `canceled` dan `unavailable` dikeluarkan dari analisis transaksi dan pelanggan.
- Ulasan ganda pada satu pesanan dirata-ratakan; 551 pesanan memiliki lebih dari satu ulasan.
- Kategori produk yang kosong diberi label "Tidak diketahui"; 610 produk tidak memiliki kategori.
- Koordinat geolocation di luar batas Brazil (lintang -34 sampai 6, bujur -74 sampai -33) dibuang sebelum
  menghitung titik tengah tiap negara bagian.
- Bulan dengan kurang dari 30 pesanan disembunyikan dari grafik tren agar tidak mendistorsi skala.
- Nilai pembayaran yang hilang diisi dari harga item ditambah ongkos kirim.
        """
    )

    st.write("")
    ui.section("Keterbatasan", "Hal yang perlu disampaikan saat mempresentasikan hasil.", eyebrow="Hati-hati")
    st.markdown(
        """
1. **Snapshot, bukan data berjalan.** Data berakhir 3 September 2018. Tidak ada periode masa depan,
   sehingga dashboard tidak dapat mengukur churn secara langsung.
2. **Repeat rate sangat rendah.** Sekitar 97% pelanggan hanya membeli sekali. Segmen dengan label
   "Loyal" dan "Juara" otomatis kecil. Ini karakter pasar, bukan kesalahan segmentasi.
3. **Tidak ada data kontak atau kanal.** Dataset tidak memuat nama, email, telepon, kanal akuisisi,
   maupun riwayat kampanye. Rekomendasi kanal bersifat praktik umum, bukan hasil analisis.
4. **Korelasi bukan sebab-akibat.** Hubungan pengiriman cepat dengan pembelian ulang bersifat asosiatif.
   Pelanggan dengan pesanan bernilai tinggi mungkin memang punya perilaku berbeda.
5. **Kohort terpotong.** Pelanggan yang baru bertransaksi belum punya cukup waktu untuk diamati.
   Analisis repeat 90 hari hanya memakai pelanggan yang sudah teramati penuh.
6. **Mata uang.** Semua nilai dalam Real Brazil (R$), bukan Rupiah.
        """
    )

    st.write("")
    ui.section("Pemetaan pertanyaan tugas", "Setiap pertanyaan dijawab di halaman yang jelas.", eyebrow="Kelengkapan")
    mapping = [
        ("Siapa pelanggan terbaik?", "Ringkasan, Pelanggan, Segmentasi", "Peringkat nilai historis, tier, dan segmen Juara."),
        ("Dari mana pelanggan berasal?", "Geografi", "Peta, negara bagian, wilayah, dan kota."),
        ("Berapa nilai transaksi setiap pelanggan?", "Pelanggan", "Total belanja, AOV, persentil, dan riwayat pesanan."),
        ("Pelanggan mana yang berpotensi tidak aktif?", "Risiko", "Skor risiko, band, dan simulator sasaran reaktivasi."),
        ("Bagaimana meningkatkan loyalitas?", "Loyalitas", "Repeat rate, kohort, pemicu pembelian ulang."),
        ("Strategi pemasaran apa yang diterapkan?", "Loyalitas", "Buku strategi per segmen dan prioritas 90 hari."),
    ]
    ui.table(
        pd.DataFrame(
            {
                "Pertanyaan": [row[0] for row in mapping],
                "Halaman": [row[1] for row in mapping],
                "Bukti": [row[2] for row in mapping],
            }
        ),
        wrap=["Bukti"],
        max_height=300,
    )

    st.write("")
    with st.container(border=True):
        ui.section("Catatan teknis", "Cara dashboard dijalankan dan dihitung.", eyebrow="Implementasi")
        st.markdown(
            f"""
Dashboard dibangun dengan Python, pandas, Streamlit, dan Plotly. Seluruh agregasi dihitung di memori
dari sembilan CSV sumber. Cache lokal mempercepat pemuatan ulang tanpa mengubah data asli.

Pada filter aktif: **{number(len(orders))}** pesanan sah dan **{number(len(customers))}** pelanggan unik.
Segmentasi dan skor risiko dihitung ulang setiap filter berubah, sehingga angka dapat berbeda dari
tampilan tanpa filter.
            """
        )
