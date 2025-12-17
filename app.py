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

URUTAN_HARI = ["SENIN", "SELASA", "RABU", "KAMIS", "JUMAT"]
URUTAN_SESI = ["1", "2", "3", "4"]

# ============================================================
# LOAD DATA
# ============================================================
def load_data(semester_filter="SEMUA"):
    df_ruang = pd.read_csv(URL_RUANG)
    df_matkul = pd.read_csv(URL_MATKUL)

    df_matkul["th_ajaran"] = df_matkul["th_ajaran"].astype(str).str.upper().str.strip()

    if semester_filter != "SEMUA":
        df_matkul = df_matkul[df_matkul["th_ajaran"] == semester_filter]

    return df_ruang, df_matkul

# ============================================================
# SUMMARY CARDS
# ============================================================
def summary_cards(df):
    df["ef"] = df["peserta"] / df["kapasitas"]

    ef = df.groupby("ruang")["ef"].mean().reset_index()

    ef["kategori"] = pd.cut(
        ef["ef"],
        bins=[0, 0.6, 0.8, 1.5],
        labels=["Tidak Efisien", "Cukup Efisien", "Efisien"],
        include_lowest=True
    )

    total = ef["ruang"].nunique()

    return {
        "efisien": (ef["kategori"] == "Efisien").sum(),
        "efisien_pct": round((ef["kategori"] == "Efisien").mean() * 100, 2),
        "cukup": (ef["kategori"] == "Cukup Efisien").sum(),
        "cukup_pct": round((ef["kategori"] == "Cukup Efisien").mean() * 100, 2),
        "tidak": (ef["kategori"] == "Tidak Efisien").sum(),
        "tidak_pct": round((ef["kategori"] == "Tidak Efisien").mean() * 100, 2),
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
            "x": 0.95,
            "y": 1.20,
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
    df = df_matkul.merge(df_ruang[["ruang", "kapasitas"]], on="ruang", how="left")
    df["ef"] = df["peserta"] / df["kapasitas"]

    ef = df.groupby("prodi")["ef"].mean().reset_index()
    ef["ef_pct"] = (ef["ef"] * 100).round(2)

    fig = go.Figure(go.Bar(
        x=ef["prodi"],
        y=ef["ef_pct"],
        text=ef["ef_pct"].astype(str) + "%",
        textposition="outside"
    ))

    fig.update_layout(height=460)
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)

# ============================================================
# CHART 3 — Efisiensi Hari–Sesi (FIX FINAL)
# ============================================================
def fig_efisiensi_hari_sesi(df_ruang, df_matkul, filter_hari="SEMUA"):

    df = df_matkul.merge(df_ruang[["ruang", "kapasitas"]], on="ruang", how="left")
    df["hari"] = df["hari"].astype(str).str.upper()
    df["sesi"] = df["sesi"].astype(str)
    df["ef"] = df["peserta"] / df["kapasitas"]

    fig = go.Figure()

    for h in ["SEMUA"] + URUTAN_HARI:
        subset = df if h == "SEMUA" else df[df["hari"] == h]

        hari_list = URUTAN_HARI if h == "SEMUA" else [h]
        template = pd.MultiIndex.from_product(
            [hari_list, URUTAN_SESI],
            names=["hari", "sesi"]
        ).to_frame(index=False)

        ef = subset.groupby(["hari", "sesi"])["ef"].mean().reset_index()
        ef = template.merge(ef, on=["hari", "sesi"], how="left").fillna(0)
        ef["ef_pct"] = (ef["ef"] * 100).round(2)

        ef["hari"] = pd.Categorical(ef["hari"], hari_list, ordered=True)
        ef["sesi"] = pd.Categorical(ef["sesi"], URUTAN_SESI, ordered=True)
        ef = ef.sort_values(["hari", "sesi"])

        ef["hari_sesi"] = ef["hari"].astype(str) + " - " + ef["sesi"].astype(str)

        fig.add_trace(go.Bar(
            x=ef["hari_sesi"],
            y=ef["ef_pct"],
            visible=(h == filter_hari),
            text=ef["ef_pct"].astype(str) + "%",
            textposition="outside",
            name=h
        ))

    buttons = []
    for i, h in enumerate(["SEMUA"] + URUTAN_HARI):
        vis = [False] * (len(URUTAN_HARI) + 1)
        vis[i] = True
        buttons.append({"label": h, "method": "update", "args": [{"visible": vis}]})

    fig.update_layout(
        height=460,
        updatemenus=[{"buttons": buttons, "x": 0.95, "y": 1.15, "xanchor": "right"}]
    )

    return pio.to_html(fig, full_html=False, include_plotlyjs=False)

# ============================================================
# CHART 4 — Penggunaan Ruang (FIX FINAL)
# ============================================================
# ============================================================
# CHART 4 — Penggunaan Ruang (FINAL: 2 DROPDOWN SAJA)
# ============================================================
def fig_penggunaan_kelas(df_ruang, df_matkul):

    df = df_matkul.copy()
    df["hari"] = df["hari"].astype(str).str.upper()
    df["sesi"] = df["sesi"].astype(str)

    fig = go.Figure()
    trace_keys = []

    HARI_LIST = ["SEMUA"] + URUTAN_HARI
    SESI_LIST = ["SEMUA"] + URUTAN_SESI

    # ======================================================
    # BUAT TRACE UNTUK SETIAP KOMBINASI HARI & SESI
    # ======================================================
    for hari in HARI_LIST:
        df_hari = df if hari == "SEMUA" else df[df["hari"] == hari]
        hari_vals = URUTAN_HARI if hari == "SEMUA" else [hari]

        for sesi in SESI_LIST:
            df_sesi = df_hari if sesi == "SEMUA" else df_hari[df_hari["sesi"] == sesi]
            sesi_vals = URUTAN_SESI if sesi == "SEMUA" else [sesi]

            # TEMPLATE AGAR YANG KOSONG JADI 0
            template = pd.MultiIndex.from_product(
                [hari_vals, sesi_vals],
                names=["hari", "sesi"]
            ).to_frame(index=False)

            hs = (
                df_sesi
                .groupby(["hari", "sesi"])["ruang"]
                .nunique()
                .reset_index(name="jumlah")
            )

            hs = template.merge(hs, on=["hari", "sesi"], how="left").fillna(0)
            hs["label"] = hs["hari"] + " - " + hs["sesi"]

            fig.add_trace(go.Bar(
                x=hs["label"],
                y=hs["jumlah"],
                visible=(hari == "SEMUA" and sesi == "SEMUA"),
                text=hs["jumlah"],
                textposition="outside"
            ))

            trace_keys.append((hari, sesi))

    # ======================================================
    # DROPDOWN FILTER HARI
    # ======================================================
    hari_buttons = []
    for h in HARI_LIST:
        vis = [(key[0] == h and key[1] == "SEMUA") for key in trace_keys]
        hari_buttons.append({
            "label": h,
            "method": "update",
            "args": [{"visible": vis}]
        })

    # ======================================================
    # DROPDOWN FILTER SESI
    # ======================================================
    sesi_buttons = []
    for s in SESI_LIST:
        vis = [(key[0] == "SEMUA" and key[1] == s) for key in trace_keys]
        sesi_buttons.append({
            "label": s,
            "method": "update",
            "args": [{"visible": vis}]
        })

    # ======================================================
    # LAYOUT
    # ======================================================
    fig.update_layout(
        height=480,
        updatemenus=[
            {
                "buttons": hari_buttons,
                "x": 0.05,
                "y": 1.2,
                "xanchor": "left"
            },
            {
                "buttons": sesi_buttons,
                "x": 0.35,
                "y": 1.2,
                "xanchor": "left"
            }
        ]
    )

    return pio.to_html(fig, full_html=False, include_plotlyjs=False)


# ============================================================
# ROUTE
# ============================================================
@app.route("/dashboard")
def dashboard():
    semester = request.args.get("semester", "SEMUA").upper()
    hari = request.args.get("hari", "SEMUA").upper()

    df_ruang, df_matkul = load_data(semester)

    return render_template(
        "dashboard.html",
        chart_ruang=fig_efisiensi_ruang(df_ruang, df_matkul),
        chart_prodi=fig_efisiensi_prodi(df_ruang, df_matkul),
        chart_hari_sesi=fig_efisiensi_hari_sesi(df_ruang, df_matkul, hari),
        chart_penggunaan=fig_penggunaan_kelas(df_ruang, df_matkul),
        hari_selected=hari,
        semester_selected=semester
    )

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    app.run(debug=True)
