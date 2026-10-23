# Sprint 161 — inspekcja i pojedyncza próba MapLark

Stan: przygotowane lokalnie, bez pusha, wdrożenia i prób API. Konta Free
potwierdzone przez operatora. Nie zmieniać flag POI/świata, wieku ani OAuth.
To nie jest instrukcja włączenia nowego skanera.

## Bez sieci i bez klucza

Po dostarczeniu tego pakietu na maszynę docelową zainstalować requirements
(nowa zależność Shapely 2.1.2), uruchomić testy world i poi. Sam plan:

```bash
.venv/bin/python tools/world_discovery_probe.py
```

Wyświetla endpoint, stały publiczny punkt Warszawy (nie położenie gracza),
300 m, pełny zestaw filtrów POI, limit 1000 obiektów, deadline 35 s, maksymalnie
jedno żądanie. Bez DB, secretu i jakiegokolwiek requestu.

Inspekcja syntetycznego pliku (przykład formatu, nie dowód usługi):

```bash
.venv/bin/python tools/world_discovery_inspect.py --provider maplark \
  --body tests/fixtures/poi/world_maplark_synthetic.json \
  --headers tests/fixtures/poi/world_maplark_headers_synthetic.json
```

## Próba — dopiero po zgodzie na ten konkretny zakres

MapLark rozlicza pracę zapytania po jego wykonaniu. Limit 1000 obiektów i 35 s
nie gwarantuje konkretnej liczby kredytów: serwer może dokończyć pracę po
zerwaniu połączenia. Próba to jawna jednorazowa diagnostyka na potwierdzonym
koncie Free, nie wdrożenie wewnętrznego budżetu gry. Jeśli operator wymaga
twardej granicy kredytów tej próby, nie uruchamiać jej bez potwierdzonego
ograniczenia po stronie dostawcy. Nie akceptować nadwyżek płatnego planu.

Po zgodzie: klucz ustawić tylko w bieżącej powłoce, bez wpisywania wartości
w komendzie, logach, PM2 czy czacie. Poniższy blok jest procedurą do zatwierdzenia,
nie potwierdzeniem wykonania. Ścieżka DB musi odpowiadać konfiguracji działającego
CHAOS, aby użyć jego wspólnego slotu upstream.

```bash
(
set -eu
umask 077
read -r -s -p 'MapLark API key: ' CHAOS_MAPLARK_API_KEY
printf '\n'
export CHAOS_MAPLARK_API_KEY
.venv/bin/python tools/world_discovery_probe.py \
  --db data/poi_cache.sqlite3 \
  --output "$HOME/chaos-maplark-161-$(date -u +%Y%m%dT%H%M%SZ)" \
  --execute --accept-variable-credit-cost
)
```

Subshell kończy życie zmiennej. Nowy katalog musi nie istnieć; pliki otrzymują
600, katalog 700 na Linux. Zapis: body.json i dozwolone nagłówki odpowiedzi.
Nie zapisujemy klucza/nagłówków żądania. Błąd nie uruchamia retry. Kolejna ręczna
próba podlega 15-minutowemu ograniczeniu; nie usuwać lease, żeby je obejść.
Po błędzie może zostać pusty katalog diagnostyczny — nie oznacza udanego pobrania.

Wynik `captured_not_approved` oznacza jedynie zebranie próbki, nie PASS PROVIDER.
`captured_contract_error` zachowuje materiał do analizy, ale nie pozwala na
eksport do gry. Nie włączać registry/normal_scan na podstawie samego HTTP 200.
World ingest, cache gry i gameplay nie są modyfikowane; zmienia się wyłącznie
koordynacja diagnostyki w bazie POI (leases/circuit przy błędach).

Następnie przekazać raport i próbkę z nagłówkami do analizy. Potwierdzić zużycie
w panelu konta; brak nagłówka opłaty oznacza unknown, nie zero. Dopiero potem
rozstrzygamy zgodność pełnych geometrii, tagów, relacji, kolejności i kosztu.
Bez tych dowodów nie robimy pusha aktywującego adapter w gameplayu.
