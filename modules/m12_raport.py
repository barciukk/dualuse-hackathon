from datetime import datetime

import streamlit as st

import ui
from modules import (m01_zalanie, m02_waly, m03_zatory, m04_ewakuacja, m05_szkody, m06_priorytety, m07_poszukiwania,
                     m08_wodne, m09_medyczne, m10_mosty, m11_zapory, m13_loty, m14_siec)

TITLE = "Automatyczny raport z misji w 5 minut"
USER = "dowódca akcji"
SOURCES = [m01_zalanie, m02_waly, m03_zatory, m04_ewakuacja, m05_szkody, m06_priorytety, m07_poszukiwania,
           m08_wodne, m09_medyczne, m10_mosty, m11_zapory, m13_loty, m14_siec]
ORDER = {"PILNE": 0, "UWAGA": 1, "OK": 2}
DEMO_MODULES = {"m05_szkody", "m06_priorytety", "m07_poszukiwania", "m09_medyczne", "m13_loty", "m14_siec"}


def collect(ctx):
    out = []
    for m in [x for x in SOURCES if ui.w_trybie(x)]:
        try:
            items = m.summary(ctx)
        except Exception as e:
            items = [("UWAGA", f"Moduł niedostępny: {e}")]
        out.append((m.TITLE, m.__name__.split(".")[-1], items))
    return out


def build_md(ctx, data):
    df = ctx["df"]
    recs = sorted([(s, t, txt, mod in DEMO_MODULES) for t, mod, its in data for s, txt in its if s != "OK"],
                  key=lambda x: ORDER[x[0]])
    tryb = st.session_state.get("tryb", "Codzienny")
    L = [f"# Raport sytuacyjny - {datetime.now():%Y-%m-%d %H:%M}", "",
         f"Tryb: **{tryb}** · adresat: **{ui.TRYBY[tryb]['uzytkownik']}**", "",
         f"Obszar: **{ctx['voiv']}** · dane IMGW-PIB ({ctx['src']}, ostatni pomiar {ctx['ref']:%Y-%m-%d %H:%M})"
         + (f" · **TRYB SYMULACJI POWODZI {ctx['flood']}%**" if ctx["flood"] else ""), "",
         "## Podsumowanie",
         f"- Stacje: {len(df)}, aktualne: {int(df['aktualny'].sum())}",
         f"- PILNE: {int((df['status'] == 'PILNE').sum())}, UWAGA: {int((df['status'] == 'UWAGA').sum())}, OK: {int((df['status'] == 'OK').sum())}",
         "", "## Co najpierw"]
    if recs:
        for i, (s, t, txt, demo) in enumerate(recs[:5], 1):
            L.append(f"{i}. **[{s}]** {txt}" + (" _(dane demonstracyjne)_" if demo else ""))
    else:
        L.append("Brak działań pilnych - sytuacja spokojna.")
    L += ["", "## Moduły"]
    for t, mod, its in data:
        L.append(f"### {t}" + (" _(DEMO)_" if mod in DEMO_MODULES else ""))
        L += [f"- [{s}] {txt}" for s, txt in its]
    L += ["", "---", "_Źródło danych rzeczywistych: IMGW-PIB (danepubliczne.imgw.pl). Elementy oznaczone DEMO są symulacją. "
          "Raport wspiera decyzję dowódcy, nie zastępuje jej._"]
    return "\n".join(L), recs


def summary(ctx):
    return [("OK", "Raport generowany na żądanie.")]


def render():
    ctx = ui.get_ctx()
    ui.header(TITLE, USER, ctx, ui.src_badge(ctx), "DEMO",
              real="agreguje wnioski z pozostałych modułów (na podstawie szablonu).",
              demo="części pochodzące z modułów demonstracyjnych są oznaczone.")
    ui.freshness(ctx)
    data = collect(ctx)
    md, recs = build_md(ctx, data)
    ui.kpis([("Modułów w raporcie", len(data)), ("Pilne", sum(1 for r in recs if r[0] == "PILNE")),
             ("Uwaga", sum(1 for r in recs if r[0] == "UWAGA"))])
    ui.actions([(s, txt) for s, _, txt, _ in recs[:5]], "Co najpierw (top 5)")
    st.markdown("---")
    st.markdown(md)
    st.download_button("Pobierz raport (.md)", md, file_name=f"raport_{datetime.now():%Y%m%d_%H%M}.md", mime="text/markdown")
