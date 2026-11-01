# Camera Street View S1–S3 — zbiorcze wdrożenie po zatwierdzeniu

Przygotowane lokalnie 01.11.2026. Nie wykonywano poniższej procedury na VPS.
Nie uruchamiać historycznych procedur wdrożeniowych z poprzednich sprintów.

1. Zatwierdzić zakres Git i raport lokalny. Commit/push wyłącznie po decyzji
   operatora. Wykluczyć lokalne bazy, sesje, logi Playwright, cookies i sekrety.
2. W jednej sesji serwera sprawdzić HEAD/status/PM2 i zrobić istniejącym
   mechanizmem spójny backup SQLite oraz prywatnego archiwum. Nie kasować
   nieśledzonych katalogów danych. Zatrzymać zapisy procesów podczas migracji.
3. Zaktualizować repo standardowym mechanizmem. Uruchomić idempotentnie:
   `.venv/bin/python tools/camera_archive.py --db <baza-gry> --action migrate --apply`.
   Trzy dodatkowe tabele pomocnicze; istniejące consumed i aktywatory zostają.
4. Ustawić `CHAOS_CAMERA_CONFIG` na absolutną ścieżkę jednego prywatnego JSON.
   Plik zawiera zatwierdzone flagi, ścieżki i limity, bez tokenu. Przykład OFF:

```json
{
  "CHAOS_DB_PATH": "/home/johndoe/app/chaos/data/game.sqlite3",
  "CHAOS_CAMERA_ARCHIVE_DIR": "/home/johndoe/app/chaos/data/camera_visual",
  "CHAOS_CAMERA_STREET_VIEW": "0",
  "CHAOS_CAMERA_VISUAL_PILOT": "0",
  "CHAOS_CAMERA_SOURCE": "off",
  "CHAOS_CAMERA_WORKER": "0",
  "CHAOS_CAMERA_ACQUISITION": "0",
  "CHAOS_CAMERA_SERVE": "0",
  "CHAOS_CAMERA_RETENTION_SECONDS": "0",
  "CHAOS_CAMERA_MAX_REQUESTS": "100",
  "CHAOS_CAMERA_MAX_BYTES": "104857600",
  "CHAOS_CAMERA_MAX_ARCHIVES": "1000",
  "CHAOS_CAMERA_MAX_STORAGE_BYTES": "1073741824",
  "CHAOS_CAMERA_DIAGNOSTICS": "0"
}
```

Nie nadpisywać aktywnego pilota tym przykładem. Przenieść do pliku faktycznie
zatwierdzony zakres bieżących flag. Zmiana na globalne `1` jest osobnym rolloutem.
`MAPILLARY_ACCESS_TOKEN` pozostaje w istniejącym prywatnym mechanizmie sekretów,
dostępny procesowi archiwum. Uzupełnić tylko zatwierdzone dokładne CDN hosts,
rights reference, license/license URL i retencję. Nie kopiować testowej retencji
jako domyślnej polityki publicznej.

5. Z tego samego środowiska załadować trzy aktualne ecosystem files przez
   standardowy PM2 start/reload z aktualizacją env: web, territory-worker,
   camera. Restart samego `chaos` nie aktualizuje finalizatora. Wszystkie role
   dostają tę samą DB/source/flagę gameplayu. Rola operations ma acquisition i
   serve OFF; rola archive ma serve OFF; web ma worker/acquisition OFF.
6. Sprawdzić `/dev?tab=camera`: zgodność identyfikatora DB, source i zakresu
   gameplayu w trzech rolach; heartbeat operations i archive nie starszy niż
   około 30–60 s. Web jest bieżącym odczytem, nie dodatkowym zapisującym workerem.
   CLI `status` nie wywołuje API. `work-loop` zastępuje ręczny work-once i cron.
7. Po poprawnej konfiguracji zapisać stan PM2 i zweryfikować istniejący startup
   service. PM2 zapisuje projekcję env; późniejsza edycja JSON wymaga przeładowania
   ecosystem files, samo `pm2 restart chaos` nie wczytuje zmienionego pliku.
   Sprawdzić recovery po restarcie wszystkich ról, następnie kontrolowany reboot.
8. Zbiorczy test 166: nowy scan/hack → sukces → rzeczywisty download → zapis
   aktywatora → jedno okno → reload/reconnect → close consumed → nowy hack.
   Dodatkowo failure, pełny dysk, retry finalizatora, API/rate limits, wycofanie,
   expiry/GC, osobne konta i kamery, Insider Feed/Operational Prediction,
   camera_off/incydenty, sześć scenariuszy, mobile/PWA oraz sześć ścieżek linków.
   Nie skracać produkcyjnego timera na potrzeby tego odbioru.

Rollback: wyłączyć nowe bramki w tym samym pliku i przeładować trzy role.
Zatrzymać pozyskiwanie; zachować DB, tombstones i consumed. Cofnięcie kodu do
wcześniejszego commita nie wymaga usuwania addytywnych tabel. Nie odtwarzać
starej bazy ponad nowsze zużyte granty. Archive restore jest addytywny i nie
zastępuje pełnego backupu danych gry. Osobny rollback konfiguracji nie daje
prawa do ponownego otwarcia wykorzystanego podglądu.
