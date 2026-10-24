# 162–163 — cieki i powierzchnie wód: dwie ograniczone odpowiedzi

Pakiet przygotowany lokalnie. Brak wykonania API/VPS dla tych profili.
Drogi zostały odebrane; ich operacji nie powtarzamy i nie zmieniamy.

## Zakres

W istniejącym regionie `20.36,51.53,20.37,51.54` pobieramy osobno `waterway`
i `natural=water`. Nie zakładamy, że ten region zawiera jezioro z wyspą.
Raport ma to ujawnić; pusty wynik lub brak otworów nie zamyka odbioru wysp.

Najwyżej dwa requesty łącznie, bez paginacji/retry. Każdy: limit 1000 obiektów,
clipGeometry=false, deadline 35 s, rezerwacja 20. Wspólne, nieodnawiane okno
diagnostyczne 40 kredytów/1 h i obecne limity konta 800/dzień, 24000/31 dni.
To rezerwacja wewnętrzna, nie gwarantowana maksymalna cena dostawcy.
Skan gracza zachowuje pierwszeństwo; osobne stałe ID operacji per warstwa.

Wymagane obecne dopuszczenie storage i aktywny MapLark. CLI zapisuje tylko
księgę, koordynację i prywatne body/headers/report. Brak world ingest, zmiany
flag, rejestru i mechanik; bez PM2 restart/save. Nie trzeba migrować bazy.

## VPS po push

Poniższy blok zatwierdza te dwie próby. Hasło API nie trafia do historii.

```bash
(
set -eu
cd ~/app/chaos
git pull --ff-only
.venv/bin/python -m unittest discover -s tests -p 'test_world_region*.py'
.venv/bin/python -m unittest discover -s tests -p 'test_world_read.py'
.venv/bin/python -m unittest discover -s tests -p 'test_world_acquisition.py'
.venv/bin/python tools/world_region_probe.py --profile waterways
.venv/bin/python tools/world_region_probe.py --profile inland_water
umask 077
WATER_PROBE=$(mktemp -d "$HOME/chaos-water-region-XXXXXX")
printf 'Katalog odpowiedzi wodnych: %s\n' "$WATER_PROBE"
read -r -s -p 'Klucz API MapLark: ' CHAOS_MAPLARK_API_KEY
printf '\n'
export CHAOS_MAPLARK_API_KEY
export CHAOS_POI_PRIORITY_ENABLED=1
.venv/bin/python tools/world_region_probe.py --profile waterways \
  --db data/poi_cache.sqlite3 --output "$WATER_PROBE/waterways" \
  --execute --approve-bbox-probe --accept-variable-credit-cost
.venv/bin/python tools/world_region_probe.py --profile inland_water \
  --db data/poi_cache.sqlite3 --output "$WATER_PROBE/inland_water" \
  --execute --approve-bbox-probe --accept-variable-credit-cost
)
```

Przekazać oba JSON-y. Pliki body.json i headers.json zachować do analizy offline;
nie wykonywać tych requestów ponownie w celu skopiowania odpowiedzi.
Po błędzie zatrzymać się; nie zmieniać ID, nie czyścić księgi ani resetować okna.
Opłacony request nie oznacza zaakceptowanego źródła ani kompletnego regionu.

## Odczyt wyniku

- `captured_not_certified` i billing settled: pobrana odpowiedź, koszt rozliczony.
- `candidate.prepared_not_certified`: walidacja jednej odpowiedzi; żadnej zgody
  area. `candidate.blocked` podaje powód, nie należy go omijać.
- `topology.geometry_types`, `polygon_parts`, `interior_rings` i
  `water_surface_with_holes_observed` opisują faktycznie zwrócone geometrie.
  Otwarte linie ani punkty nie są zastępowane domyślnymi powierzchniami jezior.
- Wyspa w jeziorze odpowiada otworowi w powierzchni wody, ale same pierścienie
  nie są niezależnym dowodem rzeczywistej geografii. Żadnych nowych gwarancji OSM.
- `region_certified=false`, brak wersji datasetu i brak world ingest pozostają
  prawdziwe. Odbiór roads nie kwalifikuje automatycznie żadnej warstwy wodnej.

Lokalnie sprawdzono pełne LineString z końcami poza bbox, MultiPolygon z otworem
i częścią poza bbox, zachowanie geometrii po SQLite backup/restore i ponownym
otwarciu, pusty wybór wewnątrz otworu, MISS poza dowodem oraz izolację warstw.
Są to syntetyczne testy silnika. Rzeczywiste odpowiedzi są potrzebne do
przygotowania dalszego pilota zapisu; brak otworów w próbce pozostawi odbiór
jeziora z wyspą otwarty bez ponawiania tego samego zapytania.

Wybrzeża i morza pozostają osobnym kontraktem. Nie domykamy coastline do bbox,
nie wyprowadzamy oceanu z braku danych, nie kwalifikujemy land_water.
