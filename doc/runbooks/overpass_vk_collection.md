# VK: uruchomienie kolektora geometrii

Stan 2026-10-26: operator przekazał wynik `probe_completed`, `tested_ok`, `enabled:false`.
To dowód dostępności małego zapytania, nie jeszcze odbiór pobrania geometrii.

Źródło decyzji: https://wiki.openstreetmap.org/wiki/Overpass_API — wpis VK Maps
deklaruje wykorzystanie w dowolnym projekcie bez obecnie ogłoszonych limitów.
Jest to publiczna deklaracja w wykazie OSM, nie indywidualne potwierdzenie VK.
Dane OSM wymagają zachowania informacji o źródle i licencji ODbL.

Zakres: roads, waterways, inland_water, coastline; tylko obserwacje kolektora.
VK przed dotychczasowymi źródłami tła. Bez zmian routingu skanera graczy i flag wieku.
120 prób/dobę, 3720/31 dni, istniejące tempo jednego żądania/cykl i backoff.
Retencja 7 dni. Termin polityki regularnej nie jest odnawiany.
`UNKNOWN` pozostaje poprawnym wynikiem obserwacji; nie oznacza pełnego pokrycia regionu.

## Wdrożenie

```bash
cd ~/app/chaos && git pull --ff-only &&
.venv/bin/python -m unittest discover -s tests -p 'test_overpass_collection_enable.py' &&
.venv/bin/python -m unittest discover -s tests -p 'test_world_overpass_collection.py' &&
.venv/bin/python tools/overpass_collection_enable.py
```

Po wyniku `plan`:

```bash
umask 077
VK_BACKUP="$HOME/chaos-backups/vk-collection-$(date -u +%Y%m%dT%H%M%SZ)/poi_cache.sqlite3"
.venv/bin/python tools/overpass_collection_enable.py --apply --backup "$VK_BACKUP"
```

Aktywny kolektor odczytuje rejestr i routing przy kolejnych cyklach. Nie potrzeba
restartu web ani nowego klucza. Plan i aktywacja same nie wykonują HTTP;
działający worker może rozpocząć pobieranie po aktywacji.

Po kilku cyklach:

```bash
.venv/bin/python tools/world_collection_monitor.py
pm2 logs chaos-world-discovery-worker --lines 25 --nostream
```

Odbiór: `provider:overpass-vk`, `status:committed`, snapshot geometrii i naliczenie
próby. `waiting` lub `idle` bez żądania nie potwierdzają pobrania. Przy świeżych
obserwacjach nie wymuszamy odświeżenia ani nie kasujemy receiptów tylko dla testu.
Przy błędzie zapisujemy wynik; backoff i przejście na inne źródło pozostają aktywne.

## Wyłączenie

W panelu POI wyłącz `overpass-vk`. Kolektor przestanie wybierać źródło; pozostałe
źródła nadal działają. Nie przywracaj całej kopii bazy przy aktywnym kolektorze,
ponieważ cofnęłoby to również nowsze rozliczenia i obserwacje.

## Walidacja lokalna

Testy aktywacji: brak mutacji w planie, blokada nieudanego probe i wygasłej
polityki, ochrona istniejącej kopii, zachowanie routingu live i kosztów przy
powtórzeniu. Odbiór rzeczywistego cyklu VK pozostaje do wykonania na VPS.
