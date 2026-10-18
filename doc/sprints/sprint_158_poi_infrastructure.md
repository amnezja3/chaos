# Sprint 158 — niezawodna infrastruktura POI

Status: **implementacja lokalna i testy ukończone; baseline i wdrożenie produkcyjne oczekują**. Data: 18 października 2026.
Identyfikator: `CHAOS.POI.INFRASTRUCTURE.V1`.

Stan odbioru: [macierz dowodów](../audits/sprint_158_evidence.md). Konfiguracja i wdrożenie: [runbook](../runbooks/poi_infrastructure_158.md). Poniższy zakres pozostaje kontraktem sprintu; lokalny PASS nie oznacza odbioru produkcji.

Źródło: [CHAOS POI Infrastructure v1](../prototypes/poi/CHAOS_POI_INFRASTRUCTURE_V1_CONCEPT.md). Sprint realizuje pierwszą wersję koncepcji, bez opcjonalnego cache sąsiednich obszarów.

## Cel i granica zakresu

Skan ma korzystać z trwałych danych OSM i kontrolowanej liczby zapytań do Overpass, zachowując obecne reguły gry. Identyczne zapytania współdzielą surowe dane, ale każdy gracz otrzymuje osobno przetworzony wynik.

Warstwa pozostaje wewnątrz aplikacji jako biblioteka za fasadą `POIFetcher`; nie tworzymy mikroserwisu, nowego publicznego API ani własnego Overpassa. Oddzielna baza SQLite WAL na lokalnym dysku jest rozwiązaniem dla jednego hosta. Potwierdzenie topologii jest warunkiem wdrożenia.

Poza zakresem: nowe POI/gameplay, zmiana promienia i uprawnień, ekonomia, PvP, NPC, kamery, nowa semantyka deduplikacji, migracja kont, OAuth, wiek i komunikacja z 157.8 oraz umowy powierzenia. Ich otwarty status nie zmienia się.

## Co potwierdzono w repozytorium

- `poiFetchClass.py`: cache w pamięci instancji, klucz zaokrąglony do czterech miejsc, przechowywany `overpy.Result`, fresh 300 s i stale 1800 s.
- `_fetch`: timeout klienta domyślnie 8 s, QL 15 s, wspólny deadline 110 s, ograniczone próby oraz częściowa obsługa Retry-After. Błędy parsera i nietypowych HTTP mogą ominąć stale.
- `_categorize_data` przekazuje referencje do tagów; potrzebna izolacja mutowalnych danych od cache i kolejnych żądań.
- `get_all` zachowuje kolejność kategorii, deduplikację po `(lat, lon)` i limit po kategoryzacji. To kontrakt regresyjny, nie miejsce na korektę zasad gry.
- `ghostlab_scanner.py`: aktywacja 35 s, `still_active`, `extra_retries` 0–3 i `extra_timeout` 0–10. W 158.1 sprawdzamy także odnowienia aktywacji, nie utożsamiamy 35 s z nieodnawialnym limitem całego skanu.
- `run.py` ma globalną instancję fetchera i per-graczowe przetwarzanie wyniku. Globalna instancja nie oznacza współdzielenia pomiędzy procesami.

Operator potwierdził 4 workery Gunicorn i timeout 120 s. Typ workerów, QPS i latencje produkcji pozostają do pomiaru lub odczytu na VPS. Nie zakładamy określonego procentu poprawy. Stan koncepcji z 17 października nie zastępuje pomiarów bieżącego VPS.

## Kontrakt v1

Wejście: dokładne współrzędne, promień, filtry, wersja zapytania i formatu odpowiedzi, polityka prób/czasu, `still_active`. Wyjście: kompletny surowy wynik OSM albo sklasyfikowany błąd; fasada zachowuje dotychczasowy format i sygnatury metod.

Cache nie zawiera kont, tokenów GhostLab, oznaczonych celów, wyników uprawnień, ikon ani wygenerowanych NPC/kamer. Każdy odczyt rekonstruuje niezależne obiekty. Lokalny limit wyników nie ogranicza pobrania surowych danych ani nie czyni wpisu częściowym.

Klucz odpowiada rzeczywiście wysłanemu zapytaniu: bez zaokrąglania środka. Kanonizacja liczb, filtrów i zapytania musi być wspólna; kolejność kategorii używana w fasadzie pozostaje bez zmian. Równoważność innych reprezentacji liczb wymaga testu. Nowa semantyka = nowa wersja klucza.

Fresh i stale liczymy od ostatniego udanego pobrania. Granicę stale sprawdzamy przy wydaniu wyniku, także po długiej próbie HTTP. Odczyt i nieudany refresh nie przedłużają TTL. Pusty, kompletny wynik jest sukcesem; błąd nie staje się pustą listą. HTTP 200 nie wystarcza: błędy runtime/remark i częściowa odpowiedź Overpass nie mogą nadpisać kompletnego cache.

## Plan etapów

### 158.1 — kontrakt, baseline i fixtures

Zakres:

- Prześledzić wszystkie wywołania metod fetchera, mapowanie wyjątków na `scan_outcome`, anulowanie, odnowienia GhostLab oraz ustawienia PM2/Gunicorn.
- Uruchomić istniejące testy skanera i zapisać wynik przed zmianami; oddzielić zastane błędy od regresji.
- Przygotować deterministyczne odpowiedzi OSM: node/way/relation, duży way z center poza promieniem, nakładające się kategorie, wspólne współrzędne, pusty wynik, błędy i częściowy JSON.
- Utrwalić oczekiwany wynik fasady: pola, kolejność, limity i deduplikacja. Nie generować wzorca przez nową implementację.
- Uzgodnić liczbowy budżet czasu skanu i oczekiwania na podstawie serwera oraz GhostLab. Rejestrować baseline błędów, wywołań upstream, p50/p95/p99 i obciążenia, bez identyfikatorów graczy.

Artefakt: `doc/audits/sprint_158_1_contract_baseline.md`, fixtures i testy charakterystyki. Minimum 24 h obserwacji normalnego ruchu, docelowo 24–72 h; przy małej liczbie skanów raportować liczebność i wydłużyć pomiar. Kod kolejnych etapów można przygotowywać podczas pomiaru, ale nie ogłaszać poprawy bez danych.

Odbiór: znamy granicę infrastruktura/gameplay, zastane wyniki testów, konfigurację czasu oraz sposób porównania przed/po. Brak dostępu do VPS oznacza otwarty punkt pomiarowy, nie domniemany PASS.

### 158.2 — kompletne dane, dokładny klucz i trwały cache

Zakres:

- Moduły query/repository/service pod istniejącym `POIFetcher`.
- Osobny plik `data/poi_cache.sqlite3`, WAL, wersjonowany schemat, krótkie transakcje i ograniczony busy timeout. Brak migracji tabel graczy.
- Bezstratny JSON z metadanymi, hashem, rozmiarem i czasem pobrania; walidacja przy zapisie/odczycie oraz odrzucenie uszkodzonego wpisu.
- Fresh/stale zgodne z kontraktem, także dla pustego wyniku. Rekonstrukcja `overpy.Result` per skan; żadnej współdzielonej mutowalnej instancji.
- Limity liczby elementów i rozmiaru odpowiedzi, w tym wielkości po dekompresji; przekroczenie to błąd, nie ucięty sukces.
- Nie importować bez dowodu kompletności `poi_cache.json` z metod diagnostycznych: zawiera dane po kategoryzacji, nie pełny surowy cache.

Odbiór: A01, A02, A05, A11–A14, A16; powtarzany odczyt nie wymaga HTTP, restart nie usuwa wpisu, mutacja jednego wyniku nie wpływa na drugi. W tym etapie brak zgody na produkcyjne włączenie bez koordynacji z 158.3.

### 158.3 — koordynacja między procesami

Zakres:

- Lease dla klucza z generacją/fencing; atomowe zajęcie, odnowienie i zwolnienie. Spóźniony właściciel nie zapisuje ani nie zwalnia cudzego lease'a.
- Globalne sloty upstream, również z wygaśnięciem po awarii. Propozycja startowa: jeden aktywny request na VPS.
- Oczekujący mają ograniczony czas i odczytują wynik zwycięzcy; brak nieograniczonej kolejki i brak HTTP w transakcji SQLite.
- Anulowanie oczekującego dotyczy tylko jego skanu. Właściciel rozpoczętego HTTP kończy ograniczoną czasem próbę i może opublikować kompletny surowy cache, ale nie wynik gameplayu anulowanemu graczowi. Po utracie uprawnienia nie rozpoczyna kolejnej próby na rzecz własnego skanu.
- Przed każdą próbą sprawdzenie własności lease'a i budżetu. Utrata lease'a zatrzymuje kolejne próby i zapis. Recovery nie może pozostawić trwałego zakleszczenia.

Odbiór: A03, A04, A10, A11 oraz testy rzeczywistych procesów korzystających z jednej bazy, nie tylko wątków. Jedna próba dla równoczesnego identycznego miss przy zdrowym właścicielu; po jego awarii kontrolowane przejęcie i brak starego zapisu. Wygaśnięcie lease'a nie dowodzi anulowania pracy już wykonywanej przez zewnętrzny serwer — opisujemy tę granicę gwarancji.

### 158.4 — odporność Overpass i wartość GhostLab

Zakres:

- Wspólny klient HTTP: rozdzielone connect/read timeout, ograniczenie całej operacji (także wolnego strumienia), jawna identyfikacja CHAOS.
- Bounded exponential backoff z jitterem; Retry-After w sekundach i dacie HTTP, bez skracania oczekiwania dla kolejnej próby. Gdy termin nie mieści się w budżecie: stale albo `api_error`.
- Wspólny stan circuit breaker: closed/open/half-open, pojedyncza próba kontrolna, cooldown współdzielony przez procesy i aliasy tej samej infrastruktury.
- Nie obchodzić 429 rotacją aliasów. Lista dozwolonych endpointów i grup ustalona przy implementacji na podstawie aktualnych zasad dostawców.
- Timeout, błąd sieci, 429/502/503/504: ograniczone ponowienie; 400/401/403/406: brak pętli, sklasyfikowany błąd i dopuszczalny stale. Błąd JSON/Overpass runtime: brak zapisu, zachowany fallback.
- GhostLab zwiększa dozwolone próby/czas w ramach globalnej ochrony; demonstracyjny test: bazowy skan kończy próby, ulepszony korzysta z dodatkowej dozwolonej próby i odnosi sukces. Żaden nie omija circuit lub Retry-After.

Odbiór: A06–A10 i A16; kontrola liczby requestów i czasu za pomocą deterministycznego zegara oraz lokalnego serwera HTTP. CI nie wysyła obciążenia do publicznego Overpass.

### 158.5 — limity, telemetria i degradacja lokalna

Zakres:

- Konfigurowalne limity cache, sprzątanie w małych partiach, ochrona aktywnych lease'ów i ograniczenie wielkości WAL. Rozróżnić logiczny rozmiar payloadów od fizycznego rozmiaru SQLite/WAL.
- Brak dużego VACUUM podczas requestu; checkpoint/utrzymanie opisane w runbooku. Test disk-full, busy, uszkodzony cache i brak praw do katalogu.
- Przy awarii koordynatora nie wykonywać niekoordynowanych requestów jako cichego fallbacku. Użyć zwalidowanego dostępnego stale albo `api_error`; powrót do starej ścieżki tylko świadomą flagą operatora.
- Metryki fresh/upstream/stale/error, próby na skan, czas całości i oczekiwania, circuit, lease, wpisy/bajty/evictions. Sposób agregacji wykorzystuje istniejącą infrastrukturę, bez obowiązkowej nowej platformy monitoringu.
- Logi z losowym request ID, skrótem klucza, źródłem i klasą błędu. Bez nicków, tokenów, dokładnych współrzędnych, treści tagów i dynamicznych kluczy jako etykiet metryk.
- Surowe OSM mogą zawierać nazwy lub dane kontaktowe: nie nazywać cache automatycznie anonimowym. Ograniczyć dostęp do pliku i nie kopiować do niego danych kont. Zachować atrybucję OSM; warunki dostawców/licencji sprawdzić przed wdrożeniem.

Odbiór: A15, brak lawiny HTTP przy awarii SQLite, ograniczona zajętość dysku i brak blokowania profili graczy. Operator odróżnia awarię dostawcy od błędu cache i anulowania skanu.

### 158.6 — integracja, regresja i pakiet wdrożeniowy

Zakres:

- Integracja fasady pod proponowaną flagą `CHAOS_POI_INFRASTRUCTURE_ENABLED=0`; domyślnie stara ścieżka do odbioru. Ostateczne nazwy konfiguracji opisać w jednym miejscu.
- Całość A01–A16, regresja skanerów oraz izolacja dwóch graczy. Testy symulowanego przeciążenia w wielu procesach z lokalnym dostawcą.
- Playwright MCP: mapa i skan zwykły/GhostLab, sukces, stale, brak danych przy awarii, wygaśnięcie/zamknięcie skanera, PL/EN, desktop/mobile. Użyć izolowanych kont i lokalnych fixtures; sprawdzić widoczny wynik, konsolę i brak przecieku markerów. Nie pytać operatora o testy możliwe lokalnie.
- Przygotować runbook, macierz dowodów, konfigurację, sekwencję startu bazy i restartów, backup konfiguracji oraz rollback. Cache jest odtwarzalny; nie usuwać ani nie zmieniać `game.sqlite3`.

Odbiór: komplet wymaganych lokalnych PASS, diff do przeglądu, jawne wyniki/ograniczenia, brak zmiany reguł gry. Artefakty: `doc/runbooks/poi_infrastructure_158.md` i `doc/audits/sprint_158_evidence.md`. Na tym etapie jeszcze nie pełny PASS produkcyjny.

### 158.7 — wdrożenie, obserwacja i zamknięcie

Zakres:

- Osobna zgoda na wdrożenie. Potwierdzić jeden host, wspólną ścieżkę i prawa dostępu dla wszystkich workerów, zapas dysku, parametry czasu oraz wyłączoną początkowo flagę.
- Sprawdzić inicjalizację schematu i smoke z flagą OFF; włączyć kontrolowanie. Canary tylko dla izolowanego procesu/ruchu, który nie podwaja zapytań i jest uwzględniony w budżecie. Gdy takiego podziału nie ma, użyć krótkiego okna kontrolowanego z jednym globalnym przełączeniem. Nie udawać canary per gracz przy globalnym fetcherze.
- Nie porównywać starej i nowej ścieżki przez podwojenie ruchu publicznego; porównanie semantyki wykonane na tym samym fixture.
- Potwierdzić fresh po powtórzeniu skanu i po restarcie procesu, dostępność starego cache po restarcie, działanie zwykłego skanera/GhostLab i izolację graczy.
- Zebrać 24–72 h danych po włączeniu, porównać z baseline przy jawnej liczebności, obciążeniu i warunkach upstream. Spadek requestów dla powtarzanych skanów i brak regresji są mierzalne; jeśli brak awarii upstream, skuteczność stale potwierdzają testy awarii, nie wymyślony procent produkcyjny.

Rollback: wyłączyć flagę w trwałej konfiguracji i zrestartować wszystkie korzystające z niej procesy. Pozostawić cache do diagnostyki. Stara ścieżka nie ma nowego wspólnego limitu, więc obserwować ruch; nie otwierać automatycznie pętli prób w czasie awarii. Przećwiczyć rollback i powrót przed zamknięciem.

Odbiór: macierz produkcyjna, pomiar efektu, brak regresji gameplayu, udany restart i rollback. Pełny PASS 158 dopiero po tym etapie; nie przypisujemy go na podstawie samych testów jednostkowych.

## Macierz testów koncepcji

| ID | Odpowiedzialny etap | Dowód |
| --- | --- | --- |
| A01–A02 | 158.2 | cache hit bez HTTP; rozróżnienie pobliskich środków |
| A03–A04 | 158.3 | test wieloprocesowy, awaria i fencing |
| A05 | 158.2, 158.7 | trwałość na dysku i restart produkcyjny |
| A06–A09 | 158.4 | awarie, parser, Retry-After i circuit |
| A10 | 158.3–158.4, 158.6 | anulowanie, GhostLab i jego dodatkowa próba |
| A11, A13 | 158.2, 158.6 | izolacja mutacji i wyników dwóch graczy |
| A12 | 158.1–158.2 | node/way/relation i center poza okręgiem; bez lokalnego odcinania |
| A14 | 158.2 | pusty kompletny wynik jako sukces |
| A15 | 158.5 | limity, sprzątanie, WAL, błędy storage |
| A16 | każdy etap, finał 158.6 | test_ghostlab_scanner, test_poi_fetcher_geometry, test_poi_fetcher_latency_contract |

Dodatkowo: częściowy wynik HTTP 200, nieaktualne stale po oczekiwaniu, utrata globalnego slotu, powolna odpowiedź przekraczająca deadline, konkurencyjny half-open, restart podczas cleanup. Testy zachowują reguły gry; nie osłabiamy asercji, żeby wymusić PASS.

## Parametry i decyzje operacyjne

| Parametr | Punkt wyjścia | Kiedy ustalić |
| --- | --- | --- |
| Fresh/stale | 300/1800 s od udanego fetch | Zachować w v1, jawnie potwierdzić przy odbiorze |
| Storage | osobna SQLite WAL, jeden lokalny host | 158.1: topologia; 158.2: schemat |
| Równoległe HTTP | propozycja 1 na VPS | 158.3 i pomiar obciążenia |
| Deadline, connect/read, lease | brak arbitralnego nowego limitu | 158.1–158.4; spójność z Gunicorn i GhostLab |
| Rozmiar odpowiedzi/cache/WAL, cleanup | obowiązkowe skończone limity | 158.2/158.5 na podstawie fixtures i wolnego dysku |
| Endpointy i grupy | nie zakładać niezależności aliasów | 158.4, aktualne zasady dostawców |
| Flaga | OFF przed odbiorem | 158.6–158.7 |
| Cache a backupy | dane odtwarzalne, bez obowiązku pełnego backupu cache | runbook 158.6; nie zmieniać retencji danych graczy |

Budżety prób i czasu muszą być zapisane liczbowo przed odbiorem implementacji. Nierozstrzygnięty parametr oznacza brak odpowiedniej bramki PASS, a nie nieograniczony fallback.

## Kolejność i zakres pracy

158.1 → 158.2 → 158.3 → 158.4 → 158.5 → 158.6 → 158.7.

Kod i lokalne testy zostały wykonane na polecenie operatora. Operator dostarcza odczyty produkcyjne, gdy brak dostępu, zatwierdza wdrożenie i potwierdza gameplay. Naturalnego ruchu pomiarowego nie zastępujemy sztucznym obciążaniem publicznych endpointów. Włączenie nowej warstwy na produkcji pozostaje osobnym krokiem po baseline.

## Backlog po 158

Cache sąsiednich obszarów, geohash/komórki, superset + pełna geometria, import przestrzenny i własny Overpass pozostają osobnymi propozycjami. Warunek rozpoczęcia: pomiary v1 uzasadniają koszt, a algorytm ma dowód zgodności `around` dla nodes/ways/relations. Samo `out center` nie wystarcza. Ten backlog nie blokuje zamknięcia 158 v1.
