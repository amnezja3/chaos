# CHAOS — Project Journal

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
