import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
import streamlit as st

BASE = "https://danepubliczne.imgw.pl/api/data/"
HERE = os.path.dirname(os.path.abspath(__file__))
HIST_URL = "https://raw.githubusercontent.com/AdamCofala/polish-hydro-data/refs/heads/master/data/{}.json"
STALE_H = 3


def _snap(name):
    return os.path.join(HERE, f"snapshot_{name}.json")


def _fetch(endpoint, name):
    try:
        r = requests.get(BASE + endpoint, timeout=8)
        r.raise_for_status()
        data = r.json()
        if data:
            with open(_snap(name), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            return data, "LIVE IMGW"
    except Exception:
        pass
    with open(_snap(name), encoding="utf-8") as f:
        return json.load(f), "MIGAWKA"


@st.cache_data(ttl=600, show_spinner="Pobieranie danych IMGW…")
def _raw_all():
    jobs = {"hydro": "hydro", "synop": "synop", "warn": "warningshydro"}
    with ThreadPoolExecutor(3) as ex:
        futs = {n: ex.submit(_fetch, ep, n) for n, ep in jobs.items()}
        return {n: f.result() for n, f in futs.items()}


def _num(s):
    return pd.to_numeric(s, errors="coerce")


@st.cache_data(ttl=600, show_spinner=False)
def load_hydro():
    raw, src = _raw_all()["hydro"]
    df = pd.DataFrame(raw)
    for c in ["lon", "lat", "stan_alarmowy", "stan_ostrzegawczy", "stan_wody", "temperatura_wody", "przeplyw", "kilometr_biegu_rzeki"]:
        df[c] = _num(df[c])
    df["data_pomiaru"] = pd.to_datetime(df["stan_wody_data_pomiaru"], errors="coerce")
    df["wojewodztwo"] = df["wojewodztwo"].fillna("-")

    ref = datetime.now() if src == "LIVE IMGW" else df["data_pomiaru"].max()
    df["wiek_h"] = (ref - df["data_pomiaru"]).dt.total_seconds() / 3600
    df["aktualny"] = df["wiek_h"] <= STALE_H
    df = df.dropna(subset=["lon", "lat"]).reset_index(drop=True)
    return df, src, ref


@st.cache_data(ttl=600, show_spinner=False)
def load_synop():
    raw, src = _raw_all()["synop"]
    df = pd.DataFrame(raw)
    for c in ["temperatura", "predkosc_wiatru", "kierunek_wiatru", "wilgotnosc_wzgledna", "suma_opadu", "cisnienie"]:
        df[c] = _num(df[c])
    df["wiatr_kmh"] = df["predkosc_wiatru"] * 3.6
    df["czas"] = pd.to_datetime(df["data_pomiaru"] + " " + df["godzina_pomiaru"].astype(str) + ":00", errors="coerce")
    return df, src


@st.cache_data(ttl=600, show_spinner=False)
def load_warnings():
    raw, src = _raw_all()["warn"]
    return raw, src


@st.cache_data(ttl=3600, show_spinner=False)
def load_history(station_id):
    try:
        r = requests.get(HIST_URL.format(station_id), timeout=10)
        r.raise_for_status()
        rows = json.loads(r.content.decode("utf-8-sig"))
        out = []
        for x in rows:
            d = x.get("data", {})
            out.append((d.get("stan_wody_data_pomiaru"), d.get("stan_wody")))
        h = pd.DataFrame(out, columns=["czas", "stan"])
        h["czas"] = pd.to_datetime(h["czas"], errors="coerce")
        h["stan"] = _num(h["stan"])
        h = h.dropna().drop_duplicates("czas").sort_values("czas")
        return h if len(h) >= 3 else None
    except Exception:
        return None


def apply_flood(df, intensity):
    df = df.copy()
    df["symulowany"] = False
    if intensity <= 0:
        return df
    rng = np.random.default_rng(42)
    k = rng.uniform(0.6, 1.0, len(df))
    has = df["stan_alarmowy"].notna() & df["stan_wody"].notna()
    target = df["stan_alarmowy"] * 1.1
    add = (target - df["stan_wody"]).clip(lower=0) * (intensity / 100) * k
    factor = 1 + (add / df["stan_wody"].clip(lower=20)).where(has, 0)
    df.loc[has, "stan_wody"] = df.loc[has, "stan_wody"] + add[has]
    df["przeplyw"] = df["przeplyw"] * factor
    df.loc[has, "symulowany"] = True
    return df


def add_status(df):
    df = df.copy()
    alarm, warn, st_ = df["stan_alarmowy"], df["stan_ostrzegawczy"], df["stan_wody"]
    df["pct_alarm"] = (st_ / alarm * 100).where(alarm > 0)
    pilne = (st_ >= alarm) & alarm.notna()
    uwaga = ((st_ >= warn) & warn.notna()) | ~df["aktualny"]
    df["status"] = np.where(pilne, "PILNE", np.where(uwaga, "UWAGA", "OK"))
    return df


def get_context(voiv, intensity):
    df, src, ref = load_hydro()
    df = add_status(apply_flood(df, intensity))
    if voiv != "Cała Polska":
        df = df[df["wojewodztwo"] == voiv].reset_index(drop=True)
    return df, src, ref
