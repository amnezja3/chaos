# Sprint 131 — GhostNetwork Suite: audit przedsprintowy

Data audytu: 2026-08-24.

Status po re-audycie 2026-08-26:
`SPRINT 131 AUDIT COMPLETE — READY FOR SPRINT 132`.

Pierwotne ustalenia `NO-GO` poniżej pozostają historycznym zapisem audytu z
2026-08-24. Sprint 130.12 zamknął wszystkie wskazane blockery bez implementacji
GUI GhostNetwork Suite.

Audit jest wyłącznie dokumentacyjno-kontraktowy. Nie dodaje endpointu, GUI,
produktu, migracji, pollera ani mutacji bazy. Zweryfikowano aktualny kod i testy,
a nie tylko historyczne nagłówki roadmapy.

## Werdykt

Fundament GhostNetwork Suite istnieje i powinien zostać rozszerzony, nie
zbudowany ponownie:

- `GhostVisibilityService` jest jedyną granicą projekcji części;
- `GhostModuleStateService` rozwiązuje sześć wymaganych relacji;
- konflikt jest nakładką z zamrożonym kontekstem;
- `/api/ghostnetwork/snapshot?view=suite` istnieje i korzysta z lekkiej identity;
- delty niosą bezpieczne `part_projection` i mają recovery przez snapshot;
- helper Territory Control istnieje, ale nie jest podłączony do snapshotu;
- wspólny desktopowy bridge mapy istnieje;
- rodzina `ghost_control_suite` obejmuje trzy obecne produkty.

Przejście do Sprintu 132 jest jednak zablokowane przez wiążący kontrakt
`doc/architecture/profile_hot_path_contract_130_11_plus.md`. Aktualne Territory
Control i wspólny teleport nadal wchodzą w pełny profil. Brakuje też bounded
projekcji aliasów właścicieli. Te problemy muszą zostać usunięte lub zamknięte
osobnym zatwierdzonym cutoverem przed rozpoczęciem implementacji 132.

## Source of truth

| Zakres | Kanoniczne źródło | Rola Suite |
| --- | --- | --- |
| cykl, części, topology, lifecycle | `ghost_*`, `GhostNetworkRepository`, `GhostNetworkService` | tylko viewer projection |
| stan neutral/blocked/active | `GhostModuleStateService` | filtr i etykieta, bez własnej decyzji |
| visibility i bezpieczna lokalizacja | `GhostVisibilityService.project_part_for_viewer` | bez zmian po stronie klienta |
| kontrola obszaru | territory stores, ownership, `player_areas`, conflicts | odczyt stabilnego wyniku |
| tożsamość viewera | `UserStore.get_profile_identity` | tylko login, klan, profesja |
| alias właściciela | brak gotowej bounded batch projection | blocker; nie wolno czytać pełnych profili |
| instalacja produktu | `PlayerInventoryStore` / Googleplex receipts | sprawdzenie canonical inventory |
| pozycja gracza | `PlayerPositionStore` | odległość i wynik teleportu |
| oznaczony cel | `PlayerTargetRuntimeStore` | Suite nie ustawia ani nie zmienia celu |
| snapshot/delta | istniejący scope `ghostnetwork` | bootstrap/recovery i aktualizacja punktowa |

Profil gracza, session cache, frontend snapshot i `player_areas` nie stają się
źródłem prawdy GhostNetwork.

## Macierz widoczności

| Relacja | Stan bazowy | Tożsamość | Lokalizacja | Mapa | Teleport |
| --- | --- | --- | --- | --- | --- |
| `public_neutral` | neutral | pełna | exact | tak | exact |
| `self_foreign_blocked` | blocked | pełna dla właściciela | exact | tak | exact |
| `foreign_blocked` | blocked | ukryta | territory-only | tylko opaque territory | tylko bezpieczny punkt territory |
| `self_own_active` | active | pełna dla właściciela | exact | tak | exact |
| `clan_own_active` | active | pełna dla klanu części | exact | tak | exact |
| `foreign_active` | active | ograniczona, bez part identity/ability | exact | tak | exact |

`conflict_state=contested` nie tworzy siódmej relacji. Zachowuje bazowe
`module_state`, `viewer_relation` i `visibility_level` w
`frozen_visibility_context` do stabilizacji terytorium.

## Kanoniczne grupy Suite

Grupy są deterministycznymi indeksami jednego viewer-projected `parts[]`.
Element grupy wskazuje wyłącznie `public_entity_id`; nie kopiuje całej części i
nie tworzy osobnego magazynu.

| Grupa | Warunek |
| --- | --- |
| `public` | `viewer_relation == public_neutral` |
| `blocked` | `module_state == blocked` |
| `clan_active` | `viewer_relation == clan_own_active` |
| `self_foreign` | `viewer_relation == self_foreign_blocked` |
| `self_own` | `viewer_relation == self_own_active` |

`foreign_active` pozostaje widoczną pozycją w głównej liście i może otrzymać
jawnie nazwaną sekcję prezentacyjną, ale nie wolno dopisać jej do grupy
ujawniającej pełną tożsamość. Bieżące `_build_suite_views()` zwraca listy pełnych
obiektów i pozwala jednej części występować w kilku listach. Sprint 132 ma
zastąpić to bezpiecznymi indeksami/summary wyprowadzonymi z głównego `parts[]`.

## Kontrakt części dla Suite

Dozwolone pola bazowe po projekcji:

```text
public_entity_id
cycle_id
visibility_version
viewer_relation
visibility_level
module_state
conflict_state
contested
identity_visible
ability_visible
location_visibility
can_show_on_map
can_teleport
territory_id
territory_owner_id
territory_clan
display_label
summary
marker_asset_url
state_version
```

Pola identity (`part_id`, kody/nazwy części, maszyny, profesji i ability,
`target_id`, dokładne współrzędne oraz właściwy asset) występują wyłącznie wtedy,
gdy dopuści je `project_part_for_viewer`. Frontend nie filtruje surowego rekordu.

## Właściciel i klaster

`cluster_id` jest aliasem prezentacyjnym istniejącego `territory_id` /
`player_areas.id`. Nie powstaje nowy identyfikator ani tabela.

Docelowa projekcja może zawierać:

```text
territory_id
cluster_id
cluster_label
territory_owner_id
territory_owner_alias
territory_clan
```

`get_profile_identity(username)` potrafi zwrócić lekki `nick`, ale wykonywanie
go osobno dla każdego właściciela tworzyłoby N+1. `list_profile_identities()`
skanuje wszystkich użytkowników i jest zabronione w zwykłym runtime. Przed
użyciem aliasów należy dodać bounded batch lookup po unikalnych owner IDs albo
dedykowaną identity projection/index. Brak aliasu ma dawać bezpieczny fallback,
nie full-profile read.

## Territory Control

Istniejący helper:

```text
GhostVisibilityService.project_territory_component_for_viewer(cluster, viewer)
```

zwraca `contains_ghost_part`, count, relation, state, identity flag, summary i
viewer-projected `parts`. Docelowy snapshot Territory Control mapuje tę tablicę
na `ghost_parts[]`; nie spłaszcza pierwszego elementu i nie przekazuje surowych
wierszy repository.

Aktualny runtime nie wywołuje helpera. `build_territory_control_snapshot()` nie
zawiera komponentów GN i korzysta z `load_profile_readonly()` dla instalacji,
pozycji i aimed targetu. Jest to blocker heavy-profile.

Wymagany cutover:

- instalacja z canonical `PlayerInventoryStore`;
- pozycja z `PlayerPositionStore`;
- aimed target, jeżeli nadal potrzebny, z `PlayerTargetRuntimeStore`;
- viewer identity z `get_profile_identity`;
- części z GN repository/service i wyłącznie przez visibility helper;
- bounded owner alias projection;
- zero `load_profile_readonly`, `get_profile`, `sync_session_profile` i
  `profile_bytes` w GET snapshot/detail.

## Mapa i teleport

Wspólny bridge desktop–mapa to:

```text
createMap()
notifyOpenMapsBlacknetFocus(...)
```

Suite przekazuje opaque payload:

```text
source=ghostnetwork_suite
target_type=ghostnetwork_part|ghostnetwork_territory
public_entity_id|territory_id
```

Nie przekazuje dokładnych współrzędnych ukrytej części, nie ustawia
`aimed_target`, nie rezerwuje części i nie uruchamia operacji.

Istniejący `/api/blacknet/cta/teleport` akceptuje klientowe `lat/lng`, ładuje
pełny profil i zapisuje go przez `UserProfileManager`. Nie jest bezpiecznym
contractem dla Suite. Sprint 134 musi dla `source=ghostnetwork_suite`:

1. odrzucać klientowe współrzędne;
2. rozwiązać opaque ID po stronie serwera;
3. ponownie zbudować visibility dla aktualnego viewera;
4. wybrać exact anchor albo bezpieczny punkt territory;
5. zapisać pozycję przez canonical position boundary z session precommit guard;
6. nie wykonywać pełnego profile read/write.

## Produkt, okno i ikony

Potwierdzone produkty rodziny:

```text
victimPicker
territoryControl
operationControl
```

Wszystkie mają `type=pro-system-tool`, `category=pro-system-tools` i
`family_id=ghost_control_suite`. GhostNetwork Suite zachowuje:

```text
id=ghostnetworkSuite
launcher=createGhostNetworkSuiteApp
data-app=ghostnetwork-suite
```

Wzorce jednej instancji, `app-window`, `findAvailablePosition`,
`makeDraggable`, `bringWindowToFront` i taskbara są dostępne. Obecnie każda z
trzech aplikacji ma osobny słownik ikon. `GHOST_CONTROL_ICONS` nie istnieje;
jego utworzenie jest współdzielonym refaktorem prezentacji w 133/135, a nie
założeniem audytu.

## Snapshot, delta i recovery

- endpoint `GET /api/ghostnetwork/snapshot` już obsługuje `view=suite`;
- viewer identity pochodzi z `get_profile_identity`;
- `normalize_snapshot_view(..., suite)` usuwa geometrię endpointów connections;
- delta niesie viewer-projected `part_projection`;
- wersje i checksumy są dostępne do recovery;
- snapshot/recovery nie powinny odtwarzać SFX.

`GhostNetworkDeltaClient` mieszka jednak w `static/js/map/ghostnetwork.js`, a
terminal deleguje event do klienta w oknie mapy. Suite nie może ładować Leaflet
ani wymuszać otwarcia mapy. Sprint 135 wydziela jeden lekki współdzielony klient
transport/dedupe/recovery; nie dodaje drugiego pollera.

## Inventory callsites 132–138

| Sprint | Callsite / potrzeba | Klasyfikacja | Disposition |
| --- | --- | --- | --- |
| 132 | `/api/ghostnetwork/snapshot?view=suite` | `canonical_projection` | rozszerzyć istniejący endpoint |
| 132 | viewer identity | `canonical_projection` | `get_profile_identity`, zero full profile |
| 132 | owner aliases | `blocker` | bounded batch identity projection |
| 132 | groups/summary/actions | `canonical_projection` | pochodne `parts[]`, IDs zamiast kopii |
| 133 | product install/launch | `canonical_projection` | canonical inventory + istniejący launcher lifecycle |
| 133 | GUI identity fields | `canonical_projection` | tylko suite snapshot/delta |
| 134 | Territory Control snapshot | `blocker` | usunąć `load_profile_readonly`, podłączyć helper GN |
| 134 | GN teleport | `blocker` | server-resolved opaque target, canonical position write |
| 134 | show-on-map | `canonical_projection` | istniejący bridge, opaque ID |
| 135 | delta/recovery client | `blocker` | wydzielić z mapowego pliku bez Leaflet |
| 135 | product registry | `canonical_projection` | jeden katalog/inventory receipt |
| 136 | audience recipient resolution | `blocker` | zakaz all-user/per-recipient profile reads; trwały indeks |
| 136 | narrative facts | `canonical_projection` | istniejący publisher/outbox, per-audience projection |
| 137 | model worker input | `canonical_projection` | wyłącznie zatwierdzony outbox task, zero profilu |
| 138 | BlackNet publish/CTA | `canonical_projection` | audience payload i opaque CTA z pipeline'u |

`allowed_offline_heavy` dotyczy wyłącznie jawnych narzędzi operatorskich i nie
jest dozwolone w żadnym zwykłym callsite 132–138.

## Zabronione duplikaty

- drugi store części, grup albo ownerów;
- drugi visibility resolver;
- drugi snapshot endpoint lub cache Suite;
- surowy rekord GN w Territory Control;
- frontendowe `viewer.clan === part.clan`;
- drugi poller albo osobny delta client;
- drugi iframe/map renderer;
- alternatywny endpoint teleportu;
- klientowe współrzędne dla ukrytego celu;
- pełny profil, all-user scan lub per-recipient profile read;
- zapis GN, terytorium lub inventory do session cache jako canonical state.

## Plan testów 132–135

### Sprint 132

- sześć relacji i conflict overlay;
- jedna część raz w `parts[]`, grupy wyłącznie po `public_entity_id`;
- ukryte identity/ability/target/asset/coordinates nie występują w JSON;
- owner aliases bez N+1 i all-user scan;
- `view=suite` bez geometrii connections;
- mały i syntetyczny profil 35 MB: identyczny bounded query count oraz
  `profile_full_read/write/bytes=0`;
- cache key rozdziela viewer ID, clan, state i visibility version.

### Sprint 133

- produkt ma właściwe ID/family/type/category;
- instalacja i launcher używają canonical inventory;
- jedna instancja okna, focus/taskbar/close bez listener leak;
- brak `/api/profile`, mapy i aktywnych requestów teleportu;
- karty renderują wyłącznie projected fields i usuwają tajne DOM po zmianie
  visibility.

### Sprint 134

- Territory Control owner/clan/foreign/hidden/conflict matrix;
- `ghost_parts[]` zawiera tylko `project_part_for_viewer` output;
- hidden part nie ujawnia ID, assetu ani coordinates;
- opaque map focus nie ustawia celu ani reservation;
- teleport odrzuca `lat/lng`, ponownie autoryzuje viewer i rozwiązuje exact lub
  territory-only anchor;
- session generation input/precommit guard i idempotentny position delta;
- zero full profile dla Territory Control, focus i teleport.

### Sprint 135

- mapa i Suite używają jednej instancji shared delta client;
- dedupe, version gap i recovery przez `view=suite`;
- snapshot/recovery bez SFX;
- zmiana visibility usuwa stare sekrety z modelu, DOM i cache;
- zamknięcie Suite usuwa listener;
- desktop/mobile oraz pełna regresja Victim Picker, Territory Control,
  Operation Control, mapy, GN i session isolation.

## Blockery i bramka

Blockery przed Sprintem 132:

1. Territory Control GET/detail używa pełnego profilu.
2. Wspólny teleport używa pełnego read/write profilu i przyjmuje klientowe
   współrzędne; nie ma bezpiecznej gałęzi GN.
3. Brak bounded batch projection aliasów właścicieli.
4. Shared delta client jest związany z mapą; blocker musi zostać zamknięty
   najpóźniej przed pracami delta/GUI Sprintu 135.
5. Audience fan-out 136 nie ma zatwierdzonego lekkiego indeksu odbiorców; nie
   wolno użyć istniejących all-user identity scans jako rozwiązania.

Werdykt:

`SPRINT 131 AUDIT COMPLETE`

`NO-GO FOR SPRINT 132 — HEAVY-PROFILE AND BOUNDED-IDENTITY BLOCKERS OPEN`

## Re-audit po Sprint 130.12 — 2026-08-26

| Historyczny blocker | Wynik | Dowód |
| --- | --- | --- |
| Territory Control pełny profil | RESOLVED | `territory_control_load_context()` korzysta z identity, inventory, position i target canonical stores |
| Teleport pełny profil / client coordinates | RESOLVED | `ghostnetwork_suite` rozwiązuje opaque ID po stronie serwera i zapisuje `PlayerPositionStore` |
| Brak bounded owner aliases | RESOLVED | revision-aware `UserIdentityProjectionStore.get_identities()` |
| Delta client zależny od Leaflet | RESOLVED | `static/js/ghostnetwork_delta_client.js`, wspólna instancja i adapter mapy |
| Audience fan-out bez lekkiego indeksu | RESOLVED | `list_recipient_ids()` i bounded `get_identities()` |

Re-audit nie znalazł runtime fallbacku do pełnego profilu w tych call chainach.
Pełna regresja: 1092/1092 Python; heavy-profile/read-path: 24/24; frontend:
13/13 pakietów Node.

Werdykt po re-audycie:

`SPRINT 131 AUDIT COMPLETE — READY FOR SPRINT 132`
