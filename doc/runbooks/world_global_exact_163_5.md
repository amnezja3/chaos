# 163.5.1 — przygotowanie odbioru globalnego exact local-read

Status: instrukcja pierwszego pakietu; nie jest poleceniem natychmiastowej aktywacji.
Regionalne POI i sąsiednie zapytania pozostają kolejnym etapem 163.5.2.

## Lokalnie i na VPS bez API

Z katalogu projektu na VPS, po pobraniu ustalonego commita:

```bash
PYTHONPATH=tests .venv/bin/python -m unittest \
  test_world_global_access test_world_shadow test_world_pilot_scope \
  test_world_routing test_world_read test_world_maplark_pilot test_poi_infrastructure
```

Testy używają tymczasowych baz i mockowanego transportu. Nie uruchamiać ich
z produkcyjnymi flagami odziedziczonymi przez powłokę. Testy niezależnych instancji
serwisu nie zastępują odbioru oddzielnych procesów Gunicorna na VPS.

## Konfiguracja i zgodność

Schemat nie zmienia się. Wymagany przygotowany wcześniej canonical world v2,
registry oraz jawne `world_storage` obok uprawnień live/cache źródła.
Pakiet nie przyznaje praw, nie włącza providerów i nie zmienia budżetów.

| Ustawienie w ecosystem.web.config.js | Znaczenie |
| --- | --- |
| WORLD_ACCESS_MODE=pilot | Dotychczasowy konkretny użytkownik/środek/promień/okno |
| WORLD_ACCESS_MODE=global | Brak ograniczenia do konta/punktu pilota; pozostałe kontrole nadal wymagane |
| WORLD_ACCESS_MODE=off | Brak odczytu/zapisu canonical przez nową integrację skanera |
| WORLD_INGEST_ENABLED=1 | Zapis nowych zgodnych odpowiedzi |
| WORLD_REPOSITORY_ENABLED=1 | Odczyt zgodnych snapshotów |
| SCAN_NETWORK_PAUSED=1 | Bez nowych wywołań dostawców przez skaner; cache/world dozwolone |

W tabeli pominięto wspólny prefiks `CHAOS_POI_`. Nie zmieniać wartości pilota,
aby imitować tryb globalny. Zostawić routing w aktualnym zatwierdzonym trybie;
nowa ścieżka Overpass canonical dotyczy aktywnego routera.
Pauza skanera nie zatrzymuje workera kolektora i nie cofa już rozpoczętych żądań.
Provider disabled lub cofnięte prawa nadal blokują odczyt, zgodnie z dotychczasowym
zachowaniem; do wstrzymania sieci użyć osobnej pauzy, nie zmieniać decyzji źródła.

## Zbiorczy odbiór po uzgodnieniu wdrożenia

1. Zrobić backup SQLite istniejącym narzędziem projektu, zachować commit i
   niesekretne flagi baseline; potwierdzić integralność i aktualne uprawnienia.
2. W ecosystemie ustawić global + ingest=1 + read=0, pause=0. Reload web
   istniejącą procedurą projektu, zachowując aktywny profil routing; poczekać na HTTP 200.
3. Jeden kontrolowany skan konta A w ustalonym punkcie. Potwierdzić snapshot
   exact i jego czasy, nie tylko obecność markerów albo zwykłego cache.
4. Włączyć read. Istniejącym narzędziem pilota inspect/evict, po sprawdzeniu jego
   planu dla tego punktu i rewizji, usunąć wyłącznie cache tego zapytania.
   Nie czyścić całego cache, księgi, snapshotów ani danych gry.
5. Powtórzyć dokładnie ten sam skan kontem B: `source=world`, poprawny wynik,
   zero nowych prób skanera i brak naliczenia za ten skan. Kolektor może niezależnie
   zmieniać globalny licznik — porównywać operacje/źródła, nie samą sumę konta.
6. Restart web, ten sam skan ponownie przed końcem świeżości; potwierdzić inny PID.
   Opcjonalną pauzę sieci skanera stosować tylko w uzgodnionym krótkim oknie,
   ponieważ inne lokalizacje graczy mogą wtedy nie mieć wyniku.
7. Wygaśnięcie, błędy dysku, niezgodne rewizje, brak uprawnień i częściowe dane
   sprawdza pakiet izolowany. Nie uszkadzać produkcyjnych danych do testu.
8. Potwierdzić skan/hakowanie/terytoria na starym i nowym koncie; zapisać wyniki
   z wersją kodu i aktywnymi flagami. Dopiero po odbiorze `pm2 save`.

Overpass powtarza ten scenariusz wyłącznie wtedy, gdy ma zatwierdzony normal_scan
oraz world_storage. Obecny odbiór VK dla tła nie jest takim uprawnieniem.
Brak zatwierdzenia live Overpass nie blokuje wykonania lokalnych testów adaptera.

## Rollback

Przywrócić zapisane flagi baseline w ecosystemie; ingest/read=0, access=pilot,
pause=0, zachować dotychczasową konfigurację skanera/routingu. Reload i HTTP 200.
Nie usuwać snapshotów ani rozliczeń. Samo przywrócenie kodu bez zmiany aktywnych
flag PM2 nie jest pełnym rollbackiem konfiguracji. Nie przywracać starej kopii
bazy nad nowymi rozliczeniami bez osobnego planu odtworzenia.
