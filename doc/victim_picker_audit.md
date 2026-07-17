# Sprint 99 - Victim Picker Source Contract Audit

## Cel

Victim Picker ma byc jednym agregowanym widokiem kandydatow na cel. Nie jest
nowym systemem targetowania i nie tworzy nowego magazynu danych. Widok ma
korzystac z obecnych zrodel prawdy mapy, profilu, relacji graczy,
vulnerability store, territory store oraz obecnych endpointow mapowych.

Ten dokument blokuje tworzenie:

* `profile.victims`;
* osobnego victim store;
* drugiego systemu `aimed_target`;
* drugiego wzoru zasiegu;
* osobnej procedury teleportu albo focusu mapy.

## Obecne zrodla i funkcje

### Zwykle obiekty mapy

Zrodlo:

* scan mapy przez `POST /map-action` z `action=scan`;
* wyniki Overpass/fetchera i obiekty generowane lokalnie przez map action;
* trwale oznaczone obiekty w `profile.targets`.

Aktualny zapis:

* `POST /map-action` z `action=mark_target` zapisuje obiekt do
  `profile.targets`;
* obiekt dostaje `lat`, `lng`, `label`, `name`, `icon`, `source_type`,
  `generated`;
* nie ustawia jeszcze `aimed_target`; jest to tylko lista znanych obiektow.

Ustawienie jako aktywny cel:

* `POST /hack-action` ustawia albo aktualizuje `profile.aimed_target`;
* target dostaje `target_mode=standard`, `security` oraz `actions_allowed`;
* kolejne narzedzia mapy, terminala i desktopu musza isc przez ten sam kontrakt
  `actions_allowed`.

### Gracze

Zrodlo:

* `GET /api/map/player-actors`;
* endpoint sklada graczy z accepted contacts, intruderow na terytorium,
  aktualnej pozycji i relacji.

Pozycja:

* `target_profile.curently_possition`;
* intruder moze miec pozycje z `territory_store.list_recent_area_intruders`.

Relacje i blokady:

* `resolve_player_actor_relation`;
* `resolve_player_actor_actions`;
* self jest blokowany;
* friend jest blokowany dla `mark_target`;
* same clan jest blokowany dla `mark_target`;
* pending contact blokuje zaproszenie, nie samo targetowanie;
* intruder oraz neutral moga byc kandydatami, o ile akcja `mark_target` jest
  enabled.

Ustawienie celu:

* `POST /api/map/player-targets/mark`;
* endpoint ponownie sprawdza self/friend/same clan;
* buduje `aimed_target` z `target_mode=player`, `target_username`,
  `source_type=player`, aktualna pozycja i `security` gracza;
* nie wolno pomijac tego endpointu w Victim Pickerze.

### Filary podatnosci

Zrodlo:

* `GET /api/map/clan-vulnerabilities`;
* dane pochodza z `vulnerability_store.list_active()`;
* payload zawiera `target`, `vulnerability_id`, `lat`, `lng`, `security`,
  `same_clan`, `is_reporter`.

Ustawienie celu:

* mapa przekazuje do `showHackingMenuForMarker` target z `vulnerability_id`;
* `POST /hack-action` rozpoznaje `vulnerability_id` i ustawia
  `target_mode=vulnerability`;
* security pochodzi z raportu podatnosci.

Regula:

* Victim Picker moze pokazac filar jako kandydata, ale ustawienie celu musi
  zachowac `vulnerability_id` i przejsc przez `/hack-action` albo przyszly
  wspolny backendowy helper z tym samym kontraktem.

### Filary konfliktu

Zrodlo:

* `GET /api/map/player-areas`;
* payload zwraca `territory_conflicts`, `conflict_areas`,
  `revealed_conflict_targets`, `captured_conflict_pillars` i
  `contested_targets`;
* dane powstaja z `territory_store`, `detect_territory_conflicts`,
  `get_active_conflicts_for_player`, `find_contested_targets_for_player`.

Ustawienie celu:

* target konfliktowy musi przeniesc `foreign_area_id`,
  `contest_owner_username`, `conflict_id` i pozycje;
* `/hack-action` ustawia wtedy `target_mode=territory_contest`;
* security pochodzi z contested targetu.

Regula:

* nie wolno budowac drugiego modelu konfliktow dla Victim Pickera;
* kandydat ma byc tylko projekcja danych juz zwracanych przez
  `/api/map/player-areas`.

### Pozycja motocykla

Zrodlo:

* `profile.curently_possition`;
* czesc frontendu uzywa tez aliasu `current_position`;
* map travel i teleport zapisuje `curently_possition`.

Miejsca zapisu:

* `POST /map-action` z `action=travel`;
* `POST /api/blacknet/cta/teleport` dla BlackNet i terminal teleport;
* produkty Googleplex `travel_ticket` przez `apply_googleplex_product_effect`.

Regula:

* Victim Picker liczy dystans od `curently_possition`;
* jesli brak pozycji, kandydat moze byc pokazany, ale z disabled reason
  `missing_position`.

## Zasieg

Jedynym zrodlem wzoru zasiegu jest:

```text
get_player_action_range(profile)
```

Obecnie:

* bazuje na levelu;
* uwzglednia `scan_range_bonus`;
* ma limit gorny `4000`;
* jest juz zwracany w `/api/map/player-areas` jako `player.action_range`;
* `/map-action` uzywa go dla `scan` i `travel`.

Odleglosc:

* obecna mapa i backend uzywaja `Haversine.haversine_distance`;
* Victim Picker nie powinien kopiowac wzoru dystansu do nowego miejsca bez
  wspolnego helpera.

Regula kontraktu:

* backend powinien zwracac `distance_m`, `action_range_m` i `in_range`;
* frontend moze renderowac wynik, ale nie powinien decydowac o prawie do akcji
  jako jedyne zrodlo prawdy.

## Fokus mapy i teleport

Fokus mapy:

* obecne mechanizmy frontendu potrafia otworzyc mape i ustawic focus na
  `lat/lng`;
* dla Victim Pickera wystarczy payload `focus: {lat, lng, zoom, mode}` albo
  zgodny z obecnym mostem mapy.

Teleport:

* terminal `teleport <lat:lon>` i BlackNet uzywaja
  `POST /api/blacknet/cta/teleport`;
* teleport wymaga potwierdzenia OK/ANULUJ w UI;
* endpoint zapisuje `curently_possition`, emituje `map.player_moved` i sprawdza
  intruzje terytorium;
* mapa `travel` uzywa `/map-action` i sprawdza zasieg motocykla.

Regula:

* Victim Picker moze oferowac `show_on_map` dla kazdego kandydata z pozycja;
* teleport powinien uzywac istniejacego potwierdzenia i endpointu teleportu;
* travel w zasiegu powinien zostac oddzielony od teleportu poza zasiegiem.

## Agregowany widok VICTIMS

Widok powinien skladac kandydatow z czterech zrodel:

1. `profile.targets`
   * typ: `saved_target`;
   * pozycja: `lat/lng` zapisane przy `mark_target`;
   * target mode: standard.
2. `GET /api/map/player-actors`
   * typ: `player_actor`;
   * pozycja: `lat/lng` aktora;
   * target mode: player;
   * `can_aim` zgodnie z `actions.mark_target.enabled`.
3. `GET /api/map/clan-vulnerabilities`
   * typ: `vulnerability`;
   * pozycja: `lat/lng` raportu;
   * target mode: vulnerability;
   * wymaga zachowania `vulnerability_id`.
4. `GET /api/map/player-areas`
   * typ: `territory_contest`;
   * pozycja: target konfliktu;
   * target mode: territory_contest;
   * wymaga `foreign_area_id` i danych konfliktu.

## Wspolny kontrakt kandydata v0

```json
{
  "target_id": "map:52.10000:21.20000:label",
  "target_mode": "standard",
  "target_type": "poi",
  "source_type": "atm",
  "candidate_source": "profile.targets",
  "label": "ATM",
  "icon": "payload_icon",
  "lat": 52.1,
  "lng": 21.2,
  "distance_m": 123,
  "action_range_m": 900,
  "in_range": true,
  "can_aim": true,
  "disabled_reason": "",
  "is_aimed": false,
  "focus": {
    "lat": 52.1,
    "lng": 21.2,
    "zoom": 17
  },
  "teleport": {
    "lat": 52.1,
    "lng": 21.2,
    "requires_confirm": true
  },
  "raw_ref": {
    "vulnerability_id": null,
    "foreign_area_id": null,
    "target_username": null
  }
}
```

Uwagi:

* `icon` rodzaju obiektu pochodzi z payloadu celu;
* Victim Picker nie tworzy drugiego zestawu ikon bankomatu, kamery, pojazdu czy
  gracza;
* `target_id` musi uzywac obecnej logiki runtime identity, z tolerancja dla
  labela tam, gdzie pozycja jest jedynym stabilnym identyfikatorem.

## Kontrakt ikon UI Victim Pickera

Zamkniety lokalny zestaw ikon powinien obejmowac:

* aplikacja;
* pozycja motocykla;
* zasieg;
* odswiez;
* pokaz na mapie;
* oznacz jako cel;
* aktywny cel;
* teleport;
* w zasiegu;
* poza zasiegiem;
* brak aktualnej pozycji;
* obiekt niedostepny.

Wymagania:

* lokalne SVG albo CSS-only;
* bez zewnetrznej biblioteki z sieci;
* bez mieszania przypadkowych emoji;
* kazdy przycisk ikonowy ma `title`, `aria-label`, tooltip, hover,
  disabled i active state.

## Miejsca wymagajace refaktoru

1. `POST /map-action`
   * `mark_target`, `scan` i `travel` sa w jednym endpointzie;
   * Victim Picker powinien korzystac z istniejacych reguly, ale docelowo warto
     wydzielic helpery do budowania target payloadu.
2. `POST /hack-action`
   * buduje `aimed_target` dla standard, player, vulnerability i
     territory_contest;
   * potrzebuje wspolnego helpera dla przyszlego Victim Pickera, zeby nie
     dublowac konstrukcji `aimed_target`.
3. `GET /api/map/player-actors`
   * juz zawiera relacje i `actions.mark_target`;
   * Victim Picker powinien odczytywac te flagi, nie odtwarzac relacji w JS.
4. `GET /api/map/player-areas`
   * jest ciezkim endpointem mapy;
   * Victim Picker powinien uwazac, zeby nie zwiekszyc presji pollingowej.
5. `GET /api/map/clan-vulnerabilities`
   * source jest gotowy, ale kandydat musi zachowac `vulnerability_id`.
6. Teleport/focus
   * focus mapy powinien pozostac frontendowym mostem;
   * teleport ma isc przez istniejacy endpoint z potwierdzeniem.

## Plan testow regresyjnych

Backend:

* saved target z `profile.targets` tworzy kandydata standard;
* player actor self/friend/same clan nie ma `can_aim`;
* intruder/neutral player actor moze miec `can_aim`;
* player target uzywa `/api/map/player-targets/mark`;
* vulnerability candidate zachowuje `vulnerability_id`;
* territory contest candidate zachowuje `foreign_area_id`;
* distance i range korzystaja z `get_player_action_range`;
* brak `curently_possition` daje `disabled_reason=missing_position`;
* aktywny `aimed_target` daje `is_aimed=true`;
* teleport nie zapisuje pozycji bez potwierdzenia.

Frontend:

* kazdy przycisk ikonowy ma `title` i `aria-label`;
* disabled state blokuje akcje;
* show on map nie teleportuje;
* teleport odpala potwierdzenie;
* refresh nie uruchamia mapy od nowa;
* brak kandydatow pokazuje pusty stan, nie blad.

## Decyzja Sprintu 99

Victim Picker moze powstac dopiero po wydzieleniu wspolnej warstwy kandydatow i
ustawiania celu. Jego pierwsza wersja powinna byc read-only agregatem obecnych
zrodel plus akcje delegowane do istniejacych endpointow. Najwieksze ryzyko to
nie wydajnosc samego okna, tylko przypadkowe odtworzenie logiki mapy w drugim
miejscu.
