# Sprint 135.5.1 — Deterministic Editorial Queue and Slot-Owned LLM Copy

Status: `IN PROGRESS — ETAP I IMPLEMENTED LOCALLY / SERVER VALIDATION PENDING`

## Stan implementacji — Etap I

Zaimplementowano lokalnie:

- scheduler wybiera jeden deterministic signal na task i najwyżej jeden nowy
  assignment per medium na tick;
- BlackNet korzysta z `blacknet_signal_narration`, a Googleplex HERO z
  `googleplex_world_dispatch`;
- model nie otrzymuje listy tematów ani CTA; selected fact, canonical action i
  target są code-owned;
- niezmieniona wersja źródła jest idempotentna, a scheduler przechodzi do
  kolejnego nieprzetworzonego sygnału;
- semantyczny hash źródła ignoruje ruchome runtime TTL (`valid_until`), więc
  odświeżenie ważności tego samego faktu nie tworzy pozornie nowej publikacji;
- Googleplex serializuje otwarte assignmenty HERO i zapisuje aktywny pointer w
  `ghost_narrative_slot_state`;
- publikacja slotu używa optimistic CAS; stale assignment kończy się
  `slot_assignment_superseded`;
- `/api/googleplex/news` czyta wyłącznie aktywne rekordy slot state; rekord bez
  jawnego `presentation_slot` nie może nadpisać foundation;
- Stage I dopuszcza publikacje LLM wyłącznie do `gp-home-world-grid`; pozostałe
  karty pozostają canonical foundation;
- działa bounded novelty guard `duplicate_content`;
- po pierwszej walidacji serwerowej dodano fail-closed guards
  `raw_coordinate_leak` i `source_calendar_year_leak`; aktywne prompty BlackNet
  v5 i Googleplex HERO v10 nie mogą przepisywać runtime roku 2026 ani lat/lng;
- kolejna walidacja dodała `technical_region_prefix_leak`; BlackNet v5 nie
  otrzymuje technicznego `region_id` rozpoczynającego się od `world-/_/:`;
- worker nie claimuje historycznej polityki wielofaktowego `world_digest`;
- testy wymuszają brak pełnego profilu na schedulerze i endpointach.

Pozostaje przed uznaniem Etapu I za zwalidowany:

- deploy i migracja SQLite na serwerze;
- fizyczny przebieg `signal -> task -> candidate -> receipt -> BlackNet/HERO`;
- potwierdzenie jednego rekordu na BlackNet i zmiany wyłącznie HERO;
- ponowny tick bez zmiany źródła oraz test stale-slot na danych serwerowych;
- krótki soak writer contention i pomiar hot paths z
  `profile_full_read/profile_full_write/profile_bytes = 0`.

Etap II pozostaje poza tym wdrożeniem: product promo, box BlackNet na Home,
rotacja small slots i role assetów.

## Cel sprintu

Przebudować publikacje BlackNet i Googleplex News tak, aby backend w pełni
deterministycznie wybierał temat, medium, slot, canonical dane, CTA, budżet tekstu
i moment odświeżenia. Ollama ma pełnić wyłącznie rolę copywritera roku 2108:
tworzyć tekst dla jednego, z góry przypisanego zadania oraz opcjonalnie wybierać
semantyczną rolę assetu z bounded allowlisty.

Sprint usuwa model `world_digest -> model wybiera jeden z wielu faktów` i
zastępuje go kontraktem:

```text
canonical fact/capability/product
        |
        v
deterministic signal + editorial scheduler
        |
        v
one source + one medium + one slot + one copy contract
        |
        v
Ollama: title/body/slogan + optional asset_role
        |
        v
backend validation + novelty guard + slot CAS
        |
        v
BlackNet feed albo dokładnie wskazany Googleplex Home slot
```

## Powód otwarcia 135.5.1

Walidacja produkcyjna Sprintu 135.5 potwierdziła poprawny transport, lease,
candidate, publication receipt i medium record, ale ujawniła pozorne publikacje:

- co 15 minut powstawały dwa nowe taski mimo braku istotnej zmiany źródła;
- oba media otrzymywały prawie ten sam zestaw maksymalnie 20 sygnałów;
- backend nie wskazywał `selected_fact_ref`, więc model sam wybierał temat;
- stabilny ranking wielokrotnie podawał ten sam konflikt jako pierwszy;
- przy `temperature=0` model 8B kopiował gotowe przykłady z promptów;
- kolejne candidates i receipts były technicznie unikalne, ale semantycznie
  identyczne;
- Googleplex News ponownie podstawiał taki sam tekst do HERO;
- BlackNet zachowywał najnowszy rekord dla tego samego zbioru `fact_refs`, więc
  wizualnie również nie pojawiała się nowa treść.

Przykłady z produkcji były literalnymi kopiami wzorców promptów:

```text
Googleplex News:
Napiecie rosnie nad Tokio
W poblizu miasta wykryto aktywny konflikt. Cel nadal pozostaje sporny.

BlackNet:
PRZECHWYT // WEZEL SPORNY
Konflikt nadal aktywny. Cel pozostaje sporny. Dalsza czesc transmisji zaginela.
```

To nie była awaria Ollamy ani publishera. Błąd dotyczył własności decyzji
redakcyjnej i braku trwałej polityki świeżości.

## Nadrzędna zasada odpowiedzialności

| Decyzja | Właściciel |
|---|---|
| Co jest prawdą | canonical fact/state/catalog |
| Jaki deterministic signal z tego wynika | backend |
| Co publikujemy teraz | editorial scheduler |
| Do którego medium | backend policy |
| Do którego slotu | backend slot registry |
| Nazwa i cena produktu | canonical Googleplex catalog |
| CTA, target i link | backend |
| Budżet tekstu | slot copy contract |
| Konkretne słowa i ton | Ollama |
| Semantyczna rola assetu | Ollama opcjonalnie, z allowlisty |
| Konkretny asset i kadrowanie | backend registry |
| Czy treść jest nowa i legalna | backend validator |

Model nie jest redaktorem naczelnym. Nie wybiera faktu, produktu, medium, slotu,
linku, ceny, canonical targetu ani momentu publikacji.

## Twardy zakaz heavy-profile

Sprint podlega bezwzględnemu invariantowi wynikającemu z produkcyjnej regresji
ścieżki `operacje -> pliki -> File Manager -> GX`: pełny `profile_json` nie może
ponownie wejść na żaden hot path narracji ani Googleplex News.

Zakaz obejmuje:

```text
editorial scheduler
wybór world signal
wybór promowanego produktu
budowę task package
worker Ollamy
candidate validation
publisher
slot state CAS
/api/googleplex/news
/api/blacknet/world-signals
asset resolution
novelty lookup
```

Nie wolno użyć pełnego profilu jako wygodnego fallbacku do znalezienia produktu,
operacji, pliku, klanu, storage, market history, wiadomości ani aktywności gracza.
Źródłami mogą być wyłącznie bounded canonical stores, statyczne registry oraz
jawne publiczne/capability projections.

W szczególności zabronione jest:

```text
user_store.get_profile(...)
UserProfileManager.get_profile(...)
hydracja profile_json.operations
skan profile_json.files
kopiowanie całego profilu do taska lub projekcji News
ponowny zapis profilu podczas publikacji copy
```

Jeżeli wymagany sygnał nie ma jeszcze bounded canonical projection, sprint ma
najpierw dodać taką projekcję albo zakończyć assignment jako `source_unavailable`.
Nie wolno obchodzić braku adaptera przez pełny odczyt profilu.

Każdy nowy producer, scheduler i endpoint otrzymuje test, w którym próba odczytu
pełnego profilu rzuca wyjątek. Test musi mimo tego przejść dla poprawnego bounded
źródła. Telemetria odpowiedzi zachowuje:

```text
profile_full_read:  0
profile_full_write: 0
profile_bytes:      0
```

Regresja ta jest opisana w
`doc/hardbugfix/heavy_profile_operation_files_gx_regression_sprint_135_5_2026-08-30.md`
i ma być traktowana jako obowiązkowy punkt review każdej zmiany dotykającej
łańcucha `hackowanie -> operacje/pliki -> File Manager/GX/wallet` oraz wszystkich
współdzielonych z nim projekcji profilu.

## Zakres

### W zakresie

1. Deterministyczna kolejka redakcyjna BlackNet per signal.
2. Jawny registry i aktywny stan slotów Googleplex Home.
3. Code-owned przypisanie jednego źródła do jednego taska.
4. Osobne task variants i schema dla różnych rodzajów copy.
5. Promocyjny copywriting produktu na podstawie canonical katalogu.
6. Odświeżanie boxu promującego BlackNet na Googleplex Home.
7. Deterministyczna, rozłożona w czasie rotacja małych boxów.
8. Slot-aware limity tekstu i allowlista ról assetów.
9. Novelty guard, source-version dedupe i ochrona przed kopiowaniem promptu.
10. Atomowa aktualizacja dokładnie jednego slotu z optimistic CAS.
11. Zachowanie append-only receipts i medium records jako audytu.
12. Brak pełnych odczytów profilu w producerze, schedulerze, workerze,
    publisherze i projekcji News.

### Poza zakresem

- zmiana modelu `llama3.1:8b`;
- generowanie obrazów przez Ollamę;
- pozwalanie modelowi na tworzenie URL, CTA, ceny lub targetu;
- personalizowanie publicznych Googleplex News danymi pełnego profilu;
- przebudowa Cyberner AGI, poza zachowaniem wspólnego transportu;
- automatyczne łączenie wielu faktów w jeden digest BlackNet;
- zmiana canonical mechaniki produktów, konfliktów, incydentów i radia.

## Rozdzielenie powierzchni

### A. Rzeczywisty feed BlackNet

Źródłem jest pojedynczy deterministic world signal. Backend wybiera sygnał,
przypina jego `fact_ref`, canonical CTA i target. Ollama tworzy wyłącznie wersję
narracyjną przechwyconej transmisji.

```text
canonical fact -> deterministic signal -> blacknet_signal_narration
              -> accepted copy -> BlackNet medium record -> feed BlackNet
```

### B. Box BlackNet na Googleplex Home

To nie jest rekord feedu BlackNet. Jest to osobny, evergreen box nawigacyjny:

```text
slot_id:       gp-home-blacknet
content_kind:  navigation_promo
fixed_action:  open_blacknet
```

Ollama może odświeżyć tytuł, opis i `asset_role`. Backend zawsze zachowuje link,
akcję i legalne twierdzenia o istniejącym feedzie.

### C. Googleplex World Intelligence / HERO

Źródłem jest jeden wybrany world signal. Backend przypisuje go do HERO albo innej
jawnej powierzchni editorial. Ollama nie wybiera faktu ani slotu.

### D. Promocja produktu Googleplex

Canonical katalog pozostaje właścicielem produktu, ceny, dostępności, nazwy,
opisu, pobrań i linku. Backend wybiera produkt, a Ollama pisze slogan lub krótki
tekst reklamowy na podstawie jego opisu.

### E. Małe boxy capability/navigation

Operations, Data, Storage, Clans i inne dopuszczone sloty mogą otrzymywać nowe
copy według deterministycznego harmonogramu. Ich funkcja i akcja pozostają stałe.
Sloty systemowe mogą mieć `llm_refresh_enabled=false` i pozostać canonical static.

## Canonical registry slotów

Backend utrzymuje jawny registry. Minimalny kontrakt slotu:

```json
{
  "slot_id": "gp-home-featured",
  "content_kind": "product_promo",
  "presentation_weight": "small",
  "llm_refresh_enabled": true,
  "allowed_task_variants": ["googleplex_product_promo"],
  "title_owner": "backend",
  "title_chars": 32,
  "body_chars": 90,
  "body_words": 18,
  "estimated_lines": 3,
  "allowed_asset_roles": ["scanner", "security", "network"],
  "fixed_action": "open_googleplex_product",
  "refresh_policy": "campaign",
  "minimum_refresh_seconds": 21600
}
```

Registry obejmuje co najmniej:

```text
gp-home-world-grid       hero editorial
gp-home-blacknet         BlackNet navigation promo
gp-home-exchange         Ghost Exchange navigation promo
gp-home-map              map navigation promo
gp-home-cyberner         Cyberner navigation promo
gp-home-featured         product promo
gp-home-operations       small capability
gp-home-data             small capability
gp-home-storage          small capability
gp-home-clans            small capability
gp-home-integrity        small system/capability
gp-home-protocol         small system/capability
```

Nie wszystkie sloty muszą zostać od razu włączone do rotacji. Registry jawnie
określa, które są zarządzane przez LLM copy, a które pozostają statyczne.

## Aktywny stan slotu

Historia publikacji pozostaje append-only, lecz frontend nie powinien zgadywać,
który rekord należy do którego boxu. Potrzebna jest canonical projekcja aktywnego
stanu, np. `ghost_narrative_slot_state`:

```text
target_medium
slot_id
content_kind
active_medium_record_id
active_source_ref
active_source_version
active_content_hash
creative_epoch
last_refreshed_at
next_refresh_at
version
updated_at
```

Klucz główny:

```text
(target_medium, slot_id)
```

`version` służy do optimistic CAS. Spóźniony candidate nie może nadpisać slotu,
jeżeli scheduler zdążył przypisać do niego nowsze źródło.

## Rozszerzenie task assignment

Istniejący `ghost_narrative_outbox` pozostaje kolejką wykonawczą Ollamy. Task
otrzymuje code-owned assignment:

```text
content_kind
presentation_slot
selected_source_ref
selected_source_version
creative_epoch
editorial_contract_json
fixed_action_json
allowed_asset_roles_json
expected_slot_version
```

Pola te nie są generowane ani zmieniane przez model.

Canonical dedupe taska uwzględnia:

```text
source_scope
selected_source_ref
selected_source_version
target_medium
presentation_slot
content_kind
creative_epoch
audience
```

Dla zmieniającego się sygnału nowa wersja źródła legalnie tworzy nowy task. Dla
evergreen copy nowy `creative_epoch` tworzy task wyłącznie wtedy, gdy slot jest
rzeczywiście due. Samo kolejne 15-minutowe okno nie tworzy nowej tożsamości.

## Editorial scheduler

Scheduler działa okresowo, ale nie ma obowiązku tworzenia taska. W jednym ticku
wybiera bounded liczbę assignmentów, domyślnie najwyżej jeden na medium.

Kolejność decyzji:

1. nowy lub zmieniony critical/high world signal;
2. canonical source version różna od aktywnej wersji slotu;
3. niepublikowany wcześniej sygnał nadal mieszczący się w TTL;
4. nowa kampania produktu po upływie product cooldown;
5. najdawniej odświeżony evergreen slot, którego `next_refresh_at` minął;
6. brak taska, jeżeli żadna powierzchnia nie jest due.

Scheduler musi uwzględniać historię per medium. Publikacja faktu w BlackNet nie
oznacza automatycznie publikacji tego samego faktu w Googleplex News.

### Fairness i cooldown

- ten sam `selected_source_ref + selected_source_version` nie jest publikowany
  ponownie w tym samym medium;
- ten sam produkt nie wygrywa dwóch kolejnych kampanii, jeśli istnieje inny
  legalny kandydat;
- stały najwyżej punktowany konflikt nie blokuje wszystkich pozostałych
  niepublikowanych sygnałów;
- expired signal nie może wejść do taska;
- failed/quarantined copy nie zmienia aktywnego slotu;
- retry zachowuje to samo assignment, nie wybiera nowego źródła.

## Wybór produktu Googleplex

Backend wybiera produkt na podstawie code-owned rankingu, np.:

```text
published/available gate
+ freshness
+ downloads
+ price/temperature/campaign score
+ czas od ostatniej promocji
- repeat cooldown
```

Dokładna funkcja jest deterministyczna i testowalna. Losowość nie może zmieniać
wyniku bez jawnego, utrwalonego campaign seed.

Źródło produktu przekazane do taska:

```json
{
  "product_id": "v_map",
  "name": "V-MAP",
  "description": "Skanuje i szuka otwartych portów i luk w zabezpieczeniach.",
  "category": "scanner_recon",
  "price_hc": 955,
  "downloads": 15,
  "available": true
}
```

Do modelu trafiają nazwa, opis i presentation-safe kategoria. Cena i pobrania
mogą być widoczne jako kontekst wyłącznie wtedy, gdy schema wymaga ich użycia,
ale ich renderowaną wartość zawsze składa backend.

Finalny box:

```text
title       <- backend: V-MAP
body        <- Ollama: Masz problem z przelamaniem zabezpieczen? Sprawdz V-MAP.
price       <- backend: 955 HC
downloads   <- backend, jeśli slot je pokazuje
CTA label   <- backend: ZOBACZ NARZEDZIE
CTA/link    <- backend: canonical product action
asset       <- backend registry z optional asset_role
```

Ollama nie może zmienić nazwy produktu, ceny, linku ani dostępności.

## Task variants

### `blacknet_signal_narration`

Źródło: jeden deterministic signal.  
Cel: fragment transmisji przechwyconej przez Ghost System.  
Output modelu:

```json
{
  "title": "...",
  "body": "...",
  "tone": "mystery"
}
```

`fact_ref`, CTA i payload dokłada backend z assignmentu.

### `googleplex_world_dispatch`

Źródło: jeden world signal.  
Cel: depesza dla jawnego slotu editorial.  
Output:

```json
{
  "title": "...",
  "body": "...",
  "tone": "critical",
  "asset_role": "danger"
}
```

### `googleplex_product_promo`

Źródło: jeden wybrany canonical produkt.  
Cel: slogan/reklamowy opis bez zmiany danych katalogowych.  
Output:

```json
{
  "body": "Masz problem z przelamaniem zabezpieczen? Sprawdz V-MAP.",
  "tone": "advertising",
  "asset_role": "scanner"
}
```

Tytuł jest canonical nazwą produktu i nie jest generowany.

### `googleplex_navigation_promo`

Źródło: bounded capability contract, np. BlackNet, Exchange, mapa lub Cyberner.  
Cel: odświeżenie tekstu boxu z zachowaniem stałego linku.  
Output:

```json
{
  "title": "BLACKNET: PRZECHWYC BIEZACE SYGNALY",
  "body": "Wejdz do strumienia przechwyconych transmisji swiata CHAOS.",
  "tone": "mystery",
  "asset_role": "intercept"
}
```

### `googleplex_capability_card_refresh`

Źródło: bounded lista legalnych twierdzeń o jednej funkcji systemu.  
Cel: krótki tekst konkretnego small slotu.  
Output: title/body/tone/optional asset_role zgodnie z budżetem slotu.

## Prompty

Każdy task variant otrzymuje osobny immutable prompt i osobną, minimalną schema.
Prompty opisują strukturę, głos i zakazane zachowania, ale nie zawierają gotowych
tytułów ani zdań, które model może skopiować.

Dozwolony wzorzec instrukcji:

```text
- zacznij w środku transmisji;
- użyj konkretu z przekazanego sygnału;
- jedno lub dwa krótkie zdania;
- nie dopisuj nowego zdarzenia;
- nie pisz raportu ani metakomunikatu.
```

Niedozwolony wzorzec:

```text
Tytul: "PRZECHWYT // WEZEL SPORNY"
Tresc: "Konflikt nadal aktywny..."
```

Fingerprinti jawnych fraz instrukcyjnych mogą zostać dodane do novelty guard,
ale podstawową naprawą jest brak copy-ready przykładów w promptach.

## Asset contract

Ollama może opcjonalnie zwrócić wyłącznie semantyczną rolę:

```text
neutral
danger
victory
defence
mystery
market
broadcast
scanner
security
network
```

Task zawiera bounded `allowed_asset_roles`. Backend rozwiązuje:

```text
asset_role + slot presentation_weight + registry status
-> konkretny asset_ref
```

Model nie widzi ścieżki pliku, URL ani assetu niedozwolonego dla geometrii slotu.
Brak legalnego resolution kończy się canonical fallback assetem slotu, nie
arbitralnym wyborem.

## Slot-aware copy budgets

Budżety są częścią registry i task package, nie CSS-em przekazywanym modelowi.
Wartości startowe podlegają walidacji wizualnej:

```text
hero:
  title: 32-64 chars
  body: 120-260 chars
  sentences: 1-3

sidebox:
  title: 24-48 chars
  body: 80-140 chars
  sentences: 1-2

small:
  title: 18-32 chars
  body: 50-90 chars
  sentences: 1-2

product_promo:
  title: backend-owned product name
  body: 45-90 chars
```

Backend sprawdza char count, word count i bounded estimated lines. Tekst
przekraczający kontrakt jest odrzucany albo kierowany do jednego kontrolowanego
retry. Nie może zostać bezrefleksyjnie obcięty w połowie zdania.

## Candidate contract

Candidate dziedziczy z taska i nie pozwala modelowi nadpisać:

```text
content_kind
presentation_slot
selected_source_ref
selected_source_version
creative_epoch
expected_slot_version
fixed_action
```

Model-owned payload jest minimalny. Backend składa finalny candidate/publication
z obu części.

Dla single-source taska `fact_refs` jest code-owned. Jeżeli pozostaje w schema
kompatybilności, musi być dokładnie równe `[selected_fact_ref]`; relacja
`subset of 20 facts` przestaje być wystarczająca.

## Novelty guard

Przed accepted/publication backend porównuje copy z:

- aktywną treścią wskazanego slotu;
- ostatnimi bounded publikacjami tego samego medium i content kind;
- poprzednimi publikacjami tego samego source ref;
- zakazanymi frazami pochodzącymi z promptu;
- normalized content hash.

Minimalne bramki:

```text
same source_ref + same source_version -> no new world publication
same normalized title/body           -> duplicate_content
same active slot content              -> slot_no_change
prompt example fingerprint            -> copied_prompt_example
stale expected_slot_version           -> slot_assignment_superseded
```

Similarity ponad ustalony próg może uruchomić maksymalnie jeden rewrite attempt.
Po drugim braku nowości task kończy się audytowalnym `no_change`, bez tworzenia
kolejnego medium recordu i bez nieskończonego retry.

## Publisher i slot CAS

Publisher zachowuje exactly-once candidate/receipt, a dla Googleplex wykonuje
dodatkowy slot-aware prepublish:

1. candidate jest `accepted`;
2. task policy i schema są aktualne;
3. candidate ma code-owned `presentation_slot`;
4. źródło nadal jest legalne i niewygasłe;
5. `expected_slot_version` jest aktualne;
6. content przechodzi novelty i geometry guard;
7. powstaje append-only medium record;
8. aktywny pointer slotu zmienia się atomowo przez CAS;
9. receipt dostaje `published`.

Jeśli slot ma nowszą wersję, candidate kończy się terminalnie jako
`slot_assignment_superseded`. Nie wolno nadpisywać nowszej karty starszym,
długo generowanym tekstem.

## Projekcja Googleplex News

`/api/googleplex/news` buduje foundation i dla każdego slotu odczytuje wyłącznie
jego aktywny pointer. Usunięty zostaje mechanizm:

```text
weź sześć najnowszych rekordów
-> deduplikuj
-> przypisz kolejno do sześciu slotów
```

Nowy mechanizm:

```text
gp-home-world-grid.active_record -> HERO
gp-home-blacknet.active_record   -> BlackNet box
gp-home-featured.active_record   -> product promo copy
...
```

Brak aktywnego rekordu zachowuje canonical foundation placeholder. Publikacja
jednego slotu nie zmienia żadnego innego slotu ani liczby kart.

## Projekcja BlackNet

BlackNet pobiera najnowsze legalne single-signal publications. Deterministic
fallback dla wybranego fact ref jest tłumiony tylko wtedy, gdy istnieje aktywna
publikacja narracyjna tego sygnału.

Scheduler nie zleca ponownej narracji dla tej samej wersji sygnału. W feedzie nie
powstają więc nowe receipts tylko po to, aby selektor po `fact_refs` później je
ukrył.

## Migracja i rollout

### Etap 1 — schema i registry

- dodać slot registry i slot state;
- rozszerzyć assignment outbox/candidate/medium record;
- dodać indeksy source ref/version oraz slot state;
- brak zmiany aktywnej projekcji.

### Etap 2 — nowe task variants

- zarejestrować immutable prompty i minimalne schema;
- producent tworzy single-source taski za feature flagą;
- stary `world_digest` nie tworzy nowych tasków;
- taski starej polityki nie są claimowane przez nowy worker.

### Etap 3 — publisher dual write

- append-only medium record pozostaje źródłem audytu;
- Googleplex publisher zapisuje również slot state;
- projekcja nadal może pozostać na dotychczasowym odczycie podczas testów.

### Etap 4 — read cutover

- Googleplex News czyta aktywne pointery slotów;
- BlackNet korzysta z single-signal publications;
- dotychczasowe rekordy pozostają w audycie, ale nie są automatycznie
  przypisywane do nowych slotów;
- foundation jest bezpiecznym fallbackiem.

### Etap 5 — wyłączenie legacy

- usunąć tworzenie okresowych tasków tylko na podstawie 15-minutowego okna;
- usunąć modelowy wybór spośród wielu facts;
- usunąć copy-ready przykłady z aktywnych promptów;
- zachować możliwość rollbacku projekcji do foundation bez usuwania records.

## Invarianty

```text
one task -> one selected source
one Googleplex task -> one preassigned slot
model-selected fact/slot/CTA/link/price -> 0
same unchanged source version -> no new world publication
same copy -> no slot update
stale candidate -> cannot overwrite newer slot
product name/price/link/availability -> canonical backend only
BlackNet feed publication != Googleplex BlackNet promo box
profile full read/write -> 0
append-only audit -> preserved
```

## Testy wymagane

### Scheduler i kolejka

- niezmieniony snapshot nie tworzy kolejnych world tasks;
- zmiana source version tworzy jeden task per uprawnione medium;
- ten sam fakt może mieć niezależny stan BlackNet i Googleplex News;
- expired signal jest pomijany;
- fairness wybiera niepublikowany sygnał zamiast stałego top conflict;
- product cooldown nie wybiera bez końca tego samego produktu;
- najwyżej jeden assignment per medium na tick.

### Task package

- pakiet zawiera dokładnie jedno code-owned źródło;
- model nie dostaje listy 20 tematów do wyboru;
- `presentation_slot` i budżet są obowiązkowe dla Googleplex;
- CTA payload, URL i cena nie są model-owned;
- allowed asset roles są bounded i zgodne ze slotem;
- task package pozostaje poniżej limitu bajtów.

### Product promo

- backend wybiera V-MAP deterministycznie z fixture katalogu;
- canonical tytuł pozostaje `V-MAP` niezależnie od outputu modelu;
- body pochodzi z accepted copy;
- cena i pobrania są identyczne z katalogiem;
- CTA prowadzi do dokładnie wybranego produktu;
- model nie może podmienić produktu ani ceny;
- niedostępny produkt nie może zostać opublikowany.

### Navigation i small slots

- odświeżenie `gp-home-blacknet` zachowuje `open_blacknet`;
- tekst BlackNet promo nie tworzy rekordu w feedzie BlackNet;
- task slotu nr 5 aktualizuje wyłącznie slot nr 5;
- niedue slot nie tworzy taska;
- slot z `llm_refresh_enabled=false` pozostaje canonical static;
- copy przekraczające budżet jest fail-closed.

### Novelty i bezpieczeństwo

- identyczny normalized output daje `duplicate_content`;
- kopia historycznego przykładu promptu jest odrzucana;
- jeden rewrite attempt, potem terminalne `no_change`;
- unknown asset role jest odrzucane lub rozwiązywane do canonical fallbacku;
- unknown fact/source ref jest quarantine;
- internal identifier i unknown POI guards pozostają aktywne.

### Publisher i projekcja

- exactly-once receipt/record;
- slot CAS aktualizuje dokładnie jeden pointer;
- stale candidate daje `slot_assignment_superseded`;
- sześć publikacji nie tworzy drugiego HERO ani nowej karty;
- product promo nie nadpisuje world HERO;
- world dispatch nie nadpisuje product promo;
- brak aktywnego copy zachowuje foundation;
- pełny profil nie jest czytany przez żadną ścieżkę sprintu.
- coordinate-backed CTA BlackNet daje pierwszeństwo canonical `lat/lng` przed
  legacy `hotspot_id`; `label` jest wyłącznie tekstem prezentacyjnym, a mapa
  oznacza punkt faktu osobnym markerem również po wykonaniu teleportu.

### Heavy-profile regression

- producer i scheduler kończą pracę poprawnie, gdy `user_store.get_profile`
  oraz `UserProfileManager.get_profile` są zastąpione wyjątkiem;
- wybór produktu korzysta wyłącznie z canonical katalogu;
- slot navigation/capability korzysta wyłącznie z bounded capability contract;
- novelty guard korzysta z medium records/slot state, nie z profilu;
- endpointy BlackNet i Googleplex News raportują zero pełnych odczytów i zapisów;
- test na ciężkim koncie nie zwiększa czasu mapy, pickera, Operation Control,
  File Managera, GX ani walletu;
- brak canonical adaptera kończy się `source_unavailable`, nigdy profile fallback.

## Walidacja serwerowa

1. Wytworzyć nowy konflikt/sygnał i potwierdzić jeden task BlackNet oraz jeden
   jawnie przypisany task Googleplex, jeśli policy zezwala na oba media.
2. Sprawdzić `selected_source_ref`, source version i slot przed uruchomieniem
   Ollamy.
3. Potwierdzić, że output modelu nie zawiera modelowego wyboru CTA/faktu/slotu.
4. Opublikować i sprawdzić, że BlackNet pokazuje nową transmisję tylko raz.
5. Potwierdzić, że Googleplex aktualizuje wyłącznie przypisany slot.
6. Uruchomić kolejny tick bez zmiany świata: zero nowych world tasks.
7. Wygenerować product promo V-MAP: canonical nazwa, cena i link oraz nowe body.
8. Odświeżyć `gp-home-blacknet`: zmienione copy, niezmieniony link do BlackNet.
9. Odświeżyć jeden small slot i potwierdzić brak zmian pozostałych kart.
10. Zasymulować spóźniony candidate: slot pozostaje przy nowszej wersji.
11. Obserwować SQLite writer contention i czasy endpointu News w soak.
12. Dla CTA incydentu potwierdzić, że etykieta w rodzaju `INCYDENT <lat,lng>`
    nie jest rozwiązywana jako hotspot: zapis pozycji i fokus mapy używają
    współrzędnych z canonical payloadu, a mapa pokazuje marker celu.

## Definition of Done

Sprint 135.5.1 można zamknąć wyłącznie, gdy:

```text
deterministic source selection:       PASS
single-source task contract:          PASS
BlackNet semantic rotation:           PASS
Googleplex explicit slot ownership:   PASS
product promo copy + canonical data:  PASS
navigation/small deterministic refresh: PASS
asset role -> registry resolution:    PASS
novelty/no-change guard:               PASS
slot CAS / stale protection:          PASS
exactly-once audit:                    PASS
profile reads/writes:                  0
physical server validation:           PASS
```

Po spełnieniu tych bramek Sprint 135.5 może zostać zamknięty semantycznie, a
135.6 może rozpocząć fairness, backpressure i replay na już poprawnym kontrakcie
redakcyjnym.

## Powiązane dokumenty

- `doc/sprints/sprint_135_5_llm_publishers_blacknet_googleplex_cyberner.md`
- `doc/hardbugfix/llm_publication_contract_regressions_sprint_135_5_2026-08-30.md`
- `doc/hardbugfix/heavy_profile_operation_files_gx_regression_sprint_135_5_2026-08-30.md`
- `doc/sprints/googleplex_news_functional_spec.md`
- `doc/sprints/googleplex_news_visual_css_spec.md`
- `doc/sprints/sprint_135_4_ollama_worker_canonical_inbox.md`
