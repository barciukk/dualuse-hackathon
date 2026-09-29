import plotly.graph_objects as go
import streamlit as st

import ui
from data.geo import GMINY, NOFLY
from sim import sims

TITLE = "Dostawa sprzętu medycznego do miejsc odciętych"
USER = "pogotowie, GOPR"
BASE = "Rzeszów"


def _mission(ctx, dest, payload_kg, batt_wh, limit_ms):
    a, b = GMINY[BASE], GMINY[dest]
    km = sims.dist_km(a, b)
    w = ui.wind_for(ctx, b[0], b[1])
    wind = float(w["predkosc_wiatru"]) if w is not None else 0.0

    need = 2 * km * (12 + 8 * payload_kg) * (1 + 0.04 * wind)
    blocked = [n for la, lo, r, n in NOFLY if sims.seg_hits_circle(a, b, (la, lo), r)]
    ok_wind = wind <= limit_ms
    ok_batt = need <= batt_wh * 0.8
    return dict(km=km, wind=wind, station=None if w is None else w["stacja"], need=need, blocked=blocked, ok_wind=ok_wind, ok_batt=ok_batt)


def summary(ctx):
    m = _mission(ctx, "Cisna", 2.0, 500, 10.0)
    if m["ok_wind"] and m["ok_batt"] and not m["blocked"]:
        return [("OK", f"Dostawa {BASE} → Cisna wykonalna: wiatr {m['wind']:.1f} m/s, zapotrzebowanie energii {m['need']:.0f} Wh (DEMO).")]
    why = []
    if not m["ok_wind"]:
        why.append(f"wiatr {m['wind']:.1f} m/s powyżej limitu")
    if not m["ok_batt"]:
        why.append("za mała bateria z 20% rezerwą")
    if m["blocked"]:
        why.append("trasa przecina strefę zakazu")
    return [("UWAGA", f"Dostawa {BASE} → Cisna niewykonalna bezpośrednio: {', '.join(why)}.")]


def render():
    ctx = ui.get_ctx()
    ui.header(TITLE, USER, ctx, "LIVE", "DEMO",
              real="wiatr z najbliższej stacji synoptycznej IMGW.",
              demo="trasa, model baterii, strefy zakazu lotów (przykładowe).")
    st.caption(f"Pogoda: IMGW synop ({ctx['ssrc']}).")
    c1, c2, c3, c4 = st.columns(4)
    dest = c1.selectbox("Miejsce odcięte", [g for g in GMINY if g != BASE], index=list(g for g in GMINY if g != BASE).index("Cisna"))
    payload = c2.slider("Ładunek [kg]", 0.5, 5.0, 2.0, 0.5)
    batt = c3.slider("Bateria [Wh]", 200, 1500, 500, 50)
    limit = c4.slider("Limit wiatru drona [m/s]", 5, 15, 10)
    m = _mission(ctx, dest, payload, batt, limit)
    ui.kpis([("Dystans (linia prosta)", f"{m['km']:.0f} km"), ("Wiatr", f"{m['wind']:.1f} m/s ({m['station']})"),
             ("Energia tam-powrót", f"{m['need']:.0f} Wh"), ("Czas lotu (60 km/h)", f"{2 * m['km']:.0f} min")])
    a, b = GMINY[BASE], GMINY[dest]
    fig = ui.base_map((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 8, 430)
    for la, lo, r, n in NOFLY:
        cl, co = ui.circle(la, lo, r)
        fig.add_trace(go.Scattermap(lat=cl, lon=co, mode="lines", fill="toself", name=n, line=dict(color="#7a1fd1"),
                                    fillcolor="rgba(122,31,209,0.2)"))
    fig.add_trace(go.Scattermap(lat=[a[0], b[0]], lon=[a[1], b[1]], mode="lines+markers", name="Trasa (DEMO)",
                                line=dict(width=4, color="#d92d20" if m["blocked"] else "#2e9e5b")))
    st.plotly_chart(fig, width='stretch')
    items = []
    items.append(("OK" if m["ok_wind"] else "PILNE", f"Wiatr {m['wind']:.1f} m/s {'w limicie' if m['ok_wind'] else 'powyżej limitu ' + str(limit) + ' m/s - odłożyć lot'}."))
    items.append(("OK" if m["ok_batt"] else "PILNE", f"Bateria: potrzeba {m['need']:.0f} Wh, dostępne {batt * 0.8:.0f} Wh po rezerwie 20%."))
    items.append(("OK" if not m["blocked"] else "UWAGA", "Trasa poza strefami zakazu." if not m["blocked"] else "Trasa przecina: " + "; ".join(m["blocked"]) + " - uzyskać zgodę / obejście."))
    ui.actions(items, "Ocena misji")
