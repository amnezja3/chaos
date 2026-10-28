# 163.5 — bieżący bilans odbioru, 28.10.2026

Ten dokument porządkuje istniejące dowody. Nie uruchomiono nowego pobrania,
nie zmieniono budżetów, routingu, dat świeżości ani zgód dostawców.
Historyczne statusy w traceability nie są aktualną listą zadań.

## Bieżący post VPS — PASS, 28.10.2026

Materiał operatora `bd43f156-0391-4d74-803a-71a55a6b2e44/Pasted text.txt`,
raport `/home/johndoe/chaos-world-completion-gCwuSf`. Commit należy odczytać
z `commit.txt` tego katalogu; nie był wypisany w przekazanym logu.

- `checked`, integralność/FK OK, schema 2, wszystkie wymagane schematy gotowe.
- 265 snapshotów, 20 042 354 bajty logiczne. Liczba nie jest dowodem pokrycia.
- `baseline_matches`: web i kolektor online, global ingest/read, regional read,
  wizyty, routing i halo aktywne. Świeży heartbeat `waiting`, wiek 27.7 s.
- Końcowy HTTP 200 oraz `PASS: post`. Diagnostyka: 0 wywołań dostawców,
  0 zapisów produkcyjnych; istniejący kolektor działa równolegle.
- Kolejka: 70 COMMITTED, 125 DEFERRED, 16 FAILED_TERMINAL, 52 CANCELLED;
  brak wygasłych lease i nierozstrzygniętych zadań. Same historyczne stany
  nie dowodzą bieżącej awarii; najnowsze odroczenie to `budget_scope_exhausted`.
- MapLark tło 188/200, wolne 12 < rezerwacja 20. Konto 326/800, wolne 474:
  skaner ma osobny dostęp do pozostałego budżetu konta. Ostrzeżenie
  `maplark_background_scope_exhausted` jest uzasadnione; nie zwiększamy limitu.
- Geoapify tło 186/200; pięć dawnych uncertain / 25 kredytów zachowane.
- Metryki okna: 16/16 udanych wyników, w tym 2 puste, źródła network 14 / world 2.
  To agregat istniejących wyników, nie 16 nowych testów. p95 całego skanera
  w koszyku do 30 s nie jest pomiarem p95 lokalnego readera ani jego SLO.
- Natural Earth jest teraz EXPIRED dla krótkiego TTL odczytu, ale zachowany
  w archiwum. Nie odmładzamy źródła i nie powtarzamy importu dla zielonego statusu.

Aktualny raport techniczny odebrany. W załączniku nadal nie ma potwierdzenia
bieżącego wizualnego smoke skanu i panelu; pozostaje tylko to potwierdzenie
operatora oraz jawny, odrębny brak pełnego kontraktu skanera Geoapify.

## Wykonane i odebrane

| Zakres | Dowód | Granica |
| --- | --- | --- |
| Exact repozytorium w aktywnym skanerze | VPS: `poi_maplark_cache source=world`, klucz `3e284b592d56`; odczyt na innym workerze | Exact nie zastępuje dowodu regionalnego |
| Regionalny odczyt MapLark | VPS: geometry-v2, klucze `1e27dc10d1ba` / `cfdf8bd1dde1`, ten sam snapshot, różne PID; 0.9246/0.7406 s | Zatwierdzony kontrakt CHAOS, jeden kompletny bbox; brak deklaracji parytetu całego natywnego radius |
| Wizyty bez skanu i halo | VPS: sześć warstw `origin=direct`; kolektor `committed`, halo osiem sektorów | Ograniczony popyt, nie dowód pokrycia całego świata |
| Geografia | Rzeczywiste drogi, cieki, woda z otworami; Natural Earth 5.1.1 import `894ac02a…445af`, 2 obiekty COMPLETE_FRESH | Ląd–morze 1:10 mln, nie dokładność wysp OSM ani użycie w mechanikach gry |
| Atlas, metryki i budżety | Playwright PL/EN 1440/390; viewport, unikalne ID, DB/WAL, wiek kolejki, heartbeat; VPS monitor po wdrożeniu | Agregaty zachowanego archiwum; brak pomiaru p95 bez wymaganej próby |
| Wdrożenie pakietu | `745bad6`, preflight/deploy/post PASS, 210 testów, backup/import, integrity/FK OK, końcowy HTTP 200 | Raporty hj85i7/KDxDT8/styOQb; szczegóły w traceability |
| Zapis PM2 | Operator później potwierdził `pm2 save` po przeładowaniu web przy odbiorze Cybernera | Nie zastępuje świeżego heartbeat kolektora |

## Kod ukończony, scenariusze sprawdzone deterministycznie

- Nowa wizyta/skan po pobraniu może wywołać odświeżenie pełnych regionalnych POI
  najwcześniej po 1 h. Sam czas/restart/halo nie odświeża regionu.
  `test_visit_collect_full_poi_read_and_demand_driven_hourly_refresh` obejmuje
  wizytę → kolektor → dwa przesunięte odczyty → brak kosztu → nowy popyt/refresh.
- Restart, lease/fencing, odwołanie praw, niepełna odpowiedź, digest, zmiana
  profilu/rewizji, empty/MISS, 300/1800 s oraz retencja 7 dni: istniejące zestawy
  world_read, maplark_region, regular_collection, discovery, retention, budget.
- Współbieżność i fallback: procesowe testy regionalnego Overpass oraz metryk;
  nie deklarujemy obciążeniowego p95 produkcji na podstawie tych testów.
- Rollback: niezależne flagi i profile ecosystem; zatrzymanie kolektora nie
  kasuje księgi ani repozytorium. Destrukcyjnych awarii nie wywołujemy na VPS.

## Przypisanie kryteriów odbioru

| Kryteria | Bieżący stan |
| --- | --- |
| A01 | PASS VPS: backup, schemat, integrity/FK, runtime, HTTP 200 |
| A02 | PASS wcześniejsze skany MapLark i rozliczone pobrania |
| A03–A05 | PASS odczytu lokalnego/regionalnego na różnych workerach; dwa konta według sekwencji operatora. Lokalne testy izolacji kont i restartu. Nie dopisujemy nieudokumentowanego restartu do tego samego logu VPS |
| A06–A08 | PASS lokalnych testów pełności, wieku, wersji, praw i budżetów; VPS pokazał rzeczywiste ograniczenie podlimitu tła |
| A09 | PASS wizyt/halo VPS i testów dedup/restart/priorytetu. Naturalny godzinny refresh po ostatnim pakiecie jeszcze nieudokumentowany |
| A10 | PASS produktu geograficznego VPS oraz lokalnego UI/atlasu; bieżący wizualny smoke panelu po końcowym pakiecie do potwierdzenia |
| A11 | Wcześniej operator potwierdził skan/hack/terytoria na nowym i starym koncie. Końcowy pakiet zachowuje ten dowód; nowy smoke skanu po nim do potwierdzenia |
| A12 | Instrukcja i lokalne testy przełączników/rollback gotowe; nie cofano produkcji tylko dla próby |

Mapa C/G/R/D pozostaje w `sprint_163_5_traceability.md`; powyższy stan i
chronologiczne dowody zastępują historyczne kolumny „pozostały odbiór”.

## Jedyna niezakwalifikowana ścieżka dostawcy

Pełny **skaner Geoapify** nie jest ukończony. Działają jego transport, OSM ID
w sprawdzonych odpowiedziach, budżet, kolejka i archiwum commercial, ale nie
kontrakt wszystkich kategorii i pełnych geometrii potrzebnych CHAOS.

Ponownie sprawdzono oficjalną [dokumentację Places API](https://apidocs.geoapify.com/docs/places/)
28.10.2026: odpowiedź to obiekty Point, wyszukiwanie opiera się na kategoriach.
Polygon/MultiPolygon w filtrze wejściowym określa obszar zapytania, nie oznacza
zwracania pełnej geometrii obiektów. To zgadza się z zapisanym wynikiem 63 Point.
Place Details jest osobnym API; nie dowodzi automatycznie kompletności kategorii
ani wykonalności pełnego skanu w przyjętym limicie wywołań i czasie.

| Wymóg CHAOS | Obecny materiał Geoapify | Wniosek |
| --- | --- | --- |
| Tożsamość OSM | 63/63 w próbce commercial | Potwierdzone w tej próbce, walidowane dla każdego obiektu |
| shop / amenity / office / healthcare / atm=yes / surveillance | W próbce shop 63, amenity 3, healthcare 1; pozostałych brak | Nie dowodzi pełności kategorii ani tagów |
| Point/LineString/Polygon/MultiPolygon | Places zwraca Point | Pełna geometria nie jest dostarczona tym endpointem |
| Selekcja przecięcia pełnej geometrii | Filtr obszaru oraz punkty reprezentacyjne | Nie dowodzi selekcji CHAOS geometry-v2 |
| Kompletność regionalna | Koniec jednej strony commercial | Koniec strony nie certyfikuje pełnego profilu CHAOS |

Nie przełączamy `geoapify_contract_unverified`, nie zerujemy rezerwacji i nie
zmieniamy definicji skanu w celu uzyskania zielonego statusu. Warunkiem dalszej
pracy nad pełnym fallbackiem jest źródło pełnych geometrii i dowód pełności
profili albo osobno zaakceptowany inny kontrakt skanowania. Wymóg pozostaje
jawnie otwarty — nie został usunięty ze sprintu.

## Co teraz wymaga VPS

Kod końcowego pakietu jest wdrożony, bieżący `post` odebrany powyżej. Nie
powtarzać deploy/importu, post ani płatnego Paryża. Potwierdzić tylko zwykły
skan oraz panel World Discovery. Zakończony etap odczytał bazę,
PM2 i monitor, a HTTP sprawdza wyłącznie własne `/launch`. Działający kolektor
może równolegle korzystać ze swoich zatwierdzonych limitów.

Przy braku budżetu/popytu poprawnym wynikiem jest odroczenie, nie wymuszony
refresh. Statystyczne SLO i 7 dni obserwacji należą do utrzymania. Pełnego
historycznego zakresu ze skanerem Geoapify nadal nie nazywamy CLOSED.
