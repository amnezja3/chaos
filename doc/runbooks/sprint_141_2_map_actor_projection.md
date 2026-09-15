# 141.2 — projekcja aktorów mapy i kolejność pozycji

Status: autor wykonał migrację na serwerze 15 IX; verify READY dla 31 kont.
Dowody i ścieżka backupu: journal, wpis „141.2: migracja projekcji na serwerze”.
Autor potwierdził również przeładowania chaos oraz trzech workerów: wszystkie
online, ponowne verify READY, brak brakujących awatarów. Odbiór mapy pozostaje
otwarty. Szczegóły w journalu: „141.2: przeładowanie procesów i ponowne verify READY”.

## Zmiana

`/api/map/player-actors` czyta identity/capability, canonical target i pozycje.
Kandydaci pochodzą z klanu, kontaktów i bounding boxów własnego terytorium oraz
geometrii engagement; końcowa widoczność nadal używa dokładnych wielokątów
i dotychczasowych reguł. Bez `list_profiles`, pełnego profilu ani fallbacku
pozycji. Nowy indeks `player_positions(lat,lng)` powstaje przy schema init,
nie w requestach. Limity: 500 kandydatów/kontaktów, 128 wielokątów, mniej niż
1000 obszarów. Przekroczenie limitu daje odmowę, nie niepełną listę sukcesu.

Snapshot i delta przenoszą `position_version`. Mapa odrzuca starszą wersję,
także po usunięciu markera, oraz snapshot rozpoczęty przed odebraną deltą.
Odzyskanie widoczności następuje podczas kolejnego istniejącego odświeżenia.
Delta usunięcia nie zawiera współrzędnych ani danych nowego markera.

## Wymagana projekcja przed uruchomieniem zmienionych ścieżek

Awatar należy do `desktop_boot_json.avatar`, utrzymywanego przy guarded write.
Istniejące rekordy trzeba jawnie uzupełnić. Bez tego nowe odczyty mapy kończą się
`profile_recovery_required`; nie pobierają awatara z ciężkiego profilu.
Nie uruchamiać nowego runtime przed weryfikacją projekcji.

Istniejące narzędzie `tools/migrate_identity_projection.py` ma rozszerzony
status `map_avatar_missing`. Uzupełnienie aktualizuje projekcje, nie profile,
nie zmienia pozycji, nagród ani receiptów. Pod writer-lockiem ponownie sprawdza
revision/checksum/integrity; zmienione w międzyczasie konta są pomijane.

Operator wskazuje rzeczywistą bazę przez `--db`; nie zakładać, że lokalna baza
odpowiada serwerowi. Z katalogu repozytorium:

```powershell
python -m tools.migrate_identity_projection status --db '<pełna ścieżka bazy>'
python -m tools.migrate_identity_projection dry-run --db '<pełna ścieżka bazy>' --batch-size 1
```

Dry-run obejmuje jedną stronę; kolejne sprawdza się z `--after-username` zgodnie
z `next_cursor`. Mały batch ogranicza pamięć dla profili ≥35 MiB. Po przeglądzie
wyniku operator może wykonać osobno autoryzowane uzupełnienie i weryfikację:

```powershell
python -m tools.migrate_identity_projection apply --db '<pełna ścieżka bazy>' --batch-size 1 --confirm-apply
python -m tools.migrate_identity_projection verify --db '<pełna ścieżka bazy>'
```

Warunek: `status=ready`, `missing=0`, `stale=0`, `map_avatar_missing=0`;
przejrzeć pominięte konta, bez automatycznego repair profilu. Te komendy nie są
poleceniem wykonania migracji/deployu/restartu w bieżącej sesji.

## Walidacja i otwarte punkty

Lokalne testy obejmują cztery warianty rozmiaru dwóch profili, zero profile_bytes,
brak pełnych metod odczytu, zachowanie awatara, bounded selekcję, jawny backfill,
historyczne reguły widoczności, Kicker i kolejność snapshot/delta w JS.

Nie zamyka to 141.2: pozostają pending travel commit/animacja po teleportacji,
pełne audience wyjścia/wejścia oraz pomiar czasu na rzeczywistych klientach.
Browser E2E, migracja i stan serwera nie zostały potwierdzone tymi testami.
