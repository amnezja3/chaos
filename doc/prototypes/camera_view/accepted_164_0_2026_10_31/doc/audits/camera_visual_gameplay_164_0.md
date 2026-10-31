# CVN 164.0 — działający lokalny pilot w gameplayu

Data: 2026-10-31. Baza kodu: `3556abd` + lokalne zmiany, bez commitu/pushu.
Status: **implementacja lokalna i testy pilota; wygląd do odbioru operatora**.
[Tablica pracy](../plans/camera_visual_pilot_164_0_board.md).

## Co działa

Konto `main`, istniejący Glass Eye (`admin_seed_camera_stream_v1`), Kamera sklepu
`48.864173348628704, 2.330499567661377`. Właściwa aplikacja Flask i `/desktop`,
istniejąca kolejka uruchomień, referencja `progressbar_random`, Centrum Operacji,
kanoniczny dysk gracza i standardowy renderer okna. Bez osobnego demonstratora.

Sukces zapisuje trwały wynik i jedną operację `camera_stream`; jej początek
przypada po 5 s SESSION CLOSE. Pobieranie trwa 1800 s. Istniejący runtime operacji
kończy je i finalizuje zwykłe zasoby. Dodatkowy aktywator ma deterministyczne ID,
checksum i treść wiążącą operację, instancję oraz cel. Zapis do
`player_data_files` i obciążenie `player_storage` są atomowe; odczyt kontrolny
jest warunkiem udostępnienia podglądu. Brak miejsca, uszkodzenie, anulowanie,
brak uprawnień lub nierozliczona płatność nie dają dostępu.

Failure jest trwałym wynikiem i nie tworzy operacji ani aktywatora. Referencja
zostaje z widocznym komunikatem końcowym. Reload przywraca końcowy stan bez
ponawiania działania aplikacji. Jawne zamknięcie zostaje zapamiętane.

Podgląd jest nową instancją `interface: window`, tworzoną przez
`prepareApplicationRenderWindow`/`finishApplicationRenderWindow`, z normalnym
taskbarem, przeciąganiem i kontrolkami Ghost Systemu. Serwerowa dzierżawa
dopuszcza jeden dokument; UI usuwa okno przed końcem dzierżawy bez odnowienia.
Ponowne otwarcie jest dostępne w Centrum Operacji, bez nowego pobierania.
Obrazy pobierane autoryzowanym fetch z generacją sesji, cache `no-store`.

Mechanizm rozpoznaje zgodny kontrakt `camera_stream`, nie nazwę/id aplikacji.
Test wygenerowanego wydania z inną nazwą i ID potwierdza dołączenie do pilota.
Zakres aktywacji ograniczony flagą do wskazanego konta i jednej kamery.

## Zmiany techniczne

- `camera_visual.py`: wąski koordynator, kanoniczny cel legacy, wynik, zapis,
  weryfikacja aktywatora i dzierżawa. Tabela `camera_visual_sessions` i indeks
  tworzone przez `init_db`, nigdy przez endpoint snapshotu.
- `run.py`: wejścia istniejących `/hack-action` i `/gonna-win`, finalizacja
  przez `process_operation_runtime_tick`, endpointy stanu/okna/mediów.
- `static/js/terminal.js`: przekazanie celu przypisanego do launch receipt
  zamiast starego celu z toolbara; serwerowy deadline SESSION CLOSE;
  postęp aktywatora i powrót do podglądu w Centrum Operacji.
- `static/js/camera_visual.js`, CSS i `linux.html`: integracja pulpitu,
  odzyskiwanie stanu, standardowe okno, trzy kadry i NO SIGNAL, PL/EN.
- `database.py`: opcjonalny `CHAOS_DB_PATH` umożliwia izolowany lokalny start;
  domyślna ścieżka pozostaje `data/game.sqlite3`.

## Dowody lokalne

- 10 testów `test_camera_visual_gameplay.py` PASS (9 testów pakietu i osobno
  dodany test wygenerowanej aplikacji): rzeczywiste trasy, profil 35 MiB bez
  pełnego odczytu, success/failure, 1800 s i 50%, retry/konkurencja, brak miejsca,
  korupcja, izolacja kont, media, CSRF, aliasy i rollback transakcji nadrzędnej.
- 20 testów `test_camera_shutdown_contract.py` PASS.
- Trzy regresje JS: `test_camera_window_dedupe`, `test_camera_target_transport`,
  `test_camera_operation_delta` PASS. Kontrola składni JS i diff PASS.
- Playwright MCP na realnym `/desktop`: normalne logowanie `main`; start przez
  rzeczywisty endpoint mapy `/hack-action`, dalej istniejąca launch queue i UI
  aplikacji. Nie deklarujemy osobnego testu klikania menu na mapie.
- Sukces → widoczny SESSION CLOSE → referencja znika → postęp w Centrum
  Operacji → realny worker zapisuje aktywator → automatyczny nowy viewer.
  Baza po teście: jedna operacja pilota `timeout`, jeden aktywator; osobne
  wyniki porażki nie utworzyły dodatkowych operacji ani aktywatorów.
- Porażkę wywołano przez `requires_off` aktywnego zabezpieczenia w **lokalnej
  kopii** zainstalowanej aplikacji. Serwer rzeczywiście odrzucił wykonanie;
  przywrócono oryginalny kontrakt po teście. Referencja została otwarta po 5 s,
  bez auto-close i viewera; reload odtworzył wynik.
- `tests/browser/camera_visual_gameplay_164_0.js`: 15 sprawdzeń PASS — standard
  window, brak referencji, drag, max/min/taskbar, trzy autoryzowane obrazy,
  close/reopen, reload, dwie karty, EN i bounds telefonu 390×844.
- Osobno: zwykły logout i ponowne logowanie przywróciły tę samą instancję;
  pełny restart procesu gry i ponowne logowanie również zachowały instance_id.
  kontrolowane przerwanie żądania medium pokazało NO SIGNAL i powrót obrazu.
  Konsola końcowego normalnego przebiegu: 0 błędów. Celowo przerwane medium
  dało oczekiwany błąd sieci w tym konkretnym teście.

Szersza suita `test_creator_payments.py` nie ma PASS: w niezmienionej wersji
17/18 przypadków zatrzymuje przygotowanie konta `admin` przez create-only
`save_profile`. Ten sam błąd potwierdzono na oryginalnych `run.py`/`database.py`
z HEAD `3556abd`, uruchamiając `test_success_retry_and_fallback_admin`.
Diagnostyczne pominięcie ponownego seeding admina ujawniło dalsze niezgodności
macierzy starych receptur gracza; tę próbną zmianę testu cofnięto. Nie deklarujemy
PASS całej macierzy Creator. Pilot ma własny test wygenerowanej aplikacji i
transakcji nadrzędnej; pełne rozszerzenie zgodności pozostaje w 165.

W przeglądarce przyspieszono **wyłącznie zapisane terminy operacji testowej
w izolowanej bazie** do środka i końca pobierania. Nie czekano pełnych 30 minut
zegara ściennego. Kontrakt pozostaje 1800 s, sprawdzony testami backendu;
nie dodano produkcyjnego skrótu ani endpointu zmiany zegara/wyniku.

Zrzuty:

- [SESSION CLOSE](../../artifacts/cvn-164-gameplay-session-close.png)
- [Pobieranie](../../artifacts/cvn-164-gameplay-download.png)
- [Podgląd na prawdziwym pulpicie](../../artifacts/cvn-164-gameplay-viewer.png)
- [Failure](../../artifacts/cvn-164-gameplay-failure.png)
- [Failure po reload](../../artifacts/cvn-164-gameplay-failure-restored.png)
- [Telefon EN](../../artifacts/cvn-164-gameplay-mobile-en.png)
- [NO SIGNAL](../../artifacts/cvn-164-gameplay-no-signal.png)

## Uruchomienie do odbioru

```powershell
.venv/Scripts/python.exe tools/camera_visual_local.py
```

Adres `http://127.0.0.1:8998`, zwykłe logowanie gry. Launcher korzysta wyłącznie
z `instance/cvn-gameplay-164/data/game.sqlite3`, uruchamia prawdziwy Flask i tick
operacji, a zmienne ścieżki zapisu utrzymuje wewnątrz tego katalogu. Nie przywraca
backupu przy kolejnym starcie. Dane lokalnego dostępu zapisano w ignorowanym
`instance/cvn-gameplay-164/LOCAL_ACCESS.txt`; nie są danymi produkcyjnymi.
Testowa kopia zawiera ukończony przypadek do szybkiego obejrzenia.

Flagi: `CHAOS_CAMERA_VISUAL_PILOT=1`, `CHAOS_CAMERA_VISUAL_PILOT_USER=main`.
Launcher ustawia je lokalnie. Poza nim pilot jest domyślnie wyłączony.
Wyłączenie flagi blokuje serwowanie CVN; nie usuwa historii operacji/plików.

Źródłowy backup zachowany. `PRAGMA quick_check` kopii: `ok`.
Nie uruchamiano VPS, pozyskiwania Mapillary, starych kolejek ani zdjęć graczy.
Materiały są jawnie syntetyczne; nie dowodzą wyglądu rzeczywistej lokalizacji.
Operator zaakceptował pierwszy wygląd jako bazę. Rozszerzenie 164.1–165 pozostaje odrębnym etapem.

## Korekta prezentacji: ruchomy podgląd

Trzy istniejące zasoby są dekodowane przez chronione endpointy po aktywacji.
Viewport pokazuje najwyżej ćwierć obrazu (200% szerokości i wysokości, cover).
Patrol kadru trwa 96 s w jedną stronę; zdjęcia zmieniają się co 24 s z 2 s
przenikaniem. Nakładki dodają szum, linie skanowania, winietę i okresowe
zakłócenia. Minimalizacja zatrzymuje animacje i zmianę zdjęć; zamknięcie
zwalnia timer, żądania i URL-e blob. Preferencja reduced-motion wyłącza ruch
i animowane zakłócenia.

Okno i taskbar wskazują `Paris · 48.86417, 2.33050`. Znak MapiFi jest lokalnym
znakiem SVG/tekstem; link „Panel kamery” otwiera w tym samym oknie współrzędne
i opis syntetycznego materiału. Nie ma integracji z zewnętrznym dostawcą.
Usunięto tytuł GLASS EYE oraz przyciski pór dnia. Kontrakt aktywacji nie zmienił się.

Walidacja pakietu: Playwright MCP na lokalnym Flask `/desktop`, zwykły login
`main`, istniejąca zweryfikowana aktywacja testowa. 22 sprawdzenia PASS:
trzy obrazy 1672×941, kadr 2×, rzeczywista zmiana transformacji, pełny cykl
1→2→0 bez przyspieszania zegara, logo/panel, standardowy drag/max/min/taskbar,
close/reopen/reload, dwie karty bez duplikatu, EN i mobile. Konsola: 0 błędów.
Trzy regresje JS (window_dedupe, target_transport, operation_delta): PASS.
Zrzuty: `artifacts/cvn-164-camera-motion-desktop.png`,
`artifacts/cvn-164-camera-motion-panel.png`, `artifacts/cvn-164-camera-motion-mobile.png`.
Backend niezmieniony w tym pakiecie; jego wcześniejsze wyniki są opisane powyżej.

## Nagłówek Camera Network i HUD transmisji

Obramowania okna i obrazu mają turkus z przezroczystością 30%, a nagłówek
przygaszone tło i linię 20%. Nowa ikona pochodzi z built-in image_gen:
`static/images/camera_visual/camera-network-v1.png`; pełny prompt i metadane
w sąsiednim `generation.json`. Zasób skopiowano do repo bez modyfikacji oryginału.

Współrzędne `48.86417:2.33050` są linkiem do istniejącego map focus bridge.
Fokus używa pełnej precyzji kanonicznego celu; nie zmienia pozycji gracza.
HUD pokazuje ONLINE dopiero po dekodowaniu obrazu, REC i zegar czasu Paryża.
Co 3 s dochodzi kolejny wiersz logu, maksymalnie trzy w DOM. Logi są dekoracją
symulacji, nie telemetrią rzeczywistej kamery; wyjaśnia to panel. Nie ma zapisu
filmu. Timer zatrzymuje pracę przy minimalizacji i jest zwalniany przy zamknięciu.
Dotychczasowe kadrowanie, patrol, przenikanie i efekty pozostają aktywne.

Walidacja: Playwright MCP na prawdziwym `/desktop`: 27 sprawdzeń PASS,
obejmujących ikonę, `lat:lon`, ONLINE/REC, zmieniający się zegar, ograniczone
logi i wcześniejszy cykl/lifecycle okna. Osobny test
`tests/browser/camera_visual_map_focus_164_0.js`: PASS, znacznik dokładnie
48.864173348628704:2.330499567661377, środek mapy w tolerancji 0.0001°.
Test czeka na zakończenie animacji fokusu. Konsola: 0 błędów (mapa zgłaszała
ostrzeżenia). Trzy regresje JS PASS. Backend w tym pakiecie niezmieniony.
Zrzuty: `artifacts/cvn-164-camera-hud-desktop.png`,
`artifacts/cvn-164-camera-hud-mobile.png`, `artifacts/cvn-164-camera-map-focus.png`.

## Stabilność, linki v1, trwały ruch i resize

Log operatora z 12:18 wskazał `database is locked` w BEGIN IMMEDIATE endpointu
window oraz innych zapisach gry. Poprzedni lease 12 s wygasał przed końcem
15-sekundowego busy_timeout SQLite; callback usuwał DOM, a następny claim
tworzył nowe okno i pobierał ponownie obrazy. Naprawa rozdziela te cykle:
lease 60 s, odnowienie 20 s przed końcem, read-only heartbeat w pozostałym
czasie. Przy wygaśnięciu wyłączana jest prezentacja feedu (RECONNECTING),
ale DOM i zdekodowane obrazy pozostają; powrót dostępu wznawia tę instancję.
Przejściowa blokada window zwraca 503/Retry-After, frontend ponawia po 5 s.
Pagehide/ukrycie dokumentu zwalnia lease bez zamknięcia trwałego podglądu.
Worker nie otwiera transakcji zapisu dla już zapisanego aktywatora.

Nie ustalono posiadacza pierwotnej długiej blokady całej bazy. Naprawa usuwa
zbędną presję zapisów pilota i restartowanie podglądu przy takim zdarzeniu;
nie jest twierdzeniem o naprawieniu każdej przyczyny blokad innych endpointów.

`motion` w payloadzie grantu zawiera wersję, skalę 2, tryb ping-pong oraz
trzy tory: start/end w zakresie 0–50% i czas jednokierunkowy 48–112 s.
Losowanie następuje raz dla konkretnego grantu gracza. Ponowienie wyniku
zwraca zapisany wariant, inny gracz otrzymuje nowy. Stare granty są uzupełniane
jednorazowo przy claim, nie przy snapshot/media. CSS alternate odwraca ten
sam tor; faza startowa wynika z ready_at. Resize nie losuje toru ponownie.

Linki: [kontrakt CHAOS v1](../architecture/chaos_links_v1.md). Cztery warianty
przechodzą przez istniejące handlery terminala; teleport zachowuje potwierdzenie.
Panel i metadane obrazu używają wspólnych badge’ów. Okno ma natywny `resize:both`
jak Centrum Operacji; container queries przestawiają HUD według szerokości okna.
Przy bardzo małym oknie treść panelu może przewijać się wewnątrz aplikacji.

Walidacja: 15 testów backendu PASS (w tym realny konkurencyjny writer lock,
lease takeover/release, zapis motion i drugi gracz), 3 regresje JS PASS.
Playwright: 27 sprawdzeń gameplayu PASS; osobno wymuszone 503 dłużej niż dawny
lease — recovery w tym samym DOM, 0 pobrań obrazów; natywny drag resize do
463×523, responsywne linki/HUD i zachowanie motion; focus lat:lon i cur:loc;
oba warianty teleportu dochodzą do dialogu, anulowanie wysyła 0 teleportów;
nieprawidłowe linki są odrzucane. Błędy HTTP 503 podczas fault injection są
oczekiwane. Po usunięciu fault injection konsola bez błędów.
Zrzut do odbioru: `artifacts/cvn-164-resize-links.png`.

## Korekta: jeden obraz na jeden podgląd (motion v2)

Ta sekcja zastępuje wcześniejszy kontrakt rotacji trzech zdjęć. Podgląd zapisuje
jedno `image` (0–2), start, control, end i czas 180–300 s w jedną stronę.
Ruch jest krzywą kwadratową Béziera z niewielkim odchyleniem prostopadłym do
kierunku przejazdu. Łagodny rozbieg i hamowanie wynikają z parametryzacji
cosinusowej, próbkowanej w 61 keyframe’ach. Alternate odwraca dokładnie tę samą
ścieżkę; pełna pętla trwa 360–600 s. Wszystkie punkty pozostają wewnątrz
dozwolonego kadru. Resize nie zmienia wyboru źródła ani parametrów trasy.

Frontend tworzy jeden element zdjęcia i pobiera tylko wybrane źródło. Nie ma
timera rotacji ani automatycznego przejścia do innego zdjęcia. Wybór pozostaje
przy reloadzie/reopen; inny gracz otrzymuje własne losowanie. Granty motion v1
są uaktualniane raz przy claim. Nowy skrypt odrzuca stary kontrakt przed
utworzeniem okna, aby mieszane wersje serwera/static nie tworzyły częściowych
instancji. Do działania migracji wymagany jest restart lokalnego procesu Flask.

Walidacja motion v2: 15 testów backendu PASS, trzy regresje JS PASS.
Playwright MCP na lokalnym Flask (port testowy 8999): 29 sprawdzeń PASS,
w tym jeden obraz w DOM, brak przełączenia po 26 s, czas 180–300 s, krzywizna
i równość pozycji podczas jazdy w przód/wstecz. Pełny wielominutowy cykl
zweryfikowano przez seek czasu animacji, nie czekanie 6–10 minut. Reload
zachowuje źródło. Osobny test fault injection: ten sam DOM, zero ponownych
pobrań obrazu po odzyskaniu dostępu. Zwykła konsola bez błędów; trzy 503
w teście awarii są celowo wymuszone.

## Systemowe frazy akcji i stopka MapiFi

Kamera pokazuje wyłącznie Focus i Teleport, na górze, ze wspólnej fabryki
ChaosLinks i dedykowanymi SVG. Współrzędne na ekranie mają cztery miejsca
dziesiętne, akcje zachowują pełną precyzję. cur:loc usunięto z UI kamery.
Stała stopka podaje MapiFi, typ syntetyczny, autorstwo AI, źródło CHAOS/Paris
i „Licencja: nie przypisano”; nie dopisuje praw ani autora fotografii.
„O materiale” rozwija krótki opis pochodzenia i symulacji.

Warstwa tekstowa zamienia focus:lat:lon i teleport:lat:lon na aktywne badge’e
w standardowych oknach. Pomija edytory, code/pre, istniejące linki/przyciski.
Obserwuje tylko nowe/zmienione poddrzewa; nie korzysta z profilu ani backendu.
Google Plex News ma article i osobny CTA, by uniknąć linku wewnątrz button.
Kontrakt: `doc/architecture/chaos_links_v1.md` (rozszerzenie v2).

Playwright MCP na rzeczywistym lokalnym desktopie, port 9000: 29 sprawdzeń
kamery PASS, resize 463×523 PASS, powrót mobile→desktop zachowuje resize.
Poprawiono scoped CSS dla inline resize:none pozostawianego przez mobilny shell.
Test `chaos_text_links.js` używa fixture wyłącznie odczytu API wiadomości/news:
rzeczywiste renderery Cybernera i Google Plexa tworzą oba linki; fokus mapy
i dialog teleportu PASS, edytowalny tekst/kod/HTML literalny nie są wykonywane,
dynamiczne zmiany i powtórne enhance nie tworzą duplikatów. Nie wysyłano żadnych
wiadomości ani publikacji. Test kamery potwierdza 0 teleportów po anulowaniu.
Konsola 0 błędów. Google Plex News PL/EN i trzy regresje kamer JS PASS.

Ograniczenie walidacji: test_googleplex_search_layout.js nadal wymaga regexem
literalnego `item.description || 'Brak opisu.'`, podczas gdy kod używa tłumaczeń.
Identyczną porażkę odtworzono z niezmienionym terminal.js z HEAD; poza tym zakresem.
Zrzuty: `artifacts/cvn-164-mapifi-window.png`, `artifacts/cvn-164-mapifi-mobile.png`.
# 2026-10-31 — dodatkowa walidacja zestawu zakłóceń P20

Operator zaakceptował dotychczasowy wygląd i show. Dodano sześć SVG opisanych
w `static/images/camera_visual/effects/README.md`, podpiętych do właściwego
okna. CSS/JS cache: `164-0-7`. Brak zmian backendu lub zapisanej ścieżki ruchu.

Playwright MCP, lokalna gra na porcie 9001, izolowana kopia main:

- `camera_visual_effects_164_0.js`: 12 kontroli PASS, w tym pobranie/dekodowanie
  sześciu assetów, widoczność warstw, reduced-motion, minimalizacja, tożsamość
  DOM i zdjęcia. Fazy okresowych efektów przewinięto przez CSS Animation API;
  nie oczekiwano pełnych 49/67/83 sekund każdego cyklu.
- `camera_visual_gameplay_164_0.js`: 29 kontroli PASS.
- `camera_visual_resize_164_0.js`: PASS, resize 463×523, HUD/linki w granicach,
  bez zmiany charakterystyki ruchu.
- `camera_visual_reconnect_164_0.js`: PASS, dropout w RECONNECTING,
  powrót bez odtwarzania okna i bez ponownego pobrania zdjęcia.
- Zrzuty sześciu wariantów: `artifacts/cvn-164-effects-*.png`; wizualnie
  sprawdzono chroma oraz dropout. Po regresji konsola bez błędów; trzy 503
  pochodziły z celowego testu awarii. Nie testowano ponownie backendu ani
  całego czasu pobrania aktywatora, ponieważ pakiet zmienia wyłącznie prezentację.

