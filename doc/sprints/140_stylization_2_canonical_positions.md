# .2 — canonical positions v2

REFERENCE / FOUR DEPTH PLANES / AWAITING AUTHOR REVIEW

Wersja 2 zastępuje poprzednią płaską siatkę. Pozycje oznaczają środki
obiektów w procentach pola części, osobno dla obu formatów.
Plan 1: Virex / V1–V5; plan 2: Echo / E1–E5; plan 3: Phantom / P1–P5;
plan 4: Sentinel / S1–S5. Przypisanie planów jest kompozycyjne, nie rankingowe.

Szerokość części względem pola: desktop 20%, 15%, 11%, 8%; portrait 25%,
19%, 14%, 10%. Warstwy bliższe zasłaniają dalsze, a kontrast maleje w głąb.
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
To jedna statyczna para do akceptacji. Ruch, paralaksa i reszta grupy
nie zostały jeszcze zaimplementowane.

| Code | Depth | Desktop X,Y (%) | Portrait X,Y (%) | Machine slot |
| --- | --- | --- | --- | --- |
| V1 | 1 | 15, 62 | 20, 56 | 1 |
| S5 | 4 | 30, 37 | 90, 76 | 5 |
| E4 | 2 | 82, 19 | 81, 18 | 4 |
| P3 | 3 | 70, 13 | 34, 9 | 3 |
| V2 | 1 | 38, 82 | 67, 68 | 2 |
| E1 | 2 | 12, 36 | 18, 33 | 1 |
| S4 | 4 | 77, 53 | 56, 59 | 4 |
| P5 | 3 | 12, 88 | 91, 56 | 5 |
| V3 | 1 | 67, 70 | 25, 85 | 3 |
| S2 | 4 | 53, 14 | 71, 8 | 2 |
| E5 | 2 | 62, 93 | 48, 96 | 5 |
| P1 | 3 | 25, 19 | 16, 16 | 1 |
| V4 | 1 | 85, 87 | 76, 89 | 4 |
| E3 | 2 | 59, 36 | 48, 22 | 3 |
| S1 | 4 | 35, 9 | 52, 8 | 1 |
| P4 | 3 | 92, 62 | 15, 72 | 4 |
| V5 | 1 | 84, 43 | 77, 42 | 5 |
| S3 | 4 | 60, 55 | 33, 27 | 3 |
| E2 | 2 | 38, 49 | 46, 45 | 2 |
| P2 | 3 | 47, 28 | 70, 29 | 2 |
