# Sprint 157 — Identity Gateway

[Plan 157.8 — polityka 16+ i bezpieczeństwo komunikacji](sprint_157_8_age_policy_16_communication_safety.md): etapy 157.8.1–157.8.4, kryteria odbioru i decyzje przed aktywacją. Polityka wieku pozostaje wyłączona na produkcji.

[Audyt kodu i ustalone callbacki do rejestracji aplikacji — 16 X 2026](../audits/sprint_157_1_auth_callback_contract.md).
Kontrakt: `https://chaos.re/auth/google/callback`,
`https://chaos.re/auth/discord/callback`, `https://chaos.re/auth/github/callback`.
Adresy bez końcowego ukośnika; endpointy zaimplementowano lokalnie, także
`https://chaos.re/auth/steam/callback`. Odbiór rzeczywistych dostawców pozostaje przed nami.

Status: **IMPLEMENTACJA LOKALNA — PRZED WDROŻENIEM**, 16 X 2026.
Adaptery, rejestracja, zarządzanie kontem i poczta w adminie są zaimplementowane.
Bez zmian na serwerze; pełny PASS wymaga odbiorów opisanych w
[macierzy dowodów](../audits/sprint_157_evidence.md) i
[procedurze wdrożenia](../runbooks/identity_gateway_157.md).
[Wyniki i otwarte punkty 157.1](../audits/sprint_157_1_foundation.md).

Przygotowanie UI w 156.7: panel logowania zawiera cztery przyciski w kolejności
Google / GitHub / Discord / Steam, z ikonami i kolorami według wizualizacji.
Do wdrożenia adapterów pozostają `disabled`, z jawnym komunikatem PL/EN.
157 ma podłączyć te kontrolki do zweryfikowanych endpointów backendu, zgodnie
z dostępnością konfiguracji każdego dostawcy. Sam wygląd nie stanowi integracji.

Onboarding 156.7 ma już wspólny wygląd wszystkich sześciu kroków, PL/EN i ten sam
fragment przycisków dostawców na pierwszym kroku rejestracji. Podłączając intencję
zewnętrzną w 157, zachować wspólny wybór frakcji/roli i podsumowanie; stan
zweryfikowanego dostawcy dostarcza backend, nie parametr klienta. Pomijanie hasła,
potwierdzanie e-maila i zgody dodać dopiero razem z właściwymi kontraktami 157.
Źródło: koncepcja autora „CHAOS — Identity Gateway” v1.0 oraz decyzja
o dodaniu **Steam już do pierwszej fazy**.

## Cel i zakres pierwszego wydania

Jedno konto CHAOS, jedna postać i wiele metod logowania:
**Google / Discord / GitHub / Steam / lokalne konto z hasłem**.
Wszyscy czterej dostawcy obejmują rejestrację, logowanie, podłączanie,
odłączanie i odbiór. Steam nie jest dodatkiem odłożonym na później.

Identity Gateway potwierdza tożsamość i przekazuje ją do istniejącego mechanizmu
sesji. Nie tworzy alternatywnych postaci, portfeli, klanów ani historii.
Cały nowy interfejs, błędy, pomoc i wiadomości aktywacyjne mają PL/EN.
Nazwy graczy pozostają treściami użytkowników.

Plan obejmuje również potwierdzanie e-maila, opcjonalne ustawienie hasła,
zarządzanie połączeniami w ustawieniach, usunięcie konta i nową zakładkę
administracyjną. Nie obejmuje społecznościowych API dostawców, importu znajomych,
repozytoriów, ekwipunku Steam, własności gier ani publikacji CHAOS w sklepie Steam.
Apple, Microsoft, Telegram, MetaMask/Web3, passkeys i dodatkowe mechanizmy
odzyskiwania kont pozostają poza pierwszym wydaniem.

## Zależności i stan zastany

[156](sprint_156_universal_installation_persistent_session.md) pozostaje osobnym
sprintem: trwałe sesje i start wdrożono; użytkownik potwierdził działanie Windows
i wybranych urządzeń Android. Linux/iOS pozostają do odbioru. Integrację OAuth
z PWA trzeba sprawdzić osobno. Użytkownik autoryzował rozpoczęcie 157;
nie nadaje to PASS sprintom 155/156. 149–152 nadal zamrożone.

Wstępny przegląd kodu z 15 X 2026:

| Obszar | Stan i konsekwencja dla 157 |
| --- | --- |
| `database.py`, `users` | Istnieją `id`, unikalny `username`, `password`, `salt`, `profile_json`. Używamy istniejącego ID; nie zmieniamy kluczy gameplayu opartych na username. |
| `run.py`, `index()` | Lokalny login uwierzytelnia username i hasło. Logowania przez e-mail nie uznajemy za już dostępne; wymaga jawnego resolvera i obsługi kolizji. |
| `/api/register-finalize` | Rejestracja wymaga też frakcji i roli. Krótki formularz zewnętrzny nie może pominąć tych danych ani losować klanu/profesji. Zachowujemy wybór w istniejącym onboardingu przed utworzeniem pełnego konta. |
| Walidatory rejestracji | Kontrola formatu e-maila i długości nicku nie wystarcza do potwierdzenia adresu oraz unikalności nicku. Potrzebny audyt danych historycznych. |
| Aktywacja i regulamin | W przeglądanej ścieżce nie potwierdzono kompletnego mechanizmu wysyłki/aktywacji e-maila ani wersjonowanej zgody. Zaplanować dostarczenie lub integrację, nie zakładać gotowości. |
| Sesje | `begin_authenticated_session`, lineage, ownership i precommit guard pozostają wspólne. 156.2 dostarcza activity, CSRF, logout POST i unieważnianie po zmianie hasła. |
| Usuwanie | Istnieją `/api/users/delete`, `UserStore.delete_user`, cleanup terytoriów i tombstones. Rozszerzamy wspólną ścieżkę; audytujemy częściowe błędy i ponowienie, zamiast tworzyć drugi niezależny delete. |

## Kontrakty obowiązujące

1. Identyfikujemy przez parę **provider + stabilny subject**, nigdy przez nick
   ani e-mail. Tożsamość zewnętrzna może należeć najwyżej do jednego konta CHAOS.
2. Zbieżny e-mail **nie łączy kont automatycznie**, również gdy dostawca go
   potwierdził. Wymagamy zalogowania do istniejącego konta i świadomego podłączenia.
   Nie przenosimy zasobów ani nie scalamy postaci.
3. Publiczny nick jest oddzielony od niezmiennego technicznego username i ID.
   Dla nowych kont zewnętrznych username generuje backend, w formacie zgodnym
   z istniejącym kodem. Podpowiedź nicku od dostawcy wymaga zatwierdzenia.
4. Do ukończenia formularza, potwierdzenia wymaganych danych i regulaminu istnieje
   tylko wygasająca intencja rejestracji. Konto, tożsamość, zgoda i inicjalny profil
   powstają atomowo, jednokrotnie. Awaria wydania sesji nie tworzy drugiej postaci.
5. Konto zewnętrzne nie wymaga hasła. Brak hasła jest jawnym stanem; puste hasło,
   automatyczny hash pustego tekstu lub techniczne hasło zastępcze nie mogą działać.
6. Podłączenie, odłączenie, ustawienie hasła i usunięcie konta wymagają aktualnej
   sesji oraz świeżego potwierdzenia tożsamości. Sam powrót z istniejącej sesji SSO
   lub wybór konta dostawcy nie jest automatycznie dowodem ponownego uwierzytelnienia.
7. Nie odłączamy ostatniej używalnej metody. Sprawdzenie i zmiana są jedną
   transakcją odporną na dwa równoległe żądania. Chwilowa awaria dostawcy nie
   oznacza usunięcia metody z konta.
8. Każdy login respektuje te same blokady i stan konta, obraca SID oraz zastępuje
   poprzednie aktywne logowanie. TTL pozostaje zatwierdzone **30 dni nieaktywności /
   90 dni od logowania**. Podłączenie dostawcy nie przełącza gracza na inne konto.
9. Wznowienie ważnej sesji przez launch 156 nie kontaktuje się z dostawcą.
   Nie kopiujemy cookie pomiędzy PWA i przeglądarką ani nie przekazujemy sesji w URL.
10. Sekrety wyłącznie na serwerze. Tokeny dostawców służą do ustalenia tożsamości;
    nie przechowujemy access/refresh tokenów po zakończeniu tej operacji bez
    konkretnej potrzeby. Logi nie zawierają kodów, tokenów, haseł ani sekretów.

## Dostawcy: wspólny wynik, różne protokoły

Adapter zwraca zweryfikowane `provider`, `subject`, opcjonalny e-mail i informację
o jego weryfikacji oraz opcjonalną podpowiedź nazwy. Nie zwraca uprawnień gameplayu.

| Dostawca | Integracja pierwszego wydania | E-mail |
| --- | --- | --- |
| Google | OpenID Connect, authorization code; walidacja podpisu, issuer, audience, czasu i nonce; subject `sub` | Akceptujemy tylko poprawnie zweryfikowane twierdzenie o konkretnym adresie. |
| Discord | OAuth2 authorization code; backend odczytuje tożsamość użytkownika; minimalne `identify` i `email` | Brak adresu lub brak potwierdzenia prowadzi do aktywacji CHAOS. |
| GitHub | OAuth2 authorization code, PKCE S256; backend pobiera ID użytkownika; minimalne zakresy potrzebne do profilu/e-maila, bez dostępu do repozytoriów | Prywatny/brakujący adres i jego weryfikacja wymagają osobnej obsługi. |
| Steam | **OpenID 2.0 dla strony WWW**, odrębny adapter; zweryfikowany SteamID zapisany jako tekst | Nie zakładamy dostępności adresu. Nowy gracz podaje e-mail i potwierdza go przez CHAOS. |

Steam nie jest adapterem OAuth2 ani OpenID Connect. Walidujemy odpowiedź przez
zaufany endpoint Steam, powiązanie z lokalną intencją, `return_to`, realm,
podpisane pola i nonce/replay. Nie ufamy samemu SteamID przesłanemu przez klienta
ani dowolnemu adresowi serwera wskazanemu w callbacku. Publiczny profil/avatar
jest opcjonalny; awaria jego pobrania nie blokuje zweryfikowanego logowania.
Oficjalna dokumentacja opisuje webowe logowanie Steam i identyfikację przez
SteamID: [Steamworks — Website authentication](https://partner.steamgames.com/doc/features/auth#website).

Dla OAuth stosujemy authorization code, jednorazowy state i PKCE tam, gdzie
dostawca je wspiera; zdolności i konfigurację biblioteki potwierdza 157.1.
Callback przypisany jest do konkretnego dostawcy i celu login/link/reauth.
Adres powrotu jest z allowlisty, a dane tożsamości sprawdza backend.
Podstawa: [Google OIDC](https://developers.google.com/identity/openid-connect/openid-connect),
[Discord OAuth2](https://docs.discord.com/developers/topics/oauth2),
[GitHub OAuth apps](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps)
oraz [OAuth Security BCP](https://www.rfc-editor.org/rfc/rfc9700.html).

## Etapy realizacji

157.1–157.5 i 157.7: implementacja i lokalna weryfikacja wykonane; odbiór
produkcyjny oczekuje. 157.6: wspólna sesja podłączona, fizyczne PWA do odbioru.
157.8: regresja lokalna wykonana, macierz pozostaje otwarta. 157.9: procedura
gotowa, wdrożenia nie wykonano. Poniższe listy opisują zakres i kryteria odbioru,
nie deklarację pełnego PASS.

### 157.1 — audyt i kontrakt Identity Gateway

- Zinwentaryzować wszystkie logowania, tworzenie profilu, hasła, bany/blokady,
  usuwanie, reset, zgody, pocztę oraz zależności ID/username/nick/e-mail.
- Sprawdzić duplikaty nicków i e-maili bez zmieniania historycznych kont.
  Ustalić normalizację i politykę kolizji przed dodaniem ograniczeń unikalności.
- Wybrać utrzymywane biblioteki OAuth/OIDC oraz OpenID 2.0 Steam; ustalić
  callbacki, minimalne zakresy, timeouty, rate limiting i politykę reauth.
- Rozpisać konfigurację czterech dostawców i poczty: właściciel konfiguracji,
  callbacki testowe/produkcyjne, wymagane sekrety, status gotowości. Nie zakładać,
  że Steam potrzebuje takiej samej rejestracji klienta OAuth jak pozostali.
- Uzgodnić szczegóły retencji po usunięciu konta i zasady migracji nicków/e-maili.

**Odbiór:** kontrakt danych i bezpieczeństwa, mapa integracji, raport kolizji,
lista ustawień/sekretów i jawnie zapisane decyzje. Bez zmian świata gry.

### 157.2 — dane, migracja i operacje atomowe

[Lokalny schemat, migrator i dowody transakcyjne](../audits/sprint_157_2_data_foundation.md).
Nie nadano pełnego PASS: usługa rejestracji profilu i uprawnienia reauth pozostają otwarte.

- Dodać `user_identities`: ID, FK do istniejącego `users.id`, provider,
  `provider_user_id` TEXT, opcjonalny provider_email, email_verified,
  linked_at, last_used_at; UNIQUE(provider, provider_user_id).
- Propozycja v1: najwyżej jedno połączenie danego dostawcy na konto; potwierdzić
  w 157.1 i egzekwować w DB, nie tylko w interfejsie.
- Dodać wygasające intencje uwierzytelnienia/rejestracji i jednorazowe uprawnienia
  reauth, powiązane z inicjującym klientem, celem i właściwą generacją konta.
- Zapisać wersję regulaminu i czas zgody oraz stan weryfikacji adresu.
  Dane tymczasowe mają cleanup; nie są pełnymi kontami graczy.
- Przygotować idempotentną migrację, dry-run, integralność/FK i porównanie
  identyfikatorów oraz oryginalnych profili. Nie przenumerowywać istniejących kont.

**Odbiór:** ponowiona migracja niczego nie dubluje; konkurencyjne callbacki
nie tworzą dwóch kont; błąd zapisu wycofuje całą rejestrację.

### 157.3 — czterej dostawcy i wspólny login

- Zaimplementować ProviderManager, adaptery Google/Discord/GitHub/**Steam**,
  obsługę callbacków i IdentityResolver. Rozdzielić protokoły od logiki konta.
- Znana tożsamość prowadzi do istniejącej sesji CHAOS; nieznana do intencji
  krótkiej rejestracji. Zablokowane/usunięte konto nie odzyskuje dostępu callbackiem.
- Obsłużyć anulowanie, błędny callback, niedostępność dostawcy i wygaśnięcie
  intencji bez zakładania konta, utraty sesji innego gracza ani pętli przekierowań.
- Dodać cztery przyciski na login gate, lokalny login zostaje dostępny.
  Sekrety nie trafiają do HTML; niedostępny dostawca ma czytelny komunikat PL/EN.

**Odbiór:** rzeczywisty login wszystkich czterech dostawców na kontach testowych;
testy błędnego state/nonce, podmiany providera, replay i fałszywego SteamID.

### 157.4 — krótka rejestracja, nick, e-mail i regulamin

- Formularz nick + e-mail + zgoda na konkretną wersję regulaminu, bez obowiązku
  hasła; zachować wymagany wybór frakcji/roli w onboardingu.
- Dostępność nicku sprawdzać ponownie przy commit. Nie zmieniać automatycznie
  nicków dawnych graczy. Zmiana nicku w profilu respektuje tę samą politykę.
- Dostarczyć aktywację e-maila z jednorazowym tokenem, wygaśnięciem, limitem
  wysyłek i ponowieniem. Sam GET linku nie powinien nieodwracalnie konsumować
  tokenu przez skaner pocztowy; potwierdzenie kończy kontrolowana operacja.
- Steam zawsze ma ścieżkę ręcznego adresu. Dla pozostałych dostawców wykorzystać
  potwierdzony adres tylko przy zachowaniu jego dokładnej tożsamości; edycja
  adresu wymaga nowej weryfikacji. Zmiana maila u providera nie zmienia automatycznie
  kontaktu CHAOS.
- Kolizja z istniejącym kontem kieruje do potwierdzenia jego własności i linkowania;
  nie ujawnia publicznie pełnych danych konta. Lokalny login przez e-mail dopuszcza
  tylko jednoznaczny, potwierdzony adres; legacy username nadal działa.

**Odbiór:** nowy gracz każdego dostawcy otrzymuje jedną postać; przerwanie formularza
nie tworzy osieroconego konta; kolizje nicku/e-maila nie umożliwiają przejęcia.

### 157.5 — połączone konta i lokalne hasło

- Ustawienia → Konto / Bezpieczeństwo → Połączone konta: czterej dostawcy,
  status, podłącz/odłącz oraz stan lokalnego hasła.
- Linkowanie wymaga dowodu własności aktualnego CHAOS i zewnętrznej tożsamości;
  callback po zmianie użytkownika lub generacji zostaje odrzucony.
- Odłączenie i zmiana danych mają CSRF, świeży reauth i ochronę ostatniej metody.
  Tożsamości związanej z innym kontem nie przepinamy.
- Ustawienie hasła po zewnętrznym reauth: dwa pola, walidacja, istniejący bezpieczny
  hash i polityka revocation z 156.2. Pokazać graczowi działający identyfikator
  lokalnego logowania. Zmiana/reset hasła nie omija potwierdzenia własności.
- Potwierdzić sposób świeżego reauth dla każdego dostawcy, w tym Steam. Jeśli
  nie można uzyskać wymaganego dowodu, stosować zatwierdzoną alternatywę,
  nie uznawać samego powrotu z SSO za wystarczający.

**Odbiór:** równoległe unlink nie usuwają wszystkich metod; brak hasła nie pozwala
zalogować się pustym tekstem; wszystkie metody otwierają tę samą postać.

### 157.6 — trwała sesja i powrót do PWA

- Podłączyć wszystkich dostawców do launch/bootstrap 156 i istniejących guardów,
  bez tworzenia drugiego menedżera sesji lub zdublowanych endpointów logout/status.
- Sprawdzić redirect w tym samym kontekście oraz powrót z zewnętrznej przeglądarki
  do PWA na Android/iOS. Nie uzależniać podstawowego loginu od popupu.
- Gdy system otwiera callback w innym magazynie cookies, zaprojektować i przetestować
  jawne dokończenie w pierwotnej instalacji. Ewentualny jednorazowy handoff musi
  wymagać dowodu powiązania z inicjującą instalacją; sam kod z URL nie daje sesji.
  Brak możliwości powrotu ma bezpieczny, czytelny UX, nie pozorne zalogowanie.
- Wznowienie nie wymaga aktywnego API dostawcy. Nowe logowanie inną metodą
  unieważnia stare, a stare okno nie zapisuje danych i nie wylogowuje nowego.

**Odbiór:** desktop Windows/Linux, mobile Android/iOS i zainstalowane PWA;
osobny dowód dla każdego rzeczywiście sprawdzonego środowiska. Emulacja viewportu
nie zastępuje testu izolowanych magazynów na urządzeniu.

### 157.7 — Danger Zone i panel administracyjny

- Udostępnić usunięcie własnego konta z jasnym opisem skutków, świeżym reauth
  i potwierdzeniem. Zachować ograniczenia istniejącej ścieżki administracyjnej.
- Dodać zakładkę Identity Gateway w adminie: status konfiguracji bez sekretów,
  powiązania wybranego konta, zdarzenia bezpieczeństwa i kontrolowana procedura
  usunięcia z uprawnieniami, potwierdzeniem oraz śladem audytowym.
- Ujednolicić usuwanie profilu, tożsamości, sesji, intencji, tokenów aktywacji
  i zadań; zabezpieczyć wieloetapowy cleanup przed częściowym błędem/ponowieniem.
  Callback rozpoczęty przed usunięciem nie odtwarza konta ani jego zasobów.
- Rozdzielić usunięcie danych prywatnych od zachowania/anonymizacji wymaganych
  referencji świata i historii według polityki 157.1. Chronić wiadomości,
  identyfikatory, saldo i nagrody innych graczy; nie usuwać kont u dostawców.

**Odbiór:** próba usunięcia obcego konta bez uprawnień jest odrzucana; ponowienie
cleanup jest bezpieczne; stare sesje i intencje nie przywracają dostępu.

### 157.8 — pełna regresja i macierz dowodów

- Testy integracyjne na izolowanych danych: czterej dostawcy × nowy/powiązany
  gracz, login/link/unlink, odmowa zgody, e-mail brak/niepotwierdzony/kolizyjny,
  równoległa rejestracja, restarty, timeouty, replay i usuwanie w trakcie callbacku.
- Testy zachowania istniejących ID, profili, terytoriów, nagród i historii;
  porównanie przed/po i brak powtórnego onboardingu istniejącego gracza.
- Regresja lokalnego loginu, hasła, resetu, blokad kont i całego lifecycle 156.
- Playwright MCP: lokalny UI PL/EN desktop/mobile, klawiatura, błędy konsoli,
  formularze, ustawienia i admin; osobno prawdziwe callbacki dostawców i PWA.
- Sekrety, konta testowe lub urządzenia niedostępne → konkretny otwarty punkt
  w evidence matrix, nie domniemany PASS. Mocki nie zastępują odbioru live.

**Odbiór:** macierz ze scenariuszem, środowiskiem, wynikiem i dowodem; brak
otwartych błędów przejęcia konta, utraty danych lub odcięcia ostatniej metody.

### 157.9 — procedura wdrożenia i odbiór

- Instrukcja „komenda → spodziewany wynik”: konfiguracja, spójny backup,
  dry-run, migracja, kontrole integralności, restart i smoke test.
- Wdrożenie na obecnym środowisku zgodnie z dotychczasowym modelem; nie wymaga
  drugiej instancji produkcyjnej. Konfiguracja dostawców jest częścią gotowości.
- Flagi rozdzielają nowe rejestracje, nowe podłączenia i dostęp istniejących
  kont przez dostawcę. Wyłączenie rejestracji nie może odciąć kont bez hasła.
- Rollback zachowuje addytywne tabele i dane. Po powstaniu kont external-only
  powrót do starego kodu bez ich obsługi nie jest bezpiecznym rollbackiem:
  potrzebna zgodna wersja lub kontrolowana naprawa. Nie przywracać starej bazy
  na aktywny świat kosztem nowych postępów graczy.
- Uzupełnić instrukcje operatora, pomoc PL/EN i dowody produkcyjnego odbioru.

**Odbiór:** czterej dostawcy działają na produkcji, stare konta i trwałe sesje
zachowane, operator ma przetestowaną procedurę awarii/wycofania. Dopiero wtedy
pełny PASS 157; sam komplet przycisków lub testów z mockami nie zamyka sprintu.

## Proponowane API i podział odpowiedzialności

Nazwy robocze do uzgodnienia z audytem 157.1:

| Operacja | Proponowana ścieżka / odpowiedzialność |
| --- | --- |
| Rozpoczęcie i callback | `/auth/<provider>` oraz `/auth/<provider>/callback`; adapter protokołu i weryfikacja intencji |
| Dokończenie rejestracji | POST `/auth/complete-registration`; RegistrationManager, dane z serwerowej intencji |
| Lista połączeń | GET `/api/account/identities`; tylko aktualny właściciel |
| Link/unlink | POST w `/api/account/identities/...`; IdentityLinkManager, CSRF/reauth |
| Hasło | Rozszerzenie istniejącej ścieżki credentials; CredentialManager i wspólna revocation |
| Sesja i logout | Istniejące mechanizmy 156; bez równoległego `/auth/session` i `/auth/logout` |
| Usunięcie | Wspólna usługa pod istniejącą ścieżką usuwania i kontrolowanym UI admina |

Callback z zewnętrznego serwisu ma dedykowaną ochronę protokołu; nie wolno przez
to wyłączać CSRF dla pozostałych operacji konta. Wszystkie operacje wrażliwe
wiążemy z właściwym użytkownikiem i generacją, z kontrolą także przed commit.

## Decyzje do zamknięcia w 157.1

Są to szczegóły projektu, nie warunki rozpoczęcia niniejszego planowania:

- Normalizacja nicków i zachowanie historycznych kolizji, zasady adresów legacy.
- Dostawca poczty i adres nadawcy; TTL tokenów, intencji i świeżego reauth.
- Polityka jednego połączenia na dostawcę oraz potwierdzenie reauth dla Steam
  i pozostałych dostawców, także dla kont bez lokalnego hasła.
- Retencja/anonymizacja przy usunięciu, zakres audytu administracyjnego i zasady
  ponownej rejestracji po usunięciu bez odtworzenia dawnych zasobów.
- Konkretna obsługa powrotu między kontekstami PWA, wynikająca z testów 156.

## Artefakty do dostarczenia podczas realizacji

Kontrakt architektury i audyt 157.1, migrator dry-run/apply/check, implementacja
adapterów i wspólnych usług konta, formularze i ustawienia PL/EN, panel admina,
testy regresji, macierz dowodów i runbook wdrożenia/rollbacku. Na dzień sporządzenia
tego dokumentu są to zadania sprintu, nie istniejące funkcje lub wykonane testy.
