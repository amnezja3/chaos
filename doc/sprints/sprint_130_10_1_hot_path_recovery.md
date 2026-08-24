# Sprint 130.10.1 — Hot Path Recovery

Data realizacji lokalnej: 2026-08-23.

Status: `SPRINT 130.10.1 — COMPLETE`.

## Cel

Odzyskać wydajność sprzed Sprintu 130.10 bez cofania profile integrity,
revision/CAS, checksum, LKG, recovery ani izolacji generacji sesji. Sprint zmienia
wyłącznie ścieżki wykonania. Nie zmienia payloadów API, mechaniki, animacji,
timingów OFS, canonical stores ani formatu profilu.

## Potwierdzona regresja

Po Sprintcie 130.10 zwykły `UserStore.get_profile()` stał się aliasem pełnego
`get_profile_with_revision()`. Każdy runtime read parsował i walidował pełny
schemat, liczył checksumę i kopiował cały profil. Guarded writers wykonywały
overlay, walidację, serializację i przygotowanie LKG pod `BEGIN IMMEDIATE`.

Skutek był proporcjonalny do rozmiaru konta i wzmacniany przez globalny writer
lock SQLite. `Secret Path` czekał na `/api/map/aim-target`, a jedno użycie
narzędzia wykonywało dwa zachowane, szeregowane requesty `/gonna-win`.

## Zrealizowane zmiany

1. `UserStore.get_profile()` jest lekkim runtime read:
   - wykonuje jeden odczyt `profile_json`;
   - odrzuca malformed JSON, niepoprawny root, złą tożsamość i trwały status
     recovery;
   - nie wykonuje pełnej walidacji schematu, checksumy ani `deepcopy`;
   - jawny `get_profile_with_revision()` pozostaje pełnym integrity/audit path.
2. `/api/map/aim-target`:
   - używa małej identity projection;
   - odczytuje i zapisuje wybór wyłącznie przez `PlayerTargetRuntimeStore`;
   - nie wykonuje full-profile read/write ani compatibility mirror write;
   - aktualizuje istniejący cache sesji bez zastępowania go sparse profilem.
3. `/gonna-win`:
   - zachowuje dwa requesty i `gonnaWinRequestQueue`;
   - `operation_only` oraz częściowe wyniki narzędzi zapisują target i operacje w
     canonical runtime stores bez `UserProfileManager` i pełnego profilu;
   - właściwy trwały capture nadal wykonuje pojedynczy guarded profile patch;
   - monotoniczny merge postępu korzysta z `PlayerTargetRuntimeStore`, nie z
     compatibility projection w profilu.
4. `UserProfileManager`:
   - nie skanuje wszystkich profili w konstruktorze ani po każdym zapisie;
   - domyślny `UserStore` jest współdzielony w procesie, więc `init_db()` nie
     wykonuje się przy każdym utworzeniu managera;
   - jawne ładowanie listy pozostaje tylko dla operacji, które faktycznie go
     potrzebują.
5. Guarded profile writes:
   - parse, canonical overlay, walidacja, destructive assessment, checksum,
     serializacja i przygotowanie LKG odbywają się przed writer-lockiem;
   - pod `BEGIN IMMEDIATE` pozostają recheck revision/checksum/status,
     session precommit guard, CAS write, atomowy zapis przygotowanego LKG i
     commit;
   - patch bez jawnej rewizji ma ograniczony retry po konkurencyjnej zmianie.
6. GhostNetwork:
   - event hooks korzystają z jednego process-local `GhostNetworkService`;
   - schema readiness jest wykonywane raz przy utworzeniu usługi, a nie przy
     każdym evencie.
7. Telemetria:
   - `/api/map/aim-target` dołączono do `PERF_LOG_ENDPOINTS`;
   - log `[HOT_PATH]` koreluje `request_ms`, `profile_full_read`,
     `profile_full_write`, `profile_bytes` i `sqlite_writer_wait_ms`;
   - metryki nie zawierają profilu, współrzędnych, cookie ani danych innych kont.
8. Lokalne snapshoty produkcyjnej bazy:
   - `data/game.sqlite3.*` jest jawnie ignorowane przez Git;
   - `game.sqlite3.server` i kopie `.bak` nie są artefaktami projektu.

## Kontrakty zachowane

- malformed lub jawnie uszkodzony profil nadal fail-closed;
- każdy pełny zapis nadal waliduje bieżący profil i checksumę;
- stale revision oraz zmiana checksumy przed commit kończą się kontrolowanym
  konfliktem;
- LKG pozostaje atomowe z profile write;
- session-generation precommit guard działa w tej samej transakcji;
- canonical target i operation stores pozostają source of truth;
- kolejka `/gonna-win`, payloady i presentation timing nie zostały zmienione.

## Automatyczna bramka GO

Testy celowane obejmują mały i duży syntetyczny profil oraz wymagają:

- zero heavy reads/writes dla pojedynczego `aim-target`;
- zero `UserProfileManager` dla `operation_only`;
- brak skanowania wszystkich profili przez manager;
- przygotowanie LKG przed writer-lockiem;
- pojedynczą inicjalizację GN service w procesie;
- zachowanie integrity, CAS, LKG, session precommit oraz monotonicznego target
  progress.

Wyniki:

- testy celowane hot path/integrity/target/session/GN: `267/267 OK`;
- końcowa pełna regresja: `978/978 OK`;
- testy po ostatniej zmianie telemetryki writer wait: `8/8 OK`;
- `py_compile`, `node --check` i `git diff --check`: OK.

Odczytowy benchmark lokalnego snapshotu produkcyjnego (`mode=ro`,
`query_only=ON`) potwierdził:

- `main`, profil `34 580 098 B`: lekki read median `460.167 ms`, heavy/audit
  median `2490.354 ms`, poprawa `5.41×`;
- `ania`, profil `3 071 B`: lekki read median `20.528 ms`, heavy/audit median
  `17.226 ms`; dla małego profilu dominuje koszt otwarcia połączenia;
- rozmiar i `mtime` pliku bazy pozostały bez zmian (`db_unchanged=true`).

Lokalna bramka correctness jest zamknięta. Pozostaje wyłącznie serwerowy pomiar
`before → after` rzeczywistych requestów i lock contention.

Nie wykonano commita, deployu, restartu ani mutacji serwerowej bazy.

## Formalne zamknięcie — 2026-08-24

`SPRINT 130.10.1 — COMPLETE`

Późniejszy serwerowy gameplay potwierdził, że lag ciężkiego profilu zniknął.
Aktualny kod i testy nadal utrzymują zero full-profile reads/writes dla
`aim-target` i częściowych ścieżek `/gonna-win`, brak skanowania wszystkich
profili przez managera oraz przygotowanie LKG poza writer-lockiem. Nie pozostał
otwarty blocker 130.10.1; kontrakt zerowego heavy-profile hot path jest dalej
wiążący dla Sprintów 130.11+.
