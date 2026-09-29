import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import ui
from data import osm
from sim import sims

TITLE = "Szacowanie szkód po powodzi"
USER = "urząd gminy, ubezpieczyciele"
COST = {"brak": 0, "lekkie": 15_000, "średnie": 60_000, "ciężkie": 180_000}
ORTO = ("https://mapy.geoportal.gov.pl/wss/service/PZGIK/ORTO/WMS/StandardResolution?service=WMS&request=GetMap"
        "&layers=Raster&styles=&format=image/jpeg&transparent=false&version=1.1.1&width=256&height=256"
        "&srs=EPSG:3857&bbox={bbox-epsg-3857}")


def summary(ctx):
    df = ctx["df"]
    mx = df["pct_alarm"].max()
    if not (mx == mx) or mx < 100:
        return [("OK", "Brak przekroczeń stanów alarmowych - brak podstaw do szacowania szkód powodziowych.")]
    return [("PILNE", "Po opadnięciu wody: lot dokumentacyjny nad zalanymi zabudowaniami (przed/po) i wstępna wycena szkód dla gminy.")]


def render():
    ctx = ui.get_ctx()
    df = ctx["df"]
    ui.header(TITLE, USER, ctx, "OSM", "DEMO",
              real="budynki z OpenStreetMap, podkład ortofotomapy z WMS Geoportalu (GUGiK).",
              demo="klasyfikacja szkód przed/po (w produkcji: model na zdjęciach z drona) i koszty jednostkowe.")
    ui.freshness(ctx)
    row = ui.pick_station(df, "m05_st")
    if row is None:
        return
    orto = st.toggle("Podkład: ortofotomapa Geoportalu (GUGiK)", value=False)
    with st.spinner("Pobieranie budynków z OpenStreetMap…"):
        b = osm.buildings(row["lat"], row["lon"], 1.0)
    pl, plo, r_km = sims.flood_polygon(row["lat"], row["lon"], max(row["pct_alarm"], 105), salt=1)
    fig = ui.base_map(row["lat"], row["lon"], 14)
    if orto:
        fig.update_layout(map=dict(style="white-bg", center=dict(lat=row["lat"], lon=row["lon"]), zoom=14,
                                   layers=[dict(sourcetype="raster", source=[ORTO], below="traces")]))
    if not b:
        st.warning("Overpass API niedostępne lub brak budynków - pokazuję tylko zasięg zalania (DEMO).")
        d = pd.DataFrame(columns=["lat", "lon", "klasa"])
    else:
        d = pd.DataFrame([{"lat": e["center"]["lat"], "lon": e["center"]["lon"]} for e in b if "center" in e])
        g = sims.rng(5)
        dist = np.hypot((d["lat"] - row["lat"]) * 111, (d["lon"] - row["lon"]) * 111 * 0.64)
        p_dmg = np.clip(1.2 - dist / max(r_km, 0.2), 0, 1) * (0.4 + 0.6 * min(max(row["pct_alarm"], 0) / 100, 1.2))
        u = g.random(len(d))
        d["klasa"] = np.select([u < p_dmg * 0.25, u < p_dmg * 0.6, u < p_dmg], ["ciężkie", "średnie", "lekkie"], "brak")
    colors = {"brak": "#2e9e5b", "lekkie": "#f0d020", "średnie": "#f0a020", "ciężkie": "#d92d20"}
    for k, c in colors.items():
        s = d[d["klasa"] == k]
        if len(s):
            fig.add_trace(go.Scattermap(lat=s["lat"], lon=s["lon"], mode="markers", name=f"Szkody: {k} (DEMO)", marker=dict(size=8, color=c)))
    fig.add_trace(go.Scattermap(lat=pl, lon=plo, mode="lines", line=dict(color="#1f5fd1"), name="Zasięg zalania (DEMO)"))
    cnt = d["klasa"].value_counts() if len(d) else pd.Series(dtype=int)
    loss = sum(cnt.get(k, 0) * v for k, v in COST.items())
    ui.kpis([("Budynki (OSM)", len(d)), ("Ciężkie", int(cnt.get("ciężkie", 0))), ("Średnie", int(cnt.get("średnie", 0))),
             ("Szacunek strat (DEMO)", f"{loss / 1e6:.1f} mln zł")])
    st.plotly_chart(fig, width='stretch')
    if len(cnt):
        f2 = px.bar(cnt.reindex(list(COST)).fillna(0).reset_index(), x="klasa", y="count", color="klasa", color_discrete_map=colors)
        f2.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
        st.plotly_chart(f2, width='stretch')
    st.caption("Koszty jednostkowe (DEMO): " + ", ".join(f"{k} {v:,} zł" for k, v in COST.items() if v))
    ui.actions(summary(ctx))
