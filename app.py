import streamlit as st

st.set_page_config(page_title="Dron dashboard - zarządzanie kryzysowe", layout="wide")

import ui
from data import imgw
from modules import (m01_zalanie, m02_waly, m03_zatory, m04_ewakuacja, m05_szkody, m06_priorytety,
                     m07_poszukiwania, m08_wodne, m09_medyczne, m10_mosty, m11_zapory, m12_raport, m13_loty, m14_siec)

MODULES = [m01_zalanie, m02_waly, m03_zatory, m04_ewakuacja, m05_szkody, m06_priorytety, m07_poszukiwania,
           m08_wodne, m09_medyczne, m10_mosty, m11_zapory, m12_raport, m13_loty, m14_siec]

st.markdown("<style>.block-container{padding-top:1.5rem}</style>", unsafe_allow_html=True)
with st.sidebar:
    st.title("Dron dashboard")
    st.caption("Dual-use w zarządzaniu kryzysowym · rozwiązanie defensywne")
    st.radio("Tryb pracy", list(ui.TRYBY), key="tryb")
    st.caption(ui.TRYBY[st.session_state["tryb"]]["opis"])
    st.divider()
    NAMES = {m.TITLE: m for m in MODULES if ui.w_trybie(m)}
    choice = st.radio("Moduł", list(NAMES), label_visibility="collapsed")
    st.divider()
    _df, _, _ = imgw.load_hydro()
    voivs = ["Cała Polska"] + sorted(v for v in _df["wojewodztwo"].unique() if v != "-")
    st.selectbox("Województwo", voivs, index=voivs.index("podkarpackie"), key="voiv")
    st.slider("Symuluj powódź (intensywność %)", 0, 100, 0, 5, key="flood",
              help="Podbija stany stacji z progami (100% ≈ 110% stanu alarmowego), aby pokazać działanie modułów.")
    if st.button("Odśwież dane IMGW"):
        st.cache_data.clear()
        st.rerun()
    st.caption("Dane: IMGW-PIB (danepubliczne.imgw.pl), OpenStreetMap, GUGiK Geoportal (ortofoto). Elementy DEMO są symulacją.")

NAMES[choice].render()
