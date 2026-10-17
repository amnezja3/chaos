# CHAOS 18+ — audyt przed zmianami, 17 X 2026

- Local: `/register` → `/api/register-finalize`; sześć etapów, bez zgody
  i kontroli wieku. Gałąź po migracji Identity zapisuje profil atomowo;
  historyczna gałąź UserProfileManager działa bez tabel Identity.
- OAuth/OpenID: `/auth/<provider>` → callback → ticket `/auth/register`
  → `/auth/complete-registration`. Google/GitHub/Discord/Steam mają wspólny
  finał. Konto powstaje dopiero w transakcji profilu/portfela/identity/consent.
- `identity_consents`: user_id, terms_version, accepted_at; brak wieku.
  `157-v1` oznacza wcześniejsze warunki konta, nie oświadczenie pełnoletności.
- Profile zachowują stabilny users.id. Sesje mają trwałą generację i revocation;
  drugie logowanie unieważnia poprzednie. PWA boot używa status/bootstrap/shell.
- Bramy sesji, detention i Ghost Signal działają przed widokami. Nowa kontrola
  musi poprzedzać gameplay, pozostawiając działające usuwanie/reauth/logout.
- Usunięcie przez Identity wymaga świeżego potwierdzenia, retire usuwa zgody,
  metody i własne kopie danych. Zachowuje hashe tożsamości emerytowanych,
  username tombstone, historię świata i kopie odbiorców; nie obiecuje pełnego purge.
- `/privacy`, `/terms`: publiczne projekty PL/EN, 157-draft-1, noindex.
  13+ oraz zgoda opiekuna występują wyłącznie w legal_documents.py; historia
  w journal pozostaje historycznym zapisem, nie zasadą aktualnego produktu.
- Google: openid email, walidowany sub/email/email_verified. GitHub: read:user
  user:email, API /user i /user/emails, wybór verified primary. Discord:
  identify email, /users/@me. Steam: OpenID, SteamID, bez e-maila.
  Adaptery redukują odpowiedzi do identyfikatora/e-maila/statusu. Access/refresh
  tokeny nie są utrwalane. Chwilowe odpowiedzi mogą zawierać dodatkowe pola.
- Cleanup usuwa wygasłe intencje/tickety/grants/challenges oraz security events
  starsze niż 90 dni (dopiero przy wykonaniu cleanup). Proxy/access log i backup
  retention nie wynika z tego kodu. Nie deklarujemy ich okresów.

## Projekt rozszerzenia

Addytywne kolumny zgody: age_confirmed oraz age_statement_version; starym
wierszom nie przypisujemy potwierdzenia. Flaga CHAOS_ADULT_POLICY_ENABLED
domyślnie OFF do zatwierdzenia dokumentów i wdrożenia. Włączenie wymaga migracji.
Nowa wersja warunków i oświadczenia, dokładne typy/wersje API, atomowy zapis.
Istniejące konta: aktualne oświadczenie + warunki przed każdą ścieżką gameplayu.
Osobna trwała blokada wieku nie daje się zdjąć ponowną akceptacją; brak kasowania.
Nie zbieramy daty urodzenia, skanów ani adresu IP w rekordzie zgody.

## Źródła i decyzje

- https://developers.google.com/identity/protocols/oauth2/production-readiness/brand-verification
- https://developers.google.com/identity/protocols/oauth2/policies
- https://developers.google.com/terms/api-services-user-data-policy
- https://eur-lex.europa.eu/eli/reg/2016/679/oj

Google wymaga publicznej polityki powiązanej z domeną/ekranem zgody i opisem
działania aplikacji. Testy kodu nie oznaczają akceptacji Google ani prawnej.
Otwarte: adres operatora, odpłatność, retencja danych i kopii, proces reklamacji,
moderacja/odwołania, podwykonawcy/transfery, zakres produkcyjnych usług AI.
