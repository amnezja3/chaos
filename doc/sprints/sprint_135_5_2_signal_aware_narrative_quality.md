# Sprint 135.5.2 — Signal-Aware Narrative Quality

Status: `IN PROGRESS — ETAP I IMPLEMENTED LOCALLY / SERVER VALIDATION PENDING`

## Stan implementacji — Etap I

Zaimplementowano lokalnie:

- trwałe pole `narrative_intent` w outboxie oraz medium recordzie;
- deterministyczny mapping konfliktu, incydentu, radia, produktu i fallbacku;
- intent wchodzi do semantic source version, więc zmiana kontraktu tworzy jeden
  nowy legalny task zamiast reinterpretować historyczny candidate;
- bounded task package przekazuje intent modelowi, ale nie daje mu możliwości
  wyboru lub zmiany tego pola;
- immutable prompty `blacknet-signal-prompt-v7` oraz
  `googleplex-world-hero-prompt-v12`, opisujące role bez przykładów odpowiedzi;
- `signal_source_echo` dla body kopiującego presentation-safe pole źródła;
- `narrative_filler_phrase` dla pustych konstrukcji potwierdzonych w gameplayu;
- product promo v2 zachowuje osobny `product_benefit_promo`;
- navigation i capability assignments zachowują `capability_invitation`;
- retry, candidate i publisher zachowują ten sam code-owned intent w audycie;
- 101 testów kolejki, policy, producentów, publishera i projekcji: PASS.

Pierwsza walidacja serwerowa v6/v11 potwierdziła poprawny routing intentów, ale
ujawniła dwie kolejne granice jakości. Product transmission użył nieistotnego
`45 TEMP / 0 POBRAN`, a radio skleiło `stat + label` bez transformacji. Kontrakt
`signal-aware-v2` usuwa `stat` z bounded faktu produktu, pozostawiając nazwę i
cenę, a validator odrzuca `TEMP/pobrania` jako
`product_transmission_metric_leak`. Composite source-echo rozpoznaje teraz body
złożone wyłącznie z kilku pól canonical. Prompty v7/v12 opisują oba wymagania;
zmiana wersji kontraktu źródła tworzy jeden nowy legalny task zamiast replayować
zakończone v6/v11.

Nie zmieniono kwalifikacji sygnałów do HERO; to pozostaje Etapem II.

## Cel

Podnieść jakość treści BlackNet i Googleplex bez oddawania modelowi decyzji
redakcyjnych odzyskanych w 135.5.1. Backend nadal wybiera źródło, medium, slot,
CTA, target, produkt, cenę i asset allowlistę. Ollama dostaje jedno zadanie i
pisze tekst w głosie właściwym dla jego deterministycznego rodzaju.

```text
canonical source
  -> backend narrative_intent + slot eligibility
  -> one bounded task
  -> Ollama copy
  -> source-echo / safety / geometry validation
  -> assigned medium and slot
```

## Powód otwarcia

Transport 135.5.1 przeszedł walidację serwerową, ale pierwsze realne publikacje
ujawniły teksty poprawne faktograficznie i słabe narracyjnie:

- product promo kopiował canonical opis produktu słowo w słowo;
- radio przepisywało liczbę kanałów jak rekord bazy;
- BlackNet używał raportowego języka zamiast przechwyconej transmisji;
- HERO wypełniał brak miejsca frazami `w roku 2108` i `w rejonie celu`;
- sygnał o małej zawartości informacyjnej mógł otrzymać powierzchnię HERO.

To nie są błędy kolejki, publishera ani slot CAS. Są luką pomiędzy typem
canonical sygnału a kontraktem językowym modelu 8B.

## Zasady

1. Model nie wybiera `narrative_intent`; przypina go backend.
2. Jeden task nadal zawiera dokładnie jedno canonical źródło.
3. Prompt opisuje rolę i sposób wypowiedzi, bez copy-ready przykładów.
4. Brak danych nie może być maskowany pustym dramatyzmem ani zmyśleniem.
5. Słaby sygnał może trafić do BlackNet lub małego boxu, ale nie musi dostać HERO.
6. Canonical nazwa, cena, statystyka, CTA i link pozostają backend-owned.
7. Pełny profil gracza jest zabroniony na całej ścieżce.

## Deterministyczne narrative intents

Minimalny registry:

```text
conflict_target_alert -> intercepted_conflict_warning
incident_hotspot      -> intercepted_incident_alert
radio_promotion       -> intercepted_broadcast_fragment
product_opportunity   -> intercepted_product_transmission (BlackNet)
googleplex product    -> product_benefit_promo (Googleplex box)
capability contract   -> capability_invitation
```

Intent określa dozwolony głos, zakres faktów, limity oraz kwalifikację slotu.
Nie zmienia canonical `signal_type` i nie jest generowany przez Ollamę.

## HERO eligibility

Backend wylicza bounded `content_sufficiency`, bez profilu i bez modelu.
HERO wymaga konkretu pozwalającego napisać tytuł i lead bez technicznych
wypełniaczy. Radio promotion, pusty status lub sam licznik nie otrzymują HERO,
jeżeli brakuje canonical obiektu, miejsca albo znaczącej zmiany stanu.

Brak legalnego HERO assignmentu zachowuje aktywny slot/foundation. Nie tworzy
fallbackowego taska tylko po to, aby zapełnić harmonogram.

## Source-echo guards

Walidator porównuje output z presentation-safe źródłem odpowiednim dla intentu:

```text
exact normalized copy       -> rejected
source wrapped in filler    -> rejected
near-identical description  -> rejected
canonical title required    -> preserved by backend
canonical stat in own field -> preserved by backend, nie wymaga kopii w body
```

Guard nie zabrania użycia canonical nazwy produktu, obiektu lub miejsca. Odrzuca
kopiowanie całego opisu zamiast wykonania transformacji narracyjnej.

## Pierwszy slice — product promo v2

Zaimplementowano lokalnie:

- immutable prompt `googleplex-product-promo-v2`;
- rola copywritera Googleplex roku 2108, bez przykładów odpowiedzi;
- wymaganie nowego sloganu opartego na problemie i jednej korzyści;
- `product_promo_source_echo` wykrywający kopię, zawarty opis i prawie identyczną
  parafrazę;
- canonical tytuł, cena, produkt, CTA, link i asset resolution bez zmian;
- test dokładnego produkcyjnego przypadku V-MAP;
- 53 testy policy/producer/publication: PASS.

Historyczny rekord v1 pozostaje append-only audytem. Nowy task po cooldownie
używa v2; nie edytujemy istniejącej publikacji w miejscu.

## Zakaz heavy-profile

`narrative_intent`, content sufficiency, prompt selection i source-echo validation
korzystają wyłącznie z pojedynczego bounded factu, publicznego katalogu, registry,
medium records i slot state. Zabronione są:

```text
user_store.get_profile
UserProfileManager.get_profile
users.profile_json
profile operations/files/apps/wallet hydration
account-specific catalog jako fallback publicznej publikacji
```

Brak potrzebnej canonical projekcji daje `source_unavailable` albo brak taska.
Nie wolno omijać tego pełnym odczytem profilu.

## Etapy

### Etap I — intents i jakość copy

- product benefit promo v2;
- intent registry dla conflict/incident/radio/product;
- prompty roli bez przykładów;
- source-echo i filler guards;
- testy na rzeczywistych kształtach faktów.

### Etap II — kwalifikacja powierzchni i soak

- deterministic HERO eligibility/content sufficiency;
- brak niskoinformacyjnego radia w HERO;
- walidacja kilku publikacji per intent;
- pomiar novelty, quarantine/rejected i retry/no-change;
- potwierdzenie braku heavy-profile I/O i SQLite contention.

## Definition of Done

```text
backend-owned narrative_intent:       LOCAL PASS / SERVER PENDING
one source / one task:                PASS
product description echo rejected:   LOCAL PASS / SERVER PENDING
BlackNet voice per signal type:       LOCAL PASS / SERVER PENDING
HERO content sufficiency gate:        PENDING
no filler year/region phrases:        LOCAL PASS / SERVER PENDING
canonical data and CTA ownership:     PASS
profile reads/writes:                 0
physical multi-intent validation:     PENDING
gameplay performance soak:            PENDING
```

## Walidacja serwerowa Etapu I

Po deployu nowy single-signal task powinien mieć prompt v6 albo v11 i jawny
intent. Historyczne v5/v10 pozostają audytem i nie są claimowane jako nowa
polityka.

```sql
SELECT outbox_id,target_medium,status,task_variant,narrative_intent,
       prompt_version,attempt_count,last_error_code,created_at
FROM ghost_narrative_outbox
WHERE prompt_version IN ('blacknet-signal-prompt-v7',
                         'googleplex-world-hero-prompt-v12')
ORDER BY created_at DESC
LIMIT 20;
```

Po publikacji `ghost_narrative_medium_records.narrative_intent` musi być zgodny
z taskiem. W outputach nie mogą wystąpić `w roku 2108`, `w rejonie celu`,
`w globalnym zasięgu`, raportowe `odnotowano produktową szansę` ani body będące
kopią lub sklejeniem `title/label/value/stat`. Dla intentu produktowego model
nie otrzymuje `stat` i nie może publikować `TEMP` ani liczby pobrań.

## Powiązane dokumenty

- `doc/sprints/sprint_135_5_1_deterministic_editorial_queue_slot_copy.md`
- `doc/sprints/sprint_135_5_llm_publishers_blacknet_googleplex_cyberner.md`
- `doc/hardbugfix/llm_publication_contract_regressions_sprint_135_5_2026-08-30.md`
- `doc/hardbugfix/heavy_profile_operation_files_gx_regression_sprint_135_5_2026-08-30.md`
