# Wdrożenie 159 — MASA / skaner

Pakiet lokalny gotowy. Nie wykonano zmiany flag produkcyjnych. Zależność: [158](poi_infrastructure_158.md). Brak migracji bazy graczy i nowego schematu cache. Utrwalić wybrane flagi w konfiguracji procesu.

## Publikacja kodu i regresja OFF

Po zatwierdzonym push:

```bash
git pull --ff-only &&
.venv/bin/python -m unittest discover -s tests -p 'test_poi*.py' -v &&
.venv/bin/python -m unittest discover -s tests -p 'test_ghostlab_scanner.py' -v &&
.venv/bin/python -m unittest discover -s tests -p 'test_ghost_i18n.py' -v
```

Oczekiwane 34 + 17 + 6 testów OK. Przy błędzie nie kontynuować restartu. Następnie:

```bash
CHAOS_POI_INFRASTRUCTURE_ENABLED=0 CHAOS_POI_MASA_UX_ENABLED=0 pm2 restart chaos --update-env
```

Sprawdzić Launch HTTP 200 i brak regresji normalnej gry. Nie zmieniać flag wieku/Identity/AI. Nie restartować pozostałych workerów bez potrzeby.

## Kontrolowane ON — osobny krok

Po ocenie baseline i uzgodnieniu kontrolowanego włączenia 158:

```bash
umask 077
.venv/bin/python tools/poi_cache.py --initialize &&
.venv/bin/python tools/poi_cache.py
```

Potwierdzić integralność cache, wspólną lokalną ścieżkę dla czterech workerów, prawa do katalogu oraz dostępne miejsce. Po zgodzie na włączenie:

```bash
CHAOS_POI_INFRASTRUCTURE_ENABLED=1 CHAOS_POI_MASA_UX_ENABLED=1 pm2 restart chaos --update-env
```

Ponownie otworzyć mapę, aby pobrać aktualne assety i katalogi. Status MASA powinien pojawić się w Chaos Logu w prawym dolnym rogu, bez osobnej belki. Aktywna blokada daje drugi poziom glitcha; po jej wygaśnięciu wpis i efekt MASA znikają bez komunikatu końcowego i bez automatycznej próby. Testować zwykły skan i GhostLab w PL/EN na desktop/mobile. Sprawdzić prawdziwe markery i układ kontrolek. W logach oczekiwać infrastructure=true. Świeży cache nie pokazuje MASA; kompletny stale daje sukces z informacją o ostatnim zapisie; rzeczywisty wspólny cooldown daje blokadę. Sam 502 przed otwarciem polityki może nadal dać zwykły błąd. Nie prowokować awarii ani obciążać publicznego Overpass seryjnymi próbami — te scenariusze są deterministycznie testowane lokalnie.

Przy wyłączonej infrastrukturze samo MASA_UX_ENABLED=1 niczego nie uruchamia. Obsługa cooldownu nie naprawia dostawcy: zimny cache podczas jego awarii nadal nie dostarczy POI. Obserwacja 158 i końcowy produkcyjny PASS pozostają osobnym odbiorem.

## Rollback

Sama prezentacja/kontrakt MASA:

```bash
CHAOS_POI_MASA_UX_ENABLED=0 pm2 restart chaos --update-env
```

Cały nowy tor POI:

```bash
CHAOS_POI_INFRASTRUCTURE_ENABLED=0 CHAOS_POI_MASA_UX_ENABLED=0 pm2 restart chaos --update-env
```

Utrwalić OFF i ponownie otworzyć mapę. Nie usuwać cache ani bazy gry. Powrót do legacy nie usuwa awarii publicznego dostawcy.
