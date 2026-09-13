# 140.stylization.8 — para referencyjna graczy i rankingu

Status: ZAAKCEPTOWANA I WDROŻONA do scen graczy. Numer pozycji zmniejszony
o dodatkowe 50% zgodnie z ostatnią uwagą. Procedura:
[wdrożenie rankingu](../runbooks/deploy_140_stylization_8_ranking.md).

Korekta ranking-ref-2: wszystkie 20 systemowych avatarów ma 1024 × 1536 px.
Ramka zachowuje proporcje 2:3 na desktopie i portrait. Nick zmniejszony
z 12vw do 8vw (portrait z 18vw do 13vw). W prawym górnym rogu avataru
widnieje numer pozycji #01 itd., aktualizowany razem z podświetleniem listy.

Para: `/static/references/ghostsignal/ranking-pair.html?v=ranking-ref-1`.
Osobna scena: `/static/references/ghostsignal/ranking.html?v=ranking-ref-1`.
Desktop 1920 × 1080 i portrait 1080 × 1920, skalowane tak jak wcześniejsze pary.

Nick jest tytułem, klan podtytułem. Avatar gracza stanowi główny element,
obok są LVL oraz RSP za sygnał. Pełna lista rankingu pozostaje na ekranie;
wiersz aktualnie prezentowanego gracza ma jasne obramowanie i podświetlenie OFS.
Desktop: lista po prawej. Portrait: lista pod avatarem. Wspólne tło, glitch,
przygaszona kolorystyka, puls światła i ramki wykorzystują istniejące style.

Referencja zawiera osiem jawnie przykładowych profili z istniejącymi assetami
`static/images/avatar-frakcja-*-player-*.png`. Przyciski pary uruchamiają oba
widoki (6 s na gracza, jeden przebieg), zatrzymują je lub wybierają kolejną osobę.
Nie ma odczytów API, audio, zapisów do bazy ani triggera gry.

## Ustalenia danych z etapu referencji

- Ranking finału już zapisuje nick, klan, pozycję i RSP za sygnał.
- Obecny snapshot rankingu nie zawiera avataru i poziomu: trzeba je dodać
  do istniejącej ograniczonej projekcji przy tworzeniu zapisu finału.
- Starsze archiwum nie daje podstaw do odtworzenia historycznego LVL/avataru;
  brak musi być jawny. Ewentualny podgląd aktualnego profilu wymaga oznaczenia.
- Nie pobierać ciężkiego profilu w pętli show. Nie budować nowego kontrolera.
- Pełna lista w tej parze ma 8 graczy; przed implementacją ustalić zachowanie
  większego rankingu i limit istniejącej projekcji (obecnie 20 graczy).
- Zachować kolejność rankingu, równy czas i ciągłą sekwencję bez resetów scen.

Sprawdzone lokalnie: składnia JS oraz obecność wszystkich ośmiu avatarów.
Ocena wizualna desktop/portrait pozostaje do wykonania w przeglądarce.
