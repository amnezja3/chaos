# Sprint 135.4.2 — Purchasable Googleplex LLM Tool

Status: `PLANNED / BLOCKED BY SPRINT 135.4.1`.

## Cel

Stworzyć proste narzędzie kupowane i instalowane z Googleplex, które pozwala
graczowi zlecić zatwierdzony task narracyjny przez ingress Sprintu 135.3 oraz
śledzić jego techniczny status. Sprint nie publikuje jeszcze treści odpowiedzi
modelu — to następuje w 135.5.

## Decyzje produktowe do zamknięcia na początku sprintu

Przed implementacją należy zatwierdzić:

```text
product_id / app_id
nazwa in-world
ikona i rodzina produktu
cena HC
target/fallback sprzedawcy
approved template set
limity użycia i ewentualny koszt pojedynczego taska
domyślny kanał wyniku: owner-scoped Cyberner AGI 2108 / aplikacja
```

Nie należy wprowadzać roboczej nazwy, ceny ani odbiorcy jako ukrytego fallbacku.
Po zatwierdzeniu wartości trafiają do canonical app/product config.

## Warunek wejścia

- app ingress, entitlement, receipt i session/precommit guard z 135.3;
- działający Outbox/worker/Inbox z 135.2-135.4;
- Googleplex Home i izolacja stanów z 135.4.1;
- canonical uninstall nie pozostawia launchera w Menu Start.

## Product lifecycle

```text
Googleplex product
→ purchase receipt
→ canonical PlayerInventoryStore installation
→ launcher w Menu Start
→ app window
→ approved task request
→ accepted task receipt/status
```

Zakup, instalacja i uninstall korzystają ze wspólnego Googleplex/inventory
contract. Narzędzie nie tworzy własnej listy aplikacji w profilu.

Retry purchase/install:

- nie pobiera HC drugi raz;
- nie zajmuje storage drugi raz;
- zwraca ten sam canonical receipt;
- nie tworzy dwóch launcherów;
- uninstall usuwa entitlement i launcher bez full-profile write.

## Zakres aplikacji

Minimalny interfejs:

- wybór jednego z zatwierdzonych template;
- bounded pola wejściowe przewidziane dla template;
- przycisk wysłania;
- kontrolowane potwierdzenie kosztu, jeśli występuje;
- receipt/task ID w skróconej postaci;
- status: `accepted`, `queued`, `processing`, `completed`, `failed`;
- retry UI wyłącznie zgodnie z canonical receipt policy;
- link do Googleplex News albo Cybernera pozostaje nieaktywny do czasu
  publikacji w 135.5.

Nie ma pola „system prompt”, wyboru modelu, URL ani dowolnej audience/CTA.

## Request call chain

```text
installed app action
→ active session-generation precheck
→ bounded entitlement check
→ template/input validation
→ rate/quota/cost policy
→ canonical action receipt
→ session-generation precommit check
→ enqueue task through 135.3 ingress
→ accepted response
```

Frontend nigdy nie wywołuje Ollamy bezpośrednio. Zamknięcie okna, refresh lub
relogin nie tworzy nowego taska. Status jest odtwarzany po receipt/task ID.

## Status projection

Aplikacja dostaje wyłącznie bezpieczny owner-scoped status:

```text
receipt_id
task_public_id
status
submitted_at
updated_at
retryable
user_message
```

Nie dostaje `claimed_by`, lease internals, promptu, raw outputu, validation
payload ani treści quarantined candidate.

W 135.4.2 status `completed` oznacza, że Inbox candidate został przetworzony,
ale jego body nie jest jeszcze publikowane w aplikacji. 135.5 dodaje
owner-scoped result projection i publication receipt.

## Bezpieczeństwo

- aplikacja musi być zainstalowana w canonical inventory;
- owner widzi tylko własne task receipts;
- replaced/stale session nie może wysłać ani ponowić taska;
- template i target medium są backend allowlist;
- public publication nie jest domyślna;
- rate limit i quota są per account oraz app action;
- task request nie czyta pełnego profilu;
- output modelu nigdy nie jest wykonywany jako HTML/JS lub command;
- launcher nie utrzymuje danych poprzedniego konta po relogin.

## Integracja z Googleplex Home

- produkt może pojawić się w Featured według canonical config;
- karta produktu korzysta ze wspólnego purchase/install UX;
- Home, Catalog i okno narzędzia mają osobny state;
- instalacja nie resetuje feedu News ani filtrów katalogu;
- po zakupie launcher jest widoczny bez ciężkiego profile refreshu;
- odinstalowanie usuwa launcher i blokuje następny request.

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

### Purchase/install/uninstall

- zakup z wystarczającym HC → jeden receipt i jedna instalacja;
- retry zakupu → brak drugiej płatności;
- brak HC/requirements/session conflict → canonical system message;
- uninstall → brak launchera i brak entitlement;
- reinstall → nowy legalny lifecycle bez starego UI state;
- 35 MB profile fixture → zero full-profile read/write/bytes.

### Task submission

- installed app + valid template → jeden accepted task;
- brak instalacji → zero tasków;
- duplicate submit receipt → ten sam task;
- stale/replaced session → zero tasków;
- session cutover przed commit → zero tasków;
- arbitrary prompt/model/audience/CTA/URL → reject;
- quota/rate limit → controlled message i zero nieautoryzowanych tasków;
- zamknięcie/reopen app → status tego samego taska.

### Privacy/UI

- konto B nie widzi receipts konta A;
- relogin czyści owner-scoped app state;
- raw output/quarantine/lease fields nie trafiają do frontend;
- completed przed 135.5 nie pokazuje body modelu;
- Googleplex/GX/BlackNet filters pozostają niezależne;
- mobile ma jeden scroll i dostępne wszystkie kontrolki.

## Walidacja

- Googleplex purchase/install/uninstall/inventory regression;
- session generation i precommit guard;
- Outbox dedupe/lease 135.2;
- app ingress 135.3;
- worker/Inbox status 135.4;
- Home/state isolation 135.4.1;
- `py_compile`;
- `node --check`;
- `git diff --check`.

## Poza zakresem

- wyświetlenie model-generated body;
- publikacja do Googleplex News, BlackNet lub Cybernera;
- dowolny prompt i narzędzia wykonywane przez model;
- publiczne taski bez zatwierdzonej policy;
- nowe mechaniki gameplayowe;
- deploy, restart PM2 i produkcyjne mutacje.

## Exit gate

`PURCHASED APP → ONE SAFE TASK RECEIPT / ZERO MODEL CONTENT PUBLISHED`

Po spełnieniu bramki: `SPRINT 135.4.2 — READY FOR SERVER VALIDATION`, a po
potwierdzeniu `READY FOR SPRINT 135.5`.


