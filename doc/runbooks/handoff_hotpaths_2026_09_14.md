# Załącznik przekazania: ciężkie profile, lekkie ścieżki i audyt regresji

Stan: 2026-09-14, kod `96dec35`. Czytać razem z
[głównym handoffem](handoff_project_2026_09_14.md) i
[wiążącym kontraktem 130.11+](../architecture/profile_hot_path_contract_130_11_plus.md).

## 1. Co ten spis udowadnia

To **statyczna mapa miejsc do analizy**, nie profil czasu wykonania ani lista
potwierdzonych nowych bugów. Bezpośrednie wywołanie `get_profile` może leżeć
w rzadkim wariancie, recovery, mutacji albo ścieżce normalnego odczytu.
Ten sam endpoint może mieć wariant lekki i ciężki. Brak takiego wywołania
w endpointcie nie wyklucza go w helperze.

W szczególności nie ogłaszaj „aim-target już zawsze lekki” ani „gonna-win
zawsze ciężkie”. W `map_aim_target` wariant celu gracza nadal odczytuje jego
profil/security, podczas gdy inne warianty korzystają z nowych ścieżek.
`gonna_win` ma wczesny powrót `operation_only`, a dalej inne efekty i mutacje.
Regresję ocenia się dla konkretnego wejścia i całego call chainu.

## 2. Główne granice API profilu

| Symbol / mechanizm | Znaczenie |
| --- | --- |
| `UserStore.get_profile` | Runtime read po 130.10.1; nadal pełny JSON, nie bounded scalar read |
| `get_profile_with_revision` | Odczyt wymagający kontraktu revision/integrity; zachować semantykę |
| `UserProfileManager` | Mutacja/obsługa profilu; nie używać do odczytu drobnej metadanej |
| `sync_session_profile` | Legacy synchronizacja/hydratacja; audytować wszystkich callerów |
| `load_profile_readonly` | Nazwa nie oznacza braku pełnego JSON; audyt callerów |
| `merge_latest_profile_runtime_fields` | Merge ze świeżym profilem może przywrócić pełny odczyt w pozornie lekkiej ścieżce |
| `list_profiles` | Odczyt wielu pełnych dokumentów; szczególnie groźny w requestach/audience |
| `UserIdentityProjectionStore.get_desktop_boot` | Ograniczony boot/tożsamość z integrity gate |
| `UserCapabilityProjectionStore.get_capabilities` | Projekcja możliwości, nie hydratacja całego konta |
| `PlayerTargetRuntimeStore`, `PlayerMarkedTargetStore` | Cel/postęp oddzielony od profilu |
| `PlayerOperationStore`, `PlayerInventoryStore` | Kanoniczne operacje/inventory zamiast lustrzanej historii |

## 3. Pozostałe bezpośrednie callsite'y w `run.py`

Nazwy poniżej pochodzą z przeglądu `get_profile`, `list_profiles` i
`UserProfileManager`. Numery linii celowo pominięte — szybko się przesuwają.
Wyszukaj definicję i jej callerów. Nie zamieniaj wszystkich na projekcje jednym
mechanicznym find/replace: niektóre rzeczywiście zapisują kanoniczne pola.

| Obszar | Symbole do sprawdzenia | Pytanie audytowe |
| --- | --- | --- |
| BlackNet fakty | `build_blacknet_world_facts_snapshot` | Czy użyty wariant wpada w `list_profiles`? Czy da się policzyć fakty z indeksów? |
| Audience/terytoria | `territory_engagement_audience` | Czy klan odbiorcy powoduje pełny read per gracz? |
| Intruders | `sync_static_area_intruders_for_owner` | Kiedy skan wielu profili jest uruchamiany i czy wewnątrz requestu? |
| Konflikty | `detect_multi_conflict_candidates` | Domyślny `profile_lookup` jest ciężki; czy caller przekazuje bounded lookup? |
| Reconcile/rebuild | `restore_territory_reconcile_targets`, `consolidate_conflict_rebuild`, `rebuild_conflict_polygons` | Zakres uczestników, writer lock, czy utrzymanie świata uruchamia się na zwykłym odczycie? |
| Poziom i runtime GN | `territory_player_level`, `build_ghostnetwork_runtime_coordinator` | Czy scalar level/effect callback musi czytać pełny dokument? |
| Merge | `merge_latest_profile_runtime_fields` | Czy merge jest wymagany dla rzeczywistej mutacji, czy niechcianą hydratacją? |
| Market/GX | `refresh_market_runtime`, `commit_ghost_exchange_runtime` | Które pola są canonical profile, które inventory/ledger; ile read/write na sprzedaż? |
| Operacje | `refresh_and_persist_operations`, `persist_operation_control_profile` | Czy droga cancel/refresh wraca do pełnego profilu lub historii? |
| Security | `save_owned_hacked_security`, `target_security_status` | Odczyt vs rzeczywista mutacja security, liczba odczytów |
| Terytoria przy celu | `find_area_for_point`, `find_contested_targets_for_player`, `contested_targets_from_active_conflicts` | Czy każdy obszar czyta właściciela? Czy cache jest lokalny i ograniczony? |
| Intrusion | `notify_area_intrusion` | Czy powiadomienie potrzebuje tylko tożsamości aktora? |
| Googleplex produkt | `persist_googleplex_product_profile` | Kanoniczna mutacja vs niepotrzebna pełna odbudowa, ochrona CAS |
| Player hack | `serialize_player_hack_access`, `build_victim_picker_player_candidates` | Czy sama prezentacja czyta profile ofiary i atakującego? |
| Progresja/terytoria | `finalize_territory_progression_receipt`, `refresh_stale_territory_polygons` | Czy receipt pozostaje idempotentny po ograniczeniu reads? |
| Generowane aplikacje | `build_generated_app` | Czy dane twórcy mogą być projekcją; co naprawdę wymaga pełnego profilu? |
| Rejestracja | `register_check_username`, `api_register_finalize` | `list_profiles` dla email/username, osobno prawdziwe utworzenie konta |
| Dev/admin | `build_dev_state`, `build_admin_dashboard_state` | Ciężka lista użytkowników; nie uruchamiać dla zakładki bugów |
| Mapa i hack | `map_aim_target`, `map_action`, `hack_action` | Rozdziel wariant POI/player/conflict, capture/operation_only i read/mutation |
| GX API | `api_ghost_exchange_preview`, `api_ghost_exchange_sell` | Preview nie powinien odziedziczyć kosztu całego profilu; sprzedaż ma guarded effects |
| Konto/security API | `update_profile_security`, `update_profile_account` | Jawny wyjątek mutacyjny, nie pretekst do globalnych scans |
| Narzędzia na gracza | `api_player_hack_tool_use`, `mark_player_target` | Wiele możliwych branchy i dwa konta; potrzebny test każdego efektu |
| Picker | `victim_picker_candidates`, `victim_picker_aim` | Ograniczona lista i bezpieczeństwo celu; unikać read per kandydat |
| Mapa graczy | `map_friends`, `map_player_actors` | Fan-out i częstotliwość odpytywania; sparse identity/position |
| Response Network | `execute_response_network_consequence` | Koszt prawdziwej konsekwencji vs prezentacja; nie osłabić reguł mechaniki |
| GhostLab | `ghostlab_create_project`, `ghostlab_rename_project`, `ghostlab_update_project_blueprint`, `ghostlab_compile_project`, `ghostlab_publish_project`, `ghostlab_delete_project` | Rzeczywiste mutacje projektu; wyizolować zakres i integralność |
| Apps | `generate_app`, `remove_generated_app`, `install_app` | Inventory vs canonical profile; nie zgubić opłat/uprawnień/receipts |
| Uruchomienie aplikacji | `gonna_win` | Wczesna lekka ścieżka `operation_only` kontra późniejsze efekty/capture |

To mapa `run.py`, nie kompletny call graph repo. Szukaj również w workerach,
`ghostnetwork/`, helperach profilu, BlackNet i skryptach administracyjnych.
Przykład wyszukiwania całego kodu:

```text
rg -n 'sync_session_profile|UserProfileManager\(' . -g '*.py'
rg -n '\.(get_profile|list_profiles|get_profile_with_revision)\(' . -g '*.py'
rg -n 'json_extract|BEGIN IMMEDIATE|deepcopy' database.py profileManagment.py
rg -n 'profile_full|HOT_PATH|PROFILE_WRITE_METRICS' . -g '*.py'
```

Wyniki w testach są często ochroną przed regresją, nie produkcyjnym callem.
Default callback bywa ciężki, choć konkretny caller wstrzykuje lekki provider.
Nie diagnozuj bez sprawdzenia wiring.

## 4. Zależności nowych ścieżek

```text
kanoniczny zapis + receipt + scope version
    → ograniczona projekcja / delta
    → klient sprawdza generację, epokę i wersję
    → merge właściwego scope
    → bounded recovery, jeśli wykryto lukę
```

- Usunięcie mirror profilu wymaga, by wszyscy czytelnicy danego scope przeszli
  na canonical store. Przykład: operacja → plik → File Manager → GX.
- Zmiana transportu nie usuwa obowiązku zachowania `target_id` i canonical
  marker binding. UI może być płynny, ale wykonywać akcję na złym obiekcie.
- Zmiana cache nie zastępuje trwałego receipt/dedupe. Po restarcie procesu
  te zabezpieczenia muszą nadal działać.
- Krótki request nie dowodzi krótkiego writer locka. Mierz czas trzymania
  blokady, także przy jednoczesnym territory workerze.
- `operation_only` nadal aktualizuje dozwolony cache sesji z istniejącego
  kontekstu; nie myl tego z przyzwoleniem na zastępowanie go sparse profilem.
- Przejście na identity projection musi respektować integrity status konta,
  a nie omijać quarantined/recovery state.

## 5. Minimalny szablon audytu kolejnego sprintu poprawkowego

1. **Objaw i wejście:** endpoint/app, typ celu, konto, rozmiar profilu,
   częstotliwość, współbieżne requesty i workery. Bez prywatnych payloadów.
2. **Call chain:** frontend → route → helper → store → zapis/odpowiedź.
   Zaznacz oba warianty: główny i fallback/recovery.
3. **Authority:** która tabela/receipt jest kanoniczna, jaka projekcja jest
   tylko odczytem, jaka wersja i audience obowiązują.
4. **Pomiar przed:** pełne odczyty/zapisy/bajty, query count, writer wait,
   request latency dla małego i ciężkiego profilu.
5. **Zmiana ograniczona:** bez nowych źródeł prawdy, bez usunięcia integralności,
   bez all-users fallback. Zachować idempotencję i izolację sesji.
6. **Regresje:** końcowy efekt (np. plik/HC), retry, stale response, dwa konta,
   duplicate action, restart, brak projekcji/uszkodzona tożsamość.
7. **Pomiar po i odbiór:** ten sam scenariusz, informacja o niewykonanym QA.
8. **Artefakty:** sprint/hardbugfix + journal + test. Nazwij świadomie
   pozostawione ciężkie wyjątki i otwarte punkty, nie wpisuj „wszystko lekkie”.

## 6. Źródła historyczne, które trzeba zachować

- [130.10.1 hot path recovery](../sprints/sprint_130_10_1_hot_path_recovery.md)
- [130.11+ kontrakt](../architecture/profile_hot_path_contract_130_11_plus.md)
- [135.5 regresja operacji/plików/GX](../hardbugfix/heavy_profile_operation_files_gx_regression_sprint_135_5_2026-08-30.md)
- [138 marker identity](../hardbugfix/scan_marker_menu_identity_leaflet_dispatch_sprint_138_getway_3_5_2026-09-07.md)
- [138 Operation Center/Leaflet](../hardbugfix/138_operation_center_cache_signature_canvas_bounds_2026-09-09.md)
- [stare przekazanie 139–140](handoff_sprints_139_140.md) — wyłącznie historyczny status,
  nadal użyteczne szczegółowe kontrakty i lekcje.

`bounceback` pozostaje nazwą historyczną z opisów. Przy użyciu tego słowa
w nowym sprincie dopisz, który konkretnie request, merge lub recovery masz
na myśli, aby nie stworzyć kolejnej niejednoznacznej warstwy architektury.
