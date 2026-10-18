# Sprint 156 — Universal Installation System

**Rozszerzenie 15 X 2026:** [156.7 — lift ekranu wejścia i instalacji](sprint_156_7_entry_gate.md)
zaimplementowane i sprawdzone lokalnie; oczekuje wdrożenia. Poniższe zamknięcie
dotyczy zakresu 156.1–156.6, nie nowego wyglądu 156.7.

Status: IMPLEMENTACJA I WDROŻENIE ZAMKNIĘTE, 15 X 2026; odbiór platform częściowy.
Windows i Android potwierdzone w zakresie [macierzy dowodów](../audits/sprint_156_acceptance.md).
Linux oraz iOS pozostają PENDING decyzją autora. Redmi A5: problem zgodności,
działa dostęp przez widżet zakładek. Nie deklarujemy pełnego PASS wszystkich platform.
[156.6 — utrwalenie konfiguracji i rollback](../runbooks/universal_installation_156_6.md).
Źródło: specyfikacja autora „CHAOS — Universal Installation System”
oraz doprecyzowanie dotyczące izolacji PWA i startu bez ekranu logowania.

[Audyt i kontrakt 156.1](../audits/sprint_156_1_installation_session_contract.md)
ustala szczegóły storage, bootstrapu, guardów i flag. Autor zatwierdził limity
30 dni nieaktywności / 90 dni maksymalnie. Pozostałe odbiory: Linux i iOS w 156.5.
[Runbook i dowody 156.3](../runbooks/launch_controller_156_3.md).

## Cel

**Zainstaluj → zaloguj się → graj → zamknij → wróć → graj dalej.**

Jeden frontend i backend, cztery ścieżki instalacji: Windows, Linux, Android,
iOS. Ważna sesja rozpoznana przez backend otwiera właściwy interfejs CHAOS
bez renderowania formularza logowania po drodze. Zamknięcie aplikacji nie
oznacza wylogowania. Nie zmieniamy kont, postaci, świata ani zasad rozgrywki.

156 nie nadaje automatycznie PASS 155. Odbiory narracji, historii oraz naturalnego
cyklu Show/Sender pozostają osobne. Sprinty 149–152 nadal zamrożone.

## Decyzje obowiązujące

1. Autorytatywny jest backend oraz aktualny właściciel logowania. Lokalna flaga
   „logged in”, tryb standalone ani obecność ikony nie potwierdzają sesji.
2. PWA i przeglądarka mogą mieć osobne magazyny danych. Nie zakładamy kopiowania
   cookies, localStorage ani sessionStorage podczas instalacji. Skopiowane cookie
   również wymaga sprawdzenia po stronie serwera.
3. Bez credentialu w danym środowisku pierwsze logowanie jest konieczne.
   Sam serwerowy zapis sesji nie potrafi rozpoznać nowej, pustej instalacji.
   Nie wprowadzamy fingerprintingu, przekazywania sekretów w URL ani automatycznego
   połączenia instalacji na podstawie nazwy użytkownika.
4. Zachowujemy **jedno aktywne logowanie konta**: skuteczne nowe logowanie B
   zastępuje A, również między przeglądarką i PWA. Instalacje mogą istnieć na wielu
   urządzeniach, ale nie dostają prawa do równoczesnych niezależnych sesji konta.
5. Samo otwarcie aplikacji, kontrola sesji i jej odnowienie nie są nowym logowaniem.
   Nie zmieniają account ownership ani nie przywracają zastąpionej sesji.
6. Logout unieważnia bieżące uprawnienie na backendzie, nie tylko usuwa cookie.
   Stare okno A nie może wylogować nowszego B. Kopie tego samego credentialu
   dzielą los tej sesji — nie obiecujemy ich niezależnego wylogowania.
7. Formularz pojawia się wyłącznie po potwierdzonym braku/wygaśnięciu/unieważnieniu
   sesji. Błąd sieci lub 5xx oznacza ekran ponowienia, nie „błędne logowanie”.
8. Cały systemowy UX, instrukcje i komunikaty mają PL/EN. Nie tłumaczymy UGC.

## Stan obecny i punkty integracji

Audyt lokalny 15 X 2026; konfiguracja produkcyjna wymaga osobnego sprawdzenia
bez wypisywania sekretów.

| Obszar | Obecnie | Zmiana w 156 |
| --- | --- | --- |
| `config.py`, `FLASK_SESSION_CONFIG` | Flask-Session, domyślnie filesystem `data/flask_session`, `SESSION_PERMANENT=False` | Kontrolowana trwałość, TTL, cookie i stabilny storage |
| `run.py`: `/`, `index()` | GET renderuje `login.html`; POST uwierzytelnia | Oddzielić start/rozpoznanie sesji od widoku formularza |
| `begin_authenticated_session`, `invalidate_authenticated_session`, `_rotate_server_session_id` | Generacja i rotacja sesji | Zachować; audyt wszystkich miejsc ustawiających `session.permanent`, nie tylko config |
| `session_generation_store.py` | Trwałe lineage, account ownership, replaced/logged_out/expired, precommit guard | Dołączyć trwałość bez ominięcia obecnej ochrony przed zapisem starego konta |
| `static/js/session_generation.js`, `/session/recover`, `/desktop` | Izolacja generacji i recovery; query token dokumentów | Zaprojektować bootstrap ze zwykłego start URL, bez sekretów w adresie i bez pętli recovery |
| `tests/test_session_generation_*.py`, `tests/js/test_session_generation_isolation.js` | Regresja sesji i zapisów | Rozszerzyć o PWA, restart, wznowienie i wygaśnięcie |
| PWA | W przeglądanych frontendowych plikach brak rejestracji service workera i obsługi `beforeinstallprompt`; istniejące manifesty dotyczą innych systemów | Manifest instalacyjny, ikony, publiczny shell, kontrolowana aktualizacja |

`_session_generation` w obecnym URL jest osobnym tokenem ochrony dokumentu.
W 156 trzeba sklasyfikować jego uprawnienia i bezpiecznie usunąć zależność nowej
ścieżki startowej od query tokenu. Nie wolno po prostu wyłączyć guardów dokumentów,
iframe ani API. Stary deep link nie może ustanowić nowego logowania.

## Architektura docelowa

| Moduł | Odpowiedzialność |
| --- | --- |
| PlatformDetector | Możliwości przeglądarki, platforma i tryb standalone; detekcja platformy jest wskazówką UX, nie zabezpieczeniem |
| InstallManager | Natywny prompt dopiero po kliknięciu, instrukcje, opcjonalny bezpieczny skrót Linux |
| ConsentManager | Jawne rozpoczęcie instalacji i istniejące wymagane warunki, bez nowych zgód marketingowych czy wymuszania powiadomień |
| SessionManager | Cookie HttpOnly, serwerowy lifecycle, TTL, odnowienie i unieważnianie, istniejąca autoryzacja |
| LaunchController | Neutralny ekran startowy, kontrola sesji, przejście do gry/logowania/ponowienia |

Proponowane kontrakty do ustalenia w 156.1, jeszcze nieistniejące API:

- Stałe `id` i `scope` manifestu; `start_url=/launch`, bez loginu, cookie,
  tokenu sesji i generacji w URL.
- Publiczny `/launch` renderuje neutralny, lekki ekran CHAOS, bez danych konta
  i formularza logowania. Publiczny shell nie daje dostępu do profilu.
- `/api/session/status` (GET, `no-store`, same-origin): ograniczony kontrakt
  `authenticated / unauthenticated`, kod powodu oraz właściwy lokalny ekran
  wejścia, bez sekretów i pełnego profilu. Backend sprawdza termin ważności,
  lineage, login identity, ownership i revocation. Nie tworzy sesji ani profilu.
- Przy ważnej sesji kontrolowany bootstrap generacji do `/desktop`; dane konta
  dopiero po autoryzacji. Brak tokenów w URL, analytics, logach i refererze.
- Wznowienie istniejącego, uśpionego okna ponownie sprawdza aktualność przed
  mutacjami; precommit pozostaje ostatnią granicą ochrony.
- Logout jako operacja chroniona przed CSRF i stale-generation; migrować
  istniejące wywołania `/logout`, zachowując funkcję przycisku w Start.

```text
START /launch → CHECK SESSION → authenticated → CHAOS
                             → unauthenticated → LOGIN
                             → offline / timeout / 5xx → RETRY
LOGIN → poprawne dane → nowa tożsamość logowania → CHAOS
```

## Trwałość i zabezpieczenia sesji

- Wykorzystać istniejący serwerowy magazyn i guardy; nie budować drugiego
  systemu kont ani niezależnego remember-me obchodzącego account ownership.
- Cookie `HttpOnly`, `Secure` na HTTPS, `Path=/`, świadomie dobrane `SameSite`
  (proponowane Lax dla obecnego same-origin), host-only bez zbędnej domeny.
  TTL cookie nie przekracza pozostałej ważności na backendzie.
- **Zatwierdzone przez autora 15 X 2026:** 30 dni nieaktywności, 90 dni limitu
  bezwzględnego. Wartości konfigurowalne. Nie są jeszcze wdrożoną polityką.
  Odnawianie z ograniczoną częstotliwością podczas uwierzytelnionej aktywności;
  sam polling w tle nie przedłuża sesji bez końca. Limit bezwzględny pozostaje.
- Przeglądarka może usunąć cookies/dane; brak pamięci, tryb prywatny, odinstalowanie
  i czyszczenie danych nie dają gwarancji zachowania logowania.
- Rotować ID po uwierzytelnieniu; nie zapisywać hasła ani bearer tokenów w JS,
  localStorage, IndexedDB, manifestach czy plikach `.desktop`.
- Zmiana/reset hasła, blokada konta i zdarzenie bezpieczeństwa unieważniają
  odpowiednie sesje. Kontrola przy statusie, API i zatwierdzeniu zapisu.
- Nieudane logowanie nie unieważnia poprawnej sesji innego urządzenia.
- Stabilny sekret i trwały storage muszą przetrwać restart usług/urządzenia
  oraz deploy; sprawdzić cleanup Flask-Session i spójność TTL z lineage.
  Nie wystarczy ustawić trwałego cookie przy nietrwałym magazynie backendu.
- Zmiany session storage i danych ownership wymagają spójnego backupu; przy
  rollbacku nie przywracać unieważnionych uprawnień ze starego snapshotu.

## Instalacja i shell

Panel INSTALL CHAOS jest dostępny przed zalogowaniem oraz z Ustawień. Pokazuje
cztery opcje jednocześnie; rekomendowana platforma jest wyróżniona, a inne mają
instrukcje. Nazwa platformy nie przesądza dostępności natywnego prompta.

| Platforma | Obsługa |
| --- | --- |
| Windows | Instalacja PWA w obsługującej ją przeglądarce; przy braku API instrukcja menu przeglądarki |
| Linux | PWA, ewentualnie pobierany na żądanie `.desktop` z publicznym URL; skrót nie jest równoważny instalacji PWA |
| Android | Prompt PWA lub instrukcja dodania do ekranu głównego; informacja o rzeczywiście dostępnym trybie |
| iOS/iPadOS | Instrukcja systemowego „Dodaj do ekranu początkowego”; brak udawania programowej instalacji lub współdzielonej sesji |

- Obsłużyć brak/odroczenie eventu, akceptację, anulowanie, nieobsługiwaną
  przeglądarkę, uruchomienie standalone i powrót do panelu. Nie pokazywać sukcesu
  instalacji na podstawie samego kliknięcia lub pobrania skrótu.
- Manifest: stabilne ID, nazwy, kolory, scope, publiczny start, `display=standalone`,
  ikony 192/512, maskable i apple-touch-icon, bez przyciętego logo.
- Linux: stały publiczny origin, poprawne kodowanie Desktop Entry, bez danych
  użytkownika i dowolnych komend z inputa; brak automatycznego wykonywania/chmod.
- Service worker: cache wyłącznie wersjonowanych publicznych assetów i neutralnego
  ekranu offline. Nigdy prywatnych HTML, statusu sesji, API, wiadomości ani odpowiedzi
  z cookie. Brak kolejki mutacji offline i „odtwarzania” zakupów/nagród.
- Aktualizacja SW nie przeładowuje gry w środku operacji; kontrolowany komunikat
  aktualizacji i zgodność starych klientów. Worker cleanup tylko własnego cache CHAOS.
- Offline: neutralna informacja PL/EN i ponowienie; nie ujawnia poprzedniego konta
  na współdzielonym urządzeniu. Brak internetu nie kasuje ważnego credentialu.

## Etapy realizacji

156.1–156.4: WDROŻONE. 156.5: ODBIÓR CZĘŚCIOWY. 156.6: procedura wykonana,
runbook gotowy; zapis końcowych flag w PM2 oczekuje potwierdzenia operatora.
Kolejność 156.1 → 156.2 → 156.3 → 156.4 → 156.5 → 156.6.

156.2 — stan lokalny: trwałe daty uwierzytelnienia, aktywności, idle/absolute expiry
w lineage (schema v3, polityka v1); sprawdzanie expiry w istniejących guardach
request/precommit; CAS renewal z odstępem 5 minut, bez przesuwania granicy 90 dni.
Adapter Flask-Session ogranicza cookie i storage do terminu backendu oraz tłumi
zapis wykrytej starej odpowiedzi. Recovery przekazuje jedynie publiczny klucz
komunikatu, dzięki czemu nie musi ustawiać starego cookie po nowym loginie.
Legacy nie dostaje automatycznie nowego TTL; wyłączenie flagi nie usuwa expiry
już wydanych sesji. `CHAOS_PERSISTENT_SESSION_ENABLED` domyślnie false.

Domknięcie 156.2: trusted input widocznego dokumentu wywołuje chronione POST activity,
osobny CSRF i kontrola Origin zabezpieczają renewal/logout/credentials. Wszystkie
trzy akcje wylogowania terminala używają POST; GET wyświetla potwierdzenie PL/EN.
Zapis hasła i revocation są jednym commitem po kontroli precommit. Błąd wycofuje oba.
Recovery starej karty nie kasuje poprawnego nowszego loginu; terminal pokazuje
lokalizowany komunikat po zmianie hasła. Logout nie wysyła usunięcia cookie.
Migracja ma dry-run, kontrolę integralności i zachowania oryginalnych danych;
cleanup działa partiami na wygasłych plikach, apply wymaga zatrzymanych writerów.

Backend i testy Node PASS; Chrome/Playwright desktop PL i mobile EN PASS
(input → renewal w DB, brak CSRF → 403, logout → login, brak błędów JS).
[Runbook i dowody 156.2](../runbooks/persistent_session_156_2.md).
156.3 domknięte lokalnie: neutralny `/launch`, read-only status, CSRF/bootstrap,
chroniony dokument pulpitu, binding karty i handshake mapy/dev bez tokenów w URL.
Zachowany restart Show i precommit; stary kontekst nie adoptuje nowszego cookie.
98 testów backendu i cztery zestawy Node PASS; Chrome/Playwright desktop PL,
mobile EN, mapa, stale reload, jawne logowanie i retry bez utraty cookie PASS.
PWA pozostaje w 156.4–156.5; nie deklarujemy odbioru iOS ani pełnego PASS 156.
Flagi domyślnie OFF, bez zmian na produkcji.

| Etap | Zakres i rezultat | Bramka ukończenia |
| --- | --- | --- |
| **156.1 — audyt i kontrakt** | Pełna mapa login/logout/recovery/iframe, cookie/storage/TTL, ustalenie flag i terminów, źródła instalacji, projekt UI PL/EN, polityka jednego logowania | Zatwierdzony kontrakt TTL i bootstrapu, brak otwartych sprzeczności z guardami |
| **156.2 — trwała sesja** | Cookie, backend expiry/renewal/revocation, rotacja, trwałość storage, nowe logowanie zastępujące stare, hasło i CSRF | Testy restartu, wygaśnięcia, odwołania i precommit PASS; brak obejścia ownership |
| **156.3 — LaunchController** | `/launch`, status sesji, cichy start, offline/retry, recovery i wznowienie aplikacji | Ważna sesja nigdy nie renderuje loginu; brak pętli 302/409 i profilu sprzed autoryzacji |
| **156.4 — instalacja wieloplatformowa** | Manifest, ikony, SW, cztery opcje, detekcja możliwości, instrukcje, skrót Linux, PL/EN | Sprawdzalny natywny prompt tam, gdzie dostępny; poprawne fallbacki i jawne stany |
| **156.5 — odbiór i regresja** | Automatyczne scenariusze oraz rzeczywiste instalacje, izolacja iOS, restart urządzeń, smoke gameplayu | Macierz dowodów z wersjami OS/przeglądarki i stanem PASS/FAIL/PENDING |
| **156.6 — wdrożenie i dokumentacja** | Flagi, dry-run/migracja jeśli potrzebna, backup, runbook i rollback, obserwacja po wdrożeniu | Kontrolowany rollout na obecnej produkcji; pełny PASS dopiero po odbiorze |

156.1 ma wskazać konkretną implementację storage i migrację; nie wpisujemy
nieistniejących komend jako gotowych do wykonania. 156.6 dostarcza instrukcje
„komenda → spodziewany wynik → warunek STOP → rollback”.

## Macierz odbioru

Aktualny stan i rozróżnienie testów lokalnych/produkcyjnych:
[macierz odbioru 156](../audits/sprint_156_acceptance.md). Poniższa lista jest
pełnym kontraktem testów; nie należy traktować jej jako potwierdzenia wszystkich
scenariuszy na każdym urządzeniu.

Każdy rekord dowodowy: data, OS/przeglądarka i wersja, browser/standalone,
scenariusz, wynik oraz zanonimizowane logi. Tokenów/cookies nie kopiować do raportów.

- [ ] Windows, Linux, Android i iOS/iPadOS: panel, rekomendacja i instrukcja PL/EN.
- [ ] Instalacja, anulowanie i brak natywnego wsparcia; ponowne otwarcie z ikony.
- [ ] Pierwsza instalacja z pustym storage wymaga jednego logowania.
- [ ] iOS/PWA: osobny storage bez cookies oraz możliwy scenariusz skopiowanych
  cookies; przy kopii serwer sprawdza aktualność i nie tworzy nowego ownership.
- [ ] Ważna sesja po zamknięciu okna, przeglądarki i restarcie urządzenia:
  przejście do CHAOS, zero klatek formularza logowania i brak żądania widoku loginu.
- [ ] Restart backendu/deploy: sesja zachowana, jeśli nadal ważna; handshake
  generacji i epoch zgodny z istniejącymi guardami.
- [ ] Nowe logowanie B unieważnia A; stare API, iframe i zapis rozpoczęty przez A
  nie zmieniają konta. Odnowienie A nie odbiera własności B.
- [ ] Logout aktualnej sesji, powtórzenie logoutu i logout starego A po loginie B.
- [ ] Upływ idle/absolute TTL, zmiana/reset hasła, blokada konta, ręczna revocation.
- [ ] Uśpienie aplikacji podczas wygaśnięcia lub nowego logowania na innym urządzeniu.
- [ ] Offline, timeout i 5xx: ekran ponowienia, brak pętli i brak fałszywego logoutu.
- [ ] Czyszczenie danych/tryb prywatny: zrozumiałe przejście do ponownego logowania.
- [ ] Dwie karty, szybkie zamknięcie/start, stale query token, stare assety/SW.
- [ ] Brak prywatnych danych w cache/offline po zmianie konta; brak sekretów w URL.
- [ ] Aktualizacja/rollback SW nie odtwarza mutacji i nie restartuje aktywnej operacji.
- [ ] Smoke: rejestracja, FM, mapa, terminal, zakup/instalacja, Cyberner, News/BN,
  Show/Sender bez sztucznego przyspieszania cyklu; tożsamości, wiadomości i nagrody bez zmian.

Backend: izolowane bazy i kontrolowany zegar do TTL. Frontend: Playwright na
lokalnym fixture, DOM/nawigacja/console, PL/EN, mobile/desktop. Emulacja viewportu
nie jest dowodem instalacji PWA ani restartu iOS — te wymagają rzeczywistego sprzętu.
Nie blokować rozgrywki na czas testów.

## Wdrożenie i wycofanie

Istniejąca instancja produkcyjna; bez kopii gry i dodatkowego portu produkcyjnego.
W 156.6 przygotować niezależne flagi instalacji, nowego startu i trwałości,
ich kolejność włączenia oraz zachowanie już wydanych sesji po wyłączeniu flag.

Przed zapisem: backup spójnej bazy, konfiguracji i magazynu sesji z ograniczonym
dostępem. Migracja tylko addytywna, idempotentna, dry-run i kontrola integralności,
jeżeli audyt wykaże konieczność schematu. Publiczny `/launch` musi pozostać sprawny
także po wycofaniu UI, ponieważ zainstalowane aplikacje będą nadal go używać.
Wycofanie SW musi obsłużyć już zarejestrowane wersje — usunięcie pliku nie wystarczy.
Nie przywracać starej bazy po nowych transakcjach i nie wskrzeszać sesji revokowanych.
W razie niezgodnego storage dopuszczalne kontrolowane ponowne logowanie zamiast
przywrócenia nieważnego uprawnienia. Bez migracji postaci/nagród/wiadomości.

Po rollout obserwować anonimowe agregaty: wynik launch, przyczyny 401/409,
czas potwierdzenia sesji, błędy instalacji i wersje SW. Bez nowych danych śledzących.

## Poza zakresem

Natywne instalatory EXE/APK/IPA, sklepy aplikacji, Electron, dodatkowe uprawnienia
systemowe, rozgrywka offline, push, nowe konta/SSO, wielosesyjność konta oraz panel
zdalnego zarządzania urządzeniami. MacOS nie jest piątą pozycją panelu tego sprintu.

## Źródła techniczne

Sprawdzone 15 X 2026; wersje wspieranych przeglądarek potwierdzić ponownie w 156.5.

- [WebKit — Safari 17.2](https://webkit.org/blog/14787/webkit-features-in-safari-17-2/):
  opis kopiowania cookies podczas dodawania web app; nie stanowi gwarancji
  trwałego współdzielenia storage ani ważności sesji CHAOS.
- [MDN — Making PWAs installable](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable):
  instalowalność zależy od platformy/przeglądarki, manifest i sposób prezentacji.
- [MDN — Trigger installation](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/How_to/Trigger_install_prompt):
  prompt wymaga dostępnego mechanizmu; instrukcje są ścieżką alternatywną.

## Domknięcie 156.4 — 15 X 2026

Manifest, ikony, publiczny SW, panel Windows/Linux/Android/iOS przed logowaniem
i w Ustawieniach, instrukcje, skrót Linux oraz PL/EN gotowe lokalnie.
[Runbook i dowody 156.4](../runbooks/installation_156_4.md). Flagi nadal OFF;
bez wdrożenia. Odbiór rzeczywistej instalacji na urządzeniach należy do 156.5.

## 156.8 — odbiór publikacji Google

[Zamknięcie etapu 156.8](sprint_156_8_google_publication_closure.md): PASS operatora 18 X 2026, Google OAuth działa publicznie. Zakres i odrębne otwarte zadania opisano w protokole.
