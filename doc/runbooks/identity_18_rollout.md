# CHAOS 18+ — przygotowanie i wdrożenie

Stan: implementacja lokalna. Nie uruchomiono na chaos.re. Dokumenty są nadal
`157-18-draft-2`. Sama flaga nie nadaje dokumentom statusu zatwierdzonego.

## Warunki przed uruchomieniem

Operator zatwierdza pełne PL/EN `/terms` i `/privacy`, uzupełnia adres, odpłatność,
retencję/backupy, listę podwykonawców i transferów, procedury kontaktu,
reklamacji/moderacji/odwołań oraz faktyczny zakres AI/analityki na produkcji.
Przy finalizacji usunąć sekcje otwarte i baner projektu, nadać dokumentom wersję
1.0 oraz dopasować `identity_gateway/adult_policy.py:TERMS_VERSION` do rzeczywiście
zaakceptowanej wersji. Oświadczenie wieku ma osobną wersję `18-v1`.
Nie zmieniać treści wersji już zaakceptowanej bez nadania nowej wersji.
Aktualny identyfikator techniczny do testów: `157-18-v1`.

Obecny DRAFT ma noindex. Po zatwierdzeniu finalnych dokumentów przejrzeć też
robots/meta i nagłówki w `run.py` i `templates/legal_document.html`.
Sprawdzić publiczne strony bez sesji oraz zgodność nazwy CHAOS, domeny i URL
polityki w Google Cloud Branding. Nie wysyłać projektu jako finalnej polityki.

## Przygotowanie kodu i bazy, flaga OFF

Przed wdrożeniem: przegląd diff, zatwierdzony commit, testy. `git pull --ff-only`.
Nie wklejać sekretów do raportu. Zapisać bieżący commit i stan PM2, tak jak w 157.

```bash
cd ~/app/chaos
umask 077
export ADULT_BACKUP="$HOME/chaos-backups/157-18-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$ADULT_BACKUP"
git rev-parse HEAD > "$ADULT_BACKUP/commit"
pm2 jlist > "$ADULT_BACKUP/pm2-before.json"
.venv/bin/python tools/identity_157_migrate.py --db data/game.sqlite3
```

Oczekiwane: dry_run, integralność/FK OK, oryginalne dane niezmienione.
Migracja dodaje tylko `identity_consents.age_confirmed` (domyślnie 0),
`age_statement_version` (NULL) i `identity_account_security.age_restricted` (0).
Nie podnosi dawnych zgód do 18+, nie zmienia User ID, postępów ani sesji.

Krótka przerwa na spójny backup i migrację wszystkich piszących procesów CHAOS:

```bash
pm2 stop chaos chaos-territory-worker chaos-ollama-worker chaos-narrative-publisher
.venv/bin/python tools/identity_157_migrate.py --db data/game.sqlite3 --backup "$ADULT_BACKUP/game.sqlite3"
tar -czf "$ADULT_BACKUP/flask-session.tar.gz" -C data flask_session
.venv/bin/python tools/identity_157_migrate.py --db data/game.sqlite3 --apply
.venv/bin/python tools/identity_157_migrate.py --db data/game.sqlite3 --check --baseline "$ADULT_BACKUP/game.baseline.json"
.venv/bin/python tools/identity_157_migrate.py --db data/game.sqlite3 --apply
```

Oczekiwane: migrated, baseline_matches=true, następnie already_migrated.
Jeśli dowolny krok zawiedzie, nie włączać flagi. Przywrócić procesy do zapisanego
stanu z polityką OFF; nie wykonywać automatycznego restore bazy.

```bash
CHAOS_ADULT_POLICY_ENABLED=0 pm2 restart chaos --update-env
pm2 restart chaos-territory-worker chaos-ollama-worker chaos-narrative-publisher
```

Restartować tylko procesy, które wcześniej działały; nazwy potwierdzić w PM2.
Wdrożenie kodu i migracji z OFF zachowuje wcześniejsze ścieżki rejestracji.

## Aktywacja — dopiero po decyzjach operatora i zatwierdzeniu dokumentów

Utrwalić `CHAOS_ADULT_POLICY_ENABLED=1` w rzeczywistej konfiguracji startowej
PM2/plikach środowiska. Nie dopisywać sekretów do repozytorium. Sam `--update-env`
może zostać nadpisany późniejszym uruchomieniem z ecosystem config.

```bash
CHAOS_ADULT_POLICY_ENABLED=1 pm2 restart chaos --update-env
```

Nie trzeba zatrzymywać świata i workerów na czas odbioru oświadczeń.
Użytkownicy bez aktualnej zgody otrzymują `/account/terms`; API gry zwraca 403
`adult_acceptance_required`. Znany brak pełnoletności: `age_restricted`.
Brak migracji przy ON blokuje żądania; nie przechodzi do trybu bez ochrony.

Odbiór na kontach testowych: rejestracja local i czterej dostawcy; brak jednego
checkboxa; stare konto i już otwarta gra/PWA; ponowne logowanie i drugi telefon;
odmowa, wylogowanie i usunięcie testowego konta; publiczne PL/EN dokumenty.
Nie uznawać symulacji OAuth lub odtworzenia cookies w testach za odbiór fizycznej PWA.

## Informacja o niepełnoletnim użytkowniku

Samodzielne „Mam mniej niż 18 lat” zapisuje blokadę bez kasowania konta.
Operator może użyć CLI na serwerze, po sprawdzeniu właściwego loginu:

```bash
.venv/bin/python tools/identity_18_access.py --db data/game.sqlite3 --username LOGIN --confirm-username LOGIN restrict
```

Po rozpatrzeniu pomyłki analogiczne `release` zdejmuje blokadę. Nie tworzy zgody,
nie usuwa dotychczasowej historii akceptacji. Jeśli nie było aktualnej zgody,
użytkownik nadal musi ją świadomie złożyć. Blokady są sprawdzane w każdym żądaniu
do gry, również w aktywnej sesji. Operacje mają zapis w security events.

## Wycofanie

Przed publiczną aktywacją można pozostawić flagę OFF; addytywne kolumny są
kompatybilne ze ścieżką 157-v1 w tym nowym kodzie. Nie cofać bez sprawdzenia
do starszego commita: poprzedni finał OAuth używał `INSERT INTO identity_consents
VALUES (?,?,?)` i po dodaniu kolumn wymaga poprawki na jawne nazwy kolumn.
Rollback kodu musi zachować tę poprawkę. Po ogłoszeniu obowiązujących zasad 18+
nie wyłączać ochrony jako zwykłego obejścia błędu — ograniczyć dostęp do gry
na czas naprawy. Nie cofać aktywnej bazy świata do backupu sprzed rozgrywki.
Nie usuwać zgód ani blokad w ramach rollbacku kodu.

## Granice rozwiązania

Oświadczenie nie dowodzi rzeczywistego wieku; nie ma dat urodzenia/skanów.
Zmiana dotyczy dostępu użytkowników, nie zatrzymuje autonomicznych zdarzeń świata.
Użytkownik, który kłamie w deklaracji, nie jest automatycznie wykrywany.
Nie ma automatycznej prawnej walidacji dokumentów ani gwarancji akceptacji Google.
