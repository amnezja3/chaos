# Sprint 158.1 — kontrakt i baseline

18 X 2026. Przegląd lokalny wykonany; pomiar produkcyjny oczekuje na wdrożenie telemetrii z flagą OFF.

- Operator potwierdził 4 workery i timeout Gunicorn 120 s. Typ workera nie został osobno potwierdzony; plik ecosystem.web.config.js nie ustawia worker-class.
- Zwykły fetch miał już deadline 110 s. Nowa ścieżka zachowuje 110 s, connect maksymalnie 3 s, read 8 s + GhostLab 0–10 s; proces HTTP można zakończyć po deadline. Oczekiwanie na identyczny query lease: 2 s. Przy zajętym globalnym slocie: natychmiast stale albo api_error, bez długiej kolejki.
- GhostLab lease 35 s jest odnawiany przez klienta co 10 s. Anulowanie testowane przed cache, podczas oczekiwania i po ukończonym HTTP. Cały wynik gameplayu nie trafia do anulowanego skanu, kompletny surowy cache może pozostać dla innych.
- Kontrakt: nwr + out center, bez filtrowania way/relation po odległości center; kolejność kategorii, deduplikacja po współrzędnych i limit 60 zachowane.
- Stan bazowy przed zmianami: 3 testy POI i 17 testów GhostLab PASS. Nie zastępuje to pomiaru latencji/QPS VPS.
- Fixtures: tests/fixtures/poi/complete.json — node, duplikat współrzędnych, way i relation z center poza typowym promieniem. Pusty wynik i błędy są deterministycznie generowane w testach.

## Zbieranie baseline

Po wdrożeniu kodu z CHAOS_POI_INFRASTRUCTURE_ENABLED=0 log poi_scan pokazuje wynik i czas dla skanów, które doszły do fetchera. Nie obejmuje odmów autoryzacji przed fetcherem. Zbieramy 24–72 h normalnego ruchu; nie odpytywać publicznego Overpass testem obciążeniowym.

Dotychczasowe linie Overpass try pozwalają policzyć stare próby, a nowe poi_fetch/poi_http po włączeniu dają źródło i próby. Porównywać okna o znanej liczbie skanów, nie same sumy. Liczba unikalnych dokładnych kluczy ogranicza możliwy hit-rate; cache sąsiednich pozycji nie jest częścią v1.

Aktualne QPS, procent api_error, koszt CPU/RAM/I/O i stan dysku produkcji: **niezmierzone**. Nie wpisujemy fikcyjnych wyników ani procentu poprawy.
