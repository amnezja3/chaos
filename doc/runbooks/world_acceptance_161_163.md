# 161–163 — pakiet panelu i odbiór na VPS

Ten pakiet nie uruchamia nowych prób dostawców. Skaner MapLark zostaje aktywny,
ingest/read pozostają OFF, discovery passive, routing OFF, worker OFF.
Włącza tylko lokalne agregaty skanera po jawnej migracji `--metrics`.
Nie odnawia wygasłego permitu roads i nie rozlicza zaległych operacji Geoapify.

## 1. Kod i testy przed przeładowaniem procesów

Po lokalnym push, na VPS:

```bash
cd ~/app/chaos
git pull --ff-only
.venv/bin/python -m unittest discover -s tests -p 'test_world_*.py'
.venv/bin/python -m unittest discover -s tests -p 'test_poi_*.py'
```

Wymagane oba OK. Zestawy używają baz tymczasowych i transportów testowych.
Zawierają 4 procesy live + 1 background, FIFO/priorytet, wspólny limit kredytów,
idempotencję, restart, fencing, expiry, lokalny odczyt i zgodność eksportu.
Nowe testy obejmują 4 równoczesne procesy zapisujące liczniki, dowody versus
obserwacje, puste wyniki, cofnięcie zgody, CSRF, konflikt rewizji i ręczne saldo.
To testy syntetyczne na VPS, nie pomiar ruchu prawdziwych graczy.

## 2. Migracja agregatów i ręcznych odczytów

```bash
.venv/bin/python tools/poi_world.py --db data/poi_cache.sqlite3 --canonical --discovery --jobs --metrics
```

Oczekiwane dry_run, integrity/FK=ok, original_data_unchanged=true.
Następnie:

```bash
umask 077
WORLD_RELEASE_BACKUP="$HOME/chaos-backups/163-dashboard-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$WORLD_RELEASE_BACKUP"
.venv/bin/python tools/poi_world.py --db data/poi_cache.sqlite3 \
  --canonical --discovery --jobs --metrics --apply \
  --backup "$WORLD_RELEASE_BACKUP/poi_cache.sqlite3"
.venv/bin/python tools/world_release_check.py --db data/poi_cache.sqlite3 --require-metrics
```

Wymagane schema_ready, a raport `ok=true`, `world_schema=2`, metrics_schema_ready,
integrity/FK=ok, production_writes=0, network_calls=0. Raport otwiera źródło
SQLite w mode=ro i bada spójną kopię tymczasową; nie deklaruje, że inni gracze
nie zmieniali równocześnie produkcji. Nie importuje run.py ani kont graczy.

## 3. Aktywacja konfiguracji

```bash
pm2 startOrReload ecosystem.web.config.js --only chaos --update-env &&
pm2 startOrReload ecosystem.discovery.config.js --only chaos-world-discovery-worker --update-env &&
pm2 stop chaos-world-discovery-worker
```

Web ma priority=1 i metrics=1. Worker ma enabled=0, bez --serve i autorestart.
Nie wymaga ponownego wpisywania klucza dostawcy. Żadna flaga wieku nie jest zmieniana.

```bash
for i in $(seq 1 15); do
  code=$(curl -sS -o /dev/null -w '%{http_code}' https://chaos.re/launch)
  printf 'Launch HTTP: %s\n' "$code"
  [ "$code" = "200" ] && break
  sleep 2
done
```

Jeżeli nie ma 200, nie zapisuj PM2; sprawdź logi web. Gdy jest 200:

```bash
pm2 save
.venv/bin/python tools/world_release_check.py --db data/poi_cache.sqlite3 --require-metrics
```

Nie wysyłać całego `pm2 jlist` ani środowiska — mogą zawierać sekrety.

## 4. Testy po wdrożeniu

1. Panel POI / World Discovery: mapa obserwacji, filtry warstw, UNKNOWN,
   lista kolejki, dwa liczniki konta (odczyt ręczny / księga wewnętrzna).
   Pusty widok po wygaśnięciu snapshotu nie jest awarią ani dowodem pustego świata.
2. Jedno zwykłe skanowanie w grze. Powinno działać jak wcześniej. Panel statystyk
   pokaże wynik po odświeżeniu; nie wymuszamy nowych skanów po wyczerpaniu budżetu.
3. Raport `world_release_check.py`: liczba próbek wzrasta; suma źródeł sukcesów
   równa się successful; background/probe nie są w tym mianowniku.
4. Odświeżanie mapy/pan/zoom/zmiana warstwy nie wysyłają requestów do dostawców
   danych. Nie używać przycisków probe podczas tego odbioru.

Lokalne UI sprawdzone przez Playwright MCP. Odbiór produkcji może wykonać agent
przez autoryzowaną sesję przeglądarki; bez niej potrzebny jest wynik operatora.

Opcjonalny porównywalny benchmark (syntetyczny, izolowana baza, 0 API):

```bash
.venv/bin/python tools/world_storage_benchmark.py --counts 50 680 3000
```

Zachować wynik czasu publikacji/odczytu, transakcji, RSS i WAL. Nie traktować
tracemalloc jako RSS ani jednego odczytu WAL jako maksimum obciążenia.

## 5. Granice metryk i panelu

- Mierzone są wyniki `POIFetcher.get_all` przed generowaniem NPC/scen. To nie jest
  pomiar końcowej odpowiedzi całego endpointu ani czasu renderowania przeglądarki.
- Sukces obejmuje pusty kompletny wynik. Osobno błędy i liczba wszystkich prób.
- Udziały world/cache/mixed/network są rozłączne. Nieudane HTTP przed stale-cache
  oznacza network. Nieznane źródło pozostaje unknown. Zero próbek daje brak danych.
- Latencje p50/p95 to górne granice przedziałów histogramu, nie dokładne percentyle.
  Próby transportu oznaczają wejścia do transportu; nie dowodzą odebrania requestu
  przez dostawcę. Okno: bieżąca i 23 poprzednie godziny UTC.
- Agregaty godzinowe usuwane przy zapisie po 7 dniach (bieżąca godzina plus
  poprzednie 168 godzin). Nie zawierają user_id, trasy, współrzędnych ani klucza skanu.
- Mapa pobiera maks. 100 ostatnich snapshotów / 8 MiB payloadów / 2 s zapytań SQL.
  Ograniczony widok jest oznaczony, nie udaje całości bazy. Bez sklejania dowodów,
  rozciągania małego obszaru na cały sektor ani procentu odkrycia planety.
- Dowód exact dla POI nie staje się dowodem obszarowym. Obrys z geometrii obiektów
  jest przerywany i oznaczony UNKNOWN. Cofnięta zgoda blokuje etykietę lokalnego odczytu.
- Saldo panelu dostawcy jest ręcznym odczytem z datą i okresem, po 24 h lub końcu
  okresu oznaczanym jako nieaktualne. Nie zmienia księgi, rezerwacji ani limitów.
  Progi 70/85/95 dotyczą budżetu wewnętrznego. Brak odczytu dostawcy = unknown.

## 6. Regionalny test — roads odebrany w ograniczonym pilocie

Aktualizacja 24.10.2026: niezależne parent/left/right porównane, następnie
pilot 21f62b5 zapisał świeży snapshot 75 dróg. Lokalne wycinki 33/54 oraz
osobny proces --check: PASS, zero HTTP. Pozyskanie: jeden request / 3 kredyty
settled. Procedura i ograniczenia: [pilot roads](world_region_storage_pilot.md).
Nie powtarzać odebranych prób. Poniższy plan offline nadal nie wykonuje HTTP.

```bash
.venv/bin/python tools/world_region_plan.py --layer roads --bbox 20.36 51.53 20.37 51.54
```

To plan 0 HTTP. Alternatywne profile: waterways, inland_water, coastline.
Inspekcję offline z argumentami `--body` i `--headers` uruchamiamy dopiero po
uzyskaniu rzeczywistych plików odpowiedzi z zatwierdzonej próby. Ten pakiet
nie tworzy tych plików. Nie wklejać przykładowych ścieżek; konkretne polecenie
zostanie przygotowane razem z artefaktem próby bbox.

Kontrola sprawdza kompletność odpowiedzi, przecięcie geometrii i kandydatów
w dwóch sąsiednich wycinkach. Nadal zwraca region_certified=false. Nie przyznaje
certyfikatu dostawcy na podstawie jednego sukcesu. Dokumentacja źródłowa:
https://maplark.com/products/osm-features-api (odczyt 24.10.2026; v3 bbox/intersects).
Dotychczasowy zaakceptowany skaner radius pozostaje bez zmian.

Otwarte bramki wymagające rzeczywistych danych: kwalifikacja bbox poza odebraną
próbką, spójność wersji źródła; pilot cieku/jeziora z wyspą/wybrzeża; źródło land_water;
Geoapify pełny profil i rozliczenie. Nie odtwarzać oceanu przez domknięcie coastline
do bbox. Ten pakiet nie ogłasza pełnego PASS 161–163 ani włączenia stałego tła.

## Rollback

Wyłączyć `CHAOS_POI_METRICS_ENABLED` w ecosystem.web.config.js i przeładować web,
jeżeli metryki powodują opóźnienia. Skaner działa przy OFF i przy braku tabel.
Worker pozostaje OFF; routing/ingest/read nie są aktywowane przez ten pakiet.
Zachować nową bazę i naliczenia. Nie przywracać całego starego SQLite nad
nowymi operacjami kredytowymi; test restore odbywa się wyłącznie na oddzielnej kopii.
