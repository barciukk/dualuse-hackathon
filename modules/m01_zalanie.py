import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import ui
from data import imgw
from sim import sims

TITLE = "Prognoza zasięgu zalania + weryfikacja dronem"
USER = "sztab kryzysowy gminy"


def warn_summary(ctx):
    flood, drought = [], []
    for w in ctx["warns"]:
        areas = [(a.get("wojewodztwo") or "").lower() for a in w.get("obszary", [])]
        if ctx["voiv"] != "Cała Polska" and ctx["voiv"].lower() not in areas:
            continue
        ev = (w.get("zdarzenie") or "").lower()
        (drought if "susz" in ev else flood).append(w)
    return flood, drought


def summary(ctx):
    df = ctx["df"]
    items = []
    n_p, n_u = (df["status"] == "PILNE").sum(), (df["status"] == "UWAGA").sum()
    flood_w, drought_w = warn_summary(ctx)
    if n_p:
        names = ", ".join(df[df["status"] == "PILNE"]["stacja"].head(5))
        items.append(("PILNE", f"{n_p} stacji powyżej stanu alarmowego ({names}) - uruchomić lot weryfikacyjny i przygotować ewakuację."))
    if flood_w:
        items.append(("UWAGA", f"{len(flood_w)} aktywnych ostrzeżeń hydrologicznych o zagrożeniu powodziowym (IMGW)."))
    near = df[(df["pct_alarm"] >= 70) & (df["status"] != "PILNE")]
    if len(near):
        items.append(("UWAGA", f"{len(near)} stacji powyżej 70% stanu alarmowego - monitorować, przygotować drona."))
    if not n_p and not flood_w and not len(near):
        msg = "Brak zagrożenia powodziowego."
        if drought_w:
            msg += f" Obowiązują ostrzeżenia o suszy hydrologicznej ({len(drought_w)}) - nie dotyczą powodzi."
        items.append(("OK", msg))
    return items


def render():
    ctx = ui.get_ctx()
    df = ctx["df"]
    ui.header(TITLE, USER, ctx, ui.src_badge(ctx), "DEMO",
              real="stany wody, progi, % stanu alarmowego, ostrzeżenia IMGW, mapa stacji, trend z historii 7 dni.",
              demo="zasięg zalania (docelowo z NMT/LiDAR GUGiK), weryfikacja dronem.")
    ui.freshness(ctx)
    flood_w, drought_w = warn_summary(ctx)
    ok = df[df["pct_alarm"].notna() & df["aktualny"]]
    ui.kpis([
        ("Stacje w obszarze", len(df)),
        ("Aktualne pomiary", f"{int(df['aktualny'].sum())}/{len(df)}"),
        ("Maks. % stanu alarmowego", f"{ok['pct_alarm'].max():.0f}%" if len(ok) else "-"),
        ("Powyżej alarmowego", int((df['status'] == 'PILNE').sum())),
        ("Ostrzeżenia powódź / susza", f"{len(flood_w)} / {len(drought_w)}"),
    ])
    if not ctx["flood"] and not flood_w:
        st.success("Brak zagrożenia powodziowego w wybranym obszarze. Włącz „Symuluj powódź” w pasku bocznym, aby zobaczyć działanie modułu.")

    top = ok.sort_values("pct_alarm", ascending=False).head(15)
    if len(top):
        fig = px.bar(top, x="pct_alarm", y="stacja", orientation="h", color="status",
                     color_discrete_map=ui.COLORS, labels={"pct_alarm": "% stanu alarmowego", "stacja": ""})
        fig.add_vline(x=100, line_dash="dash", line_color="#d92d20")
        fig.update_layout(height=420, yaxis=dict(autorange="reversed"), margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, width='stretch')

    st.markdown("#### Prognoza i zasięg zalania dla wybranej stacji")
    row = ui.pick_station(df, "m01_st")
    lat, lon = ui.center(df)
    fig = ui.base_map(lat, lon, 8)
    ui.station_traces(fig, df)
    if row is not None:
        hist = imgw.load_history(row["id_stacji"])
        hrs, pred, slope, to_alarm, how = sims.forecast(hist, row["stan_wody"], row["stan_alarmowy"], ctx["flood"])
        pl, plo, r_km = sims.flood_polygon(row["lat"], row["lon"], row["pct_alarm"], salt=1)
        fig.add_trace(go.Scattermap(lat=pl, lon=plo, mode="lines", fill="toself", name="Zasięg zalania (DEMO)",
                                    line=dict(color="#1f5fd1"), fillcolor="rgba(31,95,209,0.35)"))
        fig.update_layout(map=dict(style="open-street-map", center=dict(lat=row["lat"], lon=row["lon"]), zoom=11))
        c1, c2 = st.columns([3, 2])
        with c2:
            st.plotly_chart(fig, width='stretch')
        with c1:
            f2 = go.Figure()
            if hist is not None:
                f2.add_trace(go.Scatter(x=hist["czas"], y=hist["stan"], name="historia IMGW (7 dni)"))
            f2.add_trace(go.Scatter(x=[row["data_pomiaru"] + pd.Timedelta(hours=int(h)) for h in hrs], y=pred,
                                    name="prognoza (DEMO)", line=dict(dash="dot")))
            f2.add_hline(y=row["stan_alarmowy"], line_color="#d92d20", annotation_text="stan alarmowy")
            f2.add_hline(y=row["stan_ostrzegawczy"], line_color="#f0a020", annotation_text="ostrzegawczy")
            f2.update_layout(height=340, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="stan wody [cm]")
            st.plotly_chart(f2, width='stretch')
        st.caption(f"Tempo zmiany: {slope:+.2f} cm/h ({how}). "
                   + (f"Szacowany czas do stanu alarmowego: {to_alarm:.0f} h." if to_alarm else "Stan alarmowy nie jest osiągany w horyzoncie prognozy.")
                   + f" Promień zasięgu zalania (DEMO): {r_km:.1f} km.")
        st.markdown("**Weryfikacja dronem (DEMO):** lot nad doliną na wysokości 100 m, ortofoto porównywane z prognozą zasięgu; "
                    "wynik koryguje model i decyzję o ewakuacji.")
    else:
        st.plotly_chart(fig, width='stretch')
    ui.actions(summary(ctx))
