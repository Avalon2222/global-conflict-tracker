"""
analisis.py - Fungsi analisis murni (pandas saja, tanpa Streamlit) agar mudah diuji.

Semua fungsi menerima DataFrame hasil muat_data dan mengembalikan DataFrame/dict baru;
tidak ada yang mengubah input di tempat.
"""

from __future__ import annotations

import pandas as pd

# Ambang UCDP untuk intensitas konflik (per konflik per tahun)
AMBANG_KONFLIK = 25
AMBANG_PERANG = 1000


def filter_data(
    df: pd.DataFrame,
    tahun_awal: int,
    tahun_akhir: int,
    jenis: list[str] | None = None,
    wilayah: list[str] | None = None,
    sertakan_awal: bool = True,
) -> pd.DataFrame:
    """Saring tabel menurut rentang tahun, jenis kekerasan, wilayah, dan status data.

    `sertakan_awal=False` membuang baris berstatus "awal" (data kandidat UCDP
    yang belum melewati tinjauan akhir).
    """
    if tahun_awal > tahun_akhir:
        tahun_awal, tahun_akhir = tahun_akhir, tahun_awal  # rentang terbalik tetap dibaca wajar
    m = (df["tahun"] >= tahun_awal) & (df["tahun"] <= tahun_akhir)
    if jenis:
        m &= df["jenis"].isin(jenis)
    if wilayah and "wilayah" in df.columns:
        m &= df["wilayah"].isin(wilayah)
    if not sertakan_awal:
        m &= df["status"] != "awal"
    return df.loc[m].copy()


def ringkasan(df: pd.DataFrame) -> dict:
    """Angka-angka untuk kartu KPI."""
    if df.empty:
        return {"korban": 0, "kejadian": 0, "negara": 0, "negara_tertinggi": "-", "korban_tertinggi": 0, "tahun_terburuk": None, "korban_tahun_terburuk": 0}
    per_negara = df.groupby("negara")["korban"].sum().sort_values(ascending=False)
    per_tahun = df.groupby("tahun")["korban"].sum().sort_values(ascending=False)
    # Kalau semua baris korbannya nol, tidak ada negara atau tahun yang pantas disebut "tertinggi".
    ada_korban = per_negara.iloc[0] > 0
    return {
        "korban": int(df["korban"].sum()),
        "kejadian": int(df["kejadian"].sum()),
        "negara": int(df.loc[df["korban"] > 0, "negara"].nunique()),
        "negara_tertinggi": str(per_negara.index[0]) if ada_korban else "-",
        "korban_tertinggi": int(per_negara.iloc[0]),
        "tahun_terburuk": int(per_tahun.index[0]) if ada_korban else None,
        "korban_tahun_terburuk": int(per_tahun.iloc[0]),
    }


def per_tahun(df: pd.DataFrame, kolom_kelompok: str | None = None) -> pd.DataFrame:
    """Jumlah korban dan kejadian per tahun, opsional dipecah per kolom (jenis/wilayah)."""
    kunci = ["tahun"] + ([kolom_kelompok] if kolom_kelompok else [])
    agg = {"korban": ("korban", "sum"), "kejadian": ("kejadian", "sum")}
    if "korban_min" in df.columns:
        agg["korban_min"] = ("korban_min", "sum")
        agg["korban_max"] = ("korban_max", "sum")
    if "korban_sipil" in df.columns:
        agg["korban_sipil"] = ("korban_sipil", "sum")
    return df.groupby(kunci, as_index=False).agg(**agg).sort_values(kunci).reset_index(drop=True)


def top_negara(df: pd.DataFrame, n: int = 10, metrik: str = "korban") -> pd.DataFrame:
    """N negara dengan jumlah korban (atau kejadian) terbanyak dalam data yang diberikan.

    Negara baru yang belum punya kode ISO-3 (iso3 kosong saat dibaca dari CSV) tetap ikut dihitung.
    """
    g = (
        df.groupby(["negara", "iso3", "wilayah"], as_index=False, dropna=False)
        .agg(korban=("korban", "sum"), kejadian=("kejadian", "sum"))
        .sort_values(metrik, ascending=False)
        .head(n)
        .reset_index(drop=True)
    )
    g["peringkat"] = range(1, len(g) + 1)
    return g


def perubahan_tahunan(df: pd.DataFrame) -> pd.DataFrame:
    """Korban per tahun beserta selisih dan persentase perubahan dari tahun sebelumnya."""
    t = per_tahun(df)[["tahun", "korban", "kejadian"]].copy()
    if not t.empty:
        # Tahun tanpa satu baris pun (misalnya setelah filter jenis) berarti 0 korban, bukan
        # tahun yang dilompati; tanpa ini selisih 2019 -> 2021 tampil sebagai perubahan setahun.
        semua = range(int(t["tahun"].min()), int(t["tahun"].max()) + 1)
        t = t.set_index("tahun").reindex(semua, fill_value=0).rename_axis("tahun").reset_index()
    t["selisih"] = t["korban"].diff()
    sebelumnya = t["korban"].shift(1)
    t["perubahan_pct"] = (t["selisih"] / sebelumnya.where(sebelumnya > 0)) * 100
    return t


def pangsa_sipil(df: pd.DataFrame) -> pd.DataFrame:
    """Persentase korban sipil dari seluruh korban, per tahun."""
    t = per_tahun(df)
    if "korban_sipil" not in t.columns:  # kolom sipil opsional, sama seperti di per_tahun dan peta_negara
        t["korban_sipil"] = float("nan")
    t["pangsa_sipil_pct"] = (t["korban_sipil"] / t["korban"].where(t["korban"] > 0)) * 100
    return t[["tahun", "korban", "korban_sipil", "pangsa_sipil_pct"]]


def kategori_intensitas(korban: int) -> str:
    """Label intensitas mengikuti ambang UCDP: <25 tidak tercatat, 25-999 konflik minor, >=1000 perang."""
    if pd.isna(korban):
        return "Tidak diketahui"
    if korban >= AMBANG_PERANG:
        return "Perang"
    if korban >= AMBANG_KONFLIK:
        return "Konflik minor"
    return "Di bawah ambang"


def peta_negara(df: pd.DataFrame, metrik: str = "korban") -> pd.DataFrame:
    """Satu baris per negara untuk choropleth, lengkap dengan kategori intensitas."""
    agg = {"korban": ("korban", "sum"), "kejadian": ("kejadian", "sum")}
    if "korban_sipil" in df.columns:  # sama seperti per_tahun: kolom sipil opsional
        agg["korban_sipil"] = ("korban_sipil", "sum")
    g = df.groupby(["negara", "iso3", "wilayah"], as_index=False, dropna=False).agg(**agg)
    g["intensitas"] = g["korban"].apply(kategori_intensitas)
    g = g[g[metrik] > 0]
    return g.sort_values(metrik, ascending=False).reset_index(drop=True)


def profil_negara(negara_tahun: pd.DataFrame, konflik_tahun: pd.DataFrame, negara: str, n_konflik: int = 8) -> dict:
    """Kumpulan tabel untuk tab satu negara: tren per jenis, konflik terbesar, tahun puncak."""
    d = negara_tahun[negara_tahun["negara"] == negara]
    tren = per_tahun(d, "jenis")
    total = per_tahun(d)
    konflik = (
        konflik_tahun[konflik_tahun["negara_utama"] == negara]
        .groupby(["konflik", "jenis"], as_index=False)
        .agg(korban=("korban", "sum"), kejadian=("kejadian", "sum"), tahun_awal=("tahun", "min"), tahun_akhir=("tahun", "max"))
        .sort_values("korban", ascending=False)
        .head(n_konflik)
        .reset_index(drop=True)
    )
    puncak = total.sort_values("korban", ascending=False).head(1)
    return {
        "tren": tren,
        "total": total,
        "konflik": konflik,
        "korban": int(d["korban"].sum()),
        "kejadian": int(d["kejadian"].sum()),
        "korban_sipil": int(d["korban_sipil"].sum()) if "korban_sipil" in d.columns else 0,
        # Seperti ringkasan(): kalau semua tahun nol korban, tidak ada tahun yang pantas disebut puncak.
        "tahun_puncak": int(puncak["tahun"].iloc[0]) if not puncak.empty and puncak["korban"].iloc[0] > 0 else None,
        "korban_puncak": int(puncak["korban"].iloc[0]) if not puncak.empty else 0,
        "tahun_aktif": int((total["korban"] >= AMBANG_KONFLIK).sum()),
    }


def konflik_teratas(konflik_tahun: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Konflik dengan korban terbanyak dalam data yang diberikan (sudah difilter tahun)."""
    return (
        konflik_tahun.groupby(["konflik", "jenis"], as_index=False)
        .agg(korban=("korban", "sum"), kejadian=("kejadian", "sum"), tahun_awal=("tahun", "min"), tahun_akhir=("tahun", "max"))
        .sort_values("korban", ascending=False)
        .head(n)
        .reset_index(drop=True)
    )
