"""
muat_data.py - Baca CSV hasil agregasi di folder data/ menjadi DataFrame.
Tidak ada Streamlit di sini; caching dilakukan di app.py.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

FOLDER_DATA = Path(__file__).resolve().parent.parent / "data"

KOLOM_ANGKA = ["tahun", "kejadian", "korban", "korban_min", "korban_max", "korban_sipil", "lat", "lon"]

URUTAN_JENIS = ["Konflik negara", "Konflik non-negara", "Kekerasan sepihak"]


def _kolom_teks(kolom: pd.Series) -> bool:
    """True untuk kolom teks. Di pandas 3 teks dibaca sebagai dtype `str`, bukan `object` lagi."""
    return kolom.dtype == object or isinstance(kolom.dtype, pd.StringDtype)


def _baca(nama_file: str) -> pd.DataFrame:
    df = pd.read_csv(FOLDER_DATA / nama_file)
    for kolom in df.columns:
        if _kolom_teks(df[kolom]):
            df[kolom] = df[kolom].fillna("")
    return df


def muat_negara_tahun() -> pd.DataFrame:
    """Korban per negara x tahun x jenis kekerasan (tabel utama)."""
    df = _baca("korban_negara_tahun.csv")
    _validasi(df, ["negara", "iso3", "wilayah", "tahun", "jenis", "status", "kejadian", "korban"], "korban_negara_tahun.csv")
    return df


def muat_grid() -> pd.DataFrame:
    """Kejadian per sel grid 0,5 derajat x tahun x jenis (untuk peta titik)."""
    df = _baca("grid_kejadian.csv")
    _validasi(df, ["tahun", "lat", "lon", "jenis", "negara", "status", "kejadian", "korban"], "grid_kejadian.csv")
    return df


def muat_konflik() -> pd.DataFrame:
    """Korban per konflik (nama konflik UCDP) x tahun."""
    df = _baca("konflik_tahun.csv")
    _validasi(df, ["konflik", "jenis", "tahun", "status", "kejadian", "korban", "negara_utama"], "konflik_tahun.csv")
    return df


def _validasi(df: pd.DataFrame, kolom_wajib: list[str], nama: str) -> None:
    hilang = [k for k in kolom_wajib if k not in df.columns]
    if hilang:
        raise ValueError(f"{nama}: kolom hilang -> {hilang}")
    if df.empty:
        raise ValueError(f"{nama}: file kosong")
    # Satu sel rusak membuat kolom angka terbaca sebagai teks; _baca lalu mengisinya "" dan
    # sum() menyambung teks, bukan menjumlah. Lebih baik gagal dengan pesan yang jelas.
    for kolom in KOLOM_ANGKA:
        if kolom in df.columns and not pd.api.types.is_numeric_dtype(df[kolom]):
            rusak = pd.to_numeric(df[kolom].replace("", None), errors="coerce").isna() & (df[kolom] != "")
            baris = (df.index[rusak] + 2).tolist()[:5]  # +2: header dan nomor baris mulai dari 1
            raise ValueError(f"{nama}: kolom {kolom} harus angka, cek baris {baris}")
        # "inf" terbaca sebagai angka sehingga lolos cek di atas, lalu int(sum) di kartu KPI gagal (OverflowError).
        if kolom in df.columns and pd.api.types.is_numeric_dtype(df[kolom]):
            tak_hingga = df[kolom].isin([float("inf"), float("-inf")])
            if tak_hingga.any():
                baris = (df.index[tak_hingga] + 2).tolist()[:5]
                raise ValueError(f"{nama}: kolom {kolom} berisi nilai tak hingga, cek baris {baris}")
