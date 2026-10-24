# Znikające pole main po przejęciu filarów — 24.10.2026

Odczyt VPS przekazany przez operatora: player_areas 453761, owner main,
active, 9 różnych wierzchołków, Valid Geometry, publikacja 226. Bounds:
20.1131042 / 51.9610687 / 22.2832641 / 52.6441913. Rozpiętość długości
2.1701599 stopnia. Worker opublikował przejęcie i rozliczenie progresji.
Pole run ma rozpiętość około 1.32 stopnia i pozostawało widoczne.

Przyczyna: isSaneTerritoryPolygon w map_template.html odrzucał każdą geometrię
o latSpan lub lngSpan >2.0. Nowa publikacja była pomijana przy wymianie warstw,
a poprzednia warstwa usuwana. Markery konfliktu pozostały niezależne.
Operator potwierdził identyczny warunek na VPS przez grep.

Poprawka usuwa limit rozpiętości wyłącznie w rendererze. Nadal wymagane są
minimum trzy różne punkty, skończone liczbowe współrzędne i zakresy lat/lng.
Nie zmienia kanonicznej geometrii, spójności klastrów, rozliczeń, własności,
konfliktów ani bazy. Nie dodaje nowego limitu, który ukryłby kolejne duże pole.
Obsługa topologii i budowa terytoriów pozostają odpowiedzialnością backendu.

## Weryfikacja

- Node: test_territory_geometry_display.js PASS — rozpiętość raportowana na VPS,
  wzrost szerokości geograficznej, zwykłe pole, odrzucanie NaN/Infinity,
  niedozwolonych współrzędnych, pustych/uszkodzonych i powtarzających się punktów.
- Node: test_map_snapshot_recovery.js PASS.
- Playwright MCP: lokalny tools/territory_display_fixture.py, prawdziwy Leaflet
  1.9.3, produkcyjne funkcje walidacji i atomowej wymiany warstw. Dwa syntetyczne
  prostokąty o bounds z raportu, nie pełna geometria produkcyjna. Bez bazy gry,
  mapowych kafelków i API; biblioteka Leaflet pobrana z CDN.
- Funkcja z HEAD odtwarza błąd: po wzroście mainVisible=false, jedna warstwa.
  Poprawka: mainVisible=true, span=2.1701599000000016, niepusta ścieżka SVG,
  dwie warstwy po trzech odświeżeniach i na viewport 390x844. Brak duplikatów.
  Końcowa konsola: 0 błędów i ostrzeżeń. Browser i fixture zamknięte.

Pełne starsze testy kontraktowe nie są zielone: loader 21 testów/3 failures,
cutover 31 testów/2 failures/1 error. Niepowiązane asercje dotyczą literalnych
tekstów sprzed lokalizacji, wycinania animacji avatara oraz inspekcji starej
funkcji gonna_win zamiast wrappera. Nie pominięto tych wyników w odbiorze.
Powtórzenie na niezmienionych testach i szablonie z HEAD potwierdziło te same
5 failures i 1 error (52 testy, 4.185 s); nie są regresją tej poprawki.

## Wdrożenie

Po push/pull przeładować wyłącznie web:
`pm2 startOrReload ecosystem.web.config.js --only chaos --update-env`.
Po HTTP 200 ponownie otworzyć mapę, aby przeglądarka pobrała nowy szablon.
Samo odświeżenie snapshotu w starej karcie nie wymienia załadowanej funkcji JS.
Nie przebudowywać terytoriów i nie modyfikować bazy ani stanu workera.
Odbiór VPS PASS: po wdrożeniu pakietu 4c6322e operator potwierdził powrót pola
main i przekazał zrzut mapy z widocznym zielonym wielokątem oraz markerami.
Potwierdzenie dotyczy renderowania w grze; nie wykonywano naprawy danych.
