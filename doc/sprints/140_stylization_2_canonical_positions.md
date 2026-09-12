# .2 — canonical positions v6

REFERENCE v6 ACCEPTED / IMPLEMENTED / SERVER REVIEW PENDING

Pierwszy plan V1–V5 używa teraz istniejących obrazów `superpower/` 540×540
(łącznie 1 760 653 B), zamiast `parts/` 128×128 (245 536 B).
Pozostałe 15 części zachowuje lekkie pliki `parts/`. Podmiana dotyczy
referencji i renderera .2; skale, pozycje i odsłanianie pozostają zachowane.

Po akceptacji autora kompozycję przeniesiono do istniejącego renderera show.
`PART_POSES` w `static/js/ghost_signal_show.js` utrwala adresy kodów;
referencja i runtime korzystają ze wspólnego `static/css/ghost_signal_parts.css`.
Historia i stany zachowują te adresy, a `connections` nakłada zapisany ring.
Przejścia do późniejszych grup maszyn i ringu pozostają zakresem .3/.4.

V6: podświetlenie hover/focus w prezentacji ograniczono do około 20%
intensywności v5. Alpha poświaty assetu .9 → .18; kolor obrysu i cieni
halo ma alpha .2. Halo jest dodatkowo rozmyte o 1 px, aby osłabić widoczny
kontur przy dużej skali. Nie zmniejszamy opacity samej części. Rytm ruchu
i pulsowania zachowany, CSS mapy bez zmian. Nadpisuje intensywność opisaną
niżej dla pierwotnego przeniesienia efektu z mapy.

Korekta v3: pierwszy plan może częściowo wychodzić poza kadr. V4 wychodzi
za prawą krawędź w obu formatach, V1 dodatkowo za lewą na portrait.
W obrębie grup zróżnicowano skalę (mnożnik bazowego rozmiaru) oraz obrót
samych obrazów. Pozycje, skale i obroty są utrwalone w parts.html.
Podpisy nie obracają się wraz z assetem, a przy skrajnych elementach są
przesunięte do wnętrza kadru. Dolny pasek ma własne ciemne pole ponad
kompozycją. Nieregularność jest reżyserowana, bez losowania przy renderze.

Wersja 2 zastępuje poprzednią płaską siatkę. Pozycje oznaczają środki
obiektów w procentach pola części, osobno dla obu formatów.
Plan 1: Virex / V1–V5; plan 2: Echo / E1–E5; plan 3: Phantom / P1–P5;
plan 4: Sentinel / S1–S5. Przypisanie planów jest kompozycyjne, nie rankingowe.

Szerokość części względem pola: desktop 24%, 15%, 11%, 7,2%; portrait 30%,
19%, 14%, 9%. Pierwszy plan +20%, ostatni −10% względem v3; indywidualne
mnożniki i pozycje zachowane. Warstwy bliższe zasłaniają dalsze, kontrast maleje w głąb.
Rozkład ma wyglądać swobodnie i losowo, ale jest utrwalony dla odtworzenia
po seek i dla ciągłości między scenami. Bez losowania nowych pozycji co klatkę.

Transformacja część → węzeł zaczyna się w tym samym środku. Następnie
węzeł przechodzi na pozycję w ringu zamrożonego cyklu; w makiecie tożsamość
indeksów wynika z TOPOLOGY_ANCHOR w katalogu. Brak historycznego ring_codes
w runtime wymaga jawnego fallbacku, nie dopisania połączeń.
Przejście do grupy i maszyny zachowuje kod, machine_code i slot 1–5.
Układ docelowy grupy ustalamy z kompozycją maszyny w .4; kolejność odkryć
może zmieniać odsłanianie, ale nie tożsamość ani adres części.

Najdalsze plany pokazują kody; nazwy pozostają w HTML dla dostępności,
a pełna ekspozycja części będzie rozwijana w kolejnych scenach .2.
V4 dodaje oddychanie istniejącą animacją ghostnetwork-part-active-float,
spowolnioną do 6,8–8,4 s i z przesuniętymi fazami. Hover/focus stosuje
efekt aktywnej części z mapy: poświata rgba(183,255,53,.9) o promieniu
7 px, active-float 2,8 s i halo active-pulse 1,55 s. Źródło:
ghostnetwork_map.css; obrót assetu jest na osobnym wrapperze.
Reduced motion wyłącza ruch i puls, pozostawiając statyczne podświetlenie.
Para v6 została zaakceptowana. Cztery sceny .2 są wdrożone;
docelowe transformacje sieci i maszyn pozostają w .3/.4.

V5 koryguje nadmierne +40% z v4 do +20% względem v3. Dodano wspólny
glitch mapy w tle (slow 7 s / overloaded 5 s) oraz efekty OFS napisów,
kodów, legendy i nagłówka. Trzy istniejące keyframes OFS wydzielono bez
zmian do ofs_ambient_effects.css, importowanego również przez style.css.
Podgląd ma wyłącznie lokalny zegar dekoracji, startujący od 01:15;
zatrzymuje timer w tle/po opuszczeniu strony. To nie kontroler show.
Reduced motion wyłącza glitch i animacje. Układ części pozostaje stały.

| Code | Depth | Desktop X,Y (%) | Portrait X,Y (%) | Machine slot |
| --- | --- | --- | --- | --- |
| V1 | 1 | 8, 61 | -3, 52 | 1 |
| S5 | 4 | 84, 90 | 90, 89 | 5 |
| E4 | 2 | 80, 9 | 86, 10 | 4 |
| P3 | 3 | 32, 8 | 32, 5 | 3 |
| V2 | 1 | 56, 53 | 64, 66 | 2 |
| E1 | 2 | 17, 27 | 18, 29 | 1 |
| S4 | 4 | 48, 70 | 49, 64 | 4 |
| P5 | 3 | 91, 52 | 91, 56 | 5 |
| V3 | 1 | 30, 85 | 24, 86 | 3 |
| S2 | 4 | 65, 10 | 73, 7 | 2 |
| E5 | 2 | 68, 86 | 62, 91 | 5 |
| P1 | 3 | 8, 11 | 11, 12 | 1 |
| V4 | 1 | 104, 73 | 105, 81 | 4 |
| E3 | 2 | 52, 17 | 51, 17 | 3 |
| S1 | 4 | 46, 6 | 53, 5 | 1 |
| P4 | 3 | 10, 82 | 12, 73 | 4 |
| V5 | 1 | 88, 29 | 86, 35 | 5 |
| S3 | 4 | 32, 29 | 33, 27 | 3 |
| E2 | 2 | 38, 44 | 44, 49 | 2 |
| P2 | 3 | 69, 38 | 70, 29 | 2 |
