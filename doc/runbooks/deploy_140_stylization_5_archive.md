# 140.stylization.5 — zapis 420–425 s

Wdrożono zaakceptowany zapis: tło `write_signal_scena_bg.png`, nakładkę,
glitch, opisy i puls źródła światła. CSS jest wspólny z referencją.
Puls ma fazę wyznaczaną przez istniejący zegar show; bez dodatkowych timerów.
Zmiana nie obejmuje stylizacji filmu ani dalszych scen .5. Miks pozostaje
dotychczasowy. Brak migracji i triggera.

Po push, w `~/app/chaos`:

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
  --output static/previews/ghostsignal-stylization-5-archive-1.html
```

Otwórz `/static/previews/ghostsignal-stylization-5-archive-1.html`.
Jeśli plik istnieje, wybierz nową nazwę. Token CSS/JS:
`signal-show-stylization-5-archive-1`.

Desktop i portrait: obejrzyj 07:00–07:05. Łuna ma pokrywać punkt źródła
światła również po zmianie orientacji. Sprawdź seek 06:59 → 07:02 → 07:06
i wstecz: zapis usuwa się przed filmem, a powrót zatrzymuje film.
Panel dźwięku i postępu musi pozostać dostępny. Reduced motion wyłącza
pulsowanie, zachowując słabe światło. Pięć zestawów JS lokalnie PASS;
odbiór wizualny runtime pozostaje otwarty.
