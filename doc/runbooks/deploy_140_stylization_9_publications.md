# .9 — publikacje i archiwum

Zaakceptowany układ wdrożony w googleplex, blacknet_history i archive.
Wspólny CSS referencji/runtime; tło zapisu, ramki, glitch i OFS korzystają
z istniejącego kontrolera. Nie ma nowych odczytów backendu, schematu,
timerów publikacji ani zmian audio. Tekst widoczny od początku dla czytelności.

Źródło: settlement.publications. Wpisy filtrowane po medium, do 6 rekordów,
równy czas w scenie. Tytuł, treść i data są archiwalne; brak rekordu/daty/treści
oznaczony. Nie dodajemy demonstracyjnego tekstu ani promptów do publikacji.
Treść renderowana jako tekst (bez HTML). Oznaczenie „fragment publikacji”
odpowiada limitom istniejącej projekcji. Długi tekst mieści się w ograniczonym
ekranie z przewijaniem. Signal Registry pokazuje ID sygnału/cyklu i wersje,
bez wymyślania brakującej metryki. Generator historyczny przekazuje cycle_id.

Po push/pull:

```bash
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
  --output static/previews/ghostsignal-stylization-9-publications-1.html
```

Sprawdź nowy HTML na desktopie i portrait: Googleplex 12:20,
BlackNet 13:20, Signal Registry 14:40. Brak publikacji w archiwum
powinien dać komunikat, nie demonstracyjną treść.

Lokalne 5 zestawów JS PASS. Test montażu: filtrowanie źródeł, równy czas,
zachowanie treści, aktywny indeks, brak publikacji, wejście do archiwum.
Składnia i diff check PASS. Runtime nie wprowadza ?? ani ?.; lokalny Node 24.
Odbiór serwerowy pozostaje otwarty. Statystyki cyklu .8 i montaż .10
pozostają do wykonania; trigger nie jest uruchamiany.
