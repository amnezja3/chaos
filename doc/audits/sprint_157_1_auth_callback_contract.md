# 157.1 — audyt istniejącego uwierzytelniania i kontrakt callbacków

16 X 2026. Przegląd statyczny aktualnego kodu i planu 157. Bez implementacji,
migracji, rejestracji aplikacji u dostawców i zmian na serwerze. Nie jest to
pełny odbiór bezpieczeństwa 157.1 ani test rzeczywistych callbacków.

## Adresy do rejestracji aplikacji — ustalony kontrakt produkcyjny

| Dostawca | Callback / redirect URI |
| --- | --- |
| Google | `https://chaos.re/auth/google/callback` |
| Discord | `https://chaos.re/auth/discord/callback` |
| GitHub | `https://chaos.re/auth/github/callback` |

Dokładnie HTTPS, host bez www, bez końcowego ukośnika, bez query i fragmentu.
Adres strony aplikacji: `https://chaos.re/`. Google: klient typu Web application,
pole Authorized redirect URIs. Discord: OAuth2 / Redirects. GitHub: OAuth App,
pole Authorization callback URL. To adresy przyszłych backendowych tras Flask,
nie `/launch`, nie strona logowania i nie endpointy JS.

Ścieżki wynikają ze wspólnej przestrzeni `/auth/<provider>` opisanej już w 157;
obecny Flask obsługuje aplikację od korzenia hosta i nie ma kolidujących tras
`/auth/…`. Jest to decyzja kontraktowa dla implementacji, nie opis istniejących
działających endpointów. Konfiguracja produkcyjnego reverse proxy nie była
sprawdzana w tym audycie; przy wdrożeniu trzeba sprawdzić przekazanie `/auth/*`
do Flask. Backend powinien używać stałego zaufanego publicznego originu,
zamiast budować redirect URI z niezweryfikowanego nagłówka Host.

Steam pozostaje w pierwszej fazie 157 jako odrębny adapter OpenID 2.0.
Nie należy konfigurować go jako aplikacji OAuth na podstawie tabeli powyżej.

## Stan obecny

| Obszar | Ustalenia z kodu |
| --- | --- |
| Logowanie | `run.py:index`, POST `/`: username/hasło, `authenticate_user`, następnie `begin_authenticated_session`; z aktywnym LaunchController odpowiedź uruchamia istniejącą ścieżkę launch. GET `/` kieruje do `/launch`, a `/?login=1` pokazuje bramę. |
| Rejestracja | GET `/register`, POST `/api/register-check`, POST `/api/register-finalize`. Sześć kroków; backend waliduje username, hasło, frakcję/rolę, nick, e-mail i inicjuje profil. Callback nie może omijać tego kontraktu. |
| Konta | `database.py`: `users.id`, unikalny `username`, `password`, `salt`, `profile_json`, znaczniki czasu i rozszerzenia rewizji/integralności. Gameplay korzysta również z username. Nie zmieniamy istniejących identyfikatorów ani profili. |
| Hasła | `hash_password`: PBKDF2-HMAC-SHA256, 240000 iteracji, losowa sól `secrets.token_hex(16)`, hash z parametrami. `verify_password` używa porównania stałoczasowego. Istnieje zgodność z historycznymi hasłami niehashowanymi oraz upgrade przy uwierzytelnieniu; nie badano danych produkcyjnych. |
| Sesja | Flask-Session filesystem; cookie HttpOnly/SameSite=Lax, Secure wymuszane dla trwałych sesji. Stabilny sekret wymagany po włączeniu trwałości. Domyślny kontrakt 30 dni idle / 90 absolute. SID rotuje przy udanym logowaniu, generacja/lineage/ownership pozostają serwerowe. |
| Wiele urządzeń | `SessionGenerationStore.activate` zastępuje poprzednie logowanie konta. Drugie urządzenie unieważnia poprzednie, nie tworzy równoległej aktywnej sesji. PWA może mieć odrębny magazyn cookies. |
| Wylogowanie | GET `/logout` wyświetla stronę; POST `/logout` weryfikuje CSRF/generację i unieważnia sesję. `/session/recover` obsługuje odzyskanie widoku, nie przyznaje tożsamości. |
| Inne trasy sesji | `/api/session/status`, `/api/session/bootstrap`, `/api/session/activity`, `/api/desktop-shell`; obecne kontrole originu, CSRF i generacji nie są callbackami OAuth. |
| OAuth obecnie | Brak adapterów i callbacków; przyciski w bramie/onboardingu są disabled. |

## Warunki bezpiecznej integracji bez naruszania kont

1. Dodatkowa tabela tożsamości z unikalną parą provider + subject i odwołaniem
   do istniejącego konta. Nigdy automatyczne scalenie po e-mailu/nicku.
2. Istniejące konto podłącza dostawcę po uwierzytelnieniu i świadomym potwierdzeniu.
   Nowy użytkownik kończy serwerową intencję rejestracji przed utworzeniem profilu.
3. Konto bez lokalnego hasła musi mieć jawny stan i odmowę lokalnej autoryzacji.
   Obecne legacy porównanie dopuszcza równość dwóch pustych wartości, więc samo
   zapisanie pustego `password` dla SSO byłoby nieprawidłowe. To wymaganie 157.2,
   nie stwierdzenie istnienia takich kont na produkcji.
4. Udany zewnętrzny login wywołuje wspólne `begin_authenticated_session`;
   podłączenie dostawcy nie zmienia konta. Brak alternatywnego systemu sesji.
5. Callbacki potrzebują osobnych jednorazowych intencji/state, walidacji protokołu
   i replay protection. Włączyć je świadomie do wyjątków obecnych guardów
   `SESSION_GENERATION_PUBLIC_ENDPOINTS` i Ghost Signal; nie wymagać nagłówka
   generacji z przekierowania dostawcy. Dla link/reauth potwierdzić zgodność
   pierwotnej sesji/konta przed zapisem; publiczna trasa nie oznacza autoryzacji.
6. Nie przenosić cookies/tokenów w URL do PWA. Powrót do innego magazynu cookies
   wymaga osobnego przetestowania w 157, bez obchodzenia powiązania state.

## Dokumentacja dostawców sprawdzona podczas audytu

- [Google — web server OAuth](https://developers.google.com/identity/protocols/oauth2/web-server):
  redirect_uri musi dokładnie odpowiadać zarejestrowanemu URI.
- [Discord — OAuth2](https://discord.com/developers/docs/topics/oauth2):
  redirect_uri i state w przepływie authorization code.
- [GitHub — tworzenie OAuth App](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app):
  pola Homepage URL i Authorization callback URL.
