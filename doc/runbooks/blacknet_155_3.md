# 155.3 — wdrożenie języków źródeł BlackNet

Stan 14 X 2026: pakiet lokalny. Nie wykonywano komend na produkcji.
Bez drugiej instancji gry, bez dodatkowego portu, bez zatrzymywania rozgrywki
na generacje LLM. Odbiór nowych publikacji pozostaje w normalnym gameplayu.

## Zmiana i przełączniki

- Pakiet tekstów i JS `155.3.0`: etykiety kart w języku UI, oryginał publikacji
  w jednym języku. Pole `signal_language` w kreatorach oraz marce GhostLaba.
- `CHAOS_BLACKNET_LANGUAGES_ENABLED=1` włącza nowy wybór źródła i trwałe przypisanie
  języka. Domyślnie wyłączony. Wymaga tabeli `blacknet_signal_languages`.
- `CHAOS_NARRATIVE_LOCALES=pl,en` dopuszcza oba języki nowych neutralnych sygnałów.
  Nie zmienia języka wcześniej przypisanych sygnałów. ANY nie jest locale.
- Flaga wariantów News pozostaje osobną konfiguracją. Nie włączać jej tym runbookiem.
- Mistral pozostaje według konfiguracji admina; sekret i limity bez zmian.

Tabela przechowuje tylko kontrakt języka dla ID sygnału i wersji jego źródła.
Publiczne ID sygnału, klucze publikacji, read cursor i nagrody pozostają bez zmian.
Przełączenie audycji w tym samym slocie może zmienić język nowej treści; retry tej
samej audycji lub wydania produktu nie wybiera języka ponownie.

## Przygotowanie kodu i spójny backup

Komendy wykonuje operator po decyzji wdrożeniowej. Przed pull potwierdzić brak
zmian w śledzonych plikach; nie usuwać lokalnych danych ani nie robić `git reset`.

```bash
cd ~/app/chaos
git status --short
git pull --ff-only
umask 077
export BN_BACKUP="$HOME/chaos-backups/155-3-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BN_BACKUP"
git rev-parse HEAD > "$BN_BACKUP/deployed-commit"
pm2 jlist > "$BN_BACKUP/pm2-before.json"
.venv/bin/python - <<'PY'
import os, sqlite3
from contextlib import closing
from pathlib import Path
destination = Path(os.environ['BN_BACKUP']) / 'game.sqlite3'
with closing(sqlite3.connect('file:data/game.sqlite3?mode=ro', uri=True)) as source:
    with closing(sqlite3.connect(destination)) as backup:
        source.backup(backup, pages=512, sleep=0.05)
        assert backup.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert not backup.execute('PRAGMA foreign_key_check').fetchall()
print('backup: ok')
PY
```

Spodziewane: fast-forward albo brak nowych zmian; `backup: ok`.
SQLite Backup API obejmuje zatwierdzone dane WAL i daje spójny obraz podczas gry.
Plik PM2 zawiera sekrety — nie wklejać jego zawartości do rozmowy ani raportu.

## Dry-run, migracja i kontrola

```bash
.venv/bin/python tools/blacknet_language_migrate.py inventory --db data/game.sqlite3
.venv/bin/python tools/blacknet_language_migrate.py migrate --db data/game.sqlite3
```

Spodziewane: `ok:true`, `applied:false`, `integrity:"ok"`, `foreign_keys:"ok"`,
`published:false`. Raport `declarations` pokazuje języki i `unknown` w istniejących
projektach, wydaniach, publikacjach oraz instalacjach. Unknown nie oznacza ANY.
Nie jest to automatyczny audyt języka całego tekstu historii.

```bash
.venv/bin/python tools/blacknet_language_migrate.py migrate --db data/game.sqlite3 --apply
.venv/bin/python tools/blacknet_language_migrate.py check --db data/game.sqlite3
```

Spodziewane: apply `ok:true`, potem check `ledger_exists:true`, integralność OK.
Pole `ledger_exists` w wyniku apply opisuje stan wejściowy. Powtórzenie migracji
nie dopisuje publikacji ani nie przepisuje produktów. Zapis jest jedną krótką
transakcją DDL. Błąd na którymkolwiek etapie → nie włączać flagi emisji.

## Kontrolowane włączenie

Po migracji i zatwierdzeniu obu języków poniższy kod aktualizuje tylko obecnie
działające procesy CHAOS. Nie uruchamia zatrzymanych workerów i nie dotyka innych
aplikacji serwera. Ich późniejsze uruchomienie wymaga tych samych flag.

```bash
.venv/bin/python - <<'PY'
import json, os, subprocess
rows = json.loads(subprocess.check_output(['pm2', 'jlist'], text=True))
allowed = {'chaos', 'chaos-territory-worker', 'chaos-ollama-worker', 'chaos-narrative-publisher'}
names = [row['name'] for row in rows if row.get('name') in allowed
         and row.get('pm2_env', {}).get('status') == 'online']
assert 'chaos' in names, 'Web nie jest online; sprawdź stan przed kontynuacją'
env = dict(os.environ, CHAOS_BLACKNET_LANGUAGES_ENABLED='1', CHAOS_NARRATIVE_LOCALES='pl,en')
subprocess.run(['pm2', 'restart', *names, '--update-env'], env=env, check=True)
print('Zaktualizowano:', ', '.join(names))
PY
pm2 ls
```

Spodziewane: wymienione procesy online; wcześniej zatrzymane pozostają zatrzymane.
Restart web to krótka przerwa procesowa, nie wielogodzinne wyłączenie gry.
Jeśli narracyjne workery są zatrzymane, karty deterministyczne działają, ale nowych
publikacji modeli nie będzie — nie oznaczać ich wtedy jako sprawdzonych w gameplayu.
Po potwierdzeniu konfiguracji `pm2 save`; zachować uprawnienia dumpu i backupu 600.

## Odbiór

EN: CHANNELS ONLINE, TRACKS ON AIR, systemowe etykiety pozostałych kart;
przełączenie PL/EN zachowuje tytuł publikacji i CTA. Radio PL → tekst PL,
radio EN → EN, nieznane audio nie udaje neutralnego. Brak kwalifikowanej audycji
nie blokuje pozostałych kart. Nowy kreator: PL/EN/ANY → zapis → publikacja → zakup
→ instalacja. Starsza instalacja zachowuje poprzednią deklarację po nowym wydaniu.
Log `blacknet_language_rejected` podaje powód pominięcia nowej kandydatury.

Ollama: dowód lokalny obejmuje odrzucenie/timeout/zły JSON → zatwierdzony szablon
PL/EN → jedną publikację; ponowienie ma `duplicate:true`. Nie uruchamiać wielogodzinnej
macierzy realnego modelu w celu poprawienia stylu. Mistral/News/historia: odbiór
rzeczywistych nowych treści w grze. Show/Sender: naturalny cykl, około dwóch tygodni.

## Rollback

Przy problemie z nową kwalifikacją ustawić `CHAOS_BLACKNET_LANGUAGES_ENABLED=0`
i zrestartować tylko działające procesy analogicznie do powyższego skryptu.
Zachować wcześniejsze ustawienie `CHAOS_NARRATIVE_LOCALES` ze snapshotu, nie zakładać
automatycznie PL. Nie usuwać tabeli z zapisanymi wyborami: czytniki zachowują
kompatybilność ze starymi zadaniami v1 i nowymi kontraktami.

```bash
.venv/bin/python tools/blacknet_language_migrate.py rollback --db data/game.sqlite3
```

Spodziewane: tylko raport, `applied:false`. Jeżeli tabela jest pusta i flaga
wyłączona, można wykonać tę samą komendę z `--apply`. Zajęta tabela powoduje
`ledger_in_use_keep_for_existing_signals` — to celowa odmowa usunięcia historii
wyborów. Przywrócenie całej bazy nie jest standardową ścieżką rollbacku po
wznowieniu gry, ponieważ skasowałoby nowsze działania graczy.

Historyczne produkty i UGC pozostają bez zmian. Potwierdzone 9 polskich audycji
już ma metadane PL; nie wymagają kolejnego backfillu. Brakujące deklaracje autora
uzupełnia nowe wydanie produktu, nie automatyczna migracja instalacji.
