"""
app.py - Global Conflict Tracker
================================
Jalankan dengan:   streamlit run app.py

Alur besar file ini (baca dari atas ke bawah):
  1. Import library + konfigurasi halaman
  2. Muat data (CSV hasil agregasi UCDP di folder data/)
  3. Sidebar: rentang tahun, jenis kekerasan, wilayah, data awal 2026
  4. Saring data (src/analisis.py)
  5. Tampilkan: angka ringkasan -> tab peta / tren / negara / data / cara kerja

Setiap bagian diberi komentar "APA" dan "MENGAPA". Penjelasan istilah ada di docs/BELAJAR.md.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import analisis, muat_data

# ----------------------------------------------------------------------------
# 0. KONFIGURASI HALAMAN
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Global Conflict Tracker", page_icon="🌍", layout="wide")

TAHUN_MIN, TAHUN_MAX = 1989, 2026
WARNA_JENIS = {
    "Konflik negara": "#e0483e",
    "Konflik non-negara": "#f2a93b",
    "Kekerasan sepihak": "#7c9cf5",
}
URUTAN_JENIS = muat_data.URUTAN_JENIS
SKALA_PANAS = ["#2b1d1d", "#6b1f1f", "#b32d2d", "#e0483e", "#f58a5a", "#ffd27a"]
TEMPLATE = "plotly_dark"
DISCLAIMER = (
    "ℹ️ Sumber data: **UCDP Georeferenced Event Dataset 26.1** (Uppsala University), kejadian 1989–2025, ditambah "
    "**UCDP Candidate** untuk Januari–September 2026 (data awal, belum final). Angka korban adalah estimasi *best* "
    "UCDP, bukan hitungan resmi. Proyek ini bersifat edukatif dan tidak berafiliasi dengan lembaga mana pun."
)
PENJELASAN_JENIS = {
    "Konflik negara": "Pertempuran yang melibatkan pemerintah suatu negara (melawan negara lain atau kelompok pemberontak).",
    "Konflik non-negara": "Pertempuran antar kelompok bersenjata tanpa pemerintah di salah satu pihak, misalnya antar milisi atau kartel.",
    "Kekerasan sepihak": "Kekerasan oleh pemerintah atau kelompok bersenjata terhadap warga sipil yang tidak bersenjata.",
}


def rapikan(fig: go.Figure, tinggi: int = 420) -> go.Figure:
    """Gaya seragam untuk semua grafik Plotly: latar gelap, grid tipis, legenda di atas."""
    fig.update_layout(
        template=TEMPLATE,
        height=tinggi,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=20, t=70, b=10),
        title=dict(y=0.97, yanchor="top", x=0, xanchor="left", font=dict(size=15)),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, title=None),
        font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="#2a2f3a", zeroline=False)
    return fig


def gaya_peta_dunia(fig: go.Figure) -> go.Figure:
    """Peta dunia gelap, dipotong di bawah 58°LS agar Antarktika tidak memakan tempat."""
    fig.update_geos(
        showframe=False, showcoastlines=False, showland=True, landcolor="#1b2029",
        showocean=True, oceancolor="#0e1117", showcountries=True, countrycolor="#2a2f3a",
        showlakes=False, bgcolor="rgba(0,0,0,0)",
        lataxis_range=[-58, 84], lonaxis_range=[-180, 180],
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        geo=dict(domain=dict(x=[0, 1], y=[0, 1])),
        legend=dict(orientation="h", y=0.02, x=0.01, yanchor="bottom", bgcolor="rgba(14,17,23,0.6)"),
    )
    return fig


def ribuan(angka: float) -> str:
    """Format 1234567 -> '1.234.567' (gaya Indonesia)."""
    return f"{int(round(angka)):,}".replace(",", ".")


def ringkas(angka: float) -> str:
    """Format singkat: 1.2 jt / 45 rb."""
    if angka >= 1_000_000:
        return f"{angka / 1_000_000:.1f} jt".replace(".", ",")
    if angka >= 10_000:
        return f"{angka / 1_000:.0f} rb"
    return ribuan(angka)


# ----------------------------------------------------------------------------
# 1. MUAT DATA (di-cache: CSV hanya dibaca sekali meskipun halaman dijalankan ulang)
# ----------------------------------------------------------------------------
@st.cache_data
def ambil_data():
    return muat_data.muat_negara_tahun(), muat_data.muat_grid(), muat_data.muat_konflik()


df_semua, grid_semua, konflik_semua = ambil_data()

# ----------------------------------------------------------------------------
# 2. SIDEBAR: filter
# ----------------------------------------------------------------------------
with st.sidebar:
    st.title("🌍 Global Conflict Tracker")
    st.caption("Konflik bersenjata di seluruh dunia, 1989–2026, dari data UCDP.")

    st.subheader("Filter")
    tahun_awal, tahun_akhir = st.slider("Rentang tahun", TAHUN_MIN, TAHUN_MAX, (2000, TAHUN_MAX))
    jenis_pilihan = st.multiselect(
        "Jenis kekerasan",
        URUTAN_JENIS,
        default=URUTAN_JENIS,
        help="Tiga kategori UCDP. Penjelasan ada di tab Cara Kerja.",
    )
    semua_wilayah = sorted(df_semua["wilayah"].unique())
    wilayah_pilihan = st.multiselect("Wilayah", semua_wilayah, default=semua_wilayah)
    sertakan_awal = st.toggle(
        "Sertakan data awal 2026",
        value=True,
        help="Data UCDP Candidate (Jan–Sep 2026) belum final dan dapat direvisi.",
    )
    metrik = st.radio("Ukuran utama", ["korban", "kejadian"], format_func=lambda m: {"korban": "Korban jiwa", "kejadian": "Jumlah kejadian"}[m], horizontal=True)

    mode_belajar = st.toggle("🎓 Mode belajar", value=False, help="Tampilkan penjelasan dan potongan kode di setiap bagian.")
    st.caption("Data: UCDP GED 26.1 + UCDP Candidate. Lihat tab *Data & Sumber*.")

LABEL_METRIK = {"korban": "Korban jiwa", "kejadian": "Kejadian"}[metrik]

# ----------------------------------------------------------------------------
# 3. SARING DATA
# ----------------------------------------------------------------------------
# APA: terapkan filter ke tiga tabel. MENGAPA: df_semua tetap utuh agar pembanding tidak ikut berubah.
df = analisis.filter_data(df_semua, tahun_awal, tahun_akhir, jenis_pilihan, wilayah_pilihan, sertakan_awal)
grid = analisis.filter_data(grid_semua, tahun_awal, tahun_akhir, jenis_pilihan, None, sertakan_awal)
grid = grid[grid["negara"].isin(df["negara"].unique())]
konflik = analisis.filter_data(konflik_semua, tahun_awal, tahun_akhir, jenis_pilihan, None, sertakan_awal)
konflik = konflik[konflik["negara_utama"].isin(df["negara"].unique())]
ring = analisis.ringkasan(df)

# ----------------------------------------------------------------------------
# 4. HEADER + ANGKA RINGKASAN
# ----------------------------------------------------------------------------
st.title("🌍 Global Conflict Tracker")
st.markdown(
    f"Peta dan tren **konflik bersenjata di seluruh dunia** berdasarkan data UCDP, "
    f"periode **{tahun_awal}–{tahun_akhir}**. Di mana perang terjadi, seberapa mematikan, dan bagaimana arahnya."
)

if df.empty:
    st.warning("Tidak ada data untuk kombinasi filter ini. Longgarkan filter di sidebar.")
    st.stop()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Korban jiwa", ringkas(ring["korban"]), help="Estimasi best UCDP, dijumlahkan dalam rentang & filter aktif")
k2.metric("Kejadian tercatat", ringkas(ring["kejadian"]))
k3.metric("Negara terdampak", ring["negara"])
k4.metric("Negara paling mematikan", ring["negara_tertinggi"])
k4.caption(f"{ringkas(ring['korban_tertinggi'])} korban jiwa")
k5.metric("Tahun terburuk", ring["tahun_terburuk"])
k5.caption(f"{ringkas(ring['korban_tahun_terburuk'])} korban jiwa")
if sertakan_awal and tahun_akhir >= 2026:
    st.caption("⚠️ Angka 2026 hanya mencakup Januari–September dan berasal dari data awal UCDP Candidate.")

tab_peta, tab_tren, tab_negara, tab_data, tab_cara = st.tabs(
    ["🗺️ Peta", "📈 Tren", "🔎 Negara", "📋 Data & Sumber", "🧭 Cara Kerja"]
)

# ----------------------------------------------------------------------------
# 5. TAB PETA
# ----------------------------------------------------------------------------
with tab_peta:
    c1, c2 = st.columns([1, 2])
    with c1:
        mode_peta = st.radio("Tampilan", ["Per negara", "Titik kejadian"], horizontal=True, help="Per negara = choropleth; titik = sel grid 0,5° (≈55 km)")
    with c2:
        tahun_peta = st.select_slider(
            "Tahun pada peta (geser untuk melihat satu tahun saja; filter sidebar tetap berlaku)",
            options=["Semua tahun"] + list(range(tahun_awal, tahun_akhir + 1)),
            value="Semua tahun",
        )

    df_peta = df if tahun_peta == "Semua tahun" else df[df["tahun"] == tahun_peta]
    grid_peta = grid if tahun_peta == "Semua tahun" else grid[grid["tahun"] == tahun_peta]
    judul_tahun = f"{tahun_awal}–{tahun_akhir}" if tahun_peta == "Semua tahun" else str(tahun_peta)

    if True:
        if mode_peta == "Per negara":
            negara_peta = analisis.peta_negara(df_peta, metrik)
            if negara_peta.empty:
                st.info("Tidak ada kejadian pada tahun ini.")
            else:
                # APA: warna memakai log10 agar Rwanda 1994 tidak membuat negara lain tampak kosong.
                negara_peta["log_nilai"] = np.log10(negara_peta[metrik])
                maks = float(negara_peta["log_nilai"].max())
                tick = [t for t in range(0, int(np.ceil(maks)) + 1)]
                fig = px.choropleth(
                    negara_peta,
                    locations="iso3",
                    color="log_nilai",
                    hover_name="negara",
                    hover_data={"iso3": False, "log_nilai": False, "korban": ":,", "kejadian": ":,", "intensitas": True, "wilayah": True},
                    color_continuous_scale=SKALA_PANAS,
                    range_color=(0, max(maks, 1)),
                    projection="natural earth",
                    title=f"{LABEL_METRIK} per negara, {judul_tahun}",
                )
                fig.update_coloraxes(
                    colorbar=dict(title=LABEL_METRIK, tickvals=tick, ticktext=[ribuan(10**t) for t in tick], len=0.5, thickness=10, x=0.93, y=0.45),
                )
                rapikan(fig, 520)
                gaya_peta_dunia(fig)
                st.plotly_chart(fig, use_container_width=True)
        else:
            if grid_peta.empty:
                st.info("Tidak ada kejadian pada tahun ini.")
            else:
                sel = (
                    grid_peta.groupby(["lat", "lon", "jenis", "negara"], as_index=False)
                    .agg(korban=("korban", "sum"), kejadian=("kejadian", "sum"))
                )
                sel = sel[sel[metrik] > 0].sort_values(metrik, ascending=False)
                # APA: ukuran titik = akar dari nilai. MENGAPA: luas lingkaran proporsional dengan nilai, bukan diameternya.
                sel["ukuran"] = np.sqrt(sel[metrik])
                fig = px.scatter_geo(
                    sel,
                    lat="lat",
                    lon="lon",
                    size="ukuran",
                    color="jenis",
                    color_discrete_map=WARNA_JENIS,
                    category_orders={"jenis": URUTAN_JENIS},
                    hover_name="negara",
                    hover_data={"lat": False, "lon": False, "ukuran": False, "korban": ":,", "kejadian": ":,", "jenis": True},
                    size_max=30,
                    opacity=0.6,
                    projection="natural earth",
                    title=f"Titik kejadian ({LABEL_METRIK.lower()}), {judul_tahun}",
                )
                fig.update_traces(marker=dict(line=dict(width=0.4, color="#0e1117")))
                rapikan(fig, 520)
                gaya_peta_dunia(fig)
                st.plotly_chart(fig, use_container_width=True)
        st.caption(DISCLAIMER)

    # Peringkat negara untuk tahun yang sama
    top = analisis.top_negara(df_peta, 12, metrik)
    if not top.empty:
        fig = px.bar(
            top.sort_values(metrik),
            x=metrik,
            y="negara",
            orientation="h",
            color="wilayah",
            text=top.sort_values(metrik)[metrik].map(ribuan),
            title=f"12 negara dengan {LABEL_METRIK.lower()} terbanyak, {judul_tahun}",
            labels={metrik: LABEL_METRIK, "negara": "", "wilayah": "Wilayah"},
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(rapikan(fig, 440), use_container_width=True)

    if mode_belajar:
        with st.expander("🎓 Di balik peta ini"):
            st.markdown(
                """
**Choropleth** mewarnai negara berdasarkan satu angka. Plotly mengenali negara lewat kode **ISO-3** (`IDN`, `UKR`),
sedangkan UCDP memakai nama seperti `DR Congo (Zaire)`. Pemetaan nama → ISO-3 ada di `src/negara.py`.

**Mengapa skala log?** Rwanda 1994 mencatat ~800 ribu korban, sementara banyak negara hanya puluhan. Pada skala
linear, semua negara lain akan tampak "kosong". Dengan `log10`, 10 → 1, 1.000 → 3, 100.000 → 5, sehingga
perbedaan antar negara kecil tetap terlihat.

**Titik kejadian** bukan koordinat persis setiap kejadian (ada 434 ribu baris di data mentah), melainkan
agregasi per **sel grid 0,5°** (sekitar 55 km). Lihat `src/siapkan_data.py` fungsi `agregasi_grid`.
                """
            )
            st.code(
                'negara_peta["log_nilai"] = np.log10(negara_peta["korban"])\n'
                'px.choropleth(negara_peta, locations="iso3", color="log_nilai", projection="natural earth")',
                language="python",
            )

# ----------------------------------------------------------------------------
# 6. TAB TREN
# ----------------------------------------------------------------------------
with tab_tren:
    per_jenis = analisis.per_tahun(df, "jenis")
    fig = px.area(
        per_jenis,
        x="tahun",
        y=metrik,
        color="jenis",
        color_discrete_map=WARNA_JENIS,
        category_orders={"jenis": URUTAN_JENIS},
        title=f"{LABEL_METRIK} per tahun menurut jenis kekerasan",
        labels={"tahun": "", metrik: LABEL_METRIK, "jenis": ""},
    )
    fig.update_traces(line=dict(width=0.5))
    st.plotly_chart(rapikan(fig, 420), use_container_width=True)

    kolom_a, kolom_b = st.columns(2)
    with kolom_a:
        per_wilayah = analisis.per_tahun(df, "wilayah")
        fig = px.bar(
            per_wilayah,
            x="tahun",
            y=metrik,
            color="wilayah",
            title=f"{LABEL_METRIK} per tahun menurut wilayah",
            labels={"tahun": "", metrik: LABEL_METRIK, "wilayah": ""},
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        st.plotly_chart(rapikan(fig, 400), use_container_width=True)
    with kolom_b:
        n_top = st.slider("Jumlah negara pada grafik garis", 3, 12, 6)
        daftar_top = analisis.top_negara(df, n_top, metrik)["negara"].tolist()
        garis = analisis.per_tahun(df[df["negara"].isin(daftar_top)], "negara")
        fig = px.line(
            garis,
            x="tahun",
            y=metrik,
            color="negara",
            markers=True,
            title=f"{n_top} negara dengan {LABEL_METRIK.lower()} terbanyak, per tahun",
            labels={"tahun": "", metrik: LABEL_METRIK, "negara": ""},
            category_orders={"negara": daftar_top},
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        fig.update_traces(line=dict(width=2), marker=dict(size=5))
        st.plotly_chart(rapikan(fig, 400), use_container_width=True)

    kolom_c, kolom_d = st.columns(2)
    with kolom_c:
        if metrik == "korban":
            rentang = analisis.per_tahun(df)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=rentang["tahun"], y=rentang["korban_max"], line=dict(width=0), showlegend=False, hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=rentang["tahun"], y=rentang["korban_min"], fill="tonexty", fillcolor="rgba(224,72,62,0.18)", line=dict(width=0), name="Rentang low–high"))
            fig.add_trace(go.Scatter(x=rentang["tahun"], y=rentang["korban"], line=dict(color="#e0483e", width=2.5), name="Estimasi best"))
            fig.update_layout(title="Ketidakpastian estimasi: best vs low–high", yaxis_title="Korban jiwa")
            st.plotly_chart(rapikan(fig, 380), use_container_width=True)
        else:
            perubahan = analisis.perubahan_tahunan(df)
            fig = px.bar(
                perubahan.dropna(),
                x="tahun",
                y="selisih",
                color=perubahan.dropna()["selisih"] > 0,
                color_discrete_map={True: "#e0483e", False: "#5cb27c"},
                title="Perubahan korban jiwa dari tahun sebelumnya",
                labels={"tahun": "", "selisih": "Selisih korban"},
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(rapikan(fig, 380), use_container_width=True)
    with kolom_d:
        sipil = analisis.pangsa_sipil(df)
        fig = px.line(
            sipil,
            x="tahun",
            y="pangsa_sipil_pct",
            markers=True,
            title="Persentase korban sipil dari seluruh korban",
            labels={"tahun": "", "pangsa_sipil_pct": "% sipil"},
        )
        fig.update_traces(line=dict(color="#7c9cf5", width=2.5))
        fig.update_yaxes(range=[0, 100], ticksuffix="%")
        st.plotly_chart(rapikan(fig, 380), use_container_width=True)

    st.subheader("Konflik paling mematikan dalam rentang ini")
    teratas = analisis.konflik_teratas(konflik, 10)
    teratas_tampil = teratas.assign(
        periode=teratas["tahun_awal"].astype(str) + "–" + teratas["tahun_akhir"].astype(str),
        korban=teratas["korban"].map(ribuan),
        kejadian=teratas["kejadian"].map(ribuan),
    )[["konflik", "jenis", "periode", "korban", "kejadian"]]
    teratas_tampil.columns = ["Konflik (nama UCDP)", "Jenis", "Periode aktif", "Korban jiwa", "Kejadian"]
    st.dataframe(teratas_tampil, use_container_width=True, hide_index=True)
    st.caption("Nama konflik mengikuti UCDP: `Negara: Government` berarti perang melawan pemerintah; `A - B` berarti pertempuran dua pihak; `X - Civilians` berarti kekerasan sepihak.")

    if mode_belajar:
        with st.expander("🎓 Membaca grafik tren"):
            st.markdown(
                """
- **Best, low, high.** Untuk setiap kejadian UCDP mencatat tiga angka: estimasi paling masuk akal (*best*),
  batas bawah (*low*) dan batas atas (*high*) dari berbagai sumber berita. Pita merah muda menunjukkan seberapa
  tidak pasti jumlah total per tahun. Pada tahun perang besar (Suriah 2014, Ukraina 2022) rentangnya sangat lebar.
- **Pangsa sipil** = `korban_sipil / korban`. Kolom `deaths_civilians` di UCDP hanya diisi jika sumber menyebut
  korban sipil secara eksplisit, sehingga angka ini cenderung **terlalu rendah**.
- **Grafik area bertumpuk** cocok untuk melihat total sekaligus komposisi, tetapi kurang tepat untuk membandingkan
  lapisan tengah. Untuk perbandingan antar negara dipakai grafik garis.
                """
            )
            st.code(
                "per_jenis = df.groupby(['tahun', 'jenis'], as_index=False)['korban'].sum()\n"
                "px.area(per_jenis, x='tahun', y='korban', color='jenis')",
                language="python",
            )

# ----------------------------------------------------------------------------
# 7. TAB NEGARA
# ----------------------------------------------------------------------------
with tab_negara:
    urutan_negara = analisis.top_negara(df, 500, metrik)["negara"].tolist()
    negara_terpilih = st.selectbox("Pilih negara (diurutkan dari yang paling terdampak dalam rentang aktif)", urutan_negara, index=0)
    profil = analisis.profil_negara(df, konflik, negara_terpilih)
    info = df[df["negara"] == negara_terpilih].iloc[0]

    n1, n2, n3, n4, n5 = st.columns(5)
    n1.metric("Korban jiwa", ringkas(profil["korban"]), help=f"{tahun_awal}–{tahun_akhir}")
    n2.metric("Kejadian", ringkas(profil["kejadian"]))
    n3.metric("Korban sipil tercatat", ringkas(profil["korban_sipil"]))
    n4.metric("Tahun puncak", profil["tahun_puncak"])
    n4.caption(f"{ringkas(profil['korban_puncak'])} korban jiwa")
    n5.metric("Tahun ≥ 25 korban", profil["tahun_aktif"], help="Jumlah tahun di mana negara ini melewati ambang konflik aktif UCDP (25 korban)")

    kolom_e, kolom_f = st.columns([3, 2])
    with kolom_e:
        fig = px.bar(
            profil["tren"],
            x="tahun",
            y=metrik,
            color="jenis",
            color_discrete_map=WARNA_JENIS,
            category_orders={"jenis": URUTAN_JENIS},
            title=f"{negara_terpilih}: {LABEL_METRIK.lower()} per tahun",
            labels={"tahun": "", metrik: LABEL_METRIK, "jenis": ""},
        )
        fig.add_hline(y=analisis.AMBANG_PERANG, line_dash="dot", line_color="#aaaaaa", annotation_text="ambang perang (1.000)", annotation_position="top left")
        st.plotly_chart(rapikan(fig, 420), use_container_width=True)
    with kolom_f:
        grid_negara = grid[grid["negara"] == negara_terpilih]
        sel = grid_negara.groupby(["lat", "lon"], as_index=False).agg(korban=("korban", "sum"), kejadian=("kejadian", "sum"))
        sel = sel[sel[metrik] > 0]
        if sel.empty:
            st.info("Tidak ada titik untuk ditampilkan.")
        else:
            sel["ukuran"] = np.sqrt(sel[metrik])
            fig = px.scatter_geo(
                sel, lat="lat", lon="lon", size="ukuran", color=metrik,
                color_continuous_scale=SKALA_PANAS, size_max=22, opacity=0.8,
                hover_data={"lat": False, "lon": False, "ukuran": False, "korban": ":,", "kejadian": ":,"},
                title=f"Sebaran kejadian di {negara_terpilih}",
            )
            fig.update_geos(
                fitbounds="locations", showframe=False, showcoastlines=False, showland=True, landcolor="#1b2029",
                showocean=True, oceancolor="#0e1117", showcountries=True, countrycolor="#3a404d", bgcolor="rgba(0,0,0,0)",
            )
            fig.update_coloraxes(showscale=False)
            rapikan(fig, 420)
            fig.update_layout(margin=dict(l=0, r=0, t=50, b=0))
            st.plotly_chart(fig, use_container_width=True)

    st.subheader(f"Konflik utama di {negara_terpilih}")
    if profil["konflik"].empty:
        st.info("Tidak ada konflik yang berpusat di negara ini dalam rentang aktif.")
    else:
        kt = profil["konflik"].assign(
            periode=profil["konflik"]["tahun_awal"].astype(str) + "–" + profil["konflik"]["tahun_akhir"].astype(str),
            korban=profil["konflik"]["korban"].map(ribuan),
            kejadian=profil["konflik"]["kejadian"].map(ribuan),
        )[["konflik", "jenis", "periode", "korban", "kejadian"]]
        kt.columns = ["Konflik (nama UCDP)", "Jenis", "Periode aktif", "Korban jiwa", "Kejadian"]
        st.dataframe(kt, use_container_width=True, hide_index=True)
    st.caption(f"Wilayah UCDP: {info['wilayah']} · kode ISO-3: {info['iso3']}. Konflik dikaitkan ke negara tempat kejadian terbanyak terjadi.")

    if mode_belajar:
        with st.expander("🎓 Bagaimana satu negara dirangkum"):
            st.markdown(
                """
Semua angka pada tab ini berasal dari satu fungsi, `profil_negara()` di `src/analisis.py`, yang menyaring tabel
negara-tahun ke satu negara lalu menjumlahkannya per tahun dan per jenis. Ambang **25 korban** dan **1.000 korban**
adalah definisi UCDP untuk *konflik aktif* dan *perang*; di sini diterapkan pada total per negara, jadi sifatnya
indikatif (satu negara dapat memuat beberapa konflik sekaligus).
                """
            )
            st.code(
                "d = negara_tahun[negara_tahun['negara'] == negara]\n"
                "tren = d.groupby(['tahun', 'jenis'], as_index=False)['korban'].sum()\n"
                "tahun_aktif = (d.groupby('tahun')['korban'].sum() >= 25).sum()",
                language="python",
            )

# ----------------------------------------------------------------------------
# 8. TAB DATA & SUMBER
# ----------------------------------------------------------------------------
with tab_data:
    st.markdown(
        """
Tiga tabel di bawah adalah hasil agregasi dari data mentah UCDP (434 ribu kejadian, ~270 MB) oleh
`src/siapkan_data.py`. Filter sidebar berlaku untuk tabel yang ditampilkan dan file yang diunduh.
        """
    )
    pilihan_tabel = st.radio(
        "Tabel",
        ["Negara × tahun", "Konflik × tahun", "Grid peta"],
        horizontal=True,
    )
    tabel = {"Negara × tahun": df, "Konflik × tahun": konflik, "Grid peta": grid}[pilihan_tabel]
    nama_unduh = {"Negara × tahun": "korban_negara_tahun", "Konflik × tahun": "konflik_tahun", "Grid peta": "grid_kejadian"}[pilihan_tabel]
    st.caption(f"{ribuan(len(tabel))} baris. Kolom `status` = `final` (GED 26.1) atau `awal` (UCDP Candidate 2026).")
    st.dataframe(tabel.head(2000), use_container_width=True, hide_index=True, height=380)
    st.download_button(
        "⬇️ Download CSV (sesuai filter)",
        tabel.to_csv(index=False).encode("utf-8"),
        file_name=f"{nama_unduh}_{tahun_awal}_{tahun_akhir}.csv",
        mime="text/csv",
    )

    st.subheader("Sumber")
    st.markdown(
        """
| Sumber | Isi | Lisensi / akses |
|---|---|---|
| [UCDP Georeferenced Event Dataset (GED) 26.1](https://ucdp.uu.se/downloads/index.html#ged_global) | Kejadian kekerasan mematikan 1989–2025 dengan koordinat, tanggal, pihak, estimasi korban | Gratis, tanpa registrasi, CC BY 4.0 |
| [UCDP Candidate Events Dataset](https://ucdp.uu.se/downloads/index.html#candidate) | Kejadian 2026 (Jan–Sep) yang belum melewati tinjauan akhir | Gratis, tanpa registrasi |
| [Codebook UCDP GED](https://ucdp.uu.se/downloads/ged/ged261.pdf) | Definisi kolom, ambang 25 korban, tiga jenis kekerasan | - |

Kutipan yang diminta UCDP: Davies, Pettersson, Sollenberg & Öberg (2026), *Journal of Peace Research*;
Sundberg & Melander (2013), *Journal of Peace Research* 50(4).
        """
    )
    st.subheader("Keterbatasan yang perlu diingat")
    st.markdown(
        """
1. **UCDP hanya mencatat kematian langsung akibat kekerasan** yang dapat diverifikasi dari sumber berita atau laporan.
   Kematian tidak langsung (kelaparan, penyakit, runtuhnya layanan kesehatan) tidak termasuk, padahal sering kali jauh lebih besar.
2. **Hanya kejadian dengan minimal 1 korban jiwa** yang masuk, dan hanya untuk konflik/pihak yang pernah melewati
   ambang 25 korban dalam setahun. Kekerasan kriminal biasa tidak masuk kecuali pelakunya kelompok terorganisasi (misalnya kartel Meksiko).
3. **Liputan media tidak merata.** Konflik yang sulit diliput (Tigray, Myanmar, Sudan) hampir pasti kurang tercatat; rentang low–high memberi gambaran ketidakpastiannya.
4. **Negara mengikuti lokasi kejadian**, bukan kewarganegaraan korban. Serangan di perbatasan dapat tercatat di negara tetangga.
5. **Data 2026 bersifat awal** (UCDP Candidate): dikodekan lebih cepat dengan tinjauan lebih sedikit, dan hanya sampai September.
6. **Nama negara UCDP mengikuti entitas saat ini** (misalnya kejadian 1989 di Uni Soviet tercatat di bawah negara penerusnya).
        """
    )
    st.caption(DISCLAIMER)

# ----------------------------------------------------------------------------
# 9. TAB CARA KERJA
# ----------------------------------------------------------------------------
with tab_cara:
    st.markdown(
        """
### Alur data

```
ucdp.uu.se (zip 39 MB)  ──►  src/siapkan_data.py  ──►  data/*.csv (3 tabel, ~4 MB)  ──►  src/muat_data.py
                              agregasi per negara-tahun,                                      │
                              grid 0,5°, per konflik                                           ▼
                                                                    sidebar (filter) ──► src/analisis.py ──► app.py (peta & grafik)
```

Data mentah tidak disimpan di repositori karena ukurannya. Untuk memperbarui ke rilis UCDP berikutnya, cukup ganti
URL di `src/siapkan_data.py` lalu jalankan `python -m src.siapkan_data`.

### Tiga jenis kekerasan menurut UCDP
        """
    )
    for nama, teks in PENJELASAN_JENIS.items():
        st.markdown(f"- <span style='color:{WARNA_JENIS[nama]}'>●</span> **{nama}** — {teks}", unsafe_allow_html=True)
    st.markdown(
        """
### Istilah penting

| Istilah | Arti |
|---|---|
| **Kejadian (event)** | Satu peristiwa kekerasan mematikan pada satu lokasi dan tanggal tertentu, dengan pihak yang teridentifikasi |
| **Best / low / high** | Tiga estimasi korban per kejadian; *best* adalah angka yang paling dapat dipertanggungjawabkan |
| **Konflik aktif** | Konflik dengan ≥ 25 korban jiwa dalam satu tahun kalender |
| **Perang** | Konflik dengan ≥ 1.000 korban jiwa dalam satu tahun kalender |
| **Korban sipil** | Kolom `deaths_civilians`; hanya terisi jika sumber menyebutnya secara eksplisit |
| **Sel grid 0,5°** | Kotak 0,5 × 0,5 derajat (≈ 55 km di khatulistiwa) tempat kejadian dijumlahkan untuk peta titik |

### Fungsi inti (`src/analisis.py`)

| Fungsi | Yang dihitung |
|---|---|
| `filter_data(df, awal, akhir, jenis, wilayah, sertakan_awal)` | Menyaring tabel sesuai sidebar |
| `ringkasan(df)` | Angka KPI: total korban, kejadian, negara, negara dan tahun terburuk |
| `per_tahun(df, kolom)` | Jumlah per tahun, opsional dipecah per jenis / wilayah / negara |
| `top_negara(df, n, metrik)` | Peringkat negara |
| `perubahan_tahunan(df)` | Selisih dan persen perubahan antar tahun |
| `pangsa_sipil(df)` | Persentase korban sipil |
| `kategori_intensitas(korban)` | Label "Di bawah ambang / Konflik minor / Perang" |
| `profil_negara(...)` | Semua tabel untuk tab Negara |

Seluruh fungsi tersebut murni pandas dan diuji dengan `pytest` (`tests/test_analisis.py`).
        """
    )
    if mode_belajar:
        with st.expander("🎓 Mengapa data diagregasi dulu, bukan dibaca langsung?"):
            st.markdown(
                """
Membaca 270 MB CSV setiap kali aplikasi dibuka akan lambat dan melewati batas memori Streamlit Community Cloud.
Karena dashboard hanya membutuhkan jumlah per negara-tahun, per sel grid, dan per konflik, agregasi dilakukan
**sekali** di `siapkan_data.py` dan hasilnya (sekitar 4 MB) yang disimpan. Pola ini disebut *pre-aggregation*
dan sangat umum pada dashboard: pisahkan pekerjaan berat (ETL) dari tampilan.
                """
            )
            st.code(
                "g = kejadian.groupby(['negara', 'iso3', 'wilayah', 'tahun', 'jenis'], as_index=False).agg(\n"
                "    kejadian=('korban', 'size'), korban=('korban', 'sum'), korban_sipil=('korban_sipil', 'sum'))",
                language="python",
            )
