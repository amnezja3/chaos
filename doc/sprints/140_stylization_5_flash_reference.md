# .5 — błysk i kanał 2108: para referencyjna

Status: `REFERENCE / AUTHOR REVIEW PENDING`.

[Desktop i portrait](../../static/references/ghostsignal/transmission-flash-pair.html).
Adres po push/pull: `/static/references/ghostsignal/transmission-flash-pair.html?v=flash-ref-1`.
Przyciski: przed błyskiem, odtworzenie, terminal. Błysk nie zapętla się.

Oprawa i pole obrazu pozostają takie jak w zaakceptowanym filmie.
Overlay obejmuje cały kadr sceny. Trzy ekspozycje zmieniają się skokowo:
poziomy pasek wysokości 3% / 100 ms, prostokąt wysokości 75% z równymi
marginesami góra/dół / 150 ms, biały ekran / 1000 ms. Potem 250 ms
wygaszenia z przezroczystością `1 - t²`: początkowo wolno, później szybciej.
Nie ma interpolacji geometrii pomiędzy klatkami. Reduced motion pomija błysk.

Po błysku pole filmu pokazuje terminal. Zapis → ślad → kanał 2108
pozostają w tej samej scenografii. Typewriter odtwarza przykładowy tekst
oznaczony jako referencyjny, z zawijaniem i przewijaniem do końca przekazu.
To nie jest produkcyjna treść sygnału. Przy integracji wykorzystamy istniejące
dane i bramkę sygnału; ta makieta nie zmienia backendu ani czasu show.

Podgląd jest bez dźwięku; pokazuje poster przed błyskiem i przykładowe logi.
Sprawdzono składnię JS oraz granice 100/250/1250/1500 ms, narastające tempo
wygaszenia i uruchomienie tekstu. Odbiór wizualny w przeglądarce otwarty.
