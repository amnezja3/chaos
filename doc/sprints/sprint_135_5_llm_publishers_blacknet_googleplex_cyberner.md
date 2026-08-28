# Sprint 135.5 — LLM Publishers: BlackNet, Googleplex News and Cyberner

Status: `PLANNED / BLOCKED BY SPRINT 135.4.2`.

## Cel

Po raz pierwszy opublikować zaakceptowane odpowiedzi Ollamy graczom przez
kontrolowane adaptery BlackNet, Googleplex News oraz Cyberner/AI Central 2108.
Surowy output modelu, quarantine i rejected candidates nigdy nie trafiają do
UI.

Finalny zakres produktu 135.5 obejmuje również domknięcie dwóch przygotowanych
powierzchni Googleplex:

- uruchomienie newsów na Home zaprojektowanym w 135.4.1;
- udostępnienie owner-scoped wyniku w prostym, kupowanym narzędziu z 135.4.2.

## Warunek wejścia

- canonical queue i crash recovery ze Sprintu 135.2;
- bezpieczni producenci oraz app ingress ze Sprintu 135.3;
- realny worker, Inbox i validator ze Sprintu 135.4;
- Googleplex Home i News foundation ze Sprintu 135.4.1;
- kupowane narzędzie oraz bezpieczny task/status flow ze Sprintu 135.4.2.

135.5 nie projektuje tych powierzchni od zera. Wykorzystuje ich zatwierdzone
kontrakty i po raz pierwszy podłącza accepted model content. Nie wolno zastąpić
News wpisem w katalogu produktów ani mieszać jego filtrów z Googleplex/GX.

## Source of truth

```text
canonical domain facts
→ Outbox task
→ accepted Inbox candidate
→ publisher receipt
→ medium read model
```

Publisher może czytać wyłącznie candidate ze statusem `ACCEPTED`. Medium read
model przechowuje opublikowaną projekcję, ale nie zmienia faktów gameplayowych.

## Publication router

Router wybiera adapter po immutable `target_medium` z taska:

```text
blacknet
googleplex_news
cyberner
radio                    opcjonalnie
```

Model nie wybiera nowego medium ani audience. Mismatch między taskiem,
candidate i adapterem kończy się fail-closed przed publikacją.

## Publication receipt

Każda próba publikacji posiada trwały receipt:

```text
publication_receipt_id
candidate_id
task_id
target_medium
audience_scope/clan/owner
status
medium_record_id
attempt_count
last_error_code
created_at
updated_at
published_at
```

Unique `candidate_id + target_medium + audience` zapewnia exactly-once
semantics. Crash po zapisie medium record, ale przed acknowledgement, jest
domykany przez ten sam receipt/medium ID, bez drugiej publikacji.

## BlackNet publisher

Accepted candidate trafia do mixed feed jako jawnie oznaczone źródło:

```text
source = ollama_enriched
truth_class
fact_refs
canonical publication receipt
```

Invariants:

- deterministic signals pozostają dostępne i nie są zastępowane;
- sortowanie/paginacja nie faworyzują bez limitu treści Ollamy;
- candidate nie może nadpisać istniejącego canonical signal;
- CTA przechodzi przez istniejący dispatcher i jego allowlistę;
- filtr BlackNet nie miesza stanu Googleplex ani Ghost Exchange;
- brak Ollamy/publishera nie powoduje pustego BlackNetu.

## Googleplex News publisher

Publisher zachowuje kontrakt produktu zamknięty w 135.4.1:

- jednoznaczna nazwa i launcher/zakładka;
- read model oddzielny od katalogu aplikacji i zakupów;
- audience public/clan/owner;
- paginacja oraz bounded retention;
- źródło, truth class i timestamp;
- bezpieczne CTA;
- niezależny state/input/filter od Googleplex catalog, GX i BlackNet;
- zachowanie przy braku Ollamy.

Googleplex News nie może zmieniać ceny, instalacji, inventory ani receipt zakupu.
Dedykowana aplikacja z 135.4.2 może otworzyć własny owner-scoped wynik, ale nie
może automatycznie promować go do publicznego feedu.

Publisher podłącza accepted candidates do read modelu przygotowanego w 135.4.1
i aktywuje sekcję News na Googleplex Home. Empty/deterministic fallback nadal
działa, gdy Ollama lub publisher są niedostępne.

## Publisher wyniku w kupowanym narzędziu

Narzędzie ze Sprintu 135.4.2 otrzymuje owner-scoped result projection:

```text
receipt_id
publication_receipt_id
source/truth_class
title/body
created_at/published_at
approved CTA
```

- tylko owner taska może pobrać wynik;
- wynik pochodzi wyłącznie z accepted Inbox candidate;
- retry/reopen/relogin pokazuje ten sam publication receipt;
- uninstall blokuje launcher i nowe taski, ale zachowanie historycznego wyniku
  musi być jawnie ustalone przez product retention policy;
- narzędzie może skierować do Cyberner AGI 2108 lub Googleplex News wyłącznie
  przez canonical receipt/publisher, nie przez frontendowy copy;
- raw output, prompt, validation i quarantine pozostają niewidoczne.

## Cyberner / AI Central / AGI 2108 publisher

Publisher używa istniejącej infrastruktury Cybernera i jawnego systemowego
źródła `AI Central`, rozszerzonego o stabilny kanał/identity AGI 2108.

Invariants:

- public, clan i owner messages trafiają wyłącznie do właściwej audience;
- owner-scoped odpowiedź aplikacji nie trafia do WORLD ani innego gracza;
- backend ustala nadawcę, autentyczność i wynik odpowiedzi z 2108;
- Ollama zapewnia język, ton i kontekst, ale nie podszywa się pod canonical
  system message bez odpowiedniego source/truth label;
- retry nie tworzy dwóch wiadomości ani dwóch unread notifications;
- istniejące direct notifications nadal działają bez Ollamy.

## Opcjonalny Radio publisher

Radio pozostaje adapterem opcjonalnym i nie może blokować podstawowych trzech
mediów. Tekst może zostać przekazany do osobnego kontraktu TTS dopiero po
accepted candidate i publication receipt. Sprint nie rozszerza się automatycznie
o nowy system syntezy głosu.

## Prepublish guard

Tuż przed zapisem publisher sprawdza:

- candidate nadal `ACCEPTED`;
- task/candidate medium i audience są zgodne;
- visibility-sensitive target nadal może otrzymać komunikat;
- CTA nadal należy do allowlisty i wskazuje opaque/canonical target;
- receipt nie ma już skutecznej publikacji.

Guard nie przelicza faktów przez pełny profil. Używa bounded identity,
entitlement i visibility projections. Zmiana relacji może zawęzić lub odrzucić
publikację, nigdy poszerzyć audience.

## Fallback i niezależność mediów

- awaria jednego adaptera nie blokuje innych tasków/mediów;
- retry jest per publication receipt;
- deterministic BlackNet/System/Cyberner content działa bez modelu;
- fallback nie udaje odpowiedzi Ollamy i ma jawne źródło;
- dead-letter publikacji nie cofa accepted candidate ani gameplayu;
- backpressure publishera nie blokuje Flask requestów i workerów gameplayowych.

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

### Exactly once

- accepted candidate → jeden medium record i jeden published receipt;
- concurrent publishers → jedna publikacja;
- crash po medium insert przed receipt update → recovery bez duplikatu;
- ponowny start publishera → brak replayu terminalnych receiptów;
- quarantined/rejected candidate → zero publikacji.

### BlackNet

- deterministic + `ollama_enriched` mixed feed;
- źródło/truth class/fact refs zachowane;
- brak nadpisania canonical signal;
- CTA tylko z allowlisty;
- brak Ollamy → deterministic feed działa.

### Googleplex News

- oddzielny state/filter/tab od katalogu, GX i BlackNet;
- public/clan/owner audience bez cross-account leak;
- brak wpływu na install/purchase/wallet;
- owner app result nie staje się publiczny;
- paginacja i retention są bounded.

### Kupowane narzędzie

- accepted owner candidate → jeden result receipt widoczny dla ownera;
- konto B nie może odczytać wyniku konta A;
- reopen/relogin → ten sam wynik bez ponownego model call;
- retry publishera → brak zduplikowanego wyniku;
- uninstall/new request policy zachowuje canonical entitlement;
- quarantined/rejected candidate → controlled failure status, zero body;

### Cyberner AGI 2108

- owner response widzi tylko owner;
- clan response widzi tylko właściwy klan;
- public response trafia do zatwierdzonego kanału;
- retry → jedna wiadomość i jedna unread notification;
- sender/authenticity/outcome są zgodne z canonical facts;
- direct Cyberner flow działa przy wyłączonej Ollamie.

### Visibility/performance

- audience cutover przed publikacją → fail-closed;
- hidden facts nie pojawiają się w żadnym medium ani logu;
- profil 35 MB → zero full-profile read/write/bytes;
- duży backlog receiptów → bounded indexed query;
- awaria adaptera → brak wpływu na gameplay i inne media.

## Walidacja

- pełna regresja Outbox/lease 135.2;
- producer/app ingress 135.3;
- worker/Inbox/validator 135.4;
- BlackNet mixed feed i CTA;
- Googleplex/GX/BlackNet state isolation;
- Cyberner channels/unread/audience;
- map/GhostNetwork regression dla CTA;
- `py_compile`;
- `node --check` dla zmienionych klientów;
- `git diff --check`.

## Poza zakresem

- nowe mechaniki gameplayowe generowane przez LLM;
- wykonywanie dowolnych narzędzi przez model;
- automatyczna moderacja zmieniająca canonical facts;
- cloud LLM;
- pełny TTS/podcast, jeśli nie ma osobnego kontraktu;
- ręczne SQL hotfixy;
- deploy, restart PM2 i produkcyjne mutacje bez zgody.

## Exit gate

`ACCEPTED INBOX CANDIDATE → EXACTLY ONE SAFE PUBLICATION TO THE RIGHT AUDIENCE`

Po spełnieniu bramki: `SPRINT 135.5 — READY FOR SERVER VALIDATION`, a po
potwierdzeniu `READY FOR SPRINT 135.6`.


