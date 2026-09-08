# 138.getway.5 — finalny audyt supermocy 20/20

Status: `COMPLETE / SERVER E2E + GAMEPLAY PASS / GO FOR 138.op.1–3`

Data zamknięcia: `2026-09-08`

## Wynik

| Część | Moc | Rodzina | Kanoniczny call-site | Evidence |
| --- | --- | --- | --- | --- |
| V1 | Insider Feed | `operation_speed` | aktywacja + konstrukcja nowej operacji | server E2E PASS |
| V2 | Wejście Serwisowe | `hack_actions` | aktywacja + zapis `aimed` | server gameplay PASS |
| V3 | Fałszywy Obraz | `operation_risk` | aktywacja + nowa operacja + risk engine | server gameplay PASS |
| V4 | Wrogie Przejęcie | `file_yield` | marker operacji + finalizacja plików GX | server E2E PASS |
| V5 | Predykcja Operacyjna | `operation_speed` | aktywacja + konstrukcja nowej operacji | server E2E PASS |
| E1 | Ujawnienie | `target_security` | aktywacja + CAS celu `aimed` | server gameplay PASS |
| E2 | Przejęcie Narracji | `operation_risk` | aktywacja + nowa operacja + risk engine | server gameplay PASS |
| E3 | Pełne Ujawnienie | `data_quality` | marker operacji + finalizacja plików GX | server E2E PASS |
| E4 | Beacon Oporu | `scan_range` | distance gate komendy skanu | server gameplay PASS |
| E5 | Efekt Domina | `target_security` | aktywacja + CAS celu `aimed` | server gameplay PASS |
| P1 | Węzeł Widmo | `operation_risk` | aktywacja + nowa operacja + risk engine | server gameplay PASS |
| P2 | Glitch Injection | `target_security` | aktywacja + CAS celu `aimed` | server gameplay PASS |
| P3 | Fałszywe Tropienie | `scan_range` | distance gate komendy skanu | server E2E PASS |
| P4 | Pęknięcie Sieci | `map_zoom` | ability snapshot + budowa mapy/TileLayer | server gameplay PASS |
| P5 | Odbicie | `territory_defense` | report + capture/alarm + expiry roju | server gameplay PASS |
| S1 | Skan Integralności | `scan_range` | distance gate komendy skanu | server gameplay PASS |
| S2 | Bastion | `territory_defense` | report + capture/alarm + expiry roju | server gameplay PASS |
| S3 | Odtworzenie | `hack_actions` | aktywacja + zapis `aimed` | server gameplay PASS |
| S4 | Korytarz Zaufania | `operation_risk` | aktywacja + nowa operacja + risk engine | server gameplay PASS |
| S5 | Kwarantanna | `map_zoom` | ability snapshot + budowa mapy/TileLayer | server gameplay PASS |

## Zamrożone inwarianty

- Jedna rodzina ma identyczną mechanikę, limit, expiry i call-site niezależnie od
  profesji. Różni się wyłącznie nazwa, asset, hasło i paleta.
- Aktywne okno trwa `900 s`, cooldown `3600 s` od chwili aktywacji.
- Klient nie wybiera rodziny ani parametrów; produkcyjne mapowanie jest serwerowe.
- `file_value`, `actor_visibility` i `incident_decoy` nie są osiągalne.
- Nie powstał drugi runtime, worker, poller, interpreter ani ciężki odczyt profilu.
- Utrata części zatrzymuje nowe zastosowania, zachowuje cooldown i nie cofa już
  zatwierdzonych mutacji.
- Każda moc ma widoczny dowód w UI, timer z miniaturą, fallback brakującej grafiki
  i System Message dla odrzuconej aktywacji.

## Bramka automatyczna

`tests/test_ghostnetwork_polish_gate.py` jest fail-closed na brak dowolnego kodu,
rodziny, profilu UX lub assetu. Testuje również równe pokrycie klanów `5/5`, brak
rodzin odłożonych i spójność efektu UI z rodziną.

Końcowa regresja: Python `test_ghostnetwork_*` — `444/444 PASS`; celowane pakiety
JS suite/map/delta/SFX/motocykl — `7/7 PASS`; `py_compile` i `git diff --check` —
PASS.

Zamknięcie `138.getway` nie omija osobnej bramki wydajnościowej mapy. Następny
obowiązkowy etap to `138.op.1–3`; dopiero jego wynik pozwala wydać finalne
`GO FOR 138.2`.
