import numpy as np
import pandas as pd

SEED = 2026


def rng(*salt):
    return np.random.default_rng(SEED + sum(int(x) for x in salt))


def flood_polygon(lat, lon, pct_alarm, salt=0):
    r_km = float(np.clip((pct_alarm - 50) / 60 * 3.0, 0.15, 3.5)) if pct_alarm == pct_alarm else 0.15
    g = rng(salt, int(lat * 100))
    a = np.linspace(0, 2 * np.pi, 48)
    rad = r_km * (1 + 0.25 * np.sin(3 * a + g.uniform(0, 6)) + 0.1 * g.normal(size=a.size))
    rad = np.clip(rad, 0.1, None)

    dlat = rad * np.sin(a) * 0.6 / 111.0
    dlon = rad * np.cos(a) * 1.4 / (111.0 * np.cos(np.radians(lat)))
    return lat + dlat, lon + dlon, r_km


def in_blob(lat, lon, clat, clon, r_km):
    dy = (lat - clat) * 111.0 / 0.6
    dx = (lon - clon) * 111.0 * np.cos(np.radians(clat)) / 1.4
    return np.hypot(dx, dy) <= r_km


def forecast(hist, stan_now, alarm, flood_pct, horizon_h=24):
    slope, how = 0.0, "brak historii - tempo 0"
    if hist is not None and len(hist) >= 3:
        h = hist.tail(24)
        t = (h["czas"] - h["czas"].iloc[-1]).dt.total_seconds() / 3600
        if t.max() - t.min() >= 1:
            slope = float(np.polyfit(t, h["stan"], 1)[0])
            how = "regresja liniowa z historii IMGW"
    if flood_pct > 0 and alarm == alarm:
        slope += (alarm * 1.1 - stan_now) * (flood_pct / 100) / 24
        how += " + narastanie symulowane"
    hrs = np.arange(0, horizon_h + 1)
    pred = stan_now + slope * hrs
    to_alarm = None
    if slope > 0 and alarm == alarm and stan_now < alarm:
        to_alarm = (alarm - stan_now) / slope
    return hrs, pred, slope, to_alarm, how


WEIGHTS = {
    "zagrozenie_zycia": (40, "zagrożenie życia"),
    "osoba_wrazliwa": (20, "osoba wrażliwa (75+/niepełnosprawność/dziecko <3 r.ż.)"),
    "brak_ogrzewania": (15, "brak ogrzewania"),
    "odciety": (10, "budynek odcięty od drogi"),
    "brak_pradu": (5, "brak prądu"),
    "brak_lacznosci": (5, "brak łączności"),
}


def score_report(r):
    pts, why = 0, []
    for k, (w, label) in WEIGHTS.items():
        if r[k]:
            pts += w
            why.append(f"+{w} {label}")
    extra = min(int(r["osoby"]) * 2, 10)
    pts += extra
    why.append(f"+{extra} liczba osób ({int(r['osoby'])})")
    return pts, "; ".join(why)


def reports(center, n=25, salt=6):
    g = rng(salt)
    df = pd.DataFrame({
        "id": [f"Z-{i + 1:03d}" for i in range(n)],
        "lat": center[0] + g.normal(0, 0.03, n),
        "lon": center[1] + g.normal(0, 0.05, n),
        "osoby": g.integers(1, 6, n),
        "zagrozenie_zycia": g.random(n) < 0.12,
        "osoba_wrazliwa": g.random(n) < 0.3,
        "brak_ogrzewania": g.random(n) < 0.35,
        "odciety": g.random(n) < 0.4,
        "brak_pradu": g.random(n) < 0.5,
        "brak_lacznosci": g.random(n) < 0.25,
    })
    df["adres"] = [f"adres ukryty (demo) #{i + 1}" for i in range(n)]
    sc = df.apply(score_report, axis=1)
    df["punkty"] = [s[0] for s in sc]
    df["uzasadnienie"] = [s[1] for s in sc]
    df["priorytet"] = np.where(df["punkty"] >= 60, "PILNE", np.where(df["punkty"] >= 30, "UWAGA", "OK"))
    return df.sort_values("punkty", ascending=False).reset_index(drop=True)


def search_grid(clat, clon, n=6, cell_km=0.6, hours=6, mobility_kmh=2.0, salt=12):
    g = rng(salt)
    sigma = max(0.4, mobility_kmh * hours * 0.35)
    rows = []
    for i in range(n):
        for j in range(n):
            dy = (i - (n - 1) / 2) * cell_km
            dx = (j - (n - 1) / 2) * cell_km
            p = np.exp(-(dx * dx + dy * dy) / (2 * sigma ** 2)) * g.uniform(0.7, 1.3)
            rows.append(dict(sektor=f"{chr(65 + i)}{j + 1}", lat=clat + dy / 111.0,
                             lon=clon + dx / (111.0 * np.cos(np.radians(clat))), p=p,
                             trudnosc=float(g.uniform(1, 3))))
    d = pd.DataFrame(rows)
    d["p"] /= d["p"].sum()
    return d, cell_km


def search_order(d, teams, minutes_per_easy=30):
    d = d.copy()
    d["czas_min"] = d["trudnosc"] * minutes_per_easy
    d["wskaznik"] = d["p"] / d["czas_min"]
    d = d.sort_values("wskaznik", ascending=False).reset_index(drop=True)
    d["kolejnosc"] = np.arange(1, len(d) + 1)

    free = np.zeros(teams)
    ends = []
    for m in d["czas_min"]:
        k = int(np.argmin(free))
        free[k] += m
        ends.append(free[k])
    d["koniec_min"] = ends
    d = d.sort_values("koniec_min")
    d["pokrycie_p"] = d["p"].cumsum()
    return d


def coverage(drones, points, speed_kmh, minutes):
    r = speed_kmh * minutes / 60.0
    covered = np.zeros(len(points), bool)
    for la, lo in drones:
        d = np.hypot((points[:, 0] - la) * 111.0, (points[:, 1] - lo) * 111.0 * np.cos(np.radians(la)))
        covered |= d <= r
    return covered, r


def dist_km(a, b):
    return float(np.hypot((a[0] - b[0]) * 111.0, (a[1] - b[1]) * 111.0 * np.cos(np.radians(a[0]))))


def seg_hits_circle(p, q, c, r_km):
    k = np.cos(np.radians(c[0]))
    P = np.array([(p[1] - c[1]) * 111 * k, (p[0] - c[0]) * 111])
    Q = np.array([(q[1] - c[1]) * 111 * k, (q[0] - c[0]) * 111])
    d = Q - P
    L2 = float(d @ d)
    t = 0 if L2 == 0 else float(np.clip(-(P @ d) / L2, 0, 1))
    return float(np.linalg.norm(P + t * d)) <= r_km
