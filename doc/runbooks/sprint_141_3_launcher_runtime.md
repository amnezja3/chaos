# 141.3 — domknięcie launchera PvP

Status 15 IX: implementacja lokalna; wymagany jawny backfill istniejących
kont przed uruchomieniem nowego launchera. Nie wykonano migracji ani deployu.
Odbiór wcześniejszego pakietu Picker/capture: autor potwierdził PASS po
wdrożeniu i restarcie procesu 13. Nie rozszerzać tego odbioru na ten pakiet.

## Zmiana i kontrakt

Player-mode `/hack-action` używa identity/capability, inventory, pozycji i
canonical target/operations. Wymaga istniejącego wybranego celu, sprawdza
self/friend/klan i zachowuje cooldown. Kontynuacja po wyjeździe poza terytorium
i zasięg pozostaje dozwolona. Client coordinates i obce identyfikatory nie
zmieniają tożsamości rozpoczętego celu. Ponowne uruchomienie akcji zachowuje
security progress; nie pobiera zabezpieczeń od nowa z profilu ofiary.

Nowe tabele:

- `player_launcher_state`: potwierdzenie jawnego przeniesienia danych konta;
- `player_launch_entries`: trwała kolejka z receipt i znacznikiem consumed;
- `player_launch_risk_events`: historia ryzyka uruchomień, deduplikowana kluczem.

Kolejka, nowe zdarzenie ryzyka i ostrzeżenie SystemMessageStore są zapisywane
w jednej transakcji. Błąd cofa wszystkie trzy elementy. Zużytych receiptów
nie kasujemy podczas pobrania, dlatego powtórzenie nie uruchamia aplikacji
ponownie. Nowe intencje bez klucza klienta dostają odrębny losowy receipt;
bez klucza klienta nie da się utożsamić dwóch odrębnych requestów jako retry.

`/launch-queue` odczytuje wyłącznie nowy store. Pusty polling nie otwiera
transakcji zapisu. Niepusta kolejka jest atomowo pobierana po maks. 32 elementy;
pozostałe czekają na kolejne pobranie. Brak migracji daje recovery, bez fallbacku
do profilu. Zarówno nowe uruchomienia PvP, jak i pozostałe wywołania hack-action
publikują kolejkę przez wspólny store; cutover pełnego profilu w samym
hack-action dotyczy player-mode, nie przebudowy wszystkich mechanik POI.

Historia ryzyka w legacy profile pozostaje zachowana; nowe zdarzenia launchera
są trwale w nowym store. Widoki profilu dokładają do historii do 250 ostatnich
rekordów, bez nadpisywania istniejących zmian statusu. Pozostałe źródła ryzyka
w grze zachowują dotychczasowe ścieżki. Nie usunięto danych profilu ani
archiwalnej metody UserStore.consume_launch_queue; runtime endpoint jej nie używa.

## Migracja przed przełączeniem procesów

Rozszerzono istniejący `tools.migrate_identity_projection` o `launcher_missing`.
Nowe konta inicjalizują pusty canonical state przy utworzeniu profilu.
Istniejące konta wymagają jawnego apply. Migracja kopiuje oczekującą kolejkę
i historię ryzyka, nie zmienia profile revision/checksum/LKG ani samego profilu.
Pod writer-lockiem nadal sprawdza, czy revision/checksum/integrity nie zmieniły
się od odczytu. Kolejne apply nie przywraca consumed entries: marker migracji
powoduje pominięcie ponownego importu danych launchera.

Dry-run i apply odrzucają niepoprawne kształty danych. Limity źródła: 1000
oczekujących wpisów, 16 KiB JSON wpisu kolejki, 64 KiB JSON rekordu ryzyka.
Nie pomijać błędnych rekordów automatycznie. Historia ryzyka importowana jest
w całości w jawnej operacji, a odczyty runtime są ograniczone.

Operator potwierdza aktualną bazę i checkout. Historyczna baza serwera:
`/home/johndoe/app/chaos/data/game.sqlite3`. Procedura referencyjna:

1. Status i pełny dry-run po jednym koncie, aż `done=true`. CLI dry-run czyta
   jedną stronę; kolejne wymagają `--after-username` z `next_cursor`.
2. Zatrzymać writery CHAOS przed kopią i apply, aby stary launcher nie dopisywał
   rekordów do profilu po imporcie. Nie dotykać innych aplikacji PM2.
3. Nowa spójna kopia przez SQLite backup API i `quick_check` kopii = `ok`.
4. Apply po jednym koncie; przejrzeć `skipped`. Verify musi mieć wszystkie
   braki równe zero, w tym `launcher_missing=0`.
5. Uruchomić nowe procesy, ponownie verify i wykonać smoke gameplayu.

```bash
.venv/bin/python -m tools.migrate_identity_projection status --db data/game.sqlite3
.venv/bin/python -m tools.migrate_identity_projection dry-run --db data/game.sqlite3 --batch-size 1
# Dopiero po pełnym dry-run, zatrzymaniu writerów i sprawdzonym backupie:
.venv/bin/python -m tools.migrate_identity_projection apply --db data/game.sqlite3 --batch-size 1 --confirm-apply
.venv/bin/python -m tools.migrate_identity_projection verify --db data/game.sqlite3
```

To instrukcja wdrożenia, nie polecenie automatycznej migracji ani restartów.
Stare READY dla security nie oznacza gotowości launchera. Nie cofać na stary
launcher po imporcie bez osobnego planu zachowania nowych kolejek i receiptów.

## Walidacja

116 testów Python PASS w końcowej regresji. Dodatkowo po zaostrzeniu bramki
player: dwa testy preflight/odmowy PASS. Trzy zestawy JS PASS: gonna-win
lifecycle, intrusion alarm SFX bridge i player actor position ordering.

Izolowane testy sprawdzają pełny request PvP na dwóch profilach ≥35 MiB,
zero profile_bytes, brak zmiany rewizji profilu, preflight, kontynuację poza
terytorium, odmowę arbitralnego username, jednorazowe pobranie/replay,
konkurencję, rollback kolejki/ryzyka/wiadomości, import danych i ponowny apply.
Regresje obejmują capture, grant, Picker, identity, historyczną idempotencję,
mapę i narzędzia PvP; JS zachowuje lifecycle, kolejność pozycji i alarm SFX.

Końcowy smoke po migracji: uruchomić narzędzie z mapy, sprawdzić jedno okno
i postęp; po wyjeździe celu kontynuować; potwierdzić warning ryzyka skanowania
i brak podwójnego uruchomienia. Wcześniejsze zaakceptowane zasady pozostają
bez zmian. Produkcyjne zamknięcie 141.3 wymaga tego ostatniego odbioru.
