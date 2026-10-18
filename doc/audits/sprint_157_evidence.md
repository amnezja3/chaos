# Sprint 157 — macierz dowodów, 16 X 2026

## Rozszerzenie 18+ — 17 X 2026, lokalnie

76 testów backendu oraz testy JS/Playwright PASS. Dwie ścieżki rejestracji,
czterej symulowani dostawcy, stare konta i zgody, aktywne sesje, odmowa,
blokada wieku i usuwanie. Migracja addytywna/idempotentna, bez zmian kont.
Raport: [identity_18_report.md](identity_18_report.md).
Flaga domyślnie OFF, dokumenty DRAFT. Nie aktywowano produkcyjnie; nie nadano
pełnego PASS prawnego ani Google. Fizyczne PWA i prawdziwi dostawcy w odbiorze
wdrożenia. Źródła i otwarte decyzje operatora zapisane w raporcie.

## Aktualizacja 17 X 2026

Operator wdrożył `230a40c`: backup bazy/sesji, dry-run, migrated,
baseline_matches, already_migrated i HTTP 200 potwierdzone wynikami z serwera.
Audyt: 43 konta, 1 grupa kolizji nicków, brak kolizji e-maili, 2 brakujące
e-maile, 1 konto bez hasła, 0 uszkodzonych profili. Nie zmieniano tych kont.
Użytkownik potwierdził dostarczenie poczty, podłączanie i logowanie dostawców
(Google również osobnym odbiorem). Nie wnioskujemy z tego kompletnego testu
wszystkich dostawców na wszystkich urządzeniach. Nowa rejestracja jest w odbiorze.

Lokalna poprawka UX: okno konta wewnątrz CHAOS, styl bramy, właściwy kursor,
wyniki przy przyciskach + powiadomienia systemowe. Backend: 28 testów PASS.
Playwright Chromium lokalnie (MCP niedostępny): rzeczywisty formularz konta,
settings i admin; desktop/mobile, jedno okno przeglądarki, symulowany dostawca
i powrót do panelu; błędy przy przycisku i toast. Kolejki gameplayu są atrapami
z zachowaniem kontraktu nagłówków sesji, bez testowania świata gry.
Nowa poprawka nie wymaga zmiany schematu ani zatrzymania workerów.

Rejestracja po OAuth: nick → klan → profesja → podsumowanie, karty klanów
z opisami oraz avatary profesji z istniejącego onboardingu. Kod e-mail dopiero
na końcu, gdy adres nie jest już potwierdzony. Weryfikacja zachowuje wybory.
`tools/test_identity_registration_ui.py`: PASS desktop EN (adres dostawcy)
i mobile PL (kod z mock poczty), oba z rzeczywistym utworzeniem konta
w izolowanej bazie. Sprawdzono zmianę klanu/reset profesji, zmianę adresu,
komunikat pustego kodu, brak overflow i błędów JS. Końcowe przejście do świata
jest zastąpione stroną testową; nie jest to odbiór gameplayu ani prawdziwego OAuth.
Regresja web/store/providers: 28 PASS (24,085 s). Przeglądarka i fixture zamknięte.
Nowy UI rejestracji nadal wymaga wdrożenia i odbioru użytkownika.

Poniższy zapis opisuje stan przed pierwszym wdrożeniem i historyczne testy.

Status: implementacja lokalna przed wdrożeniem. **Nie nadano pełnego PASS.**
Nie uruchomiono nowych funkcji na produkcji ani nie używano sekretów dostawców.

| Obszar | Dowód lokalny | Pozostały odbiór |
| --- | --- | --- |
| Audyt, schemat, migracja | Dry-run, apply, idempotencja, backup, baseline, integralność i FK na izolowanych bazach | Audyt oraz spójny backup rzeczywistej bazy przed apply |
| Google, Discord, GitHub, Steam | Adaptery; testy podpisanych JWT i negatywnych claims, PKCE, walidacji Steam, zweryfikowanych adresów; przepływy HTTP z zastąpionym serwerem dostawcy | Logowanie i powrót od każdego prawdziwego dostawcy |
| Rejestracja | Atomowe konto/profil/portfel/tożsamość/zgoda; rollback, kolizje, jednorazowy ticket; przeglądarka EN mobile | Realna rejestracja, potwierdzenie adresu i akceptacja treści zgody |
| Konta i sesje | Link/unlink, ostatnia metoda, świeży reauth, wygasanie, zmiana hasła, generacje sesji, CSRF | Powrót OAuth na fizycznych urządzeniach, w tym oddzielny magazyn PWA |
| Poczta w adminie | Zapis szyfrowanego sekretu, brak odczytu hasła przez API, zachowanie pustego hasła, kontrola uprawnień; formularz PL desktop i EN mobile | Ustawienie SMTP i rzeczywisty odbiór wiadomości |
| Usuwanie | Kontrola reauth, blokada ostatniej metody, tombstone tożsamości, zachowanie innego konta i kopii wiadomości odbiorcy | Kontrolowany odbiór na koncie testowym po wdrożeniu |
| Wdrożenie | Runbook komenda → wynik, flagi, rollback funkcji bez cofania aktywnego świata | Wspólne wykonanie na serwerze |

## Uruchomione sprawdzenia

- Szeroka regresja: 146 testów PASS (123,875 s), przed końcowymi poprawkami.
- Końcowe testy skupione na Gateway: zestaw web/store/providers,
  **26 testów PASS (34,456 s)**, przez `tools/run_isolated_tests.py`.
  Fixture jawnie wyłącza import seedów lokalnej gry. Bezpośrednie uruchomienie
  unittest wcześniej ujawniło zależność fixture od katalogu roboczego; poprawiono ją.
- Czyste lokalne `.venv`, pełne requirements i `pip check`: PASS.
  Authlib 1.9.1; test negatywny klucza JWK dostarczonego przez niezaufany token.
- Playwright MCP: zapis SMTP przez rzeczywisty formularz admina z kontem testowym;
  czyszczenie pola hasła, brak poziomego overflow; konto EN przy 390×844;
  rejestracja EN i przejście po utworzeniu konta. Końcowy ekran rejestracji bez
  błędów konsoli. Błąd wysyłki przy wyłączonej poczcie był oczekiwany.
- Testy przeglądarkowe korzystały z izolowanego fixture, bez prawdziwej wysyłki
  i bez logowania do zewnętrznych kont. Browser i serwer fixture zamknięto.
- Screenshot: `.playwright-mcp/identity-157-register-en-mobile.png`.

## Konfiguracja poczty

**Admin → Identity Gateway → Konfiguracja poczty**: tryb wyłączony/SMTP,
host, port, STARTTLS lub TLS/SSL, adres nadawcy, login i hasło. Zapis wymaga
świeżego ponownego uwierzytelnienia administratora. Hasło jest szyfrowane
kluczem wyprowadzonym z trwałego `CHAOS_SECRET_KEY`; nie wraca przez API.
Puste pole zachowuje hasło; osobna opcja pozwala je usunąć. Test wysyłki ma
własne pole odbiorcy. Zmiana konfiguracji nie wymaga restartu.

SMTP pozostaje wyłączone do konfiguracji. Tryb mock istnieje wyłącznie w testach;
brak SMTP nie oznacza pozornej dostawy. Dane OAuth pozostają sekretami serwera.

## Ograniczenia odbioru

Wspólna sesja używa mechanizmu 156; nie zakładamy przenoszenia cookies między
przeglądarką i PWA. Zmiana kontekstu wymaga bezpiecznego ponowienia logowania.
Linux/iOS nadal wymagają odbioru urządzeniowego. Weryfikacja historycznych
kolizji nicków/e-maili wymaga audytu na serwerze. Nie łączymy kont po samym e-mailu.

Instrukcja: [wdrożenie 157](../runbooks/identity_gateway_157.md).
Wcześniejsze raporty 157.1/157.2 są zapisami etapów, nie opisem końcowej implementacji.

## Publiczny Google OAuth — 18 X 2026

PASS potwierdzony przez operatora: Google działa publicznie dla użytkowników spoza listy testerów. Etap publikacji zamknięto na polecenie operatora pod oznaczeniem [156.8](../sprints/sprint_156_8_google_publication_closure.md). Nie oznacza to zamknięcia pełnej polityki wieku/komunikacji 157.8, odbioru innych dostawców ani zgodności z RODO. Umowy pozostają osobnym pilnym zadaniem. Flaga wieku 0, Mistral pozostaje zablokowany. Wynik VPS: cztery procesy online po aktualizacji plików, właściwy katalog, losowanie miasta bez dawnego ip-api; cztery akceptacje 157-v1 bez oświadczeń wieku.
