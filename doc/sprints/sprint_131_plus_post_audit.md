# Post-audit Sprintów 131–138 — baseline po 130.9.5 i bramka 130.10–130.11

Data audytu: 2026-08-21. Aktualizacja hot-path: 2026-08-23.

Status: Sprinty 130.10 i 130.11 są zamknięte. Audit Sprintu 131 wykonano
2026-08-24 i zapisano w
`doc/sprints/sprint_131_ghostnetwork_suite_audit.md`. Werdykt pozostaje `NO-GO
FOR SPRINT 132` do zamknięcia wykrytych heavy-profile i bounded-identity
blockerów. Audit nie implementuje GhostNetwork Suite ani pipeline'u Ollamy.

Wiążąca bramka dla całej serii:
`doc/architecture/profile_hot_path_contract_130_11_plus.md`. Jeżeli opis sprintu można
zrealizować zarówno przez canonical store/projection, jak i pełny profil,
obowiązkowa jest pierwsza ścieżka. Brak lekkiej projekcji oznacza pracę do
wykonania w danym sprincie, a nie zgodę na tymczasowy fallback.

## Bramka incydentowa przed Sprintem 131

Incydent `Trollu2` ujawnił możliwe P0 dotyczące trwałości profilu i izolacji
kolejnych logowań. Rozwój Suite nie może rozszerzać liczby user-scoped cache,
snapshotów i delt przed zamknięciem tych podstaw.

Wiążąca kolejność:

1. `130.10 — Profile Integrity and Cross-Account Session Isolation`;
2. `130.11 — Trollu2 Controlled Profile and Territory Recovery`;
3. dopiero `131 — GhostNetwork Suite audit`.

Artefakty:

- `doc/sprints/sprint_130_10_profile_integrity_session_isolation.md`;
- `doc/sprints/sprint_130_11_trollu2_controlled_recovery.md`;
- `doc/incidents/Incydent Trollu2 — utrata profilu, błędy sesji i plan odbudowy.md`.

Zakres 131–138 nie jest renumerowany ani anulowany. Status Sprintu 131:

`SPRINT 131 AUDIT COMPLETE — NO-GO FOR SPRINT 132`.

## Zweryfikowany baseline

1. GhostNetwork ma jeden source of truth w `ghost_cycles`, `ghost_parts`,
   reservations, connections i append-only events. Aktywny cykl ma 20 części.
2. `GhostVisibilityService` i `GhostModuleStateService` obsługują relacje:
   `public_neutral`, `foreign_blocked`, `foreign_active`, `clan_own_active`,
   `self_foreign_blocked`, `self_own_active`. Konflikt jest nakładką z
   `frozen_visibility_context`, nie osobnym stanem bazowym.
3. Projekcja viewer v2 posiada stabilny `public_entity_id`, pola tożsamości
   wyłącznie dla uprawnionego odbiorcy, `location_visibility`,
   `can_show_on_map`, `can_teleport`, asset właściwej części albo neutralny
   `classified_part.png`.
4. Endpoint `GET /api/ghostnetwork/snapshot` już obsługuje `view=map`,
   `view=suite`, `view=territory_summary` i `view=status`. Po recovery wydajności
   korzysta z integrity-gated `get_profile_identity`, a nie
   `load_profile_readonly`; dalej używa projekcji odbiorcy, `state_version`,
   `visibility_version` i `snapshot_checksum`.
5. Dzisiejszy `view=suite` nie jest jeszcze finalnym read modelem aplikacji:
   zachowuje viewer-projected `parts`, a z połączeń usuwa geometrię. Brakuje
   grup, gotowych akcji, lekkiego owner/territory summary i kontraktu GUI.
6. Delta/publication bridge publikuje viewer-projected `part_projection`, ma
   fan-out według visibility contract, dedupe, version-gap recovery oraz nie
   publikuje internal/system do klienta. SFX nie odtwarza snapshot/recovery.
7. Renderer mapy GN już obsługuje części, assety, stany CSS, terytorialny badge,
   połączenia i aktualizację in-place. Nie należy budować drugiej warstwy mapy.
8. Territory Control ma własny lekki snapshot. Istnieje helper
   `project_territory_component_for_viewer`, ale nie jest jeszcze podłączony do
   runtime snapshotu Territory Control.
9. Rodzina produktów używa `type/category=pro-system-tool`,
   `family_id=ghost_control_suite`, `icon_pack=ghost_control` oraz ID w stylu
   `victimPicker`, `territoryControl`, `operationControl`.
10. Map bridge na desktopie to `createMap()` plus
    `notifyOpenMapsBlacknetFocus(...)`. Nie jest to kontrakt iframe.
11. Teleport używa `/api/blacknet/cta/teleport`. Obecny wariant przyjmuje
    współrzędne klienta; nie jest wystarczający dla ukrytej części GN.
12. Sprint 129 dostarczył `GhostNarrativePublisher`, tabelę
    `ghost_narrative_outbox`, media `blacknet/cyberner/radio/ollama_outbox`,
    dedupe, fallback facts, CTA i podstawowy walidator outputu.
13. BlackNet ma osobny adminowy, plikowy Ollama outbox dla world facts. Nie ma
    działającego workera modelu; diagnostyka jawnie raportuje
    `ollama_executed=false`.

## Wiążące korekty zakresu

### Sprint 131

- Jest audytem i kontraktem, bez endpointu i GUI.
- Artefakt trafia do `doc/sprints/sprint_131_ghostnetwork_suite_audit.md`,
  zgodnie z bieżącą strukturą repo, nie do nieistniejącego `docs/ghostnetwork/`.
- Kanoniczne nazwy pól bazowych pozostają zgodne z aktualną płaską projekcją:
  `name`, `clan_code/name`, `machine_code/name`, `profession_code/name`,
  `ability_code/name/description`, `territory_id`, `territory_owner_id`,
  `territory_clan`, `location_visibility`.
- `cluster_id` jest aliasem prezentacyjnym istniejącego `territory_id` /
  `player_areas.id`, a nie nowym identyfikatorem ani tabelą.
- Alias właściciela może zostać dodany tylko lekką projekcją backendową;
  aplikacja nie pobiera pełnych profili.
- Audyt tworzy inventory call sites profilu dla 132–138 i oznacza każdy jako
  `canonical_projection`, `allowed_offline_heavy` albo blocker. Runtime heavy
  call site nie może przejść do Sprintu 132.
- Wspólne ikony są kontraktem do ujednolicenia. Obecnie aplikacje mają osobne
  słowniki ikon; audyt nie może twierdzić, że `GHOST_CONTROL_ICONS` już istnieje.

### Sprint 132

- Rozszerza istniejący `normalize_snapshot_view(..., view="suite")` i ten sam
  endpoint. Nie tworzy nowego magazynu, pełnego snapshotu ani drugiego cache.
- Główne `parts[]` pozostaje viewer projection. `summary`, `groups` i `actions`
  są wyłącznie deterministycznymi pochodnymi tej listy.
- Jedna część występuje raz; grupy zawierają `public_entity_id`.
- Nie dodawać punktowego endpointu, dopóki pomiar nie wykaże potrzeby: aktualna
  delta niesie bezpieczną pełną `part_projection`, a recovery pobiera suite
  snapshot.
- Nie wysyłać reservation ani części o stanie `reserved`; brak strategicznej
  projekcji już je odcina.
- Suite nie potrzebuje geometrii connections. Obecny skrócony licznik/state
  może zostać, ale endpoint nie wysyła endpointów linii.
- Cache/recovery kluczuje istniejące `cache_key`, `visibility_version`,
  `state_version`, viewer ID i clan. Zmiana kontraktu wymaga testu cross-viewer.
- Viewer identity pochodzi wyłącznie z wąskiej projekcji. Snapshot ma testy
  wymuszające zero `get_profile`, `get_profile_with_revision`,
  `sync_session_profile` i `profile_bytes` także dla profilu 35 MB.

### Sprint 133

- ID produktu: `ghostnetworkSuite`; launcher:
  `createGhostNetworkSuiteApp`; `data-app="ghostnetwork-suite"`.
- Okno stosuje `app-window`, `findAvailablePosition`, `makeDraggable`,
  `bringWindowToFront` i istniejący lifecycle taskbara.
- Karty renderują aktualne `visual_asset_url` / `marker_asset_url` oraz CSS
  lifecycle. Nie kopiują mapowego renderera.
- Akcje Sprintu 134 są w 133 ukryte lub disabled; placeholder nie może wysyłać
  współrzędnych ani wykonywać requestu.
- Błąd zachowuje ostatni dobry model widoku, ale nie historyczne tajne pola po
  zmianie visibility.
- Launcher i renderer nie pobierają `/api/profile`, nie wkładają profilu do
  cache aplikacji i nie uruchamiają toolbar profile refresh po aktualizacji karty.

### Sprint 134

- Pokaż na mapie używa `createMap()` i `notifyOpenMapsBlacknetFocus()`.
  Payload jest opaque: `target_type` plus `public_entity_id` albo
  `territory_id`. Nie zawiera ukrytych współrzędnych.
- Mapa rozwiązuje focus z aktualnej projekcji GN po gotowości warstwy. Akcja nie
  ustawia `aimed_target` i nie wywołuje reservation.
- `/api/blacknet/cta/teleport` należy rozszerzyć o serwerowo rozwiązywany cel GN
  (`source=ghostnetwork_suite`, `target_type`, opaque ID). Dla tego source
  endpoint odrzuca klientowe `lat/lng`, ponownie buduje visibility projection i
  dopiero wtedy wybiera anchor lub bezpieczny punkt territory.
- Territory Control ma konsumować `project_territory_component_for_viewer` w
  swoim istniejącym snapshotcie. Nie dodaje warstw ani własnej kopii części.
- Mapowe assety, badge i efekty ze Sprintów 130.9.3–130.9.4 są reuse, nie
  przedmiotem ponownej implementacji.
- Opaque focus i teleport rozwiązują viewer/target przez identity oraz canonical
  GN/territory stores. Zakazane są pełny profil, `sync_session_profile` i
  `UserProfileManager`; zwykły request ma `profile_full_read/write=0`.

### Sprint 135

- `GhostNetworkDeltaClient` istnieje obecnie w `static/js/map/ghostnetwork.js`.
  Suite nie może ładować tego pliku, bo wymusiłaby mapę. Należy wydzielić lekki
  transport/dedupe/recovery client do współdzielonego modułu bez Leaflet albo
  rozszerzyć istniejący terminalowy router; mapa i Suite mają używać jednej
  instancji.
- Nie tworzyć nowego pollera. Delty przychodzą istniejącym `/api/state/changes`.
- Recovery używa `snapshot?view=suite`; snapshot/recovery nie uruchamia SFX.
- Rejestr produktu należy zsynchronizować zgodnie z obecną konwencją katalogu
  runtime i `static/app_config.json`, z testem jednej instancji i instalacji.
- Manualna bramka obejmuje desktop/mobile, mapę na żądanie, teleport exact i
  territory-only oraz zmianę widoczności usuwającą stare dane z DOM/cache.
- Delta i recovery nie odświeżają `/api/profile`, nie wykonują profile overlay i
  nie trzymają profilu w shared client cache.

### Sprint 136

- Nie tworzyć równoległego `GhostNetworkBlackNetBridge`. Rozszerzyć istniejący
  `GhostNarrativePublisher` i `ghost_narrative_outbox`; ewentualne wydzielenie
  klasy jest refaktorem wewnętrznym tego samego pipeline'u.
- Przed rozszerzeniem allowlisty usunąć możliwość publicznego przeniesienia
  surowego `entity_id/part_id` przez generic fact. Fakty części muszą powstawać
  z `GhostVisibilityService` dla każdego audience.
- Obecny publisher generuje wyłącznie audience public. Sprint dodaje rzeczywisty
  fan-out public/clan/owner/player bez wkładania pełnego faktu do public tasku.
- Zachować istniejące CTA: `show_ghostnetwork_part`,
  `show_ghostnetwork_territory`, `open_ghostnetwork_suite`,
  `open_ghostsignal_archive`, `open_cyberner_channel`; nowe nazwy wymagają
  migracji allowlisty i dispatcherów, nie aliasów tylko w dokumencie.
- Hook działa po trwałym evencie i fail-open; błąd narracji nie cofa gameplayu.
- Audience resolver nie może używać `list_profiles()`, per-recipient
  `get_profile()` ani batch JSON projection pełnych rekordów. Jeżeli brak
  trwałego indeksu clan/recipient, Sprint 136 dodaje go przed fan-outem.
- Task outbox zawiera tylko audience-specific projected facts; pełny profil nie
  może wejść do tasku, fallbacku, logu ani dedupe material.

### Sprint 137

- Nie istnieje worker Ollamy do „rozszerzenia”. Sprint tworzy pierwszy worker
  runtime, ale nie drugi source of truth.
- Źródłem zadań GN są rekordy `ghost_narrative_outbox` z
  `medium=ollama_outbox`, nie adminowy world-snapshot file store.
- Tabela wymaga lease/claim/attempt/retry/dead-letter rozszerzonego migracją
  additive. Claim ma być atomowy i odporny na zwykłe SQLite contention według
  wzorca territory workera.
- Istniejący `build_model_input_package` i `validate_model_output` należy
  rozszerzyć, a nie dublować. File-based BlackNet Ollama package może dostać
  adapter diagnostyczny, ale nie staje się kolejką GN.
- Flagi używają konwencji `CHAOS_GHOSTNETWORK_OLLAMA_*`; worker musi mieć
  wersjonowany ecosystem, status/verify i dry-run bez wywołania modelu.
- Worker nie importuje runtime helpera pełnego profilu i nie wykonuje żadnego
  profile read podczas claim/generate/validate/retry. Wszystkie dane wejściowe
  pochodzą z zatwierdzonego tasku 136.

### Sprint 138

- Rozszerzyć istniejące `blacknet_world_signals`, feed oraz dispatcher CTA.
  Nie tworzyć drugiego feedu ani niezależnego publishera, jeśli obecna funkcja
  może przyjąć zwalidowany candidate `ollama_enriched`.
- Publikacja zachowuje audience-specific payload z 136/137. Frontend nie filtruje
  pełnej wiadomości.
- Dedupe łączy `source_event_id`, audience, prompt/output version i istniejący
  signal contract. Fallback bierze zatwierdzone fakty z GN outboxu.
- Rotacja, TTL i invalidation są rozszerzeniem istniejącej polityki BlackNet.
- E2E musi przejść także przy wyłączonej Ollamie; gameplay, delta, reward i
  GhostSignal pozostają niezależne.
- Publisher/feed/CTA nie wzbogacają sygnału przez pełny profil. Audience i CTA
  są rozwiązywane przez identyfikatory/projekcje zapisane w pipeline albo
  bounded canonical lookup.

## Model pracy 131–138

Każdy sprint ma:

1. audyt realnych call sites i source of truth przed zmianą;
2. additive schema migration tylko jeśli jest konieczna;
3. testy jednostkowe, privacy, dedupe, concurrency/recovery oraz regresję
   dotkniętych systemów;
4. `py_compile`, syntax JS, `git diff --check`;
5. aktualizację `doc/history/game_play_180726.md`, właściwego artefaktu technicznego i
   `doc/history/project_journal.md`;
6. techniczny skrypt `status/verify/dry-run` dla nowego workera lub kolejki;
7. manualną bramkę wyłącznie dla zmian gameplay/GUI/audio/mapy;
8. brak commit i deploy, dopóki użytkownik nie zleci ich osobno.
9. obowiązkowy `PROFILE HOT PATH AUDIT` z zerem full reads/writes, profile bytes,
   all-user scans i per-recipient profile reads dla zwykłego runtime;
10. test na małym oraz syntetycznym profilu co najmniej 35 MB, który musi mieć
    identyczny bounded query count i nie uruchamiać heavy path.

## Kolejność i bramki

- 130.10: integralność profilu, LKG, CAS i izolacja sesji A/B, zakończone
  manualnym testem dwóch kont i dwóch kart.
- 130.11: podpisany dry-run i kontrolowane recovery `Trollu2`, zakończone
  post-apply verify i manualnym ponownym logowaniem.
- 131: audit-only, `READY FOR SPRINT 132`.
- 132: backend suite read model + privacy/cache tests.
- 133: listy desktopowe bez aktywnych map/teleport requestów.
- 134: opaque map/teleport + Territory Control integration, manual gameplay.
- 135: shared delta/recovery/product GUI, pełna regresja i manual Suite.
- 136: bezpieczne audience facts w istniejącym narrative outbox.
- 137: worker Ollamy, verify/dry-run, test z modelem zastępczym; realny model ma
  osobną bramkę operatorską.
- 138: publikacja BlackNet i fallback E2E, manual feed/CTA.
