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
