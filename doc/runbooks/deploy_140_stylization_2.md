# 140.stylization.2 — wdrożenie i odbiór

Zaakceptowana para v6 została zintegrowana z rendererem. Testy lokalne JS
obejmują odsłanianie, stałe pozycje, archiwalne dane, braki danych i cleanup.
Odbiór wizualny runtime na serwerze pozostaje otwarty. Bez migracji bazy.
Trigger/E2E dopiero po stylizacji .1–.9 i odbiorze montażu .10.

## Testy na serwerze

W `~/app/chaos`, po push; przy błędzie przerwij:

```bash
git pull --ff-only && git status --short --branch && git rev-parse --short HEAD
node tests/ghost_signal_show_frontend.test.js &&
node tests/ghost_signal_show_recovery.test.js &&
node tests/ghost_signal_show_manifest.test.js &&
node tests/ghost_signal_show_montage.test.js &&
node tests/ghost_signal_show_audio.test.js &&
node tests/js/test_ghostnetwork_delta_client.js &&
node tests/js/test_game_sfx.js &&
node --check static/js/ghost_signal_show.js
```

Po PASS przeładuj aplikację, aby strony dostały nowy token CSS/JS.
Worker nie wymaga reloadu z powodu tej zmiany.

```bash
pm2 reload chaos
.venv/bin/python -B tools/build_ghostsignal_show_preview.py \
  --db data/game.sqlite3 --cycle-id ghostnetwork_0001 \
  --output static/previews/ghostsignal-stylization-2-depth-1.html
```

Jeżeli plik już istnieje, wybierz nową nazwę. Otwórz
`/static/previews/ghostsignal-stylization-2-depth-1.html`.
Token CSS/JS: `signal-show-stylization-2-depth-1`.
Podgląd historyczny czyta bazę, nie wyzwala sygnału ani restartu gry.

## Odbiór desktop i portrait

Sprawdź 1920×1080, 1080×1920 oraz rzeczywisty telefon, zarówno suwakiem,
jak i odtwarzając granice scen bez przeskakiwania.

| Czas | Scena | Co sprawdzić |
| --- | --- | --- |
| 00:30–01:00 | parts_enter | Stopniowe wejście; pozycje nie zmieniają się wraz z kolejnością odkryć |
| 01:00–01:30 | parts_complete | 20 części w czterech planach; pierwszy +20%, ostatni −10% względem v3 |
| 01:30–02:00 | connections | Te same adresy, połączenia z archiwum; docelowa stylizacja sieci w .3 |
| 02:00–02:20 | history_logs | Cztery grupy po pięć rekordów, zmiana co 5 s; daty UTC lub brak zapisu |
| 02:20–02:40 | part_states | Archiwalny status i czas aktywacji; te same pozycje części |
| od 02:40 | machine_groups | Wyjście z layoutu .2, brak pozostałości; stylizacja maszyn w .4 |

Obserwuj kilkanaście sekund: delikatne oddychanie, puls napisów/indeksów,
glitch w tle średni/najwyższy. Hover i focus dają miękką łunę około 20%
poprzedniej intensywności, bez zmiany stanu części i bez akcji w grze.
Celowy overscan V4 (oraz V1 w portrait) nie może zasłaniać kodów, podpisów
i paska postępu/dźwięku. Historia musi być czytelna bez przewijania.

Sprawdź zmianę orientacji, powrót z tła i reduced motion (wyłączone efekty,
widoczna treść). Brak obrazka daje nazwę, brak pełnej historii jawny komunikat,
brak zapisu ringu nie tworzy fikcyjnych połączeń. W podglądzie z dźwiękiem
potwierdź ciągłość zatwierdzonego miksu. Produkcyjnego triggera teraz nie uruchamiamy.
