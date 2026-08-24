# GhostNetwork Endgame Runbook

## Cel

Runbook opisuje bezpieczne uruchamianie pierwszego etapu endgame GhostNetwork
po Sprint 130.

## Kolejnosc uruchamiania

1. `GHOSTNETWORK_ENABLED`
2. `GHOSTNETWORK_DROPS_ENABLED`
3. `GHOSTNETWORK_MAP_LAYER_ENABLED`
4. `GHOSTNETWORK_ABILITIES_ENABLED`
5. `GHOSTNETWORK_REWARDS_ENABLED`
6. `GHOSTNETWORK_TRANSMISSION_ENABLED`
7. `GHOSTNETWORK_MEDIA_ENABLED`
8. `GHOSTNETWORK_OLLAMA_ENABLED`

Kazda flaga powinna byc wlaczana osobno i obserwowana przed przejsciem dalej.

## Readiness check

Najpierw sprawdź runtime bez mutowania danych:

```text
python tools/ghostnetwork_runtime.py status
python tools/ghostnetwork_runtime.py verify
python tools/ghostnetwork_runtime.py bootstrap
GET /api/dev/ghostnetwork/readiness
```

Utworzenie brakującego cyklu jest osobną decyzją operatora:

```text
python tools/ghostnetwork_runtime.py bootstrap --apply
```

Zwykły start aplikacji/workera nie wykonuje bootstrapu. Kod wyjścia `2` dla
`status`/`verify` oznacza `NOT READY`. Wartości dropów pochodzą z
`CHAOS_GHOSTNETWORK_DROPS_ENABLED` i `CHAOS_GHOSTNETWORK_DROP_CHANCE`; runbook
nie ustala produkcyjnego balansu.

Kontrolowany przykład dla procesu development:

```powershell
$env:CHAOS_GHOSTNETWORK_RUNTIME_MODE='development'
$env:CHAOS_GHOSTNETWORK_DROPS_ENABLED='true'
$env:CHAOS_GHOSTNETWORK_DROP_CHANCE='0.25'
python tools/ghostnetwork_runtime.py verify
```

Przed restartem lub po awarii capture:

```text
python tools/ghostnetwork_runtime.py reconcile
python tools/ghostnetwork_runtime.py reconcile --apply
python tools/ghostnetwork_runtime.py drain --apply
python tools/ghostnetwork_runtime.py verify
```

Komendy bez `--apply` nie wykonują reconciliation mutation. `drain --apply`
odtwarza brakujące effects i przetwarza `pending/failed`; nie usuwa cyklu,
części ani ledgerów. Po drain wymagane są `pending_effects=0` i
`unreconciled_effects=0`.

`CHAOS_GHOSTNETWORK_TEST_MODE=true` jest dozwolone wyłącznie przy runtime mode
`development` albo `test`. W `production` readiness zwraca
`test_mode_forbidden_in_production`.

Readiness archiwum/endgame sprawdzaj osobno.

## Manual gameplay Sprint 130.9.1 na serwerze

Manual wykonujemy na kontrolowanym serwerze z działającym webem, territory
workerem i rzeczywistymi kontami testowymi. Lokalny `verify` nie zastępuje
serwerowego pre-flight.

Przed restartem wykonaj backup bazy i zanotuj commit oraz nazwy procesów PM2.
W lokalnym, niewersjonowanym `ecosystem.config.js` ustaw dla procesu webowego
i territory workera:

```text
CHAOS_GHOSTNETWORK_RUNTIME_MODE=development
CHAOS_GHOSTNETWORK_DROPS_ENABLED=true
CHAOS_GHOSTNETWORK_DROP_CHANCE=0.25
CHAOS_GHOSTNETWORK_TEST_MODE=false
```

Następnie, używając istniejących nazw procesów:

```text
pm2 restart ecosystem.config.js --update-env
pm2 status
pm2 logs --lines 100
python tools/ghostnetwork_runtime.py status
python tools/ghostnetwork_runtime.py verify
python tools/audit_ghostnetwork_runtime_state.py
python tools/ghostnetwork_runtime.py reconcile
python tools/ghostnetwork_runtime.py drain
```

`reconcile` i `drain` bez `--apply` są obowiązkowym dry-run. Mutację wolno
wykonać dopiero po sprawdzeniu raportu. Przed przekazaniem manuala wymagane są:

* jedna wersja kodu na webie i workerze,
* `READY`, jeden aktywny cykl, 20 części i valid topology,
* zero pending/unreconciled effects,
* działający territory worker bez pętli restartów,
* wskazane konto testowe z klanem/profesją i wymaganymi narzędziami,
* brak włączonego test mode i brak wymuszonego rolla.

Po manualu najpierw zabezpiecz logi oraz identyfikatory operacji/celu/części,
potem wykonaj `status`, audyt i dry-run reconcile/drain. Nie czyść stanu przed
zebraniem dowodów.

Przed publicznym wlaczeniem endgame sprawdz:

```text
GET /api/ghostnetwork/archive/readiness
```

Wymagane:

* `ok = true`;
* `health.ok = true`;
* katalog GhostNetwork jest poprawny;
* endpoint archiwum nie zwraca bledu;
* zwykly gameplay dziala przy wylaczonych flagach GhostNetwork;
* endpointy mapy nie maja nowych regresji wydajnosci.

## Rollback

W razie problemu:

1. Wylacz `GHOSTNETWORK_MEDIA_ENABLED`.
2. Wylacz `GHOSTNETWORK_TRANSMISSION_ENABLED`.
3. Wylacz `GHOSTNETWORK_REWARDS_ENABLED`.
4. Wylacz `GHOSTNETWORK_ABILITIES_ENABLED`.
5. Jesli problem dotyczy mapy, wylacz `GHOSTNETWORK_MAP_LAYER_ENABLED`.
6. Jesli problem dotyczy calego systemu, wylacz `GHOSTNETWORK_ENABLED`.

Rollback nie usuwa archiwum ani historycznych sygnalow.

## Recovery

Archiwum mozna odtworzac idempotentnie przez:

```text
GhostNetworkService().finalize_signal_archive(signal_id)
```

Osiagniecia maja `dedupe_key`, wiec ponowna finalizacja nie powinna tworzyc
duplikatow.

## Zakazy

* Nie wlaczac Suite UI przed osobnym sprintem.
* Nie dawac Ollamie prawa do zmiany mechaniki.
* Nie kasowac historycznych wezlow przy rollbacku.
* Nie budowac drugiego stanu GhostNetwork poza repozytorium i snapshotami.
