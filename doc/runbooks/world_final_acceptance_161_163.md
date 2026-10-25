# 161–163 — wspólny odbiór przygotowanego pakietu

Nie wykonywać kolejnych pojedynczych prób w trakcie przygotowania. Ten dokument
zbiera fazy do jednego wspólnego przejścia operatora i Codexa. PASS testów nie
aktywuje produkcji i nie oznacza kwalifikacji wszystkich dostawców/warstw.

## 1. Odbiór kodu i stanu, bez zmian produkcyjnych

Po uzgodnieniu terminu i push commita, na VPS:

```bash
cd ~/app/chaos
git pull --ff-only
bash tools/world_vps_acceptance.sh
```

Skrypt zapisuje prywatny katalog raportów, commit, wykonuje pełne zestawy
test_world_*.py i test_poi_*.py na izolowanych fixtures, sprawdza kopię SQLite
przez mode=ro oraz odczytuje wyłącznie dopuszczone pola PM2. Nie drukuje sekretów,
nie uruchamia workera, nie migruje bazy, nie restartuje gry i nie wywołuje API.
Testy wieloprocesowe obejmują wspólne budżety, dedup, lease i priorytet live;
nie są benchmarkiem zachowania wszystkich graczy na produkcji.

Oczekujemy testów OK, storage.ok=true, integrity/foreign_keys=ok oraz
runtime.baseline_matches. Stan oczekiwany: chaos online z właściwego cwd,
MapLark/infrastructure ON, world ingest/read/routing OFF, discovery passive,
age=0, discovery worker stopped albo nieobecny. Brak jawnej wartości flagi
oznacza unknown i wymaga sprawdzenia; skrypt nie dopisuje jej ani nie restartuje.
PM2 metadata nie dowodzi zawartości pamięci każdego workera.

Nowe pola produktu ląd–morze są opcjonalne w istniejącym JSON payloadzie;
nie wymagają migracji tabel. Stary kod nie obsługuje nowego produktu. Rollback
to wyłączenie jego konsumenta i zachowanie danych/księgi; nie przywracamy starej
bazy nad kosztami naliczonymi po backupie. Nie obiecujemy odczytu nowego formatu
przez stary commit. Dotychczasowe obiekty są kodowane bez nowego pola.

## 2. Runtime i gameplay — wspólnie po fazie 1

Faza 1 odebrana na VPS 2026-10-24 dla `9927254`: 273 World + 92 POI PASS,
storage OK i runtime baseline_matches. Raporty operatora:
`/home/johndoe/chaos-world-acceptance-KGe8to`. Nie powtarzać tego zestawu
bez zmiany kodu lub nowego problemu. Przeładowanie web i odbiór gry pozostają
do wykonania; EXPIRED poprzedniego pilota roads nie wymaga ponownego pobierania.

Jeżeli przyjmujemy kod do procesu web, używamy wyłącznie istniejącego
ecosystem.web.config.js, po kontroli flag i konfiguracji sekretów. Nie uruchamiać
nowych flag razem z restartem. Polecenie operatora:

```bash
pm2 startOrReload ecosystem.web.config.js --only chaos --update-env
curl --fail --silent --show-error -o /dev/null -w 'Launch HTTP: %{http_code}\n' https://chaos.re/launch
.venv/bin/python tools/world_runtime_check.py
```

Przy cold start HTTP może być chwilowo niedostępne — sprawdzić log i ponowić
kontrolę strony, nie zapytanie providera. Po poprawnym odbiorze `pm2 save`.

W dwóch kontach testowych: zwykły skan, istniejące markery/kategorie i limit 60,
GhostLab, przerwanie operacji, brak podwójnego naliczenia, cichy powrót z glitcha.
To kontrolowany odbiór gry; skan upstream może wydać kredyty istniejącego budżetu.
Zapisujemy wynik i czas okna, nie prywatne trasy graczy. Mapa admina PL/EN:
warstwy, puste/UNKNOWN/stale, klik szczegółów, zoom i budżety. Sam refresh panelu
nie może tworzyć requestów do dostawcy. Lokalny Playwright sprawdza te interakcje
na fixtures; nie zastępuje odbioru konfiguracji produkcyjnej.

## 3. Dalsze dane źródłowe — jeden uzgodniony plan, nie retry w ciemno

25.10: kolejny konkretny blok jest przygotowany w
[instrukcji wodnej](world_region_water_probe.md#następny-blok-odbioru--jezioro-z-wyspą-25102026).
`world_water_topology_acceptance.sh` domyślnie pokazuje plan;
--execute to jedno uzgodnione pobranie, potem wyłącznie kontrola offline.
Nie wymaga restartu gry ani zmiany flag.

Nie powtarzać już odebranych roads ani water-2036-5153. Zachowane body/headers
mają fixtures i hash, można pracować offline. Dodatkowa próba jeziora z 25.10
zwróciła Polygon z dwoma otworami za 3 kredyty. Pliki otrzymano lokalnie,
utworzono fixture z hashami; zachowanie otworów, pusty odczyt wyspy wewnątrz
dowodu, MISS poza nim i backup/restore przeszły testy (regresja regionalna 58 PASS).
Nie powtarzać również tego requestu. Rzeczywisty MultiPolygon nie został jeszcze
otrzymany; syntetyczne testy tego typu nie są dowodem danych dostawcy.

Warstwa ląd–morze ma lokalny kontrakt gotowego regionalnego produktu,
opisany w world_land_water_product.md. Brak zatwierdzonego regionalnego źródła
i rzeczywistych danych blokuje jej ON, nie testy silnika. Żadnego automatycznego
pobierania całej planety lub zamykania otwartego brzegu do bbox.

Geoapify: pełny profil skanera niepotwierdzony; 4 niepewne operacje zachowują
rezerwacje. Odczyt sumy z panelu nie rozstrzyga każdej z nich. Hierarchia może
pokazać i pominąć źródło niekwalifikowane; samo ustawienie na pierwszym miejscu
nie daje zgody na użycie. Nie zerować księgi, nie nadawać approval na podstawie
samych 63 obiektów commercial ani nie traktować Point jako pełnej geometrii.

## 4. Kontrolowane ON i obserwacja

Osobny uzgodniony zakres per warstwa: regiony, prawa storage/background,
fresh/usable, czas pozwolenia, liczba zadań, limity konta i warstwy, progi stop.
Istniejący jednorazowy worker i permit są mechanizmem wdrożenia; nie ustawiamy
autorestart=true i nie odnawiamy wygasłego pozwolenia automatycznie.

Kontrolować requesty/kredyty, local vs network, latency, SQLite busy/WAL/RSS,
rozmiar repo i oczekiwanie graczy. Stop nowych zadań niezależny od odczytu
zachowanych dopuszczonych danych. Błąd pełności, nieznane koszty lub regresja
gry zatrzymują rozszerzenie. Pełny rollout wymaga tej obserwacji; testy lokalne
ani pojedynczy pilot nie są jej substytutem.

## Status domknięcia

2026-10-25: odbiór wdrożonego pakietu PASS. Faza 1: 365 testów i spójność
bazy PASS. Faza 2: operator przekazał baseline_matches, HTTP 200, pm2 save
oraz potwierdził skanowanie, hakowanie i łączenie w terytorium na nowym
i istniejącym koncie. Nie powtarzać tych testów bez nowej zmiany lub regresji.
Flagi pozostają w stanie bazowym; fazy 3–4 i kwalifikacje źródeł są otwarte.

Zamykamy osobno: kod/testy lokalne, odbiór serwera, kwalifikację źródeł i
aktywację produkcyjną. Ten pakiet nie ogłasza pełnego PASS 161–163. Otwartych
źródeł, geometrii i decyzji nie oznaczamy jako zakończone tylko dlatego, że
skrypt testowy zwrócił OK. Nie wymagamy od operatora nowych działań przed
przygotowaniem całego uzgodnionego bloku odbioru.
