# Profile Store Migration Manual

Sprint: 130.5

Cel: bezpiecznie przeniesc gorace scope'y runtime z `users.profile_json` do
dedykowanych store'ow wprowadonych w Sprintach 130.1-130.4.

Narzedzie:

```bash
python tools/profile_store_migration.py
```

Domyslna baza:

```bash
data/game.sqlite3
```

Mozna podac inna baze przez:

```bash
--db /sciezka/do/game.sqlite3
```

## Zasady

* Najpierw zawsze `audit`.
* Przed zapisem zawsze `backup`.
* `dry-run` nie zmienia bazy.
* Kazda komenda zapisujaca wymaga `--write`.
* Produkcyjna migracja wymaga `--backup-manifest`.
* `--allow-without-backup` jest tylko awaryjne i nie powinno byc standardem.
* Nie uruchamiac dwoch migracji rownolegle.
* Dla `migrate-all` najlepiej uzyc okna maintenance albo niskiego ruchu.

## Quick Manual Na Serwerze

Wejscie do katalogu aplikacji:

```bash
cd ~/app/chaos
source .venv/bin/activate
```

Audit bez zmian w bazie:

```bash
python tools/profile_store_migration.py audit --db data/game.sqlite3
```

Backup bazy:

```bash
python tools/profile_store_migration.py backup \
  --db data/game.sqlite3 \
  --backup-dir data/backups/profile_store_migration
```

Polecenie wypisze sciezke `manifest`. Zachowac ja do kolejnych krokow.

Dry-run calej bazy:

```bash
python tools/profile_store_migration.py dry-run --db data/game.sqlite3
```

Dry-run jednego konta:

```bash
python tools/profile_store_migration.py dry-run \
  --db data/game.sqlite3 \
  --username main
```

Migracja jednego konta:

```bash
python tools/profile_store_migration.py migrate-user \
  --db data/game.sqlite3 \
  --username main \
  --write \
  --backup-manifest data/backups/profile_store_migration/PROFILE_STORE_MANIFEST.json
```

Weryfikacja jednego konta:

```bash
python tools/profile_store_migration.py verify-user \
  --db data/game.sqlite3 \
  --username main
```

Migracja calej bazy partiami:

```bash
python tools/profile_store_migration.py migrate-all \
  --db data/game.sqlite3 \
  --write \
  --backup-manifest data/backups/profile_store_migration/PROFILE_STORE_MANIFEST.json \
  --batch-size 10 \
  --sleep-seconds 1 \
  --max-errors 1
```

Wznowienie przerwanej migracji:

```bash
python tools/profile_store_migration.py resume \
  --db data/game.sqlite3 \
  --write \
  --backup-manifest data/backups/profile_store_migration/PROFILE_STORE_MANIFEST.json \
  --batch-size 10
```

Raport:

```bash
python tools/profile_store_migration.py report --db data/game.sqlite3
```

Rollback jednego konta:

```bash
python tools/profile_store_migration.py rollback-user \
  --db data/game.sqlite3 \
  --username main \
  --write \
  --backup-manifest data/backups/profile_store_migration/PROFILE_STORE_MANIFEST.json
```

Rollback calego `migration_id`:

```bash
python tools/profile_store_migration.py rollback-all \
  --db data/game.sqlite3 \
  --write \
  --backup-manifest data/backups/profile_store_migration/PROFILE_STORE_MANIFEST.json \
  --migration-id profile-store-130-5
```

## Checklist Operatora

1. Potwierdzic sciezke bazy.
2. Uruchomic `audit`.
3. Sprawdzic warningi i konta `FAILED`.
4. Uruchomic `backup`.
5. Zachowac sciezke manifestu.
6. Uruchomic `dry-run`.
7. Zaczac od `migrate-user` dla jednego konta testowego.
8. Uruchomic `verify-user`.
9. Dopiero potem `migrate-all` partiami.
10. Po migracji uruchomic `verify-all` i `report`.
11. Przetestowac login, mape, terminal, desktop, wallet, storage, apps,
    operacje, system messages i target.

## Status Bezpieczenstwa

Narzędzie nie usuwa legacy pol z `profile_json`.

Narzędzie nie wlacza `store_primary`.

Narzędzie przygotowuje produkcyjny cutover, ale nie wykonuje deployu ani commita.
