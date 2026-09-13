# .7 — mapa i terytoria: pierwsza para

Status: `REFERENCE / AUTHOR REVIEW PENDING`.

Korekta v2: blok tytułu przesunięty do 9vh, ciaśniejsze odstępy podtytułu
i hasła. Na desktopie skala tytułu uwzględnia wysokość viewport (26vh),
żeby szeroki, niski ekran nie powodował kolizji z logami na 61vh.

[Desktop 1920×1080 / portrait 1080×1920](../../static/references/ghostsignal/world-pair.html).
Po push/pull: `/static/references/ghostsignal/world-pair.html?v=world-ref-2`.
Przyciski „Obszar” i „Ślad obszaru” porównują dwie ekspozycje tych samych
wierzchołków. To makieta warstw i efektów, nie wynik rozliczenia produkcji.

Kierunek autora: duży glob, siatka, zarys lądów i świetlny wielokąt.
Zachowano przygaszoną szarozieloną paletę, dużą typografię, OFS, glitch
i pulsujące węzły. Desktop: glob dominuje po prawej, komunikat i logi po
lewej. Portrait: nagłówek, kołowy glob, logi i legenda pod nim. SVG ma
kwadratowe pole; nie rozciąga globu w elipsę.

Kontury lądów: [Natural Earth, ne_110m_land.geojson](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_land.geojson),
lokalna kopia w `static/references/ghostsignal/world-land.geojson`.
To lokalny zasób referencji, bez zewnętrznych requestów podczas podglądu.
Rzut ortograficzny skierowany na Europę/Afrykę. Za horyzontem linie są
ukryte; kontury przecinające horyzont pozostają bez wypełnienia.

Trójkąt jest jawnie demonstracyjny, bez nazw właścicieli, powierzchni
i fikcyjnych statusów. Przy integracji użyjemy wyłącznie zachowanej
geometrii rozliczenia, z obsługą braku danych i obszarów poza kadrem.
Nie oznaczamy terytoriów jako zachowane/zredukowane bez źródłowego zapisu.

Do oceny: skala i kadrowanie globu, widoczność granic, łuny węzłów,
kontrast lądów i czytelność logów na obu formatach. Reduced motion
wyłącza pulsowanie. Sprawdzono składnię JS i lokalne zasoby;
odbiór wizualny w przeglądarce otwarty. Runtime i trigger bez zmian.
