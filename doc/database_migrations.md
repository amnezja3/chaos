# Database Migrations

Ten dokument opisuje zasady migracji runtime SQLite w CHAOS.

`data/game.sqlite3` jest bazą runtime i nie jest źródłem prawdy w Git. Każda
zmiana struktury danych albo większa normalizacja profili musi mieć własny,
idempotentny skrypt.

## Zasada główna

```text
git pull
↓
backup DB
↓
dry-run migracji
↓
apply migracji
↓
schema_migrations
↓
restart PM2
↓
gameplay smoke
```

## Kolejność Sprintu 31

Przed klasycznymi migracjami wykonujemy cleanup katalogu aplikacji.

```text
1. app catalog cleanup
2. schema_migrations runner
3. profile storage defaults
4. installed apps normalization
5. files.tools reconciliation
6. optional static JSON resource sync
7. smoke-check
```

## App Catalog Cleanup

Skrypt:

```text
scripts/app_catalog_cleanup.py
```

Cel:

* czyści `json_resources.app_config` ze starych narzędzi testowych;
* usuwa `admin_test_seed`;
* usuwa stare `migration_inferred`, jeśli nie są częścią finalnego zestawu;
* zachowuje aplikacje generated/player-created;
* zachowuje GhostLab published apps;
* dodaje produkcyjny zestaw `admin_seed_v1`;
* czyści profile graczy z testowych aplikacji;
* czyści orphan `files.tools`;
* nie rusza `files.projects`;
* przelicza `storage_used`.

Tryby:

```bash
python scripts/app_catalog_cleanup.py --db data/game.sqlite3
python scripts/app_catalog_cleanup.py --db data/game.sqlite3 --apply
```

Domyślnie skrypt działa jako dry-run. Zapis wymaga `--apply`.

Przy `--apply` skrypt tworzy backup bazy w `data/backups`.

## admin_seed_v1

`admin_seed_v1` oznacza produkcyjny zestaw narzędzi startowych opublikowanych
przez konto admin/CyberPhoenix.

Wymagane pola:

* `purchase_account: admin`;
* `creator_username: admin`;
* `creator_nick`;
* `creator_level_at_publish: 80`;
* `creator_power`;
* `quality_score`;
* `reliability`;
* `map_actions_source: admin_seed_v1`;
* `generated: false`;
* `published: true`;
* jawne `map_actions`, `target_types`, `operation_types`, `resource_types`;
* `file_size`, `disk_usage`, `install_size`;
* `price`, `required_level`, `required_respect`, `balance_tier`.

Po cleanupie każda istotna akcja mapy powinna mieć co najmniej jedno narzędzie.

## Runner migracji

Runner:

```text
scripts/db_migrations/run_migrations.py
```

Komendy:

```bash
python scripts/db_migrations/run_migrations.py --db data/game.sqlite3
python scripts/db_migrations/run_migrations.py --db data/game.sqlite3 --apply
```

Runner:

* tworzy `schema_migrations`, jeśli trzeba;
* wykrywa pliki `NNN_*.py`;
* pomija migracje już zapisane w `schema_migrations`;
* domyślnie działa jako dry-run;
* zapisuje stan dopiero przy `--apply`.

## Migracje Sprintu 31

| ID | Nazwa | Cel |
| --- | --- | --- |
| `001` | `schema_migrations table` | Tworzy tabelę stanu migracji. |
| `002` | `profile storage defaults` | Dodaje/przelicza storage w profilach. |
| `003` | `installed apps contract normalization` | Utrwala nowe pola kontraktu w `profile.apps`. |
| `004` | `files.tools reconciliation` | Czyści orphan tools i dopisuje brakujące wpisy tools dla zainstalowanych apps. |

## Optional app_config sync

Sync statycznego katalogu do SQLite nie jest migracją profili.

Używać osobnego narzędzia:

```bash
python tools/sync_static_json_resources.py --db data/game.sqlite3 --static-dir static
python tools/sync_static_json_resources.py --db data/game.sqlite3 --static-dir static --apply --key app_config
```

Zasada:

* najpierw dry-run;
* backup przed apply;
* nie nadpisywać katalogu, jeśli serwer ma player-created/GhostLab apps bez
  świadomej decyzji.

## Rollback

Domyślny rollback to przywrócenie backupu bazy.

Migracje JSON profili nie powinny usuwać danych graczy tylko po to, żeby mieć
prosty rollback.

## Checklist deploy

1. `git pull`.
2. Sprawdź `.env`/PM2/APP_ENV.
3. Backup `data/game.sqlite3`.
4. `python scripts/app_catalog_cleanup.py --db data/game.sqlite3`.
5. Po akceptacji raportu: `python scripts/app_catalog_cleanup.py --db data/game.sqlite3 --apply`.
6. `python scripts/db_migrations/run_migrations.py --db data/game.sqlite3`.
7. Po akceptacji: `python scripts/db_migrations/run_migrations.py --db data/game.sqlite3 --apply`.
8. Opcjonalny sync `app_config` tylko po dry-run.
9. Restart PM2.
10. Gameplay smoke admina.

## Decision

* Przyjęto: katalog aplikacji czyścimy przed standardowymi migracjami.
* Przyjęto: `admin_seed_v1` jest produkcyjnym seedem narzędzi, nie testowym
  `admin_test_seed`.
* Przyjęto: migracje są idempotentne i domyślnie dry-run.
* Przyjęto: usuwanie danych wymaga backupu i `--apply`.
