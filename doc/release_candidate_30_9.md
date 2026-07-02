# Release Candidate 30.9 — przygotowanie wdrożenia

Data: 02.07.2026

Status: dokument przygotowawczy przed commitem, pushem i wdrożeniem serwerowym po Sprintach 21–30.5.

Sprint 30.9 nie dodaje funkcjonalności gameplayowych. Jego celem jest opisanie bezpiecznej ścieżki:

```text
commit
↓
push
↓
pull na serwerze
↓
narzędzia migracyjne
↓
restart PM2
↓
gameplay smoke
```

## Zakres zmian Sprintów 21–30.5

### App Contract i katalog aplikacji

Sprinty 21–21.5 uporządkowały kontrakt aplikacji jako runtime checklistę:

* pola UI: `interface`, `type`, `tags`, opis, nazwa;
* pola gameplayowe: `map_actions`, `target_types`, `operation_types`, `resource_types`;
* pola ekonomiczno-storage: `file_size`, `disk_usage`, `install_size`;
* pola jakości: `creator_power`, `quality_score`, `reliability`;
* pola balansu: `power_score`, `price_hint`, `balance_tier`, `recommended_level`, `recommended_respect`;
* pola źródła: `map_actions_source`, `tool_family`, `tool_mode`.

Źródłem runtime katalogu aplikacji jest SQLite `json_resources.app_config`. Pliki `static/*.json` są seed/reference i nie aktualizują runtime bez jawnego syncu.

### Storage

Sprint 22 dodał miękki model pojemności:

* `profile.storage_capacity`;
* `profile.storage_used`;
* `profile.storage_unit`;
* `profile.storage_soft_limit`;
* `profile.storage_over_limit`;
* `file.file_size`;
* `app.disk_usage` / `install_size`.

Model jest miękki: brak miejsca nie blokuje jeszcze instalacji ani zapisu pliku.

### Quality i creator power

Sprint 23 dodał:

* `creator_power`;
* `quality_score`;
* `reliability`;
* wpływ jakości aplikacji na jakość/kompletność tworzonych plików;
* testy low-level vs high-level creator.

### Map tool classification

Sprint 24 uporządkował klasyfikację narzędzi mapy:

* jawne `app.map_actions` wygrywa;
* legacy fallback po `type/detects/interferes_with` jest tylko migracją;
* aplikacje z `tool_family` kreatora nie powinny dostawać przypadkowych `map_actions` z fallbacku;
* PenCombo/exploit_suite nie powinno wracać jako `scan_ports`.

### Kreatory i Tool Laboratory

Sprinty 25–27 rozwinęły istniejące kreatory, bez tworzenia nowego publish flow:

* ButtonMaker;
* TermCreator;
* WindowMaker;
* AppForge.

Kreatory korzystają dalej z `/api/apps/generate`. Dodano ścieżki:

* Scanner / Recon;
* Exploit;
* Sniffer;
* tryby: mapowy, desktopowy na `aimed_target`, hybrydowy.

Sprint 30.5 dodał prowadzoną narrację kroków kreatora, ale nie zmienił kontraktu backendowego.

### GhostLab

Sprint 28 dopasował GhostLab/pro-system-tools do tego samego kontraktu aplikacji:

* publish trafia do tego samego katalogu Googleplex;
* pro-system-tools mają storage, quality, reliability i wymagania;
* `runtime_status: pending_custom_runtime` pozostaje świadomym ograniczeniem dla custom runtime.

### Balance i pricing

Sprint 29 dodał pierwszy miękki balance pass:

* `power_score`;
* `price_hint`;
* `balance_tier`;
* rekomendowane wymagania level/respect.

`price_hint` jest wskazówką balansu, nie drugim systemem cen. Istniejące seed/legacy ceny nie są automatycznie nadpisywane poza generated/pro-system przypadkami, gdzie wymaga tego spójność.

### Lifecycle i uninstall

Sprint 30 domknął Tool Laboratory v1:

```text
creator / GhostLab
↓
publish
↓
json_resources.app_config
↓
Googleplex
↓
install
↓
profile.apps + files.tools
↓
/tools
↓
runtime mapy / desktop
↓
uninstall
```

Uninstall:

* usuwa aplikację z `profile.apps`;
* usuwa odpowiadający wpis z `files.tools`;
* przelicza `storage_used`;
* nie usuwa projektów z `files.projects`;
* nie usuwa publikacji z `json_resources.app_config`;
* jest idempotentny dla brakującej aplikacji.

## Audyt gotowości

| Obszar | Status | Uwagi |
| --- | --- | --- |
| Backend app contract | Gotowy do RC | Normalizacja obejmuje storage, quality, balance i map actions. |
| Frontend Googleplex | Gotowy do RC | Pokazuje kontrakt, wagę, jakość, niezawodność i balans. |
| File Manager `/tools` | Gotowy do RC | Pokazuje storage i umożliwia uninstall. |
| Kreatory | Gotowe do RC | Guided UX jest warstwą nad istniejącym publish flow. |
| GhostLab | Gotowy z ograniczeniem | Publish zgodny z kontraktem; custom runtime nadal `pending_custom_runtime`. |
| Storage | Gotowy jako soft model | Brak twardej blokady miejsca. |
| Quality/pricing | Gotowe jako MVP | Heurystyki wymagają playtestów. |
| Map runtime | Bez przebudowy | Router nadal używa `app.map_actions`; legacy fallback tylko migracyjny. |
| DB migrations | Gotowe jako narzędzia Sprintu 31 | Runner `schema_migrations` istnieje; migracje nadal wymagają dry-run, backupu i apply na serwerze. |
| Stare profile | Kompatybilne przez normalizację | Zalecana migracja utrwalająca nowe pola po deployu. |

## Potencjalne migracje

Sprint 30.9 nie implementuje migracji. Poniższa lista jest materiałem wejściowym dla Sprintu 31.

### 000 — app catalog cleanup and admin seed tools

Cel:

* wyczyścić `json_resources.app_config` ze starych narzędzi testowych/dev;
* usunąć `admin_test_seed` i stare `migration_inferred`, jeśli nie są częścią finalnego zestawu;
* zachować aplikacje generated/player-created;
* zachować GhostLab published apps;
* dodać produkcyjny zestaw `admin_seed_v1`;
* wyczyścić profile z testowych aplikacji;
* wyczyścić orphan `files.tools`;
* przeliczyć `storage_used`;
* nie ruszać `files.projects`.

Skrypt:

```bash
python scripts/app_catalog_cleanup.py --db data/game.sqlite3
python scripts/app_catalog_cleanup.py --db data/game.sqlite3 --apply
```

Ryzyko:

* wysokie, jeśli serwerowy katalog zawiera ręcznie utrzymywane aplikacje bez
  pełnego kontraktu. Najpierw wymagany jest dry-run i backup.

### 001 — schema_migrations

Cel:

* utworzyć tabelę `schema_migrations`;
* zapisywać `id`, `name`, `applied_at`, `script_hash`, `status`, `notes`;
* migrator musi być idempotentny.

Ryzyko:

* niskie, jeśli migracja tworzy tylko nową tabelę.

### 002 — profile storage defaults

Cel:

* dopisać do profili brakujące:
  * `storage_capacity`;
  * `storage_used`;
  * `storage_unit`;
  * `storage_soft_limit`;
  * `storage_over_limit`;
* przeliczyć `storage_used` z `profile.apps` i `profile.files`.

Ryzyko:

* średnie: istniejące profile mogą mieć stare formaty plików/tools.

### 003 — installed apps contract normalization

Cel:

* znormalizować `profile.apps`;
* dopisać brakujące `file_size`, `disk_usage`, `install_size`;
* dopisać `creator_power`, `quality_score`, `reliability`;
* dopisać `power_score`, `price_hint`, `balance_tier`;
* zachować stare pola `type`, `detects`, `affects`, `interferes_with`.

Ryzyko:

* średnie: nie wolno usuwać legacy pól ani nadpisywać ręcznych wartości.

### 004 — files.tools reconciliation

Cel:

* porównać `profile.apps` z `files.tools`;
* dodać brakujące wpisy tools dla zainstalowanych aplikacji;
* oznaczyć orphan tools do review zamiast usuwać agresywnie;
* nie ruszać `files.projects`.

Ryzyko:

* średnie: stare konta mogą mieć ręcznie stworzone pliki tools.

### 005 — app catalog sync

Cel:

* porównać `static/app_config.json` z `json_resources.app_config`;
* uruchomić dry-run;
* wykonać sync tylko po świadomej decyzji:

```bash
python tools/sync_static_json_resources.py --db data/game.sqlite3 --static-dir static --apply --key app_config
```

Ryzyko:

* wysokie, jeśli serwerowy katalog ma ręcznie opublikowane aplikacje. Sync statycznego katalogu nie może przypadkiem skasować player-created apps.

Decision:

* Przyjęto: sync `app_config` przed deployem wykonujemy tylko po sprawdzeniu dry-run i backupie DB.

## Kolejność wdrożenia

```text
1. commit lokalny
2. push
3. pull na serwerze
4. sprawdzenie APP_ENV / CHAOS_DEV_MODE / konfiguracji PM2
5. backup data/game.sqlite3
6. dry-run app catalog cleanup
7. apply app catalog cleanup po akceptacji raportu
8. dry-run migracji DB
9. apply migracji DB
10. opcjonalny dry-run/apply sync static JSON resources
11. restart PM2
12. gameplay smoke
13. obserwacja logów
```

## Szkice komend wdrożeniowych

### Backup bazy

Linux:

```bash
mkdir -p data/backups
cp data/game.sqlite3 data/backups/game_$(date +%Y%m%d_%H%M%S)_before_rc_30_9.sqlite3
```

PowerShell:

```powershell
New-Item -ItemType Directory -Force data/backups
Copy-Item data/game.sqlite3 ("data/backups/game_{0}_before_rc_30_9.sqlite3" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
```

### Sync statycznych JSON-ów do SQLite

Dry-run:

```bash
python tools/sync_static_json_resources.py --db data/game.sqlite3 --static-dir static
```

Tylko `app_config`, zapis:

```bash
python tools/sync_static_json_resources.py --db data/game.sqlite3 --static-dir static --apply --key app_config
```

### Przyszły runner migracji

Sprint 31 dostarcza docelową komendę w tym stylu:

```bash
python scripts/db_migrations/run_migrations.py --db data/game.sqlite3
python scripts/db_migrations/run_migrations.py --db data/game.sqlite3 --apply
```

Nie uruchamiać ad hoc migracji na produkcyjnej bazie bez osobnego skryptu i backupu.

### App Catalog Cleanup

Dry-run:

```bash
python scripts/app_catalog_cleanup.py --db data/game.sqlite3
```

Apply:

```bash
python scripts/app_catalog_cleanup.py --db data/game.sqlite3 --apply
```

Raport skryptu pokazuje:

* ile aplikacji usuwa z katalogu;
* ile zostawia;
* ile dodaje seedów `admin_seed_v1`;
* ile profili modyfikuje;
* ile wpisów `files.tools` czyści;
* zmianę storage per profil.

### Walidacja techniczna

```bash
python -m py_compile run.py database.py profileManagment.py
python -m unittest tests.test_target_persistence
node --check static/js/terminal.js
git diff --check
```

### Restart PM2

```bash
pm2 restart ecosystem.config.js --update-env
pm2 logs --lines 100
```

Jeżeli serwer używa innej nazwy procesu, nie zmieniać jej podczas deployu. Użyć istniejącej konfiguracji lokalnej `ecosystem.config.js`.

## Deploy checklist

1. Sprawdź branch i tag release candidate.
2. Upewnij się, że `data/game.sqlite3`, `data/backups`, `flask_session` i cache nie są commitowane.
3. Wykonaj `git pull` na serwerze.
4. Sprawdź `APP_ENV`, `CHAOS_DEV_MODE`, `CHAOS_PERF_LOG`, `PORT`.
5. Zrób backup `data/game.sqlite3`.
6. Uruchom testy składniowe, jeśli środowisko serwera ma zależności.
7. Uruchom dry-run `scripts/app_catalog_cleanup.py`.
8. Po akceptacji raportu uruchom `scripts/app_catalog_cleanup.py --apply`.
9. Uruchom dry-run `scripts/db_migrations/run_migrations.py`.
10. Po akceptacji uruchom `scripts/db_migrations/run_migrations.py --apply`.
11. Uruchom dry-run sync JSON resources, jeśli katalog seed ma zostać zsynchronizowany.
12. Restart PM2.
13. Otwórz aplikację i wykonaj gameplay smoke.
14. Sprawdź logi PM2 i `[PERF]`.
15. Dopisz wynik deployu do `doc/project_journal.md`.

## Rollback checklist

1. Zatrzymaj albo wycisz aplikację, jeśli błąd psuje profile.
2. Zachowaj kopię uszkodzonej bazy do analizy.
3. Przywróć ostatni backup:

```bash
cp data/backups/<backup>.sqlite3 data/game.sqlite3
```

4. Cofnij kod do poprzedniego tagu/commita:

```bash
git checkout <previous_tag>
```

5. Restart PM2.
6. Zaloguj admina i wykonaj krótki smoke:
   * desktop;
   * mapa;
   * Googleplex;
   * File Manager;
   * Ghost Exchange.
7. Zanotuj rollback w `doc/project_journal.md`.

## Testy po deployu

### Smoke admin

1. Login admin.
2. Desktop ładuje avatar/profil/toolbar.
3. Googleplex ładuje katalog.
4. Zakup aplikacji działa.
5. `/tools` pokazuje aplikację.
6. File Manager pokazuje storage.
7. Uninstall usuwa aplikację z `/tools` i przelicza storage.
8. Mapa otwiera menu pustego pola i menu targetów bez mieszania.
9. Akcja mapy tworzy operację.
10. Centrum Operacji pokazuje operację.
11. Po finalizacji powstaje plik.
12. Ghost Exchange pokazuje sprzedawalny plik.
13. Sprzedaż dodaje HC, mail i historię rynku.

### Kreatory

1. Otwórz AppForge/TermCreator/WindowMaker/ButtonMaker.
2. Sprawdź, że wizard pokazuje kroki, a nie ścianę pól.
3. Utwórz Scanner / Recon app.
4. Opublikuj przez `/api/apps/generate`.
5. Sprawdź, że aplikacja trafia do Googleplex.
6. Zainstaluj i usuń aplikację.

### GhostLab

1. Otwórz GhostLab.
2. Utwórz/otwórz projekt.
3. Sprawdź preview kontraktu.
4. Compile.
5. Publish.
6. Sprawdź Googleplex i instalację.

### Resource architecture

1. Sprawdź `/resources.json`.
2. Porównaj liczbę aplikacji z `json_resources.app_config`.
3. Nie zakładaj, że edycja `static/app_config.json` zmieni runtime bez syncu.

## Ryzyka

| Ryzyko | Poziom | Zalecenie |
| --- | --- | --- |
| Serwerowe profile nie mają nowych pól storage/quality/balance | Średnie | Runtime normalizuje, ale Sprint 31 powinien utrwalić pola migracją. |
| `json_resources.app_config` na serwerze różni się od `static/app_config.json` | Wysokie | Najpierw dry-run sync i backup; nie nadpisywać katalogu bez decyzji. |
| Ręcznie opublikowane aplikacje w Googleplex | Wysokie | Sync statycznego katalogu może je pominąć; sprawdzić DB przed apply. |
| `files.tools` zawiera stare/orphan wpisy | Średnie | Reconciliation migracja powinna oznaczać do review, nie usuwać agresywnie. |
| `pending_custom_runtime` w GhostLab | Niskie/świadome | To ograniczenie v1, nie błąd deployu. |
| CRLF/LF warnings w plikach static | Niskie | `git diff --check` może pokazać ostrzeżenia; nie są blokujące, jeśli brak whitespace errors. |
| Runner `schema_migrations` jest nowy | Średnie | Najpierw wykonać dry-run na kopii bazy i dopiero potem apply na serwerze. |
| Miękki storage nie blokuje przepełnienia | Niskie/świadome | To decyzja Sprintu 22–30. |
| Balance heurystyczny wymaga playtestów | Niskie/świadome | Obserwować ceny i wagę aplikacji po deployu. |

## Obserwacja po pierwszym uruchomieniu

Monitorować:

* PM2 logs i błędy endpointów:
  * `/resources.json`;
  * `/install-app`;
  * `/api/apps/uninstall`;
  * `/api/apps/generate`;
  * `/api/ghostlab/projects/*/publisher`;
  * `/api/profile`;
  * `/api/operations`.
* `[PERF]` dla:
  * `/api/operations`;
  * `/api/map/player-areas`;
  * `/api/map/player-actors`;
  * `/launch-queue`;
  * `/system-messages`.
* Profile z dużą liczbą starych aplikacji.
* Poprawność `storage_used` po instalacji i uninstallu.
* Czy Googleplex pokazuje generated/GhostLab apps.
* Czy tool selection nie używa legacy fallbacku tam, gdzie aplikacja ma jawne `map_actions`.

## Decision

* Przyjęto: Sprint 30.9 przygotowuje deployment i materiały migracyjne, ale nie wykonuje migracji.
* Przyjęto: właściwy system migracji DB należy do Sprintu 31.
* Przyjęto: przed serwerowym syncem `app_config` wymagany jest backup i dry-run.
* Przyjęto: runtime normalizatory zapewniają kompatybilność starych profili, ale migracja utrwalająca nowe pola jest zalecana przed większym playtestem.
