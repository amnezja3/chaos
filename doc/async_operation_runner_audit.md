# Sprint 60.5 - Async Operation Runner Audit

## Cel

Wskazac akcje runtime, ktore moga szybko zwracac `operation_id`, a wlasciwa
praca moze konczyc sie w tle.

Sprint 60.5 jest audytem. Nie dodaje workera, nie zmienia endpointow i nie
przebudowuje runtime.

## Metoda audytu

Sprawdzone obszary:

* cykliczne odswiezanie mapy i desktopu,
* endpointy akcji `POST`,
* endpointy generujace ciezkie snapshoty,
* istniejacy perf logging,
* wyniki baseline po Sprintach 55-59.

Najwazniejszy wniosek:

```text
Nie kazdy wolny endpoint jest kandydatem do Async Operation Runnera.
```

Ciezkie endpointy odczytu nalezy przenosic do modelu snapshot + delta feed.
Runner powinien obslugiwac tylko akcje, ktore moga szybko zwrocic
`operation_id`, a wynik dostarczyc pozniej przez system message albo delta event.

## Ciezkie odczyty, ktore NIE sa kandydatem do runnera

| Scope | Endpoint | Trigger | Ciezkie operacje | Klasyfikacja |
| --- | --- | --- | --- | --- |
| map actors | `/api/map/player-actors` | polling 5 s | `sync_session_profile(rebuild_territory=False)`, kontakty, terytoria, pending contact checks | DELTA |
| map areas | `/api/map/player-areas` | polling 10 s | `sync_session_profile(rebuild_territory=False)`, `safe_player_areas`, `refresh_stale_territory_polygons`, `detect_territory_conflicts`, conflict payload | DELTA |
| clan vulnerabilities | `/api/map/clan-vulnerabilities` | polling 10 s | `sync_session_profile(rebuild_territory=False)`, `vulnerability_store.list_active()` | DELTA |
| operations summary | `/api/operations?summary=1` | polling 10 s | readonly profile, `refresh_and_persist_operations`, `refresh_operations_runtime` | DELTA/ACTION cleanup |
| Ghost Exchange | `/api/ghost-exchange` | Browser refresh | `refresh_and_persist_operations`, `refresh_market_runtime`, dashboard payload | DELTA summary, nie runner |

Te endpointy sa wazne dla Fazy G, ale Async Runner nie rozwiaze ich glownego
problemu. One sa odczytem albo kontrolowanym refreshem stanu, nie pojedyncza
akcja gracza do zakolejkowania.

## Endpointy akcji

| Endpoint | Co robi dzis | Czy potrzebuje natychmiastowego payloadu | Czy moze byc queued | Ocena |
| --- | --- | --- | --- | --- |
| `/map-action` | Dodaje/obsluguje akcje mapowe po kliknieciu punktu | Tak, UI oczekuje statusu akcji i walidacji zasiegu | Czesc akcji moze w przyszlosci, ale nie jako v0 | Nie wybierac na v0 |
| `/hack-action` | Waliduje hack, narzedzia, konflikty, target gracza i tworzy operacje | Tak, zwraca blokady, wybor narzedzia albo start operacji | Potencjalnie tylko finalizacja dlugiej pracy, nie start | Nie wybierac na v0 |
| `/api/operations/cancel` | Anuluje aktywna operacje i zwraca nowy stan | Tak | Nie | Nie kandydat |
| `/install-app` | Kupuje aplikacje/produkt, odejmuje HC, zmienia profil/storage/apps | Tak, ekonomia musi byc atomowa dla requestu | Nie dla v0 | Nie kandydat |
| `/api/apps/uninstall` | Odinstalowuje aplikacje i zmienia storage/files | Tak | Nie | Nie kandydat |
| `/api/apps/generate` | Generuje aplikacje, publikuje do katalogu i dodaje project file | Nie zawsze; wynik moze przyjsc pozniej | Tak | Kandydat v1, ryzyko srednie |
| `/api/ghostlab/projects/<project_id>/compile` | Waliduje blueprint i buduje artifact projektu | Nie; wynik compile moze przyjsc pozniej | Tak | Najlepszy kandydat v0 |

## Najlepszy kandydat v0

Najbezpieczniejsza pierwsza akcja do Sprintu 60.6:

```text
POST /api/ghostlab/projects/<project_id>/compile
```

Powody:

* akcja jest samodzielna,
* nie dotyka mapy,
* nie dotyka Ghost Exchange,
* nie dotyka Googleplex economy,
* nie zmienia pozycji gracza ani konfliktow,
* ma naturalny status `queued/running/done/failed`,
* wynik mozna przekazac przez system message albo delta event,
* UI moze pokazac compile jako zadanie w tle.

Minimalny klucz deduplikacji dla przyszlego runnera:

```text
ghostlab_compile:{username}:{project_id}:{blueprint_hash}
```

## Kandydat zapasowy

Drugi kandydat:

```text
POST /api/apps/generate
```

Ten endpoint moze skorzystac z runnera, ale jest bardziej ryzykowny, bo dotyka:

* `resources_store` / katalogu Googleplex,
* `profile.files.projects`,
* widoku katalogu aplikacji.

Dlatego nie powinien byc pierwszym runnerem v0.

## Akcje, ktorych nie przenosic w pierwszym kroku

Nie przenosic w Sprint 60.6:

* `/hack-action`,
* `/map-action`,
* `/install-app`,
* `/api/apps/uninstall`,
* `/api/ghost-exchange`,
* endpointow map polling.

Powody:

* czesc wymaga natychmiastowego payloadu,
* czesc dotyka ekonomii albo storage,
* czesc jest odczytem/snapshotem, a nie akcja,
* czesc jest juz objeta planem delta feed.

## Kontrakt do wznowienia tematu

Jesli temat runnera zostanie wznowiony w przyszlosci, pierwszy sprint
implementacyjny powinien objac tylko jedna akcje.

Minimalny kontrakt requestu:

```json
{
  "success": true,
  "operation_id": "async_...",
  "status": "queued"
}
```

Minimalny kontrakt statusu:

```text
queued
running
done
failed
```

Minimalne zasady:

* runner nie jest drugim systemem operacji,
* runner nie zastepuje `profile.operations`,
* runner nie tworzy drugiego scheduleru gry,
* blad zadania nie zabija requestu,
* podwojne odpalenie tej samej akcji ma byc kontrolowane przez dedupe key,
* jesli runner jest niedostepny albo zadanie nie moze byc zakolejkowane,
  endpoint zwraca kontrolowany blad i nie wykonuje ciezkiej pracy awaryjnie w
  requestcie.

## Ryzyka

* Uzycie runnera do endpointow odczytu zamiast przeniesienia ich na delta feed.
* Przeniesienie ekonomii Googleplex do tla bez atomowej odpowiedzi.
* Zakolejkowanie `/hack-action` i utrata natychmiastowej walidacji.
* Brak deduplikacji i podwojne wykonanie tej samej pracy.
* Cichy fallback do starej synchronicznej pracy, gdy runner jest niedostepny.
* Drugi ukryty system operacji obok istniejacego runtime.

## Kryteria Sprintu 60.5

* Istnieje lista ciezkich endpointow akcji.
* Wiadomo, ktore akcje musza zwracac natychmiastowy wynik.
* Wiadomo, ktore akcje moga zwrocic tylko `operation_id`.
* Wiadomo, ktora akcja jest najlepszym kandydatem na v0.
* Nie zmieniono runtime.

## Status

Sprint 60.5 zamkniety jako audyt.

Audyt wskazal jako technicznie najbezpieczniejsza akcje v0:

```text
GhostLab compile project
```

Po decyzji planistycznej Sprint 60.6 zostal jednak oznaczony jako
cancelled/postponed. Dla jednej samodzielnej akcji koszt wdrozenia runnera,
statusow, deduplikacji i utrzymania osobnego przeplywu async jest wiekszy niz
aktualny zysk runtime.

Temat runnera mozna wznowic, gdy pojawi sie wiecej akcji typu queued job.
