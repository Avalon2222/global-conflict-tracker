"""
Pengujian untuk src/siapkan_data.py (pipeline UCDP mentah -> CSV ringkas).

Data mentah UCDP asli ~270 MB, jadi di sini dipakai beberapa baris tiruan
dengan format kolom yang sama persis.
"""

import pandas as pd
import pytest

from src import siapkan_data


@pytest.fixture
def mentah() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "year": [2024, 2024, 2024, 2025],
            "type_of_violence": [1, 1, 3, 2],
            "conflict_new_id": [10, 10, 11, 12],
            "conflict_name": ["Ukraina: Rusia", "Ukraina: Rusia", "IS - warga sipil", "Geng A - Geng B"],
            "side_a": ["Government of Russia", "Government of Russia", "IS", "Geng A"],
            "side_b": ["Government of Ukraine", "Government of Ukraine", "Civilians", "Geng B"],
            "latitude": [48.10, 48.20, 34.0, 18.5],
            "longitude": [37.60, 37.70, 43.0, -72.3],
            "country": ["Ukraine", "Ukraine", "Iraq", "Haiti"],
            "region": ["Europe", "Europe", "Middle East", "Americas"],
            "best": [10, 5, 3, 7],
            "high": [12, 6, 4, 9],
            "low": [8, 5, 3, 6],
            "deaths_civilians": [1, 0, 3, 2],
            "status": ["final", "final", "final", "awal"],
        }
    )


def test_rapikan_kejadian_menerjemahkan_kolom(mentah):
    k = siapkan_data.rapikan_kejadian(mentah)
    assert k["negara"].tolist()[:3] == ["Ukraina", "Ukraina", "Irak"]
    assert k["iso3"].tolist() == ["UKR", "UKR", "IRQ", "HTI"]
    assert k["jenis"].tolist() == ["Konflik negara", "Konflik negara", "Kekerasan sepihak", "Konflik non-negara"]
    assert k["korban"].dtype == "int64"
    assert (k["korban_min"] <= k["korban"]).all() and (k["korban"] <= k["korban_max"]).all()


def test_rapikan_kejadian_negara_asing_tetap_lolos(mentah, capsys):
    mentah.loc[3, "country"] = "Negara Fiksi"
    k = siapkan_data.rapikan_kejadian(mentah)
    assert k.loc[3, "negara"] == "Negara Fiksi"     # nama asli dipertahankan
    assert k.loc[3, "iso3"] == ""
    assert "Negara Fiksi" in capsys.readouterr().err


def test_agregasi_negara_tahun_menjumlahkan(mentah):
    g = siapkan_data.agregasi_negara_tahun(siapkan_data.rapikan_kejadian(mentah))
    ukr = g[g["iso3"] == "UKR"].iloc[0]
    assert ukr["kejadian"] == 2
    assert ukr["korban"] == 15
    assert ukr["korban_sipil"] == 1
    assert g["korban"].sum() == mentah["best"].sum()  # tidak ada korban yang hilang


def test_agregasi_grid_membulatkan_ke_sel(mentah):
    g = siapkan_data.agregasi_grid(siapkan_data.rapikan_kejadian(mentah), resolusi=0.5)
    ukr = g[g["negara"] == "Ukraina"]
    assert len(ukr) == 1                            # 48.1/37.6 dan 48.2/37.7 masuk sel yang sama
    assert (ukr["lat"].iloc[0], ukr["lon"].iloc[0]) == (48.0, 37.5)
    assert ukr["kejadian"].iloc[0] == 2
    assert g["korban"].sum() == mentah["best"].sum()


def test_agregasi_konflik_negara_utama(mentah):
    g = siapkan_data.agregasi_konflik(siapkan_data.rapikan_kejadian(mentah))
    ukr = g[g["konflik"] == "Ukraina: Rusia"].iloc[0]
    assert ukr["korban"] == 15 and ukr["negara_utama"] == "Ukraina"
    # urut per tahun, lalu korban terbanyak dulu
    assert g["tahun"].is_monotonic_increasing
    assert g[g["tahun"] == 2024]["korban"].tolist() == [15, 3]


def test_baca_kejadian_ambil_kolom_dan_tandai_status(mentah, tmp_path):
    path = tmp_path / "ged.csv"
    mentah.assign(kolom_lain="dibuang").to_csv(path, index=False)
    df = siapkan_data.baca_kejadian(path, "awal")
    assert set(df.columns) == set(siapkan_data.KOLOM) | {"status"}
    assert (df["status"] == "awal").all()
    assert len(df) == len(mentah)


class _Respons:
    def __init__(self, isi: bytes):
        self.content = isi

    def raise_for_status(self):
        pass


def _pasang_unduhan(monkeypatch, isi: bytes) -> list[str]:
    import requests

    diminta: list[str] = []

    def palsu(url, timeout):
        diminta.append(url)
        return _Respons(isi)

    monkeypatch.setattr(requests, "get", palsu)
    return diminta


def test_unduh_pakai_file_lokal_kalau_sudah_ada(monkeypatch, tmp_path):
    diminta = _pasang_unduhan(monkeypatch, b"tidak dipakai")
    tujuan = tmp_path / "ged.csv"
    tujuan.write_text("lama", encoding="utf-8")
    assert siapkan_data.unduh("https://contoh/ged.csv", tujuan) == tujuan
    assert diminta == [] and tujuan.read_text(encoding="utf-8") == "lama"


def test_unduh_ekstrak_dari_zip(monkeypatch, tmp_path):
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("GEDEvent_v25_1.csv", "id,year\n1,2024\n")
        z.writestr("README.txt", "abaikan")
    _pasang_unduhan(monkeypatch, buf.getvalue())
    tujuan = tmp_path / "raw" / "GEDEvent_v25_1.csv"
    siapkan_data.unduh("https://contoh/ged.zip", tujuan)
    assert tujuan.read_text(encoding="utf-8").startswith("id,year")
    assert not (tmp_path / "raw" / "README.txt").exists()


def test_unduh_csv_langsung(monkeypatch, tmp_path):
    _pasang_unduhan(monkeypatch, b"id,year\n2,2026\n")
    tujuan = tmp_path / "kandidat.csv"
    siapkan_data.unduh("https://contoh/kandidat.csv", tujuan)
    assert tujuan.read_bytes() == b"id,year\n2,2026\n"
