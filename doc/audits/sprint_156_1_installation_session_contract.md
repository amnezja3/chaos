# 156.1 — audyt instalacji i kontrakt trwałej sesji

Data: 15 X 2026. Status: AUDYT I KONTRAKT GOTOWE DO IMPLEMENTACJI.
Limity zatwierdzone przez autora w rozmowie: **30 dni nieaktywności / 90 dni
od logowania**, z zachowaniem zastępowania poprzedniego logowania przez nowe.
Nie wdrożono API, migracji, PWA ani zmiany cookie. Nie jest to PASS całego 156.

## Ustalenia z kodu

| Punkt | Dowód w repozytorium | Wniosek / zadanie |
| --- | --- | --- |
| Backend sesji | `config.py: FLASK_SESSION_CONFIG`, `run.py: Session(app)`; Flask-Session >=0.8,<1 | Obecnie filesystem w `data/flask_session`, trwałość domyślnie wyłączona; nie znamy nadpisań produkcyjnych |
| Uwierzytelnienie | `index`, `api_register_finalize`, `begin_authenticated_session` | Po sukcesie aktywacja ownership, rotacja SID, nowe generation/login identity; zachować kolejność fail-closed |
| Rozpoznanie konta | `SessionGenerationStore.assert_current` | Sprawdza lineage, generation, user, login identity i account revision; brak kontroli timestampów idle/absolute |
| Zastępowanie sesji | `SessionGenerationStore.activate` | Transakcyjne zwiększenie revision i zastąpienie wcześniejszych lineage tego konta; nie uruchamiać przy resume |
| Stare sesje bez lineage | `ensure_session_generation` | Legacy document bootstrap może wywołać activate; nowy status/launch nie może korzystać z tego trybu dla odwołanych ani niekompletnych danych |
| Start | `index` GET, `desktop`, `enforce_authenticated_session_generation` | `/` renderuje login; `/desktop` bez tokenu przechodzi kontrolę i redirect do URL z tokenem |
| Token w URL | `_session_generation_query_token`, `_request_session_generation` | SHA-256 generation, nie SID; akceptowany wraz z cookie dla dokumentów/logout. To wciąż materiał autoryzacyjny dokumentu, usuwamy z nowej ścieżki |
| Mapa / dev | `SESSION_GENERATION_DOCUMENT_ENDPOINTS`, `mapFrameUrl` i okolice w `terminal.js` | Iframe powiązany z generacją rodzica; nie można zastąpić tokenu w URL bez równoważnego wiązania |
| Klient | `static/js/session_generation.js` | Pinning generation, fetch bridge, kontrola odpowiedzi, BroadcastChannel, czyszczenie stanu i recovery; zachować również przy niewspółdzielonym storage |
| Logout | `logout`, `authenticatedLogoutUrl`, trzy wywołania w `terminal.js` | Obecnie GET z query tokenem; docelowo POST z bindingiem i CSRF; zmigrować Start i pozostałe ścieżki |
| Opóźniona odpowiedź | `_session_generation_mismatch` | `session.permanent=False`, `session.modified=False` mają zapobiegać nadpisaniu cookie A po loginie B; trwałość wymaga jawnej blokady zapisu cookie stale response |
| Recovery | `/session/recover`, `_discard_stale_document_session` | Czyszczą/rotują lokalną sesję, wracają na login; nie uruchamiać bezwarunkowo dla transport error ani starego dokumentu używającego nowego cookie |
| Hasło | zapis `profile.account_credentials` w `run.py` | W handlerze brak jawnej revocation po zmianie hasła. W 156.2 dodać dowiedzioną ścieżkę unieważnienia, także dla resetu/admin jeśli dostępne |
| Usunięcie konta | `revoke_all_by_username(... account_deleted)` | Unieważnia po usunięciu danych; zachować ochronę transakcji i kolejność |
| Restart gry | `session_restart_receipts`, `prepare_restart_boot`, `acknowledge_restart` | Oddzielny handshake epoch/restart; resume nie tworzy ponownie nagród ani receiptów i nie pomija tego handshake |
| PWA | brak rejestracji SW/manifestu instalacyjnego w sprawdzonych ścieżkach | Nowy manifest niezależny od manifestów locale/audio/Show |

Zakres wyszukiwania: konfiguracja, entry/register/desktop/map/dev/logout/recovery,
guard request/response, guard precommit, klient generation, credentials/account
deletion, manifesty i mechanizmy instalacji. Nie czytano produkcyjnych sekretów.

## Decyzja 1: storage i lifecycle

156.2 pozostaje przy istniejącym Flask-Session i trwałym katalogu sesji. Nie
dodajemy Redis ani nowego magazynu kont. Produkcja musi mieć stałą ścieżkę poza
czasowym wydaniem kodu, stały sekret i uprawnienia ograniczone do użytkownika usługi.
W ramach obecnego backendu usuwamy możliwość kasowania aktywnych sesji wyłącznie
z powodu progu liczby plików (threshold=0, po sprawdzeniu użytej wersji), dodajemy
kontrolowane sprzątanie wygasłych wpisów i monitoring miejsca. Migracja z
deprecated filesystem do CacheLib nie jest warunkiem 156 i wymagałaby osobnego
sprawdzenia zgodności istniejących SID. Wersje zależności potwierdzić przy deployu.

Trwały lifecycle rozszerza tabelę `session_generation_lineages` addytywnie:

- `authenticated_at`, `last_activity_at`, `idle_expires_at`, `absolute_expires_at`
  jako UTC według jednej reprezentacji i serwerowego zegara;
- `persistence_policy_version`, aby odróżnić nowe sesje od legacy;
- obecne hashe, status, login identity i revision pozostają źródłem własności;
- `expires_at = min(idle_expires_at, absolute_expires_at)`;
- sprawdzenie `now >= expires_at` odrzuca sesję w request oraz precommit,
  niezależnie od tego, czy cleanup zdążył zmienić status na expired.

Przy nowym loginie zapis: idle=now+30 dni, absolute=now+90 dni. Wznowienie nie
zmienia authenticated_at ani absolute_expires_at. Renewal aktualizuje wyłącznie
bieżące aktywne lineage z pasującym ownership (CAS / jedna transakcja).
Nie może zareaktywować replaced/logged_out/expired ani przydzielić nowej revision.

Aktywność: udana jawna interakcja w zalogowanym interfejsie, zaakceptowana mutacja
lub poprawny interaktywny start. Nowy endpoint activity może agregować zdarzenia
widocznego okna (trusted input) do jednego wywołania na 5 minut. Polling, sam
status GET, worker, heartbeat w tle oraz ukryta karta nie odnawiają czasu.
To miara nieaktywności UX, nie zabezpieczenie przed posiadaczem skradzionego cookie;
bezwzględne 90 dni i revocation nadal obowiązują.

Cookie: `Secure`, `HttpOnly`, `SameSite=Lax`, host-only, `Path=/`; nazwa zachowana
dla kompatybilności. `Expires`/`Max-Age` ograniczone do czasu pozostałego na backendzie.
`SESSION_REFRESH_EACH_REQUEST=False`; dedykowane odnawianie ustawia cookie po
powtórnej weryfikacji ownership. Sam globalny `PERMANENT_SESSION_LIFETIME` nie
realizuje dwóch limitów — adapter save_session musi kontrolować termin i tłumić
Set-Cookie starej odpowiedzi. Nie zmieniać globalnej konfiguracji per request.

Przy wygaśnięciu lub revocation odrzucamy żądania nawet ze starym SID istniejącym
w magazynie. Odpowiedź stale A nie może usuwać ani nadpisywać nowego cookie B.
Kontrolowana odpowiedź logout może usunąć cookie tylko dla tożsamości, którą
zweryfikowała. Przy jednoczesnych login/logout testować obie kolejności odpowiedzi.

Legacy: włączenie flagi nie przedłuża automatycznie wszystkich sesji o 90 dni.
Nowe logowania dostają nową politykę. Istniejące kompletne sesje zachowują dotychczasowy
termin; po następnym jawnym loginie przechodzą na nową politykę. Niekompletna
legacy sesja na nowym launch wymaga logowania zamiast przejęcia ownership.
Rollback flag nie przywraca wygasłych uprawnień; odczyt nowego lifecycle pozostaje.

## Decyzja 2: start bez credentialu w URL

`/launch` jest stałym start_url i neutralnym ekranem. Wejście nie renderuje loginu
ani prywatnego pulpitu. Należy wydzielić publiczny shell z obecnego desktop boot,
tak aby prywatne dane i kontekst generacji docierały dopiero po kontroli backendu.

| Planowana trasa | Ochrona i wynik |
| --- | --- |
| GET `/launch` | Publiczny shell, zero profilu/generation; brak skutków gameplayu |
| GET `/api/session/status` | Same-origin, cookie, no-store; HTTP 200 `authenticated`/`unauthenticated` z powodem. Jeżeli klient wysłał binding starej karty, mismatch → 409, bez danych nowego konta |
| POST `/api/session/bootstrap` | Origin/Fetch-Metadata + CSRF; sprawdzenie lifecycle i ownership; zwraca kontekst tylko dla poprawnej sesji, bez activate. Wznowienie wysyła poprzedni binding, świeży launch może go nie mieć |
| GET `/api/desktop-shell` | Cookie + generation header; chroniona zawartość do zamontowania przez publiczny shell, bez redirectu z tokenem. Powtórna kontrola przed odpowiedzią |
| POST `/api/session/activity` | Cookie, generation i CSRF, throttling 5 min; CAS odnowienia, bez zmiany ownership |
| POST `/logout` | Cookie, generation i CSRF; revoke właściwej sesji, brak automatycznego logowania innego konta |

Nazwy są kontraktem planowanej implementacji, nie istniejącym API.
Endpointy bootstrap nie dziedziczą wymagania brakującej generacji, ale mają
własną kontrolę lifecycle i same-origin. Status nie odnawia cookie ani nie
generuje nowego ownership. Token CSRF dla świeżego kontekstu dostarcza neutralny
shell związany z cookie; nie wykorzystujemy generation jako jedynego CSRF.

Tab binding w sessionStorage może zawierać jedynie niebędący credentialem znacznik
porównania generacji; nie SID ani bearer token. Serwer nie akceptuje go samodzielnie
do autoryzacji. Istniejący runtime generation pozostaje w pamięci po bootstrapie.
Przy reloadzie binding porównujemy przed pokazaniem konta; przy mismatch nie
zastępujemy go wartością nowego cookie. Puste storage po instalacji to nowy kontekst,
a nie dowód zalogowania. Nie używać BroadcastChannel jako jedynego zabezpieczenia.

W 156.3 wydzielić montowanie istniejącego desktop runtime od odbioru dokumentu.
Nie stosować redirectu `/desktop?_session_generation=...` w nowym przepływie.
Stare adresy mogą jedynie sprawdzić istniejący binding i przejść do neutralnego
startu; nie uzyskują uprawnienia z samego URL. Nadal chronić starych klientów
do końca okna kompatybilności, nie wyłączać guardów globalnie.

Mapa/dev: publiczny shell ramki, same-origin handshake z rodzicem i pobranie
chronionej zawartości z nagłówkiem generation. Sprawdzać origin i source okna
w postMessage, nigdy `*` dla kontekstu sesji. Zachować `_embedded` i epoch jako
niesekretne parametry. Powtórne ładowanie mapy A po loginie B nie może pokazać B.
Bez tej regresji 156.3 nie ma PASS, nawet jeśli sam `/launch` działa.

Po pozytywnym statusie i przed bootstrapem sesja może wygasnąć lub być zastąpiona:
bootstrap ponownie sprawdza wszystko. Błąd 5xx/timeout nie usuwa cookie i nie
pokazuje loginu. 409 bindingu zatrzymuje stary kontekst; 401/unauthenticated
pokazuje login. Recovery nie rotuje nowego SID na podstawie żądania starej karty.

## Decyzja 3: logout, hasło, błędy

- Trzy wywołania `authenticatedLogoutUrl` zastąpić wspólną akcją POST. GET
  logout nie mutuje: w okresie kompatybilności pokazuje neutralny ekran działania,
  którego autoryzowana akcja jest POST; nie dodawać nowego tokenu do URL.
- Zmiana/reset hasła unieważnia wszystkie stare sesje, także inicjującą; po
  powodzeniu pokazujemy komunikat PL/EN i prosimy o ponowne logowanie.
- Zapis hasła i revocation muszą mieć spójny commit. Precommit sprawdza aktywną
  sesję przed zmianą, a revocation jest końcową operacją transakcji; nie może
  przypadkowo wycofać poprawnej zmiany hasła ani pozostawić okna z nowym hasłem
  i nadal aktywną starą sesją. Osobny test awarii pomiędzy operacjami.
- Usunięcie konta zachowuje dotychczasową revocation; brak konta nie tworzy go na
  launch. Blokada konta, jeśli wspierana przez istniejący model, ma wspólny hook.
- Nie nazywać problemu storage/database „expired”. Wewnętrzny błąd → retry,
  log bez sekretów, brak sukcesu logoutu, gdy revocation nie została utrwalona.

## UI i instalacja — kontrakt dla 156.4

Panel przed loginem i w Ustawieniach: nagłówek „Zainstaluj CHAOS / Install CHAOS”,
cztery karty Windows, Linux, Android, iOS. Rekomendację pokazujemy na podstawie
platformy; aktywny natywny prompt wyłącznie po wykryciu capability i kliknięciu.
Inne karty otwierają instrukcję. Stany: dostępna instalacja, instrukcja ręczna,
anulowano, nieobsługiwane, uruchomiono jako aplikację. Brak prompta nie oznacza
braku możliwości instalacji z menu przeglądarki. Nie deklarujemy instalacji na
podstawie samego kliknięcia. Zgody używają istniejących warunków konta; bez nowej
zgody marketingowej/push i bez uzależnienia wejścia do gry od instalacji.

Ekran startowy: logo, dyskretne „Uruchamianie CHAOS / Starting CHAOS”; podczas
kontroli sesji brak pól login/hasło. Offline: „Brak połączenia / No connection”
i „Spróbuj ponownie / Retry”. Mismatch: lokalizowany komunikat zastąpienia sesji,
bez danych nowego konta. Po potwierdzeniu sesji standardowy preloader gry.

Manifest: `id=/chaos`, `start_url=/launch`, `scope=/`, `display=standalone`,
publiczne ikony 192/512/maskable/apple-touch-icon. Nie tworzyć osobnych wersji
aplikacji na język/konto. Linux .desktop: `Type=Link`, stały publiczny URL i ikona,
bez Exec z inputa; to jawnie skrót, nie obietnica okna standalone.
SW scope `/`: wyłącznie allowlista publicznych plików po hashu/wersji, bez API,
HTML kont i fallbacku prywatnego desktopu. Nie przejmować POST ani offline queue.

## Flagi i kolejność wdrożenia

Planowane flagi, domyślnie OFF:

1. `CHAOS_PERSISTENT_SESSION_ENABLED` — wydawanie nowych trwałych sesji.
2. `CHAOS_LAUNCH_CONTROLLER_ENABLED` — nowy start; wymaga zgodnego bootstrapu
   i obsługi lifecycle. Publiczny `/launch` pozostaje dostępny po rollbacku.
3. `CHAOS_INSTALL_UI_ENABLED` — panel i manifest po odbiorze dwóch poprzednich.

Konfiguracja TTL: `CHAOS_SESSION_IDLE_DAYS=30`, `CHAOS_SESSION_ABSOLUTE_DAYS=90`;
walidacja wartości >0 i idle<=absolute, błąd konfiguracji nie daje sesji bez limitu.
Testy mają wstrzykiwany zegar; nie skracamy czasu produkcyjnego na potrzeby testu.
Flagi zmieniają wydawanie/UX, nie wyłączają revocation i kontroli już wydanych sesji.
Restart istniejącej usługi, bez nowej instancji gry, Redis i dodatkowego portu.

## Dowody i bramki

Wykonano 15 X 2026:

- `python tools/run_isolated_tests.py test_session_generation_store`: **5/5 PASS**, 0,597 s.
  Pokrycie: hash-only persistence, zastąpienie loginu, stale revoke, revoke-all,
  równoczesne logowania i jedna zwycięska revision.
- `node tests/js/test_session_generation_isolation.js`: **PASS**.
- Audyt statyczny wymienionych funkcji; bez uruchamiania aplikacji na produkcji.
- Nie wykonano instalacji urządzeń ani testu UI: 156.1 nie zmienia interfejsu.
  Backend TTL, cookies i nowy bootstrap mają testy dopiero wraz z implementacją.

Wymagane przed PASS 156.2: boundary TTL, brak renewal po revoke, concurrent
login/renew/logout i opóźnione Set-Cookie, restart procesu i storage, hasło+revocation
w jednej transakcji, brak precommit po wygaśnięciu.
Wymagane przed PASS 156.3: status→bootstrap race, stara karta/iframe A po loginie B,
brak login DOM dla ważnej sesji, brak auth w URL, brak profilu w shell/cache,
epoch/receipt dokładnie raz, offline bez kasowania sesji.

Nie ma już otwartej decyzji produktowej TTL. Pozostaje walidacja techniczna
adaptera cookie/storage w 156.2 i neutralnego dokumentu/ramek w 156.3 — to część
implementacji, nie potwierdzone obecnie możliwości. Nie osłabiać guardów, gdy test
ujawni sprzeczność; poprawić kontrakt i test reprodukcji przed wdrożeniem.

## Źródła

- [Flask-Session — Configuration](https://flask-session.readthedocs.io/en/latest/config.html):
  backend expiry i ograniczenia niepermanentnych sesji; filesystem deprecated.
- [Flask-Session — API](https://flask-session.readthedocs.io/en/latest/api.html):
  interfejs filesystem i domyślny próg plików wymagający audytu produkcyjnego.
- [Flask — Configuration](https://flask.palletsprojects.com/en/stable/config/):
  odnawianie cookie, permanent lifetime i SameSite. Sprawdzone 15 X 2026.
- Weryfikacja platform/PWA oraz źródła WebKit/MDN: dokument nadrzędny Sprintu 156.
