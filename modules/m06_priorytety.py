import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import ui
from sim import sims

TITLE = "Priorytetyzacja pomocy"
USER = "OPS, wojewoda"


def _reports(ctx):
    row = ctx["df"].sort_values("pct_alarm", ascending=False).head(1)
    c = (float(row["lat"].iloc[0]), float(row["lon"].iloc[0])) if len(row) else (50.04, 22.0)
    return sims.reports(c)


def summary(ctx):
    r = _reports(ctx)
    n = int((r["priorytet"] == "PILNE").sum())
    items = []
    if n:
        top = r.iloc[0]
        items.append(("PILNE", f"{n} zgłoszeń o priorytecie pilnym; najwyżej {top['id']} ({top['punkty']} pkt: {top['uzasadnienie']})."))
    items.append(("UWAGA" if (r["priorytet"] == "UWAGA").any() else "OK", f"{int((r['priorytet'] == 'UWAGA').sum())} zgłoszeń wymaga interwencji w ciągu doby (DEMO)."))
    return items


def render():
    ctx = ui.get_ctx()
    ui.header(TITLE, USER, ctx, "DEMO", "REGULY",
              real="algorytm punktowania jest prawdziwy i wyjaśnialny (jawne wagi, uzasadnienie przy każdym zgłoszeniu).",
              demo="zgłoszenia i adresy (losowe, seed stały, brak danych osobowych).")
    r = _reports(ctx)
    ui.kpis([("Zgłoszenia", len(r)), ("Pilne", int((r["priorytet"] == "PILNE").sum())),
             ("Uwaga", int((r["priorytet"] == "UWAGA").sum())), ("Osoby objęte", int(r["osoby"].sum()))])
    with st.expander("Jawne zasady punktowania"):
        for k, (w, label) in sims.WEIGHTS.items():
            st.write(f"+{w} pkt - {label}")
        st.write("+2 pkt za każdą osobę w gospodarstwie (maks. 10). Progi: ≥60 PILNE, ≥30 UWAGA.")
    fig = ui.base_map(r["lat"].mean(), r["lon"].mean(), 11, 400)
    for s in ["OK", "UWAGA", "PILNE"]:
        d = r[r["priorytet"] == s]
        fig.add_trace(go.Scattermap(lat=d["lat"], lon=d["lon"], mode="markers", name=s, marker=dict(size=12, color=ui.COLORS[s]),
                                    text=d["id"] + ": " + d["punkty"].astype(str) + " pkt", hoverinfo="text"))
    st.plotly_chart(fig, width='stretch')
    top = r.head(10)
    f2 = px.bar(top, x="punkty", y="id", orientation="h", color="priorytet", color_discrete_map=ui.COLORS)
    f2.update_layout(height=320, yaxis=dict(autorange="reversed"), margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(f2, width='stretch')
    st.dataframe(r[["id", "punkty", "priorytet", "osoby", "uzasadnienie"]], width='stretch', hide_index=True)
    ui.actions(summary(ctx))
