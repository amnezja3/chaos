# Sprint 139 — GhostSignal: natychmiastowy show i kontrolowany restart

Status: `IN PROGRESS / 139.1 LOCAL PASS / SERVER GATE PENDING`

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
python3 --version
python3 -B - <<'PY'
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

Przed wdrożeniem produkcyjnym nadal domknąć read-only summary z handoffu:
HEAD serwera, filtr Ollamy, ready/retry_wait, bieżący cykl i strict audyty.
Przekazany `pm2 status` potwierdził wszystkie cztery procesy CHAOS online,
ale nie zastępuje tych kontroli.

139.2 (HTTP lock/delta/recovery), 139.3 (reboot/ack/boot) i 139.4
(production E2E) pozostają otwarte. Samo 139.1 nie jest jeszcze gotową
mechaniczną bramką do produkcyjnego finału.
