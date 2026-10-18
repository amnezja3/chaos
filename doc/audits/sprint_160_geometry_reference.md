# Sprint 160 — niezależna referencja geometrii

2026-10-18. Referencję wykonał operator na izolowanej bazie syntetycznej,
bez sieci kontenera, portów i zmian w działającej grze.

- Overpass: `0.7.62.3 00a720d2`.
- Obraz zgłoszony przez operatora: `wiktorn/overpass-api:v0.7.62.3`.
- Digest pobrania: `sha256:a9ddf6394345ada688fe7791db5092d2bfdad297af0d52a96bab59aaf0aa22a0`.
- Dokładne odpowiedzi i hashe binariów: `tests/fixtures/poi/geometry_reference.json`.
- Wejście: `tests/fixtures/poi/geometry_source.osm`; hash wejścia jest sprawdzany w teście.
- Zapytania pochodzą z rzeczywistej metody `POIFetcher._build_query`, nie z algorytmu lokalnego.

| Przypadek | Obiekty Overpass | Porównanie lokalne |
| --- | ---: | --- |
| origin | 5 | PASS |
| nearby | 6 | PASS |
| edge | 7 | PASS |
| small | 3 | PASS |
| empty | 0 | PASS |
| larger | 7 | PASS |

Porównujemy całe listy elementów, identyfikatory, tagi, węzły/members i center.
Dodatkowo rzeczywista fasada skanera porównuje kategorie, kolejność, deduplikację
oraz limity 0/2/60. Oczekiwania pochodzą wyłącznie z odpowiedzi Overpass.

Wynik potwierdza przecięcie koła przez way ze środkiem poza zasięgiem oraz
brak automatycznego trafienia zamkniętego obrysu obejmującego gracza.
Relacja zawierająca wyłącznie relację nie trafiła do żadnej z sześciu odpowiedzi.
Semantykę bezpośrednich node/way members dodatkowo sprawdzono w
[implementacji upstream](https://github.com/drolbr/Overpass-API/blob/master/src/overpass_api/statements/around.cc).
Nie przeniesiono kodu upstream do CHAOS; obliczenia odległości są własną implementacją.

## Granice dowodu

`geometry.py` jest podłączone do Service za domyślnie wyłączonymi flagami 160. Nie certyfikujemy
światowego pokrycia na podstawie sześciu przypadków. Brakujące dependencies,
przypadki graniczne do 1 m, okolice biegunów/antymeridianu, długie segmenty,
nieobsługiwany promień i środki wybranych relacji zagnieżdżonych kończą się
odmową lokalnego rozstrzygnięcia.

`CoveredGeometry` wymaga zgodnych filtrów i zawierania całego koła skanu
w pojedynczym obszarze pobrania; nie łączy niepełnych snapshotów. Testy storage
potwierdzają lokalny wynik sąsiednich skanów po odtworzeniu SQLite, puste pokrycie,
fencing, terminy ważności i odrzucenie uszkodzonego payloadu. Dane wejściowe tych
testów storage po przyjęciu drugiej referencji pochodzą z rzeczywistej odpowiedzi
`geometry_wide_reference.json`, nie z rekonstrukcji syntetycznego XML.
Licznik `certified_cells` pozostaje 0; zapisy mają profil experimental.

Operator wykonał także `tests/fixtures/poi/geometry_wide.ql` na tej samej bazie.
Odpowiedź `tests/fixtures/poi/geometry_wide_reference.json` zawiera 19 obiektów:
13 nodes, 4 ways i 2 relations. Generator i identyfikator bazy zgadzają się z exact
referencją, wszystkie elementy są zgodne z wejściowym XML. Pełne dependencies
obejmują także węzły poza promieniem pobrania; nie obcinamy geometrii do koła.

Pięć mieszczących się skanów (origin, nearby, edge, small, larger) odtworzono
z tej jednej odpowiedzi: identyczne elementy i wynik fasady dla limitów 0/2/60.
Punkt empty leży poza pobranym obszarem i prawidłowo daje brak pokrycia, a nie
lokalny pusty sukces. Testy geometrii oraz storage: **10 PASS (0,662 s)**.
Nie wykonano nowych żądań do publicznych endpointów Overpass.

Referencja pełnego pobrania jest dostarczona. Integracja wspólnego budżetu,
anulowania i scope dostawcy ma testy PASS: cztery procesy współdzielą jeden fill;
wadliwa geometria przechodzi do exact w tym samym deadline i pozostałych próbach;
anulowany skan nie wydaje gameplayu. Dalsze bramki to zakres rzeczywistego dostawcy,
pilotaż, szersza regresja i kontrolowany rollout. To nie jest jeszcze PASS całego Sprintu 160.
Flagi produkcji pozostają bez zmian.
