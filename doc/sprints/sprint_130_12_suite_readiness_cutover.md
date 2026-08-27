# SPRINT 130.12 — COMPLETE

## GhostNetwork Suite Readiness Cutover

Data rozpoczęcia: 2026-08-24  
Branch baseline: `2ae469a`

Sprint został rozpoczęty po audycie przedsprintowym 131. Jego jedynym celem jest
usunięcie infrastrukturalnych blockerów wejścia w Sprint 132. Sprint nie rozszerza
gameplayu, nie uruchamia narracji i nie zmienia semantyki konfliktów.

Pełny kontrakt wykonawczy i DoD pozostają w
`doc/history/game_play_180726.md`, w sekcji „Sprint 130.12 — GhostNetwork Suite
Readiness Cutover”. Ten plik jest technicznym artefaktem wykonania i dowodów.

## Ograniczenia wykonania

- bez deployu i bez restartu PM2;
- bez migracji ani mutacji produkcyjnej bazy;
- bez rozpoczęcia Sprintu 131 lub 132;
- bez request-time bootstrapu pełnych profili;
- bez ujawniania prywatnych kotwic GhostNetwork;
- bez zmiany runtime poza zakresem kontraktu 130.12.

## Baseline Etapu 0

- working tree zawiera wcześniejszą, zamierzoną reorganizację `doc/`; zmiany są
  zachowane i nie będą cofane;
- `UserStore.patch_profile_guarded` i `UserStore.save_profile_guarded` wykonują
  CAS na revision/checksum w krótkiej transakcji `BEGIN IMMEDIATE`;
- `PlayerInventoryStore`, `PlayerPositionStore` i
  `PlayerTargetRuntimeStore` są istniejącymi canonical boundaries;
- `PlayerPositionStore.upsert` korzysta ze wspólnego requestowego precommit guard
  przez warstwę `db_connect`;
- istniejący `UserStore.list_profile_identities` skanuje `users.profile_json` i
  nie spełnia kontraktu bounded recipient resolution;
- Territory Control nadal ładuje pełny profil;
- teleport Blacknet nadal wykonuje pełny profile read/write;
- transport delt GhostNetwork nadal jest osadzony w module mapy zależnym od
  Leaflet.

## Etapy i dowody

| Etap | Status | Artefakt / dowód |
|---|---|---|
| 0. Baseline i inventory | COMPLETE (LOCAL) | niniejszy dokument, inventory callsites |
| 1. Bounded identity/recipient projection | COMPLETE | migracja, store, guarded-write tests |
| 2. Territory Control zero-profile cutover | COMPLETE | endpoint tests, GN projection contract |
| 3. Canonical teleport i opaque GN targets | COMPLETE | endpoint/security/idempotency tests |
| 4. Shared GhostNetwork delta client | COMPLETE (LOCAL) | JS unit tests bez Leaflet |
| 5. Recipient readiness | COMPLETE | bounded audience resolver tests |
| 6. Telemetry i narzędzia audytu | COMPLETE | static/runtime audit outputs |
| 7. Re-audit 131 i bramka | COMPLETE | `READY FOR SPRINT 132` |

## Historyczne blockery wejścia w Sprint 132

1. Brak materializowanej, revision-aware projekcji identity/recipient.
2. Pełny profil w request path Territory Control.
3. Pełny profil w canonical teleport path.
4. Brak bezpiecznej serwerowej rezolucji opaque GhostNetwork targetów.
5. Delta client wymagający obecności mapy/Leaflet.

Status tego dokumentu może zostać zmieniony na `COMPLETE` dopiero po spełnieniu
pełnego DoD z roadmapy oraz ponownym audycie Sprintu 131.

## Lokalny checkpoint 2026-08-24 — historyczny

Wykonane lokalnie:

- additive `user_identity_projection` z indeksami `username` i `clan_code`;
- atomowy guarded-write upsert z revision/checksum oraz bounded API
  `get_identity`, `get_identities`, `list_recipient_ids`;
- jawne polecenia migracyjne `status`, `audit`, `dry-run`, `apply --confirm-apply`
  i `verify`; web startup nie wykonuje backfillu;
- Territory Control korzysta z inventory/position/target canonical stores i
  viewer-projected GN components;
- teleport zapisuje canonical position, odrzuca współrzędne dla
  `ghostnetwork_suite` i rozwiązuje exact/territory-only server-side;
- shared delta client działa bez Leaflet, a mapa rejestruje adapter przez
  wspólną instancję desktop/session;
- lokalne `py_compile`, `node --check`, testy klienta delt i renderer mapy są
  zielone; targeted Python regressions są zielone po poprawkach kompatybilności.

Pozostaje przed bramką operatorską: pełna regresja, heavy-profile query
measurement, manual exact/territory-only, production backup/status/audit/dry-run
oraz re-audit Sprintu 131. Żaden z tych kroków nie został oznaczony jako
wykonany ani nie uruchamia produkcyjnej migracji/deployu.

## Finalny checkpoint 2026-08-26

- 1092/1092 testów Python, 24/24 heavy-profile/read-path i 13/13 pakietów Node
  przeszło poprawnie.
- Produkcyjny manual całej serii 130.12 potwierdził session, map/GN/territory,
  operations/OFS, Googleplex/GX/BlackNet, Cybernera i teleport.
- Pięć blockerów wskazanych wyżej jest `RESOLVED` przez canonical store/projection
  i shared-client cutover. Re-audit 131 nie wykazał nowego blockera wejścia w
  Sprint 132.
- Nie wykonano w tym domknięciu nowego deployu, restartu PM2 ani migration apply.

Finalny status:

`SPRINT 130.12 — COMPLETE`

`SPRINT 131 AUDIT COMPLETE — READY FOR SPRINT 132`
