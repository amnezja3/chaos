# App uninstall — canonical inventory i launcher

Data: 2026-08-27  
Status: `READY FOR SERVER VALIDATION`

## Problem / objawy

Po deinstalacji aplikacji z Menedżera Plików `/tools` aplikacja mogła pozostać
w Menu Start. Sama operacja zachowywała się jak ciężki odczyt profilu.

## Root cause

`POST /api/apps/uninstall` wykonywał `sync_session_profile()` i zapis przez
`UserProfileManager`, czyli pełny read/write `profile_json`. Jednocześnie
kanonicznym źródłem aplikacji, plików narzędzi i storage jest wydzielony
`PlayerInventoryStore`.

Endpoint usuwał wpis tylko z profilowego mirrora. Nie oznaczał odpowiadającego
rekordu `player_apps` jako `uninstalled`, dlatego późniejszy inventory overlay
albo recovery mógł ponownie wprowadzić aplikację do projekcji pulpitu i Menu
Start.

## Finalne rozwiązanie

- uninstall czyta wyłącznie bounded snapshot `PlayerInventoryStore`;
- aplikacja, powiązane `player_tool_files` i wykorzystanie `player_storage` są
  aktualizowane w jednej transakcji `BEGIN IMMEDIATE`;
- request transaction precommit guard chroni transakcję przed replaced session;
- odpowiedź oraz `apps.app_uninstalled` niosą kanoniczne `apps` i `files.tools`;
- frontendowy `updateAppsView()` natychmiast przebudowuje pulpit i Menu Start;
- retry jest idempotentny i zwraca `noop` bez ponownego odjęcia storage;
- brak kanonicznej migracji kończy się fail-closed `inventory_not_initialized`,
  bez fallbacku do pełnego profilu.

## Testy i weryfikacja

- uninstall aplikacji + tool + storage;
- install → uninstall oraz seed/GhostLab lifecycle;
- retry uninstall → `noop`, storage bez drugiego odjęcia;
- stale profilowy mirror nie wskrzesza aplikacji;
- syntetyczny profil 35 MB:
  `profile_full_read=0`, `profile_full_write=0`, `profile_bytes=0`;
- A request → login B przed commit → rollback całej transakcji;
- frontend: launcher znika z Menu Start i pulpitu, pozostałe katalogi zostają;
- 5/5 testów celowanych, 69/69 inventory/migration/hot-path oraz 134/134
  gameplay/session — OK;
- 14/14 pakietów Node, `py_compile`, `node --check`, `git diff --check` — OK.

## Bramka manualna

Po wdrożeniu odinstalować zwykłą aplikację z `/tools` i potwierdzić bez
odświeżania strony:

1. plik znika z `/tools`;
2. launcher znika z Menu Start i pulpitu;
3. ponowne otwarcie Menu Start oraz `/api/profile` nie przywraca aplikacji;
4. storage zmniejsza się raz;
5. ponowny uninstall jest bezpiecznym `noop`;
6. operacja nie powoduje heavy-profile freeze.

