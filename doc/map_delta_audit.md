# Sprint 66 - Map Delta Audit

## Cel

Sprint 66 przygotowuje mape pod delty bez migracji runtime.

Nie zmieniono mapy, pollerow, endpointow ani `applyDelta()`. Audyt opisuje,
ktore warstwy Leaflet mozna latac punktowo, ktore nadal wymagaja snapshotu oraz
jakie zrodla prawdy powinny emitowac przyszle eventy mapy.

## Zasady

* Zrodlem prawdy pozostaja istniejace modele: profil, territory store, target
  store, vulnerability store i operations runtime.
* Delta bus nie liczy stanu mapy.
* Event mapy jest powiadomieniem o zmianie, ktora juz zaszla w zrodle prawdy.
* Kazdy event mapy musi miec stabilne `entity_id`.
* Jezeli warstwa nie ma stabilnego klucza albo jest zalezna od wielu obiektow,
  zostaje snapshot/recovery.

## Obecne endpointy mapy

| Endpoint | Dane | Zrodlo prawdy | Obecny render | Kandydat na delte |
| --- | --- | --- | --- | --- |
| `/api/map/player-actors` | aktorzy graczy, znajomi, intruzi, target gracza | profil, `mail_store`, territory store | markery po `username`, aktualizacja `setLatLng` / `setIcon`, usuwanie niewidocznych | TAK, pierwszy kandydat |
| `/api/map/friends` | markery znajomych | `mail_store`, profile znajomych | markery po `username`, aktualizacja punktowa | TAK, ale uwaga na duplikacje z player actors |
| `/api/map/player-areas` | pola graczy, intruzi, konflikty, contested targets, captured pillars | territory store, territory conflict store, profil | pelne czyszczenie tablic layerow i rebuild | POZNIEJ, snapshot zostaje |
| `/api/map/clan-vulnerabilities` | aktywne podatnosci klanowe | vulnerability store, profil/klan | pelne czyszczenie warstwy, rebuild markerow, registry pomocniczy | TAK po nadaniu stabilnego klucza |

## Eventy v0

| Event | Zrodlo prawdy | Entity id | Minimalny payload | Patch strategy | Recovery |
| --- | --- | --- | --- | --- | --- |
| `map.player_moved` | profil gracza / pozycja runtime | `player:<username>` | `username`, `lat`, `lng` | `setLatLng` istniejacego markera albo dodanie markera przez actor snapshot | `/api/map/player-actors` |
| `map.player_actor_updated` | profil, `mail_store`, territory store | `player:<username>` | `username`, `nick`, `avatar`, `status`, `relation`, `context`, `lat`, `lng` | aktualizacja ikony, tooltipu, snapshotu menu | `/api/map/player-actors` |
| `map.player_actor_removed` | profil/presence/contact/territory intruder | `player:<username>` | `username` | usuniecie markera z `playerActorMarkers` | `/api/map/player-actors` |
| `map.target_updated` | target store / profil / operation runtime | `target:<target_id>` | `target_id`, `lat`, `lng`, `label`, `security`, `status` | aktualizacja pojedynczego targetu tylko po wprowadzeniu registry targetow | snapshot mapy albo dedykowany target snapshot |
| `map.target_captured` | target store, territory store, profil `captured_targets` | `target:<target_id>` | `target_id`, `owner`, `captured_by`, `lat`, `lng`, `status` | aktualizacja ownership targetu i ewentualnego filaru konfliktu | `/api/map/player-areas` + snapshot targetow |
| `map.target_removed` | target store / operation runtime | `target:<target_id>` | `target_id` | usuniecie pojedynczego targetu po registry targetow | snapshot mapy albo dedykowany target snapshot |
| `map.area_claimed` | territory store | `area:<area_id>` | `area_id`, `owner_username`, `vertices`, `status` | pozniej: update/dodanie polygonu po `area_id` | `/api/map/player-areas` |
| `map.area_contested` | territory conflict store | `conflict:<conflict_id>` | `conflict_id`, `participants`, `intersections`, `targets` | pozniej: update conflict polygonow i contested markers | `/api/map/player-areas` |
| `map.vulnerability_added` | vulnerability store | `vulnerability:<id>` | `id`, `target`, `lat`, `lng`, `label`, `source_type`, `security` | dodanie markera i wpisu registry | `/api/map/clan-vulnerabilities` |
| `map.vulnerability_removed` | vulnerability store | `vulnerability:<id>` | `id` albo target key | usuniecie markera i wpisu registry | `/api/map/clan-vulnerabilities` |

## Warstwy Leaflet

### Player actors

`window.playerActorMarkers` jest juz slownikiem po `username` / `nick`.
Renderer potrafi:

* dodac nowy marker,
* przesunac marker przez `setLatLng`,
* zmienic ikone przez `setIcon`,
* podmienic snapshot menu,
* usunac markery, ktorych nie ma w widocznym zbiorze.

To jest najbezpieczniejsza pierwsza migracja mapy w Sprincie 67.

### Friends

`window.friendMarkers` tez jest slownikiem po uzytkowniku i technicznie nadaje
sie do delt. Ryzyko: znajomi sa rownolegle uwzgledniani w `player-actors`, wiec
przed migracja trzeba zdecydowac, czy `friends` zostaje osobna warstwa, czy jest
zlozone w `player-actors`. Inaczej latwo o duplikaty markerow.

### Clan vulnerabilities

Warstwa ma `clanVulnerabilityRegistry` i `vulnerabilityTargetKey()`, ale obecny
refresh czysci `window.clanVulnerabilityLayers` i buduje wszystko od zera.

Delty sa mozliwe dopiero po przyjeciu stabilnego `entity_id`:

* preferowane `vulnerability:<report.id>`,
* fallback `vulnerabilityTargetKey(target)` tylko wtedy, gdy `id` nie istnieje.

### Player areas / conflicts

`refreshPlayerAreas()` robi pelny rebuild:

* `playerAreaLayers`,
* `areaIntruderLayers`,
* `contestedTargetLayers`,
* `conflictAreaLayers`,
* `capturedConflictPillarLayers`.

To sa warstwy zlozone i zalezne od territory store oraz conflict store. W Fazie G
powinny zostac snapshot/recovery do czasu, az polygon, konflikt i contested
target dostana stabilne klucze oraz osobne registry.

### Targety bazowe

Targety renderowane przez glowna mape / template nie maja jeszcze w tym audycie
jednego potwierdzonego registry po `target_id`. Eventy `map.target_*` sa
potrzebne w kontrakcie, ale ich runtime powinien wejsc dopiero po audycie
target registry. Do tego czasu snapshot mapy pozostaje bezpieczna sciezka.

## Rekomendacja dla Sprintu 67

Sprint 67 powinien objac tylko:

* `map.player_moved`,
* `map.player_actor_updated`,
* `map.player_actor_removed`.

Zakres powinien korzystac z istniejacego read modelu `/api/map/player-actors`.
Nie nalezy jeszcze ruszac targetow, terytoriow, konfliktow ani podatnosci.

## Ryzyka

* Utworzenie drugiego stanu mapy w delta busie.
* Dublowanie `friendMarkers` i `playerActorMarkers`.
* Patchowanie polygonow bez stabilnego `area_id`.
* Patchowanie targetow bez registry po `target_id`.
* Traktowanie `map.area_contested` jako prostego markera, mimo ze zmienia
  polygon, liste targetow i filary konfliktu.

## Status

Sprint 66 zamkniety jako audyt. Runtime mapy pozostaje bez zmian.
