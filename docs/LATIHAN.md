# 🏋️ Latihan

Diurutkan dari yang mudah ke yang lebih menantang. Setiap latihan dilengkapi petunjuk dan kunci jawaban yang dapat
dibuka. Usahakan mencoba minimal 10 menit sebelum membuka kunci. Setelah setiap latihan, jalankan
`python -m pytest tests/` dan `streamlit run app.py`.

---

### Latihan 1 — Mengubah nilai bawaan filter ⭐

Saat ini rentang tahun bawaan adalah 2000–2026. Ubah agar aplikasi dibuka dengan rentang **2010–2026** dan hanya
jenis **Konflik negara** yang aktif.

<details><summary>Petunjuk</summary>
Cari `st.slider("Rentang tahun", ...)` dan `st.multiselect("Jenis kekerasan", ...)` di bagian sidebar `app.py`.
Argumen `default=` pada multiselect menerima list.
</details>

<details><summary>Kunci</summary>

```python
tahun_awal, tahun_akhir = st.slider("Rentang tahun", TAHUN_MIN, TAHUN_MAX, (2010, TAHUN_MAX))
jenis_pilihan = st.multiselect("Jenis kekerasan", URUTAN_JENIS, default=["Konflik negara"], ...)
```
</details>

---

### Latihan 2 — KPI baru: rata-rata korban per kejadian ⭐

Tambahkan kartu keenam di baris KPI yang menampilkan **rata-rata korban per kejadian** (korban ÷ kejadian) dengan
satu angka desimal, misalnya `7,3`.

<details><summary>Petunjuk</summary>
`ring["korban"]` dan `ring["kejadian"]` sudah tersedia. Ubah `st.columns(5)` menjadi `st.columns(6)`. Format
desimal gaya Indonesia: `f"{nilai:.1f}".replace(".", ",")`.
</details>

<details><summary>Kunci</summary>

```python
k1, k2, k3, k4, k5, k6 = st.columns(6)
...
rata = ring["korban"] / ring["kejadian"] if ring["kejadian"] else 0
k6.metric("Korban per kejadian", f"{rata:.1f}".replace(".", ","))
```
Dengan filter bawaan nilainya sekitar 7. Bandingkan dengan rentang 1994–1994: genosida Rwanda membuatnya ratusan.
</details>

---

### Latihan 3 — Fungsi baru + tesnya: negara dengan kenaikan terbesar ⭐⭐

Tulis fungsi `kenaikan_terbesar(df, tahun, n=5)` di `src/analisis.py` yang mengembalikan `n` negara dengan
**kenaikan korban terbesar** dari `tahun - 1` ke `tahun` (kolom: `negara`, `sebelum`, `sesudah`, `selisih`). Lalu
tulis satu tes untuknya memakai `df_kecil`.

<details><summary>Petunjuk</summary>
Jumlahkan korban per negara untuk dua tahun secara terpisah (`groupby("negara")["korban"].sum()`), gabungkan dengan
`pd.concat([...], axis=1).fillna(0)`, hitung selisih, urutkan menurun. Pada `df_kecil`, dari 2020 ke 2021 negara A
naik dari 100 menjadi 1.550.
</details>

<details><summary>Kunci</summary>

```python
def kenaikan_terbesar(df: pd.DataFrame, tahun: int, n: int = 5) -> pd.DataFrame:
    sebelum = df[df["tahun"] == tahun - 1].groupby("negara")["korban"].sum()
    sesudah = df[df["tahun"] == tahun].groupby("negara")["korban"].sum()
    t = pd.concat([sebelum.rename("sebelum"), sesudah.rename("sesudah")], axis=1).fillna(0)
    t["selisih"] = t["sesudah"] - t["sebelum"]
    return t.sort_values("selisih", ascending=False).head(n).reset_index()
```

```python
def test_kenaikan_terbesar(df_kecil):
    k = analisis.kenaikan_terbesar(df_kecil, 2021, n=1)
    assert k.iloc[0]["negara"] == "A"
    assert k.iloc[0]["selisih"] == 1450
```
Tampilkan hasilnya di tab Tren sebagai tabel kecil untuk `tahun_akhir`.
</details>

---

### Latihan 4 — Korban per 100 ribu penduduk ⭐⭐

Angka absolut tidak adil untuk negara kecil. Tambahkan file `data/populasi.csv` (kolom `iso3,populasi`) untuk
10–20 negara teratas, gabungkan ke `peta_negara`, dan tampilkan pilihan metrik ketiga **"Korban per 100 ribu
penduduk"** pada choropleth.

<details><summary>Petunjuk</summary>
Populasi dapat diambil dari Wikipedia atau World Bank (tahun terbaru). Gabungkan dengan
`negara_peta.merge(pop, on="iso3", how="left")`, lalu `korban / populasi * 100_000`. Negara tanpa populasi akan NaN;
buang dengan `.dropna()`.
</details>

<details><summary>Kunci</summary>

```python
pop = pd.read_csv(FOLDER_DATA / "populasi.csv")
negara_peta = negara_peta.merge(pop, on="iso3", how="left")
negara_peta["per_100rb"] = negara_peta["korban"] / negara_peta["populasi"] * 100_000
```
Setelah dinormalisasi, Suriah, Sudan Selatan, dan Eritrea biasanya naik jauh melampaui negara berpenduduk besar.
Ini contoh bagaimana pilihan *denominator* mengubah cerita.
</details>

---

### Latihan 5 — Choropleth beranimasi per tahun ⭐⭐⭐

Buat versi choropleth yang bergerak dari tahun ke tahun dengan tombol play (`animation_frame`).

<details><summary>Petunjuk</summary>
`animation_frame` membutuhkan satu baris per `iso3 × tahun`, bukan agregat satu baris per negara. Buat
`per_negara_tahun = df.groupby(["iso3", "negara", "tahun"], as_index=False)["korban"].sum()`, tambahkan kolom log,
lalu `px.choropleth(..., animation_frame="tahun", range_color=(0, maks))`. `range_color` harus ditetapkan agar skala
warna tidak berubah antar frame. Negara yang tidak punya kejadian pada suatu tahun akan hilang dari frame itu; untuk
mengisinya pakai `pivot_table(fill_value=0)` lalu `melt`.
</details>

<details><summary>Kunci</summary>

```python
pnt = df.groupby(["iso3", "negara", "tahun"], as_index=False)["korban"].sum()
lengkap = pnt.pivot_table(index=["iso3", "negara"], columns="tahun", values="korban", fill_value=0).reset_index()
lengkap = lengkap.melt(id_vars=["iso3", "negara"], var_name="tahun", value_name="korban")
lengkap["log_nilai"] = np.log10(lengkap["korban"].clip(lower=1))
fig = px.choropleth(lengkap.sort_values("tahun"), locations="iso3", color="log_nilai", hover_name="negara",
                    animation_frame="tahun", range_color=(0, lengkap["log_nilai"].max()),
                    color_continuous_scale=SKALA_PANAS, projection="natural earth")
```
`clip(lower=1)` membuat log10(0) menjadi 0, bukan minus tak hingga.
</details>

---

### Latihan 6 — Memperbarui data secara otomatis ⭐⭐⭐

UCDP merilis data kandidat setiap bulan. Buat GitHub Actions workflow yang setiap tanggal 15 menjalankan
`python -m src.siapkan_data`, lalu membuat commit jika ada perubahan di `data/`.

<details><summary>Petunjuk</summary>
Gunakan `on: schedule: - cron: "0 3 15 * *"` dan `workflow_dispatch`. Setelah skrip selesai, periksa
`git status --porcelain data/`; jika tidak kosong, commit dan push dengan token bawaan `GITHUB_TOKEN`. Karena URL
kandidat berubah nama tiap bulan, tambahkan opsi `--url-kandidat` pada skrip atau cari nama file terbaru dari
halaman unduhan UCDP.
</details>

<details><summary>Kunci</summary>

```yaml
name: Update data UCDP
on:
  schedule:
    - cron: "0 3 15 * *"
  workflow_dispatch:
jobs:
  update:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt
      - run: python -m src.siapkan_data
      - run: python -m pytest tests/ -q
      - run: |
          if [ -n "$(git status --porcelain data/)" ]; then
            git config user.name "github-actions[bot]"
            git config user.email "github-actions[bot]@users.noreply.github.com"
            git add data/ && git commit -m "Update data UCDP" && git push
          fi
```
Menjalankan tes sebelum commit memastikan data baru tidak merusak aplikasi yang sedang live.
</details>
