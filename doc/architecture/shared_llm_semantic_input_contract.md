# Shared LLM Semantic Input Contract

Status: `137.pre.1 — IMPLEMENTATION CONTRACT`  
Contract version: `chaos-llm-semantic-input-v1`

## Granica odpowiedzialności

```text
canonical domain data
  -> deterministic domain converter
  -> relevance filter
  -> audience-safe semantic projection
  -> shared semantic contract
  -> bounded task packer
  -> model
```

Outbox, claim/lease/heartbeat, worker, retry/dead letter, candidates, validator,
publisher, receipts i medium records pozostają istniejącym canonical pipeline.
Warstwa semantic input nie pisze narracji, nie wywołuje modelu, nie czyta
profilów i nie wykonuje zewnętrznego geocodingu.

## Model-visible contract

Nowa polityka modelu otrzymuje control metadata oraz listę `semantic_facts`:

```json
{
  "semantic_contract": "chaos-llm-semantic-input-v1",
  "medium": "blacknet",
  "audience": {"scope": "public"},
  "narrative_intent": "ghost_part_discovery",
  "event_family": "part_discovered",
  "significance": "high",
  "tone_hint": "warning",
  "output_limits": {
    "title_chars": 72,
    "body_chars": 420,
    "fact_refs": 4,
    "json_only": true
  },
  "semantic_facts": [
    {
      "fact_ref": "f01",
      "statement": "Ujawniono wcześniej ukryty element sieci GhostNetwork.",
      "entities": [
        {"role": "lokalizacja zakotwiczenia zdarzenia", "kind": "target", "label": "Alior Bank"}
      ],
      "location": {
        "city": "Warszawa",
        "country": "Polska",
        "country_code": "PL"
      }
    }
  ]
}
```

Wymagane jest `statement`. Opcjonalne są:

- `entities`: maksymalnie sześć human-readable labeli z rolą i rodzajem;
- `location`: wyłącznie `label`, `city`, `country`, `country_code`;
- `attributes`: maksymalnie osiem nazwanych, skalarnych faktów.

Każdy tekst i każda kolekcja ma limit. Puste elementy nie są serializowane.
Domain converter wybiera treść; task packer wyłącznie waliduje, ogranicza i
serializuje już zatwierdzoną projekcję.

## Lineage i technical-ID firewall

Canonical fact w Outboxie nadal posiada `fact_id`, event/cycle identity i
backendową provenance. Packer mapuje canonical `fact_id` na task-local alias
`f01`, `f02` itd. Model kopiuje alias wyłącznie do `fact_refs`; validator mapuje
go z powrotem na canonical fact ID przed zapisem candidate.

Model-visible semantic content nie zawiera event/task/attempt/candidate/receipt
ID, cycle ID, hashed entity ID, opaque target ID ani DB ID. Shared contract
odrzuca wartości wyglądające jak wewnętrzne identyfikatory w labelach i
statement. `fact_ref` jest jedynym jawnym tokenem lineage i jest lokalnym
aliasem bez znaczenia narracyjnego.

Backendowa `semantic_provenance` zapisuje wyłącznie mapowanie semantic path →
canonical source path, bez kopii wartości i bez sekretów. Pozwala wyjaśnić,
dlaczego pole zostało dopuszczone, ale nigdy nie trafia do `messages[]`.

## Audience projection

Projection odbywa się przed zbudowaniem model package. Brak uprawnienia oznacza
brak pola, nie instrukcję „nie ujawniaj”. GhostNetwork używa istniejącego
`GhostVisibilityService` oraz domenowego convertera:

- public: opis publicznego zdarzenia, dozwolony publiczny target i bounded
  location; bez części, maszyny i prywatnego klanu;
- clan: publiczny opis oraz wyłącznie label własnego klanu, gdy projection
  potwierdza relację;
- owner: dozwolone canonical labels części, maszyny i klanu;
- brak canonical labela lub brak prawa widoczności: pole nie istnieje.

Kody `phantom_mesh`, `phantom_veil`, part codes i hashed public entity IDs nie
są zastępczymi labelami. Label jest pobierany z istniejącego katalogu; brak
labela kończy się pominięciem encji.

## Location inference i retention

Obsługiwane klucze OSM:

```text
city:         addr:city, city, is_in:city
country:      addr:country, country, is_in:country
country_code: addr:country_code, country_code, ISO3166-1:alpha2
```

Normalizacja:

- Unicode NFKC;
- redukcja whitespace i trim;
- casefold tylko do porównania;
- zachowanie pierwszej bounded wartości display;
- country code upper-case, maksymalnie 8 znaków;
- brak mapowania kodu państwa na nazwę i brak wnioskowania z koordynatów.

Reguła scan agreement jest konserwatywna:

1. analizowane są tylko źródłowe, nieproceduralne POI;
2. braki są ignorowane, ale raportowane przez bounded evidence counters;
3. pole jest przyjęte, gdy wszystkie niepuste obserwacje są zgodne oraz ma co
   najmniej dwie obserwacje;
4. wyjątek: skan zawierający dokładnie jeden źródłowy POI może przyjąć jego
   bezpośredni canonical tag;
5. dowolny konflikt albo zbyt mała liczba dowodów daje `UNKNOWN`, czyli brak
   pola w `location`.

Bezpośrednia bounded location pojedynczego POI może być przypisana temu POI.
Scan location jest fallbackiem dla markerów z tego samego response, w tym
obiektów proceduralnych. Nie zapisujemy całego response ani pełnych `tags`.

Minimalny `scan_context` zawiera wersję, promień, liczbę źródłowych POI,
bounded location i counters. Nie tworzymy trwałego subsystemu ani `scan_id`.

Przepływ retention:

```text
OSM tags
  -> bounded POI location + conservative scan context
  -> frontend target.location
  -> mark_target.location
  -> canonical target
  -> operation/capture
  -> GhostNetwork anchor.location
  -> audience-safe semantic_fact.location
```

## Relevance i failure policy

Converter domenowy wybiera wyłącznie fakty potrzebne dla danego event family,
intentu i audience. Nie kopiuje całych obiektów gameplay. Unknown, konflikt,
brak canonical labela lub niedozwolona widoczność powodują pominięcie pola.
Zasada: `UNKNOWN > GUESS`.

Brak wymaganego `statement`, nieznany klucz semantic, opaque ID w treści albo
przekroczenie limitu jest błędem fail-closed przed wywołaniem modelu. Brak
opcjonalnej location nie jest błędem.

## Compatibility i cutover

- v1 i v2 zachowują dotychczasowe prompty, package builder i resolution tuple;
- GhostNetwork v3 było pierwszym `chaos-llm-semantic-input-v1` consumerem;
- świeże GhostNetwork taski dostają v5, a v3/v4 pozostają semantic-compatible;
- już zapisane READY/RETRY_WAIT/CLAIMED v1/v2 pozostają claimowalne;
- alias jest mapowany do canonical fact ID przed candidate, więc publication i
  fact lineage nie zmieniają kontraktu;
- inne domeny zachowują obecne model input do czasu jawnego przepięcia. Shared
  contract dopuszcza domenowe entities/attributes, więc Googleplex Editorial
  nie traci product name/description/price/category.

## Observability

Audyt jednego taska składa się z:

```text
canonical facts in outbox
  -> semantic + semantic_provenance
  -> fact_ref_map held by worker
  -> exact model-visible semantic_facts
  -> candidate canonical fact_refs
```

Logi nie powinny drukować prywatnych semantic values. Bezpieczne telemetry to:
contract version, liczba semantic facts, obecność location, liczba provenance
entries, input bytes, prompt version, audience scope i wynik firewalla.

Read-only audyt najnowszego rzeczywistego `part_discovered`:

```bash
.venv/bin/python scripts/audit_semantic_input.py \
  --db data/game.sqlite3 \
  --strict
```

Audyt pojedynczego taska przyjmuje dodatkowo `--task-id`. Raport pokazuje
dokładny `model_input`, backendowe ścieżki provenance oraz wynik firewalla; nie
wykonuje generacji, nie zmienia taska i nie zapisuje semantic values w logach.

## Exit gate 137.pre.1

- shared contract istnieje i jest bounded;
- GhostNetwork jest pierwszym pełnym consumerem dla wszystkich aktywnych event
  families;
- location przechodzi POI → target → anchor → semantic fact;
- public/clan/owner są rozdzielone przed modelem;
- model nie widzi technical IDs jako semantic content;
- v1/v2 compatibility pozostaje aktywne;
- fact lineage, validator, budget i heavy-profile zero przechodzą testy;
- Sprint 137 pozostaje zatrzymany do lokalnego i następnie serwerowego exit
  gate 137.pre.1.
