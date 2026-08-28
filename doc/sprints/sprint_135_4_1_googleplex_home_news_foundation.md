# Sprint 135.4.1 — Googleplex Home and News Foundation

Status: `PLANNED / BLOCKED BY SPRINT 135.4`.

## Cel

Zaprojektować i zbudować nową stronę główną Googleplex z wydzieloną sekcją
News oraz bezpieczny read model tej sekcji. Sprint przygotowuje powierzchnię
publikacji, ale nie publikuje jeszcze treści Ollamy.

## Warunek wejścia

- canonical Outbox ze Sprintu 135.2;
- producenci i Googleplex app ingress ze Sprintu 135.3;
- canonical Inbox oraz validator ze Sprintu 135.4.

Googleplex Home nie może czytać bezpośrednio Outboxa, surowego outputu modelu
ani quarantine. Docelowo czyta wyłącznie osobny publication read model z 135.5.

## Zakres produktu

Googleplex otrzymuje jednoznaczną stronę główną, która rozdziela:

```text
HOME
├── NEWS
├── FEATURED / polecane produkty
├── CATALOG / aplikacje i bilety
└── status własnych instalacji
```

Sekcja News jest częścią Googleplex, ale nie katalogiem produktów. Nie może
zmieniać filtrów, wyszukiwania ani aktywnej zakładki Ghost Exchange i BlackNet.

## Kontrakt Googleplex Home

Home page zawiera:

- lekki nagłówek i bieżący kontekst Googleplex;
- bounded listę najnowszych newsów;
- osobną sekcję polecanych produktów;
- wejście do pełnego katalogu;
- jasne oznaczenie źródła i czasu każdego newsa;
- responsywny layout z jednym głównym scrollem;
- kontrolowany empty/loading/error state;
- brak automatycznego otwierania mapy lub wykonywania CTA podczas renderu.

Stan UI jest izolowany:

```text
googleplex_home_state
googleplex_news_state
googleplex_catalog_state
ghost_exchange_state
blacknet_state
```

Zmiana filtra lub zakładki w jednym produkcie nie modyfikuje pozostałych.

## News read model

Minimalny rekord:

```text
news_id
publication_receipt_id
source
truth_class
title
summary/body_excerpt
published_at
audience_scope
cta
```

Read model nie zawiera promptu, raw model output, validation details, hidden
facts ani wewnętrznych identyfikatorów części/targetów. CTA używa istniejącego
opaque/canonical dispatcher contract.

Endpoint/read service jest:

- paginowany i bounded;
- sortowany stabilnie po `published_at + news_id`;
- audience-projected;
- cache-keyed co najmniej po viewer/audience revision i page cursor;
- fail-closed przy nieznanej audience;
- niezależny od pełnego profilu i katalogu produktów.

W 135.4.1 może zwracać pustą listę albo kontrolowane deterministyczne fixture.
Nie czyta accepted Inbox candidate jako publikacji. Produkcyjny zapis newsów
zostaje podłączony dopiero w 135.5.

## Projekt interfejsu

Desktop:

- Home otwiera się jako domyślny widok Googleplex;
- News i Featured są widoczne bez mieszania ich z tabelą katalogu;
- przejście do produktu zachowuje normalny purchase/install flow;
- powrót do Home nie przenosi filtrów z katalogu.

Mobile:

- jeden pionowy scroll całego okna;
- brak nested scrolli dla samego feedu;
- nagłówek i przełączniki nie zajmują większości viewportu;
- CTA i karty nie wychodzą poza szerokość;
- focus/keyboard nie resetuje pozycji listy.

## Audience i privacy

Sekcja News przygotowuje obsługę:

- `public`;
- `clan`;
- `owner`.

Publiczny viewer nigdy nie otrzymuje clan/owner record, nawet jeśli frontend
ukryłby kartę CSS. Projekcja następuje w backendzie. Zmiana sesji lub konta nie
może użyć cache poprzedniego viewera.

## Twarda bramka heavy-profile

Każdy nowy endpoint, worker, producer, publisher i read model tego sprintu musi
spełniać kontrakt
`doc/architecture/profile_hot_path_contract_130_11_plus.md`.

Zakazane w hot path:

- `load_profile*`, `get_profile()`, `list_profiles()` i skan wszystkich kont;
- parsowanie `profile_json` per task, odbiorca, karta, news albo publikacja;
- pełny profile read/write jako sposób odczytu identity, entitlement, walletu,
  inventory, sesji, audience albo statusu aplikacji;
- cache pełnego profilu jako nowy source of truth.

Dozwolone są wyłącznie canonical bounded stores, receipts, lekkie identity i
audience projections oraz indeksowane batch lookupy. Obowiązkowa regresja z
profilem syntetycznym co najmniej 35 MB musi wykazać:

```text
profile_full_read = 0
profile_full_write = 0
profile_bytes = 0
all_user_profile_scan = 0
per_recipient_profile_read = 0
```

## Obowiązkowe testy

### UI/state isolation

- wejście Googleplex → Home jest domyślnym widokiem;
- Home → Catalog → Home zachowuje niezależne stany;
- filtr Googleplex nie zmienia GX/BlackNet;
- filtr GX/BlackNet nie zmienia Googleplex News;
- empty/loading/error state nie powoduje `catalog.filter` crash;
- mobile ma jeden główny scroll i pełny dostęp do Home/News/Catalog.

### Read model

- paginacja jest stabilna i bounded;
- public/clan/owner projection nie przecieka między kontami;
- cache key zmienia się po viewer/session/audience cutover;
- brak prompt/raw output/quarantine/hidden fact fields;
- CTA jest wyłącznie z canonical allowlisty;
- duży zbiór historycznych newsów nie uruchamia pełnego skanu.

### Brak publikacji przed 135.5

- accepted Inbox candidate nie pojawia się automatycznie w Home;
- quarantine/rejected candidate nigdy nie pojawia się w Home;
- brak Ollamy pokazuje poprawny empty/deterministic state;
- otwarcie Home nie wykonuje requestu do Ollamy.

## Walidacja

- testy Googleplex catalog/purchase/install;
- testy GX/BlackNet/Googleplex state isolation;
- testy audience/session cache isolation;
- testy responsywne i `node --check`;
- backend read-model tests i `py_compile`;
- `git diff --check`.

## Poza zakresem

- publikacja accepted candidate;
- uruchamianie modelu z Home;
- formularz narzędzia LLM ze Sprintu 135.4.2;
- zmiana cen, walletu i instalacji aplikacji;
- nowe mechaniki gameplayowe;
- deploy, restart PM2 i produkcyjne mutacje.

## Exit gate

`GOOGLEPLEX HOME + SAFE NEWS READ SURFACE / ZERO OLLAMA PUBLICATION`

Po spełnieniu bramki: `SPRINT 135.4.1 — READY FOR SERVER VALIDATION`, a po
potwierdzeniu `READY FOR SPRINT 135.4.2`.


