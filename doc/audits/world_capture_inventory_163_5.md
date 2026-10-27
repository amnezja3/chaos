# 163.5.0 — zapisane materiały i rzeczywiste braki

Inspekcja offline: 27.10.2026, punkt wyjścia kodu `46843f8`.
Narzędzie: `tools/world_capture_inventory.py`; zero API, zero zapisów produkcyjnych.
Zakres: `tests/fixtures/poi`, `instance/provider-captures`, `doc/audits/body.json`.
Surowe capture pozostają lokalne; raport nie wypisuje tagów osobowych ani nagłówków.

| Materiał | Obiekty / geometria | Co potwierdza | Czego nie potwierdza |
| --- | --- | --- | --- |
| maplark_roads_bbox_20261024 | 76: 10 Point, 66 LineString | Zapisana odpowiedź i geometrie; hash fixture zgodny | Pełny profil POI, wersja całego zbioru |
| maplark_waterways_bbox_20261024 | 2 LineString | Rzeczywiste cieki; hash fixture zgodny | Wszystkie przypadki graniczne |
| maplark_inland_water_bbox_20261024 | 4 Polygon, bez otworów | Rzeczywiste powierzchnie wody; hash zgodny | MultiPolygon |
| maplark_inland_water_holes_20261025 | 1 Polygon, 2 otwory | Zachowanie otworów; hash zgodny | Wieloczęściowa geometria |
| world_maplark_synthetic | Point, LineString, MultiPolygon z otworem | Lokalny kontrakt dekodera | Rzeczywista odpowiedź dostawcy |
| geometry_reference / geometry_wide_reference | Referencje Overpass z 160 | Selekcja względem lokalnej bazy referencyjnej | Aktualna dostępność publicznego API |

Kopie w `instance/provider-captures` obejmują te same odpowiedzi wody i cieków.
`doc/audits/body.json` zawiera odpowiedź dróg. Nie liczymy ich jako niezależnych
próbek. Wszystkie dziewięć znalezionych GeoJSON-ów ma poprawne geometrie według
lokalnej walidacji topologii. To nie jest dowód kompletności obszaru.

Metadata dróg używa starszego opisu pochodzenia (`captured_by`, `capture_date`,
`source_body_sha256`), bez pola `synthetic`. Narzędzie rozpoznaje zgodność hasha,
ale nie dopisuje automatycznie deklaracji pochodzenia. Udokumentowany odbiór
odpowiedzi pozostaje w `sprint_163_evidence.md`.

## Rozdzielenie braków

| Element | Dane dostępne | Kod dostępny | Pozostały warunek |
| --- | --- | --- | --- |
| Woda z otworami | Tak, rzeczywista próbka | Dekoder, zapis, odczyt, testy | Odbiór zbiorczy; nie pobierać ponownie tylko dla otworów |
| Rzeczywisty MultiPolygon | Nie w sprawdzonych capture | Obsługa i test syntetyczny | Jedna rzeczywista próbka kwalifikująca wieloczęściowość |
| Regionalne Overpass POI | Referencje geometrii | Aktywny router z pakietu 06f9b13 | Zbiorczy odbiór VPS i właściwy zakres źródła |
| Regionalne MapLark POI | Raporty skanu w historii, lokalne capture dotyczą geografii | Dokładny skan działa | Profil regionalny i dowód selekcji; drogi nie zastępują POI |
| Pełny Geoapify POI | Wyniki commercial opisane w audycie | Kolektor commercial działa | Macierz kategorii i zgodność selekcji/geometrii, nie sam nowy klucz API |
| Produkt ląd–woda | Brak rzeczywistego regionalnego produktu | `land_water.py` sprawdza kompletny podział i lineage | Wybór źródła/wersji/licencji, regionalny produkt i integracja importu |
| Wizyty i halo | Nie wymagają nowego capture | 46843f8, lokalne testy PASS | Migracja i aktywacja w zbiorczym odbiorze |

Nie ma podstaw do ponownego zamawiania próbek już potwierdzających drogi, cieki
i otwory. Rzeczywisty MultiPolygon oraz ląd–woda pozostają odrębnymi brakami.
Narzędzie inwentaryzacyjne nie przyznaje uprawnień źródłom ani certyfikatu obszaru.

## Powtórzenie

```bash
.venv/bin/python tools/world_capture_inventory.py tests/fixtures/poi instance/provider-captures
.venv/bin/python -m unittest discover -s tests -p 'test_world_capture_inventory.py'
```

Brak lokalnego katalogu jest jawny jako `missing_roots`; limit 128 plików jest
sygnalizowany przez `truncated`. Pojedynczy plik: do 8 MiB i 10 000 cech.
Pięć testów PASS: geometrie/otwory, hash i naruszenie fixture, pliki uszkodzone,
limity, brak ujawniania treści nagłówków/tagów, odróżnienie syntetyków i duplikatów.
