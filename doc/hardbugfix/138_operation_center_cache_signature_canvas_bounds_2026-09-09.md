# Hardbugfix 138 — Operation Center cache signature i Canvas bounds race

Status: `IMPLEMENTED / LOCAL PASS / SERVER-DEVICE REVALIDATION PENDING`

## Objawy

- operacje uruchomione na markerach skanu, konfliktu i publicznych
  podatnościach działały w runtime, ale nie pojawiały się w Centrum Operacji;
- po reloadzie panel pozostawał praktycznie pusty albo zwijał się do minimalnej
  wysokości;
- konsola zgłaszała `ReferenceError: cacheSignature is not defined` w
  `renderActiveOperationsPanel`;
- podczas hover/click Canvas pojawiał się również historyczny błąd Leafleta
  `Bounds.js: Cannot read properties of undefined (reading 'x')`.

Komunikat przeglądarki o zamkniętym kanale asynchronicznego listenera pochodzi z
rozszerzenia przeglądarki i nie należy do tego przepływu aplikacji.

## Przyczyna Centrum Operacji

Po `.op.2` w szablonie istniała starsza oraz nowa definicja
`renderActiveOperationsPanel`. Aktywna wersja incremental umieszczała
`cacheSignature` w `data-operation-render-signature`, ale nie tworzyła tej
zmiennej w callbacku `active.map(...)`.

Pierwszy aktywny rekord przerywał cały renderer. Przez to nie wykonywało się
również dalsze uzgodnienie markerów wywoływane po panelu. Backend i runtime
operacji pozostawały poprawne.

## Przyczyna Bounds.js

Historyczny fix chronił `Polyline._clipPoints`, ale aktualny wyjątek powstawał
w późniejszym hit-teście wspólnego renderera Canvas:

```text
Canvas._handleMouseHover / Canvas._onClick
  -> Polygon._containsPoint
  -> Bounds.contains
  -> undefined.x
```

W trakcie atomowej wymiany/LOD warstwy krótko istnieje klatka, w której obiekt
jest jeszcze w indeksie interaktywnym Canvas, a jego `_pxBounds` albo bounds
renderera są już niedostępne.

## Poprawka

- aktywny renderer kart wylicza `cacheId` i `cacheSignature` lokalnie dla każdej
  operacji przed użyciem;
- zachowano incremental DOM: niezmienione karty nie są odtwarzane, countdown
  nadal aktualizuje tylko text node;
- guard Leafleta obejmuje teraz także `Polyline._containsPoint` i własną
  implementację `Polygon._containsPoint`;
- nieważne bounds kończą hit-test wynikiem `false`, uruchamiają ograniczone
  recovery/redraw i nie przerywają obsługi mapy;
- prawidłowe bounds nadal delegują do oryginalnej implementacji Leafleta;
- wyjątki niezwiązane z przejściowym brakiem bounds nie są ukrywane.

## Korekta po teście urządzenia

Pierwsza wersja ograniczała ostrzeżenia osobno dla każdej warstwy. Przy wielu
poliliniach oznaczało to nadal lawinę wpisów w konsoli, mimo że każdy pojedynczy
obiekt raportował błąd najwyżej raz na pięć sekund. Raportowanie jest teraz
agregowane dla całej instancji mapy: pierwszy przechwycony wyścig jest widoczny
od razu, a następne raporty pojawiają się najwyżej raz na 30 sekund i zawierają
liczbę zdarzeń oraz sumę od uruchomienia mapy. Fail-closed hit-test i bounded
recovery pozostają bez zmian.

## Regresja

- test wykonawczy Canvas sprawdza invalid oraz valid `_containsPoint`;
- kontrakt szablonu wymaga lokalnej deklaracji `cacheSignature` przed jej
  użyciem w aktualnym rendererze;
- map loader, interaction fast path, snapshot i marked-target hot path:
  `41/41 PASS`;
- JS map renderer: `PASS`;
- operation cancel dispatch oraz feedback composer: `PASS`.

## Server/device gate

Po deployu należy uruchomić operacje kolejno na markerze skanu/konfliktu oraz
publicznej podatności innego gracza. Obie muszą natychmiast pojawić się w
Centrum Operacji. Następnie reload mapy, hover/click/pan/zoom na desktopie i
mobile nie mogą zwijać panelu ani generować `cacheSignature` lub `Bounds.js`.
