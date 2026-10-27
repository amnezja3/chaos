# 163.5 — sygnał życia kolektora

Ten pakiet oddziela żywotność procesu od ostatniego udanego pobrania.
Nie zmienia źródeł, kosztów, odświeżania, geometrii ani konfiguracji web.
Monitor i raport odbioru dodają `heartbeat`; sam `jobs.runtime=unknown`
pozostaje informacją, że kolejka nie jest inspekcją PM2.

## Semantyka

- `running`: świeży sygnał przed pracą; nie dowodzi sukcesu zadania.
- `waiting`: cykl zakończony, proces oczekuje na następny.
- `stopped` / `error`: świeżo zapisane zakończenie lub błąd.
- `unknown`: brak schematu, brak obserwacji, wygaśnięcie albo zegar cofnięty
  względem obserwacji. Nie oznacza automatycznie wyłączonego procesu.

Termin ważności: max(120 s, interwał pętli + 110 s); przy obecnym interwale
30 s wynosi 140 s. Sygnał odnawiany przed cyklem i przed oczekiwaniem.
Nagłe zabicie procesu pozostawia wpis, który wygasa. Nowa instancja zastępuje
właściciela; poprzednia nie może odnowić wpisu ani zatrzymać następcy.
To stan ostatnio zarejestrowanej instancji, nie wykrywacz wszystkich procesów.
Zapis telemetrii jest opcjonalny; awaria nie zmienia lease ani księgi kolektora.
Odczyty nie odnawiają terminu i nie migrują schematu. Tylko aktywny daemon
`--execute --serve` zapisuje sygnał. Plan, pojedyncze wykonanie i wyłączony
worker nie przejmują wpisu działającego kolektora.

## Zbiorczy odbiór VPS

Po pushu, bez nowych prób dostawców z narzędzi diagnostycznych:

```bash
cd ~/app/chaos &&
git pull --ff-only &&
bash tools/world_local_read_acceptance_163_5.sh &&
.venv/bin/python tools/poi_world.py --canonical --discovery --jobs --metrics
```

Addytywna migracja jednej tabeli, z backupem istniejącej bazy:

```bash
umask 077
HEARTBEAT_BACKUP="$HOME/chaos-backups/163-5-heartbeat-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$HEARTBEAT_BACKUP" &&
.venv/bin/python tools/poi_world.py --canonical --discovery --jobs --metrics --apply --backup "$HEARTBEAT_BACKUP/poi_cache.sqlite3" &&
.venv/bin/python tools/world_release_check.py --require-metrics --require-collection --require-visits --require-heartbeat &&
pm2 startOrReload ecosystem.discovery.config.js --only chaos-world-discovery-worker --env regular_halo --update-env &&
.venv/bin/python tools/world_runtime_check.py --routing 1 --worker online --world-stage visits --halo 1
```

Po uruchomieniu procesu sprawdzić razem monitor i logi:

```bash
.venv/bin/python tools/world_collection_monitor.py
pm2 logs chaos-world-discovery-worker --lines 15 --nostream
```

Oczekiwane: heartbeat prepared=true, running lub waiting, świeży observed_at
i expires_at w przyszłości. Archiwalny wynik `last` nie musi być nowym pobraniem.
Regularny kolektor nadal działa według dotychczasowej polityki i może wykonywać
naturalne zapytania. Nie wymuszać zadania dla testu żywotności.
Po odbiorze `pm2 save`. Web nie wymaga restartu dla tego etapu.

Wygaśnięcie i przejęcie wpisu przez nową instancję sprawdzają testy deterministyczne;
nie zatrzymywać celowo produkcyjnego kolektora ani czekać 140 s dla powtórzenia testu.
Rollback kodu nie wymaga usuwania tabeli ani odtwarzania bazy. Stary worker nie
odnawia heartbeat, więc nowy monitor poprawnie pokaże unknown po wygaśnięciu.
Prezentacja nowych stanów w panelu pozostaje częścią pakietu atlas/UX.
