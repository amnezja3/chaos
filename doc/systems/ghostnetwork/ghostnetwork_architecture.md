# GhostNetwork — architektura modułu strategicznego

## Status dokumentu

Dokument jest technicznym źródłem prawdy dla implementacji rozgrywki klanowej GhostNetwork w CHAOS.

Łączy zaakceptowany gameplay z architekturą kodu i stanowi podstawę do późniejszego podziału prac na sprinty. Nie zastępuje:

- `clans_machines.md`, który opisuje kanon, maszyny, części i zasady rozgrywki;
- `ABOUT_CHAOS.md`, który jest skróconym opisem świata dla gracza;
- dokumentacji istniejących systemów mapy, operacji, profilu i delt.

## Cel modułu

GhostNetwork ma obsłużyć globalny, powtarzalny cykl strategiczny:

```text
hakowanie markerów
→ odkrywanie 20 części
→ przypisywanie części do lokalizacji
→ walka o terytoria
→ aktywowanie modułów właściwych klanów
→ tworzenie połączeń na mapie
→ domknięcie GhostNetwork
→ wysłanie GhostSignalu
→ nagrody i historia
→ ewolucja GhostSystemu
→ kolejny cykl
```

Moduł musi działać obok istniejącej mapy, profili i mechaniki terytoriów. Nie może przenosić globalnego stanu świata do profilu gracza ani wymagać ciężkiego odpytywania całej bazy.

## Granice odpowiedzialności

### Profil gracza

Profil pozostaje źródłem prawdy o danych osobistych operatora:

- klanie;
- profesji;
- RSP;
- LVL;
- osiągnięciach;
- trwałej historii udziału.

Klan i profesja są wybierane podczas onboardingu i istnieją już przed uruchomieniem GhostNetwork.

Profil nie przechowuje:

- bieżących części;
- połączeń;
- stanu maszyny;
- postępu globalnego cyklu;
- właścicieli strategicznych węzłów;
- aktywności modułów;
- topologii GhostNetwork.

### GhostNetwork

GhostNetwork jest właścicielem globalnego stanu strategicznego:

- cyklu;
- zestawu 20 części;
- rezerwacji przed hackiem;
- przypisania części do markerów;
- powiązań części;
- aktywności modułów;
- wkładu graczy i klanów;
- GhostSignali;
- zmian wersji GhostSystemu.

### Terytoria

Istniejący system terytoriów pozostaje źródłem prawdy o kontroli lokalizacji.

GhostNetwork nie tworzy własnych granic. Odczytuje wynik istniejącej mechaniki i na tej podstawie ustala, czy część jest:

- neutralna;
- zablokowana przez obcy klan;
- aktywna we właściwym klanie;
- zamrożona w poprzednim stanie podczas konfliktu.

### Frontend

Frontend renderuje stan otrzymany z backendu. Nie losuje części, nie aktywuje modułów i nie rozstrzyga transmisji.

## Proponowany pakiet domenowy

Docelowa nazwa katalogu powinna zostać dopasowana do struktury projektu. Logiczny podział odpowiedzialności:

```text
gameplay/
└── ghostnetwork/
    ├── catalog
    ├── cycles
    ├── parts
    ├── drops
    ├── territory
    ├── topology
    ├── visibility
    ├── abilities
    ├── rewards
    ├── transmission
    ├── events
    ├── narrative
    └── repository
```

Moduły mogą zostać połączone w mniejszą liczbę plików na początku, ale ich odpowiedzialności nie powinny mieszać się w jednym kontrolerze lub w `run.py`.

## `catalog`

Wersjonowany katalog stałych definicji:

- czterech klanów;
- czterech maszyn;
- 20 profesji;
- 20 części;
- relacji profesja–część;
- definicji supermocy;
- kolorów i identyfikatorów;
- dozwolonych statusów;
- reguł topologii.

Definicje kanoniczne mogą być przechowywane w module konfiguracyjnym albo wersjonowanym pliku JSON. Nie wymagają tabeli, dopóki nie mają być edytowane przez panel administracyjny.

Identyfikatory techniczne muszą być stałe i niezależne od nazw wyświetlanych:

```text
virex
echo_freedom
phantom_mesh
sentinel_order

virex_oracle
ledger_nexus
broker
```

## `cycles`

Zarządza cyklem GhostNetwork:

- tworzy zestaw 20 części;
- przechowuje wersję GhostSystemu;
- pilnuje jednego aktywnego cyklu;
- zmienia stan cyklu;
- uruchamia stabilizację po transmisji;
- otwiera kolejny cykl.

Dozwolone statusy:

```text
preparing
active
transmitting
stabilizing
closed
```

## `parts`

Jest właścicielem prawdziwego stanu części:

- identyfikatora;
- klanu;
- maszyny;
- profesji;
- statusu;
- markera i współrzędnych;
- odkrywcy;
- stabilnego właściciela terytorium;
- dat aktywacji i wyłączenia.

Nie losuje części i nie oblicza geometrii terytorium.

## `drops`

Łączy normalne hakowanie markerów z pulą części.

Przepływ:

```text
oznaczenie celu
→ sprawdzenie aktywnego cyklu
→ możliwa rezerwacja obcej części
→ rozpoczęcie operacji
→ sukces: zatwierdzenie rezerwacji
→ brak sukcesu: zwolnienie rezerwacji
```

Rezerwacja jest niewidoczna i nie oznacza emisji części. Dopiero potwierdzony sukces hackowania przypisuje część do markera.

Gracz nigdy nie może wyemitować części należącej do własnego klanu.

## `territory`

Reaguje na zdarzenia istniejącego systemu terytoriów:

```text
territory.stabilized
territory.contested
territory.released
territory.owner_changed
```

Po zmianie sprawdza tylko części leżące w dotkniętym obszarze.

Reguły:

- obcy klan blokuje część;
- właściwy klan aktywuje część;
- brak stabilnego właściciela upublicznia część;
- konflikt zachowuje stan sprzed rozpoczęcia walki;
- zmiana następuje dopiero po stabilizacji granic.

## `topology`

Tworzy i przechowuje schemat połączeń cyklu.

Warunki:

- 20 węzłów;
- jeden zamknięty obwód;
- dokładnie dwa połączenia na część;
- brak połączeń pomiędzy częściami tego samego klanu;
- topologia nie zmienia się podczas cyklu;
- kolejna wersja może otrzymać inny schemat.

Stan wizualny linii jest wyliczany:

- część nieodkryta — brak linii;
- część odkryta i nieaktywna, sąsiad aktywny — połowa linii;
- obie części aktywne — pełna linia;
- utrata aktywności — zerwanie pełnego połączenia.

## `visibility`

Buduje projekcję stanu odpowiednią dla odbiorcy.

### Część neutralna

Wszyscy widzą:

- nazwę;
- klan;
- maszynę;
- profesję;
- supermoc;
- lokalizację.

### Część otoczona przez obcy klan

Właściciel terytorium widzi pełne dane. Pozostali widzą jedynie informację, że terytorium zawiera niezidentyfikowaną część.

### Część aktywna we właściwym klanie

Członkowie właściwego klanu widzą pełne dane. Pozostali widzą klan, lokalizację i aktywny status, ale nie nazwę części ani supermoc.

Ta sama projekcja musi być wykorzystywana przez mapę, API, BlackNet, Cyberner oraz outbox narracyjny.

## `abilities`

Supermoce nie są zapisywane jako trwałe uprawnienia profilu.

Uprawnienie jest wyliczane:

```text
klan gracza
+ profesja gracza
+ aktywna część właściwej maszyny
= aktywna supermoc
```

Utrata modułu natychmiast odbiera moc wszystkim graczom odpowiedniej profesji.

Rejestr efektów powinien wystawiać kontrakty używane przez istniejące systemy:

```text
hack_threshold_modifier
market_demand_preview
territory_defense_layer
operation_alert_delay
scan_detail_modifier
territory_repair
```

Nie należy rozrzucać warunków `if clan` i `if profession` po endpointach.

## `rewards`

Naliczanie:

- RSP za odkrycie;
- RSP za pierwsze otoczenie;
- RSP za aktywację;
- RSP za odbicie;
- RSP za czas stabilnego utrzymania;
- RSP za obronę;
- końcowej nagrody transmisji;
- reputacji klanowej;
- osiągnięć;
- historycznego udziału.

Nagrody strategiczne są większe niż nagrody regularnej rozgrywki i rozwijają LVL przez istniejący system RSP.

Każda nagroda musi być idempotentna.

## `transmission`

Uruchamia końcową sekwencję po aktywacji 20 stabilnych węzłów.

Kolejność backendowa:

1. Sprawdzenie warunków.
2. Atomowe zablokowanie cyklu.
3. Snapshot właścicieli i uczestników.
4. Utworzenie rekordu GhostSignalu.
5. Naliczenie nagród.
6. Publikacja zdarzenia transmisji.
7. Zużycie części i usunięcie połączeń.
8. Podniesienie wersji GhostSystemu.
9. Ustawienie wymaganego restartu.
10. Rozpoczęcie 15-minutowej stabilizacji.

Frontend odtwarza animację na podstawie zdarzenia. Błysk lub przeładowanie klienta nie jest źródłem prawdy o wysłaniu sygnału.

## `events`

Publikuje zdarzenia do obecnego systemu delt:

```text
ghost.part_discovered
ghost.part_contained
ghost.part_revealed
ghost.part_activated
ghost.part_deactivated
ghost.connection_changed
ghost.cycle_locked
ghost.signal_sent
ghost.version_changed
ghost.restart_required
```

Zdarzenia muszą posiadać identyfikator, wersję stanu i zakres odbiorców.

## `narrative`

Tworzy zatwierdzone fakty dla:

- deterministycznego BlackNetu;
- Cybernera;
- Radia;
- przyszłego demona Ollamy.

Nie generuje treści i nie odczytuje pełnych profili. Zapisuje do outboxa tylko fakty dozwolone dla wskazanej grupy odbiorców.

## `repository`

Izoluje zapis i odczyt danych GhostNetwork od warstwy domenowej.

Odpowiada za:

- transakcje;
- blokady cyklu;
- ograniczenia unikalności;
- idempotencję;
- odczyt snapshotów;
- zapis dziennika zdarzeń.

Warstwa domenowa nie powinna budować zapytań do bazy bezpośrednio.

## Model danych

Nazwy tabel są robocze. Ostateczne nazewnictwo należy dopasować do używanego magazynu danych i konwencji projektu.

### `ghost_cycles`

Jeden rekord na cykl:

```text
cycle_id
signal_number
ghostsystem_version
status
topology_seed
started_at
locked_at
transmitted_at
stabilization_until
closed_at
```

Tylko jeden cykl może znajdować się w stanie aktywnym.

### `ghost_parts`

Dokładnie 20 rekordów na cykl:

```text
part_id
cycle_id
part_code
clan_code
machine_code
profession_code
status
target_id
latitude
longitude
discovered_by
discovered_at
territory_owner_id
territory_clan
activated_at
deactivated_at
```

Ograniczenia:

- unikalne `cycle_id + part_code`;
- jedna lokalizacja części;
- brak dwóch części wyemitowanych przez ten sam marker w jednym cyklu.

### `ghost_part_reservations`

Tymczasowa rezerwacja przed hackiem:

```text
reservation_id
cycle_id
part_id
target_id
player_id
player_clan
status
reserved_at
expires_at
committed_at
```

### `ghost_connections`

Połączenia cyklu:

```text
connection_id
cycle_id
part_a_id
part_b_id
position_in_ring
```

Dwadzieścia części w zamkniętym obwodzie daje 20 połączeń.

### `ghost_part_events`

Niezmienny dziennik historii:

```text
event_id
cycle_id
part_id
event_type
player_id
clan_code
territory_id
created_at
payload
```

Jest podstawą nagród, narracji i audytu.

### `ghost_signals`

Jeden rekord na transmisję:

```text
signal_id
signal_number
cycle_id
source_version
target_year
status
outcome
integrity
recipient
sent_at
resolved_at
next_version
```

Stan początkowy:

```text
status = sent
outcome = pending
target_year = 2108
```

### `ghost_contributions`

Wkład graczy i klanów:

```text
contribution_id
cycle_id
signal_id
player_id
clan_code
contribution_type
part_id
territory_id
score
created_at
```

### `ghost_reward_ledger`

Idempotentne nagrody:

```text
reward_id
reward_key
cycle_id
player_id
reward_type
rsp_amount
level_progress
status
created_at
applied_at
```

`reward_key` musi być unikalny.

### `ghost_clan_reputation`

Agregat rankingu klanów:

```text
clan_code
total_reputation
signals_participated
parts_discovered
parts_activated
parts_recovered
territories_defended
updated_at
```

### `ghost_narrative_outbox`

Zatwierdzone fakty dla mediów i przyszłej Ollamy:

```text
outbox_id
event_id
audience_scope
audience_clan
medium
truth_class
facts_json
status
created_at
processed_at
```

## Statusy części

Minimalny katalog statusów domenowych:

```text
pooled
reserved
public
contained
active
contested
consumed
```

`contested` nie musi zastępować faktycznego stanu części. Może być informacją pomocniczą, podczas gdy część zachowuje stan sprzed konfliktu.

## Przepływ części od markera do transmisji

```text
gracz oznacza marker
        ↓
drops sprawdza aktywny cykl
        ↓
losuje możliwość części obcego klanu
        ↓
tworzy czasową rezerwację
        ↓
gracz kończy hack
        ↓
rezerwacja zostaje zatwierdzona
        ↓
część zostaje przypisana do markera
        ↓
ghost.part_discovered
        ↓
territory określa stabilnego właściciela
        ↓
obcy klan: contained
właściwy klan: active
        ↓
topology przelicza widoczne połączenia
        ↓
20 aktywnych części
        ↓
transmission blokuje cykl
        ↓
GhostSignal + nagrody + restart + nowa wersja
```

## Integracja z obecnym kodem

### Onboarding i profil

Onboarding zapisuje:

```text
profile.clan
profile.profession
```

Profil otrzymuje wyłącznie trwałe skutki GhostNetwork:

- RSP;
- LVL;
- osiągnięcia;
- historię udziału;
- liczbę GhostSignali.

### Oznaczenie celu

Istniejąca obsługa oznaczenia celu wywołuje lekki hook domenowy:

```text
ghostnetwork.on_target_aimed(player, target)
```

Hook może utworzyć niewidoczną rezerwację, ale nie wymaga pełnej synchronizacji profilu.

### Zakończenie hackowania

Potwierdzony sukces operacji wywołuje:

```text
ghostnetwork.on_target_hacked(player, target, operation)
```

W tym miejscu rezerwacja jest zatwierdzana i marker emituje część.

### Terytoria

Po przeliczeniu terytorium istniejący system publikuje zmianę stabilnego stanu. GhostNetwork sprawdza tylko części znajdujące się w obszarze zmiany.

### System delt

GhostNetwork otrzymuje osobny scope:

```text
ghostnetwork
```

Snapshot zawiera:

- bieżący cykl;
- wersję GhostSystemu;
- części widoczne dla odbiorcy;
- pełne i połowiczne połączenia;
- stan transmisji;
- wymóg restartu.

Delty aktualizują pojedyncze markery, połączenia i stan cyklu.

GhostNetwork nie powinien używać:

- pełnego `/api/profile` do synchronizacji świata;
- `sync_session_profile()`;
- ciężkiego pollera;
- przeliczania wszystkich terytoriów przy każdym odświeżeniu.

### Frontend mapy

Warstwa frontowa powinna zostać wydzielona, przykładowo:

```text
static/js/map/ghostnetwork.js
```

Odpowiada za:

- markery części;
- oznaczenia terytoriów przechowujących części;
- aktywne węzły;
- połowy linii;
- pełne linie;
- szczegóły dostępne po kliknięciu;
- warstwę historii;
- animację transmisji;
- czarny ekran;
- obsługę restartu.

Nie podejmuje decyzji domenowych.

### BlackNet

BlackNet otrzymuje deterministyczne sygnały z zatwierdzonych zdarzeń GhostNetwork. Później sygnały `ollama_enriched` mogą być przeplatane z automatycznymi publikacjami.

### Cyberner

Cyberner otrzymuje:

- globalne komunikaty systemowe;
- komunikaty klanowe;
- informacje o transmisji;
- odpowiedzi z 2108;
- kanał rozmów graczy wykorzystywany do koordynacji.

### Radio

Radio reaguje na transmisję krótkim komunikatem alarmowym tylko wtedy, gdy jest uruchomione. Po komunikacie wraca do poprzedniego trybu odtwarzania.

### Ollama

Ollama nie otrzymuje bezpośredniego dostępu do tabel ani pełnych profili. Konsumuje zatwierdzone fakty z outboxa i zwraca ustrukturyzowane treści, które muszą przejść walidację przed publikacją.

## Spójność i współbieżność

Operacje wymagające transakcji:

- rezerwacja części;
- zatwierdzenie emisji;
- zmiana stabilnego stanu części;
- zablokowanie cyklu;
- utworzenie GhostSignalu;
- zapis wkładu;
- przyznanie nagród;
- zamknięcie cyklu i podniesienie wersji.

System musi chronić się przed:

- wyemitowaniem dwóch kopii tej samej części;
- zatwierdzeniem jednej rezerwacji przez dwie operacje;
- dwukrotną transmisją tego samego cyklu;
- podwójnym naliczeniem nagrody;
- zmianą części po zablokowaniu cyklu;
- ujawnieniem danych poza zakresem odbiorcy.

## Snapshot i recovery

Snapshot GhostNetwork powinien umożliwiać odbudowanie frontendu po utracie delt.

Powinien zawierać co najmniej:

- `cycle_id`;
- wersję stanu;
- status cyklu;
- wersję GhostSystemu;
- widoczne części;
- widoczne połączenia;
- wymóg restartu;
- czas końca stabilizacji.

Recovery odświeża wyłącznie scope GhostNetwork i zależne warstwy mapy. Nie wymaga pełnego profilu.

## Obserwowalność i audyt

Należy logować:

- utworzenie cyklu;
- rezerwacje i ich wygaśnięcia;
- emisje części;
- zmiany właściciela;
- aktywacje i wyłączenia;
- konflikty;
- zablokowanie cyklu;
- transmisję;
- nagrody;
- zmianę wersji;
- błędy projekcji widoczności;
- błędy publikacji zdarzeń.

Każdy wpis powinien posiadać `cycle_id`, a jeśli dotyczy części również `part_id`.

## Reguły niefunkcjonalne

1. Brak ciężkiego pollera.
2. Brak pełnego profilu na potrzeby aktualizacji mapy.
3. Punktowe przeliczanie części w zmienionym obszarze.
4. Idempotentne handlery zdarzeń.
5. Atomowe zamknięcie cyklu.
6. Jedna wspólna projekcja widoczności.
7. Backend jako źródło prawdy.
8. Możliwość odtworzenia stanu z bazy i dziennika zdarzeń.
9. Brak wpływu błędu Ollamy na mechanikę gry.
10. Zachowanie zgodności z istniejącym systemem delt i recovery.

## Świadomie poza tym dokumentem

Dokument nie ustala jeszcze:

- dokładnych wartości procentowych supermocy;
- czasów cooldownów;
- liczbowych progów RSP;
- prawdopodobieństwa emisji części;
- algorytmu wykrywania powiązanych multikont;
- finalnego wyglądu markerów i linii;
- dokładnej kolejności sprintów;
- momentu uruchomienia Ollamy;
- panelu administracyjnego GhostNetwork.

Te decyzje powinny zostać rozpisane w odpowiednich sprintach bez zmiany granic architektury.

## Decyzje architektoniczne

1. GhostNetwork jest globalnym modułem świata, nie częścią profilu.
2. Markery mogą emitować części, ale dopiero po potwierdzonym hacku.
3. Rezerwacja części przed hackiem jest niewidoczna i czasowa.
4. Każdy cykl ma dokładnie 20 unikalnych części.
5. Terytorium pozostaje źródłem prawdy o kontroli lokalizacji.
6. Konflikt zamraża poprzedni stan części do stabilizacji granic.
7. Supermoce są wyliczane z aktywnych modułów.
8. Topologia jest stała podczas cyklu.
9. Nagrody korzystają z idempotentnego ledgeru.
10. Transmisję rozstrzyga backend.
11. Frontend renderuje projekcję przeznaczoną dla odbiorcy.
12. Wszystkie media korzystają z jednego strumienia zatwierdzonych faktów.
13. Ollama nie zmienia stanu gry.
14. Snapshot i delty posiadają osobny scope GhostNetwork.
15. Dokument jest podstawą do późniejszego podziału implementacji na sprinty.

## Runtime Foundation (Sprint 130.9)

Start procesu webowego i workera nie tworzy ani nie naprawia cyklu. Stan
runtime jest sprawdzany read-only przez `GhostNetworkService.get_runtime_readiness()`;
mutujący bootstrap wykonuje operator przez
`python tools/ghostnetwork_runtime.py bootstrap --apply`. Operacja korzysta z
istniejącej transakcji i ograniczeń repository, więc równoległe wywołania
prowadzą do jednego aktywnego cyklu z 20 częściami i poprawną topologią.

Bezpieczne wartości domyślne to `CHAOS_GHOSTNETWORK_DROPS_ENABLED=false` oraz
`CHAOS_GHOSTNETWORK_DROP_CHANCE=0`. Włączenie dropów z chance spoza `(0, 1]`
daje `NOT READY`; kod nie wybiera wartości balansowej za operatora.

Tabela `ghost_pipeline_telemetry` przechowuje tylko agregat per `cycle_id`, fazę
`aim|capture` i kod wyniku wraz z licznikiem oraz czasem ostatniego wystąpienia.
Nie zapisuje `part_id`, target payloadu, wyniku rolla ani topologii i nie rośnie
o jeden rekord na każdy aim. Błąd zapisu telemetrii nie blokuje gameplay hooka.

Runtime readiness jest osobnym kontraktem od readiness archiwum/endgame. Pola
`pending_effects` i `unreconciled_effects` pochodzą z trwałego capture outboxu.

## Runtime integration po refaktorze 130

`ghost_capture_effects` rozdziela kanoniczny capture od wykonania discovery.
Normalna ścieżka zapisuje effect po committed capture i wykonuje go od razu;
operator `reconcile/drain` dodatkowo odtwarza brakujący effect z aktywnej
reservation oraz aktualnego `TerritoryTargetOwnershipStore`/`captured_targets`.
Idempotencję zapewniają capture key, unikalny target części, dedupe eventu,
contribution ledger i reward key.

Źródłem prawdy terytorium pozostają post-130 ownership CAS, obszary, conflicts,
engagements i reconciliation. Bridge działa przy publication boundaries
`record_territory_areas_delta()` oraz `record_territory_conflict_delta()`.
GhostNetwork otrzymuje tylko kanoniczną projekcję polygon/owner/clan/version i
nie przechowuje alternatywnej geometrii świata. Pełna publikacja obszarów jest
również mechanizmem release/recovery dla części, których poprzednie terytorium
zniknęło.

Każda zmiana lifecycle uruchamia istniejący module state i ledger nagród.
Osiągnięcie 20/20 na tej samej granicy prowadzi przez atomowy closure do
transmission/narrative/archive, bez automatycznego utworzenia kolejnego cyklu.
