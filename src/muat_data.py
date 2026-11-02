"""
muat_data.py - Baca CSV hasil agregasi di folder data/ menjadi DataFrame.
Tidak ada Streamlit di sini; caching dilakukan di app.py.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

FOLDER_DATA = Path(__file__).resolve().parent.parent / "data"

URUTAN_JENIS = ["Konflik negara", "Konflik non-negara", "Kekerasan sepihak"]


def _baca(nama_file: str) -> pd.DataFrame:
    df = pd.read_csv(FOLDER_DATA / nama_file)
    for kolom in df.columns:
        if df[kolom].dtype == object:
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
