# Wdrożenie i odbiór szkieletu 140.3

Sceny 08–14 rozwijają istniejący kontroler. Runtime audio nadal należy do 140.4,
oprawa artystyczna do 140.stylization.1+. Wykonuj w ~/app/chaos.
Przy błędzie zatrzymaj procedurę. Testy są izolowane od produkcyjnej bazy.

## 1. Kod i izolowane testy

Po opublikowaniu zmian 140.3:

```bash
git pull --ff-only && git status --short --branch && git rev-parse --short HEAD
.venv/bin/python -B - <<'PY'
import os, shutil, sys, tempfile, unittest
root = os.getcwd()
sys.path[:0] = [root, os.path.join(root, "tests")]
with tempfile.TemporaryDirectory(prefix="chaos140-3-") as tmp:
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
                 "test_ghostnetwork_transmission", "test_ghostnetwork_endgame_audits",
                 "test_ghostnetwork_signal_ranking", "test_ghostnetwork_signal_ranking_http"]
        result = unittest.TextTestRunner().run(
            unittest.defaultTestLoader.loadTestsFromNames(names))
    finally:
        os.chdir(root)
sys.exit(not result.wasSuccessful())
PY
```

Oczekiwane: 64 testy, OK. Następnie:

```bash
node tests/ghost_signal_show_frontend.test.js &&
node tests/ghost_signal_show_recovery.test.js &&
node tests/ghost_signal_show_manifest.test.js &&
node tests/ghost_signal_show_montage.test.js &&
node tests/js/test_ghostnetwork_delta_client.js &&
node --check static/js/ghost_signal_show.js
```

## 2. Stan schematu i reload

Nie ma nowej migracji. Wymagana jest kolumna scene_snapshot_json z 140.2:

```bash
.venv/bin/python -B scripts/migrate_ghostsignal_scene_snapshot.py --db data/game.sqlite3
```

Oczekiwane ok:true i schema_change:false. Jeżeli kolumny brakuje, wróć do
procedury backupu/migracji 140.2; nie uruchamiaj apply bez jej bramki.
Po PASS testów i schematu:

```bash
pm2 reload chaos && pm2 reload chaos-territory-worker && pm2 status
.venv/bin/python -B tools/build_ghostsignal_show_preview.py --output static/previews/ghostsignal-140-3.html
```

Jeżeli plik podglądu już istnieje, użyj nowej nazwy ghostsignal-*.html.
Nie przywracamy bazy ani nie wysyłamy sygnału na potrzeby podglądu.

## 3. Podgląd i smoke

Otwórz https://chaos.dmd-transport.pl/static/previews/ghostsignal-140-3.html.
To dane DEMO, nie fakty produkcyjnego cyklu. Na desktop i mobile sprawdź:

- 495/525 s: geometria zakresu finału przed/po konsumpcji, jawny zakres mapy;
- 555 s: brak wymyślonych stanów preserved/reduced;
- 585 s: archiwalne konflikty;
- 630/660/680/700 s: nagrody, uczestnicy, osiągnięcia z rankingu, klany;
- 720/740/760/780/800/820/835 s: rekonstrukcja systemu i publiczne teksty;
- seek w obie strony i powrót z tła trafiają w odpowiednią scenę;
- wyłączone potwierdzenie sygnału daje waiting zamiast sukcesu;
- regresja wcześniejszych scen i filmu, bez dźwięku w tym podglądzie;
- zwykły pulpit/mapa/logowanie: brak nowych błędów API.

Stare show bez zapisanej projekcji settlement mają jawne oczekiwanie/brak
projekcji; nie pobierają live world ani profili jako zastępstwa. Nowa projekcja
powstaje przy istniejącej finalizacji rankingu. Nie wykonujemy masowego backfillu.
Oceniamy poprawność szkieletu i danych; zmiany estetyczne zapisujemy w draftcie
140.stylization.1+. Przekaż HEAD, wynik testów, PM2 i odbiór podglądu.