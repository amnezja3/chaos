# CHAOS — App Contract

Ten dokument opisuje kontrakt aplikacji w gameplayu CHAOS.

Aplikacja jest narzędziem gracza. Może mieć UI, kategorię, poziomy i efekty mechaniczne, ale uruchamianie z mapy powinno opierać się przede wszystkim na `app.map_actions`.

---

## Zasady główne

### `app.interface`

`app.interface` odpowiada tylko za sposób uruchomienia UI aplikacji.

Przykłady:

* `window`
* `terminal`
* `progressbar_random`
* `button_choices`
* `system_launcher`

To pole mówi desktopowi i launcherowi, jak pokazać aplikację.

Nie powinno decydować, czy aplikacja obsługuje akcję mapy.

---

### `app.map_actions`

`app.map_actions` jest głównym routerem uruchamiania aplikacji z mapy.

Przykład:

```json
{
  "map_actions": ["trace_gps", "trace_device"]
}
```

Jeśli gracz klika akcję mapy `trace_gps`, backend powinien szukać aplikacji, które mają `trace_gps` w `app.map_actions`.

---

### `app.detects`, `app.affects`, `app.interferes_with`

Te pola opisują mechanikę aplikacji:

* `app.detects` mówi, jakie dane aplikacja potrafi wykryć,
* `app.affects` mówi, jakie parametry lub stany aplikacja zmienia,
* `app.interferes_with` mówi, z czym aplikacja wchodzi w konflikt.

Nie powinny same decydować o starcie aplikacji z mapy.

Mogą wpływać na:

* jakość wyniku,
* kompletność zasobów,
* skuteczność operacji,
* konflikty zabezpieczeń,
* ryzyko wykrycia.

---

## Minimalny model aplikacji gameplayowej

| Pole | Znaczenie |
| --- | --- |
| `id` | stabilny identyfikator aplikacji |
| `name` | nazwa widoczna dla gracza |
| `interface` | sposób otwarcia UI |
| `type` | ogólny rodzaj aplikacji |
| `map_actions` | akcje mapy obsługiwane przez aplikację |
| `target_types` | typy celów, na których aplikacja może działać |
| `operation_types` | operacje, które aplikacja może uruchomić |
| `resource_types` | zasoby, które aplikacja może produkować |
| `tags` | tagi wyszukiwania i klasyfikacji |
| `detects` | dane wykrywane przez aplikację |
| `affects` | parametry zmieniane przez aplikację |
| `interferes_with` | zabezpieczenia lub systemy, z którymi aplikacja koliduje |
| `file_size` | waga aplikacji jako pliku/narzędzia w inventory |
| `disk_usage` | miejsce zajmowane po instalacji w profilu gracza |
| `quality_score` | jakość wykonania narzędzia, wpływa na wynik operacji i plików |
| `reliability` | przewidywana niezawodność, wpływa na awarie i ryzyko |
| `creator_power` | syntetyczna moc twórcy, wyprowadzana z poziomu/reputacji twórczej |

### Pola rozwojowe po Sprincie 21

Sprint 21 traktuje poniższe pola jako kontrakt dokumentacyjny pod kolejne
sprinty. Nie każda istniejąca aplikacja musi je już mieć w danych runtime.

| Pole | Znaczenie | Czego nie zastępuje |
| --- | --- | --- |
| `file_size` | Widoczna waga aplikacji jako pliku w `/tools`. | Nie zastępuje ceny ani poziomu wymagań. |
| `disk_usage` | Realny koszt instalacji w przyszłym limicie pojemności. | Nie zastępuje `file_size`, bo instalacja może zajmować więcej niż paczka. |
| `quality_score` | Jakość narzędzia, docelowo wpływa na kompletność zasobów, jakość pliku i price preview. | Nie decyduje, czy aplikacja obsługuje akcję mapy. Od tego jest `app.map_actions`. |
| `reliability` | Niezawodność uruchomienia/operacji, docelowo wpływa na awarie i ryzyko. | Nie zastępuje `risk_level`; dobra aplikacja nadal może być ryzykowna. |
| `creator_power` | Wypadkowa poziomu, respectu i przyszłych kompetencji twórcy. | Nie jest statycznym wymaganiem zakupu; to parametr generowania aplikacji. |

Decision:

* Przyjęto: `file_size` opisuje artefakt aplikacji, a `disk_usage` opisuje koszt po instalacji.
* Przyjęto: `quality_score` i `reliability` są częścią kontraktu aplikacji, ale nie są routerem mapy.
* Przyjęto: aplikacja bez jawnych `operation_types/resource_types` może być support-only, ale powinna być tak oznaczana w UI w kolejnych sprintach.

---

## Klasy pól aplikacji

Sprint 21.5 rozdziela pola aplikacji na cztery grupy. To jest kontrakt dla
runtime, Googleplexa, File Managera i przyszłych kreatorów.

| Grupa | Pola | Odpowiedzialność |
| --- | --- | --- |
| UI / launcher | `interface`, `icon`, `name`, `description`, `system_launcher`, `aliases` | Jak aplikacja jest widoczna i jak się otwiera. |
| Gameplay routing | `map_actions`, `target_types`, `operation_types`, `resource_types`, `support_effects` | Co aplikacja może zrobić w pętli mapy i operacji. |
| Ekonomia / progresja | `price`, `required_level`, `required_respect`, `purchase_account`, `file_size`, `disk_usage`, `quality_score`, `reliability`, `creator_power` | Ile kosztuje, ile waży, jaka jest jakość i jakie są wymagania. |
| Legacy / migracja | `type`, `detects`, `affects`, `interferes_with`, `map_actions_source` | Stare pola mechaniczne i informacje o pochodzeniu kontraktu. |

Decision:

* Przyjęto: tylko grupa gameplay routing decyduje o tym, czy aplikacja pasuje
  do akcji mapy.
* Przyjęto: `interface` nie może być używany jako gameplay router.
* Przyjęto: pola legacy mogą podpowiadać migrację, ale nie są docelowym
  kontraktem kreatora.

## Pola runtime

### Wymagane dla każdej aplikacji

| Pole | Wymaganie |
| --- | --- |
| `id` | Stabilne i unikalne w katalogu Googleplex. |
| `name` | Czytelna nazwa dla gracza. |
| `interface` | Jeden z obsługiwanych launcherów UI. |
| `type` | Ogólna klasyfikacja, także dla legacy i filtrów. |
| `price` | Cena lub `0`; brak ceny nie powinien być zgadywany przez UI. |

### Wymagane dla narzędzia mapy

Jeżeli aplikacja ma działać z menu mapy, musi mieć:

| Pole | Wymaganie |
| --- | --- |
| `map_actions` | Lista obsługiwanych `map_action_id`. |
| `target_types` | Lista typów celów albo świadome `[]`, jeśli narzędzie jest globalne/support. |
| `operation_types` | Lista operacji albo `[]`, jeśli aplikacja jest support-only/natychmiastowa. |
| `resource_types` | Lista zasobów albo `[]`, jeśli aplikacja nie produkuje plików. |

### Opcjonalne, ale zalecane

| Pole | Kiedy używać |
| --- | --- |
| `tags` | Wyszukiwanie, filtrowanie, Googleplex, przyszły research. |
| `app_level` | Czytelny poziom Basic / Advanced / Pro. |
| `risk_level` | Preview ryzyka aplikacji. |
| `support_effects` | Wpływ na ryzyko albo warunki innych operacji. |
| `file_size` | Sprint 22: waga paczki aplikacji. |
| `disk_usage` | Sprint 22: miejsce zajęte po instalacji. |
| `install_size` | Alias runtime dla `disk_usage`, zwracany przez Googleplex i instalator. |
| `quality_score` | Sprint 23: jakość wyniku. |
| `reliability` | Sprint 23: niezawodność działania. |
| `creator_username`, `creator_nick`, `creator_power` | Twórca i moc twórcy dla aplikacji generowanych. |

### Storage runtime po Sprincie 22

Sprint 22 wprowadza miękki model pojemności:

* `file_size` jest normalizowany dla każdej aplikacji,
* `disk_usage` / `install_size` jest normalizowany dla każdej aplikacji,
* brak tych pól nie blokuje starej aplikacji,
* instalator pokazuje wpływ na dysk, ale nie blokuje zakupu,
* twarda blokada braku miejsca nie jest częścią Sprintu 22.

Decision:

* Przyjęto: `install_size` jest kompatybilnym aliasem `disk_usage` dla UI i endpointów.
* Przyjęto: jeśli `disk_usage` nie istnieje, runtime ustawia go na wartość co najmniej równą `file_size`.

### Quality runtime po Sprincie 23

Sprint 23 wprowadza jakość aplikacji do runtime:

| Pole | Runtime |
| --- | --- |
| `creator_power` | Normalizowane `0-100`; dla aplikacji generowanych liczone z poziomu, respectu i HC twórcy. |
| `quality_score` | Normalizowane `0-100`; wpływa na jakość pliku tworzonego przez operację. |
| `reliability` | Normalizowane `0-100`; przygotowane pod awarie/ryzyko bez pełnego rebalance. |

Zasady:

* stare aplikacje dostają wartości domyślne przez normalizację,
* aplikacje generowane dostają wartości zależne od twórcy,
* operacja zapisuje snapshot jakości aplikacji w `source_app_quality`,
* finalizacja operacji może podnieść `file.quality_score` do jakości użytego narzędzia,
* `quality_score` i `reliability` nie zastępują `map_actions`.

Decision:

* Przyjęto: lepszy twórca tworzy lepsze narzędzie już od Sprintu 23.
* Przyjęto: pełne awarie i rebalance ryzyka zostają poza zakresem Sprintu 23.

### Balance runtime po Sprincie 29

Sprint 29 dodaje miękki opis mocy i ceny narzędzia. To nie jest drugi system
sklepu ani finalny balans ekonomii.

| Pole | Runtime |
| --- | --- |
| `power_score` | Liczba `0-100` opisująca siłę kontraktu aplikacji: zakres akcji, operacje, zasoby, jakość, niezawodność, wagę i ryzyko. |
| `price_hint` | Sugerowana cena wynikająca z `power_score`, wagi, trybu działania i rodzaju narzędzia. |
| `balance_tier` | Czytelny poziom balansu: `Basic`, `Advanced`, `Pro`. |
| `recommended_level` | Miękka rekomendacja poziomu gracza dla narzędzia. Nie blokuje instalacji, jeśli aplikacja nie używa twardego `required_level`. |
| `recommended_respect` | Miękka rekomendacja respectu. Nie zastępuje `required_respect`. |

Zasady:

* istniejące seed/legacy aplikacje z ręcznie ustawionym `price` zachowują cenę,
* wszystkie aplikacje dostają `price_hint` i `power_score` przez normalizację,
* aplikacje generowane przez kreatory nie mogą publikować się poniżej własnego
  `price_hint`,
* GhostLab `pro-system-tool` pozostaje droższy i cięższy niż zwykłe narzędzie,
* `price_hint` jest informacją dla UI i przyszłych kreatorów, a nie finalnym
  dynamicznym pricingiem rynku.

Decision:

* Przyjęto: Sprint 29 nie nadpisuje cen seedów testowych i legacy, żeby nie
  rozbić obecnej pętli HC.
* Przyjęto: twarde wymagania `required_level` i `required_respect` zostają tylko
  tam, gdzie już były używane; creator apps dostają miękkie rekomendacje.

### Lifecycle aplikacji po Sprincie 30

Googleplex Tool Laboratory v1 domyka pełny cykl życia aplikacji bez tworzenia
drugiego sklepu ani drugiego runtime:

```text
creator / GhostLab
↓
validated app contract
↓
publish
↓
json_resources.app_config
↓
Googleplex
↓
install
↓
profile.apps + files.tools
↓
map runtime / desktop runtime
↓
uninstall
↓
profile.apps/files.tools cleanup + storage recalculation
```

Zasady:

* `/api/apps/generate` pozostaje ścieżką publikacji istniejących kreatorów,
* GhostLab Publisher pozostaje ścieżką publikacji `pro-system-tool`,
* Googleplex czyta ten sam katalog `json_resources.app_config`,
* install kopiuje kontrakt aplikacji do `profile.apps` i tworzy wpis w
  `files.tools`,
* uninstall usuwa tylko instalację gracza: `profile.apps` i odpowiadający wpis
  `files.tools`,
* uninstall nie usuwa projektu z `files.projects`,
* uninstall nie usuwa seed app ani generated app z katalogu Googleplex,
* uninstall przelicza `storage_used`.

Decision:

* Przyjęto: publikacja i instalacja są rozdzielone. Wycofanie projektu z
  Googleplex to inna akcja niż odinstalowanie narzędzia z profilu gracza.
* Przyjęto: Tool Laboratory v1 to wspólny lifecycle istniejących kreatorów,
  GhostLaba, Googleplexa, File Managera i runtime mapy, a nie nowy moduł obok.

### Guided creator UX po Sprincie 30.5

Sprint 30.5 nie dodaje nowych pól do kontraktu aplikacji. Zmienia sposób, w jaki
gracz podejmuje decyzje w istniejących kreatorach.

Zasada:

```text
friendly decision label
↓
existing contract field
↓
same /api/apps/generate payload
```

Mapowanie UI:

| Język gracza | Pole kontraktu |
| --- | --- |
| Jakim obiektem chcesz się zająć? | `target_types` |
| Skąd gracz ma uruchamiać narzędzie? | `map_actions` |
| Co ma zrobić Twoje narzędzie? | `operation_types` |
| Jakich informacji ma szukać? | `resource_types` |
| Gdzie będzie działało? | `tool_mode` |
| Jak dopracowane jest narzędzie? | `quality_score`, `reliability` |

Decision:

* Przyjęto: guided UX nie zmienia payloadu, nazw pól ani runtime.
* Przyjęto: narracja edukacyjna ma budować świadomość świata gry, bez realnych
  instrukcji technicznych.

## Legacy fallback

Fallback po `type`, `detects`, `affects` i `interferes_with` jest wyłącznie
mechanizmem migracyjnym.

Zasady:

* jawne `app.map_actions` zawsze wygrywa,
* `map_actions_source: migration_inferred` oznacza aplikację wymagającą review,
* nowy kreator nie powinien publikować aplikacji bez jawnych `map_actions`,
* UI może pokazywać informację, że kontrakt jest migracyjny,
* docelowo `detects/type` nie powinny dopisywać akcji mapy w nowych aplikacjach.

Decision:

* Przyjęto: `legacy_inferred` i `migration_inferred` zostają do czasu Sprintu
  24 jako kompatybilność, nie jako projekt docelowy.

### Sprint 24 — klasyfikacja narzędzi mapy

Sprint 24 doprecyzowuje, że tool selection na mapie ma opierać się na
kontrakcie aplikacji, a nie na domysłach z pól legacy.

Zasady runtime:

* jawne `app.map_actions` bez źródła legacy wygrywa zawsze,
* `map_actions_source: migration_inferred` oznacza dane przeniesione z pól
  legacy i nadal podlegające cleanupowi,
* `map_actions_source: legacy_inferred` oznacza akcje wyliczone w runtime dla
  starych aplikacji,
* `migration_inferred` i `legacy_inferred` mogą być wyłączone w dev/test przez
  `CHAOS_LEGACY_MAP_ACTION_FALLBACK=false`,
* nowe kreatory i publisher nie powinny emitować `migration_inferred` ani
  `legacy_inferred`,
* `app.interface` nie bierze udziału w klasyfikacji narzędzia mapy.

Klasyfikacja:

* `scan_ports` jest dla scanner/recon tools,
* `exploit` jest dla exploit/exploit_suite tools,
* `sniff` jest dla sniffer/support/data sniffing tools,
* hybryda może obsługiwać kilka akcji tylko wtedy, gdy ma jawny kontrakt bez
  źródła legacy.

Decision:

* Przyjęto: `exploit_suite` nie dostaje `scan_ports` z samego faktu, że wykrywa
  `open_ports` albo `weak_configs`.
* Przyjęto: PenCombo pozostaje exploitem (`exploit`), a nie scannerem
  (`scan_ports`), dopóki nowy jawny kontrakt nie powie inaczej.

## Checklist przyszłego kreatora

Przed publikacją aplikacji kreator powinien potwierdzić:

1. Czy aplikacja jest tylko UI, czy narzędziem gameplayowym.
2. Jaki ma `interface`.
3. Jakie `map_actions` obsługuje.
4. Na jakich `target_types` działa.
5. Czy uruchamia `operation_types`.
6. Czy produkuje `resource_types`.
7. Czy jest support-only, data-producing, czy hybrydowa.
8. Jakie ma wymagania: `price`, `required_level`, `required_respect`.
9. Jaką ma wagę: `file_size`, `disk_usage`.
10. Jaką ma jakość i niezawodność: `quality_score`, `reliability`.
11. Jakie ryzyko pokazuje graczowi.
12. Czy kontrakt jest jawny, bez fallbacku legacy.

Minimalny wynik kreatora:

```json
{
  "id": "custom_tool_id",
  "name": "Custom Tool",
  "interface": "progressbar_random",
  "type": "scanner",
  "map_actions": ["scan_ports"],
  "target_types": ["router", "server"],
  "operation_types": ["wifi_scanner"],
  "resource_types": ["wifi_networks"],
  "price": 250,
  "file_size": 12,
  "disk_usage": 18,
  "quality_score": 60,
  "reliability": 70
}
```

### Sprint 25 — Step-by-step creator

Istniejące kreatory `AppForge`, `TermCreator`, `WindowMaker` i `ButtonMaker`
korzystają z jednego krokowego modelu UX. Nie tworzą osobnego sklepu ani
osobnego publishera.

Kroki kreatora:

1. `meta` — nazwa, ikona, opis i cena.
2. `tool_type` — typ narzędzia i pola rozpoznania.
3. `environment` — `interface` oraz `target_types`.
4. `map_actions` — jawne akcje mapy / desktopu.
5. `operations` — `operation_types`.
6. `resources` — `resource_types`.
7. `risk` — `interferes_with`, `requires_off`, `disables`, `affects`.
8. `storage_quality_preview` — podgląd wagi, jakości i niezawodności.
9. `publish` — publikacja przez `/api/apps/generate`.

Wynik publikacji:

* aplikacja trafia do `json_resources.app_config`,
* projekt trafia do `files.projects`,
* `map_actions` wybrane w kreatorze są zapisywane jako jawny kontrakt,
* `map_actions_source` dla takiej aplikacji ma wartość `creator_explicit`,
* brak wyboru `map_actions` nadal oznacza aplikację UI/support albo legacy,
  ale nowy kreator powinien zachęcać do jawnego kontraktu.

Decision:

* Przyjęto: Sprint 25 zmienia UX kreatorów, a nie tworzy nowego runtime.
* Przyjęto: `/api/apps/generate` pozostaje jedyną ścieżką publikacji dla tych
  kreatorów.
* Przyjęto: kreator pokazuje storage/quality preview, ale nie implementuje
  jeszcze twardych blokad pojemności ani ścieżek Scanner/Exploit ze Sprintów
  26-27.

### Sprint 26 — Scanner / Recon path

Scanner jest rodziną narzędzi rozpoznania, a nie pojedynczą akcją
`scan_ports`.

Tryby kreatora:

| Tryb | Znaczenie | `map_actions` |
| --- | --- | --- |
| `map` | Scanner uruchamiany z mapy na konkretny obiekt. | Wymagane, jawne. |
| `desktop` | Scanner uruchamiany z pulpitu na aktualny `aimed_target`. | Może być puste. |
| `hybrid` | Scanner działający z mapy i z desktopu. | Jawne, jeśli ma działać z mapy. |

Pola:

* `tool_family: scanner_recon` oznacza ścieżkę Scanner / Recon,
* `scanner_mode` opisuje tryb `map`, `desktop` albo `hybrid`,
* `map_actions_source: creator_explicit` oznacza wybór gracza w kreatorze,
* desktop scanner nie powinien dostawać `map_actions` z fallbacku legacy,
* hybryda może mieć recon/diagnostic behavior, ale nie staje się przez to
  ścieżką Exploit/Sniffer ze Sprintu 27.

Scanner / Recon może służyć do:

* rozpoznania celu,
* wykrywania usług,
* wykrywania sieci,
* śledzenia,
* diagnostyki celu,
* przygotowania późniejszej operacji.

Decision:

* Przyjęto: dla `tool_family: scanner_recon` kreator zapisuje jawny kontrakt i
  nie polega na inferencji `type/detects`.
* Przyjęto: PenCombo-like hybrydy zachowują miejsce w kontrakcie, ale Sprint 26
  nie implementuje ścieżki Exploit/Sniffer.

### Sprint 27 — Exploit / Sniffer path

Istniejący wizard obsługuje kolejne rodziny narzędzi:

| `tool_family` | Znaczenie |
| --- | --- |
| `exploit` | Symulowane przełamanie, zakłócenie albo wpływ na cel w świecie gry. |
| `sniffer` | Symulowana obserwacja, podsłuch, zbieranie danych albo implant. |

Każda rodzina może działać w trybie:

| `tool_mode` | Znaczenie |
| --- | --- |
| `map` | Narzędzie widoczne przy jawnych `map_actions`. |
| `desktop` | Narzędzie działające na aktualny `aimed_target`; `map_actions` może być puste. |
| `hybrid` | Narzędzie działa z mapy i z desktopu. |

Zasady:

* `tool_family: exploit` i `tool_family: sniffer` zapisują jawny kontrakt,
* `map_actions_source: creator_explicit` oznacza wybór gracza w kreatorze,
* brak `map_actions` w trybie desktop nie uruchamia fallbacku legacy,
* `tool_mode` jest ogólnym polem trybu działania,
* `scanner_mode` pozostaje kompatybilnym aliasem tylko dla Scanner / Recon.

Exploit może deklarować między innymi:

* `map_actions`: `exploit`, `camera_shutdown`, `install_sniffer`,
  `audio_hack`, `car_hack`,
* `operation_types`: `camera_shutdown`, `persistent_sniffer`,
  `audio_interference`, `vehicle_ecu`,
* `resource_types` tylko wtedy, gdy wybrana operacja realnie produkuje zasób.

Sniffer może deklarować między innymi:

* `map_actions`: `sniff`, `mic_sniff`, `atm_logs`, `install_sniffer`,
  `camera_stream`,
* `operation_types`: `persistent_sniffer`, `microphone_sniffer`,
  `atm_log_extraction`, `camera_stream`,
* `resource_types`: `credentials`, `financial_records`, `atm_dump`,
  `audio_transcript`, `camera_dump`, `video_material`, `device_logs`,
  `internal_recon_state`.

Decision:

* Przyjęto: Sprint 27 rozszerza kreator i kontrakt aplikacji, ale nie zmienia
  runtime mapy ani nie dodaje nowych operacji.
* Przyjęto: opisy w UI pozostają edukacyjne i gameplayowe; nie opisują realnych
  komend ani realnych technik ofensywnych.

### Sprint 28 — GhostLab pro-system-tool contract

GhostLab jest cięższym IDE dla `pro-system-tool`, ale publikuje do tego samego
katalogu aplikacji co istniejące kreatory.

Zasady:

* Publisher GhostLab zapisuje rekord do `json_resources.app_config`,
* typ aplikacji pozostaje `type: pro-system-tool`,
* kategoria pozostaje `category: pro-system-tools`,
* `source: ghostlab` i `ghostlab_generated: true` oznaczają pochodzenie,
* `map_actions_source: ghostlab_contract` oznacza kontrakt wygenerowany przez
  Publisher,
* aplikacja nadal instaluje się przez Googleplex i `/install-app`,
* runtime custom pro-system pozostaje `pending_custom_runtime`, jeśli nie ma
  osobnego wykonania.

Minimalny kontrakt GhostLab Publisher:

| Pole | Wymaganie |
| --- | --- |
| `tool_family` | Rodzina narzędzia wyprowadzona z template. |
| `tool_mode` | Domyślnie `desktop`, bo pro-system-tools działają przez Player Hack Access. |
| `map_actions` | Domyślnie `[]`, chyba że przyszły runtime jawnie doda akcje mapy. |
| `target_types` | Domyślnie `player`. |
| `operation_types` | `[]`, dopóki custom runtime nie tworzy nowych operacji. |
| `resource_types` | Jawne zasoby wynikające z template lub `internal_recon_state`. |
| `file_size`, `disk_usage`, `install_size` | Normalizowane jak dla innych aplikacji. |
| `creator_power`, `quality_score`, `reliability` | Liczone z profilu twórcy. |
| `required_level`, `required_respect` | Zachowane z wymagań template. |

Decision:

* Przyjęto: GhostLab nie ma osobnego sklepu ani osobnego publishera runtime.
* Przyjęto: custom pro-system-tool nie tworzy nowych `operation_type` bez
  przyszłego runtime.
* Przyjęto: Player Hack Access pozostaje bramką działania pro-system-tools.

---

## Przykłady aplikacji

### GPS Tracker

```json
{
  "id": "gps_tracker",
  "name": "GPS Tracker",
  "interface": "progressbar_random",
  "map_actions": ["trace_gps"],
  "target_types": ["vehicle"],
  "operation_types": ["vehicle_tracking"],
  "resource_types": ["gps_logs", "location_history"]
}
```

### Camera Viewer

```json
{
  "id": "camera_viewer",
  "name": "Camera Viewer",
  "interface": "window",
  "map_actions": ["camera_stream"],
  "target_types": ["camera"],
  "operation_types": ["camera_stream"],
  "resource_types": ["camera_dump"]
}
```

### ATM Log Reader

```json
{
  "id": "atm_log_reader",
  "name": "ATM Log Reader",
  "interface": "terminal",
  "map_actions": ["atm_logs"],
  "target_types": ["atm"],
  "operation_types": ["atm_log_extraction"],
  "resource_types": ["atm_dump", "financial_records"]
}
```

### Mic Sniffer

```json
{
  "id": "mic_sniffer",
  "name": "Mic Sniffer",
  "interface": "progressbar_random",
  "map_actions": ["mic_sniff", "audio_hack"],
  "target_types": ["person", "venue"],
  "operation_types": ["microphone_sniffer"],
  "resource_types": ["audio_transcript"]
}
```

### Port Scanner

```json
{
  "id": "port_scanner",
  "name": "Port Scanner",
  "interface": "progressbar_random",
  "map_actions": ["scan_ports"],
  "target_types": ["poi", "camera", "atm", "player", "server", "router"],
  "operation_types": ["recon_scan"],
  "resource_types": ["internal_recon_state"]
}
```

Port Scanner obsługuje `scan_ports`, ale zgodnie z nowszym kontraktem `map_actions` / `operations` nie produkuje zasobów handlowych.

`internal_recon_state` oznacza wewnętrzny stan rozpoznania celu używany w procesie hackowania, a nie plik na sprzedaż.

### ECU Injector

```json
{
  "id": "ecu_injector",
  "name": "ECU Injector",
  "interface": "button_choices",
  "map_actions": ["car_hack"],
  "target_types": ["vehicle"],
  "operation_types": ["vehicle_ecu"],
  "resource_types": ["vehicle_diagnostics"]
}
```

---

## Routing z mapy

Docelowy flow:

```text
map_action_id
↓
znajdź aplikacje z app.map_actions zawierającym map_action_id
↓
brak aplikacji: komunikat systemowy
jedna aplikacja: automatyczny start
kilka aplikacji: wybór narzędzia
↓
uruchom app.interface
↓
aplikacja startuje operation_type albo wykonuje akcję natychmiastową
```

## Decyzje człowieka

* `operation_types` w aplikacji jest zawsze listą, nawet jeśli aplikacja uruchamia tylko jedną operację.
* Aplikacja może obsługiwać `map_action_id`, ale nie tworzyć operacji.
* Fallback po starych polach `detects` i `type` zostaje tylko jako migracja i docelowo znika po sprintach gameplayowych.

## admin_seed_v1

`admin_seed_v1` oznacza produkcyjny seed narzędzi Googleplexa przygotowany przez
konto admin/CyberPhoenix.

To nie jest testowy `admin_test_seed`.

Zasady:

* `map_actions_source: admin_seed_v1`,
* `purchase_account: admin`,
* `creator_username: admin`,
* `creator_nick` z profilu admina albo fallback `CyberPhoenix`,
* `creator_level_at_publish: 80`,
* `generated: false`,
* `published: true`,
* pełny jawny kontrakt:
  * `tool_family`,
  * `tool_mode`,
  * `target_types`,
  * `map_actions`,
  * `operation_types`,
  * `resource_types`,
  * `risk_level`,
  * `file_size`,
  * `disk_usage`,
  * `install_size`,
  * `creator_power`,
  * `quality_score`,
  * `reliability`,
  * `power_score`,
  * `price_hint`,
  * `balance_tier`.

Po cleanupie katalogu aplikacji `admin_seed_v1` ma zapewnić co najmniej jedno
sensowne narzędzie dla każdej istotnej akcji mapy.

Decision:

* Przyjęto: `admin_seed_v1` jest produkcyjnym katalogiem startowym narzędzi, a
  nie developerskim smoke seedem.
* Przyjęto: `admin_test_seed` może być usuwany przez skrypty cleanupu katalogu.
* Przyjęto: `migration_inferred` nie jest finalnym źródłem klasyfikacji narzędzia
  i powinno zostać wyczyszczone albo ręcznie zatwierdzone przed serwerowym RC.

## TODO_DECISION

* Czy `internal_recon_state` zostaje nazwą stanu rozpoznania dla wszystkich scannerów, czy powstanie kilka typów stanów rozpoznania.

## Operation Feedback adapter — 130.8.6.1

OFS jest opcjonalnym adapterem prezentacji wokół istniejącego requestu
`/gonna-win`; nie jest nowym `app.interface` i nie zmienia kontraktu aplikacji.

W spike'u obsługiwane jest wyłącznie `map_action_id=scan_ports`, po włączeniu
obu flag:

```text
CHAOS_OPERATION_FEEDBACK_ENABLED
CHAOS_OPERATION_FEEDBACK_SCAN_PORTS
```

Launcher przekazuje lokalnie `action_key` i zamrożony `security_state` do okna
aplikacji. Dane prezentacyjne nie są dodawane do requestu gameplayowego.
`flow_id`, receipt, `choice_id`, expected target, kolejka i idempotencja
pozostają własnością obecnego runtime. Flag-off zachowuje legacy UI.
