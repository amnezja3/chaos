# 140.stylization.4 — grupy części 160–300 s

Zaakceptowany wariant PHANTOM VEIL wdrożono do sceny zbiorczej i czterech
grup części. Hero maszyn 360–420 s pozostają dalszym zakresem .4.
Brak zmian backendu, migracji i nowych bitmap. Trigger nadal odłożony.

## Testy i podgląd

W `~/app/chaos`, po push. Przy błędzie przerwij:

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
node --check static/js/ghost_signal_show.js
```

Po PASS:

```bash
pm2 reload chaos
.venv/bin/python -B tools/build_ghostsignal_show_preview.py \
  --db data/game.sqlite3 --cycle-id ghostnetwork_0001 \
  --output static/previews/ghostsignal-stylization-4-focus-1.html
```

Jeśli plik już istnieje, wybierz nową nazwę. Otwórz
`/static/previews/ghostsignal-stylization-4-focus-1.html`.
Token CSS/JS: `signal-show-stylization-4-focus-1`. Worker nie wymaga reloadu.

## Odbiór

| Czas | Scena | Pierwszy plan |
| --- | --- | --- |
| 160–180 s | machine_groups | Zbiorcza kompozycja .2 |
| 180–210 s | machine_group_1 | V1–V5 |
| 210–240 s | machine_group_2 | E1–E5 |
| 240–270 s | machine_group_3 | P1–P5 — zaakceptowana para |
| 270–300 s | machine_group_4 | S1–S5 |
| 300–301,5 s | network_expand | Przejście z końcowych pozycji S1–S5 do pierścienia |

Sprawdź desktop i portrait: prezentowana piątka jest duża i czytelna,
15 pozostałych części mniejszych i wybledzonych. Wszystkie zapisane krawędzie
pozostają obecne; połączenia tła są słabsze. OFS, glitch, łuna i oddychanie
korzystają z oprawy .2. Piątka z przodu ładuje `superpower/`, reszta `parts/`.

Zmiana grupy trwa 0,9 s, według czasu show. Przewiń do 210,2 / 210,6 s
i wstecz: krawędzie muszą podążać za częściami także po seek. Obejrzyj
granice 239–242 i 299–303 s oraz zmianę orientacji. Wejście pierścienia
interpoluje pozycje, skalę i pole do kwadratu; docelowo zachowuje koło.
Reduced motion pomija ruch przejścia. Tooltipy i dźwięk pozostają dostępne.

Brak zapisanego ringu nie tworzy zastępczych połączeń. Wyjście z grup usuwa
layout oraz listenery tooltipów. Osiem lokalnych zestawów JS PASS;
odbiór wizualny runtime na serwerze pozostaje otwarty.
