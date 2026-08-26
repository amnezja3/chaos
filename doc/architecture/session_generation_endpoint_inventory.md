# Session generation endpoint inventory

Sprint 130.10. Stan: implementacja lokalna, bez deployu.

## Reguła klasyfikacji

Runtime stosuje kontrakt deny-by-default. Gdy sesja zawiera `user`, każda
zarejestrowana trasa Flask jest user-scoped i wymaga bieżącej generation, chyba
że znajduje się na jednej z dwóch jawnych list wyjątków poniżej. Oznacza to,
że nowy endpoint API lub gameplay mutation automatycznie wchodzi pod guard i
nie wymaga pamiętania o dopisaniu go do kolejnej allowlisty.

Chronione są więc wszystkie aktualne grupy:

- profile, desktop settings, wallet, apps i Googleplex;
- state changes, system messages, launch queue i operations;
- map snapshots, actors, territories, targets, scan/hack/travel oraz konflikty;
- GhostNetwork snapshot/archive/delta consumers;
- mail, contacts, chats, radio manifests i resources;
- Ghost Exchange, GhostLab, vulnerability, player-hack i control apps;
- dev/admin JSON APIs oraz account deletion.

## Jawne wyjątki publiczne

| Endpoint Flask | Trasa | Powód |
| --- | --- | --- |
| `static` | `/static/<path>` | asset, brak danych sesyjnych |
| `index` | `GET/POST /` | anonimowy login; uwierzytelniony `POST` jest chroniony i wymaga najpierw logoutu, a sukces nowego loginu rotuje SID i generation |
| `register_page` | `GET /register` | publiczny formularz |
| `register_check_username` | `POST /api/register-check` | publiczna walidacja rejestracji |
| `api_register_finalize` | `POST /api/register-finalize` | anonimowe tworzenie konta; uwierzytelniony `POST` wymaga najpierw logoutu, a sukces rotuje SID i generation |
| `logout` | `GET /logout` | anonimowo publiczny; zalogowana sesja wymaga query generation i rotuje SID |

## Jawne dokumenty uwierzytelnione

| Endpoint Flask | Trasa | Kontrakt |
| --- | --- | --- |
| `desktop` | `GET /desktop` | bootstrapuje generation dla sesji sprzed deployu i osadza config bridge'a |
| `map_view` | `GET /map` | top-level może bootstrapować; iframe zawsze podaje query generation |
| `dev_dashboard` | `GET /admin`, `GET /dev` | nawigacja dokumentu; dane JSON pozostają chronione |

`/map` staje się requestem chronionym, gdy ma `_embedded=1`, nagłówek
`Sec-Fetch-Dest: iframe` albo parametr `_session_generation`. Stary iframe A po
przełączeniu cookie na B dostaje `409 session_generation_mismatch` przed
renderem mapy.

## Transport

| Kierunek | Transport |
| --- | --- |
| desktop/map document → JS | JSON config `session-generation-config` |
| `fetch` → backend | `X-Chaos-Session-Generation` |
| map iframe → backend | `_session_generation` (jednokierunkowy SHA-256 token) + `_embedded=1` w query |
| logout navigation → backend | `_session_generation` (jednokierunkowy SHA-256 token) w query |
| desktop `sendBeacon` → backend | `_session_generation` w JSON body |
| odpowiedź → JS | `X-Chaos-Session-Generation` i `X-Chaos-Session-User` |
| mismatch | HTTP 409 + `X-Chaos-Session-Error: mismatch` |

Body fallback jest porównywany z surową generation bieżącej sesji. Nawigacje
iframe/logout wysyłają jej pełny jednokierunkowy SHA-256 token, aby surowa
generation nie trafiła do access logu URL; backend akceptuje token wyłącznie
dla tych dwóch tras. Mapa ustawia ponadto `Referrer-Policy: origin`: zewnętrzny
provider kafelków otrzymuje wymagany origin aplikacji, ale nigdy ścieżkę ani
query zawierające token generation.
Telemetria zapisuje tylko SHA-256 prefix generation, username i request ID; nie
zapisuje surowych wartości.

## Zachowanie klienta

`static/js/session_generation.js` instaluje się przed pozostałym runtime:

1. wiąże każdy same-origin `fetch` z generation;
2. sprawdza generation oraz username ponownie przed oddaniem response callerowi;
3. odrzuca 401/409 oraz odpowiedź poprzedniej generation;
4. przez `BroadcastChannel` unieważnia stare karty po A → B → A;
5. abortuje kontrolowane requesty, czyści `sessionStorage`, usuwa iframe mapy i
   wykonuje pełną nawigację do login gate;
6. dwa osobne browser sessions tego samego konta mają niezależne generation i
   nie unieważniają się wzajemnie.

Sesja utworzona canonical loginem/rejestracją zawsze ma generation. W runtime
API bez generation zwraca `generation_bootstrap_required`; jedyny compatibility
exception dotyczy `app.testing`, ponieważ starsze unit fixtures wstrzykują
bezpośrednio samo `session["user"]` i nie wykonują login/document boot.
