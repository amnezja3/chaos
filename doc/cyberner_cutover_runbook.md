# Cyberner shared channels — runbook cutoveru

Sprint 130.8.7.4 przygotowuje cutover, ale go automatycznie nie wykonuje.
Migracje są addytywne i nie usuwają tabeli `chat_messages` ani danych legacy.

## Kontrakt po cutoverze

* `WORLD` — jeden rekord wiadomości w `cyberner_world_messages`, widoczny dla
  całej gry.
* `KLAN` — jeden rekord w `cyberner_clan_messages`, izolowany przez `clan_key`.
* `ZNAJOMI` i direct — nadal lokalny `MailStore`; nie zależą od shared stores.
* unread `WORLD`/`KLAN` — cursor per użytkownik i kanał.
* delta `cyberner.message_created` — szybka dostawa; GET historii i polling są
  recovery i deduplikują po `message_id`.

## Bezpieczna kolejność produkcyjna

1. Wdrożyć kod z czterema flagami ustawionymi na `0`.
2. Na czas migracji zatrzymać proces zapisujący wiadomości. Zapobiega to
   powstaniu wpisów legacy między skanem migracji a włączeniem nowego store'a.
3. Wykonać kopię pliku SQLite wraz z WAL/SHM, jeśli istnieją.
4. Uruchomić dry-run:

   ```bash
   ./.venv/bin/python scripts/db_migrations/run_migrations.py --db data/game.sqlite3
   ```

5. Uruchomić migracje:

   ```bash
   ./.venv/bin/python scripts/db_migrations/run_migrations.py --db data/game.sqlite3 --only 005,006 --apply
   ```

   Produkcyjny cutover Cybernera używa `--only 005,006`. Nie wolno przy okazji
   zastosować starszych, oczekujących migracji profili `002`–`004` bez ich
   osobnego audytu.

6. Zweryfikować read modele i cursory:

   ```bash
   ./.venv/bin/python scripts/audit_cyberner_cutover.py --db data/game.sqlite3 --strict
   ```

7. Dopiero po wyniku `"ok": true` ustawić wszystkie flagi na `1` i uruchomić
   proces z odświeżonym środowiskiem:

   ```text
   CHAOS_CYBERNER_CHANNEL_STORE_ENABLED=1
   CHAOS_CYBERNER_WORLD_STORE_ENABLED=1
   CHAOS_CYBERNER_CLAN_STORE_ENABLED=1
   CHAOS_CYBERNER_LIVE_DELIVERY_ENABLED=1
   ```

## Cursor baseline

Migracja `006` oznacza zmigrowaną historię jako przeczytaną dla istniejących
użytkowników. Historia pozostaje dostępna, ale nie generuje po cutoverze lawiny
starych unreadów. `INSERT OR IGNORE` nie cofa cursorów utworzonych wcześniej.

## Obserwowalność

Monitorować wpisy:

* `[CYBERNER_SEND]` — commit, kanał, nadawca, liczba odbiorców i replay;
* `[CYBERNER_DELTA]` — błąd dostawy live po commicie;
* `[CYBERNER_NOTIFY]` — błąd notyfikacji po commicie;
* `[CYBERNER_READ]` — izolowany błąd odczytu konkretnego kanału.

Kontrola funkcjonalna: dwóch graczy w różnych klanach widzi ten sam `WORLD`,
dwóch z jednego klanu widzi ten sam `KLAN`, obcy klan go nie widzi, a kanał
`ZNAJOMI` nadal działa po wyłączeniu shared stores.

## Rollback

Natychmiastowy rollback polega na ustawieniu czterech flag na `0` i restarcie z
odświeżonym środowiskiem. Przywraca legacy routing bez cofania migracji i bez
utraty danych w shared tables.

Wiadomości zapisane już po cutoverze pozostają bezpieczne w shared tables, ale
nie są widoczne w legacy UI podczas rollbacku. Nie wolno usuwać shared tables;
po ponownym włączeniu flag wiadomości wracają. Pełne materializowanie nowych
shared wiadomości do starego fanoutu jest osobną operacją awaryjną i nie jest
wykonywane automatycznie.
