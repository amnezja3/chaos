# 142.6 — kanoniczne wykonanie kar i recovery

Status: testy lokalne PASS; kontrolowany odbiór gameplay na `main` —
PASS AUTORA 21 IX 2026. Potwierdzono stopnie 1–5, komunikaty, kartotekę,
trwałość po reconnectcie oraz aktualizację dysku/pulpitu/FM na żywo.
Pełny odbiór integracyjny i rollout pozostają w 142.7.

## Wykonanie

Nowy `CanonicalConsequenceExecutor` korzysta z tabeli `RESPONSE_CONSEQUENCE_TABLE`
i `CriminalRecordStore`. Stary executor mutujący profile pozostaje zablokowany.

1. Kwalifikacja i trwały rzut w transakcji spotkania. Nowy wynik selected dla
   konta objętego rolloutem otrzymuje pending. avoided i obserwacja nie uruchamiają kary.
2. Osobna transakcja BEGIN IMMEDIATE ponownie sprawdza sesję, presence, wersję
   pozycji, dystans do aktualnego patrolu, incident/capsule, blokadę Ghost Signala
   i datę ostatniego rollover. Stara epoka nie może wykonać kary.
3. Plan z bieżącego poziomu incydentu i wspólnej kartoteki. Mandat według
   formuły z configu (risk = canonical heat incydentu); szansa 80/30 nie jest losowana ponownie.
4. Jedna transakcja zapisuje debit + ledger, odinstalowanie aplikacji i plików,
   korektę zajętego dysku, anulowanie jednej własnej aktywnej operacji powiązanej
   przez response_incident_members, Judgment, historię/kartotekę, wynik receipt,
   system message i trwałe delty. Wszystkie helpery dostają tę samą connection.

Postronny i inicjator bez aktywnej operacji też mogą dostać karę. Nie wymagamy
fikcyjnej operacji. Jeśli jest ich kilka, wybierana jest pierwsza własna aktywna
po operation_id; cudze i niepowiązane pozostają nietknięte. Przy konfiskacie
pierwszeństwo ma narzędzie tej operacji, potem deterministyczna kolejność app_id.
Ochrona ostatniego narzędzia i rezerwa HC są zachowane. Faktyczna konfiskata
może być mniejsza od planowanej przez tę ochronę; historia zapisuje oba wyniki.

Stopnie 6–9: unsupported/detention_requires_sprint_143. Nie pobieramy zastępczego
mandatu, nie liczymy nieodbytego aresztu i nie uruchamiamy timera. Zatwierdzone
online/pauza offline pozostają kontraktem implementacji 143.

## Recovery i stany

| execution_status | Znaczenie |
|---|---|
| not_enabled | Obserwacja lub avoided; nie konwertujemy starych wyników 142.5 na kary |
| pending | Rzut trwały; wykonanie czeka na aktualne, prawidłowe spotkanie |
| executed | Skutki, historia i outbox zatwierdzone razem |
| no_effect | L1 lub chronione/puste zasoby; brak zwiększenia kartoteki |
| unsupported | Plan wymaga aresztu z 143 |
| blocked | Niepełna lub zbyt duża projekcja zasobów; brak częściowej kary |
| expired | Source zamknięte, cooling zakończony lub epoka zastąpiona |

Crash przed commit skutków cofa wszystkie skutki, zachowując wcześniej zapisany
rzut. Kolejne świeże spotkanie z dowolnym patrolem tego incydentu ponawia pending.
Worker uwzględnia pending w detekcji przestrzennej i sprząta zamknięte źródła
po maksymalnie 16 rekordów na tick, z kursorem czasu. Offline nigdy nie wykonuje
zaległego wykrycia. Crash po commit/retry odczytuje trwały wynik, bez drugiego debitu.

GET `/api/map/incidents/encounter?incident_id=...` daje wynik wyłącznie konta
z sesji. Działa także po opuszczeniu zasięgu/zamknięciu incydentu, bez wykonywania
czegokolwiek. Używać fetch w aktywnym kliencie z generacją sesji.

## Live i koszt

Wallet/storage/map.operations_changed korzystają z istniejących delt.
Konfiskata wysyła mały apps.confiscated z removed_app_ids i removed_tools;
desktop oraz otwarte menedżery usuwają wskazane pozycje lokalnie. Nie wysyłamy
całego inventory. Nazwa pliku powiązanego z inną aplikacją nie usuwa tej aplikacji.
Powiadomienie korzysta z kanonicznego system_messages i istniejącego odbioru.
Ponowienie dostarczenia delty jest idempotentne.

Nie ma get_profile/list_profiles/sync_session_profile ani schema init w executorze.
Wybieramy maksymalnie cztery kandydatury narzędzi (trzy do konfiskaty i jedno
chronione), jedną operację, małe projekcje portfela i kartoteki. Duży arsenał
nie jest sam w sobie podstawą odmowy. Bezpieczniki payloadów: 256 KiB na wybraną
aplikację/operację, 256 plików narzędzi i 1 MiB ich JSON na konto. Przekroczenie
nie powoduje odczytu profilu ani częściowego obciążenia; zapisuje blocked.

## Rollout — najpierw main

Historyczny rollout 142.6 (20 IX): w czterech ecosystemach ustawiono:

```js
CHAOS_RESPONSE_QUALIFICATION_MODE: "observe",
CHAOS_RESPONSE_ENCOUNTERS_ENABLED: "true",
CHAOS_RESPONSE_EXECUTION_MODE: "enforce",
CHAOS_RESPONSE_EXECUTION_ACTORS: "main",
```

142.7 rozszerza konfigurację na `*`; aktualna instrukcja wdrożenia i odbioru:
[runbook 142.7](sprint_142_7_integration_rollout.md).

Nazwy oddzielone przecinkami poszerzają test; `*` oznacza wszystkie konta.
Pusty wykaz nie dopuszcza żadnego konta. Tryb execution observe wyłącza nowe
skutki, zachowując receipt/history. Ustawienia muszą być spójne w ecosystemach.
Kwalifikacja zachowuje nazwę observe; jedyną bramką kar jest osobny executor.

Po pobraniu kodu:

```bash
pm2 startOrRestart ecosystem.web.config.js --update-env
pm2 startOrRestart ecosystem.territory-worker.config.js --update-env
pm2 startOrRestart ecosystem.ollama-worker.config.js --update-env
pm2 startOrRestart ecosystem.narrative-publisher.config.js --update-env
pm2 save
```

Odświeżyć klientów dla obsługi przyrostowej delty arsenału. Addytywne pola
execution_json/execution_checked_at i indeks pending powstają przy starcie;
nie usuwać starych receipts. Schemat GhostNetwork musi być już zainicjalizowany
przez normalne wdrożenie świata. Brak źródeł canonical zamyka wykonanie.

## Historyczne Judgment

Nowe punkty i historia trafiają do response_judgment/response_penalty_history.
Stare profile nie są automatycznie odczytywane. Jawny importer uruchamiany poza
ruchem requestów archiwizuje legacy judgment_history i dodaje stare punkty
dokładnie raz, bez modyfikacji profilu i bez zmyślania licznika nowych kar:

```bash
.venv/bin/python tools/migrate_response_judgment.py --limit 25
```

Domyślnie tylko odczyt. Jeśli raport pokazuje eligible, po backupie bazy wykonać
ten sam zakres z `--apply`, potem ponowić odczyt, który nie powinien już wykazać
tych kont jako eligible. Kolejne strony: `--after LOGIN_Z_next_after`. Narzędzie
skanuje maksymalnie 50 kont na wywołanie; duże historyczne dane są czytane tylko
przez ten jawny proces migracji. Punkty istniejących nowych kar są zachowane.

## Odbiór gameplay

1. main, nowy incydent L2: po selected oczekiwany mandat, komunikat i live HC.
   avoided jest prawidłowe i wymaga nowego incydentu do kolejnego losowania.
2. Powrót/reconnect/restart: ten sam wynik, brak kolejnego pobrania i komunikatu.
3. Kolejny nowy incydent: stopień uwzględnia tylko wcześniej wykonane kary.
   Dla stopnia konfiskaty zostawić otwarty menedżer; narzędzia i dysk zmieniają
   się live, co najmniej jedno narzędzie operacyjne pozostaje.
4. Brak kary offline; powrót poza zasięgiem również bez kary. Powrót w aktualny
   zasięg może wznowić pending, ale nie powtarza executed.
5. Konto poza listą, stare not_enabled i avoided pozostają bez skutków.

SQL do diagnostyki (wyłącznie odczyt):

```sql
SELECT actor_id,incident_id,roll,outcome,execution_status,
       json_extract(execution_json,'$.reason') AS reason,
       json_extract(execution_json,'$.plan.stage') AS stage,
       json_extract(execution_json,'$.effects') AS effects
FROM response_encounters ORDER BY created_at DESC LIMIT 30;
SELECT actor_id,executed_count FROM response_criminal_records;
```

## Walidacja lokalna

Zestawy: 94 testy regresji wallet/inventory/operacji/PvP i spotkań PASS;
33 testy po dodaniu granicy epoki PASS; końcowe 28 testów executora i endpointów
PASS (zestawy częściowo się pokrywają). Dodatkowy test JS przyrostowej konfiskaty PASS.
Testy obejmują współbieżność, rollback po zapisaniu skutków, retry, role,
offline między fazami, kill switch, wersję pozycji, epokę, bystandera bez operacji,
ochronę zasobów, ponad 150 aplikacji, import Judgment i prywatność recovery.

Baseline lokalny, Windows: 10 próbek na rozmiar profilu. Ostatni przebieg:
mały profil p95 66,8 ms, profil 35 MB p95 66,3 ms; maksimum 43 instrukcje SQL;
p95 czasu trzymania writer lock 17,3 / 14,6 ms. Zero profile_full_read/write
i profile_bytes; dodatkowo SQLite authorizer zabrania SELECT users.profile_json,
a init_db jest zablokowane w trakcie wykonania. To baseline, nie produkcyjny SLA.
Odbiór desktop/mobile i pomiary pod obciążeniem VPS pozostają do wykonania.
