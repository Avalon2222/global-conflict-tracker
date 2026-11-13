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
