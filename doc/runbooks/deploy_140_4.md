# Wdrożenie i odsłuch 140.4

Zakres: cztery MP3 w istniejącym GhostRadio, audio filmu, miks 0,5 s,
ranking 14–15 i przejście do restartu. Baza i kontrakt 139 pozostają bez zmian.
Pracuj w ~/app/chaos; przerwij procedurę przy błędzie kroku.
## 1. Kod i izolowane testy

Po opublikowaniu zmian 140.4:

```bash
git pull --ff-only && git status --short --branch && git rev-parse --short HEAD
.venv/bin/python -B - <<'PY'
import os, shutil, sys, tempfile, unittest
root = os.getcwd()
sys.path[:0] = [root, os.path.join(root, "tests")]
with tempfile.TemporaryDirectory(prefix="chaos140-4-") as tmp:
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
node tests/ghost_signal_show_audio.test.js &&
node tests/js/test_game_sfx.js &&
node --check static/js/ghost_radio.js &&
node --check static/js/ghost_signal_show.js
```

## 2. Reload i pełny podgląd z audio

Po PASS sprawdź dotychczasowy schemat (bez apply):

```bash
.venv/bin/python -B scripts/migrate_ghostsignal_scene_snapshot.py --db data/game.sqlite3
```

Oczekiwane schema_change:false. Nie ma nowej migracji.

```bash
pm2 reload chaos && pm2 reload chaos-territory-worker && pm2 status
.venv/bin/python -B tools/build_ghostsignal_show_preview.py --output static/previews/ghostsignal-140-4.html
```

Przy istniejącym pliku wybierz nową nazwę ghostsignal-*.html.
Otwórz https://chaos.dmd-transport.pl/static/previews/ghostsignal-140-4.html.
To nadal dane demonstracyjne, ale prawdziwe pliki video i cztery MP3.
Nie traktuj tego jako odbioru rzeczywistych danych finału. Pełna walidacja
projekcji z produkcyjnego finału pozostaje bramką 140.5.

## 3. Odsłuch desktop/mobile

Jeśli autoplay został zablokowany, użyj przycisku „Włącz dźwięk” w show.
Film nie ma własnych kontrolek. Globalny mute dotyczy tła i audio filmu.
Podgląd nie emituje ghost.signal_sent, więc nie ponawia jego SFX.

- Obejrzyj całe 15 minut bez przewijania: dopiero teraz oceń tempo i muzykę.
- Granice MP3: 203,702813 s; 414,667688 s; 686,370938 s czasu show.
- Od 425 do 425,5 s muzyka wygasa równolegle z początkiem AAC filmu.
- Od 425,5 do 463,12 s MP3 jest zatrzymane; działa audio filmu.
- Od 463,12 do 463,62 s MP3 wraca od pozycji 425,5 s ścieżki, z fade-in 0,5 s.
- Muzyka kończy się około 897,675376 s; około 2,325 s ciszy przed końcem zegara.
- Sprawdź seek do środka każdego pliku/filmu, powrót z tła i wyjście ze sceny.
- Sprawdź mute przed filmem, podczas filmu i po nim; brak drugiego audio z iframe.
- Od 840 s: ranking graczy/klanów, statystyki, archiwum, shutdown/waiting.
  Sam podgląd nie wywołuje rzeczywistego restartu. Potwierdza się on przez 139.
- Zablokowanie pliku w DevTools lub odmowa autoplay nie mogą zatrzymać zegara.
- Zwykły pulpit/mapa/logowanie nadal działają; radio nie zmienia źródła wskutek
  spóźnionej odpowiedzi ładowania kanału podczas show.

Zmiany estetyczne zapisujemy w 140.stylization.1+. Problemy czasu, miksu,
ładowania lub danych należą do bieżącego odbioru technicznego. Na urządzeniu
mobilnym sprawdź także ograniczenia autoplay i zachowanie po tle — testy
symulowane nie zastępują odsłuchu i pomiaru rzeczywistego buforowania.