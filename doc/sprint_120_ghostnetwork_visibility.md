# Sprint 120 - GhostNetwork: visibility projection

## Cel

Sprint 120 dodaje jedna bezpieczna projekcje widocznosci danych GhostNetwork dla
wszystkich interfejsow gry.

`GhostVisibilityService` jest teraz miejscem, w ktorym surowy stan czesci,
maszyn, polaczen i komponentow terytorium jest filtrowany dla konkretnego
odbiorcy.

## Zasady

Zrodlem prawdy pozostaja:

* `GhostNetworkRepository`;
* `GhostModuleStateService`;
* obecny system terytoriow;
* katalog GhostNetwork.

Projekcja widocznosci nie zapisuje gameplayu, nie tworzy drugiego stanu i nie
ukrywa danych przez CSS po stronie frontendu.

Ukryte pola sa zwracane jako `None` albo nie sa obecne w projekcji. Dla
ukrytych czesci uzywany jest stabilny `public_entity_id`, zeby nie przeciekal
`part_code`, `part_id` ani `target_id`.

## Wdrozone

* `GhostVisibilityService`;
* `VISIBILITY_VERSION`;
* `build_viewer_projection(...)`;
* kontekst odbiorcy:
  * `viewer_id`,
  * `viewer_clan`,
  * `viewer_profession`,
  * `is_authenticated`,
  * `is_admin`,
  * `audience_scope`;
* poziomy widocznosci:
  * `internal`,
  * `full_public`,
  * `full_owner`,
  * `full_clan`,
  * `active_foreign`,
  * `contained_hidden`;
* projekcje:
  * `project_part_for_viewer(...)`,
  * `project_parts_for_viewer(...)`,
  * `project_connection_for_viewer(...)`,
  * `project_machine_for_viewer(...)`,
  * `project_territory_component_for_viewer(...)`,
  * `project_event_fact_for_audience(...)`;
* snapshot gracza przez `GhostNetworkService.get_snapshot_for_viewer(...)`;
* jawny `cache_key` zalezy od wersji widocznosci, cyklu, state version i
  odbiorcy;
* grupy Suite:
  * `public_parts`,
  * `blocked_parts`,
  * `active_parts`,
  * `self_controlled_parts`,
  * `clan_parts`.

## Widocznosc

Neutralna czesc jest publiczna i pokazuje pelna tozsamosc.

Czesc zablokowana przez obcy klan pokazuje pelna tozsamosc tylko wlascicielowi
terytorium. Czlonkowie klanu wlasciciela i inne klany widza tylko fakt, ze
terytorium zawiera czesc GhostNetwork.

Czesc aktywna pokazuje pelna tozsamosc wlascicielowi terytorium i wlasciwemu
klanowi czesci. Obce klany widza aktywny wezel, lokalizacje i klan, ale bez
kodu czesci, nazwy, profesji, maszyny, ability i target id.

Konflikt zachowuje zamrozony stan widocznosci. `contested` nie podnosi ani nie
obniza uprawnien.

## Poza zakresem

Sprint 120 nie wdraza:

* markerow mapy;
* linii GhostNetwork;
* supermocy;
* nagrod;
* BlackNet bridge;
* Cybernera;
* Radia;
* integracji z Ollama;
* transmisji GhostSignalu.

## Walidacja

Testy pokrywaja:

* neutralna czesc jako `full_public`;
* zablokowana czesc jako `full_owner` dla wlasciciela terytorium;
* ukrycie tozsamosci zablokowanej czesci przed innymi odbiorcami;
* aktywna czesc jako `full_clan` dla wlasciwego klanu;
* aktywna czesc jako `active_foreign` dla obcych klanow;
* konflikt z zachowaniem zamrozonej widocznosci;
* brak rezerwacji i `ring_order` w snapshotach gracza;
* brak ukrytych wartosci w JSON;
* projection dla Territory Control;
* projection dla publicznych faktow mediowych;
* rozdzielenie `cache_key` per odbiorca;
* zachowanie internal recovery dla admina.

