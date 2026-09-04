# Audyt stanu faktycznego supermocy GhostNetwork

Data audytu: 2026-09-04
Rewizja bazowa: `626b161`
Zakres: katalog 20 części, aktywacja uprawnienia, registry, adaptery, gameplay
call-sites, API, UI, zdarzenia, feature flags i testy.

## 1. Werdykt

Supermoce GhostNetwork są obecnie **zaimplementowane jako katalog i read-only
system uprawnień, ale nie jako mechanika rozgrywki**.

Stan w liczbach:

| Warstwa | Stan faktyczny |
| --- | --- |
| Części w katalogu | 20/20 |
| Profesje w katalogu | 20/20 |
| Definicje ability/effect type | 20/20 |
| Powiązanie część → profesja → moc | 20/20 |
| Wyliczanie dostępności po aktywacji części | działa |
| Ochrona klan/profesja/cykl/module state | działa |
| Widoczność nazwy mocy w Suite/Territory Control | działa zgodnie z projekcją |
| Konkretne adaptery zmieniające mechanikę | 0/6 |
| Produkcyjne call-site `collect_ability_effects()` | 0 |
| Produkcyjne call-site `apply_ability_modifier()` | 0 |
| Endpoint/komenda użycia aktywnej mocy | 0 |
| Trwałe instancje, cooldowny i limity użycia | 0 |
| Eventy pojedynczego użycia mocy | 0 |
| E2E testy rzeczywistego efektu gameplay | 0/20 |

Najważniejsze rozróżnienie:

```text
aktywna część
  → registry zwraca active_abilities=[...]
  → UI może pokazać nazwę zdolności
  → rozgrywka NIE otrzymuje żadnego efektu
```

Nie należy zatem komunikować graczom, że supermoc mechanicznie działa. Obecny
stan oznacza: „moc jest odblokowana w modelu domenowym”, nie „moc jest dostępna
do użycia albo zmienia parametry gry”.

## 2. Źródła prawdy i dowody

### Katalog

`ghostnetwork/catalog.py` zawiera:

- `PART_DEFINITIONS` — 20 części, profesji i `ability_code`;
- `ABILITY_EFFECT_TYPES` — mapowanie 20 mocy na typ efektu;
- `_build_abilities()` — kontrakt ability z `requires_active_part=true`;
- walidację wymuszającą dla każdej katalogowej mocy
  `mechanics_status="catalog_only"`.

### Warunek aktywacji

`ghostnetwork/abilities.py:286` wylicza dostępność na podstawie:

1. poprawnej tożsamości katalogowej gracza;
2. właściwego klanu i profesji;
3. odpowiadającej profesji części;
4. otwartego cyklu;
5. `module_state == active`.

Właściciel terytorium nie musi być użytkownikiem mocy. Aktywna część odblokowuje
ją wszystkim członkom właściwego klanu mającym odpowiadającą profesję. Konflikt
nie wyłącza uprawnienia, jeżeli frozen module state pozostaje `active`. Utrata
części, zamknięcie cyklu albo transmisja odbiera uprawnienie przy kolejnym
resolve.

Ta część kontraktu jest rzeczywiście wykonywalna i pokryta testami.

### Adaptery

Istnieje sześć nazwanych adapterów:

- `GhostMarketAbilityAdapter`;
- `GhostHackAbilityAdapter`;
- `GhostTerritoryAbilityAdapter`;
- `GhostOperationAbilityAdapter`;
- `GhostVisibilityAbilityAdapter`;
- `GhostCybernerAbilityAdapter`.

Żaden nie nadpisuje `collect_effects()` ani `apply_modifier()`. Wszystkie
dziedziczą zachowanie bazowe:

```python
def collect_effects(self, active_effects, context):
    return list(active_effects or [])

def apply_modifier(self, effect, context, value):
    return value
```

Registry potrafi więc zwrócić metadane aktywnej mocy, lecz każdy modyfikator
zwraca niezmienioną wartość.

### Brak integracji produkcyjnej

Poza `ghostnetwork/abilities.py`, wrapperami w `ghostnetwork/service.py` i testami
nie ma wywołań:

- `resolve_player_abilities()`;
- `is_ability_active()`;
- `collect_ability_effects()`;
- `apply_ability_modifier()`.

Nie istnieje route API ani komenda gracza aktywująca zdolność. Systemy market,
hack, territory, operation, visibility i Cyberner nie pytają registry o efekt.

### UI

Viewer-safe projection może ujawnić `ability_code`, `ability_name` i
`ability_description` tylko widzowi mającemu pełną widoczność części.
GhostNetwork Suite i Territory Control pokazują nazwę zdolności, ale nie
udostępniają przycisku użycia, stanu cooldownu, limitu instancji ani wyniku
mechanicznego.

### Zdarzenia

Transmisja emituje globalne `ghost.abilities_disabled`, gdy części zostają
zużyte. Nie istnieją działające producenci eventów:

- `ghost.ability_enabled`;
- `ghost.ability_disabled` dla pojedynczej mocy;
- `ghost.ability_activated`;
- `ghost.ability_expired`;
- `ghost.ability_cancelled`;
- `ghost.ability_cooldown_changed`.

Globalny event końca cyklu jest spójny narracyjnie, ale obecnie nie zamyka
żadnych trwałych instancji mocy, ponieważ takie instancje nie istnieją.

### Feature flag

Runbook wymienia `GHOSTNETWORK_ABILITIES_ENABLED`, lecz runtime nie definiuje ani
nie odczytuje tej zmiennej. Nie jest to działający kill switch. Aktualnie nie
powoduje to efektu gameplay, ponieważ adaptery są no-op, ale przed wdrożeniem
pierwszej realnej mocy brak flagi byłby ryzykiem operacyjnym.

## 3. Macierz 20 supermocy

W kolumnie „klasa registry” podano wartość nadawaną dynamicznie przez
`_ability_mechanics_status()`. Nie oznacza ona implementacji efektu.

| Część | Klan / profesja | Moc (`ability_code`) | Typ efektu | Klasa registry | Realny efekt |
| --- | --- | --- | --- | --- | --- |
| V1 Ledger Nexus | VIREX / Broker | Przepływy rynku (`insider_feed`) | `market_demand_preview` | `passive_active` | brak; Ghost Exchange nie konsumuje efektu |
| V2 Backdoor Forge | VIREX / Architekt | Wejścia serwisowe (`service_entrance`) | `hack_threshold_modifier` | `passive_active` | brak; próg hacku nie jest modyfikowany |
| V3 Mimicry Engine | VIREX / Manipulator | Obrazy zastępcze (`false_image`) | `territory_information_mask` | `passive_active` | brak; projekcja terytorium nie jest maskowana mocą |
| V4 Acquisition Drive | VIREX / Egzekutor Zysku | Przejęcia (`hostile_takeover`) | `territory_attack_window` | `active_command` | brak komendy i okna ataku |
| V5 Probability Core | VIREX / Kurator Algorytmu | Predykcja operacji (`operational_prediction`) | `operation_probability_zone` | `active_command` | brak komendy i stref prawdopodobieństwa |
| E1 Breach Voice | Echo Wolności / Haktywista | Ujawnienie (`expose`) | `security_weakness_reveal` | `active_command` | brak komendy i ujawnienia słabości |
| E2 Influence Relay | Echo Wolności / Socjotechnik | Przejęcie narracji (`narrative_takeover`) | `operation_alert_delay` | `passive_active` | brak; alert operacji nie jest opóźniany |
| E3 Truth Lens | Echo Wolności / Odsłaniacz | Pełne ujawnienie (`full_disclosure`) | `scan_detail_modifier` | `passive_active` | brak; skan nie otrzymuje dodatkowych danych |
| E4 Resonance Beacon | Echo Wolności / Wizjoner | Beacon oporu (`resistance_signal`) | `clan_operation_beacon` | `active_command` | brak komendy, beacona i publikacji Cybernera |
| E5 Spark Chamber | Echo Wolności / Zapalnik | Efekt domina (`domino_effect`) | `neighbor_security_reduction` | `event_reaction` | brak reakcji po rozbrojeniu sąsiada |
| P1 Mirage Projector | Siatka Widmo / Iluzjonista | Węzeł-widmo (`phantom_node`) | `false_activity_marker` | `active_command` | brak komendy i fałszywego markera |
| P2 Glitch Reactor | Siatka Widmo / Wirusolog | Wstrzyknięcie glitcha (`glitch_injection`) | `territory_stability_damage` | `active_command` | brak komendy, infekcji i obrażeń stabilności |
| P3 Paranoia Loop | Siatka Widmo / Paranoik | Fałszywe tropienie (`false_tracking`) | `false_tracking_traces` | `active_command` | brak komendy i fałszywych śladów |
| P4 Fracture Engine | Siatka Widmo / Rozłamowiec | Rozłam sieci (`network_fracture`) | `territory_connection_disruption` | `active_command` | brak komendy i zakłócenia połączeń |
| P5 Mirror Kernel | Siatka Widmo / Lustrzany Sędzia | Odbicie (`reflection`) | `attack_reflection` | `event_reaction` | brak reakcji na skan/infiltrację |
| S1 Deep Sensor | Strażnicy Ładu / Analizator | Skan integralności (`integrity_scan`) | `territory_integrity_scan` | `active_command` | brak komendy i raportu integralności |
| S2 Bastion Matrix | Strażnicy Ładu / Obrońca | Bastion (`bastion`) | `territory_defense_layer` | `active_command` | brak komendy i dodatkowej warstwy obrony |
| S3 Restoration Engine | Strażnicy Ładu / Rekonstruktor | Odtworzenie (`rollback`) | `territory_repair` | `active_command` | brak komendy i naprawy |
| S4 Accord Relay | Strażnicy Ładu / Mediator | Korytarz zaufania (`trust_corridor`) | `trusted_access_corridor` | `active_command` | brak komendy i czasowego dostępu |
| S5 Judgment Core | Strażnicy Ładu / Egzekutor | Kwarantanna (`quarantine`) | `operation_quarantine` | `active_command` | brak komendy i blokady operacji |

Podsumowanie klasyfikacji registry:

- `passive_active`: 5;
- `active_command`: 13;
- `event_reaction`: 2;
- rzeczywiście `implemented`: 0.

## 4. Rozbieżności i ryzyka

### GN-ABILITY-01 — CRITICAL — brak mechaniki 20/20

Kontrakt fabularny opisuje efekty, ale żaden system gameplay ich nie konsumuje.
Aktywowanie części nie zmienia rynku, hacku, terytorium, operacji, widoczności
ani Cybernera.

### GN-ABILITY-02 — HIGH — mylący `mechanics_status`

Katalog prawidłowo zapisuje wszystkie moce jako `catalog_only`, lecz registry
zamienia status na `passive_active`, `active_command` albo `event_reaction` tylko
na podstawie nazwy `effect_type`. Te wartości wyglądają jak stopień wdrożenia,
mimo że adaptery nadal są no-op. Testy sprawdzają jedynie, że status nie jest
równy `implemented`.

Rekomendacja: rozdzielić pola:

```text
interaction_mode = passive | command | reaction
implementation_status = catalog_only | implemented | disabled
```

### GN-ABILITY-03 — HIGH — niedziałająca flaga operacyjna

`GHOSTNETWORK_ABILITIES_ENABLED` istnieje wyłącznie w dokumentacji. Przed
wdrożeniem pierwszego efektu potrzebny jest backendowy, domyślnie wyłączony
kill switch egzekwowany przy resolve i ponownie przy wykonaniu.

### GN-ABILITY-04 — HIGH — brak command/runtime contract

Dla 13 mocy sklasyfikowanych jako `active_command` nie istnieją:

- request schema;
- canonical target resolver;
- autoryzacja i ponowny resolve aktywnej części;
- idempotency key/receipt;
- koszt, cooldown i limit instancji;
- durable state oraz recovery;
- event wyniku i System Messaging;
- przycisk lub terminalowa komenda.

### GN-ABILITY-05 — HIGH — brak hooków reakcji

`domino_effect` i `reflection` nie są podłączone do canonical eventów hacku,
capture, skanu ani infiltracji. Sam status `event_reaction` niczego nie
subskrybuje.

### GN-ABILITY-06 — MEDIUM — UI sugeruje możliwość, której nie ma

Suite pokazuje etykietę „ZDOLNOŚĆ”/„MOC” przy aktywnej części, ale nie odróżnia
„zidentyfikowana w katalogu” od „mechanicznie dostępna”. Może to tworzyć fałszywe
oczekiwanie gracza.

### GN-ABILITY-07 — MEDIUM — testy potwierdzają tylko fundament

`tests/test_ghostnetwork_abilities.py` dobrze testuje eligibility, cache,
konflikt, utratę części i zamknięcie cyklu. Jawnie potwierdza również, że
`apply_modifier(..., 100)` zwraca `100`. Nie ma testu realnego efektu żadnej z
20 mocy, ponieważ taki efekt nie istnieje.

## 5. Stan produkcyjny z dostępnych dowodów

Ostatni przekazany odczyt serwera z 2026-09-03 pokazywał w aktywnym cyklu:

- 11 części `active`;
- 1 część `contained`;
- 5 części `public`;
- 3 części `pooled`.

Oznacza to, że registry mogło wyliczać dostępność mocy odpowiadających 11
aktywnym częściom dla graczy o pasującej profesji. Nie oznacza to 11 działających
efektów — ich realna liczba pozostawała równa zero. Jest to dowód historyczny,
nie live snapshot po wdrożeniu `626b161`.

## 6. Skorygowany kierunek wdrożenia

Audyt pierwotnie wskazywał potrzebę pełnego executora, receiptów i lifecycle
osobnego dla każdej mocy. Decyzja produktowa upraszcza ten kierunek: supermoce
mają używać wzorca prezentacyjnego `Secret Path` oraz małych modyfikatorów w już
istniejących mechanikach. Nie powstaje drugi system efektów.

Potwierdzone punkty zaczepienia obecnego runtime:

| Obszar | Stan faktyczny |
| --- | --- |
| Overlay 4 s i CSS | działa w `showSecretPathLore()` |
| SFX | działa przez wspólne `window.GameSfx` i bus `lore` |
| Assety | istnieją dla wszystkich 20 części |
| Timery operacji | istnieją `started_at`, `expires_at`, `duration_seconds`, `remaining_seconds` |
| Pliki | canonical finalizacja oraz foldery camera/audio/credentials/financial/personal itd. |
| Hack | istnieją action state oraz mapa zabezpieczeń celu |
| Zasięg/zoom | istnieją `get_player_action_range()` i `get_player_map_zoom()` |
| Incydenty/NPC | istnieją store, kapsuły, TTL, snapshot/delta i renderer mapy |
| Aktorzy | istnieje endpoint i renderer aktorów mapy |
| Ryzyko operacji | istnieją heat, warning/incident thresholds i risk state |
| Jakość danych | istnieją quality/completeness oraz ich wpływ na cenę plików |

Pole `bike_range_bonus` jest zapisywane przez zakup, ale znaleziony runtime
zasięgu korzysta z `scan_range_bonus` przez `get_player_action_range()`. Przed
użyciem `bike_range_bonus` jako mocy potrzebny byłby rzeczywisty consumer; sama
obecność pola nie jest dowodem działania.

Minimalne wspólne rozszerzenie to jeden backendowo autorytatywny rekord okna:

```text
player + ability + source_part + activated_at + expires_at + cooldown_until
```

Domyślna hipoteza testowa to 15 minut działania i cooldown 1 godziny od
aktywacji. Snapshot mapy odbudowuje licznik po reloadzie. Nie jest potrzebny
scheduler wygaśnięć: call-site uznaje modyfikator za aktywny wyłącznie, gdy
`now < expires_at`.

Wymagane przed pierwszym realnym efektem:

1. viewer-safe przycisk z nazwą mocy tylko dla poprawnej profesji;
2. ponowna walidacja cyklu, części, klanu, profesji i cooldownu na backendzie;
3. brak mnożników i wyników pochodzących z payloadu klienta;
4. jedno okno 15 min, odporne na podwójny klik i reload;
5. show 4–6 s na bazie Secret Path, asset części, SFX i tekstowy fallback;
6. jeden mały hook w konkretnym istniejącym call-site;
7. widoczny dla gracza skutek oraz System Message bez spamu;
8. brak nowego workera, kolejki, event busa, LLM i osobnego runtime'u mocy;
9. decyzja `KEEP / ADJUST / REPLACE / DEFER` po pierwszym teście frontendowym;
10. prosty unit/integration/E2E dla wybranego parametru.

Obowiązują również twarde ograniczenia projektu: zero pełnych odczytów i zapisów
`profile_json`, zero `list_profiles()`/account scan, zero nieograniczonego
fan-out, krótka transakcja SQLite, narrow canonical stores, istniejące CAS/owner
checks oraz session generation. Supermoc nie może wprowadzić nowego workera,
kolejki, schedulera, outboxu, event busa, LLM na hot path ani osobnej bazy.
Szczegółowa lista blokujących reguł i wymaganych metryk znajduje się w sekcji 2
planu `138.getway`.

Pierwszym kandydatem jest `Insider Feed`: przyspieszenie już rozpoczętych i
nowych operacji w aktywnym oknie. Hipoteza balansu
`clamp(0.1 × LVL, 1.5, 8.0)` daje `7.1×` na poziomie 71. Następne dwa pionowe
testy to `Wejście Serwisowe` (wykonane action dots oznaczonego celu, security
pozostaje) i `Fałszywy Obraz` (syntetyczne incydenty oraz istniejące kapsuły
służb na obrzeżach klastrów).

Do pakietu bezpiecznych rodzin modyfikatorów dodano także `operation_risk` oraz
`data_quality`. Pierwsza korzysta z istniejącego risk metera, druga z istniejącej
kompletności/jakości plików i ich obecnego wpływu na cenę. Nie ustawiają
bezpośrednio wyniku detekcji, incydentu ani finalnej ceny.

Warstwa wizualna korzysta ze wspólnej palety klanów już obecnej na mapie: VIREX
czerwony, Echo żółty, Siatka Widmo turkusowy, Strażnicy niebieski. Asset
konkretnej aktywnej części pozostaje widoczny przy liczniku przez całe 15 minut.

## 7. Polecenia do weryfikacji serwerowej

Stan części bieżącego cyklu:

```bash
sqlite3 -cmd ".timeout 10000" -header -column data/game.sqlite3 "
WITH active AS (
  SELECT cycle_id
  FROM ghost_cycles
  WHERE status='active'
  ORDER BY created_at DESC
  LIMIT 1
)
SELECT part_code,status,conflict_state,discovered_clan,territory_clan
FROM ghost_parts
WHERE cycle_id=(SELECT cycle_id FROM active)
ORDER BY part_code;
"
```

Sprawdzenie, czy PM2 posiada dokumentowaną flagę (nie zmienia faktu, że obecny
kod jej nie konsumuje):

```bash
pm2 env 13 | grep -E 'CHAOS_GHOSTNETWORK_ABILITIES_ENABLED|GHOSTNETWORK_ABILITIES_ENABLED'
pm2 env 14 | grep -E 'CHAOS_GHOSTNETWORK_ABILITIES_ENABLED|GHOSTNETWORK_ABILITIES_ENABLED'
```

Test fundamentu registry:

```bash
.venv/bin/python -m unittest tests.test_ghostnetwork_abilities -v
```

## 8. Decyzja audytu

| Pytanie | Odpowiedź |
| --- | --- |
| Czy aktywacja części zmienia `module_state` i eligibility? | TAK |
| Czy właściwa profesja widzi odblokowaną moc w registry? | TAK |
| Czy UI może pokazać nazwę mocy? | TAK |
| Czy moc może zostać użyta? | NIE |
| Czy moc pasywna zmienia wynik gameplay? | NIE |
| Czy reakcja eventowa działa? | NIE |
| Czy istnieje operacyjny kill switch? | NIE |
| Czy można uznać którąkolwiek moc za wdrożoną? | NIE |

Końcowy status: **FOUNDATION PASS / GAMEPLAY NOT IMPLEMENTED**.

Lekki plan wdrożenia i blokująca bramka przed pełnym testem GhostSignalu:
`doc/sprints/sprint_138_getway_ghostnetwork_superpowers.md`.

Nazwy i `effect_type` w powyższej macierzy opisują aktualny katalog, ale nie są
jeszcze finalną decyzją produktową. `138.getway.0` najpierw certyfikuje 12/12
zamkniętych realizerów przez operatorski pilot V1 / `Insider Feed`. Override
rodziny jest wyłącznie testowy i serwerowy; finalny V1 używa tylko
`operation_speed`. W `138.getway.1–4` każda profesja otrzymuje
osobny podsprint frontend-first. Finalny efekt jest wybierany z małej grupy
istniejących parametrów i zatwierdzany jako `KEEP / ADJUST / REPLACE / DEFER`
po pierwszym teście frontendowym. Priorytetem jest odczuwalny efekt mapowy i
gameplay przez 15 minut, nie budowa uniwersalnego silnika supermocy.
