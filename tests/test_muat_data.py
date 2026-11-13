"""Tes pemuat data (src/muat_data.py): deteksi kolom teks, validasi, dan isi file di repo."""

import numpy as np
import pandas as pd
import pytest

from src import muat_data


def test_kolom_teks_kenali_object_dan_string():
    assert muat_data._kolom_teks(pd.Series(["a", None], dtype=object))
    assert muat_data._kolom_teks(pd.Series(["a", None], dtype="string"))
    assert not muat_data._kolom_teks(pd.Series([1, 2]))
    assert not muat_data._kolom_teks(pd.Series([1.5, np.nan]))


def test_baca_isi_teks_kosong_tapi_biarkan_angka(tmp_path, monkeypatch):
    (tmp_path / "uji.csv").write_text("negara,korban\nIndonesia,5\n,\n", encoding="utf-8")
    monkeypatch.setattr(muat_data, "FOLDER_DATA", tmp_path)
    df = muat_data._baca("uji.csv")
    assert df["negara"].tolist() == ["Indonesia", ""]
    assert pd.isna(df.loc[1, "korban"])     # angka kosong tetap NaN, bukan teks ""


def test_validasi_kolom_hilang_dan_file_kosong():
    with pytest.raises(ValueError, match="kolom hilang"):
        muat_data._validasi(pd.DataFrame({"a": [1]}), ["a", "b"], "x.csv")
    with pytest.raises(ValueError, match="file kosong"):
        muat_data._validasi(pd.DataFrame(columns=["a"]), ["a"], "x.csv")
    muat_data._validasi(pd.DataFrame({"a": [1]}), ["a"], "x.csv")


def test_tabel_negara_tahun_di_repo_konsisten():
    df = muat_data.muat_negara_tahun()
    assert set(df["jenis"]) <= set(muat_data.URUTAN_JENIS)
    assert (df["korban"] >= 0).all() and (df["kejadian"] >= 0).all()
    assert df["iso3"].str.len().eq(3).all()
    # Satu baris per negara x tahun x jenis x status.
    assert not df.duplicated(["negara", "tahun", "jenis", "status"]).any()


def test_grid_dan_konflik_di_repo_masuk_akal():
    grid = muat_data.muat_grid()
    assert grid["lat"].between(-90, 90).all() and grid["lon"].between(-180, 180).all()
    konflik = muat_data.muat_konflik()
    assert set(konflik["jenis"]) <= set(muat_data.URUTAN_JENIS)
    assert konflik["konflik"].ne("").all()
    # Rentang tahun ketiga tabel sama, supaya filter tahun di dashboard berlaku seragam.
    negara = muat_data.muat_negara_tahun()
    assert grid["tahun"].max() == negara["tahun"].max() == konflik["tahun"].max()
