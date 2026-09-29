import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui
from sim import sims

TITLE = "Wykrywanie zatorów na rzekach"
USER = "straż pożarna"
JUMP_PP = 25


def _river_pairs(ctx):
    out = []
    d = ctx["df"]
    for river, g in d[d["pct_alarm"].notna() & d["aktualny"] & d["kilometr_biegu_rzeki"].notna()].groupby("rzeka"):
        g = g.sort_values("kilometr_biegu_rzeki", ascending=False)
        for a, b in zip(g.itertuples(), g.iloc[1:].itertuples()):
            jump = b.pct_alarm - a.pct_alarm
            if abs(jump) >= JUMP_PP:
                out.append((river, a, b, jump))
    return out


def summary(ctx):
    pairs = _river_pairs(ctx)
    items = [("UWAGA", f"{r}: skok stanu {a.stacja} → {b.stacja} o {j:+.0f} p.p. - możliwy zator; skierować drona wzdłuż odcinka.") for r, a, b, j in pairs[:5]]
    if not items:
        items.append(("OK", "Brak nagłych różnic stanu między sąsiednimi stacjami - brak przesłanek zatorów."))
    return items


def render():
    ctx = ui.get_ctx()
    df = ctx["df"]
    ui.header(TITLE, USER, ctx, ui.src_badge(ctx), "DEMO",
              real="stacje i rzeki, skoki stanu (% stanu alarmowego) między sąsiednimi stacjami tej samej rzeki.",
              demo="rozpoznanie zatoru przez drona i trasa inspekcji.")
    ui.freshness(ctx)
    pairs = _river_pairs(ctx)
    ui.kpis([("Rzeki z ≥2 stacjami", int(df.groupby("rzeka")["id_stacji"].count().ge(2).sum())),
             ("Podejrzane odcinki", len(pairs)), ("Próg skoku", f"{JUMP_PP} p.p.")])
    lat, lon = ui.center(df)
    fig = ui.base_map(lat, lon, 7)
    ui.station_traces(fig, df)
    route = None
    if pairs:
        labels = [f"{r}: {a.stacja} → {b.stacja} ({j:+.0f} p.p.)" for r, a, b, j in pairs]
        ch = st.selectbox("Podejrzany odcinek", labels)
        r, a, b, j = pairs[labels.index(ch)]
        route = [(a.lat, a.lon), (b.lat, b.lon)]
        fig.add_trace(go.Scattermap(lat=[p[0] for p in route], lon=[p[1] for p in route], mode="lines+markers",
                                    name="Trasa inspekcji (DEMO)", line=dict(width=4, color="#7a1fd1")))
        fig.update_layout(map=dict(style="open-street-map", center=dict(lat=sum(p[0] for p in route) / 2,
                                                                       lon=sum(p[1] for p in route) / 2), zoom=10))
        km = sims.dist_km(route[0], route[1])
        st.caption(f"Odcinek {km:.1f} km w linii prostej · lot inspekcyjny przy prędkości 40 km/h: ok. {km / 40 * 60:.0f} min.")
    else:
        st.success("Brak podejrzanych odcinków. Włącz symulację powodzi - skoki stanu między stacjami pojawią się w danych.")
    st.plotly_chart(fig, width='stretch')
    if pairs:
        st.markdown("**Wykrycie zatoru przez drona (DEMO):** kamera RGB + termowizja na odcinku - zator drewna/lodu potwierdzony w punkcie "
                    "pośrodku odcinka, szerokość ok. 25 m.")
    ui.actions(summary(ctx))
