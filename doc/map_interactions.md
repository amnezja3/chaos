# Map Interactions Runtime Contract

Ten dokument opisuje zasade utrzymania interaktywnych obiektow mapy CHAOS.
Powstal po debugowaniu buga, w ktorym player actor, terytoria i scan targety
potrafily mieszac menu, tooltipy i obsluge prawego klikniecia.

## Zasada glowna

Kazdy interaktywny obiekt mapy musi byc calkowicie samodzielny.

Dotyczy to w szczegolnosci:

- player actorow,
- scan targetow,
- hacked targetow,
- vulnerability markerow,
- territory markerow,
- conflict pillars,
- captured targets,
- aktywnych operacji.

## Wymagania dla obiektu mapy

Kazdy typ obiektu powinien miec:

- wlasny registry,
- wlasny cleanup,
- wlasny snapshot danych,
- wlasny hitbox,
- wlasne menu,
- wlasna sciezke eventow.

Obiekt nie powinien:

- uzywac globalnego `currentTarget` jako zrodla prawdy dla menu,
- mutowac wspolnego obiektu danych przekazanego do innych warstw,
- zostawiac starych listenerow po refreshu,
- zostawiac tooltipow/popupow po usunieciu warstwy,
- udawac klikniecia w mape,
- udawac klikniecia w inny obiekt,
- delegowac swojego menu do menu innego typu obiektu.

## Event routing

Prawy klik na markerze powinien obslugiwac tylko ten marker.

Prawy klik na pustej mapie powinien obslugiwac tylko mapa.

Jezeli Leaflet blednie odpali handler markera mimo klikniecia poza realnym
hitboxem, handler markera musi najpierw odrzucic event na podstawie geometrii
DOM, np. `getBoundingClientRect()`.

Protezy przeliczajace event na menu mapy sa dopuszczalne tylko jako defensywny
airbag przy blednym routingu Leafleta. Nie powinny stawac sie glowna sciezka
architektury.

## Registry i cleanup

Kazdy typ warstwy powinien miec osobny registry, np.:

- `playerActorMarkers`,
- `playerAreas`,
- `conflictAreas`,
- `contestedTargets`,
- `capturedConflictPillars`.

Przed ponownym renderem nalezy:

- zamknac tooltip/popup,
- odpiac tooltip/popup,
- odpiac event listenery,
- usunac warstwe z mapy,
- wyczyscic registry.

Samo nadpisanie tablicy nie wystarcza, bo stara warstwa Leafleta moze nadal
istniec na mapie i przejmowac hover/contextmenu.

## Snapshot danych

Handler menu powinien dostac snapshot danych kliknietego obiektu.

Nie nalezy czytac menu z danych, ktore mogly zostac nadpisane przez pozniejszy
refresh mapy albo przez inny typ obiektu.

Rekomendowane:

- `structuredClone()` jesli dostepne,
- defensywna plain-copy,
- `Object.freeze()` dla obiektow menu, jesli ma to sens diagnostycznie.

## Hitbox

Kazdy marker `L.divIcon` powinien miec jawny rozmiar:

- `iconSize`,
- `iconAnchor`,
- root wrapper o stalej szerokosci i wysokosci,
- `overflow: hidden`,
- brak elementow wychodzacych poza marker,
- kontrolowane `pointer-events`.

Label, badge i avatar nie powinny powiekszac klikalnego obszaru poza marker.

## UI

Nie kazdy obiekt potrzebuje tooltipa.

Player actor ma juz label nad avatarem i menu pod prawym klikiem, wiec dodatkowy
tooltip `Nick / Znajomy` jest zbedny i moze tylko zwiekszac szum eventow.

## Decision

Mapa CHAOS bedzie rozwijana jako zestaw samodzielnych interaktywnych warstw.
Kazda warstwa odpowiada za wlasny runtime, cleanup i menu. Wspolne helpery sa
dopuszczalne, ale nie moga mieszac tozsamosci obiektow.
