# 163.5 — zbiorczy pakiet odbioru, 27.10.2026

Nie kasujemy bazy, księgi ani historycznych operacji Geoapify. Etap pierwszy
wdraża kod i panel bez rozszerzania praw dostawców. Etap drugi jawnie dopuszcza
VK do skanów i regionalnego pobrania; działający MapLark pozostaje fallbackiem.

## 1. Kod, testy, backup i schemat

Po pushu:

```bash
cd ~/app/chaos &&
git pull --ff-only &&
bash tools/world_local_read_acceptance_163_5.sh &&
.venv/bin/python tools/poi_world.py --canonical --discovery --jobs --metrics
```

Testy używają izolowanych baz i transportów; nie wykonują prób dostawców.

```bash
umask 077
WORLD_BACKUP="$HOME/chaos-backups/163-5-final-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$WORLD_BACKUP" &&
.venv/bin/python tools/poi_world.py --canonical --discovery --jobs --metrics --apply --backup "$WORLD_BACKUP/poi_cache.sqlite3" &&
.venv/bin/python tools/world_release_check.py --require-metrics --require-collection --require-visits --require-heartbeat &&
pm2 startOrReload ecosystem.web.config.js --only chaos --env world_visits --update-env &&
pm2 startOrReload ecosystem.discovery.config.js --only chaos-world-discovery-worker --env regular_halo --update-env &&
.venv/bin/python tools/world_runtime_check.py --routing 1 --worker online --world-stage visits --halo 1
```

Po krótkim rozruchu sprawdzić HTTP oraz monitor razem:

```bash
curl -sS -o /dev/null -w 'Launch HTTP: %{http_code}\n' https://chaos.re/launch
.venv/bin/python tools/world_collection_monitor.py
pm2 logs chaos-world-discovery-worker --lines 15 --nostream
```

Warunek: HTTP 200, świeży heartbeat running/waiting, zgodne flagi. Panel
POI / Overpass: atlas pozwala wczytać widoczny obszar, pokazuje liczbę obiektów,
rozmiar DB/WAL i wiek oczekujących zadań. Stan kolektora opisuje moment odczytu.
Nie wymuszać nowego płatnego pobrania dla sprawdzenia heartbeat.

## 2. Plan regionalny i jawna aktywacja

```bash
.venv/bin/python tools/world_regional_enable.py
```

Plan: live VK → MapLark; archiwum POI MapLark przed dotychczasowymi alternatywami.
Wymaga aktualnego zatwierdzonego VK, budżetu prób i działającego fallbacku.
Nie odnawia terminu przeglądu, nie zwiększa limitów. Sam plan nie wykonuje HTTP.

Po przyjęciu planu:

```bash
.venv/bin/python tools/world_regional_enable.py --apply --approve-live-wide --backup "$WORLD_BACKUP/before-regional.sqlite3" &&
pm2 startOrReload ecosystem.web.config.js --only chaos --env world_regional --update-env &&
.venv/bin/python tools/world_runtime_check.py --routing 1 --worker online --world-stage regional --halo 1
```

Aktywacja pozwala naturalnym skanom pobierać jeden obszar Overpass 1500 m;
skan gracza nadal ma 300 m. Próby live i kolektora korzystają ze wspólnego
limitu VK 120/dzień i 3720/31 dni. Archiwalne POI MapLark obejmują wszystkie
sześć filtrów CHAOS, ale nie otrzymują automatycznie certyfikatu skanu kołowego.

## 3. Jeden przebieg gry i wspólny odczyt logów

1. Konto testowe: jeden skan w nowym miejscu. Zanotować dokładne współrzędne.
2. Drugie konto: skan w tym samym miejscu, następnie około 100 m dalej,
   w ciągu pięciu minut. Nie przesuwać się na granicę pobranego regionu.
3. Odczytać razem `poi_route`, `poi_world_optional`, monitor i HTTP.

```bash
pm2 logs chaos --lines 100 --nostream 2>&1 | grep -E 'poi_route|poi_world_optional|poi_maplark_cache'
.venv/bin/python tools/world_collection_monitor.py
```

Odbiór regionalny wymaga VK upstream, a potem VK world dla sąsiedniego skanu,
bez wzrostu liczby prób dla lokalnych odczytów. Sukces MapLark po awarii VK
potwierdza fallback, nie regionalny PASS. Wtedy nie powtarzać serii zapytań.
Restart i współbieżność czterech procesów są sprawdzone lokalnie; na VPS
po reload powtórzyć ten sam punkt przed upływem ważności, jeśli VK odpowiedział.
Sprawdzić też brak regresji skanu, hakowania i terytoriów. Po odbiorze `pm2 save`.

## Rollback regionalnej sieci

```bash
pm2 startOrReload ecosystem.web.config.js --only chaos --env world_visits --update-env
```

Wyłącza regionalne fills i wide fetch, zachowuje exact world oraz ruch graczy.
Aby wrócić również do samego MapLark, w panelu hierarchii live POI zapisać
łańcuch z samym MapLark. Nie odtwarzać starego backupu nad pracującą księgą.

## Granice odbioru

- MapLark bbox POI jest archiwum pełnych filtrów, ale jego selekcja radius
  nie ma jeszcze dowodu równoważności dla lokalnego skanu sąsiedniego.
- Geoapify commercial pozostaje alternatywą obserwacyjną; nie pełnym skanerem.
- Natural Earth 5.1.1: lokalny ekstraktor i rzeczywista próbka ląd–morze
  MultiPolygon przetestowane. Skala 1:10 mln, bez użycia w mechanikach gry;
  nie jest to dowód wieloczęściowej wody śródlądowej MapLark.
- Produkcyjny odbiór regionalny i powyższe kwalifikacje pozostają osobnymi
  pozycjami. Nie oznaczać całego 163.5 jako ukończonego wyłącznie po HTTP 200.
