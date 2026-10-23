# Sprint 163 — pierwszy etap pasywny, 23.10.2026

Status: implementacja lokalna, nie pełny PASS 163. Produkcja bez zmian.

`discovery_queue.py` ponownie wykorzystuje SQLite POI. Jawna inicjalizacja przez
`tools/poi_world.py --discovery`; brak migracji przy skanie gracza. Tryb domyślny
`CHAOS_POI_DISCOVERY_MODE=off`, opcjonalnie `passive`.

Zapotrzebowanie agreguje sektory 0,01 stopnia i sześć warstw, bez identyfikatora
gracza, sesji, dokładnej pozycji lub trasy. To przybliżona lokalizacja świata gry,
nie dowód coverage ani deklaracja pełnej anonimowości wobec korelacji z innymi
danymi. Maksymalnie 2000 wpisów, wygasanie 24 h od ostatniego zapotrzebowania,
czyszczenie do 100 wygasłych wpisów przy zapisie; bez rekurencyjnych sąsiadów.
Wygasłe wpisy nie są wyświetlane. Bez nowego ruchu fizycznie pozostają do prune.

Stan to tylko PENDING. Nie ma workera, retry, pobierania w tle ani kosztów API.
To fundament 163.1, nie realizacja całej kolejki opisanej w sprincie.

Panel istniejącego admina pokazuje snapshoty/freshness, flagi, księgę kredytów
i maksymalnie 100 ostatnich sektorów zapotrzebowania. Te sektory nie oznaczają
obszarów z kompletnymi danymi. Liczniki kredytów to wewnętrzna księga CHAOS,
nie saldo panelu dostawcy. Podgląd nie uruchamia HTTP do dostawcy.

5 testów kolejki: dedup sześciu warstw, TTL, limit bez ekspansji, cztery procesy
zapisujące ten sam sektor, podgląd bez zmiany księgi, granice współrzędnych.
Pełny World: 107 PASS (46,198 s), łącznie z magazynem i integracją.
Regresja POI: 87 PASS (87,644 s). Po rozszerzeniu kontroli niezmienności tabel
księgi: 5 testów kolejki PASS (4,158 s). `git diff --check` i składnia JavaScript
panelu oraz obu ecosystemów: PASS.

Playwright MCP na izolowanym `tools/poi_admin_fixture.py --world`:
- PL mobile 390×844 i EN desktop 1440×900: poprawne etykiety, brak overflow;
- 3 sektory, 18 wpisów warstw, budżety 0/800 i 0/24000;
- zrzut sekcji mobilnej obejrzany; mapa sektorów i liczby czytelne;
- końcowy przebieg EN: 0 błędów/ostrzeżeń konsoli. W fixture poprawiono 404 favicon;
- powtórny GET nie dowodzi identyczności całego JSON: granice ruchomego okna
  kredytów zależą od czasu. Brak mutacji tabel księgi sprawdza test jednostkowy.

Do następnych etapów pozostają: worker z lease/fencing/priorytetem live,
certyfikowane pobieranie warstw, szczegółowa mapa coverage, filtry i statystyki,
obserwacja zasobów na VPS oraz osobno zatwierdzony pilot background.
Nie uruchomiono API MapLark/Geoapify, nie zmieniono zgód ani limitów produkcji.
