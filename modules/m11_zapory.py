import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

import ui
from sim import sims

TITLE = "Ochrona zapór i zbiorników retencyjnych"
USER = "RZGW"
PATTERN = r"Zb\.?\s|Zbiornik|Siemian|Dobczyce|Sromowce|Solina|Czchów|Tresna|Rożnów|Żywiec|Besko|Jeziorsko|Otmuchów|Nysa"


def _res(ctx):
    d = ctx["df_all"]
    key = d["stacja"].fillna("") + " " + d["rzeka"].fillna("")
    return d[key.str.contains(PATTERN, case=False, regex=True)].drop_duplicates(["stacja", "rzeka"]).reset_index(drop=True)


def _deform(r):
    g = sims.rng(20)
    return np.round(g.gamma(2.0, 2.5, len(r)) * (0.6 + 0.6 * np.clip(r["pct_alarm"].fillna(30).to_numpy() / 100, 0, 1.2)), 1)


def summary(ctx):
    r = _res(ctx)
    items = []
    hi = r[r["pct_alarm"] >= 80]
    if len(hi):
        items.append(("PILNE" if (hi["pct_alarm"] >= 100).any() else "UWAGA", f"Wysoki stan przy obiektach: {', '.join(hi['stacja'].head(4))} - lot inspekcyjny korony i skarp."))
    if len(r):
        d = _deform(r)
        n = int((d >= 10).sum())
        if n:
            items.append(("UWAGA", f"{n} obiekt(ów) z przemieszczeniem ≥10 mm w porównaniu NMT/LiDAR (DEMO) - pomiar kontrolny."))
    if not items:
        items.append(("OK", "Stany przy zbiornikach poniżej 80% alarmowego, brak deformacji ponad próg."))
    return items


def render():
    ctx = ui.get_ctx()
    ui.header(TITLE, USER, ctx, ui.src_badge(ctx), "DEMO",
              real="stany wody na stacjach przy zbiornikach (dane z całej Polski, np. Siemianówka, Dobczyce, Sromowce Wyżne).",
              demo="deformacje z porównania NMT/LiDAR w czasie.")
    ui.freshness(ctx)
    r = _res(ctx)
    if r.empty:
        st.info("Brak stacji przy zbiornikach w danych.")
        return
    r["deformacja_mm"] = _deform(r)
    r["stan_%"] = r["pct_alarm"].round(0)
    ui.kpis([("Stacje przy zbiornikach", len(r)), ("Maks. % alarmowego", f"{r['pct_alarm'].max():.0f}%" if r["pct_alarm"].notna().any() else "-"),
             ("Nieaktualne", int((~r["aktualny"]).sum())), ("Deformacja ≥10 mm (DEMO)", int((r["deformacja_mm"] >= 10).sum()))])
    fig = px.bar(r, x="stacja", y="stan_%", color="status", color_discrete_map=ui.COLORS, labels={"stan_%": "% stanu alarmowego", "stacja": ""})
    fig.add_hline(y=100, line_color="#d92d20")
    fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, width='stretch')
    m = ui.base_map(r["lat"].mean(), r["lon"].mean(), 5, 380)
    ui.station_traces(m, r)
    st.plotly_chart(m, width='stretch')
    f2 = px.bar(r, x="stacja", y="deformacja_mm", labels={"deformacja_mm": "przemieszczenie repera [mm] (DEMO)", "stacja": ""})
    f2.add_hline(y=10, line_dash="dash", line_color="#f0a020", annotation_text="próg 10 mm")
    f2.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(f2, width='stretch')
    st.dataframe(r[["stacja", "rzeka", "stan_wody", "stan_alarmowy", "stan_%", "status", "deformacja_mm"]], width='stretch', hide_index=True)
    ui.actions(summary(ctx))
