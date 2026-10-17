# 157.1 — lokalny fundament, 16 X 2026

Zapis etapu historycznego. Aktualny stan: [macierz 157](sprint_157_evidence.md).

Status: w realizacji. To nie jest odbiór adapterów ani pełny PASS 157.1/157.
Kontrakt callbacków pozostaje w `sprint_157_1_auth_callback_contract.md`.

## Wykonane

- `identity_gateway/config.py`: konfiguracja Google, Discord, GitHub, Steam;
  stały origin serwerowy, flagi domyślnie OFF, status bez sekretów. Moduł nie
  rejestruje endpointów ani nie aktywuje przycisków UI.
- `config/identity_gateway.env.example`: puste miejsca na sekrety i SMTP.
  Na decyzję autora poczta pozostaje `disabled`; `mock` dozwolony tylko przy
  jawnej konfiguracji testowej. Nie zaimplementowano jeszcze transportu poczty.
- `tools/identity_157_audit.py`: odczyt SQLite w trybie read-only, raport ID
  kolizji/braków bez nicków, e-maili i haseł; brak migracji lub importu aplikacji.
- `database.verify_password`: brak/puste hasło nigdy nie przechodzi autoryzacji.
  Usunięto możliwość zaakceptowania dwóch pustych wartości przez porównanie
  legacy. Nie oznacza to jeszcze wdrożenia stanu konta external-only.

## Ustalenia implementacyjne

- Klucz nicku: NFKC + trim + casefold. E-mail: trim + lowercase, bez usuwania
  kropek lub części `+tag`. Historycznych kont nie zmieniamy automatycznie;
  kolizje raportujemy do indywidualnego rozstrzygnięcia przed ograniczeniami DB.
- Jedna tożsamość danego dostawcy na konto; unikalność provider/subject oraz
  user/provider ma wymusić 157.2. E-mail nie stanowi podstawy autołączenia.
- Domyślne TTL konfiguracji: intencja logowania 10 min, rejestracja 30 min,
  świeży reauth 5 min, token pocztowy 30 min. Egzekwowanie dopiero w usługach DB.
- Reauth nie może wynikać wyłącznie z powrotu SSO. Dla dostawcy bez dowodu
  świeżego uwierzytelnienia potrzebne będzie hasło lokalne lub kod na wcześniej
  zweryfikowany adres. Przy wyłączonej poczcie nie wolno symulować potwierdzenia.
- Wspólnym punktem nowej sesji pozostaje `begin_authenticated_session`:
  generacja, rotacja SID i zastępowanie poprzedniego logowania bez zmian.

## Ryzyka wykryte w istniejącym kodzie

Rejestracja lokalna tworzy konto i uzupełnia profil w oddzielnych operacjach.
Nowa rejestracja zewnętrzna wymaga atomowego zapisu konta, profilu, tożsamości
i zgód, zachowując istniejący spawn, portfel i wybór frakcji/roli.

E-mail profilu nie jest dowodem weryfikacji. Nie nadajemy historycznym adresom
stanu verified w migracji. Usuwanie konta obejmuje dziś również współdzielone
wiadomości i wieloetapowe porządki świata; przed 157.7 należy ustalić retencję
i idempotentne czyszczenie, bez automatycznego rozszerzania obecnego usuwania.

## Dowody

| Kontrola | Wynik | Ograniczenie |
| --- | --- | --- |
| Izolowane testy foundation + user_store_credentials + registration_locale | 19/19 PASS | Bez komunikacji z dostawcami |
| Lokalny audyt legacy | 21 kont; 0 kolizji nick/e-mail; 0 błędnych profili; 2 braki e-maila; 1 puste hasło; 2 hasła legacy | Baza lokalna, nie aktualna produkcja |
| Niezmienność bazy przez audyt | PASS, porównanie SHA-256 fixture | Produkcja nie była modyfikowana ani testowana |
| UI/OAuth/SMTP | Nie testowano | Brak adapterów i transportu na tym etapie |

Polecenie regresji:
`python tools/run_isolated_tests.py test_identity_gateway_foundation test_user_store_credentials test_registration_locale`.

Audyt operatora: `python tools/identity_157_audit.py --db data/game.sqlite3`.
Status konfiguracji: `python tools/identity_157_audit.py --config`.
Raporty zawierające ID kont przechowywać poza repozytorium.

## Pozostałe warunki zamknięcia 157.1

Inwentaryzacja blokad/bana i reguł usuwania, finalna retencja, audyt bieżących
danych produkcyjnych oraz wybór i przypięcie bibliotek adapterów pozostają
otwarte. Kandydatem OAuth/OIDC jest Authlib; Steam wymaga osobnego OpenID 2.0.
Nie uznajemy jeszcze biblioteki Steam ani obsługi PKCE każdego dostawcy za
zweryfikowane. Dane SMTP/nadawcy poda autor; ich brak nie blokuje pracy nad DB.

Źródła kontraktów adapterów:
[Authlib](https://docs.authlib.org/en/latest/oauth2/client/web/flask.html),
[Google OIDC](https://developers.google.com/identity/openid-connect/openid-connect),
[Discord](https://docs.discord.com/developers/topics/oauth2),
[GitHub](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps),
[Steam](https://partner.steamgames.com/doc/features/auth#website).
