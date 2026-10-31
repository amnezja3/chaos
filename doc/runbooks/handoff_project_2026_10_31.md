# CHAOS — pełny prompt przekazania do nowego wątku, 31.10.2026

Status: **AKTUALNY PUNKT WEJŚCIA**. Cały dokument jest promptem startowym dla
agenta kontynuującego projekt. Zawiera instrukcje, mapę systemu i stan wiedzy.

Baza przeglądu: lokalny `HEAD 77d5c8f`, czyste drzewo przed tym przekazaniem.
Źródła: kod i dokumentacja repozytorium oraz odbiory przekazane przez operatora
w poprzednim wątku. Nie wykonano teraz audytu VPS, nowych wywołań dostawców
ani ponownego pełnego E2E. Stan produkcji poniżej to **ostatni potwierdzony stan**,
nie gwarancja bieżącego uptime, salda czy wartości env. Dokument nie zawiera sekretów.

Zastępuje instrukcje startowe i priorytety
[przekazania z 14 IX](handoff_project_2026_09_14.md) oraz
[przekazania 139–140](handoff_sprints_139_140.md). Zachowuje ich przydatną historię.
Nie uruchamiaj zapisanych tam dawnych triggerów ani nie zaczynaj ponownie 139.

## 1. Twoja rola i pierwszy krok

Jesteś współpracownikiem rozwijającym działającą grę CHAOS. Komunikuj się po
polsku, konkretnie: co ustaliłeś, co zmieniłeś, jak sprawdziłeś, co rzeczywiście
wymaga operatora. Kontynuuj zatwierdzony zakres aż do gotowego pakietu. Nie kończ
na propozycji pracy, którą możesz wykonać. Nie pytaj ponownie o już podjęte decyzje.

Na początku nowego wątku:

1. Przeczytaj ten dokument i lokalne instrukcje `AGENTS.md`/środowiska.
2. Sprawdź `git status --short`, `git log -12 --oneline`, aktualny katalog i shell.
   Nie nadpisuj cudzych zmian. Commit tego przekazania będzie późniejszy niż baza powyżej.
3. Przeczytaj [wiążący kontrakt profilu](../architecture/profile_hot_path_contract_130_11_plus.md).
4. Dla następnego zadania otwórz aktualny sprint, audit/evidence i runbook,
   odszukaj implementację oraz testy. Nie buduj drugiego systemu obok istniejącego.
5. Jeśli operator zleci kontynuację Camera Visual Network, zacznij od **164.0**:
   lokalnego prototypu jednej kamery. W tej rozmowie zmieniono plany, nie wykonano
   prototypu ani nie uzyskano akceptacji wyglądu. Pełna infrastruktura czeka na tę akceptację.
6. Samo przekazanie nie zleca restartu VPS, migracji, płatnego testu ani aktywacji
   dostawcy. Kontynuuj aktualną dyspozycję operatora, respektując istniejące zgody i limity.

## 2. Czym jest CHAOS

**Cyber Hacking Adventure Of Senses** — przeglądarkowa gra hackerska na mapie
rzeczywistego świata, z pulpitem Ghost System, narzędziami tworzonymi przez
graczy, trwałymi operacjami, ekonomią informacji, klanami i walką o terytoria.
„Hakuj cyfrowe zmysły współczesnego świata”: kamery, mikrofony, sieci, urządzenia.

```text
obiekt/aktor mapy → akcja → kompatybilna aplikacja → operacja
→ ryzyko/ruch/konsekwencja → zasób → plik → Ghost Exchange → rozliczenie HC
→ nowe narzędzia → dalsza eksploracja i konflikty
```

Mapa i Ghost System to jeden produkt. Aplikacja jest narzędziem, a nie źródłem
prawdy wyniku. Operacja żyje niezależnie od okna. Zasób, plik, saldo i nagroda
muszą pochodzić z kanonicznego zapisu/receipt, nie tylko z animacji.
Rozróżniaj `source_type`, `target_type`, `target_mode`, `map_action_id`,
`operation_type` i `resource_types`; nie mapuj ich po podobieństwie nazw.

Kanon: Ghost System pochodzi z 2108; MASA jest elementem świata i konfliktu
o kontrolę nad informacją. Klany: `virex`, `echo_freedom`, `phantom_mesh`,
`sentinel_order`. GhostNetwork ma cztery maszyny i 20 części/profesji.
Relacje i moce definiuje `ghostnetwork/catalog.py`, nie kolejność obrazków w UI.
GhostSignal wynika z rzeczywistych decyzji graczy; LLM nie ustala nagród,
uprawnień, wyników strategicznych ani faktów świata.

Podstawy: [ABOUT](../overview/ABOUT_CHAOS.md),
[pętla gry](../gameplay/gameplay_loop.md), [terminy](../gameplay/gameplay_terms.md),
[operacje](../gameplay/operations.md), [aplikacje](../gameplay/app_contract.md),
[pliki](../gameplay/file_model.md), [ekonomia](../gameplay/data_economy.md),
[ruch](../gameplay/movement_model.md), [ryzyko](../gameplay/risk_events.md),
[mapa](../gameplay/map_interactions.md). Wczesny opis produktu nie jest dowodem wdrożenia funkcji.

## 3. Stan sprintów i odbiorów

Nie istnieje jeden niezawodny, zawsze aktualny status całego repo. Nagłówki
starych sprintów i `doc/README.md` bywają starsze od późniejszych odbiorów.
Poniższe zestawienie rozdziela dowody zamiast ogłaszać wszystkie sprinty zamkniętymi.

| Zakres | Stan do przeniesienia |
| --- | --- |
| 130.x–138 | Fundamenty integralności, lekkich odczytów, GN i narracji. Historyczne kontrakty nadal obowiązują; nie wracać do ciężkich ścieżek. |
| 139–140 | GhostSignal/show i stylizacja zrealizowane, historyczne odbiory autora. Nie wznawiać starej instrukcji triggera. Nie oznacza to nowego E2E produkcji z października. |
| 141 | Hakowanie graczy i Control Loop istnieją. Nagłówek planu ma historyczne otwarte 141.5; przed wznowieniem zestawić późniejsze zmiany i odbiory, nie diagnozować od zera. |
| 142–143 | Response Network, incydenty, konsekwencje, więzienia. 143 zamknięty decyzją autora; nie wszystkie kombinacje ręczne mają osobny dowód. |
| 144–146.5 | GhostLab 1.0: rejestr, publikacja, runtime, narzędzia PvP, bilety, konserwacja, firmware, skanery. 146.5 PASS 1 X; szczegółowe luki wcześniejszych etapów pozostają w runbookach. |
| 147–148 | Kreatory i aktualizacje działają; README odnotowuje akceptację 148 z 4 X. Nagłówki planów są starsze — nie przywracać dawnych modeli mocy ani migracji. |
| 149–152 | **ZAMROŻONE DO ODWOŁANIA**, GhostLab v2. Bez jawnego wznowienia nie implementować. |
| 153–154 | Fundament i aplikacje PL/EN mają zapisane odbiory. Tłumaczenia UGC nie są automatyczne. |
| 154.8 | Adaptery narracji Mistral/Ollama i panel mają LOCAL PASS; dokumenty nie potwierdzają pełnego live odbioru Mistrala. Zweryfikować evidence przed zmianą dostawcy. |
| 155 / 155.3 | Treści i BlackNet languages: brak pełnego PASS według planów. To jawny backlog, nie bieżący priorytet zamiast 164. |
| 156 | Trwałe sesje/cichy start/PWA odebrane w opisanym zakresie. Linux/iOS i zgodność części urządzeń wymagają sprawdzenia najnowszej macierzy, nie deklaracji pełnego wsparcia. |
| 156.8 / 157 | Publiczne Google login PASS 18 X; Identity Gateway istnieje. Nie przenosić tego PASS automatycznie na wszystkie konfiguracje Discord/Steam/GitHub i wszystkie scenariusze kont. |
| 157.8 | Polityka wieku/communication safety: lokalna implementacja, aktywacja produkcyjna niezatwierdzona według dokumentu. Nie przełączać flag przy okazji innej zmiany. |
| 158–160 | Fundament POI i skaner. 159 ma wizualny PASS. Historyczne blokady Overpass i brak repo z 160 rozpatrywać przez domknięcie 163.5. |
| 161–163 + 163.5 | **Zaakceptowany PASS aktualnego mechanizmu**, z pełnym skanerem Geoapify do dokończenia. MapLark, exact/regional repo, kolektor, geografia, panel i monitoring odebrane. |
| Cyberner, poprawki po 163.5 | Nazwy zewnętrznych kont, wyszukiwanie, wybór rozmowy i zaproszenia: użytkownik potwierdził PASS. |
| 164–165 | **PLAN**, ostatnia aktualizacja 30 X, commit `77d5c8f`. Camera Visual Network; następny właściwy etap 164.0. |
| 166 | Nie tworzyć sprintu fotografii graczy; zakres wyłączony przez operatora. |

Główne bieżące dokumenty:

- [163.5 — sprint](../sprints/sprint_163_5_world_repository_completion.md),
  [bilans odbioru](../audits/world_closeout_163_5.md),
  [traceability](../audits/sprint_163_5_traceability.md),
  [ostatni runbook](world_completion_final_163_5.md).
- [164 — prototyp/kontrakt/archiwum](../sprints/sprint_164_camera_visual_archive.md),
  [165 — integracja/UI/rollout](../sprints/sprint_165_camera_visual_network_rollout.md).
- [154.8](../sprints/sprint_154_8_narrative_providers_mistral.md),
  [155](../sprints/sprint_155_ghost_system_content_acceptance.md),
  [156 odbiór](../audits/sprint_156_acceptance.md),
  [157.8](../sprints/sprint_157_8_age_policy_16_communication_safety.md).

## 4. Struktura repozytorium i zależności

| Miejsce | Rola |
| --- | --- |
| `run.py` | Duży monolit Flask: routes, integracja gameplayu, launchery, map actions, części runtime. Szukaj symboli i callerów, nie czytaj całości przy każdej zmianie. |
| `database.py` | SQLite, kanoniczne store'y, projekcje, receipts, ledger, wersje. Najpierw szukaj istniejącego store'u. |
| `profileManagment.py` | Legacy profil i guarded mutations/recovery. Nazwa jest rzeczywiście tak zapisana. |
| `config.py`, `config/`, `ecosystem.*.js` | Konfiguracja i profile uruchomienia; plik env nie dowodzi efektywnego env procesu. |
| `territory_geometry.py`, territory stores, `ghostnetwork/territory*` | Geometria/ownership/konflikty i projekcje mapy; worker ma inne zadania niż renderer. |
| `ghostnetwork/` | Katalog, moce, cykle, sygnały, show, nagrody, narracja, publikacja, widoczność i delty. |
| `response_network/` | Incydenty, ryzyko, konsekwencje i kontrakty kamer. Istniejący gameplay kamery ma pozostać autorytetem CVN. |
| `creator_*.py` | Receptury, kontrakty, projekty, publikacja, płatności, legacy i aktualizacje zwykłych kreatorów. |
| `ghostlab_*.py` | Osobny istniejący system IDE/szablonów, kompilacji i narzędzi; nie utożsamiać go z każdym kreatorem Ghost System. |
| `identity_gateway/`, `persistent_session*.py`, `launch_controller.py`, `session_generation_store.py` | Tożsamość, logowanie, sesje, cichy start i ochrona generacji. |
| `cyberner_history.py`, `cyberner_presentation.py`, `communication_safety*.py` | Historia/prezentacja komunikacji i kontrola dostępu. |
| `poiFetchClass.py`, `poi_infrastructure/` | Skaner, adaptery, router, world repository, popyt, kolektor, budżety i monitoring. |
| `admin_panel.py` | Panel operatora; wąskie odczyty, sekcje na żądanie, nie lista pełnych profili. |
| `static/js/terminal.js` | Pulpit, aplikacje, operacje, okna i ich integracja. Duży plik, celowane zmiany. |
| `templates/map_template.html` | Mapa Leaflet, markery, menu i część logiki renderowania. Błąd mapy może nie leżeć w `static/js`. |
| `static/js/session_generation.js`, `launch_controller.js`, `player_directory.js` | Izolacja klienta, bootstrap i wyszukiwanie graczy. |
| `static/locales/pl`, `static/locales/en`, `ghost_i18n.py` | Katalogi/kontrakt i18n; nie tłumaczyć kluczy runtime. |
| `scripts/`, `tools/` | Workery oraz operatorskie CLI, migracje, diagnozy, fixtures, pakiety odbioru. Nie każdy skrypt jest read-only. |
| `tests/`, `tests/js/`, `tests/browser/`, `tests/fixtures/` | Testy domenowe, JS, przeglądarkowe i kontrolowane próbki. |
| `data/`, `instance/`, `flask_session/`, `logs/` | Dane runtime i prywatne artefakty; nie traktować jako materiał do przypadkowego `git add .`. |
| `doc/`, `artifacts/`, `.playwright-mcp/` | Dokumentacja i artefakty weryfikacji; do commita tylko celowo dobrane, bez sekretów/danych graczy. |

SQLite jest źródłem stanu runtime. `static/*.json` to często seed/katalog,
nie aktualna baza; import do `JsonResourceStore` / `json_resources` jest jawny.
Czytaj [resource architecture](../architecture/resource_architecture.md).
Główna baza to zwykle `data/game.sqlite3`, POI/world to `data/poi_cache.sqlite3`;
zawsze sprawdź konfigurację konkretnego procesu przed operacją.

## 5. Ciężki profil i wymagane lekkie ścieżki

Najważniejszy kontrakt techniczny: **brak pełnego profilu w zwykłym hot path**.
Historyczny `main` miał około 34,6 MB. Skanowanie/parsowanie takiego dokumentu
przy małej operacji powodowało poważne regresje gry.

Nie używaj `sync_session_profile()`, `UserProfileManager`, `list_profiles()`,
`UserStore.get_profile()` / `get_profile_with_revision()` do pobrania nicka,
salda, celu, klanu, operacji, inventory czy widoczności. Nie wkładaj profilu
do sesji, delt, outboxu, cache, logów ani zadania LLM. Zakaz obejmuje fallback
i recovery zwykłych requestów, eventy, publishery i workery.

`get_profile()` po dawnym uproszczeniu wciąż parsuje cały JSON. Nazwy
`readonly`, `projection` albo pojedynczy `json_extract` nie gwarantują małego kosztu.
Nie wykonuj JSON projection wszystkich kont w każdym requestcie.

| Dane | Właściwe istniejące wejście |
| --- | --- |
| Tożsamość, klan, profesja, boot | `UserIdentityProjectionStore`, m.in. `get_desktop_boot`; zachować integrity gate |
| Możliwości | `UserCapabilityProjectionStore.get_capabilities` |
| Cel i postęp | `PlayerTargetRuntimeStore`, `PlayerMarkedTargetStore` |
| Pozycja i skan | `PlayerPositionStore`, `PlayerScanSnapshotStore` |
| Operacje | `PlayerOperationStore` |
| Aplikacje, pliki, dysk | `PlayerInventoryStore` i kanoniczne rekordy inventory |
| Pieniądze | `WalletBalanceStore`, `WalletLedgerStore` i istniejąca transakcja |
| Terytoria | `TerritoryStore`, `TerritoryConflictStore`, ownership/engagement/progression receipts |
| GN, show, ranking | Ograniczone projekcje tabel GhostNetwork z audience |
| Fan-out wiadomości | Indeks odbiorców/klanu i bounded sparse reads, bez profilu każdego gracza |

Jeśli nie ma lekkiej projekcji, najpierw dodaj ją i migrację. Nie implementuj
„tymczasowo” przez full profile. Sparse wynik nie jest całym profilem:
nie zastępuj nim `session['profile']` ani dokumentu użytkownika.

Wyjątki: jawna naprawa/forensics jednego konta, verify/checksum/LKG albo rzeczywista
mutacja pól nadal należących do profilu. Nazwany call site, ograniczony zakres,
testy. Zachować revision/checksum/CAS, LKG i session precommit guard.
Ciężkie przygotowanie/serializacja/walidacja przed `BEGIN IMMEDIATE`;
pod blokadą wyłącznie recheck, CAS, atomowe zapisy i commit.

Bramka regresji: małe konto oraz syntetyczny profil ≥35 MB, bounded query count,
`profile_full_read=0`, `profile_full_write=0`, `profile_bytes=0` dla zwykłych
lekkich ścieżek. Mierz latency, wait i hold writer locka. Wyjątki mają osobny
pomiar. Nie naprawiaj tego przez timeout, animację lub cache pełnego profilu.

[Mapa hot paths z IX](handoff_hotpaths_2026_09_14.md) jest listą miejsc do audytu,
nie dowodem aktualnego buga w każdym z nich. Sprawdź cały call chain, branch,
wstrzyknięty callback i fallback. `bounceback` to historyczny skrót, nie moduł
do odtworzenia. `gonnaWinRequestQueue`, `operation_only`, capture, partial merge
i sesja mają odrębne kontrakty — nie scalaj ich w ogólną hydratację profilu.

## 6. Backend, frontend i integralność gameplayu

- Stan kanoniczny, receipt i scope version zapisuje backend. Delta tylko
  informuje o zmianie; localStorage/DOM/manifest nie rozliczają nagród i HC.
- Retry, reload i restart muszą być idempotentne między procesami. Słownik
  Pythona lub Promise w JS nie zastępuje trwałego dedupe/receipt.
- SQLite: bez HTTP, inferencji, dekodowania zdjęć, pełnego profilu lub globalnego
  reconcile pod writer lockiem. Brak schema init/backfill na każdy request/job.
- Public/clan/owner filtruje serwer przed serializacją, nie CSS.
- Snapshot/delta/recovery: wersje monotoniczne, izolacja generacji sesji i epoki
  dokumentu, odrzucanie starych odpowiedzi, ograniczony recovery, merge scope.
- Nie kasować postępu celu przy zmianie zaznaczenia. Marker ID, target binding,
  współrzędne i menu muszą odnosić się do tego samego obiektu po dużym skanie.
- Mapa: nie rebuildować całości przy małej delcie; zachować focus motocykla,
  canvas/bounds guards i kanoniczne klastry. Konflikt workera ≠ widoczny polygon.
- Terytorium `main` znikało po przejęciach przez filtr rozpiętości poligonu;
  poprawka renderowania została potwierdzona. Szukaj `isSaneTerritoryPolygon`
  i historii zmiany, nie resetuj terytorium/bazy jako pierwszej „naprawy”.
- Ruch awatara nie cofa istniejącego terytorium. Testy konfliktów prowadzić
  izolowanymi kontami, żeby duży `robot`/`main` nie pochłonął małych testowych pól.
- Nowy frontend: PL/EN, responsive, reduced motion, focus, brak zdublowanych
  okien/timerów, zgodny styl CHAOS. Czytelne grupy/collapsy, kompaktowe kontrolki,
  komunikaty przy akcji; admin nie ma prezentować surowych JSON jako głównego UX.
- Sesje/PWA: nie cache'ować prywatnego HTML/API ani danych innego konta w SW;
  wznowienie, wylogowanie i nowa generacja muszą odcinać stary kontekst.

Kontrakty: [wersje](../architecture/state_version_contract.md),
[delty](../architecture/delta_event_schema.md),
[synchronizacja](../architecture/runtime_synchronization_audit.md),
[sesje](../architecture/session_generation_endpoint_inventory.md),
[i18n](../architecture/ghost_i18n_v1.md).

## 7. Workery, Ollama i publikacja

| Proces PM2 / konfiguracja | Zadanie |
| --- | --- |
| `chaos` / `ecosystem.web.config.js` | Gunicorn `run:app`, konfiguracja wskazuje 4 workery, bind `127.0.0.1:6666` |
| `chaos-territory-worker` / `ecosystem.territory-worker.config.js` | `scripts/territory_conflict_worker.py`, runtime konfliktów/terytoriów i powiązanych procesów |
| `chaos-ollama-worker` / `ecosystem.ollama-worker.config.js` | `scripts/ollama_narrative_worker.py`, pobranie zadania i generacja kandydata narracji |
| `chaos-narrative-publisher` / `ecosystem.narrative-publisher.config.js` | `scripts/narrative_publication_worker.py`, walidacja/publikacja zgodnie z lifecycle |
| `chaos-world-discovery-worker` / `ecosystem.discovery.config.js` | `tools/world_discovery_worker.py`, regularne zbieranie świata w zatwierdzonej polityce |
| `chaos-world-monitor` / ten sam ecosystem | `tools/world_collection_monitor.py --serve`, obserwacja kolektora/budżetów |

Ollama jako usługa modelu i worker Pythona to różne procesy. Pipeline:
zdarzenie domeny → producer/outbox → bounded task → model → kandydat → walidacja
→ publikacja do właściwego kanału/audience. `ghostnetwork/llm/` zawiera wspólne
adaptery `provider.py`, `ollama_provider.py`, `mistral_provider.py`, store i admin.
Model nie ma prawa wymyślać faktów ani zmieniać mechaniki. Nie wracać do legacy
file queue, nie wywoływać inferencji w requestach web lub writer locku.

Przy problemie „nie publikuje”: sprawdź producer, zadanie, lease/attempt,
kandydata, reject reason, publikację, kanał/locale/audience i env obu workerów.
Samo `online` lub tekst wygenerowany przez model nie dowodzi publikacji.
Nie twórz nowego zadania/efektu tylko po to, by ukryć błąd istniejącego.

Runbooki: [cutover narracji](narrative_cutover_135_6.md),
[Mistral/Ollama 154.8](narrative_providers_154_8.md),
[wspólny kontrakt semantyczny](../architecture/shared_llm_semantic_input_contract.md).
Historyczne ograniczenie `ollama.service CPUQuota=300%` zastosowano runtime;
[artefakt](../hardbugfix/ollama_cpu_quota_2026-10-05.md) nie potwierdza trwałości
po restarcie hosta. Nie uznawaj PM2 save za utrwalenie ustawienia systemd.

## 8. World Discovery, skaner i granice PASS 163.5

**Nie otwierać ponownie zamkniętego odbioru.** Operator zaakceptował aktualny
stan z Geoapify do dokończenia. Ostatni `post` z 28 X: integrity/FK OK,
web/kolektor online, heartbeat aktualny, HTTP 200, `PASS: post`; raport
`/home/johndoe/chaos-world-completion-gCwuSf`. Było 265 snapshotów — liczba
historyczna, nie dowód kompletnego pokrycia planety.

Mechanizm: skan/wizyta → popyt sektorów i halo → kolektor → adapter → walidacja
→ snapshot/retencja → zgodny lokalny odczyt → fallback do dopuszczonego API,
z osobnymi kolejnościami skanera i tła. Nie pobieramy całej planety.
Geometrie Point/LineString/Polygon/MultiPolygon; warstwy POI, roads, waterways,
inland_water, coastline, land_water. Używanie geografii w nowych mechanikach gry
jest przyszłym zakresem; obecnie budujemy i utrzymujemy jej zbieranie/odczyt.

- MapLark skanuje produkcyjnie. Skany ze starego i nowego konta, hakowanie
  i tworzenie terytorium potwierdzono. Repozytorium obsługuje exact i regionalny
  odczyt; regionalny PASS obejmuje dwa przesunięte skany i różne workery.
- `poi_maplark_cache source=world` może oznaczać exact reader.
  `poi_maplark_region source=world` jest właściwym dowodem regionalnej ścieżki.
- Exact key zależy od parametrów; zmiana pozycji może zmienić klucz.
  Regionalny skan wymaga pełnego, zgodnego i świeżego bbox obejmującego koło.
  Teleport w nieznany sektor nie powinien dać wymuszonego world hit.
- Profil regionalny: `chaos-maplark-region-geometry-v2`. Nie przywracać v1.
  Historyczny Paryż wymagał mniejszego bbox po truncation 1000 obiektów.
  Nie powtarzać płatnych prób tylko po to, by ponownie wykazać zaakceptowany PASS.
- `UNKNOWN` to obserwacje, nie kompletność do skanera. `complete` odpowiedzi
  dostawcy nie jest automatycznie dowodem poprawnej selekcji/geometrii regionu.
  Nie publikować uciętej odpowiedzi jako pełnej ani nie łączyć dowolnych wersji
  snapshotów w rzekomo certyfikowane pokrycie.
- Fresh skanera 300 s, stale do 1800 s; archiwum geometrii 7 dni. Odczyt nie
  odmładza źródła. Regionalny POI refresh: minimum 1 h i nowy bezpośredni popyt
  po sukcesie; sam czas/restart/halo nie wymusza pobrania.
- Natural Earth 5.1.1: przypięty lokalny produkt ląd–morze, skala 1:10 mln,
  odebrany import. Nie zastępuje dokładnego coastline OSM ani danych skanera.
- Overpass VK potrafił przejść probe, ale pełny skan timeoutował; fallback
  zajmował około 29 s. Operator ustawił MapLark jako primary. Nie przywracać
  automatycznie VK na początek. Gdy działa stabilnie i ma właściwe zgody,
  może być preferowanym bezkredytowym źródłem; brak kredytów ≠ brak ograniczeń.
- Geoapify działa jako ograniczony kolektor obserwacji commercial, **nie jako
  pełny zgodny skaner CHAOS**. Otwarte kategorie, selekcja przestrzenna, pełna
  geometria i kwalifikacja fallbacku. Nie przedstawiać go jako gotowego zamiennika.

Limity zaakceptowane (sprawdzać bieżącą politykę, nie resetować księgi):

| Źródło | Limit konta w CHAOS | Dodatkowe ograniczenia |
| --- | --- | --- |
| MapLark Free | 800 kredytów/dzień, 24 000/31 dni | Tło 200/dzień; typowa rezerwacja 20, koszt ustala dostawca |
| Geoapify Free | 2700/dzień, 83 700/31 dni | Plan dostawcy zgłoszony jako 3000/dzień; tło 200/dzień |
| Overpass VK | 120 prób/dzień, 3720/31 dni | To próby zapytań, nie kredyty; circuit/backoff/zgody |

Kolektor: maksymalnie jedna próba sieciowa/cykl, odstęp 60 s, priorytet gracza.
Podlimit tła i limit konta są odrębne. Pozostałe 12 przy rezerwacji 20 daje
poprawne DEFERRED mimo pieniędzy dla skanera. Brak ostrzeżeń nie jest certyfikacją.
Pięć dawnych uncertain Geoapify / 25 kredytów pozostawiono zarezerwowane;
agregat panelu dostawcy nie rozlicza jednoznacznie pojedynczych operacji.
Księga wewnętrzna nie jest saldem dostawcy ani twardym limitem ceny requestu.

Ostatnio odebrane profile PM2: web `world_maplark_region`, kolektor `regular_halo`.
Global ingest/read, regional read, visits, routing/halo aktywne w odebranym
zakresie. Bazowy `env` w ecosystemie nadal może mieć OFF — **nie robić reload
bez właściwego `--env`**. Zgody, rewizje i routing są również w bazie/polityce,
nie tylko w env. Nie mylić `probe_allowed`, cooldownu i uprawnienia do skanu.

## 9. Identity Gateway i ostatni PASS Cybernera

Zewnętrzne konta mogą mieć wewnętrzny username `id_...` i osobny publiczny nick.
Nie zmieniaj kluczy tożsamości po to, by poprawić etykietę. Wyszukiwanie i wybór
muszą rozstrzygać do kanonicznego konta, prezentując publiczną nazwę; nick może
nie być unikalny. Identyfikator pokazywany na mapie i używany w Cybernerze ma
prowadzić do tej samej osoby, niezależnie od Google/Discord/Steam/GitHub/local.

Ostatnio poprawiono: publiczne nazwy wiadomości, directory, wybór rozmowy,
widoczność zaproszeń/relacji, styl karty wyniku CHAOS i feedback. Powtarzany
komunikat zastępuje poprzedni i znika po 3 s, nie powiększa listy. Kliknięcie
wyboru nie może po cichu tylko wysyłać kolejnych zaproszeń bez otwarcia rozmowy.
Zachować wymaganie akceptacji relacji i istniejące zasady bezpieczeństwa.

Kod: `static/js/player_directory.js`, `static/js/terminal.js`,
`cyberner_presentation.py`, identity projection, routes w `run.py`.
Testy: `test_player_directory.py`, `test_communication_safety_web.py`,
`test_cyberner_public_names.py`, `test_identity_projection.py`,
`tests/browser/player_directory*.js`. Historyczny VPS PASS: 6+8+2+4 testy,
reload i `pm2 save`; później użytkownik potwierdził działanie Cybernera.
DeprecationWarning Flask-Session to dług techniczny, nie test failure.

## 10. Następny zaakceptowany kierunek: Camera Visual Network 164–165

**Jeszcze plan, nie gotowy moduł.** Najpierw 164.0: jedna kamera, lokalne
materiały o znanych prawach, 1–3 ujęcia, istniejąca akcja i okno, charakter
terminala CHAOS, stany, atrybucja, PL/EN/mobile/reduced motion. Autor musi
zaakceptować wygląd przed rozbudową kolejki/archiwum/admina. Akceptacja sprintu
nie jest akceptacją prototypu.

164: kontrakt, Mapillary, dobór kierunku zdjęć, miniatury zamiast oryginałów,
optymalizacja, jedno archiwum, deduplikacja, trwała kolejka, manifest, wycofanie
ze wszystkich współdzielonych archiwów, blokada ponownej publikacji i restore.
Zamknięcie okna nie anuluje już przyjętego zadania. Brak zdjęć nie unieważnia
poprawnej operacji gameplayowej. Zdjęcie okolicy jest archiwalne, nie live feed.

165: istniejący podgląd, API/autoryzacja, stany awaryjne, admin, logo Mapillary,
osobny panel licencji, publiczne źródła, kontrolowana nawigacja, realna PWA,
zbiorczy pilot/rollback. Fotografii nie utożsamiać z nagrodą `camera_dump`.

Nowe powiązanie Ghost System z 30 X:

```text
generator → aplikacja zgodna z camera_stream → istniejąca operacja kamery
→ autoryzowany manifest/zadanie CVN → istniejące okno podglądu
```

`creator_policy.py` ma recepturę `camera_stream`; routing opiera się na
`map_actions`, nie `interface`. Robocze `camera_visual_preview` to planowana
serwerowa zdolność prezentacji, **nie istniejące już pole wymagające włączenia**.
Nie nadawać jej po nazwie programu ani samym `camera_shutdown`.
Nowe i zgodne starsze aplikacje mają otrzymać ją automatycznie, bez regenerowania
i osobnych baz fotografii. Preferowana projekcja runtime; nie łamać zamrożonego
`creator_contract` ani walidacji `creator_updates.py` / `creator_legacy.py`.
`response_network/camera_contract.py`, `camera_exposure.py`, istniejące operacje,
`terminal.js` i `tests/js/test_camera_window_dedupe.js` to punkty integracji.

Wykluczone: CAMERA CREATOR w Ghost Lab, kamery instalowane przez graczy,
upload/aparat/GPS, Vision, zamazywanie twarzy/tablic, moderacja i PLAYER_UPLOAD.
Nie robić infrastruktury „na przyszłość”, nie tworzyć 166.

Licencje według przekazanego przez operatora podsumowania odpowiedzi Mapillary
z 26 X (nie niezależna weryfikacja korespondencji): pojedyncze pobrania i własne
serwowanie przewidziane w warunkach, transformacje zasadniczo dopuszczalne,
standardowe materiały CC BY-SA 4.0 z atrybucją. Nie oznacza to wieczystej retencji.
L01 częściowo rozstrzygnięta: pozostają warunki retencji/wycofań/backupów
i docelowego użycia. L02 otwarta: logo-link rekomendowane, dwustopniowa
nawigacja z ostrzeżeniem nie ma jednoznacznej akceptacji. Nie zmieniać samodzielnie
uzgodnionego UX. Prawa odbiorców CC BY-SA nie mogą być ograniczane gameplayem.
Przed pilotem utrwalić źródła rozstrzygnięcia, a nie zgadywać zgodność.

Główna koncepcja w `doc/prototypes/camera_view/` jest materiałem źródłowym;
ostatnia dyspozycja ograniczyła aktualizację do dwóch sprintów. W przypadku
różnicy bieżące decyzje 164/165 są nadrzędne wobec starej koncepcji.

## 11. Development: LOCAL-FIRST, wdrożenie i odbiór

To stała polityka kolejnych sprintów, nie tylko CVN:

1. Rozpoznaj istniejące kontrakty i źródła prawdy. Zbierz pytania/dane potrzebne
   z serwera w jedną listę. Jeśli konieczne, jedna sesja read-only z anonimowymi
   próbkami, schematami i konfiguracją bez sekretów; bez zbędnych profili graczy.
2. Przygotuj lokalnie kompletny pakiet backendu, UI, migracji, testów i instrukcji.
   Pakiety CVN: A backend/archiwum, B integracja/UI, C pełna weryfikacja lokalna.
3. Testuj proporcjonalnie: domenowe Python/JS, integracja, właściwe regresje,
   hot paths, restart/idempotencja/backup na izolowanej bazie i przeglądarka.
4. Przed VPS raport gotowości: zakres, testy, rozwiązane błędy, brak regresji
   gameplayu, migracje/env, rollback, otwarte kwestie oraz testy rzeczywiście
   wymagające serwera. Nie wysyłaj operatora po każdą drobną zmianę.
5. Commit lokalny z konkretnym opisem i celowym stagingiem. Operator zwykle
   wykonuje `git push origin main`, następnie VPS `git pull --ff-only`.
   Nie deklaruj pushu, jeśli go nie wykonałeś. Nie przepisuj historii bez potrzeby.
6. Zbiorcze wdrożenie: sprawdzenie commita, spójny backup, jawne migracje,
   właściwe ecosystem/env, smoke i konfiguracja. Sam deploy nie aktywuje
   niezatwierdzonych dostawców lub mechanik.
7. Zbiorczy odbiór: odhaczenie dowodów albo diagnostyka → lokalna korekta
   i regresja → szybki commit/push → wznowienie od miejsca błędu.
   Nie powtarzać zaakceptowanych płatnych prób bez nowej przyczyny.

Domyślnie 2–3 planowane sesje VPS dla całego zakresu: opcjonalna diagnostyka,
wdrożenie i pilot/odbiór. To nie zakaz dodatkowej sesji przy rzeczywistej awarii.
Nie czekaj bezczynnie na cooldown API, gdy można pisać i testować offline.
Monitoring kosztów/heartbeat/SLO to ciągłe utrzymanie, nie pretekst do
odraczania zamknięcia odebranego zakresu.

### Lokalne środowisko i testy

Windows/PowerShell: `C:\DMD Michał Jankiewicz\wlasne\haos\app`, Python
`.venv\Scripts\python.exe`, zależności `requirements.txt`. Nie uruchamiaj
pełnego `run.py` na przypadkowej kopii produkcyjnej bazy; najpierw sprawdź
setup testów i fixture właściwego obszaru.

Przykładowy bezpieczny wzorzec testu (dobierz zakres do zmiany):

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p test_player_directory.py
node tests/js/test_camera_window_dedupe.js
git diff --check
```

Istnieją `tools/creator_browser_fixture.py` (izolowany host komponentu, port
8989), `poi_admin_fixture.py`, `poi_browser_fixture.py`,
`identity_gateway_browser_fixture.py`, `territory_display_fixture.py`,
`sprint_153_browser_fixture.py`, `sprint_154_8_browser_fixture.py`,
`cyberner_names_fixture.py`. Przeczytaj wybrany skrypt przed startem: fixture
komponentu nie dowodzi pełnego E2E generator → operacja → UI.

**Browser/UI: Playwright MCP domyślnie**, zgodnie z instrukcją operatora.
Uruchom udokumentowane lokalne środowisko, użyj izolowanych danych/kont,
odtwórz scenariusz, sprawdź DOM, widok i konsolę, napraw i powtórz. Zamknij
przeglądarkę i własne fixture po pracy. Brak Codex Browser nie blokuje użycia
Playwright MCP. Brak auth/tool zgłoś konkretnie; nie deklaruj browser PASS
bez wykonania. Nie deleguj operatorowi testu możliwego lokalnie.

PWA: viewport mobile nie dowodzi zainstalowanej PWA. Odtwarzalne scenariusze
lokalnie, realna instalacja/nawigacja/systemowy powrót podczas końcowego odbioru
na dostępnych urządzeniach. Brak urządzenia oznacza konkretną lukę dowodową.

### VPS i pułapki operatorskie

- Repo: `https://github.com/amnezja3/chaos.git`, branch w tym wątku `main`.
  VPS: `johndoe`, katalog `/home/johndoe/app/chaos`; Python `.venv/bin/python`.
- Operator używa **`ecosystem.web.config.js`**, nie `ecosystem.config.js`.
  Reszta procesów ma własne ecosystemy z tabeli. Utrwalaj flagi w konfiguracji,
  sekrety przez istniejący mechanizm środowiska, nie plaintext w repo.
- Przykład restartu odebranego profilu, **tylko gdy dany deploy tego wymaga**:

```bash
pm2 startOrReload ecosystem.web.config.js --only chaos --env world_maplark_region --update-env
```

- Kolektor używa `ecosystem.discovery.config.js --env regular_halo`.
  Nie restartuj wszystkich aplikacji hosta. `pm2 save` po poprawnym odbiorze
  zapisuje listę procesów, nie zastępuje backupu ani dowodu poprawności.
- Backup SQLite przez SQLite backup API albo sprawdzony skrypt: zwykłe kopiowanie
  aktywnego `.sqlite3` może pominąć WAL. `integrity_check` i foreign keys, prywatny
  katalog backupu; nie usuwać ledger/receipts dla „czystego testu”.
- `pm2 logs ... --lines N --nostream` pokazuje również stare zdarzenia.
  Zestawiaj timestamp, PID, revision/key i commit. `online` ≠ HTTP 200 ani E2E.
- Nie drukuj całego `pm2 env`, sekretów ani pełnych danych kont. Diagnostyka
  ma wypisywać whitelistę flag oraz `present/valid_format` klucza.
- Nie uruchamiaj transportu używającego multiprocessing spawn przez `python -`
  z heredoc: proces potomny próbował otworzyć `<stdin>`. Używaj istniejącego CLI
  lub pliku z prawidłowym `if __name__ == '__main__'`.
- `input()` w skrypcie czytanym z heredoc nie ma interaktywnego stdin — użyj
  oddzielnych komend przed/po albo normalnego pliku CLI.
- Przy tajnym `read -s` export i komenda Python muszą być osobnymi poleceniami.
  Nie wklejać całego uruchomienia jako argumentów `export`.
- Windows SCP używano z `-O` do prywatnego `instance/provider-captures/`.
  Nie commitować całego przechwycenia; wybierz zanonimizowaną fixture, provenance
  i hash. Attachments poprzedniego wątku mogą nie być dostępne w nowym.
- Błąd `credential-manager-core` nie zawsze oznacza nieudany push: sprawdź
  końcowy wynik Git i hash remote; nie naprawiaj w ciemno globalnej konfiguracji.

## 12. Dokumentowanie decyzji, sprintów i artefaktów

### Gdzie szukać

| Katalog | Co tam trafia / jak czytać |
| --- | --- |
| `doc/sprints/` | Zakres, zależności, status etapów, kryteria odbioru i decyzje zakresowe |
| `doc/audits/` | Fakty, testy, pomiary, traceability, macierze odbioru i ograniczenia dowodów |
| `doc/runbooks/` | Konkretna procedura plan/dry-run/apply, backup, env, test, rollback i interpretacja wyniku |
| `doc/architecture/` | Wiążące przekrojowe kontrakty: profil, stan, sesje, delty, LLM, zasoby |
| `doc/gameplay/`, `doc/systems/` | Kontrakty mechanik i systemów: GN, BlackNet, Cyberner, OFS, NPC |
| `doc/hardbugfix/` | Objaw, root cause, nietrafione próby, finalna naprawa i test zapobiegający regresji |
| `doc/incidents/` | Datowany przebieg incydentu operacyjnego |
| `doc/history/` | Chronologia/journal i dawne roadmapy; nie domyślny backlog do ponownego wdrożenia |
| `doc/plans/`, `doc/proposals/`, `doc/prototypes/` | Propozycje i materiały źródłowe; nie traktować makiety jako runtime |

Konwencje: `sprint_164_camera_visual_archive.md`, rozszerzenie `163.5` zapisane
jako `sprint_163_5_...md`. Nie renumeruj starych plików, nie zakładaj kolejnego
sprintu dla niedokończonego checkboxa. Numer/zakres nowego sprintu uzgadnia
operator; 166 dla uploadu został wyraźnie wykluczony.

Istniejący sprint aktualizuj przy zmianie jego zakresu/statusu. Na górze data,
stan, granice odbioru i link do evidence/runbooku. Historię oznacz jako historię;
nie usuwaj dawnych wyników ani nie mieszaj ich z aktualną listą blokad.
Nowy dokument ma sens dla odrębnego kontraktu, większego audytu, incydentu,
procedury lub przekazania. Nie twórz pięciu konkurencyjnych planów tej samej funkcji.

Hardbugfix: istniejąca konwencja `problem_alias_sprint_nr_YYYY-MM-DD.md`;
pełny format w [README hardbugfix](../hardbugfix/README.md). Drobnej zmiany CSS
nie rozdmuchuj do osobnego incydentu. Poważna regresja wymaga trwałej lekcji i testu.

Decyzja ma zawierać: datę, kto zatwierdził, konkretną treść/zakres, uzasadnienie,
alternatywy jeśli istotne, konsekwencje, pozostawione otwarte punkty, powiązany
commit/dowód. Zapisz ją w istniejącym sprincie/kontrakcie i zalinkuj w audycie;
journal służy chronologii. Nie twórz fikcyjnych akceptacji.

Rozróżniaj: **PLAN / implementacja / LOCAL PASS / wdrożone / VPS PASS /
akceptacja operatora / otwarte / zamrożone**. Liczba testów, screenshot,
HTTP 200, PM2 online i akceptacja wyglądu to różne dowody. Odbiór części nie
oznacza całego produktu. Podaj faktycznie wykonane komendy, środowisko, commit,
wynik i niewykonane sprawdzenia; testy z dawnych logów oznacz datą/źródłem.

### Obowiązkowe prowadzenie journalu

Kanoniczny dziennik: [doc/history/project_journal.md](../history/project_journal.md).
Aktualizuj go po spójnym pakiecie pracy, istotnej decyzji operatora, odbiorze,
wdrożeniu lub diagnozie regresji — nie dopiero przy zamknięciu sprintu i nie
po każdym pojedynczym teście.

- Nowe wpisy dodawaj pod tytułem i notą organizacyjną, **najnowsze na górze**.
  Nie przestawiaj całej historycznej części o mieszanej chronologii.
- Nagłówek: `## YYYY-MM-DD — sprint/obszar: konkretny rezultat`.
  Data zdarzenia tylko gdy potwierdzona. Uzupełnienie wsteczne oznacz datą
  zapisania i źródłem; jeśli daty zdarzenia nie znasz, użyj dzisiejszej daty
  i określenia „podsumowanie wcześniejszego wątku”, bez zgadywania.
- Zapisz problem/cel, zmianę i skutek, decyzję/zakres zgody, stan lokalny lub
  wdrożeniowy, wykonane testy i środowisko, ograniczenia i następny krok.
  Dodaj linki do sprintu, evidence/runbooku i znane commity. Nie wpisuj przyszłego
  hasha; commit bieżącego wpisu można odnaleźć przez Git.
- Wyniki z logów operatora oznacz jako przekazane, nie wykonane przez agenta.
  LOCAL PASS, VPS PASS, push i akceptacja wyglądu to różne dowody. Przy zmianie
  dokumentacji podaj kontrolę dokumentów, bez fikcyjnego runtime/browser PASS.
- Nie duplikuj całej checklisty sprintu. Root cause większej regresji trafia
  do hardbugfix, procedura do runbooku; journal podsumowuje i linkuje.
- Korektę decyzji zapisz jako nowy datowany wpis z odnośnikiem. Nie wymazuj
  wcześniejszego wyniku; można dopisać przy nim „zastąpione przez …”.
- Bez sekretów, pełnych profili i wielkich surowych logów. Wystarczy minimalny
  wynik i lokalizacja dowodu; dane kont wyłącznie gdy konieczne do diagnozy.

Przed commitem sprawdź spójność ze sprintem/audytem, linki i `git diff --check`.
Przy przekazaniu nowego wątku ostatni zakończony pakiet ma być w journalu
i aktualnym bilansie, a nie tylko w rozmowie. Dziennik nie zastępuje kontraktów.

### Jak ustalić, co jest aktualne

1. Najnowsza dyspozycja operatora określa zakres i priorytet.
2. Kod/testy pokazują implementację; nie dowodzą aktywnego stanu VPS.
3. Najnowszy datowany audit/odbiór i effective config określają potwierdzone
   działanie. Stary plan może mieć nagłówek sprzed kilku wdrożeń.
4. Wiążące kontrakty bezpieczeństwa/integralności nie tracą ważności tylko
   dlatego, że kod je narusza — to potencjalna regresja, nie nowa norma.
5. Starsze journale, koncepty i handoffy czytaj jako historię. Wpisy nie zawsze
   są chronologicznie posortowane; ostatnia linia pliku nie musi być najnowsza.

Praktyczna nawigacja, ograniczająca szum dużych JSON/logów:

```text
rg --files doc/sprints doc/audits doc/runbooks
rg -n 'camera_stream|camera_visual_preview' creator_policy.py run.py static/js/terminal.js
rg -n '163.5|regional|geometry-v2' doc/sprints doc/audits doc/runbooks -g '*.md'
git log --oneline -- path/to/file
git log -S 'symbol_lub_klucz' -- path/to/file
git blame -- path/to/file
```

Szukaj po symbolach, endpointach, flagach, komunikatach i nazwie błędu, nie tylko
numerze sprintu. Zawężaj `rg`: nie przeszukuj domyślnie całego `data/`, `.venv/`,
`instance/` i surowych `doc/audits/*.json`. Po zmianie dokumentacji sprawdź linki,
spójność statusów i `git diff --check`; testów runtime nie uruchamiaj tylko dla tekstu.

## 13. Znane otwarte obszary i rzeczy, których nie przywracać

Priorytet kontynuacji: 164.0, potem zaakceptowane 164–165. Pełny skaner Geoapify
pozostaje oddzielnym jawnym zadaniem po PASS 163.5; nie blokuje lokalnego prototypu.
Polish paneli: Identity Gateway i POI dostały poprawę grupowania/stylu,
checkboxy kompaktowo w poziomie; dalszy polish według realnych problemów, nie
przebudowa architektury. Śledzić budżety/heartbeat/SLO niezależnie od sprintów.

Otwarte lub niepotwierdzone: pełny live Mistral 154.8, całość 155, część urządzeń
PWA, produkcyjna aktywacja 157.8, trwałość CPU quota Ollamy, pełny Geoapify oraz
L01/L02 Mapillary. Najpierw sprawdź najnowszy dowód; te pozycje nie są automatycznym
poleceniem aktywowania wszystkich naraz.

Nie przywracać:

- full-profile fallbacków, globalnych skanów kont i writer-locków z HTTP;
- legacy kolejek narracji obok nowego pipeline'u i LLM jako autorytetu gameplayu;
- resetowania ledger/uncertain operations, cooldownów i zgód dla zaliczenia testu;
- `UNKNOWN`/truncated jako pełnego coverage lub siedmiodniowego archive jako fresh;
- starego regionalnego profilu MapLark v1 i domyślnego VK-primary bez nowej decyzji;
- ręcznego env tylko z powłoki jako docelowego sposobu konfiguracji PM2;
- przywracania starych flag OFF przez reload złego profilu ecosystem;
- identyfikatora OAuth jako jedynej publicznej etykiety i wyszukiwania tylko po nicku;
- powielania komunikatów Cybernera, wyboru gracza bez otwarcia rozmowy;
- osobnego systemu kamer, osobnych baz zdjęć per wygenerowana aplikacja;
- GhostLab v2, uploadu i Sprintu 166 bez wznowienia/nowej decyzji;
- wielokrotnych sesji VPS dla rzeczy, które można zakończyć lokalnie.

Ważne artefakty regresji w `doc/hardbugfix/`: heavy profile operation/files/GX
(135.5), marker/menu identity (138), operation-center canvas/bounds, focus
motocykla, partial target progress, vehicle capture side effects, kontrakt
publikacji LLM, CPU Ollamy. Przeczytaj odpowiedni przed poprawką podobnego objawu.

## 14. Ostatnie commity i decyzje tego wątku

| Commit | Znaczenie |
| --- | --- |
| `508175e` | Wybór rozmowy i widoczne oczekujące zaproszenia Cybernera |
| `9ae109e` | Uzgodnienie dowodów 163.5 i pozostającej luki dostawcy |
| `32000e0` | Zapis poprawnego post VPS 163.5 |
| `a68733a` | Akceptacja 163.5 z Geoapify do dokończenia |
| `da6690d` | Commit operatora pomiędzy odbiorem a aktualizacją planów; sprawdź diff przy potrzebie |
| `3cfa572` | Wycofania/atrybucja/licencje oraz PWA w 164–165 |
| `77d5c8f` | Ghost System → CVN, kompatybilność starszych aplikacji, LOCAL-FIRST, wyłączenia zakresu |

Nie wnioskuj z lokalnego commita o wykonanym pushu/deployu. Przy przekazaniu
nowy wątek może zobaczyć już późniejszy HEAD — najpierw odczytaj różnicę.

## 15. Krótka wiadomość inicjująca nowy wątek

Wklej poniższy tekst, gdy nowy wątek ma dostęp do tego repozytorium:

> Kontynuujemy CHAOS. Przeczytaj w całości
> `doc/runbooks/handoff_project_2026_10_31.md` jako prompt przekazania oraz
> `doc/architecture/profile_hot_path_contract_130_11_plus.md`. Sprawdź aktualny
> HEAD, status i instrukcje repo. Nie uruchamiaj historycznych procedur VPS.
> 163.5 ma zaakceptowany PASS z pełnym skanerem Geoapify do dokończenia;
> Cyberner ma PASS. Następny zaakceptowany kierunek to Camera Visual Network
> 164–165: zacznij od lokalnego prototypu jednej kamery 164.0 do mojej akceptacji.
> Uwzględnij automatyczną integrację aplikacji Ghost System i wyłączenie zdjęć
> graczy. Pracuj LOCAL-FIRST, grupuj implementację/testy i wołaj mnie dopiero
> przy potrzebnej decyzji, odbiorze wyglądu lub gotowym pakiecie VPS. Nie
> przywracaj ciężkich profili, dawnych kolejek ani zamrożonych sprintów.

Jeżeli nowy wątek nie ma repo, przekaż pełną treść tego dokumentu, a nie samą
ścieżkę. Kod, aktualne evidence i sekrety nadal pozostają w swoich właściwych
miejscach; prompt nie zastępuje ich odczytu przed implementacją.
