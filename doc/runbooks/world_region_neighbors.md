# 162–163 — niezależne odpowiedzi dwóch sąsiednich wycinków

Cel: porównać lokalny wybór z próby parent (76 surowych / 75 po filtrze)
z nowymi odpowiedziami dostawcy. To kolejny test zgodności, nie automatyczny
certyfikat kompletności świata. Kod nie włącza regionalnego odczytu produkcji.

## Ograniczenia

- Lewy bbox 20.36,51.53,20.365,51.54; prawy 20.365,51.53,20.37,51.54.
- Wyłącznie roads/highway, limit 1000, clipGeometry=false.
- Najwyżej dwa HTTP łącznie; każde do 35 s, rezerwacja 20 kredytów.
- Wspólne nieodnawiane okno diagnostyczne 40 kredytów/1 h i istniejące
  limity konta 800/dzień, 24000/31 dni. Nie jest to zdalna gwarancja ceny.
- Odrębne stałe identyfikatory lewego/prawego zapytania. Użytej operacji
  nie można wykonać ponownie; timeout zachowuje rezerwację.
- Niższy priorytet niż oczekujący skan gracza. Żadnych zadań background,
  retry, odnowień permitu, zmian rejestru, migracji, restartu ani ingest.
- Zmiany na VPS: księga/koordynacja transportu oraz nowe prywatne artefakty.
  Porównanie samo jest offline, bez DB i bez sekretu.

## Kod i testy

Po push lokalnego commita na VPS:

```bash
cd ~/app/chaos
git pull --ff-only
.venv/bin/python -m unittest discover -s tests -p 'test_world_region*.py'
.venv/bin/python tools/world_region_probe.py --part left
.venv/bin/python tools/world_region_probe.py --part right
```

Wymagane testy OK i dwa plany z network_calls=0. Nie uruchamiać ponownie parent.

## Jednorazowa próba i porównanie

Uruchomienie tego bloku zatwierdza powyższe dwa zapytania i zmienny koszt.
Klucz pozostaje w subshellu, nie zapisuje się w historii ani raportach.
Sprawdzamy istnienie poprzedniej próbki przed wykonaniem nowych zapytań.

```bash
(
set -eu
umask 077
REGION_PARENT="$HOME/chaos-bbox-roads-oXi9gp/capture"
test -r "$REGION_PARENT/body.json"
test -r "$REGION_PARENT/headers.json"
test -r "$REGION_PARENT/report.json"
REGION_PAIR=$(mktemp -d "$HOME/chaos-bbox-neighbors-XXXXXX")
printf 'Katalog porównania: %s\n' "$REGION_PAIR"
read -r -s -p 'Klucz API MapLark: ' CHAOS_MAPLARK_API_KEY
printf '\n'
export CHAOS_MAPLARK_API_KEY
export CHAOS_POI_PRIORITY_ENABLED=1
.venv/bin/python tools/world_region_probe.py --part left \
  --db data/poi_cache.sqlite3 --output "$REGION_PAIR/left" \
  --execute --approve-bbox-probe --accept-variable-credit-cost
.venv/bin/python tools/world_region_probe.py --part right \
  --db data/poi_cache.sqlite3 --output "$REGION_PAIR/right" \
  --execute --approve-bbox-probe --accept-variable-credit-cost
.venv/bin/python tools/world_region_compare.py \
  --parent "$REGION_PARENT" --left "$REGION_PAIR/left" --right "$REGION_PAIR/right" \
  > "$REGION_PAIR/comparison.json" || {
    cat "$REGION_PAIR/comparison.json"
    exit 1
  }
cat "$REGION_PAIR/comparison.json"
)
```

Przekazać wynik comparison.json oraz raporty rozliczenia. Po błędzie zatrzymać
się: nie kasować operacji, nie zmieniać identyfikatorów ani resetować okna.
Jeżeli lewy wynik jest już zapisany, zachować jego katalog; nie odtwarzać go
ponownie. Dalszy krok ustalimy z przyczyny błędu i stanu księgi.

## Interpretacja

Oczekiwane na niezmienionych danych: left=33, right=54, wspólne 12. Liczby
nie są wymuszane przez narzędzie; rzeczywista zmiana źródła ma być widoczna.
Raport porównuje ID, pełne geometrie oraz klasyfikację highway. Odrzuca
niepełne odpowiedzi, inne bbox w raportach i zmianę rewizji dostawcy.
Geometrie są porównywane topologicznie, bez tolerancji przybliżenia; różna
kolejność punktów nie jest sama w sobie zmianą przebiegu drogi.

Wynik sample_comparison_pass nie oznacza region_certified. Rewizja konfiguracji
CHAOS nie jest wersją zbioru OSM. Zgodność kilku odpowiedzi nie wyklucza tego
samego pominięcia we wszystkich odpowiedziach ani zmian źródła pomiędzy nimi.
dataset_version_verified pozostaje false do niezależnego rozstrzygnięcia.
SHA-256 identyfikuje porównane pliki, nie jest podpisem dostawcy.

Całe porównanie można powtarzać offline; żadne ponowienie porównania nie
uruchamia API. Arkusza wyników nie wykorzystywać do automatycznego wpisania
certyfikatu area. Następny krok zależy od różnic w tej konkretnej próbce.
