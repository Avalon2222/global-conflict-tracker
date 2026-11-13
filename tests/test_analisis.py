"""
Pengujian untuk src/analisis.py, src/negara.py, dan konsistensi data di folder data/.
Jalankan:  python -m pytest tests/ -v
"""

import pandas as pd
import pytest

from src import analisis, muat_data
from src.negara import PETA_NEGARA, iso3, nama_indonesia


# ----------------------------------------------------------------------------
# Data buatan kecil agar pengujian fungsi tidak bergantung pada CSV besar
# ----------------------------------------------------------------------------
@pytest.fixture
def df_kecil() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "negara": ["A", "A", "A", "B", "B", "C"],
            "iso3": ["AAA", "AAA", "AAA", "BBB", "BBB", "CCC"],
            "wilayah": ["Asia", "Asia", "Asia", "Afrika", "Afrika", "Eropa"],
            "tahun": [2020, 2021, 2021, 2020, 2021, 2021],
            "jenis": ["Konflik negara", "Konflik negara", "Kekerasan sepihak", "Konflik non-negara", "Konflik negara", "Konflik negara"],
            "status": ["final", "final", "final", "final", "awal", "final"],
            "kejadian": [10, 20, 5, 3, 4, 1],
            "korban": [100, 1500, 50, 30, 40, 0],
            "korban_min": [90, 1200, 50, 30, 40, 0],
            "korban_max": [150, 2000, 60, 35, 50, 1],
            "korban_sipil": [10, 300, 50, 0, 0, 0],
        }
    )


def test_filter_tahun_dan_jenis(df_kecil):
    hasil = analisis.filter_data(df_kecil, 2021, 2021, ["Konflik negara"])
    assert set(hasil["tahun"]) == {2021}
    assert set(hasil["jenis"]) == {"Konflik negara"}
    assert len(hasil) == 3


def test_filter_buang_data_awal(df_kecil):
    tanpa_awal = analisis.filter_data(df_kecil, 2000, 2030, sertakan_awal=False)
    assert "awal" not in set(tanpa_awal["status"])
    assert len(tanpa_awal) == len(df_kecil) - 1


def test_filter_wilayah(df_kecil):
    hasil = analisis.filter_data(df_kecil, 2000, 2030, wilayah=["Eropa"])
    assert hasil["negara"].tolist() == ["C"]


def test_ringkasan(df_kecil):
    r = analisis.ringkasan(df_kecil)
    assert r["korban"] == 1720
    assert r["kejadian"] == 43
    assert r["negara"] == 2  # C punya 0 korban, tidak dihitung
    assert r["negara_tertinggi"] == "A" and r["korban_tertinggi"] == 1650
    assert r["tahun_terburuk"] == 2021


def test_ringkasan_kosong(df_kecil):
    r = analisis.ringkasan(df_kecil.iloc[0:0])
    assert r["korban"] == 0 and r["negara_tertinggi"] == "-"


def test_per_tahun_dan_kelompok(df_kecil):
    total = analisis.per_tahun(df_kecil)
    assert total.set_index("tahun")["korban"].to_dict() == {2020: 130, 2021: 1590}
    per_jenis = analisis.per_tahun(df_kecil, "jenis")
    baris = per_jenis[(per_jenis["tahun"] == 2021) & (per_jenis["jenis"] == "Konflik negara")]
    assert int(baris["korban"].iloc[0]) == 1540


def test_top_negara_urut_dan_peringkat(df_kecil):
    top = analisis.top_negara(df_kecil, 2)
    assert top["negara"].tolist() == ["A", "B"]
    assert top["peringkat"].tolist() == [1, 2]
    top_kejadian = analisis.top_negara(df_kecil, 1, metrik="kejadian")
    assert top_kejadian["negara"].iloc[0] == "A"


def test_perubahan_tahunan(df_kecil):
    p = analisis.perubahan_tahunan(df_kecil).set_index("tahun")
    assert pd.isna(p.loc[2020, "selisih"])
    assert p.loc[2021, "selisih"] == 1460
    assert p.loc[2021, "perubahan_pct"] == pytest.approx(1460 / 130 * 100)


def test_pangsa_sipil(df_kecil):
    s = analisis.pangsa_sipil(df_kecil).set_index("tahun")
    assert s.loc[2020, "pangsa_sipil_pct"] == pytest.approx(10 / 130 * 100)
    assert s.loc[2021, "pangsa_sipil_pct"] == pytest.approx(350 / 1590 * 100)


@pytest.mark.parametrize("korban,label", [(0, "Di bawah ambang"), (24, "Di bawah ambang"), (25, "Konflik minor"), (999, "Konflik minor"), (1000, "Perang"), (50000, "Perang")])
def test_kategori_intensitas(korban, label):
    assert analisis.kategori_intensitas(korban) == label


def test_peta_negara_buang_nol(df_kecil):
    p = analisis.peta_negara(df_kecil)
    assert "C" not in set(p["negara"])
    assert p.iloc[0]["negara"] == "A" and p.iloc[0]["intensitas"] == "Perang"


def test_profil_negara(df_kecil):
    konflik = pd.DataFrame(
        {
            "konflik": ["A: Government", "A: Government", "X - Civilians"],
            "jenis": ["Konflik negara", "Konflik negara", "Kekerasan sepihak"],
            "tahun": [2020, 2021, 2021],
            "status": ["final"] * 3,
            "kejadian": [10, 20, 5],
            "korban": [100, 1500, 50],
            "korban_sipil": [10, 300, 50],
            "negara_utama": ["A", "A", "A"],
        }
    )
    p = analisis.profil_negara(df_kecil, konflik, "A")
    assert p["korban"] == 1650 and p["tahun_puncak"] == 2021 and p["korban_puncak"] == 1550
    assert p["tahun_aktif"] == 2
    assert p["konflik"]["konflik"].tolist() == ["A: Government", "X - Civilians"]
    assert p["konflik"].iloc[0]["tahun_awal"] == 2020 and p["konflik"].iloc[0]["tahun_akhir"] == 2021


# ----------------------------------------------------------------------------
# Pemetaan negara
# ----------------------------------------------------------------------------
def test_pemetaan_negara():
    assert iso3("DR Congo (Zaire)") == "COD"
    assert nama_indonesia("Myanmar (Burma)") == "Myanmar"
    assert iso3("Negara Tidak Ada") == ""
    assert nama_indonesia("Negara Tidak Ada") == "Negara Tidak Ada"
    kode = [v[0] for v in PETA_NEGARA.values()]
    assert len(kode) == len(set(kode)), "kode ISO-3 harus unik"
    assert all(len(k) == 3 and k.isupper() for k in kode)


# ----------------------------------------------------------------------------
# Data sungguhan di folder data/
# ----------------------------------------------------------------------------
def test_dataset_bisa_dimuat():
    nt = muat_data.muat_negara_tahun()
    grid = muat_data.muat_grid()
    konflik = muat_data.muat_konflik()
    assert nt["tahun"].min() == 1989 and nt["tahun"].max() >= 2025
    assert (nt["iso3"].str.len() == 3).all(), "setiap negara harus punya kode ISO-3"
    assert set(nt["jenis"]) == set(muat_data.URUTAN_JENIS)
    assert grid["lat"].between(-90, 90).all() and grid["lon"].between(-180, 180).all()
    assert set(konflik["status"]) <= {"final", "awal"}


def test_total_korban_konsisten_antar_tabel():
    """Ketiga tabel berasal dari kejadian yang sama, jadi total per tahun harus identik."""
    nt = muat_data.muat_negara_tahun().groupby("tahun")["korban"].sum()
    grid = muat_data.muat_grid().groupby("tahun")["korban"].sum()
    konflik = muat_data.muat_konflik().groupby("tahun")["korban"].sum()
    pd.testing.assert_series_equal(nt, grid, check_names=False)
    pd.testing.assert_series_equal(nt, konflik, check_names=False)


def test_angka_acuan_ucdp():
    """Angka yang dikenal luas: genosida Rwanda 1994 adalah tahun paling mematikan dalam data."""
    nt = muat_data.muat_negara_tahun()
    per_tahun = nt.groupby("tahun")["korban"].sum()
    assert per_tahun.idxmax() == 1994
    rwanda_1994 = nt[(nt["negara"] == "Rwanda") & (nt["tahun"] == 1994)]["korban"].sum()
    assert rwanda_1994 > 500_000


def test_kolom_teks_kenal_dtype_pandas_3(tmp_path, monkeypatch):
    (tmp_path / "uji.csv").write_text("negara,catatan,korban\nA,,1\nB,ok,2\n")
    monkeypatch.setattr(muat_data, "FOLDER_DATA", tmp_path)
    df = muat_data._baca("uji.csv")
    assert df["catatan"].tolist() == ["", "ok"]       # sel kosong jadi "", bukan NaN
    assert df["korban"].tolist() == [1, 2]            # kolom angka tidak disentuh


def test_konflik_teratas_menjumlah_lintas_tahun():
    kt = pd.DataFrame(
        {
            "konflik": ["X", "X", "Y", "Z"],
            "jenis": ["Konflik negara", "Konflik negara", "Kekerasan sepihak", "Konflik non-negara"],
            "tahun": [2020, 2022, 2021, 2021],
            "korban": [100, 300, 250, 5],
            "kejadian": [4, 6, 9, 1],
        }
    )
    hasil = analisis.konflik_teratas(kt, n=2)
    assert list(hasil["konflik"]) == ["X", "Y"]     # X total 400 mengalahkan Y 250
    x = hasil.iloc[0]
    assert x["korban"] == 400 and x["kejadian"] == 10
    assert (x["tahun_awal"], x["tahun_akhir"]) == (2020, 2022)


def test_validasi_tolak_kolom_hilang_dan_file_kosong():
    df = pd.DataFrame({"negara": ["Sudan"], "tahun": [2024]})
    muat_data._validasi(df, ["negara", "tahun"], "uji.csv")   # lolos tanpa error
    with pytest.raises(ValueError, match=r"uji.csv: kolom hilang -> \['korban'\]"):
        muat_data._validasi(df, ["negara", "korban"], "uji.csv")
    with pytest.raises(ValueError, match="file kosong"):
        muat_data._validasi(df.iloc[0:0], ["negara"], "uji.csv")


def test_muat_grid_dan_konflik_punya_kolom_wajib():
    grid = muat_data.muat_grid()
    assert grid["lat"].between(-90, 90).all() and grid["lon"].between(-180, 180).all()
    konflik = muat_data.muat_konflik()
    assert (konflik["korban"] >= 0).all()
    assert not konflik["konflik"].eq("").any()


def _konflik_kosong():
    return pd.DataFrame(columns=["konflik", "jenis", "tahun", "korban", "kejadian", "negara_utama"])


def test_profil_negara_yang_tidak_ada_di_data(df_kecil):
    p = analisis.profil_negara(df_kecil, _konflik_kosong(), "Negara Fiktif")
    assert p["korban"] == 0 and p["kejadian"] == 0
    assert p["tahun_puncak"] is None and p["korban_puncak"] == 0
    assert p["tahun_aktif"] == 0 and p["konflik"].empty


def test_peta_negara_buang_negara_tanpa_korban(df_kecil):
    p = analisis.peta_negara(df_kecil)
    assert "C" not in set(p["negara"])                     # korban 0
    assert p["korban"].is_monotonic_decreasing
    assert p.set_index("negara").loc["A", "intensitas"] == "Perang"   # 1650 korban


def test_konflik_teratas_gabung_tahun_dan_batasi_n():
    k = pd.DataFrame({
        "konflik": ["X", "X", "Y", "Z"],
        "jenis": ["Konflik negara"] * 4,
        "tahun": [2019, 2021, 2020, 2020],
        "korban": [10, 30, 25, 5],
        "kejadian": [1, 2, 3, 1],
    })
    t = analisis.konflik_teratas(k, n=2)
    assert t["konflik"].tolist() == ["X", "Y"]
    x = t.iloc[0]
    assert x["korban"] == 40 and x["tahun_awal"] == 2019 and x["tahun_akhir"] == 2021


def test_perubahan_tahunan_tahun_pertama_kosong(df_kecil):
    p = analisis.perubahan_tahunan(df_kecil)
    assert pd.isna(p["selisih"].iloc[0]) and pd.isna(p["perubahan_pct"].iloc[0])
