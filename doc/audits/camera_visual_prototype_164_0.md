# CVN 164.0 — lokalny prototyp do odbioru wyglądu

Data: 2026-10-31. Baza: `82a8f6f`, branch `main`, czyste drzewo przed pracą.
Status: **LOCAL PASS komponentu; akceptacja wyglądu oczekuje**.
[Sprint 164](../sprints/sprint_164_camera_visual_archive.md),
[sprint 165](../sprints/sprint_165_camera_visual_network_rollout.md).

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
