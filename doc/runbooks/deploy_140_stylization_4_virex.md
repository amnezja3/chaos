# 140.stylization.4 — cztery maszyny 360–420 s

Decyzją autora para VIREX zatwierdza wspólny schemat wszystkich czterech
maszyn. Renderer dobiera własne tło `_active`, grafikę, opisy katalogowe,
akcent koloru i pięć części. Dłuższe nazwy mają mniejszą skalę, zachowując
dwa wiersze również na portrait. Poprawka dopasowania obrysu jest w komplecie.

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
  --output static/previews/ghostsignal-stylization-4-machines-1.html
```

Otwórz `/static/previews/ghostsignal-stylization-4-machines-1.html`.
Jeśli plik istnieje, wybierz nową nazwę. Token CSS/JS:
`signal-show-stylization-4-machines-1`.

Wariant 2 usuwa starą klasę `ghost-show-hero__image` z nowego hero.
Jej wymiary 100% × 100% nadpisywały geometrię maszyny, rozsuwając ją
z obrysem. Obraz i obrys korzystają teraz z tej samej klasy `hero-image`.
Sprawdź ich dopasowanie w obu orientacjach w 06:08.

Sprawdź 06:08 na desktopie i portrait: dwa wiersze VIREX/ORACLE,
duża maszyna z obrysem, tło `_active` z ciemnym środkiem i jaśniejszymi
bokami, pięć komponentów. Desktop ma opisy funkcji i ryzyka oraz dodatkowe
OFS i ruch światła; mobile zachowuje spokojniejszą oprawę. Panel dźwięku
i postępu pozostaje dostępny. Reduced motion wyłącza animacje CSS.

Przewiń 05:59 → 06:08 → 06:16 i wstecz. Sprawdź usunięcie poprzedniej
sceny, brak powielania elementów oraz powrót do właściwego czasu muzyki.
Cały komplet sprawdź na desktopie i portrait:

| Czas podglądu | Maszyna | Części |
| --- | --- | --- |
| 06:08 | VIREX ORACLE | V1–V5 |
| 06:23 | ECHO LIBERTAS | E1–E5 |
| 06:38 | PHANTOM VEIL | P1–P5 |
| 06:53 | SENTINEL AEGIS | S1–S5 |

Sprawdź seek w obie strony i przejście 06:59 → 07:01. Odbiór runtime
całego kompletu pozostaje otwarty; trigger nadal odłożony.
