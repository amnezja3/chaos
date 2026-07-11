# BlackNet Signal Generation Audit

Data: 2026-07-11

## Cel

Ten dokument opisuje, jak BlackNet buduje sygnaly w obecnym runtime CHAOS.

Audyt rozdziela dwa aktywne zrodla:

* lokalny fallback `static/blacknet_signals.json`,
* runtime publisher `GET /api/blacknet/world-signals`.

To rozroznienie jest krytyczne: sygnal moze wygladac jak informacja ze swiata,
ale na razie czesc sygnalow nadal jest statycznym fallbackiem.

## Glowna sciezka UI

BlackNet wczytuje sygnaly w `static/js/terminal.js`:

```text
loadBlacknetSignals()
↓
fetch /static/blacknet_signals.json
+
fetch /api/blacknet/world-signals
↓
world_generated idzie przed local fallback
↓
dedupe po signal.id
↓
renderBlackNet()
```

Jesli endpoint runtime nie dziala albo nie zwroci sygnalow, UI nadal pokazuje
lokalne sygnaly ze `static/blacknet_signals.json`.

## Przyklad: HOTSPOT / MOKOTOW

Sygnal ze screena:

```text
HOTSPOT / MOKOTOW
WZROST RUCHU
240%
17 AKTYWNYCH OPERACJI
04:32
PRZECHWYC TELEPORT
```

### Zrodlo

Ten konkretny sygnal obecnie pochodzi z lokalnego fallbacku:

```text
static/blacknet_signals.json
```

Id:

```text
hotspot-mokotow
```

Nie jest jeszcze liczony z `blacknet_world_facts`.

### Tytul: HOTSPOT / MOKOTOW

Pole:

```json
"title": "HOTSPOT / MOKOTOW"
```

Pochodzenie:

* wpisane statycznie w `static/blacknet_signals.json`,
* nie pochodzi jeszcze z mapy,
* nie pochodzi jeszcze z regionow miasta,
* nie pochodzi jeszcze z operations runtime.

### Kanal: PRZECHWYCONY KANAL

Pole:

```json
"channel": "PRZECHWYCONY KANAL"
```

Pochodzenie:

* wpisane statycznie,
* renderer pokazuje to jako mala ramke nad trescia sygnalu.

### Label: WZROST RUCHU

Pole:

```json
"label": "WZROST RUCHU"
```

Pochodzenie:

* wpisane statycznie,
* opisuje znaczenie glownej liczby,
* nie jest jeszcze liczone z liczby operacji, ruchu graczy ani mapy.

### Wartosc: 240%

Pole:

```json
"value": "240%"
```

Pochodzenie:

* wpisane statycznie,
* na teraz oznacza "plakatowa" wartosc sygnalu,
* nie jest jeszcze przeliczeniem realnego ruchu na Mokotowie.

Docelowo taki procent powinien powstawac np. z:

```text
aktywnosc regionu teraz
/
bazowa aktywnosc regionu
```

albo:

```text
liczba aktywnych operacji w regionie
/
srednia z poprzedniego okna czasu
```

Tego runtime jeszcze nie ma.

### Stat: 17 AKTYWNYCH OPERACJI

Pole:

```json
"stat": "17 AKTYWNYCH OPERACJI"
```

Pochodzenie:

* wpisane statycznie w fallbacku,
* nie jest obecnie liczone z `profile.operations`.

Runtime ma juz osobna rodzine faktow:

```text
operations_active_count
```

Ale ta rodzina liczy globalne aktywne operacje ze wszystkich profili, a nie
regionalny hotspot Mokotow.

### Timer: 04:32

Pole:

```json
"timer": "04:32"
```

Pochodzenie:

* wpisane statycznie,
* nie odlicza jeszcze do realnego `expires_at`.

Runtime publisher ma realny timer, ale tylko dla `world_generated`:

```text
blacknet_timer_text(fact, now)
↓
fact.expires_at - now
↓
HH:MM
```

Wszystkie fakty runtime maja obecnie domyslny TTL:

```text
BLACKNET_WORLD_FACTS_TTL_SECONDS = 10 * 60
```

czyli okno waznosci 10 minut.

### Teleport: PRZECHWYC TELEPORT

Pola:

```json
"cta": "PRZECHWYC TELEPORT",
"cta_action": "teleport_to_hotspot",
"cta_target": "hotspot",
"cta_target_id": "mokotow",
"metadata": {
  "hotspot_id": "mokotow",
  "label": "Mokotow",
  "risk": "high"
}
```

Pochodzenie:

* `cta_action` i `cta_target_id` sa w fallbacku,
* wspolrzedne nie sa w sygnale,
* wspolrzedne sa pobierane z whitelisty backendowej:

```text
BLACKNET_HOTSPOTS["mokotow"]
```

Aktualne wspolrzedne:

```text
lat: 52.1934
lng: 21.0348
```

Flow:

```text
klik CTA
↓
blacknetTeleportToHotspot(signal)
↓
modal decyzyjny Ghost System OK/ANULUJ
↓
POST /api/blacknet/cta/teleport
↓
walidacja hotspot_id w BLACKNET_HOTSPOTS
↓
update profile.curently_possition
↓
record_map_player_actor_delta(map.player_moved)
↓
otwarcie mapy
```

BlackNet nie trzyma wspolrzednych w sygnale. Sygnal niesie tylko `hotspot_id`.

### Radar

Pole:

```json
"radar": {
  "sides": 0,
  "nodes": [...]
}
```

Pochodzenie:

* dla fallbacku radar jest wpisany statycznie,
* renderer zamienia `nodes` na linie, punkty, satelity i sweep SVG.

Runtime publisher robi radar deterministycznie:

```text
blacknet_radar_from_seed(fact_id, layout)
↓
sha1(fact_id)
↓
6 punktow radaru
```

## Runtime families: jak powstaja inne sygnaly

### operations_active_count

Zrodlo danych:

```text
user_store.list_profiles()
↓
profile.operations
```

Builder faktu:

```text
build_blacknet_operations_facts()
```

Co liczy:

* aktywne operacje,
* zakonczone operacje,
* bledne/anulowane operacje,
* top typy operacji,
* top target labels,
* laczny output MB.

Signal rule:

```text
fact_type: operations_active_count
signal_type: operation_activity
channel: PRZECHWYCONY KANAL
title: HOTSPOT / OPERACJE
label: AKTYWNE OPERACJE
value: {value}x
stat: {value} OPERACJI W TOKU
cta: OTWORZ MAPE
```

Uwagi:

* to jest globalny licznik operacji,
* nie jest jeszcze regionem typu Mokotow,
* nie tworzy teleportu.

### operations_top_type

Zrodlo danych:

```text
profile.operations
```

Co liczy:

* najczestszy typ operacji.

Signal rule:

```text
title_template: AKTYWNOSC / {category}
label: NAJCZESTSZY TYP
value: {value}x
stat: {category}
cta: SPRAWDZ MAPE
```

Uwagi:

* `category` to typ operacji, np. `sniff`,
* nie jest jeszcze mapa regionu.

### market_sales_7d

Zrodlo danych:

```text
profile.market_history
collect_ghost_exchange_transactions(profile)
```

Okno czasu:

```text
ostatnie 7 dni
```

Co liczy:

* laczny HC ze sprzedazy,
* liczbe plikow,
* wolumen MB,
* liczbe transakcji,
* rozbicie na sektory.

Signal rule:

```text
title: RYNEK DANYCH / 7D
label: OBROT HC
value: +{total_hc} HC
stat: {file_count} PLIKOW / {volume_mb} MB
cta: OTWORZ GHOST EXCHANGE
```

Uwagi:

* to jest realny runtime z historii rynku,
* nie odpala settlementu,
* nie sprzedaje danych.

### market_top_sector_7d

Zrodlo danych:

```text
profile.market_history
```

Co liczy:

* sektor z najwyzszym HC w ostatnich 7 dniach,
* wolumen MB tego sektora.

Signal rule:

```text
title_template: {category} / POPYT
label: TOP SEKTOR
value: +{top_hc} HC
stat: {volume_mb} MB W RUCHU
cta: OTWORZ GHOST EXCHANGE
```

Uwagi:

* `category` jest sektorem rynku, np. `gps`, `camera`, `network`,
* CTA otwiera Ghost Exchange, ale nie filtruje jeszcze realnie pelnego dashboardu
  po sektorze w kazdym miejscu UI.

### googleplex_catalog_size

Zrodlo danych:

```text
get_app_catalog()
```

Co liczy:

* liczbe aplikacji,
* liczbe system products,
* srednia cene,
* kategorie,
* pierwszy/featured produkt jako `product_id`, `product_name`, `cta_query`.

Signal rule:

```text
title: GOOGLEPLEX / KATALOG
label: DOSTEPNE PRODUKTY
value: {len(catalog)}
stat: {products} SYSTEM PRODUCT
cta: SPRAWDZ W GOOGLEPLEX
```

CTA:

```text
open_googleplex
↓
frontend bierze cta_query / product_name
↓
wpisuje realna fraze w wyszukiwarke Googleplexa
```

Uwagi:

* po hotfixie nie szuka juz po plakatowym tytule sygnalu,
* szuka po realnej nazwie produktu z katalogu.

### radio_channels_available

Zrodlo danych:

```text
static/mp3/radio/channel/*/meta.channel
pliki .mp3 w katalogu kanalu
```

Co liczy:

* liczbe kanalow,
* laczna liczbe MP3,
* preferowany kanal BlackNet po `source` zaczynajacym sie od `blacknet`.

Signal rule:

```text
title: GHOST HACK RADIO
label: KANALY ONLINE
value: {channels_count}
stat: {tracks_total} TRACKOW W ETERZE
cta: WLACZ RADIO
```

CTA:

```text
open_radio
↓
GhostRadio.loadChannel(metadata.channel_id)
↓
GhostRadio.play()
```

Uwagi:

* po hotfixie `cta_target=radio` nie jest juz traktowane jako ID kanalu,
* kanal idzie przez `metadata.channel_id` albo `cta_target_id`.

### system_messages_24h

Zrodlo danych:

```text
profile.system_messages
```

Okno czasu:

```text
ostatnie 24h
```

Co liczy:

* liczbe komunikatow systemowych,
* top tytuly komunikatow.

Signal rule:

```text
title: SYSTEM / 24H
label: ZDARZENIA
value: {total_messages}
stat: {value} KOMUNIKATOW
cta: OTWORZ CYBERNER
```

Uwagi:

* nie pokazuje prywatnych body,
* agreguje tylko lekkie metadane.

## Jak powstaje runtime signal z fact

Pipeline:

```text
build_blacknet_world_facts_snapshot()
↓
facts[]
↓
blacknet_signal_from_fact()
```

Kroki:

1. Sprawdzenie `fact_type` w `BLACKNET_SIGNAL_RULES`.
2. Sprawdzenie threshold:

```text
value >= rule.threshold
```

3. Sprawdzenie waznosci:

```text
expires_at > now
```

4. Zbudowanie display fields:

```text
channel, title, label, value, stat, timer, tone, layout, cta
```

5. Zbudowanie CTA:

```text
cta_action z rule
cta_target z rule
cta_target_id z metadata albo subject_id
cta_query z metadata
```

6. Zbudowanie radaru:

```text
sha1(fact_id) -> nodes
```

7. Ranking i dedupe:

```text
importance desc
signal_type
fact_id
```

## Co jest jeszcze statyczne

Na dzisiaj statyczne sa:

* regionalne hotspoty typu `HOTSPOT / MOKOTOW`,
* wartosci procentowe typu `240%`,
* timery fallbacku,
* teksty typu `17 AKTYWNYCH OPERACJI` w fallbacku,
* fallbackowe radary.

## Co jest juz runtime

Runtime jest:

* globalny licznik aktywnych operacji,
* top typ operacji,
* 7-dniowa sprzedaz Ghost Exchange,
* top sektor rynku,
* liczba produktow Googleplex,
* dostepne kanaly radia i liczba MP3,
* liczba system messages z 24h,
* CTA target metadata dla Googleplexa/radia,
* whitelistowany teleport po `hotspot_id`.

## Luka modelu: regionalne hotspoty

Najwieksza luka miedzy ekranem a runtime jest taka:

```text
HOTSPOT / MOKOTOW
240%
17 aktywnych operacji
04:32
```

wyglada jak sygnal runtime, ale jest statycznym fallbackiem.

Zeby stal sie realnym sygnalem, potrzebny jest nowy read model regionow:

```text
region_id
region_name
lat/lng albo hotspot_id
active_operations_in_region
baseline_operations_in_region
traffic_change_percent
expires_at
risk
```

Wtedy `HOTSPOT / MOKOTOW` moglby powstawac jako fakt:

```text
fact_type: regional_hotspot_activity
category: hotspot
region_id: mokotow
subject_id: mokotow
value: traffic_change_percent
metadata:
  active_operations: 17
  hotspot_id: mokotow
```

## Rekomendacja

Nie usuwac fallbacku od razu.

Najpierw dopisac runtime rodzine:

```text
regional_hotspot_activity
```

Potem sprawic, zeby lokalny `hotspot-mokotow` byl tylko fallbackiem na brak
runtime facts.

Docelowy kontrakt:

```text
source=world_generated
signal_type=regional_hotspot
cta_action=teleport_to_hotspot
cta_target_id=mokotow
metadata.hotspot_id=mokotow
```

Wtedy ekran BlackNetu przestanie udawac runtime i zacznie naprawde opisywac
aktywny stan miasta.
