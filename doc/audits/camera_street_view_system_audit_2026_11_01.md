# Camera Street View — audyt przejścia z pilota do systemu

Data: 01.11.2026. Baza kodu: `025fd3f`. Audyt statyczny kodu, testów,
konfiguracji i dotychczasowych dowodów; bez nowych testów, zmian runtime,
wywołań Mapillary, odczytu VPS, pushu i wdrożenia. Lokalne zmiany zastane:
journal, tablica i runbook po odbiorze VPS oraz plik diagnostyki Playwright.
Ostatni potwierdzony stan serwera pochodzi z odbioru operatora, nie z tej sesji.

## Wniosek i aktualny punkt realizacji

Pilot jednej kamery ma PASS operatora. Istnieje rzeczywisty, trwały lifecycle
i zalążek integracji globalnej; nie jest to już wyłącznie demonstrator.
Nie ma jednak kompletnego systemowego generatora instancji ani odebranego
wdrożenia dla wszystkich kamer i użytkowników. Samo STREET_VIEW=1 nie zamyka zakresu.

**Najbliższa praca: połączyć istniejący lifecycle, wybór materiału, tor oraz
zakłócenia/offline w jeden utrwalany kontrakt instancji i podłączyć go do
wszystkich kanonicznych kamer/aplikacji. Dopiero potem szeroka macierz odbioru,
w tym Insider Feed.** Nie budować kolejnego prototypu i nie przeprojektowywać
zaakceptowanego okna.

Statusy: **systemowe** = kod ogólny, nie automatycznie live PASS;
**pilot PASS** = potwierdzony przypadek main/Paryż; **częściowe** = mechanizm
istnieje, lecz nie pokrywa całego kontraktu; **brak** = nie znaleziono implementacji.

## Macierz całej ścieżki

| Etap | Stan i dowód | Co pozostaje |
| --- | --- | --- |
| Kamera świata przy sklepie/ATM/innych POI | Systemowe podstawy: `run.py` generuje `camera_marker`, zapis skanu; `response_network/camera_contract.py` nadaje stabilne camera_id i weryfikuje obserwacje | Odbiór wszystkich ścieżek mapy i istniejących kamer legacy; nie zakładać, że każda historyczna kamera ma scan_id |
| Wybór aplikacji i hakowanie | `camera_visual.py`: launch/app/eligible/result, kontrakt camera_stream zamiast nazwy Glass Eye; normalizacja aplikacji i kanoniczny cel | Integracja globalna za flagą, VPS sprawdzony tylko na main/Glass Eye; pełne E2E publikacja/instalacja/mapa dla interfejsów i zgodnych wydań historycznych |
| Success/failure | Trwały wynik, dedupe receipt, SESSION CLOSE 5 s; failure bez operacji i viewera. Testy lokalne; sukces pilot PASS | Systemowa regresja wszystkich adapterów aplikacji, failure i retry bez nowych kosztów |
| Wpływ na incydenty | Normalny build_operation_instance, runtime ryzyka; osobne camera_shutdown/camera_exposure. Lokalne regresje 20+8+3 PASS | Nie scalać stream z shutdown; test wzajemnego działania na wielu kamerach/kontach. Offline wizualne nie wyłącza kamery świata |
| Generowanie/pobieranie pliku | Kanoniczna operacja i finalizacja camera_dump, dodatkowy aktywator na dysku gracza, checksum i kontrola wolnego miejsca | Zapis aktywatora zależy od existing territory workera; wdrożyć wspólną konfigurację i diagnostykę brakującego finalizatora |
| Czas + Super Powers | project czyta daty operacji; build_operation_instance i późniejsza akceleracja korzystają z realizerów. Lokalne 300/1800 s i insider_feed | VPS: dwa przebiegi zwykłych 30 min PASS. Insider Feed/robot i inne czasy dopiero po integracji systemowej, bez sztucznego skracania produkcji |
| Jednorazowe otwarcie | Backend wymaga stanu terminalnego i zweryfikowanego aktywatora; claim/lease, standardowe okno. Pilot PASS | Odbiór skali, wielu równoległych kamer, spójności web/worker po restarcie |
| Wybór zdjęcia | Utrwalane image_id przy claim; jeden obraz na instancję. Archiwum wspólne, grant osobny | Losowanie nadal bazuje na indeksie trzech fixture zdjęć i modulo liczby obrazów; uogólnić na rzeczywistą listę dopuszczonych materiałów |
| Trajektoria | generate_motion v2: losowy start/end/control, Bézier, 180–300 s w jedną stronę, dokładny reverse; zapis per grant i inny wektor niż poprzedni | Włączyć do jednego wersjonowanego kontraktu feedu; nie regenerować po reconnect; test dla różnych proporcji zdjęć |
| Zakłócenia/offline | Sześć assetów i zaakceptowany wygląd; w normalnym oknie stałe warstwy i okresy CSS. NO SIGNAL dla niedostępności mediów | **Brak losowanego, zapisanego wariantu zakłóceń/offline per instancja.** Porównywarka to narzędzie odbioru, nie generator gameplayu |
| Zamknięcie | close potwierdzane backendowo, viewer_closed i consumed; reopen odrzucone | Pilot API + brak powrotu po zamknięciu PASS; utrzymać przy globalizacji i zmianie schematu |
| Kolejny feed | Nowe hakowanie po close → nowa operacja, download, instancja i motion | Drugi przebieg 30 min pilot PASS; pełny nowy zestaw foto+motion+FX/offline jeszcze nie istnieje |

## Co jest rzeczywiście zintegrowane

- `camera_visual.py` korzysta z wąskich target/position/capability/inventory/
  operation stores. Brak potrzeby nowego pełnego profilu gracza.
- `enabled()` obsługuje globalny STREET_VIEW lub PILOT/PILOT_USER. Globalny
  `target()` weryfikuje camera_id/scan_id przez CameraContractStore. Lokalny
  test `test_observed_world_camera_uses_canonical_identity` obejmuje sklep,
  ATM i commercial oraz odrzuca podmieniony identyfikator.
- `run.py` podłącza launch i wynik aplikacji, stan/claim/media/admin/sources.
  Gotowość archiwum nie zastępuje sukcesu hakowania lub aktywatora.
- `camera_visual_source.py`: HTTPS, kontrolowane DNS/hosty, bez redirect/retry,
  jedna strona do 30 kandydatów, 100 m, kierunek/sekwencja, do 3 miniatur,
  brak oryginałów, WebP do 960x540, EXIF usunięty, limity bajtów/pikseli.
- `camera_visual_archive.py`: wspólne materiały, osobne grants, trwała kolejka,
  lease/fencing, limity przed HTTP, max 2 próby, TTL 900 s, negatywny cache,
  retencja, tombstones, checksum, GC i addytywny backup/restore.
- `tools/camera_archive.py`: oddzielny bounded worker z limitem procesu 90 s,
  migracja/status/withdraw/GC/backup/restore. To kod narzędzi operacyjnych,
  nie dowód automatycznego utrzymania na VPS.
- Ghost UI: natywne okno, resize, Focus/Teleport, MapiFi, HUD/REC/logi,
  pojedynczy obraz, recovery lease bez odtwarzania DOM przy krótkiej awarii,
  późny materiał i wycofanie. Lokalny Playwright i pilot obrazu mają dowody.

## Konkretne ograniczenia pilota i luki

### A. Tożsamość i instancja

1. LAT/LNG/TARGET_KEY, legacy fallback do historii jednej kamery i nazwa
   Glass Eye.activation pozostają w serwisie. Ścieżka globalna istnieje,
   ale przypadki historyczne poza Paryżem nie otrzymują ogólnego odpowiednika
   fallbacku. Potrzebna jawna kompatybilność, nie zaufanie do współrzędnych klienta.
2. `generate_motion()` wybiera `secrets.randbelow(len(IMAGES))`, a claim
   wiąże `manifest.images[motion.image % len(images)]`. Przy dwóch materiałach
   daje to prawdopodobieństwa 2/3 i 1/3. Nie jest to równomierny wybór ze zbioru.
   Indeks fixture nie powinien określać zdjęcia dostawcy ani API mediów.
3. Brak payloadu wersjonującego wspólnie image choice, motion i effect/state.
   Trzeba określić moment jednorazowego losowania, także gdy materiał przychodzi
   po otwarciu, oraz kompatybilność istniejących niezamkniętych grantów.
4. Różne instancje mogą legalnie wylosować to samo zdjęcie i wariant. Niezależność
   nie oznacza globalnej unikalności. Zachować wymaganie nowego toru przy
   kolejnym feedzie; nie obiecywać wszystkich możliwych kombinacji bez powtórzeń.

### B. Prezentacja i znaczenie offline

1. Warstwy grain/scan/tracking/chroma/blocks nakładane są wszystkim; okresy
   49/67/83 s są wspólne. Dropout ma asset i scenariusz porównywarki, nie
   utrwalany losowy wariant całej instancji. Brak zapisanych intensywności/faz.
2. Konieczne trzy niezależne osie: uprawnienie/lifecycle, techniczny stan
   materiału, wylosowany scenariusz prezentacji. Opcjonalny stan kamery świata
   odczytywać z istniejącej mechaniki, nigdy zapisywać go przez wizualny efekt.
3. Wylosowane offline jest prezentacją feedu i nie może naliczać shutdown,
   zmieniać incydentów, anulować nagrody ani omijać aktywatora. Awaria API,
   wycofanie, brak pokrycia i lease utracony mają własne przyczyny oraz
   pierwszeństwo przed wylosowanym obrazem online.
   W `CameraVisual.project()`/rendererze nie ma odczytu shutdown_windows
   sterującego stanem obrazu. Nie zakładać, że obecne OFFLINE odwzorowuje
   rzeczywiste camera_off. Przy integracji ustalić prezentację zgodną z istniejącą
   regułą dostępu i czasu shutdown, bez dopisywania nowych skutków incydentowych.
4. Renderer hardcoduje `Europe/Paris`, napis PARIS i fallback źródła CHAOS/Paris;
   poza pilotem tytuł jest ogólnym „Kamera”. Uogólnić lokalizację/czas/atrybucję.
5. „Porównaj 6 zakłóceń” jest dostępne w zwykłym oknie. Zachować jako narzędzie
   testowe/administracyjne, nie główny wybór scenariusza przez gracza.
6. Wiele stanów archiwum sprowadza się do NO SIGNAL/OFFLINE; pełny słownik
   przyczyn z planu 165.2 nie jest wyrenderowany. PROCESSING nie jest osobnym
   utrwalonym stanem workera. Nie dopisywać sztucznych stanów wyłącznie dla tabeli.

### C. Wdrożenie, niezawodność i skala

1. VPS pilot pozyskał zdjęcia ręcznie przez enqueue + work-once. Istnieje
   automatyczne enqueue po sukcesie, ale cykliczny proces archiwum nie został
   odebrany w produkcyjnym przepływie nowych kamer. Worker startuje raz/2 min
   z domyślnym OFF; globalny rollout potrzebuje potwierdzonej przepustowości.
2. Web i territory worker wymagają zgodnych flag gameplayu oraz tego samego
   DB. Pominięcie territory workera spowodowało realne save_pending przez brak
   aktywatora. Poprawiono ręcznie konfigurację testu i runbook, **nie ma jeszcze
   kompletnego, trwałego profilu systemowego w ecosystemach**.
3. Domyślne limity 10 aktywnych archiwów, 100 żądań/100 MiB rezerwacji,
   128 oczekujących i jeden lease są bezpiecznikami pilota, nie planem pojemności.
   Snapshot zwraca 64 sesje; retry aktywatorów bierze 32 najstarsze brakujące
   pliki. Zweryfikować utratę widoczności/starvation przy wielu kontach i pełnych
   dyskach, dodać indeksy/paginację/fairness tam, gdzie potwierdzi to pomiar.
4. Polling 2 s na widoczną kartę, claim/renew i manifest/atrybucja wymagają
   pomiaru kosztu. Minimalizacja pauzuje animacje, ale globalny polling trwa;
   to nie spełnia wprost dawnej obietnicy zatrzymania wszystkich odpytań.
5. GC jest ręcznym CLI, nie automatycznym harmonogramem retencji. Wygaśnięcie
   odczytu nie usuwa fizycznego pliku. Restore zachowuje tombstones/budżety,
   ale cykl backupów i usuwania ich materiałów nie jest odebrany operacyjnie.
6. Budżet liczy konserwatywne rezerwacje, nie pomiar rzeczywistego transferu;
   limit aktywnych archiwów nie jest limitem nowych archiwów/dobę. Brakuje
   pełnych telemetry/heartbeat/SLO i skalowanego storage quota z dawnych planów.
7. Wycofanie blokuje publikację; worker filtruje tombstone przed publikacją.
   Nie jest to dowód zapobiegania samemu ponownemu HTTP dla wycofanego image_id.
   Odebrać filtrowanie przed download, GC referencji i brak resurrection.
8. Jeden CDN host potwierdzono w Warszawie. Globalne lokalizacje/przyszłe URL
   mogą używać innych hostów; utrzymać walidację, nie zastępować jej wildcardem.

### D. Administracja, źródła i prawa

Panel jest ograniczonym read-only wykazem 50 archiwów/7 dni budżetu, czterech
flag i obecności tokena. Brakuje pełnych ustawień/profilu przetwarzania,
metryk, inspekcji referencji, audytowanych retry/withdraw oraz osobnego stanu
L01/L02. CLI istnieje; zdecydować świadomie, które operacje pozostają CLI,
a które są wymagane w docelowym panelu — nie oznaczać całego 165.3 jako DONE.

Publiczne `/camera-sources` PL/EN istnieje i ma live HTTP PASS. Nie znaleziono
odnośnika do niego w szablonach bramki; nie zaliczono wymaganej integracji
gatewaya. Strona opisuje adapter jako przygotowany/testowy; docelowy tekst
musi odpowiadać faktycznej publikacji. MapiFi branding jest odebrany; nazwa
Mapillary w stopce nie zamyka wymogu znaku/linkowania dostawcy z historycznego planu.

Zatwierdzono testowe 24 h i niezbędne testy 164–166. Nie oznacza to ustalenia
docelowej retencji, usuwania backupów i zamknięcia L01/L02 dla publicznego rollout.
Ten audyt nie jest nową oceną prawną. Zachować istniejące wymagania oraz evidence;
nie wstawiać fikcyjnego rights_reference jako dowodu rozstrzygnięcia.

## Dowody i ich granice

- Raport 165.1: 22 testy gameplayu, 10 archiwum, shutdown/exposure/incident
  20+8+3, 3 JS, 31 kontroli Playwright i dodatkowe resize/reconnect/media/close.
  To wyniki wcześniejszych przebiegów, nie ponowne wykonanie w tym audycie.
- 35 MB profil: lokalny kontrakt zerowych full reads/writes/bytes; nie dowód
  globalnego p95. Nowe call sites nadal podlegają kontraktowi 130.11+.
- VPS: 025fd3f, migracja 4 tabel, Pillow 12.3.0, źródła/admin/API OFF, potem
  metadata live i 2 WebP 720x540, 117468 B, checksum/atrybucja, retencja testowa.
- Main/Paryż: 30 min → save_pending → naprawa konfiguracji workera → obraz;
  close consumed i brak powrotu; drugi 30-minutowy przebieg automatyczny PASS.
  Brak nowego ID/porównania wektorów drugiej próby; nie fabrykować pomiaru.
- Brak szerokiego E2E na kontach/kamerach/czasach/mocach, brak live Insider Feed,
  pomiarów obciążenia/PWA i pełnego fault matrix. Nie rozszerzać pojedynczego
  PASS na te zakresy. Osobny manual resize/restore nie został szczegółowo
  potwierdzony na VPS; lokalne dowody istnieją, pilot jako całość zaakceptowany.
- Testowy materiał wygasa 01.11.2026 17:47:48 UTC; nie twierdzimy, że wykonano
  GC ani że obecnie jest jeszcze dostępny. Nie pobierano ponownie w tym audycie.

## Kolejność dalszych zakresów (bez osobnego wdrożenia każdego punktu)

| Zakres | Sprint | Rezultat i bramka |
| --- | --- | --- |
| S1: kontrakt instancji + kamery świata | 164 | Wersjonowany utrwalony feed: binding gracz/kamera/operacja, zdjęcie z realnego zbioru, motion, FX/offline; kompatybilność aktywnych grantów, bez resetu consumed; wszystkie kanoniczne kamery i zgodne aplikacje |
| S2: render i lifecycle w systemie | 165 | Jeden renderer korzysta z całego profilu; brak pilotowych lokalizacji/fixture indeksów; awarie i offline rozdzielone od shutdown; complete path success/failure/close/new feed |
| S3: archiwum i eksploatacja | 164 + 165 | Automatyczne demand→worker→media, fairness i limity, trwała konfiguracja trzech ról procesów, GC/backup/withdraw, admin i publiczne źródła; brak dawnych kolejek/profili |
| S4: zbiorczy odbiór kompletnego systemu | 166 | Dopiero po S1–S3 szeroka macierz kont/aplikacji/lokalizacji/kamer, normalnych czasów i Super Powers (robot/insider_feed), concurrency/faults/PWA/performance |
| S5: standardowe wdrożenie i rollout | 166 | Jeden raport gotowości, Git/deployment, migracje/rollback, uzgodniona polityka źródła i budżety, odbiór VPS nowych punktów; testowa zgoda obowiązuje, nie pytać ponownie o każdą próbę |

S1–S3 tworzą jeden spójny zakres implementacyjny w repo. Wewnętrzne testy
zmienionego kodu wykonujemy na bieżąco; szeroki odbiór gameplayu z mocami
następuje po integracji, nie jest kolejnym rozwijaniem pilota. Bez ZIP i bez
przenoszenia implementacji na serwer. Akceptacja pilota pozostaje zamknięta.

## Kryteria wspólnego kontraktu do implementacji

- Backend losuje i zapisuje profil raz dla nowej instancji; renderer go odczytuje.
  Reload/retry/minimize/druga karta nie losują ponownie. Dla materiału opóźnionego
  wiązanie następuje raz, bez przebudowy okna i bez zmiany uprawnień.
- Wspólny materiał nie oznacza wspólnego zdjęcia/toru/scenariusza. Nowy grant
  po nowym sukcesie i download może ponownie użyć obrazu, ma nowy tor i nowy
  niezależny wybór efektu/offline. Wagi wariantów są wersjonowane i testowalne.
- Realne niedostępności i cofnięcie dostępu mają priorytet; estetyczny offline
  nie daje prawa do obrazu i nie zmienia camera_shutdown ani incydentów.
- Utrzymać jeden kanoniczny zegar pliku i istniejące moce, jeden aktywator,
  terminalność consumed, atomowość lease/claim/close i recovery po awarii procesu.
- Nie zmieniać zamrożonych kontraktów aplikacji, kosztów, nagród, camera_dump,
  ekonomii ani istniejących skutków shutdown przy globalizacji.
- Dane i ścieżki minimalne: bez ciężkich profili, zdjęć graczy, Vision,
  nowego generatora świata, nowych specjalnych okien lub dawnych kolejek.

Źródła repo: `camera_visual.py`, `camera_visual_archive.py`, `camera_visual_source.py`,
`run.py`, `database.py`, `scripts/territory_conflict_worker.py`, trzy ecosystemy,
`static/js/camera_visual.js`, `static/css/camera_visual.css`, `static/js/terminal.js`,
`templates/admin_camera.html`, `templates/camera_sources.html`, testy wymienione
w [raporcie 165.1](camera_street_view_package_165_1.md),
[journal](../history/project_journal.md), [tablica](../plans/camera_visual_pilot_164_0_board.md).
