# Sprint 144 — implementacja i wdrożenie GhostLaba

24 IX 2026. Zmiany lokalne; brak wdrożenia i odbioru przeglądarkowego na serwerze.
Zakres: [plan 144](../sprints/sprint_144_ghostlab_publication_integrity.md).
Runtime narzędzi pozostaje `pending_custom_runtime` (Sprinty 145–146).

## Zmieniona ścieżka

- `ghostlab_store.py`: osobne projekty, niezmienne buildy, tożsamości publikacji,
  receipts utworzenia projektu, mapowanie legacy ID i statusy migracji.
- `ghostlab_policy.py`: zamknięty schemat pięciu szablonów, skończone liczby,
  całkowite limity/cooldown, serwerowe reguły ochrony, brak dodatkowych pól.
- `ghostlab_routes.py`: stare URL zachowane, bez sync/get/save ciężkiego profilu.
- `database.py`: mały odczyt nick/respekt; poziom z capability projection,
  saldo z walletu. Brak desktop/security hydration dla wyceny.
- Publish: BEGIN IMMEDIATE, porównanie rewizji/hash/artefaktu, kontrola autora,
  zapis katalogu, canonical publikacji, znacznika buildu i projektu w jednej transakcji.
- JsonResourceStore chroni canonical publikacje przed nadpisaniem starszym snapshotem
  katalogu z innych writerów. Edycja takiej aplikacji odbywa się przez GhostLab,
  nie przez podmianę jej rekordu w app_config.
- GUI: rewizja i build, niezapisane zmiany, wymagany Save Draft przed Compile,
  Compile przed Publisher, wycofanie sprzedaży, pola policy tylko do odczytu.
  Publikacja nie wywołuje pełnego odświeżenia pulpitu.

Konfiguracja w `config.py`: 100 aktywnych projektów na konto, 200 buildów na projekt,
20 ostatnich pozycji historii w odpowiedzi UI, request do 16 KiB. Pełne artefakty
zachowane w store; po osiągnięciu limitu nie usuwamy automatycznie kupionych wersji.
Nie dodano zmiennych środowiskowych ani nowego procesu PM2.

## Wdrożenie i migracja

1. Przygotować spójną kopię SQLite przez istniejącą procedurę backupu (uwzględniając WAL).
   Dry-run wykonać najpierw na kopii. Nie kopiować samego aktywnego pliku DB z pominięciem WAL.
2. Dostarczyć komplet kodu 144. Przy pierwszej inicjalizacji store istniejące konta
   otrzymują stan `required`. Endpoint GhostLaba zwróci `ghostlab_migration_required`
   do czasu migracji konta; nie pokaże pustej listy udającej brak starych projektów.
   Konta utworzone po inicjalizacji rozpoczynają nowy canonical workspace.
3. Uruchomić nowe procesy obsługujące web, aby stary endpoint nie zapisywał już legacy
   projektów. W tej fazie GhostLab starych kont jest świadomie niedostępny; inne
   funkcje gry nie są blokowane tym znacznikiem.
4. Dla jawnie wybranych kont wykonać dry-run, np. z katalogu aplikacji:

```bash
.venv/bin/python tools/migrate_ghostlab_projects.py --db data/game.sqlite3 --user main --user robot
```

5. Sprawdzić `would_migrate`, mapowanie projektów i app ID, `errors`. Brak projektów
   też wymaga zatwierdzenia pustej migracji istniejącego konta. `blocked` wymaga
   wyjaśnienia danych; narzędzie nie przejmuje publikacji innego autora.
6. Ten sam zestaw kont zastosować:

```bash
.venv/bin/python tools/migrate_ghostlab_projects.py --db data/game.sqlite3 --user main --user robot --apply
```

Powtarzalne `--user`, maksymalnie 100 kont w wywołaniu. Każde konto ma osobną
transakcję i receipt ze źródłowym hashem. Ponowienie daje `already_migrated`;
zmienione legacy po migracji powoduje blokadę, nie nadpisanie canonical projektów.
Narzędzie czyta wyłącznie wybrane stare poddrzewo projektów i metadane rekordu;
nie zapisuje `users.profile_json`, inventory, zakupów ani sald.

Istniejące app ID pozostają bez zmian po potwierdzeniu właściciela i source_project_id.
Nowe project ID są globalnie unikalne, z tabelą mapowania legacy. Stare buildy są
archiwalnym dowodem w ghostlab_meta, nie aktualnym artefaktem do publikacji.
Projekt po migracji wymaga Compile; istniejący produkt i zakupione kopie pozostają.

## Semantyka wersji i wycofania

- Zmiana nazwy lub blueprintu zwiększa rewizję i unieważnia możliwość publikowania
  starego artefaktu. Build niezmienny; ponowienie compile tej samej rewizji nie
  tworzy duplikatu. Publish wymaga jawnego artifact_id i rewizji.
- Projekt/app ID nie zależy od slugu ani numeru buildu. Podobny slug różnych autorów
  nie koliduje; nazwa katalogowa nadal musi być unikalna, z czytelną odmową.
- Aktualizacja produktu zmienia ofertę katalogową. Istniejących kopii inventory
  nie podmieniamy w tle; wykonanie wersji zakupionej jest zakresem 145–146.
- Wycofanie ustawia `published=false` i blokuje nowe instalacje z katalogu, również
  bezpośredni POST po ID. Nie usuwa istniejących instalacji ani buildów.
- Można usuwać szkice. Opublikowane projekty pozostają archiwum, także po wycofaniu.
  Powtórna publikacja aktualnego buildu przywraca ofertę.

## Odbiór ręczny

1. Konto po migracji widzi swoje projekty. Drugie konto nie odczytuje i nie edytuje
   ich przez URL; stare niemigrowane konto otrzymuje jawny powód blokady.
2. Utworzyć szablon System Log Reader, Save Draft → Compile → Publisher. Sprawdzić
   ID produktu i komunikat `pending_custom_runtime`.
3. Zmienić log_limit bez zapisu: Publisher/Compile muszą odmówić. Zapisać: Publisher
   nadal odmawia do ponownego compile. Po publikacji sprawdzić nowy parametr w artefakcie.
4. W dwóch kartach zmienić ten sam projekt: starsza rewizja nie może nadpisać nowszej.
   Przy konflikcie wrócić do Projects i odświeżyć listę przed ponowną edycją.
5. Wycofać sprzedaż, potwierdzić ukrycie oferty i zachowanie istniejącej instalacji.
   Sprawdzić obie przeglądarkowe wielkości okna, eksport `.glab` i ponowne wejście.

## Testy i granice dowodów

Wynik lokalny: **17 testów Python PASS**, test funkcji formularza Node PASS,
`node --check static/js/terminal.js` PASS. Nie jest to jeszcze PASS odbioru produkcyjnego.

Pakiet `tests.test_ghostlab_publication`: kolizje tożsamości, CAS, idempotencja,
stare/niezapisane buildy, rollback po awarii, równoległa publikacja, starszy writer
katalogu, wycofanie, migracja i ścieżka HTTP zero-heavy. W teście HTTP pełne helpery
profilu i SQL zawierający `profile_json` kończą się błędem; odczyty autora/walletu
są izolowanymi zależnościami. Osobny test sprawdza realne projekcje autora.
To nie jest pomiar produkcyjnego ruchu ani test instalacji/wykonania z 145.

```bash
python -B tools/run_isolated_tests.py tests.test_ghostlab_publication tests.test_target_persistence.TargetPersistenceHelpersTest.test_ghostlab_published_tool_has_app_contract tests.test_target_persistence.TargetPersistenceHelpersTest.test_ghostlab_published_tool_preserves_requirements_and_googleplex_shape tests.test_app_catalog_cleanup
node tests/js/test_ghostlab_publication.js
node --check static/js/terminal.js
```

## Rollback

Nie uruchamiać starego GhostLaba zapisującego profile po rozpoczęciu nowej pracy.
W razie problemu zablokować tylko endpointy GhostLaba w warstwie wdrożeniowej,
zachować nowe tabele, katalog i receipts, naprawić lub wdrożyć zgodną wersję.
Nie kasować tabel i nie odtwarzać pełnego profilu jako źródła prawdy. Kopia DB
służy analizie/odtworzeniu kontrolowanego stanu, nie automatycznemu cofnięciu
wszystkich działań i HC graczy wykonanych po wdrożeniu.
