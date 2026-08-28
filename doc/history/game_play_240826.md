# game_play_240826.md

Kontynuacja planu z `doc/history/game_play_180726.md`.

cały pakiet **130.12.1–130.12.4**
Pierwsze trzy wynikają bezpośrednio z audytu gameplayowego, a `130.12.4` proponuję jako końcowy sprint walidacyjny/cutover, żeby 130.12 nie wisiał potem znowu w stanie „prawie skończony”.

---

# Sprint 130.12.1 — Single Active Login / Session Ownership P0

**Status bieżący:** SPRINT 130.12.1 — COMPLETE
**Priorytet:** P0
**Cel:** jedno konto może mieć tylko jedno aktywne, niezależne logowanie. Najnowsze poprawne logowanie zawsze wygrywa.

## Problem

Obecny `session_generation` chroni requesty przed stale generation, ale jawnie dopuszcza równoczesne aktywne sesje tego samego konta w dwóch niezależnych przeglądarkach/urządzeniach.

Dodatkowo lifecycle nie domyka poprawnie:

```text
login
→ inactivity/logout
→ ponowny login
```

co prowadzi do:

* `CHAOS // SESSION GATE`,
* `409 CONFLICT`,
* konieczności czyszczenia cookies/cache,
* 409 na `/resources.json`,
* 409 na `/api/profile/desktop`,
* części wtórnych błędów Googleplex/Webdragon/UI.

Audit potwierdził, że obecny kontrakt posiada testy zakładające równoległe aktywne lineages tego samego konta. Ten kontrakt zostaje zmieniony.

## Docelowy invariant

```text
ONE ACCOUNT = ONE ACTIVE LOGIN SESSION
```

Kilka kart tej samej sesji przeglądarki pozostaje dozwolone.

Oddzielna przeglądarka lub urządzenie oznacza nowe logowanie i przejęcie konta.

## Model

Rozszerzyć istniejący `SessionGenerationStore`. Nie tworzyć drugiego, równoległego systemu.

Account-level source of truth:

```text
username_hash
active_login_id_hash
active_revision
status
updated_at
```

Lineage:

```text
lineage_hash
generation_hash
username_hash
login_id_hash
account_revision
status
revision
invalidated_at
last_reason
```

Stany:

```text
active
replaced
logged_out
expired
```

Timestamp nie jest source of truth. O kolejności decyduje monotoniczna revision.

## Login

Przy poprawnym nowym logowaniu:

```text
BEGIN IMMEDIATE

account_revision += 1
poprzednie active lineages -> replaced
nowe login identity -> active
account.active_login_id = nowe login identity

COMMIT
```

Dopiero potem:

* rotate Flask SID,
* ustaw cookie/session,
* zwróć generation.

Najnowszy poprawnie zakończony login wygrywa.

## Request guard

Każdy mutujący request musi sprawdzić:

```text
lineage
generation
username
account_revision
active login identity
```

dwukrotnie:

1. przed rozpoczęciem pracy,
2. bezpośrednio przed canonical commit.

Scenariusz:

```text
A rozpoczyna request
→ B loguje się
→ B przejmuje account revision
→ A dochodzi do commit
→ precommit A FAIL CLOSED
```

Zero mutacji A.

## Logout / timeout

Logout ma być CAS-safe.

Stara sesja A po przejęciu konta przez B nie może wylogować B.

```text
logout A
WHERE active_login_id = A
AND account_revision = revision_A
```

Jeśli warunek nie pasuje:

```text
0 rows affected
```

i B działa dalej.

Timeout/relogin musi działać bez ręcznego czyszczenia cookies.

## Login recovery

Stale/revoked cookie nie może blokować samego endpointu loginu.

Login/relogin musi mieć możliwość bezpiecznego przejścia:

```text
stale authenticated cookie
→ anonymous/login recovery
→ new authenticated generation
```

Nie osłabiać przy tym guardów gameplay API.

## `/resources.json`

Nie dodawać obecnego endpointu po prostu do `PUBLIC_ENDPOINTS`.

Audit potwierdził, że:

```text
/resources.json
→ sync_session_profile()
```

więc endpoint nie jest faktycznie statycznym/publicznym resource.

Rozdzielić:

```text
public catalog
```

od:

```text
account-scoped catalog/projection
```

Publiczny katalog:

* bez generation,
* bez pełnego profilu,
* bounded.

Account-scoped projection:

* authenticated,
* generation protected,
* kontrolowany błąd session.

Frontend musi sprawdzać:

```text
response.ok
Array.isArray(payload)
```

`catalog` nigdy nie może dostać JSON error object.

## `/api/profile/desktop`

Zachować generation/CAS.

Przy 409:

* frontend nie oznacza zapisu jako successful,
* lokalny UI nie może przyjąć niezapisanego tile scheme jako canonical.

Po reloginie scheme pochodzi z ostatniego potwierdzonego stanu serwera.

## Session UI

Rozróżnić:

```text
SESSION_REPLACED
SESSION_EXPIRED
SESSION_LOGGED_OUT
SESSION_STALE
SESSION_MISSING_GENERATION
```

Dla `SESSION_REPLACED`:

```text
Konto zostało zalogowane na innym urządzeniu.
```

Następnie kontrolowane przejście do loginu.

Bez nieskończonego SESSION GATE.

## Precommit matrix

Zweryfikować co najmniej:

```text
/api/profile/security
/api/profile/desktop
/api/profile/account

/api/wallet/transfer
/api/ghost-exchange/*

/api/map/aim-target
/api/victim-picker/aim
/api/map/player-targets/mark
/map-action
/hack-action

/secure-action
/secure-preset
/api/map/captured-object/abandon
/api/ghost-control/territory/*

/command
/gonna-win
operation cancel endpoints

/api/blacknet/cta/teleport

contacts
chats
system messages
install/uninstall
GhostLab mutation endpoints
```

Dla każdego ustalić, czy posiada prawdziwy guard w tej samej transakcji co canonical write.

## Obowiązkowe testy

```text
A login → B login → A blocked
A request starts → B login → A precommit blocked
logout A po B nie wylogowuje B
timeout → relogin bez cookie-clear
2 karty tej samej browser session działają
2 browsery → najnowszy login wygrywa
równoległe B/C login → ostatni commit wygrywa
stary wallet request nie mutuje
stary profile request nie mutuje
stary territory request nie mutuje
stara finalizacja operation nie mutuje
public catalog działa bez generation
account catalog ma kontrolowany session failure
catalog nigdy nie dostaje error object
desktop 409 nie zapisuje lokalnego fake-success
```

Usunąć/zmienić stare testy wymagające niezależnej aktywności dwóch lineages tego samego usera.

## Performance

Nie wolno wprowadzić:

```text
full profile read
full profile write
sync_session_profile w guardzie
globalnego skanu sesji
długiego BEGIN IMMEDIATE
```

Account ownership lookup musi być bounded.

## Definition of Done

```text
single active login działa
relogin nie wymaga cookie-clear
logout stale session nie rusza current session
precommit race jest zabezpieczony
/resources catalog boundary uporządkowany
desktop state zachowuje canonical confirmation
testy zielone
py_compile OK
node --check OK
git diff --check OK
```

Końcowy status:

```text
SPRINT 130.12.1 — COMPLETE
```

Bez deployu bez jawnej zgody.

## Checkpoint implementacyjny — 2026-08-24

Lokalnie wdrożono:

* atomowy account ownership w rozszerzonym `SessionGenerationStore`,
* monotoniczną account revision i lifecycle `ACTIVE/REPLACED/LOGGED_OUT/EXPIRED`,
* CAS-safe logout oraz request/precommit ownership guard,
* relogin i kontrolowany `/session/recover` bez czyszczenia cookies,
* publiczny `/resources.json` oddzielony od chronionego `/api/catalog`,
* fail-closed frontend catalog oraz canonical-confirmed map tile scheme,
* regresje A/B, B/C, stale precommit, dwie karty jednego SID oraz rollback
  profile/wallet/territory/operation.

Walidacja lokalna:

```text
294 targeted tests OK
session generation JS isolation OK
py_compile OK
node --check OK
```

Pełne discovery: `1055` testów, `6` istniejących failure/error poza diffem
130.12.1 (captured-object helper, GN post-130 fixture, dwa kontrakty GN map layer,
hot-path aim target i static profile writer contract).

Manual produkcyjny potwierdził latest-login-wins, kontrolowane zastąpienie starej
sesji, relogin bez czyszczenia cookies/cache, współdzielenie jednej sesji przez
kilka kart, fail-closed stale requests oraz poprawne granice katalogu i desktop
tile state. Werdykt: `SPRINT 130.12.1 — COMPLETE`.

---

# Sprint 130.12.2 — Map / Territory / GhostNetwork / Operation Integrity P0

**Status bieżący:** SPRINT 130.12.2 — READY FOR SERVER REVALIDATION
**Priorytet:** P0

## Cel

Usunąć dwie klasy błędów blokujących realny gameplay:

1. Leaflet/GN renderer crash `undefined.x`,
2. niespójność finalizacji aplikacji/OFS i `/gonna-win`.

Oba problemy są P0, ale niezależne przyczynowo.

---

## Część A — Leaflet / GhostNetwork renderer

### Problem

Powrócił:

```text
Bounds.js:150
Cannot read properties of undefined (reading 'x')
```

Call chain:

```text
GN snapshot/delta
→ renderGhostConnections()
→ updateGhostConnectionLayer()
→ layer.addTo(map)
→ Polyline._clipPoints()
→ Bounds.intersects()
→ undefined.x
```

Skutki:

* GN snapshot fail,
* map boot scope fail,
* biały/zepsuty overlay,
* częściowe warstwy,
* blokada pan/zoom,
* territory refresh może zostać przerwany.

Historyczny guard istnieje, ale sprawdza bounds tylko przed wejściem do `originalClipPoints()`. Bounds może się zmienić już podczas clippingu.

## Fix contract

`_clipPoints` musi być fail-closed.

Jeśli renderer/bounds są nieważne:

```text
_parts = []
return safely
```

Jeżeli `originalClipPoints()` rzuci wyjątek spowodowany invalid renderer bounds:

* wyczyść `_parts`,
* nie propaguj wyjątku do głównego map loop,
* nie blokuj drag/zoom.

Nie maskować innych, niezwiązanych wyjątków bez diagnostyki.

## Atomic GN layer replacement

Obecnie stara warstwa może zostać usunięta zanim nowa zostanie poprawnie dodana.

Nowy model:

```text
build candidate layer
→ validate/add successfully
→ dopiero wtedy replace previous layer
```

Jeżeli candidate fail:

```text
zachowaj previous valid layer
```

## Territory snapshot recovery

Problem:

```text
delta
→ request snapshot recovery
→ refreshPlayerAreas
→ in_flight / aborted
→ false
→ retry zależy od caller
```

Wprowadzić deterministyczną koordynację:

* jeden owner recovery,
* dedupe requestów,
* retry po `in_flight`,
* retry po `aborted`,
* bounded backoff,
* newest refresh sequence wins,
* critical recovery nie może zostać na zawsze pominięte przez optional refresh.

## Testy mapy

```text
GN render zanim renderer ready
bounds zmieniają się podczas _clipPoints
GN snapshot + zoom jednocześnie
territory delta podczas GN render
optional refresh + critical recovery race
aborted snapshot → deterministic retry
in_flight snapshot → deterministic retry
exception GN nie blokuje pan
exception GN nie blokuje zoom
previous valid connection layer pozostaje po candidate failure
```

---

## Część B — Operation finalization / OFS

### Problem

Objaw:

```text
SFX ogłasza sukces hacku
→ aplikacja jeszcze działa
→ kolejny /gonna-win albo generation mismatch
→ 409
→ OFS pokazuje czerwony failed/end
```

Audit wykazał, że istnieje kilka legalnych ścieżek `/gonna-win`, a receipts mogą mieć różne `receipt_scope`. Sama obecność dwóch requestów nie dowodzi podwójnej mutacji.

Potrzebna jest korelacja semantyczna.

## Telemetryka

Dla każdego flow logować bounded:

```text
flow_id
launch_receipt
receipt_key
receipt_scope
operation_id
request_ordinal
response_status
receipt_result
generation_result
OFS terminal state
SFX terminal state
```

Bez pełnego payload dump.

## Jeden lifecycle owner

Jedna warstwa odpowiada za terminal state OFS.

Nie może być:

```text
success SFX
+
późniejszy transport error
=
FAILED GAMEPLAY
```

Jeżeli canonical effect został już potwierdzony:

* replay receipt = idempotent success,
* późniejszy stale request nie zmienia semantic result.

## 409 generation

Generation mismatch:

* przekazuje sterowanie do session UI,
* nie jest zwykłym gameplay failure,
* nie generuje czerwonego OFS failure po potwierdzonym canonical success.

## Receipt replay

Replay dokładnie tej samej semantic operation:

```text
same receipt / same operation
→ same operation_id
→ duplicate=true/replayed=true
→ UI success/complete
```

Nie tworzy nowej operation.

## Testy operations

```text
1 semantic operation → max 1 canonical operation
receipt replay → ten sam operation_id
success SFX + późniejszy stale response → brak fake failure
generation 409 → session transition, nie OFS red end
operation_only + normal scope zachowują istniejący intentional contract
crash/retry po receipt write → exactly-once
OFS terminal success renderowany dokładnie raz
```

## Definition of Done 130.12.2

## Implementacja lokalna i walidacja

- Historyczny fix `undefined.x` z commita
  `ecaa77ea36e187f06783dc38b891934608914d76` został rozszerzony o kontrolowane
  przechwycenie wyłącznie transient race wewnątrz `originalClipPoints()`;
  niezwiązane wyjątki nadal są propagowane.
- Snapshot GhostNetwork jest podmieniany atomowo. Niepoprawny marker lub curve
  usuwa wyłącznie candidate layers i zachowuje poprzedni poprawny snapshot.
- Territory areas stosują candidate-first replacement. Niepełny, niepoprawny
  albo zduplikowany candidate nie usuwa poprzednich polygonów.
- Recovery territory ma jednego promise ownera, bounded backoff i współdzieli
  cały aktywny `refreshPlayerAreas`, dzięki czemu odpowiedź snapshotu jest
  konsumowana dokładnie raz również w race optional refresh / critical recovery.
- `/gonna-win` raportuje bounded `flow_id`, hashe receiptów, `receipt_scope`,
  `operation_id`, `request_ordinal`, status i wynik receipt. Replay zachowuje ten
  sam canonical `operation_id`.
- OFS ma jednego terminal ownera dla semantic receipt. Późniejszy false payload
  lub transport error nie nadpisuje wcześniej potwierdzonego canonical success.
- Walidacja lokalna: 169 celowanych testów Python — OK; regresje Node map/GN,
  snapshot recovery, delta client, OFS composer i gonna-win lifecycle — OK;
  `py_compile`, `node --check` i `git diff --check` — OK.
- Nie wykonano deployu ani restartu PM2. Zakres P1 130.12.3 pozostał nietknięty.

```text
undefined.x nie blokuje mapy
GN snapshot może się bezpiecznie ponowić
territory recovery zawsze kończy się snapshotem albo kontrolowanym failure
pan/zoom działa po renderer race
OFS nie pokazuje false failure po canonical success
/gonna-win lifecycle jest obserwowalny i exactly-once
```

Końcowy status:

```text
SPRINT 130.12.2 — READY FOR SERVER REVALIDATION
```

## Korekta po pierwszej walidacji serwerowej

Manual produkcyjny wykazał dwa sprzężone objawy pierwszego uruchomienia:

- opóźniony Trace Compass na filarze konfliktu kończył `/gonna-win` przez `409`,
  chociaż ponowne uruchomienie przechodziło;
- Browser i zapis stanu pulpitu mogły otrzymać `409` podczas równoległych zapisów
  profilu.

Root cause operacji: mapa przekazywała kanoniczne `target_id/conflict_id`, lecz
`/hack-action` gubił je w `pending_action`, a frontend redukował
`expected_target` do pozycji i etykiety. Ostatnie z kilku równoległych narzędzi
nie mogło więc rozpoznać przejętego filaru jako tego samego celu.

Root cause Browser/Desktop: `/api/catalog` wykonywał normalizujący zapis profilu
na ścieżce odczytu, a `/api/profile/desktop` zapisywał projekcję z potencjalnie
nieaktualnego snapshotu. Katalog jest teraz read-only, a desktop stosuje mały
CAS-safe patch z bounded retry i rebase na najnowszej rewizji.

Regresje obejmują zachowanie kanonicznej tożsamości filaru przez picker i
`expected_target`, read-only catalog oraz pierwszy konflikt CAS zapisu pulpitu.
Bez deployu, restartu PM2 i commita.

## Zamknięcie Sprintu 130.12.2 po manualu produkcyjnym

**Status końcowy:** `SPRINT 130.12.2 — COMPLETE`

- Powracający 409 ostatniej kropki filaru został ostatecznie przypisany do
  `ProfileWriteConflict` wtórnej projekcji profilu poprzedniego właściciela już
  po canonical capture, nie do target identity, ownership CAS, OFS ani session
  generation.
- Full-profile writer zastąpiono małym, rebasowanym patchem z bounded CAS retry.
  Konflikt projekcji nie może już zamienić zatwierdzonego transferu w false
  failure; session/precommit mismatch nadal pozostaje fail-closed.
- Manual produkcyjny potwierdził finalizację filarów za pierwszym razem oraz
  stabilny rebuild territory/GN bez białego overlaya.
- Pełny zapis diagnostyczny:
  `doc/hardbugfix/gonna_win_conflict_pillar_final_dot_409_sprint_130_12_2_2026-08-25.md`.

---

# Sprint 130.12.3 — State Boundaries / UX / Cyberner Hot Paths P1

**Status bieżący:** `SPRINT 130.12.3 — COMPLETE`
**Priorytet:** P1

## Cel

Usunąć regresje wynikające z pomieszania stanów frontendowych i niepoprawnych source-of-truth oraz pozostały heavy-profile path Cybernera.

Zakres:

```text
BlackNet
Googleplex
Ghost Exchange
Victim Picker
Territory Control
foreign territory UX
GN dotted connections
tile scheme confirmation
Cyberner
```

---

## Część A — BlackNet / Googleplex / Ghost Exchange

### Problem

```text
catalog.filter is not a function
```

Powstaje m.in.:

```text
/resources.json 409
→ JSON error object
→ catalog = error object
→ catalog.filter()
```

Dodatkowo:

* GGPL/GX współdzielą search input,
* keyword BlackNet przechodzi do złej zakładki,
* GX może odziedziczyć filtr GGPL,
* CTA zmieniają state innych tabów.

## Nowy model

Osobne stany:

```text
googleplexQuery
exchangeQuery
blacknetQuery
```

oraz osobne typed models.

CTA:

```text
BlackNet CTA
→ target tab command
→ target tab state
```

Nie manipuluje globalnym inputem.

### Stan wejściowy potwierdzony 2026-08-25

`CTA BlackNet → właściwy produkt i właściwa zakładka` jest już spełnione przez
istniejący dispatcher:

- `open_googleplex` i `open_googleplex_search` używają
  `blacknetOpenGoogleplex()` oraz przełączają wyłącznie na `googleplex`;
- `open_ghost_exchange`, `open_exchange_market` i `open_exchange_category`
  używają `blacknetOpenExchange()` oraz przełączają wyłącznie na `exchange`;
- query produktu i sector GX pochodzą z osobnych pól kontraktu CTA.

Status tego punktu: `CONFIRMED IN CODE — NO REIMPLEMENTATION`.

W ramach 130.12.3 wspólny element DOM `search` otrzymał trzy niezależne modele
query (`googleplex`, `exchange`, `blacknet`). Przełączenie zakładki zapisuje stan
wyłącznie zakładki opuszczanej i przywraca stan zakładki docelowej.

Payload katalogu:

```text
if !response.ok → controlled error
if !Array.isArray(payload) → controlled error
```

Zero `.filter()` na error object.

## Testy

```text
409 catalog nie crashuje
BlackNet→GGPL nie zmienia GX query
BlackNet→GX nie zmienia GGPL query
GGPL search nie filtruje GX
GX search nie filtruje GGPL
CTA otwiera właściwy tab
```

---

## Część B — Victim Picker / Territory Control

### Problem

UI pokazuje phantom aimed target.

Focus/teleport prowadzi czasem do:

```text
0.00 : 0.00
```

Audit wskazuje, że frontend nie posiada jawnego fallbacku `(0,0)` w tej ścieżce. Zera lub phantom state pochodzą wyżej.

Obecny candidate path nadal może rozpoczynać się od profilu.

## Source of truth

Aktywny target:

```text
PlayerTargetRuntimeStore
```

Profil:

```text
compatibility projection only
```

Nie używać stale `profile.aimed_target` do wyboru bieżącego celu.

## Kontrakt

Brak canonical runtime target:

```text
aimed_target = null
active_target_id = ""
focus_enabled = false
teleport_enabled = false
```

Target musi posiadać:

```text
stable target_id
finite lat
finite lng
canonical current state
```

Backend teleportu również fail-closed.

`0,0` nie może oznaczać „brak celu”.

W ścieżkach Victim Picker i Territory Control `(0,0)` jest zawsze odrzucane
fail-closed; nie jest reprezentacją braku celu ani dozwolonym fallbackiem.

## Testy

```text
brak targetu → brak CEL
brak targetu → brak focus
brak targetu → brak teleport
cleared target → brak phantom
captured target → runtime aktualizuje state
stale profile aimed_target ignorowany
missing coords → fail closed
```

---

## Część C — Foreign Territory UX

Backendowe:

```text
403 FORBIDDEN
Target znajduje się na kontrolowanym terenie...
```

jest prawidłowe.

Frontend ma tłumaczyć kontrolowany gameplay error na komunikat systemowy.

Wprowadzić wspólny parser:

```text
parseGameplayApiResponse()
```

lub równoważną istniejącą warstwę.

Rozróżniać:

```text
authorization gameplay denial
session replaced/expired
conflict/replay
transport/server error
```

403 territory:

* system message,
* brak uncaught exception,
* brak czerwonego technicznego error UX.

Backend nadal 403.

---

## Część D — GhostNetwork dotted connections

Nie zakładać, że różnica między kontami jest bugiem.

Connections renderowane tylko, gdy visibility contract na to pozwala.

Porównać viewer A/B:

```text
public_connection_id
state
can_show_on_map
location_visibility endpoint A
location_visibility endpoint B
viewer_relation
frontend layer count
```

Jeżeli payload różny zgodnie z visibility:

```text
EXPECTED
```

Jeżeli payload ten sam, a renderer różny:

```text
FRONTEND BUG
```

Dodać fixture dwóch viewerów z różną relacją.

Nie osłabiać GN visibility dla „naprawy” renderera.

---

## Część E — Tile scheme

Po 130.12.1 session fix sprawdzić ponownie.

Jeżeli problem pozostaje:

* canonical desktop settings,
* validated scheme enum,
* confirmed save state,
* iframe/map boot source.

Nie używać niezapisanego lokalnego stanu jako canonical.

404 tile provider:

* oddzielić problem invalid scheme od zewnętrznego unavailable tile URL,
* zapewnić kontrolowany fallback do `osm`,
* nie zapisywać fallbacku jako preference użytkownika bez jawnej zmiany.

---

## Część F — Cyberner heavy profile

### Problem

Audit potwierdził:

```text
/api/mail/bootstrap
/api/chats/messages GET
/api/chats/messages POST
→ load_profile_readonly()
→ full profile
```

Direct recipient lookup również potrafi użyć pełnego `get_profile(peer)`.

To łamie:

```text
profile_hot_path_contract_130_11_plus
```

## Cel

Cyberner bootstrap, polling i messaging:

```text
profile_full_read = 0
profile_full_write = 0
```

na normalnej ścieżce.

## Nowe projekcje

Użyć bounded:

```text
identity projection
clan projection
recipient projection
contact/channel index
```

Nie tworzyć kolejnego cache jako source of truth.

Projection musi posiadać:

```text
username
display identity
revision/checksum jeśli wymagane
minimal clan/relation fields
```

## Performance test

Profil testowy ~35 MB.

Sprawdzić:

```text
bootstrap
thread GET
message POST
recipient resolution
polling
```

Oczekiwane:

```text
0 full profile reads
0 full profile writes
bounded query count
bounded payload
```

## Wynik implementacji 2026-08-25

- CTA BlackNet do GGPL/GX potwierdzono w istniejącym dispatcherze bez
  reimplementacji. Query trzech zakładek są odseparowane, a katalog przyjmuje
  payload dopiero po `response.ok` i `Array.isArray()`.
- Victim Picker czyta aktywny cel z `PlayerTargetRuntimeStore`; stale
  `profile.aimed_target`, brak współrzędnych i `(0,0)` nie tworzą focusu ani
  teleportu. Territory Control używa tego samego fail-closed guarda.
- Oczekiwany backendowy `403 foreign_territory_protected` pozostaje bez zmian,
  ale frontend mapy tłumaczy go na komunikat systemowy bez wyjątku i czerwonego
  technicznego error UX.
- Różnica dotted connections między dwoma kontami została sklasyfikowana jako
  `EXPECTED`: backendowa viewer projection pomija connection, jeżeli dowolny
  endpoint nie ma `location_visibility=exact`. Renderer respektuje wyłącznie
  `state` i `can_show_on_map`; nie osłabiono visibility.
- Canonical tile scheme nadal pochodzi z walidowanych desktop settings. Po trzech
  kolejnych błędach `tileerror` zewnętrznego providera warstwa przechodzi runtime
  na OSM, bez zapisywania fallbacku jako preferencji użytkownika.
- Cyberner bootstrap, GET i POST wiadomości używają integralność-gated
  `UserIdentityProjectionStore`. Usunięto runtime `load_profile_readonly()`,
  `get_profile(peer)`, `list_profiles()` i profilowy skan klanu z tych ścieżek.

```text
PROFILE HOT PATH AUDIT
new runtime call sites: 0 heavy
profile_full_read: 0
profile_full_write: 0
profile_bytes: 0
list_profiles/all-user scans: 0
per-recipient profile reads: 0
allowed heavy recovery/write call sites: none
```

- Regresje: 40 celowanych testów Python dla 130.12.3 — OK; dodatkowe 3 testy
  desktop/catalog persistence — OK; Node GN renderer i map snapshot recovery —
  OK; profil syntetyczny Cybernera 35 MB — OK; `py_compile`, `node --check` i
  `git diff --check` — OK.
- Bez deployu, restartu PM2 i bez commita.

## Definition of Done 130.12.3

```text
GGPL/GX/BlackNet niezależne
catalog type-safe
phantom target usunięty
0:0 nie jest fallbackiem
foreign 403 ma normalny UX
GN visibility zweryfikowana
tile scheme stabilne
Cyberner bez heavy profile hot path
```

Końcowy status:

```text
SPRINT 130.12.3 — COMPLETE
```

### Domknięcie manuala produkcyjnego 2026-08-25

- Manual potwierdził BlackNet/Googleplex/Ghost Exchange, izolację filtrów,
  type-safe katalog, Victim Picker i Territory Control bez phantom targetu i
  `(0,0)`, kontrolowany foreign territory scan, tile fallback oraz Cyberner bez
  heavy-profile freeze.
- Osobna ścieżka MARK została potwierdzona dla obu frontendowych call chainów:
  `/api/map/aim-target` i `/map-action` rozpoznają backendowy
  `403 foreign_territory_protected`, pokazują system message i nie przechodzą do
  technicznego error UX. Sam wpis `Failed to load resource: 403` w DevTools jest
  oczekiwany; backend nadal fail-closed zwraca 403.
- Kanon i implementacja potwierdzają, że aktywna część ma dla każdego widza
  `location_visibility=exact`, publiczny klan i aktywny status. Pełne połączenie
  dwóch aktywnych części jest globalnie publiczne, ale zaszyfrowana tożsamość,
  profesja i supermoc pozostają ukryte dla obcego/neutralnego widza.
- Dodano regresje: to samo aktywne połączenie jest widoczne dla viewerów same
  clan, foreign clan i neutral; pooled/hidden oraz dotychczasowe half/inactive
  visibility pozostają bez zmian.
- Testy domykające: 22 Python — OK; pełny celowany pakiet 130.12.3: 45 Python —
  OK; Node GN renderer i map snapshot recovery — OK; `py_compile`,
  `node --check` i `git diff --check` — OK.

### Finalne domknięcie po hotfixach produkcyjnych 2026-08-26

- Operations runtime ponownie publikuje ruchome kapsuły plików, incidenty i NPC
  bez przywracania pełnego profilu do pollera.
- GhostNetwork lifecycle SFX działa symetrycznie: prawdziwe transition gra
  dokładnie raz, natomiast rebuild/snapshot/recovery nie odtwarza state jako
  zdarzenia. Manual potwierdził także drop oraz spatial separation 50 km.
- Ghost Exchange rozlicza duże batch settlementy z idempotentnym walletem i
  bounded profile CAS retry; manual potwierdził ponowne otwieranie GX.
- Googleplex ticket zachowuje travel receipt, canonical teleport i live-map
  bridge. Jawny kontrakt `current_city=None|string` domknął ostatni backendowy
  błąd 500; manual potwierdził poprawny teleport po bilecie.
- Tile provider 403 nie był cache ani Leaflet race. Mapa wysyła teraz wyłącznie
  origin jako Referer, bez ścieżki i query tokenu generation.

Finalny status po manualu:

```text
SPRINT 130.12.3 — COMPLETE
```

---

# Sprint 130.12.4 — Full Validation / Production Cutover / Sprint 131 Re-audit

**Status bieżący:** `SPRINT 130.12.4 — COMPLETE`
**Priorytet:** Closure

**Rozpoczęto:** 2026-08-26
**Zamknięto:** 2026-08-26

Ten pod-sprint proponuję jako formalne zamknięcie całego 130.12.

Nie dodawać nowych feature'ów.

## Stan bramki startowej 2026-08-26

- Pełny pierwszy przebieg: 1092 testy Python, 4 failures i 2 errors. Wszystkie
  sześć przypadków odtworzyło się również izolowanie.
- Audit nie wykazał nowej regresji runtime. Testy odwoływały się do usuniętego
  loadera Territory Control, nie patchowały nowych canonical target/identity
  store'ów, nie obejmowały marked-target store w GN E2E, nadal wstrzykiwały
  `UserProfileManager` zamiast bounded projection writera oraz nie miały jawnego
  wyjątku dla istniejącego offline CAS recovery toola.
- Fixture'y i statyczna allowlista zostały dostosowane do aktualnych call chainów
  bez zmiany runtime. Precommit regresja ponownie wymusza przejęcie A → B tuż
  przed transakcją bounded writera i potwierdza 409 oraz brak mutacji profilu.
- Walidacja po korekcie: sześć testów celowanych — OK; sześć pełnych modułów,
  łącznie 266 testów — OK; 13/13 pakietów Node — OK; `py_compile` kluczowych
  runtime/test modules, `node --check` 27 plików i `git diff --check` — OK.
- Pełny rerun 1092 testów, heavy-profile measurements, manual/server validation
  i Sprint 131 re-audit pozostają otwarte.

## Finalna bramka 2026-08-26

- Pełny rerun Python po korekcie fixture'ów: `1092/1092 OK` w 799,716 s.
- Pełny frontend: `13/13` pakietów Node — OK; `node --check` 27 plików — OK.
- Dodatkowa bramka heavy-profile/read-path: 24/24 — OK. Profil syntetyczny
  35 MB dla Cybernera zachował `profile_full_read=0`,
  `profile_full_write=0`, `profile_bytes=0`, bez `list_profiles` i bez
  per-recipient full-profile reads. GN snapshot, Territory Control, opaque
  teleport, desktop/map boot i target hot paths mają bounded canonical source
  oraz kontrakty zabraniające fallbacku do pełnego profilu.
- Manual produkcyjny z 130.12.1–130.12.3 pokrył lifecycle A/B/relogin/tabs,
  mapę i territory/GN, operations/OFS, Googleplex/GX/BlackNet, Cybernera,
  lifecycle SFX, drop oraz teleport. Ostatnie zgłoszone blockery zostały przez
  użytkownika potwierdzone jako poprawnie działające.
- Identity projection ma jawne `status/audit/dry-run/apply/verify`, atomiczny
  guarded-write i read-only dry-run. W tej bramce nie wykonano ponownego apply,
  deployu, restartu PM2 ani mutacji produkcyjnej.
- Re-audit Sprintu 131 oznaczył wszystkie pięć historycznych blockerów jako
  `RESOLVED`: bounded identity/owner aliases, Territory Control zero-profile,
  server-resolved opaque GN teleport, shared delta client bez Leaflet oraz
  bounded audience recipient resolver.

## Cel

Udowodnić, że:

```text
130.12.1
130.12.2
130.12.3
```

rozwiązały problemy z manuala bez regresji:

* profilu,
* sesji,
* mapy,
* territory,
* GN,
* operations,
* walletu,
* Cybernera.

## 1. Pełna regresja

Uruchomić cały dostępny zestaw testów.

Osobno raportować:

```text
Python
JS
py_compile
node --check
git diff --check
```

Nie maskować flaky failures.

## 2. Heavy-profile measurements

Na ciężkim profilu zmierzyć co najmniej:

```text
desktop boot
map boot
aim target
/gonna-win
Cyberner bootstrap
Cyberner GET thread/messages
Cyberner POST message
Googleplex open
Territory Control open
GN snapshot
```

Raport:

```text
before
after
full_profile_read_count
full_profile_write_count
elapsed
query count
```

Hot paths nie mogą wrócić do pełnych profili.

## 3. Session manual

Minimum:

```text
A login
B login na tym samym koncie
A zostaje wyrzucony
B działa

A stale POST po B
→ brak mutacji

logout A
→ B nadal działa

timeout
→ ponowny login bez cookie clear

2 karty tej samej browser session
→ działają
```

## 4. Map manual

Sprawdzić:

```text
pan
zoom
GN snapshot
GN delta
territory rebuild
territory delta
map close/open
map refresh
tile scheme
actor refresh
```

Zero:

```text
undefined.x
white overlay
permanent in_flight
permanent aborted recovery
```

## 5. Operations manual

Uruchomić kilka rodzajów narzędzi:

```text
terminal
button_choices
window
progressbar_random
```

Sprawdzić:

```text
SFX
OFS
receipt
operation_id
/gonna-win count
success
replay
generation replacement
```

Zero false-red failure po canonical success.

## 6. Googleplex / GX / BlackNet

Test:

```text
GGPL query
GX query
BlackNet CTA → GGPL
BlackNet CTA → GX
switch tabs
install app
logout/login
```

State nie może przeciekać pomiędzy tabami.

## 7. Territory / Victim Picker

```text
brak celu
aktywny cel
clear target
foreign territory
own territory
teleport
focus
```

Nigdy phantom target / accidental `(0,0)`.

## 8. GN visibility

Porównać co najmniej dwa konta z różnymi relacjami.

Potwierdzić:

* brak hidden data leak,
* dotted connections zgodne z projection,
* frontend nie różni się przy identycznym payloadzie.

## 9. Cyberner

Manual:

```text
bootstrap
lista rozmów
thread
send
receive/poll
switch contact
```

oraz latency.

Nie może wykazywać dawnego heavy-profile freeze.

## 10. Production migration/backfill

Jeżeli 130.12.1 wymaga schema migration/backfill session ownership:

najpierw:

```text
status
audit
dry-run
```

Potem:

```text
backup
apply
verify
```

Jeżeli narzędzie ma taki kontrakt.

Bez ręcznych SQL hotfixów.

## 11. PM2/server

Przed deployem:

```text
git status
HEAD
pm2 status
DB backup/readiness
migration dry-run
```

Po deployu:

```text
health
web logs
worker logs
lock metrics
session metrics
map errors
```

## 12. Re-audit Sprintu 131

Po zielonym manualu ponownie przeczytać:

```text
doc/sprint_131_plus_post_audit.md
```

i sprawdzić każdy historyczny blocker względem aktualnego kodu.

Nie kopiować starego statusu.

Każdy blocker oznaczyć:

```text
RESOLVED
STILL OPEN
OBSOLETE
REPLACED BY NEW CONTRACT
```

## Finalne Definition of Done 130.12

Sprint może być `COMPLETE` dopiero, gdy:

```text
130.12.1 COMPLETE
130.12.2 COMPLETE
130.12.3 COMPLETE

full regression green
heavy-profile measurements green
manual green
production migration verified
session lifecycle green
map/GN green
operations/OFS green
Cyberner green
Sprint 131 re-audit complete
```

Wtedy:

```text
SPRINT 130.12 — COMPLETE
```

oraz:

```text
READY TO PLAN / START SPRINT 131
```

Finalny wynik:

```text
SPRINT 130.12.4 — COMPLETE
SPRINT 130.12 — COMPLETE
SPRINT 131 AUDIT COMPLETE — READY FOR SPRINT 132
```

---



> Lecimy z całym desktopowym domknięciem GhostNetwork — Sprint 131 ustali bezpieczne relacje i integrację z Territory Control, 132 przygotuje lekki wspólny snapshot, 133 zbuduje właściwe listy części, 134 podepnie mapę oraz teleport, a 135 zamknie GUI, delty i regresję całej rodziny narzędzi.

# Sprint 131 — GhostNetwork Suite: audyt widoczności części i integracja z Territory Control

> **Post-audit 2026-08-21 — wiążące.** Sprint bazuje na istniejących:
> `GhostVisibilityService` v2, sześciu relacjach, frozen conflict context,
> `project_territory_component_for_viewer`, `view=suite` i delta bridge.
> Nie tworzy ich ponownie. Rzeczywisty artefakt ma ścieżkę
> `doc/sprints/sprint_131_ghostnetwork_suite_audit.md`. Pełne ustalenia:
> `doc/sprints/sprint_131_plus_post_audit.md`.

**Status po re-audycie 2026-08-26:**
`SPRINT 131 AUDIT COMPLETE — READY FOR SPRINT 132`.

Audit z 2026-08-24 potwierdził istniejący visibility/snapshot/delta foundation,
ale wykrył otwarte blockery: pełny profil w Territory Control i teleporcie,
klientowe współrzędne wspólnego teleportu oraz brak bounded owner-alias
projection. Szczegóły i inventory callsites 132–138:
`doc/sprints/sprint_131_ghostnetwork_suite_audit.md`.

Sprint 130.12 zamknął wskazane blockery; powyższe zdanie pozostaje opisem
historycznego wyniku audytu z 2026-08-24.

**Bramka heavy-profile:** audyt musi zinwentaryzować wszystkie przyszłe call
sites 132–138. Każdy runtime full-profile read/write albo all-user profile scan
jest blockerem przed `READY FOR SPRINT 132`; obowiązuje
`doc/architecture/profile_hot_path_contract_130_11_plus.md`.

## Cel sprintu

Przeprowadzić audyt istniejącego GhostNetwork, Territory Control oraz wspólnej infrastruktury desktopowych `pro-system-tools`, a następnie zdefiniować kontrakt nowej aplikacji obserwacyjnej.

GhostNetwork Suite nie tworzy:

* nowego magazynu części,
* własnej klasy widoczności,
* alternatywnego systemu terytoriów,
* kopii właścicieli klastrów,
* osobnego pollera,
* własnej mechaniki teleportu.

Aplikacja jest lekką projekcją istniejącego globalnego stanu GhostNetwork i uzupełnia:

* Victim Picker,
* Territory Control,
* Operation Control.

Stan części nadal należy do GhostNetwork, kontrola obszaru do systemu terytoriów, a frontend wyświetla wyłącznie projekcję zatwierdzoną dla aktualnego operatora. 

## 1. Miejsce produktu w Ghost Control Suite

Potwierdzić wspólną rodzinę aplikacji:

```text
ghost_control_suite
```

Komponenty:

```text
Victim Picker
Territory Control
Operation Control
GhostNetwork Suite
```

Nowa aplikacja pozostaje produktem:

```text
type: pro-system-tool
category: pro-system-tools
```

Nie tworzyć nowej kategorii gameplayowej ani drugiego systemu instalacji.

Audyt ma wskazać:

* obecny kontrakt zakupu w Googleplexie,
* instalację produktu w profilu,
* launcher desktopowy,
* taskbar,
* zachowanie aktywnego okna,
* wspólny icon pack,
* mechanizm aktualizacji przez delty.

Cena produktu pozostaje konfigurowalna i nie jest ustalana w tym sprincie.

## 2. Audyt projekcji widoczności

Sprawdzić implementację ze Sprintu 120:

```text
GhostVisibilityService
```

Nowe narzędzie musi korzystać dokładnie z tych samych reguł co:

* mapa,
* Territory Control,
* BlackNet,
* Cyberner,
* narracyjny outbox.

Nie może samodzielnie wyliczać widoczności na podstawie:

```text
viewer.clan === part.clan
```

Do aplikacji trafia gotowa projekcja.

## 3. Kanoniczne grupy widoku

Ustalić pięć grup wyświetlanych w GhostNetwork Suite.

### Publiczne

Części:

```text
module_state = neutral
```

Nie są otoczone stabilnym terytorium.

Wszyscy widzą pełne dane:

* nazwę,
* klan,
* maszynę,
* profesję,
* supermoc,
* dokładną lokalizację.

### Zablokowane przez inny klan

Części znajdują się na stabilnym terytorium klanu innego niż klan części.

Dla zwykłego obserwatora:

* tożsamość może być ukryta,
* znane jest terytorium,
* znany jest stan `blocked`,
* dokładna kotwica może pozostać niewidoczna.

### Aktywne w naszym klanie

Części własnej maszyny aktywowane przez innego członka klanu.

Aktualny operator widzi pełne dane dzięki przynależności klanowej, ale nie jest właścicielem terytorium.

### Kontrolowane przeze mnie — część obca

Aktualny operator jest właścicielem klastra zawierającego część obcego klanu.

Relacja:

```text
self_foreign_blocked
```

Operator widzi pełną tożsamość komponentu, ponieważ sam go blokuje.

### Kontrolowane przeze mnie — część własna

Aktualny operator jest właścicielem klastra aktywującego część własnego klanu.

Relacja:

```text
self_own_active
```

Część jest aktywna i daje moc właściwej profesji całemu klanowi.

## 4. Brak osobnych list w bazie

Grupy są filtrami jednego snapshotu:

```text
parts[]
```

Nie tworzyć struktur:

```text
public_parts_store
blocked_parts_store
my_parts_store
clan_parts_store
```

Ta sama część może po zmianie terytorium przejść z jednej sekcji do drugiej bez zmiany swojego `part_id`.

## 5. Relacje odbiorcy

Audyt ma potwierdzić i ewentualnie uzupełnić resolver:

```text
resolve_part_viewer_relation(part, viewer)
```

Wymagane wartości:

```text
public_neutral
foreign_blocked
foreign_active
clan_own_active
self_foreign_blocked
self_own_active
```

Opcjonalnie dla spójności:

```text
self_contested
clan_contested
foreign_contested
```

Konflikt pozostaje jednak nakładką, a nie nowym stanem bazowym.

## 6. Audyt danych właściciela

Ustalić kanoniczne pola:

```text
territory_id
territory_owner_id
territory_owner_alias
territory_clan
cluster_id
cluster_label
```

Nie pobierać pełnych profili właścicieli.

Alias i klan muszą pochodzić z lekkiej projekcji przygotowanej na backendzie.

## 7. Audyt integracji z Territory Control

Backend ma już helper projekcji komponentu, ale runtime snapshot Territory
Control jeszcze go nie wywołuje. Sprint ma podłączyć helper bez tworzenia
drugiego modelu.

Potwierdzić pola:

```text
contains_ghost_part
ghost_part_count
ghost_part_relation
ghost_part_state
ghost_part_identity_visible
ghost_part_summary
```

Dla odbiorcy uprawnionego do pełnej tożsamości dodatkowo przekazać bezpieczne
projekcje w jednej tablicy (mapowanie helperowego `parts` do kontraktu
Territory Control):

```text
ghost_parts[]
```

Każdy element `ghost_parts[]` pozostaje wynikiem `project_part_for_viewer`; nie
spłaszczać pierwszej części do osobnego zestawu pól i nie wysyłać surowego
rekordu repository. Pola szczegółowe mogą wystąpić tylko wtedy, gdy pozwala na
to projekcja widoczności.

## 8. Klaster z własną częścią

Territory Control pokazuje:

```text
GHOST COMPONENT
WŁASNY KLAN
STATUS: AKTYWNY
```

Jeżeli właścicielem jest aktualny operator:

```text
RELACJA: KONTROLOWANY PRZEZE MNIE
```

Jeżeli inny członek klanu:

```text
RELACJA: WĘZEŁ KLANOWY
```

## 9. Klaster z obcą częścią

Dla właściciela:

```text
GHOST COMPONENT
CZĘŚĆ OBCEGO KLANU
STATUS: BLOKOWANY
```

Dla pozostałych:

```text
TERYTORIUM ZAWIERA CZĘŚĆ GHOSTNETWORK
TOŻSAMOŚĆ: UKRYTA
STATUS: NIEAKTYWNA
```

Nie ujawniać kodu części w badge, tooltipie, DOM ani danych aplikacji.

## 10. Konflikt terytorialny

Podczas konfliktu aplikacja pokazuje stan sprzed jego rozpoczęcia:

```text
module_state: active lub blocked
conflict_state: contested
```

Pozycja otrzymuje dodatkowe oznaczenie:

```text
STAN ZAMROŻONY — KONFLIKT
```

Nie przenosić jej między grupami aż do zdarzenia stabilizacji.

Reguła odpowiada kanonowi, według którego konflikt nie zmienia natychmiast właściciela ani aktywności części. 

## 11. Audyt akcji mapy

Sprawdzić wspólny kontrakt używany już przez:

* Victim Picker,
* Territory Control,
* Operation Control.

Wymagane akcje:

```text
show_on_map
teleport
```

Obie muszą używać wspólnego bridge’a desktop–mapa.

GhostNetwork Suite nie może tworzyć własnego iframe ani alternatywnego endpointu teleportacji.

## 12. Audyt teleportu

Teleport ma prowadzić:

* do dokładnej kotwicy, jeśli odbiorca ją zna,
* do pozycji klastra lub bezpiecznego punktu terytorium, jeśli część jest ukryta,
* do aktualnej pozycji historycznej kotwicy Ghost Anchor, jeśli źródło zniknęło.

Aplikacja nie może ujawnić dokładnych współrzędnych ukrytej części przez payload teleportu.

## 13. Audyt lifecycle okna

Sprawdzić wzorce:

* instalacja produktu,
* utworzenie okna,
* jedna instancja aplikacji,
* przywracanie z taskbara,
* focus istniejącego okna,
* zamknięcie,
* wyrejestrowanie listenerów delt,
* restart GhostSystemu.

## 14. Wspólne ikony

Rozszerzyć:

```text
GHOST_CONTROL_ICONS
```

Minimalne klucze:

```text
ghostnetwork
public_part
blocked_part
active_part
self_controlled
clan_controlled
map
teleport
territory
owner
machine
profession
ability
conflict
refresh
```

Ikony inline SVG:

* posiadają `title`,
* `aria-label`,
* stany hover/focus/disabled,
* nie są anonimowymi symbolami.

## 15. Artefakt sprintu

Dokument:

```text
doc/sprints/sprint_131_ghostnetwork_suite_audit.md
```

Powinien zawierać:

* źródła danych,
* macierz widoczności,
* mapowanie grup,
* kontrakt Territory Control,
* kontrakt mapy,
* kontrakt teleportu,
* listę wykorzystywanych helperów,
* listę zabronionych duplikatów,
* plan testów 132–135.

## Testy Sprintu 131

Minimum:

* neutralna część trafia do `public_neutral`,
* blokowana część dla właściciela trafia do `self_foreign_blocked`,
* blokowana część dla obcego obserwatora trafia do `foreign_blocked`,
* aktywna część właściciela trafia do `self_own_active`,
* aktywna część członka klanu trafia do `clan_own_active`,
* konflikt nie zmienia grupy bazowej,
* ukryta tożsamość nie przechodzi do Territory Control,
* dokładna pozycja ukrytej części nie trafia do akcji mapy,
* istniejące helpery mapy i teleportu są wskazane,
* brak drugiego źródła danych.

## Poza sprintem

Nie tworzyć jeszcze:

* endpointu snapshotu,
* aplikacji GUI,
* list,
* delty,
* zakupu produktu,
* nowych akcji mapy.

## DoD

Sprint jest zakończony, gdy dokładnie wiadomo:

1. Jak części są grupowane.
2. Kto widzi ich tożsamość.
3. Jak Territory Control oznacza klastry.
4. Jakie dane otrzymuje mapa.
5. Gdzie kieruje teleport.
6. Które istniejące helpery zostaną ponownie użyte.
7. Jak uniknąć przecieku dokładnej pozycji blokowanej części.
8. Jak aplikacja wpina się w Ghost Control Suite.

---

# Sprint 132 — GhostNetwork Suite: lekki snapshot części, właścicieli i stanów terytorialnych

> **Post-audit 2026-08-21 — wiążące.** `view=suite` już istnieje w
> `/api/ghostnetwork/snapshot` i usuwa geometrię połączeń. Sprint rozszerza
> `normalize_snapshot_view`, zachowuje viewer-projected `parts[]` jako jedyną
> listę, a `summary/groups/actions` buduje jako pochodne. Nie dodaje punktowego
> endpointu bez pomiaru uzasadniającego potrzebę; delty już niosą bezpieczną
> `part_projection`, a recovery pobiera suite snapshot.

**Status bieżący:** `SPRINT 132 — COMPLETE`.

Walidacja serwerowa 2026-08-27: dwa niezależne odczyty viewer-projected
zwróciły HTTP 200, `suite_health.ok=true`, poprawny kontrakt privacy/groups oraz
stabilne `state_version`, checksum i suite cache key.

**Rozpoczęto:** 2026-08-26.

Artefakt wykonawczy:
`doc/sprints/sprint_132_ghostnetwork_suite_read_model.md`.

**Bramka heavy-profile:** viewer identity pochodzi z wąskiej integrity-gated
projekcji. Snapshot i recovery mają `profile_full_read=0`,
`profile_full_write=0`, `profile_bytes=0` oraz nie wywołują
`sync_session_profile`, także przy profilu 35 MB.

## Cel sprintu

Przygotować lekki backendowy snapshot przeznaczony specjalnie dla desktopowej aplikacji GhostNetwork Suite.

Snapshot ma zawierać jedynie dane potrzebne do:

* wyświetlenia list,
* określenia relacji części względem operatora,
* pokazania właściciela i klastra,
* wykonania akcji mapy oraz teleportu,
* aktualizacji przez delty.

Nie może zawierać:

* pełnej topologii,
* geometrii wszystkich terytoriów,
* rezerwacji,
* pełnego profilu,
* historii wszystkich części,
* danych ukrytych przed odbiorcą.

## 1. Widok snapshotu

Rozszerzyć istniejący endpoint:

```text
GET /api/ghostnetwork/snapshot?view=suite
```

Nie tworzyć zupełnie niezależnego magazynu ani endpointu omijającego `GhostVisibilityService`.

## 2. Kontrakt główny

Response:

```text
cycle
summary
groups
parts
state_version
visibility_version
restart_required
stabilization_until
```

`cycle` zawiera:

```text
cycle_id
signal_number
ghostsystem_version
status
```

`summary`:

```text
parts_total
parts_discovered
parts_public
parts_blocked
parts_active
parts_contested
parts_visible_to_viewer
```

## 3. Rekord części

Każda widoczna pozycja może zawierać:

```text
public_entity_id
part_id
display_label
identity_visible
module_state
conflict_state
viewer_relation
visibility_level
part_clan
machine
profession
ability
territory
owner
location
actions
updated_at
state_version
```

Ukryte pola muszą być `null` albo nieobecne.

Nie wysyłać prawdziwej wartości z dodatkowym `visible: false`.

## 4. Identyfikator aplikacyjny

Aplikacja kluczuje elementy po:

```text
public_entity_id
```

Identyfikator:

* stabilny w cyklu,
* nie zdradza `part_code`,
* działa również dla ukrytej części,
* może zostać użyty w deltach i focusie Territory Control.

## 5. Dane tożsamości

Gdy `identity_visible = true`:

```text
part_id
part_code
part_name
part_clan_code
part_clan_name
machine_code
machine_name
profession_code
profession_name
ability_code
ability_name
ability_description
```

Gdy tożsamość jest ukryta:

```text
part_id: null
part_code: null
part_name: null
machine: null
profession: null
ability: null
```

Dozwolony `display_label`:

```text
NIEZIDENTYFIKOWANY KOMPONENT
```

## 6. Dane terytorialne

Minimalny kontrakt:

```text
territory:
    territory_id
    cluster_id
    cluster_label
    owner_id
    owner_alias
    owner_clan
    threat_state
    pillar_count
    inner_count
    conflict_state
```

Nie przesyłać całej listy wierzchołków klastra.

Do listy wystarczy agregat.

## 7. Pozycja części

Kontrakt:

```text
location:
    visibility
    latitude
    longitude
    map_focus_type
    map_focus_id
```

Dozwolone wartości:

```text
visibility: exact
visibility: territory_only
```

### `exact`

Współrzędne kotwicy są dostępne.

### `territory_only`

Snapshot nie zawiera dokładnej pozycji komponentu.

Może zawierać:

* centroid klastra,
* publiczny identyfikator terytorium,
* bezpieczny punkt teleportu.

## 8. Akcje

Backend zwraca gotowe możliwości:

```text
actions:
    can_show_on_map
    can_teleport
    map_target_type
    map_target_id
    teleport_target_type
    teleport_target_id
```

Frontend nie zgaduje dostępności na podstawie stanu.

## 9. Pokaż na mapie

Dla `exact`:

```text
map_target_type: ghost_part
map_target_id: public_entity_id
```

Dla `territory_only`:

```text
map_target_type: territory
map_target_id: territory_id
```

To zapobiega ujawnieniu dokładnej kotwicy blokowanej części.

## 10. Teleport

Dla `exact` teleport może używać pozycji części.

Dla `territory_only` teleport kieruje do:

* centroidu klastra,
* dozwolonego punktu wejścia,
* publicznej kotwicy terytorium.

Backend ponownie waliduje target przy kliknięciu.

Nie ufać współrzędnym przechowywanym w DOM.

## 11. Grupy snapshotu

Backend może zwrócić gotowe grupowanie:

```text
groups:
    public
    blocked_by_other_clans
    active_in_my_clan
    self_foreign_blocked
    self_own_active
```

Każda grupa zawiera listę `public_entity_id`.

Alternatywnie frontend może filtrować po `viewer_relation`, ale jedna kanoniczna metoda grupowania powinna być współdzielona z testami.

## 12. Brak duplikatów

Jedna część występuje dokładnie raz w głównej liście `parts`.

`groups` zawiera jedynie odwołania.

Nie zwracać pięciu pełnych kopii tego samego rekordu.

## 13. Sortowanie

Backend zwraca stabilne pola sortowania:

```text
distance_from_player
owner_alias
part_clan_sort
module_state_sort
updated_at
```

Odległość liczona jest od aktualnej pozycji motocykla operatora.

Jeżeli część jest `territory_only`, odległość może być liczona do punktu klastra, nie dokładnej kotwicy.

## 14. Aktualna pozycja operatora

Snapshot może zawierać:

```text
viewer_position:
    latitude
    longitude
    updated_at
```

Nie uruchamia pełnej synchronizacji profilu.

Używa lekkiego źródła bieżącej pozycji, tego samego co Victim Picker i Territory Control.

## 15. Ghost Anchor

Dla części ze źródłem utraconym:

```text
anchor_state: source_lost
display_source: GHOST ANCHOR
```

Jej dostępność mapy i teleportu nadal zależy od projekcji.

## 16. Cykl transmitting i stabilizing

Podczas `transmitting`:

* snapshot może zwracać zamrożone 20 części,
* akcje mapy mogą być czasowo wyłączone,
* GUI pokazuje transmisję.

Po `consumed`:

* aktywna lista zostaje wyczyszczona,
* aplikacja pokazuje brak aktywnych części,
* może pokazać odnośnik do archiwum.

Podczas `stabilizing`:

* lista jest pusta,
* widoczne jest odliczanie do kolejnego cyklu.

## 17. Cache

Cache kluczowany:

```text
cycle_id
state_version
viewer_id
viewer_clan
view=suite
```

Nie mieszać snapshotów:

* właściciela,
* członka klanu,
* obcego gracza.

## 18. Rozmiar odpowiedzi

Maksymalnie 20 części.

Nie wysyłać:

* pełnej geometrii,
* event history,
* pełnych definicji katalogu,
* opisów fabularnych większych niż potrzebne w kartach.

Długie opisy supermocy mogą być opcjonalne i pobierane dopiero przy rozwinięciu szczegółów.

## 19. Endpoint punktowy

Nie dodawać go w podstawowym zakresie Sprintu 132. Aktualna delta niesie
bezpieczną `part_projection`, a recovery odtwarza cały lekki suite snapshot.
Endpoint:

```text
GET /api/ghostnetwork/parts/<public_entity_id>?view=suite
```

może wrócić jako osobny follow-up wyłącznie po pomiarze, który wykaże potrzebę:

* punktowego odświeżenia,
* obsługi delty bez pełnego payloadu,
* ponownej walidacji przed otwarciem mapy.

Endpoint nadal stosuje projekcję widoczności.

## 20. Health check snapshotu

Sprawdza:

* duplikaty `public_entity_id`,
* część w dwóch bazowych grupach,
* `exact` bez współrzędnych,
* `territory_only` bez `territory_id`,
* ukrytą część z nazwą,
* self relation bez zgodnego właściciela,
* active clan relation bez zgodnego klanu,
* action target zdradzający ukryty `part_id`.

## Testy Sprintu 132

Minimum:

* snapshot z pustym cyklem,
* snapshot z 20 częściami,
* neutralna część z pełnymi danymi,
* blokowana część dla właściciela,
* blokowana część dla członka klanu właściciela,
* blokowana część dla właściwego klanu części,
* aktywna część własnego klanu,
* aktywna część obcego klanu,
* `self_foreign_blocked`,
* `self_own_active`,
* `territory_only` bez dokładnych współrzędnych,
* mapa wskazuje klaster zamiast kotwicy,
* teleport wskazuje klaster,
* brak pełnego profilu,
* brak geometrii terytorium,
* brak rezerwacji,
* brak duplikatów,
* cache nie przecieka między odbiorcami.

## Poza sprintem

Nie tworzyć jeszcze:

* końcowego GUI,
* paneli list,
* map bridge,
* teleport endpointu,
* delt frontendowych.

## DoD

Sprint jest zakończony, gdy desktopowa aplikacja może jednym lekkim odczytem otrzymać wszystkie części dostępne operatorowi, bez pobierania mapy, pełnego profilu i bez możliwości poznania ukrytej tożsamości albo dokładnej lokalizacji.

---

# Sprint 133 — GhostNetwork Suite: lista części publicznych, blokowanych i aktywnych

> **Post-audit 2026-08-21 — wiążące.** Produkt używa ID
> `ghostnetworkSuite`, launchera `createGhostNetworkSuiteApp`,
> `family_id=ghost_control_suite` i `data-app="ghostnetwork-suite"`. Karty
> wykorzystują istniejące `visual_asset_url/marker_asset_url`. Akcje mapy i
> teleportu są do Sprintu 134 ukryte lub disabled i nie wysyłają requestów.

**Status planu:** `SPRINT 133 — COMPLETE`.

Manual serwerowy potwierdził instalację produktu, widoczność części oraz działanie
filtrów. Akcje mapy i teleportu przechodzą do Sprintu 134.

**Bramka heavy-profile:** aplikacja konsumuje wyłącznie `view=suite` i delty.
Nie pobiera `/api/profile`, nie przechowuje profilu w cache i nie uruchamia
toolbar profile refresh po renderze lub zmianie karty.

## Cel sprintu

Zbudować funkcjonalny frontend desktopowej aplikacji, który prezentuje części GhostNetwork w pięciu jednoznacznych sekcjach i pozwala operatorowi szybko zrozumieć strategiczny stan świata bez otwierania mapy.

Sprint tworzy listy oraz szczegóły, ale akcje mapy i teleportu mogą pozostać jeszcze podłączone do placeholderów kontraktowych do Sprintu 134.

## 1. Okno aplikacji

Dodać:

```text
createGhostNetworkSuite()
```

Zasady:

* tylko jedna instancja,
* ponowne uruchomienie podnosi istniejące okno,
* osobny `data-app`,
* integracja z taskbarem,
* wspólna rodzina `ghost_control_suite`.

## 2. Główny układ

Widok powinien zawierać:

* nagłówek cyklu,
* wersję GhostSystemu,
* licznik odkrytych części,
* licznik aktywnych części,
* sekcje list,
* status aktualizacji,
* przycisk lekkiego odświeżenia.

Nie odwzorowywać ciężkiej mapy ani diagramu pełnej topologii.

## 3. Nagłówek statusu

Przykład:

```text
GHOSTNETWORK // CYKL 0047

ODKRYTE: 13 / 20
AKTYWNE: 7 / 20
BLOKOWANE: 4
PUBLICZNE: 2
```

Dodatkowo:

```text
GHOSTSYSTEM 1.0.47
```

Statusy:

* aktywny,
* transmisja,
* stabilizacja,
* restart wymagany.

## 4. Nawigacja sekcji

Preferowane dwa poziomy:

### Główne filtry

```text
WSZYSTKIE
PUBLICZNE
BLOKOWANE
AKTYWNE
MOJA KONTROLA
```

### Podgrupy

W `MOJA KONTROLA`:

```text
CZĘŚCI OBCE
CZĘŚCI WŁASNE
```

Alternatywnie aplikacja może pokazywać pięć stałych sekcji w jednej przewijanej liście.

Na mobilnym układzie zakładki powinny mieścić się bez szerokich napisów, wykorzystując ikony i krótkie etykiety.

## 5. Sekcja publiczna

Nagłówek:

```text
PUBLICZNE CZĘŚCI
```

Opis:

```text
Odkryte komponenty poza stabilną kontrolą terytorium.
```

Karta pokazuje:

* nazwę,
* kod części,
* klan,
* maszynę,
* profesję,
* moc,
* odległość,
* lokalizację,
* stan neutralny.

## 6. Sekcja blokowana przez inne klany

Nagłówek:

```text
BLOKOWANE CZĘŚCI
```

Karta może być pełna albo ukryta zależnie od projekcji.

Dla ukrytej:

```text
NIEZIDENTYFIKOWANY KOMPONENT

TERYTORIUM: [nazwa]
WŁAŚCICIEL: [alias]
KLAN: [klan kontrolujący]
STATUS: BLOKOWANY
```

Nie pokazywać pustych etykiet:

```text
PROFESJA: —
MOC: —
```

Sekcja szczegółów w ogóle nie powinna ich renderować.

## 7. Sekcja aktywna w naszym klanie

Nagłówek:

```text
AKTYWNE WĘZŁY KLANU
```

Pokazuje części własnej maszyny aktywowane przez innych operatorów klanu.

Karta:

* pełna nazwa,
* właściciel,
* klaster,
* profesja,
* aktywna moc,
* czas aktywności,
* stan konfliktu,
* odległość.

Wyraźnie odróżnić:

```text
WŁAŚCICIEL: INNY OPERATOR KLANU
```

od części kontrolowanej osobiście.

## 8. Sekcja „kontrolowane przeze mnie — obce”

Nagłówek:

```text
BLOKOWANE PRZEZE MNIE
```

Karta zawiera pełne dane części:

* część,
* właściwy klan,
* maszyna,
* profesja,
* supermoc,
* własny klaster,
* czas blokady.

Stan:

```text
MODUŁ NIEAKTYWNY
```

Aplikacja nie sugeruje, że operator otrzymuje moc komponentu.

## 9. Sekcja „kontrolowane przeze mnie — własne”

Nagłówek:

```text
AKTYWNE PRZEZE MNIE
```

Karta:

* część,
* maszyna,
* profesja,
* moc,
* własny klaster,
* czas aktywności,
* liczba obron,
* stan połączeń w formie lekkiego licznika.

Stan:

```text
WĘZEŁ AKTYWNY
```

## 10. Karta części

Minimalna struktura:

```text
ikona stanu
nazwa lub bezpieczny label
klan
właściciel
terytorium
stan
odległość
konflikt
akcje
```

Nie tworzyć rozbudowanego panelu z każdą informacją na stałe.

Dodatkowe dane można otworzyć w rozwijanym szczególe.

## 11. Szczegóły części

Po rozwinięciu:

* maszyna,
* profesja,
* moc,
* odkrywca, jeśli widoczny,
* data odkrycia,
* stan kotwicy,
* właściciel,
* liczba filarów klastra,
* zagrożenie klastra,
* stan konfliktu,
* status połączeń.

Renderować wyłącznie dane obecne w snapshotcie.

## 12. Konflikt

Karta zachowuje kolor stanu bazowego i otrzymuje:

```text
KONFLIKT — STAN ZAMROŻONY
```

Nie przenosić pozycji do innej sekcji przed stabilizacją.

## 13. Puste sekcje

Zamiast pustego panelu:

```text
BRAK PUBLICZNYCH CZĘŚCI
```

```text
NIE BLOKUJESZ ŻADNEGO KOMPONENTU
```

```text
TWÓJ KLAN NIE MA AKTYWNYCH WĘZŁÓW
```

Komunikaty mają być krótkie i zgodne ze stylem GhostSystemu.

## 14. Sortowanie

Domyślne:

1. konflikt,
2. kontrolowane przeze mnie,
3. aktywne,
4. odległość,
5. nazwa.

Dostępne sortowania:

* odległość,
* stan,
* klan,
* właściciel,
* ostatnia zmiana.

Nie sortować ukrytej części po prawdziwej nazwie.

## 15. Filtrowanie

Lekki filtr tekstowy może przeszukiwać wyłącznie widoczne dane:

* nazwę,
* klan,
* właściciela,
* terytorium,
* profesję.

Nie może zwracać ukrytej części po wpisaniu jej prawdziwego kodu.

## 16. Stan ładowania

Aplikacja powinna pokazać kontekstowe logi, na przykład:

```text
SYNCHRONIZACJA GHOSTNETWORK
ODCZYT PROJEKCJI WĘZŁÓW
WERYFIKACJA ZAKRESU ODBIORCY
```

Nie ładować mapy w tle.

## 17. Stan błędu

Przy błędzie snapshotu:

* zachować ostatni widok,
* oznaczyć go jako nieaktualny,
* pokazać retry,
* nie zamykać aplikacji,
* nie otwierać mapy.

## 18. Stan transmisji

Po `cycle.status = transmitting`:

```text
GHOSTNETWORK ZAMKNIĘTY
TRANSMISJA W TOKU
```

Listy mogą zostać zamrożone.

Po zużyciu części:

```text
AKTYWNY CYKL ZAKOŃCZONY
20 WĘZŁÓW ZUŻYTYCH
```

Podczas stabilizacji:

```text
NOWY CYKL OCZEKUJE NA STABILIZACJĘ
```

## 19. Dostępność

Każda akcja:

* ma ikonę,
* `title`,
* `aria-label`,
* stan focus,
* stan disabled z wyjaśnieniem.

Kolor nie jest jedynym komunikatem stanu.

## 20. Testy Sprintu 133

Minimum:

* pięć grup list,
* jedna część tylko w jednej grupie,
* pełna publiczna karta,
* ukryta blokowana karta,
* karta aktywna klanowa,
* karta `self_foreign_blocked`,
* karta `self_own_active`,
* konflikt zachowuje sekcję,
* sortowanie po odległości,
* wyszukiwanie nie ujawnia ukrytego kodu,
* puste stany,
* transmitting,
* stabilizing,
* błąd snapshotu,
* aplikacja nie ładuje mapy,
* jedna instancja okna.

## Poza sprintem

Nie wdrażać jeszcze:

* rzeczywistego show-on-map,
* teleportu,
* finalnych delt,
* pełnej responsywności,
* integracji zakupu produktu.

## DoD

Sprint jest zakończony, gdy operator może bez mapy zobaczyć wszystkie dostępne mu części, rozróżnić elementy publiczne, blokowane, aktywne i kontrolowane osobiście oraz nie otrzymuje żadnej informacji wykraczającej poza jego projekcję.

---

# Sprint 134 — GhostNetwork Suite: mapa na żądanie, teleport i oznaczenia klastrów z komponentami

> **Post-audit 2026-08-21 — wiążące.** Kanoniczny bridge to `createMap()` +
> `notifyOpenMapsBlacknetFocus()`, nie iframe. Dla GN przekazuje opaque
> `public_entity_id` albo `territory_id`. `/api/blacknet/cta/teleport` musi dla
> `source=ghostnetwork_suite` odrzucać klientowe współrzędne i rozwiązać cel po
> aktualnej backendowej projekcji visibility. Territory Control rozszerza swój
> istniejący snapshot przez `project_territory_component_for_viewer`.

**Status planu:** `SPRINT 134 — READY FOR SERVER VALIDATION`.

**Korekta UX po manualu 133:** przyciski akcji w GhostNetwork Suite używają
ikon `map` i `teleport` z tego samego języka wizualnego co Territory Control
(`▣`, `➜`). Nie pokazują tekstowych etykiet `MAPA` ani `TELEPORT`; znaczenie
pozostaje dostępne przez `title` i `aria-label`.

**Korekta manualna 134:** focus centruje dokładny marker części. Teleport do
widocznej dokładnie części prowadzi do deterministycznego bezpiecznego punktu w
jej okolicy, nie na samą kotwicę. Po zgodzie i canonical success teleport otwiera
mapę oraz pokazuje motocykl w nowej pozycji; mapa nie może otworzyć się przed
dialogiem zgody. Dla ukrytej części nadal używany jest bezpieczny punkt terytorium.

Manual potwierdził teleport i automatyczne otwarcie mapy zarówno na małych, jak
i dużych kontach. Responsywny Suite używa jednego scrolla całej zawartości jak
Cyberner; lista kart nie tworzy zagnieżdżonego scrolla, a nagłówek i filtry
naturalnie znikają podczas przewijania.

**Bramka heavy-profile:** focus, teleport i Territory Control rozwiązują
identity oraz target przez canonical GN/territory stores. Zakazane są
`get_profile`, `get_profile_with_revision`, `sync_session_profile` i
`UserProfileManager` w request path.

## Cel sprintu

Podłączyć do każdej pozycji dwie właściwe akcje:

* `Pokaż na mapie`,
* `Teleport`.

Jednocześnie zakończyć integrację z Territory Control tak, aby oba narzędzia korzystały z tych samych oznaczeń komponentów w klastrach.

Mapa pozostaje ładowana wyłącznie wtedy, gdy gracz jawnie wybierze akcję podglądu.

## 1. Wspólny bridge mapy

Użyć istniejącego mechanizmu:

```text
createMap()
notifyOpenMapsBlacknetFocus(...)
```

lub jego kanonicznego odpowiednika ustalonego w audycie.

Bridge powinien:

1. sprawdzić, czy mapa istnieje,
2. otworzyć ją tylko na żądanie,
3. poczekać na gotowość iframe,
4. wysłać bezpieczny focus target,
5. podnieść okno mapy,
6. nie zmieniać `aimed_target`.

## 2. Pokaż dokładną część

Dla:

```text
location.visibility = exact
```

akcja:

```text
show_on_map(public_entity_id)
```

Mapa:

* otwiera warstwę GhostNetwork,
* centruje część,
* podświetla marker,
* otwiera bezpieczny panel,
* nie ustawia celu hackowania.

## 3. Pokaż terytorium

Dla:

```text
location.visibility = territory_only
```

akcja otwiera:

* klaster,
* badge komponentu,
* panel terytorium.

Nie centruje ukrytej kotwicy.

Komunikat:

```text
DOKŁADNA LOKALIZACJA KOMPONENTU JEST UKRYTA
POKAZANO TERYTORIUM PRZECHOWUJĄCE CZĘŚĆ
```

## 4. Brak przecieku przez map bridge

Payload nie może zawierać:

* ukrytego `part_id`,
* prawdziwych współrzędnych,
* kodu części,
* ukrytej maszyny,
* profesji,
* mocy.

Dla ukrytej części bridge otrzymuje wyłącznie identyfikator terytorium.

## 5. Teleport do części

Dla dokładnej pozycji:

```text
teleport_target_type = ghost_part
```

Backend przed teleportem sprawdza:

* aktywny cykl,
* aktualną projekcję widoczności,
* aktualną pozycję kotwicy,
* poprawność współrzędnych,
* brak stanu restartu,
* możliwość użycia teleportu przez operatora.

Nie ufać starym współrzędnym snapshotu.

## 6. Teleport do klastra

Dla ukrytej części:

```text
teleport_target_type = territory
```

Cel:

* bezpieczny punkt klastra,
* centroid,
* dozwolona kotwica wejścia.

Nie przenosić operatora bezpośrednio na ukrytą część.

## 7. Potwierdzenie teleportu

Przed wykonaniem:

```text
TELEPORT DO WĘZŁA GHOSTNETWORK
```

lub:

```text
TELEPORT DO TERYTORIUM Z KOMPONENTEM
```

Pokazać:

* odległość,
* cel,
* typ lokalizacji,
* ostrzeżenie o konflikcie.

Przyciski:

```text
TELEPORT
ANULUJ
```

## 8. Aktualizacja motocykla

Teleport korzysta z istniejącego procesu przesuwania pozycji motocykla.

Po sukcesie:

* aktualizuje bieżącą pozycję,
* emituje istniejącą deltę pozycji,
* odświeża odległości w Victim Pickerze,
* odświeża odległości w Territory Control,
* odświeża odległości w GhostNetwork Suite,
* nie przeładowuje mapy, jeśli jest zamknięta.

## 9. Brak automatycznego ustawienia celu

Teleport ani pokazanie mapy nie może:

* ustawić `aimed_target`,
* uruchomić hacku,
* zarezerwować kolejnej części,
* rozpocząć operacji.

GhostNetwork Suite jest narzędziem obserwacyjnym i nawigacyjnym.

## 10. Territory Control — badge klastra

Karta klastra otrzymuje ikonę GhostNetwork oraz status.

Możliwe warianty:

```text
CZĘŚĆ WŁASNEGO KLANU // AKTYWNA
CZĘŚĆ OBCEGO KLANU // BLOKOWANA
KOMPONENT NIEZIDENTYFIKOWANY // BLOKOWANY
KOMPONENT // KONFLIKT
```

Badge nie zastępuje istniejącego koloru zagrożenia:

* zielony,
* pomarańczowy,
* czerwony.

## 11. Territory Control — szczegół klastra

W szczególe dodać sekcję:

```text
GHOSTNETWORK
```

Dla pełnej widoczności:

* część,
* klan,
* maszyna,
* profesja,
* moc,
* status,
* czas aktywności lub blokady.

Dla ukrytej:

```text
TERYTORIUM PRZECHOWUJE NIEZIDENTYFIKOWANY KOMPONENT
```

Nie wyświetlać pustych szczegółów.

## 12. Synchronizacja między aplikacjami

Kliknięcie klastra w Territory Control może opcjonalnie otworzyć GhostNetwork Suite i ustawić filtr na powiązaną część.

Kliknięcie części w GhostNetwork Suite może podświetlić powiązany klaster w już otwartym Territory Control.

Nie uruchamiać drugiej aplikacji automatycznie bez akcji gracza.

## 13. Ghost Anchor

`Pokaż na mapie`:

* centruje niezależną kotwicę,
* pokazuje specjalny marker.

Teleport:

* używa zachowanych współrzędnych,
* nadal ponownie je waliduje.

## 14. Konflikt

Podczas konfliktu:

* mapa pokazuje badge sporu,
* teleport jest nadal możliwy, jeśli zwykłe zasady na to pozwalają,
* potwierdzenie ostrzega o aktywnym konflikcie,
* dokładność pozycji nadal zależy od zamrożonej projekcji widoczności.

## 15. Nieistniejący już target

Jeżeli między snapshotem a kliknięciem część została:

* ukryta,
* przeniesiona technicznie,
* zużyta,
* objęta innym terytorium,

backend zwraca aktualną projekcję.

Frontend:

* aktualizuje kartę,
* nie wykonuje starej akcji,
* pokazuje czytelny komunikat.

## 16. Stany przycisków

### Pokaż na mapie

Aktywny, gdy istnieje:

* dokładna część,
* terytorium,
* historyczna kotwica.

### Teleport

Disabled, gdy:

* restart wymagany,
* brak poprawnej lokalizacji,
* stan transmisji blokuje akcje,
* bieżący system teleportu odrzuca cel.

Tooltip wyjaśnia powód.

## 17. Testy Sprintu 134

Minimum:

* mapa nie ładuje się przed kliknięciem,
* dokładna część centruje marker,
* ukryta część centruje terytorium,
* payload nie zawiera ukrytych współrzędnych,
* pokazanie mapy nie ustawia celu,
* teleport do dokładnej części,
* teleport do klastra,
* ponowna walidacja przed teleportem,
* teleport odświeża odległości wszystkich narzędzi,
* konflikt pokazuje ostrzeżenie,
* consumed część blokuje akcję,
* Ghost Anchor działa,
* badge własnej części,
* badge obcej części,
* badge ukrytej części,
* Territory Control i Suite używają tej samej projekcji.

## Poza sprintem

Nie wykonywać jeszcze:

* końcowego polishu GUI,
* pełnej obsługi delt w aplikacji,
* finalnej regresji zakupów i instalacji.

## DoD

Sprint jest zakończony, gdy każda część może bezpiecznie otworzyć właściwy punkt mapy albo terytorium, teleport nie ujawnia ukrytej kotwicy, a Territory Control jednoznacznie pokazuje, które klastry przechowują własne i obce komponenty.

## Wynik implementacji lokalnej 2026-08-27

- Suite używa ikon Territory Control `▣` oraz `➜`, bez napisów na przyciskach.
- Map bridge przekazuje tylko opaque `public_entity_id` albo `territory_id` i
  rozwiązuje docelową warstwę dopiero w otwartej mapie.
- Teleport ponownie sprawdza bieżący cykl, lifecycle oraz visibility targetu;
  współrzędne klienta są zabronione.
- Zmiana projekcji, `transmitting` i `consumed` blokują starą akcję fail-closed.
- Territory Control renderuje istniejącą canonical projection jako badge i
  szczegóły, bez ujawniania ukrytej tożsamości.
- 65/65 testów GN/Territory, 13/13 endpoint/session oraz 16/16 pakietów Node — OK.
- `py_compile`, `node --check`, `git diff --check` — OK.
- Bez deployu, restartu PM2 i commita.

---

# Sprint 135 — GhostNetwork Suite: GUI desktopowe, delty, recovery i regresja całej Ghost Control Suite

> **Post-audit 2026-08-21 — wiążące.** `GhostNetworkDeltaClient` istnieje,
> ale obecnie mieszka w pliku mapy. Przed użyciem przez Suite należy wydzielić
> lekki wspólny transport/dedupe/recovery bez Leaflet; Suite nie może ładować
> mapowego JS. Delty korzystają z `/api/state/changes`, recovery z
> `snapshot?view=suite`, a snapshot/recovery nie odtwarza SFX.

**Status realizacji:** `SPRINT 135 — READY FOR SERVER VALIDATION`.

**Bramka heavy-profile:** delta/recovery nie odpytują `/api/profile`, nie
wykonują profile overlay ani pełnego refreshu. Shared client przechowuje tylko
viewer-projected model Suite i wersje, nigdy profil.

## Cel sprintu

Dokończyć produkcyjne GUI GhostNetwork Suite, podłączyć je do wspólnego klienta delt i recovery oraz przeprowadzić regresję całej rodziny czterech narzędzi.

Po tym sprincie zaawansowany operator może obsługiwać większość warstwy strategicznej z lekkiego desktopu, używając mapy tylko do świadomego podglądu przestrzennego.

## 1. Rejestr produktu

Dodać produkt do istniejącego katalogu Googleplex:

```text
type: pro-system-tool
category: pro-system-tools
family_id: ghost_control_suite
id: ghostnetworkSuite
system_launcher: createGhostNetworkSuiteApp
```

Produkt ma:

* nazwę,
* opis,
* ikonę,
* cenę z konfiguracji,
* kontrakt instalacji,
* launcher.

Nie tworzyć osobnej procedury zakupu.

## 2. Instalacja i launcher

Po zakupie:

* produkt zapisuje się istniejącą ścieżką,
* aplikacja pojawia się na desktopie,
* launcher używa wspólnego icon packa,
* brak produktu blokuje uruchomienie,
* istniejące profile z przyznanym produktem działają po migracji.

## 3. Finalny układ GUI

Okno powinno być zwarte i czytelne.

Sekcje:

* pasek statusu cyklu,
* szybkie liczniki,
* filtry,
* lista kart,
* rozwijane szczegóły,
* pasek aktualizacji.

Nie robić ogromnej tabeli z dwudziestoma kolumnami.

## 4. Responsive desktop i mobile

Desktop:

* lista i panel szczegółów mogą działać obok siebie.

Węższe okno:

* szczegóły otwierają się pod kartą albo jako osobny ekran,
* przyciski zmieniają się w ikony,
* etykiety nie nachodzą na statusy,
* sekcje są przewijalne.

Nie skalować całego okna transformacją CSS.

## 5. Wspólny klient delt

Aplikacja rejestruje się w:

```text
GhostNetworkDeltaClient
```

Obsługiwane eventy:

* `ghost.part_discovered`
* `ghost.part_contained`
* `ghost.part_revealed`
* `ghost.part_activated`
* `ghost.part_deactivated`
* `ghost.part_contested`
* `ghost.part_conflict_resolved`
* `ghost.part_anchor_migrated`
* `ghost.part_consumed`
* `ghost.machine_progress_changed`
* `ghost.cycle_locked`
* `ghost.signal_sent`
* `ghost.version_changed`
* `ghost.restart_required`
* `ghost.cycle_activated`

## 6. Przenoszenie pozycji między sekcjami

Po zmianie stanu część powinna:

* zaktualizować kartę,
* opuścić poprzednią grupę,
* wejść do nowej grupy,
* zachować rozwinięcie, jeśli nadal jest widoczna,
* nie duplikować się.

Przykład:

```text
PUBLICZNA
→ BLOKOWANA PRZEZE MNIE
→ PUBLICZNA
→ AKTYWNA W KLANIE
```

## 7. Zmiana widoczności

Najważniejszy przypadek:

```text
public → blocked
```

Dla nieuprawnionego operatora karta:

* usuwa nazwę,
* usuwa kod,
* usuwa profesję,
* usuwa moc,
* usuwa dokładną pozycję,
* zmienia akcję mapy na terytorium.

Nie pozostawia starych danych w DOM, datasetach ani tooltipach.

## 8. Recovery

Przy:

* luce wersji,
* nieznanym `public_entity_id`,
* zmianie cyklu,
* niespójnym grupowaniu,
* błędzie zastosowania delty,

aplikacja pobiera:

```text
snapshot?view=suite
```

Następnie:

* odtwarza listy,
* zachowuje aktywny filtr,
* przywraca fokus, jeśli element nadal istnieje,
* nie otwiera mapy,
* nie pobiera pełnego profilu.

## 9. Zamknięcie okna

Po zamknięciu:

* wyrejestrować callbacki,
* usunąć lokalne listenery,
* anulować pending retry widoku,
* zachować wspólnego klienta, jeśli korzystają z niego inne aplikacje.

Nie tworzyć kolejnego delta clienta po każdym uruchomieniu okna.

## 10. Restart GhostSystemu

Po `ghost.restart_required`:

* aplikacja zostaje zablokowana,
* listy pozostają jako końcowy snapshot transmisji,
* przyciski mapy i teleportu są disabled,
* widoczny jest status aktualizacji.

Po restarcie:

* aplikacja może zostać automatycznie zamknięta lub odtworzona na nowym pulpicie zgodnie z istniejącym lifecycle,
* stary cykl nie wraca do aktywnej listy.

## 11. Stabilizacja

Po transmisji:

```text
BRAK AKTYWNYCH CZĘŚCI
NOWY CYKL ZA: [czas]
```

Odliczanie może być lokalne na podstawie `stabilization_until`, ale backend pozostaje źródłem prawdy o rozpoczęciu kolejnego cyklu.

## 12. Wspólne wzorce wizualne

Cztery aplikacje powinny używać:

* tej samej wysokości nagłówków,
* tego samego systemu ikon,
* podobnych przycisków mapy i teleportu,
* wspólnych statusów synchronizacji,
* wspólnych tooltipów,
* tych samych stanów błędu i recovery.

Nie muszą mieć identycznego layoutu, ponieważ obsługują inne dane.

## 13. Regresja Victim Picker

Sprawdzić:

* ustawianie `aimed_target`,
* skan,
* oznaczanie celów,
* mapę na żądanie,
* teleport,
* odległości po zmianie pozycji,
* brak konfliktu listenerów.

GhostNetwork Suite nie może zmieniać celu gracza.

## 14. Regresja Territory Control

Sprawdzić:

* klastry i samotne filary,
* minimum trzy filary,
* badge części,
* własna część,
* obca część,
* ukryta część,
* konflikt,
* porzucenie obiektu,
* rozpad klastra,
* aktualizacja części po stabilizacji,
* wspólna mapa i teleport.

Porzucenie kotwicy nie usuwa części GhostNetwork.

## 15. Regresja Operation Control

Sprawdzić:

* listy operacji,
* grupy,
* anulowanie,
* incydenty,
* odległości,
* aktualizację pozycji,
* brak mieszania delt GhostNetwork z deltami operacji.

## 16. Regresja mapy

Sprawdzić:

* mapa ładuje się wyłącznie na żądanie,
* focus części,
* focus terytorium,
* Ghost Anchor,
* markery,
* linie,
* brak przecieku danych,
* brak wielokrotnego tworzenia iframe,
* powrót do aplikacji po zamknięciu mapy.

## 17. Regresja zakupów

Dla wszystkich czterech produktów:

* zakup,
* brak środków,
* ponowny zakup,
* instalacja,
* istniejący zakup,
* launcher,
* jedna instancja,
* odinstalowanie, jeśli system je obsługuje,
* restart profilu.

## 18. Testy widoczności E2E

Dla jednej części wykonać pełny przebieg:

1. Neutralna — pełna dla wszystkich.
2. Zablokowana przez gracza A — pełna dla A.
3. Zablokowana — ukryta dla członka klanu A.
4. Zablokowana — ukryta dla właściwego klanu części.
5. Aktywna — pełna dla właściwego klanu.
6. Aktywna — zaszyfrowana dla obcych.
7. Kontestowana — widoczność zamrożona.
8. Zużyta — usunięta z aktywnych list.

Sprawdzić snapshot, deltę, GUI, mapę i Territory Control.

## 19. Testy wydajności

Mierzyć:

* czas otwarcia aplikacji,
* czas snapshotu,
* wielkość response,
* czas aktualizacji jednej karty,
* czas przegrupowania,
* liczbę listenerów,
* zużycie pamięci po wielokrotnym otwieraniu,
* brak pełnego profilu,
* brak ciężkiego pollera,
* brak renderowania mapy bez żądania.

## 20. Testy recovery

Minimum:

* utrata jednej delty,
* zmiana widoczności podczas zamkniętego okna,
* otwarcie po zmianie cyklu,
* consumed podczas braku połączenia,
* restart wymagany,
* powrót po restarcie,
* błąd snapshotu,
* retry z backoffem.

## 21. Testy bezpieczeństwa

Sprawdzić, że ukryte dane nie występują w:

* JSON,
* HTML,
* `dataset`,
* `title`,
* `aria-label`,
* logach konsoli,
* bridge mapy,
* payloadzie teleportu,
* cache frontendowym po zmianie widoczności.

## 22. Dokumentacja

Dodać:

```text
doc/systems/ghostnetwork/GHOSTNETWORK_SUITE.md
```

Dokument opisuje:

* przeznaczenie,
* grupy części,
* widoczność,
* mapę,
* teleport,
* integrację z Territory Control,
* delty,
* recovery,
* zależności z pozostałymi narzędziami.

## DoD

Sprint jest zakończony, gdy:

1. GhostNetwork Suite można kupić, zainstalować i uruchomić.
2. Lista prezentuje wszystkie części widoczne dla operatora.
3. Publiczne, blokowane, klanowe i własne części są jednoznacznie rozdzielone.
4. Każda pozycja posiada bezpieczne akcje mapy i teleportu.
5. Ukryta część nigdy nie ujawnia dokładnej kotwicy.
6. Territory Control pokazuje klastry przechowujące komponenty.
7. Delty aktualizują pojedyncze karty bez pełnego odświeżenia.
8. Recovery obejmuje wyłącznie scope GhostNetwork.
9. Zamknięcie okna nie pozostawia listenerów.
10. Cała Ghost Control Suite przechodzi regresję.
11. Mapa nie jest ładowana bez jawnej akcji gracza.
12. Narzędzie nie tworzy żadnego alternatywnego źródła prawdy.

Po Sprintach 131–135 zaawansowany operator dostaje kompletną lekką ścieżkę obserwacji GhostNetwork: widzi, gdzie znajdują się publiczne części, kto blokuje komponenty, które moduły jego klanu są aktywne oraz jakie części kontroluje osobiście — a ciężką mapę otwiera wyłącznie wtedy, gdy naprawdę potrzebuje zobaczyć przestrzenny kontekst.

Implementacja 2026-08-27: Suite korzysta ze shared delta clienta, stosuje
serverową `suite_part_projection`, wykonuje replacement przy zmianie visibility,
usuwa consumed przez opaque ID i odzyskuje stan wyłącznie przez `view=suite`.
Mapa i Suite mają osobne baseline, adapter-specific recovery oraz wspólny
transport bez dodatkowego pollera. Walidacja: 231/231 GhostNetwork, 93/93
Ghost Control/territory/session i 18/18 JavaScript; składnia i diff — OK.
Bez deployu, restartu PM2 i commita.

---

> Historyczny wstęp do planu 136–138, zastąpionego rewizją poniżej: trzy sprinty
> miały domknąć obieg narracyjny przez event bridge, model i publikację
> `ollama_enriched`.

# Rewizja roadmapy Ollama/Outbox — Sprinty 135.1–135.5

Data rewizji: 2026-08-27.

Status: `SPRINT 135.1 — COMPLETE / READY FOR SPRINT 135.2`.

Ta rewizja jest wiążąca wobec historycznych planów Sprintów 136–138 zapisanych
poniżej. Stare rozdziały pozostają materiałem źródłowym i nie są usuwane, ale
nie stanowią już równoległej kolejności implementacji.

## Powód rewizji

Audit 135.1 potwierdził, że repo posiada dwa różne mechanizmy nazywane
outboxem:

1. plikowy, administracyjny BlackNet Ollama outbox ze Sprintu 83;
2. trwały SQLite `ghost_narrative_outbox` ze Sprintu 129.

Nie wolno podłączać modelu do dwóch kolejek ani rozpoczynać od event bridge'a.
Najpierw istniejący store Sprintu 129 musi zostać przekształcony w jeden
niezawodny transport tasków dla całego GhostSystemu. Plikowy outbox zostaje
wyłącznie diagnostycznym eksportem canonical taska.

Odzyskany zakres obejmuje:

- formalnie zamrożony Sprint 84 `Ollama Enriched Signal Ingest + Mixed Feed`;
- świadomie odłożony `BlackNet AI Ecosystem (Sprint 21+)`;
- GhostNetwork/GhostSignal i odpowiedzi z 2108;
- BlackNet, Googleplex News, Cyberner AI Central/AGI 2108;
- dedykowane narzędzie kupowane i instalowane z Googleplex.

## Wiążący przepływ

```text
canonical event albo authorized installed-app request
→ audience-projected facts
→ canonical Ollama Outbox task
→ local Ollama worker/LLM
→ canonical Inbox candidate
→ validation/quarantine
→ publication receipt/router
→ BlackNet | Googleplex News | Googleplex tool | Cyberner AGI 2108
```

Ollama jest demonem narracyjnym, nie source of truth. Nie może zmieniać
gameplayu, outcome GhostSignalu, audience, faktów, walletu, profilu, terytoriów,
części GN ani operacji.

## Nowa kolejność sprintów

### Sprint 135.2 — Canonical LLM Task Transport

Dokument:
`doc/sprints/sprint_135_2_canonical_llm_task_transport.md`.

Cel: niezawodny transport tasków, jeszcze bez LLM.

- addytywne rozszerzenie `ghost_narrative_outbox`;
- `source_scope`, `processor=ollama`, `target_medium` i wersje kontraktów;
- atomic enqueue/claim/lease/renew/complete/retry/dead-letter;
- dokładnie jeden task per event/audience/medium;
- dokładnie jeden aktywny lease owner;
- crash/lease recovery bez utraty i duplikatu;
- legacy BlackNet file outbox tylko jako DB → JSON diagnostic export.

Poza zakresem: producenci, aplikacja Googleplex, worker, Inbox i publikacja.

Implementacja 2026-08-27: schema/store, canonical dedupe, transakcyjny claim,
owner/lease CAS, retry/dead-letter, crash recovery, bounded cursor i indeksy są
gotowe lokalnie. Rekordy Sprintu 129 są migrowane addytywnie, a plikowy
BlackNet outbox jest read-only eksportem canonical DB. Nie podłączono Ollamy.

Status: `SPRINT 135.2 — READY FOR SERVER VALIDATION`.

### Sprint 135.3 — Event Producers and Googleplex App Ingress

Dokument:
`doc/sprints/sprint_135_3_llm_event_producers_googleplex_ingress.md`.

- GhostNetwork/GhostSignal oraz BlackNet world facts producers;
- visibility projection przed enqueue;
- bounded ingress dla zainstalowanej aplikacji Googleplex;
- entitlement, session/precommit guard, quota i receipt/dedupe;
- nadal brak klienta Ollamy i publikacji.

Implementacja 2026-08-28: canonical event bridge GhostNetwork/GhostSignal,
bounded BlackNet digest producer oraz owner-scoped Googleplex ingress są
gotowe lokalnie. Audience jest projektowane przed enqueue, replay i requesty
równoległe zachowują jeden task, a nowe ścieżki nie czytają ani nie zapisują
pełnego profilu. Nie podłączono klienta Ollamy, Inboxu ani publikacji.

Status: `SPRINT 135.3 — READY FOR SERVER VALIDATION`.

### Sprint 135.4 — Ollama Worker and Canonical Inbox

Dokument:
`doc/sprints/sprint_135_4_ollama_worker_canonical_inbox.md`.

- pierwszy lokalny worker Ollamy;
- structured JSON, timeout i lease heartbeat;
- canonical Inbox, validator i quarantine;
- zaakceptowany wynik pozostaje niewidoczny dla graczy.

Status: `SPRINT 135.4 — COMPLETE / READY FOR SPRINT 135.4.1`.

### Sprint 135.4.1 — Googleplex Home and News Foundation

Dokument:
`doc/sprints/sprint_135_4_1_googleplex_home_news_foundation.md`.

- status: `PLANNED / READY TO START`;
- zakres został rozpisany od nowa według
  `googleplex_news_functional_spec.md`, `googleplex_news_visual_css_spec.md`
  oraz zatwierdzonej referencji `doc/visual/ggpl_news.png`;
- pusty query otwiera Home/News, a niepusty zachowuje istniejący search,
  purchase, install i travel;
- audience-projected, bounded read surface z kartami `ACTIONABLE` lub
  `STAMP_ONLY` i wyłącznie canonical action bridge;
- cztery poziomy geometrii `hero/large/medium/small`, editorialowy CSS Grid,
  dolny status strip i jeden scroll na mobile;
- heavy-profile hot path, wywołanie Ollamy i enqueue tasków podczas open/refresh
  pozostają równe zero;
- accepted Inbox candidate pozostaje niewidoczny bez publication receipt z
  przyszłego Sprintu 135.5.

### Sprint 135.4.2 — Purchasable Googleplex LLM Tool

Dokument:
`doc/sprints/sprint_135_4_2_googleplex_purchasable_llm_tool.md`.

- prosty produkt kupowany i instalowany z Googleplex;
- canonical purchase/install/uninstall i launcher;
- approved templates zamiast dowolnego promptu;
- jeden bezpieczny task receipt oraz owner-scoped status;
- brak wyświetlenia body odpowiedzi przed Sprintem 135.5.

### Sprint 135.5 — LLM Publishers

Dokument:
`doc/sprints/sprint_135_5_llm_publishers_blacknet_googleplex_cyberner.md`.

- BlackNet mixed feed `ollama_enriched`;
- newsy na Googleplex Home;
- owner-scoped wynik w kupowanym narzędziu;
- Cyberner AI Central/AGI 2108;
- exactly-once publication receipts, audience prepublish guard i fallback;
- tylko `ACCEPTED` Inbox candidate może zostać opublikowany.

### Sprint 135.6 — Hardening and Cutover

Pozostaje końcową bramką replay/crash/load/visibility, backpressure,
observability, runbooka i controlled cutover. Cutover jest fail-closed przy
jakimkolwiek full-profile read/write, skanie wszystkich profili albo
per-recipient `profile_json`; obowiązuje fixture 35 MB i komplet metryk
heavy-profile równy zero.

## Mapowanie historycznych Sprintów 136–138

| Historyczny plan | Wiążący następca |
| --- | --- |
| 136 — event bridge do outboxa | 135.2 transport + 135.3 producers |
| 137 — Ollama Inbox/Outbox | 135.4 worker + canonical Inbox |
| 138 — publikacja do BlackNet | 135.4.1 + 135.4.2 + 135.5 publishers |

Historyczne opisy 136–138 mogą dostarczać przypadki testowe i założenia
narracyjne, ale ich numeracja, kolejność i schema nie są już wiążące.

## Aktualna bramka

```text
135.1 COMPLETE
→ 135.2 COMPLETE
→ 135.3 COMPLETE
→ 135.4 COMPLETE
→ 135.4.1 PLANNED / READY TO START
→ 135.4.2 BLOCKED BY 135.4.1
→ 135.5 BLOCKED BY 135.4.2
```

Pierwotna rewizja roadmapy była dokumentacyjna. Implementacja 135.2 zmienia
lokalny runtime i addytywny schema contract, ale nie wykonała deployu,
produkcyjnej migracji ani zmiany konfiguracji procesów.

# Sprint 136 — GhostNetwork: bridge zdarzeń do BlackNet Outbox

> **Post-audit 2026-08-21 — wiążące.** Sprint rozszerza istniejące
> `GhostNarrativePublisher` i `ghost_narrative_outbox` ze Sprintu 129, zamiast
> tworzyć drugi bridge lub kolejkę. Najpierw usuwa możliwość przeniesienia
> surowego `entity_id/part_id` w publicznym generic fact, następnie dodaje
> audience fan-out przez `GhostVisibilityService` i rozszerza allowlistę.

**Status planu:** `QUEUED — po domknięciu GhostNetwork Suite 131–135`.

**Bramka heavy-profile:** audience fan-out nie może używać `list_profiles()`,
per-recipient `get_profile()` ani batch parsowania `profile_json`. Jeżeli brak
lekkiego indeksu clan/recipient, Sprint 136 dodaje go przed publikacją. Outbox
zawiera wyłącznie audience-specific projected facts.

## Cel sprintu

Podłączyć zatwierdzone zdarzenia GhostNetwork do istniejącego pipeline’u narracyjnego BlackNetu.

BlackNet Outbox ma od tej pory otrzymywać również fakty dotyczące:

* odkrywania części,
* blokowania komponentów,
* aktywowania modułów,
* walk i obron,
* odbijania części,
* powstawania połączeń,
* postępu maszyn,
* domknięcia sieci,
* transmisji GhostSignalu,
* zmiany wersji GhostSystemu.

Sprint nie uruchamia jeszcze generowania tekstu przez Ollamę. Przygotowuje bezpieczne, wersjonowane zadania narracyjne.

Backend nadal rozstrzyga, co faktycznie się wydarzyło. Ollama może później jedynie opisać zatwierdzone wydarzenie. 

## 1. Integracja z istniejącym outboxem

Nie tworzyć drugiego, konkurencyjnego systemu kolejek, jeżeli BlackNet posiada już działający outbox.

Rozszerzyć istniejący kontrakt o:

```text
source_scope: ghostnetwork
source_event_id
cycle_id
signal_id
part_id
territory_id
state_version
narrative_thread_id
```

Dopuszczalne źródła:

```text
world
blacknet
ghostnetwork
system
```

GhostNetwork ma korzystać z tej samej obsługi:

* statusów,
* retry,
* deduplikacji,
* priorytetów,
* publikacji,
* audytu.

## 2. Bridge zdarzeń domenowych

Dodać obsługę do istniejącego komponentu:

```text
GhostNarrativePublisher
```

Minimalne rozszerzenie kontraktu:

```text
handle_domain_event(event)
is_narrative_worthy(event)
build_audience_tasks(event)
build_blacknet_facts(event, audience)
enqueue_tasks(tasks)
```

Bridge subskrybuje zapisane wydarzenia domenowe, a nie wywołania frontendu.

## 3. Dozwolone zdarzenia

Podstawowa allowlista:

```text
ghost.part_discovered
ghost.part_contained
ghost.part_revealed
ghost.part_activated
ghost.part_deactivated
ghost.part_defended
ghost.part_recovered
ghost.part_contested
ghost.part_conflict_resolved

ghost.connection_changed
ghost.machine_progress_changed
ghost.machine_online
ghost.machine_offline

ghost.cycle_locked
ghost.signal_sent
ghost.version_changed
ghost.stabilization_started
ghost.cycle_activated
```

Zdarzenia techniczne niewidoczne narracyjnie:

```text
ghost.part_reserved
ghost.part_reservation_released
ghost.part_reservation_expired
ghost.reward_pending
ghost.delta_published
ghost.health_check_completed
```

Nie mogą trafiać do BlackNetu.

## 4. Polityka istotności

Nie każde `ghost.connection_changed` powinno tworzyć osobny sygnał.

Dodać:

```text
GhostNarrativeSignificancePolicy
```

Polityka ocenia:

* typ wydarzenia,
* pierwsze wystąpienie w cyklu,
* wpływ na postęp maszyny,
* zmianę układu strategicznego,
* liczbę uczestników,
* długość konfliktu,
* znaczenie dla domknięcia sieci,
* czas od ostatniego podobnego sygnału.

Poziomy:

```text
ignore
low
normal
high
critical
```

Przykłady:

* pierwsza część cyklu — `high`,
* zwykłe kolejne połączenie — `low`,
* pierwsza kompletna maszyna — `high`,
* odbicie ostatniej brakującej części — `critical`,
* GhostSignal — `critical`.

## 5. Łączenie drobnych wydarzeń

Dodać możliwość agregowania wydarzeń w krótkim oknie.

Przykład:

```text
3 aktywacje części Echo Wolności w ciągu 10 minut
```

mogą utworzyć jeden task:

```text
Echo Wolności uruchomiło trzy kolejne moduły Libertas.
```

Agregator nie zmienia historii domenowej. Łączy wyłącznie zadania narracyjne.

Klucz grupowania może obejmować:

```text
cycle_id
event_family
clan_code
machine_code
time_bucket
```

## 6. Projekcja widoczności przed outboxem

Bridge musi najpierw użyć:

```text
GhostVisibilityService
```

Dopiero potem budować fakty dla konkretnej grupy odbiorców.

Nie wolno umieszczać pełnych danych w outboxie publicznym z założeniem, że Ollama ich nie wykorzysta.

Dla blokowanej części publiczny task może zawierać:

```json
{
  "territory_contains_part": true,
  "part_identity": null,
  "part_clan": null,
  "machine": null,
  "profession": null,
  "ability": null,
  "owner_clan": "virex",
  "module_state": "blocked"
}
```

Właściciel terytorium może otrzymać osobny task z pełną tożsamością.

## 7. Zakresy odbiorców

Dozwolone:

```text
public
clan
owner
player
```

Jedno wydarzenie może utworzyć kilka tasków.

Przykład aktywacji części:

### Publiczny

* aktywny węzeł,
* klan,
* lokalizacja,
* zaszyfrowany moduł.

### Właściwy klan

* pełna nazwa części,
* maszyna,
* profesja,
* supermoc,
* właściciel.

### Właściciel

* pełne dane i wpis o jego terytorium.

Każdy task posiada własny `audience_scope`.

## 8. Kontrakt tasku narracyjnego

Minimalna struktura:

```text
task_id
source_scope
source_event_id
cycle_id
signal_id
state_version

medium
audience_scope
audience_clan
audience_owner

event_family
truth_class
priority
narrative_thread_id

facts_json
allowed_actions_json
editorial_rules_json

canon_version
ghostsystem_version
prompt_version

status
dedupe_key
created_at
expires_at
```

Dla tego pipeline’u:

```text
medium = blacknet
truth_class = canonical
```

Ollama może zwrócić interpretacyjny język, ale nie może zmienić klasy źródłowego faktu.

## 9. Fakty wiążące

Każdy fakt otrzymuje stabilny identyfikator:

```text
fact_id
fact_type
value
visibility_scope
source_event_id
```

Przykład:

```json
{
  "fact_id": "fact-part-activated-9281",
  "fact_type": "part_activated",
  "value": {
    "clan": "phantom_mesh",
    "territory": "territory_441",
    "module_identity_visible": false
  },
  "visibility_scope": "public",
  "source_event_id": "event_9281"
}
```

Późniejszy output Ollamy musi wskazywać użyte `fact_refs`.

## 10. Wątki narracyjne

Dodać stabilne wątki:

```text
ghost-cycle:<cycle_id>
ghost-part:<part_id>
ghost-machine:<cycle_id>:<machine_code>
ghost-conflict:<conflict_id>
ghost-signal:<signal_id>
```

Dzięki temu kolejne sygnały mogą kontynuować historię:

* znalezienie części,
* późniejsza blokada,
* atak,
* odbicie,
* aktywacja,
* utrzymanie podczas transmisji.

Outbox nie potrzebuje pełnej historii. Może otrzymać skrót wątku.

## 11. CTA

Dozwolone akcje dla tasków GhostNetwork:

```text
open_ghostnetwork_suite
show_ghostnetwork_part
show_ghostnetwork_territory
open_territory_control
open_cyberner_channel
open_ghostsignal_archive
```

Model nie może tworzyć dowolnych URL ani endpointów.

Dla ukrytej części:

```text
show_ghostnetwork_territory
```

zamiast dokładnej lokalizacji komponentu.

## 12. Deduplikacja

Przykładowy klucz:

```text
blacknet:ghostnetwork:<event_id>:<audience_scope>
```

Dla agregatu:

```text
blacknet:ghostnetwork:<cycle_id>:<event_family>:<time_bucket>:<audience>
```

Retry eventu nie może utworzyć kolejnego tasku.

## 13. Deterministyczny fallback

Każdy task powinien posiadać:

```text
fallback_template_key
fallback_payload
```

Jeżeli Ollama jest niedostępna, BlackNet może opublikować prosty, deterministyczny sygnał.

Przykład:

```text
fallback_template_key:
ghost_part_activated_public
```

Brak modelu nie może zatrzymać informowania graczy o ważnych zdarzeniach.

## 14. Priorytety

Przykładowe priorytety:

```text
critical:
  cycle_locked
  signal_sent
  restart_required

high:
  machine_online
  part_recovered
  first_part_discovered

normal:
  part_activated
  part_contained
  part_defended

low:
  connection_changed
  machine_progress_changed
```

Critical otrzymuje najwyższy priorytet claim/publikacji, ale nie omija trwałego
outboxu, dedupe ani exactly-once.

## 15. Obserwowalność

Logować:

* odebrany event,
* wynik significance policy,
* liczbę tasków,
* zakresy odbiorców,
* `fact_ids`,
* dedupe,
* wybrany fallback,
* czas budowy outboxa,
* odrzucone zdarzenia.

## Testy Sprintu 136

Minimum:

* odkrycie części tworzy task publiczny,
* blokowana część nie ujawnia tożsamości publicznie,
* właściciel otrzymuje pełny task,
* aktywna część tworzy wariant publiczny i klanowy,
* rezerwacja nie tworzy tasku,
* trzy małe zdarzenia mogą zostać zagregowane,
* pierwsza część ma wyższy priorytet,
* GhostSignal ma priorytet critical,
* retry eventu nie duplikuje tasku,
* CTA ukrytej części prowadzi do terytorium,
* każdy task posiada fallback,
* błąd bridge’a nie cofa zdarzenia GhostNetwork.

## DoD

Sprint jest zakończony, gdy BlackNet Outbox otrzymuje bezpieczne, deduplikowane i gotowe do narracyjnego przetworzenia fakty dotyczące ważnych działań GhostNetwork.

---

# Sprint 137 — Ollama Inbox/Outbox: generowanie i walidacja sygnałów GhostNetwork

> **Post-audit 2026-08-21 — wiążące.** Realny worker Ollamy jeszcze nie
> istnieje; obecny BlackNet Ollama outbox jest adminowym file store i raportuje
> `ollama_executed=false`. Pierwszy worker claimuje addytywnie rozszerzone
> rekordy `ghost_narrative_outbox` z `medium=ollama_outbox`, wykorzystuje
> istniejące `build_model_input_package` / `validate_model_output`, ma
> wersjonowany ecosystem oraz `status/verify/dry-run`.

**Status planu:** `QUEUED — po Sprint 136`.

**Bramka heavy-profile:** worker nie czyta profilu podczas
claim/generate/validate/retry i nie importuje heavy helperów runtime. Model
otrzymuje wyłącznie zatwierdzony, ograniczony task zapisany przez Sprint 136.

## Cel sprintu

Utworzyć pierwszy runtime worker Ollamy, który atomowo claimuje zadania
GhostNetwork z istniejącego `ghost_narrative_outbox` (`medium=ollama_outbox`) i
zapisuje ustrukturyzowane, zwalidowane wyniki. Adminowy plikowy BlackNet Ollama
outbox pozostaje narzędziem diagnostycznym, a nie kolejką workera.

Model nie otrzymuje dostępu do tabel GhostNetwork ani pełnych profili. Pracuje wyłącznie na zatwierdzonym pakiecie faktów przygotowanym w Sprincie 136. 

## 1. Lifecycle zadania inbox

Rozszerzyć addytywnie obecne statusy
`created/ready/processing/processed/failed/expired/archived`; nie przepisywać
historycznych rekordów tylko dla zmiany nazewnictwa. Runtime worker używa:

```text
ready
claimed
processing
generated
validated
rejected
retry_wait
dead_letter
processed
```

Worker atomowo przejmuje jeden task.

Pola przejęcia:

```text
claimed_by
claimed_at
lease_until
attempt_count
```

Jeżeli worker przestanie działać, task po wygaśnięciu lease może zostać odzyskany.

## 2. Obsługa `source_scope = ghostnetwork`

Worker rozpoznaje:

```text
source_scope: ghostnetwork
medium: blacknet
```

i używa dedykowanego prompt contract:

```text
blacknet_ghostnetwork_signal_v1
```

Nie mieszać tego z promptem zwykłego podsumowania świata.

## 3. Pakiet wejściowy

Ollama otrzymuje:

```text
task_id
medium
audience
truth_class
event_family

canon_version
ghostsystem_version
cycle_id
signal_number

facts
fact_refs
narrative_context
editorial_rules
allowed_actions
output_schema
```

Nie otrzymuje:

* pełnej bazy,
* ukrytych części,
* tabel nagród,
* adresów mailowych,
* danych sesji,
* prywatnych profili,
* dowolnych endpointów.

## 4. Reguły promptu GhostNetwork

Prompt systemowy powinien jasno określać:

* nie dodawaj nowych faktów,
* nie zmieniaj stanu części,
* nie wybieraj wyniku transmisji,
* nie ujawniaj pól `null`,
* nie zgaduj nazwy ukrytej części,
* nie twórz nowych graczy ani lokalizacji,
* użyj wyłącznie podanych `fact_refs`,
* zwróć wyłącznie JSON,
* zachowaj styl BlackNetu,
* nie udawaj komunikatu autorytatywnego backendu.

## 5. Rodziny sygnałów

Obsłużyć co najmniej:

```text
part_discovery
part_blockade
part_reveal
part_activation
part_deactivation
part_defense
part_recovery
connection_progress
machine_progress
machine_online
cycle_closure
signal_transmission
system_version_change
cycle_stabilization
```

Każda rodzina może posiadać własne limity długości i ton.

## 6. Ton sygnału

Dozwolone wartości:

```text
info
warning
critical
victory
mystery
system
clan
```

Przykłady:

* neutralna część — `info`,
* blokada — `warning`,
* odbicie — `victory`,
* pierwsze połączenie — `mystery`,
* transmisja — `critical`,
* stabilizacja — `system`.

## 7. Kontrakt outputu

Model zwraca:

```json
{
  "content_id": "ollama_ghost_0047_018",
  "task_id": "task_018",
  "medium": "blacknet",
  "source": "blacknet_editorial",
  "truth_class": "canonical",
  "audience_scope": "public",
  "signal_type": "ghost_part_activated",
  "title": "WĘZEŁ PHANTOM AKTYWNY",
  "body": "Siatka Widmo uruchomiła kolejny fragment swojej maszyny.",
  "tone": "warning",
  "fact_refs": [
    "fact-part-activated-9281"
  ],
  "cta_action": "show_ghostnetwork_part",
  "cta_payload": {
    "target_id": "ghost-node:8f3a12"
  },
  "thread_id": "ghost-machine:0047:phantom_veil",
  "expires_at": "2026-07-20T12:00:00Z"
}
```

Nie pozwalać na dodatkowe nieznane pola bez jawnej zgody schematu.

## 8. Walidator struktury

Dodać:

```text
GhostNetworkNarrativeOutputValidator
```

Sprawdza:

* poprawny JSON,
* wymagane pola,
* znany `signal_type`,
* dozwolony `tone`,
* poprawny audience,
* poprawną klasę prawdziwości,
* maksymalną długość,
* poprawne CTA,
* zgodny `thread_id`,
* brak zewnętrznego URL.

## 9. Walidator faktów

Każde `fact_ref` musi istnieć w tasku.

Output zostaje odrzucony, jeśli:

* zawiera nieznany fakt,
* nie wskazuje żadnego faktu,
* twierdzi coś sprzecznego z faktami,
* ujawnia ukryty identyfikator,
* zmienia `pending` na `delivered`,
* nazywa niezidentyfikowany komponent,
* przypisuje część niewłaściwemu klanowi.

## 10. Kontrola ukrytych danych

Walidator powinien sprawdzić gotowy tekst pod kątem zabronionych wartości znanych systemowi wewnętrznemu.

Dla publicznego tasku blokowanej części sprawdzić, czy output nie zawiera:

* `part_code`,
* nazwy,
* maszyny,
* profesji,
* supermocy,
* dokładnej kotwicy.

Model nie powinien ich znać, ale walidacja pozostaje dodatkową ochroną.

## 11. Walidacja CTA

CTA musi znajdować się w `allowed_actions`.

Payload musi odpowiadać przekazanemu identyfikatorowi.

Niedozwolone:

```text
teleport
set_aimed_target
purchase
activate_ability
capture_territory
send_hc
external_url
```

Model nie może zamienić obserwacyjnego sygnału w akcję mechaniczną.

## 12. Zapis do Ollama Outbox

Po poprawnej walidacji utworzyć wpis:

```text
output_id
task_id
source_event_id
cycle_id
signal_id
content_json
fact_refs_json
validation_status
validation_report
model_name
model_version
prompt_version
generation_time_ms
created_at
published_at
dedupe_key
```

Statusy:

```text
generated
validated
rejected
published
expired
```

## 13. Idempotencja outputu

Dla jednego tasku może istnieć maksymalnie jeden aktywny zwalidowany output.

Ponowne generowanie po błędzie może utworzyć kolejną próbę, ale tylko jeden wynik zostaje oznaczony:

```text
validated
```

Stabilny klucz:

```text
ollama-output:<task_id>:<prompt_version>
```

## 14. Retry

Retry przy:

* timeout,
* niedostępny model,
* niepoprawny JSON,
* chwilowy błąd walidatora technicznego.

Nie wykonywać automatycznego retry przy:

* ujawnieniu ukrytych danych,
* wymyśleniu faktów,
* niedozwolonym CTA,
* powtarzającym się naruszeniu schematu po ustalonym limicie.

Po limicie task trafia do:

```text
dead_letter
```

i może zostać obsłużony fallbackiem deterministycznym.

## 15. Timeout i limity

Konfiguracja:

```text
CHAOS_GHOSTNETWORK_OLLAMA_TIMEOUT_SECONDS
CHAOS_GHOSTNETWORK_OLLAMA_MAX_ATTEMPTS
CHAOS_GHOSTNETWORK_OLLAMA_MAX_TITLE_LENGTH
CHAOS_GHOSTNETWORK_OLLAMA_MAX_BODY_LENGTH
CHAOS_GHOSTNETWORK_OLLAMA_LEASE_SECONDS
```

Długi task nie może blokować całej kolejki BlackNetu.

## 16. Kolejność priorytetów

Worker powinien przetwarzać najpierw:

1. `signal_transmission`,
2. `cycle_closure`,
3. `machine_online`,
4. `part_recovery`,
5. zwykłe aktywacje i odkrycia,
6. agregaty postępu.

Stary sygnał niskiego priorytetu może wygasnąć, jeśli świat zdążył się znacząco zmienić.

## 17. Kontekst poprzednich publikacji

Worker może otrzymać maksymalnie kilka ostatnich wpisów wątku.

Cel:

* unikać powtarzania tego samego początku,
* utrzymać ciągłość konfliktu,
* nawiązać do wcześniejszej blokady.

Nie przekazywać całego BlackNetu ani pełnej historii cyklu.

## 18. Brak wpływu na gameplay

Awaria workera:

* nie blokuje aktywacji,
* nie blokuje transmisji,
* nie zatrzymuje rewardów,
* nie zmienia wersji,
* nie opóźnia delt gameplayowych.

Pipeline narracyjny pozostaje asynchroniczny.

## 19. Obserwowalność

Logować:

* task,
* model,
* prompt version,
* próbę,
* czas generowania,
* wynik parsowania,
* wynik walidacji,
* zabronione fakty,
* użyte CTA,
* dead letter.

Nie logować pełnych tajnych danych w zwykłym logu aplikacji.

## Testy Sprintu 137

Minimum:

* poprawny task odkrycia,
* poprawny sygnał aktywacji,
* ukryta część pozostaje anonimowa,
* nieznany `fact_ref` odrzucony,
* niedozwolone CTA odrzucone,
* zmiana outcome sygnału odrzucona,
* niepoprawny JSON trafia do retry,
* timeout odzyskuje task po lease,
* tylko jeden validated output,
* fallback po dead letter,
* priorytet transmisji,
* model nie ma dostępu do bazy,
* błąd modelu nie wpływa na mechanikę.

## DoD

Sprint jest zakończony, gdy Ollama może bezpiecznie przekształcić zatwierdzone fakty GhostNetwork w ustrukturyzowane propozycje sygnałów BlackNetu, a każdy output przechodzi walidację faktów, widoczności i CTA.

---

# Sprint 138 — BlackNet: publikacja narracyjnych sygnałów GhostNetwork

> **Post-audit 2026-08-21 — wiążące.** Publikacja rozszerza istniejące
> `blacknet_world_signals`, feed i dispatcher CTA; nie tworzy konkurencyjnego
> feedu. Audience payload pozostaje rozdzielony backendowo, a rotacja, TTL,
> dedupe i invalidation korzystają z obecnego kontraktu BlackNet. E2E musi
> przejść również z wyłączoną Ollamą i deterministycznym fallbackiem.

**Status planu:** `QUEUED — po Sprint 137`.

**Bramka heavy-profile:** publisher, feed i CTA nie wzbogacają sygnału przez
pełny profil. Audience oraz akcje są rozwiązywane z zapisanej projekcji albo
bounded canonical lookup; zwykła publikacja ma wszystkie heavy-profile counters
równe zero.

## Cel sprintu

Podłączyć zwalidowany Ollama Outbox do istniejącego publishera BlackNetu i publikować sygnały dotyczące GhostNetwork jako wpisy:

```text
ollama_enriched
```

Sygnały mają przeplatać się z deterministycznym BlackNetem, zachowywać ciągłość historii i zawsze posiadać mechaniczny fallback.

## 1. Publisher

Rozszerzyć istniejący publisher `blacknet_world_signals`; mały adapter dla
zwalidowanego outputu może mieć kontrakt:

```text
BlackNetOllamaOutboxPublisher
```

Minimalny kontrakt:

```text
publish_validated_output(output)
build_blacknet_signal(output)
resolve_signal_priority(output)
deduplicate_signal(output)
publish_fallback(task)
```

Publisher nie interpretuje ponownie faktów.

Korzysta ze zwalidowanego outputu.

## 2. Typ sygnału

Publikowany wpis:

```text
source: ollama_enriched
origin: ghostnetwork
signal_class: ollama_enriched
```

Dodatkowo:

```text
source_event_id
cycle_id
signal_id
thread_id
fact_refs
truth_class
```

Pozwala to odróżnić:

* sygnał deterministyczny,
* narrację Ollamy,
* wpis klanowy,
* komunikat systemowy.

## 3. Relacja z sygnałami deterministycznymi

Ważne zdarzenie może stworzyć dwa elementy:

### Natychmiastowy sygnał deterministyczny

Publikowany od razu.

### Późniejszy sygnał narracyjny

Rozwija znaczenie wydarzenia.

Przykład:

```text
SYSTEM:
GHOSTSIGNAL 0047 WYSŁANY.
```

Następnie:

```text
BLACKNET:
Sygnał opuścił naszą warstwę czasu, ale kanał po drugiej stronie nadal milczy.
```

Nie publikować dwóch niemal identycznych wiadomości.

## 4. Deduplikacja semantyczna

Poza `dedupe_key` sprawdzić:

* ten sam event,
* ten sam tytuł,
* bardzo podobne body,
* ten sam thread,
* krótki odstęp czasu,
* identyczne CTA.

Jeżeli narracja nie wnosi nic ponad deterministic fallback, może zostać odrzucona albo opóźniona.

## 5. Typy kompozycji BlackNet

Przygotować layouty dla:

```text
ghost_discovery
ghost_blockade
ghost_activation
ghost_defense
ghost_recovery
ghost_machine_progress
ghost_machine_online
ghost_connection
ghost_cycle_closure
ghost_signal_sent
ghost_version_change
ghost_stabilization
```

Nie wszystkie muszą mieć osobny CSS. Mogą używać wspólnych wariantów z różnymi ikonami i danymi.

## 6. Wizualne dane sygnału

Sygnał może zawierać:

* ikonę klanu,
* ikonę maszyny, jeśli widoczna,
* stan części,
* licznik `N/20`,
* licznik `N/5`,
* status konfliktu,
* właściciela,
* lokalizację,
* numer GhostSignalu,
* wersję systemu.

Nie dołączać danych, których nie było w zwalidowanym outboxie.

## 7. Priorytety publikacji

### Critical

* domknięcie sieci,
* transmisja,
* restart,
* odpowiedź z 2108.

Mogą przerwać zwykłą rotację BlackNetu.

### High

* maszyna online,
* odbicie strategicznej części,
* pierwsza część cyklu.

### Normal

* aktywacja,
* blokada,
* skuteczna obrona.

### Low

* częściowy postęp,
* pojedyncze połączenie,
* agregat mniejszych wydarzeń.

## 8. TTL

Przykładowe zasady:

* odkrycie — średni TTL,
* konflikt — krótki TTL,
* blokada — do zmiany stanu albo określonego limitu,
* aktywacja — dłuższy TTL,
* transmisja — pozostaje do restartu,
* wersja systemu — pozostaje przez okres stabilizacji.

Sygnał może zostać unieważniony przez późniejszy event.

## 9. Unieważnianie

Przykłady:

* sygnał o publicznej części wygasa po jej zablokowaniu,
* sygnał o blokadzie wygasa po ujawnieniu lub aktywacji,
* sygnał o trwającym konflikcie wygasa po stabilizacji,
* sygnał o maszynie online może zostać zastąpiony przez `machine_offline`.

Publisher powinien korzystać z:

```text
supersedes_signal_id
invalidated_by_event_id
```

## 10. Wątki

Sygnały tego samego komponentu lub konfliktu mogą tworzyć ciąg:

```text
ODKRYCIE
→ BLOKADA
→ ATAK
→ ODBICIE
→ AKTYWACJA
→ TRANSMISJA
```

BlackNet może pokazywać oznaczenie:

```text
KONTYNUACJA SYGNAŁU
```

Nie musi wyświetlać pełnej historii na głównej kompozycji.

## 11. CTA

Publisher zachowuje wyłącznie zwalidowane CTA.

Przykłady:

### Publiczna część

```text
POKAŻ NA MAPIE
```

### Ukryta blokada

```text
POKAŻ TERYTORIUM
```

### Aktywny węzeł

```text
OTWÓRZ GHOSTNETWORK SUITE
```

### Konflikt

```text
OTWÓRZ TERRITORY CONTROL
```

### Transmisja

```text
OTWÓRZ ARCHIWUM SYGNAŁU
```

## 12. Widoczność publikacji

Publisher publikuje osobne wpisy dla:

* publicznego feedu,
* feedu klanowego,
* ewentualnie feedu owner-only.

Nie publikuje jednego pełnego wpisu z frontendowym filtrem.

## 13. Fallback

Jeżeli:

* Ollama jest wyłączona,
* task wygasł,
* output został odrzucony,
* worker nie odpowiada,
* outbox jest uszkodzony,

publisher używa deterministycznego szablonu ze Sprintu 136.

W logu zapisuje:

```text
publication_mode: fallback
```

Gracz nadal otrzymuje informację o wydarzeniu.

## 14. Przeplatanie z istniejącymi sygnałami

Dodać politykę rotacji:

```text
BlackNetSignalMixPolicy
```

Uwzględnia:

* sygnały świata,
* sygnały GhostNetwork,
* sygnały klanowe,
* podcasty,
* wpisy deterministyczne,
* `ollama_enriched`.

Nie dopuścić, aby intensywny konflikt GhostNetwork całkowicie zalał pozostały BlackNet.

Możliwe limity:

* maksymalna liczba sygnałów GN w krótkim oknie,
* wyjątek dla priority critical,
* agregowanie powtarzalnych działań.

## 15. Odpowiedź z 2108

Pipeline musi być gotowy na przyszły fakt:

```text
ghost.signal_outcome_resolved
```

Ollama może przygotować wiadomość dopiero po zatwierdzeniu przez backend:

* outcome,
* odbiorcy,
* integralności,
* autentyczności,
* źródła odpowiedzi.

Nie może samodzielnie wybrać, czy sygnał został przechwycony albo dostarczony.

## 16. Regresja GhostNetwork

Pełny test:

1. Część zostaje odkryta.
2. Bridge tworzy task.
3. Ollama generuje output.
4. Walidator akceptuje.
5. Publisher tworzy `ollama_enriched`.
6. BlackNet wyświetla sygnał.
7. CTA otwiera poprawny cel.
8. Zmiana stanu unieważnia poprzedni wpis.

## 17. Testy braku Ollamy

Powtórzyć najważniejsze scenariusze przy:

```text
CHAOS_GHOSTNETWORK_OLLAMA_ENABLED=false
```

Wszystkie wydarzenia:

* nadal zmieniają gameplay,
* nadal publikują sygnały deterministyczne,
* nadal trafiają do archiwum,
* nie generują błędów interfejsu.

## 18. Obserwowalność

Raport pipeline’u:

```text
GN EVENTS
OUTBOX TASKS
OLLAMA CLAIMED
VALIDATED OUTPUTS
REJECTED OUTPUTS
BLACKNET PUBLISHED
FALLBACK PUBLISHED
EXPIRED
DEAD LETTER
```

Metryki:

* czas event → task,
* task → output,
* output → publikacja,
* liczba retry,
* udział fallbacków,
* liczba unieważnionych wpisów.

## 19. Dokumentacja

Dodać:

```text
doc/systems/ghostnetwork/GHOSTNETWORK_OLLAMA_BLACKNET.md
```

Dokument opisuje:

* źródłowe eventy,
* projekcję widoczności,
* inbox,
* worker,
* outbox,
* walidację,
* publisher,
* fallback,
* retry,
* feature flags,
* recovery.

## Testy Sprintu 138

Minimum:

* narracyjne odkrycie części,
* narracyjna blokada bez ujawnienia tożsamości,
* aktywacja pełna dla klanu,
* aktywacja zaszyfrowana publicznie,
* obrona,
* odbicie,
* maszyna online,
* transmisja,
* poprawne CTA,
* unieważnienie starego sygnału,
* brak duplikatu deterministycznego tekstu,
* rotacja nie zalewa BlackNetu,
* fallback przy wyłączonej Ollamie,
* dead letter nie zatrzymuje publishera,
* odpowiedź modelu nie wpływa na mechanikę,
* pełne E2E event → BlackNet.

## DoD

Sprint jest zakończony, gdy ważne działania GhostNetwork automatycznie stają się narracyjnymi sygnałami BlackNetu, przechodzą przez Ollama Inbox/Outbox, respektują widoczność części, posiadają mechaniczny fallback i pozostają całkowicie odseparowane od źródła prawdy gameplayu.

Po Sprintach 136–138 GhostNetwork nie tylko działa jako system strategiczny — zaczyna również sam opowiadać historię swoich konfliktów, aktywacji i transmisji przez żywy strumień BlackNetu.

## Sprint 135.4 — lokalny worker Ollamy i canonical Inbox

Status implementacji: `SPRINT 135.4 — COMPLETE`.

Sprint dostarczył niezależny, domyślnie wyłączony proces
`chaos-ollama-worker`, atomowy consumer Outboxa, heartbeat lease, trwałą historię
attemptów oraz bounded Inbox candidates. Crash po zapisie candidate nie powoduje
drugiego model call, a stale owner nie może zapisać ani domknąć wyniku.

Prompty nie są danymi taska ani stringami workera. Powstał wersjonowany registry
`ghostnetwork/llm/`, który składa warstwy `SYSTEM + DOMAIN + TASK PACKAGE` i
wiąże `source_scope + task_variant + target_medium` z prompt/schema/model policy.
Nieznane kombinacje, `unassigned`, brak pliku lub mismatch wersji pozostają
fail-closed przed claimem.

Ollama generuje tylko `title/body/tone/fact_refs/cta_ref`. Source, audience,
truth class, outcome i payload CTA pozostają backend-owned. Accepted candidate
nie jest jeszcze publikowany graczom; publikacja pozostaje zakresem 135.5.

Zachowano twardy zakaz heavy profile. Worker korzysta wyłącznie z bounded taska,
Outboxa i Inboxa; fixture profilu 35 MiB nie powoduje pełnego odczytu ani skanu.

Walidacja produkcyjna ujawniła zbyt ciężki prompt: 2513 tokenów wymagało około
259 sekund prompt evaluation. Bez zwiększania timeoutu TASK PACKAGE został
ograniczony do 2400 bajtów (~500–700 tokenów dla realnego digestu),
`num_predict` do 192, a attempt telemetry rozszerzona o `input_bytes` i
`fact_count`. Wszystkie canonical refs pozostają zachowane.

Finalna walidacja produkcyjna przeszła pełny tor
`Outbox → local Ollama → canonical Inbox → backend validator → completed`.
Ciężki BlackNet digest zawierał 20 facts, finalny package 2395 B, 978 tokenów
promptu i 160 tokenów odpowiedzi. Model pracował 196.97 s, czyli dłużej niż
lease 180 s; poprawny commit CAS potwierdził heartbeat renewal. Outbox zakończył
się z `attempt_count=1` i pustym `last_error_code`, a candidate
`narrative_candidate_2b8de8afec953faa` powstał dokładnie raz ze statusem
`accepted`. Publikacja do graczy pozostała zerowa, a worker po teście nadal
raportował `enabled=false`.

Werdykt:

```text
SPRINT 135.4 — COMPLETE
READY FOR SPRINT 135.4.1
```
