"""Konstanta tampilan dan pemetaan domain untuk dashboard CRM Olist."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = BASE_DIR / "archive"
ASSETS_DIR = BASE_DIR / "assets"

# ---------------------------------------------------------------------------
# Palet
# ---------------------------------------------------------------------------
INK = "#0B1F2A"
MUTED = "#667085"
FAINT = "#98A2B3"
BORDER = "#E4E8EE"
SURFACE = "#FFFFFF"
CANVAS = "#F5F7F9"

PRIMARY = "#0E7C6B"
PRIMARY_DARK = "#0A5B4F"
PRIMARY_SOFT = "#E6F4F1"
ACCENT = "#D97706"
ACCENT_SOFT = "#FDF3E3"
RED = "#C2414F"
RED_SOFT = "#FBECEE"
BLUE = "#3A6EA5"

CHART_SEQUENCE = [
    "#0E7C6B",
    "#3A6EA5",
    "#D97706",
    "#7A5AF8",
    "#C2414F",
    "#2A9D8F",
    "#8D99AE",
    "#B08968",
]

GRID = "#EDF0F3"

# ---------------------------------------------------------------------------
# Segmen RFM
# ---------------------------------------------------------------------------
SEGMENT_ORDER = [
    "Juara",
    "Loyal",
    "Berpotensi Loyal",
    "Pelanggan Baru",
    "Menjanjikan",
    "Perlu Perhatian",
    "Tidak Boleh Hilang",
    "Berisiko",
    "Tidur",
    "Hilang",
]

SEGMENT_COLORS = {
    "Juara": "#0E7C6B",
    "Loyal": "#2A9D8F",
    "Berpotensi Loyal": "#6BBF9E",
    "Pelanggan Baru": "#3A6EA5",
    "Menjanjikan": "#7FA8D9",
    "Perlu Perhatian": "#E0A458",
    "Tidak Boleh Hilang": "#B45309",
    "Berisiko": "#D97706",
    "Tidur": "#8D99AE",
    "Hilang": "#B7BEC9",
}

SEGMENT_DESCRIPTION = {
    "Juara": "Sering bertransaksi, baru-baru ini, dan nilai belanja tinggi.",
    "Loyal": "Bertransaksi berulang dan masih cukup aktif.",
    "Berpotensi Loyal": "Sudah mengulang transaksi dan baru saja membeli lagi.",
    "Pelanggan Baru": "Baru bertransaksi pertama kali dalam 90 hari terakhir.",
    "Menjanjikan": "Baru sekali membeli, berumur 3 sampai 6 bulan.",
    "Perlu Perhatian": "Sudah mengulang, tetapi mulai jarang bertransaksi.",
    "Tidak Boleh Hilang": "Pelanggan berulang bernilai tinggi yang sudah lama diam.",
    "Berisiko": "Pernah bernilai tinggi, tetapi sudah lebih dari 6 bulan tidak membeli.",
    "Tidur": "Nilai belanja menengah dan sudah lama tidak bertransaksi.",
    "Hilang": "Nilai belanja rendah dan sudah lama tidak bertransaksi.",
}

SEGMENT_ACTION = {
    "Juara": ("Pertahankan", "Program loyalitas berjenjang, akses awal produk baru, dan referral."),
    "Loyal": ("Kembangkan", "Bundling lintas kategori dan penawaran eksklusif anggota."),
    "Berpotensi Loyal": ("Dorong", "Rekomendasi produk pelengkap dan pengingat pembelian kedua."),
    "Pelanggan Baru": ("Onboarding", "Rangkaian sapaan 30 hari dan insentif pembelian kedua."),
    "Menjanjikan": ("Panaskan", "Konten kategori favorit dan voucher terbatas."),
    "Perlu Perhatian": ("Re-engage", "Pengingat personal dan penawaran ulang kategori favorit."),
    "Tidak Boleh Hilang": ("Selamatkan", "Penawaran win-back bernilai tinggi dan kontak langsung."),
    "Berisiko": ("Pulihkan", "Kampanye reaktivasi dengan voucher bertingkat nilai belanja."),
    "Tidur": ("Aktifkan", "Email reaktivasi massal dan diskon kategori populer."),
    "Hilang": ("Uji ulang", "Kampanye murah berbiaya rendah, ukur respons sebelum investasi."),
}

# ---------------------------------------------------------------------------
# Risiko tidak aktif
# ---------------------------------------------------------------------------
RISK_ORDER = ["Rendah", "Sedang", "Tinggi", "Kritis"]
RISK_COLORS = {
    "Rendah": "#2A9D8F",
    "Sedang": "#E0A458",
    "Tinggi": "#D97706",
    "Kritis": "#C2414F",
}

# ---------------------------------------------------------------------------
# Geografi Brazil
# ---------------------------------------------------------------------------
STATE_NAMES = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapa",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceara",
    "DF": "Distrito Federal",
    "ES": "Espirito Santo",
    "GO": "Goias",
    "MA": "Maranhao",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Para",
    "PB": "Paraiba",
    "PR": "Parana",
    "PE": "Pernambuco",
    "PI": "Piaui",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondonia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "Sao Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins",
}

STATE_REGION = {
    "AC": "Norte",
    "AP": "Norte",
    "AM": "Norte",
    "PA": "Norte",
    "RO": "Norte",
    "RR": "Norte",
    "TO": "Norte",
    "AL": "Nordeste",
    "BA": "Nordeste",
    "CE": "Nordeste",
    "MA": "Nordeste",
    "PB": "Nordeste",
    "PE": "Nordeste",
    "PI": "Nordeste",
    "RN": "Nordeste",
    "SE": "Nordeste",
    "DF": "Centro-Oeste",
    "GO": "Centro-Oeste",
    "MT": "Centro-Oeste",
    "MS": "Centro-Oeste",
    "ES": "Sudeste",
    "MG": "Sudeste",
    "RJ": "Sudeste",
    "SP": "Sudeste",
    "PR": "Sul",
    "RS": "Sul",
    "SC": "Sul",
}

REGION_ORDER = ["Sudeste", "Sul", "Nordeste", "Centro-Oeste", "Norte"]

PAYMENT_LABELS = {
    "credit_card": "Kartu kredit",
    "boleto": "Boleto",
    "voucher": "Voucher",
    "debit_card": "Kartu debit",
    "not_defined": "Tidak terdefinisi",
}

# ---------------------------------------------------------------------------
# Metode RFM dan risiko (dipakai di halaman metodologi)
# ---------------------------------------------------------------------------
RFM_WEIGHTS = {"R": 0.55, "F": 0.15, "S": 0.15, "D": 0.15}

SNAPSHOT_NOTE = "Data berakhir 4 September 2018; tanggal analisis memakai 5 September 2018."
