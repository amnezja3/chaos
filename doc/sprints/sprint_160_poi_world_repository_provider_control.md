# Sprint 160 — POI World Repository i zarządzanie dostawcami

Data: 2026-10-18. Status: realizacja lokalna rozpoczęta; bez wdrożenia i pełnego PASS. Źródło: [koncepcja operatora](../prototypes/poi/sprint_160_poi_world_repository_provider_control.md). Zależności: [158](sprint_158_poi_infrastructure.md), [159](sprint_159_masa_scan_interference_ux.md). Stan odbioru: [macierz 160](../audits/sprint_160_evidence.md), [kontrakt i pierwsze wyniki](../audits/sprint_160_0_contract_baseline.md).

Cel: zapisane, kompletne dane OSM mają obsługiwać kolejne skany lokalnie, również przy niedostępności Overpass. Administrator ma zarządzać zatwierdzonymi endpointami i widzieć ich rzeczywisty stan bez edycji kodu. Korzystamy z infrastruktury 158 oraz prezentacji 159; kontrakt skanera i mechaniki gry pozostają zachowane.

Operator potwierdził wizualny PASS 159. Aktualnie zgłasza brak odpowiedzi używanych endpointów Overpass; przyczyna i zasięg awarii nie są potwierdzone. To uzasadnia priorytet trwałego repozytorium, ale nie dowodzi globalnej awarii usług. Puste repozytorium nie zastąpi niedostępnego źródła: pierwsze zapełnienie wymaga działającego i dopuszczonego dostawcy.

## Granice i zasady

- Przechowujemy wszystkie zwalidowane obiekty pasujące do profilu pobrania, nie tylko 60 markerów. OSM, pochodzenie i pokrycie są wspólne; odkrycia, kamery/NPC proceduralne, ikony, tokeny, koszty i stan graczy pozostają w gameplayu.
- Lokalna odpowiedź wymaga dowodu pokrycia całego żądanego obszaru, zgodnych filtrów, geometrii i aktualności. Brak rekordów nie jest dowodem pustego terenu.
- `out center` nie dowodzi zgodności sąsiednich skanów dla way/relation. Do czasu udowodnienia równoważności obowiązuje exact-query 158. Nie wolno certyfikować samego podzbioru nodes jako pełnego wyniku nwr.
- Jeden wspólny budżet HTTP obejmuje fill, exact fallback, probe i refresh. Nie tworzymy drugiego klienta omijającego lease, circuit, Retry-After lub deadline.
- Awaria lokalnej bazy, błędna konfiguracja, brak zatwierdzonych dostawców, sesja i token nie stają się fabularną blokadą MASA. Stan blocked wymaga dowodu niedostępności kwalifikujących się źródeł dla konkretnego skanu i braku dopuszczonych lokalnych danych.
- 159 pozostaje wizualnie bez zmian: Chaos Log w prawym dolnym rogu, drugi poziom glitcha podczas blokady, ciche usunięcie wpisu i efektu po wygaśnięciu terminu, bez automatycznej próby.
- Publiczne API nie służy do masowego benchmarku. Testy awarii i współbieżności działają na lokalnym transporcie; porównania geometrii na tym samym kontrolowanym snapshotcie OSM.

## Wykorzystanie istniejących modułów

| Miejsce | Rozszerzenie w 160 |
| --- | --- |
| `poiFetchClass.py` | Zachować `get_all`, `_categorize_data`, kolejność, limity, deduplikację i `scan_options`; podłączyć źródło lokalne poniżej kategoryzacji. |
| `poi_infrastructure/service.py` | Zachować ograniczony transport, walidację, anulowanie, deadline i fallback; dodać wybór źródła oraz typ operacji i konfigurację providera. |
| `poi_infrastructure/repository.py` | Ponownie użyć współdzielonych lease i circuit. Obecna tabela `providers` oznacza stan breakerów, nie nowy rejestr konfiguracji. Nie nadpisywać jej inną semantyką. |
| `poi_infrastructure/presentation.py` | Rozszerzyć metadane odczytu world/exact/stale bez globalnego `last_result` i bez zmiany znaczenia stanów 159. |
| `run.py`, GhostLab | Zachować autoryzację, zasięg, token i anulowanie, przetwarzanie niezależnej kopii OSM, snapshot dopiero po sukcesie. |
| Istniejący panel admina | Wykorzystać obecną autoryzację, układ `admin_base`, locale PL/EN i wzorce konfiguracji dostawców narracji; kontrolę CSRF i uprawnienia potwierdzić dla nowych operacji. |
| `tools/poi_cache.py`, fixture i testy 158/159 | Rozszerzyć diagnostykę, testy wieloprocesowe, fixture mapy i dowody, bez drugiego silnika skanowania. |

Wstępny odczyt kodu potwierdza: promień domyślny 300 m, statyczną listę endpointów i limit dwóch bazowych prób, wersję exact-key opartą na `out-center`, granicę deadline 110 s oraz domyślne limity odpowiedzi 4 MiB/20 000 elementów. Produkcja ma według operatora 4 workery i timeout Gunicorn 120 s. To wartości wyjściowe, nie automatyczny budżet szerokiego fetchu.

## Kolejność realizacji

Zachowujemy numerację koncepcji 160.0–160.5. Kolejność zależności: **160.0 → 160.1 oraz 160.3 → 160.2 i 160.4 → 160.5**. Prace nad geometrią i rejestrem można wykonywać niezależnie, ale publiczny wide fetch wymaga gotowego rejestru, zabezpieczonego transportu i zatwierdzonego zakresu. Numer etapu nie oznacza zgody na wcześniejsze uruchomienie ruchu.

### 160.0 — audyt kontraktu i punkt odniesienia

Zakres:

1. Prześledzić wszystkie ścieżki fetchera, realne promienie/opcje GhostLab, kolejność i limit wyników, uprawnienia admina oraz zapis konfiguracji. Potwierdzić wspólną ścieżkę SQLite na VPS i odczytać efektywne limity; nie zakładać ich na podstawie defaults.
2. Utrwalić wynik istniejącej fasady na fixtures: nodes, przecinające koło ways z center poza promieniem, relacje wieloczęściowe i zagnieżdżone, brakujące members, wielkie obiekty, nakładające się kategorie, pusty wynik, granice komórek, wysokie szerokości i antymeridian.
3. Ustalić profil kompletnej geometrii, kanonizację i wersjonowanie query/filter/geometry. Zaplanować niezależny wzorzec parity: lokalny Overpass lub uprzednio utrwalone odpowiedzi referencyjne z dokładnie tego samego kontrolowanego zbioru, a nie oczekiwania wyliczane nowym algorytmem.
4. Zebrać dostępny baseline 158: liczebność skanów, źródła wyników, upstream na skan, czasy, rozmiary odpowiedzi/bazy/WAL. Awarię oznaczyć w pomiarach; nie porównywać jej bezpośrednio z późniejszym zdrowym okresem jako dowodu optymalizacji.
5. Zarejestrować kandydatów i źródła warunków. Informacje o VK Maps z koncepcji traktować jako dowody do ponownej weryfikacji, nie aktualny certyfikat dostępności. Brak odpowiedzi operatora nie daje akceptacji.

Artefakt realizacji: `doc/audits/sprint_160_0_contract_baseline.md`, fixtures i rejestr decyzji liczbowych. Bramka: testowalny kontrakt lokalnej kompletności, wybrany model storage i geometria oraz plan parity. Brak bieżącego upstream nie blokuje lokalnych prac; nie pozwala zamknąć pomiarów produkcyjnych.

### 160.1 — trwałe obiekty, snapshoty i pokrycie

Decyzja pierwszej implementacji: tabele world w istniejącej `data/poi_cache.sqlite3`, aby fencing i publikacja miały jedną transakcję. Pierwotną propozycję osobnego pliku odłożono; pomiar locków/WAL i budżetu rosnącej bazy pozostaje bramką przed produkcyjnym ON. Nie zwiększać limitów dysku bez tego pomiaru.

Zakres:

- Wersjonowane, idempotentne migracje z dry-run, backup/check i kontrolą integralności. WAL, indeksy przestrzenne, krótkie transakcje; HTTP poza transakcją. Brak migracji tabel graczy.
- Model: obiekt `(osm_type, osm_id)`, snapshot, membership i coverage z rdzeniem/halo, profilem, hashami, pochodzeniem, `complete`, `fresh_until`, `usable_until`. Zachować rewizje obiektów albo ich treść w snapshotach, aby późniejszy upsert nie zmieniał odpowiedzi starego pokrycia.
- Atomowo publikować snapshot, jego obiekty i dowód coverage. Niedokończony zapis pozostaje niewidoczny; po utracie lease spóźniony właściciel nie zastępuje nowszej generacji. Przy osobnych bazach jawny protokół generacji/commit i testy awarii na granicach operacji.
- Puste kompletne pobranie zapisuje puste pokrycie. Błąd, obcięty JSON, remark, brak wymaganej geometrii i przekroczenie limitu nie tworzą `complete=true`.
- Konflikty wersji rozstrzygać po wiarygodnym pochodzeniu/czasie OSM; samo późniejsze pobranie starego serwera nie dowodzi nowszej wersji obiektu. Brak obiektu w mniejszym/niepełnym pobraniu nie usuwa go globalnie.
- Shadow ingest wykorzystuje już udane pobrania bez nowego HTTP i bez zmiany wyniku gry. Dotychczasowy `out center` może budować zasób exact/provenance, ale nie certyfikuje sąsiedniego pokrycia.
- Niezależne kopie wyników, limity dysku, snapshotów, komórek i payloadów, sprzątanie partiami. Usunięcie danych wymaganych przez coverage atomowo unieważnia to pokrycie. Nie usuwać aktywnych snapshotów pod odczytem.
- Spójny backup i restore world wraz z coverage; odbudowa indeksów, test disk-full/busy/corruption. Retencja tego zasobu oddzielona od krótkiego cache 158 i od danych kont.

Bramka: restart/restore zachowuje poprawne dane; niekompletny ingest nie daje lokalnego sukcesu; shadow ingest nie dodaje HTTP ani nie zmienia markerów. Awaria opcjonalnego zapisu shadow nie unieważnia poprawnego wyniku pierwotnego skanu.

### 160.2 — certyfikowana geometria i lokalny odczyt

Zakres:

- Wybrać siatkę i halo na podstawie fixtures miejskich/wiejskich. Około 200 m jest kandydatem do pomiaru, nie sztywną decyzją. Halo obejmuje rzeczywisty promień skanera oraz błąd numeryczny. Profil nieobsługujący większego promienia wraca do exact 158.
- Pobierać pełny potrzebny model way/relation, rekonstruować predykat zgodny z `around` i prezentowany center. Nie zastępować selekcji przestrzennej odległością środka ani uproszczonym bbox.
- Wykazać parity na tym samym snapshotcie: zbiór typ/id/tagi/geometria, wyjście fasady, kolejność, limit i deduplikacja. Niezgodność lub nieobsługiwany rodzaj relacji wyłącza lokalne rozstrzygnięcie całego skanu dla tego pokrycia.
- Lokalny odczyt wydaje tylko kompletne zgodne dane fresh albo dopuszczone stale. Sprawdzić aktualność również przy wydaniu wyniku po oczekiwaniu. Nie łączyć dowolnych fragmentów różnych snapshotów w pozornie kompletną odpowiedź.
- Miss przejmuje lease komórki/profilu, ponownie sprawdza zasób i dopiero wtedy używa globalnego slotu 158. Sąsiednie skany należące do tego samego obszaru fill współdzielą pobranie; różne obszary nadal respektują globalny budżet.
- Wide fetch i ewentualny exact fallback dzielą jeden deadline/próby. Przy braku pozostałego budżetu zwrócić dopuszczone stare dane albo sklasyfikowany błąd; nie rozpoczynać nowego pełnego budżetu. Nie trzymać slotu podczas oczekiwania na inny lease.
- Każda faza respektuje `still_active`; ukończony poprawny ingest może służyć innym, lecz anulowanemu skanowi nie wydaje gameplayu. Odświeżenie nieudane ani sam odczyt nie przedłużają świeżości.

Bramka: serię sąsiednich skanów w certyfikowanym rdzeniu obsługujemy z 0 HTTP, także po restarcie i przy wyłączonych źródłach. Nieudowodniona geometria pozostaje na 158; ten fallback jest bezpieczny, ale sam nie zamyka głównego celu 160.

### 160.3 — rejestr dostawców i bezpieczna administracja

Zakres:

- Trwałe provider ID, URL, operator group, priorytet, budżety, konfiguracja z epoch oraz audyt zmian. Osobne `technical_status` i `policy_status`, dowody, data przeglądu, autor i zakres: probe/normal_scan/wide_fetch/background_refresh oraz przechowywanie danych.
- Seed statycznych endpointów jako kandydaci bez automatycznego approved. Przed przełączeniem ruchu jawnie zatwierdzić listę; po przełączeniu registry jest jedynym źródłem konfiguracji. Pusta lista lub błąd registry nie przywraca ukrytego hardcode.
- Udany probe nie aktywuje providera. VK Maps pozostaje `POLICY_PENDING` zgodnie z koncepcją, dopóki nie rozstrzygnięto zakresu użycia. Nie wysyłać korespondencji w imieniu operatora bez jego polecenia.
- Zmiana URL unieważnia test techniczny; zmiana operatora/domeny/warunków/zakresu wymaga odpowiedniej ponownej decyzji. Test i approve związane z wersją konfiguracji; wynik starego testu nie zatwierdza nowszego adresu.
- Propagacja do czterech workerów bez restartu: lekki odczyt epoch przed przyznaniem nowego transportu, lokalny cache pełnej konfiguracji. Disable blokuje nowe wywołania; rozpoczęta próba kończy się w istniejącym deadline. Admin widzi wersję i stan propagacji.
- HTTPS, ścisła ścieżka, brak userinfo/fragmentów/dowolnych nagłówków/QL, zatwierdzone domeny i porty. DNS sprawdzany przy zapisie i połączeniu, IPv4/IPv6 publiczne; połączenie z walidowanym adresem z zachowaniem Host/SNI i TLS. Wyłączyć redirect i proxy środowiskowe. Test samego DNS przed ponownym niezależnym resolve nie chroni przed rebindingiem.
- Istniejące RBAC, CSRF, rate limits i audyt kto/co/kiedy; odrzucić dostęp zwykłego gracza. Formularze PL/EN, komunikaty przy przyciskach, sekcje technika/warunki/zakres/decyzja/dowody.
- Rollback konfiguracji odtwarza wersję z ponowną walidacją; nie przywraca wygasłej zgody ani starych uprawnień do nowego URL.

Bramka: zatwierdzona zmiana URL działa na czterech workerach bez deploya, policy pending nie wysyła ruchu gry, aliasy grupy nie mnożą budżetu, testy SSRF/RBAC/CSRF i audyt PASS. Brak potrzeby dodawania nowego systemu kont lub sekretów.

### 160.4 — zdrowie źródeł i panel operacyjny

Zakres:

- Pasywnie utrwalać wyniki rzeczywistego transportu: źródło i rodzaj operacji, HTTP/DNS/TLS/timeout/schema, czas, liczba prób, bytes, cache/world/stale. Bez kont, tokenów i dokładnej historii pozycji w logach.
- Widok admina odczytuje zapisane metryki, nie pyta Overpass przy otwarciu/odświeżeniu. Oddzielić wynik `/status` od zwalidowanego `/interpreter`, czas ostatniego testu od skanu i obserwację od bieżącej gwarancji.
- Pokazać osobno dostępność upstream i lokalnego repozytorium. `UPSTREAM DOWN` tylko przy dowodach dla dopuszczonych grup; brak grup to błąd konfiguracji, a brak świeżych obserwacji to unknown. Lokalna dostępność nie oznacza pokrycia całej mapy.
- p50/p95 i success rate zawsze z oknem i liczebnością; przy braku próbek brak wartości. Pokrycie jako liczba/powierzchnia certyfikowanych komórek i ich świeżość, nie wymyślony procent świata.
- Jeden skoordynowany job aktywnych probe, domyślnie OFF; kandydat częstotliwości ≥15 min/grupa, nie częściej niż polityka źródła. Niedawny poprawny realny ruch zastępuje probe. Integracja z istniejącym wzorcem worker/CLI, bez nowego schedulera w każdym Gunicornie.
- „Sprawdź teraz” to małe stałe query, uprawnienie, limit i wspólny slot/circuit/Retry-After. Nie zużywa zasobów gracza, nie emituje MASA i nie omija blokady przez panel. Ścisłe probe diagnostyczne kandydata wymagają dopuszczenia do tego zakresu.

Bramka: admin rozpoznaje przyczynę ostatniego błędu i źródło obsługi skanów bez konsoli VPS; 20 odświeżeń panelu daje 0 HTTP do Overpass; równoległe probe nie mnożą wywołań.

### 160.5 — integracja, odbiór i rollout

Zakres:

1. Regresje POI/GhostLab/159, koszty i snapshoty, dwa izolowane konta, cztery procesy/20 żądań, awaria właściciela, utrata lease, restore i brak miejsca.
2. Playwright MCP: admin i mapa, PL/EN, desktop/mobile, formularze/błędy/uprawnienia, świat fresh/stale/brak pokrycia, zachowanie markerów i cichy koniec glitcha. Lokalne konta/fixtures; konsola bez nowych błędów.
3. Runbook `doc/runbooks/poi_world_repository_160.md`: migracja, backup/restore, konfiguracja, dodanie i zmiana providera, monitoring, incident i rollback. Uzupełnić macierz dowodów 160.
4. Wdrożenie z nowymi flagami OFF i zachowaniem efektywnych ustawień 158/159. Brak automatycznej aktywacji nowego źródła lub szerokich pobrań.
5. Kontrolowany shadow ingest, potem odczyt certyfikowanych danych. Wide fetch dopiero po parity, zabezpieczeniach i dopuszczonym zakresie; bez masowego warmupu. Jeśli shadow na `out center` nie tworzy certyfikowanych komórek, odczyt może być włączony, ale nadal trafia do 158; realny odbiór wymaga ograniczonego certyfikowanego fill.
6. Dowody VPS: trwałość po restarcie, odczyt lokalny bez HTTP, konfiguracja widoczna dla 4 workerów, działanie po kontrolowanym odcięciu źródeł dla izolowanego testu, restore i rollback. Nie wyłączać globalnie gry dla testu awarii.
7. Obserwacja naturalnego ruchu z liczebnością i porównywalnym baseline; mierzyć requesty/skan i latency dla pokrytych miejsc. Okno 24–72 h jest punktem startowym obserwacji, nie automatycznym PASS przy kilku próbkach.

Bramka końcowa: zapisany teren działa bez upstream, nieznany teren nie powoduje lawiny prób, metryki potwierdzają ograniczenie HTTP i brak regresji. Lokalny PASS, wdrożenie i produkcyjny PASS zapisujemy osobno. Awaria wszystkich źródeł może opóźnić pierwsze zapełnienie i końcowy odbiór, nie lokalną implementację.

## Flagi i rollback

Nazwy poniżej są planem, nie istniejącą konfiguracją do wklejenia do PM2. Wszystkie nowe przełączniki startowo OFF.

| Proponowany przełącznik | Znaczenie i zależność |
| --- | --- |
| `CHAOS_POI_WORLD_INGEST_ENABLED` | Zapis shadow do world; wymaga infrastruktury 158 i dopuszczalnego przechowywania źródła. |
| `CHAOS_POI_WORLD_REPOSITORY_ENABLED` | Odczyt certyfikowanego world; wymaga 158. |
| `CHAOS_POI_WIDE_FETCH_ENABLED` | Fill obszaru; wymaga ingest, geometrii, aktywnego registry i właściwego scope. |
| `CHAOS_POI_PROVIDER_ADMIN_ENABLED` | Nowy panel administracyjny; nie oznacza przełączenia ruchu. |
| `CHAOS_POI_PROVIDER_REGISTRY_ENABLED` | Registry zastępuje statyczny wybór źródeł; wymaga 158 i gotowej konfiguracji. |
| `CHAOS_POI_PROVIDER_MONITOR_ENABLED` | Aktywne zaplanowane probe; wymaga registry i dopuszczonego scope. Pasywne metryki nie wymagają probe. |

Invalid dependency nie może po cichu omijać bezpieczeństwa. Wyłączenie world/wide zachowuje 158/159 i bazę do diagnostyki. Wyłączenie admin UI nie wyłącza rejestru ani nie przywraca hardcode. Powrót z registry do statycznej konfiguracji jest odrębną świadomą operacją z przeglądem dozwolonych endpointów; rollback nie przywraca sprawności zewnętrznego serwera.

## Parametry do zamknięcia w 160.0–160.2

| Decyzja | Punkt wyjścia | Dowód wymagany przed ON |
| --- | --- | --- |
| Storage world | Osobna SQLite, wspólna koordynacja 158 | Locki, fencing pomiędzy bazami, spójny backup/restore. |
| Geometria i siatka | Pełna geometria; komórka ok. 200 m jako kandydat | Parity nwr, halo dla realnego promienia, bytes/czas w różnych gęstościach. |
| Fresh i usable world | Osobne od 300/1800 s exact-cache | Jawne liczby ustalone po danych i akceptacji oczekiwanej aktualności; bez bezterminowego stale. |
| Budżet fill + fallback | Wspólny deadline ≤110 s, Gunicorn 120 s | Czas na parsing/ingest/gameplay, anulowanie GhostLab, brak podwójnego budżetu. |
| Rozmiar i retencja | Skończone limity world/WAL/snapshotów | Zapas dysku, rozmiar fixtures, sprzątanie zachowujące coverage. |
| Probe | OFF; kandydat ≥15 min/grupa | Zakres dopuszczenia i wspólny limiter, brak duplikacji między procesami. |
| Źródła | Kandydaci, bez automatycznego approve | Aktualne dowody techniczne i warunki dla konkretnego zakresu. |

## Macierz testów i kryteria zamknięcia

| ID | Scenariusz / oczekiwany dowód | Etap |
| --- | --- | --- |
| W01 | Pełny ingest i puste pokrycie; błąd/partial nie tworzy coverage | 160.1 |
| W02 | Snapshoty i rewizje bez przypadkowego kasowania lub mieszania wersji | 160.1 |
| W03 | Parity node/way/relation, center poza kołem, granice i niepełna geometria | 160.0/160.2 |
| W04 | Kolejne sąsiednie skany i restart: 0 HTTP, zgodna fasada | 160.2/160.5 |
| W05 | Cztery procesy/20 żądań, jeden fill obszaru, fencing i awaria właściciela | 160.1/160.2 |
| W06 | Fill + fallback w jednym budżecie, anulowanie i korzyść GhostLab | 160.2 |
| W07 | Izolacja dwóch graczy, kosztów, markerów i snapshotów gameplay | 160.5 |
| W08 | Disk-full/busy/corruption/cleanup oraz backup i restore | 160.1/160.5 |
| P01 | Uprawnienia, CSRF, audit, SSRF/DNS/IPv6/redirect/proxy | 160.3 |
| P02 | Policy pending bez ruchu gry, osobne scopes, zmiana URL/epoch | 160.3 |
| P03 | Propagacja/disable/rollback na 4 workerach, bez resetu cooldown aliasami | 160.3/160.5 |
| H01 | Panel odświeżany bez HTTP, probe skoordynowane, status ≠ interpreter | 160.4 |
| H02 | Upstream down z działającym world; unknown i config error bez fałszywej MASA | 160.4/160.5 |
| U01 | Playwright PL/EN desktop/mobile, zwykły/GhostLab i panel admina | 160.5 |
| O01 | VPS: deploy, lokalny odczyt, restart/restore, metryki i rollback | 160.5 |

Pełny PASS wymaga wszystkich odpowiednich dowodów, nie samego bezpiecznego fallbacku. Zatwierdzenie VK Maps nie jest warunkiem zamknięcia sprintu, jeśli pozostaje wyłączony i mamy inne dopuszczone źródło; warunki muszą być rozstrzygnięte przed jego własną aktywacją.

## Udział operatora i zakres poza sprintem

Do planowania nie potrzeba dodatkowej decyzji. Przed produkcyjnym ON potrzebne będą: wybór i zatwierdzenie dostawców/scopes na podstawie dowodów, uzgodnienie parametrów aktualności i miejsca na rosnącą bazę, dostępne odczyty VPS oraz zgoda na wdrożenie. Przy braku dostępu do VPS podamy krótkie komendy diagnostyczne bez sekretów. Nie traktujemy tego planu jako zgody na push, zmianę PM2 lub kontakt z dostawcą.

Poza 160: pełny import planety, własny publiczny Overpass, PostGIS bez pomiarowej potrzeby, masowy preload, globalny robot refresh i webhooki alertów. Nie przebudowujemy Identity Gateway, zasad wieku, ekonomii ani mapowych logów zaakceptowanych w 159.
