# Sprint 139 — GhostSignal: natychmiastowy show i kontrolowany restart

Status: `COMPLETE / SERVER E2E PASS / 139.1–139.4 CLOSED`

Źródło produktowe: `doc/sprints/sprint_139_opis_15-minutowe_show.md`

## 1. Cel sprintu

Usunąć lukę pomiędzy faktycznym rozpoczęciem finału GhostSignal a przejęciem
interfejsu przez Signal Show oraz domknąć przejście do nowego GhostSystemu bez
ręcznego odświeżenia lub restartu operatora.

Po sprincie pierwszy trwały krok transmisji ma natychmiast:

1. utworzyć durable instancję show;
2. zablokować gameplay wszystkim zalogowanym graczom;
3. dostarczyć stan do aktywnych, wznawianych i nowych sesji;
4. utrzymać blokadę aż do poprawnego settlementu i rolloveru;
5. wykonać jeden kontrolowany reboot klienta do nowej generacji systemu;
6. uruchomić pulpit nowego cyklu z dostępną aplikacją Signal Registry.

Sprint 139 nie przebudowuje jeszcze oprawy piętnastu minut. Dostarcza pewny
kontrakt czasu i przejścia stanów, na którym oprze się Sprint 140.

## 2. Potwierdzona regresja i przyczyna

Production E2E `138.2` pokazał, że mechanika backendowa zakończyła cykl
poprawnie, ale:

- konsumpcja terytoriów i pozostałe skutki transmisji ruszyły przed show;
- aktywna sesja zobaczyła pełnoekranowy ekran dopiero po około 2–3 minutach;
- do tego czasu mapa, narzędzie i pulpit pozostawały używalne;
- po zakończeniu show nie nastąpił kontrolowany restart klienta;
- Signal Registry pojawiło się dopiero po ręcznym restarcie/ponownym bootowaniu.

Aktualna kolejność w `GhostTransmissionService` tworzy sygnał, wykonuje ciężkie
skutki transmisji, przygotowuje wersję, a dopiero przy
`begin_stabilization()` tworzy show. Serwerowa blokada zapisów obejmuje tylko
status `stabilizing`. Frontend reaguje wyłącznie na istniejące `show_active`, a
po jego zakończeniu pokazuje toast — nie wykonuje rebootu.

To jest błąd kontraktu, nie wydajności assetu show.

## 3. Decyzje architektoniczne

### 3.1. Punkt zero

Punktem `T0` show jest skuteczne przejście kompletnego, odblokowanego cyklu do
transmisji i utrwalenie immutable locka. Show musi być zapisane i możliwe do
odczytu **przed pierwszym skutkiem nieodwracalnym**, w szczególności przed:

- konsumpcją terytoriów;
- naliczeniem nagród;
- konsumpcją części i połączeń;
- wyłączeniem SP;
- zmianą wersji GhostSystemu.

Nie czekamy na zakończenie tych operacji ani na późny stan `stabilizing`.
Jeżeli obecny model show wymaga `signal_id`, dopuszczalne są dwa rozwiązania:

- utworzenie canonical signal/show zaraz po locku, a następnie wykonywanie
  skutków transmisji;
- instancja show zakotwiczona w `cycle_id + lock_snapshot_id`, później
  atomowo dopięta do `signal_id`.

Wybrana implementacja musi zachować dokładnie jeden show na cykl i pełną
idempotencję recovery. Nie wolno emitować fałszywego `signal_sent` tylko po to,
aby wcześniej otworzyć ekran.

### 3.2. Jawne kamienie milowe

Timeline rozróżnia co najmniej:

```text
cycle_locked / transmission_started
  -> show_started + gameplay_locked
  -> territories/rewards/parts/version effects
  -> signal_sent
  -> stabilizing
  -> ranking/archive/settlement ready
  -> next_cycle_active
  -> client_restart_required
  -> client_restart_acknowledged
```

`transmission_started`, `signal_sent` i `restart_required` nie mogą być jednym
nieprecyzyjnym stanem. Każdy event ma canonical dedupe key, `cycle_id`,
`signal_id` gdy już istnieje, `state_version` i czas serwera.

### 3.3. Globalna blokada gameplayu

Overlay nie jest zabezpieczeniem. Źródłem prawdy pozostaje backend.

Blokada obejmuje wszystkie mutujące endpointy od `T0` przez `transmitting` i
`stabilizing`, dopóki successor cycle nie jest aktywny. Dozwolone pozostają
tylko:

- odczyty potrzebne do show, delty, czasu serwera i recovery;
- kontrolowane wylogowanie;
- endpoint potwierdzenia rebootu;
- techniczne health checks nieuwierzytelnione jako gracz.

Odpowiedź `423` zwraca stabilny kod, stan show, `cycle_id`, deadline oraz
instrukcję odświeżenia projekcji. Guard musi opierać się na durable stanie
cyklu/locka/show, nie wyłącznie na klasie CSS albo pamięci procesu.

### 3.4. Natychmiastowa propagacja i recovery

Po commitcie `show_started` wszystkie aktywne klienty otrzymują deltę. Polling
endpointu show pozostaje ścieżką samonaprawy.

Klient otwarty, klient mobilny uśpiony, drugi tab, reload oraz logowanie w trakcie
finału muszą dojść do tej samej fazy na podstawie czasu serwera. Nie odtwarzamy
od początku już minionych scen i nie wydłużamy show wskutek reconnectu.

API musi umieć odtworzyć brakującą projekcję show także dla przerwanego stanu
`transmitting`, a nie dopiero dla `stabilizing`.

### 3.5. Kontrolowany reboot GhostSystemu

„Restart systemu” oznacza kontrolowany reboot warstwy klienckiej po trwałym
domknięciu backendu. Nie oznacza restartu PM2, serwera ani brutalnego logoutu.

Warunki wejścia:

- poprzedni cykl jest `closed`;
- dokładnie jeden następny cykl jest `active`;
- ranking, archiwum i wymagany settlement są trwałe;
- show osiągnęło fazę końcową;
- wersja docelowa została zatwierdzona.

Backend publikuje durable `client_restart_required`/restart epoch związany z
zamkniętym sygnałem i nowym cyklem. Klient:

1. zamyka narzędzia, mapę i aplikacje;
2. pokazuje końcową sekwencję shutdown/boot;
3. wykonuje pojedynczy canonical reload pulpitu z aktualną generacją sesji;
4. po poprawnym boot snapshotcie zapisuje acknowledgement.

Istniejący system session generation ma chronić przed starymi requestami.
Reboot nie może tworzyć pętli reloadów, wymagać ponownego logowania bez powodu
ani pozostawiać drugiej karty w starej generacji. Receipt jest trwały co najmniej
per `user + signal + session lineage`; localStorage może być tylko optymalizacją,
nie źródłem prawdy.

Signal Registry ma być wyliczone z backendowego readiness/archive i widoczne na
pierwszym pulpicie po rebootcie. Nie może zależeć od wcześniejszego otwarcia
GhostNetwork Suite ani ręcznego odświeżenia.

## 4. Zakres wykonawczy

### 139.1 — durable timeline i kolejność commitów

- dodać jawny milestone startu transmisji/show;
- przenieść `ensure_for_signal` lub jego następcę przed skutki nieodwracalne;
- zachować atomic lock oraz idempotentne wznowienie `transmitting`;
- utrwalać `started_at`, `ends_at`, wersję policy i lineage lock/signal;
- rozszerzyć audyt o chronologię side effects.

### 139.2 — globalny lock i natychmiastowy frontend

- objąć guardem właściwe stany `transmitting` i `stabilizing`;
- dostarczyć delta `show_started` natychmiast po commitcie;
- rozszerzyć `/api/ghostnetwork/show` o transmitting recovery;
- podłączyć desktop, mapę, mobile i drugi tab;
- dodać fail-safe ekran przy chwilowym błędzie renderera, bez odblokowania gry.

### 139.3 — restart, nowy boot i Signal Registry

- dodać durable restart epoch/receipt;
- uruchomić shutdown dopiero po poprawnym rolloverze;
- zintegrować reboot z session generation i boot snapshotem;
- zagwarantować gotowość Signal Registry na pierwszym pulpicie;
- zabezpieczyć exactly-once, multi-tab i recovery po zerwanym połączeniu.

### 139.4 — testy i production gate

- test jednostkowy kolejności: show istnieje przed pierwszą konsumpcją;
- test przerwania po każdym kroku i idempotentnego resume;
- test HTTP `423` dla wszystkich mutacji w chronionym oknie;
- test delty, poll recovery, reloadu i drugiego urządzenia;
- test restart epoch/ack, braku pętli i obecności Signal Registry;
- test desktop + mobile oraz bounded production E2E z monitorem JSONL.

## 5. Monitoring i kryteria PASS

Monitor jednego finału zapisuje co najmniej:

```text
locked_at
show_created_at
show_first_delivered_at (per obserwowana sesja)
first_irreversible_effect_at
signal_sent_at
stabilizing_at
ranking/archive_ready_at
cycle_closed_at
next_cycle_active_at
restart_requested_at
restart_acknowledged_at
```

Wymagania:

- `show_created_at <= first_irreversible_effect_at`;
- aktywna sesja dostaje ekran bez wielominutowej luki; cel P95 do 2 sekund od
  dostarczenia delty, polling recovery do jednego interwału;
- zero zaakceptowanych mutacji gameplayowych w chronionym oknie;
- dokładnie jeden lock, signal, show, ranking, następny cykl i restart receipt;
- po rebootcie mapa/narzędzia sprzed finału nie są nadal otwarte;
- Signal Registry jest dostępne bez ręcznego restartu;
- brak pętli reload, 500, utraty sesji i rozjazdu mobile/desktop.

## 6. Definition of Done

Sprint 139 otrzymuje `PASS`, gdy production E2E potwierdzi pełny przebieg:

```text
rozwiązanie ostatniej blokady
  -> natychmiastowy durable show i lock UI
  -> skutki GhostSignal pod osłoną show
  -> 15 minut server-clock timeline
  -> poprawny settlement i next cycle
  -> jeden kontrolowany reboot
  -> nowy pulpit + Signal Registry
```

Bez tego Sprint 140 może przygotowywać assety i prototypy, ale nie może zamknąć
montażu produkcyjnego.

## 7. Poza zakresem

- pełna grafika poszczególnych scen;
- nowe utwory radiowe i nowe assety artystyczne;
- zmiana reguł nagród, konsumpcji terytoriów lub rankingu;
- generowanie przez Ollamę treści na żywo podczas show;
- restart procesów PM2 jako element gameplayu.

## 8. Realizacja 139.1 — 2026-09-10

### Kontrola wejściowa i decyzja

- Stan wejściowy: czysty `main`, `HEAD=dc1255d`, zgodny z lokalnym
  `origin/main`. Dokumenty handoffu są już wersjonowane.
- Baseline: 47 testów Pythona, kontrakt JS show i `node --check` PASS.
- Niezależne połączenie SQLite przed pierwszą konsumpcją widziało zero
  sygnałów i show. `start_transmission()` obejmował całość zewnętrzną
  transakcją, więc samo przesunięcie `ensure_for_signal()` nie usuwało błędu.
- Dwa nowe testy przed implementacją odtworzyły brak widocznego show oraz
  ponowne wykonywanie skutków przy retry zakończonej transmisji.

Zmiana rozwija istniejące `GhostTransmissionService`, `GhostSignalShowService`,
repository, ledgery i audytor. Nie dodaje równoległego runtime, kolejki,
magazynu endgame ani źródła prawdy. Nie zmienia schematu SQLite.

### Kontrakt trwałości

```text
immutable lock / transmitting
  -> walidacja i przygotowanie payloadu poza writer-lockiem
  -> recheck cyklu/locka + istniejący signal(status=transmitting, sent_at='')
     + istniejący show + transmission_started + signal_show_started
  -> COMMIT widoczny z drugiego połączenia
  -> terytoria / nagrody / części / historia / połączenia / SP / wersja
     (osobne transakcje etapów, istniejące ledgery i dedupe)
  -> signal(status=sent, sent_at=czas zakończenia skutków)
     + signal_sent + stabilizing
  -> COMMIT
```

- T0 nowych transmisji pochodzi z `locked_at`; deadline i policy utrwala
  istniejący rekord show. Resume, późniejsza zmiana konfiguracji i przekroczenie
  deadline'u nie rozpoczynają show od nowa.
- Start i resume używają jednej ścieżki. Otaczająca je cudza transakcja jest
  odrzucana, ponieważ uniemożliwiałaby wymagany wcześniejszy commit.
- Zmiana cyklu między przygotowaniem a zapisem daje jawne
  `transmission_state_changed`; kolejny runtime tick może ponowić próbę.
- Każdy etap ponownie sprawdza stan cyklu pod writer-lockiem. Zakończony cykl
  zwraca istniejące receipts bez powtarzania skutków i bez cofania rolloveru.
- Nowe `sent_at` oznacza zakończenie skutków, a `transmitted_at` jest ustawiane
  przy wejściu w stabilizację. Historia części używa ich trwałego `consumed_at`.
- Dla przerwanego legacy signal zachowane są wcześniejsze `sent_at` i zegar
  istniejącego show. Recovery nie przepisuje historii, żeby zaliczyć 139.
- Publisher narracji odrzuca `transmitting` jako `signal_not_sent`; model
  pozostaje poza ścieżką krytyczną.
- Wstępne przygotowanie i serializacja payloadu nowego sygnału odbywają się
  przed writer-lockiem. Istniejące transakcje konsumpcji terytoriów i operacje
  na 20 częściach zachowują swoje domenowe reguły; 139.1 nie wprowadza
  zewnętrznych requestów ani odczytów profili w tych transakcjach.

### Testy i audyt

Końcowa walidacja lokalna: 86 testów PASS (216,351 s): transmisja, show,
HTTP show, integralność endgame, runtime/recovery/rollover, audyty, archiwum,
ranking, narracja, closure i session generation. Po ostatnim zachowaniu
kompatybilności domyślnego `sent_at` repository: 11 testów PASS (10,111 s),
w tym ponowione testy widoczności show i legacy recovery. Zestawy częściowo
się pokrywają. `py_compile` sześciu zmienionych plików Pythona, kontrakt JS show,
`node --check` i `git diff --check`: PASS. Dane testowe oraz bytecode powstawały
w katalogach tymczasowych, poza lokalną bazą gry. To lokalny PASS 139.1,
nie server PASS ani zamknięcie Sprintu 139.

Nowe testy obejmują drugi odczyt SQLite przed skutkami, rollback zapisu show,
awarie etapów wraz z częściowo wykonaną finalizacją, świeży proces serwisu,
resume po deadline, wyścig dwóch przygotowanych workerów, recheck cyklu,
niepoprawny lock przy istniejącym sygnale i recovery legacy. Sprawdzają też
blokadę przedwczesnej narracji oraz rzeczywisty raport chronologii.

Mały profil i syntetyczny profil 35 MB przechodzą tę samą transmisję oraz
projekcję show: identyczna liczba zapytań (limit testu <2500 dla całego flow),
`profile_full_read=0`, `profile_full_write=0`, `profile_bytes=0`,
`all_user_profile_scan=0`, `per_recipient_profile_read=0`. Test blokuje
ciężkie metody UserStore i SQL zawierający `profile_json` w badanej ścieżce.

Istniejący `scripts/audit_ghostnetwork_endgame.py` raportuje
`transmission_chronology`. Porównuje rzeczywisty `show.created_at` z czasami
receipts oraz kolejność wersji eventów. To kontrola danych; granicę commitu
udowadnia test z drugim połączeniem. Cykl legacy bez milestone'u nie dostaje
automatycznie certyfikacji 139 (`status=legacy`, `ok=null`). Flaga
`--require-transmission-timeline` wymusza nowy kontrakt także dla takiego cyklu.

### Pierwsza bramka serwerowa — przed 139.2

Uruchomić po udostępnieniu zweryfikowanego kodu 139.1 na serwerze, najlepiej
w osobnym checkoucie nieużywanym przez PM2. Commit/push pozostają decyzją
operatora. Ta bramka nie uruchamia produkcyjnego finału ani nie wymaga restartu
PM2, migracji produkcyjnej bazy lub zmiany konfiguracji workera.

Z katalogu tego kodu (interpreter zgodny z runtime aplikacji):

```bash
git status --short --branch
git rev-parse HEAD
.venv/bin/python --version
.venv/bin/python -B - <<'PY'
import os
import sys
import tempfile
import unittest

root = os.getcwd()
sys.path[:0] = [root, os.path.join(root, "tests")]
with tempfile.TemporaryDirectory(prefix="chaos139-server-") as scratch:
    try:
        os.chdir(scratch)
        os.environ["CHAOS_SESSION_FILE_DIR"] = os.path.join(scratch, "sessions")
        names = [
            "test_ghostnetwork_transmission",
            "test_ghostnetwork_signal_show",
            "test_ghostnetwork_endgame_integrity",
            "test_ghostnetwork_runtime_endgame",
            "test_ghostnetwork_endgame_audits",
        ]
        result = unittest.TextTestRunner(verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromNames(names)
        )
    finally:
        os.chdir(root)
sys.exit(0 if result.wasSuccessful() else 1)
PY
```

Zachować HEAD, wersję Pythona, wynik i czas testów. Testy zakładają własne bazy
w katalogach tymczasowych; import `run.py` również odbywa się poza katalogiem
danych gry. Wymagany wynik to zero błędów, w tym test niezależnego czytelnika
i dwóch workerów. Błąd przerywa bramkę i wymaga diagnozy przed 139.2.

Pierwsza próba serwerowa na `1d73a8d`: systemowy Python 3.10.12 zakończył
39 pozycji wynikiem `FAILED (errors=2)` (119,237 s). Przyczyną obu błędów
był brak `folium` podczas importu `run.py`: nie wykonano testu profilu 35 MB
ani modułu runtime endgame. Pozostałe 37 pozycji przeszło. To nie jest PASS
bramki serwerowej. Poprawiono powyższe polecenie na `.venv/bin/python`, zgodnie
z konfiguracją web/territory-worker; należy ponowić cały zestaw w środowisku
aplikacji, bez instalowania zależności w systemowym Pythonie.

Przed wdrożeniem produkcyjnym nadal domknąć read-only summary z handoffu:
HEAD serwera, filtr Ollamy, ready/retry_wait, bieżący cykl i strict audyty.
Przekazany `pm2 status` potwierdził wszystkie cztery procesy CHAOS online,
ale nie zastępuje tych kontroli.

139.2 (HTTP lock/delta/recovery), 139.3 (reboot/ack/boot) i 139.4
(production E2E) pozostają otwarte. Samo 139.1 nie jest jeszcze gotową
mechaniczną bramką do produkcyjnego finału.

### Wynik ponowienia bramki serwerowej

Operator ponowił ten sam zestaw przez `.venv/bin/python` (Python 3.10.12):
**53 testy, 346,637 s, OK**. Wykonały się wszystkie pięć rodzin, w tym
test małego/35 MB profilu oraz cały runtime endgame, których poprzednia próba
nie uruchomiła. Potwierdzono widoczność show przed konsumpcją, dwa workery,
rollback/recovery, conflict gate, idempotencję nagród oraz rollover.

Status: `139.1 ISOLATED SERVER PASS`. Jest to bramka kodu na tymczasowych
bazach w środowisku serwera, nie production E2E ani potwierdzenie działania
nowej wersji w procesach PM2. Nie wymaga ponawiania triggera GhostSignal.

### Wejściowy audyt 139.2

- Istniejący guard HTTP sprawdza tylko mutujące metody i `stabilizing`,
  a wyjątek odczytu przepuszcza request. Należy również objąć ochroną zapis
  requestu rozpoczętego przed T0; istniejący request transaction precommit
  jest punktem integracji, bez równoległego systemu blokad.
- `get_signal_show_for_viewer()` odtwarza brakujący rekord tylko w
  `stabilizing`. Recovery trzeba rozszerzyć na `transmitting` z zachowaniem
  walidacji locka, zegara i lekkiej ścieżki.
- `ghost.signal_show_started` jest już typem publicznego routingu delt,
  ale odbiór durable delivery queue odbywa się w tym samym workerze co
  endgame. Samo wcześniejsze enqueue nie dowodzi natychmiastowej dostawy
  podczas długiej transmisji. Rozwiązanie ma rozwinąć istniejący delta feed,
  bez drugiego busa i bez skanu wszystkich profili.
- Kontroler show odświeża się na boot/deltę oraz przy deadline; nie ma
  okresowego odczytu naprawczego przed pojawieniem się show. Pomija też
  osadzone dokumenty. Weryfikacji wymagają samodzielna mapa, karta w tle,
  ponowne połączenie i awaria renderera.
- Przeczytano wskazane kontrakty mapy, marker/menu identity i zabezpieczeń
  Leaflet. Blokada/show nie może przebudowywać markerów ani usuwać tych ochron.

### 139.2 — implementacja i kontrakt

139.1 zamknięty decyzją operatora po 53 testach izolowanych na serwerze.
139.2 rozwija istniejące repository/show, request precommit, delta feed
i kontroler JS. Nie powstał drugi bus, ledger, worker ani system blokad.

- Guard obejmuje `transmitting`, `stabilizing`, aktywne show i zamknięty
  cykl z show bez uruchomionego następcy. Upływ deadline nie zwalnia blokady.
  Jawna lista wyjątków obejmuje shell `/desktop`, zasoby statyczne,
  show, delty, session recovery i logout. Pozostałe GET/HEAD także są
  blokowane, bo starsze endpointy mogą mieć skutki uboczne; `/map` przekierowuje
  do chronionego shella. Błąd odczytu daje kontrolowane `503`.
- Request transaction precommit zachowuje guard generacji sesji i sprawdza
  zatwierdzony lock przed zapisem. Odczyt przez niezależne połączenie podczas
  trzymania writer locka wspólnej SQLite pozwala zatwierdzić transakcję
  tworzącą T0, a odrzuca późniejszego writera. Rollback zachowuje odpowiedź
  `423` także przy przechwyceniu wyjątku przez starszy handler. Atomowa
  serializacja dotyczy wspólnej bazy produkcyjnej; pomocnicza, odrębna baza
  sprawdza canonical lock, lecz nie tworzymy transakcji rozproszonej.
- `/api/ghostnetwork/show` używa istniejącego lekkiego serwisu show, bez
  konstrukcji pełnej fasady i bez migracji schematu w requestach. Recovery
  `transmitting` wykonuje tylko przygotowanie trwałego signal/show/eventów
  z walidowanego locka. Nie wykonuje konsumpcji, nagród ani publikacji.
- `/api/state/changes` dostarcza utrwalony `ghost.signal_show_started`
  wyłącznie pytającemu graczowi, z tym samym dedupe key co dotychczasowy
  publisher. Nie czeka na worker, nie skanuje kont ani pełnych profili.
  „Natychmiast” oznacza dostępność po commitcie przy kolejnym odczycie
  istniejącego feedu; nie jest to nowy transport push.
- Kontroler desktop/map/iframe odświeża stan na boot, deltę, wznowienie,
  powrót połączenia i co 5 sekund. Single-flight i timeout 8 sekund ograniczają
  zalegające requesty. Starsza generacja cyklu, wersja i czas odpowiedzi nie
  cofają stanu. Zegar pozostaje serwerowy, błąd sieci/renderera nie odblokowuje
  gameplayu. Awaria renderera daje prosty pełnoekranowy widok; localStorage
  pozostaje wyłącznie opcjonalną obsługą dotychczasowego toastu.
- Nie zmieniano handlerów Leaflet ani ścieżki marker/menu identity.
  Reboot/epoch/receipt i Signal Registry pozostają zakresem 139.3.

### Druga bramka serwerowa — 139.2

Wynik lokalny: **137 testów Python, 126,422 s, OK**; cztery zestawy JS
(show, recovery/iframe, delta client, session generation) PASS. Mały profil
i profil 35 MB: zero heavy-profile read/write/bytes/scan oraz identyczna,
ograniczona liczba zapytań, również dla viewer recovery, locka i dostawy
startu do feedu. `py_compile`, `node --check` i `git diff --check` PASS.

Po udostępnieniu tego zestawu zmian i pullu operator sprawdza HEAD oraz
uruchamia poniższy zestaw z katalogu repozytorium. Bramka używa tymczasowych
baz, nie wymaga restartu PM2 ani uruchomienia produkcyjnego GhostSignal.
Zastane pliki użytkownika pozostają poza zakresem.

```bash
git status --short --branch
git rev-parse --short HEAD
.venv/bin/python --version
.venv/bin/python -B - <<'PY'
import os
import shutil
import sys
import tempfile
import unittest

root = os.getcwd()
sys.path[:0] = [root, os.path.join(root, "tests")]
with tempfile.TemporaryDirectory(prefix="chaos139-2-") as tmp:
    try:
        # Istniejący test sesji czyta te dwa assety względem cwd.
        os.makedirs(os.path.join(tmp, "static", "js"))
        for name in ("session_generation.js", "terminal.js"):
            shutil.copyfile(os.path.join(root, "static", "js", name),
                            os.path.join(tmp, "static", "js", name))
        os.chdir(tmp)  # przed importem run/database: żadnej lokalnej bazy gry
        os.environ["CHAOS_SESSION_FILE_DIR"] = os.path.join(tmp, "sessions")
        names = [
            "test_ghostnetwork_transmission", "test_ghostnetwork_signal_show",
            "test_ghostnetwork_signal_show_http", "test_ghostnetwork_runtime_endgame",
            "test_ghostnetwork_endgame_integrity", "test_ghostnetwork_endgame_audits",
            "test_ghostnetwork_suite_snapshot", "test_session_generation_precommit",
            "test_session_generation_isolation", "test_ghostnetwork_delta_publisher",
            "test_ghostnetwork_delta_audience_bridge",
        ]
        result = unittest.TextTestRunner(verbosity=1).run(
            unittest.defaultTestLoader.loadTestsFromNames(names))
    finally:
        os.chdir(root)
sys.exit(not result.wasSuccessful())
PY
node tests/ghost_signal_show_frontend.test.js
node tests/ghost_signal_show_recovery.test.js
node tests/js/test_ghostnetwork_delta_client.js
node --check static/js/ghost_signal_show.js
```

Regresję przeglądarkowego modułu sesji
`node tests/js/test_session_generation_isolation.js` uruchamiamy osobno
w środowisku testowym zgodnym z jego składnią i API przeglądarkowymi
(potwierdzone lokalnie: Node 24.8.0). Ten istniejący test wymaga m.in.
optional chaining oraz `Headers`; nie jest zgodny z serwerowym Node 12.22.9.
Nie zmieniamy runtime PM2 ani kodu modułu sesji tylko na potrzeby tej bramki.

Każde polecenie musi zakończyć się kodem 0. Błąd wymaga diagnozy; nie
uruchamiamy kolejnego finału ani naprawczego SQL. Wynik tej bramki nadal
nie jest production E2E 139.4. Kontrola wizualna desktop/mobile, dwóch kart,
reloadu i powrotu połączenia pozostaje otwarta: lokalna sesja Browser
zwróciła `No browser is available` i pustą listę przeglądarek.

### Wynik serwerowy 139.2 — 3ac2c3b

- Python: **137 testów, 380,252 s, OK**.
- JS: show, recovery/iframe i delta client PASS na Node 12.22.9.
- Stary test session generation zatrzymał się na `?.` przed wykonaniem
  asercji. To błąd doboru polecenia do środowiska w pierwotnej instrukcji,
  nie wynik FAIL asercji sesji. Ponowienie lokalnie na Node 24.8.0: PASS.
- Po zatrzymaniu łańcucha `&&` operator wykonał osobno
  `node --check static/js/ghost_signal_show.js`; `echo $?` zwróciło **0**.
- Izolowana bramka serwerowa 139.2 zaliczona. Kontrola wizualna desktop/mobile
  pozostaje otwarta; wynik nie potwierdza przeładowania PM2 ani production E2E.
  Nie ma potrzeby ponawiać 137 zaliczonych testów Python.

### Kontrola po przeładowaniu aplikacji

Operator wykonał pull do `c70d3e5` i `pm2 reload 13`. Przekazany log
potwierdził status online oraz uruchomienie czterech nowych workerów Gunicorna.
Następnie operator potwierdził brak nieprawidłowości podczas opisanej kontroli
zwykłego pulpitu na komputerze i telefonie: odświeżenie, mapa/aplikacja,
układ mobilny, powrót z tła i odzyskanie połączenia.

Zwykły desktop/mobile smoke: **PASS według operatora**. Nie uruchamiano
GhostSignal na potrzeby tej kontroli. Wygląd aktywnego show, blokada
interakcji pod overlayem oraz odtworzenie trwającego show po reloadzie
pozostają do sprawdzenia wizualnie w przygotowanym scenariuszu. Nie zaliczamy
tych punktów na podstawie poprawnego działania zwykłego pulpitu.

### Podgląd show — korekta pasków przewijania

Operator pokazał lokalny podgląd konsolowy: overlay zasłania cały ekran,
lecz pojawiają się oba paski przewijania. Styl inline `overflow:auto`
nadpisywał istniejące CSS `overflow:hidden`; dekoracyjna siatka z ujemnym
insetem i perspektywą rozszerzała obszar przewijania. Przywrócono przycinanie
na kontenerze i zmieniono wersję assetu JS w czterech template'ach.
Istniejące testy show/recovery oraz node --check PASS. Operator potwierdził
w podglądzie konsolowym, że po ustawieniu overflow:hidden oba paski zniknęły,
a overlay pozostał pełnoekranowy. Korekta w repozytorium pozostaje lokalna.
Podgląd konsolowy nie potwierdza blokady
backendowej ani recovery rzeczywistego show po reloadzie.

### 139.3 — wejście 2026-09-11

Operator zamknął 139.2 i zlecił rozpoczęcie 139.3. Zachowano lokalną
poprawkę scrolla oraz dokumentację; HEAD wejściowy `c70d3e5`, branch main.
Zamknięcie etapu nie certyfikuje niewykonanego production E2E: recovery
aktywnego show i pełne przejście pozostają dowodem wymaganym w 139.4.

Audyt: rollover zamyka cykl, tworzy następcę i kończy show atomowo;
session generation ma istniejące guardy wejścia, precommit i odpowiedzi.
Frontend po show pokazuje wyłącznie toast. Pierwszy boot korzysta z
`/api/profile`, które nadal wywołuje ciężkie `sync_session_profile()`.
139.3 nie może użyć tego odczytu jako ścieżki nowego bootu. Wymaga lekkiej
projekcji desktopu z istniejących stores i zachowania zapisanych ustawień.

### 139.3 — kontrakt implementacji

- `rollover_stabilized_cycle()` po walidacji settlementu zapisuje
  `ghost.client_restart_required` w tej samej transakcji co aktywacja następcy
  i zakończenie show. Epoka jest deterministyczna dla show i następnego cyklu;
  dedupe eventu gwarantuje jeden zapis. Awaria publikacji cofa również
  aktywację następcy i zakończenie show. Nie dorabiamy eventu historycznym,
  już zamkniętym cyklom w idempotentnej gałęzi recovery.
- Kontekst istniejącej session generation w dokumencie zawiera `ghost_epoch`.
  Ten sam bridge fetch przekazuje `X-Chaos-Ghost-Epoch`; iframe i beacon
  przekazują `_ghost_epoch`. Guard wejścia, istniejący request precommit
  i kontrola odpowiedzi odrzucają stary dokument po rolloverze. Login
  zachowuje swój redirect, a nawigacja mapy kieruje do canonical desktopu.
  Generacja logowania nie jest rotowana bez powodu; epoka świata rozszerza
  ochronę istniejącej sesji. ACK jednej karty nie autoryzuje starych kart.
- Dotychczasowy kontroler show wykrywa nową epokę dopiero po zwolnieniu
  globalnego show. Wywołuje istniejący teardown okien/timerów, pokazuje
  końcową fazę i raz przechodzi do canonical `/desktop` z bieżącym tokenem
  generacji. Iframe prosi kontroler rodzica o refresh. Nowy dokument dostaje
  aktualną epokę i nie wykonuje ponownego reloadu, także po utracie ACK.
- Boot używa **GET `/api/profile/desktop`**, rozszerzającego istniejący
  endpoint ustawień (POST zachowuje swój kontrakt). Odczytuje identity,
  capability, canonical apps i wallet oraz dostępność rankingu właściwego
  sygnału. Nie uruchamia `sync_session_profile()`, pełnej fasady GN ani
  inicjalizacji schematu. Brak projekcji powoduje kontrolowany błąd i retry,
  nigdy fallback do pełnego `/api/profile`.
- Ustawienia i respect są małą projekcją `user_identity_projection.desktop_boot_json`.
  Aktualizuje ją istniejący guarded write profilu razem z identity.
  Własne source revision/checksum projekcji bootu wykrywają również zapis
  starszego procesu między migracją a reloadem; stale snapshot jest odrzucany.
  Zwykłe odczyty identity nie pobierają nowej kolumny. Istniejące konta
  wymagają jawnej migracji; nie zerujemy ustawień, tapet ani pozycji ikon.
- `session_restart_receipts` w `SessionGenerationStore` przechowuje receipt
  per hash użytkownika + lineage + epoka sygnału. Token przygotowania bootu
  i generacja są hashowane. Snapshot przygotowuje receipt dopiero po
  poprawnym odczycie danych i gotowości Signal Registry. Klient wysyła
  **POST `/api/ghostnetwork/restart/ack`** po zbudowaniu ikon/paska/pulpitu.
  Brak bootu, zła epoka lub zastąpiona sesja nie przechodzą walidacji.
  Utrata odpowiedzi ACK uruchamia bounded retry; powtórzenie jest idempotentne.
- Schemat: jedna nullable kolumna istniejącej projekcji i jedna tabela
  receipts w domenie sesji. Nie dodano równoległego busa, workera ani
  drugiego systemu endgame. Bieżący GET pełnego `/api/profile` zachowuje
  starszych konsumentów, ale nie jest wywoływany przez nowy boot.

### Trzecia bramka serwerowa — 139.3

Wynik lokalny: baseline **52 testy PASS**, pełna regresja **145 testów PASS
w 336,865 s**. Po końcowych zmianach adaptera HTTP dodatkowo **15 testów PASS**,
a po dodaniu własnego source revision/checksum projekcji bootu **19 testów
PASS w 54,412 s** (zestawy częściowo się pokrywają). Małe konto i profil
35 MB: zero heavy-profile read/write/bytes/scan, identyczna ograniczona liczba
zapytań przy boot snapshot + receipt/ACK. Cztery zestawy JS, py_compile,
node --check zmienionych skryptów i git diff --check PASS. Bramka serwerowa,
migracja produkcyjna i wizualny scenariusz pełnego rebootu pozostają otwarte.

Najpierw isolated tests po udostępnieniu zmian i pullu. **Nie reloadować
jeszcze web/territory-worker**: przed uruchomieniem nowego bootu potrzebna
jest migracja projekcji istniejących kont. Testy wykonują migrację wyłącznie
w tymczasowych bazach.

```bash
.venv/bin/python -B - <<'PY'
import os, shutil, sys, tempfile, unittest
root = os.getcwd()
sys.path[:0] = [root, os.path.join(root, "tests")]
with tempfile.TemporaryDirectory(prefix="chaos139-3-") as tmp:
    try:
        os.makedirs(os.path.join(tmp, "static", "js"))
        for name in ("session_generation.js", "terminal.js"):
            shutil.copyfile(os.path.join(root, "static", "js", name),
                            os.path.join(tmp, "static", "js", name))
        shutil.copyfile(os.path.join(root, "run.py"), os.path.join(tmp, "run.py"))
        os.chdir(tmp)
        os.environ["CHAOS_SESSION_FILE_DIR"] = os.path.join(tmp, "sessions")
        names = [
            "test_ghostnetwork_client_restart", "test_ghostnetwork_signal_show",
            "test_ghostnetwork_signal_show_http", "test_ghostnetwork_runtime_endgame",
            "test_ghostnetwork_transmission", "test_ghostnetwork_endgame_integrity",
            "test_ghostnetwork_endgame_audits", "test_session_generation_store",
            "test_session_generation_precommit", "test_session_generation_isolation",
            "test_profile_boot_snapshot", "test_identity_projection",
        ]
        result = unittest.TextTestRunner().run(
            unittest.defaultTestLoader.loadTestsFromNames(names))
    finally:
        os.chdir(root)
sys.exit(not result.wasSuccessful())
PY
node tests/ghost_signal_show_frontend.test.js
node tests/ghost_signal_show_recovery.test.js
node tests/js/test_ghostnetwork_delta_client.js
node --check static/js/ghost_signal_show.js
```

Test `tests/js/test_session_generation_isolation.js` oraz składnia zmienionych
session_generation/terminal są sprawdzane w środowisku z Node 24.8.0;
serwerowy Node 12 nie parsuje ich istniejącej składni przeglądarkowej.

Po zaliczonych testach można wykonać read-only plan migracji:

```bash
.venv/bin/python -B scripts/migrate_desktop_boot_projection.py --db data/game.sqlite3 --limit 100
```

Plan pokazuje tylko potrzebę zmiany schematu, liczbę brakujących projekcji
i limit partii. Przed `--apply` obowiązują świeży backup SQLite,
quick_check/SHA-256 i zatwierdzony zakres operatorski. Skrypt przygotowuje
dane przed writer-lockiem, a aktualizacja ma recheck revision/checksum.
Nie zapisuje profili. Po wykonaniu wszystkich zatwierdzonych partii plan
musi zwrócić `pending=0`; stale/invalid rows wymagają diagnozy, nie fallbacku.
Nowych reloadów i migracji produkcji nie wykonano w ramach implementacji.

Po migracji trzeba przeładować web i territory-worker, ponieważ nowy event
powstaje w runtime rolloveru. Ponowić read-only plan po reloadzie; jeśli
stary proces zdążył zmienić profil, uzupełnić wskazane projekcje w zatwierdzonym
zakresie. Następnie sprawdzić boot małego/dużego konta,
zachowanie ustawień i aplikacji, a w przygotowanym scenariuszu pełny
show → rollover → shutdown → boot z Signal Registry → ACK, dwie karty,
mobile w tle, utratę ACK i brak pętli reloadu. Production E2E nadal należy
do 139.4 i wymaga preflightu/backupów/monitora z handoffu.

### Zamknięcie 139.3 — produkcja, 2026-09-11

Operator wdrożył `69aa71c`. Izolowana bramka serwerowa: **145 testów Python
PASS w 615,612 s**, frontend show, recovery/lock/iframe oraz delta client JS
PASS. Po pullu wystąpił przejściowy GET `/api/profile/desktop` 405: nowy plik
JS był już dostępny, podczas gdy stary proces WWW nadal miał endpoint POST.
Procedura wdrożenia musi uwzględniać to okno niespójności statyk i backendu;
sam pull na żywym katalogu nie jest atomowym wdrożeniem.

Read-only plan: 31 projekcji, wymagana zmiana schematu. Operator wykonał
backup `data/backups/pre-139-3-20260911T061356737452Z.sqlite3`,
`quick_check: ok`, następnie migrację z limitem 31: prepared/written 31,
retry_or_recovery 0. Plan zwrócił pending 0 przed i po reloadzie PM2
13 (`chaos`) i 14 (`chaos-territory-worker`); oba procesy online.

Operator potwierdził przywrócenie ładowania gry i ustąpienie błędu API,
a następnie: „teraz wszystko wygląda poprawnie w grze”. Zamyka to 139.3
po testach serwerowych, migracji i ogólnym smoke wizualnym. Nie stanowi
potwierdzenia pełnego production E2E show → rollover → shutdown → boot
→ ACK ani wszystkich wariantów kart/mobile; pozostają one w 139.4.

### Wejście 139.4 — 2026-09-11

Operator zlecił rozpoczęcie ostatniej bramki. Lokalny HEAD `69aa71c`,
zmiany robocze wyłącznie w dokumentacji zamknięcia 139.3. Zaliczonej
regresji 145 testów nie powtarzamy bez nowej zmiany lub wykrytej luki.
Przed triggerem wymagane są aktualny cykl i blokady, stan kolejek oraz
filtra source eventu Ollamy, strict audyty, świeży backup i działający
monitor JSONL z PID. Historyczne ID cyklu/konfliktu monitora 138.2 nie
mogą zostać użyte domyślnie. Istniejący monitor wymaga przeglądu pokrycia
epoki restartu i receipt/ACK z 139.3; nie tworzymy równoległego monitora.
Nie uruchomiono triggera ani nie zmieniono produkcyjnego stanu gry.

### Wynik wejściowy 139.4 — produkcja 2026-09-11

Operator potwierdził HEAD `5ad4ce4`, cztery procesy online i brak filtra
CHAOS_OLLAMA_SOURCE_EVENT_ID. Cykl `ghostnetwork_0001` jest closed,
`ghostnetwork_0002` active, lecz wszystkie 20 części mają status pooled.
Nie jest to checkpoint 19/20 ani 20/20 z blokadą konfliktu wymagany przez
istniejący preflight finału.

Worker verify, runtime audit i lifecycle audit: ok=true, bez errors.
Ostrzeżenia: historical_incomplete_attempts i historical_legacy_records_present.
Raporty operatora: `data/audits/139-4-entry-20260911T063232Z`.
W poprzedzającym odczycie kolejka Ollamy miała completed 1415, dead_letter 80,
processing 1, ready 1 i brak retry_wait. Nie wykonano cleanupu.

Stan: kontrola runtime zaliczona, przygotowanie scenariusza produkcyjnego
pozostaje otwarte. Potrzebne są wskazane konta i zakres świata do testu,
przygotowane przez istniejące mechanizmy gry; nie wolno traktować pooled
jako błędu wymagającego bezpośredniego UPDATE ani odtwarzać starego finału.

### 139.4 — uzgodniony restore i online preflight

Operator uzgodnił cofnięcie postępu z graczami i wybrał restore checkpointu
001. Źródło: `game-pre-138-2-arm-20260910T151816Z.sqlite3`, quick_check OK,
SHA-256 `c61403a4d144927a7e29c11739834dc5f50cb358539d852e036046c081164a0d`.
Potwierdzono 20 active parts, zero skutków finału i dokładnie jeden blocker:
S1 contested / `territory_conflict_5145c32c3e634c66`.

Przy zatrzymanych czterech procesach wykonano recovery backup
`pre-139-4-restore-20260911T064149953277Z.sqlite3`, następnie restore przez
SQLite Backup API. Quick_check OK. Migracja bootu 31/31, pending 0,
SessionGenerationStore schema OK. Świeży backup przed triggerem:
`pre-139-4-trigger-20260911T064618158666Z.sqlite3`.
Monitor uruchomiony z PID 4037133 i limitem 7200 s; dowody:
`data/audits/139-4-restored-20260911T064618158666Z`.

Po starcie procesów online-preflight, worker verify, runtime i lifecycle
mają ok=true. Pozostają wyłącznie historical_incomplete_attempts oraz
historical_legacy_records_present. Operator potwierdził działanie gry.
Trigger nadal niewykonany.

Istniejący monitor rozszerzono lokalnie o show-start/restart events i
ograniczony odczyt receiptów dla epoki monitorowanego cyklu (limit 1000
z flagą truncation). Raport zawiera hashe użytkownika/lineage i czasy boot/ACK,
bez tokenów i profili. Podwójny restart event nie zalicza milestone.
Testy monitora: 5 PASS, git diff --check PASS. Rozszerzenie wymaga wdrożenia
i ponownego uruchomienia samego monitora z --resume; nie wymaga reloadu gry.
Czasy milestone monitora są czasami obserwacji, a nie dostarczenia do
przeglądarki; odbiór UI pozostaje osobnym dowodem operatorskim.

### 139.4 — odbiór wizualny finału, postflight pending

Operator zgłosił rozwiązanie S1 o 09:21 i ujawnienie drugiej blokady;
po jej rozwiązaniu o 09:22 show pojawiło się po około 3 s, praktycznie
równocześnie na trzech sesjach. Powrót karty i telefonu z tła przebiegł
zgodnie ze scenariuszem. Druga blokada pozostaje rozbieżnością względem
wcześniejszego preflightu wymagającą sprawdzenia w dowodach.

Po zakończeniu show operator potwierdził restart i Signal Registry na
pulpitach oraz ocenił test jako zaliczony. SFX ruszył sam na wszystkich
sesjach około 2–3 min po początku show. Kod terminal.js wiąże ten dźwięk
z ghost.signal_sent, nie ghost.signal_show_started. Decyzja operatora:
pozostawić ten kontrakt i wykorzystać go w Sprincie 140. Nie zmieniono audio.
Dokładny czas transmisji/dostarczenia pozostaje do porównania z monitorem.
Odbiór wizualny PASS; strict postflight, końcowe audyty i zatrzymanie
monitora pozostają otwarte przed zamknięciem całego sprintu.

### 139.4 — diagnoza czerwonej chronologii postflightu

Końcowe runtime/lifecycle/narrative ok=true; restart event jeden, boot receipts
3 i ACK 3, bez truncation. Strict endgame nie miał pending, ale odrzucił
show_not_created_before_effects: first_effect_at wskazywał 2026-08-19,
show_created_at 2026-09-11T07:24:15.001871+00:00, sent_at
2026-09-11T07:24:15.950182+00:00. Audyt konfliktów sprawdził dwa konflikty
bez naruszeń. Przyczyna w kodzie audytu: do czasów skutków transmisji
włączano created_at wszystkich nagród cyklu, również sprzed finału.

Poprawka ogranicza wyłącznie daty nagród do badanego signal_id; pozostałe
kontrole chronologii pozostają bez zmian. Test z historyczną nagrodą cyklu
przechodzi, a zbyt wczesna nagroda właściwego sygnału nadal jest odrzucana.
Izolowany zestaw audytów: 12 PASS (12,130 s), diff check PASS.
Wymagane wdrożenie poprawki i ponowienie strict postflight na tym samym
cyklu, z zachowaniem pierwotnego raportu. Nie wymaga kolejnego triggera,
restore ani restartu procesów. Nie ustalono jeszcze dokładnego źródła
produkcjnego znacznika z sierpnia ani pełnej osi czasu obserwowanej przez UI.

### 139.4 — końcowy strict postflight PASS

Operator ponowił audyt po poprawce zakresu nagród: ok=true,
status=complete, integrity_errors=[], pending=[], chronologia valid.
Show created: 2026-09-11T07:24:15.001871+00:00;
pierwszy skutek: 2026-09-11T07:24:15.167819+00:00;
signal sent: 2026-09-11T07:24:15.950182+00:00.
Show wyprzedza pierwszy skutek o 165,948 ms. Od utworzenia show do sent
upłynęło 948,311 ms. Nie należy na tej podstawie przypisywać obserwowanego
opóźnienia SFX 2–3 min wykonaniu samych skutków transmisji; dokładna relacja
obserwacji UI do znaczników backendu nie została rozstrzygnięta.

Wynik 139.4: wizualny E2E i techniczny postflight PASS, jeden restart event,
3 boot receipts i 3 ACK, runtime/lifecycle/narrative PASS. Do formalnego
zamknięcia pozostało clean stop monitora i zabezpieczenie końcowych dowodów.

### Zamknięcie Sprintu 139 — 2026-09-11

Operator potwierdził clean stop monitora: status=stopped, samples=1216,
errors=0, last_error pusty. Monitor zaobserwował restart_requested,
cycle_closed i next_cycle_active o 07:39:17.681769 UTC, a ACK o
07:39:19.680102 UTC. Są to czasy obserwacji; kanoniczne restart event
created_at wynosi 07:39:16.244206 UTC. Potwierdzono 3/3 receipts/ACK.

Sprint 139 zamknięty: COMPLETE / SERVER E2E PASS. Podsumowanie przekazanych
przez operatora dowodów: `doc/audits/139-4-production-e2e-summary.md`.
Pełne raporty i JSONL pozostają na serwerze w wcześniej wskazanym katalogu;
lokalne podsumowanie nie jest kopią pełnego logu. SFX pozostaje przypisany
do ghost.signal_sent zgodnie z decyzją operatora dla Sprintu 140.
