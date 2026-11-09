"""
siapkan_data.py - Mengubah data mentah UCDP GED menjadi CSV ringkas di folder data/.

Data mentah UCDP berukuran ~270 MB (lebih dari 400 ribu kejadian), terlalu besar
untuk disimpan di repositori. Skrip ini mengagregasinya menjadi tiga tabel kecil:

  data/korban_negara_tahun.csv   korban per negara x tahun x jenis kekerasan
  data/grid_kejadian.csv         kejadian per sel grid 0,5 derajat x tahun x jenis (untuk peta)
  data/konflik_tahun.csv         korban per konflik (pasangan pihak) x tahun

Cara pakai:
    python -m src.siapkan_data                 # unduh dari ucdp.uu.se lalu olah
    python -m src.siapkan_data --folder-mentah data/raw   # pakai file yang sudah diunduh

Sumber (tanpa registrasi):
  - GED 26.1 (final, 1989-2025): https://ucdp.uu.se/downloads/ged/ged261-csv.zip
  - UCDP Candidate (awal, 2026):  https://ucdp.uu.se/downloads/candidateged/GEDEvent_v26_01_26_09.csv
"""

from __future__ import annotations

import argparse
import io
import sys
import zipfile
from pathlib import Path

import pandas as pd

from src.negara import JENIS_KEKERASAN, WILAYAH_ID, iso3, nama_indonesia

URL_GED = "https://ucdp.uu.se/downloads/ged/ged261-csv.zip"
URL_KANDIDAT = "https://ucdp.uu.se/downloads/candidateged/GEDEvent_v26_01_26_09.csv"
NAMA_FILE_GED = "GEDEvent_v26_1.csv"
NAMA_FILE_KANDIDAT = "GEDEvent_v26_01_26_09.csv"
FOLDER_DATA = Path(__file__).resolve().parent.parent / "data"
RESOLUSI_GRID = 0.5  # derajat

KOLOM = [
    "id", "year", "type_of_violence", "conflict_new_id", "conflict_name",
    "side_a", "side_b", "latitude", "longitude", "country", "region",
    "best", "high", "low", "deaths_civilians",
]


def unduh(url: str, tujuan: Path) -> Path:
    """Unduh file jika belum ada di folder mentah."""
    import requests  # impor di sini agar modul tetap ringan saat diuji

    tujuan.parent.mkdir(parents=True, exist_ok=True)
    if tujuan.exists():
        print(f"  pakai file lokal {tujuan}")
        return tujuan
    print(f"  mengunduh {url} ...")
    r = requests.get(url, timeout=600)
    r.raise_for_status()
    if url.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            z.extract(tujuan.name, tujuan.parent)
    else:
        tujuan.write_bytes(r.content)
    return tujuan


def baca_kejadian(path: Path, status: str) -> pd.DataFrame:
    """Baca CSV UCDP, ambil kolom yang diperlukan, tambahkan kolom status."""
    df = pd.read_csv(path, usecols=KOLOM, low_memory=False)
    df["status"] = status
    return df


def rapikan_kejadian(df: pd.DataFrame) -> pd.DataFrame:
    """Terjemahkan kode/nama UCDP ke kolom berbahasa Indonesia yang dipakai aplikasi."""
    out = pd.DataFrame(
        {
            "tahun": df["year"].astype(int),
            "negara_ucdp": df["country"],
            "negara": df["country"].map(nama_indonesia),
            "iso3": df["country"].map(iso3),
            "wilayah": df["region"].map(WILAYAH_ID).fillna(df["region"]),
            "jenis": df["type_of_violence"].map(JENIS_KEKERASAN),
            "konflik": df["conflict_name"],
            "pihak_a": df["side_a"],
            "pihak_b": df["side_b"],
            "lat": df["latitude"].astype(float),
            "lon": df["longitude"].astype(float),
            "korban": df["best"].astype(int),
            "korban_min": df["low"].astype(int),
            "korban_max": df["high"].astype(int),
            "korban_sipil": df["deaths_civilians"].astype(int),
            "status": df["status"],
        }
    )
    tanpa_iso = sorted(out.loc[out["iso3"] == "", "negara_ucdp"].unique())
    if tanpa_iso:
        print(f"  PERINGATAN: negara tanpa kode ISO-3 -> {tanpa_iso}", file=sys.stderr)
    return out


def agregasi_negara_tahun(k: pd.DataFrame) -> pd.DataFrame:
    """Satu baris per negara x tahun x jenis kekerasan."""
    g = (
        k.groupby(["negara", "iso3", "wilayah", "tahun", "jenis", "status"], as_index=False)
        .agg(
            kejadian=("korban", "size"),
            korban=("korban", "sum"),
            korban_min=("korban_min", "sum"),
            korban_max=("korban_max", "sum"),
            korban_sipil=("korban_sipil", "sum"),
        )
        .sort_values(["tahun", "negara", "jenis"])
    )
    return g


def agregasi_grid(k: pd.DataFrame, resolusi: float = RESOLUSI_GRID) -> pd.DataFrame:
    """Kejadian dibulatkan ke sel grid agar peta ringan tetapi polanya tetap terlihat."""
    sel = k.assign(
        lat=(k["lat"] / resolusi).round() * resolusi,
        lon=(k["lon"] / resolusi).round() * resolusi,
    )
    g = (
        sel.groupby(["tahun", "lat", "lon", "jenis", "negara", "status"], as_index=False)
        .agg(kejadian=("korban", "size"), korban=("korban", "sum"))
        .sort_values(["tahun", "lat", "lon"])
    )
    g["lat"] = g["lat"].round(2)
    g["lon"] = g["lon"].round(2)
    return g


def agregasi_konflik(k: pd.DataFrame) -> pd.DataFrame:
    """Korban per konflik (nama konflik UCDP) per tahun, beserta negara dengan kejadian terbanyak."""
    g = (
        k.groupby(["konflik", "jenis", "tahun", "status"], as_index=False)
        .agg(kejadian=("korban", "size"), korban=("korban", "sum"), korban_sipil=("korban_sipil", "sum"))
    )
    negara_utama = (
        k.groupby(["konflik", "tahun", "negara"]).size().reset_index(name="n")
        .sort_values("n", ascending=False)
        .drop_duplicates(["konflik", "tahun"])[["konflik", "tahun", "negara"]]
        .rename(columns={"negara": "negara_utama"})
    )
    return g.merge(negara_utama, on=["konflik", "tahun"], how="left").sort_values(["tahun", "korban"], ascending=[True, False])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--folder-mentah", default=str(FOLDER_DATA / "raw"), help="tempat file UCDP mentah disimpan")
    ap.add_argument("--tanpa-kandidat", action="store_true", help="lewati data kandidat 2026")
    args = ap.parse_args()
    mentah = Path(args.folder_mentah)

    print("1/4 Menyiapkan file mentah")
    ged = unduh(URL_GED, mentah / NAMA_FILE_GED)
    bagian = [rapikan_kejadian(baca_kejadian(ged, "final"))]
    if not args.tanpa_kandidat:
        kandidat = unduh(URL_KANDIDAT, mentah / NAMA_FILE_KANDIDAT)
        bagian.append(rapikan_kejadian(baca_kejadian(kandidat, "awal")))
    k = pd.concat(bagian, ignore_index=True)
    print(f"  total {len(k):,} kejadian, {k['tahun'].min()}-{k['tahun'].max()}")

    print("2/4 Agregasi per negara-tahun")
    agregasi_negara_tahun(k).to_csv(FOLDER_DATA / "korban_negara_tahun.csv", index=False)
    print("3/4 Agregasi grid untuk peta")
    agregasi_grid(k).to_csv(FOLDER_DATA / "grid_kejadian.csv", index=False)
    print("4/4 Agregasi per konflik")
    agregasi_konflik(k).to_csv(FOLDER_DATA / "konflik_tahun.csv", index=False)
    for f in ("korban_negara_tahun.csv", "grid_kejadian.csv", "konflik_tahun.csv"):
        p = FOLDER_DATA / f
        with open(p, encoding="utf-8") as isi:
            baris = sum(1 for _ in isi) - 1
        print(f"  {f}: {baris:,} baris, {p.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
