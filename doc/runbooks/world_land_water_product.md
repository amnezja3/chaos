# Regionalny produkt ląd–morze — kontrakt offline

Implementacja: poi_infrastructure/land_water.py, istniejące world_snapshot /
world_member / world_coverage, bez drugiego magazynu. Brak aktywacji produkcyjnej.

Wybrany kierunek: gotowe, wersjonowane polygony lądu i morza w małym wycinku.
Dokumentacja źródła sprawdzona 24.10.2026:
- https://osmdata.openstreetmap.de/data/land-polygons.html
- https://osmdata.openstreetmap.de/data/water-polygons.html

Produkty powstają z coastline. Water polygons obejmują morza/oceany, nie jeziora
natural=water. Dostawca udostępnia Shapefile WGS84/Mercator, warianty split mogą
nakładać się na szwach; aktualizacje mogą być zatrzymane przez błędy coastline.
Licencja wskazana przez dostawcę: ODbL, OpenStreetMap contributors. Nie znaleziono
w tych opisach kontraktu regionalnego API; nie wdrażamy z tego powodu pobrania
globalnego archiwum na VPS. Pozyskanie dopuszczonego wycinka pozostaje otwarte.

## Wejście

Mały GeoJSON FeatureCollection, każdy Feature: unikalne string id,
properties.surface = land albo sea, geometry Polygon/MultiPolygon WGS84.
Bez OSM ID przypisanego sztucznie produktowi, bez markerów i mieszania z POI.
Pełne geometrie wejściowe zachowane. Pochodzenie: provider, adapter
land-sea-regional-product-v1, snapshot, prawdziwy fetched_at, jawna wersja
datasetu i licencja. Wersja datasetu nie może być zastąpiona datą pobrania.

Manifest JSON wymaga dokładnie:
bounds (4 liczby), provider, snapshot, fetched_at, dataset_version, license_ref,
dependencies (1–16 SHA-256 źródeł), body_sha256 (hash dokładnych bajtów GeoJSON).
Inspektor nie potwierdza prawdziwości ręcznie wpisanego pochodzenia/licencji.

```bash
.venv/bin/python tools/world_land_water_inspect.py --body /sciezka/region.json --manifest /sciezka/manifest.json
```

0 HTTP, 0 DB writes; wynik topology_checked_not_approved. Nie jest to import,
certificate ani nowa zgoda na produkcję. Nie uruchamiać z przykładową ścieżką.

## Walidacja i magazyn

Do 0.02 stopnia na oś, 4 MiB wejścia, 1000 obiektów, 20 000 wierzchołków na
geometrię i 100 000 łącznie. Nieobsługiwany antymeridian. Nie ma repair/buffer(0)
ani uproszczenia: błędna topologia zatrzymuje produkt. Nie domykamy linii brzegu.
Po przecięciu z obszarem dowodu suma lądu i morza musi pokrywać dokładnie region,
bez luk i nakładania przeciwstawnych klas. Nakładanie tej samej klasy dopuszczone
dla split produktów. Sama woda lub sam ląd może pokryć cały wycinek, ale brak
obiektów nigdy nie tworzy domyślnego oceanu. Wszystkie obiekty mają jedno lineage.

LandWaterOrigin przechowuje rolę, obszar, wersję, digest produktu, zależności
i algorytm. Zwykły adapter OSM nie nadaje tego pola na podstawie tagów.
Publikacja korzysta z dotychczasowego lease/revision/storage i wymaga osobnego
certyfikatu area; konstruktor dowodu bez wersji datasetu odmawia działania.
Czytelnik wymaga aktualnych dependency_digests i dataset_version. Zmiana,
brak zależności, wygaśnięcie, rewizja lub zapytanie poza dowodem daje MISS.
Nie łączy źródeł/snapshotów. Stare obiekty bez nowego pola zachowują format.

Testy syntetyczne obejmują wyspę i otwór w morzu po restore, źródła zmienione,
luki, konflikty klas, szwy tej samej klasy, niekompletny/otwarty brzeg,
brak wersji i brak automatycznej certyfikacji. Nie stanowią odbioru źródła live.
