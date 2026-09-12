# .6 — wszystkie sceny z ekranem

Kanał 2108, potwierdzenie wysłania, Pro Tools oraz pliki i dane korzystają
z oprawy archiwum i zaakceptowanej ramki filmu. Desktop 2:1, portrait 3:2
i marginesy 6vw. Nowe sceny mają typewriter, ramki wierszy oraz OFS.
Nie uruchamiają ponownie błysku. Brak nowych API, migracji i zmian miksera.

Treść pochodzi z publicznego manifestu: ID i czas wysłania sygnału, cel 2108,
wersje systemu, dostępność rankingu, podsumowanie finału i indeks archiwum.
Nie wykonujemy komend terminala ani odczytu prywatnych plików graczy.
Brak danych jest oznaczony tekstowo. Sukces wymaga trwałego potwierdzenia.

Po push, w repozytorium na serwerze:

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
  --output static/previews/ghostsignal-stylization-6-screens-1.html
```

Otwórz `/static/previews/ghostsignal-stylization-6-screens-1.html`.
Sprawdź desktop/portrait:

| Czas | Scena |
| --- | --- |
| 07:52 | Kanał 2108 |
| 07:59 | Potwierdzenie wysłania |
| 12:55 | Pro Tools / terminal |
| 13:15 | Pliki i dane |

Sprawdź także początki scen, przewijanie w obie strony i reduced motion.
Wiersze mają zawijać się do szerokości ekranu, bez poziomego scrolla;
czytany tekst przesuwa się do końca w obrębie ramki. OFS podświetla wiersze
i indeksy. Panel audio/postępu pozostaje dostępny. Trigger odłożony.
Pięć zestawów JS PASS; odbiór wizualny serwerowy otwarty.
