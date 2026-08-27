# Sprint 132 — GhostNetwork Suite Read Model

Data rozpoczęcia: 2026-08-26.

Status: `SPRINT 132 — COMPLETE`.

## Cel

Rozszerzyć istniejący `GET /api/ghostnetwork/snapshot?view=suite` do lekkiego,
viewer-projected read modelu przyszłej aplikacji GhostNetwork Suite. Sprint nie
tworzy GUI, nowego endpointu, tabeli, cache ani drugiego visibility resolvera.

## Source of truth i call chain

```text
user_identity_projection
→ viewer context
→ GhostNetworkRepository internal snapshot
→ GhostVisibilityService viewer projection
→ bounded owner identity batch
→ normalize_snapshot_view(view=suite)
→ summary/groups/parts
```

- lifecycle/topology: istniejące `ghost_*` i `GhostNetworkService`;
- privacy: wyłącznie `GhostVisibilityService`;
- owner alias: revision-aware `UserIdentityProjectionStore.get_identities()`;
- targety akcji: opaque `public_entity_id` albo `territory_id`;
- `parts[]` pozostaje jedyną listą części.

## Kontrakt read modelu

- `summary` jest deterministyczną pochodną końcowej listy części;
- `groups` zawiera tylko `public_entity_id` i nie kopiuje rekordów;
- każda część posiada bezpieczne `owner`, `territory`, `location` i `actions`;
- exact action wskazuje `ghostnetwork_part + public_entity_id`;
- territory-only action wskazuje `ghostnetwork_territory + territory_id`;
- nieaktywny cykl wyłącza akcje;
- connections zachowują wyłącznie publiczny identyfikator i stan, bez geometrii;
- legacy `projection.suite` z pełnymi kopiami rekordów został usunięty.

Grupy bazowe są rozłączne:

```text
public
blocked
clan_active
self_foreign
self_own
```

`foreign_active` pozostaje bezpiecznie widoczne wyłącznie w głównym `parts[]` i
nie trafia do grupy sugerującej pełną identity.

## Privacy i fail-closed

- hidden identity fields są ponownie zerowane podczas budowy suite view;
- territory-only nie zawiera dokładnych współrzędnych;
- geometry, vertices, reservations i event history są usuwane;
- brak bounded owner alias nie uruchamia full-profile fallbacku;
- alias lookup jest jednym batch query dla maksymalnie 20 owner IDs;
- output jest ograniczony do 20 unikalnych `public_entity_id`;
- `suite_health` raportuje duplicate ID, overflow, brak wymaganej lokalizacji,
  hidden identity oraz niespójną relację owner/clan.

## Cache

Suite cache key zachowuje istniejący viewer-scoped klucz i dodaje:

```text
view=suite
owner identity revision/checksum signature
```

Zmiana viewera, klanu albo revision aliasu nie może użyć starego modelu.

## Heavy-profile contract

Zwykły suite request ma:

```text
profile_full_read=0
profile_full_write=0
profile_bytes=0
all_user_profile_scan=0
per_recipient_profile_read=0
```

Test porównuje mały profil i syntetyczny profil 35 MB. Obie ścieżki wykonują
jedno bounded viewer identity read; rozmiar `profile_json` nie wchodzi do
requestu.

## Walidacja

Celowane przypadki obejmują:

- pusty snapshot;
- dokładnie 20 części i fail-closed overflow;
- brak duplikatów oraz reference-only groups;
- public/blocked/clan/self/foreign relations;
- exact i territory-only actions;
- hidden identity/geometry/reservation stripping;
- owner alias batch i bezpieczny fallback;
- viewer/owner revision cache isolation;
- profil 35 MB bez heavy path;
- map snapshot, visibility, Territory Control i shared delta client regression.

Wynik końcowy:

- pełna regresja Python: `1105/1105 OK`;
- pełna regresja GhostNetwork: `217/217 OK`;
- testy suite/visibility/read-path: `31/31 OK`;
- celowane testy identity/Territory Control: `35/35 OK`;
- GhostNetwork delta client i map renderer: `OK`;
- `py_compile`, `node --check` i `git diff --check`: `OK`.

Walidacja serwerowa 2026-08-27 potwierdziła dla dwóch niezależnych sesji:

- HTTP 200 i `view=suite`;
- `suite_health.ok=true` bez błędów;
- unikalne części, limit, summary i reference-only groups;
- poprawne exact/territory-only oraz hidden-identity privacy;
- connections bez geometrii;
- stabilne `state_version`, checksum i suite cache key.

Sprint został zamknięty. Nie wykonano w ramach zamknięcia restartu PM2,
produkcyjnych mutacji ani commita.

## Ograniczenia

- bez GUI Sprintu 133;
- bez nowych map/teleport feature'ów Sprintu 134;
- bez zmian transportu delta/recovery Sprintu 135;
- bez deployu, restartu PM2 i produkcyjnych mutacji.
