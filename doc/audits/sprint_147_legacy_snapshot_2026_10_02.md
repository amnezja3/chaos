# Sprint 147 — audyt lokalnej kopii produkcyjnej

Data: 2 X 2026. Źródło: dostarczony `game-147-local.sqlite3`.
Rozmiar: 1 804 005 376 bajtów; 37 kont; SQLite `quick_check`: `ok`.
SHA-256 źródła: `416b41e6b1ee2f0588c2955dcdd15f2a632f71f9d52ac0fd138205a6ad2b63a7`.

## Import historycznych publikacji — PASS na kopii

Kanoniczny `app_config` zawiera 50 aplikacji, w tym 13 historycznych
publikacji kreatorskich bez znacznika GhostLaba. Jawna lista autorów została
wyznaczona z tych rekordów. `creator_migration.plan` zakwalifikował wszystkie
13 do importu, bez niejednoznaczności nazw, identyfikatorów i cen.

Na osobnej kopii wykonano `apply`: 13 wyników `migrated`. Powtórzenie dało
13 wyników `already_migrated`. Każdy zapisany `app_json` porównano z pełnym
snapshotem źródłowym: identyczny, łącznie z ID, ceną, opcjami i efektami.
Odciski zawartości całych tabel `users`, `player_apps` i `json_resources`
przed i po imporcie są identyczne. Końcowy `quick_check`: `ok`.

Nie wykonano importu na serwerze ani konwersji starych projektów do nowego
edytowalnego kontraktu. Kopie zainstalowane u graczy pozostają bez zmian.

## Rzeczywisty XMapper — PASS w dwóch testach HTTP

Użyto pełnej definicji aplikacji z dostarczonego katalogu, bez podmiany ceny,
identyfikatora ani efektów. Cena produktu to 758 HC, a opcja `Hack All`
ma cenę 500 HC i 28 wpisów efektu wyłączających zabezpieczenia.

W osobnym katalogu roboczym, na fikcyjnych kontach testowych, wykonano przez
klient HTTP Flask dwa scenariusze `/gonna-win`:

- przejęcie zwykłego celu;
- przejęcie celu innego gracza w trybie `territory_contest`.

Oba zwróciły HTTP 200 i `success`, zapisały przejęty cel i wyczyściły aktywny
cel. Drugi usunął przejęty punkt z własności poprzedniego właściciela.
Aktywna blokada ciężkich metod profilu i SQL wykrywającego `profile_json`
nie zgłosiła naruszeń. Połączenia sieciowe były zablokowane.
Wynik: 2/2 testy PASS. To testy backendu; potwierdzenie uruchamiania
z pulpitu, terminala i pickera pochodzi od użytkownika.

Po zakończeniu testów Windows zgłosił błąd usunięcia pustego katalogu
tymczasowego, który pozostawał bieżącym katalogiem procesu. Nie dotyczył
asercji testowych, bazy źródłowej ani działania aplikacji.

## Granice tego potwierdzenia

Audyt zamyka lokalną weryfikację dokładności importu oraz dwóch ścieżek
rzeczywistego XMappera. Nie potwierdza rozliczenia płatnej opcji, wszystkich
recept kreatorskich, generowania ich plików ani zakupu i aktualizacji wersji.
Te bramki sprintu 147 pozostają otwarte. Flaga nowego kreatora pozostaje
wyłączona; wynik audytu nie jest zgodą na jej włączenie.
