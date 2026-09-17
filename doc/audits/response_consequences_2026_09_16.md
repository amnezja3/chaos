# Response Network — audyt konsekwencji, 16 IX 2026

Status: rozszerzony audyt kodu i testów lokalnych zakończony przed sprintami;
MVP nie ma odbioru produkcyjnego
w obecnej architekturze. Bez wykonania kar na produkcji. Zmiany robocze Cybernera
zastane w repo pozostawione bez zmian.

Rozszerzenie zakresu autora: plany 142/143 obejmują także publikacje w mediach
i BlackNecie, ponowne użycie reguł Super Powers oraz recydywę. Audyt publikacji,
cyklu incydentu, autoryzacji shutdown i modyfikatorów uzupełniono poniżej;
nie jest zadaniem odkładanym na development. Wylogowanie nie kończy automatycznie incydentu ani
wcześniej nałożonej kary; plany zastępują wcześniejszą propozycję czasu offline.

## Wniosek

Zachował się działający szkielet: kapsuły trzech służb, lokalny detektor,
walidator backendowy, policy, executor, tabela efektów i audyt. Są anulowanie
operacji, konfiskata narzędzia, kara HC, punkty Judgment i hooki powiadomień.
Nie jest to jednak opisany przez autora mechanizm 30%/80% dla napotkanego gracza.
Executor nadal mutuje pełny profil, mimo przeniesienia zasobów do store’ów.
Nie należy rozszerzać go o więzienie przed zakończeniem sprintu 142.

## Przepływ istniejący

1. `response_network/npc_capsule_factory.py`: police, cyberpolice, secretservice,
   deterministyczny ruch z seed; promień `max(55, min(180, 65 + level*18 + service_level*8))`.
   Promień zależy też od poziomu incydentu, nie tylko rodzaju służby.
2. `templates/map_template.html`: `collectLocalDetectionActors` zbiera markery
   graczy i własny avatar; `runLocalDetectionProbe` sprawdza odległość co min.
   1200 ms w pętli animacji. To request przeglądarki, nie samodzielny tick służby.
3. `submitLocalDetectionCandidate`: POST `/api/map/incidents/detection-candidates`.
   Dedupe klienta: kapsuła/aktor/10 s; maks. 300 zapamiętanych zgłoszeń.
   Zgłoszenie trafia do `submitted` także po HTTP error; feedback pochodzi
   z `payload.status`. Znacznik wykrycia nie oznacza wykonania kary.
4. `run.py:map_incident_detection_candidates`: wymaga sesji, dopisuje obserwatora,
   wymusza `full`, przekazuje `load_profile_readonly` do walidatora.
5. `DetectionValidator.validate`: weryfikuje identyfikatory, status incydentu,
   kapsułę, publiczny tracking token, wersję/seed, okno czasu kapsuły,
   rekonstrukcję NPC (tolerancja 45 m), operację i zasięg (+15 m tolerancji).
6. `ConsequencePolicy.prepare_intent`: dla accepted i operation_id tworzy intent.
   Nie losuje 30% ani 80%. Flagi kar są w run.py włączone w trybie full.
7. `ConsequenceExecutor.execute`: zapisuje prepared, mutuje profil, zapisuje
   executed. Wrapper dopiero potem obciąża kanoniczny portfel, publikuje delty
   i zapisuje profil przez UserProfileManager.

## Ustalenia i ryzyka

| Priorytet | Stan faktyczny | Znaczenie |
|---|---|---|
| P0 | Pozycja aktora pochodzi z requestu; backend rekonstruuje tylko NPC | Obserwator może zgłosić cudzą pozycję; publiczny token nie dowodzi obecności |
| P0 | `detected_at` nie jest ograniczony względem czasu serwera | Akceptowana jest historyczna scena, jeżeli rekordy nadal mają aktywny status |
| P0 | `_protected_passive_or_offline` nie odczytuje presence; przy znalezionej operacji zwraca False | Nie ma gwarancji ochrony offline ani osobnej klasyfikacji timeout/inactive |
| P0 | prepared/executed, wallet, inventory, profil i wiadomości nie są jedną transakcją | Crash może zostawić karę częściową; istniejący prepared jest zwracany jako duplicate, bez wznowienia |
| P0 | Konfiskata zmienia `profile.apps/files`, nie wywołuje canonical inventory uninstall | Dzisiejszy arsenał nie musi utracić aplikacji mimo wyniku confiscated |
| P1 | Walidacja wymaga aktywnej operacji powiązanej z incydentem | Postronny bez operacji odpada przed policy; brak ścieżki 30% |
| P1 | Brak klasyfikacji inicjator/postronny i brak losowania szans w policy/executor | Accepted prowadzi do próby wykonania, a nie rzutu 80% |
| P1 | Hook wiadomości dopisuje do profilu | Nie jest to trwała publikacja przez dzisiejszy SystemMessageStore |
| P1 | Pełny profil w validator loader, drugi odczyt we wrapperze, UserProfileManager i session.profile | Naruszenie kontraktu hot path; koszt rośnie z profilem, także przy odrzuceniu po odczycie |
| P1 | Operacje w validatorze mają overlay runtime, executor czyta surowy profil | Dwa różne źródła stanu operacji w tej samej ścieżce |
| P1 | Dedupe walidacji bazuje na 10 s, operation_id i kapsule | Nie definiuje pojedynczego spotkania ani trwałego rzutu; wiele patroli/obserwatorów wymaga wspólnej reguły |
| P2 | Praca zależy od mapy i requestAnimationFrame; interakcja mapy pomija probe | Sam znacznik w UI nie gwarantuje serwerowego, niezależnego od widoku wykrycia |

Canonical overlay w `database.py:overlay_canonical_profile_scopes_with_conn`
przy zapisie profilu przywraca istniejący inventory. Nie wolno naprawiać tego
przez wyłączenie overlay: kara musi zmieniać źródło kanoniczne.
Portfel ma klucz `response_consequence:<id>`, co chroni ten sam debit, lecz nie
zapewnia atomowości całego zestawu kar. Wartość kary jest wyliczana przed debit;
rezerwa HC wymaga ponownej kontroli przy współbieżnym obciążeniu.

## Co jest zaimplementowane

- Anulowanie powiązanej operacji i usunięcie jej postępu/bufora.
- Konfiskata narzędzia użytego w operacji; ochrona ostatniego narzędzia
  operacyjnego. To nie losowy przedmiot postronnego — tej reguły brakuje.
- HC: baza max(10, risk/2), limit 18% salda, rezerwa do 50 HC; implementacja
  algorytmu istnieje, trwałość całego workflow wymaga naprawy.
- Judgment: punkty i poziom low/medium/high. Nie jest więzieniem ani blokadą ruchu.
- Feature flags, globalny kill switch executora, identyfikator skutku i audyt.

W prześledzonej ścieżce Response Network brak egzekwowanych sankcji komunikacji,
ruchu, teleportacji oraz pobytu w więzieniu i zwolnienia z niego.

## Dowody i ograniczenia

Uruchomiono na tymczasowych bazach:

```text
python -B tools/run_isolated_tests.py test_consequence_full_response test_consequence_limited_enforcement test_detection_feedback_shadow test_response_warning_visible_safe test_response_npc_frontend_contract test_npc_behavior_capsules test_response_consequence_audit
33 testy: PASS
```

W tym 3 nowe reprodukcje potwierdzają aktualne luki: klient nadpisuje pozycję,
historyczny czas zostaje zaakceptowany, postronny bez operacji jest odrzucany.
Ich PASS potwierdza diagnozę, NIE gotowość produkcyjną. Sprint 142 zastąpi je
testami kontraktu naprawionego. Poprawiono wyłącznie względne ścieżki w starym
teście frontendowym, aby działał z izolowanym cwd. Pierwsze uruchomienie miało
błąd setup tego testu; po poprawce cały zestaw przeszedł.

Stare testy executora sprawdzają głównie słownik profilu. Nie dowodzą aktualności
kanonicznego inventory, operacji, outboxu ani odporności na awarię między commitami.
Nie wykonywano produkcyjnego smoke, pomiarów p95/p99 ani pełnego testu UI.
Nie wdrażano hotfixa ani nie zmieniano ustawień egzekucji kar.

## Ustalenia autora a starszy kontrakt

Aktualne wymaganie: offline nie otrzymuje konsekwencji do powrotu online;
inicjator 80%, postronny 30%. Starszy dokument gameplay dopuszcza przerwanie
operacji wcześniejszego podejrzanego offline. Dla nowego wykonawcy obowiązuje
nowsza decyzja autora. Dokumenty historyczne nie są podstawą wyjątku.
Nie należy naliczać zaległych spotkań po zalogowaniu; proponowane jest nowe
sprawdzenie bieżącej obecności i odległości, bez automatycznej kary za offline.

Plany: [142 — MVP](../sprints/sprint_142_response_consequences_mvp.md),
[143 — ograniczenia i więzienia](../sprints/sprint_143_response_consequences_expansion.md).

## Uzupełnienie — kamery wykryte w scanie

Wymaganie autora: kamery pozostawione aktywne zwiększają ryzyko incydentu;
wyłączenie przynajmniej jednej z wykrytych kamer ogranicza lub niweluje
kamerowe źródło incydentu. Audyt nie potwierdza tego połączenia end to end.

### Scan i identyfikacja

`run.py` generuje m.in. 2–4 kamery wokół sklepu i kamerę bankomatu.
Generowane kamery dziedziczą `source_type` sklepu/ATM; menu w map_template
rozpoznaje je także po nazwie zawierającej „kamera”. Współrzędne są jitterowane,
brakuje tu trwałego identyfikatora kamery i jawnego powiązania z obserwowanym
obiektem. Kolejny scan może wygenerować inne położenie.

Scan zapisuje `scan_id` i markery przez `PlayerScanSnapshotStore` (maks. 512,
TTL 1 h). Nowy scan usuwa poprzedni snapshot tego gracza. Snapshot przechowuje
lokalizację/etykiety/typ, nie stan on/off i historię wyłączeń. Błąd zapisu
nie blokuje scanu. Obecny odczyt snapshotu służy m.in. territory defense;
nie ma go w kalkulatorze ryzyka ani inicjalizatorze incydentów.
Nie wolno więc używać tego TTL snapshotu jako jedynego trwałego dowodu
kamer dla już rozpoczętej operacji.

### Wyłączenie i dwa modele ryzyka

- Akcja `camera_shutdown` i operacja wsparcia istnieją; domyślny czas 15 min.
  `camera_shutdown_state_for_operation` określa offline/recovering i active.
- Stary `find_risk_modifiers` szuka shutdown w operacjach tego samego profilu,
  ze wspólnym oknem czasu, tym samym targetem albo odległością do 80 m.
  Wybiera jedną redukcję **18 punktów**, bez sumowania kolejnych kamer.
  Dotyczy tylko zdarzenia `camera_detected`, nie wszystkich rodzajów hakowania
  i nie samego shutdown. Wygaśnięcie/anulowanie usuwa ochronę.
- Publiczny `operation_risk_meter` liczy osobno base/time/tool/security/conflict/
  ability heat; próg incydentu to 60. Nie odczytuje `risk_state.support_effects`,
  wyłączeń kamer ani listy kamer ze scanu. `IncidentInitializer` korzysta z tego
  metera. Aktywna kamera w `target.security.camera=True` daje jedynie generyczne
  +4 security pressure; to nie powiązanie z rzeczywistym markerem scanu.
- Stara ścieżka profilowa wywołuje `ensure_camera_shutdown_state` i assessment.
  Dzisiejszy bounded worker używa `refresh_operation_runtime` osobno dla każdej
  operacji, bez budowy kamerowego kontekstu wsparcia innych operacji. Nie można
  przywrócić redukcji przez powrót workera do odczytów pełnego profilu.

### Reprodukcja i zakres potwierdzenia

`tests/test_camera_incident_audit.py`: aktywne wyłączenie obniża stary score
46 → 28, po timeout wraca 46. Ten sam aktywny shutdown nie zmienia publicznego
heat; dla operacji ponad progiem `IncidentInitializer` nadal zapisuje incydent.
Test dodatkowo rozróżnia generyczne +4 security od rzeczywistych kamer scanu.

```text
python -B tools/run_isolated_tests.py test_camera_incident_audit test_operation_risk_meter test_incident_initializer
20 testów PASS, w tym 3 nowe testy audytu
```

To lokalna reprodukcja rozłączenia modeli, nie produkcyjny test kliknięcia
wyłączenia kamery. Nie zmieniano balansu ani runtime. Wniosek: kamera jako
źródło incydentu wymaga naprawy w 142 przed naprawianiem samych skutków.

## Zamknięcie rozszerzonego audytu przed sprintami

### Mapa całej ścieżki i ustalone granice

| Etap | Sprawdzone call sites / źródło | Wynik i praca implementacyjna |
|---|---|---|
| Pierwszy scan | scan branch w run.py; position/identity/capability projections, active_scan_range_effect, PlayerScanSnapshotStore | Lekki odczyt pozycji/zasięgu istnieje. Kamery generowane bez trwałego powiązania stanu: dodać kontekst z 142.2 |
| Uprawnione shutdown | get_apps_for_map_action, hack_action: early_matched_apps/selected_app_id, create_operations_for_app_action | Sprawdzana zainstalowana aplikacja i deklaracja map_actions; legacy fallback konfigurowalny. Nie ma dowodu wyłączenia kamery konkretnego scanu ani atomowego recheck uprawnienia+camera state |
| Persist operacji | build_operation_instance → PlayerOperationStore.upsert_operations; filter_accepted_created_operations | Operacja trwała i aktywny duplikat blokowany. Nie utożsamiać zapisu operacji z zapisem globalnego on/off kamery |
| Ciężka ścieżka shutdown | hack_action dla celu nie-player: load_profile_readonly/sync_session_profile; set_player_aimed_target z persist_profile_projection | Nadal pełny odczyt, sesja i guarded write profilu. Cutover nie-player wymagany dla shutdown, bez powrotu do legacy assessment |
| Inicjacja / wygaszanie kamerą | apply_risk_modifiers vs calculate_operation_risk | Udowodnione rozłączenie -18 od metera; dodać jawny kamerowy składnik i jego wersję |
| Eskalacja | IncidentInitializer.sync_operations, _build_incident_from_refs | Heat sumowane do 100; poziomy 60/75/90, status escalated od 85. Recompute z części operacji może zgubić innego właściciela |
| Wygaśnięcie / offline | process_operation_runtime_tick, initializer, IncidentStore.list_public, build_blacknet_incident_facts | Worker niezależny od sesji, timeout operacji usuwa jej wkład; brak wkładów anuluje incydent. Public store nie filtruje czasu, BlackNet filtruje expires_at: rozbieżność |
| Mapa i NPC | publish_incident_actions → dispatcher → record_incident_delta / record_npc_capsule_delta | Oddzielne zapisy, dedupe per user/type/id/version, błędy delty przechwytywane. Delta skierowana do przekazanego username, nie do wszystkich obserwatorów; public snapshot jest recovery |
| BlackNet | build_blacknet_incident_facts → build_blacknet_world_signals | Działa publiczny fakt i CTA; nie ujawnia operation_ids/suspect_refs, ma punkt wejścia poza promieniem |
| Media narracyjne | territory_conflict_worker.process_blacknet_narrative_if_due → enqueue_blacknet_world_narrative_digest → BlackNetNarrativeProducer → Ollama task → NarrativePublicationService | Działa infrastruktura BlackNet/Googleplex News, źródła wersjonowane, lease/retry/dedupe i ochrona przed spóźnionym wynikiem. Selekcja ograniczona, nie każdy incydent automatycznie dostaje artykuł |
| Radio | BlackNetNarrativeProducer, ConsequenceExecutor._emit_hooks, ghostnetwork.narrative | Producer incydentu odrzuca medium radio. Stary hook dopisuje profile.radio_events; brak potwierdzonego consumer bridge do kanonicznego radia. Istniejący publisher radia dla GN nie stanowi tego mostka |
| Służby / konsekwencje | validator → policy → executor → wrapper | Luki pozycji/czasu/presence/30–80/atomowości potwierdzone w pierwszej części raportu |

Autoryzacja ogólnej akcji istnieje, ale nie jest certyfikacją całego shutdown:
sam get_apps_for_map_action sprawdza map_actions, nie relację kamera-scan ani
trwały camera_id. App target_types nie jest dowodem istnienia fizycznej kamery.
Potrzebny commit obejmujący wersję inventory, właściwy target i efekt shutdown.
Przypadki uninstalacji aplikacji w trakcie żądania mają być zamknięte testem
regresji nowej transakcji; nie zakładać gwarancji wyłącznie z preflight.

### Nowe reprodukcje, które zmieniają zakres napraw

`tests/test_incident_pipeline_audit.py` potwierdza:

1. Alice i Bob tworzą wspólny incydent; następny sync tylko Alice usuwa op Boba
   z operation_ids. Worker rzeczywiście wywołuje sync per gracz. Naprawa musi
   przeliczać pełny zbiór canonical wkładów danego incydentu, a nie pełne profile.
2. Timeout ostatniej operacji usuwa publiczny incydent bez sprawdzenia presence.
   To jawna sprzeczność z wymaganiem trwałego publicznego miejsca po wylogowaniu.
3. Po 3 h public store nadal zwraca aktywny rekord, ale BlackNet nie zwraca faktu
   przez expires_at. Nie wystarczy wydłużyć TTL jednej warstwy: wspólny lifecycle.
4. Realny incident → fact → signal daje intercepted_incident_alert; próba
   przekazania tego sygnału do radia jest odrzucona jako unsupported_target_medium.

Publikacja nie jest jednym atomowym workflow z aktualizacją incydentu. Błąd
między upsert i deltą może zostawić nowy stan bez eventu; lokalna invalidacja
cache BlackNet nie invaliduje pamięci innych procesów. W 142 potrzebny trwały
outbox/wersja oraz okresowe recovery, nie retry całej kary.

### Macierz reuse / adapt / replace

| Mechanizm | Decyzja | Warunek |
|---|---|---|
| position/identity/capability, canonical inventory/wallet/operations | Reuse | Odczyty po kluczu, bez profile overlay; wspólne conn przy karze |
| PlayerScanSnapshotStore | Adapt | Trwała referencja ekspozycji poza wymienianym/TTL snapshotem |
| get_apps_for_map_action / normalizacja kontraktu | Reuse + adapt | Serwerowy target i ponowny entitlement check przy commit |
| calculate_operation_risk / update_operation_risk_meter | Adapt | Jawny kontekst kamer, bez dostępu kalkulatora do DB |
| IncidentInitializer | Adapt | Wkłady per incydent, własny lifecycle niezależny od sesji/końca operacji |
| public payload, safe CTA, BlackNet facts/signals | Reuse + adapt | Spójna wersja i expiry z canonical lifecycle, limit odczytu |
| producer + publication leases/receipts/active head | Reuse | Dodać mostek incydent→radio, nie klonować kolejki publikacji |
| GN ability windows + active_operation_risk_rules | Reuse | Aktywne i kwalifikowane okno, pobrane raz na gracza/tick |
| Judgment / konsekwencje modyfikujące słownik profilu | Replace boundary | Mały canonical store i wspólny commit; można zachować czyste formuły |
| prison_catalog | Reuse w 143 | ID jako klucz, współrzędne osadzenia, osobna reguła zwolnienia |

Nie ma uzasadnienia do klonowania całego podsystemu. GN ma gotowe trwałe
okna, cooldown i dedupe aktywacji; utrata części kończy efekt. Cztery istniejące
policies operation_risk (false_image, narrative_takeover, phantom_node,
trust_corridor) zwracają -15 heat; calculator ogranicza ability modifier do
[-25,25]. To współczynnik ryzyka, nie gotowa tabela kar ani skrócenie wyroku.
Nowe sankcje wymagają własnej policy, korzystającej z zatwierdzonych wejść;
nie wolno automatycznie stosować -15 jako procentu redukcji kary.

### Koszt i deterministyczność przed implementacją

Potwierdzone statycznie ciężkie call sites: nie-player hack_action oraz
executor; opisane wcześniej pełne odczyty, write i session.profile muszą zniknąć.
Potwierdzona strukturalnie nieograniczona praca: list_active/list_public
pobierają wszystkie incydenty, initializer skanuje je wielokrotnie per batch
gracza. Limit 4 użytkowników ticka nie ogranicza tej liczby incydentów.
Scheduler narracji domyślnie działa co 900 s (minimum 300 s), wybiera źródła
z max. 20 sygnałów; realny czas ukazania artykułu zależy też od kolejki/modelu.
Nie obiecywać natychmiastowej publikacji na podstawie samej delty mapy.

Testy istniejących lekkich workerów i GN potwierdzają zero heavy I/O dla ich
zakresów. Nie przenosić tego wyniku na ciężki endpoint shutdown. p95 produkcji
nie zmierzono: brak sesji pomiarowej na serwerze. To ograniczenie pomiarowe,
nie niewiadoma co do występowania pełnych odczytów w wskazanym kodzie.

### Walidacja rozszerzenia

```text
python -B tools/run_isolated_tests.py test_blacknet_incident_bridge test_public_incident_map test_ghostnetwork_ability_realizers test_ghostnetwork_ability_canonical_stores test_narrative_publications test_hack_action_idempotency
84 testy PASS
python -B tools/run_isolated_tests.py test_incident_pipeline_audit test_ghostnetwork_ability_windows
10 testów PASS
```

Dodatkowe 94 testy obejmują istniejące komponenty oraz cztery reprodukcje luk.
Nie jest to zielony test całej ścieżki: połączenia camera→heat i incident→radio
nie istnieją w wymaganej postaci, a więc kryterium end-to-end jest dziś FAIL
z ustaloną przyczyną. Implementacja ma naprawić opisane granice, a nie dopiero
szukać, czy istnieją. Testy nowych zachowań pozostają kryteriami odbioru 142.

## Bramka rozpoczęcia sprintów

Audyt techniczny rozszerzonego zakresu: GOTOWY jako wejście do planowania
i implementacji napraw. Stan produktu: NIEGOTOWY do produkcyjnego odbioru.
Nie zmieniano runtime ani danych produkcyjnych. Wiedza z kodu i testów nie
jest gwarancją braku wszystkich przyszłych usterek.

Przed implementacją polityk należy zamknąć decyzje autora, nie odkrycia kodu:
lokalność/siła ochrony kamer i wpływ na już aktywny incydent, reguła zamknięcia
incydentu niezależna od offline, nowe spotkanie vs retry, kara postronnego,
progi/okno recydywy i dokładna tabela wyroków/ograniczeń. Propozycje w sprintach
nie są zatwierdzonym balansem. 142 nie rozpoczyna się kolejnym ogólnym audytem.
