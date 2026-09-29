import plotly.express as px
import streamlit as st

import ui

TITLE = "Ratownictwo wodne i lodowe"
USER = "WOPR"
T_WARN, T_URGENT = 15.0, 10.0


def _risk(df):
    t = df["temperatura_wody"]
    return t.where(t.notna())


def summary(ctx):
    df = ctx["df"]
    t = df[df["temperatura_wody"].notna() & df["aktualny"]]
    ice = df[df["zjawisko_lodowe"].astype(str).isin(["1", "2", "3", "4"]) & df["aktualny"]] if "zjawisko_lodowe" in df else df.iloc[0:0]
    items = []
    cold = t[t["temperatura_wody"] < T_URGENT]
    mid = t[(t["temperatura_wody"] >= T_URGENT) & (t["temperatura_wody"] < T_WARN)]
    if len(cold):
        items.append(("PILNE", f"{len(cold)} stacji z wodą <{T_URGENT:.0f} °C (np. {cold.iloc[0]['stacja']}): wysokie ryzyko wychłodzenia - czas przeżycia liczony w minutach."))
    if len(mid):
        items.append(("UWAGA", f"{len(mid)} stacji z wodą {T_URGENT:.0f}-{T_WARN:.0f} °C: ryzyko wychłodzenia, wyposażyć ratowników w suche skafandry."))
    if len(ice):
        items.append(("UWAGA", f"Zjawiska lodowe na {len(ice)} stacjach - ostrzec o niebezpieczeństwie wejścia na lód."))
    if not items:
        items.append(("OK", "Temperatury wody ≥15 °C, brak zjawisk lodowych - ryzyko wychłodzenia niskie."))
    return items


def render():
    ctx = ui.get_ctx()
    df = ctx["df"]
    ui.header(TITLE, USER, ctx, ui.src_badge(ctx), "DEMO",
              real="temperatura wody i przepływ ze stacji IMGW; ocena ryzyka wychłodzenia (<15 °C uwaga, <10 °C pilne).",
              demo="zdarzenie (osoba w wodzie), dryf i obraz z termowizji.")
    ui.freshness(ctx)
    t = df[df["temperatura_wody"].notna() & df["aktualny"]].copy()
    ui.kpis([("Stacje z temp. wody", len(t)), ("Najzimniejsza", f"{t['temperatura_wody'].min():.1f} °C" if len(t) else "-"),
             ("Poniżej 15 °C", int((t["temperatura_wody"] < T_WARN).sum())), ("Poniżej 10 °C", int((t["temperatura_wody"] < T_URGENT).sum()))])
    if t.empty:
        st.info("Brak aktualnych pomiarów temperatury wody w wybranym obszarze.")
    else:
        t["ryzyko"] = t["temperatura_wody"].map(lambda x: "PILNE" if x < T_URGENT else ("UWAGA" if x < T_WARN else "OK"))
        fig = px.bar(t.sort_values("temperatura_wody").head(25), x="temperatura_wody", y="stacja", orientation="h",
                     color="ryzyko", color_discrete_map=ui.COLORS, labels={"temperatura_wody": "temperatura wody [°C]", "stacja": ""})
        fig.update_layout(height=420, yaxis=dict(autorange="reversed"), margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, width='stretch')
        lat, lon = ui.center(t)
        m = ui.base_map(lat, lon, 8, 380)
        t2 = t.assign(status=t["ryzyko"], pct_alarm=t["pct_alarm"])
        ui.station_traces(m, t2)
        st.plotly_chart(m, width='stretch')
        st.markdown("#### Zdarzenie: osoba w wodzie (DEMO)")
        s = st.selectbox("Stacja najbliżej zdarzenia", t["stacja"].tolist())
        r = t[t["stacja"] == s].iloc[0]
        minutes = st.slider("Minuty od zdarzenia", 0, 60, 15)
        q = r["przeplyw"] if r["przeplyw"] == r["przeplyw"] else 1.0
        v = min(0.3 + 0.15 * q ** 0.5, 2.5)
        km = v * minutes * 60 / 1000
        st.write(f"Woda {r['temperatura_wody']:.1f} °C, przepływ {q:.1f} m³/s → szacunkowy dryf ok. **{km:.2f} km** w dół rzeki po {minutes} min "
                 f"(prędkość prądu ~{v:.1f} m/s, model DEMO). Dron z termowizją: przeszukać odcinek do {km * 1.3:.1f} km poniżej punktu zdarzenia.")
    ui.actions(summary(ctx))
