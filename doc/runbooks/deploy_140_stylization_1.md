# 140.stylization.1 — wdrożenie i odbiór

Implementacja i lokalna regresja JS PASS. Odbiór wizualny siedmiu scen
pozostaje otwarty. Brak nowej migracji, zmian backendu i nowych assetów.
Trigger dopiero po stylizacji całego show.

## Kod i testy

W ~/app/chaos, po push. Przy błędzie przerwij:

```bash
git pull --ff-only && git status --short --branch && git rev-parse --short HEAD
node tests/ghost_signal_show_frontend.test.js &&
node tests/ghost_signal_show_recovery.test.js &&
node tests/ghost_signal_show_manifest.test.js &&
node tests/ghost_signal_show_montage.test.js &&
node tests/ghost_signal_show_audio.test.js &&
node tests/js/test_ghostnetwork_delta_client.js &&
node tests/js/test_game_sfx.js &&
node --check static/js/map_glitch.js &&
node --check static/js/ghost_signal_show.js
.venv/bin/python -B -m unittest discover -s tests -p test_map_loader_frontend_contract.py
```

Po PASS reload aplikacji dla tokenów cache w template'ach; worker nie
wymaga przeładowania z powodu tej zmiany:

```bash
pm2 reload chaos
.venv/bin/python -B tools/build_ghostsignal_show_preview.py \
  --db data/game.sqlite3 --cycle-id ghostnetwork_0001 \
  --output static/previews/ghostsignal-stylization-1-ofs-2.html
```

Przy istniejącym pliku wybierz nową nazwę. Otwórz
`/static/previews/ghostsignal-stylization-1-ofs-2.html`. Cache CSS/JS:
`signal-show-stylization-1-ofs-2`. Podgląd używa istniejącego kontrolera,
historycznych danych i prawdziwych mediów; nie emituje sygnału ani restartu.

## Odbiór siedmiu scen

| Czas | Scena | Kompozycja |
| --- | --- | --- |
| 00:00–00:15 | takeover | Duża typografia po lewej, indeks po prawej |
| 00:15–00:30 | network_layer | Odwrócenie dominanty na desktopie |
| 12:00–12:20 | system_layers | Nacisk na rekonstrukcję i zapis wyników |
| 13:40–13:55 | desktop_assembly | Szeroki układ i pas warstw; mobile z siatką |
| 13:55–14:00 | system_ready | Podsumowanie widoku, nie rzeczywistego bootu |
| 14:50–14:56 | shutdown | Centralny komunikat i wygaszenie |
| 14:56–15:00 | restart | Dominujące CYKL, oczekiwanie na backend |

Sprawdź 1920×1080, 1080×1920 i rzeczywisty telefon: czytelność, proporcje,
brak uciętych treści, safe area, progress i dostępny przycisk dźwięku.
Przejdź do scen suwakiem oraz obejrzyj ich granice w ciągłym odtwarzaniu.
Wyjście do części, publikacji i rankingu nie może pozostawić layoutu .1.
Sprawdź reduced motion (widoczny shutdown), powrót z tła, zmianę orientacji
i brak wallpaper2.jpg. Miks filmu/muzyki pozostaje zatwierdzony w 140.4.

Aktualizacja pulsowania: obserwuj każdą scenę przez kilka sekund bez seek.
Nagłówek i lokalna poświata mają spokojny rytm 5,4 s, a kicker i aktywny
wiersz rytm 8 s. Nie powinny zanikać treści ani zmieniać się układ.
Po seek światło wraca do fazy wynikającej z czasu show; reduced motion
utrzymuje stałe podświetlenie. Istniejący shutdown nadal wygasza scenę.

Aktualizacja glitch: ten sam generator 18 bloków RGB i CSS co na mapie
zostały wydzielone do map_glitch.js/css, wspólnych dla mapy i show.
W .1 poziom zmienia się według czasu show: 7 s slow (średni), 5 s overloaded
(najwyższy), cykl 12 s. Efekt jest za treścią, miesza się z tłem przez screen;
nie koloruje progressu i nie zmienia danych. Puls nagłówka ma zakres
opacity .72–1, mocniejszą poświatę oraz podświetlenie aktywnego wiersza.
Reduced motion wyłącza glitch. Brak skryptu efektu nie blokuje sceny.
Sprawdź pierwsze 15 s takeover bez przewijania oraz powrót do mapy:
jej dotychczasowe poziomy i obsługa wejścia powinny działać jak wcześniej.
Poziomy show są dekoracją, nie raportem rzeczywistego przeciążenia mapy.

OFS-2: indeksy i etykiety wierszy są osobnymi elementami. Korzystają z
istniejących ofs-scene-icon/ofs-scene-text oraz keyframes ofs-fx-icon-live,
ofs-fx-line-focus i ofs-fx-soft-pulse. Kolejne wiersze mają przesunięcie 2,4 s;
opis, system tag, notatka i fakty mają różne fazy. Obejrzyj 12 s sceny:
podświetlenie przechodzi między etykietami, bez zmiany aktywnej warstwy.
Reduced motion wyłącza te animacje, a seek odtwarza fazę z czasu show.

Brak settlementu daje jawny komunikat. Brak potwierdzenia sygnału nadal
blokuje późniejsze sceny. Na końcu podglądu nie oczekujemy restartu gry.
Produkcja wymaga triggera/E2E po stylizacji .1–.9 i odbiorze montażu .10.
