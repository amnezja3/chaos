# Sprint 135.5 — regresje kontraktu publikacji LLM

Data: 2026-08-30  
Status: `IMPLEMENTATION RESOLVED — FINAL SERVER VALIDATION`

## Problem / objawy

Pierwsza walidacja produkcyjna publisherów BlackNet, Googleplex News i Cyberner
potwierdziła transport `outbox -> Ollama -> candidate -> publication receipt ->
medium record`, ale ujawniła serię regresji semantycznych i projekcyjnych:

- Googleplex News dopisywał kolejne karty i mógł tworzyć dodatkowe HERO zamiast
  aktualizować ograniczony zestaw istniejących powierzchni;
- title/body ujawniały skrócone identyfikatory faktów, tasków i token-like hash;
- model łączył tekst, `fact_ref`, asset i CTA pochodzące z różnych faktów;
- BlackNet potrafił pokazać narrację obok deterministic fallbacku dla tych
  samych faktów;
- CTA prowadziło do niewłaściwego obiektu mapy mimo poprawnego deterministic
  sygnału;
- waga rankingu `importance` była interpretowana przez model jako procent;
- Cyberner mógł przedstawić echo inputu albo fallback jako odpowiedź AGI;
- publikacja narracyjna mogła nadpisać canonical box promocyjny produktu na
  Googleplex Home;
- podczas soak testu publishera zaobserwowano pojedynczy
  `sqlite3.OperationalError: database is locked`.

Jakość pierwszych wyników była dodatkowo zbyt raportowa: „BlackNet Digest”,
„Wydajny komunikat reporterski” i techniczne streszczenia nie odpowiadały
językowi przechwyconej transmisji z roku 2108. To ostatnie jest problemem
kalibracji, nie integralności transportu.

## Wpływ na grę i runtime

- feed Googleplex mógł rosnąć bez ograniczenia i łamać hierarchię layoutu;
- gracz mógł dostać CTA do innego celu niż opisany w publikacji;
- wewnętrzne identyfikatory przeciekały do presentation layer;
- dwie powierzchnie mogły prezentować semantycznie ten sam sygnał jako dwa
  niezależne wpisy;
- odpowiedź AGI mogła wyglądać na poprawną technicznie, mimo że nie zawierała
  wyniku modelu;
- narracja mogła zastąpić ofertę produktu z canonical katalogu treścią modelu.

Gameplay, wallet, inventory i canonical state świata nie zostały przekazane
modelowi do mutacji. Regresje dotyczyły projekcji, publikacji i rozwiązywania CTA.

## Evidence produkcyjne

Walidacja objęła rzeczywiste taski, candidates, receipts i medium records w
`data/game.sqlite3`.

- `narrative_candidate_37855d92c3fabd76` i
  `narrative_candidate_4e4b63d17a0f88fb` zostały poddane kwarantannie jako
  `internal_identifier_leak`;
- `narrative_candidate_5be6de7233fd090b` został poddany kwarantannie jako
  `selected_fact_not_grounded`;
- `narrative_candidate_8eac01d02857d803` potwierdził accepted publication,
  exactly-once (`1 receipt / 1 record`) oraz code-owned CTA;
- task `narrative_task_83dc20c4bcb75ac5` pokazał błędne wartości `75/50/25`
  wyprowadzone z backendowego `importance`;
- canonical target konfliktu był zapisany w
  `territory_conflict_pillars.public_target_json.target`, lecz wcześniejsza
  projekcja czytała tylko płaski wrapper;
- po poprawce task `narrative_task_7bcfc1fd7fa3330b` zachował target
  `legacy:181483bf01cfd1275055`, label `プラスパークス和泉第4` oraz współrzędne
  `35.6766 / 139.653286` zarówno w fakcie, jak i dozwolonym CTA;
- log publishera zawierał pojedynczą blokadę SQLite podczas
  `BEGIN IMMEDIATE`; proces został podniesiony przez PM2 i kontynuował
  publikowanie. Brak jeszcze dowodu na cykliczny writer-lock.

## Root causes

### 1. Brak stabilnej projekcji Googleplex News

Medium records były traktowane jak kolejne elementy feedu. Nie istniał twardy
kontrakt mapowania publikacji na skończone, istniejące sloty foundation.

### 2. Model otrzymywał dane techniczne i zbyt szeroki kontekst

Task package eksponował pola, które były potrzebne backendowi, ale nie były
bezpiecznym materiałem redakcyjnym. Lokalny model 8B kopiował skrócone hashe,
łączył wiele faktów i interpretował `importance` jako treść domenową.

### 3. Niezależne wybory fact, CTA i assetu

Samo allowlistowanie CTA nie zapewniało, że wybrana akcja oraz asset należą do
tego samego faktu, na którym oparto narrację. Exactly-once publishera chronił
liczbę zapisów, ale nie spójność semantyczną rekordu.

### 4. Niejednorodny kształt canonical targetu

`public_target_json` występował jako płaski target albo wrapper z właściwym
obiektem w polu `target`. Projekcja konfliktu obsługiwała tylko pierwszy wariant,
więc traciła label i współrzędne, a późniejszy CTA payload korzystał z
niepełnego celu.

### 5. Dwa niezależne tory prezentacji tych samych faktów

Deterministic BlackNet oraz `ollama_enriched` mogły przejść do widoku
równolegle, ponieważ deduplikacja po receipt/task ID nie wykrywała wspólnego
zbioru canonical `fact_refs`.

### 6. Brak rozróżnienia canonical product promo i narracji

Sygnał `googleplex_product_signal` trafiał do tasków Googleplex News, a
historyczny medium record mógł zostać przypisany do dowolnego stable slotu.
Tymczasem box produktu ma osobny kontrakt katalogowy i nie jest powierzchnią
redakcyjną modelu.

### 7. Fallback Cybernera udawał wynik modelu

Brak accepted candidate nie był dostatecznie odróżniony od poprawnej
odpowiedzi. Echo topicu mogło przejść jako pozorny rezultat AGI.

## Próby naprawy i odrzucone hipotezy

- kolejne prompty v1–v6 ograniczały długość i zakazywały identyfikatorów, ale
  literalny grounding okazał się zbyt restrykcyjny dla modelu 8B;
- zwiększenie roli modelu w geolokacji zostało odrzucone — model może opisać
  przybliżoną okolicę, lecz target ID i współrzędne pozostają code-owned;
- nie zastosowano usuwania nazw `POI-*`, ponieważ są legalnymi canonical nazwami
  obiektów świata;
- nie rozwiązano problemu przez append-only feed ani przez frontendowe ukrywanie
  duplikatów; ograniczenia należą do backendowej projekcji;
- nie dodano jeszcze `presentation_slot` do task package. Najpierw trwa fizyczna
  walidacja istniejących limitów HERO/sidebox/small;
- pojedyncza blokada SQLite pozostaje obserwacją soak, a nie potwierdzonym root
  cause wymagającym osobnego hotfixu.

## Finalne rozwiązanie

- Googleplex News zastępuje maksymalnie sześć stabilnych slotów foundation bez
  zwiększania liczby kart i bez drugiego HERO;
- title/body przechodzą presentation validator i prepublish guard; URL-e,
  techniczne identyfikatory i nieznane token-like strings kończą się fail-closed;
- task package udostępnia bounded presentation facts, bez `importance` i
  zbędnych identyfikatorów;
- wybrany `fact_ref`, `asset_ref` i `cta_ref` są walidowane jako jeden kontrakt;
- CTA payload jest rozwiązywany wyłącznie przez backend z canonical signal;
  model nie tworzy target ID ani współrzędnych;
- projekcja targetu normalizuje płaski oraz zagnieżdżony
  `public_target_json.target`;
- BlackNet deduplikuje deterministic i enriched records po canonical fact refs;
- echo inputu Cybernera jest odrzucane, a brak accepted candidate daje jawny
  stan „wynik niedostępny”, nie fałszywą odpowiedź;
- `googleplex_product_signal` nie tworzy tasków Googleplex News, choć pozostaje
  dostępny dla narracji BlackNet;
- historyczna publikacja produktowa nie może nadpisać slotów Googleplex News;
- box `gp-home-featured` nadal bierze nazwę, pełny opis, `DL` i link do produktu
  bezpośrednio z canonical katalogu;
- immutable prompty `blacknet-world-prompt-v2`,
  `googleplex-news-assets-prompt-v8` oraz `cyberner-agi-2108-prompt-v2` rozdzielają
  ton trzech mediów bez rozszerzania uprawnień modelu.

## Testy i weryfikacja

- walidacja parsera, schema, grounding, CTA/fact/asset matching oraz presentation
  safety;
- stable-slot projection bez wzrostu feedu;
- exactly-once publication receipt i brak replayu terminalnego rekordu;
- deterministic/enriched dedupe po `fact_refs`;
- nested canonical target z niełacińskim labelem i współrzędnymi;
- brak `importance` w pakiecie widocznym dla modelu;
- canonical product card i odrzucenie product signal w Googleplex News;
- Cyberner echo detection oraz jawny failed/unavailable state;
- finalny lokalny pakiet regresji: `52` testy — `OK`;
- testy celowane routingu produktu i canonical boxu: `2` — `OK`;
- `py_compile` i `git diff --check` — `OK`.

## Wpływ na architekturę

Sprint utrwalił rozdział odpowiedzialności:

```text
canonical facts/state
        |
        v
bounded task package ---> Ollama: wyłącznie interpretacja tekstowa
        |                            |
        |                            v
        +--------------------> validated candidate
                                     |
                                     v
code-owned CTA/asset/slot ---> publication receipt ---> medium projection
```

Model nie jest źródłem targetu, współrzędnych, assetów spoza allowlisty,
produktów katalogowych ani prawdy świata. Exactly-once nie zastępuje groundingu,
deduplikacji semantycznej ani kontroli projection surface.

## Wnioski na przyszłość

1. Ranking metadata nie może automatycznie trafiać do promptu jako fakt.
2. Allowlista akcji musi być związana z konkretnym `fact_ref`, nie tylko z
   całym taskiem.
3. Canonical JSON wymaga normalizacji jawnych wariantów kształtu przed budową
   publicznego faktu.
4. Deduplikacja techniczna i semantyczna są dwiema różnymi bramkami.
5. Deterministyczne moduły katalogowe nie powinny być powierzchnią zapisu LLM.
6. Mały model lokalny potrzebuje krótkich przykładów tonu i ograniczonej roli;
   backend musi zachować całą odpowiedzialność wykonawczą.
7. Slot-aware generation należy dodawać dopiero po obserwacji realnego problemu,
   zachowując backendowy hard limit niezależnie od promptu.
8. Powtarzalny `database is locked` powinien otrzymać osobny artefakt z analizą
   czasu transakcji i writerów; pojedynczy wpis w historycznym logu nie wystarcza.

## Powiązane pliki, commity i sprinty

- `doc/sprints/sprint_135_5_llm_publishers_blacknet_googleplex_cyberner.md`
- `ghostnetwork/ollama_policy.py`, `ghostnetwork/producers.py`
- `ghostnetwork/publication.py`, `ghostnetwork/repository.py`
- `ghostnetwork/llm/registry.py`, `ghostnetwork/llm/prompts/`
- `googleplex_news.py`, `run.py`
- `tests/test_ollama_policy.py`, `tests/test_llm_event_producers.py`
- `tests/test_llm_publishers.py`, `tests/test_narrative_publications.py`
- commity końcowych poprawek: `82abb64`, `4e979de`, `22fc1f4`;
- następny etap po finalnej walidacji: Sprint 135.6.

## Status końcowy

`IMPLEMENTATION RESOLVED — FINAL SERVER VALIDATION`

Pozostają trzy bramki jakościowe: Googleplex News v8, BlackNet v2 i Cyberner
AGI v2. Ewentualny `135.5.x slot-aware generation repair` powstaje wyłącznie po
potwierdzeniu rozjazdu treści z realną geometrią slotów.

### Follow-up produkcyjny — dual signal type

Pierwszy task v8 po wdrożeniu ujawnił, że snapshot używa prezentacyjnego
`signal_type=product_opportunity`, podczas gdy canonical typ produktu jest
zakodowany w `fact_id` jako `googleplex_product_signal`. Filtr oparty wyłącznie
o `signal_type` nie usuwał więc produktów z facts Googleplex News. Routing
rozpoznaje teraz oba legalne kształty: jawny typ sygnału oraz canonical segment
`fact_id`. Test regresyjny używa dokładnego produkcyjnego wariantu
`product_opportunity + bnf:googleplex:googleplex_product_signal:*`.
