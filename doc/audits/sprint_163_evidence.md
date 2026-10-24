# Sprint 163 — pierwszy etap pasywny, 23.10.2026

Status: etap pasywny odebrany na VPS 24.10.2026; dalsza implementacja lokalna,
nie pełny PASS 163.

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

## Odbiór produkcyjnego etapu pasywnego — 24.10.2026

Operator przekazał: 107 testów World PASS (44,138 s), 87 POI PASS (72,296 s),
dry-run i migracja schema 2 z integrity/foreign_keys OK, network_calls 0.
Backup: `/home/johndoe/chaos-backups/162-163-20261024T053532Z`.
Po restarcie skan gry udany; panel potwierdził przygotowany magazyn i OFF/OFF/off.
Po wdrożeniu `8e73857` przez `ecosystem.web.config.js` i `pm2 save`: discovery
passive, ingest/read nadal OFF. Kolejny skan dał jeden sektor i 6 wpisów warstw.
Snapshoty 0, background disabled; budżety widoczne 8/800 oraz 32/24000.
To dowód zapisu zapotrzebowania, nie pobrania sześciu warstw ani local-world hit.

## 163.1 — trwały cykl zadania, lokalnie

`discovery_jobs.py` jest biblioteką bez workera i bez HTTP. Oddzielna tabela
`world_discovery_job` w bazie POI jest inicjalizowana jawnie; istniejący tryb
passive nie tworzy tabeli i nie enqueue'uje zadań. Nie dodano flagi produkcyjnej.

- Enqueue wymaga istniejącego, niewygasłego zapotrzebowania. Klucz zawiera
  demand key, dostawcę, revision i profil; brak generowania sąsiednich sektorów.
- Limit 2000 zadań i 3 przejęć; claim atomowy, losowy token właściciela, lease
  maksymalnie 120 s i nie dłuższy niż TTL zadania. Brak heartbeat rozciągającego
  bez końca operację. Przyszły transport musi zmieścić deadline w lease.
- Wygasły LEASED można przejąć ponownie. FETCHING/VALIDATING po wygaśnięciu
  trafia do POLICY_BLOCKED/outcome_unknown: brak automatycznego HTTP lub refund.
- Identyfikator operacji kosztowej zapisuje się przed FETCHING. Nie ma w nim
  klucza API, konta gracza ani treści zapytania. Sama biblioteka nie rezerwuje
  kredytów: przyszły worker musi użyć istniejącej księgi przed tym przejściem.
- RETRY_AFTER/DEFERRED tylko przed HTTP; brak bezpiecznego wyniku po HTTP
  blokuje zadanie do uzgodnienia. To celowo węższe niż docelowe retry workera.
- Ack wymaga istniejącego kanonicznego snapshotu z query_key równym job id,
  zgodnego dostawcy/revision/profilu i digestu. Crash po publikacji, przed ack
  daje możliwość potwierdzenia tego snapshotu bez ponownego pobrania.
  COMMITTED oznacza zapis obserwacji, nie certyfikację całego obszaru ani
  rozliczenie kredytów. Ledger trzeba uzgodnić osobno.
- Prune usuwa tylko wygasłe zadania terminalne; nie usuwa outcome_unknown.
  Nierozstrzygnięte zadania mogą zapełnić limit i zatrzymać nowe — bez utraty
  dowodu możliwego kosztu i bez wpływu na zwykły skaner graczy.

10 testów cyklu zadania PASS (2,556 s): dedup/capacity, 4 procesy/jeden owner,
restart przed HTTP i fencing, niepewny wynik bez retry/prune, crash po publikacji,
idempotentny ack, obcy snapshot/revision, opóźnienie i limit prób, wygasanie.
Pełny World: 117 PASS (18,835 s). Następnie dodano unikalny indeks identyfikatora
operacji kosztowej, żeby dwa zadania nie wskazywały tego samego naliczenia;
ukierunkowana regresja 11 testów zadań PASS (2,342 s), w tym rollback błędnego
przejścia przy konflikcie. `git diff --check`: PASS. UI nie zmieniano.

Nie jest to jeszcze D01–D04 w całości: brak wspólnego priorytetu live, fairness
regionów, wywołań adapterów i atomowego połączenia z księgą. Nie wolno uruchamiać
tej biblioteki jako produkcyjnego workera ani traktować claim jako zgody na HTTP.
