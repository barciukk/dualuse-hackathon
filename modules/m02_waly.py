import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui
from sim import sims

TITLE = "Monitoring wałów przeciwpowodziowych"
USER = "zarząd zlewni, wodociągi"
RIVERS = ["Wisła", "Odra", "San"]


def _river_df(ctx, river):
    d = ctx["df_all"]
    d = d[(d["rzeka"] == river) & d["kilometr_biegu_rzeki"].notna()] if "kilometr_biegu_rzeki" in d else d.iloc[0:0]
    return d


def anomalies(river, km_min, km_max):
    g = sims.rng(len(river))
    kinds = ["przesiąk na skarpie odpowietrznej", "osuwisko skarpy", "obniżenie korony wału (porównanie z NMT/LiDAR)", "nory zwierząt"]
    n = 4
    km = np.sort(g.uniform(km_min, km_max, n))
    return pd.DataFrame({"km rzeki": km.round(1), "anomalia (DEMO)": [kinds[i % 4] for i in range(n)],
                         "ocena ryzyka": np.round(g.uniform(0.2, 0.95, n), 2)})


def summary(ctx):
    items = []
    for r in RIVERS:
        d = _river_df(ctx, r)
        if d.empty:
            continue
        mx = d["pct_alarm"].max()
        if mx >= 100:
            items.append(("PILNE", f"{r}: przekroczony stan alarmowy - natychmiastowa inspekcja dronem wałów na odcinku ze stacjami powyżej alarmu."))
        elif mx >= 80:
            items.append(("UWAGA", f"{r}: maks. {mx:.0f}% stanu alarmowego - zaplanować lot kontrolny wałów."))
    if not items:
        items.append(("OK", "Stany na Wiśle, Odrze i Sanie poniżej 80% stanu alarmowego - inspekcje rutynowe."))
    return items


def render():
    ctx = ui.get_ctx()
    ui.header(TITLE, USER, ctx, ui.src_badge(ctx), "DEMO",
              real="stany wody na Wiśle, Odrze i Sanie ze stacji IMGW (cała Polska, niezależnie od filtra województwa).",
              demo="anomalie wykryte przez drona (przesiąki, osuwiska) i porównanie z NMT/LiDAR.")
    ui.freshness(ctx)
    river = st.radio("Rzeka", RIVERS, horizontal=True)
    d = _river_df(ctx, river).sort_values("kilometr_biegu_rzeki")
    if d.empty:
        st.info("Brak stacji dla tej rzeki.")
        return
    mx = d["pct_alarm"].max()
    ui.kpis([("Stacje na rzece", len(d)), ("Maks. % alarmowego", f"{mx:.0f}%" if mx == mx else "-"),
             ("Nieaktualne pomiary", int((~d["aktualny"]).sum())), ("Powyżej alarmowego", int((d["status"] == "PILNE").sum()))])
    x = d["kilometr_biegu_rzeki"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=d["pct_alarm"], mode="lines+markers", text=d["stacja"], name="% stanu alarmowego"))
    fig.add_hline(y=100, line_color="#d92d20")
    fig.add_hline(y=80, line_color="#f0a020", line_dash="dash")
    fig.update_layout(height=340, xaxis_title="km biegu rzeki (od ujścia)", yaxis_title="% stanu alarmowego",
                      margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, width='stretch')
    lat, lon = ui.center(d)
    m = ui.base_map(lat, lon, 6, 380)
    ui.station_traces(m, d)
    an = anomalies(river, float(x.min()), float(x.max()))
    st.plotly_chart(m, width='stretch')
    st.markdown("**Anomalie z lotu kontrolnego (DEMO)**")
    st.dataframe(an, width='stretch', hide_index=True)
    items = summary(ctx)
    items += [("PILNE" if r > 0.8 else "UWAGA", f"km {k}: {a} (ryzyko {r}) - wysłać ekipę i powtórzyć lot.")
              for k, a, r in an.itertuples(index=False) if r > 0.6]
    ui.actions(items)
