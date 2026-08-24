# CHAOS — Data Economy + Data Lifecycle

Sprint 0.7 definiuje ekonomię danych i cykl życia pliku/zasobu.

Dane są głównym towarem w CHAOS. Rynek nie jest tylko sklepem, ale gospodarką informacji: miejscem, w którym logi, dumpy, nagrania, dane finansowe i paczki wywiadowcze dostają wartość.

Pełny cykl życia informacji:

```text
Operation
↓
Resource
↓
File
↓
Market Listing
↓
Sale
↓
Mail Notification
↓
HackCoin Transfer
↓
Archive / Delete
```

---

## Zasady główne

### Nie każdy plik jest sprzedawalny

Pliki narzędzi, projekty, statusy systemowe i stany techniczne nie są domyślnie towarem.

Przykłady niesprzedawalne:

* `/tools/*`,
* `/projects/*`,
* `internal_recon_state`,
* systemowe statusy procesu.

### Nie każdy zasób trafia na rynek

`resource_type` może istnieć tylko jako stan, plik roboczy albo element większej paczki.

Przykład:

* `internal_recon_state` wspiera hackowanie, ale nie trafia na rynek.
* `location_history` może być samodzielnym towarem albo częścią paczki Device Intelligence.

### Wartość danych jest wieloczynnikowa

Cena danych zależy od:

* typu danych,
* świeżości,
* kompletności,
* jakości,
* wolumenu,
* ryzyka operacji,
* typu celu,
* gęstości lokacji,
* rzadkości,
* popytu kupujących.

### Systemowy rynek może kupować dane

Na start rynek może działać przez automatyczny skup systemowy.

To pozwala zamknąć pętlę gameplayu bez wymagania realnego player-to-player tradingu.

### Handel między graczami jest przyszłą warstwą

Gracze w przyszłości mogą handlować między sobą, ale nie jest to wymagane w pierwszej wersji Data Economy.

Decision:

* Przyjęto: Sprint 0.7 projektuje najpierw automatyczny skup systemowy, a handel player-to-player zostaje jako `TODO_FUTURE`.

---

## Ghost Exchange

Głównym rynkiem danych jest:

```text
Ghost Exchange
```

Ghost Exchange może być zakładką w Browserze obok Googleplexa.

Googleplex sprzedaje aplikacje.

Ghost Exchange skupuje i wystawia dane.

Decision:

* Przyjęto: nazwa rynku danych to `Ghost Exchange`.
* Przyjęto: `Ghost Express` brzmi bardziej jak logistyka lub szybka usługa, a `Ghost Market` jest zbyt generyczne.
* Przyjęto: Ghost Exchange jest domyślnym rynkiem danych na start. Rynki frakcyjne mogą powstać później jako rozszerzenie.

---

## Market categories

### location

Obejmuje:

* `gps_logs`
* `location_history`

Kupujący:

* brokerzy miejskich danych,
* agenci terenowi,
* systemy predykcyjne,
* frakcje śledzące aktywność w obszarze.

Na wartość wpływa:

* liczba checkpointów,
* dokładność,
* świeżość,
* target_type,
* gęstość lokacji.

Nadaje się do automatycznego skupu: tak.

### financial

Obejmuje:

* `financial_records`
* `atm_dump`

Kupujący:

* brokerzy finansowi,
* czarne rynki scoringu,
* boty arbitrażowe,
* frakcje ekonomiczne.

Na wartość wpływa:

* liczba rekordów,
* zakres czasu,
* pewność konta,
* ryzyko,
* rzadkość źródła.

Nadaje się do automatycznego skupu: tak, ale z wyższym ryzykiem i lepszą kontrolą balansu.

### credentials

Obejmuje:

* `credentials`
* `email_accounts`

Kupujący:

* brokerzy dostępu,
* operatorzy botnetów,
* frakcje infiltracyjne,
* systemy automatycznego access resale.

Na wartość wpływa:

* liczba credentiali,
* ważność,
* zakres dostępu,
* świeżość,
* target_type.

Nadaje się do automatycznego skupu: tak, ale wymaga limitów i mocnej kontroli ekonomii.

### surveillance

Obejmuje:

* `camera_dump`
* `video_material`

Kupujący:

* agencje wywiadu,
* brokerzy materiałów dowodowych,
* frakcje obserwacyjne,
* systemy analizy obrazu.

Na wartość wpływa:

* długość materiału,
* jakość,
* event hits,
* rzadkość kamery,
* gęstość lokacji.

Nadaje się do automatycznego skupu: tak.

### personal

Obejmuje:

* `personal_records`
* `call_history`
* `messenger_data`
* część `email_accounts` jako metadane profilu

Kupujący:

* brokerzy profili,
* frakcje społeczne,
* systemy scoringu zachowań,
* czarne rynki identyfikacji.

Na wartość wpływa:

* głębokość profilu,
* kompletność,
* świeżość,
* target_type,
* powiązania społeczne.

Nadaje się do automatycznego skupu: tak.

### audio

Obejmuje:

* `audio_transcript`

Kupujący:

* brokerzy transkrypcji,
* agencje analizy rozmów,
* frakcje szukające haseł i sygnałów,
* systemy keyword intelligence.

Na wartość wpływa:

* długość,
* liczba rozmówców,
* jakość transkrypcji,
* keyword hits,
* świeżość.

Nadaje się do automatycznego skupu: tak.

### device_intelligence

Obejmuje:

* `device_logs`
* `location_history`
* `call_history`
* `messenger_data`
* `personal_records`

Kupujący:

* brokerzy urządzeń,
* frakcje techniczne,
* systemy mapujące aktywność,
* operatorzy exploitów.

Na wartość wpływa:

* liczba eventów,
* zakres czasu,
* kompletność paczki,
* jakość identyfikacji urządzenia,
* korelacja z lokacją.

Nadaje się do automatycznego skupu: tak.

### vehicle

Obejmuje:

* `vehicle_diagnostics`

Kupujący:

* brokerzy części,
* warsztaty niejawne,
* operatorzy flot,
* frakcje logistyczne.

Na wartość wpływa:

* liczba systemów,
* głębokość ECU,
* telemetria,
* rzadkość pojazdu,
* stan awarii.

Nadaje się do automatycznego skupu: tak.

### network

Obejmuje:

* `wifi_networks`
* `hotspot_database`

Kupujący:

* mapy hotspotów,
* brokerzy infrastruktury,
* frakcje sieciowe,
* systemy rozpoznania obszaru.

Na wartość wpływa:

* liczba sieci,
* typy zabezpieczeń,
* świeżość,
* pokrycie obszaru,
* gęstość lokacji.

Nadaje się do automatycznego skupu: tak.

---

## Wycena danych

Wycena danych jest kontraktem, nie finalną implementacją liczbową.

Roboczy model:

```text
price =
  base_value
  * freshness_multiplier
  * completeness_multiplier
  * quality_multiplier
  * demand_multiplier
```

### Czynniki wyceny

| Czynnik | Znaczenie |
| --- | --- |
| `base_value` | Wartość startowa zależna od `market_category` i `resource_type`. |
| `freshness` | Jak świeże są dane. Starsze dane tracą wartość. |
| `completeness` | Jak pełna jest paczka względem `completeness_fields`. |
| `quality` | Jakość materiału, pewność identyfikacji, dokładność, czytelność. |
| `volume` | Liczba rekordów, długość materiału, liczba checkpointów. |
| `risk_level` | Ryzykowniejsze operacje mogą produkować cenniejsze dane. |
| `target_type` | Dane z gracza, pojazdu, ATM albo kamery mogą mieć różne mnożniki. |
| `location_density` | Dane z gęstych obszarów miejskich mogą mieć większą wartość. |
| `rarity` | Rzadkie źródła lub nietypowe targety mogą podnosić cenę. |
| `buyer_demand` | Dynamiczny popyt rynku/frakcji/systemu. |

Decision:

* Przyjęto: pierwsza wersja rynku może liczyć cenę deterministycznie z metadanych pliku, bez aukcji i bez negocjacji.
* Przyjęto: `buyer_demand` może być na start statycznym mnożnikiem kategorii, a dopiero później dynamicznym systemem.

### Jakość narzędzia jako źródło jakości danych

Od Sprintu 23 `quality` pliku może pochodzić z dwóch źródeł:

* jakości samego materiału/danych,
* `quality_score` aplikacji, która uruchomiła operację.

Flow:

```text
app.quality_score
↓
operation.source_app_quality
↓
file.quality_score
↓
Ghost Exchange quality_multiplier
```

Zasady:

* lepsza aplikacja może podnieść `file.quality_score`,
* `reliability` jest przygotowana pod przyszłe awarie i ryzyko,
* Sprint 23 nie zmienia jeszcze finalnego pricingu poza użyciem istniejącego
  `quality_multiplier`,
* jakość nie zastępuje kompletności; dobry tool może zebrać mało danych, ale w
  lepszej jakości.

Decision:

* Przyjęto: Ghost Exchange nadal korzysta z `file.quality_score`, a aplikacje
  wpływają na ten parametr przez operację i finalizację pliku.

### Tool Balance Pass po Sprincie 29

Sprint 29 porządkuje relację między ceną aplikacji a jej kontraktem. To pierwszy
balance pass, nie finalna ekonomia narzędzi.

Nowe pola aplikacji:

* `power_score` - miękki wskaźnik siły narzędzia,
* `price_hint` - sugerowana cena narzędzia,
* `balance_tier` - Basic / Advanced / Pro,
* `recommended_level` i `recommended_respect` - miękkie rekomendacje progresji.

Heurystyka:

```text
contract scope
↓
file_size / disk_usage
↓
quality_score / reliability
↓
risk / pro-system status
↓
power_score
↓
price_hint
```

Zasady:

* lepsze i szersze narzędzie ma wyższy `power_score`,
* cięższe narzędzie ma wyższy `price_hint`,
* `pro-system-tool` dostaje wyższą wagę i wyższą sugerowaną cenę,
* aplikacje generowane przez kreatory nie publikują się poniżej własnego
  `price_hint`,
* seed/legacy aplikacje zachowują ręczne ceny, ale pokazują `price_hint` w UI.

Decision:

* Przyjęto: Sprint 29 nie wprowadza dynamicznego popytu, frakcji kupujących ani
  nowego modelu sklepu.
* Przyjęto: cena narzędzia jest na razie miękko wyjaśniana przez `price_hint`,
  a nie przeliczana globalnie dla całego katalogu.

### Uninstall a ekonomia po Sprincie 30

Odinstalowanie aplikacji:

* nie jest sprzedażą,
* nie zwraca automatycznie HC,
* nie usuwa aplikacji z Googleplex,
* nie zmienia historii rynku danych,
* zwalnia tylko miejsce w miękkim modelu storage gracza.

Decision:

* Przyjęto: refundy, odsprzedaż aplikacji i wtórny rynek narzędzi nie są częścią
  Googleplex Tool Laboratory v1.

---

## Data lifecycle

Statusy danych/pliku:

* `generated`
* `stored`
* `listed`
* `sold`
* `archived`
* `deleted`
* `expired`

### generated

Dane powstały z operacji, ale nie muszą jeszcze być zapisane jako plik.

Ustawia:

* operation system,
* aplikacja,
* scheduler operacji.

### stored

Dane są zapisane jako plik w systemie plików gracza.

Ustawia:

* file system / inventory.

### listed

Plik jest wystawiony na Ghost Exchange albo przygotowany do sprzedaży.

Ustawia:

* gracz,
* automatyczny flow sprzedaży, jeśli istnieje.

### sold

Plik został sprzedany.

Ustawia:

* market system.

### archived

Pozostaje kopia historyczna bez wartości handlowej.

Ustawia:

* market system,
* archive system.

### deleted

Plik został usunięty.

Ustawia:

* gracz,
* market system po sprzedaży,
* cleanup system.

### expired

Dane straciły ważność.

Ustawia:

* scheduler,
* market system,
* file lifecycle.

Decision:

* Przyjęto: domyślnie po sprzedaży plik handlowy przechodzi do `sold`, znika z `/data`, a wpis transakcji zostaje w `/market/history` albo `/market/sold`.
* Przyjęto: `archived` jest przyszłą funkcją historii gracza, nie wymogiem pierwszej wersji rynku.

---

## Sale flow

```text
File
↓
Listing
↓
Buyer simulation
↓
Sale
↓
HackCoin transfer
↓
Mail
↓
File archived/deleted
```

### Sprzedaż ręczna

Gracz wybiera plik sprzedawalny.

System:

1. sprawdza `can_sell`,
2. wylicza cenę,
3. tworzy listing,
4. symuluje kupującego,
5. wykonuje sprzedaż,
6. przelewa HC,
7. wysyła mail,
8. usuwa plik z `/data` albo oznacza jako `sold`.

### Automatyczny skup systemowy

System może kupić dane bez udziału realnych graczy.

To zamyka pętlę:

```text
operacja → plik → sprzedaż → HC
```

### Player-to-player trading

`TODO_FUTURE`.

Handel między graczami będzie osobną warstwą, bo wymaga:

* ofert,
* escrow albo natychmiastowych przelewów,
* widoczności ofert,
* nadużyć,
* relacji z Walletem.

---

## Mail notification

Każda sprzedaż generuje wiadomość e-mail.

Mail powinien zawierać:

* nazwę sprzedanej paczki,
* kategorię rynku,
* cenę,
* kupującego albo typ kupującego,
* timestamp,
* status pliku po sprzedaży.

Przykład:

```text
Tytuł: Sprzedaż danych zakończona
Treść:
Pakiet: gps_taxi_2037-06-26.log
Kategoria: location
Kupujący: Systemowy broker tras
Cena: 180 HC
Status pliku: sold / removed from data inventory
```

Decision:

* Przyjęto: sprzedaż danych wysyła mail systemowy do gracza zawsze, nawet jeśli kwota jest niska.
* Przyjęto: mail sprzedażowy nie ujawnia pełnej logiki wyceny, tylko wynik i najważniejsze metadane.

---

## Archive / Delete

Decision:

* Przyjęto: po sprzedaży plik danych znika z `/data`.
* Przyjęto: wpis transakcji zostaje w `/market/history` albo `/market/sold`.
* Przyjęto: archived copy może być funkcją przyszłą, ale nie jest domyślnym zachowaniem.
* Przyjęto: jeśli plik nie jest sprzedawalny, usunięcie go przez gracza jest zwykłym delete bez HC.

---

## Tabela market_categories

| market_category | resource_types | buyer_types | value_factors | auto_buy_enabled | player_trade_future | notes |
| --- | --- | --- | --- | --- | --- | --- |
| `location` | `gps_logs`, `location_history` | route brokers, field agents, prediction systems | freshness, checkpoint_count, accuracy, location_density | yes | yes | Dobry bazowy rynek na start. |
| `financial` | `financial_records`, `atm_dump` | finance brokers, arbitrage bots, economic factions | record_count, time_span, account_confidence, risk_level | yes | yes | Wymaga ostrożnego balansu HC. |
| `credentials` | `credentials`, `email_accounts` | access brokers, botnet operators, infiltration factions | validity, scope, freshness, credential_count | yes | yes | Wysoka wartość, wysokie ryzyko. |
| `surveillance` | `camera_dump`, `video_material` | evidence brokers, image analysis systems, watcher factions | duration, quality, event_hits, rarity | yes | yes | Obejmuje kamery i wideo. |
| `personal` | `personal_records`, `call_history`, `messenger_data`, `email_accounts` | profile brokers, social factions, scoring systems | profile_depth, freshness, relation_density, completeness | yes | yes | Dane społeczne i profilowe. |
| `audio` | `audio_transcript` | transcript brokers, keyword intelligence systems | duration, transcript_quality, speaker_count, keyword_hits | yes | yes | Może być łączone z surveillance. |
| `device_intelligence` | `device_logs`, `location_history`, `call_history`, `messenger_data` | device brokers, exploit operators, tech factions | events_count, signal_quality, time_span, correlation | yes | yes | Paczki urządzeń mają rosnącą wartość z kompletnością. |
| `vehicle` | `vehicle_diagnostics` | workshops, fleet operators, logistics factions | ecu_access, telemetry_quality, vehicle_rarity | yes | yes | Dobre dla mechaniki pojazdów. |
| `network` | `wifi_networks`, `hotspot_database` | infrastructure brokers, network factions, recon systems | network_count, coverage_area, security_types, freshness | yes | yes | `hotspot_database` cenniejsze niż pojedynczy skan. |

---

## Tabela data_lifecycle_statuses

| status | meaning | visible_in_files | sellable | deletable | creates_mail | creates_hc_transfer | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `generated` | Zasób powstał z operacji. | no/optional | no | no | no | no | Może jeszcze być w buforze operacji. |
| `stored` | Zasób zapisany jako plik. | yes | yes, if file allows | yes | no | no | Podstawowy status inventory. |
| `listed` | Plik wystawiony na rynku. | yes | pending | yes/cancel listing | no | no | Listing może być anulowany przed sprzedażą. |
| `sold` | Plik sprzedany. | no in `/data`; yes in `/market/history` | no | no | yes | yes | Domyślnie znika z danych. |
| `archived` | Kopia historyczna bez wartości handlowej. | optional | no | yes | optional | no | Funkcja przyszła. |
| `deleted` | Plik usunięty. | no | no | no | no | no | Zwykły cleanup. |
| `expired` | Dane przeterminowane. | yes/optional | no or reduced | yes | optional | no | Rynek może odrzucić przeterminowane dane. |

---

## Tabela sale_flow

| step | input | system_action | player_feedback | output | notes |
| --- | --- | --- | --- | --- | --- |
| `select_file` | file in `/data/*` | check file metadata | file highlighted / sell action visible | candidate file | Tylko pliki z `can_sell = true`. |
| `create_listing` | candidate file | create market listing | listing created message | `listed` file/listing | Może być natychmiastowe przy auto-buy. |
| `buyer_simulation` | listing | choose buyer type and demand multiplier | pending / sold feedback | buyer result | Na start systemowy kupujący. |
| `price_calculation` | listing + file metadata | compute price | price preview or sale summary | final HC value | Bez finalnych liczb w Sprincie 0.7. |
| `sale` | listing + buyer | mark as sold | sale success message | sold record | Transakcja zamyka listing. |
| `hc_transfer` | sold record | add HC to player | HC balance updated | wallet/profile balance | To nie jest zwykły player transfer. |
| `mail_notification` | sold record | send system mail | mail in inbox | notification | Zawiera kategorię, cenę, buyer type, timestamp. |
| `archive_or_delete` | sold file | remove from `/data`, write history | file removed / history visible | `/market/history` record | Archived copy przyszłościowo. |

---

## Spójność z istniejącymi dokumentami

Sprawdzone względem:

* `doc/gameplay/resource_types.md`
* `doc/gameplay/file_model.md`
* `doc/gameplay/operations.md`
* `doc/gameplay/gameplay_matrix.md`

### Ustalenia spójności

* `file_model.md` mówi, gdzie dane trafiają jako pliki.
* Ten dokument mówi, jak pliki dostają wartość i jak są sprzedawane.
* `resource_types.md` mówi, które zasoby są sprzedawalne.
* `operations.md` mówi, które operacje produkują zasoby.
* `gameplay_matrix.md` zawiera starszą prostą tabelę, ale nowsze kontrakty `resource_types.md`, `file_model.md` i `data_economy.md` są źródłem prawdy dla rynku.

---

## Decision

* Przyjęto: `Ghost Exchange` jest nazwą głównego rynku danych.
* Przyjęto: Ghost Exchange jest na start rynkiem systemowym z automatycznym skupem.
* Przyjęto: player-to-player trading zostaje jako `TODO_FUTURE`, nie jako wymaganie pierwszej wersji.
* Przyjęto: po sprzedaży plik handlowy znika z `/data`, a wpis zostaje w `/market/history` albo `/market/sold`.
* Przyjęto: archived copy nie jest domyślne, tylko przyszła funkcja.
* Przyjęto: każda sprzedaż generuje mail systemowy.
* Przyjęto: wycena startowa jest deterministyczna, a dynamiczny popyt może wejść później jako rozszerzenie.
* Przyjęto: `email_accounts` może należeć do `credentials` i `personal`, ale primary market category to `credentials`, a personal use jest kontekstowe.

---

## Sprint 35 — Ghost Exchange market foundation

Sprint 35 nie uruchamia jeszcze automatycznej sprzedaży, batchy ani dashboardu.
Domyka fundament ekonomii danych dla Fazy D.

Zasady:

* `sellable` pozostaje eligibility do Ghost Exchange.
* `price_preview` pozostaje bazą przyszłej wyceny.
* `market_sector` jest warstwą read modelu nad `file_category` i
  `resource_types`.
* `market_volume_mb` jest wolumenem danych liczonym z `file_size`.
* `market_status` jest normalizowany do nowego modelu, ale stare preview/sell
  flow pozostaje kompatybilne jako legacy/dev.

Minimalne sektory Fazy D:

| file_category | market_sector |
| --- | --- |
| `camera` | `camera` |
| `atm` | `atm` |
| `gps` | `gps` |
| `device` | `device` |
| `personal` | `personal` |
| `credentials` | `credentials` |
| `financial` | `financial` |
| `network` | `network` |
| `audio` | `audio` |
| `vehicle` | `vehicle` |

Sprint 35 wprowadza wyłącznie read model i helpery. Auto sale, `listed_at`,
batch settlement i dashboard należą do kolejnych sprintów Fazy D.

---

## Sprint 36 — Market Queue read model

Sprint 36 uruchamia pierwszy stan automatycznego rynku: sprzedawalny plik staje
się elementem kolejki przez `market_status: queued_for_market`.

Nie ma jeszcze:

* batch settlement,
* automatycznego transferu HC,
* zmian w `market_history`,
* usuwania plików z `/data`,
* dashboardu v1.

Ghost Exchange dostaje sektorowy read model:

| field | meaning |
| --- | --- |
| `sector` | Sektor rynku danych. |
| `pending_files` | Liczba plików w kolejce sektora. |
| `pending_mb` | Łączny wolumen plików w kolejce. |
| `threshold_mb` | Docelowy próg wolumenu dla przyszłej paczki. |
| `missing_mb` | Ile MB brakuje do progu. |
| `missing_records` | Ile rekordów brakuje do progu, jeśli sektor tego wymaga. |
| `progress_percent` | Prosty read model postępu do przyszłej paczki. |
| `estimated_sale_time` | Placeholder informacyjny; nie jest jeszcze licznikiem settlementu. |

Decision:

* Przyjęto: queue jest stanem pliku w `profile.files`, nie osobnym systemem.
* Przyjęto: `queued_at` nie resetuje się przy kolejnym refreshu.
* Przyjęto: storage nadal liczy pliki w kolejce.

---

## Sprint 37 — Auto-sale settlement

Sprint 37 uruchamia kontrolowany settlement rynku danych bez realtime loopa.
Rynek nie sprzedaje pojedynczych plikow z klikniecia jako glownej sciezki.
Pliki w kolejce sa agregowane w paczki sektorowe.

Zasady wyceny:

* cena paczki bazuje na istniejacym `price_preview`,
* do wyceny wchodza jakosc, kompletnosc, rozmiar i liczba plikow/rekordow,
* paczka ma stabilny `batch_id`,
* settlement sprawdza `profile.market_history` i `files.market`, zanim naliczy
  HC.

Zasady czasu:

* prog sektora musi byc osiagniety przed listingiem,
* po osiagnieciu progu paczka dostaje `listed_at`,
* sprzedaz nastepuje dopiero po minimalnym czasie przebywania paczki na rynku,
* `estimated_sale_time` pozostaje read-modelem dla Ghost Exchange.

Efekty settlementu:

* HC gracza rosna o wartosc paczki,
* powstaje wpis w `profile.market_history`,
* powstaje rekord sprzedazy w `files.market`,
* gracz dostaje mail/system message od Ghost Exchange,
* pliki danych sa usuwane z katalogow `/data/*`,
* `storage_used` jest przeliczane.

Decision:

* Przyjeto: auto-sale jest kontrolowanym refreshem wywolywanym przez istniejace
  sciezki, nie schedulerem i nie workerem.
* Przyjeto: manual sell zostaje kompatybilnoscia legacy/dev, ale nie jest
  glownym modelem ekonomii Fazy D.

---

## Sprint 39 - storage economy i market balance

Sprint 39 domyka zaleznosc pomiedzy operacjami, storage, Ghost Exchange i
Googleplexem.

Zasady ekonomiczne:

* pliki danych zajmuja miejsce do momentu sprzedazy paczki,
* pelny dysk blokuje zapis nowych danych, ale nie cofa samej operacji,
* dane niezapisane nie trafiaja do Ghost Exchange i nie moga zarobic HC,
* auto-sale zwalnia storage dopiero po sprzedazy paczki,
* maly dysk ogranicza tempo zbierania paczek,
* wiekszy dysk pozwala dluzej akumulowac dane i stabilniej domykac progi rynku.

Storage Upgrade jest produktem Googleplexa:

* zakup kosztuje HC,
* zwieksza `storage_capacity`,
* nie tworzy aplikacji i nie trafia do `/tools`,
* korzysta z tego samego flow zakupu co Googleplex.

Decision:

* Faza D nie tworzy osobnej ekonomii storage. Storage jest czescia tej samej
  petli HC -> Googleplex -> operacje -> dane -> Ghost Exchange -> HC.

---

## Sprint 39.1 - Googleplex Product Effects Runtime v1

Googleplex obsluguje produkty systemowe zmieniajace parametry profilu przez ten
sam zakup HC co aplikacje.

Zasady:

* nie powstaje drugi sklep,
* nie powstaje osobny inventory itemow,
* `/install-app` pozostaje wspolnym endpointem zakupu,
* produkty nieaplikacyjne nie trafiaja do `profile.apps` ani `files.tools`,
* efekty produktu wykonuje `apply_googleplex_product_effect(profile, product)`.

Efekty v1:

* `storage_capacity_bonus`,
* `travel_city`,
* `map_zoom_bonus`,
* `scan_range_bonus`,
* `bike_range_bonus`.

Travel Ticket posiada tylko `travel_city`. Wspolrzedne pochodza z centralnego
katalogu `TRAVEL_CITIES`, a nie z rekordu produktu.

Decision:

* Storage Upgrade ze Sprintu 39 zostal przeniesiony pod wspolny runtime efektow
  produktow Googleplexa.

---

## TODO_DECISION

* Rekomendacja: przed implementacją ekonomii ustalić docelowe zakresy `base_value` i mnożników, bo to wpływa na balans HC i tempo progresu.
* Rekomendacja: przed backendem rynku zdecydować, czy listingi i historia sprzedaży są osobnymi tabelami, czy częścią profilu użytkownika. To jest decyzja architektury backendu.
* Rekomendacja: później zdecydować, czy istnieją rynki frakcyjne z innymi popytami i mnożnikami. To wpływa na gameplay loop i ekonomię.

---

## Definition of Done Sprintu 0.7

Sprint 0.7 jest zakończony, gdy:

* istnieje `data_economy.md`,
* wiadomo, czym jest Ghost Exchange,
* wiadomo, jakie są `market_categories`,
* wiadomo, jak czynniki wpływają na wycenę,
* wiadomo, jakie statusy ma cykl życia danych,
* wiadomo, jak wygląda sale flow,
* wiadomo, że sprzedaż generuje mail i transfer HC,
* wiadomo, co dzieje się z plikiem po sprzedaży,
* ekonomiczne i backendowe decyzje blokujące są wpisane jako `TODO_DECISION`.
