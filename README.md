# Dron dashboard - zarządzanie kryzysowe (dual-use)

Streamlit dashboard z 14 modułami dla hackathonu „systemowe wykorzystanie technologii dronowych dual-use w zarządzaniu kryzysowym”.
Flow: potrzeba operacyjna → dron → dane → analiza → wsparcie decyzji.

## Dwa tryby pracy (dual-use)

Ten sam system dronowy służy dwóm środowiskom, co przełącza się w pasku bocznym („Tryb pracy”):

- **Codzienny** - użytkownikiem jest gmina lub powiat: planowe inspekcje wałów, mostów i zapór, monitoring stanów, plan lotów zgodny z prawem, gotowość dronów gminnych.
- **Kryzysowy** - użytkownikiem jest wojewódzka PSP: koordynuje siły i drony gmin oraz powiatów, dostaje panel sytuacyjny i raport pomagający zaplanowanie akcji ratunkowej.

Moduły w trybach:

| Tryb | Moduły |
|---|---|
| Tylko codzienny (gmina/powiat) | Wały, Zatory, Mosty, Zapory, Szkody |
| Tylko kryzysowy (wojewódzka PSP) | Ewakuacja, Priorytety, Poszukiwania, Wodne/lodowe, Sprzęt medyczny |
| Oba tryby | Zasięg zalania, Plan lotów, Sieć dronów, Raport |

Raport zawiera tylko moduły dostępne w wybranym trybie.

Sprzęt, dane i procedury są wspólne, więc w kryzysie nie buduje się nowego systemu.

## Uruchomienie

```
pip install -r requirements.txt
streamlit run app.py lub python -m streamlit run app.py
```

Pasek boczny: wybór modułu, wybór województwa, suwak symulacji powodzi, przycisk odświeżenia danych.

## Źródła danych i atrybucja

- **IMGW-PIB** - stany wód, temperatura wody, przepływ, synop, ostrzeżenia hydrologiczne (`danepubliczne.imgw.pl`, regulamin: `/apiinfo`).
  Dane zapisują się do `data/snapshot_*.json` przy każdym udanym pobraniu i służą jako **fallback offline** (plakietka „MIGAWKA”).
- **Historia 7 dni** - repozytorium `AdamCofala/polish-hydro-data` (trend i prognoza w module Zasięg zalania).
- **OpenStreetMap** - drogi, budynki, mosty. Gdy Overpass nie odpowiada, moduł pokazuje ostrzeżenie i warstwę demo.
- **GUGiK Geoportal** - podkład ortofotomapy (WMS) w module Szkody (przełącznik).

## Co jest realne, a co demo

| Moduł | Realne | Symulacja (DEMO) |
|---|---|---|
| Zasięg zalania + weryfikacja | stany, progi, % alarmowego, ostrzeżenia, trend z historii | zasięg zalania (docelowo NMT), lot weryfikacyjny |
| Wały | stany na Wiśle/Odrze/Sanie | anomalie z drona, porównanie NMT/LiDAR |
| Zatory | skoki stanu między stacjami | rozpoznanie zatoru, trasa inspekcji |
| Ewakuacja | drogi z OSM | zalanie i przejezdność |
| Szkody | budynki OSM, ortofoto GUGiK | klasyfikacja szkód, koszty |
| Priorytety | algorytm punktowania | zgłoszenia |
| Poszukiwania | - (docelowo NMT) | siatka prawdopodobieństwa, kolejność |
| Wodne/lodowe | temperatura wody, przepływ | zdarzenie, dryf |
| Sprzęt medyczny | wiatr | trasa, bateria, strefy |
| Mosty | mosty OSM, stany rzek | wyniki inspekcji |
| Zapory | stany przy zbiornikach | deformacje NMT |
| Raport | agregacja wniosków modułów (szablon, eksport .md) | części z modułów DEMO oznaczone |
| Plan lotów | wiatr, reguły (120 m, wiatr, VLOS) | lista lotów i zgód |
| Sieć dronów | geometria pokrycia | rozmieszczenie dronów |

Progi statusów: **PILNE** gdy stan ≥ alarmowy; **UWAGA** gdy ≥ ostrzegawczy lub pomiar starszy niż 3 h; w przeciwnym razie **OK**.
Stacje bez progów są pomijane w % stanu alarmowego.

Stan na 2026-09-29: wszystkie ostrzeżenia hydrologiczne IMGW dotyczyły suszy, stany były poniżej progów - dashboard pokazuje to wprost
(„brak zagrożenia powodziowego”). Tryb „Symuluj powódź” podbija stany (100% ≈ 110% stanu alarmowego), by pokazać działanie modułów.

## Ograniczenia

- **Strefy zakazu lotów** (`data/geo.py`) to przykładowa lista. Produkcyjnie należy użyć oficjalnych danych o strefach UAS (PANSA / DroneRadar).
- Współrzędne gmin są przybliżone; granice z PRG (GUGiK).
- Modele symulacji (`sim/sims.py`) są uproszczone i mają ustalony seed; nie zastępują decyzji dowódcy akcji.
- Prawne/etyczne: loty zgodnie z przepisami UAS, RODO (brak identyfikacji osób), zgody właścicieli terenu, koordynacja z ATC.
