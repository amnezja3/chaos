# 140.stylization.3 — wdrożenie i odbiór sieci

Pięć scen zintegrowanych z istniejącym rendererem. Para REF-3 zaakceptowana;
odbiór runtime potwierdzony przez autora po NETWORK-2 („to jest to”). Brak migracji i nowych bitmap.
Manifest zawiera dodatkowo publiczny opis supermocy z istniejącego katalogu.
Trigger pozostaje odłożony do zakończenia stylizacji i montażu .10.

## Testy po push/pull

W `~/app/chaos`. Przy błędzie przerwij:

```bash
git pull --ff-only && git status --short --branch && git rev-parse --short HEAD
node tests/ghost_signal_show_frontend.test.js &&
node tests/ghost_signal_show_recovery.test.js &&
node tests/ghost_signal_show_manifest.test.js &&
node tests/ghost_signal_show_montage.test.js &&
node tests/ghost_signal_show_audio.test.js &&
node tests/ghost_signal_network_reference.test.js &&
node tests/js/test_ghostnetwork_delta_client.js &&
node tests/js/test_game_sfx.js &&
node --check static/js/ghost_signal_network_details.js &&
node --check static/js/ghost_signal_show.js
```

Test manifestu w izolowanym katalogu, bez lokalnej bazy gry:

```bash
.venv/bin/python -B - <<'PY'
import os, sys, tempfile, unittest
from pathlib import Path
root = Path.cwd()
sys.path[:0] = [str(root), str(root / 'tests')]
with tempfile.TemporaryDirectory(prefix='chaos-stylization-3-') as tmp:
    try:
        os.chdir(tmp)
        suite = unittest.defaultTestLoader.loadTestsFromName('test_ghostnetwork_show_manifest')
        result = unittest.TextTestRunner(verbosity=1).run(suite)
    finally:
        os.chdir(root)
sys.exit(not result.wasSuccessful())
PY
```

## Reload i podgląd

Po PASS:

```bash
pm2 reload chaos
.venv/bin/python -B tools/build_ghostsignal_show_preview.py \
  --db data/game.sqlite3 --cycle-id ghostnetwork_0001 \
  --output static/previews/ghostsignal-stylization-3-network-2.html
```

Wybierz inną nazwę, jeżeli plik istnieje. Otwórz
`/static/previews/ghostsignal-stylization-3-network-2.html`.
Cache: `signal-show-stylization-3-network-2`. Worker nie wymaga reloadu
z powodu tej zmiany. Podgląd historyczny nie wyzwala sygnału ani restartu.

## Odbiór

NETWORK-2: pierścień formuje się w **1,5 s** (05:00–05:01,5), zamiast
przez całą 20-sekundową scenę. Szybki start i wyhamowanie ease-out;
krótkie odświeżanie klatkowe kończy się wraz z wejściem. Seek zachowuje fazę,
reduced motion od razu pokazuje pierścień. Sprawdź 04:59–05:03.

| Czas | Scena | Sprawdzenie |
| --- | --- | --- |
| 01:30–02:00 | connections | Zaakceptowana kompozycja .2 i energetyczne krawędzie; teraz również tooltip |
| 05:00–05:20 | network_expand | Rozwinięcie logicznych grup części do pierścienia; pozycje i połączenia zmieniają się razem |
| 05:20–05:40 | network_ring | Koło jak w REF-3, wszystkie 20 kodów i rzeczywisty ring |
| 05:40–05:50 | network_tension | Mocniejsza łuna i rdzeń; geometria pierścienia pozostaje stała |
| 05:50–06:00 | network_ready | Spokojniejsza sieć i przejście do hero maszyny |

Sprawdź desktop 1920×1080, portrait 1080×1920 i wąski telefon. Pole ma bok
równy mniejszemu dostępnemu wymiarowi, więc pierścień nie staje się elipsą.
Hover/fokus/tap pokazuje nazwę, klan, kod, supermoc i maszynę. Escape lub
dotknięcie poza zamyka panel; tooltip nie może wychodzić poza viewport.
Na starszym manifeście brak opisu ma jawny komunikat.

Przewiń do 05:10, 05:30, 05:45 i wstecz, także w tej samej scenie.
Pozycje, krawędzie i fazy efektów muszą odpowiadać czasowi, bez konieczności
obejrzenia początku. Sprawdź zmianę orientacji, powrót z tła i reduced motion.
Bez zapisanego ringu widok nie wymyśla połączeń ani katalogowej historii.

Obejrzyj granice 04:59–05:01 i 05:59–06:01. .4 doprecyzuje kompozycje
maszyn, a .10 montaż całości. Wyjście usuwa tooltip i jego obsługę; normalna
gra pozostaje zablokowana na czas show. Potwierdź ciągłość zatwierdzonej muzyki.

Lokalnie: osiem zestawów JS PASS, trzy testy manifestu PASS, izolowany
generator podglądu PASS. Automatyczny odbiór wizualny nie został wykonany.
