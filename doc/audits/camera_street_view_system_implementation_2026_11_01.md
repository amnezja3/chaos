# Camera Street View S1–S3 i CHAOS Links — implementacja lokalna

## Uzupełnienie 02.11.2026 — systemowe testy do Super Powers włącznie

Baza: `32d0b95` + working tree. Operator rozszerzył przygotowanie do wykonania
zakresu i testów mocy. **LOCAL PASS poniższego zakresu**, bez push/deploy,
zmiany konfiguracji VPS lub ogłoszenia globalnego rollout.

Przegląd potwierdził, że produkcyjne spięcie już istnieje: nowe receipt/flow,
trwałe oznaczone kamery, kanoniczny `build_operation_instance`, produkcyjny
hook GN, projekcja deadline z `player_operations`, weryfikowany aktywator,
jednorazowe okno oraz trwały `feed` (zdjęcie + ruch + FX). Nie dodawano drugiego
silnika ani zmian działającego renderera tylko dla uzyskania nowego diffu.
Luka była w dowodach: dotychczasowe testy kamery przyspieszały operację
bezpośrednim helperem lub mockiem hooka, a nie rzeczywistą aktywacją GN.

### Wykonane zmiany

- `tests/test_camera_system_powers.py`: rzeczywiste endpointy `/hack-action`,
  `/gonna-win`, `/api/ghostnetwork/ability`, produkcyjny GN realizer i SQLite.
  Dwa konta, global ON/pilot OFF tylko w fixture, ta sama trwale oznaczona
  kamera bez skanu, mapowy flow, kontrakty desktop/terminal, nowa kompatybilna
  aplikacja, retry i izolacja grantów. Bramki grantów kamery i uprawnień GN
  są rzeczywiste; odziedziczona fixture pomija konflikt obcego terytorium,
  więc nie zalicza nowego testu tej osobnej polityki. Mock granicy czasu
  służy sprawdzeniu sekundy przed/na deadline w testach backendu.
- `tools/camera_visual_local.py --system-test`: opcjonalny scenariusz w
  istniejącej izolowanej kopii `instance/cvn-gameplay-164`; zwykły Flask,
  worker operacji, worker materiału fixture i logowanie. Lokalny main otrzymuje
  kontrolowaną profesję broker/poziom 60, moduł V1 i oznaczoną kamerę sklepu.
  Czas bazowy 180 s; brak ręcznie tworzonych grantów, aktywatorów lub okien mocy.
  Bez opcji pozostaje wcześniejszy runner. Nie uruchamiać jako usługi VPS.
- `tests/browser/camera_system_powers.js`: rzeczywisty desktop w Playwright
  MCP; normalne okno, materiał, reload, profil, consumed i nowa próba.
- Zaktualizowano journal, tablicę, sprinty i zbiorczy runbook.

### Wyniki i granice dowodów

| Próba | Wynik lokalny |
| --- | --- |
| Insider Feed aktywny przed startem, poziom 60 | 1800 → 300 s; drugie konto bez mocy nadal 1800 s |
| Insider Feed w trakcie bazowych 300 s | Po 60 s pozostałe 240 → 40 s; ponowienie aktywacji nie skraca ponownie |
| Predykcja Operacyjna i zgodna nowa aplikacja | 1800 → 300 s, poprawne provenance; wygasłe okno nie przyspiesza nowej operacji |
| Granica pobrania/zapisu | Sekundę przed terminem brak aktywatora i odmowa okna, nawet dla przedwcześnie terminalnej operacji; na terminie zweryfikowany plik i ready |
| Konta/ponowienie/odtworzenie | Cudzy receipt odrzucony; nowe operacje i trajektorie dla nowych prób; retry bez duplikatu; odtworzenie serwisu/lease zachowuje cały feed |
| Rzeczywisty UI z Insider Feed | Dwa pełne cykle po 30 s z bazowych 180 s; worker, zapis, automatyczne okno; przy 63% drugiego pobrania okna jeszcze nie było |
| Reload/close w UI | Ten sam obraz, ruch i FX po reload; jeden viewer; zamknięty pierwszy pozostaje consumed, drugi dostaje nową operację i trajektorię |
| Zdjęcie/FX | W obu próbach wylosowano tę samą fotografię; zmienił się ruch oraz grain → blocks. Nie wymagamy innego zdjęcia przy każdym losowaniu |
| Regresje | 3 testy profilu instancji, 11 ekspozycji/incydentów i 5 skryptów JS PASS |

Łącznie **17 testów backendu PASS** w celowanych przebiegach: 3 nowe
systemowe + 14 profilu/ekspozycji/incydentów. Logi lokalne:
`instance/camera-system-final-tests.log` (15),
`instance/camera-system-powers-r3.log` (mid-download PASS; drugi test miał
błąd pojemności fixture, poprawiony i zaliczony w final),
`instance/camera-prediction-tests.log` (1). Pierwsze próby ujawniły błędy
przygotowania fixture, nie regresje runtime; nie deklarujemy ich jako PASS.
JS: launch_context, runtime_config, window_dedupe, operation_delta,
target_transport. Kontrola składni nowego testu UI i `git diff --check`.

Playwright MCP: zwykłe logowanie do lokalnego `/desktop`, aktywacja mocy
przez kanoniczne API, wejście mapowe przez `/hack-action`, potem rzeczywista
launch queue i Glass Eye. Nie deklarujemy klikania wszystkich trzech menu
ani nowego odbioru PWA/mobile. 8 asercji pliku browser PASS; po nim osobno
potwierdzono ukończenie drugiej operacji, nową trajektorię, obraz i okno.
[Widoczny wynik](../../artifacts/camera-system-powers-2026-11-02.png).
W tle pozostało stare, niezależne okno historycznej fixture z wygasłym
materiałem; nie jest duplikatem testowanego feedu. Błędy połączenia w konsoli
pochodziły z celowego restartu lokalnego serwera; po jego uruchomieniu brak
nowych błędów JS ścieżki kamery. Początkowe `/login` było nieprawidłowym
adresem narzędzia (404); właściwe logowanie odbyło się przez `/`.

PROFILE HOT PATH AUDIT: nowe produkcyjne call sites: 0; w testowanych
żądaniach `profile_full_read=0`, `profile_full_write=0`, `profile_bytes=0`,
także z kontem 35 MiB. Przygotowanie konta testowego poza pomiarem korzysta
z guarded patch; runtime korzysta z projekcji identity/capabilities,
oznaczeń, operacji i inventory. Brak nowych migracji i zależności.

### Co pozostaje przed pełnym rollout

Lokalny PASS nie zastępuje testu konta robot/Insider Feed na VPS i realnego
Mapillary z docelową konfiguracją. Następny etap to zbiorczy odbiór VPS
(konto bez mocy + robot, kamera oznaczona, mapa/desktop/terminal, oba momenty
aktywacji, OFC i plik, close/relogin, camera_off/incydent) po decyzji operatora.
166.5: recovery/skala/PWA, operacyjne limity i L01/L02/retencja pozostają
otwarte. Nie zmieniono produkcyjnych czasów, reguł teleportu, camera_off,
zamrożonego prototypu, zdjęć graczy ani stanu produkcyjnych kont.

Poniższa część z 01.11 pozostaje historycznym raportem implementacji S1–S3.

Data: 01.11.2026. Baza Git: `025fd3f`. Zmiany w working tree, bez commit/push,
VPS, produkcyjnej migracji i wywołań Mapillary. Dokument zastępuje listę braków
implementacyjnych z audytu, ale nie zastępuje odbioru systemowego Sprintu 166.

## Zakres w kodzie

- `camera_visual_instance.py`: kontrakt feed v1 związany z graczem, kamerą,
  operacją, aktywatorem i instancją. Trwałe zdjęcie, motion v2 i profil wizualny.
  Wybór zdjęcia następuje raz z faktycznie dostępnej listy, także po późnym
  nadejściu materiału. Brak modulo trzech fixture zdjęć. Stary aktywny grant
  otrzymuje profil `legacy`; consumed pozostaje consumed.
- `camera_visual.py`, `run.py`: kanoniczne czasy i zapis pliku pozostają bramką
  dostępu. Stronicowanie aktywnych sesji po 64; media wyszukują konkretny receipt.
  Stary transport współrzędnych rozwiązuje wyłącznie jednoznaczny, aktualny
  skan serwerowy. Kamery świata bez materiału nie otrzymują zdjęcia pilota.
  Retry aktywatorów ma limit 32 i odroczenie 30 s, więc pełny dysk jednego gracza
  nie zatrzymuje kolejnych użytkowników. Aliasy receipt nie zajmują retry slots.
- Renderer zachowuje zaakceptowane okno i wolny ruch Béziera ping-pong.
  Nazwa pochodzi z celu, zegar pokazuje UTC. Profil określa jeden z sześciu
  scenariuszy, intensywność, okres i fazę. Wizualny SIGNAL LOST nie mutuje
  kamery ani incydentów. Niedostępność materiału ma pierwszeństwo.
  Porównywarka jest domyślnie ukryta (`CHAOS_CAMERA_DIAGNOSTICS=0`).
- `camera.runtime.config.js`: jedno źródło ustawień dla web, operations i archive;
  walidacja flag/limitów/źródła, wspólne absolutne ścieżki DB i materiałów,
  rozdzielenie ról. Web nie pobiera materiałów, worker archiwum ich nie serwuje.
- Archiwum: proces `work-loop`, watchdog dziecka 90 s, istniejący lease/fencing,
  automatyczne GC co minutę z godzinnym grace period, limit miejsca przed
  transportem, filtrowanie wycofanych zdjęć przed pobraniem miniatury. GC nie
  zatrzymuje się na pierwszych 256 zachowanych plikach. Backup/restore nie
  kopiują wygasłych/wycofanych zdjęć; restore nie cofa tombstones ani budżetu.
- Admin: konfiguracja i limity, stan kolejki, metadane materiałów, retry/expiry,
  stan procesów i identyfikator DB bez ujawniania ścieżki, audit, wycofanie,
  dozwolone retry oraz GC przez admin+CSRF. Ustawienia zmienia operator w jednym
  prywatnym pliku; panel nie tworzy drugiego źródła ustawień. Backup/restore CLI.
  Gateway ma link do publicznej strony źródeł. Token nigdy nie trafia do panelu.

## CHAOS Links

Jeden parser i handler obsługuje `focus:lat:lon`, `teleport:lat:lon`, zapis ze
spacją i opcjonalnymi nawiasami `<lat:lon>`, a także istniejące `cur:loc`.
Cyberner, Googleplex i dokumenty PTK korzystają ze wspólnego komponentu.
W PTK pojedyncze polecenie zapisane jako inline code jest aktywne; fenced code,
edytory i istniejące elementy interaktywne pozostają tekstem.

Focus czeka na iframe mapy i zachowuje ostatni cel do zdarzenia load.
Teleport nadal wywołuje `/api/blacknet/cta/teleport` po potwierdzeniu.
Operator potwierdził zachowanie obecnego kanonicznego teleportu: brak opłaty
i cooldownu dla dopuszczonej sesji. Nie dodano nowej ekonomii teleportu.
Blokada akcji w toku i krótki debounce chronią przed podwójnym wykonaniem.
Treść jest traktowana jako tekst, nigdy jako interpreter poleceń lub HTML.

## Wykonane testy

| Zakres | Dowód lokalny |
| --- | --- |
| Gameplay | 23 testy unittest PASS, następnie celowane testy zmienionych granic oraz nowy test admin/CSRF PASS |
| Kontrakt instancji | 3 testy PASS: zbiory 1/2/3/8, brak ponownego losowania, legacy, sześć profili |
| Archiwum | 13 testów PASS; dodatkowo automatyczny work-loop w osobnym procesie PASS |
| Kamery świata | Skan kamery sklepu, ATM i obiektu commercial; legacy transport, brak materiału, błędne ID — PASS |
| Ochrona incydentów | camera_shutdown 20, exposure 8, camera_incident_audit 3 — PASS |
| JavaScript | target transport, operation delta, window dedupe, role/config validation — PASS; syntax checks PASS |
| Realny desktop / Playwright MCP | 31 sprawdzeń okna PASS: drag/maximize/minimize, obraz, wolny łuk, dokładny powrót, reload, dwie karty, close/consumed, mobile |
| Resize | Ręczna zmiana obu wymiarów, responsywny HUD, dwa linki, niezmieniony motion — PASS |
| Profil i utrata materiału | Playwright: SIGNAL LOST → ONLINE, następnie REVOKED → OFFLINE, bez odtworzenia okna i bez nadpisania revocation przez FX — PASS |
| Linki / Playwright MCP | 32 sprawdzenia PASS: Cyberner, Googleplex, PTK → Focus i zatwierdzony teleport; PTK mobile, reopen, idempotencja, HTML injection, invalid coords, anonymous denial |
| Opóźniona mapa | Focus po zamknięciu i otwarciu mapy z opóźnieniem odpowiedzi 1200 ms — PASS |
| Zamrożony prototyp | 28 SHA256 zgodnych z manifestem — PASS |

Testy interfejsu używały rzeczywistego `/desktop` i API w istniejącej izolowanej
kopii `instance/cvn-gameplay-164`. Treści wiadomości/news/PTK były kontrolowanymi
odpowiedziami odczytu przez rzeczywiste renderery; teleport był rzeczywistym
zapisem lokalnej pozycji, nie stubem. Nie wysyłano wiadomości ani publikacji.
Fixture dokumentu poprawiono tak, aby zachowywał nagłówki generacji sesji.
Fixture profilu czeka na pełny cykl zakłóceń i kończy przechwytywanie dopiero
po obsłudze trwających żądań; nie zmienia zapisanych grantów ani kamery świata.
Negatywny test współrzędnych respektuje istniejący HTTP 404 `unknown_target`.

Konsola: oczekiwane 409 dla reopen, 404 dla błędnego teleportu; lokalny backup
ma również ostrzeżenia niezależnych warstw mapy (ghostnetwork/incidents/npc,
timeout/deferred). Nie deklarujemy PASS całej konsoli ani tych systemów.

## Migracja i deployment

Procedura: [runbook S1–S3](../runbooks/camera_street_view_system_s1_s3.md).
Trzy nowe tabele: `camera_visual_runtime`, `camera_visual_admin_audit`,
`camera_visual_activation_retry`; idempotentny CREATE IF NOT EXISTS. Łącznie
siedem tabel kamer wraz z istniejącymi czterema. Bez kasowania lub resetu sesji,
plików graczy, uprawnień i snapshotu prototypu. Nie dodano zależności Python;
pozostaje istniejący Pillow. Instalacja przeglądarki Playwright dotyczy wyłącznie
lokalnego narzędzia testowego.

## Granice przekazania do 166

Nie wykonano restartu PM2/reboot VPS ani testów z produkcyjnymi sekretami.
Nie wykonano szerokiej macierzy kont, lokalizacji, aplikacji, PWA i obciążenia.
Insider Feed i Operational Prediction używają istniejącej rodziny
`operation_speed`; testy realizera i 300/1800 s są lokalne. Robot z aktywowaną
mocą i rzeczywistym czasem gry pozostaje odbiorem 166.

Kolejka materiałów ma limit 128, maksymalnie dwie próby i TTL 900 s. Odrzucony
przez limit popyt daje niedostępność materiału, nie fałszywy obraz ani sukces
API. Nowe hakowanie może ponowić pozyskanie. Retencja i publikacja Mapillary
nadal wymagają zatwierdzonych L01/L02; kod nie ustanawia nowych praw.
Limity transferu są konserwatywnymi rezerwacjami, nie pomiarem faktury dostawcy.
Backup archiwum obejmuje do 1000 rekordów na kontrolowany zakres; większy zbiór
wymaga operatorskiego planu backupu, nie cichego obcięcia danych.
