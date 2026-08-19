# CHAOS — Project Journal

## 2026-08-19 - Sprint 130.9 Foundation: runtime enablement

- Dodano read-only runtime readiness z walidacją cyklu, 20 części, topologii
  i konfiguracji dropów oraz stabilnymi kodami `READY/NOT READY`.
- Start aplikacji nie mutuje GhostNetwork. Operatorski CLI udostępnia `status`,
  `verify` i suchy `bootstrap`; zapis wymaga jawnego `bootstrap --apply`.
- Konfiguracja pozostaje bezpiecznie wyłączona. Readiness blokuje dropy z
  chance spoza `(0, 1]`; nie wybrano produkcyjnej wartości balansowej.
- Dodano techniczną telemetrię aim/capture bez ukrytych danych oraz chroniony
  endpoint `/api/dev/ghostnetwork/readiness`.
- Foundation: `GO`. Durability, Runtime bridge i E2E pozostają otwarte;
  pending/unreconciled effects będą wdrożone wraz z outboxem.
- Testy celowane Foundation/cycle/reservation/discovery/pipeline: 32/32 OK;
  pełna regresja `test_ghostnetwork*.py`: 135/135 OK.

## 2026-08-19 - domknięcie Sprintu 130.9

- Dodano durable capture outbox oraz reconciliation/drain naprawiające crash
  pomiędzy committed capture i discovery. Retry zachowuje jedną część, jeden
  event discovery, contribution, reward i permanent history effect.
- Zwykły `/gonna-win` i post-130 ownership CAS enqueue'ują effect; replay
  receiptu wznawia go zamiast zwracać sukces z utraconym discovery.
- Kanoniczne publikacje obszarów i konfliktów sterują adapterem GN. Potwierdzono
  `public → contained → active`, release do `public`, freeze przy contest oraz
  powrót po resolved publication. Module progress aktualizuje się z lifecycle.
- Istniejący reward/contribution ledger został podpięty do eventów discovery,
  containment i activation. Bieżący stan cyklu nadal nie trafia do profilu.
- Runtime publication osiągający 20/20 wywołuje istniejący closure,
  transmission, signal, narrative i archive dokładnie raz; nie tworzy kolejnego
  cyklu.
- Lokalny operatorski bootstrap utworzył `ghostnetwork_0001` z 20 pooled parts.
  Verify w procesie development z drops enabled i chance `0.25` zwrócił
  `READY`; drain znalazł zero zaległych efektów. Nie wykonano deployu.
- Walidacja: nowe E2E/crash/bridge/endgame OK, pełne GhostNetwork 143/143 OK,
  post-130 territory/CAS/reconciliation 58/58 OK. Zbiorczy legacy
  `test_target_persistence` nadal ujawnia wcześniejsze zależności od kolejności
  i globalnego stanu; dotknięte przypadki przechodzą osobno.

## 2026-08-17 - Sprint 130.8.9.UX-appcreator.1: wspólny fundament creatorów

- Cztery creatory korzystają ze wspólnego katalogu opcji: klucz runtime,
  etykieta gameplayowa, ikona, opis i grupa. Payload nie został zmieniony.
- Checkboxy wizarda dostały wspólną warstwę OFF/ON. Filtry nadal czyszczą
  opcje niezgodne z rodziną i synchronizują ich wygląd.
- `trace` pozostaje wariantem Scanner / Recon, bez nowej rodziny backendowej.
- Picker wybiera jedną ikonę. Frontend i backend walidują pojedynczy widoczny
  glif, zachowując poprawne emoji/ZWJ i flagi.
- Nie zmieniano gameplayu, mapy, OFS, launch receipt ani zapisanych aplikacji.

#### historia dziennika w plikach 
* `doc/project_journal_13082026.md`

## 2026-08-14 - Secret Path: lore dla lekkiego oznaczania celu

- Klikniecie nazwy celu w menu hakowania zostalo nazwane ukryta sciezka
  `Secret Path`. Po potwierdzonym zapisie kanonicznego celu mapa uruchamia
  czterosekundowe show z przyciemnieniem, glitchem i sygnetem laczacym tarcze,
  ostrza oraz impuls.
- Dodano szesc losowanych scen lore. Komunikuja naprawienie kanalu celu,
  pominiecie pickera, gotowosc aplikacji pulpitu i terminala oraz przewage
  wynikajaca z odkrycia ukrytej sciezki interfejsu.
- Efekt jest warstwa prezentacyjna: nie zmienia progow zabezpieczen, wyniku
  operacji ani balansu. Odpala sie dopiero po sukcesie `/api/map/aim-target`,
  nie uruchamia mapowego boot loadera i nie przechwytuje interakcji z mapa.

## 2026-08-14 - Sprint 130.8.9: receipt aplikacji związany z celem

- Manualne uruchomienie aplikacji z pulpitu albo terminala dostaje teraz świeży
  `invocation_id` i `launch_receipt`. Receipt jest tworzony raz dla okna i
  przechodzi przez provisional, hydration, content autora, wybór oraz OFS;
  `flow_id` pozostaje wyłącznie korelacją diagnostyczną.
- Receipt zawiera skrót stabilnej tożsamości celu i losową tożsamość wykonania.
  Ponowne otwarcie tej samej aplikacji dla następnego celu nie może już
  odziedziczyć klucza `flowId:appId` ani payloadu poprzedniego celu.
- Backend zapisuje kanoniczny `expected_target_id` przy receipcie. Replay jest
  zwracany tylko dla tego samego receipt i tego samego celu; próba użycia go dla
  innego celu kończy się kontrolowanym `409 receipt_target_mismatch` przed
  odtworzeniem payloadu.
- Trace `APP_FLOW` pokazuje `invocation_id`, receipt, oczekiwany i bieżący cel
  oraz flagi replayu. Dodano regresje kontraktowe frontendu i endpointu dla
  użycia jednego receipt na dwóch celach.
- Capture, progi zabezpieczeń, konflikty, geometria i territory worker nie były
  zmieniane.

## 2026-08-14 - recovery markerów po publikacji konfliktu

- Końcowa delta workera `conflict_consolidated` uruchamia jeden debounced,
  read-only snapshot recovery. Zapobiega to sytuacji, w której geometria
  konfliktu ma już nową wersję, ale registry Leaflet nadal nie zawiera nowych
  filarów i innerów. Request mapy nadal nie wykonuje rebuildu.
- Do mapy dodano kontrolkę `↻` pod kontrolkami Leaflet. Ręczne odświeżenie
  przeładowuje wyłącznie dokument mapy i ponownie pobiera kanoniczne snapshoty,
  przejęte cele oraz aktorów; nie uruchamia deployu ani przebudowy geometrii.

## 2026-08-14 - lekkie oznaczanie celu z menu hakowania

- Nazwa obiektu w nagłówku menu hakowania działa teraz jako bezpośredni skrót
  do ustawienia `aimed_target`. Kliknięcie nie otwiera wyboru narzędzia, nie
  uruchamia aplikacji, OFS, operacji ani kolejki startowej.
- Dodano dedykowany endpoint `POST /api/map/aim-target`, który zapisuje
  kanoniczny cel przez istniejący kontrakt runtime, zachowuje stabilne
  `target_id` oraz kontekst podatności lub konfliktu i publikuje deltę
  `map.target_updated`.
- Frontend aktualizuje lokalny snapshot mapy i dolną belkę celu natychmiast po
  odpowiedzi endpointu. Nagłówek ma blokadę ponownego kliknięcia podczas zapisu
  oraz pozostaje dostępny z klawiatury jako zwykły przycisk.
- Ponowne wskazanie tego samego celu zachowuje jego dotychczasowy postęp
  `actions_allowed` i stan `security`; wskazanie innego celu rozpoczyna czysty
  stan rozpoznania bez wykonywania akcji hakowania.
- Odzyskiwanie postępu toleruje różnicę między identyfikatorem markera
  prezentacyjnego i kanonicznym `target_id`: zgodność pozycji oraz etykiety
  pozwala zachować aktualne `actions_allowed` i `security`, dzięki czemu belka
  pokazuje bieżący poziom rozbrojenia bez ponownego uruchamiania narzędzia.
- Walidacja: `python -m py_compile run.py database.py
  response_network\\territory_delta.py`, 48 testów celowanych oraz
  `git diff --check` — OK.



## 2026-08-14 - audyt zmiany celu: mapa vs pulpit i terminal

- Testy ujawniły, że lekkie wskazanie nowego celu z nagłówka menu mapy zapisuje
  poprawny `aimed_target`, ale kliknięcie opcji w ponownie uruchomionej aplikacji
  może przywrócić wynik dotyczący poprzedniego celu. Objaw obejmuje podmianę
  belki, pozorny sukces bez trwałej kropki oraz brak finalnego capture mimo
  kompletu akcji.
- Ścieżka mapowa pozostaje spójna, ponieważ `/hack-action` kanonizuje cel,
  zapisuje go w `PlayerTargetRuntimeStore` oraz tworzy dla startu aplikacji nowy
  receipt oparty o `flow_id`, `client_action_key` i aplikację. Kolejka przekazuje
  ten receipt dalej do `/gonna-win`.
- Audyt wykazał lukę ścieżki pulpit/terminal: ręczny start dziedziczy globalny
  `__lastHackFlowId`, a gdy nie ma receipt z kolejki, tworzy klucz
  `flowId:appId`. `/gonna-win` wykorzystuje ten klucz jako receipt
  idempotencyjny (TTL 900 s), więc kolejne uruchomienie tej samej aplikacji dla
  nowego celu może dostać replay payloadu wcześniejszego celu. Uruchomienie
  narzędzia z mapy generuje świeży receipt i dlatego wychodzi z impasu.
- Guard odpowiedzi starego okna i klucz okna zawierający tożsamość celu są
  potrzebne, ale nie rozwiązują replayu backendowego: payload jest już
  sklasyfikowany jako duplikat zanim wykonywana jest aktualna akcja.
- Wymagany kontrakt naprawczy: każda manualna instancja działania aplikacji musi
  otrzymać nowy, niezmienny `launch_receipt`, związany jednocześnie z aplikacją i
  stabilną tożsamością celu. Ponowienie tego samego kliknięcia może użyć tego
  samego receipt, ale nowy cel ani nowe uruchomienie nie mogą dziedziczyć receipt
  poprzedniej sesji. Po capture runtime ma zostać wyczyszczony, mapa ma dostać
  deltę, konflikt ma trafić do workera, a kolejny start ma powstać na świeżym
  kontekście.
- Osobno wyrównano projekcję postępu celu: `disarm_progress` ze store jest
  procentem 0-100, a nie surową liczbą wykonanych czterech akcji. Dzięki temu
  belka i cztery kropki opisują ten sam stan autorytatywny.

## 2026-08-15 - Sprint 130.8.9.SFX.1: fundament Game SFX

- Dodano jeden desktopowy właściciel efektów dźwiękowych: `window.GameSfx` w
  `static/js/game_sfx.js`. Moduł ładuje się przed Ghost Radio, OFS i terminalem,
  ale nie jest podpięty do żadnego zdarzenia gameplayowego.
- Dodano pusty produkcyjny manifest `static/audio/sfx/manifest.v1.json` jako
  lokalną allowlistę. Definiuje magistrale `lore`, `gameplay`, `message`,
  `system` i `ui`; payload nie może przekazać własnej ścieżki pliku ani ominąć
  limitów manifestu.
- Silnik obsługuje nieblokujący init i preload, autoplay unlock po pierwszym
  geście, lokalne `enabled` i `volume`, priorytety, limity głosów, cooldown,
  deduplikację `event_id`, ujemny cache brakujących assetów oraz kontrolowane
  wyniki błędów. Brak audio nie rzuca błędu do bootu ani aplikacji.
- Ghost Radio dostało przejściowy `duck_gain` z wieloma niezależnymi uchwytami.
  Efektywna głośność jest liczona oddzielnie od wartości użytkownika, więc
  zakończenie ostatniego SFX przywraca radio bez nadpisania jego ustawień.
- Dodano test kontraktowy modułu i test kolejności skryptów. Manifest pozostaje
  bez eventów i plików MP3 do Sprintu SFX.2, dlatego samo wdrożenie SFX.1 nie
  zmienia dźwięków gry.
- Walidacja dostępna w tej sesji: `node --check static/js/game_sfx.js`,
  `node --check static/js/ghost_radio.js`, `node --check static/js/terminal.js`,
  `node tests/js/test_game_sfx.js`, `node tests/js/test_operation_feedback.js`
  oraz `git diff --check` — OK. Lokalne `python.exe` było niedostępne, więc
  unittest Pythona pozostaje do uruchomienia w środowisku projektu.

## 2026-08-15 - Sprint 130.8.9.SFX.2: sześć scen Secret Path

- Sześć istniejących wariantów wizualnych Secret Path otrzymało stabilne
  `scene_id` i mapowanie 1:1 na `secret_path.scene_01`-`scene_06`. Jeden losowany
  rekord steruje jednocześnie tekstem, sceną i eventem audio; losowanie dźwięku
  nie jest wykonywane osobno.
- Audio jest odblokowywane w geście kliknięcia nazwy celu, lecz startuje dopiero
  po autorytatywnym sukcesie `/api/map/aim-target`. Błąd API, mute, autoplay albo
  brak MP3 pozostawia bez zmian ścieżkę gameplayową i czterosekundowe show.
- Kolejne uruchomienie Secret Path kasuje poprzedni timer i głos magistrali
  `lore`. Event id ma postać `secret-path:<target_id>:<local_sequence>`, a po
  końcu show uchwyt audio i ducking są zwalniane.
- Manifest dostał sześć jawnych lokalnych ścieżek MP3. Pliki należy dostarczyć
  pod `static/audio/sfx/secret_path/` zgodnie z README; bez nich działa
  kontrolowany fallback wizualny.
- Ustawienia pulpitu dostały przełącznik efektów, suwak głośności oraz test
  Secret Path. Wszystkie korzystają z jednego `window.GameSfx`, bez osobnego
  odtwarzacza i bez wpływu na Ghost Radio poza uchwytem duckingu.
- Dodano test kontraktu sześciu scen, kolejności gesture/API/show oraz kontrolek
  Ustawień. Składnia JS, test silnika Node i `git diff --check` są poprawne;
  lokalny `python.exe` ponownie był niedostępny, więc unittest Pythona pozostaje
  do uruchomienia w środowisku projektu.
- Test wdrożeniowy ujawnił cache pustego manifestu SFX.1: moduł i manifest miały
  niezmienione URL-e, a manifest świadomie używa `force-cache`. SFX.2 dostał
  wspólny cache-bust `sfx-secret-path-2`, dzięki czemu przeglądarka pobiera
  sześć nowych wpisów i nie pozostaje na pustej allowliście fundamentu.

## 2026-08-15 - Sprint 130.8.9.SFX.3: autorytatywny capture

- Test produkcyjny potwierdził sześć scen i sześć plików Secret Path; bramka
  SFX.2 została zaakceptowana przed wejściem w dźwięki gameplayowe.
- Każde zatwierdzone przejęcie otrzymuje backendowy `capture_version`, wspólny
  dla odpowiedzi `/gonna-win` i delty `map.target_captured`. Desktop kieruje oba
  sygnały do jednego helpera oraz jednego event id
  `target-captured:<target_id>:<capture_version>`, więc response i delta nie
  odtwarzają efektu podwójnie.
- Jawny `node_role=pillar` wybiera `capture.conflict_pillar`; pozostałe cele
  wybierają `capture.target`. Frontend nie zgaduje innera z ikony, geometrii ani
  położenia.
- `capture.conflict_resolved` jest uruchamiany wyłącznie przez kanoniczną deltę
  `territory.conflict_changed` ze statusem `resolved`. Snapshoty, recovery mapy,
  lokalne kropki i pasek rozbrojenia pozostają ciche.
- Manifest dostał trzy eventy magistrali `gameplay` i cache-bust
  `sfx-capture-3`. Produkcyjne assety są oczekiwane w
  `static/audio/sfx/capture/`; ich brak korzysta z istniejącego bezpiecznego
  negative cache i nie wpływa na capture, konflikty ani przebudowę terytorium.

## 2026-08-15 - Sprint 130.8.9.SFX.4: Cyberner i komunikaty systemowe

- Test wdrożeniowy użytkownika zaakceptował SFX.3; po tej bramce uruchomiono
  warstwę wiadomości bez zmian w gameplayu capture i konfliktów.
- Kanoniczna delta `cyberner.message_created` uruchamia dźwięk incoming tylko w
  trybie live. Pierwszy poll, recovery oraz pierwszy poll po błędzie połączenia
  są celowo ciche, więc historia i cursor catch-up nie tworzą lawiny audio.
- Własna wysłana wiadomość może dostać ciche potwierdzenie dopiero po odpowiedzi
  backendu z trwałym `message_id`. Incoming i sent współdzielą dedupe
  `cyberner:<message_id>`, a dodatkowy cooldown kanału ogranicza serie zdarzeń.
- Poll komunikatów systemowych używa stabilnego ID ze store i odtwarza wyłącznie
  klasy warning/critical; info pozostaje ciche. Boot i reconnect są ciche tak
  samo jak w delcie Cybernera.
- Manifest dostał cztery allowlistowane assety magistral `message` i `system`.
  `system.critical` ma najwyższy priorytet i może przerwać słabsze głosy, które
  zwalniają własne uchwyty duckingu Ghost Radio. Cache-bust zmieniono na
  `sfx-messages-4`.
- Dodano README kontraktu plików `static/audio/sfx/messages/` oraz rozszerzono
  test silnika o globalne przerwanie niższego priorytetu. Audio pozostaje
  niezależne od read cursorów, unread count, otwierania okna i store wiadomości.
- Walidacja: `python -m unittest tests.test_game_sfx_frontend_contract
  tests.test_cyberner_channel_routing` — 15 testów OK; trzy celowane testy
  `SystemMessageStore` i endpointu `/system-messages` — OK; `python -m py_compile
  run.py database.py`, `node --check static/js/game_sfx.js` i `node --check
  static/js/terminal.js` — OK.

### Korekta watchdog audio po testach SFX.3

- Audyt wykazał, że silnik zatrzymywał MP3 sztywno po manifestowym
  `max_duration_ms`, nawet jeżeli metadane assetu wskazywały dłuższy plik. Limity
  2,5–7 s mogły przez to ucinać prawidłowy efekt przed naturalnym `ended`.
- Watchdog jest teraz przeliczany po `loadedmetadata`: wybiera większą wartość
  z limitu manifestu oraz pełnej długości MP3 z zapasem 750 ms. Zachowano
  twardy bezpiecznik 30 s i dotychczasowe sprzątanie głosu oraz duckingu.
- Dodano kontrakt JS dla assetu krótszego i dłuższego od limitu manifestu oraz
  dla bezwzględnego limitu awaryjnego.

## 2026-08-15 - Sprint 130.8.9.SFX.5: OFS i polish

- Domknięto wspólny lifecycle audio aplikacji hookami `ofs.intro`,
  `ofs.choice_available`, `ofs.choice_confirmed`, `ofs.progress_checkpoint`,
  `ofs.success`, `ofs.failure` i `ofs.runtime_warning`. Wszystkie cztery
  renderery wykonawcze korzystają z jednego `OperationFeedbackSession` i
  globalnego `GameSfx`.
- Każda emisja ma dedupe `ofs:<session_id>:<phase>:<sequence>`. Checkpointy są
  ograniczone do trzech na sesję i wyciszone na mobile do 620 px oraz przy
  `prefers-reduced-motion`, bez zmiany scen, requestu lub payloadu.
- Projekcja `feedback_content.audio_events` dopuszcza wyłącznie siedem
  odpowiadających sobie eventów semantycznych. Próby podania URL albo
  podmiany semantyki są ignorowane i korzystają z globalnego fallbacku.
- Manifest dostał siedem eventów magistrali `ui`, cache-bust `sfx-ofs-5` oraz
  README kontraktu assetów `static/audio/sfx/ofs/`. Brak pliku pozostaje
  bezpiecznym, cichym fallbackiem.
- Rozdzielono wynik gameplayowy (`ofs.failure`) od problemu transportu lub
  odpowiedzi runtime (`ofs.runtime_warning`). Critical nadal może przerwać
  OFS, a zwalnianie głosu przywraca ducking Ghost Radio.

### Korekta personalizacji `button_choice`

- Audyt wykazał, że tylko `scan_ports` miał własne pule wyborów. Pozostałe
  akcje uruchomione w aplikacji `button_choice` korzystały ze wspólnego
  fallbacku `feedback.operation.*`, przez co różne narzędzia wyglądały jak
  jedna prezentacja skanera.
- Dodano `button_choice_action_profiles` dla wszystkich 14 akcji OFS, również
  aliasów `scan_hotspots` i `audio_hack`. Każda akcja ma własny prompt,
  przyciski, wartości i jawny schemat wyłącznie prezentacyjnego stanu.
- Walidator wymaga puli `feedback.<action_key>.*` dla każdej akcji i izoluje
  wadliwy profil bez wyłączania pozostałych operacji. Composer wybiera profil
  według bieżącego `action_key`, niezależnie od domyślnego renderera operacji.
- Dodano cache-bust słownika `button-choice-actions-1` oraz regresję JSON/JS
  potwierdzającą kompletność, unikalność i brak współdzielenia pul.

### Korekta terminalnego lifecycle wyborów OFS

- Wynik payloadu, błąd, anulowanie i `dispose` usuwają teraz cały aktywny
  panel `button_choice`, zamiast jedynie blokować jego przyciski. Niewybrana
  decyzja nie pozostaje więc pod autorytatywną sceną końcową.
- Zachowano dotychczasowe potwierdzenie decyzji dla wyboru faktycznie wykonanego
  przez gracza; korekta nie wybiera automatycznie opcji po nadejściu payloadu.
- Dodano regresję JS sprawdzającą usunięcie nierozstrzygniętego panelu przed
  prezentacją sukcesu.
- Przyciski aktywnego wyboru OFS dostały czytelny glow i lekki lift na
  `hover/focus`, a wybrana opcja krótki jitter/glitch w czasie istniejącego
  potwierdzenia. Efekt nie wydłuża requestu i respektuje
  `prefers-reduced-motion`.
- Naprawiono tytuł belki po hydratacji: renderery `terminal`, `button_choice`,
  `window` i `progressbar_random` zachowują publiczną nazwę aplikacji z
  kontekstu startowego zamiast zastępować ją technicznym `app_id`.
## 2026-08-16 - Sprint 130.8.9.fixsprint-lvlrsp.1: trwałe rozliczanie progresji

- Audyt potwierdził, że pełne synchronizacje profilu mogły zapisać bieżące
  `territory_stats.effective_area` pomiędzy capture w `/gonna-win` a publikacją
  geometrii przez workera. Dotychczasowy finalizer widział wtedy przyrost równy
  zero, dlatego LVL i RSP nie rosły mimo poprawnego przejęcia.
- Dodano tabelę `territory_progression_receipts` oraz migrację `008`. Receipt ma
  unikalny event źródłowy, aktora, cel, zakres konfliktów i niezmienny snapshot
  geometrii sprzed transferu. Migracja nie wykonuje historycznego backfillu.
- Zwykły capture rozlicza receipt po lokalnej przebudowie, a conflict capture
  pozostawia go workerowi. Kanoniczny reconciliation-set finalizuje progresję
  po publikacji geometrii; późniejszy retry zwraca zapisany wynik bez ponownego
  zwiększenia `level` lub `respect`.
- Zapis nagrody i przejście receiptu `pending -> applied` odbywają się w jednej
  transakcji SQLite. Finalizer scala tylko pola progresji z aktualnym profilem,
  dzięki czemu nie cofa równoległych zmian aplikacji, operacji ani celu.
- Kilka capture skonsolidowanych w jednym publish korzysta z jednego łącznego
  przyrostu geometrii; pozostałe receipty są konsumowane jako coalesced i nie
  mogą powielić tej samej nagrody.
- Dodano log `[PROGRESSION_SETTLEMENT]` oraz regresje immutable baseline,
  idempotentnego settle i atomowego zapisu profilu. Wysokości nagród i zasady
  gameplayowe pozostały bez zmian; są zakresem osobnego sprintu `.gameplay-lvlrsp.2`.
- Korekta po teście gameplayowym: próg `+1 LVL za 10%` został przeniesiony z
  globalnego `effective_area` na surową powierzchnię konkretnego klastra, który
  objął przejęty punkt. Receipt zapisuje geometrie klastrów i pozycję celu,
  więc zmienne identyfikatory `player_areas` po rebuildzie nie zrywają ciągłości.
  Małe przyrosty jednego klastra kumulują się, a rozrost pozostałych pól nie
  dopina jego progu. RSP pozostaje liczone z efektywnego przyrostu.

## 2026-08-16 - Sprint 130.8.9.gameplay-lvlrsp.2: nagrody strategiczne

- Pełne otoczenie i trwałe wchłonięcie obcego klastra daje `+1 LVL` oraz
  `+1 RSP` za każdy faktycznie przepisany filar. Role pochodzą z immutable
  snapshotu klastra; innery nie zwiększają premii.
- Każdy konflikt zamknięty przez kanonicznego aktora daje `+1 LVL` i RSP równy
  jego poziomowi sprzed całego rozliczenia. Kilka konfliktów zamkniętych jednym
  otoczeniem sumuje się z nagrodą za wchłonięcie.
- Dodano atomowy `settle_strategic` oparty na istniejących progression receipts.
  Klucze zdarzeń zawierają dedupe otoczenia albo `conflict_id` i wersję
  rozwiązania, dlatego retry, restart workera i republikacja nie duplikują LVL
  ani RSP.
- Guard wspólnego klanu działa przed snapshotem, transferem i receiptem.
  Chronione relacje nie generują reward-only eventów.

## 2026-08-17 - Sprint 130.8.9.UX-appcreator.2 i start .3

- Domknięto wspólną prezentację opcji czterech creatorów: zasoby, operacje,
  akcje i cele są grupowane semantycznie, a zabezpieczenia otrzymały nazwy
  gameplayowe. Klucze zapisywane do kontraktu nie zostały zmienione.
- Filtry wykonują deterministyczną sekwencję rodzina → cel → akcja. Ukrywana
  aktywna wartość jest czyszczona i raportowana w statusie `aria-live`, natomiast
  nadal zgodne wybory przetrwają przejście Wstecz/Dalej.
- Krok ryzyka rozdziela pytania mapowane na `interferes_with`, `requires_off`,
  `disables` i `affects`; techniczne nazwy pozostają w podglądzie JSON.
- Rozpoczęto Sprint `.3`: podgląd ma podsumowanie dla gracza i zwijany JSON,
  walidacja wskazuje numer kroku oraz sposób naprawy, dodano stany dostępności
  zakładek i kontrolowany układ małego viewportu.
- `node --check static/js/terminal.js` oraz `git diff --check` przeszły.
  Lokalne testy Python pozostają niewykonane, ponieważ systemowy `python.exe`
  nie uruchamia procesu w tej sesji Windows; zakres zabezpiecza rozbudowany
  `tests/test_creator_ux_contract.py` do uruchomienia w środowisku projektu.
## 2026-08-17 - domknięcie Sprintów 130.8.9.UX-appcreator.1–3

- Audyt odbiorczy wykrył i usunął otwieranie pełnej puli opcji po pustym
  przecięciu filtrów. Aktywne ograniczenie rodziny, celu lub akcji może teraz
  poprawnie dać pusty wynik zamiast proponować nieobsługiwany kontrakt.
- Backend creatora waliduje jawne rodziny, tryby, typ aplikacji oraz wartości
  celów, akcji, operacji i zasobów. Tryb desktopowy nie przyjmuje akcji mapy,
  natomiast mapowy i hybrydowy jej wymagają. Ścieżka legacy bez rodziny nie
  została zmieniona i nie wymaga migracji.
- Zachowano `tracker` w rodzinie Scanner / Recon. Dzięki temu `Namierz cel`
  pozostaje istniejącą akcją `trace` z `generic_trace`, bez tworzenia nowej
  rodziny i bez cichego przepisywania typu przez backend.
- Podgląd gameplayowy obejmuje również ryzyko, wymagania, wyłączane
  zabezpieczenia i wpływ na gracza. Zakładki mają pełne relacje ARIA, obsługę
  strzałek/Home/End, a walidacja oznacza konkretne pole i prowadzi do kroku
  naprawy. Formularze mają kontrolowany scroll oraz jednokolumnowy układ na
  małym ekranie.
- Dodano regresję JS zachowania filtrów i wspólnego podpięcia czterech
  interfejsów oraz backendowe testy odrzucania wadliwego kontraktu i akceptacji
  tracera. `node --check static/js/terminal.js`, test Node creatora i
  `git diff --check` są poprawne. Testy Pythona pozostają do uruchomienia w venv
  CHAOS, ponieważ lokalny alias Windows nie uruchamia interpretera w tej sesji.
## 2026-08-19 - Sprint 130.9.1 Etap 1: gotowość do manualnego gameplayu

- Potwierdzono lokalny runtime w jawnym profilu development: cykl
  `ghostnetwork_0001`, 20 pooled części, valid topology, zero reservations,
  pending i unreconciled effects; `verify` zwraca `READY` przy drop chance 0.25.
- Dry-run `reconcile` i `drain` nie wykazał pracy do wykonania. Nie wykonano
  manualnego aim/hack/capture ani mutującego cleanupu.
- Naprawiono `tools/audit_ghostnetwork_runtime_state.py`, który odwoływał się do
  nieistniejącej metody repository; audyt korzysta teraz z kanonicznego cycle
  service i ma test regresyjny.
- `test_target_persistence` odizolowano od globalnych target/operation store'ów.
  Historyczne asercje map bootstrap, teleportu, recovery scopes i launch queue
  dostosowano do aktualnych kontraktów. Wynik pełnego pliku: `221/221 OK`.
- Przedmanualowa paczka bootstrap/readiness/durability/telemetry/bridge/E2E:
  `17/17 OK`. `py_compile` i `git diff --check` są poprawne.
- Status: `READY FOR MANUAL GAMEPLAY TEST`. Etap 2 czeka na wynik i logi
  użytkownika. Nie wykonano commita, deployu ani produkcyjnego włączenia flag.

### Korekta środowiska manualnego

- Manual przeniesiono z lokalnego runtime na kontrolowany serwer, ponieważ
  lokalnie nie ma territory workera ani właściwych kont testowych.
- Lokalna bramka pozostaje zielona, ale nie jest już końcowym readiness manuala.
  Nowy status: `LOCAL PRE-FLIGHT PASSED — SERVER RC REQUIRED`.
- Dopisano Etap 1B: backup, spójny commit web/workera, jawne flagi RC, testy
  serwerowe, status/verify/audyt, dry-run reconcile/drain, walidację kont oraz
  rollback bez domyślnego kasowania trwałych efektów.
- Commit, push, deploy i restart PM2 nadal nie zostały wykonane; wymagają
  wskazania hosta/procesów oraz jawnej zgody na wdrożenie release candidate.

## 2026-08-19 - Sprint 130.9.1 Etap 2 po manualnym teście serwerowym

- Dwóch testerów otrzymało naturalny drop części GhostNetwork przy chance 0.25.
  Jeden przypadek potwierdził log i frontendowa delta `ghost.part_discovered`;
  drugi potwierdził tester, a log nie był dostępny po odświeżeniu.
- Potwierdzono realny przepływ `map → aim → hack → capture → drop → discovery`.
  Nie ma podstaw do wymagania kolejnego manualnego dropu.
- `version_gap` przy discovery wynika z globalnego domenowego `state_version`:
  wewnętrzne eventy reservation/reward nie muszą tworzyć delty widocznej dla
  gracza. Klient prawidłowo przechodzi wtedy na autorytatywny snapshot recovery.
  Finding nie jest blockerem i nie wymaga przebudowy delta systemu.
- Rozszerzono odczytowy audyt runtime o per-part weryfikację eventu discovery,
  contribution, applied reward, profile history i capture effect exactly-once.
- Regresja: GhostNetwork `144/144`, territory/CAS/reconciliation `134/134`,
  `test_target_persistence` `221/221`, celowane delta/audit `10/10`; `py_compile`
  i `git diff --check` przeszły.
- Serwerowy odczyt potwierdził `READY`, cykl `ghostnetwork_0001`, 20 części
  (`18 pooled`, `1 public`, `1 contained`), dwa discovery oraz zero
  pending/unreconciled effects. Każda część ma pojedynczy event, contribution,
  applied reward i applied capture effect; brak duplikatów.
- Audit znalazł konkretną regresję: oba profile miały `profile_history=0` mimo
  applied ledger i eventu `ghost.player_history_changed`. Późny pełny zapis
  `/gonna-win` nadpisywał historię zapisaną przez reward coordinator.
- Naprawiono monotoniczne zachowanie historii w `UserStore.save_profile()` i
  zachowanie dynamicznych pól GN przez `UserProfileManager`. `reconcile` potrafi
  odczytowo wskazać braki, a z `--apply` odtworzyć samą historię bez ponownego
  RSP, contribution lub discovery.
- Po poprawce: testy celowane `14/14`, GhostNetwork `144/144`,
  `test_target_persistence` `221/221`. Do GO pozostaje wdrożenie poprawki,
  jednorazowy reconcile dwóch historii i końcowe audit/verify; ponowny manual
  drop nie jest potrzebny.
