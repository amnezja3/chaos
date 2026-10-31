# Camera Network — zestaw zakłóceń 1

Sześć samodzielnych assetów SVG, przygotowanych proceduralnie dla CHAOS.
Nie zawierają obrazów graczy, zasobów zewnętrznych, skryptów ani fontów.
`manifest.json` jest indeksem zasobów i scenariuszy.

| Asset | Zastosowanie w pilocie |
| --- | --- |
| fine-grain.svg | Stałe, subtelne ziarno sensora; mała tekstura kafelkowana |
| scan-lines.svg | Stałe linie skanowania |
| tracking-band.svg | Krótki przesuwany pas co 49 s |
| chroma-tear.svg | Krótki rozjazd składowych koloru co 67 s |
| compression-blocks.svg | Krótkie bloki utraconych danych co 83 s |
| signal-dropout.svg | Tło NO SIGNAL i RECONNECTING |

Warstwy działają wyłącznie wewnątrz kadru, pod logo/HUD/logami. Nie przechwytują
kliknięć i są ukryte dla technologii asystujących. Nie modyfikują obrazu źródłowego,
wyboru zdjęcia ani zapisanej ścieżki ruchu. Efekty nie sterują stanem sesji.
Minimizacja i pauza połączenia zatrzymują animacje; reduced-motion pozostawia
tylko statyczną bazę. Krótkie zakłócenia są dekoracją symulacji; rzeczywisty brak
obrazu/lease ma odrębny komunikat i używa szóstego assetu.

Integracja: `static/css/camera_visual.css`, `static/js/camera_visual.js`.
Nie dodano nowego timera, odpytywania serwera ani alternatywnego okna demonstracyjnego.
