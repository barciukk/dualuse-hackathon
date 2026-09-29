import plotly.graph_objects as go
import streamlit as st

import ui
from data.geo import GMINY
from sim import sims

TITLE = "Poszukiwanie osób zaginionych w terenie"
USER = "policja, GOPR, WOPR"


def _plan(place, hours, teams):
    lat, lon = GMINY[place]
    grid, cell = sims.search_grid(lat, lon, hours=hours)
    return sims.search_order(grid, teams), cell, (lat, lon)


def summary(ctx):
    d, _, _ = _plan("Cisna", 6, 3)
    first = d.sort_values("kolejnosc").head(3)["sektor"].tolist()
    return [("UWAGA", f"Scenariusz demo (Cisna, 3 zespoły): przeszukać najpierw sektory {', '.join(first)}; "
                      f"pokrycie prawdopodobieństwa {100 * d['pokrycie_p'].iloc[min(5, len(d) - 1)]:.0f}% po 6 sektorach.")]


def render():
    ctx = ui.get_ctx()
    ui.header(TITLE, USER, ctx, "DEMO",
              real="teren (docelowo NMT/NMPT z GUGiK i pokrycie z BDOT10k do oceny trudności sektorów).",
              demo="siatka sektorów z prawdopodobieństwem (rozkład normalny wokół ostatniego miejsca), czasy przeszukania, kolejność.")
    c1, c2, c3 = st.columns(3)
    place = c1.selectbox("Ostatnie znane miejsce (LKP)", list(GMINY), index=list(GMINY).index("Cisna"))
    hours = c2.slider("Godziny od zaginięcia", 1, 24, 6)
    teams = c3.slider("Zespoły / drony w akcji", 1, 8, 3)
    d, cell, (lat, lon) = _plan(place, hours, teams)
    d = d.sort_values("koniec_min")
    ui.kpis([("Sektory", len(d)), ("Najwyższe p", f"{100 * d['p'].max():.1f}%"),
             ("Czas do 80% pokrycia", f"{int(d[d['pokrycie_p'] >= 0.8]['koniec_min'].min())} min"),
             ("Sektor 1.", d.sort_values('kolejnosc')['sektor'].iloc[0])])
    fig = ui.base_map(lat, lon, 12, 460)
    pmax = d["p"].max()
    for r in d.itertuples():
        dy, dx = cell / 2 / 111.0, cell / 2 / (111.0 * 0.64)
        a = 0.15 + 0.6 * r.p / pmax
        fig.add_trace(go.Scattermap(
            lat=[r.lat - dy, r.lat - dy, r.lat + dy, r.lat + dy, r.lat - dy],
            lon=[r.lon - dx, r.lon + dx, r.lon + dx, r.lon - dx, r.lon - dx],
            mode="lines", fill="toself", fillcolor=f"rgba(217,45,32,{a:.2f})", line=dict(color="#7a1f11", width=1),
            showlegend=False, hoverinfo="text",
            text=f"{r.sektor}: p={100 * r.p:.1f}% · kolejność {r.kolejnosc} · koniec po {r.koniec_min:.0f} min"))
    fig.add_trace(go.Scattermap(lat=[lat], lon=[lon], mode="markers", name="LKP", marker=dict(size=14, color="#1f5fd1")))
    st.plotly_chart(fig, width='stretch')
    f2 = go.Figure(go.Scatter(x=d["koniec_min"], y=100 * d["pokrycie_p"], mode="lines+markers", line_shape="hv"))
    f2.update_layout(height=280, xaxis_title="czas akcji [min]", yaxis_title="skumulowane prawdopodobieństwo [%]",
                     margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(f2, width='stretch')
    order = d.sort_values("kolejnosc").head(6)
    ui.actions([("PILNE" if i == 0 else "UWAGA", f"Sektor {r.sektor} (p={100 * r.p:.1f}%, ok. {r.czas_min:.0f} min) - zespół {i % teams + 1}.")
                for i, r in enumerate(order.itertuples())], "Kolejność przeszukiwania")
    st.caption("Model demonstracyjny - wspiera koordynatora, nie zastępuje decyzji dowódcy akcji. Bez identyfikacji osób i inwigilacji.")
