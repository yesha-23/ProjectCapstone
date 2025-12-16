from flask import Flask, render_template, request
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

app = Flask(__name__)

# ============================================================
# DATASET / GOOGLE SHEETS
# ============================================================
URL_RUANG = "https://docs.google.com/spreadsheets/d/1CJuK0EetknB67O6CwXxXlFObHkYHhGPP/export?format=csv"
URL_MATKUL = "https://docs.google.com/spreadsheets/d/13PXTH2JAk51azCj6KzwjD59OAZrKt1f0/export?format=csv"


# ============================================================
# LOAD DATA + FILTER SEMESTER
# ============================================================
def load_data(semester_filter="SEMUA"):
    df_ruang = pd.read_csv(URL_RUANG)
    df_matkul = pd.read_csv(URL_MATKUL)

    df_matkul["th_ajaran"] = (
        df_matkul["th_ajaran"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    if semester_filter != "SEMUA":
        df_matkul = df_matkul[df_matkul["th_ajaran"] == semester_filter]

    return df_ruang, df_matkul

# ============================================================
# SUMMARY CARDS
# ============================================================
def summary_cards(df_gabung):

    df_gabung["ef"] = df_gabung["peserta"] / df_gabung["kapasitas"]

    ef_ruang = df_gabung.groupby("ruang")["ef"].mean().reset_index()

    ef_ruang["kategori"] = pd.cut(
        ef_ruang["ef"],
        bins=[0, 0.60, 0.80, 1.5],
        labels=["Tidak Efisien", "Cukup Efisien", "Efisien"],
        include_lowest=True
    )

    total = ef_ruang["ruang"].nunique()

    return {
        "efisien": (ef_ruang["kategori"] == "Efisien").sum(),
        "efisien_pct": round((ef_ruang["kategori"] == "Efisien").mean() * 100, 2),

        "cukup": (ef_ruang["kategori"] == "Cukup Efisien").sum(),
        "cukup_pct": round((ef_ruang["kategori"] == "Cukup Efisien").mean() * 100, 2),

        "tidak": (ef_ruang["kategori"] == "Tidak Efisien").sum(),
        "tidak_pct": round((ef_ruang["kategori"] == "Tidak Efisien").mean() * 100, 2),

        "total": total
    }

# ============================================================
# CHART 1 — Efisiensi Ruang
# ============================================================
def fig_efisiensi_ruang(df_ruang, df_matkul):

    df = df_matkul.merge(df_ruang[['ruang', 'kapasitas']], on="ruang", how="left")
    df["peserta"] = pd.to_numeric(df["peserta"], errors="coerce")
    df["kapasitas"] = pd.to_numeric(df["kapasitas"], errors="coerce")

    df["ef"] = df["peserta"] / df["kapasitas"]

    ef = df.groupby("ruang")["ef"].mean().reset_index()
    ef["ef (%)"] = (ef["ef"] * 100).round(2)
    ef = ef.sort_values("ef (%)", ascending=False)

    top10 = ef.head(10)
    bottom10 = ef.tail(10)

    fig = go.Figure()

    # Semua ruang
    fig.add_trace(go.Bar(
        x=ef["ruang"],
        y=ef["ef (%)"],
        name="Semua Ruang",
        visible=False,
        text=ef["ef (%)"].astype(str) + "%",
        textposition="outside",
        marker_color="#3b82f6"
    ))

    # Top 10
    fig.add_trace(go.Bar(
        x=top10["ruang"],
        y=top10["ef (%)"],
        name="10 Teratas",
        visible=True,
        text=top10["ef (%)"].astype(str) + "%",
        textposition="outside",
        marker_color="#16a34a"
    ))

    # Bottom 10
    fig.add_trace(go.Bar(
        x=bottom10["ruang"],
        y=bottom10["ef (%)"],
        name="10 Terbawah",
        visible=False,
        text=bottom10["ef (%)"].astype(str) + "%",
        textposition="outside",
        marker_color="#dc2626"
    ))

    fig.update_layout(
        updatemenus=[{
            "buttons": [
                {"label": "Semua Ruang", "method": "update",
                 "args": [{"visible": [True, False, False]}]},
                {"label": "10 Teratas", "method": "update",
                 "args": [{"visible": [False, True, False]}]},
                {"label": "10 Terbawah", "method": "update",
                 "args": [{"visible": [False, False, True]}]},
            ],
            "x": 0.95, "y": 1.20,
            "xanchor": "right",
            "yanchor": "top",
            "bgcolor": "white",
        }],
        height=460,
        xaxis_tickangle=80
    )

    return pio.to_html(fig, full_html=False, include_plotlyjs=False)

# ============================================================
# CHART 2 — Efisiensi Prodi
# ============================================================
def fig_efisiensi_prodi(df_ruang, df_matkul):

    df = df_matkul.merge(df_ruang[['ruang', 'kapasitas']], on="ruang", how="left")
    df["peserta"] = pd.to_numeric(df["peserta"], errors="coerce")
    df["kapasitas"] = pd.to_numeric(df["kapasitas"], errors="coerce")

    df["prodi"] = df["prodi"].astype(str).str.upper()

    df["ef"] = df["peserta"] / df["kapasitas"]

    ef = df.groupby("prodi")["ef"].mean().reset_index()
    ef["ef (%)"] = (ef["ef"] * 100).round(2)
    ef = ef.sort_values("ef (%)", ascending=False)

    fig = go.Figure(go.Bar(
        x=ef["prodi"],
        y=ef["ef (%)"],
        text=ef["ef (%)"].astype(str) + "%",
        textposition="outside",
        marker_color="steelblue"
    ))

    fig.update_layout(
        height=460,
        xaxis_tickangle=45,
        xaxis_title="Program Studi",
        yaxis_title="Efisiensi (%)"
    )

    return pio.to_html(fig, full_html=False, include_plotlyjs=False)


# ============================================================
# CHART 3 — Efisiensi Hari-Sesi (FIXED)
# ============================================================
def fig_efisiensi_hari_sesi(df_ruang, df_matkul, filter_hari="SEMUA"):

    df = df_matkul.merge(df_ruang[['ruang', 'kapasitas']], on="ruang", how="left")
    df["peserta"] = pd.to_numeric(df["peserta"], errors="coerce")
    df["kapasitas"] = pd.to_numeric(df["kapasitas"], errors="coerce")

    df["hari"] = df["hari"].astype(str).str.upper()
    df["sesi"] = df["sesi"].astype(str).str.upper()

    df["ef"] = df["peserta"] / df["kapasitas"]

    urutan_hari = ["SENIN", "SELASA", "RABU", "KAMIS", "JUMAT"]
    data_hari = {}

    for h in ["SEMUA"] + urutan_hari:

        if h == "SEMUA":
            subset = df
        else:
            subset = df[df["hari"] == h]

        ef = subset.groupby(["hari", "sesi"])["ef"].mean().reset_index()
        ef["ef (%)"] = (ef["ef"] * 100).round(2)
        ef["hari_sesi"] = ef["hari"] + " - " + ef["sesi"]

        data_hari[h] = ef

    fig = go.Figure()

    # Trace awal sesuai filter_hari
    for h in data_hari:
        fig.add_trace(go.Bar(
            x=data_hari[h]["hari_sesi"],
            y=data_hari[h]["ef (%)"],
            name=h,
            visible=(h == filter_hari),
            text=data_hari[h]["ef (%)"].astype(str) + "%",
            textposition="outside",
            marker_color="steelblue"
        ))

    # Dropdown
    buttons = []
    for i, h in enumerate(data_hari):
        vis = [False] * len(data_hari)
        vis[i] = True
        buttons.append({
            "label": h,
            "method": "update",
            "args": [{"visible": vis}]
        })

    fig.update_layout(
        updatemenus=[{
            "buttons": buttons,
            "x": 0.95, "y": 1.18,
            "xanchor": "right"
        }],
        height=460,
        xaxis_tickangle=45
    )

    return pio.to_html(fig, full_html=False, include_plotlyjs=False)


# ============================================================
# CHART 4 — Penggunaan Ruang (FIXED)
# ============================================================
def fig_penggunaan_kelas(df_ruang, df_matkul, filter_hari="SEMUA"):

    df = df_matkul.merge(df_ruang[['ruang']], on="ruang", how="left")
    df["hari"] = df["hari"].astype(str).str.upper()
    df["sesi"] = df["sesi"].astype(str).str.upper()

    total_ruang = df_ruang["ruang"].nunique()

    urutan_hari = ["SENIN", "SELASA", "RABU", "KAMIS", "JUMAT"]
    data_hari = {}

    for h in ["SEMUA"] + urutan_hari:

        if h == "SEMUA":
            subset = df
        else:
            subset = df[df["hari"] == h]

        pg = subset.groupby(["hari", "sesi"])["ruang"].nunique().reset_index(name="dipakai")
        pg["pers (%)"] = (pg["dipakai"] / total_ruang * 100).round(2)

        pg["hari_sesi"] = pg["hari"] + " - " + pg["sesi"]

        data_hari[h] = pg

    fig = go.Figure()

    for h in data_hari:
        fig.add_trace(go.Bar(
            x=data_hari[h]["hari_sesi"],
            y=data_hari[h]["pers (%)"],
            name=h,
            visible=(h == filter_hari),
            text=data_hari[h]["pers (%)"].astype(str) + "%",
            textposition="outside",
            marker_color="royalblue"
        ))

    buttons = []
    for i, h in enumerate(data_hari):
        vis = [False] * len(data_hari)
        vis[i] = True
        buttons.append({
            "label": h,
            "method": "update",
            "args": [{"visible": vis}]
        })

    fig.update_layout(
        updatemenus=[{
            "buttons": buttons,
            "x": 0.95, "y": 1.18,
            "xanchor": "right"
        }],
        height=460,
        xaxis_title="Hari - Sesi",
        yaxis_title="Persentase Penggunaan Ruang",
        xaxis_tickangle=45
    )

    return pio.to_html(fig, full_html=False, include_plotlyjs=False)


# ============================================================
# ROUTE — HOME
# ============================================================
@app.route("/")
def home():

    df_ruang, df_matkul = load_data()

    df_gabung = df_matkul.merge(df_ruang[['ruang', 'kapasitas']], on="ruang", how="left")
    df_gabung["peserta"] = pd.to_numeric(df_gabung["peserta"], errors="coerce")
    df_gabung["kapasitas"] = pd.to_numeric(df_gabung["kapasitas"], errors="coerce")

    summary = summary_cards(df_gabung)

    return render_template("index.html", summary=summary)


# ============================================================
# ROUTE — DASHBOARD
# ============================================================
@app.route("/dashboard")
def dashboard():

    semester = request.args.get("semester", "SEMUA").upper()
    hari = request.args.get("hari", "SEMUA").upper()

    df_ruang, df_matkul = load_data(semester)

    return render_template(
        "dashboard.html",
        semester_selected=semester,
        hari_selected=hari,

        chart_ruang=fig_efisiensi_ruang(df_ruang, df_matkul),
        chart_prodi=fig_efisiensi_prodi(df_ruang, df_matkul),
        chart_hari_sesi=fig_efisiensi_hari_sesi(df_ruang, df_matkul, hari),
        chart_penggunaan=fig_penggunaan_kelas(df_ruang, df_matkul, hari),
    )


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    app.run(debug=True)