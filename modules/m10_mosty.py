import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui
from data import osm
from sim import sims

TITLE = "Monitoring mostów i wiaduktów po powodzi lub uderzeniu"
USER = "zarządca dróg"


def _bridges(df):
    d = df[df["pct_alarm"].notna()].sort_values("pct_alarm", ascending=False).head(3)
    rows = []
    for s in d.itertuples():
        els = osm.bridges(s.lat, s.lon, 8)
        if els is None:
            return None
        for e in els[:25]:
            c = e.get("center")
            if c:
                rows.append(dict(lat=c["lat"], lon=c["lon"], nazwa=e.get("tags", {}).get("name") or f"most OSM {e['id']}",
                                 droga=e.get("tags", {}).get("ref", ""), stacja=s.stacja, rzeka=s.rzeka, pct=s.pct_alarm))
    return pd.DataFrame(rows).drop_duplicates(["lat", "lon"]) if rows else pd.DataFrame(columns=["lat", "lon", "nazwa", "droga", "stacja", "rzeka", "pct"])


def _inspect(b):
    g = sims.rng(18)
    u = g.random(len(b))
    w = np.clip(b["pct"].to_numpy() / 100, 0.1, 1.3)
    stan = np.select([u < 0.06 * w, u < 0.25 * w], ["uszkodzony - zamknąć", "podejrzany - ograniczyć ruch"], "sprawny")
    return stan


def summary(ctx):
    mx = ctx["df"]["pct_alarm"].max()
    if not (mx == mx) or mx < 80:
        return [("OK", "Stany rzek przy mostach poniżej 80% alarmowego - inspekcje planowe, bez pilnej potrzeby.")]
    return [("PILNE" if mx >= 100 else "UWAGA", "Wysoka woda przy mostach: lot inspekcyjny podpór i przyczółków, zamknięcie uszkodzonych obiektów.")]


def render():
    ctx = ui.get_ctx()
    df = ctx["df"]
    ui.header(TITLE, USER, ctx, "OSM", ui.src_badge(ctx), "DEMO",
              real="mosty z OpenStreetMap w rejonie stacji o najwyższym % stanu alarmowego + stan rzeki przy nich.",
              demo="wyniki inspekcji drona (stan techniczny mostów).")
    ui.freshness(ctx)
    with st.spinner("Pobieranie mostów z OpenStreetMap…"):
        b = _bridges(df)
    if b is None:
        st.warning("Overpass API niedostępne - nie można pobrać mostów. Spróbuj później.")
        ui.actions(summary(ctx))
        return
    if b.empty:
        st.info("Nie znaleziono mostów w rejonie.")
        ui.actions(summary(ctx))
        return
    b["wynik"] = _inspect(b)
    ui.kpis([("Mosty (OSM)", len(b)), ("Uszkodzone (DEMO)", int(b["wynik"].str.startswith("uszk").sum())),
             ("Podejrzane (DEMO)", int(b["wynik"].str.startswith("podej").sum())), ("Rzeki przy mostach", b["rzeka"].nunique())])
    fig = ui.base_map(b["lat"].mean(), b["lon"].mean(), 9, 440)
    col = {"sprawny": "#2e9e5b", "podejrzany - ograniczyć ruch": "#f0a020", "uszkodzony - zamknąć": "#d92d20"}
    for k, c in col.items():
        s = b[b["wynik"] == k]
        if len(s):
            fig.add_trace(go.Scattermap(lat=s["lat"], lon=s["lon"], mode="markers", name=f"{k} (DEMO)", marker=dict(size=10, color=c),
                                        text=s["nazwa"] + " · " + s["rzeka"] + f" ({s['pct'].round(0).astype(str)}% alarm.)", hoverinfo="text"))
    st.plotly_chart(fig, width='stretch')
    st.dataframe(b[["nazwa", "droga", "rzeka", "stacja", "pct", "wynik"]].rename(columns={"pct": "% alarm. rzeki"}).round(0),
                 width='stretch', hide_index=True)
    items = summary(ctx)
    n = int(b["wynik"].str.startswith("uszk").sum())
    if n:
        items.append(("PILNE", f"{n} mostów oznaczonych jako uszkodzone (DEMO) - zamknąć dla ruchu do potwierdzenia przez inspektora."))
    ui.actions(items)
