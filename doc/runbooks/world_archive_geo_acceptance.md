# Odbiór archiwum i przygotowanie Geoapify — 161–163

Operator zaakceptował 25.10.2026 następny etap: retencja geometrii 7 dni oraz
jeden test kolektora Geoapify z rezerwacją 5 kredytów. Wcześniejsze nierozliczone
operacje pozostają zachowane. Nie oznacza to automatycznej aktywacji źródła,
rutingu ani ciągłego pobierania.

## Kod → wdrożenie → zbiorczy test

Na VPS:

```bash
cd ~/app/chaos &&
git pull --ff-only &&
bash tools/world_archive_geo_acceptance.sh
```

Nie wymaga restartu, kluczy API, migracji ani `pm2 save`. Zmiany tego pakietu
obejmują diagnostykę, testy i instrukcje; działający skaner pozostaje bez zmian.

Pakiet sprawdza na izolowanych bazach: publikację przez worker z retencją 7 dni,
ponowne otwarcie repozytorium, wygaśnięcie dostępności dla skanera po 30 minutach,
zachowanie archiwum do jego terminu oraz usunięcie bez osieroconych rekordów.
Upływ czasu jest symulowany w testach, nie zmieniamy zegara VPS ani terminów danych
produkcyjnych. Testy Geoapify i routingu używają atrap transportu.

Raport produkcyjny powstaje z tymczasowej, spójnej kopii SQLite, źródło otwierane
jest przez `mode=ro`. Nie zmienia ledgerów, snapshotów, uprawnień, kolejek, tras
ani PM2. Pokazuje:

- faktyczne brakujące uprawnienia MapLark/Geoapify i termin ich przeglądu;
- aktywne okna budżetu oraz zachowane nierozliczone operacje;
- blokadę przeniesienia nierozliczonych kosztów ze starego okresu;
- zapisane lub domyślne trasy, także celowo puste, i powody pominięcia źródeł;
- rzeczywiste rekordy dłuższej retencji.

`PASS` skryptu oznacza przejście testów i wykonanie raportu. Nie oznacza, że lista
`blockers` jest pusta ani że endpoint działa. `execution_authorized=false` jest
celowe: sam raport nigdy nie udziela zgody na zapytanie.

## Następny krok po raporcie

Na podstawie aktualnego rejestru przygotowujemy jeden ograniczony permit
Geoapify oraz budżet uwzględniający poprzednie rezerwacje. Nie zwiększamy starego
okna diagnostycznego, nie zerujemy 20 kredytów i nie wnioskujemy o koszcie
pojedynczego zapytania z sum w panelu dostawcy. Brak potwierdzonego kosztu nowego
zapytania zachowa pełną rezerwację 5 kredytów.

Geoapify zbiera obserwacje `commercial` / Point; nie zastępuje pełnego skanu
CHAOS, geometrii dróg ani dowodu pokrycia regionu. Po raporcie technicznym nadal
pozostają osobne etapy aktywacji routingu i ciągłego kolektora. Nie powtarzamy
udanego trzylayerowego pobrania MapLark tylko dla odtworzenia PASS.

Retencja 7 dni dotyczy nowej, jawnie dopuszczonej publikacji archiwalnej;
bieżący pakiet nie przedłuża już wygasłych snapshotów i nie zmienia świeżości
skanera (300/1800 s). Nie oznacza bezterminowego archiwum ani certyfikacji regionów.

## Zatwierdzony pojedynczy test — po odbiorze c8bdaf1

VPS potwierdził wszystkie 39 testów, MapLark revision 9 bez blokad retencji,
Geoapify revision 2 / disabled / small_probe oraz cztery stare niepewne
operacje o łącznej rezerwacji 20. Brak aktywnych okien Geoapify.

```bash
cd ~/app/chaos &&
git pull --ff-only &&
bash tools/world_geo_archive_execute.sh --execute
```

Skrypt uruchamia 40 testów izolowanych, sprawdza baseline, pyta bez echa o
klucz Geoapify, wykonuje najwyżej jedno zapytanie `commercial` dla Warszawy
(52.2319,21.0067), promień 300 m, limit 100. Nie ma paginacji ani automatycznego
ponawiania. Plan bez wykonania: ten sam skrypt z `--plan`.

Przed mutacjami zapisuje spójną kopię bazy do
`data/geo-archive-7d-20261025-v1/poi_cache.sqlite3`. Wynik i stan przerwanej
operacji są w `report.json` w tym samym katalogu. Nie zapisuje klucza ani
nagłówków uwierzytelniania. Nie usuwać katalogu ani pozycji ledgeru, aby
ponawiać zapytanie: identyfikator operacji i budżetu jest jednorazowy.

Okno carry-forward trwa godzinę. Zawiera stare nierozliczone operacje przez
odwołania do tych samych rekordów, plus 5 kredytów nowego limitu. Przy obecnym
stanie to limit 25, zajęte 20, dostępne 5. Nie powstaje budżet cykliczny.
Późniejsze rzeczywiste rozliczenie operacji aktualizuje także przeniesiony koszt.
Zwykłe utworzenie nowego okna nadal nie omija blokady starych kosztów.

Po poprawnej odpowiedzi i normalizacji skrypt zapisuje rzeczywisty wynik testu
technicznego i decyzję o 7-dniowym archiwum. Rejestr Geoapify otrzyma stan
enabled wyłącznie z zakresami small_probe/storage/world_storage. **Nie otrzyma
normal_scan ani background_refresh**: router i kolejka automatyczna nadal je
pominą. Zapis jest obserwacją UNKNOWN, bez dowodu kompletności obszaru.
To test pobrania i archiwizacji, nie odbiór ciągłego workera Geoapify.

Oczekiwany wynik: `archived_observations`, `local_readback_pass: true`,
network_calls 1, retencja 604800 s; bez kosztu raportowanego przez dostawcę nowa
operacja pozostaje uncertain z rezerwacją 5. Powtórzenie narzędzia zwraca
`already_attempted_inspect_saved_report` bez sieci. Błąd nie uprawnia do resetu
rezerwacji. Gra, PM2 i flagi środowiskowe pozostają bez zmian; tymczasowy
priorytet tła dotyczy wyłącznie procesu testowego.

## Kolejny pakiet — zachowanie MapLark i włączenie routingu

Po PASS Geoapify przygotowano `world_routing_archive_rollout.sh`. Nie wykonuje
zapytań do dostawców. Wykorzystuje trzy dokładne identyfikatory snapshotów
odebranych wcześniej w sektorze 2036/5153 (roads, waterways, inland_water).

```bash
cd ~/app/chaos &&
git pull --ff-only &&
bash tools/world_routing_archive_rollout.sh --execute
```

Pakiet: kontrola baseline OFF → 32 testy izolowane → weryfikacja trasy live
`[maplark]` → kontrola istniejących snapshotów → backup SQLite → retencja
tych trzech snapshotów → ponowna kontrola trasy → reload wyłącznie web
z profilem `routing` → kontrola flag → Launch HTTP 200.
Wariant `--check` kończy się przed backupem i mutacjami.

Retencja biegnie przez 7 dni **od pierwotnego pobrania**, nie od wykonania
polecenia. Można zachować nadal istniejącą obserwację, której przydatność dla
skanera już wygasła: fresh_until, usable_until, payload, digest, provenance,
ledger i dowody coverage pozostają nietknięte. Decyzja archiwalna trafia do
istniejącej tabeli world_retention. Ponowienie nie odnawia zegara. Wszystkie
trzy snapshoty muszą przejść walidację przed zapisem; brak jednego zatrzymuje
pakiet przed reloadem i nie powoduje pobrania zastępczego.

To uzupełnia wcześniejszą zasadę „nie przedłużamy wygasłych snapshotów”:
nie przywracamy świeżości wyniku ani usuniętych danych. Zachowujemy wyłącznie
jeszcze obecne, poprawne obserwacje mieszczące się w zatwierdzonym okresie
archiwalnym. Zmiana nie ustawia automatycznie retencji przyszłych permitów
kolektora i nie uruchamia pobierania w tle.

Konfiguracja jest zapisana w `ecosystem.web.config.js`:

- `--env routing`: routing 1;
- `--env baseline`: routing 0, wycofanie aktywacji;
- pozostałe flagi (world ingest/read OFF, passive discovery, age 0) bez zmian.

Zwykły reload bez `--env routing` wraca do bazowej konfiguracji OFF.
Po odbiorze routingu używać tego profilu przy kolejnych reloadach.
Runtime checker dla nowego stanu: `tools/world_runtime_check.py --routing 1`.

Po HTTP 200 wykonać jeden skan w grze i odczytać:

```bash
pm2 logs chaos --lines 80 --nostream 2>&1 | grep 'poi_route'
```

Oczekiwany wpis z dostawcą maplark i result success. Test może korzystać z
cache albo wykonać zwykłe płatne pobranie w ramach dotychczasowego budżetu.
Po poprawnym skanie: `pm2 save`. Nie deklarować działania Overpass tylko
dlatego, że router jest ON: aktualny rejestr dopuszcza wyłącznie MapLark.
Nie nadajemy nowych scopes, nie nadpisujemy zapisanych tras ani nie aktywujemy
Geoapify w skanerze.

Rollback routingu (zachowuje archiwum i ledger):

```bash
pm2 startOrReload ecosystem.web.config.js --only chaos --env baseline --update-env
.venv/bin/python tools/world_runtime_check.py --routing 0
```

Po potwierdzeniu działania wersji bazowej można wykonać `pm2 save`. Nie
przywracać całej starej bazy POI dla wycofania flagi — cofnęłoby to nowe koszty.
