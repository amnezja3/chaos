# Sprint 56 - State Version Contract

Data: 2026-07-06

Status: contract v0

Cel: opisac wersjonowanie obecnych modeli stanu bez tworzenia nowego magazynu
stanu i bez migracji frontendu na delty.

## Zasada glowna

Wersje opisuja istniejace modele i snapshoty.

Wersje nie tworza nowego zrodla prawdy.

Wersje nie sa liczone z delta busa.

Delta bus, kiedy powstanie, bedzie dziennikiem powiadomien o zmianach. Nie
bedzie miejscem liczenia aktualnego stanu gry.

## Definicje

```text
state_version
```

Globalna wersja logicznego snapshotu runtime dla danego profilu/gracza.

`state_version` jest przydatne jako szybka informacja, ze cokolwiek istotnego
w runtime moglo sie zmienic.

```text
*_version
```

Wersja per scope. Opisuje ostatnia znana zmiane konkretnego obszaru read modelu,
np. portfela, storage albo mapy.

Frontend moze w przyszlosci porownywac wersje per scope i pobierac tylko ten
snapshot, ktory faktycznie wymaga recovery.

## Scope versions v0

| Version field | Scope | Zrodlo prawdy | Co oznacza zmiana |
| --- | --- | --- | --- |
| `state_version` | global | obecne modele profilu/runtime | dowolna istotna zmiana runtime |
| `wallet_version` | wallet | wallet/profil HC | zmiana salda HC albo waluty |
| `profile_version` | profile | profil gracza po normalizacji template | zmiana danych profilu widocznych dla UI |
| `storage_version` | storage | `storage_capacity`, `storage_used`, `file_size`, `profile.files` | zmiana zajetosci lub pojemnosci dysku |
| `apps_version` | apps | `profile.apps`, `files.tools`, katalog Googleplex | install, uninstall, status/cooldown aplikacji |
| `mail_version` | mail | `mail_store`, `system_messages` jako zrodla komunikacji | unread, thread, pending, kanal, nowa wiadomosc |
| `ghost_exchange_version` | Ghost Exchange | `profile.files`, `files.market`, `profile.market_history` | queue, listed, sold, summary, transakcja |
| `operations_version` | operations | operations runtime w profilu | start, postep, finalizacja, anulowanie operacji |
| `map_version` | map | modele mapy, territory store, actors, targets, conflicts | zmiana aktorow, targetow, obszarow, konfliktow |

## Potencjalne miejsca zwracania wersji

Sprint 56 nie zmienia payloadow runtime. Ponizsza tabela opisuje kontrakt, gdzie
wersje moga zostac dodane w pozniejszych sprintach bez zmiany znaczenia
istniejacych danych.

| Endpoint snapshot | Mozliwe wersje | Uwagi |
| --- | --- | --- |
| `GET /api/profile` | `state_version`, `profile_version`, `wallet_version`, `storage_version`, `apps_version`, `operations_version` | ciezki snapshot profilu; wersje nie powinny wymuszac dodatkowego sync |
| `GET /api/wallet` | `state_version`, `wallet_version` | lekki snapshot wallet |
| `GET /api/ghost-exchange` | `state_version`, `ghost_exchange_version`, `wallet_version`, `storage_version` | endpoint moze uruchamiac kontrolowany refresh rynku |
| `GET /api/mail/bootstrap` | `state_version`, `mail_version` | lista rozmow, kanalow, pending i unread |
| `GET /api/chats/messages` | `state_version`, `mail_version` | konkretny thread; odczyt moze zmieniac unread |
| `GET /system-messages` | `state_version`, `mail_version` | system messages jako sygnal/toast, nie osobny inbox |
| `GET /api/operations?summary=1` | `state_version`, `operations_version`, `storage_version`, `wallet_version` | finalizacja operacji moze dotknac storage/wallet |
| `GET /api/map/player-actors` | `state_version`, `map_version` | aktorzy mapy |
| `GET /api/map/player-areas` | `state_version`, `map_version` | terytoria, konflikty, contested targets |
| `GET /api/map/clan-vulnerabilities` | `state_version`, `map_version` | podatnosci klanowe |
| `GET /launch-queue` | `state_version`, `apps_version` | kolejka odpalenia aplikacji |

## Zasady generowania wersji

1. Wersja rosnie po zapisie do zrodla prawdy, nie przed zapisem.
2. Wersja opisuje snapshot po normalizacji danego modelu.
3. Zmiana jednego scope nie musi podbijac wszystkich wersji.
4. `state_version` moze rosnac razem z dowolna wersja scope.
5. Wersja scope musi byc monotoniczna dla danego profilu/gracza.
6. Wersje nie sluza do odtwarzania stanu. Do odtwarzania sluzy snapshot.
7. Jesli frontend ma wersje spoza retencji przyszlego delta feedu, backend ma
   wskazac recovery snapshotu.

## Minimalny read model wersji

W przyszlym lekkim endpointzie albo polu snapshotu wersje moga miec ksztalt:

```json
{
  "state_version": 391,
  "versions": {
    "wallet": 48,
    "profile": 120,
    "storage": 77,
    "apps": 44,
    "mail": 233,
    "ghost_exchange": 91,
    "operations": 65,
    "map": 1842
  }
}
```

Kontrakt v0 dopuszcza rowniez plaskie pola:

```json
{
  "state_version": 391,
  "wallet_version": 48,
  "profile_version": 120,
  "storage_version": 77,
  "apps_version": 44,
  "mail_version": 233,
  "ghost_exchange_version": 91,
  "operations_version": 65,
  "map_version": 1842
}
```

Decyzja implementacyjna dla Sprintow 58-59 moze wybrac jeden z wariantow, ale
semantyka pozostaje taka sama.

## Poza zakresem Sprintu 56

* brak migracji frontendu,
* brak `applyDelta()`,
* brak delta busa,
* brak `/api/state/changes`,
* brak wylaczania pollerow,
* brak nowych endpointow,
* brak zmiany zachowania snapshotow.

## Kryteria Sprintu 56

* Istnieje kontrakt `state_version`.
* Istnieja wersje per scope:
  * `wallet_version`,
  * `profile_version`,
  * `storage_version`,
  * `apps_version`,
  * `mail_version`,
  * `ghost_exchange_version`,
  * `operations_version`,
  * `map_version`.
* Wiadomo, ze wersje opisuja obecne modele i snapshoty.
* Wiadomo, gdzie snapshot endpointy moga zwracac wersje.
* Frontend nie zostal zmieniony.
* Pollery nie zostaly wylaczone.

