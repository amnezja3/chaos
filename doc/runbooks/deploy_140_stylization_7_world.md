# .7 — mapy i terytoria

Zaakceptowany wariant world-ref-2 wdrożono do sześciu scen .7.
CSS jest wspólny z referencją; kontury Natural Earth zapisano jako lokalny
`static/images/ghostnetwork/world-globe.svg`, wygenerowany z
`static/references/ghostsignal/world-land.geojson`. Bez bibliotek mapowych,
zewnętrznych requestów i dodatkowych odczytów backendu.

Terytoria pochodzą wyłącznie z istniejącego `cycle_history.settlement`.
Maksymalnie 40 obszarów, po 3–32 poprawne wierzchołki. Nie ma trójkąta demo.
Glob jest wyłącznie scenografią. Aktualne terytorium jest dopasowane do pola
380 × 380 jednostek SVG, z zachowaniem proporcji i kolejności wierzchołków.
Lokalizacja i rozmiar geograficzny nie wpływają na jego położenie ani skalę
prezentacji. Kontur ma łunę, wypełnienie i pulsujące wierzchołki.
Nie pokazuje całego stanu świata ani niezapisanych stanów zachowanych/zredukowanych obszarów.
Brak geometrii pozostawia glob i tekstowe podsumowanie.

Po push, na serwerze w repozytorium:

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
  --output static/previews/ghostsignal-stylization-7-world-2.html
```

Otwórz `/static/previews/ghostsignal-stylization-7-world-1.html`.
Wybierz inną nazwę, jeśli plik już istnieje. Desktop i portrait:

| Czas | Scena |
| --- | --- |
| 08:05 | Następstwa sygnału |
| 08:25 | Zapis granic obszarów objętych finałem |
| 08:55 | Losy terytoriów |
| 09:25 | Rozliczenie / dostępność danych o redukcji |
| 09:55 | Archiwalne konflikty |
| 10:20 | Podsumowanie końcowe |

Sprawdź podniesiony tytuł, odstępy od logów, kołowe proporcje globu,
światło wierzchołków, OFS, seek w obie strony i reduced motion.
Nie wszystkie małe terytoria będą czytelne przy skali globalnej;
podpisy i liczby odnoszą się do archiwum, nie powierzchni globu.
Panel dźwięku i postępu ma pozostać dostępny. Brak migracji i zmian miksu.
Trigger nadal odłożony.

Pięć zestawów JS lokalnie PASS, w tym brak geometrii, błędne współrzędne,
obszar poza kadrem, przecięcie horyzontu i zachowanie DOM między tickami.
Odbiór wizualny runtime na serwerze otwarty.
