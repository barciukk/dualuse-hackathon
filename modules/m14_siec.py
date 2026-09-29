import numpy as np
import plotly.graph_objects as go
import streamlit as st

import ui
from data.geo import GMINY
from sim import sims

TITLE = "Sieć dronów gminnych w gotowości"
USER = "powiat"
DEFAULT_DRONES = ["Rzeszów", "Krosno", "Sanok", "Mielec", "Przemyśl", "Stalowa Wola"]


def _grid():
    la, lo = np.meshgrid(np.linspace(49.05, 50.85, 45), np.linspace(21.1, 23.4, 45))
    return np.column_stack([la.ravel(), lo.ravel()])


def _cov(drones, speed, minutes):
    pts = _grid()
    cov, r = sims.coverage([GMINY[d] for d in drones], pts, speed, minutes)
    gm = np.array(list(GMINY.values()))
    gcov, _ = sims.coverage([GMINY[d] for d in drones], gm, speed, minutes)
    return pts, cov, r, gcov


def summary(ctx):
    pts, cov, r, gcov = _cov(DEFAULT_DRONES, 60, 15)
    names = [n for n, c in zip(GMINY, gcov) if not c]
    if not names:
        return [("OK", "Wszystkie gminy z listy w zasięgu dolotu <15 min (6 dronów, DEMO).")]
    return [("UWAGA", f"Luki pokrycia dolotu <15 min: {', '.join(names[:6])} - rozważyć dodatkowy dron/operatora.")]


def render():
    ctx = ui.get_ctx()
    ui.header(TITLE, USER, ctx, "DEMO",
              real="lokalizacje gmin (przybliżone; produkcyjnie granice z PRG GUGiK) i geometria pokrycia (odległość / prędkość).",
              demo="rozmieszczenie dronów i operatorów.")
    if st.session_state.get("tryb") == "Kryzysowy":
        st.info("Tryb kryzysowy: wojewódzka PSP widzi drony wszystkich gmin i powiatów jako jedną sieć i wskazuje, który dron ma dolecieć w rejon zdarzenia.")
    else:
        st.info("Tryb codzienny: gmina lub powiat utrzymuje własne drony w gotowości i sprawdza, czy pokrywa swój teren.")
    c1, c2, c3 = st.columns([3, 1, 1])
    drones = c1.multiselect("Gminy z dronem w gotowości", list(GMINY), DEFAULT_DRONES)
    speed = c2.slider("Prędkość [km/h]", 30, 90, 60, 5)
    minutes = c3.slider("Dolot < X min", 5, 30, 15)
    if not drones:
        st.info("Wybierz co najmniej jedną gminę.")
        return
    pts, cov, r, gcov = _cov(drones, speed, minutes)
    gaps = [n for n, c in zip(GMINY, gcov) if not c]
    ui.kpis([("Drony", len(drones)), ("Promień dolotu", f"{r:.0f} km"), ("Pokrycie obszaru", f"{100 * cov.mean():.0f}%"),
             ("Gminy poza zasięgiem", f"{len(gaps)}/{len(GMINY)}")])
    fig = ui.base_map(49.95, 22.2, 7, 500)
    unc = pts[~cov]
    fig.add_trace(go.Scattermap(lat=unc[:, 0], lon=unc[:, 1], mode="markers", name="Luka pokrycia", marker=dict(size=6, color="rgba(217,45,32,0.45)")))
    for d in drones:
        cl, co = ui.circle(*GMINY[d], r)
        fig.add_trace(go.Scattermap(lat=cl, lon=co, mode="lines", line=dict(color="#1f5fd1"), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scattermap(lat=[GMINY[d][0] for d in drones], lon=[GMINY[d][1] for d in drones], mode="markers", name="Dron w gotowości",
                                marker=dict(size=13, color="#1f5fd1"), text=drones, hoverinfo="text"))
    gl = [n for n in gaps]
    if gl:
        fig.add_trace(go.Scattermap(lat=[GMINY[n][0] for n in gl], lon=[GMINY[n][1] for n in gl], mode="markers+text", name="Gmina bez pokrycia",
                                    marker=dict(size=11, color="#d92d20"), text=gl, textposition="top right"))
    st.plotly_chart(fig, width='stretch')
    items = summary_for(gaps, minutes)
    ui.actions(items)


def summary_for(gaps, minutes):
    if not gaps:
        return [("OK", f"Wszystkie gminy z listy w zasięgu dolotu <{minutes} min.")]
    return [("UWAGA" if len(gaps) < 6 else "PILNE", f"Bez pokrycia dolotu <{minutes} min: {', '.join(gaps)} - dodać dron lub operatora w pobliżu.")]
