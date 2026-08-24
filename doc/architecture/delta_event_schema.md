# Sprint 57 - Delta Event Schema

Data: 2026-07-06

Status: contract v0

Cel: zdefiniowac stabilny format eventow delta v0 przed implementacja
`GameStateDeltaBus`.

Sprint 57 nie implementuje zapisu eventow, endpointu delt ani frontendowego
`applyDelta()`.

## Zasada glowna

Event delta opisuje zmiane, ktora juz zaszla w istniejacym zrodle prawdy.

Event delta nie jest zrodlem prawdy.

Event delta nie przechowuje pelnego snapshotu.

Jesli frontend zgubi ciaglosc wersji albo nie potrafi zastosowac eventu, musi
wrocic do snapshotu danego scope.

## Struktura eventu

```json
{
  "version": 1845,
  "scope": "wallet",
  "type": "wallet.balance_changed",
  "entity_id": "wallet",
  "dedupe_key": "wallet:balance:root:1845",
  "payload": {
    "balance": 17044,
    "currency": "HC"
  },
  "created_at": "2026-07-06T12:00:00Z"
}
```

## Pola

| Pole | Typ | Wymagane | Znaczenie |
| --- | --- | --- | --- |
| `version` | number | tak | monotoniczna wersja eventu dla profilu/gracza |
| `scope` | string | tak | obszar stanu, np. `wallet`, `storage`, `map` |
| `type` | string | tak | typ eventu w formacie `scope.action` |
| `entity_id` | string | tak | identyfikator konkretnego obiektu albo licznika |
| `dedupe_key` | string | tak | stabilny klucz idempotencji |
| `payload` | object | tak | minimalne dane potrzebne do aktualizacji UI |
| `created_at` | string ISO | tak | czas utworzenia eventu |

## Idempotencja

`dedupe_key` musi jednoznacznie identyfikowac event.

Frontend powinien pamietac zastosowane `dedupe_key` w biezacej sesji albo w
ramach aktywnego delta window.

Zastosowanie tego samego eventu drugi raz:

* nie moze podwoic salda,
* nie moze podwoic transakcji,
* nie moze zdublowac ikony aplikacji,
* nie moze zdublowac unread badge,
* nie moze utworzyc drugiego markera mapy.

Event powinien byc projektowany jako ustawienie stanu docelowego albo
aktualizacja konkretnej encji, a nie jako niekontrolowane "dodaj jeszcze raz".

## Payload nie jest snapshotem

`payload` ma byc najmniejszym zestawem danych potrzebnym do aktualizacji widoku.

Payload nie moze byc:

* pelnym profilem,
* pelnym `profile.files`,
* pelnym dashboardem Ghost Exchange,
* pelna lista rozmow,
* pelna mapa,
* pelna lista aplikacji, jesli event dotyczy jednej aplikacji.

Snapshoty pozostaja osobna sciezka startu i recovery.

## Nazewnictwo typow

Format:

```text
scope.action
```

Przyklady:

```text
wallet.balance_changed
storage.used_changed
storage.capacity_changed
apps.app_installed
apps.app_uninstalled
apps.cooldown_changed
mail.unread_changed
mail.thread_updated
ghost_exchange.summary_changed
ghost_exchange.transaction_added
operations.operation_updated
operations.operation_completed
map.player_moved
map.player_actor_updated
map.target_updated
map.area_claimed
```

Nazwy typow sa stabilnym kontraktem. Nie powinny zalezec od tekstu UI ani nazwy
wyswietlanej.

## Minimalne payloady v0

### `wallet.balance_changed`

```json
{
  "balance": 17044,
  "currency": "HC"
}
```

`entity_id`: `wallet`

### `storage.used_changed`

```json
{
  "used": 383,
  "capacity": 768,
  "unit": "MB",
  "over_limit": false
}
```

`entity_id`: `storage`

### `storage.capacity_changed`

```json
{
  "used": 383,
  "capacity": 1024,
  "unit": "MB",
  "over_limit": false
}
```

`entity_id`: `storage`

### `apps.app_installed`

```json
{
  "app_id": "ghost_hack_radio",
  "name": "Ghost Hack Radio",
  "icon": "/static/icons/ghost_hack_radio.svg",
  "source": "googleplex"
}
```

`entity_id`: app id

### `apps.app_uninstalled`

```json
{
  "app_id": "xmapper"
}
```

`entity_id`: app id

### `mail.unread_changed`

```json
{
  "scope": "direct",
  "peer": "ZeroCool",
  "unread": 2
}
```

`entity_id`: stable thread id, e.g. `direct:ZeroCool`

### `mail.thread_updated`

```json
{
  "scope": "channel",
  "peer": "clan:ghosts",
  "source": "clan",
  "last_message_at": "2026-07-06T12:00:00Z",
  "unread": 1
}
```

`entity_id`: stable thread id

### `ghost_exchange.summary_changed`

```json
{
  "pending_files": 1,
  "pending_mb": 13,
  "listed_batches": 0,
  "hc_today": 782,
  "hc_total": 7961
}
```

`entity_id`: `ghost_exchange:summary`

### `ghost_exchange.transaction_added`

```json
{
  "transaction_id": "market_batch_network_20260706_001",
  "sector": "network",
  "files": 10,
  "volume_mb": 100,
  "hc": 782,
  "sold_at": "2026-07-06T12:00:00Z"
}
```

`entity_id`: transaction id

### `operations.operation_updated`

```json
{
  "operation_id": "op_20260704184243_766932",
  "status": "active",
  "remaining_seconds": 120,
  "progress_percent": 64
}
```

`entity_id`: operation id

### `operations.operation_completed`

```json
{
  "operation_id": "op_20260704184243_766932",
  "status": "completed",
  "created_files": 2
}
```

`entity_id`: operation id

### `map.player_moved`

```json
{
  "player_id": "ZeroCool",
  "lat": 52.2297,
  "lng": 21.0122
}
```

`entity_id`: player id

### `map.player_actor_updated`

```json
{
  "player_id": "ZeroCool",
  "lat": 52.2297,
  "lng": 21.0122,
  "relation": "friend",
  "status": "online"
}
```

`entity_id`: player id

### `map.target_updated`

```json
{
  "target_id": "node_77",
  "status": "captured",
  "owner": "root"
}
```

`entity_id`: target id

### `map.area_claimed`

```json
{
  "area_id": "area_123",
  "owner_username": "root",
  "status": "active"
}
```

`entity_id`: area id

## Dedupe key format v0

Rekomendowany format:

```text
scope:type:entity_id:version
```

Przyklady:

```text
wallet:wallet.balance_changed:wallet:1845
storage:storage.used_changed:storage:1846
ghost_exchange:ghost_exchange.transaction_added:market_batch_network_20260706_001:1847
map:map.player_moved:ZeroCool:1848
```

## Poza zakresem Sprintu 57

* brak `GameStateDeltaBus`,
* brak zapisu eventow,
* brak `/api/state/changes`,
* brak frontendowego `applyDelta()`,
* brak wylaczania pollerow,
* brak migracji snapshotow.

