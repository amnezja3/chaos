# 162–163 — cieki i powierzchnie wód: dwie ograniczone odpowiedzi

**24.10.2026: obie próby wykonane na VPS, pobranie i walidacja PASS.**
Cieki: 2 surowe / 1 po filtrze; powierzchnie wód: 4 Polygon, zero otworów.
Łącznie 2 HTTP / 6 kredytów settled; 73 testy VPS PASS. Nie powtarzać poleceń
pobrania zamieszczonych niżej. To zapis wykonanej procedury, nie nowe zlecenie.
Artefakty: `/home/johndoe/chaos-water-region-ZLZnBM`.
Brak odbioru jeziora z wyspą i brak kwalifikacji area dla obu profili.
Drogi zostały odebrane; ich operacji nie powtarzamy i nie zmieniamy.

## Przekazanie zapisanych odpowiedzi do pracy offline

Na lokalnym Windows, z katalogu repozytorium (PowerShell):

```powershell
New-Item -ItemType Directory -Force -Path '.\instance\provider-captures' | Out-Null
scp -O -r 'johndoe@185.201.114.123:/home/johndoe/chaos-water-region-ZLZnBM' '.\instance\provider-captures\'
```

Katalog instance jest już ignorowany przez Git. Zachowujemy oddzielne
body.json, headers.json i report.json dla obu profili; bez nadpisywania
próbki dróg. Transfer nie wykonuje zapytań do dostawcy i nie zmienia VPS.
Przed utworzeniem wersjonowanych fixtures wyodrębnić jedynie geometrię,
tożsamość OSM, niezbędne tagi klasyfikacji i dowody pochodzenia.

Transfer wykonany i sprawdzony lokalnie 24.10.2026. Minimalne fixtures są
w tests/fixtures/poi/maplark_{waterways,inland_water}_bbox_20261024.json,
z metadanymi i hashami surowych body/headers/report. Pięć testów rzeczywistych
geometrii obejmuje selekcję, pełną linię z końcami poza bbox, odrzucenie
nadmiarowego obiektu, backup/restore i izolację dowodów. Nie potrzeba kolejnego
transferu tych plików ani powtórki API. Jezioro z otworem nadal nie występuje
w tych odpowiedziach; nie włączono ich jako regionalnego źródła produkcyjnego.

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

## Następny blok odbioru — jezioro z wyspą (25.10.2026)

Poprzednich waterways/inland_water nie pobierać ponownie. Ich utrwalone dane
mają testy offline, ale nie zawierają otworów ani MultiPolygon.
Nowy kandydat: bbox `16.79,52.26,16.80,52.27` przy Jeziorze Góreckim.
[Oficjalny materiał Wielkopolskiego Parku Narodowego](https://wpn.gov.pl/pliki-do-pobrania/otworz/7051427d-c41f-4b98-9d02-631c6a17116b.pdf)
opisuje wyspy Kopczysko i Zamkową;
[materiał parków narodowych](https://ppn.gov.pl/pliki-do-pobrania/otworz/18014297-63c7-4479-a49b-99c258c067b5.pdf)
podaje punkt przy jeziorze 52.268806, 16.797111. To uzasadnia wybór regionu,
nie dowodzi formatu odpowiedzi API, dokładnego położenia wyspy ani coverage.
Żądamy pełnej geometrii przecinającej mały bbox, bez clipGeometry.

Po push/pull, jeden blok na VPS:

```bash
cd ~/app/chaos
git pull --ff-only
.venv/bin/python -m unittest discover -s tests -p 'test_world_water_topology_probe.py'
.venv/bin/python -m unittest discover -s tests -p 'test_world_region*.py'
bash tools/world_water_topology_acceptance.sh
```

Ostatnie polecenie drukuje tylko plan, nie otwiera bazy ani nie wymaga klucza.
Po przyjęciu tego konkretnego requestu operator uruchamia:

```bash
bash tools/world_water_topology_acceptance.sh --execute
```

Jedno wywołanie MapLark, deadline 35 s, rezerwacja 20 kredytów w istniejącym
budżecie 800/24000; nowy wspólny zakres diagnostyki topologii maksymalnie 40
kredytów na godzinę, bez automatycznego odnawiania. To nie limit ceny dostawcy.
Operacja ma deterministyczny ID z bbox. Timeout pozostaje zarezerwowany;
powtórzenie tej operacji nie powoduje nowego requestu. Zmiana regionu wymaga
nowego uzgodnienia; nie służy obchodzeniu odmowy/timeoutu. Wygasłego okna nie resetować.
Domyślny region poprzedniej próby jest odrzucany: użyć istniejącego capture.

Skrypt zapisuje prywatny katalog `~/chaos-water-topology-*` z body/headers/report
i `topology.json`. Nie restartuje PM2, nie zmienia registry/flag, nie publikuje
world snapshotów. Księga kosztów jest aktualizowana normalnie przez acquire.
Nie uruchamiać skryptu z `bash -x` (klucz wprowadzany cicho w podpowłoce).

Odczyt offline zwraca exit 0 dopiero dla kompletnej, poprawnej odpowiedzi
z wybraną powierzchnią zawierającą otwór. Exit 2 oznacza brak wymaganego dowodu,
nie zachętę do ponowienia API. `water_multipolygon_observed` jest sprawdzany
osobno — sam otwór Polygon nie oznacza MultiPolygon. Liczniki `selected_*`
i flagi topology obejmują tylko poprawne obiekty właściwej warstwy przecinające
bbox; liczniki raw pozostają diagnostyczne. Pełna geometria może wychodzić
poza region, więc sam otwór nie musi leżeć wewnątrz bbox.

Przekazać wydruk raportu oraz zachowane capture. Po analizie przygotować
fixture i sprawdzenie zachowania otworu w magazynie/odczycie/restore.
Nie pobierać ponownie, nie deklarować pełności regionu ani włączać ingest.
