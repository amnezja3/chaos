# Runtime Slowdown Audit - BlackNet / Map / Delta

Data: 2026-07-14

Status: audyt bez zmian runtime. Ten dokument wskazuje potencjalne miejsca
spowolnienia po wdrozeniu BlackNetu i nie wprowadza poprawek w kodzie gry.

## Wniosek krotki

Aktualny BlackNet nie wyglada jak klasyczny daemon ani agresywny poller.

BlackNet laduje sygnaly na zadanie:

```text
renderBlackNet()
↓
loadBlacknetSignals()
↓
GET /api/blacknet/world-signals
```

Potem moze dogrywac kolejne paczki sygnalow, ale nie ma stalego
`setInterval()` tylko dla BlackNetu.

Najbardziej prawdopodobny powod ponownego odczucia mulenia to suma:

* ciezkich snapshotow mapy,
* request burst po otwarciu mapy z BlackNetu,
* cache missow `blacknet_world_facts` / `blacknet_world_signals`,
* kolejki workerow Gunicorna, gdy ciezkie requesty mapy zajmuja procesy.

## Co dziala cyklicznie

### Globalny runtime desktopu

W `static/js/terminal.js` widoczne sa stale odswiezania:

* `pollSystemMessages` co 10 s,
* `pollStateChanges` po 1 s od startu i potem co 4 s,
* Cyberner `refreshThreads` co 10 s tylko gdy okno Cybernera jest otwarte.

To nie sa nowe pollery BlackNetu.

### Mapa

W `templates/map_template.html` aktywne sa snapshoty mapy:

```text
/api/map/player-actors        co 30 s, start po 0.5 s
/api/map/player-areas         co 20 s, start po 2.6 s
/api/map/clan-vulnerabilities co 20 s, start po 5.6 s
/api/operations?summary=1     co 15 s, start po 8.2 s
```

To sa obecnie najwazniejsze miejsca do obserwacji, bo historycznie juz byly
oznaczone jako najciezsze scope'y.

Checkpointy Fazy G potwierdzaly, ze glowne obciazenie nadal generuja:

* map player areas,
* clan vulnerabilities,
* operations summary,
* wczesniej takze map player actors.

Player actors dostaly delta v0, ale player areas, clan vulnerabilities i
operations summary nadal pozostaja snapshotami.

## Jak dziala BlackNet teraz

### Backend

BlackNet korzysta z:

```text
GET /api/blacknet/world-signals
```

Endpoint uzywa:

```text
build_blacknet_world_signals()
↓
build_blacknet_world_facts_snapshot()
```

W kodzie istnieja cache:

```text
BLACKNET_WORLD_FACTS_CACHE_SECONDS = 60
BLACKNET_WORLD_SIGNALS_CACHE_SECONDS = 20
```

To znaczy, ze normalny request BlackNetu nie powinien za kazdym razem liczyc
calych faktow od zera. Nadal jednak pierwszy request po starcie, deployu albo
wygasnieciu cache moze byc drozszy.

### Frontend

BlackNet ma zrodlo:

```text
/api/blacknet/world-signals
```

I funkcje:

```text
loadBlacknetSignals()
maybeRefillBlacknetSignals()
```

Nie znaleziono osobnego stalego `setInterval()` dla BlackNetu. Dogrywanie
sygnalow jest zwiazane z widokiem i buforem sygnalow, a nie z ciaglym daemonem.

## Miejsca wysokiego ryzyka

### 1. Request burst: BlackNet + mapa

BlackNet po CTA potrafi otworzyc albo sfokusowac mape. Wtedy w krotkim czasie
moga zejsc sie:

```text
GET /api/blacknet/world-signals
GET /api/map/player-areas
GET /api/map/clan-vulnerabilities
GET /api/operations?summary=1
GET /api/map/player-actors
GET /system-messages
GET /api/state/changes
```

Jezeli Gunicorn ma malo wolnych workerow, lekkie requesty moga czekac za
ciezkimi snapshotami mapy. Wczesniejsze obserwacje produkcyjne pokazywaly juz,
ze zwiekszenie workerow z 1 do 3 wyraznie poprawilo odczuwalna responsywnosc.

### 2. Map player areas

`/api/map/player-areas` nadal jest snapshotem i w audycie Fazy G bylo oznaczone
jako bardzo kosztowne:

```text
sync_session_profile(rebuild_territory=False)
territory store
conflict detection
render warstw terytorium
```

To nadal moze blokowac worker i frontend, zwlaszcza przy otwartej mapie.

### 3. Clan vulnerabilities

`/api/map/clan-vulnerabilities` nadal jest snapshotem. Endpoint jest mniejszy
niz pelna mapa, ale historycznie mial wysokie czasy odpowiedzi i potrafi
wchodzic w kolejke razem z player areas oraz operations summary.

### 4. Operations summary

`/api/operations?summary=1` odswieza sie co 15 s. Po wprowadzeniu BlackNetu
czesc sygnalow operacyjnych kieruje gracza czesciej do mapy, wiec operations
summary moze byc czesciej aktywne w realnym gameplayu.

### 5. BlackNet world facts cache miss

`build_blacknet_world_facts_snapshot()` agreguje fakty swiata:

* aktywnosc targetow,
* operacje,
* konflikty,
* Ghost Exchange,
* Googleplex,
* radio,
* system messages.

Cache zmniejsza koszt, ale cache miss nadal moze dac krotki pik CPU. Im wiecej
profili, operacji, historii rynku i aktywnych faktow, tym wiekszy koszt
pierwszego odczytu po wygasnieciu cache.

### 6. Delta recovery

Delta-feed sam w sobie jest lekki, ale gdy endpoint zwraca `recovery_required`,
frontend odpala snapshot per scope. Jezeli recovery wystepuje czesto, gra moze
wracac do ciezkich snapshotow mimo wdrozonych delt.

Do sprawdzenia live:

```text
recovery_count
snapshot_recovery_count
```

z diagnostyki delta.

### 7. Koszt renderu klienta

BlackNet ma rozbudowany CSS i duze elementy typograficzne. To raczej nie tlumaczy
server-side stalled requestow, ale na slabym mobile moze dokladac koszt renderu
po stronie przegladarki, szczegolnie przy WebDragons + mapa otwartych naraz.

## Co raczej nie jest przyczyna

### Mail bootstrap

`mail_bootstrap()` uzywa teraz:

```text
load_profile_readonly(username, strip_sensitive=True)
```

Nie widac powrotu starego problemu:

```text
mail_bootstrap()
↓
sync_session_profile()
↓
deepcopy calego profilu
```

### BlackNet jako staly daemon

Nie znaleziono stalego cyklicznego pollera BlackNetu. BlackNet generuje i
pobiera sygnaly na zadanie oraz dogrywa paczki, gdy feed potrzebuje kolejnych
elementow.

## Co mierzyc na produkcji

Przed kolejnym fixem warto zlapac 5-10 minut live logow i policzyc:

```text
endpoint
request count
avg ms
p95 ms
p99 ms
max ms
payload size
```

Szczegolnie dla:

```text
/api/map/player-areas
/api/map/clan-vulnerabilities
/api/operations?summary=1
/api/map/player-actors
/api/blacknet/world-signals
/api/blacknet/world-facts
/api/state/changes
/system-messages
/api/profile
```

Warto osobno porownac:

* wejscie na desktop bez mapy,
* otwarcie mapy,
* otwarcie BlackNetu,
* klik CTA BlackNet -> mapa,
* kilka klikniec sygnalow BlackNetu pod rzad.

## Potencjalne kolejne optymalizacje

Bez implementowania w tym audycie:

1. Dodac metryke cache hit/miss dla `/api/blacknet/world-signals`.
2. Dodac perf log dla `build_blacknet_world_facts_snapshot()` z liczba faktow i
   czasem agregacji per rodzina.
3. Zrobic request-group trace dla akcji `BlackNet -> mapa`.
4. Przeniesc `player areas`, `clan vulnerabilities` i `operations summary` na
   wezsze snapshoty albo delty.
5. Sprawdzic, czy map boot po otwarciu z BlackNetu nie odpala jednoczesnie
   wszystkich ciezkich warstw mimo istnienia recovery/delt.
6. Jezeli cache miss BlackNetu jest kosztowny, rozwazyc dluzszy TTL albo
   prewarm po loginie/adminowym ticku.
7. Jezeli problem jest tylko na mobile, profilowac layout/render BlackNetu i
   WebDragons, a nie backend.

## Ocena koncowa

Najbardziej prawdopodobne miejsce spowolnienia nie jest w samym pseudo-daemonie,
bo taki daemon w praktyce nie dziala cyklicznie. Bardziej prawdopodobny jest
efekt uboczny integracji BlackNetu z mapa:

```text
BlackNet CTA
↓
otwarcie / fokus mapy
↓
map boot + ciezkie snapshoty
↓
kolejka workerow
↓
opoznienia lekkich endpointow i UI
```

BlackNet dodal nowy realny feed, ale glowna techniczna mina nadal siedzi w
mapowych snapshotach: player areas, clan vulnerabilities i operations summary.
