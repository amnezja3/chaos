# CHAOS 18+ — raport implementacji, 17 X 2026

Implementacja lokalna zakończona; brak pushu, migracji serwera i aktywacji na
produkcji. Flaga `CHAOS_ADULT_POLICY_ENABLED` domyślnie OFF. Nie nadano prawnego
zatwierdzenia dokumentom ani nie zgłoszono ich do Google.

## Backend i dane

Rozszerzono obecny Identity Gateway, bez drugiego systemu kont. Przy ON każda
rejestracja wymaga JSON `age_confirmed: true` (ściśle boolean), wersji
`age_statement_version: "18-v1"` i aktualnego `terms: "157-18-v1"`.
Wersja terms jest roboczym identyfikatorem kontraktu do finalizacji przed rolloutem.
Nie korzystamy z wieku deklarowanego przez OAuth, daty urodzenia ani skanów.

Klasyczna rejestracja zapisuje zgodę w tej samej transakcji co profil/portfel.
Rejestracja czterech dostawców rozszerza już istniejącą transakcję. Błąd zapisu
zgody wycofuje tworzenie konta. Nie wystarczy wysłać stringa "true", liczby 1,
starej wersji warunków ani samej poprawnej tożsamości dostawcy.

Wspólny before_request kontroluje wszystkie niepubliczne wejścia zalogowanego
użytkownika, zanim zadziałają gameplay/launch/detention. API zwraca 403,
dokument przekierowuje do `/account/terms`. Wyjątki są zamkniętą listą endpointów
niezbędnych dla logowania, dokumentów, konta i wylogowania; nowe moduły gry
nie otrzymują automatycznie wyjątku. Nie zmieniono mechaniki świata.

Stare konta nie są usuwane i nie otrzymują zgody automatycznie. Odmowa zachowuje
dane. Jawna informacja o wieku poniżej 18 zapisuje trwałą blokadę niezależną od
akceptacji. CLI operatora pozwala nakładać blokadę i korygować pomyłki, z audytem.
Zwykłe konto zablokowane ze względu na wiek może przejść reauth i usunąć konto.
Dotychczasowa ochrona technicznego konta admin przed samousunięciem pozostaje.

Akceptacja nadal używa CSRF, aktualnej generacji sesji i transakcyjnego guardu.
Test drugiego urządzenia ujawnił nieobsłużony `lineage_replaced` w actor();
zamieniono go na kontrolowane `stale_session` 409, bez zapisu zgody.

## Migracja

Istniejący `tools/identity_157_migrate.py` dodaje trzy kolumny:

- `identity_consents.age_confirmed`, INTEGER 0/1, domyślnie 0;
- `identity_consents.age_statement_version`, TEXT, domyślnie NULL;
- `identity_account_security.age_restricted`, INTEGER 0/1, domyślnie 0.

User ID, wcześniejsze terms_version/accepted_at, profile, salda i generacje sesji
pozostają zachowane. Test sprawdza dry-run bez zmiany pliku, apply,
already_migrated, integralność/FK i hash wszystkich pierwotnych kolumn/rekordów.
Brak wymaganego schematu przy aktywnej ochronie nie otwiera gry.

## Frontend

Obie rejestracje mają dwa osobne, domyślnie niezaznaczone checkboxy. Skrócony
formularz zachowuje avatary i weryfikację adresu tylko gdy potrzebna. Klasyczny
formularz umieszcza zgodę na ostatnim kroku, a błąd wyświetla obok nawigacji.
Istniejące konto widzi CONTINUE, odmowę, deklarację braku pełnoletności,
obsługę/usunięcie konta i wylogowanie. Dokumenty otwierają się w dialogu bez
kasowania formularza. Zachowano PL/EN, mobile i stylistykę bramy.

Launch, bridge fetch i wznowienie PWA kierują odpowiedzi 403 dotyczące wieku
do bramki. Zgoda nie czyści sesji i nie zastępuje procedury logowania.
Nowy klucz błędu wymagał wspólnej wersji katalogów `157.18.1`; pozostałe domeny
PL/EN zmieniły wyłącznie content_version, zgodnie z walidatorem katalogów.

## Wyniki testów

Backend: **76 PASS, 75,765 s**, zestawy adult_policy, gateway web/store/providers,
registration_locale, persistent_session_flows, launch_controller, installation,
ghost_i18n przez runner izolujący bazę i katalog roboczy.

JavaScript: test_session_generation_isolation, test_launch_session_binding,
test_ghost_i18n PASS; sprawdzono także przekierowanie po 403 na aktywnej stronie
i po wznowieniu PWA, bez kasowania sesji. Kontrola składni JS i git diff --check PASS.

Playwright Chromium lokalnie (MCP nie był dostępny), izolowana baza:

| Zakres | Wynik |
| --- | --- |
| Klasyczna rejestracja: desktop PL i mobile EN, oba checkboxy, brak jednego, dialog i utworzenie konta | PASS |
| Skrócona rejestracja: desktop EN i mobile PL, adres potwierdzony oraz kod mock, nowe konto | PASS |
| Czterej dostawcy × desktop/mobile: rzeczywisty start/callback/ticket, symulowany dostawca | 8 PASS |
| Istniejące konto: rzeczywista akceptacja w formularzu | PASS |
| Odtworzony magazyn cookies: bramka, odmowa, trwała blokada wieku, konto i logout | PASS |
| Publiczne `/privacy`, `/terms`, PL/EN, responsywność, zachowanie formularza | PASS |

API testuje brak wieku/warunków, błędne typy/wersje, replay/idempotencję,
rollback konta, stare zgody, prawdziwe lokalne logowanie i powrót istniejącej
tożsamości OAuth, zastąpioną sesję, operator restriction/release, usunięcie
konta przy blokadzie oraz publiczne dokumenty także przy wyłączonym OAuth.

Nie testowano tu prawdziwych kont Google/Discord/GitHub/Steam ani fizycznej
instalacji Android/iOS. Odtworzone cookies i test JS nie są odbiorem urządzenia.
Nie uruchamiano świata produkcyjnego; po utworzeniu konta docelowy boot jest
zastępowany w UI testach stroną kontrolną. Przeglądarki i fixture zamknięto.

## Dokumenty, Google i decyzje operatora

`/terms` i `/privacy` pozostają **157-18-draft-2**. Usunięto zasadę 13+;
zgoda opiekuna nie dopuszcza niepełnoletnich do platformy. Zapis wieku jest
opisany jako oświadczenie, nie weryfikacja dokumentem. Zachowano specyfikę
trwałego świata, klanów, konfliktów, Cybernera i interakcji ludzi/agentów AI.

Doprecyzowano Google openid/email, Discord identify/email, GitHub read:user
i user:email oraz SteamID; odbierane i zapisywane pola, opcjonalność logowania,
łączenie/odłączanie metod, brak utrwalania tokenów dostępu/odświeżania,
sesje, dane techniczne, AI Mistral/Ollama i skutki usuwania konta.
Wyraźnie rozdzielono czas ważności rekordów od ich fizycznego usunięcia.
Brak zgody marketingowej wywodzonej z odczytania polityki.

Przed finalną publikacją operator musi zatwierdzić:

1. Adres operatora; nazwę i e-mail już podał: Michał Cezary Jankiewicz,
   year2108@chaos.re.
2. Odpłatność i kompletne zasady usługi, licencję na treści potrzebną do działania
   gry, reklamacje, moderację/odwołania oraz zmiany regulaminu.
3. Okresy/zasady retencji: logi/proxy, backupy, tombstone i hashe wycofanych
   tożsamości, historia świata, wiadomości oraz procedura żądań usunięcia.
4. Podwykonawców, lokalizacje/transfery i zabezpieczenia; pełną inwentaryzację
   produkcyjnych integracji AI, cookies i analityki. Audyt adaptera narracji
   nie zastępuje audytu wszystkich agentów i konfiguracji serwera.
5. Finalną treść PL/EN, podstawy prawne i wersję 1.0, następnie aktywację flagi.

Źródła wymagane do przygotowania weryfikacji Google:
[brand verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/brand-verification),
[OAuth policies](https://developers.google.com/identity/protocols/oauth2/policies),
[User Data Policy](https://developers.google.com/terms/api-services-user-data-policy).
Nie wpisano niezweryfikowanego zapewnienia o pełnej zgodności lub Limited Use
w miejsce brakujących ustaleń organizacyjnych. Akceptacja Google pozostaje
osobnym procesem operatora.

## Wdrożenie i pliki

Procedura backup → dry-run → apply → baseline → idempotencja → uruchomienie OFF
→ zatwierdzenie dokumentów → aktywacja ON znajduje się w
[runbooku](../runbooks/identity_18_rollout.md). Nie odtwarzać starej bazy świata
po wznowieniu rozgrywki. Po ogłoszeniu zasad nie wyłączać ochrony jako obejścia
problemu; w razie potrzeby ograniczyć dostęp do gry na czas naprawy.

Lista plików poniżej obejmuje implementację, testy, dokumentację i dowody UI.

- doc/history/project_journal.md
- doc/audits/sprint_157_evidence.md

- .playwright-mcp/adult-existing-mobile.png
- .playwright-mcp/adult-local-en.png
- .playwright-mcp/adult-local-pl.png
- .playwright-mcp/identity-registration-clans-en.png
- .playwright-mcp/identity-registration-clans-pl.png
- .playwright-mcp/identity-registration-roles-en.png
- .playwright-mcp/identity-registration-roles-pl.png
- .playwright-mcp/identity-registration-summary-en.png
- .playwright-mcp/identity-registration-summary-pl.png
- .playwright-mcp/legal-privacy-en.png
- .playwright-mcp/legal-privacy-pl.png
- .playwright-mcp/legal-terms-en.png
- .playwright-mcp/legal-terms-pl.png
- doc/audits/identity_18_audit.md
- doc/audits/identity_18_report.md
- doc/runbooks/identity_18_rollout.md
- identity_gateway/adult_policy.py
- identity_gateway/store.py
- identity_gateway/web.py
- legal_documents.py
- run.py
- static/css/legal.css
- static/js/identity_gateway.js
- static/js/launch_controller.js
- static/js/legal.js
- static/js/register_scripts.js
- static/js/session_generation.js
- static/locales/en/apps.json
- static/locales/en/catalog.json
- static/locales/en/creators.json
- static/locales/en/entry.json
- static/locales/en/foundation.json
- static/locales/en/lab.json
- static/locales/en/map_actions.json
- static/locales/en/map_workspace.json
- static/locales/en/onboarding.json
- static/locales/en/radio.json
- static/locales/en/settings.json
- static/locales/en/shell.json
- static/locales/en/shop.json
- static/locales/manifest.json
- static/locales/pl/apps.json
- static/locales/pl/catalog.json
- static/locales/pl/creators.json
- static/locales/pl/entry.json
- static/locales/pl/foundation.json
- static/locales/pl/lab.json
- static/locales/pl/map_actions.json
- static/locales/pl/map_workspace.json
- static/locales/pl/onboarding.json
- static/locales/pl/radio.json
- static/locales/pl/settings.json
- static/locales/pl/shell.json
- static/locales/pl/shop.json
- templates/_adult_declaration.html
- templates/_legal_links.html
- templates/admin_base.html
- templates/identity_adult_terms.html
- templates/identity_gateway.html
- templates/identity_registration.html
- templates/launch.html
- templates/legal_document.html
- templates/linux.html
- templates/map_template.html
- templates/register.html
- templates/session_logout.html
- tests/js/test_launch_session_binding.js
- tests/js/test_session_generation_isolation.js
- tests/test_identity_adult_policy.py
- tests/test_identity_gateway_store.py
- tools/identity_157_migrate.py
- tools/identity_18_access.py
- tools/identity_gateway_browser_fixture.py
- tools/test_adult_policy_ui.py
- tools/test_identity_registration_ui.py
