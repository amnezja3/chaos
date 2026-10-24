# 162–163 — pierwszy regionalny bbox roads

Stan: narzędzie przygotowane, rzeczywista próba VPS niewykonana.
Cel: zachować odpowiedź dla komórki 20.36,51.53–20.37,51.54 oraz sprawdzić
przecięcie geometrii z bbox i kandydatów po obu stronach jego środka.
To nie jest dowód zgodności z Overpassem ani certyfikat kompletności regionu.

## Zakres

- Jedno ręczne GET MapLark v3, roads/highway, limit 1000, clipGeometry=false.
- Deadline 35 s, bez paginacji, splitów, retry i nowych zadań background.
- Wspólna księga 800/dzień i 24000/31 dni; dodatkowy nieodnawiany limit
  diagnostyczny 20 na godzinę, jedna stała tożsamość operacji.
- Rezerwacja 20 to limit wewnętrzny, nie gwarancja ceny dostawcy. Rzeczywisty
  charge rozliczany z nagłówka; brak charge/timeout pozostawia rezerwację.
- Nie zmienia rejestru, flag, cache, światowych snapshotów ani mechanik gry.
  Zmienia księgę/koordynację transportu i tworzy prywatne pliki diagnostyczne.
- Wymaga aktywnego MapLark z bieżącym zatwierdzeniem storage. Jawne
  --approve-bbox-probe zatwierdza tę pojedynczą diagnostykę, nie regionalny rollout.
- Istniejący włączony priorytet daje pierwszeństwo kolejce skanów; CLI nie
  odczytuje środowiska PM2, dlatego w subshellu ustawiamy priority=1.

## VPS: testy i plan bez HTTP

```bash
cd ~/app/chaos
git pull --ff-only
.venv/bin/python -m unittest discover -s tests -p 'test_world_region*.py'
.venv/bin/python tools/world_region_probe.py
```

Nie potrzeba migracji, restartu ani zmiany ecosystem. Wymagane testy OK,
plan network_calls=0, max_network_calls=1, reservation=20, region_certified=false.

## Jednorazowe wykonanie

Uruchomienie poniższego bloku oznacza zatwierdzenie jednego zapytania o zmiennym
koszcie w istniejącym planie Free. Klucz wpisany bez echa, nie w historii;
zmienna znika po subshellu. Nie wklejać klucza do rozmowy.

```bash
(
set -eu
umask 077
REGION_PARENT=$(mktemp -d "$HOME/chaos-bbox-roads-XXXXXX")
printf 'Katalog diagnostyki: %s\n' "$REGION_PARENT"
read -r -s -p 'Klucz API MapLark: ' CHAOS_MAPLARK_API_KEY
printf '\n'
export CHAOS_MAPLARK_API_KEY
export CHAOS_POI_PRIORITY_ENABLED=1
.venv/bin/python tools/world_region_probe.py \
  --db data/poi_cache.sqlite3 --output "$REGION_PARENT/capture" \
  --execute --approve-bbox-probe --accept-variable-credit-cost
.venv/bin/python tools/world_region_plan.py \
  --layer roads --bbox 20.36 51.53 20.37 51.54 \
  --body "$REGION_PARENT/capture/body.json" \
  --headers "$REGION_PARENT/capture/headers.json"
)
```

Każdy plik ma uprawnienia 0600, katalog 0700. Zapis obejmuje tylko poprawną
odpowiedź JSON, dozwolone nagłówki odpowiedzi i raport; bez nagłówka Authorization.
Po błędzie blok kończy się i nie uruchamia inspekcji nieistniejących plików.
Nie ponawiać przez zmianę identyfikatora, kasowanie wpisów lub reset limitów.
Podeślij raport JSON; pliki body/headers zachowaj do dalszej analizy offline.
Upstream busy przed wysłaniem nie nalicza kosztu; powtórka wymaga sprawdzenia
raportu/stanu, a istniejący katalog nie będzie nadpisany.

## Interpretacja i kolejny krok

`captured_not_certified` potwierdza odebranie pełnej odpowiedzi według nagłówków,
rozliczenie operacji i zapis. `boundary_selection_pass` oznacza jedynie, że
zwrócone geometrie spełniają kontrolowany warunek przecięcia; nie wykrywa
obiektów pominiętych przez dostawcę. Pusty wynik nie wystarcza do oceny granic.
Próbka służy następnie do porównania dwóch lokalnych wycinków, zachowania pełnych
geometrii i zaplanowania niezależnej kontroli selekcji oraz wersji danych.
Nie wystawiamy SelectionProof area i nie włączamy read/ingest po samym HTTP 200.

Inspekcja rozdziela surowy `boundary_selection_pass` od
`local_filter.observed_geometry_pass`. Wyłącznie nadmiarowe, poprawne obiekty
spoza bbox z przecinającym go prostokątem otaczającym mogą zostać odfiltrowane
lokalnie. Pozostałe błędy nie są pomijane. `selected_objects` i zgodność sumy
dwóch wycinków dotyczą zapisanej próbki, nie dowodzą kompletności dostawcy.
Surowe pliki pozostają bez zmian, a pełne geometrie nie są przycinane.

Źródło kontraktu (sprawdzone 24.10.2026):
https://maplark.com/products/osm-features-api — bbox selects intersecting features;
limit może uciąć wynik. Pełna kwalifikacja pozostaje osobnym odbiorem.
