# `/gonna-win` 409 na ostatniej kropce filaru konfliktu

**Sprint:** 130.12.2  
**Data zamknięcia:** 2026-08-25  
**Severity:** P0  
**Status:** `RESOLVED`

## Problem i wpływ

Podczas hakowania filarów konfliktu ostatnie narzędzie sporadycznie kończyło
`POST /gonna-win` statusem `409 CONFLICT`. OFS/SFX potwierdzał zakończenie, ale
Trace Compass pokazywał jednocześnie komunikat o przerwaniu lub zablokowaniu.
Natychmiastowe ponowienie tego samego narzędzia przechodziło.

Problem występował z Trace Compass, Nmap i Metasploit. Wspólną cechą nie była
aplikacja ani interfejs, lecz fakt, że request wykonywał ostatnią kropkę i
wchodził w finalny capture filaru konfliktu.

Skutki:

- canonical transfer mógł być już zapisany, mimo że klient otrzymywał 409;
- gracz dostawał false failure i ponawiał zakończoną operację;
- retry zwykle zwracał 200, utrudniając odróżnienie race od błędu celu;
- diagnoza długo skupiała się na identity, ownership bootstrapie, OFS i session
  generation zamiast na projekcji wykonywanej po commit boundary.

## Reprodukcja

1. Wybrać aktywny filar konfliktu należący do innego gracza.
2. Wykonać wymagane narzędzia aż do ostatniej kropki security/actions.
3. Na narzędziu domykającym capture obserwować `POST /gonna-win`.
4. Wadliwy przebieg: pierwszy request zwraca 409 bez kontrolowanego `reason`,
   mimo że canonical lifecycle częściowo potwierdza zakończenie.
5. Ponowić narzędzie; retry widzi już zapisany stan i zwraca 200.

Problem był sporadyczny, ponieważ wymagał konkurencyjnego zapisu revision profilu
w krótkim oknie po canonical capture.

## Evidence rozstrzygające

Telemetryka klienta pokazywała:

```text
[GONNA_WIN_RESPONSE] {"status":409,"success":false,"blocked":false,
"reason":"","expected_target_id":"","current_target_id":"",
"receipt_result":"","request_ordinal":1}
```

Brak `blocked:true` i domenowego `reason` wykluczał kontrolowane guardy:

- `target_selection_changed`;
- `invalid_target`;
- `receipt_target_mismatch`;
- `target_state_changed`;
- `canonical_owner_missing`.

Kształt odpowiedzi odpowiadał globalnemu handlerowi `ProfileWriteConflict`.
Pełny log oraz manual potwierdziły następnie, że Nmap i Metasploit również były
narzędziami domykającymi ostatnią kropkę, nie częściowymi krokami.

## Call chain i source of truth

```text
desktop tool
→ notifyGonnaWin()
→ generationBoundFetch('/gonna-win')
→ gonna_win()
→ TerritoryTargetOwnershipStore.capture()
→ capture_conflict_pillar()
→ canonical ownership/territory commit
→ projekcja utraty filaru do profilu poprzedniego właściciela
→ stale profile revision / ProfileWriteConflict
→ globalny HTTP 409
```

Source of truth:

- `TerritoryTargetOwnershipStore` — owner/version i atomic capture CAS;
- `TerritoryStore` — captured targets oraz dane rebuildów;
- `PlayerTargetRuntimeStore` — aktywny/captured target;
- `AppActionReceiptStore` — exactly-once lifecycle requestu.

`users.profile_json.hacked` i `aimed_target` są wtórną projekcją kompatybilności,
nie commit boundary przejęcia filaru.

## Root cause

Po canonical capture kod tworzył `UserProfileManager` dla poprzedniego
właściciela i wykonywał kilka pełnych zapisów profilu opartych o wcześniej
wczytaną rewizję:

1. usunięcie celu z `hacked`;
2. osobny zapis świeżej listy z `TerritoryStore`;
3. w części ścieżek kolejny patch statystyk territory.

Równoległy request albo worker mógł podnieść revision pomiędzy odczytem a którymś
z zapisów. `ProfileWriteConflict` prawidłowo odrzucał stale full-profile writer,
ale nieprawidłowo propagował się jako wynik całej operacji już po canonical
ownership commit. Dlatego pierwsza próba wyglądała na porażkę, a retry odnajdywał
przejęty filar i przechodził.

## Próby i odrzucone hipotezy

W trakcie diagnozy naprawiono również realne, lecz niewystarczające problemy:

- utratę `target_id/conflict_id` w picker/app handoff;
- zbyt ścisłe porównanie historycznego i odbudowanego `target_id` w runtime;
- bootstrap ownership revision 0 → 1 traktowany jak zewnętrzny CAS loss.

Sprawdzono i wykluczono jako końcową przyczynę:

- drugi request `/gonna-win` generowany przez OFS;
- session generation mismatch;
- `Permissions policy violation: unload`.

Rozstrzygnięcie dało logowanie `status`, `blocked`, `reason`, target IDs, receipt
result i ordinal oraz potwierdzenie, że każdy wadliwy request był finalnym
capture.

## Finalne rozwiązanie

- usunięto full-profile `UserProfileManager` z projekcji utraty filaru;
- profil poprzedniego właściciela dostaje mały top-level patch budowany na
  najnowszej revision;
- ordinary CAS conflict powoduje bounded reload/rebase/retry;
- po wyczerpaniu retry projekcja jest deferred i naprawiana przez
  rebuild/snapshot, bez zamiany canonical success w HTTP 409;
- `ProfilePrecommitRejected` i session ownership mismatch nadal są fail-closed;
- `[GONNA_WIN_RESPONSE]` zawiera również `error` i `retryable`.

Najważniejszy invariant:

```text
canonical capture success
nie może stać się failure wyłącznie przez konflikt wtórnej projekcji profilu
```

## Testy i weryfikacja

Regresje obejmują:

- CAS loss przy pierwszej próbie i poprawny rebase;
- zachowanie równoległej, niezwiązanej zmiany profilu;
- wyczerpanie trzech prób bez false 409 po canonical commit;
- czyszczenie aimed target wyłącznie przy zgodnej identity;
- exactly-once `/gonna-win`, receipt replay i operation lifecycle;
- frontendowy kontrakt telemetryki `error/retryable`.

Walidacja lokalna:

- 81/81 testów integralności — OK;
- 305/305 testów map/territory/GN/OFS/target persistence — OK;
- `py_compile` — OK;
- `node --check` — OK;
- `git diff --check` — OK.

Manual produkcyjny 2026-08-25 potwierdził, że finalizacje filarów konfliktu
przechodzą za pierwszym razem. Problem uznano za zamknięty.

## Procedura, jeżeli problem wróci

1. Skopiować pełną linię `[GONNA_WIN_RESPONSE]`.
2. Zanotować `app_id`, `status`, `error`, `retryable`, `reason`, target IDs,
   `receipt_result`, `request_ordinal` i `flow_id` z sąsiedniego `APP_FLOW`.
3. Ustalić, czy narzędzie było ostatnią kropką i czy canonical owner już się
   zmienił.
4. W logu serwera wyszukać ten sam flow/receipt oraz znaczniki
   `GONNA_WIN_FLOW`, `GONNA_WIN_CONFLICT`,
   `TERRITORY_OWNER_PROFILE_SYNC_DEFERRED` i
   `TERRITORY_CAPTURE_PROFILE_SYNC_DEFERRED`.
5. Interpretacja:
   - `blocked:true` + `reason` — domenowy guard, inny call chain;
   - `error:profile_write_conflict` — znaleźć wtórny projection writer, który
     nadal propaguje CAS;
   - session error header — osobny incident session ownership;
   - 200 + `receipt_result:replayed` — prawidłowy exactly-once replay.
6. Nie dodawać ślepego frontendowego retry i nie osłabiać ownership CAS. Najpierw
   ustalić, czy canonical mutacja została już zatwierdzona.

Jeżeli symptom powróci z innym call chainem, utworzyć nowy artefakt hardbugfix z
odwołaniem do tego dokumentu zamiast nadpisywać historię.

## Powiązane pliki i sprint

- `run.py`: `/gonna-win`, `project_lost_territory_after_capture` i capture
  lifecycle;
- `static/js/terminal.js`: `[GONNA_WIN_RESPONSE]`;
- `tests/test_territory_profile_projection_cas.py`;
- `tests/test_operation_feedback_frontend_contract.py`;
- Sprint 130.12.2 — Map / Territory / GhostNetwork / Operation Integrity P0.

## Status końcowy

`RESOLVED — MANUAL PRODUCTION VALIDATION PASSED`
