# Sumber data & catatan metodologi

Dikompilasi 2 November 2026. Seluruh data berasal dari **Uppsala Conflict Data Program (UCDP)**, Universitas
Uppsala, yang dapat diunduh siapa saja tanpa registrasi dari https://ucdp.uu.se/downloads/.

## Dua sumber yang digabung

| Sumber | Versi | Cakupan | Status | Lisensi |
|---|---|---|---|---|
| UCDP Georeferenced Event Dataset (GED) | 26.1 (rilis 2026) | 1 Jan 1989 – 31 Des 2025, 417.968 kejadian | `final` | CC BY 4.0 |
| UCDP Candidate Events Dataset | v26.0.1–26.0.9 (kumulatif) | 1 Jan – 30 Sep 2026, 16.633 kejadian | `awal` | CC BY 4.0 |

Data kandidat dikodekan setiap bulan dengan tinjauan yang lebih ringan dan akan direvisi ketika masuk ke GED versi
berikutnya. Karena itu setiap baris membawa kolom `status`, dan aplikasi menyediakan toggle untuk mengecualikannya.

Kutipan yang diminta UCDP:

- Davies, S., Pettersson, T., Sollenberg, M. & Öberg, M. (2026). Organized violence 1989–2025. *Journal of Peace Research*.
- Sundberg, R. & Melander, E. (2013). Introducing the UCDP Georeferenced Event Dataset. *Journal of Peace Research* 50(4), 523–532.
- Hegre, H. dkk. (2020). Introducing the UCDP Candidate Events Dataset. *Research & Politics* 7(3).

## Definisi UCDP yang dipakai

- **Kejadian (event):** satu peristiwa kekerasan terorganisasi yang menyebabkan minimal satu kematian, pada satu
  lokasi dan tanggal (atau rentang tanggal) tertentu, dengan pihak yang teridentifikasi.
- **Tiga jenis kekerasan** (`type_of_violence`): 1 = *state-based* (Konflik negara), 2 = *non-state* (Konflik non-negara),
  3 = *one-sided* (Kekerasan sepihak terhadap warga sipil).
- **Ambang masuk data:** suatu konflik/pihak hanya dikodekan jika pernah mencapai 25 korban jiwa dalam satu tahun
  kalender. Setelah masuk, seluruh kejadiannya (termasuk yang 1 korban) dicatat.
- **best / low / high:** tiga estimasi korban per kejadian. `best` adalah angka yang paling dapat dipertanggungjawabkan;
  `low` dan `high` adalah batas bawah dan atas dari sumber yang berbeda-beda.
- **deaths_civilians:** korban sipil, hanya diisi jika sumber menyebutnya secara eksplisit. Angkanya cenderung terlalu rendah.

## Cara data diolah (`src/siapkan_data.py`)

Data mentah (~270 MB, 434.601 baris) tidak disimpan di repositori. Skrip mengunduh, lalu membuat tiga tabel ringkas:

### korban_negara_tahun.csv (4.169 baris, 0,3 MB)
Satu baris per `negara × tahun × jenis × status`. Kolom: `negara` (nama Indonesia), `iso3`, `wilayah`, `tahun`, `jenis`,
`status`, `kejadian`, `korban` (= jumlah `best`), `korban_min` (= jumlah `low`), `korban_max` (= jumlah `high`), `korban_sipil`.

### grid_kejadian.csv (62.580 baris, 3,2 MB)
Koordinat setiap kejadian dibulatkan ke sel grid **0,5°** (sekitar 55 km di khatulistiwa), lalu dijumlahkan per
`tahun × sel × jenis × negara × status`. Ini yang dipakai peta titik. Koordinat asli UCDP sendiri memiliki tingkat presisi
berbeda (`where_prec` 1 = titik persis, hingga 7 = hanya diketahui negaranya); kejadian dengan presisi rendah
ditempatkan UCDP di titik tengah wilayah administratif, sehingga pada peta dapat tampak "menumpuk" di ibu kota provinsi.

### konflik_tahun.csv (8.983 baris, 0,6 MB)
Jumlah per `konflik × jenis × tahun × status`, dengan kolom `negara_utama` = negara tempat kejadian terbanyak konflik
itu terjadi pada tahun tersebut. Nama konflik mengikuti UCDP (`conflict_name`): `Negara: Government` untuk perang
melawan pemerintah, `Negara: Wilayah` untuk konflik teritorial, `A - B` untuk konflik non-negara, `X - Civilians` untuk
kekerasan sepihak.

Ketiga tabel berasal dari kejadian yang sama, sehingga total korban per tahun identik di ketiganya
(diperiksa oleh `tests/test_analisis.py`).

## Pemetaan nama negara (`src/negara.py`)

UCDP memakai nama negara versi Gleditsch & Ward dan menetapkan kejadian lama ke negara penerusnya
(misalnya `Russia (Soviet Union)`, `Serbia (Yugoslavia)`, `Yemen (North Yemen)`). Setiap nama dipetakan manual ke
kode ISO-3 (untuk choropleth Plotly) dan nama Indonesia. Nama Indonesia mengikuti kebiasaan umum
(Tiongkok, Pantai Gading, RD Kongo).

## Keterbatasan

1. UCDP hanya mencatat **kematian langsung** akibat kekerasan yang dapat diverifikasi. Kematian tidak langsung
   (kelaparan, penyakit, runtuhnya layanan kesehatan) tidak termasuk, padahal sering kali jauh lebih besar.
2. **Liputan media tidak merata.** Konflik yang sulit dijangkau wartawan (Tigray 2020–2022, Myanmar, Sudan) hampir
   pasti kurang tercatat. Rentang `low`–`high` yang lebar adalah sinyalnya.
3. **Negara mengikuti lokasi kejadian**, bukan kewarganegaraan korban atau pihak. Serangan lintas batas tercatat di
   negara tempat kejadian.
4. **Kekerasan kriminal** hanya masuk jika pelakunya kelompok terorganisasi yang memenuhi ambang (misalnya kartel di
   Meksiko dikodekan sebagai konflik non-negara). Pembunuhan biasa tidak masuk.
5. **Data 2026 belum final** dan hanya sampai September, sehingga 2026 tidak dapat dibandingkan langsung dengan tahun penuh.
6. Agregasi grid 0,5° **mengorbankan presisi lokasi** demi ukuran file; untuk analisis spasial detail gunakan data mentah UCDP.
