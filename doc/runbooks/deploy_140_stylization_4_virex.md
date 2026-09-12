# 140.stylization.4 — VIREX Oracle 360–375 s

Po push/pull, w `~/app/chaos`. Trigger pozostaje odłożony.
Zmiana manifestu dodaje dwa pola katalogowe; migracja nie jest potrzebna.

```bash
git pull --ff-only && git status --short --branch && git rev-parse --short HEAD
node tests/ghost_signal_show_frontend.test.js &&
node tests/ghost_signal_show_recovery.test.js &&
node tests/ghost_signal_show_manifest.test.js &&
node tests/ghost_signal_show_montage.test.js &&
node tests/ghost_signal_show_audio.test.js &&
node --check static/js/ghost_signal_show.js
```

Po PASS:

```bash
pm2 reload chaos &&
.venv/bin/python -B tools/build_ghostsignal_show_preview.py \
  --db data/game.sqlite3 --cycle-id ghostnetwork_0001 \
  --output static/previews/ghostsignal-stylization-4-virex-1.html
```

Otwórz `/static/previews/ghostsignal-stylization-4-virex-1.html`.
Jeśli plik istnieje, wybierz nową nazwę. Token CSS/JS:
`signal-show-stylization-4-virex-hero-1`.

Sprawdź 06:08 na desktopie i portrait: dwa wiersze VIREX/ORACLE,
duża maszyna z obrysem, tło `_active` z ciemnym środkiem i jaśniejszymi
bokami, pięć komponentów. Desktop ma opisy funkcji i ryzyka oraz dodatkowe
OFS i ruch światła; mobile zachowuje spokojniejszą oprawę. Panel dźwięku
i postępu pozostaje dostępny. Reduced motion wyłącza animacje CSS.

Przewiń 05:59 → 06:08 → 06:16 i wstecz. Sprawdź usunięcie poprzedniej
sceny, brak powielania elementów oraz powrót do właściwego czasu muzyki.
Echo, Phantom i Sentinel nadal mają dotychczasowy renderer hero;
ich odrębne kompozycje pozostają do zaprojektowania. Sprint .4 nie jest zamknięty.
