# .9 — publikacje i archiwum

Status: ZAMKNIĘTE / PASS użytkownika dla wariantu publications-2:
publikacje, strony tekstu bez scrolli, statystyki w ekranie i archiwum.

Poprawka publications-2: publikacje nie są ograniczone do chwili powstania
rankingu. Generator ponownie odczytuje publiczne wpisy do show_ends_at,
również przy istniejącej projekcji settlement. Odczyt zachowuje filtr cyklu,
publicznej widowni, published, active i ważności wpisu. Wpisy prywatne,
unieważnione lub rzeczywiście nieistniejące nie są zastępowane fikcją.
Po publikacji publisher odświeża tylko settlement.publications aktywnego
show, w istniejącej transakcji. Ranking, nagrody i zamknięte archiwum bez zmian.

Tekst dzielony na strony do 240 znaków, bez przewijania w ramce.
Statystyki cyklu 14:30–14:40 przeniesione do tej samej scenografii ekranowej.
Frontend odświeża treść również po nadejściu publikacji w obrębie tej samej sceny.

Zaakceptowany układ wdrożony w googleplex, blacknet_history i archive.
Wspólny CSS referencji/runtime; tło zapisu, ramki, glitch i OFS korzystają
z istniejącego kontrolera. Nie ma nowych odczytów backendu, schematu,
timerów publikacji ani zmian audio. Tekst widoczny od początku dla czytelności.

Źródło: settlement.publications. Wpisy filtrowane po medium, do 6 rekordów,
równy czas w scenie. Tytuł, treść i data są archiwalne; brak rekordu/daty/treści
oznaczony. Nie dodajemy demonstracyjnego tekstu ani promptów do publikacji.
Treść renderowana jako tekst (bez HTML). Oznaczenie „fragment publikacji”
odpowiada limitom istniejącej projekcji. Długi tekst mieści się w ograniczonym
ekranie ze stronami tekstu. Signal Registry pokazuje ID sygnału/cyklu i wersje,
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
pm2 reload chaos-narrative-publisher &&
.venv/bin/python -B tools/build_ghostsignal_show_preview.py \
  --db data/game.sqlite3 --cycle-id ghostnetwork_0001 \
  --output static/previews/ghostsignal-stylization-9-publications-2.html
```

Sprawdź nowy HTML na desktopie i portrait: Googleplex 12:20,
BlackNet 13:20, statystyki 14:30, Signal Registry 14:40. Brak publikacji w archiwum
powinien dać komunikat, nie demonstracyjną treść.

Lokalne 5 zestawów JS PASS. Test montażu: filtrowanie źródeł, równy czas,
zachowanie treści, aktywny indeks, brak publikacji, wejście do archiwum.
Składnia i diff check PASS. Runtime nie wprowadza ?? ani ?.; lokalny Node 24.
Odbiór serwerowy publikacji i statystyk zakończony — PASS użytkownika.
Montaż .10 pozostaje do wykonania; trigger nie jest uruchamiany.
