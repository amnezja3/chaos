# Przekazanie pracy do nowego wątku — CHAOS, Sprinty 139–140

Status: `ACTIVE HANDOFF / READ BEFORE ANY CHANGE`

Data stanu: `2026-09-10`

Zakres: pełny kontekst techniczny i operatorski po zamknięciu Sprintu 138.2,
przed implementacją Sprintów 139–140.

## 1. Instrukcja dla nowego wątku

Masz kontynuować rozwój gry CHAOS w tym samym repozytorium. Nie rozpoczynaj od
ponownego projektowania GhostNetwork ani od zgadywania stanu produkcji.

Przed pierwszą zmianą:

1. przeczytaj ten dokument w całości;
2. przeczytaj trzy dokumenty Sprintów 139–140 wskazane niżej;
3. sprawdź `git status`, bieżący branch i ostatnie commity;
4. zachowaj wszystkie zastane zmiany użytkownika i pliki untracked;
5. porównaj dokumentację z aktualnym kodem oraz testami;
6. wykonaj read-only baseline dotkniętych ścieżek;
7. dopiero potem zacznij `139.1`.

Jeżeli stan serwera nie został pokazany w bieżącym wątku, poproś operatora o
wynik małego read-only summary. Nie zakładaj, że proces, kolejka lub cykl nadal
ma stan zapamiętany z tego handoffu.

## 2. Produkt i sposób myślenia o grze

CHAOS to przeglądarkowa gra o hakowaniu cyfrowych zmysłów współczesnego świata.
Mapa jest wejściem do gameplayu, a fałszywy system operacyjny łączy narzędzia,
operacje, pliki, komunikację, terytoria i ekonomię informacji.

Podstawowa pętla:

```text
world object
  -> map action
  -> application/tool
  -> durable operation
  -> movement/risk/incidents
  -> resource/file
  -> market/mail/HC
  -> progression
  -> back to map
```

Najważniejsze zasady produktowe:

- mapa nie jest dekoracją — każda akcja musi mieć gameplayowy skutek;
- aplikacja uruchamia operację, nie zastępuje jej;
- operacje żyją w świecie i muszą przetrwać refresh/reconnect;
- dane oraz pliki są zasobem, nie tekstem ozdobnym;
- ryzyko i terytoria mają wpływać na decyzje gracza;
- efekty wizualne nie mogą udawać stanu innego niż canonical backend state;
- GhostSignal jest finałem cyklu i największym wydarzeniem w grze.

Canon i słownik znajdują się w:

- `doc/overview/ABOUT_CHAOS.md`;
- `doc/overview/name_of_game.md`;
- `doc/gameplay/gameplay_terms.md`;
- `doc/gameplay/gameplay_loop.md`.

## 3. Hierarchia źródeł prawdy

W przypadku rozbieżności obowiązuje kolejność:

1. aktualny kod, schema i działające testy;
2. trwały stan SQLite i immutable snapshots/ledgers;
3. najnowszy audyt produkcyjny;
4. `doc/history/project_journal.md`;
5. aktywny dokument sprintu;
6. starsze sprinty, roadmapy i dokumenty historyczne.

Dokumentacja opisuje zamiar i evidence, ale nie może unieważniać zachowania
aktualnego kodu. Przed zmianą zawsze sprawdź call site, kolejność transakcji i
testy regresyjne.

## 4. Stan przekazania

### 4.1. Repozytorium lokalne

W chwili tworzenia handoffu:

```text
branch: main
HEAD: c8bbaee
origin/main: zgodny przed lokalną dokumentacją Sprintów 139–140
```

Lokalne, niewypchnięte artefakty:

```text
M  doc/history/project_journal.md
?? doc/sprints/sprint_139_opis_15-minutowe_show.md
?? doc/sprints/sprint_139_ghostsignal_activation_restart.md
?? doc/sprints/sprint_140_ghostsignal_15_minute_finale.md
?? doc/runbooks/handoff_sprints_139_140.md
```

Nie kasuj ich, nie odtwarzaj z `HEAD` i nie wykonuj resetu. Przed commitem
ponownie sprawdź status, ponieważ użytkownik może równolegle dodać własne pliki.

### 4.2. Zamknięty Sprint 138.2

`138.2` ma potwierdzony production E2E PASS:

- konflikt `territory_conflict_5145c32c3e634c66` rozwiązano gameplayem;
- powstał dokładnie jeden lock, GhostSignal, show i ranking;
- `ghostnetwork_0001` został zamknięty;
- `ghostnetwork_0002` został dokładnie jednym aktywnym następcą;
- 20 części przeszło do historii;
- naliczono 90 nagród;
- skonsumowano 23 terytoria;
- utworzono 3/3 durable taski `ghost.signal_sent`;
- BlackNet, Googleplex News i Cyberner otrzymały publikacje;
- pierwotna kwarantanna Cybernera została zachowana, a Support Layer naprawił
  lineage bez drugiego model calla;
- strict endgame, narrative E2E, runtime i lifecycle zakończyły się `ok=true`;
- monitor zakończył pracę: 3858 próbek, 189 zmian, 0 błędów.

Pełny opis: `doc/sprints/138.2.production-e2e.md`.

### 4.3. Artefakty dowodowe

Wersjonowane raporty znajdują się w `doc/audits/`:

```text
138-2-final-endgame.json
138-2-final-signal-narrative.json
138-2-final-runtime.json
138-2-final-lifecycle.json
138-2-live-monitor.jsonl
138-2-live-monitor.summary.json
138-2-live-monitor.stdout.log
138-2-cyberner-quarantine.json
138-signal3-entry-preflight.json
138-signal3-entry-preflight.pretty.json
138-signal3-entry-preflight.summary.md
138-signal3-postflight-ghostnetwork_0001.json
138-signal3-production-e2e-findings.md
```

Duże JSON-y są evidence. Nie drukuj ich w całości do konsoli i nie ładuj do
promptu, jeżeli wystarczy mały skrypt summary.

Runtime backupy pozostają na serwerze w `data/backups/` i są ignorowane przez
Git. Recovery pointy z testu miały osobne SHA-256, ale ich aktualną obecność i
integralność należy ponownie sprawdzić przed użyciem. Nie przywracaj ich tylko po
to, aby testować Sprint 139: zakończony cykl produkcyjny jest canonical historią.

### 4.4. Stan wymagający ponownego potwierdzenia

Po teście PM2 17 (`chaos-ollama-worker`) został zatrzymany. Później potwierdzono
dry-run retirementu 25 historycznych tasków, lecz w przekazanym materiale nie ma
jednoznacznego potwierdzenia:

- wykonania mutującego `retire_narrative_backlog.py --apply`;
- stałego uruchomienia PM2 17 bez testowego filtra eventu;
- bieżącej liczby `ready/retry_wait` po tych czynnościach.

To nie jest błąd Sprintu 138.2, ale obowiązkowy check operacyjny. Najpierw
sprawdź read-only:

```text
pm2 status
pm2 env <aktualny-id-chaos-ollama-worker>
ollama_narrative_worker.py verify
audit_narrative_runtime.py --strict
audit_narrative_publication_lifecycle.py --strict
```

Nie uruchamiaj workera z historycznym
`CHAOS_OLLAMA_SOURCE_EVENT_ID=event_482e06e1401c116f`. Filtr służył wyłącznie do
kontrolowanego E2E.

## 5. Aktywny backlog: Sprinty 139–140

### 5.1. Dokument źródłowy

`doc/sprints/sprint_139_opis_15-minutowe_show.md` jest briefem produktowym.
Opisuje pełną narrację:

```text
części -> maszyny -> sieć -> GhostSignal -> transmisja
       -> rozpad starego stanu -> rekonstrukcja -> ranking -> nowy cykl
```

Nie zastępuje on dokumentów wykonawczych.

### 5.2. Sprint 139 — mechaniczna bramka P0

Dokument: `doc/sprints/sprint_139_ghostsignal_activation_restart.md`.

Problem potwierdzony podczas 138.2:

- backend rozpoczął konsumpcję i skutki GhostSignal;
- pełnoekranowe show pojawiło się dopiero po około 2–3 minutach;
- w luce gracz nadal miał otwartą mapę/narzędzie i mógł grać;
- po show nie nastąpił automatyczny reboot klienta;
- Signal Registry pojawiło się dopiero po ręcznym restarcie.

Root cause w aktualnym kodzie:

- `GhostTransmissionService.start_transmission()` i resume wykonują skutki
  transmisji przed `begin_stabilization()`;
- `begin_stabilization()` dopiero tworzy show;
- globalny HTTP guard w `run.py` blokuje tylko cykl `stabilizing`;
- frontend `static/js/ghost_signal_show.js` pokazuje overlay tylko przy
  `show_active`, a po końcu jedynie toast;
- `ghost.restart_required` tworzy stan/komunikat, ale nie wykonuje rebootu.

Docelowo show jest durable przed pierwszym skutkiem nieodwracalnym, lock
gameplayu obejmuje całe `transmitting + stabilizing`, a po poprawnym rolloverze
klient wykonuje jeden kontrolowany reboot do nowego cyklu.

Implementuj kolejno:

```text
139.1 durable timeline + ordering
139.2 backend gameplay lock + natychmiastowa propagacja
139.3 restart epoch/receipt + boot + Signal Registry
139.4 testy, recovery i production gate
```

Nie zaczynaj od CSS ani nowych assetów. Najpierw udowodnij ordering i lock.

### 5.3. Sprint 140 — pełna reżyseria finału

Dokument: `doc/sprints/sprint_140_ghostsignal_15_minute_finale.md`.

Sprint 140 zależy od mechanicznego PASS 139. Składa się z:

```text
140.1 manifest v2 + director + inventory assetów
140.2 części, maszyny, sieć, transmisja (00–08)
140.3 świat, wyniki, rekonstrukcja (08–14)
140.4 ranking, radio, shutdown/boot (14–15)
140.5 mobile performance + soak + polish
```

Ollama nie leży na ścieżce krytycznej show. Director używa immutable,
viewer-safe manifestu i wcześniej utrwalonych narracji. Timeout modelu, brak
radia lub pojedynczego assetu nie może zatrzymać settlementu ani restartu.

## 6. Mapa struktury projektu

### 6.1. Główne entrypointy

- `run.py` — Flask, HTTP API, sesje, integracja desktop/map, globalne guardy;
- `config.py` — env i polityki runtime;
- `database.py` — wspólne helpery SQLite/JSON;
- `session_generation_store.py` — durable generacje sesji i ochrona przed
  requestami starego klienta;
- `profileManagment.py` — ciężki profil; nie wolno używać w hot pathach bez
  jawnego wyjątku.

### 6.2. GhostNetwork

- `ghostnetwork/repository.py` — canonical persistence i transakcje;
- `ghostnetwork/service.py` — fasada/use cases i rollover;
- `ghostnetwork/runtime.py` — koordynacja ticków/recovery;
- `ghostnetwork/closure.py` — readiness, blokady konfliktowe i immutable lock;
- `ghostnetwork/transmission.py` — signal oraz skutki endgame;
- `ghostnetwork/show.py` — durable show i server-clock phase projection;
- `ghostnetwork/ranking.py` — immutable ranking;
- `ghostnetwork/archive.py` — read-only Signal Registry/archive;
- `ghostnetwork/deltas.py` — event/delta bridge;
- `ghostnetwork/visibility.py` — viewer-safe projections;
- `ghostnetwork/territory.py`, `conflicts.py`, `territory_defense.py` — domena
  terytoriów i konfliktów;
- `ghostnetwork/narrative.py`, `producers.py` — event -> narrative task;
- `ghostnetwork/ollama_worker.py`, `ollama_policy.py` — generacja;
- `ghostnetwork/publication.py`, `publication_lifecycle.py` — publikacja;
- `ghostnetwork/narrative_support.py` — deterministyczny Support Layer.

Logikę Sprintu 139 umieszczaj w domenowych modułach. `run.py` powinien pozostać
adapterem HTTP i integracją, nie nowym magazynem stanu ani monolitem endgame.

### 6.3. Frontend

- `static/js/ghost_signal_show.js` — obecny prosty overlay;
- `static/js/terminal.js` — desktop, aplikacje, Signal Registry, część delt;
- `templates/index.html`, `linux.html`, `linux_old.html` — wejścia klienta;
- `templates/map_template.html` — mapa Leaflet i Centrum Operacji;
- `static/css/style.css` — wspólna prezentacja;
- `static/audio/sfx/ghostnetwork/` — SFX GhostNetwork;
- `static/audio/sfx/secret_path/` — efekty Secret Path;
- `static/images/ghostnetwork/parts/` — assety części.

Sprint 140 powinien wydzielić Show Director i manifest zamiast rozbudowywać
jedną funkcję w `terminal.js` lub wkleić całą reżyserię do template.

### 6.4. Workery i narzędzia

- `scripts/territory_conflict_worker.py` — PM2 territory/runtime endgame;
- `scripts/ollama_narrative_worker.py` — PM2 Ollama consumer i komendy support;
- `scripts/narrative_publication_worker.py` — PM2 publisher;
- `scripts/audit_ghostnetwork_endgame*.py` — pre/postflight;
- `scripts/audit_narrative_*.py` — runtime, E2E, safety i lifecycle;
- `scripts/monitor_138_2_signal_e2e.py` — wzorzec trwałego monitora JSONL;
- `scripts/retire_narrative_backlog.py` — kontrolowany retirement, nigdy
  automatyczne czyszczenie.

### 6.5. Dokumentacja

- `doc/history/project_journal.md` — aktualna chronologia decyzji;
- `doc/sprints/` — plan, realizacja, bramki i wyniki sprintów;
- `doc/audits/` — evidence i read-only raporty;
- `doc/hardbugfix/` — pełne diagnozy najcięższych regresji;
- `doc/runbooks/` — procedury operatorskie;
- `doc/architecture/` — wiążące kontrakty przekrojowe;
- `doc/systems/` — dokumentacja domen;
- `doc/plans/` — przyszłe propozycje, nie aktualny stan.

Nowy dokument umieszczaj w właściwym katalogu. Nie twórz płaskich plików w
`doc/` poza `doc/README.md`. Po dodaniu/przeniesieniu ważnego dokumentu
aktualizuj indeks i referencje.

## 7. Canonical runtime i zasady danych

### 7.1. Jedno źródło prawdy

- SQLite/repository i immutable snapshots są canonical;
- delta bus jest powiadomieniem o zmianie, nie stanem;
- frontendowy cache i localStorage nie są źródłem prawdy;
- show manifest jest projekcją istniejących ledgerów, nie drugim endgame store;
- retry/recovery odtwarza brakujące efekty idempotentnie, nie tworzy alternatywnej
  historii.

### 7.2. Idempotencja

Każdy trwały efekt musi mieć stabilny klucz:

- event — `dedupe_key`;
- lock/signal/show/ranking — jednoznaczne lineage cyklu;
- reward/consumption/publication — własny ledger/receipt;
- restart — durable epoch i acknowledgement;
- frontend cue — exactly-once receipt dla efektów, które nie mogą zagrać dwa
  razy po reloadzie.

Ponowienie procesu ma zwrócić stan istniejący albo domknąć brakujący krok. Nie
może podwoić nagrody, konsumpcji, publikacji, SFX transmisji ani restartu.

### 7.3. Transakcje i SQLite

- przygotowanie danych wykonuj przed `BEGIN IMMEDIATE`;
- writer-lock ma obejmować minimalny CAS/recheck/write/commit;
- nie wykonuj zewnętrznych requestów, generacji modelu, skanów profili ani
  renderowania pod writer-lockiem;
- długie side effects rozbijaj na trwałe, idempotentne kroki recovery;
- zmiany schematu wymagają idempotentnej migracji albo jawnego ensure schema,
  testu upgrade istniejącej bazy i testu świeżej bazy.

### 7.4. Heavy-profile hot path — wiążący zakaz

Przeczytaj:
`doc/architecture/profile_hot_path_contract_130_11_plus.md`.

Zwykły endpoint, snapshot, delta, show, event, publisher i worker nie mogą:

- wywoływać `sync_session_profile()`;
- pobierać pełnego profilu dla identity/klanu/profesji/inventory/terytorium;
- tworzyć `UserProfileManager` dla małej mutacji;
- używać `list_profiles()` lub pętli `get_profile()` do fan-outu;
- wkładać profilu do sesji, cache, eventu, outboxu, taska lub manifestu;
- wracać do full-profile path jako cichego fallbacku.

Dla Sprintu 139–140 oczekiwany audit:

```text
profile_full_read: 0
profile_full_write: 0
profile_bytes: 0
list_profiles/all-user scans: 0
per-recipient profile reads: 0
allowed heavy call sites: none
```

Testuj małe konto i profil syntetyczny >= 35 MB. Brak regresji wydajności jest
częścią correctness.

### 7.5. Audience i prywatność

- publiczny show dostaje tylko viewer-safe projection;
- dane owner/clan/private nie mogą wypłynąć przez wspólny manifest;
- model nie decyduje o audience;
- CTA i publikacje muszą wskazywać canonical entity;
- nie loguj pełnych profili, lock payloadów ani danych dostępowych;
- infrastruktura SSH, klucze, hasła, cookies i prywatne IP nie trafiają do
  publicznego repozytorium.

## 8. Sesje i znaczenie restartu

CHAOS ma durable session generation. Stary request nie może zapisać profilu po
zastąpieniu generacji, a odpowiedź powstała pod starą generacją ma zostać
odrzucona kontrolowanym kontraktem reloadu.

W Sprincie 139 „restart GhostSystemu” oznacza:

- domknięcie show;
- zamknięcie starych okien klienta;
- kontrolowany shutdown/boot UI;
- canonical reload dokumentu do nowego cyklu;
- zgodność z aktualną session generation;
- durable restart receipt;
- gotowe Signal Registry na pierwszym boot snapshotcie.

Nie oznacza:

- `pm2 restart` jako mechaniki gry;
- restartu serwera;
- arbitralnego logoutu wszystkich graczy;
- nieskończonego `location.reload()`;
- localStorage jako jedynego receipt;
- pozostawienia innych kart z prawem mutacji starego świata.

Każde rozwiązanie musi przetestować: aktywną kartę, drugą kartę, mobile w tle,
reload podczas show, utratę sieci i powrót po deadline.

## 9. Delta, snapshot i frontend recovery

- event opisuje zmianę już zapisaną w canonical store;
- payload ma być minimalny i ustawiać stan docelowy;
- state versions rosną po zapisie, nigdy przed nim;
- luka wersji lub nieznany event uruchamia bounded snapshot recovery;
- snapshot nie może przywracać danych starszych niż zastosowana delta;
- polling pozostaje ścieżką samonaprawy, nie drugim niezależnym silnikiem;
- nowy handler nie może resetować popupów, menu i tooltipów wszystkich markerów
  przez przebudowę całej mapy.

Dla show: delta ma uruchamiać natychmiastowy refresh, a `/api/ghostnetwork/show`
ma samonaprawiać missing projection także podczas `transmitting`.

## 10. Mapa i znane regresje, których nie wolno przywrócić

Przed dotknięciem mapy/overlay przeczytaj:

- `doc/hardbugfix/138_operation_center_cache_signature_canvas_bounds_2026-09-09.md`;
- `doc/hardbugfix/scan_marker_menu_identity_leaflet_dispatch_sprint_138_getway_3_5_2026-09-07.md`;
- `doc/audits/map_delta_audit.md`;
- `doc/architecture/runtime_synchronization_audit.md`.

Twarde zasady:

- marker -> menu wiąż po stabilnym ID/closure konkretnego markera, nigdy po
  indeksie, kolejności tablicy, bliskości ani współdzielonej zmiennej;
- tooltip i popup są osobnymi kontraktami;
- nie usuwaj ochrony Leaflet canvas/polyline/polygon bounds race;
- nie loguj lawiny czerwonych wyjątków przy każdym pan/zoom;
- agreguj diagnostykę rendererów i ogranicz częstotliwość raportów;
- zachowaj menu pustego pola, tooltipy terytoriów/części GN i Centrum Operacji;
- testuj małe i duże konto, agresywny pan/zoom i mobile;
- warstwa replay show nie może być zwykłą interaktywną mapą ani mutować live
  world state.

## 11. Narracja, Ollama i publishery

Canonical pipeline:

```text
persisted domain event
  -> producer policy
  -> ghost_narrative_outbox
  -> Ollama worker claim/lease/heartbeat/attempt
  -> candidate validation
  -> accepted albo jawny terminal/quarantine
  -> narrative publisher claim
  -> publication receipt
  -> lifecycle medium record
```

Reguły:

- model generuje tekst, nigdy mechanikę, nagrody, ownership ani state transition;
- outbox jest trwały; plik JSON może być wyłącznie eksportem diagnostycznym;
- claim/lease/CAS i retry muszą być idempotentne;
- SIGTERM workera zatrzymuje claim loop, ale pozwala bounded model callowi się
  zakończyć; PM2 17 ma `kill_timeout=300000`;
- Support Layer naprawia istniejące lineage i zachowuje kwarantannę; nie tworzy
  nowego sygnału ani nie udaje odpowiedzi modelu;
- show 139/140 nie czeka na Ollamę;
- podczas show wolno czytać już zaakceptowane materiały i deterministyczne
  fallbacki;
- nie generuj masowo historycznego backlogu tylko po to, by uzyskać zero w
  kolejce;
- retirement wymaga dry-run, jawnego cut-offu, ochrony eventów i exact expected
  count; rekordy są terminalizowane, nie kasowane.

## 12. Środowisko i deployment

Repozytorium produkcyjne działa z katalogu:

```text
/home/johndoe/app/chaos
```

Host, użytkownik SSH, klucze i hasła pobiera się od operatora poza Git.

Procesy PM2:

```text
chaos                       ecosystem.web.config.js
chaos-territory-worker      ecosystem.territory-worker.config.js
chaos-ollama-worker         ecosystem.ollama-worker.config.js
chaos-narrative-publisher   ecosystem.narrative-publisher.config.js
```

Historycznie miały ID 13, 14, 17 i 18, ale ID nie jest kontraktem. Preferuj
nazwy i najpierw sprawdź `pm2 status`.

Zasady deploymentu:

1. użytkownik decyduje o commit/push, chyba że jawnie zlecił ich wykonanie;
2. po `git pull` sprawdź HEAD i listę zmienionych plików;
3. przed mutacją DB wykonaj świeży backup, `PRAGMA quick_check` i SHA-256;
4. migracje i clean-up uruchamiaj najpierw w dry-run;
5. `--apply` wymaga zaakceptowanego zakresu i expected count, gdy dostępny;
6. przy zmianie env użyj właściwego ecosystemu i `--update-env`;
7. zmienne GhostNetwork wspólne dla web/territory muszą pozostać symetryczne;
8. nie restartuj wszystkich PM2 bez potrzeby;
9. po restarcie sprawdź status, liczbę restartów, logi i mały gameplay smoke;
10. pełne raporty zapisuj do pliku, konsoli pokazuj summary.

Node na serwerze miał `v12.22.9`. Nie zakładaj dostępności nowych API Node w
testach operatorskich. Frontend pozostaje vanilla JS bez procesu bundlowania.

## 13. Backup, audyt i działania nieodwracalne

Przed production E2E lub migracją:

```text
git HEAD
pm2 status/env
fresh SQLite backup
PRAGMA quick_check
SHA-256
strict preflight
monitor JSONL + summary + PID
```

Po teście:

```text
strict postflight
narrative E2E
runtime audit
publication lifecycle audit
monitor clean stop
copy evidence to doc/audits
project journal update
```

Jeżeli test po nieodwracalnym triggerze zawiedzie:

- nie wykonuj drugiego triggera;
- nie czyść stanu;
- nie naprawiaj SQL-em;
- zachowaj backup diagnostyczny i pełne raporty;
- określ, czy stan jest spójny i recoverable;
- dopiero potem zdecyduj z operatorem o resume lub pełnym restore.

## 14. Standard implementacji

Każdy pod-sprint powinien przejść kolejno:

1. audit aktualnego call flow;
2. zapis decyzji i invariants;
3. minimalna zmiana domenowa;
4. test jednostkowy nowego kontraktu;
5. test recovery/idempotencji;
6. regresje sąsiednich rodzin;
7. profil hot-path i bounded-query check;
8. frontend contract test oraz `node --check` dla zmienionego JS;
9. `py_compile` dla zmienionego Pythona;
10. `git diff --check` i przegląd diffu;
11. aktualizacja sprintu, journalu i hardbugfixu, jeżeli wykryto poważną
    regresję;
12. dopiero potem controlled server validation.

Testy uruchamiaj od celowanych do szerszych. Nie „naprawiaj” czerwonego testu
przez osłabienie asercji, jeżeli test ujawnił naruszenie kontraktu.

Kod powinien:

- mieć małe funkcje i jasne granice domeny;
- używać repository/service zamiast przypadkowego SQL w route;
- mieć jawne failure states i bounded retry;
- nie łapać szerokiego wyjątku bez diagnostyki, chyba że jest to świadomy
  graceful degradation na niekrytycznej warstwie;
- zachować kompatybilność istniejących klientów albo dostarczyć migrację;
- być czytelny na Pythonie i Node dostępnych na serwerze;
- nie wymagać sieci/CDN na krytycznej ścieżce, jeśli asset jest częścią gry.

## 15. Bezwzględne zakazy

Poniższych działań nie wykonuj bez nowej, jawnej decyzji architektonicznej i
zgody operatora; część z nich nie jest dopuszczalna nawet jako szybki hotfix:

1. **Nie czytaj pełnych profili w hot pathach.**
2. **Nie twórz drugiego źródła prawdy** w cache, delcie, localStorage, pliku JSON
   ani pamięci workera.
3. **Nie dawaj Ollamie prawa do mutowania mechaniki.**
4. **Nie czekaj na Ollamę w GhostSignal show, settlement lub restarcie.**
5. **Nie emituj ręcznie canonical eventu, sygnału, taska, candidate ani receiptu**
   w celu zaliczenia testu.
6. **Nie uruchamiaj GhostSignal drugi raz** po częściowym lub pełnym commitcie.
7. **Nie rozwiązuj konfliktu przez czyszczenie projekcji lub SQL.** Musi przejść
   canonical lifecycle gameplayu.
8. **Nie wykonuj częściowego resetu tabel GN.** Recovery to idempotentne resume
   albo pełny, zweryfikowany restore po decyzji operatora.
9. **Nie kasuj ledgerów, historii, kwarantann, attempts, candidates ani receipts.**
10. **Nie cofaj części z `consumed` do `active`**, aby naprawić `stabilizing`.
11. **Nie traktuj eventu delta jako stanu** i nie licz snapshotu z eventów.
12. **Nie opieraj blokady gameplayu na overlayu.** Backend jest authority.
13. **Nie implementuj rebootu gry jako restartu PM2.**
14. **Nie używaj nieskończonego reloadu ani tylko localStorage jako restart
    receiptu.**
15. **Nie wiąż markerów i menu po indeksie, kolejności lub odległości.**
16. **Nie usuwaj ochron Leaflet bounds ani nie maskuj lawiny błędów samym
    throttlingiem bez naprawy źródła.**
17. **Nie przebudowuj całej mapy dla małej delty**, jeżeli niszczy popup/menu/
    tooltip identity.
18. **Nie podnoś timeoutów w celu ukrycia regresji wydajności.**
19. **Nie wykonuj masowego backfillu narracji bez bounded planu i dry-runu.**
20. **Nie uruchamiaj na stałe workera z filtrem source eventu z E2E.**
21. **Nie zapisuj sekretów, cookies, haseł, kluczy, prywatnych hostów ani pełnych
    profili w repozytorium lub logach.**
22. **Nie nadpisuj cudzych/untracked zmian i nie używaj destructive git reset.**
23. **Nie commituj i nie pushuj bez sprawdzenia statusu oraz zakresu; push wykonuj
    tylko, gdy użytkownik tego chce.**
24. **Nie oznaczaj sprintu PASS na podstawie lokalnych testów, jeżeli wymaga on
    manuala produkcyjnego.**
25. **Nie nazywaj mitigacji root-cause fixem bez evidence.**

## 16. Znane historyczne lekcje

- Profil `main` urósł do około 34,6 MB; ciężkie odczyty potrafiły zatrzymać mapę
  i cały runtime.
- Zmiana na bounceback/lekkie projekcje ujawniła regresje marker/menu identity;
  wydajność nie może niszczyć stabilnych powiązań UI.
- Centrum Operacji zniknęło przez niezdefiniowane `cacheSignature`, a Leaflet
  rzucał `Bounds.js: Cannot read properties of undefined (reading 'x')`.
- Ochrona tylko Polyline była niewystarczająca z powodu dziedziczenia Polygon;
  test musi odtwarzać prawdziwy układ prototypów.
- Pierwszy E2E `.signal.3` przedwcześnie wysłał sygnał, bo generic reconcile
  wyczyścił projekcję konfliktu. Obecny conflict gate ma zostać zachowany.
- Pierwszy postflight dawał false-negative przez limit 1000 eventów i zły
  algorytm checksum. Audytor również wymaga testów.
- Candidate Cybernera został poprawnie poddany kwarantannie za
  `selected_fact_mismatch`; nie wolno omijać walidatora tylko dlatego, że dwa
  inne media opublikowały tekst.
- Production test 138.2 udowodnił correctness backendu, ale ujawnił opóźniony
  show i brak rebootu. To bezpośredni cel Sprintu 139.

Pełne przypadki są w `doc/hardbugfix/` i `doc/audits/`.

## 17. Pierwsza sesja robocza nowego wątku

Po przeczytaniu dokumentów wykonaj bez mutacji:

```text
git status --short
git log -8 --oneline
git diff --check
git diff -- doc/history/project_journal.md
inspect ghostnetwork/transmission.py
inspect ghostnetwork/show.py
inspect ghostnetwork/service.py rollover/get_signal_show
inspect run.py gameplay guard/session generation/show endpoint
inspect static/js/ghost_signal_show.js
inspect targeted tests
```

Następnie przedstaw krótko:

1. potwierdzoną obecną kolejność transmisji;
2. minimalną zmianę dla `139.1`;
3. nowe invariants i plan testów;
4. pliki, które zostaną zmienione;
5. brak wpływu na heavy-profile hot path.

Po akceptacji albo zgodnie z poleceniem „rozpocznij 139” implementuj `139.1` bez
czekania na dodatkowe wyjaśnienia.

## 18. Warunek zamknięcia przekazania

Nowy wątek jest prawidłowo wdrożony w temat, jeżeli rozumie jednocześnie:

- dlaczego 138.2 jest PASS-em mimo nowego backlogu UX;
- dlaczego show musi powstać przed pierwszą konsumpcją;
- dlaczego blokada frontendu bez backend guardu jest nieszczelna;
- dlaczego reboot klienta nie jest restartem PM2;
- dlaczego Signal Registry musi być gotowe przed pierwszym nowym bootem;
- dlaczego Ollama nie może być zależnością finału;
- dlaczego każda zmiana musi zachować conflict gate, idempotencję, session
  generation, viewer safety i zerowy heavy-profile hot path;
- że Sprint 139 jest bramką mechaniczną, a Sprint 140 montażem finału.

Jeżeli którykolwiek z tych punktów jest niejasny, wróć do wskazanych dokumentów
i kodu przed pierwszą edycją.
