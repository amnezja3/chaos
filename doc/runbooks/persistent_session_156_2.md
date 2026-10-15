# Sprint 156.2 — trwała sesja, przygotowanie wdrożenia

Stan: implementacja lokalna. Produkcja nie została zmieniona. Nowy start bez
formularza logowania należy do 156.3, instalacja PWA do 156.4. Nie włączać całego
Sprintu 156 na podstawie samego zakończenia 156.2.

## Kontrakt

- Nowe logowanie przy `CHAOS_PERSISTENT_SESSION_ENABLED=1` otrzymuje 30 dni idle
  i maksymalnie 90 dni od logowania. `CHAOS_SESSION_IDLE_DAYS` i
  `CHAOS_SESSION_ABSOLUTE_DAYS` mogą zmienić wartości nowych sesji; idle<=absolute.
- Jedno aktualne logowanie konta; odnowienie nie zmienia generation/ownership.
- Widoczny dokument odnawia sesję po prawdziwym pointerdown, touchstart lub
  keydown, najwyżej raz na 5 minut. Serwer niezależnie ogranicza zapis do 5 minut.
  Polling i ukryta karta nie odnawiają terminu. Bezwzględny deadline nie przesuwa się.
- POST `/api/session/activity`, `/logout` i `/api/profile/account` wymagają
  aktualnej generacji, osobnego tokenu `X-Chaos-CSRF` i zgodnego Origin/Host.
  HTTPS Origin obsługuje terminację TLS na reverse proxy bez ufania forwarded-host.
- GET logout to potwierdzenie bez revocation. Dotychczasowe trzy akcje terminala
  korzystają ze wspólnego logout POST. Błąd nie jest przedstawiany jako sukces.
- Zmiana/reset hasła przez guarded UserStore unieważnia aktywne sesje w tym samym
  commicie co hasło, po request precommit guard. Nieudana revocation wycofuje oba
  zapisy. Upgrade hasha podczas uwierzytelnienia pozostaje osobną istniejącą ścieżką.
  Zwykła zmiana profilu/email nie wylogowuje. Ręczny SQL omija kontrakt UserStore.
- Logout/recovery nie wysyłają usunięcia/nadpisania cookie. SID jest unieważniany
  na serwerze; nieaktualne cookie klienta nie daje autoryzacji. Recovery starej
  karty nie usuwa aktualnego logowania. Komunikaty mają PL/EN.
- Cookie: Secure, HttpOnly, SameSite=Lax; termin cookie i pliku ograniczony
  terminem backendu. Wymagany HTTPS oraz trwały sekret `CHAOS_SECRET_KEY`.
  Nie zmieniać sekretu podczas zwykłego restartu/deployu.
- Storage: istniejący filesystem Flask-Session, `SESSION_FILE_THRESHOLD=0`,
  aby liczba aktywnych graczy nie wywoływała losowego usuwania ważnych sesji.
  Sprzątanie wygasłych plików wykonuje narzędzie poniżej. Katalog ma być trwały,
  prywatny dla użytkownika usługi i zawarty w procedurze backupu.

## Komenda → spodziewany wynik

Poniższe komendy są przygotowaniem operatora, nie zostały wykonane na serwerze.
Przed apply wymagany spójny backup bazy i magazynu sesji po zatrzymaniu procesów,
które je zapisują. Nie tworzymy drugiej instancji gry. Flaga pozostaje OFF.

```bash
.venv/bin/python tools/session_156_maintenance.py migrate --db data/game.sqlite3
```

→ `ok:true`, `status:dry_run`, `integrity:ok`, `foreign_keys:ok`,
`original_data_unchanged:true`. `added_columns` zawiera pięć pól TTL albo pustą
listę, jeśli aktualny runtime już dodał je idempotentnie. Dry-run wykonuje DDL
wyłącznie na schemacie w RAM; nie zmienia bazy produkcyjnej ani danych legacy.

Po backupie, w kontrolowanym oknie wdrożenia:

```bash
.venv/bin/python tools/session_156_maintenance.py migrate --db data/game.sqlite3 --apply
```

→ `status:applied`, `ok:true`, integralność i wszystkie oryginalne pola/rekordy
bez zmian. Powtórzenie jest idempotentne. Nie przyznaje starym sesjom nowego TTL.

Podaj rzeczywistą wartość `CHAOS_SESSION_FILE_DIR`; poniżej domyślna ścieżka:

```bash
.venv/bin/python tools/session_156_maintenance.py cleanup --session-dir data/flask_session
```

→ `status:dry_run`, `removed:0`, liczby `checked`, `expired`, `skipped`.
Narzędzie czyta tylko czterobajtowy timestamp CacheLib, bez deserializacji pickle,
bez rekursji, bez symlinków i bez usuwania pliku zarządzającego z expiry=0.
Domyślnie sprawdza najwyżej 1000 wpisów; `--limit` dopuszcza maksymalnie 10000.
Raport dotyczy wyłącznie sprawdzonej partii, nie potwierdza czystości całego katalogu.

Wyłącznie gdy **wszystkie procesy zapisujące ten katalog są zatrzymane**:

```bash
.venv/bin/python tools/session_156_maintenance.py cleanup --session-dir data/flask_session --apply --writers-stopped
```

→ `status:applied`, usunięte tylko rozpoznane wygasłe pliki. Brak flagi
`--writers-stopped` oznacza odmowę. To deklaracja operatora, nie automatyczny test
PM2. Bez zatrzymania writerów istnieje wyścig z atomową podmianą odnowionego pliku.
Przy dużym katalogu dobierz limit i sprawdź raport; nie usuwaj całego katalogu sesji.
Licznik CacheLib nie jest przeliczany; przy threshold=0 nie steruje usuwaniem.

## Wycofanie

Wyłączyć wydawanie: `CHAOS_PERSISTENT_SESSION_ENABLED=0` i restart z aktualizacją
środowiska według konfiguracji PM2. Zachować nowy guard TTL i addytywne kolumny.
Już wydane sesje dalej podlegają expiry, revocation i Secure cookie. Nie przywracać
starego snapshotu ownership ani całego magazynu po nowych loginach/transakcjach.
Nie cofać kodu do wersji ignorującej TTL bez kontrolowanego unieważnienia tych sesji.

## Dowody lokalne

- Backend: 90 testów PASS (61,707 s): TTL, restart storage, legacy, CSRF, GET/POST logout,
  recovery A/B, credentials i rollback, precommit, migracja, cleanup oraz katalogi PL/EN.
- Node: `test_persistent_session_activity.js` i `test_session_generation_isolation.js` PASS.
  Symulowane inputy i ukryty dokument nie odnawiają; trusted input jest throttlowany.
- Chrome/Playwright: `tools/session_156_browser_smoke.py`, rzeczywisty Flask,
  osobna tymczasowa baza i katalog sesji, desktop PL 1280×800 i mobile EN 390×844.
  Kliknięcie potwierdzone zmianą `last_activity_at` w DB, brak CSRF → 403,
  logout POST → formularz logowania, brak pageerror. Przeglądarka zamknięta.
  Playwright MCP nie był dostępny; użyto biblioteki Playwright z katalogu tymczasowego.
  To test UI sesji, nie potwierdzenie instalacji PWA lub zachowania iOS.
