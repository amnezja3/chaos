# CHAOS — Risk Model / Risk Events Contract

Sprint 0.8 definiuje kontrakt systemu ryzyka.

Ryzyko jest wspólną warstwą dla akcji mapy, operacji, aplikacji, aktywnych obiektów, ekonomii danych i konsekwencji świata gry.

Risk pipeline:

```text
Action
↓
Risk signal
↓
Risk score
↓
Risk event
↓
Consequence
```

---

## Zasady główne

### Ryzyko nie jest losowaniem co sekundę

System nie powinien losować wykrycia w każdej klatce ani przy każdym UI refreshu.

Ryzyko jest liczone:

* po zakończeniu operacji,
* podczas aktywnej operacji w kontrolowanych tickach gameplayowych,
* po wykonaniu akcji natychmiastowej,
* przy porzuceniu operacji,
* przy przekroczeniu progu agresywności.

Decision:

* Przyjęto: nie ma losowania co sekundę.
* Przyjęto: aktywne operacje mogą mieć kontrolowane punkty oceny ryzyka, ale nie wolny realtime loop.

### Risk signal nie jest jeszcze karą

`risk_signal` oznacza, że akcja wygenerowała ślad.

Ślad może:

* zwiększyć `risk_score`,
* zostać zignorowany przez zabezpieczenia celu,
* zostać zredukowany przez aplikację lub support operation,
* dopiero później wywołać `risk_event`.

### Risk event jest wynikiem oceny

`risk_event` to nazwane zdarzenie ryzyka.

Przykład:

* gracz skanuje porty agresywnie,
* akcje generują sygnały,
* `risk_score` przekracza próg,
* powstaje `aggressive_scanning`,
* konsekwencją może być `warning` albo `cooldown`.

### Consequence jest skutkiem gameplayowym

Konsekwencja wpływa na gracza, operację, cel albo świat.

Przykłady:

* ostrzeżenie,
* częściowe wykrycie,
* cooldown,
* utrata HC,
* konfiskata operacji,
* jail.

---

## Źródła wykrycia

### camera_detected

Wykrycie przez kamerę albo system obserwacji.

Typowe źródła:

* `camera_stream`,
* `camera_shutdown`,
* operacje w zasięgu aktywnej kamery,
* ruch gracza na cudzym terytorium.

### failed_exploit

Nieudany exploit zostawia ślad.

Typowe źródła:

* `exploit`,
* player target hacking,
* conflict pillar hacking,
* aplikacje wysokiego ryzyka.

### atm_alarm

Alarm finansowy lub terminalowy.

Typowe źródła:

* `atm_log_extraction`,
* `persistent_sniffer` na ATM,
* financial operations.

### suspicious_network_activity

Podejrzana aktywność sieciowa.

Typowe źródła:

* `scan_ports`,
* `sniff`,
* `wifi_scanner`,
* `persistent_sniffer`,
* `audio_interference`, jeśli używa sieci.

### long_operation_detected

Wykrycie przez zbyt długi czas działania.

Typowe źródła:

* `vehicle_tracking`,
* `device_tracking`,
* `camera_stream`,
* `persistent_sniffer`,
* `generic_trace`.

### aggressive_scanning

Wykrycie agresywnego rozpoznania.

Typowe źródła:

* wielokrotne `scan_ports`,
* duży zasięg,
* krótki odstęp między skanami,
* wiele targetów w krótkim czasie.

### player_counter_intelligence

Wykrycie przez aktywne zabezpieczenia innego gracza.

Typowe źródła:

* player target hacking,
* territory conflict,
* atak na conflict pillar,
* aktywne ustawienia profilu ofiary.

### abandoned_operation

Ryzyko po porzuceniu aktywnej operacji.

Typowe źródła:

* sniffer zostawiony na obiekcie,
* przerwany tracking,
* niezakończony stream,
* operacja bez cleanupu.

### trace_back

Ślad zwrotny prowadzący do gracza.

Typowe źródła:

* nieudane operacje wysokiego ryzyka,
* brak VPN/anonymizera,
* długie operacje,
* kontrwywiad gracza lub celu.

---

## Czynniki zmniejszające ryzyko

### camera_shutdown

Operacja wspierająca zmniejszająca ryzyko wykrycia przez kamery.

Wpływa głównie na:

* `camera_detected`,
* `camera_stream`,
* operacje w obszarze kamery.

### vpn

Zmniejsza ryzyko śladu zwrotnego i części aktywności sieciowej.

Wpływa głównie na:

* `trace_back`,
* `suspicious_network_activity`,
* player target operations.

### spoofing

Zmniejsza ryzyko identyfikacji źródła albo celu.

Wpływa głównie na:

* `trace_back`,
* `failed_exploit`,
* `suspicious_network_activity`.

### anonymizer

Zmniejsza identyfikowalność gracza.

Wpływa głównie na:

* `trace_back`,
* `player_counter_intelligence`,
* `long_operation_detected`.

### stealth_app

Aplikacja o niskim profilu sygnału.

Wpływa na:

* bazowy `risk_score`,
* poziom hałasu operacji,
* szansę `partial_detection`.

### low_noise_operation

Tryb operacji o niższym hałasie.

Zwykle:

* trwa dłużej,
* produkuje mniej danych,
* ma niższe ryzyko wykrycia.

### quality_app

Jakość aplikacji zmniejsza ryzyko i zwiększa kompletność wyników.

Wpływa na:

* `risk_score`,
* jakość zasobów,
* stabilność operacji.

### operation_level

Poziom operacji/aplikacji.

Wyższy poziom może:

* zmniejszać ryzyko,
* zwiększać próg wykrycia,
* skracać czas ekspozycji.

---

## Konsekwencje

### warning

Lekki sygnał ostrzegawczy.

Przykłady:

* toast,
* system message,
* mail ostrzegawczy.

### partial_detection

Cel lub świat wykrył część aktywności, ale nie pełną tożsamość gracza.

Efekty:

* wzrost ryzyka kolejnych operacji,
* krótkotrwały status podejrzenia,
* możliwe ostrzeżenie ofiary.

### full_detection

Gracz lub jego operacja została jednoznacznie wykryta.

Efekty:

* alarm,
* ujawnienie pozycji,
* konsekwencje reputacyjne,
* możliwość kontrataku.

### wanted_level

Poziom poszukiwania przez system/teren/frakcję.

Efekty:

* większe ryzyko kolejnych operacji,
* utrudnione podróżowanie,
* silniejsze zabezpieczenia.

### cooldown

Blokada czasowa operacji, aplikacji albo typu celu.

Efekty:

* gracz musi poczekać,
* aplikacja jest chwilowo zbyt gorąca,
* cel chwilowo wzmacnia obronę.

### HC loss

Utrata HackCoinów.

Efekty:

* kara finansowa,
* opłata za cleanup,
* automatyczna strata przy trace back.

### confiscated_operation

Operacja lub jej wynik zostaje skonfiskowany.

Efekty:

* brak pliku,
* utrata aktywnego sniffera,
* utrata resource_buffer.

### jail

Twarda kara ograniczająca aktywność.

Efekty:

* blokada części akcji,
* timeout gracza,
* wymaga ostrożnego użycia w gameplay loop.

### reputation_loss

Spadek reputacji lub respectu.

Efekty:

* gorsze ceny,
* gorszy dostęp,
* konsekwencje frakcyjne.

---

## Risk levels

| risk_level | Znaczenie | Typowe użycie |
| --- | --- | --- |
| `none` | Brak realnego ryzyka. | Czysty podgląd, lokalny stan, operacje bez ekspozycji. |
| `low` | Niski ślad. | Proste trace, krótki stream, mały skan. |
| `medium` | Umiarkowane ryzyko. | Sniffer, device tracking, Wi-Fi scan. |
| `high` | Wysokie ryzyko. | Exploit, ATM, credentials, player target. |
| `critical` | Krytyczne ryzyko. | Powtarzalne ataki, pełny trace back, konflikt z graczem/frakcją. |

Decision:

* Przyjęto: `risk_level` jest kontraktową etykietą progu, a dokładne liczby będą ustalone przy implementacji scoringu.

---

## Tabela risk_events

| risk_event | source | typical_operations | base_risk_level | possible_consequences | mitigated_by | notes |
| --- | --- | --- | --- | --- | --- | --- |
| `camera_detected` | camera / surveillance | `camera_stream`, `camera_shutdown`, operations near cameras | medium | `warning`, `partial_detection`, `full_detection` | `camera_shutdown`, `stealth_app`, `low_noise_operation` | Kamera może wykryć operację albo obecność. |
| `failed_exploit` | exploit failure | `exploit`, player target hacking, conflict pillar hacking | high | `warning`, `partial_detection`, `cooldown`, `trace_back` | `quality_app`, `spoofing`, `operation_level` | Nieudany exploit zostawia ślad. |
| `atm_alarm` | financial terminal | `atm_log_extraction`, ATM `persistent_sniffer` | high | `warning`, `full_detection`, `HC loss`, `cooldown` | `spoofing`, `quality_app`, `camera_shutdown` | Wysoka wartość i wysoka czujność. |
| `suspicious_network_activity` | network anomaly | `scan_ports`, `sniff`, `wifi_scanner`, `persistent_sniffer` | medium | `warning`, `partial_detection`, `cooldown` | `vpn`, `spoofing`, `low_noise_operation` | Normalizuje wcześniejsze `signal_anomaly`. |
| `long_operation_detected` | duration exposure | `vehicle_tracking`, `device_tracking`, `camera_stream`, `persistent_sniffer`, `generic_trace` | medium | `warning`, `partial_detection`, `confiscated_operation` | `stealth_app`, `operation_level`, `anonymizer` | Im dłuższa operacja, tym większy ślad. |
| `aggressive_scanning` | repeated recon | repeated `scan_ports`, broad scans | medium/high | `warning`, `cooldown`, `wanted_level` | `low_noise_operation`, `quality_app`, `operation_level` | Skany są procesem hackowania, ale generują ślad. |
| `player_counter_intelligence` | player security | player target operations, territory conflict | high | `partial_detection`, `full_detection`, `wanted_level`, `reputation_loss` | `vpn`, `anonymizer`, `spoofing`, `stealth_app` | Dotyczy gry PvP i profili graczy. |
| `abandoned_operation` | uncleaned active operation | `persistent_sniffer`, `camera_stream`, tracking operations | medium | `warning`, `confiscated_operation`, `partial_detection` | `quality_app`, `operation_level`, manual cleanup | Porzucony implant lub stream zostawia ślad. |
| `trace_back` | source attribution | failed high-risk ops, long operations, player ops | critical | `full_detection`, `HC loss`, `jail`, `reputation_loss` | `vpn`, `spoofing`, `anonymizer`, `stealth_app` | Najcięższe wykrycie źródła. |

---

## Tabela risk_modifiers

| modifier | type | affects_events | effect_direction | source | notes |
| --- | --- | --- | --- | --- | --- |
| `camera_shutdown` | support_operation | `camera_detected`, `camera_stream_detected` aliases | reduce | operation | Działa lokalnie i czasowo. |
| `vpn` | security/tool | `trace_back`, `suspicious_network_activity`, `player_counter_intelligence` | reduce | app/profile/tool | Chroni przed śladem zwrotnym. |
| `spoofing` | security/tool | `trace_back`, `failed_exploit`, `suspicious_network_activity` | reduce | app/tool | Zaciemnia źródło lub target. |
| `anonymizer` | security/tool | `trace_back`, `long_operation_detected`, `player_counter_intelligence` | reduce | app/tool | Zmniejsza identyfikowalność gracza. |
| `stealth_app` | app_trait | all noisy events | reduce | app contract | Niski profil sygnału aplikacji. |
| `low_noise_operation` | operation_mode | `aggressive_scanning`, `suspicious_network_activity`, `long_operation_detected` | reduce | operation config | Mniej danych lub dłuższy czas za niższy risk. |
| `quality_app` | app_quality | `failed_exploit`, `atm_alarm`, `camera_detected`, `suspicious_network_activity` | reduce | app level/quality | Lepsza aplikacja mniej hałasuje. |
| `operation_level` | operation/app level | all operation events | reduce | app level / player level | Kontraktowo poziom zmniejsza ryzyko lub podnosi próg. |
| `high_value_target` | target_trait | `atm_alarm`, `player_counter_intelligence`, `trace_back` | increase | target_type/security | Cenniejszy target mocniej reaguje. |
| `long_duration` | operation_state | `long_operation_detected`, `trace_back` | increase | operation timer | Czas ekspozycji zwiększa score. |
| `dense_location` | world_context | `camera_detected`, `suspicious_network_activity`, `aggressive_scanning` | increase | map/world | Gęsta lokacja ma więcej sensorów i świadków. |

---

## Tabela risk_consequences

| consequence | severity | triggered_by | player_feedback | gameplay_effect | notes |
| --- | --- | --- | --- | --- | --- |
| `warning` | low | low/medium risk event | toast, system message, email optional | no hard penalty | Pierwszy miękki sygnał. |
| `partial_detection` | medium | medium/high event | warning UI, target status | increased future risk, victim alert possible | Cel wie, że coś się działo, ale nie zawsze kto. |
| `full_detection` | high | high/critical event | alarm, mail/system follow-up | player exposed, possible counteraction | Może ujawniać gracza lub operację. |
| `wanted_level` | high | repeated/full detections | visible status | increased patrol/security/risk | Długofalowa kara świata. |
| `cooldown` | medium | failed exploit, aggressive scanning, network activity | disabled action timer | temporary lock | Chroni przed spamem. |
| `HC loss` | high | trace back, financial alarm | wallet/profile notice | subtract HC | Wymaga kontroli ekonomii. |
| `confiscated_operation` | medium/high | abandoned/long detected operation | operation lost message | resource_buffer lost, implant removed | Zabiera efekt, nie zawsze karze gracza finansowo. |
| `jail` | critical | severe trace back or repeated wanted level | lockout screen/status | temporary gameplay restriction | Używać ostrożnie. |
| `reputation_loss` | medium/high | player counter-intel, full detection | profile/respect notice | respect/faction penalty | Łączy risk z social/faction loop. |

---

## Pipeline szczegółowy

### 1. Action

Gracz wykonuje akcję:

* map action,
* app action,
* operation start,
* operation stop,
* file sale,
* conflict action.

### 2. Risk signal

System zapisuje ślad:

* rodzaj akcji,
* target_type,
* source app,
* czas,
* lokację,
* zasięg,
* powiązane zabezpieczenia.

### 3. Risk score

System wylicza wynik:

```text
risk_score =
  base_risk
  + action_noise
  + target_sensitivity
  + duration_pressure
  + world_context
  - mitigation_score
```

To jest kontrakt, nie finalny wzór implementacyjny.

### 4. Risk event

Jeśli `risk_score` przekracza próg, powstaje `risk_event`.

### 5. Consequence

`risk_event` mapuje się na konsekwencję.

Konsekwencja może być:

* natychmiastowa,
* opóźniona,
* zapisana jako status,
* wysłana mailem,
* widoczna na mapie.

---

## Spójność z istniejącymi dokumentami

Sprawdzone względem:

* `doc/gameplay/operations.md`
* `doc/gameplay/map_actions.md`
* `doc/gameplay/movement_model.md`
* `doc/gameplay/data_economy.md`

### Ustalenia spójności

* Eventy szczegółowe z `operations.md`, np. `tracking_detected`, `device_tracking_detected`, `audio_sniff_detected`, mapują się na kontraktowe rodziny eventów z tego dokumentu.
* `signal_anomaly` z operacji mapuje się domyślnie na `suspicious_network_activity`.
* `financial_intrusion_detected` mapuje się domyślnie na `atm_alarm` albo przyszły financial risk event, jeśli ekonomia będzie wymagała większej precyzji.
* `scan_ports` generuje risk signal, ale nie produkuje loot/resource.
* `camera_shutdown` jest jednocześnie operacją ryzyka i modyfikatorem zmniejszającym ryzyko innych działań.
* `movement_model.md` potwierdza brak realtime loopa; risk ticki są kontrolowanymi punktami oceny, nie symulacją co sekundę.

---

## Decision

* Przyjęto: ryzyko jest liczone po zakończeniu operacji albo w kontrolowanych punktach aktywnej operacji.
* Przyjęto: nie ma losowania wykrycia co sekundę.
* Przyjęto: nazwy z `operations.md` mogą być aliasami szczegółowymi, ale `risk_events.md` definiuje główne rodziny ryzyka.
* Przyjęto: `risk_signal` może istnieć bez natychmiastowej konsekwencji.
* Przyjęto: `camera_shutdown` działa jako risk reducer, ale samo też może generować ryzyko `camera_detected`, jeśli się nie powiedzie albo trwa zbyt długo.
* Przyjęto: `jail` jest konsekwencją krytyczną i nie powinna być używana często w podstawowej pętli gry.

---

## TODO_DECISION

* Rekomendacja: przed implementacją scoringu ustalić zakresy liczbowe `risk_score`, progi eventów i wpływ `risk_level`. To jest element gameplay loop i balansu.
* Rekomendacja: zdecydować, czy `wanted_level` jest globalny, lokalny dla miasta/terytorium, czy frakcyjny. To wpływa na architekturę statusów gracza.
* Rekomendacja: zdecydować, czy `jail` blokuje całą grę, tylko mapę, czy tylko akcje ryzykowne. To jest twarda decyzja gameplay loop.
* Rekomendacja: zdecydować, czy ryzyko zapisujemy jako osobne eventy/tabelę, czy jako część operacji i profilu. To jest decyzja architektury backendu.

---

## Definition of Done Sprintu 0.8

Sprint 0.8 jest zakończony, gdy:

* istnieje `risk_events.md`,
* wiadomo, jakie są źródła wykrycia,
* wiadomo, jakie modyfikatory zmniejszają ryzyko,
* wiadomo, jakie konsekwencje może wywołać ryzyko,
* wiadomo, jak wygląda risk pipeline,
* wiadomo, jakie są poziomy ryzyka,
* istnieją tabele `risk_events`, `risk_modifiers`, `risk_consequences`,
* ryzyko nie jest projektowane jako losowanie co sekundę,
* otwarte decyzje dotyczą tylko architektury, ekonomii albo gameplay loop.
