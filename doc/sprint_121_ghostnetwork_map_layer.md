# Sprint 121 - GhostNetwork Map Layer

## Cel

Pokazac czesci GhostNetwork na mapie bez dodawania kolejnego ciezkiego pollera.

## Wdrozone

* Dodano readonly endpoint `GET /api/ghostnetwork/snapshot`.
* Endpoint korzysta z `load_profile_readonly(...)` i `GhostNetworkService.get_snapshot_for_viewer(...)`.
* Dodano frontendowy modul `static/js/map/ghostnetwork.js`.
* Dodano lekki styl markerow `static/css/ghostnetwork_map.css`.
* Mapa laduje GhostNetwork jako optional scope po krytycznym bootcie.
* Delta feed dispatchuje scope `ghostnetwork` do otwartej mapy.
* Recovery odswieza tylko warstwe GhostNetwork.

## Zasady bezpieczenstwa

* Frontend renderuje tylko projekcje z `GhostVisibilityService`.
* Frontend nie liczy uprawnien widocznosci.
* Ukryte czesci bez `location_visibility = exact` nie dostaja dokladnego markera.
* Brak `/api/profile` i `sync_session_profile()` w warstwie mapy.
* Brak nowego `setInterval` dla GhostNetwork.

## Poza zakresem

* Polaczenia GhostNetwork.
* Pelny GhostNetwork Suite.
* Supermoce, nagrody, media i GhostSignal.
* Oddzielny publisher delt GhostNetwork poza istniejacym delta feedem.

## Spojnosc z artefaktami

Potwierdzono zgodnosc z:

* `doc/clans_machines.md`,
* `doc/ghostnetwork_architecture.md`,
* Sprintem 120 - projekcja widocznosci.

GhostNetwork pozostaje globalnym modulem swiata. Mapa jest tylko odbiorca
bezpiecznej projekcji.
