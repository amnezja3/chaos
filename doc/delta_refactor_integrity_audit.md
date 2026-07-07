# Sprint 70 - Delta Refactor Integrity Audit

## Cel

Przejsc jeszcze raz miejsca zmienione w Fazie G i potwierdzic, ze delta-feed,
recovery, snapshoty oraz stare pollery pozostaja spojne.

Sprint 70 nie dodaje nowego scope delta-feed. Audyt szuka protez, ukrytych
pelnych refreshy, podwojnych aktualizacji UI i niespojnosci miedzy dokumentacja
a runtime.

## Zakres sprawdzony

Sprawdzono:

* helpery `record_*_delta`,
* typy eventow delta,
* `applyDelta()`,
* recovery per scope,
* `/api/state/changes`,
* delta diagnostics,
* pozostale `fetch('/api/profile')` w frontendzie,
* snapshoty mail/Ghost Exchange/map,
* testy wallet/storage/apps/mail/GX/map actors/map targets,
* dokumentacje Fazy G.

## Helpery delta

| Helper | Scope | Eventy | Status |
| --- | --- | --- | --- |
| `record_wallet_balance_delta` | `wallet` | `wallet.balance_changed` | OK |
| `record_storage_delta` | `storage` | `storage.used_changed`, `storage.capacity_changed` | OK |
| `record_apps_delta` | `apps` | `apps.app_installed`, `apps.app_uninstalled`, `apps.status_changed`, `apps.cooldown_changed` | OK |
| `record_mail_delta` / `record_mail_thread_update` | `mail` | `mail.unread_changed`, `mail.thread_updated` | OK |
| `record_ghost_exchange_delta` | `ghost_exchange` | `ghost_exchange.summary_changed`, `ghost_exchange.transaction_added` | OK |
| `record_map_player_actor_delta` | `map` | `map.player_moved`, `map.player_actor_updated`, `map.player_actor_removed` | OK |
| `record_map_target_delta` | `map` | `map.target_updated`, `map.target_captured`, `map.target_removed` | OK |

Kazdy helper zapisuje event przez `GameStateDeltaBus.record_change(...)`.
Eventy maja:

* `scope`,
* `type`,
* `entity_id`,
* `dedupe_key`,
* `payload`,
* `created_at`.

Delta bus pozostaje dziennikiem zmian, nie zrodlem prawdy.

## applyDelta

`applyDelta()` obsluguje:

* wallet przez `updateWalletBalanceView(...)`,
* storage przez `updateStorageView(...)`,
* apps przez `updateAppsView(...)`,
* mail przez `updateCybernerDeltaViews(...)`,
* Ghost Exchange przez `updateGhostExchangeDeltaViews(...)`,
* map player actors przez `applyMapPlayerActorDelta(...)`,
* map targets przez `applyMapTargetDelta(...)`.

Idempotencja frontendu dziala przez `processedDeltaKeys` i `dedupe_key`.

Nie znaleziono drugiego delta managera ani osobnego cache stanu.

## Recovery

Recovery pozostaje per scope:

| Scope | Recovery |
| --- | --- |
| `wallet` / `profile` | `/api/profile` |
| `storage` | `/api/profile` |
| `apps` | `/api/profile` |
| `mail` | `/api/mail/bootstrap` |
| `ghost_exchange` | `/api/ghost-exchange` |
| `map` | map iframe recovery: target snapshot + player actors snapshot |

### Poprawka Sprintu 70

Przed audytem recovery mapy mialo nazwe `recoverMapPlayerActorsDeltaScope()`,
ale po Sprint 68.5 scope `map` obejmuje juz player actors i targety.

Problem:

```text
refreshMapTargetSnapshot()
↓
return
↓
refreshPlayerActors() nie zawsze bylo wolane
```

Poprawka:

* zmieniono helper na `recoverMapDeltaScope()`,
* recovery mapy probuje odswiezyc target snapshot,
* recovery mapy probuje odswiezyc player actors snapshot,
* brak globalnego reloadu strony.

## Ukryte pelne refreshy

Usunieto trzy zbedne frontendowe odswiezenia `/api/profile`:

* `loadExchange()` po otrzymaniu `balance`,
* legacy `sellGhostExchangeFile(...)` po otrzymaniu `balance`,
* `transferWallet(...)` po otrzymaniu `balance`.

Te miejsca aktualizuja teraz saldo lokalnie albo czekaja na delta-feed.

Pozostale `getUserProfile()` / `/api/profile` sa nadal dopuszczalne jako:

* startowy snapshot,
* recovery,
* otwarcie ekranow wymagajacych pelnego profilu,
* flow poza aktualnym zakresem delt, np. czesc akcji narzedzi/operacji.

## Snapshoty i stare pollery

Snapshot endpointy nadal istnieja:

* `/api/profile`,
* `/api/mail/bootstrap`,
* `/api/ghost-exchange`,
* `/api/map/player-actors`.

Stare ciezkie pollery nie zostaly usuniete, jesli nie maja pelnego replacement:

* `/api/map/player-areas`,
* `/api/map/clan-vulnerabilities`,
* `/api/operations?summary=1`,
* `/system-messages`,
* `/launch-queue`.

## Test coverage

Istniejace testy pokrywaja:

* kontrakt eventu delta,
* idempotencje `dedupe_key`,
* `/api/state/changes`,
* delta diagnostics bez `sync_session_profile()`,
* wallet delta,
* storage delta,
* apps delta,
* mail delta,
* Ghost Exchange delta,
* map player actor delta,
* map target delta.

## Wynik audytu

Sprint 70 potwierdza, ze Faza G pozostaje spojna:

* eventy maja spojny kontrakt,
* delta bus nie stal sie drugim magazynem stanu,
* `applyDelta()` aktualizuje punktowo,
* recovery dziala per scope,
* snapshoty zostaja jako start/recovery,
* nie usunieto starych endpointow snapshotowych.

Do dalszej obserwacji:

* `refreshMapTargetSnapshot()` nadal jest map iframe snapshotem, nie lekkim
  dedykowanym endpointem targetow.
* `map player areas`, `clan vulnerabilities` i `operations summary` nadal sa
  glowne ciezkie obszary poza delta replacement.
