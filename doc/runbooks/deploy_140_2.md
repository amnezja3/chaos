# Wdrożenie 140.2

Rozwija istniejące show i jego rekord o `scene_snapshot_json`. Nie uruchamia
nowego finału. Film 38,12 s jest wyciszony, SFX pozostaje przy `ghost.signal_sent`.
Wykonuj w `/home/johndoe/app/chaos`. Zatrzymaj procedurę przy błędzie kroku.

## 1. Kod i izolowane testy

Po opublikowaniu zmian 140.2:

```bash
git pull --ff-only && git status --short --branch && git rev-parse --short HEAD
.venv/bin/python -B - <<'PY'
import os, shutil, sys, tempfile, unittest
root = os.getcwd()
sys.path[:0] = [root, os.path.join(root, "tests")]
with tempfile.TemporaryDirectory(prefix="chaos140-2-") as tmp:
    try:
        os.makedirs(os.path.join(tmp, "static", "js"))
        for name in ("session_generation.js", "terminal.js"):
            shutil.copyfile(os.path.join(root, "static", "js", name),
                            os.path.join(tmp, "static", "js", name))
        shutil.copyfile(os.path.join(root, "run.py"), os.path.join(tmp, "run.py"))
        os.chdir(tmp)
        os.environ["CHAOS_SESSION_FILE_DIR"] = os.path.join(tmp, "sessions")
        names = ["test_ghostnetwork_show_manifest", "test_ghostnetwork_signal_show",
                 "test_ghostnetwork_signal_show_http", "test_ghostnetwork_client_restart",
                 "test_ghostnetwork_transmission", "test_ghostnetwork_endgame_audits"]
        result = unittest.TextTestRunner().run(
            unittest.defaultTestLoader.loadTestsFromNames(names))
    finally:
        os.chdir(root)
sys.exit(not result.wasSuccessful())
PY
```

Oczekiwane: 54 testy, OK. Następnie:

```bash
node tests/ghost_signal_show_frontend.test.js &&
node tests/ghost_signal_show_recovery.test.js &&
node tests/ghost_signal_show_manifest.test.js &&
node tests/ghost_signal_show_montage.test.js &&
node tests/js/test_ghostnetwork_delta_client.js &&
node --check static/js/ghost_signal_show.js
```

## 2. Plan, backup, migracja

```bash
.venv/bin/python -B scripts/migrate_ghostsignal_scene_snapshot.py --db data/game.sqlite3
```

Oczekiwane: `ok:true`, `historical_backfill:false`. Plan może już wskazywać
`schema_change:false`; migracja jest idempotentna. Przed apply wykonaj backup:

```bash
.venv/bin/python -B - <<'PY'
import hashlib, sqlite3
from pathlib import Path
from datetime import datetime, timezone
from contextlib import closing
src = Path("data/game.sqlite3").resolve()
dst = src.parent / "backups" / ("pre-140-2-" +
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".sqlite3")
dst.parent.mkdir(parents=True, exist_ok=True)
with closing(sqlite3.connect(src.as_uri() + "?mode=ro", uri=True)) as source:
    with closing(sqlite3.connect(str(dst))) as backup:
        source.backup(backup)
        result = backup.execute("PRAGMA quick_check").fetchall()
        if result != [("ok",)]:
            raise RuntimeError(result)
digest = hashlib.sha256()
with dst.open("rb") as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
print("BACKUP:", dst)
print("quick_check: ok")
print("SHA-256:", digest.hexdigest())
PY
```

Po poprawnym backupie:

```bash
.venv/bin/python -B scripts/migrate_ghostsignal_scene_snapshot.py --db data/game.sqlite3 --apply &&
.venv/bin/python -B scripts/migrate_ghostsignal_scene_snapshot.py --db data/game.sqlite3
```

Ostatni wynik musi mieć `schema_change:false`. Migracja dodaje jedną kolumnę,
bez przepisywania historycznych show i bez ciężkiego profilu.

## 3. Reload i podgląd

```bash
pm2 reload chaos && pm2 reload chaos-territory-worker && pm2 status
.venv/bin/python -B tools/build_ghostsignal_show_preview.py --output static/previews/ghostsignal-140-2-video.html
```

Oba procesy powinny być online. Generator nie nadpisuje istniejącej strony;
przy powtórzeniu użyj nowej nazwy `ghostsignal-*.html`. Otwórz:

`https://chaos.dmd-transport.pl/static/previews/ghostsignal-140-2-video.html`

Podgląd używa jawnie demonstracyjnych danych, bez bazy, eventów i API gry.
Na desktop i mobile sprawdź:

- zwykłe logowanie/pulpit/mapę: brak nowych błędów API;
- części, cztery grupy, ring oraz cztery maszyny: czytelność i brak scrolli;
- film od 425 s oraz seek w 435 i 450 s: właściwy moment, proporcje, bez audio;
- przejście 463,12 s do replayu, terminal i potwierdzenie do 480 s;
- wyjście ze sceny filmu oraz powrót do karty: brak pozostawionego odtwarzania;
- brak SFX przy seek, waiting po wyłączeniu potwierdzenia w scenie replay;
- po zablokowaniu żądania MP4 w DevTools: tekst zastępczy, show działa dalej.

Przekaż HEAD, wyniki testów/migracji i wynik podglądu. Dopiero odbiór
desktop/mobile zamyka 140.2. Pełny produkcyjny finał pozostaje w 140.5.
