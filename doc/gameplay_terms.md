# CHAOS — Gameplay Terms

## Nazwa gry

**CHAOS** oznacza **Cyber Hacking Adventure Of Senses**.

Hasło gry:

> Hack the digital senses of the modern world.

Po polsku:

> Hakuj cyfrowe zmysły współczesnego świata.

CHAOS nie jest tylko grą o hakowaniu komputerów. Gracz ingeruje w cyfrowe zmysły współczesnego świata:

* kamery jako oczy,
* mikrofony jako uszy,
* sieci jako nerwy komunikacyjne,
* telefony jako tożsamość,
* internet jako świadomość cyfrowego świata.

Ten dokument porządkuje słownik pojęć używany w gameplayu, backendzie, mapie, aplikacjach i dokumentacji.

---

## Zasada główna

Każde pole ma jedną odpowiedzialność.

Najważniejsze rozdzielenia:

* `app.interface` mówi tylko, jak aplikacja otwiera UI.
* `app.map_actions` mówi, jakie akcje mapy aplikacja obsługuje.
* `app.detects`, `app.affects` i `app.interferes_with` opisują mechanikę aplikacji, ale nie powinny być głównym routerem uruchamiania z mapy.
* `map_action_id` nie jest tym samym co `operation_type`.
* `target_type` nie jest tym samym co `source_type`, ale może być z niego wyprowadzany.

---

## map_action_id

Identyfikator akcji wykonywanej z poziomu mapy.

Przykłady:

* `scan_ports`
* `trace_gps`
* `camera_stream`
* `install_sniffer`

Użycie:

* menu mapy,
* routing akcji mapy,
* `app.map_actions`,
* wybór aplikacji zdolnej wykonać akcję.

Nie zastępuje:

* `operation_type`,
* `app.interface`,
* `source_type`.

`map_action_id` mówi, co gracz chce zrobić na mapie.

---

## operation_type

Typ operacji uruchamianej po użyciu aplikacji.

Przykłady:

* `vehicle_tracking`
* `device_tracking`
* `atm_sniffer`
* `camera_stream`
* `microphone_sniffer`

Użycie:

* aktywne operacje,
* czas życia operacji,
* produkcja zasobów,
* ryzyko wykrycia.

Nie zastępuje:

* `map_action_id`,
* `app.type`,
* `resource_type`.

`map_action_id` może uruchamiać `operation_type`, ale nie jest tym samym. Akcja mapy jest intencją gracza, operacja jest żyjącym stanem gry.

---

## target_type

Gameplayowy typ celu.

Przykłady:

* `camera`
* `atm`
* `shop`
* `person`
* `phone`
* `vehicle`
* `player`
* `server`

Użycie:

* walidacja, czy akcja pasuje do obiektu,
* dobór menu mapy,
* `app.target_types`,
* model świata.

Nie zastępuje:

* `source_type`,
* `target_mode`.

Lista `target_type` rozwija się rozwojowo. Nie zamykamy jej na sztywno, ale utrzymujemy kontrolowany słownik.

---

## source_type

Techniczne lub zewnętrzne źródło obiektu mapy.

Przykłady:

* `camera`
* `restaurant`
* `manual`
* `generated`
* `player`

Użycie:

* import z mapy,
* heurystyka klasyfikacji,
* debugowanie źródeł danych,
* mapowanie do `target_type`.

Nie zastępuje:

* `target_type`.

`source_type` mówi, skąd obiekt pochodzi. `target_type` mówi, czym jest w gameplayu.

Mapowanie `source_type -> target_type` jest opisane osobno w `doc/source_type_mapping.md`.

---

## target_mode

Tryb celu w mechanice hackowania.

Przykłady:

* `poi`
* `player`
* `vulnerability`
* `conflict_pillar`

Użycie:

* rozróżnienie zwykłego celu, gracza, podatności i filaru konfliktu,
* walidacja specjalnych ścieżek hackowania,
* wybór reguł po udanym hacku.

Nie zastępuje:

* `target_type`,
* `source_type`.

`target_mode` mówi, w jakim trybie system obsługuje cel.

---

## resource_type

Typ zasobu produkowanego przez operację.

Przykłady:

* `gps_logs`
* `device_logs`
* `audio_transcript`
* `atm_dump`
* `camera_dump`
* `credentials`
* `financial_records`

Użycie:

* pliki,
* rynek danych,
* wycena,
* kompletność paczek danych.

Nie zastępuje:

* `file_category`,
* `market_category`,
* `operation_type`.

`resource_type` mówi, co powstało jako wartość gameplayowa.

---

## file_category

Kategoria pliku w systemie plików gracza.

Przykłady:

* `gps`
* `audio`
* `camera`
* `atm`
* `credentials`

Użycie:

* katalogi,
* widok plików,
* filtrowanie lokalne.

Nie zastępuje:

* `resource_type`,
* `market_category`.

`file_category` organizuje pliki w systemie gracza.

---

## market_category

Kategoria zasobu na rynku danych.

Przykłady:

* `location`
* `financial`
* `credentials`
* `surveillance`
* `personal`

Użycie:

* Ghost Exchange,
* wycena,
* filtrowanie ofert,
* preferencje kupujących.

Nie zastępuje:

* `resource_type`,
* `file_category`.

`market_category` mówi, jak rynek traktuje zasób.

---

## risk_event

Typ zdarzenia ryzyka.

Przykłady:

* `camera_detected`
* `failed_exploit`
* `atm_alarm`
* `long_operation_detected`

Użycie:

* system konsekwencji,
* alarmy,
* cooldowny,
* utrata HC,
* przerwanie operacji.

Nie zastępuje:

* `risk_level`,
* `operation_type`.

`risk_event` jest zdarzeniem, które może wyniknąć z operacji albo błędu gracza.

---

## app.interface

Sposób otwierania aplikacji w systemie gracza.

Przykłady:

* `window`
* `terminal`
* `progressbar_random`
* `button_choices`
* `system_launcher`

Użycie:

* desktop,
* launcher,
* `/command`,
* efekt wizualny aplikacji.

Nie zastępuje:

* `app.map_actions`,
* `operation_type`,
* `app.type`.

`app.interface` mówi tylko, jak aplikacja się otwiera. Nie mówi, co aplikacja potrafi zrobić na mapie.

---

## app.map_actions

Lista akcji mapy obsługiwanych przez aplikację.

Przykład:

```json
["trace_gps", "trace_device"]
```

Użycie:

* główny router uruchamiania aplikacji z mapy,
* wybór narzędzia przy akcji mapy,
* walidacja, czy gracz posiada odpowiednią aplikację.

Nie zastępuje:

* `app.interface`,
* `app.detects`,
* `app.affects`,
* `app.interferes_with`.

To powinno być podstawowe pole decydujące, czy aplikacja może obsłużyć `map_action_id`.

---

## app.type

Ogólny rodzaj aplikacji.

Przykłady:

* `scanner`
* `exploit`
* `sniffer`
* `pro-system-tool`
* `system_lab`

Użycie:

* kategorie Googleplex,
* ogólne filtrowanie aplikacji,
* balans i wymagania.

Nie zastępuje:

* `app.map_actions`,
* `app.interface`.

`app.type` może pomagać w klasyfikacji, ale nie powinien sam decydować, czy aplikacja obsługuje konkretną akcję mapy.

---

## app.tags

Luźne tagi opisujące aplikację.

Przykłady:

* `finance`
* `intel`
* `gps`
* `camera`
* `social`

Użycie:

* wyszukiwanie,
* filtrowanie,
* UI,
* przyszłe research/gating.

Nie zastępuje:

* `app.map_actions`,
* `resource_type`,
* `operation_type`.

Tagi są pomocnicze i nie powinny być głównym routerem gameplayu.

---

## app.detects

Lista rzeczy, które aplikacja potrafi wykrywać.

Przykłady:

* `open_ports`
* `user_location`
* `camera_feed`
* `financial_data`

Użycie:

* jakość wyniku,
* kompletność danych,
* możliwości poboczne aplikacji.

Nie zastępuje:

* `app.map_actions`.

`detects` opisuje mechanikę aplikacji, ale nie powinno być głównym routerem uruchamiania z mapy.

---

## app.affects

Lista parametrów lub stanów, które aplikacja zmienia.

Przykłady:

* `risk_level`
* `traceability`
* `system_integrity`

Użycie:

* wpływ aplikacji na cel,
* efekty po zakończeniu operacji,
* balans zabezpieczeń.

Nie zastępuje:

* `app.map_actions`,
* `app.interferes_with`.

`affects` mówi, co aplikacja zmienia, a nie do jakiej akcji mapy jest przypisana.

---

## app.interferes_with

Lista zabezpieczeń, systemów lub mechanizmów, z którymi aplikacja wchodzi w konflikt.

Przykłady:

* `firewall`
* `camera_system`
* `gps_tracker`
* `vpn_enabled`

Użycie:

* warunki skuteczności,
* konflikty zabezpieczeń,
* wymagania przed operacją.

Nie zastępuje:

* `app.map_actions`,
* `app.affects`.

`interferes_with` opisuje przeszkody i blokady, a nie główną akcję aplikacji.

---

## file_size

Waga paczki aplikacji albo pliku widoczna dla gracza.

Użycie:

* Googleplex,
* File Manager,
* preview instalacji,
* przyszłe limity pojemności.

Nie zastępuje:

* `price`,
* `disk_usage`,
* `resource_type`.

`file_size` mówi, jak duży jest artefakt. Dla aplikacji może oznaczać rozmiar
pakietu w `/tools`; dla danych może oznaczać wagę pliku w `/data/*`.

---

## disk_usage

Miejsce zajmowane po instalacji albo zapisaniu w inventory.

Użycie:

* przyszłe `storage_used`,
* walidacja instalacji,
* ostrzeżenia o zapełnieniu dysku.

Nie zastępuje:

* `file_size`,
* `storage_capacity`,
* ceny aplikacji.

`disk_usage` może być większe niż `file_size`, bo zainstalowana aplikacja może
zajmować więcej miejsca niż sama paczka.

---

## quality_score

Liczbowa jakość narzędzia albo danych.

Użycie:

* kompletność plików,
* preview wartości w Ghost Exchange,
* przyszły wpływ poziomu twórcy na aplikację.

Nie zastępuje:

* `app.map_actions`,
* `reliability`,
* `risk_level`.

`quality_score` mówi, jak dobry jest wynik, ale nie decyduje, czy aplikacja
może obsłużyć akcję mapy.

---

## reliability

Przewidywana niezawodność aplikacji.

Użycie:

* ryzyko awarii,
* skuteczność operacji,
* przyszły balans narzędzi.

Nie zastępuje:

* `quality_score`,
* `risk_event`,
* `operation_type`.

`reliability` mówi, jak stabilnie narzędzie działa, a nie jak wartościowe dane
produkuje.

---

## creator_power

Syntetyczna moc twórcy aplikacji.

Użycie:

* przyszłe kreatory,
* jakość generowanej aplikacji,
* niezawodność,
* balans ceny i wymagań.

Nie zastępuje:

* `required_level`,
* `required_respect`,
* `creator_username`.

`creator_power` jest parametrem tworzenia narzędzia, a nie identyfikatorem
twórcy ani warunkiem zakupu.

---

## creator_wizard_step

Krok w istniejącym kreatorze aplikacji.

Użycie:

* AppForge,
* TermCreator,
* WindowMaker,
* ButtonMaker,
* przyszły Googleplex Tool Laboratory.

Nie zastępuje:

* `app.interface`,
* `app.map_actions`,
* `operation_type`,
* endpointu publikacji.

Sprint 25 przyjmuje następujące kroki:

| Krok | Znaczenie |
| --- | --- |
| `meta` | Nazwa, opis, ikona i cena aplikacji. |
| `tool_type` | Typ narzędzia i rozpoznawane cechy. |
| `environment` | Sposób uruchomienia UI i `target_types`. |
| `map_actions` | Jawne intencje mapy obsługiwane przez aplikację. |
| `operations` | Operacje, które aplikacja może utworzyć. |
| `resources` | Zasoby, które aplikacja może produkować. |
| `risk` | Pola ryzyka i wpływu na system celu. |
| `storage_quality_preview` | Podgląd wagi, jakości i niezawodności. |
| `publish` | Publikacja do Googleplex przez istniejący endpoint. |

`creator_wizard_step` opisuje UX prowadzenia gracza. Nie jest osobnym modelem
runtime i nie tworzy nowej ścieżki publikacji.

---

## Decyzje człowieka

* `phone` zostaje rozwijanym `target_type` na potrzeby kontraktu gameplayu. Implementacyjnie może być później powiązany z `person`, `player` albo urządzeniem, ale nie blokujemy go teraz.
* `server` i `router` mogą być realnymi celami w pierwszych sprintach na mockowych wersjach.
* `target_mode = vulnerability` ma własny tryb obsługi, ale `target_type` dziedziczy z obiektu źródłowego, jeśli jest znany.

## TODO_DECISION

* Doprecyzować, czy `phone` będzie widoczny jako osobny marker mapy, czy jako urządzenie przypięte do `person` / `player`.
* Dopisać docelowe realne `source_type` dla `router` i `server`, poza mockami.
## Guided creator UX

Sprint 30.5 dodaje do kreatorów warstwę prowadzenia gracza przez decyzje.

| Pojęcie | Znaczenie | Czego nie zastępuje |
| --- | --- | --- |
| `guided_step` | Krok kreatora pokazujący jedną decyzję naraz. | Nie jest nowym runtime ani nowym endpointem. |
| `subtitle` | Krótki kontekst kroku. | Nie zastępuje opisu aplikacji. |
| `educational_note` | Bezpieczne skojarzenie edukacyjne z klasą narzędzia. | Nie jest instrukcją techniczną. |
| `gameplay_hint` | Konsekwencja decyzji w świecie gry. | Nie zastępuje walidacji kontraktu. |

Decision:

* Przyjęto: guided UX tłumaczy istniejące pola kontraktu językiem gracza.
* Przyjęto: narracja nie podaje nazw realnych narzędzi ani instrukcji
  ofensywnych.
