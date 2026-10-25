# Lokalny pakiet zbierania świata — 2026-10-25

Zakres: kolekcja obserwacji i integracja istniejących modułów, bez włączania
geografii w gameplay i bez zmian produkcji.

## Wykonane

1. MapLark `sector-bbox-v1`: rzeczywisty prostokąt sektora zamiast domyślnego
   koła 300 m; stare pozwolenia i zadania zachowują poprzednią semantykę.
   Nowa tożsamość zadania, filtrowanie przy claim i jawny kontekst pobrania.
2. Poprawne niepełne wyniki sektora mogą być przechowywane jako PARTIAL,
   bez nadawania COMPLETE. Skaner live nadal odrzuca niepełne odpowiedzi.
3. Osobna retencja archiwum, bez przedłużania TTL odczytu skanera. Domyślna
   retencja bez zmian; przedłużenie wyłącznie jawne, ograniczone terminem
   przeglądu źródła i wymagające world_storage. Cleanup usuwa zależności FK.
4. Geoapify `geoapify-commercial-v1`: istniejący adapter/transport POST,
   wspólna kolejka i priorytet, własny ledger, zapis UNKNOWN, jedna strona
   100 wyników. Pusta obserwacja UNKNOWN nie staje się dowodem pustego regionu.
   Brak raportu kosztu pozostawia rezerwację, bez resetowania wcześniejszych
   niepewnych operacji. small_probe nie wystarcza do uruchomienia kolekcji.
5. Domyślna hierarchia routera live: dopuszczony Overpass → MapLark;
   najwyżej trzy źródła, osobne grupy operatorów, zachowane ręczne trasy,
   circuit breaker, deadline i cache. Geoapify nie udaje pełnego skanu POI.
6. Zbiorczy skrypt przygotowania VPS, kontrola collection_schema_ready,
   instrukcja migracji i rollbacku bez utraty ledgeru.

## Sprawdzenie

- World Discovery: 313 testów PASS / 204,661 s (po dodaniu Geoapify).
- Zmieniona hierarchia: osobno 13 testów PASS / 14,319 s po zmianie domyślnej
  kolejności i aktualizacji oczekiwania restore. Test potwierdza również
  fallback Overpass 502 → MapLark bez konfiguracji ręcznej trasy.
- POI: 92 testy PASS / 114,755 s po zmianach magazynu.
- Kolekcja: 75 testów discovery PASS / 63,074 s, obejmujące koszty,
  blokady, migrację, stare pozwolenia, Geoapify i zmianę uprawnień w locie.
- Playwright MCP, izolowany tools/poi_admin_fixture.py --world --routing:
  PL/EN, 1440/390 px, zmiana/zapis/przywrócenie hierarchii, brak overflow
  i pageErrors. Przeglądarka zamknięta, fixture zatrzymany.
- bash -n nowego skryptu i git diff --check PASS.

Testy korzystają z atrap dostawców i tymczasowych baz. Nie wykonano płatnych
zapytań, zmian VPS, migracji produkcji, włączenia flag ani push.
Sprawdzono publiczną dokumentację Geoapify Places:
https://apidocs.geoapify.com/docs/places/ — istniejący profil commercial,
filtr kołowy, paginacja oraz POST/x-api-key. Nie wyciągamy z tego równoważności
z całym kontraktem skanera ani potwierdzenia salda konta operatora.

## Granice i następny etap

Pakiet gotowy do wstępnego wdrożenia i przygotowania schematu; nie jest to
pełny PASS produkcyjny sprintów. Nadal wymagany jest odbiór ograniczonej
kolekcji na VPS z jawnymi sektorami, profilami, retencją i budżetami.
Geoapify wymaga dopuszczenia background_refresh/storage/world_storage;
wcześniejsze small_probe nie daje tych uprawnień.

Worker zbierania pełnej geometrii Overpass i produkt land_water nie zostały
dodane w tym pakiecie. Overpass obsługuje istniejący skan POI, MapLark cztery
profile geograficzne, Geoapify ograniczone obserwacje POI. Dalsze rozszerzenie
tych profili nie może być raportowane jako już działające.

Instrukcja: ../runbooks/world_collection_sector_upgrade.md.

## Korekta po pierwszym przebiegu VPS

Operator uruchomił `world_collection_acceptance.sh --prepare` na b9de0da.
Baseline PASS; 315 testów World zakończyło się jednym błędem:
`test_background_hierarchy_requires_layer_selection_and_rechecks_changes`,
`KeyError: priority`. Minimalny wpis dostawcy w fixture workera nie zawierał
pola porządkującego. Nowy domyślny routing odczytywał je bez wartości zastępczej.
To błąd finalnego pakietu, nie potwierdzona różnica działania Windows/Linux.
Wcześniejszy lokalny PASS nie stanowił pełnej regresji końcowego b9de0da.

Skrypt zakończył się w testach, przed dry-run, backupem i migracją produkcji.
Raport VPS: `/home/johndoe/chaos-world-acceptance-jYi0eY`.
Poprawka daje brakującemu priorytetowi najniższy ranking 100 i nie przelicza
domyślnych kandydatów podczas odczytu zapisanej trasy. Dodano regresję obu
przypadków; istniejący test workera nadal odtwarza pierwotny przypadek.
Nie zmieniono uprawnień źródeł ani flag aktywacji.

Końcowa regresja poprawki: 317 testów `test_world*.py` PASS / 196,548 s.
Kod nie był zmieniany w trakcie tego przebiegu. `git diff --check` PASS.
Na VPS powtórzyć dotychczasowy skrypt `world_collection_acceptance.sh --prepare`;
nie omijać jego testów ani nie uruchamiać workera przed przygotowaniem schematu.
