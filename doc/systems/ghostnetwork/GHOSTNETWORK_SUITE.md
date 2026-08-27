# GhostNetwork Suite

## Przeznaczenie

GhostNetwork Suite jest lekkim narzędziem desktopowym do obserwacji maksymalnie
20 viewer-projected części aktywnego cyklu. Nie jest źródłem prawdy gameplayu i
nie ładuje mapy, dopóki operator jawnie nie wybierze akcji przestrzennej.

Źródła prawdy:

- lifecycle, topology i state version: canonical GhostNetwork stores,
- widoczność: `GhostVisibilityService`,
- snapshot aplikacji: `GET /api/ghostnetwork/snapshot?view=suite`,
- live transport: istniejący `GET /api/state/changes`,
- pozycja po teleportacji: canonical player position store.

Suite nie odczytuje pełnego profilu, nie wykonuje profile overlay i nie tworzy
własnego pollera.

## Projekcja i grupy

`parts[]` zawiera jeden rekord na `public_entity_id`. `groups` przechowuje tylko
referencje do tych rekordów:

- `public`,
- `blocked`,
- `clan_active`,
- `self_foreign`,
- `self_own`.

Frontend wylicza liczniki i grupy ponownie po każdej zastosowanej delcie. Nie
scala nowej projekcji ze starą. Cały rekord jest zastępowany, dzięki czemu
zmiana widoczności usuwa wcześniejszą nazwę, kod, profesję, zdolność, asset i
dokładną lokalizację również z modelu pamięciowego.

## Mapa i teleport

Akcje używają wyłącznie opaque targetów wydanych przez backend:

- `ghostnetwork_part` dla dokładnej publicznej pozycji,
- `ghostnetwork_territory` dla części ujawnionej tylko na poziomie terytorium.

Klient nie wysyła współrzędnych. Backend ponownie projektuje widoczność i
rozwiązuje anchor przed zapisem. Fokus mapy nie ustawia `aimed_target` ani
reservation. Mapa jest tworzona wyłącznie po jawnej akcji użytkownika.

## Shared delty

Mapa i Suite używają jednej instancji `GhostNetworkDeltaClient`. Klient działa
bez Leaflet i zapewnia:

- dedupe eventów,
- wspólny cycle/state version,
- osobne baseline `map` i `suite`,
- adapter-specific apply/recovery,
- współdzielony transport `/api/state/changes`.

Backend dołącza do lifecycle eventu zarówno mapową `part_projection`, jak i
odchudzoną `suite_part_projection`. Projekcja Suite powstaje po stronie serwera
z tych samych reguł co snapshot. `ghost.part_consumed` przenosi wyłącznie opaque
`public_entity_id` i flagę `removed`; nie przenosi identity ani coordinates.

## Recovery

Suite pobiera `snapshot?view=suite` przy:

- zmianie cyklu,
- nieznanym identyfikatorze poza discovery,
- luce lub błędzie zastosowania delty,
- zbiorczych zmianach topology/cycle,
- recovery wymaganym przez desktopowy delta feed.

Recovery jest koaleskowane i ma ograniczony backoff. Zachowuje filtr, query,
scroll, fokus wyszukiwarki oraz rozwinięte szczegóły istniejących kart. Nie
otwiera mapy i nie odtwarza lifecycle SFX.

## Lifecycle okna

Jedno otwarte okno posiada jeden adapter. Zamknięcie:

- wyrejestrowuje adapter,
- usuwa callback recovery i position refresh,
- anuluje retry timer,
- nie niszczy współdzielonego klienta używanego przez mapę.

Restart/lock GhostSystemu blokuje akcje starego cyklu. Aktywacja lub zmiana
wersji wymusza świeży snapshot zamiast reaktywowania starych opaque targetów.

## Kontrakt bezpieczeństwa

Ukryte dane nie mogą pozostać w JSON Suite, modelu JS, DOM, datasetach,
tooltipach, `aria-label`, logach, bridge mapy ani payloadzie teleportu.
Snapshot, delta i recovery są viewer-projected. Frontend nie jest granicą
autoryzacji.

