import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui
from data.geo import GMINY, NOFLY
from sim import sims

TITLE = "Plan lotów zgodny z prawem"
USER = "operator dronów służb"
MAX_ALT = 120


def check(ctx, place, alt, limit_ms, vlos=True):
    la, lo = GMINY[place]
    w = ui.wind_for(ctx, la, lo)
    wind = float(w["predkosc_wiatru"]) if w is not None else 0.0
    zones = [n for zl, zo, r, n in NOFLY if sims.dist_km((la, lo), (zl, zo)) <= r]
    res = [
        ("Wysokość ≤120 m AGL", alt <= MAX_ALT),
        (f"Wiatr {wind:.1f} m/s ≤ limit {limit_ms} m/s", wind <= limit_ms),
        ("Poza strefami zakazu" if not zones else "W strefie: " + "; ".join(zones), not zones),
        ("Lot w zasięgu wzroku (VLOS)", vlos),
    ]
    return res, wind


def summary(ctx):
    res, wind = check(ctx, "Rzeszów", 100, 10)
    bad = [t for t, ok in res if not ok]
    if not bad:
        return [("OK", "Przykładowy lot nad Rzeszowem zgodny z regułami (wysokość, wiatr, strefy, VLOS).")]
    return [("UWAGA", "Przykładowy lot nad Rzeszowem wymaga zgody/zmiany: " + "; ".join(bad) + ".")]


def render():
    ctx = ui.get_ctx()
    ui.header(TITLE, USER, ctx, "LIVE", "REGULY", "DEMO",
              real="wiatr z najbliższej stacji synoptycznej IMGW.",
              demo="lista lotów i zgód; strefy zakazu to przykładowa lista - produkcyjnie należy użyć oficjalnych danych o strefach UAS (PANSA / DroneRadar).")
    st.caption(f"Pogoda: IMGW synop ({ctx['ssrc']}). Reguły: maks. {MAX_ALT} m, limit wiatru drona, strefy zakazu, VLOS.")
    c1, c2, c3, c4 = st.columns(4)
    place = c1.selectbox("Miejsce lotu", list(GMINY), index=0)
    alt = c2.slider("Wysokość [m AGL]", 10, 200, 100, 10)
    limit = c3.slider("Limit wiatru drona [m/s]", 5, 15, 10)
    vlos = c4.toggle("VLOS", value=True)
    res, wind = check(ctx, place, alt, limit, vlos)
    ok = all(o for _, o in res)
    ui.kpis([("Wiatr", f"{wind:.1f} m/s"), ("Wysokość", f"{alt} m"), ("Decyzja", "ZGODA" if ok else "WYMAGA ZGODY / ZMIANY")])
    ui.actions([("OK" if o else "PILNE", t) for t, o in res], "Kontrola zgodności lotu")
    la, lo = GMINY[place]
    fig = ui.base_map(la, lo, 8, 400)
    for zl, zo, r, n in NOFLY:
        cl, co = ui.circle(zl, zo, r)
        fig.add_trace(go.Scattermap(lat=cl, lon=co, mode="lines", fill="toself", name=n, line=dict(color="#7a1fd1"), fillcolor="rgba(122,31,209,0.2)"))
    fig.add_trace(go.Scattermap(lat=[la], lon=[lo], mode="markers", name="Miejsce lotu", marker=dict(size=14, color="#2e9e5b" if ok else "#d92d20")))
    st.plotly_chart(fig, width='stretch')
    st.markdown("#### Lista planowanych lotów i zgód (DEMO)")
    g = sims.rng(29)
    places = list(GMINY)[:8]
    rows = []
    for i, p in enumerate(places):
        a = int(g.choice([60, 80, 100, 120, 150]))
        r, wd = check(ctx, p, a, 10)
        bad = [t for t, o in r if not o]
        rows.append({"lot": f"L-{i + 1:02d}", "miejsce": p, "wysokość [m]": a, "wiatr [m/s]": round(wd, 1),
                     "status": "OK" if not bad else "UWAGA", "uwagi": "; ".join(bad)})
    st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)
