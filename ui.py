import numpy as np
import plotly.graph_objects as go
import streamlit as st

from data import imgw

ICON = {"OK": "🟢", "UWAGA": "🟠", "PILNE": "🔴"}
BADGE = {
    "LIVE": ("LIVE IMGW", "#0b7a3b"),
    "MIGAWKA": ("MIGAWKA IMGW (offline)", "#8a6d00"),
    "DEMO": ("DEMO - symulacja", "#8a1f11"),
    "OSM": ("LIVE OpenStreetMap", "#0b5d7a"),
    "REGULY": ("REGUŁY / przykładowe dane", "#5a3d8a"),
}
TRYBY = {
    "Codzienny": {
        "uzytkownik": "gmina / powiat",
        "opis": "Codzienne zastosowanie: gmina lub powiat prowadzi planowe inspekcje, monitoring infrastruktury, plan lotów i utrzymuje gotowość dronów.",
    },
    "Kryzysowy": {
        "uzytkownik": "wojewódzka PSP",
        "opis": "Sytuacja kryzysowa: użytkownikiem jest wojewódzka PSP, która koordynuje działania, siły i drony gmin i powiatów.",
    },
}
C, K = "Codzienny", "Kryzysowy"
DOSTEPNE = {
    "m01_zalanie": (C, K),
    "m02_waly": (C,),
    "m03_zatory": (C,),
    "m04_ewakuacja": (K,),
    "m05_szkody": (C,),
    "m06_priorytety": (K,),
    "m07_poszukiwania": (K,),
    "m08_wodne": (K,),
    "m09_medyczne": (K,),
    "m10_mosty": (C,),
    "m11_zapory": (C,),
    "m12_raport": (C, K),
    "m13_loty": (C, K),
    "m14_siec": (C, K),
}


def w_trybie(module, tryb=None):
    tryb = tryb or st.session_state.get("tryb", C)
    return tryb in DOSTEPNE[module.__name__.split(".")[-1]]


COLORS = {"OK": "#2e9e5b", "UWAGA": "#f0a020", "PILNE": "#d92d20"}


def get_ctx():
    voiv = st.session_state.get("voiv", "podkarpackie")
    flood = st.session_state.get("flood", 0)
    df_all, src, ref = imgw.get_context("Cała Polska", flood)
    df = df_all if voiv == "Cała Polska" else df_all[df_all["wojewodztwo"] == voiv].reset_index(drop=True)
    synop, ssrc = imgw.load_synop()
    warns, _ = imgw.load_warnings()
    return dict(df=df, df_all=df_all, src=src, ref=ref, synop=synop, ssrc=ssrc, warns=warns, voiv=voiv, flood=flood)


def pick_station(df, key, prefer=("Rzeszów", "Krosno", "Przemyśl")):
    d = df[df["stan_alarmowy"].notna()].sort_values("pct_alarm", ascending=False)
    if d.empty:
        st.info("Brak stacji z progami w wybranym obszarze.")
        return None
    names = [f"{r.stacja} - {r.rzeka}" for r in d.itertuples()]
    idx = next((i for i, r in enumerate(d.itertuples()) if r.stacja in prefer), 0)
    ch = st.selectbox("Stacja / rejon analizy", names, index=idx, key=key)
    return d.iloc[names.index(ch)]


def badge(*kinds):
    html = " ".join(
        f"<span style='background:{BADGE[k][1]};color:#fff;padding:2px 9px;border-radius:10px;"
        f"font-size:0.75rem;font-weight:600;margin-right:4px'>{BADGE[k][0]}</span>"
        for k in kinds
    )
    st.markdown(html, unsafe_allow_html=True)


def src_badge(ctx):
    return "LIVE" if ctx["src"] == "LIVE IMGW" else "MIGAWKA"


def header(title, user, ctx, *kinds, real=None, demo=None):
    st.subheader(title)
    tryb = st.session_state.get("tryb", "Codzienny")
    st.caption(f"Tryb: **{tryb}** · użytkownik: **{TRYBY[tryb]['uzytkownik']}** · odbiorcy informacji: {user}")
    badge(*kinds)
    if ctx["flood"] > 0:
        st.warning(f"Tryb symulacji powodzi aktywny ({ctx['flood']}%) - stany stacji są sztucznie podbite.")
    if real or demo:
        with st.expander("Co jest realne, a co demo"):
            if real:
                st.markdown(f"**Realne:** {real}")
            if demo:
                st.markdown(f"**Symulacja (DEMO):** {demo}")


def freshness(ctx):
    st.caption(
        f"Źródło: IMGW-PIB ({ctx['src']}) · ostatni pomiar w zbiorze: "
        f"{ctx['ref']:%Y-%m-%d %H:%M} · pomiar starszy niż {imgw.STALE_H} h = nieaktualny"
    )


def kpis(items):
    cols = st.columns(len(items))
    for c, it in zip(cols, items):
        c.metric(*it)


def actions(items, title="Lista działań"):
    st.markdown(f"**{title}**")
    if not items:
        st.info("Brak działań do wykonania.")
    for status, text in items:
        st.markdown(f"{ICON[status]} **{status}** - {text}")


def worst(items):
    order = {"OK": 0, "UWAGA": 1, "PILNE": 2}
    return max((s for s, _ in items), key=lambda s: order[s], default="OK")


def base_map(lat, lon, zoom=8, height=460):
    fig = go.Figure()
    fig.update_layout(
        map=dict(style="open-street-map", center=dict(lat=lat, lon=lon), zoom=zoom),
        margin=dict(l=0, r=0, t=0, b=0), height=height, legend=dict(orientation="h", y=1.02),
    )
    return fig


def station_traces(fig, df, name_prefix=""):
    for s in ["OK", "UWAGA", "PILNE"]:
        d = df[df["status"] == s]
        if d.empty:
            continue
        txt = [
            f"{r.stacja} ({r.rzeka})<br>stan {r.stan_wody:.0f} cm"
            + (f" · {r.pct_alarm:.0f}% alarm." if r.pct_alarm == r.pct_alarm else "")
            for r in d.itertuples()
        ]
        fig.add_trace(go.Scattermap(
            lon=d["lon"], lat=d["lat"], mode="markers", name=f"{name_prefix}{s}",
            marker=dict(size=11, color=COLORS[s]), text=txt, hoverinfo="text",
        ))
    return fig


def center(df, default=(50.0, 21.8)):
    if df.empty:
        return default
    return float(df["lat"].mean()), float(df["lon"].mean())


def circle(lat, lon, r_km, n=60):
    a = np.linspace(0, 2 * np.pi, n)
    dlat = r_km / 111.0
    dlon = r_km / (111.0 * np.cos(np.radians(lat)))
    return lat + dlat * np.sin(a), lon + dlon * np.cos(a)


def wind_for(ctx, lat=50.1, lon=22.0):
    from data.geo import SYNOP_XY
    best, bd = None, 1e9
    for _, r in ctx["synop"].iterrows():
        if r["stacja"] in SYNOP_XY and r["predkosc_wiatru"] == r["predkosc_wiatru"]:
            la, lo = SYNOP_XY[r["stacja"]]
            d = (la - lat) ** 2 + ((lo - lon) * 0.64) ** 2
            if d < bd:
                best, bd = r, d
    return best
