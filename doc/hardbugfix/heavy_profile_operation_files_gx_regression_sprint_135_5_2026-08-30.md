# Sprint 135.5 — heavy profile na ścieżce operacje, pliki i Ghost Exchange

Data: 2026-08-30  
Status: `RESOLVED — SERVER VALIDATED`

## Problem / objawy

Po naprawie transportu plików z operacji do File Managera i Ghost Exchange do
gorącej ścieżki ponownie dostał się pełny `profile_json`. Naprawa przywróciła
część przepływu danych, ale jednocześnie spowodowała poważną regresję wydajności:

- hakowanie zwolniło około pięciokrotnie;
- otwieranie mapy i pickera oraz przejścia związane z hackowaniem miały długie
  opóźnienia;
- Operation Control, anulowanie operacji, File Manager, Ghost Exchange i wallet
  reagowały wolniej;
- zatrzymanie workerów 14, 17 i 18 nie przywracało normalnego tempa, co
  wykluczyło je jako główną przyczynę;
- operacje były widoczne na mapie i w Operation Control, lecz od kilku dni ich
  pliki nie trafiały do File Managera ani do sprzedaży w GX.

Najmłodsze pliki znalezione podczas diagnozy pochodziły z 2026-08-26. GX miał
jeszcze historyczne sprzedaże, ale w dniu incydentu nie otrzymywał nowych danych,
mimo że kończące się operacje były widoczne w canonical runtime.

## Wpływ na grę i runtime

Incydent połączył dwie klasy awarii:

1. brak finalizacji artefaktów z operacji do File Managera i rynku;
2. regresję heavy-profile na wielu interaktywnych endpointach.

Profil nie był jedynie ciężkim payloadem odpowiedzi. Jego odczyt, kopiowanie,
hydracja tysięcy historycznych operacji i ponowny zapis znajdowały się na
ścieżkach współdzielonych przez kilka systemów gameplayu. Dlatego lokalna
poprawka przepływu plików pogorszyła również pozornie niezwiązane akcje.

## Evidence produkcyjne

Przed kompaktowaniem legacy mirror operacji zajmował między innymi:

- `main`: 884 wpisy, około 33 MB;
- `robot`: 770 wpisów, około 20 MB;
- `iasny`: 445 wpisów, około 6 MB;
- `admin`: 180 wpisów, około 5 MB;
- `neo1`: 356 wpisów, około 4 MB;
- `run`: 561 wpisów, około 4 MB.

Canonical `player_operations` zawierało pełniejsze dane niż mirror profilu:

- `main`: 1234 canonical, 1234 terminalne;
- `robot`: 1160 canonical, 1135 terminalnych i 25 aktywnych;
- `iasny`: 541 canonical;
- `admin`: 180 canonical;
- `neo1`: 557 canonical;
- `run`: 680 canonical.

Guard recovery potwierdził więc, że usunięcie legacy mirroru nie powoduje utraty
operacji. Po kompaktowaniu rozmiary profili spadły do około:

- `main`: 2.68 MB;
- `robot`: 1.71 MB;
- `run`: 1.61 MB;
- `neo1`: 1.09 MB;
- `iasny`: 0.94 MB;
- `admin`: 0.24 MB.

We wszystkich tych profilach liczba legacy operations wynosiła potem `0`.
Natychmiast po kompaktowaniu gracz potwierdził powrót normalnego tempa gry.

Operacja testowa `op_20260830200718_642218` zakończyła się statusem `timeout`,
ale przed poprawką nie miała `resource_buffer.files` ani żadnego pliku w File
Managerze. Po bounded finalization powstał dokładnie jeden rekord:

```text
folder:         network
file:           wifi_target_op_20260830200718_642218.net
size:           13 MB
market_status:  queued_for_market
sellable:       true
operation_id:   op_20260830200718_642218
```

`artifact_state` operacji zawierał `finalized_at`, `file_count=1` i identyfikator
pliku. Kontrola idempotencji dała `1 file / 1 distinct file_id`.

Następnie Ghost Exchange sprzedał paczkę sektora `Sieci` o rozmiarze 52 MB za
470 HC o 23:25 czasu polskiego. Potwierdziło to cały przepływ:

```text
operation -> canonical data file -> File Manager -> GX batch -> sale -> wallet
```

## Root cause

### 1. Historyczne operacje wróciły do pełnego profilu

`profile_json.operations` ponownie pełniło rolę runtime mirroru mimo istnienia
canonical tabeli `player_operations`. Każda hydracja profilu mogła więc wciągnąć
setki albo ponad tysiąc operacji, głównie terminalnych, wraz z ich rozbudowanymi
targetami, security state, risk meterami i artefaktami.

### 2. Finalizacja plików była zależna od profilu

Generatory plików operacyjnych oczekiwały projekcji zawierającej `operations`,
`files` i storage. Po odcięciu ciężkiej hydracji canonical tick poprawnie
kończył operację i wykonywał cleanup, ale nie miał niezależnej, bounded ścieżki
materializacji jej plików. W efekcie operacja mogła przejść do `timeout`, a plik
nie powstawał.

### 3. Poprzednia naprawa transportu zamaskowała granicę odpowiedzialności

Pełny profil dostarczał jednocześnie historyczne operacje, inventory, pliki i
stan rynku. Przywrócenie jednego brakującego efektu przez ponowną hydrację
profilu naprawiało symptom, ale przenosiło koszt na wszystkie endpointy
korzystające z tego samego profilu. Był to powrót znanej klasy regresji
heavy-profile, nie problem wydajności pojedynczego workera.

## Odrzucone hipotezy

- workery Ollamy, publishera i territory nie były główną przyczyną — po ich
  zatrzymaniu tempo nadal było złe;
- sam SQLite lock nie wyjaśniał stałego spowolnienia wielu ekranów;
- brak plików nie wynikał z braku operacji: canonical `player_operations`
  zawierało aktywne i terminalne rekordy;
- samo przyspieszenie anulowania operacji nie wystarczało, ponieważ ciężki profil
  pozostawał na innych wspólnych ścieżkach;
- nie wolno było usuwać legacy operations bez porównania ich z canonical store;
  recovery wykonało loss guard przed zmianą profilu.

## Finalne rozwiązanie

- `player_operations` pozostaje canonical źródłem operacji; zakończone operacje
  nie są ponownie zapisywane do `profile_json.operations`;
- kontrolowane narzędzie `compact_legacy_profile_operations.py` usuwa legacy
  mirror dopiero po potwierdzeniu, że canonical store zawiera co najmniej ten sam
  zbiór operacji;
- powstał canonical, indeksowany magazyn `player_data_files`, rozdzielający pliki
  gameplayowe od ciężkiego profilu;
- terminalny tick wywołuje `finalize_operation_files_bounded()` dla pojedynczej
  operacji, korzystając tylko z minimalnej projekcji storage i pustego inventory
  plików — bez odczytu `profile_json`;
- zapis pliku, aktualizacja storage i oznaczenie `artifact_state` operacji odbywa
  się w jednej transakcji;
- `file_id` jest kluczem idempotencji, więc retry finalizacji nie tworzy
  duplikatu ani nie nalicza ponownie storage;
- File Manager dostaje canonical pliki przez projekcję inventory;
- cykl GX synchronizuje zmiany lifecycle istniejących canonical plików po
  poprawnym zapisie rynku;
- worker raportuje liczbę automatycznie sfinalizowanych plików jako
  `operation_files_finalized`.

## Testy i weryfikacja

- `py_compile database.py run.py scripts/territory_conflict_worker.py` — PASS;
- celowany test `test_terminal_tick_finalizes_file_without_profile_io` — PASS;
- test wymusza błąd przy próbie `user_store.get_profile`, dzięki czemu dowodzi,
  że finalizacja terminalnego ticka nie czyta pełnego profilu;
- fizyczna finalizacja historycznej operacji Wi-Fi — PASS;
- canonical file record i `artifact_state` — PASS;
- idempotencja `1 / 1` — PASS;
- widoczność File Manager i utworzenie paczki GX — PASS;
- sprzedaż paczki oraz wypłata 470 HC — PASS;
- subiektywna i praktyczna prędkość gameplayu po kompaktowaniu — potwierdzona
  przez gracza.

## Guardrail na przyszłość

Ta ścieżka wymaga szczególnej ostrożności przy każdej kolejnej zmianie:

```text
hackowanie -> operacje -> incydenty/pliki -> File Manager -> Ghost Exchange -> wallet
```

1. Nie wolno naprawiać braku pliku przez ponowne dołączanie całego
   `profile_json.operations` do odczytu lub zapisu endpointu.
2. Operacje terminalne nie mogą wrócić jako stale synchronizowany mirror pełnego
   profilu. Ich canonical źródłem jest `player_operations`.
3. Finalizer ma otrzymywać jedną operację oraz bounded inventory/storage, nigdy
   pełny profil gracza.
4. File Manager i GX powinny korzystać z canonical plików; profil może być
   projekcją kompatybilności/prezentacji, ale nie transportem archiwum operacji.
5. Każdy fix na tej ścieżce musi mierzyć nie tylko poprawność pliku i sprzedaży,
   lecz także czas hackowania, mapy, pickera, Operation Control, File Managera i
   walletu na ciężkim koncie.
6. Test regresyjny powinien failować, jeśli bounded terminal tick spróbuje
   wywołać `user_store.get_profile`.
7. Przed czyszczeniem legacy mirroru zawsze obowiązuje canonical loss guard.
8. Jeżeli pozornie niezwiązane ekrany zwalniają równocześnie, pierwszym audytem
   powinien być rozmiar i liczba hydratowanych pól `profile_json`, a dopiero potem
   workery oraz obciążenie CPU.

## Powiązane pliki i sprinty

- `database.py` — `player_data_files` i canonical inventory API;
- `run.py` — bounded finalization i synchronizacja lifecycle GX;
- `scripts/territory_conflict_worker.py` — automatyczny tick i telemetryka;
- `scripts/compact_legacy_profile_operations.py` — kontrolowana kompaktacja;
- `tests/test_operation_risk_meter.py` — regresja bez odczytu profilu;
- `doc/sprints/sprint_130_10_1_hot_path_recovery.md`;
- `doc/hardbugfix/post_130_10_130_12_runtime_regressions_sprint_130_12_2026-08-26.md`;
- Sprint 135.5 / przejście do 135.6.

## Status końcowy

`RESOLVED — SERVER VALIDATED`

Przepływ plików i sprzedaż GX zostały potwierdzone na serwerze, a normalna
prędkość gry wróciła. Najważniejszą lekcją nie jest sama naprawa finalizera:
ciężki profil ponownie wszedł na gorącą ścieżkę podczas naprawy transportu i
namieszał w kilku systemach naraz. Każda przyszła zmiana tego łańcucha musi
utrzymać canonical/bounded granicę i nie może przywracać pełnej hydracji jako
skrótu implementacyjnego.
