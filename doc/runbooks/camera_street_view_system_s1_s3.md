# Camera Street View S1–S3 — zbiorcze wdrożenie po zatwierdzeniu

## Aktualizacja 166.1 — branding / nowa kamera, 01.11.2026

Ta sekcja dotyczy działającego VPS 56d5af0. Niżej zachowano pierwotny runbook
S1–S3; nie wykonywać ponownie jego konfiguracji OFF ani migracji przy tej zmianie.
Nowy zakres nie wymaga migracji, zależności, nowych sekretów ani zmiany flag.
Global OFF, pilot main, source Mapillary, acquisition/worker ON tylko w archiwum,
serve w web, retencja 24 h pozostają. Nie zmieniać danych ani grantów.

Po zatwierdzeniu konkretnego zakresu Git i standardowym commit/push operatora:

```bash
set -e
cd /home/johndoe/app/chaos
git status --short
git pull --ff-only
git log -1 --oneline
pm2 restart chaos chaos-territory-worker
pm2 status
curl --fail --silent --output /dev/null --write-out 'Web HTTP: %{http_code}\n' http://127.0.0.1:6666/
```

Restart nazwanych procesów zachowuje ich istniejące env. Nie przeładowywać
ecosystem z domyślnymi OFF, nie kopiować tokenu. Archive worker nie jest zmieniany.
Nie czyścić nieśledzonych danych. Wykonać istniejący spójny backup przed deployem.
Rollback kodu nie wymaga cofania bazy; nie odtwarzać zużytych grantów.

Cel wybrany z rzeczywistych obserwacji main w backupie 31.10:
`camera_0014ac41c138c389e40fa5cf`, rodzic `5001825490`, Kamera sklepu,
`48.85294369549624:2.3349836995089666` (około 1,3 km od pilota).
To kandydat, nie potwierdzona aktualna obserwacja VPS. Na main przejść do tej
lokalizacji normalnym Focus/Teleport i wykonać zwykły skan. Potwierdzić camera_id
i parent_target_id; nie tworzyć markera ani nie odświeżać expires_at przez SQL.

Zbiorczy odczyt po skanie, PRZED hakowaniem (bez API/zapisów gameplayu):

```bash
cd /home/johndoe/app/chaos
mkdir -p /home/johndoe/.local/state/chaos-camera/166-1
chmod 700 /home/johndoe/.local/state/chaos-camera/166-1
.venv/bin/python tools/camera_checkpoint_166.py \
  --db /home/johndoe/app/chaos/data/game.sqlite3 \
  --archive-dir /home/johndoe/app/chaos/data/camera_visual \
  --camera-id camera_0014ac41c138c389e40fa5cf \
  | tee /home/johndoe/.local/state/chaos-camera/166-1/before.json
```

Wymagane: scan_current=true, poprawny rodzic/pozycja, brak exact archiwum i brak
nearby_ready_archives. Narzędzie pokazuje także granty, budżet, dysk i heartbeat.
Jeśli jest materiał do reuse, nie usuwać go: wybrać inną rzeczywistą kamerę
w zatwierdzonym budżecie i zachować osobny baseline. Stan z lokalnego starego
backupu (scan_current=false, archive_schema=false) nie zalicza baseline VPS.

Następnie zwykłe camera_stream → kompatybilna aplikacja → sukces backendu.
Istniejący kod enqueue uruchamia się przy przyjęciu sukcesu, równolegle do
downloadu aktywatora. Nie dodajemy pozyskiwania przed hackiem ani ręcznego
enqueue/work-once w celu odtworzenia literalnej kolejności diagramu.
Obserwować automatyczny worker: nowy archive_id, QUEUED/FETCHING → READY,
attempts, przyrost budżetu, maksymalnie 3 fotografie, WebP i checksum.
Zachować log cyklu archiwum oraz czas utworzenia po baseline jako dowód
automatycznego pozyskania; samo READY nie dowodzi nowego pobrania.
NO_COVERAGE odnotować bez klasyfikowania jako awarii, dobrać następny realny cel.

Po rzeczywistym czasie downloadu (bez zmiany zegara/mocy) zweryfikować aktywator
i jednorazowe okno z wybranym materiałem, prawdziwym autorem/licencją/linkiem.
Powtórzyć powyższy odczyt do `after.json` zamiast `before.json`, zebrać:

```bash
pm2 logs chaos-camera-archive --lines 40 --nostream
```

W konsoli zalogowanej gry: tylko odczyt stanu, bez claim/close/reopen:

```javascript
fetch('/api/camera-visual/state').then(r => r.json()).then(d => console.table(
  d.sessions.filter(s => s.target?.camera_id === 'camera_0014ac41c138c389e40fa5cf')
   .map(s => ({operation_id:s.operation_id,state:s.state,progress:s.progress,
     archive_id:s.archive_id,image_id:s.image_id,viewer_closed:s.viewer_closed}))
));
```

Odbiór wyglądu: niewielki oryginalny znak, ostrzeżenie hover/focus/tap, link do
tego samego zdjęcia, nowa karta, powrót do tej samej instancji bez consumed.
Lokalne testy tych zachowań są wykonane; VPS ma potwierdzić właściwe realne
metadane i pozyskanie. Nie powtarzać pilota paryskiego. Zatrzymać się na raporcie
166.1; bez global ON i bez 166.2–166.5 w tej sesji.

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
