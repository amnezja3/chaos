# Sprint 69 - Poller Thinning / Retirement

Data: 2026-07-07

Status: v0 complete

## Cel

Zmniejszyc liczbe cyklicznych requestow po potwierdzeniu, ze pierwsze scope'y
dzialaja przez delta-feed/recovery:

* wallet,
* storage,
* apps,
* mail/Ghost Exchange summary,
* player actors,
* target registry / target delta v0.

Sprint 69 nie usuwa endpointow snapshotowych. Snapshoty zostaja jako start i
recovery.

## Zasady

* Pollery wylaczane albo ograniczane sa pojedynczo.
* Nie ma globalnego reloadu jako normalnej sciezki odswiezania.
* Endpointy snapshotowe zostaja.
* Scope bez pelnego delta replacement zostaje przy dotychczasowym pollingu.

## Zmienione pollery

| Scope | Endpoint | Przed | Po | Powod |
| --- | --- | --- | --- | --- |
| Cyberner thread list | `/api/mail/bootstrap` | 3000 ms | 10000 ms | unread/thread summary ma delta-feed, bootstrap zostaje snapshot/recovery |
| Map player actors | `/api/map/player-actors` | 5000 ms | 30000 ms | `map.player_*` dziala przez delta-feed, endpoint zostaje snapshot/recovery |

## Pollery zostawione bez zmian

| Scope | Endpoint | Interwal | Powod |
| --- | --- | --- | --- |
| Map player areas | `/api/map/player-areas` | 10000 ms | nadal najciezsza warstwa, ale nie ma jeszcze area delta |
| Clan vulnerabilities | `/api/map/clan-vulnerabilities` | 10000 ms | vulnerability layers nie sa jeszcze migrowane |
| Active operations | `/api/operations?summary=1` | 10000 ms | operations summary nadal jest ciezkim snapshotem |
| System messages | `/system-messages` | 10000 ms | notification bridge nie zastapil jeszcze tego pollera |
| Launch queue | `/launch-queue` | 10000 ms | pozostaje action/snapshot flow |
| State delta feed | `/api/state/changes` | 4000 ms | glowny lekki feed zmian |

## Request count przed/po

Szacunek statyczny dla jednego otwartego okna mapy i jednego otwartego Cybernera:

| Request | Przed / min | Po / min | Zmiana |
| --- | ---: | ---: | ---: |
| `/api/mail/bootstrap` | 20 | 6 | -14 |
| `/api/map/player-actors` | 12 | 2 | -10 |
| `/api/map/player-areas` | 6 | 6 | 0 |
| `/api/map/clan-vulnerabilities` | 6 | 6 | 0 |
| `/api/operations?summary=1` | 6 | 6 | 0 |
| `/system-messages` | 6 | 6 | 0 |
| `/launch-queue` | 6 | 6 | 0 |
| `/api/state/changes` | 15 | 15 | 0 |

Oczekiwany spadek w tej konfiguracji:

```text
68 requestow / min
↓
44 requesty / min
```

To daje okolo 35% mniej cyklicznych requestow w tej konkretnej konfiguracji.

## Czas odpowiedzi przed/po

Sprint 69 zapisuje kontrakt pomiaru, ale nie udaje pomiaru produkcyjnego.

Do checkpointu live nalezy zapisac:

* sredni czas `/api/mail/bootstrap` przed/po,
* max czas `/api/mail/bootstrap` przed/po,
* sredni czas `/api/map/player-actors` przed/po,
* max czas `/api/map/player-actors` przed/po,
* recovery_count po zmianie,
* subiektywne lagi mapy i Cybernera.

## Recovery

* Mail recovery zostaje przez `/api/mail/bootstrap`.
* Map actor recovery zostaje przez `/api/map/player-actors`.
* Target recovery zostaje przez snapshot mapy.
* Delta feed nadal uzywa `recovery_required` i scope recovery.

## Ryzyka

* Aktywny Cyberner moze widziec pelna tresc wiadomosci z opoznieniem do 10 s,
  jesli nie przyszla delta summary albo watek nie zostal otwarty.
* Player actor marker moze skorygowac sie snapshotem dopiero po 30 s, jesli
  delta zostanie zgubiona i nie wymusi recovery.
* Glowne lagi mapy moga pozostac, bo player areas, clan vulnerabilities i
  operations summary nadal pracuja co 10 s.

## Status

Poller thinning v0 wykonany. Endpointy snapshotowe zostaja, a najciezsze
nierozmigrowane pollery mapy pozostaja bez zmian do kolejnych sprintow.
