# CVN 164.0 — historyczne demonstratory A/B; pilot w grze nieukończony

Data: 2026-10-31. Historyczna rewizja: **B**, baza `5949c04`.
Status po korekcie operatora: **A/B nie realizują 164.0; rozwój demonstratora
zatrzymany.** Aktualna implementacja: [działający pilot w gameplayu](camera_visual_gameplay_164_0.md),
lokalnie przetestowany, do odbioru autora.
[Sprint 164](../sprints/sprint_164_camera_visual_archive.md),
[sprint 165](../sprints/sprint_165_camera_visual_network_rollout.md).

## Wiążąca korekta zakresu 31.10.2026

Prototyp oznacza jeden działający przypadek w normalnej grze, nie osobny host
do projektowania. Aplikacja referencyjna: istniejący Glass Eye (`admin_seed_camera_stream_v1`).
Konkretną kamerę należy wskazać ze zweryfikowanego skanu gry i zapisać jej
kanoniczne powiązanie. Wymagane są prawdziwe rozstrzygnięcie wyniku aplikacji,
Centrum Operacji, dysk gracza i nowa instancja standardowego okna Ghost Systemu.
Pełny kontrakt i warunki odbioru znajdują się w sekcji 164.0 sprintu 164.

Poniższe wyniki i polecenia zachowano wyłącznie jako historię. Nie uruchamiać
tego hosta jako rozwiązania 164.0 i nie rozwijać jego osobnego logowania,
runtime, interfejsu operacji ani wybieranego ręcznie wyniku. PASS harnessu,
zrzuty A/B i wykorzystanie wyciągniętych funkcji renderera nie są dowodem
integracji z gameplayem. Bieżący pakiet do odbioru opisuje osobny audit gameplayu powyżej.

## Rewizja B — historyczna decyzja i rezultat poza grą

Operator po pierwszym prototypie zażądał rozdzielenia instancji i etapów:

```text
success → końcowy stan referencji → SESSION CLOSE 5 s → zamknięcie referencji
        → Centrum Operacji: pobieranie aktywatora przez 1800 s, 0–100%
        → atomowy zapis i weryfikacja pliku na dysku gracza
        → nowa instancja standardowego okna Ghost System: GLASS EYE
failure → końcowy stan referencji; brak pobierania, aktywatora i podglądu
```

To zastępuje wcześniejszą zamianę zawartości okna referencyjnego na fotografię.
Zgoda dotyczy tej zmiany przebiegu i wskazanej wizualizacji; nie oznacza odbioru
wyglądu wykonanej rewizji B ani aktywacji Mapillary.

Wykonano w izolowanym, trwałym prototypie:

- Wynik referencji zapisany raz; retry nie zmienia failure w success ani nie
  przesuwa terminów. Termin zamknięcia jest serwerowy. Zamknięcie okna,
  refresh, brak odbiorcy i logout nie zatrzymują przyjętego procesu.
- Pobieranie ma rzeczywisty kontrakt 1800 sekund. Lokalny worker odtwarza
  zaległą pracę po restarcie. Postęp obliczany z trwałych terminów, nie timera DOM.
- Receipt, operacja i aktywator używają jednej izolowanej bazy SQLite.
  Operacje/pliki/dysk to istniejące tabele `player_operations`,
  `player_data_files`, `player_storage`; odczyty przez istniejące stores.
  Transakcja zapisu pliku, zajętości dysku i READY jest atomowa, z read-back
  treści oraz checksum. Brak miejsca, błąd zapisu i uszkodzony plik blokują viewer.
- Trwały `instance_id` jest inny od `reference_id`. Serwerowa dzierżawa
  dopuszcza jeden dokument do tego samego viewera; drugi tab nie dubluje okna.
  Klient odnawia co sekundę i usuwa viewer po utracie dzierżawy. Stary dokument
  nie może zamknąć dzierżawy nowego. Jawne zamknięcie zapamiętuje `closed`;
  automatyczny polling nie otwiera go ponownie. Ręczne otwarcie używa tego
  samego aktywatora i tożsamości viewera, bez kolejnego pobierania.
- `app_window`, `prepareApplicationRenderWindow`, `bindWindowMaximize`,
  `makeDraggable`, `minimizeWorkspaceWindow` i workspace bounds są wykonywane
  bezpośrednio z aktualnego terminal.js. Obie instancje mają `interface: window`.
  Taskbar hosta jest adapterem fixture. Brak nowego typu interfejsu kamery.
- Wygląd zgodny z kierunkiem referencji: ciemne okno, turkusowe obramowanie,
  GLASS EYE, ikona, − / maksymalizacja / ×, fotografia wewnątrz okna.
  Pozostaje prawdziwa atrybucja CC0/Wikimedia, bez podszywania się pod Mapillary.

### Historyczne uruchomienie demonstratora — nie ścieżka odbioru 164.0

```powershell
.venv/Scripts/python.exe tools/camera_visual_browser_fixture.py
```

Adres: `http://127.0.0.1:8999`. LOGIN (`cvn-alice` lub `cvn-bob`) → Uruchom
GLASS EYE → testowa operacja. Wybór `RESULT` dotyczy **pierwszego** wyniku
danego konta. Konto z zapisaną porażką nie zmieni go przełączeniem selektora.
Konta są wyłącznie lokalnymi fixture; nie jest to produkcyjny system logowania.
Domyślna baza: `instance/camera-visual-164-0.sqlite3`, zachowana między startami.
Program odmawia użycia istniejącej bazy bez znacznika fixture.
Stara komenda Node nadal działa jako launcher Pythona. Zatrzymanie: Ctrl+C.

Do szybkiego odbioru przebiegu na **nowej** izolowanej bazie:

```powershell
.venv/Scripts/python.exe tools/camera_visual_browser_fixture.py --db instance/camera-visual-review.sqlite3 --test-controls
```

`TEST +15 min` przesuwa wyłącznie zegar fixture. Dwa użycia po końcu SESSION
CLOSE pozwalają zobaczyć 50% i zakończenie bez czekania pół godziny.
Bez `--test-controls` endpoint przesunięcia czasu jest niedostępny i przycisk ukryty.
Do nowego scenariusza użyć drugiego konta albo nowej ścieżki `--db`;
nie kasować produkcyjnych danych. Plik aktywacyjny znajduje się na **dysku gry**
w canonical inventory, nie w katalogu Pobrane systemu Windows.

Aktualne zrzuty:

- [SESSION CLOSE](../../artifacts/cvn-164-0-b-session-close.png)
- [Pobieranie 50%](../../artifacts/cvn-164-0-b-download.png)
- [Osobne okno GLASS EYE](../../artifacts/cvn-164-0-b-desktop.png)
- [Mobile EN](../../artifacts/cvn-164-0-b-mobile.png)
- [Failure — końcowy stan referencji](../../artifacts/cvn-164-0-b-failure.png)

### Weryfikacja B

- `python -m unittest discover -s tests -p test_camera_visual_fixture.py`:
  **10 PASS**, izolowane SQLite; exact 5+1800 s, 0/50/100%, failure/retry,
  restart/re-login, konkurencja 8 wywołań, storage full, rollback transakcji,
  lease/close/reopen, korupcja, izolacja kont, odmowa nieoznaczonej bazy.
  Syntetyczny profil 35 MiB i pułapki na pełne odczyty: PASS.
- Playwright MCP `tests/browser/camera_visual_lifecycle_164_0.js`: **24 PASS**,
  w tym reload podczas SESSION CLOSE i pobierania, logout/login, standardowe
  kontrolki i drag, dwie karty, osobna instancja, jawne close/reopen, mobile/EN.
- Playwright MCP `tests/browser/camera_visual_164_0.js`: **13 PASS** — fotografia,
  atrybucja/schowek/Escape, 4 stany awaryjne, reload, brak ponownego pobrania,
  świadoma nawigacja tej samej karty (odpowiedź zewnętrzna przechwycona lokalnie).
- Faktyczny restart procesu hosta na tej samej bazie i ponowne wejście:
  **PASS**, ten sam instance_id, jedna operacja i jeden plik.
- Trzy dotychczasowe regresje kamer JS: PASS; `node --check`, `git diff --check`: PASS.
- Aktualny przebieg przeglądarki: **0 errors, 0 warnings**. Historyczny bufor
  zawierał 3 ERR_CONNECTION_REFUSED z celowego zatrzymania wcześniejszego hosta.
  Naprawiono brakujące importy CSS hosta, wyścig logowania, reset stanu okien
  po logout oraz zamykanie testowego SQLite na Windows.
- Python 3.11.9 działa poza sandboxem. Wcześniejsza blokada uruchomienia
  WindowsApps z rewizji A nie jest już blokadą lokalnych testów.

### Granice dowodów i dalsza integracja

To nadal **164.0, lokalny prototyp do odbioru**, nie zmiana produkcyjnego
`run.py`, routingu, generatora ani Centrum Operacji gry. Host używa istniejących
rendererów i canonical tabel, ale jego konta, odpowiedź `success/failure`,
receipt, endpointy i karta postępu są adapterami testowymi. Nie ma zdjęć graczy,
Mapillary, archiwum ani kolejki CVN. Nie używać modułu `tools/*fixture*` jako
gotowej autoryzacji produkcyjnej. Lokalne assety CC0 są publiczne w tym hoście.

Przy integracji 164–165: wykorzystać existing camera_stream i jego 30-minutowy
runtime jako źródło przebiegu; nie dopisywać drugiego płatnego procesu ani
kolejnych 30 minut. Nazwa `camera_activation_download` w tym hoście jest typem
fixture, **nie nowym typem operacji wdrożonym do gry**. Aktywator prezentacji
pozostaje odrębny od nagrody camera_dump. Serwer musi wywodzić zdolność z
zweryfikowanego kontraktu aplikacji (nowej lub zgodnej historycznej), potwierdzać
wynik/zapis i aktualne prawo do materiału; sam status completed nie daje uprawnień.

Production profile hot paths: **0 nowych, 0 zmienionych**, brak wyjątków heavy.
Fixture odczytuje ograniczone receipts i canonical stores; brak profili runtime,
brak schema init w requestach, HTTP/inferencji i obróbki zdjęć pod writer lockiem.
Nie wykonano pełnego E2E prawdziwego konta, realnej PWA, rolloutu ani VPS.
Następny krok: **odbiór wyglądu i przebiegu rewizji B**.

## Historia — rewizja A (`5949c04`), zastąpiona powyżej

Baza A: `82a8f6f`. Poniższy opis/testy dotyczą wcześniejszego nietrwałego hosta;
aktualne uruchomienie i zakres są w sekcji rewizji B.

## Uruchomienie i odbiór

Z katalogu repo, Windows/PowerShell, Node 24.8.0:

```powershell
node tools/camera_visual_browser_fixture.js
```

Otwórz `http://127.0.0.1:8999`, wybierz „Podgląd kamery”, następnie
„Uruchom testową operację”. Zatrzymanie: Ctrl+C. Host nasłuchuje tylko na loopback,
serwuje zamkniętą listę plików; nie uruchamia Flask, DB, kont ani dostawców.
Przeglądarka podczas podglądu pobiera wyłącznie lokalne zasoby.

Jedna kamera i jedna rzeczywista fotografia. „Pełny kadr” i „Zbliżenie”
przełączają prezentację **tego samego zdjęcia**, nie udają innych ujęć.
Pełny kadr zachowuje całe zdjęcie, z pasami przy innych proporcjach okna.
SYNCHRONIZING → ARCHIVE LINK, subtelna zmiana filtru i scanlines, pauza,
PL/EN, reduced motion, NO SIGNAL, SIGNAL LOST, REVOKED i ARCHIVE CORRUPTED.
Źródło i licencja są widoczne przy obrazie oraz w osobnym panelu.
Kopiowanie ma komunikat i fallback ręczny. EXTERNAL CONNECTION obsługuje
anulowanie/Escape, przywrócenie focusu i rzeczywistą nawigację w tej samej karcie.
Nie ma logo Mapillary: materiał nie pochodzi od tego dostawcy.

Materiały do odbioru:

- [Desktop PL](../../artifacts/cvn-164-0-desktop.png)
- [Mobile PL](../../artifacts/cvn-164-0-mobile-pl.png)
- [Mobile EN](../../artifacts/cvn-164-0-mobile-en.png)
- [EXTERNAL CONNECTION](../../artifacts/cvn-164-0-external-en.png)
- [NO SIGNAL](../../artifacts/cvn-164-0-no-signal.png)

## Pochodzenie zdjęcia

`doc/prototypes/camera_view/v164_0/walowa.jpg`: **Cybularny**,
„2018 Warszawa Wałowa.jpg”, wykonane 2018-07-19, Wikimedia Commons.
[Strona źródłowa i deklaracja autora CC0 1.0](https://commons.wikimedia.org/wiki/File:2018_Warszawa_Wa%C5%82owa.jpg),
[CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/).
Sprawdzone 2026-10-31; pobrano jedną publiczną miniaturę, nie oryginał:
`https://upload.wikimedia.org/wikipedia/commons/thumb/7/79/2018_Warszawa_Wa%C5%82owa.jpg/960px-2018_Warszawa_Wa%C5%82owa.jpg`.
960 × 720, JPEG, 233266 bajtów. Bez transformacji zapisanego pliku.
SHA-256: `ee09e61db05e23ddfcc0ea54c2b53c986332fe0fb21cb66cfac4ca9079170e16`.
Filtr, scanlines i opcjonalny crop dotyczą tylko prezentacji CSS.
Nie ustalano azymutu ani odległości od rzeczywistej kamery; lokalizacja kamery
to izolowana etykieta fixture. Nie ma deklaracji zgodności kierunkowej.

## Rozpoznanie istniejącej integracji

- `templates/map_template.html`: menu celu camera zawiera `camera_stream` oraz
  `camera_shutdown`, uruchamia istniejący transport wyboru narzędzia.
- `creator_policy.py`: receptura `camera_stream` → scanner_recon/scanner,
  target camera, operation camera_stream, resource camera_dump.
- `terminal.js`: `launchApplicationEffect` rozdziela interfejsy;
  `app_window` renderuje istniejące okno i korzysta z `sendGonnaWinRequest`.
  `rememberGonnaWinCanonicalResult` utrwala w kliencie referencje
  `created_operations`; `notifyCreatedOperations` deduplikuje powiadomienia.
- Proponowany punkt podłączenia po odbiorze: wspólna obsługa **zatwierdzonej
  odpowiedzi operacji** z camera_stream i operation_id, przed auto-close,
  dołączająca presenter do istniejącego okna. Serwer później weryfikuje aplikację,
  aktywną operację i kanoniczną kamerę przed wydaniem manifestu.
- `cameraApplicationLaunchKey` obecnie obsługuje tylko camera_shutdown
  i współrzędne. Nie jest gotową deduplikacją CVN stream ani autoryzacją.
  `camera_contract.py` także zawiera kontrakt shutdown, nie gotowe uprawnienie stream.
- `run.py`: `ensure_camera_stream_fragments` / `finalize_camera_stream_file`
  pozostają autorytetem zasobu camera_dump. Prototyp ich nie wywołuje ani nie zmienia.

Host wycina i wykonuje aktualne `app_window` oraz `findCameraApplicationWindow`
z terminal.js. Środowisko renderera i transport operacji są jawnie stubowane.
Warstwa wizualna działa w jego `.app-content`; nie ma drugiego produkcyjnego
launchera. W fixture odmiany new/legacy współdzielą jeden klucz kamery i materiał.
To demonstracja docelowej prezentacji, **nie dowód kompatybilności kontraktów**.

Po akceptacji wyglądu: serwerowa projekcja `camera_visual_preview` dla
zweryfikowanego camera_stream; automatycznie dla nowych i zgodnych starszych
aplikacji, bez regenerowania, heurystyk nazw ani zmiany zamrożonej mechaniki.
Jedno archiwum dla wszystkich aplikacji, oddzielna autoryzacja każdej operacji.
Nie dodano CAMERA CREATOR, uploadu, aparatu/GPS, PLAYER_UPLOAD ani Sprintu 166.

## Wykonane sprawdzenia

- Playwright MCP, Chromium: `tests/browser/camera_visual_164_0.js` — **21 PASS**.
  Desktop 1440 × 1000, mobile 390 × 844; PL/EN, reduced-motion, obraz 960 × 720,
  wejście dopiero po wyniku testowej operacji, dedupe, reopen, crop/pauza,
  metadane/kopiowanie, Escape/focus, wszystkie cztery stany awaryjne,
  zamknięcie w trakcie synchronizacji, brak poziomego overflow.
- Potwierdzone wyjście wykonało rzeczywistą nawigację tej samej karty do
  zamrożonego URL; odpowiedź zewnętrznej strony przechwycona lokalnie w teście.
- Konsola Playwright: **0 errors, 0 warnings**. Zrzuty obejrzane wizualnie.
- `node tests/js/test_camera_window_dedupe.js` — PASS.
- `node tests/js/test_camera_target_transport.js` — PASS.
- `node tests/js/test_camera_operation_delta.js` — PASS.
- `node --check doc/prototypes/camera_view/v164_0/preview.js` — PASS.
- `git diff --check` — PASS.

Python `.venv/Scripts/python.exe` wskazuje niedostępną instalację WindowsApps;
także domyślny python nie startuje (błąd sesji logowania). Nie wykonano testów
Python ani pełnego E2E gry. Nie zmieniono backendu. Fixture Node umożliwiła
pełny odbiór komponentu przeglądarkowego bez naprawiania środowiska przy okazji.

PROFILE HOT PATH AUDIT: nowe produkcyjne call sites **0**, dotknięte **0**,
heavy wyjątki **none**. Fixture nie importuje DB/profili; reads/writes/bytes,
queries i writer locks **0 z konstrukcji hosta**, nie jako pomiar Flask.
Benchmark konta ≥35 MB nie był wykonywany: nie dodano ścieżki profilu.

Nie wykonano: generator→publikacja→instalacja→autoryzowana operacja→CVN E2E,
Mapillary, archiwum/worker, rollout, prawdziwa instalowana PWA ani VPS.
L01/L02 pozostają otwarte. Nie rozpoczęto infrastruktury 164.1–164.5.
Następna decyzja: **odbiór kierunku wizualnego przez autora** albo uwagi do iteracji.
