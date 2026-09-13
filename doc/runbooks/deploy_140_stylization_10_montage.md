# 140.stylization.10 — montaż i odbiór całości

Status: ZAMKNIĘTY / PASS użytkownika, 2026-09-13. Autor zaakceptował całość,
a następnie korektę audio: wyciszanie 3,5 s od startu filmu, powrót 0,5 s.
Rollback, trigger i produkcyjny E2E pozostają następnym etapem;
zamknięcie dokumentacji nie uruchamia tych operacji.

Para przejścia: 415–480 s, ostatnia maszyna → zapis → wideo → błysk →
kanał 2108 → świat. Korzysta bezpośrednio z renderera show w viewportach
1920×1080 i 1080×1920. Nie dodaje nowego stylu ani assetów.
Odbiór show potwierdzony przez autora. Nie dołączono osobnego raportu
wydajności urządzeń; wyniki testów automatycznych nie są takim pomiarem.

## Przygotowanie po pobraniu zmian

```bash
node tests/ghost_signal_show_frontend.test.js &&
node tests/ghost_signal_show_recovery.test.js &&
node tests/ghost_signal_show_manifest.test.js &&
node tests/ghost_signal_show_montage.test.js &&
node tests/ghost_signal_show_audio.test.js &&
node --check static/js/ghost_signal_show.js

.venv/bin/python -B tools/build_ghostsignal_show_preview.py --output static/previews/ghostsignal-stylization-10.html
.venv/bin/python -B tools/build_ghostsignal_show_preview.py --db data/game.sqlite3 --cycle-id ghostnetwork_0001 --output static/previews/ghostsignal-stylization-10-history.html
```

Istniejący plik podglądu nie jest nadpisywany: przy kolejnej generacji wybrać
nową nazwę. Para używa pliku demo `ghostsignal-stylization-10.html`.

- Para: `/static/references/ghostsignal/montage-pair.html` (bez audio).
- Pełny odsłuch: `/static/previews/ghostsignal-stylization-10-history.html`.
- Bez panelu operatora: dopisać `?controls=hidden`; powrót przez usunięcie parametru.
- Fragment od 415 s: dopisać `?start=415`.

Demo pokazuje datę podróży do 2108; stary replay może nie mieć daty odbioru.
Dane i nagrody archiwalne pozostają historyczne. Nie traktować ich jako
wyniku nowego triggera z aktualnymi stawkami.

## Checkpointy odbioru

| Czas | Kontrola |
| --- | --- |
| 0–160 s | Przejęcie, części, głębia, OFS i połączenia |
| 160–420 s | Grupy, pierścień, cztery maszyny; brak pozostałości poprzedniej sceny |
| 420–480 s | Cały film z końcówką; wyciszenie muzyki przez 3,5 s od pierwszej klatki, powrót przez 0,5 s; błysk i ekran 2108 |
| 480–630 s | Jednokrotny przegląd terytoriów, równe czasy, właściciele i współrzędne |
| 630–720 s | Nagrody, gracze, avatary, poziomy, klany i aktywne pozycje list |
| 720–840 s | Ekrany systemowe, publikacje i logi bez scrolli |
| 840–900 s | Rankingi, statystyki, archiwum i oczekiwanie na nowy cykl |

Sprawdzić pełny odsłuch osobno na desktopie i telefonie, zmianę orientacji,
seek w obie strony oraz powrót do karty po ukryciu. Raport wydajności
eksportować z panelu po pełnym przebiegu. Para iframe nie służy do pomiaru
wydajności ani audio: renderuje dwa widoki równocześnie.

Automatyczny test montażu przechodzi 49 scen z kanonicznej osi backendu,
sprawdzając 98 wejść/wyjść, brak starego układu, awarii renderera i wycieku
wideo. To nie zastępuje wizualnego odbioru, odsłuchu ani pomiaru na urządzeniu.
