# .8 — nagrody finału

Status: ZAMKNIĘTE — PASS użytkownika, również po ustawieniu nowych stawek.

Zaakceptowana referencja wdrożona w `reward_ledger` (630–660 s).
Tytuł ma `display:block`, dzięki czemu FINAŁU jest pod NAGRODY również
na portrait; nadpisuje odziedziczony flex. CSS jest wspólny z referencją.
Subtelny puchar SVG pozostaje przy nagłówku rejestru. Efekty OFS i glitch
synchronizuje dotychczasowy kontroler show.

Kwoty i liczby pochodzą z settlement.reward_groups, rsp_total, rewards_total.
Każda kategoria dostaje 30/N sekund. Wszystkie zapisane kategorie (limit
projekcji: 16) są uwzględnione, również nieznane typy, bez wymyślania nagród.
Łączna suma pozostaje archiwalna. Zero RSP jest zerem; brak danych pokazuje —.
Przy dłuższej liście jej okno utrzymuje aktywny wiersz. Brak zmian backendu,
schematu bazy, audio ani triggera. Ranking klanów pozostaje do stylizacji.

## Testy po push/pull

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
  --output static/previews/ghostsignal-stylization-8-rewards-1.html
```

Sprawdź 10:30–11:00 na desktopie i mobile: tytuł w dwóch wierszach,
kwota wybranej kategorii, podświetlenie rejestru, liczba zapisów, stała suma.

Lokalnie: pięć zestawów JS PASS, składnia i diff check PASS. Test montażu
obejmuje równe czasy, granice kategorii, zero, brak danych, dodatkowy typ
oraz zgodność aktywnego wiersza z prezentowaną kwotą. Lokalny Node 24;
kod nie wprowadza operatorów ?? ani ?. nieobsługiwanych na serwerowym Node 12.
