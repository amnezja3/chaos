# 156.4 — instalacja PWA

Stan: implementacja lokalna, bez wdrożenia. Flaga `CHAOS_INSTALL_UI_ENABLED`
domyślnie OFF. Panel działa tylko przy równocześnie włączonych
`CHAOS_PERSISTENT_SESSION_ENABLED` i `CHAOS_LAUNCH_CONTROLLER_ENABLED`.
Nie zmienia limitów 30 dni bezczynności / 90 dni od logowania.

## Zakres

- Panel przed logowaniem i w Ustawieniach, centralne katalogi PL/EN 156.4.0.
- Windows, Linux, Android, iOS jednocześnie; wyróżnienie platformy jest tylko
  wskazówką. Dostępność natywnej instalacji wynika z eventu przeglądarki.
- Prompt wyłącznie po kliknięciu. Anulowanie, zaakceptowane żądanie i potwierdzona
  instalacja to osobne stany. `appinstalled` potwierdza instalację; standalone
  potwierdza sposób bieżącego uruchomienia. Brak eventu prowadzi do instrukcji.
- iOS/iPadOS: Safari → Udostępnij → Dodaj do ekranu początkowego. Możliwe osobne
  logowanie, bez założenia przeniesienia cookies. Instalacja opcjonalna, bez nowych
  zgód marketingowych i bez zastępowania istniejących warunków konta.
- Linux: pobierany `Type=Link` do stałego `https://chaos.re/launch`, bez Exec,
  chmod i danych gracza. To skrót, nie obietnica instalacji PWA.
- Manifest `/chaos.webmanifest`: id `/chaos`, start `/launch`, scope `/`, standalone.
  PNG 192/512 i Apple 180 pochodzą z istniejącej wektorowej ikony CHAOS;
  logo ma bezpieczny margines maskable. Nie powstają osobne aplikacje na konto/język.

## Cache i aktualizacje

`/chaos-sw.js`, scope `/`, rejestracja `updateViaCache:none`.
Cache `chaos-install-156-4` zawiera dokładnie: neutralny offline HTML/JS,
CSS instalacji i ikony 192/512, wszystkie pod URL z `v=156-4`.
Pobieranie do cache ma `credentials:omit`, odrzuca błędy i przekierowania.
Brak zapisu prywatnych HTML, `/launch`, statusu, bootstrapu, API, wiadomości,
zakupów czy profilu. POST i pozostałe mutacje nie są przechwytywane.
Offline fallback wyłącznie dla nawigacji `/`, `/launch`, `/desktop` po błędzie sieci.
Ekran używa języka przeglądarki PL/EN, nie odczytuje ostatniego konta ani jego języka.

Nowy worker czeka na zamknięcie wszystkich okien poprzedniej wersji. Panel pokazuje
komunikat aktualizacji; nie ma automatycznego reload, `skipWaiting` ani `clients.claim`
w aktywnym workerze. Zakończyć operacje, zamknąć okna CHAOS i uruchomić ponownie.
Zmiana publicznych cache'owanych plików wymaga nowej wersji URL oraz nazwy cache.

Rollback: wyłączyć `CHAOS_INSTALL_UI_ENABLED` w rzeczywistej konfiguracji procesu
i zrestartować zgodnie z runbookiem wdrożenia. **Zachować endpoint `/chaos-sw.js`**:
zwraca worker wycofujący, który przejmuje aktualizację, usuwa tylko cache
`chaos-install-*` i wyrejestrowuje się. Nie usuwać endpointu ani nie cofać kodu do
wersji sprzed jego istnienia przed wycofaniem workerów. Klient offline otrzyma
wycofanie dopiero po powrocie online. Zachować `/launch` dla zainstalowanych skrótów.
Wyłączenie którejkolwiek zależności także uruchamia ten rollback.

## Weryfikacja lokalna

Komenda → spodziewany wynik:

```text
python tools/run_isolated_tests.py test_installation test_launch_controller
→ 20 testów, OK
python tools/run_isolated_tests.py test_installation test_ghost_i18n
→ 10 testów, OK
node tests/js/test_installation_worker.js
→ Installation worker isolation PASS
python tools/session_156_install_browser_smoke.py
→ JSON ok:true; PL desktop / EN mobile; brak błędów JS i nieoczekiwanych błędów konsoli
```

Browser harness wymaga Python Playwright i Chrome. Tworzy tymczasowy lokalny serwer
i izolowaną bazę; nie uruchamia drugiej instancji produkcyjnej. Sprawdza panel,
instrukcje, katalog języka, manifest/SW, cache, offline, Ustawienia i wycofanie
workera z zachowaniem obcego cache. Prompt jest symulowany do testu anulowania
i akceptacji; nie jest dowodem rzeczywistej instalacji systemowej.

Playwright MCP nie był dostępny w tej sesji; wykorzystano lokalny Playwright/Chrome.
Wynik końcowy 15 X 2026: PL 1280 px i EN 390 px PASS, po pięć wpisów cache,
brak błędów JS i nieoczekiwanych błędów konsoli. Rollback rzeczywistej rejestracji
PASS; obcy cache zachowany. Zrzuty lokalne `.playwright-mcp/install-156-4-pl.png`
i `.playwright-mcp/install-156-4-en.png` sprawdzone wizualnie (EN po poprawce zawijania).
Prawdziwa instalacja, powrót po zamknięciu aplikacji i izolacja cookies na fizycznym
iOS/Android oraz odbiór desktopowych platform pozostają w **156.5**.
Nie nadano pełnego PASS Sprintowi 156.

Źródła zachowania API: [MDN — install prompt](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/How_to/Trigger_install_prompt)
oraz [MDN — cykl service workera](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers), sprawdzone 15 X 2026.
