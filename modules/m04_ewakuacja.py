import plotly.graph_objects as go
import streamlit as st

import ui
from data import osm
from sim import sims

TITLE = "Ewakuacja: które drogi są przejezdne"
USER = "powiatowe centrum zarządzania kryzysowego"


def _classify(roads, clat, clon, r_km):
    ok, fl = ([], []), ([], [])
    n_ok = n_fl = 0
    for w in roads:
        geom = w.get("geometry") or []
        if len(geom) < 2:
            continue
        flooded = any(sims.in_blob(p["lat"], p["lon"], clat, clon, r_km) for p in geom)
        tgt = fl if flooded else ok
        tgt[0].extend([p["lat"] for p in geom] + [None])
        tgt[1].extend([p["lon"] for p in geom] + [None])
        if flooded:
            n_fl += 1
        else:
            n_ok += 1
    return ok, fl, n_ok, n_fl


def summary(ctx):
    df = ctx["df"]
    worst = df["pct_alarm"].max()
    if not (worst == worst) or worst < 80:
        return [("OK", "Brak zalania dróg w danych - sieć dróg przejezdna (status wg stanów IMGW).")]
    row = df.sort_values("pct_alarm", ascending=False).iloc[0]
    st_ = "PILNE" if worst >= 100 else "UWAGA"
    return [(st_, f"Rejon stacji {row['stacja']} ({row['rzeka']}): ryzyko zalania dróg dojazdowych - wyznaczyć trasy ewakuacji poza strefą.")]


def render():
    ctx = ui.get_ctx()
    df = ctx["df"]
    ui.header(TITLE, USER, ctx, "OSM", "DEMO",
              real="sieć dróg z OpenStreetMap (Overpass API) wokół wybranej stacji.",
              demo="warstwa zalania (zasięg wg % stanu alarmowego, docelowo z NMT) i wynikający status przejezdności.")
    ui.freshness(ctx)
    row = ui.pick_station(df, "m04_st")
    if row is None:
        return
    pl, plo, r_km = sims.flood_polygon(row["lat"], row["lon"], row["pct_alarm"], salt=1)
    with st.spinner("Pobieranie dróg z OpenStreetMap…"):
        roads = osm.roads(row["lat"], row["lon"], 4)
    fig = ui.base_map(row["lat"], row["lon"], 12)
    if roads is None:
        st.warning("Overpass API niedostępne - pokazuję tylko warstwę zalania (DEMO).")
        n_ok = n_fl = 0
    else:
        ok, fl, n_ok, n_fl = _classify(roads, row["lat"], row["lon"], r_km)
        fig.add_trace(go.Scattermap(lat=ok[0], lon=ok[1], mode="lines", name="Przejezdne", line=dict(width=3, color="#2e9e5b")))
        fig.add_trace(go.Scattermap(lat=fl[0], lon=fl[1], mode="lines", name="Zalane / nieprzejezdne", line=dict(width=4, color="#d92d20")))
    fig.add_trace(go.Scattermap(lat=pl, lon=plo, mode="lines", fill="toself", name="Zasięg zalania (DEMO)",
                                line=dict(color="#1f5fd1"), fillcolor="rgba(31,95,209,0.30)"))
    tot = max(n_ok + n_fl, 1)
    ui.kpis([("Odcinki dróg (OSM)", n_ok + n_fl), ("Przejezdne", n_ok), ("Nieprzejezdne (DEMO)", n_fl),
             ("Odcięte odcinki", f"{100 * n_fl / tot:.0f}%")])
    st.plotly_chart(fig, width='stretch')
    items = summary(ctx)
    if n_fl:
        items.append(("UWAGA" if n_fl < 0.3 * tot else "PILNE", f"{n_fl} odcinków dróg w strefie zalania - lot drona po trasach ewakuacyjnych potwierdza przejezdność."))
    ui.actions(items)
