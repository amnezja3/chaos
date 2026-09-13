# .8 — klany / wdrożenie

Status: ZAMKNIĘTE / PASS użytkownika po podmianie logotypów na `_pro.png`.

Wariant clans-2: na życzenie użytkownika symbole SVG zastąpiono przygotowanymi
assetami virex_logo_pro.png, echo_logo_pro.png, mesh_logo_pro.png oraz
sentinel_logo_pro.png z tego samego katalogu. `object-fit:contain` zachowuje
pełny obraz i proporcje (VIREX 1024×1536, pozostałe 1145×1374).
Podmiana obejmuje runtime i referencję. Łączna waga plików: około 7,46 MiB.

Zaakceptowana para clans-ref-2 podłączona do `clans` (700–720 s)
i `clan_ranking` (855–870 s). Wspólny renderer rankingu i CSS referencji;
bez dodatkowego kontrolera, odczytów backendu i zmian schematu.

Symbole SVG: virex, echo_freedom, phantom_mesh, sentinel_order. Nazwy
pochodzą z katalogu, pozycje, score, suma RSP członków i liczba uczestników
z settlement.clans. Zachowana kolejność rankingu; każda pozycja ma równy
czas w danej scenie. Lista podświetla aktywny klan i pokazuje Ghost Score,
nie RSP. RSP w statystykach to suma nagród uczestników, nie nowa wypłata.
Zero score pozostaje zerem, brak danych jest oznaczony, brak SVG pokazuje
komunikat. Nieznany klan nie otrzymuje cudzego symbolu.

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
  --output static/previews/ghostsignal-stylization-8-clans-2.html
```

Otwórz nowy HTML: 11:40–12:00 oraz 14:15–14:30, desktop/portrait.
Trigger nadal odłożony. Lokalne 5 zestawów JS PASS; test montażu obejmuje
obie sceny, zmianę aktywnego klanu, score=0, trzy statystyki, SVG/fallback
i brak danych. Składnia sprawdzona na lokalnym Node 24; nie dodano ?? ani ?..
