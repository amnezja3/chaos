# Przywracanie fokusu mapy na motocykl

**Etap:** pre-polish po `138.getway.4`  
**Data:** 2026-09-08  
**Severity:** UX/performance  
**Status:** `IMPLEMENTED / LOCAL PASS / SERVER UI TEST PENDING`

## Problem

Po ręcznym przesunięciu mapy na odległy obszar gracz nie miał szybkiej drogi
powrotu do motocykla. Jedynym praktycznym obejściem było zamknięcie i ponowne
otwarcie mapy, co uruchamiało niepotrzebny pełny boot i odczyty snapshotów.

## Rozwiązanie

Pod kontrolką ręcznego odświeżenia dodano zielony przycisk motocykla. Kliknięcie:

- bierze bieżące `LatLng` z `window.avatarMarkerRef`, również podczas animacji;
- korzysta z ostatniej logicznej pozycji jako fallbacku przed utworzeniem markera;
- wykonuje wyłącznie animowane `map.panTo()`;
- zachowuje aktualny zoom, w tym zakres odblokowany przez `map_zoom`;
- nie wykonuje `fetch`, reloadu, teleportu ani zapisu pozycji;
- nie uruchamia ponownie bootu mapy i jej ciężkich snapshotów.

Kontrolka ma dostępny opis `aria-label`, zielony SVG oparty o `currentColor` i
krótki lokalny feedback po kliknięciu.

## Invariant

```text
focus motocykla = zmiana środka viewportu
focus motocykla ≠ ruch gracza
focus motocykla ≠ zmiana zoomu
focus motocykla ≠ reload/synchronizacja mapy
```

## Testy

`tests.test_map_loader_frontend_contract`: `19/19 PASS`.

Regresja potwierdza obecność kontrolki, odczyt aktywnego markera, `panTo`, brak
`fetch`, `setView`, `setZoom` i `window.location.reload` w ścieżce fokusu.

## Pliki

- `templates/map_template.html`
- `tests/test_map_loader_frontend_contract.py`

## Bramka

`LOCAL PASS / SERVER UI TEST PENDING`

