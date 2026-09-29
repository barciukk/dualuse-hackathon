import hashlib
import json
import os

import requests
import streamlit as st

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "osm_cache")

HEADERS = {"User-Agent": "dron-dashboard-hackathon/1.0 (crisis management demo)", "Accept": "application/json"}
URLS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


@st.cache_data(ttl=3600, show_spinner=False)
def overpass(query):
    os.makedirs(CACHE, exist_ok=True)
    fp = os.path.join(CACHE, hashlib.md5(query.encode()).hexdigest() + ".json")
    if os.path.exists(fp):
        with open(fp, encoding="utf-8") as f:
            return json.load(f)
    for u in URLS:
        try:
            r = requests.post(u, data={"data": query}, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                els = r.json().get("elements", [])
                with open(fp, "w", encoding="utf-8") as f:
                    json.dump(els, f)
                return els
        except Exception:
            continue
    return None


def bbox(lat, lon, km):
    d = km / 111.0
    dl = km / (111.0 * 0.64)
    return f"{lat - d:.4f},{lon - dl:.4f},{lat + d:.4f},{lon + dl:.4f}"


def roads(lat, lon, km=4):
    hw = "motorway|trunk|primary|secondary|tertiary|residential"
    return overpass(f'[out:json][timeout:12];way["highway"~"^({hw})$"]({bbox(lat, lon, km)});out geom 400;')


def bridges(lat, lon, km=12):
    hw = "motorway|trunk|primary|secondary|tertiary"
    return overpass(f'[out:json][timeout:12];way["bridge"="yes"]["highway"~"^({hw})$"]({bbox(lat, lon, km)});out center 60;')


def buildings(lat, lon, km=1.0):
    return overpass(f'[out:json][timeout:12];way["building"]({bbox(lat, lon, km)});out center 300;')
