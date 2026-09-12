# .5 — błysk i terminal w ramce transmisji

Korekta VIDEO-TAIL-1: plik ma potwierdzone ffprobe 38,120 s obrazu i audio.
Poprzednia granica sceny mogła usunąć odtwarzacz opóźniony o dopuszczalne
0,75 s. Teraz przy odtwarzanej końcówce (pozostało ≤1,5 s) czekamy na
`ended`, bez seek do granicy. Błysk zaczyna od pierwszej klatki po końcu
filmu, a muzyka wraca w 0,5 s. Limit oczekiwania to 1,5 s od granicy sceny,
żeby uszkodzony odtwarzacz nie blokował show. Dalszy seek omija oczekiwanie.
Końcowy termin show pozostaje bez zmian.

Implementacja zaakceptowanego wariantu flash-ref-2: linia 2 px / 50 ms,
prostokąt 75% / 75 ms, biel / 500 ms, przyspieszające wygaszenie / 125 ms.
Łącznie 750 ms od początku `transmission_replay`. Overlay obejmuje cały
ekran show. Reduced motion pomija błysk.

`transmission_replay`, `signal_point` i `terminal_2108` zachowują jedną
scenografię i ramkę. Typewriter korzysta z ID sygnału, czasu wysłania
i zapisanej daty docelowej 2108; bez przykładowych wiadomości z referencji.
Nie zmieniono czasów manifestu ani bramki potwierdzenia sygnału.
Efekt korzysta z zegara show; klatki przelicza requestAnimationFrame,
czyszczony przy zmianie sceny. Seek odtwarza właściwy stan bez replay od zera.

Po push/pull w repozytorium na serwerze:

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
  --output static/previews/ghostsignal-stylization-5-video-tail-1.html
```

Otwórz `/static/previews/ghostsignal-stylization-5-video-tail-1.html`.
Odtwórz od 07:39 bez dalszego seek i potwierdź pełny efekt końcowy filmu
przed błyskiem. Przy opóźnieniu filmu błysk może przesunąć się o tę końcówkę.
Desktop/portrait: odtwórz 07:41–08:00. Błysk zaczyna się w 07:43,12,
kończy w 07:43,87. Ślad sygnału w 07:46,12 i terminal w 07:49,12
pozostają w tej samej ramce. W 07:57 wchodzi dotychczasowe potwierdzenie.
Sprawdź seek wstecz, ponowne wejście i reduced motion. Audio zachowuje
istniejący miks 0,5 s. Bez migracji; trigger pozostaje odłożony.

Pięć zestawów JS PASS, w tym progi błysku, ciągłość ramki, tekst z danych,
seek, bramka sygnału i usuwanie overlay. Odbiór wizualny runtime otwarty.
