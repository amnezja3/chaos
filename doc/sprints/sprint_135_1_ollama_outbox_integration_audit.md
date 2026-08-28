# Sprint 135.1 - audit in preparation for Ollama Outbox

Data audytu: 2026-08-27.

Status:

`SPRINT 135.1 - COMPLETE`

Nastepna bramka: `READY FOR SPRINT 135.2`.

Sprint 135.1 jest audytem i projektem kontraktu. Nie uruchamia Ollamy, nie
zmienia runtime, bazy ani procesow PM2. Jego celem jest odzyskanie odlozonych
planow, zinwentaryzowanie wszystkich istniejacych wpietych miejsc oraz
wyznaczenie jednej drogi implementacji dla Sprintow 135.2+.

## 1. Odzyskane zakresy historyczne

Odnaleziono dwa osobne zakresy. Ich status historyczny nie byl taki sam.

### 1.1 Sprint 84 - formalnie zamrozony

`Sprint 84 - Ollama Enriched Signal Ingest + Mixed Feed` ma w
`doc/systems/blacknet/blacknet.md` status `frozen / postponed`. Zamrozenie bylo
swiadome: Sprint 83 dostarczyl bezpieczny eksport, ale nie istnial jeszcze
stabilny kontrakt odpowiedzi modelu, daemonowy feedback loop, walidacja
kandydatow, quarantine ani bezpieczny mixed feed.

Odzyskany zakres Sprintu 84 obejmuje:

- rejestr rodzin sygnalow i wersjonowany schema outputu;
- kontrolowany inbox odpowiedzi Ollamy;
- walidacje faktow, audience, truth class i CTA;
- quarantine odpowiedzi niepoprawnych;
- publikacje zaakceptowanych kandydatow jako `ollama_enriched` obok sygnalow
  deterministycznych, bez zastapienia tych ostatnich.

Zrodla: `doc/systems/blacknet/blacknet.md` oraz
`doc/systems/blacknet/blacknet_ollama_outbox.md`.

### 1.2 BlackNet AI Ecosystem (Sprint 21+) - swiadomie odlozony

Drugi zakres nie ma osobnego numeru sprintu. Dokument nazywa go
`Backlog - Blacknet AI Ecosystem (Sprint 21+)` i jawnie nakazuje wrocic do niego
dopiero po zamknieciu podstawowej petli gameplayu Sprintow 1-20. Nie byl to
technicznie zamrozony sprint, lecz funkcja swiadomie pominieta do etapu, w
ktorym bezpieczna integracja z lokalnym LLM bedzie mozliwa.

Odzyskany zakres obejmuje zywy ekosystem informacyjny:

- Ghost News;
- Ghost Forums;
- Ghost Jobs;
- Ghost Market Analyst;
- Ghost Intelligence;
- lekkich agentow publikujacych na podstawie zatwierdzonych faktow swiata.

Nie nadajemy temu zakresowi nowego historycznego numeru. Sprinty 135.2+ sa jego
kontrolowana, wspolczesna realizacja.

### 1.3 Zakresy, ktorych nie nalezy mylic z odzyskanymi planami

- Sprint 60.6 byl odlozonym Async Operation Runnerem i nie jest planem Ollamy.
- Sprint 129 jest ukonczonym fundamentem narracyjnego outboxa, nie zamrozonym
  sprintem.
- Stary roadmap 136-138 (`event bridge`, `pierwszy worker`, `publish to
  BlackNet`) opisuje fragment tej samej pracy. Zostaje zastapiony bardziej
  kompletnym podzialem 135.2+ z tego audytu, a nie implementowany rownolegle.

## 2. Obowiazujaca metodyka komunikacji

Docelowy przeplyw jest eventowy:

```text
canonical GhostSystem/game event
lub autoryzowane polecenie z zainstalowanej aplikacji
        |
        v
backend fact + visibility projection
        |
        v
canonical Ollama Outbox
        |
        v
local Ollama worker -> Ollama LLM
        |
        v
canonical Ollama Inbox candidate
        |
        v
schema/fact/audience/CTA validator + quarantine
        |
        v
publisher router
        |
        +--> BlackNet
        +--> Googleplex News
        +--> Cyberner / AI Central / odpowiedzi z 2108
        +--> opcjonalnie BlackNet Radio
```

Ollama jest demonem narracyjnym, nie administratorem swiata. Backend ustala
fakty, wynik mechaniczny, nadawce, autentycznosc, audience oraz dostepne CTA.
Model moze dobierac jezyk, ton, emocje i interpretacje w granicach pakietu.
Nie moze tworzyc ani modyfikowac gameplay state, profilu, walletu, czesci GN,
terytoriow, operacji, nagrod ani wyniku GhostSignalu.

Kontrakt zachowuje dyrektywy z `doc/overview/clans_machines.md`:

- model nie dostaje bezposredniego dostepu do bazy ani profili;
- dostaje tylko audience-projected fakty, ktore wolno opublikowac danemu
  odbiorcy;
- zwraca ustrukturyzowany JSON, nigdy tekst publikowany bez walidacji;
- klasy prawdziwosci pozostaja jawne: `canonical`, `interpretation`, `rumor`,
  `propaganda`, `narrative_deception`;
- `fact_refs` musza wskazywac fakty z konkretnego taska;
- CTA moze pochodzic tylko z allowlisty taska;
- odpowiedz z 2108 ma wynik i autentycznosc wybrane przez backend; Ollama
  jedynie formuluje komunikat.

## 3. Aktualny model i call chainy

### 3.1 Plikowy BlackNet Ollama outbox - Sprint 83

Aktualny chain:

```text
blacknet_world_facts + blacknet_world_signals
-> build_blacknet_ollama_outbox()
-> validate_blacknet_ollama_outbox()
-> instance/blacknet_ollama_outbox/<digest_id>.json
-> admin/dev GET/POST status endpoints
```

Implementacja w `run.py` zapisuje pliki atomowo przez plik tymczasowy i
`os.replace`. Jest bezpiecznym, ograniczonym eksportem diagnostycznym. Pole
`ollama_executed=false` potwierdza, ze nie ma workera, inboxu ani publikacji
wyniku modelu.

Werdykt: ten magazyn nie moze zostac druga kolejka runtime. Po konwergencji ma
byc jednokierunkowym eksporterem/adapterem diagnostycznym z kolejki
kanonicznej. Worker nie moze claimowac plikow jako source of truth.

### 3.2 SQLite GhostNetwork narrative outbox - Sprint 129

Aktualny chain:

```text
GhostNetwork canonical event
-> GhostNarrativePublisher.publish_domain_event()
-> audience facts + allowed actions
-> ghost_narrative_outbox
```

`ghostnetwork/repository.py` zapewnia trwaly SQLite store, unikalny
`dedupe_key`, status oraz atomowy zapis. `ghostnetwork/narrative.py` buduje
bezpieczne facts, model input package i ma pierwszy walidator outputu.

Obecne luki:

- brak atomowego claim/lease dla workera;
- brak realnego klienta Ollamy;
- brak osobnego, trwalego inboxu i quarantine;
- brak publication receipts oraz publisherow do mediow;
- audience builder zwraca obecnie tylko `public`;
- `medium=ollama_outbox` miesza procesor z docelowym medium;
- zestaw event producers jest ograniczony;
- statusy nie opisuja wszystkich crash/retry boundaries.

Werdykt: ten store jest najlepsza istniejaca baza dla jednego kanonicznego
outboxa. Nalezy go rozszerzyc addytywnie, a nie tworzyc trzeci system.

### 3.3 Powierzchnie docelowe

| Powierzchnia | Stan obecny | Luka do 135.2+ |
| --- | --- | --- |
| BlackNet | deterministyczne facts/signals, CTA i plikowy export istnieja | validated mixed feed `ollama_enriched` i receipt publikacji |
| Googleplex News | brak odrebnej kanonicznej powierzchni runtime o tej nazwie | zdefiniowac read model, audience i publisher; nie mylic z katalogiem sklepu |
| Cyberner | istnieja kanaly i zrodlo `AI Central` | kanoniczny kanal AGI/2108, inbox publication i dedupe |
| BlackNet Radio | kontrakt narracyjny istnieje jako medium | pozostaje opcjonalnym adapterem po podstawowych trzech odbiorcach |

Brak Googleplex News jest luka implementacyjna, nie blockerem audytu. Przed
publisherem trzeba zatwierdzic minimalny produkt: feed news wewnatrz Googleplex
albo jednoznacznie nazwany launcher do istniejacego feedu. Nie wolno po cichu
publikowac newsow do katalogu produktow.

## 4. Jeden source of truth

Wiazaca decyzja 135.1:

> Jedna fizyczna, trwala kolejka backendowa jest source of truth dla zadan
> Ollamy. Pliki, cache, UI i model nie sa kolejka ani zrodlem prawdy.

Rozszerzamy semantycznie `ghost_narrative_outbox` do wspolnego Ollama narrative
task store. Fizyczna nazwa tabeli moze pozostac w pierwszej addytywnej migracji,
aby ograniczyc ryzyko. Nowe pola musza rozdzielic:

```text
processor = ollama
target_medium = blacknet | googleplex_news | cyberner | radio
```

Nie wolno utrzymywac `ollama_outbox` jako rownorzednego medium. Legacy BlackNet
file export moze byc generowany tylko z kanonicznego rekordu i nie moze zapisac
niezaleznego statusu przetwarzania.

## 5. Kontrakt Ollama Outbox

Minimalny rekord taska:

```text
task_id / outbox_id
schema_version
source_scope              ghostnetwork | blacknet_world | installed_app | system_schedule
source_event_id
source_receipt_id
source_app_id
canon_version
world/state/ghostsystem_version
processor                 ollama
target_medium
audience_scope
audience_clan
audience_owner
truth_class_policy
facts[]                   juz po visibility projection
allowed_actions[]
editorial_profile
narrative_context         bounded, bez pelnej historii
output_schema_version
prompt_version
model_policy
priority
dedupe_key
status
attempt_count
claimed_by / claimed_at / lease_until
next_attempt_at
last_error_code
created_at / updated_at / completed_at
```

Wiążąca decyzja Sprintu 135.2: `dedupe_key` obejmuje source identity, audience
i `target_medium`. Wersje prompt/schema/model policy oraz wariant są zapisane w
tasku, ale nie tworzą drugiego taska dla tego samego eventu. Jawny replay wymaga
nowego source receipt. Jeden task obsługuje jedną audience i jedno medium. To
zapobiega przeciekom podczas fan-outu i pozwala niezależnie ponawiać publisher.

Lifecycle outboxa:

```text
READY -> CLAIMED -> PROCESSING -> MODEL_COMPLETED
READY/PROCESSING -> RETRY_WAIT -> READY
PROCESSING + expired lease -> READY
MODEL_COMPLETED -> INBOX_RECORDED
repeated terminal failure -> DEAD_LETTER
```

Claim jest atomowym compare-and-swap z lease. Tylko wlasciciel aktualnego lease
moze zapisac wynik taska. Spadniecie workera nie moze zgubic taska ani utworzyc
dwoch kandydatow. Timeout nie moze blokowac gameplayu.

## 6. Kontrakt Ollama Inbox

Inbox przechowuje kandydat modelu, nie stan swiata:

```text
candidate_id
task_id / outbox_id
output_schema_version
model_name / model_version
prompt_version
target_medium
audience identity copied from task
source / truth_class / title / body / tone
fact_refs[]
cta_action + cta_payload
bounded_raw_output / output_hash
validation_status
validation_errors[]
quarantine_reason
published_receipt_id / published_at
created_at
```

Walidator musi sprawdzic schema, rozmiar, audience equality, dozwolona truth
class, kompletne i znane `fact_refs`, CTA oraz brak niedozwolonych danych i URL.
Model nie moze podniesc poziomu visibility ani wiarygodnosci. Kandydat
niepoprawny trafia do quarantine i nie generuje mutacji ani publikacji.

Publikacja jest idempotentna po `candidate_id + target_medium + audience`.
Awaria po publikacji, ale przed potwierdzeniem, jest domykana przez ten sam
receipt, a nie przez drugi wpis.

## 7. Dedykowana aplikacja instalowana z Googleplex

Outbox przyjmie zadanie od dedykowanej aplikacji, ale aplikacja nie dostanie
bezposredniego zapisu do tabeli ani dowolnego promptu.

Chain:

```text
installed Googleplex app action
-> authenticated backend endpoint/action
-> active session-generation guard
-> bounded PlayerInventoryStore entitlement check
-> app action receipt/dedupe
-> approved template + backend-resolved facts/audience
-> canonical Ollama Outbox task
-> immediate accepted receipt to UI
```

Wymagane invariants:

- app musi byc kanonicznie zainstalowana i aktywna;
- zadnych full-profile read/write w tym hot pathie;
- retry tej samej akcji zwraca ten sam receipt/task;
- request nie przyjmuje arbitralnego system promptu, modelu, zewnetrznego URL,
  audience, faktow, CTA ani gameplay mutation;
- backend wybiera szablon, fakty i visibility projection;
- domyslnym wynikiem aplikacji jest prywatny owner-scoped komunikat w
  `cyberner` (surface AGI-2108); publikacja publiczna wymaga osobnej polityki;
- endpoint sprawdza session generation ponownie przed zapisem taska;
- rate limit, quota i maksymalny rozmiar sa per konto oraz per app action;
- request konczy sie po zapisie taska i nie czeka synchronicznie na LLM.

## 8. Invariants bezpieczenstwa i wydajnosci

1. Gameplay jest fail-open wobec narracji: awaria Ollamy nie cofa zdarzenia gry.
2. Narracja jest fail-closed wobec publikacji: niewalidowany output nie trafia do
   graczy.
3. Fakty sa audience-projected przed enqueue; worker nie wykonuje visibility.
4. Publiczny task nie zawiera owner-only, hidden parts, hidden topology, sesji,
   maili ani profilu.
5. Worker nie czyta bazy gameplayowej poza API/repository kolejki.
6. Brak `list_profiles`, pelnego `get_profile`, `profile_bytes` i fan-outu przez
   profile. Identity/clan resolve korzysta z bounded indeksu.
7. Jedno zdarzenie nie moze blokowac requestu gracza ani territory workera.
8. Context, output, czas modelu, retry i liczba rownoleglych taskow sa bounded.
9. Brak odpowiedzi modelu uruchamia deterministyczny fallback tylko tam, gdzie
   medium go wymaga.
10. Wszystkie granice crashu maja receipt/dedupe i sa obserwowalne bez logowania
    wrazliwych payloadow.

## 9. Macierz testowa przyszlej implementacji

### Queue i worker

- ten sam event/audience/medium enqueue dwa razy -> jeden task;
- dwa workery claimuja rownoczesnie -> jeden lease owner;
- worker pada po claim -> lease expiry i jeden skuteczny retry;
- model timeout/invalid JSON -> retry albo quarantine, gameplay bez zmian;
- crash po inbox insert -> brak drugiego candidate;
- crash po publikacji -> ten sam publication receipt, brak duplikatu wpisu.

### Visibility i canon

- public, clan i owner task zawieraja tylko dozwolone fakty;
- hidden part/topology nie przecieka przez prompt, raw output ani log;
- nieznany `fact_ref`, CTA lub truth class -> quarantine;
- model probuje zmienic gameplay outcome -> reject;
- odpowiedz 2108 zachowuje canonical sender/authenticity/outcome backendu.

### Media

- accepted candidate trafia dokladnie raz do BlackNet;
- mixed feed zachowuje sygnaly deterministyczne i oznacza `ollama_enriched`;
- Googleplex News i Cyberner AGI-2108 zachowuja audience i receipt;
- awaria jednego publishera nie powiela ani nie blokuje pozostalych;
- brak Ollamy daje przewidziany fallback bez pustego lub technicznego wpisu.

### Installed app

- brak instalacji -> fail-closed, zero taskow;
- stara session generation -> 409/controlled session flow, zero taskow;
- retry z tym samym receipt -> jeden task;
- arbitralny prompt/audience/CTA/fact -> reject;
- task prywatny nie pojawia sie w publicznym BlackNecie;
- syntetyczny profil 35 MB -> zero full-profile read/write/bytes.

## 10. Roadmap Sprintow 135.2+

Kolejne sprinty sa rozdzielone twardymi granicami. Nie wolno przyspieszac
integracji przez podpinanie Ollamy w 135.2 ani producentow w 135.2. Kazdy etap
zamyka jedna warstwe i dopiero potem odblokowuje nastepna.

### Sprint 135.2 - canonical LLM task transport, jeszcze bez LLM

Pełna specyfikacja:
`doc/sprints/sprint_135_2_canonical_llm_task_transport.md`.

Cel:

> Zbudowac niezawodny transport taskow LLM, jeszcze bez LLM.

Sprint zamienia istniejacy `ghost_narrative_outbox` ze Sprintu 129 w jedna
porzadna, kanoniczna kolejke dla calego GhostSystemu. To jest praca nad
persistence, concurrency i recovery, nie integracja modelu.

Zakres schema/store:

- addytywnie rozszerzyc rekord o `source_scope`, source event/receipt/app,
  `processor=ollama`, `target_medium`, audience identity, prompt/schema/model
  policy versions, priority i dopracowany `dedupe_key`;
- dodac `attempt_count`, `claimed_by`, `claimed_at`, `lease_until`,
  `next_attempt_at`, `last_error_code`, `created_at`, `updated_at` i terminalny
  timestamp;
- dodac indeksy wspierajace unikalny dedupe, pobranie kolejnego gotowego taska,
  odzyskanie wygaslego lease i bounded diagnostyke statusow;
- zachowac addytywna migracje i kompatybilny odczyt rekordow Sprintu 129;
- nie tworzyc drugiej tabeli/kolejki jako rownorzednego source of truth.

Zakres API repository/service:

```text
enqueue
-> atomic claim
-> lease
-> renew
-> complete
   lub retry_wait -> ready
   lub dead_letter
```

- `enqueue` zwraca istniejacy task przy tym samym semantycznym dedupe;
- `claim` atomowo wybiera task i nadaje dokladnie jednego lease ownera;
- `renew`, `complete`, `retry` i `dead_letter` sa CAS-safe wobec ownera i
  aktualnego lease;
- task z wygaslym lease wraca do kolejki bez utraty source identity i bez
  utworzenia kopii;
- retry ma bounded attempts oraz deterministyczny backoff zapisany w rekordzie;
- terminalny task nie moze zostac ponownie claimowany;
- status transition jest walidowany centralnie, nie przez dowolny update pola.

Legacy BlackNet outbox:

- plik powstaje wylacznie jako diagnostyczny eksport wybranego rekordu
  kanonicznej kolejki;
- eksport jest jednokierunkowy: DB -> plik;
- plik nie ma niezaleznego lifecycle, nie moze byc claimowany i nie moze
  zmieniac statusu taska;
- dotychczasowe endpointy admin/dev maja czytac canonical task albo jego
  eksport, ale nie tworzyc alternatywnej kolejki;
- eksport musi jawnie raportowac `diagnostic_export=true` oraz brak wykonania
  modelu.

Obowiazkowe regresje 135.2:

```text
ten sam event + audience + target_medium
-> dokladnie 1 task

dwa rownolegle workery/proby claim
-> dokladnie 1 lease owner

claim -> crash przed complete -> lease expires
-> ten sam task ponownie dostepny
-> task nie jest zgubiony
-> nie powstaje duplikat

stary lease owner po przejeciu taska przez nowego ownera
-> renew/complete/retry odrzucone

complete -> ponowny claim
-> brak taska

retry do limitu
-> jeden task przechodzi do dead_letter

concurrent enqueue tego samego dedupe
-> jeden rekord, ten sam task_id

diagnostic export
-> odzwierciedla canonical task
-> nie zmienia jego lifecycle
```

Poza zakresem 135.2:

- brak polaczenia HTTP z Ollama;
- brak procesu Ollama worker;
- brak Inboxu i odpowiedzi modelu;
- brak nowych producentow gameplayowych;
- brak endpointu dedykowanej aplikacji Googleplex;
- brak publikacji do BlackNet, Googleplex News, Cybernera i Radia;
- brak prompt engineeringu poza przechowywaniem identyfikatorow wersji.

Exit gate:

`ONE CANONICAL QUEUE / EXACTLY ONE TASK / EXACTLY ONE ACTIVE LEASE / CRASH RECOVERABLE`

### Sprint 135.3 - event producers i Googleplex app ingress, nadal bez LLM

Pełna specyfikacja:
`doc/sprints/sprint_135_3_llm_event_producers_googleplex_ingress.md`.

- producenci zatwierdzonych GhostNetwork/GhostSignal oraz BlackNet world facts;
- audience projection przed enqueue;
- bounded endpoint/action dla dedykowanej zainstalowanej aplikacji;
- entitlement, session/precommit guard, quota i receipt/dedupe;
- telemetry source event -> task.

Poza zakresem pozostaja klient Ollamy, Inbox i publikacja tekstu modelu.

Exit gate: wszystkie zrodla tworza bezpieczne taski, ale nadal bez Ollamy.

### Sprint 135.4 - pierwszy realny Ollama worker i canonical Inbox

Pełna specyfikacja:
`doc/sprints/sprint_135_4_ollama_worker_canonical_inbox.md`.

- osobny lokalny worker ecosystem;
- klient Ollamy z timeoutem, bounded context i structured JSON;
- trwaly inbox, validator, quarantine, retry i dead letter;
- dry-run bez publikacji;
- pelny audit trail model/prompt/facts/output hash.

Worker korzysta wylacznie z transportu i lease contractu zakonczonego w 135.2.
Nie dostaje specjalnej sciezki omijajacej kolejke. W tym sprincie zaakceptowany
kandydat pozostaje w Inboxie; nie jest jeszcze publikowany graczom.

Exit gate: model przetwarza task end-to-end do zaakceptowanego albo
odrzuconego kandydata bez wplywu na gameplay.

### Sprint 135.4.1 - Googleplex Home and News foundation

Pełna specyfikacja:
`doc/sprints/sprint_135_4_1_googleplex_home_news_foundation.md`.

- projekt i implementacja Googleplex Home;
- wydzielony, audience-projected News read surface;
- pełna izolacja Home/News/Catalog/GX/BlackNet state;
- responsywny layout z jednym scrollem;
- brak publikacji treści Ollamy.

Exit gate: gotowa powierzchnia News, nadal z `model publication = 0`.

### Sprint 135.4.2 - purchasable Googleplex LLM tool

Pełna specyfikacja:
`doc/sprints/sprint_135_4_2_googleplex_purchasable_llm_tool.md`.

- prosty produkt kupowany i instalowany z Googleplex;
- launcher, uninstall i bounded app state;
- zatwierdzone templates zamiast dowolnego promptu;
- ingress/receipt/status przez kontrakt 135.3;
- brak wyświetlenia treści modelu przed 135.5.

Exit gate: zakupiona aplikacja tworzy jeden bezpieczny task receipt, ale nie
publikuje model-generated body.

### Sprint 135.5 - publisher adapters

Pełna specyfikacja:
`doc/sprints/sprint_135_5_llm_publishers_blacknet_googleplex_cyberner.md`.

- BlackNet mixed feed `ollama_enriched`;
- publikacja News na Googleplex Home przygotowanym w 135.4.1;
- owner-scoped wynik w kupowanym narzędziu z 135.4.2;
- Cyberner `AI Central / AGI 2108`;
- opcjonalny BlackNet Radio;
- publication receipts, per-medium retry i deterministyczny fallback.

135.5 jest pierwszym sprintem, w ktorym wynik Ollamy moze stac sie trescia
widoczna dla gracza. Publisher czyta tylko zaakceptowany canonical Inbox i nie
moze publikowac surowej odpowiedzi modelu.

Exit gate: zaakceptowany kandydat jest publikowany dokladnie raz i tylko do
wlasciwej audience.

### Sprint 135.6 - hardening i cutover

- E2E replay/crash/visibility/load tests;
- limity, backpressure, observability i runbook operatorski;
- awaria/odlaczenie Ollamy oraz recovery backlogu;
- usuniecie roli legacy file outboxa jako kolejki;
- manual BlackNet, Googleplex News, Cyberner AGI-2108 i installed app.
- finalny cutover jest zablokowany, jeżeli dowolny producer, worker, publisher,
  read model albo diagnostyka wykonuje full-profile read/write, skan kont lub
  per-recipient `profile_json`; fixture 35 MB musi zachować wszystkie metryki
  heavy-profile równe zero.

Exit gate: jeden spojny system eventowej komunikacji LLM gotowy do kontrolowanej
walidacji serwerowej.

## 11. Finalny werdykt

Nie ma blockera do rozpoczecia Sprintu 135.2. Decyzje produktowe wymagane przed
publikacja w 135.5 zostaly wydzielone do bramek 135.4.1 (Googleplex Home/News)
i 135.4.2 (kupowane narzedzie oraz jego result surface).

Najwazniejsza decyzja techniczna jest zamknieta: nie budujemy drugiego outboxa.
Rozszerzamy trwaly store ze Sprintu 129, a plikowy outbox Sprintu 83 zachowujemy
wylacznie jako kompatybilny eksport diagnostyczny.
