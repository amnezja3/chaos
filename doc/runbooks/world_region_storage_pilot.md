# 162–163 — jeden regionalny snapshot roads

Stan: przygotowany i przetestowany lokalnie; odbiór VPS jeszcze otwarty.
Poprzednie porównanie parent/left/right ma PASS. Nie powtarzamy tych trzech
zapytań. Teraz sprawdzamy świeże pobranie, trwały zapis i lokalny odczyt.

## Co zatwierdza wykonanie

Jeden region `20.36,51.53,20.37,51.54`, highway, limit 1000, pełne geometrie.
Najwyżej jeden request, rezerwacja 20, osobne nieodnawiane okno 20/1 h
oraz istniejące limity 800/dzień i 24000/31 dni. Rezerwacja nie ogranicza
ceny naliczonej przez dostawcę. Nie ma automatycznych powtórek.

`--approve-single-region-pilot` akceptuje ograniczony, empiryczny kontrakt
selekcji dla jednego snapshotu. Podstawa: dokumentacja bbox dostawcy oraz
odebrane niezależne porównanie dwóch wycinków (33/54, identyczne ID i geometrie).
Usuwane są tylko zaobserwowane nadmiarowe geometrie, których envelope przecina
bbox, ale sama geometria nie. Inne błędy, niepełna odpowiedź i pusty pilot
zatrzymują publikację. Nie dowodzi to braku pominięć we wszystkich danych OSM.

Osobny adapter `maplark-roads-single-region-pilot-v1` i certyfikat
`operator-empirical-roads-2036-5153-v1` są dostępne wyłącznie temu CLI.
Nie kwalifikujemy zwykłego adaptera MapLark do regionalnego gameplayu.
Nie przypisujemy wersji źródłowego datasetu: pozostaje nieznana. Czytamy
wyłącznie jeden snapshot, bez łączenia wersji lub regionów. Certyfikat jest
wewnętrzną zgodą operatora na eksperyment, nie poświadczeniem dostawcy.

Wymagane aktualne scope `storage` i `world_storage`, aktywny dostawca, schema v2.
CLI wykonuje spójny backup SQLite przed mutacją. Zapisuje jeden snapshot,
księgę kosztów, koordynację i prywatne artefakty. Pełne geometrie i źródłowe
ID pozostają zachowane. Świeżość 300 s i użyteczność 1800 s liczone są od
rzeczywistego pobrania, nie od późniejszej inspekcji. Nie odświeżamy starych danych.

Nie zmieniamy ecosystem, rejestru, skanera, bramki wieku ani flag read/ingest.
Nie uruchamiamy workera. Nie trzeba restartować PM2 ani ponownie robić pm2 save.

## Push, testy i wykonanie

Po wypchnięciu commita uruchomić na VPS poniższy blok. Klucz wpisany bez echa
pozostaje tylko w subshellu. Katalog nadrzędny i backup tworzone są prywatnie.

```bash
(
set -eu
cd ~/app/chaos
git pull --ff-only
.venv/bin/python -m unittest discover -s tests -p 'test_world_region*.py'
.venv/bin/python -m unittest discover -s tests -p 'test_world_read.py'
.venv/bin/python -m unittest discover -s tests -p 'test_world_acquisition.py'
.venv/bin/python tools/world_region_pilot.py
umask 077
REGION_PILOT=$(mktemp -d "$HOME/chaos-region-storage-XXXXXX")
printf 'Katalog pilota: %s\n' "$REGION_PILOT"
read -r -s -p 'Klucz API MapLark: ' CHAOS_MAPLARK_API_KEY
printf '\n'
export CHAOS_MAPLARK_API_KEY
export CHAOS_POI_PRIORITY_ENABLED=1
.venv/bin/python tools/world_region_pilot.py \
  --db data/poi_cache.sqlite3 \
  --backup "$REGION_PILOT/poi_cache.sqlite3" \
  --output "$REGION_PILOT/capture" \
  --execute --approve-single-region-pilot --accept-variable-credit-cost
.venv/bin/python tools/world_region_pilot.py --db data/poi_cache.sqlite3 --check
)
```

Oczekujemy `published_pilot`, jeden request i settled charge, a weryfikacja
`local_pilot_pass`. Ponowny proces `--check` ma zero requestów i zapisów,
czyta SQLite w mode=ro. Parent/left/right muszą wskazywać ten sam snapshot,
obie części mają zachować pełne geometrie, a suma ich ID odpowiadać parent.
Historyczne liczby 75/33/54 są punktem odniesienia, nie wymuszonym wynikiem.

Przekazać dwa raporty JSON. Nie czekamy ponownie pół godziny: wygaśnięcie,
zmiana rewizji i blokada zwykłego czytnika mają testy automatyczne. Po 300 s
`--check` może poprawnie pokazać `local_pilot_not_fresh`; nie uruchamiać z tego
powodu kolejnego płatnego requestu. `--check` można powtarzać bez sekretu.

## Błąd lub wycofanie

Po błędzie blok zatrzymuje się. Zachować ścieżkę katalogu i raport. Nie kasować
operacji, nie resetować budżetu i nie zmieniać jej stałego ID. Błąd po HTTP
może oznaczać naliczony koszt bez opublikowanego snapshotu; to nie uprawnia
do ponowienia. Artefakty capture i księga pozwalają rozstrzygnąć stan.

Pilot nie przełącza żadnego konsumenta produkcyjnego, więc wycofanie oznacza
pozostawienie flag bez zmian i niewykonywanie następnych operacji. Dane tracą
użyteczność po 1800 s. Nie przywracać całej kopii bazy nad aktywną księgą,
ponieważ usunęłoby to koszty i skany wykonane przez graczy po backupie.
Fizyczne sprzątanie snapshotu odbywa się istniejącym mechanizmem prune.

## Co ten odbiór zamyka

Trwały regionalny zapis roads i lokalny odczyt podobszarów na prawdziwym VPS,
pod ograniczoną zgodą operatora. Nie zamyka kwalifikacji innych regionów,
warstw wodnych/wybrzeży ani stałego pobierania. Szersza aktywacja wymaga osobnej
decyzji; ten pilot nie przenosi ograniczonego certyfikatu do zwykłego routingu.
