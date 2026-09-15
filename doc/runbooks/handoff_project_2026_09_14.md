# CHAOS — pełne przekazanie projektu, 14 września 2026

Status: **AKTYWNY PUNKT WEJŚCIA DO NOWEGO WĄTKU**.

Stan kodu sprawdzony przy `HEAD 96dec35` (`admin bug reporter`). Przed rozpoczęciem
tego przekazania drzewo Git było czyste. Dokument powstał na podstawie kodu,
kontraktów, journalu i przekazanych przez autora wyników produkcyjnych. Nie jest
wynikiem nowego audytu serwera ani świeżego pełnego E2E. Nie zawiera sekretów.

Ten dokument zastępuje **instrukcję startową i status** starego
[handoffu 139–140](handoff_sprints_139_140.md), nie usuwa jego historii.
Nie zaczynaj ponownie Sprintu 139.1, budowy show ani stylizacji 140 od zera.

## 1. Instrukcja startowa dla siebie w nowym wątku

1. Przeczytaj cały ten dokument i
   [kontrakt ciężkiego profilu](../architecture/profile_hot_path_contract_130_11_plus.md).
2. Sprawdź `git status --short`, `git log -12 --oneline`, aktualne instrukcje
   repozytorium oraz najnowsze wpisy [journalu](../history/project_journal.md).
3. Przeczytaj kontrakt konkretnej zmiany i powiązany hardbugfix **przed** edycją.
   Wyszukaj implementację i testy po nazwie funkcji/mechanizmu, nie tylko numerze sprintu.
4. Kontynuuj najnowsze polecenie autora. Kolejnym kierunkiem jest **Control Loop:
   sprinty poprawkowe całego gameplayu**; autor zapowiedział własne artefakty.
   Ich zakres nie został jeszcze dostarczony. Nie wymyślaj za niego nowego sprintu.
5. Ostatnia implementacja to admin Bug Reports. Jest w kodzie i ma testy;
   brak osobnego potwierdzenia ręcznego odbioru tej funkcji w rozmowie.
6. Nie wykonuj automatycznie rollbacku, ponownego triggera, zamknięcia sieci,
   migracji produkcyjnych, restartów workerów ani ponownego naliczania nagród.
   Polecenia i zgody z poprzedniego testu nie są instrukcją powtarzania go teraz.

### Co jest zakończone, co otwarte

| Obszar | Stan i jakość dowodu |
| --- | --- |
| 138.2 producer-backed E2E | Historyczny produkcyjny PASS; nie dowodzi bieżącego env workerów |
| 139 aktywacja/show/restart | Zrealizowany; wcześniejszy strict postflight PASS zapisany w historii |
| 140 i stylizacja .1–.10 | Zrealizowane, zamknięte w artefaktach; autor zaakceptował końcowy przebieg 13 IX |
| Odtwarzanie w jednej sesji | Autor potwierdził brak zacięć; nie mamy profilu GPU/CPU dla dwóch sesji |
| Puste archiwum Googleplex/BlackNet | Poprawiony odczyt historyczny; autor pokazał wpisy (2 i 4) |
| Brak NOWYCH publikacji po triggerze | **Otwarte**: osobna diagnostyka pipeline'u; hipoteza wyłączonych workerów/env |
| Logowanie po restarcie bez logoutu | Poprawione; testy i ręczny test autora PASS |
| Signal Registry | Układ, ikona, avatary, loga i położenie wyboru sygnału zaakceptowane |
| Bug Reports w adminie | Implementacja `96dec35`, 3 izolowane testy PASS; brak potwierdzenia browser QA |
| Control Loop | Następny kierunek, oczekiwanie na artefakty autora |

Formalnego strict postflight całego **nowego przebiegu z 13 IX** nie należy
dopisywać na podstawie screenów. Autor potwierdził zakończenie i restart;
to odrębny dowód od kompletnego audytu receiptów, efektów i ACK.

## 2. Produkt, świat, mechaniki

CHAOS = **Cyber Hacking Adventure Of Senses**. Przeglądarkowa gra hackerska:
„Hakuj cyfrowe zmysły współczesnego świata”. Mapa, pulpit GhostSystemu,
aplikacje, trwałe operacje, zasoby, pliki, rynek informacji i inni gracze są
jedną pętlą, a nie niezależnymi demonstracjami UI.

Podstawowa pętla:

```text
obiekt świata → akcja mapy → aplikacja → operacja → ruch/ryzyko
→ zasób → plik → Ghost Exchange → poczta/rozliczenie → HC → aplikacje → mapa
```

Rozróżniaj `source_type`, `target_type`, `target_mode`, `map_action_id`,
`operation_type` i `resource_types`. Akcja wyraża intencję, aplikacja określa
obsługiwane możliwości, operacja jest trwałym procesem, zasób jest wynikiem.
Nie mapuj ich zamiennie po podobnej nazwie. Operacje mogą trwać, zostać wykryte,
zakończyć się, wygasnąć lub zostać anulowane; UI nie jest właścicielem ich życia.
Plik i HC wymagają kanonicznego efektu/rozliczenia, nie lokalnego dopisania licznika.

Czytaj [ABOUT](../overview/ABOUT_CHAOS.md),
[pętlę](../gameplay/gameplay_loop.md), [terminy](../gameplay/gameplay_terms.md),
[operacje](../gameplay/operations.md), [aplikacje](../gameplay/app_contract.md),
[pliki](../gameplay/file_model.md), [ekonomię](../gameplay/data_economy.md),
[ruch](../gameplay/movement_model.md), [ryzyko](../gameplay/risk_events.md)
i [interakcje mapy](../gameplay/map_interactions.md).
Wczesne dokumenty opisują także stan docelowy; realizację potwierdzaj w kodzie.

### Kanon, którego nie zmieniamy przypadkiem

- W 2026 MASA jeszcze nie istnieje w końcowej postaci. W 2108 ogranicza
  ludzkie decyzje przez kontrolę infrastruktury, danych i przewidywania.
- GhostSystem pochodzi z 2108. Mapa łączy infrastrukturę/ślady pomiędzy epokami.
- Cztery klany: `virex` / VIREX, `echo_freedom` / Echo Wolności,
  `phantom_mesh` / Siatka Widmo, `sentinel_order` / Strażnicy Ładu.
- Cztery maszyny, po pięć części i profesji: razem 20. Aktywne części dają
  właściwe supermoce. Tożsamości i relacje wyznacza `ghostnetwork/catalog.py`.
  Nie zastępuj katalogu zestawem przypadkowych grafik ani kolejnością DOM.
- GhostSignal pochodzi z **rzeczywistych decyzji graczy**. Model językowy może
  opowiadać o zdarzeniach, ale nie wytwarza mechaniki, strategicznych wyników,
  uprawnień, nagród czy źródłowego przebiegu sygnału.
- Kolejne cykle i sygnały są przewidziane. Wynik fabularnej podróży nie odbiera
  zdobytych nagród. Ranking graczy/RSP, wynik klanu i HC to różne wielkości.

## 3. Mapa architektury

| Warstwa / miejsce | Odpowiedzialność i sposób wejścia |
| --- | --- |
| `run.py` | Flask, endpointy, globalne bramki, integracje gameplayu; duży monolit, szukaj symboli, nie czytaj od początku przy każdej zmianie |
| `config.py`, `ecosystem.*.config.js` | Polityki i env; wartości w pliku nie są dowodem efektywnego env PM2 |
| `database.py` | SQLite i wyspecjalizowane store'y; projekcje, runtime, ledger, receipts |
| `profileManagment.py` | Legacy/kanoniczne mutacje profilu; pisownia nazwy jest celowo podana dokładnie |
| `session_generation_store.py` | Trwała generacja sesji, ochrona zapisu, restart/ACK |
| `ghostnetwork/repository.py`, `service.py`, `runtime.py` | Persistence, fasada domeny, koordynacja runtime |
| `ghostnetwork/catalog.py`, `topology.py`, `abilities.py`, `ability_realizers.py` | Części/profesje/maszyny, topologia, efekty mocy |
| `ghostnetwork/closure.py`, `transmission.py`, `rewards.py`, `ranking.py` | Gotowość i lock cyklu, transmisja, idempotentne efekty i archiwalny ranking |
| `ghostnetwork/territory.py`, `conflicts.py`, `territory_defense.py` | Terytoria, konflikt i blokady mechaniczne |
| `ghostnetwork/show.py`, `show_manifest.py` | Trwały show i ograniczona publiczna projekcja prezentacji |
| `ghostnetwork/archive.py`, `visibility.py`, `deltas.py` | Odczyt archiwum, audience, powiadomienia o zmianach |
| `ghostnetwork/producers.py`, `narrative.py`, `ollama_worker.py`, `publication.py`, `publication_lifecycle.py` | Zdarzenie → zadanie → kandydat → walidacja → publikacja i jej lifecycle |
| `static/js/terminal.js` | Pulpit, aplikacje, operacje i integracja aktualizacji; także Registry i formularz błędów |
| `static/js/ghost_signal_show.js` | Wspólny kontroler całego show, jego scen, mediów i recovery |
| `static/js/session_generation.js` | Kontekst generacji/epoki dokumentu, komunikacja z API i izolacja sesji |
| `static/js/ghost_radio.js` | Radio/audio; show współpracuje z istniejącym systemem |
| `templates/index.html`, `linux.html`, `linux_old.html`, `map_template.html` | Wejścia dokumentów, boot i referencje assetów/cache |
| `scripts/*worker.py` | Osobne procesy territory, generowania narracji i publikacji |
| `tools/build_ghostsignal_show_preview.py` | Odtworzenie projekcji do samodzielnego HTML, nie drugi silnik rozliczenia |

Dalsze mapy domen są w [indeksie](../README.md) i katalogach `doc/systems/`.
BlackNet, Cyberner, Googleplex, OFS, incydenty NPC i Response Network mają
własne kontrakty. Nie obchodź ich przez nową logikę w pojedynczym endpointcie.

### Kanoniczne magazyny i granice

SQLite jest źródłem runtime. `static/*.json` to seed/referencja, a nie automatycznie
aktualny świat: istnieje jawny import/sync do `JsonResourceStore` / `json_resources`.
Zmiana JSON w repo nie oznacza aktualizacji działającej bazy.
Zobacz [resource architecture](../architecture/resource_architecture.md).

W `database.py` odnajdziesz m.in.:

- `UserStore`, `UserIdentityProjectionStore`, `UserCapabilityProjectionStore`;
- `PlayerOperationStore`, `PlayerInventoryStore`, `SystemMessageStore`;
- `PlayerTargetRuntimeStore`, `PlayerMarkedTargetStore`, `PlayerPositionStore`;
- `WalletStore`, `WalletLedgerStore`, `WalletBalanceStore`;
- `TerritoryStore`, `TerritoryConflictStore`, `TerritoryTargetOwnershipStore`, progression/action receipts;
- store'y Cyberner world/clan/cursor/mail i `DevBugReportStore`.

Nazwę klasy sprawdź przez `rg '^class ' database.py` przed użyciem: nie twórz
drugiego store'u dlatego, że nie znalazłeś starego przez nazwę endpointu.

## 4. Nienaruszalne zasady stanu i zapisu

1. Frontend, cookie/cache, localStorage, delta bus i manifest **nie są źródłem
   prawdy mechaniki**. Delta powiadamia o zmianie istniejącego stanu.
2. Zachowuj stabilne ID i lineage: event → lock → signal → show → ranking;
   receipt rozliczenia, publikacji i konsumpcji nie może powstać drugi raz.
3. Retry/reload/restart procesu musi być idempotentny. Nie zastępuj trwałego
   dedupe flagą JS lub słownikiem w jednym workerze.
4. Snapshot/delta: monotoniczne wersje, odrzucenie starszych odpowiedzi,
   ograniczone recovery przy luce, bez cofania nowszego stanu i bez pełnego
   rebuild mapy po drobnej zmianie.
5. Public/clan/owner filtruje serwer przed serializacją. Nie wysyłaj prywatnych
   treści wszystkim, licząc na ukrycie CSS-em. LLM nie ustala audience.
6. Przed `BEGIN IMMEDIATE` przygotuj kosztowne odczyty, model, projekcję,
   serializację i walidację. W krótkiej transakcji: recheck/CAS, zapis i commit.
   Żadnego HTTP/Ollamy, pełnych profili czy globalnego reconcile w writer locku.
7. Przy mutacji profilu zachowaj revision/checksum/integrity gate, LKG,
   session precommit guard i kontrolę konfliktu. Nie wyłączaj integralności
   „dla szybkości”. Zoptymalizuj zakres danych i miejsce pracy.
8. Migracje jawne, powtarzalne, z rozróżnieniem planu i `--apply`.
   Nie uruchamiaj init schema ani globalnego backfill w każdym requestcie.

Źródła: [hot path](../architecture/profile_hot_path_contract_130_11_plus.md),
[state versions](../architecture/state_version_contract.md),
[delta schema](../architecture/delta_event_schema.md),
[synchronizacja runtime](../architecture/runtime_synchronization_audit.md),
[inwentarz sesji](../architecture/session_generation_endpoint_inventory.md),
[migracje](../architecture/database_migrations.md).
Stare kontrakty wersjonowania opisują etapy wdrażania; ich „delta dopiero powstanie”
nie jest opisem dzisiejszego kodu.

## 5. Ciężki profil: najważniejsza lekcja projektu

Historyczny realny profil `main` miał około **34,6 MB**. Pełny odczyt JSON,
parsowanie, schema validation, checksum, deepcopy, serialize, zapis i LKG
powtarzane w zwykłych requestach powodowały opóźnienia całego gameplayu.
Dotyczyło to też workerów i fan-outu odbiorców, nie tylko samego `/profile`.

**Optymalizacje nie usunęły wszystkich ciężkich callsite'ów.** Sama nazwa
`readonly`, `snapshot`, `preview` albo `get_profile` niczego nie gwarantuje.
Inwentarz do dalszej pracy jest w
[załączniku: ciężkie i lekkie ścieżki](handoff_hotpaths_2026_09_14.md).

### Dwa różne znaczenia „lekkiego odczytu”

- W 130.10.1 `UserStore.get_profile()` uproszczono: bez pełnej walidacji,
  checksum i deepcopy na zwykłym odczycie. **Nadal czyta i parsuje cały JSON**.
  Odrzuca uszkodzony format/tożsamość i respektuje stan recovery.
- Kontrakt 130.11+ wymaga dla hot path **braku pełnego odczytu profilu**:
  projekcji skalarów, indeksu albo wyspecjalizowanego store'u z limitem.
- `get_profile_with_revision` i rzeczywiste profile mutation/recovery mają
  inny kontrakt integralności. Nie wolno zamienić ich bez analizy w luźny read.

Nie wracamy do `sync_session_profile`, `UserProfileManager`, `list_profiles`
czy `json_extract` po wszystkich dużych profilach dla avatara, klanu, salda,
celu, pollingów i audience. „Jedno zapytanie SQL” może nadal skanować gigabajty.

### Z czego czytać

| Potrzeba | Preferowana ścieżka |
| --- | --- |
| Tożsamość, klan, profesja, boot pulpitu | Integrity-gated identity projection; `get_desktop_boot` |
| Dostępne możliwości | Capability projection; `get_capabilities` |
| Cel i postęp celu | Target runtime / marked-target stores |
| Operacje i wiadomości | Canonical operation/system-message stores |
| Aplikacje, storage, pliki | Inventory oraz kanoniczne rekordy plików |
| Pieniądze | Balance/ledger, nie przeliczenie przez pełny profil |
| Terytoria i konflikty | Właściciele, conflict stores, ograniczone projekcje |
| GN/show/ranking | Tabele domeny i utrwalony publiczny snapshot |
| Odbiorcy publikacji | Indeks/projekcja z audience, bez profilu każdego odbiorcy |

Sparse projection nie jest pełnym profilem. Nie podstawiaj jej jako całego
`session['profile']` ani nie zapisuj jako zamiennika dokumentu użytkownika.
Aktualizuj tylko wskazane pola, respektując wersję i generację.

### Kiedy pełny profil jest dopuszczalny

Nazwany przypadek: naprawa/forensics konkretnego konta, rzeczywista zmiana
kanonicznych pól profilu, jawna weryfikacja integralności/LKG. Taki wyjątek ma
mieć ograniczony zakres i test. Nie rozciągaj go na cały request chain.
Przy dozwolonej mutacji przygotuj payload przed writer lockiem i wykonaj
guarded CAS. Zakaz globalnych odczytów obowiązuje również wtedy.

### Jak udowodnić brak regresji

Mały fixture **i profil ≥35 MB**. Mierz `profile_full_read`, `profile_full_write`,
bajty, liczbę zapytań i writer wait; nazwy dokładnych metryk sprawdź w testach.
Dla zwykłego read oczekiwane zero pełnych odczytów/zapisów i bounded work.
Dla wyjątku wykaż dokładnie potrzebny koszt, bez fan-outu na wszystkich graczy.
Nie uznawaj wyniku z małym testowym kontem za dowód wydajności produkcyjnej.
Podnoszenie timeoutu Gunicorna nie naprawia problemu.

## 6. `bounceback`, częściowe odpowiedzi i zależności legacy

W repo określenie `bounceback` występuje w opisach historycznych; nie znaleziono
osobnego modułu ani funkcji o tej nazwie. Nie wymyślaj „BouncebackService”.
Traktuj je jako historyczny skrót rozmowy o powrocie stanu/lekkich projekcjach;
konkretne zachowanie ustalaj z call chainu i artefaktu danej poprawki.

Istotne, istniejące mechanizmy:

- `gonnaWinRequestQueue` w `terminal.js` zachowuje kolejność. Przepływ
  `gonna-win` obejmuje sekwencyjne kroki; nie „optymalizuj” ich w race.
- `operation_only` aktualizuje kanoniczną operację i ograniczony wynik,
  bez odtwarzania pełnego profilu. Faktyczny capture ma osobny guarded patch.
- Partial response nie może wymazać pozostałych pól klienta, cofnąć postępu
  celu ani przejść do dokumentu innego konta/generacji.
- Dedupe/action receipt, wersja i generacja sesji to niezależne zabezpieczenia.
  Nie usuwaj któregoś, bo „już mamy cache” albo lokalny Promise.
- `UserProfileManager` nie może wrócić do skanu wszystkich kont w konstruktorze
  i po save. Shared store/service inicjalizuje się raz na proces, nie request.
- Lżejszy transport ujawnił błędy marker/menu identity. Naprawa tożsamości mapy
  jest osobnym kontraktem, a nie argumentem za przywróceniem pełnego profilu.

### Regresja plików operacji i Ghost Exchange, 135.5

Pełny raport:
[heavy profile / operation files / GX](../hardbugfix/heavy_profile_operation_files_gx_regression_sprint_135_5_2026-08-30.md).

Po odchudzeniu lustrzanej historii operacji przestały pojawiać się pliki.
Naprawa przez ponowne hydratowanie profilu spowolniła hacki około pięciokrotnie;
ucierpiały mapa, picker, operation control/cancel, File Manager i GX/portfel.
Zatrzymanie workerów nie usuwało przyczyny.

Właściwa naprawa:

- kanoniczne `player_operations` pozostają źródłem operacji;
- `finalize_operation_files_bounded(username, operation)` finalizuje **jedną**
  operację, z minimalnymi danymi storage i bez pełnej kolekcji plików profilu;
- rekord pliku/storage/`artifact_state` jest spójny, `file_id` idempotentny;
- File Manager czyta projekcję inventory, GX synchronizuje lifecycle po sprzedaży;
- `compact_legacy_profile_operations.py` usuwa mirror tylko po sprawdzeniu,
  że canonical store zawiera wymagane dane. Nie stosować blanket-delete.

Historycznie profile po kontrolowanej kompaktacji spadły do ~2,68/1,71 MB;
to wynik konkretnego recovery, **nie gwarancja obecnego rozmiaru**. Timeout
operacji może nadal legalnie zakończyć się plikiem. Nie utożsamiaj go z brakiem
artefaktu. Weryfikuj cały łańcuch operacja → plik → storage → GX → HC.

## 7. Mapa: regresje, których nie cofamy

Obowiązkowe raporty przed zmianą mapy:

- [marker/menu identity, Sprint 138 getway 3–5](../hardbugfix/scan_marker_menu_identity_leaflet_dispatch_sprint_138_getway_3_5_2026-09-07.md);
- [Operation Center cache signature i canvas bounds](../hardbugfix/138_operation_center_cache_signature_canvas_bounds_2026-09-09.md);
- [map delta audit](../audits/map_delta_audit.md).

Akcja musi wskazywać rzeczywiście kliknięty obiekt. Zachowaj canonical DOM
binding `_chaosContextBinding`, utrwalony snapshot celu per marker,
delegowany capture `contextmenu`, zatrzymanie niepożądanego dispatchu i
przewidziany fallback per marker. Nie wyznaczaj celu po indeksie, bliskości,
kolejności warstw ani callbacku odziedziczonym po innym markerze.

Tooltip nie jest autorytetem celu. Historycznie po serii 10 skanów akcje
otrzymały PASS, a sporadyczny niewłaściwy tooltip pozostał osobnym problemem
prezentacji. Nie naprawiaj go przez zmianę prawidłowego target binding.

Zachowaj ochronę przed wyścigiem bounds Polyline/Polygon w Leaflet i naprawę
niezdefiniowanego `cacheSignature` Operation Center. Throttling logów nie jest
naprawą błędnego lifecycle. Testuj odświeżenie skanów, zmiany zoomu, usuwanie
warstw, aktywną operację, kliknięcia i powrót do karty.

## 8. GhostNetwork: closure, show i restart

Pełny zestaw 20 części nie oznacza automatycznej zgody na transmisję:
readiness/conflict gate nadal obowiązuje. Lock utrwala stan dla transmisji;
efekty, reward receipts, konsumpcja terytoriów i ranking mają trwałą lineage.
Nie ustawiaj ręcznie `conflict_state='none'`, by „uruchomić demo”.

Sprint 139 zapewnił natychmiastową trwałą aktywację show i blokadę gameplayu.
Show nie czeka na Ollamę. Rozliczenie nie zależy od tego, czy gracz obejrzał
film albo czy przeglądarka skończyła timer. Rollover i restart są domenowe.

### Epoka dokumentu i generacja sesji

To odrębne osie ochrony. Backend sprawdza kontekst dokumentu, a zapis także
precommit. Stary dokument po rollover ma dostać `ghostsystem_restart_required`
/ `document_epoch_replaced`, a nie móc dalej modyfikować gry. Nowy boot
korzysta z lekkiej projekcji, potwierdza właściwy kontekst/ACK.

Przykład historyczny: `ghostnetwork_0001` → `ghostnetwork_0002`, wersja
`1.0.1` → `1.0.2`. Nie hardkoduj tych wartości. `show_active:false` i blokada
starego dokumentu nie oznaczają, że show nadal trwa.

Naprawiony błąd: po wykonanym restarcie ponowne logowanie z zachowanym cookie
było odrzucane. `GET /` miał wyjątek, `POST /` nie. W
`ghostsignal_request_is_exempt` dodano **wyłącznie** wyjątek `index` + POST;
hasło jest nadal sprawdzane, stare gameplay writes nadal blokowane (423).
10 izolowanych testów client restart i test autora PASS.
Nie rozszerzaj wyjątku na wszystkie POST/API i nie każ użytkownikowi stale
robić logoutu. Admin page boot ma własne świadome wyjątki; zachowaj izolację.

## 9. Show: ustalony wygląd, dane, timing

Źródło scen: `ghostnetwork/show_manifest.py`, manifest v2 i kontroler
`static/js/ghost_signal_show.js`. Jest 49 scen w 900 sekundach.
`sceneAt`/elapsed względem czasu serwera, recovery po ukryciu karty i
przeorientowaniu nie mogą uruchamiać rozliczenia drugi raz.

Orientacyjna mapa czasu (dokładne granice sprawdzaj w kodzie):

| Sekundy | Segment |
| --- | --- |
| 0–160 | Części |
| 160–300 | Grupy/focus |
| 300–360 | Pierścień |
| 360–420 | Cztery maszyny |
| 420–425 | Wyciszenie sceny / przygotowanie filmu |
| 425–463,12 | Film 38,12 s |
| 463,12–480 | Replay/rozbłysk, ślad sygnału, terminal 2108, potwierdzenie |
| 480–630 | Świat, mapy i terytoria |
| 630 / 660 / 680 / 700 | Nagrody / gracze / osiągnięcia / klany |
| 720–840 | System, Googleplex, profesje/pliki, BlackNet, pulpit/gotowość |
| 840 / 855 / 870 / 880 | Rankingi / klany / statystyki / archiwum |
| 890 / 896–900 | Zamknięcie / restart |

### Oprawa zaakceptowana przez autora

- Wspólny charakter show: ciemne tło, stonowana szałwia/szarość, duża typografia,
  cienkie ramki, logi i OFS/glitch. Nie wracamy do neonowego pustego legacy HUD.
- Desktop i portrait mają oddzielny reflow, wspólny styl. Pary referencyjne
  służyły zatwierdzeniu; nie odtwarzaj bez zgody kolejnego redesignu.
- Części mają kanoniczne pozycje/tożsamości, cztery warstwy głębi. Zaakceptowano
  korekty skali foreground i przyciemnienie tylnego planu. Nie ujednolicaj
  czterech maszyn do jednej planszy VIREX z podmienioną nazwą.
- Użyte zatwierdzone assety m.in. `signal_sends/*_active.png`,
  `write_signal_scena_bg.png`, loga klanów `_pro.png`. Szukaj pliku przez `rg --files`.
- Zapis: puls światła dokładnie na jasnym punkcie tła, delikatnie wychodzi
  poza niego. Scena video zachowuje to samo tło.
- Film na pierwszym planie może przykryć tytuł. Desktop: tytuł po lewej w stylu
  zapisu, większa o ~30% i bardziej panoramiczna ramka (2:1). Sam film
  zachowuje proporcje oryginału 720×480 (3:2), bez rozciągania.
- Mobile: szerokość video do paddingu tytułu; bez dodatkowej wąskiej kolumny.
- Rozbłysk to szybkie **trzy klatki**, nie płynne powiększanie: cienka pozioma
  linia 50 ms, prostokąt ~3/4 ekranu 75 ms, biel 500 ms, zanik 125 ms
  przyspieszający ku końcowi. To finalne czasy po przyspieszeniu 2×.
- Po błysku logi typewriter kanału 2108 pojawiają się w tym samym ekranie co
  video. Nie dokładać osobnej obcej scenografii.
- Koniec filmu musi odtworzyć się wraz z efektem; zachowaj tail grace 1,5 s
  i obsługę faktycznego zakończenia. Nie ucinaj ostatnich klatek samym timerem.
- Terytoria: **abstrakcyjny kształt na tle globu**, nie geolokalizacja.
  Każde raz, równe odcinki czasu w segmencie 150 s, jednolita ciągła granica.
  W logach owner/współrzędne, gdy istnieją. Nie losować fikcyjnej geometrii.
- Gracze: kolejno, nick tytułem (mniejszy niż pierwotny gigant), klan
  podtytułem, LVL i RSP, pionowy avatar, mały numer rankingu w rogu.
  Aktywny gracz podświetla właściwą pozycję listy. Numer zmniejszono o połowę.
- Nagrody: subtelny puchar SVG, mobile łamie tytuł. Ranking/nagrody/statystyki
  korzystają z ekranowego szablonu, nie osieroconego legacy overlay.

### Audio i wydajność

Cztery ścieżki `ghostsignal_show_part_01..04.mp3` w
`static/audio/ghostnetwork/show/`, razem około 860,055 s. Nie twórz równoległych
odtwarzaczy radia bez potrzeby. Ostateczna decyzja: muzyka zaczyna wyciszać się
**dopiero z pierwszą klatką filmu**, przez **3,5 s** (425–428,5), podczas gdy
film już ma własny dźwięk. Następnie pauza muzyki; wznowienie po filmie z
krótkim fade-in. Stare 0,5 s fade-out przed filmem jest nieaktualne.

Ochrona końcówki filmu, brak kolejnego seek podczas `seeking`, tolerancja
dryfu fazy animacji do 250 ms i wygaszanie zbędnych efektów/światła podczas
filmu ograniczają pracę. Zachowaj cleanup RAF, timerów, tooltipów i DOM przy
wyjściu ze sceny. „Wyczyść cache” nie zastępuje lifecycle zasobów.
Autor miał zacięcia przy dwóch sesjach, a przy jednej potwierdził płynność.
Nie dowodzi to wyłącznej przyczyny; nie deklaruj naprawy całej wydajności GPU.

### Prawdziwe dane i uczciwe braki

`prepare_scene_snapshot` utrwala ograniczoną projekcję części i docelową datę
2108. `prepare_settlement_scene` czerpie z zatwierdzonego rankingu. Ma limity
(m.in. 24 KiB, 40 terytoriów, 20 graczy, geometria 3–32 wierzchołki) i oznacza
truncation/brak geometrii. Nie usuwaj limitów ani nie zmyślaj danych.

Avatar/LVL są utrwalonymi polami skalarnymi; nie pobieraj pełnego profilu
każdego gracza co klatkę/poll. Preview starego sygnału może pokazać aktualny
avatar/LVL tylko jako jawnie oznaczony podgląd. Nie zmienia to immutable rankingu.

Pasek postępu przedstawia **datę podróży sygnału**: interpolacja
`signal_sent_at` → `cycle_history.future_2108_timestamp`, według tej samej
frakcji czasu. Docelową datę wybiera backend stabilnie dla signal ID i zapisuje.
Historyczny brak dat ma pozostać jawny; nie losować daty przy odświeżeniu.

## 10. Archiwum publikacji a pipeline nowych treści

To **dwa osobne zagadnienia**.

### Naprawione: historyczne wpisy znikały przez TTL feedu

Show 13 IX miał 0 publikacji, podczas gdy baza miała 20 rekordów z 8–9 IX.
Nawet rekord `active` mógł mieć `valid_until` 10 IX. Odczyt archiwum błędnie
stosował ważność bieżącego feedu. Poprawka dopuszcza publiczne opublikowane
`active`/`expired` z właściwego cyklu sprzed cutoffu końca show; nadal wyklucza
`invalidated`, owner/clan, nieopublikowane, późniejsze i inne cykle.
Nie reaktywuje starych wiadomości w normalnych feedach.

Autor potwierdził wpisy Googleplex (2) i BlackNet (4). To nie znaczy, że
powstały nowe treści po triggerze. Brak tekstu nie musi być problemem CSS.

### Otwarte: nowe publikacje po triggerze

W przekazanych wynikach najnowsze publikacje były z 9 IX, show z 13 IX.
W aktualnych ecosystemach:

```text
CHAOS_OLLAMA_WORKER_ENABLED = process.env.… || "false"
CHAOS_NARRATIVE_PUBLISHER_ENABLED = process.env.… || "false"
CHAOS_OLLAMA_SOURCE_EVENT_ID = process.env.… || ""
```

`pm2 online` nie dowodzi, że worker wykonuje pracę. Reload ecosystemu z
`--update-env` bez jawnego ustawienia flag mógł zostawić/ustawić `false`.
Stary selector eventu też może ograniczać pracę. To mocna hipoteza z kodu,
**nie potwierdzony odczytem aktualnego env root cause**.

Bezpieczna kolejność diagnostyki:

1. Ustal dokładny cycle/signal/source event i czas przebiegu.
2. Sprawdź allowlistę istotnych flag PM2, bez dumpu całego środowiska/sekretów.
3. Producer/outbox: czy zadanie powstało i do jakiego eventu należy?
4. Claim/lease/heartbeat/retry/dead-letter: czy worker je podjął?
5. Kandydat/model/output validation/quarantine: gdzie zatrzymał się wynik?
6. Receipt/medium/audience/active_state/cutoff: czy opublikowano właściwą treść?
7. Dopiero potem projekcja show i cache wygenerowanego preview.

Narzędzia: `scripts/audit_narrative_runtime.py`, `audit_narrative_generation.py`,
`audit_narrative_output_safety.py`, `audit_narrative_publication_lifecycle.py`,
`audit_narrative_e2e.py`, `audit_narrative_cutover.py`.
Najpierw `--help`/kontrakt: audyt z opcją generowania nie jest automatycznie
read-only. Nie włączaj bez analizy całego starego backlogu. Nie omijaj quarantine.

Model w ecosystemie: `llama3.1:8b`, pin/digest w konfiguracji; timeout generacji
240 s i shutdown grace 300000 ms. Nie skracaj grace poniżej pracy in-flight.
Legacy BlackNet JSON jest diagnostycznym eksportem, nie drugim transportem.
Canonical outbox ma dedupe, claim/lease/CAS, retry/dead-letter i recovery.

## 11. Preview, dane demo i walidacja wizualna

`/static/previews/ghostsignal-stylization-10-history.html` jest wygenerowanym
HTML z osadzonym manifestem. Zwykłe odświeżenie pliku nie przebudowuje jego
danych z SQLite. Po poprawce danych/generatora wygeneruj nowy plik, najlepiej
z nową nazwą. Nie pomyl preview demo z historycznym podglądem produkcji.

```bash
# Najpierw sprawdź opcje bieżącego generatora:
.venv/bin/python -B tools/build_ghostsignal_show_preview.py --help
# Wzorzec odczytu historii; użyj właściwej kopii bazy i nowej nazwy:
.venv/bin/python -B tools/build_ghostsignal_show_preview.py \
  --db data/game.sqlite3 --cycle-id ghostnetwork_0001 \
  --output static/previews/ghostsignal-history-NEW.html
```

Generator ma kontrakt read-only i ochronę przed przypadkowym nadpisaniem.
Odtwarza publikacje do cutoffu show; nie przelicza nagród i nie mutuje historii.
W live pipeline publikacje mogą uzupełnić aktywną projekcję; nie wolno w tym
celu odpalać ciężkiego odczytu co poll. Brak `--db` oznacza wariant demo.

Para referencyjna `static/references/ghostsignal/montage-pair.html` prezentuje
1920×1080 i 1080×1920; iframe'y nie służą pełnemu testowi audio. Pełny odsłuch
rób na pojedynczym preview. Start blisko filmu ułatwia `?start=415&controls=hidden`
tam, gdzie obsługuje go aktualny generator/kontroler.

Testy sprawdzają kontrakty, ale nie zastąpią pełnego odsłuchu, mobile,
orientacji, ukrycia/powrotu do karty i końcówki filmu. Zapisuj, co rzeczywiście
sprawdzono, zamiast dopisywać „PASS” za test niewykonany.

## 12. Signal Registry — stan końcowy

Kod: `createGhostSignalArchiveApp` i loader w `terminal.js`,
`static/css/signal_registry.css`, backend `ghostnetwork/archive.py` i endpointy
archive/signals/rankings/all-time w `run.py`.

- Jedna kolumna nagłówka i treści, jedna powierzchnia scrolla, szczególnie mobile.
- Stylistyka show, CSS ograniczony do aplikacji; nie zmienia wszystkich okien.
- Ikona aplikacji **≋**.
- Przy nickach okrągłe avatary (44 px), delikatny szary outline, bez poświaty,
  kadr jak w profilu. Naprawiona specyficzność CSS/overflow, nie wraca pionowy prostokąt.
- Klany: kwadratowe logówki SVG w `static/images/ghostnetwork/clans/`.
  Show korzysta z zatwierdzonych `_pro.png`; nie zamieniaj tych zastosowań przypadkiem.
- Przyciski kolejnych sygnałów są **pod rankingiem wybranego sygnału, przed all-time**.
- Długie nicki/daty się zawijają, wynik na mobile może zejść pod opis.
- Archiwum pozostaje read-only. Listy mają limity; all-time nie jest obietnicą
  nieograniczonego jednorazowego payloadu. Avatary all-time korzystają z
  dostępnych danych rankingowych i jawnego defaultu, nie skanu wszystkich profili.

Autor zaakceptował całość. Nie wracaj do poprzedniej lokalizacji selektora
sygnałów na górze ani do kilku niezależnych scrolli.

## 13. Ostatnia funkcja: admin Bug Reports

Polecenie: przenieść obsługę statusów i widoczność zgłoszeń do admina,
umożliwić pobranie całości w jednym TXT. Gracze nie mają widzieć listy błędów.
Wybrano dozwolony przez autora prostszy wariant: **pulpit tylko wysyła,
również na koncie admina; zarządzanie wyłącznie w panelu**.

Implementacja `96dec35`:

- `/admin?tab=bugs`, `templates/admin_bug_reports.html`: wyszukiwanie,
  kategoria/status, lista, szczegóły, zmiana istniejących statusów, Dump all.
- Branch zakładki przed `build_admin_dashboard_state`, więc nie buduje ciężkiej
  całej listy profili tylko po to, by obejrzeć zgłoszenia.
- `DevBugReportStore`: zachowana baza i dotychczasowe statusy, bez migracji.
- `GET /api/dev/bug-reports`, podobne zgłoszenia, `PATCH` statusu i
  `GET /api/admin/bug-reports/dump` wymagają admina po stronie serwera.
- POST wymusza `new`, nie zwraca podobnych zgłoszeń. Zachowany dotychczasowy
  `require_dev_mode`: formularz nadal jest funkcją dev/staging, nie nową
  ogólnodostępną funkcją produkcyjną. Ecosystem web ma `APP_ENV=staging`.
- Dump: UTF-8 TXT, pełne rekordy/kontekst jako bloki JSON; iterator `fetchmany(200)`,
  **wszystkie** zgłoszenia, niezależnie od limitu widocznej listy 200.
- Frontend szczegółów używa bezpiecznego tekstu, nie wstrzykuje treści reportu
  jako HTML. Panel zachowuje existing session-generation/epoch bridge.
- `require_dev_admin` opiera się na serwerowej sesji konta `admin`, nie fladze JS.

`tests/test_admin_bug_reports.py`: 3 izolowane PASS, obejmują odmowę dostępu,
prywatność tworzenia, statusy i eksport 512 rekordów ponad limit listy.
Składnia JS PASS. Brak osobnego ręcznego odbioru panelu w rozmowie.
Zmiana nie wymaga migracji DB. Nie cofaj uprawnień do „ukrytego przycisku”.

## 14. Produkcja, backupy i dowody z ostatniego przebiegu

Lokalnie Windows/PowerShell:
`C:\DMD Michał Jankiewicz\wlasne\haos\app`.
Serwer autora: `/home/johndoe/app/chaos`, `.venv/bin/python`.
Web w ecosystemie: Gunicorn `127.0.0.1:6666`, 4 workers, timeout 120 s.
Adres widoczny w rozmowie: `chaos.dmd-transport.pl`.
Nie zakładaj, że lokalna baza lub checkout są aktualną produkcją.

Procesy CHAOS w PM2:

| Nazwa | Ecosystem |
| --- | --- |
| `chaos` | `ecosystem.web.config.js` |
| `chaos-territory-worker` | `ecosystem.territory-worker.config.js` |
| `chaos-ollama-worker` | `ecosystem.ollama-worker.config.js` |
| `chaos-narrative-publisher` | `ecosystem.narrative-publisher.config.js` |

Na tym serwerze są inne aplikacje. **Nie `pm2 stop all` / `delete all`.**
Zmiana wartości w ecosystemie i `pm2 reload chaos` to nie to samo co
świadome wczytanie nowych env. Przy rates trzeba zaktualizować oba procesy
web/territory. Przy narracji jawnie sprawdzić enable/selector przed reloadem.
Nie publikuj pełnych PM2 env, cookies, haseł ani treści prywatnych reportów.

### Nagrody: finalna konfiguracja

Po wykryciu fallbacków autor polecił stawki ×100. W kodzie/ekosystemach:

```text
CHAOS_GHOSTNETWORK_SIGNAL_NODE_HOLDER_RSP=800
CHAOS_GHOSTNETWORK_SIGNAL_CLOSER_RSP=2000
CHAOS_GHOSTNETWORK_SIGNAL_TERRITORY_RSP=800
CHAOS_GHOSTNETWORK_SIGNAL_TERRITORY_PRIMARY_MULTIPLIER=1.0
CHAOS_GHOSTNETWORK_SIGNAL_TERRITORY_CONFLICT_MULTIPLIER=1.0
CHAOS_GHOSTNETWORK_SIGNAL_TERRITORY_OVERLAP_MULTIPLIER=1.0
CHAOS_GHOSTNETWORK_SIGNAL_SHOW_DURATION_SECONDS=900
```

To parametry nowego naliczenia, nie polecenie przemnożenia starego rankingu.
Utrwalony plan/snapshot nie zmienia się od env reloadu. Nie myl tych stawek
z pulami `RANK_*_POOL` używanymi do score klanów. Pokazane kiedyś 364 RSP
to stare naliczenie, nie oczekiwany wynik nowego triggera.

### Ostatni restore/trigger — historia, NIE instrukcja powtórzenia

- Źródło restore: `pre-139-4-trigger-20260911T064618158666Z.sqlite3`.
- Przed triggerem: `ghostnetwork_0001 active`, 20 aktywnych części,
  19 `none`, 1 `contested`; zero lock snapshots/signals/rankings/shows.
- Safety backup: `data/backups/pre-140-final-restore-20260913T112329Z.sqlite3`.
  `quick_check: ok`, SHA256
  `5d7a79ec6d14ee78eae527ddf5ad29475ee7db123f854a63d47062a9c309e52f`.
- Autor zatrzymał cztery procesy CHAOS, wykonał backup/restore przez SQLite.
- `migrate_ghostsignal_scene_snapshot.py --apply`: schema change true;
  następny read-only przebieg: changed false, historical_backfill false.
- Preflight z `--strict --expect blocked --skip-runtime` potwierdzał bramkę,
  **nie** gotowość modelu/runtime. Historyczny warning dotyczył brakującego
  territory 450668; konflikt części `territory_conflict_5145c32c3e634c66`
  wymagał właściwego rozbrojenia, nie SQL-owego zniknięcia.
- Autor potwierdził właściwy świat/logowanie, potem zgodny z planem trigger.
- Show: `2026-09-13T11:37:50.773642+00:00` do
  `2026-09-13T11:52:50.773642+00:00`. Kolejny cykl/restart widoczny na screenach.

Pełna komenda ostatniego rozbrojenia nie jest dostępna w tym przekazaniu;
nie odtwarzaj jej z domysłu. Backupy o podobnych nazwach mają różne stany.
Nie wybieraj źródła restore wyłącznie po nazwie/pliku z najnowszą datą.

### Zasady działań operatorskich

Przed zmianą danych: potwierdzona baza, procesy zapisujące, spójny backup
SQLite, `quick_check`, hash, dry-run i expected counts; potem ograniczona
mutacja z receiptami i postflight. Nie kopiuj samotnego `.sqlite3` przy
aktywnym WAL i nie usuwaj ręcznie `-wal`/`-shm` dla „porządku”.
Nie kasuj cykli/rankingów/nagród, żeby otrzymać ładny preview.

Narzędzia endgame: `audit_ghostnetwork_endgame_preflight.py`,
`audit_ghostnetwork_endgame.py`, `monitor_138_2_signal_e2e.py`.
Numer 138 w nazwie monitora nie czyni go nieprzydatnym w nowym przebiegu.
`retire_narrative_backlog.py` wymaga kontrolowanego zakresu/dry-run; nie jest
uniwersalnym narzędziem kasowania niesprawnej narracji.

## 15. Testowanie i sposób pracy

Serwer zgłaszał **Node 12.22.9** i `Unexpected token '?'`. Kod kontrolera show
ładowany przez CommonJS test musi pozostać zgodny z tym parserem: nie wracają
`?.`/`??` tylko dlatego, że lokalny Node je rozumie. Nie zakładaj, że cały
legacy frontend ma identyczny target; sprawdź faktycznie testowany plik.

Testy Pythona izoluj od realnej bazy. Import `run.py` może inicjalizować
runtime; sam „test odczytu” nie gwarantuje bezpiecznego cwd. Stosuj istniejące
fixtures, temp cwd i konfigurację testową. W lokalnym środowisku uruchomienie
Python WindowsApps wymagało eskalacji narzędzia; to ograniczenie środowiska,
nie powód zmiany projektu.

Dobór bramek według obszaru, nie bezmyślne odpalanie wszystkiego:

| Zmiana | Szukaj testów / kontraktów |
| --- | --- |
| Profil/store/CAS | `test_hot_path_recovery`, `test_marked_target_hot_path`, `test_profile_*`, `test_territory_profile_projection_cas` |
| Sesje/restart | `test_session_generation_*`, `test_ghostnetwork_client_restart`, `tests/js/test_session_generation_isolation.js` |
| Operacja/plik/GX | Testy bounded finalization, inventory/market i raport 135.5; mały + ciężki profil |
| Mapa | `tests/js/test_map_target_hitbox.js`, map delta i scenariusz wielokrotnych skanów |
| Show | `ghost_signal_show_frontend`, recovery, manifest/montage/audio; `test_ghostnetwork_signal_show`, ranking i historical preview |
| Registry | `tests/js/test_signal_registry.js`, archive/ranking |
| Bug Reports | `tests/test_admin_bug_reports.py`, składnia skryptów, ręczny player/admin |
| Narracja | Producer/outbox/worker/output/lifecycle testy + właściwy event w audytach |

Najpierw odnajdź bieżący plik przez `rg --files tests`. Nazwy modułów powyżej
są także frazami wyszukiwania; nie wszystkie są jednym plikiem w root tests.
Po zmianie assetów sprawdź referencje/cache-bust we wszystkich wejściach,
nie tylko desktopie. `git diff --check` to kontrola formatu, nie test gameplayu.

Styl pracy autora: po polsku, konkret, małe checkpointy, „para” oznacza
desktop + portrait. Po akceptacji implementować; po „bez pary” nie generować
ponownie wizki. „Pass” zapisać z zakresem dowodu. Kontynuować autoryzowaną
pracę bez powtarzania pytań. Nie robić niezamówionego push/deploy/triggera.

## 16. Jak odnaleźć historię bez ponownego odkrywania projektu

Hierarchia:

1. Bieżące polecenie autora i aktualne instrukcje pracy.
2. Kod/schema/testy dla faktycznego zachowania; trwałe dane/receipts dla
   faktycznego przebiegu. Niezgodność kodu z kontraktem może być bugiem,
   nie powodem cichego skreślenia kontraktu.
3. Najnowszy konkretny dowód produkcyjny, z datą i zakresem.
4. Ten handoff + najnowszy journal + właściwy zamknięty artefakt/hardbugfix.
5. Wcześniejsze plany i rozmowy jako historia intencji.

Indeks: [doc/README](../README.md). Dziennik:
[project_journal](../history/project_journal.md). Starsza chronologia:
[game_play_180726](../history/game_play_180726.md).
Kontrakty: `doc/architecture`, `doc/gameplay`, `doc/systems`.
Wykonanie: `doc/sprints`; analiza regresji: `doc/hardbugfix`, `doc/audits`,
`doc/incidents`; operacje: `doc/runbooks`; pomysły: `doc/plans`.

Przykłady wyszukiwania (działają również z PowerShell):

```text
rg --files doc | rg '130_1|135_5|138|139|140|profile|session|delta'
rg -n -i 'bounce.?back|heavy.profile|operation_only|LKG' doc
rg -n 'finalize_operation_files_bounded|sync_session_profile' run.py
rg -n 'gonnaWinRequestQueue|operation_only' static/js/terminal.js
rg -n 'CHAOS_OLLAMA_WORKER_ENABLED' . -g 'ecosystem*.js'
git log --oneline --all -- doc/hardbugfix
git log -S 'operation_only' -- run.py
git log -G 'ghostsignal_request_is_exempt' -- run.py
```

PowerShell: używaj `Get-Content -Encoding UTF8`. Bez jawnego UTF-8 polskie
teksty mogą wyglądać na uszkodzone w terminalu, mimo poprawnego pliku.
`rg ecosystem*` jako literalna ścieżka nie rozwija się tak jak glob w bash;
używaj `rg … . -g 'ecosystem*.js'`. Ścieżki ze spacjami cytuj.

### Mapa etapów historycznych

| Etap | Czego tam szukać |
| --- | --- |
| Gameplay foundation / starsze sprinty | Typy celu, aplikacje, operacje, zasób/plik/rynek, pętla mapy |
| 56 i dalsze synchronizacje | Wersje scope, snapshot, delta, recovery; porównuj z aktualnym wdrożeniem |
| 130.10.1 | Runtime read uproszczony, target i `gonna-win`, shared init |
| 130.11–130.12 | Wiążąca bramka braku pełnych profili; izolacja/CAS i kolejne regresje |
| 131–135 | GhostNetwork Suite i mechaniki domeny |
| 135.1–135.6 | Canonical LLM transport, producenci, worker, publishery, controlled cutover |
| 135.5 hardbugfix | Ciężki profil, operacje/pliki/GX; nie myl z samym sprintem publisherów |
| 136–138.2 | Domain narrative bridge, generacja/walidacja, lifecycle i producer-backed E2E |
| 138 getway / hardbugfix | Marker/menu identity, cache signature i canvas bounds |
| 139 | Natychmiastowy show, gameplay lock, restart, boot/ACK |
| 140 + stylization .1–.10 | Manifest, 15 minut, finalna oprawa, video/audio i projekcje |
| Journal 13 IX / `96dec35` | Poprawki po show, TTL archive, login, Registry i admin Bug Reports |

Nazwy/daty nie zawsze idą liniowo. Przeczytaj końcowe sekcje PASS/closure,
sprawdź późniejsze sprostowanie w journalu i `git log -- <file>`.
Stary handoff 139–140 zawiera cenne szersze tło, ale jego „aktywny backlog”
jest historyczny. Trollu2 recovery jest zakończone, nie jest zadaniem na start.

## 17. Rejestr ryzyk dla kolejnego Control Loop

| Ryzyko | Objaw / bezpieczny kierunek |
| --- | --- |
| Ukryty full profile w helperze | Wolny zwykły request; trace całego chainu, metryki ≥35 MB |
| Sparse projection jako pełny profil | Znikające pola, nadpisanie; merge wyłącznie wskazanego scope |
| Odtworzenie legacy operations mirror | Nawrót wzrostu JSON i ciężkich zapisów; canonical operations/files |
| Brak finalizacji pliku | Operacja jest, pliku nie ma; bounded finalize/receipt, nie full hydrate |
| Fan-out audience | Zależność czasu od liczby graczy; indeks i bounded projection |
| Długi writer lock | Zacinanie niezwiązanych akcji; przygotowanie poza transakcją, CAS wewnątrz |
| Błędny cel mapy | Menu innego obiektu; DOM binding i lifecycle, nie tooltip/index |
| Spóźniony response | Cofnięty stan/inne konto; scope versions i session generation |
| Epoka po show | JSON zamiast loginu; zachować wąski wyjątek POST index, nie wyłączyć guardów |
| Env workerów | PM2 online bez publikacji; allowlist enable/selector i outbox trace |
| TTL w archiwum | Brak wpisów mimo records; historyczny cutoff i audience, bez reaktywacji |
| Stare preview | Poprawiony backend, stary HTML; regeneracja do nowej nazwy |
| Stare reward snapshot | Env nowe, kwoty stare; nie mutować historii, sprawdzić moment freeze |
| Media/RAF w tle | Stutter, przerwany dźwięk; cleanup, pojedynczy odsłuch, pomiar |
| Nieograniczone listy | Ciężki Registry/admin; bounded list, pełny dump iteracyjny |
| Prywatność reportów | GET/similar/dump widoczne graczom; serwerowy admin guard i testy odmowy |
| Pochopny restore | Utrata późniejszej gry; backup, właściwa lineage, jawna autoryzacja |

Nie ma dowodu, że wszystkie pozostałe ciężkie odczyty są obecnie problemem
produkcyjnym; są kandydatami do audytu. Nie ma też dowodu, że je wszystkie
usunięto. Zachowaj to rozróżnienie w następnym raporcie.

## 18. Gotowy tekst do wklejenia do nowego wątku

> Kontynuujemy CHAOS w tym repozytorium. Najpierw przeczytaj w całości
> `doc/runbooks/handoff_project_2026_09_14.md`, jego załącznik
> `doc/runbooks/handoff_hotpaths_2026_09_14.md`,
> `doc/architecture/profile_hot_path_contract_130_11_plus.md` i najnowszy
> `doc/history/project_journal.md`. Sprawdź Git i aktualne instrukcje repo.
> Sprinty 139–140 i stylizacja są wykonane; nie zaczynaj ich od nowa.
> Kolejny kierunek to Control Loop według artefaktów, które dostarczę.
> Ostatni feature to admin Bug Reports (`96dec35`). Osobno otwarta jest
> diagnostyka braku nowych publikacji narracyjnych po triggerze; historyczny
> odczyt archiwum został już naprawiony. Nie przywracaj ciężkich profili na
> hot path, legacy mirror operacji, starych błędów markerów ani luźniejszych
> guardów sesji. Nie wykonuj automatycznie restore/triggera/deployu.
> Zachowaj zatwierdzone decyzje i rozróżnienie testów, odbioru autora oraz
> rzeczy jeszcze niezweryfikowanych. Następnie zajmij się moim bieżącym zadaniem.
