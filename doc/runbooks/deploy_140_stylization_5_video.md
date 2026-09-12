# 140.stylization.5 — rekonstrukcja transmisji

Wdrożona zaakceptowana para v8. Desktop: ramka +30%, pole 2:1
z centralnym kadrowaniem bez rozciągania. Portrait: pole 3:2, marginesy
6vw wyrównane do tytułu. Film nad tytułem. Wspólny CSS z referencją.
Dotychczasowy odtwarzacz, seek, fallback i mikser 0,5 s są zachowane.
Bez migracji. Trigger nadal odłożony.

Po push, w katalogu repozytorium na serwerze:

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
  --output static/previews/ghostsignal-stylization-5-video-1.html
```

Otwórz `/static/previews/ghostsignal-stylization-5-video-1.html`.
Sprawdź 07:10 na desktopie i portrait oraz granice 07:04–07:06
i 07:42–07:45. Zweryfikuj audio filmu, fade muzyki 0,5 s, seek wstecz,
brak kontrolek i fullscreen oraz wyczyszczenie filmu po jego scenie.
Pięć zestawów JS lokalnie PASS; odbiór wizualny runtime otwarty.

Następny checkpoint .5 to rozbłysk po filmie: para referencyjna dla
`transmission_replay` (463,12–466,12 s) i `signal_point` (466,12–469,12 s).
Kierunek do oceny: ramka gaśnie, energia skupia się w centralnym źródle,
pojedynczy miękki rozbłysk przechodzi w ślad sygnału. Zachowujemy tło,
paletę i światło archiwum, brak stroboskopu, reduced motion jako statyczny
ślad. Bramka potwierdzenia wysłania i czas wejścia terminala nie zmieniają się.
Ten efekt nie jest jeszcze wdrożony.
