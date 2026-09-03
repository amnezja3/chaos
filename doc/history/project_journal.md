# CHAOS — Project Journal

## 2026-08-24 - Sprint 130.11: recovery v2 gotowe do serwerowego dry-run

- Live geometry audit potwierdził przyczynę `A+B`: dziewięć historycznych
  stationary targets reaktywuje przy LVL 25+ dwa kolidujące obszary, natomiast
  bonus-only Tokio ze starego planu jest czyste.
- Recovery v2 kończy lifecycle dokładnie dziewięciu canonical captured rows;
  ownership registry jest jawnie podpisany jako `present` albo `absent` i jest
  usuwany wyłącznie w wariancie present. Worker geometry czyta stationary
  `captured_targets`, nie ownership registry. Durable retirement receipt zapisuje
  captured row ID/SHA oraz explicit ownership state. `Kuriero-bot`, inventory
  11/11, pozostały ownership, obcy current world i GhostNetwork pozostają poza
  write scope.
- Planner rozdziela historical, bonus-only i combined-final preview. Plan v1
  może dostarczyć wyłącznie współrzędne bonusu; apply wymaga nowego planu v2.
- Pipeline jest resumable/exactly-once i ma dwie jawne bramki workera.
  Current-world drift kończy się `CURRENT_WORLD_CHANGED_REPLAN_REQUIRED`, a
  rollback jest ograniczony do recovery-owned danych przed `COMPLETE`.
- Testy: recovery/geometry `34/34 OK`, szeroka regresja sąsiednich kontraktów
  `491/491 OK`; ponowiona regresja territory po optional-ownership
  `391/391 OK`. Nie wykonano deployu, apply ani mutacji produkcyjnej bazy.
- Status: `READY FOR SERVER READ-ONLY PLAN V2 / DRY-RUN`.

### Phase-aware resume istniejącego Recovery v2

- Produkcyjny apply-03 błędnie uruchamiał ponownie pre-bonus empty-geometry
  check po poprawnym finalnym rebuildzie `8 Tokio targets / 1 area`.
- Retirement verification jest teraz scope-aware. Trwały milestone pozwala na
  późniejszą recovery-owned geometrię, nadal blokując reaktywację któregokolwiek
  z dziewięciu historycznych targetów lub naruszenie audit receipts.
- Final geometry jest weryfikowana osobno: exact 8 IDs, complete job, 1 area,
  zero recovery conflicts i zgodność geometry contract. Gameplay drift blokuje
  settlement przed wallet/profile write.
- Test `apply-01 → rebuild 0 → apply-02 → rebuild 1 → apply-03` przechodzi i
  tworzy dokładnie jeden settlement receipt. Recovery/geometry: `37/37 OK`.
- Istniejący plan i receipt są wznawialne; nie potrzeba rollbacku ani replanowania.

## 2026-08-22 - Sprint 130.10: blocker mapy po account switch

- Manual przerwano po selektywnym `500` z `/api/map/player-actors` i braku menu
  pustego pola nad terytoriami. Evidence:
  `logs/sprint-130-10-monitor-20260822T090144Z-1542232.log`.
- Traceback potwierdził legacy profil z tekstowym `fraction`; projekcja aktora
  zakładała obiekt i wywoływała `.get("role")`, przez co jeden widoczny aktor
  przerywał cały snapshot. Oczekiwane `409` opóźnionych requestów po logout
  pozostały oddzielnym, poprawnym efektem unieważnienia lineage.
- Wprowadzono read-only normalizację obu reprezentacji `fraction` dla klanu,
  profesji, pełnego snapshotu i delty aktora. Nie wykonano migracji ani zapisu
  profili.
- Polygony pól, konfliktów, frontów i multi-conflictów nie polegają już wyłącznie
  na niejednolitym bubbling `contextmenu` Leaflet. Jawnie przekazują zdarzenie do
  zwykłego menu pustego pola; interaktywne markery zachowują własne menu.
- Pierwszy retest potwierdził brak `500` i kompletne renderowanie aktorów, ale
  ujawnił przejmowanie menu pola przez captured/legacy marker. Handlery targetów
  wymagają teraz trafienia w ograniczony, projektowany hitbox ikony; event spoza
  ikony wraca do menu pustego pola.
- Historyczne `/static/images/default_avatar.png` jest w rendererze mapy
  kierowane do istniejącego `avatar-default.jpg`, bez zmiany profilu.
- Regresja map cutover: `31/31 OK`; Target Registry/session isolation/read path:
  `253/253 OK`. Nie wykonano deployu, commita ani repair konta `Trollu2`.
- Captured menu/map loader/GN layer: `78/78 OK`; behawioralny test Node hitboxu:
  OK; Target Registry/persistence: `221/221 OK`.
- Końcowy retest serwerowy potwierdził poprawne menu pustego pola i markerów,
  aktorów po zmianach kont oraz części GhostNetwork na wszystkich testowanych
  kontach. Bramka mapy ma status `MAP BLOCKER RETEST PASSED`; właściwy manual
  130.10 jest ponownie odblokowany, bez przedwczesnego werdyktu GO.

## 2026-08-22 - Sprint 130.10: blocker `/desktop` po manualnym account switch

- Monitor manuala zarejestrował cztery `GET /desktop` zakończone `500`, zero
  desktopów `200` i cztery identyczne błędy serializacji niezdefiniowanego
  `session_generation` w `linux.html`.
- Audyt całego repo potwierdził jeden endpoint `/desktop` i jeden render
  `linux.html`; nie istnieje alternatywna ścieżka renderująca template bez
  kontekstu.
- Niezgodność numeru/treści linii tracebacku oraz niezmienny PID i licznik
  restartów PM2 potwierdziły mixed deploy state: Gunicorn wykonywał starszy
  code object, gdy nowy template był już na dysku. Disposition:
  `CONFIRMED STALE WEB PROCESS / MIXED DEPLOY STATE`.
- `/desktop` inicjalizuje teraz kontekst jawnie przez kanoniczny
  `session_generation_client_context()` przed renderem. Nie dodano fallbacku w
  Jinja.
- Dodano regresję pełnego A → desktop → logout → B → desktop → logout → A →
  desktop oraz świeżej rejestracji → desktop. Testy korzystają wyłącznie z
  izolowanego session-generation store i mocków profilu; `Trollu2` nie został
  odczytany, zmieniony ani naprawiany.
- Po pełnym restarcie ujawniono pre-rollout cookie z `user`, ale bez trwałego
  lineage/generation. `POST /` kończył się
  `generation_bootstrap_required` przed uwierzytelnieniem.
- Niepełna legacy sesja jest teraz unieważniana i ma obracany SID przed
  credentialed login/register; kompletna sesja nadal nie może zmienić konta bez
  poprawnej generation i logoutu.
- Finalna regresja session store/precommit/isolation i desktop boot: `52/52
  OK`; celowany `py_compile` oraz `git diff --check`: OK.

## 2026-08-21 - Sprint 130.10: lokalny hardening gotowy do manualnej bramki

- Evidence `logs/chaos-13010-trolu2-20260821T184643Z.tar.gz` dla canonical
  loginu `trolu2` przeszło SHA-256 i SQLite `quick_check`; profil jest
  reset-like przy zachowanych dojrzałych durable stores.
- Utrzymano disposition `CONFIRMED CODE DEFECT` oraz korelację
  `STRONGLY CONSISTENT / HIGH CONFIDENCE`. Brak historycznego LKG i telemetryki
  konkretnego full-write wyklucza deklarację absolutnej atrybucji.
- Lokalnie wdrożono guarded profile CAS/LKG/checksum/validation, kanoniczny
  fail-closed wallet i inventory z idempotencją, generation/precommit i
  frontend teardown sesji, retry-safe reward sagę GN oraz bounded CAS retry dla
  worker-owned territory projections. Usunięto też NameError w clear aimed
  target.
- Testy celowane przeszły: Target Registry/persistence `221/221`, wallet
  `30/30`, GhostNetwork `26/26`, territory projection CAS `3/3`. Pełna regresja
  zakończyła się wynikiem `956/956 OK`; sześć kontraktów JS oraz pięć
  kontroli składni Node również przeszło.
- Nie wykonano manuala A → B → A, testu dwóch kart, dwóch niezależnych sesji
  ani ścieżki gameplay trzeciego filaru. Nie wykonano też commita, deployu,
  restartu, mutacji ani repair konta `trolu2`; recovery pozostaje Sprintem
  130.11 po GO 130.10.
- Status: `READY FOR MANUAL ACCOUNT-SWITCH TEST — Sprint 130.10`. To nie jest
  werdykt GO.

## 2026-08-21 - Sprint 130.10: FORENSICS CAPTURED i start hardeningu runtime

- Exact canonical login w serwerowej bazie to `trolu2`; zredagowany capture
  przeszedł SHA-256, wszystkie probe wykonały się technicznie, a SQLite
  `quick_check` zwrócił `ok`.
- Bieżący profil jest strukturalnie valid, ale reset-like (`LVL 2`, `HC 1000`,
  `EXP 0.0`, `RSP 25`). Durable stores potwierdzają dojrzałe konto: 60 capture
  receipts, 113 wallet ledger events, 578 operacji, 1000 delt, 1393 system
  messages, zakupy i zachowane inventory.
- Potwierdzono dwa exactly-once łańcuchy
  `ghost.part_activated -> part_first_activated/applied`. Ostatni z nich jest
  czasowo zgodny z publication/progression/territory job przed późniejszym
  zapisem reset-like profilu.
- Disposition: `CONFIRMED CODE DEFECT`; korelacja incydentu
  `STRONGLY CONSISTENT / HIGH CONFIDENCE`. Brak pre-incident LKG i telemetryki
  konkretnego full write pozostaje luką, dlatego nie deklarujemy absolutnego
  historycznego dowodu pojedynczego zapisu.
- Ogłoszono `FORENSICS CAPTURED — Sprint 130.10` i odblokowano Etap 2.
  Nie wykonano repair konta, deployu ani restartu.

## 2026-08-21 - Sprint 130.10 Etap 1: writer audit i read-only evidence gate

- Audyt ścieżki trzeciego filaru potwierdził deterministyczny destructive-write:
  `ghost.part_activated` może naliczyć first activation reward na sparse
  projection z `list_profile_identities()`, a następnie zapisać ją przez pełny
  `UserStore.save_profile()`. Późniejszy template sync uzupełnia brakujące pola
  wartościami starter-like.
- Defekt kodu ma status `CONFIRMED CODE DEFECT`; przypisanie go do incydentu
  `Trollu2` pozostaje `PENDING SERVER CORRELATION` do zredagowanego odczytu
  activation/reward timeline, `users.updated_at` i durable stores.
- Zinwentaryzowano full/patch-to-full/direct writers, hybrydowy wallet,
  compatibility mirrory, nieliczne istniejące CAS oraz brak profile revision,
  LKG i session generation. Osobno potwierdzono brak izolacji epoki logowania i
  nieautoryzowany zakres `/api/users/delete`.
- Dodano read-only `tools/audit_profile_integrity.py`. Narzędzie korzysta z
  SQLite `mode=ro`, `PRAGMA query_only=ON` i jednej transakcji odczytowej; nie
  importuje runtime ani nie uruchamia template/mirror/reconcile. Raport redaguje
  login, credentials, pełny profile JSON, współrzędne i topologię.
- Dodano regresję narzędzia oraz artefakty
  `doc/audits/profile_integrity_writer_inventory.md` i
  `doc/runbooks/profile_integrity_recovery_runbook.md`.
- Nie zmieniono runtime, nie wykonano repair, migracji, deployu ani restartu.
  Etap 2 czeka na dane serwerowe.
- Status: `READY FOR READ-ONLY SERVER FORENSICS — Sprint 130.10`.

## 2026-08-21 - Incydent Trollu2 i bramka 130.10–130.11 przed Sprintem 131

- Przefiltrowano załącznik konsoli bez przenoszenia nazw i współrzędnych innych
  graczy. Potwierdza on jeden defect renderera połączeń GN: dwa błędy live delta
  i jeden snapshot w `Bounds.intersects → Polyline._clipPoints`. Sześć refreshy
  actor API zakończyło się HTTP 200 dla 9 aktorów w około 3,85–5,00 s.
- Załącznik nie zawiera requestu profilu, błędu sesji, `401/403/500`, event ID
  lifecycle ani logu SFX, więc nie łączy renderera przyczynowo z utratą profilu.
- Audyt kodu wskazał P0 do weryfikacji: zacieranie `JSONDecodeError` do `{}`;
  automatyczny template sync dla niepełnego profilu; pełne last-write-wins bez
  ogólnego CAS/LKG; możliwość wtórnego obniżenia walletu z profile fallback.
  Wallet ma też legacy transfery zapisujące pełne profile, więc przed
  odwróceniem mirroru wymaga jednej granicy wszystkich writerów. Osobny
  inventory store wyjaśnia, dlaczego apps/tools mogły przetrwać.
- Rozpisano `Sprint 130.10 — Profile Integrity and Cross-Account Session
  Isolation`: forensics, write guard, revision/CAS, last-known-good,
  jednokierunkowe mirrory oraz unikalna generation i teardown sesji A/B.
- Rozpisano zależny `Sprint 130.11 — Trollu2 Controlled Profile and Territory
  Recovery`: exact-user audit, podpisany dry-run, idempotentny apply/receipt,
  before-manifest/rollback, LVL 50, RSP 2560, 250000 HC i terytoria przez
  atomowy recovery grant oraz istniejący worker.
- `exp` pozostaje projekcją powierzchni i ma zostać przeliczony
  progression-neutralnie po rebuildzie; nie będzie ustawiany surowo na 2560.
  Na aktywnym serwerze GN może zmienić się przez innych testerów, więc verify
  wymaga zero repair-sourced GN writes i valid 20-part runtime, nie globalnie
  identycznego event count.
- Numery 130.10 i 130.11 wybrano, ponieważ historyczne 130.9.6–130.9.12 są już
  zajęte. Sprint 131 jest formalnie zablokowany do GO obu bramek.
- Zmiana jest wyłącznie dokumentacyjna. Nie wykonano repair, commita, deployu
  ani mutacji danych serwerowych.

## 2026-08-21 - Post-audit Sprintów 131–138

- Zweryfikowano plan względem runtime po 130.9.5. Wykryto istniejące elementy,
  których nie wolno dublować: `view=suite`, visibility v2, delta/publication
  bridge, map renderer, `GhostNarrativePublisher` i `ghost_narrative_outbox`.
- Skorygowano map/teleport contract: desktop używa `createMap()` oraz
  `notifyOpenMapsBlacknetFocus`; GN wymaga opaque target i ponownej projekcji
  backendowej, ponieważ obecny teleport przyjmuje współrzędne klienta.
- Skorygowano delta plan: klient istnieje w pliku mapy i musi zostać wydzielony
  do lekkiego modułu przed Suite, aby nie ładować Leaflet bez żądania.
- Skorygowano 136–138: 136 rozszerza Sprint 129; 137 tworzy pierwszy realny
  worker Ollamy nad GN outboxem; 138 rozszerza istniejący feed BlackNet.
- Wiążący artefakt: `doc/sprints/sprint_131_plus_post_audit.md`. Sprinty 131–138 są
  gotowe do realizacji w kolejności, bez rozpoczęcia implementacji 131.

## 2026-08-21 - DONE Sprint 130.9.5 Spatial Separation

- Dodano atomowy limit `50 km` dla nowych GhostNetwork reservations. Check
  maksymalnie 20 anchorów i zapis `reserved` wykonuje ta sama transakcja
  repository; concurrency test potwierdza dokładnie jednego zwycięzcę dla
  dwóch targetów oddalonych o `20 km`.
- Wykorzystano wspólny `Haversine.haversine_distance`; konfiguracja to
  `CHAOS_GHOSTNETWORK_MIN_PART_DISTANCE_KM=50`.
- `reserved` kotwiczy lokalizację w `ghost_parts`, a release/expiry ją zwalnia.
  Discovery zachowuje pierwotny anchor. Odrzucenie wygląda dla klienta jak
  `roll_missed`, a agregat techniczny zapisuje wyłącznie `part_too_close`.
- Testy: spatial `8/8`, reservation/discovery/runtime `19/19`, pełny GN
  `193/193`, integracja `/gonna-win`/receipts/map `12/12`; py_compile i
  `git diff --check` — OK.
- Nie wykonano commit ani deploy.

## 2026-08-21 - Sprint 130.9.4 manual finding: classified marker

- Manual potwierdził indywidualne PNG dla części PUBLIC, ale projekcje
  `foreign_blocked` i `foreign_active` nadal wpadały w geometryczny kwadrat.
- Projekcje z prawem do tożsamości (`full_owner` / `full_clan`) nadal używają
  jednego z 20 PNG. Projekcje niejawne dostały neutralny asset
  `static/images/ghostnetwork/parts/classified_part.png`,
  który nie ujawnia kodu części ani topologii; badge terytorialny zachowuje
  przy tym efekt CSS stanu BLOCKED/ACTIVE.
- Test renderera JS i `git diff --check`: OK. Python regression wymaga
  powtórzenia w środowisku projektu (interpreter nie jest dostępny w tej sesji).
- Status: `READY FOR MANUAL GAMEPLAY RETEST — Sprint 130.9.4`.

## 2026-08-21 - Sprint 130.9.4 Etap 2: PNG Renderer

- Zweryfikowano `20/20` PNG: poprawne nazwy, `128×128`, RGBA/alpha i niezerowy
  rozmiar. Projekcja v2 nie ujawnia URL-u assetu przy ukrytej tożsamości.
- Marker używa indywidualnego PNG, zachowuje geometryczny fallback, click/popup,
  pane 625 i aktualizację in-place; rozmiar to 54 px desktop / 48 px mobile.
- Lifecycle wykorzystuje lekkie animacje CSS bez timerów per marker. Jednorazowe
  containment/activation transitions uruchamia tylko live delta, nie snapshot.
- Regresja GN/map/conflict `124/124`, renderer JS, syntax i py_compile — OK.
- Status: `READY FOR MANUAL GAMEPLAY TEST — Sprint 130.9.4`.

## 2026-08-21 - Sprint 130.9.4 Etap 1: Part Asset Contract

- Kanoniczny katalog potwierdził 20 unikalnych części, po pięć dla czterech
  maszyn; wymagane jest 20 indywidualnych PNG, nie jeden obraz per machine.
- Dodano read-only `tools/export_ghostnetwork_part_assets.py`, który łączy
  katalog z realnym `cycle_id/part_id` bez mutowania cyklu.
- Kontrakt: PNG RGBA `128×128`, safe area `108×108`, katalog
  `static/images/ghostnetwork/parts/`, bez wypalonych wariantów lifecycle.
- Eksporter i katalog: `15/15 OK`; pełna lista nazw i kierunek wizualny są w
  artefakcie sprintu oraz README katalogu assetów.
- Status: `READY FOR ASSET DELIVERY — Sprint 130.9.4`.

## 2026-08-21 - GO Sprintu 130.9.3 Territory Visual States

- Końcowy manual potwierdził prawidłowy efekt ACTIVE/HOSTILE i zachowanie
  ownership presentation.
- Retest potwierdził blokadę `scan → mark → aim → hack` zwykłego obiektu na
  terytorium wrogiego klanu oraz zachowanie kanonicznej ścieżki konfliktowej.
- Stare oznaczenia multi-conflict znikają po przebudowie; canonical snapshots
  pozostają jedynym źródłem markerów MC.
- Werdykt: `GO — Sprint 130.9.3 GhostNetwork Territory Visual States validated in gameplay`.

## 2026-08-21 - Sprint 130.9.3 manual blockers: enemy gate i MC cleanup

- Wspólna polityka serwerowa blokuje `scan`, `mark_target`, `aim` i hack
  zwykłego/vulnerability obiektu na terytorium wrogiego klanu; wyjątkiem jest
  wyłącznie kanoniczny cel aktywnego konfliktu. Ten sam klan pozostaje chroniony.
- Snapshot mode nie wysyła już równoległych legacy `contested_targets`; markery
  MC mają jedno źródło w canonical conflict snapshots i znikają przy rebuildzie.
- Regresja: action gate/aim/hack `42/42`, conflict/context `41/41`, wcześniejszy
  zestaw conflict `74/74`, `py_compile` i renderer JS — OK.
- Status pozostaje `READY FOR MANUAL GAMEPLAY TEST — Sprint 130.9.3` do krótkiego
  retestu dwóch zgłoszonych scenariuszy.

## 2026-08-21 - Sprint 130.9.3 Etap 1–2: Territory Visual States

- Kanoniczne `module_state` i `territory_id` wystarczają do prezentacji:
  `active` daje zielony pulse/glow, a `blocked` czerwony alarmowy stan HOSTILE.
- Efekt dekoruje istniejący polygon Leaflet bez tworzenia dodatkowych warstw i
  bez zastępowania ownership fill; dla wielu części obowiązuje `hostile > active`.
- Snapshot, delta, cleanup i territory rebuild używają jednego rejestru. Przy
  okazji zawężono router connection delta, aby part projection nie była błędnie
  przechwytywana jako połączenie.
- Regresja: kontrakt map/delta `37/37`, szerszy GN/territory/conflict/Target
  Registry `178/178`, renderer JS i syntax check — OK.
- Brak nowych assetów. Status: `READY FOR MANUAL GAMEPLAY TEST — Sprint 130.9.3`.

## 2026-08-21 - Formalne GO Sprintu 130.9.2 GhostNetwork SFX

- Usunięto nieaktualny status `READY FOR ASSET DELIVERY`: wszystkie osiem
  finalnych MP3 istnieje, jest niepustych, ma nagłówek ID3 i poprawne wpisy w
  `manifest.v1.json`.
- Końcowa regresja SFX, delta publication/audience, lifecycle, module state,
  territory jobs i map layer zakończyła się wynikiem `58/58 OK`; wspólny player
  JS oraz kontrola składni `terminal.js` również przeszły.
- Manual serwerowy pozostaje dowodem dokładnie jednego live SFX containment;
  visibility/dedupe są zachowane, a snapshot/recovery nie odtwarzają audio.
- Werdykt: `GO — Sprint 130.9.2 GhostNetwork SFX validated in live gameplay`.

## 2026-08-20 - GO 130.9.2.fix.all.1 i domknięcie Sprintu 130.9.2

- Finalny pomiar serwerowy objął 13 nowych jobów GN: `failures=0`, `busy=0`,
  brak `database_contended`, `OperationalError`, tracebacków i restartów.
- Kolejka po chwilowym backlogu wróciła do `depth=0`; jedno zadanie `areas`
  zostało poprawnie coalescowane.
- GN job p95 spadło z około 8.2 s do 3.86 s, max z około 19.2 s do 3.86 s,
  a `events_rewards` p95 z 7.295 s do 1.710 s.
- Repozytoryjna transakcja rewards miała p95/max 138 ms. Worker pozostał online,
  a zwykłe contention nie spowodowało awarii procesu.
- Manual wcześniej potwierdził stabilny lifecycle części i dokładnie jeden live
  SFX containment; snapshot/recovery nie odtwarza historycznego SFX.
- Hot sprint performance zostaje zamknięty bez kolejnej rundy optymalizacji.
  `130.9.2.fix.all.1`: GO, Sprint 130.9.2: DONE; 130.9.3 i 130.9.4 odblokowane.

## 2026-08-19 - P2 blockers: canonical layer cleanup i GN profile identity

- Pełny player-areas snapshot usuwał legacy arrays, ale nie canonical front,
  pillar i engagement registries. Zmienione ID publikacji zostawiały stare
  Leaflet layers i wizualnie wyglądały jak worker rebuild loop.
- Snapshot usuwa teraz wszystkie canonical conflict layers przed renderem
  autorytatywnego kompletu. Audyt workera nie wykazał bezwarunkowego self-enqueue;
  no-op kończy rebuild, a multi audit pozostaje leased i okresowy.
- GN territory publication kluczowała profile przez `profile_json.username`.
  Profile bez zduplikowanego loginu były pomijane mimo kanonicznej kolumny
  `users.username`, więc właściwy clan nie powodował lifecycle ani SFX.
- Publication i engagement audience używają teraz `list_profile_entries()`.
- Regresja GN 178/178 oraz conflict/engagement/abandon 48/48 — OK.

## 2026-08-19 - P2 blocker: porzucenie zwykłego filaru bez rebuild joba

- Reload, logout i restart nie mogły naprawić starego polygonu, ponieważ read
  path prawidłowo nie wykonuje już mutującego rebuilda.
- Abandon job ID zależało od owner/target/version. Zwykły target bez ownership
  CAS ma version 0, więc ponowne capture→abandon tego samego targetu kolidowało
  ze starym complete jobem. Delete był commitowany, ale `ON CONFLICT DO NOTHING`
  nie tworzyło nowej pracy dla workera.
- Job ID zawiera teraz ID konkretnego rekordu capture; kolizja rollbackuje całą
  transakcję zamiast pozostawić osieroconą geometrię.
- `repair_territory_visibility.py --enqueue` umożliwia jednorazowe odtworzenie
  brakującego worker-owned rebuilda dla już usuniętego targetu.
- Regresja abandon/publication 44/44 i target/territory/worker 247/247 — OK.

## 2026-08-19 - P2 manual finding: polygon publication recovery

- Manual potwierdził live `ghost.part_contained` i poprawny SFX, ale polygon po
  capture/consolidation pozostawał stary do ponownego otwarcia mapy.
- Root cause: `territory.updated` jest celowo kompaktowe i nie zawiera vertices,
  natomiast klient dla istniejącego area ID aktualizował tylko styl/tooltip.
  Snapshot recovery obejmowało abandon/encirclement, ale nie `pillar_captured`
  ani `conflict_consolidation`.
- Każda finalna area publication uruchamia teraz jeden debounced, read-only
  snapshot polygonów. Skipped/in-flight/abort ma bounded retry 0.9/1.8/3.5 s.
- Regresja: capture/territory/map 247/247, GhostNetwork 177/177 oraz kontrakty
  publication/recovery 40/40 — OK. Manual P2 wymaga powtórzenia bez resetu cyklu.

## 2026-08-19 - P2 DONE lokalnie: stabilny renderer GhostNetwork

- Renderer odrzuca niepełny i starszy snapshot przed zmianą warstwy, dzięki
  czemu timeout, niepełny payload ani wyścig z nowszą deltą nie usuwa ostatniego
  poprawnego stanu mapy.
- Recovery jest coalescowane do jednego requestu; brak projekcji nie uruchamia
  już dwóch równoległych recovery.
- Pending territory badge registry jest ograniczone do 20 części i czyszczone
  przy usunięciu markera; zmiana cyklu resetuje dedupe poprzedniego cyklu.
- Nie dodano pollera, timera per marker, nowego SFX ani dłuższego timeoutu.
- Regresja: GhostNetwork 177/177, SFX/territory/worker 34/34, behawioralny test
  JS renderera i GameSfx — OK. P2 czeka na manualną bramkę serwerową.

## 2026-08-19 - P1 potwierdzone na serwerze przy dwóch graczach

- Po wdrożeniu `984ba0f` dwóch graczy otwierało mapę jednocześnie w około 10 s;
  wcześniejsza regresja 2–5 minut nie wystąpiła.
- `/map` zmniejszył się z 36.1 MB do około 399 KB i odpowiadał w 0.1–1.5 s.
  Osobny target snapshot odpowiadał zwykle w 0.16–0.94 s; jeden pomiar ciężkiego
  profilu wyniósł 5.43 s, ale nie zablokował równoległego otwarcia mapy.
- GN snapshot odpowiadał w 0.27–0.93 s, operations w 0.35–2.50 s, a clan
  vulnerabilities w 0.20–1.01 s. Nie odnotowano timeoutu ani SQLite locked/busy.
- Wcześniejsza kontrola potwierdziła puste kolejki GN i brak failed jobs.
  Manualna bramka wydajności P1 jest zaliczona; P0 i P1 mają status DONE.
- Pozostają nieblokujące kandydaty do dalszej optymalizacji: player actors
  2.96–5.72 s i pojedynczy pusty system-message poll 2.45 s.

## 2026-08-19 - Concurrent map server finding i payload/lock fix

- Dwa równoczesne otwarcia mapy trwały około 5 minut; ciężki profil solo około
  2 minut. GN queues były puste, GN snapshot <2 s i nie było SQLite locked/busy.
- `/map` dla `main` miał 36.9 MB wobec 4.7 MB dla `run`; system-message empty
  polls trwały 11–35 s, clan vulnerabilities 7–23 s, actors 3–5 s.
- Targety nie są już generowane jako Folium HTML ani ponownie osadzane w pełnym
  profileData. Ładuje je lekki `/api/map/target-snapshot`.
- Pusty system-message poll nie bierze BEGIN IMMEDIATE i nie czyta pełnego
  profilu; clan vulnerability nie uruchamia runtime overlays/profile writes.
- Player actors używa jednego bulk query pending contacts zamiast N+1.
- Test 500 ciężkich targetów potwierdza stały rozmiar dokumentu mapy. Lokalna
  regresja target persistence 221/221 oraz polling/territory 59/59 — OK.
- Historyczny wynik NO-GO został zamknięty ponownym testem dwóch graczy po
  wdrożeniu `984ba0f`; wynik bramki opisano powyżej.

## 2026-08-19 - Start implementacji Sprintu 130.9.2.fix.all.1

- Odłączono globalny GN territory reconcile, reward/endgame i fan-out od
  synchronicznych ścieżek publikacji webowej.
- Dodano durable `ghostnetwork_territory_jobs` z idempotentnym kluczem źródła,
  lease, retry limit oraz terminalnym `failed`; konsumentem jest istniejący
  `chaos-territory-worker`.
- Conflict job nie przenosi kopii geometrii: worker ponownie pobiera kanoniczny
  snapshot po `conflict_id` i dopiero wtedy uruchamia bridge.
- `sync_session_profile` domyślnie nie przebudowuje już terytoriów. Jawne mutacje
  nadal używają `rebuild_player_areas_with_territory_delta`.
- Zbiorczy odczyt profili zastąpił N połączeń SQLite w publikacji territory GN.
- Operator `status/verify/reconcile/drain` pokazuje teraz liczność kolejki;
  `verify` zgłasza blocker dla terminalnych jobów `failed`.
- Regresja lokalna: GhostNetwork 161/161, territory 121/121, pakiet granicy
  worker/request i boot/delta 24/24 oraz `test_target_persistence` 221/221 —
  wszystko OK. Sprint pozostaje IN PROGRESS
  do pomiarów serwerowych i kontrolowanego drainu; bez deployu i bez commita.

## 2026-08-19 - Stability Recovery: bounded worker i canonical publication

- Dodano retry backoff, limit pięciu prób i terminalny `failed`; diagnostyka
  kolejki zawiera depth, oldest age oraz processing p50/p95/max.
- Scheduler territory workera naprzemiennie obsługuje GN i conflict candidates,
  dzięki czemu nawet długi backlog GN nie blokuje konfliktów.
- Geometria ma teraz monotoniczną publication version per owner. Identyczny
  rebuild zachowuje rekordy/ID i nie powoduje SQLite churn ani fałszywego joba.
- Encirclement zapisuje tylko realną zmianę statusu i podbija wersję dokładnie
  raz; profile ownerów/intruderów w player-areas są czytane zbiorczo zamiast N+1.
- Read-path test potwierdza brak territory rebuild i GN bridge w domyślnym
  profile sync oraz snapshot endpoint; rozszerzono timing krytycznych endpointów.
- Rozdzielono komendy operatorskie na `capture-reconcile`,
  `reward-history-reconcile` i `territory-reconcile`.
- Regresja: GhostNetwork 168/168, territory 123/123, target persistence 221/221.
  Bez commita i bez deployu; nadal potrzebny serwerowy baseline/p95.

## 2026-08-19 - P1 DONE lokalnie: durable GN delta delivery

- Territory lifecycle nie publikuje już synchronicznie delty do wszystkich
  kont. Zapisuje idempotentny delivery job konsumowany przez istniejącego
  territory workera; nie powstał osobny worker ani fan-out SFX.
- Delivery ma bounded cursor batch, lease, backoff, limit prób i per-user
  dedupe. Retry nie ponawia lifecycle ani reward.
- Jeden event przechowuje server-side snapshot i wykorzystuje go we wszystkich
  batchach, więc wykonuje maksymalnie jeden internal snapshot read.
- Scheduler zapewnia fairness delivery/territory/conflict. Status i verify
  pokazują delivery backlog oraz failed jobs.
- Startup nie skanuje historii eventów: odzyskuje tylko pending delivery jobs,
  dlatego snapshot/recovery nie odtwarza historycznych SFX.
- Końcowa regresja P1: GhostNetwork 171/171, territory 124/124 oraz target
  persistence 221/221 — OK. P0 i P1 są DONE lokalnie; pozostaje serwerowe p95.

## 2026-08-19 - Otwarcie Sprintu 130.9.2.fix.all.1

- Manual serwerowy wykazał krytyczną regresję: mapa otwiera się kilka minut
  zamiast 4–12 sekund, player actors/operations/delta feed timeoutują, a części
  i SFX nie odtwarzają stabilnie lifecycle.
- Audyt całego 130.9* wykazał, że zwykły `sync_session_profile` i webowe rebuildy
  terytoriów uruchamiają synchroniczny globalny GN reconcile z `apply=True`,
  reward/endgame oraz fan-out delta. Read path wykonuje więc domenowe zapisy.
- Web i territory worker mogą równocześnie wykonywać GN/territory writes w tym
  samym SQLite. Worker nie jest pojedynczym właścicielem integracji i nie ma
  durable GN territory queue ani backlog telemetry.
- Operatorskie `ghostnetwork_runtime reconcile` obejmuje capture outbox i reward
  history, ale nie uzgadnia części z terytoriami. Po deployu brak jawnej procedury
  startup/recovery dla już istniejących części.
- `build_ghostnetwork_territory_publication` wykonuje globalny skan derived
  `player_areas`, dołącza clan z profile JSON i tworzy wersję przez hash czasu,
  zamiast konsumować finalny worker-owned publication receipt/version.
- W `game_play_180726.md` dodano pełny artefakt sprintu z P0/P1 findings,
  docelową granicą web/worker, etapami naprawy, budżetami p95, testami,
  procedurą deploy/recovery i dwiema bramkami manualnymi.
- 130.9.3–130.9.4 są wstrzymane. Nie wdrażamy kolejnych presentation patches
  przed odzyskaniem stabilności i wydajności podstawowej mapy.

## 2026-08-19 - Audyt stabilnosci Sprintu 130.9.2 po manualnym gameplayu

- Manual ujawnil niestabilne przejscia markerow `public/contained`, brak live
  SFX dla containment oraz wyrazne spowolnienie mapy po rozszerzeniu publication
  bridge.
- Reconcile uzywal stalego source eventu `reconcile:<cycle>`. Legalna oscylacja
  `public -> contained -> public -> contained` trafiala w stary dedupe i nie
  emitowala drugiego kanonicznego eventu. Klucz tranzycji korzysta teraz z
  monotonicznego version cyklu sprzed mutacji.
- Lifecycle zapisywal event w repository, ale adapter zwracal tylko rekord
  czesci, wiec runtime bridge nie otrzymywal `ghost.part_contained` do publikacji.
  Wynik mutacji przenosi teraz transient canonical event bez zapisu go w part row
  i bez ekspozycji w viewer projection.
- Ukryta projekcja nie posiada internal `part_id`; publisher nie potrafil przez
  to powiazac eventu z bezpiecznym `public_entity_id`. Powiazanie jest teraz
  deterministyczne i nie ujawnia identyfikatora ani dokladnej lokalizacji.
- Public/clan fan-out wykonywal pelny odczyt snapshotu osobno dla kazdego konta
  oraz osobne zapytanie profilu. Publication pobiera profile zbiorczo i buduje
  internal snapshot raz, po czym wykonuje indywidualne projekcje visibility w
  pamieci.
- Frontend traktowal dozwolone luki globalnego domain `state_version` jako utrate
  transportu. Filtrowane `internal/system` eventy powodowaly przez to petle
  snapshot recovery i czyszczenie warstw. Ciaglosc transportu pozostaje w
  per-user delta bus; GN akceptuje monotoniczne, nieciagle wersje domenowe.
- Regresja po poprawce: GhostNetwork 158/158 oraz persistence/map/delta/SFX
  242/242 OK. Dodano test oscylacji lifecycle, live event bridge, ukrytej
  projekcji i pojedynczego odczytu snapshotu dla 25 odbiorcow.

## 2026-08-19 - Sprint 130.9 Foundation: runtime enablement

- Dodano read-only runtime readiness z walidacją cyklu, 20 części, topologii
  i konfiguracji dropów oraz stabilnymi kodami `READY/NOT READY`.
- Start aplikacji nie mutuje GhostNetwork. Operatorski CLI udostępnia `status`,
  `verify` i suchy `bootstrap`; zapis wymaga jawnego `bootstrap --apply`.
- Konfiguracja pozostaje bezpiecznie wyłączona. Readiness blokuje dropy z
  chance spoza `(0, 1]`; nie wybrano produkcyjnej wartości balansowej.
- Dodano techniczną telemetrię aim/capture bez ukrytych danych oraz chroniony
  endpoint `/api/dev/ghostnetwork/readiness`.
- Foundation: `GO`. Durability, Runtime bridge i E2E pozostają otwarte;
  pending/unreconciled effects będą wdrożone wraz z outboxem.
- Testy celowane Foundation/cycle/reservation/discovery/pipeline: 32/32 OK;
  pełna regresja `test_ghostnetwork*.py`: 135/135 OK.

## 2026-08-19 - domknięcie Sprintu 130.9

- Dodano durable capture outbox oraz reconciliation/drain naprawiające crash
  pomiędzy committed capture i discovery. Retry zachowuje jedną część, jeden
  event discovery, contribution, reward i permanent history effect.
- Zwykły `/gonna-win` i post-130 ownership CAS enqueue'ują effect; replay
  receiptu wznawia go zamiast zwracać sukces z utraconym discovery.
- Kanoniczne publikacje obszarów i konfliktów sterują adapterem GN. Potwierdzono
  `public → contained → active`, release do `public`, freeze przy contest oraz
  powrót po resolved publication. Module progress aktualizuje się z lifecycle.
- Istniejący reward/contribution ledger został podpięty do eventów discovery,
  containment i activation. Bieżący stan cyklu nadal nie trafia do profilu.
- Runtime publication osiągający 20/20 wywołuje istniejący closure,
  transmission, signal, narrative i archive dokładnie raz; nie tworzy kolejnego
  cyklu.
- Lokalny operatorski bootstrap utworzył `ghostnetwork_0001` z 20 pooled parts.
  Verify w procesie development z drops enabled i chance `0.25` zwrócił
  `READY`; drain znalazł zero zaległych efektów. Nie wykonano deployu.
- Walidacja: nowe E2E/crash/bridge/endgame OK, pełne GhostNetwork 143/143 OK,
  post-130 territory/CAS/reconciliation 58/58 OK. Zbiorczy legacy
  `test_target_persistence` nadal ujawnia wcześniejsze zależności od kolejności
  i globalnego stanu; dotknięte przypadki przechodzą osobno.

## 2026-08-17 - Sprint 130.8.9.UX-appcreator.1: wspólny fundament creatorów

- Cztery creatory korzystają ze wspólnego katalogu opcji: klucz runtime,
  etykieta gameplayowa, ikona, opis i grupa. Payload nie został zmieniony.
- Checkboxy wizarda dostały wspólną warstwę OFF/ON. Filtry nadal czyszczą
  opcje niezgodne z rodziną i synchronizują ich wygląd.
- `trace` pozostaje wariantem Scanner / Recon, bez nowej rodziny backendowej.
- Picker wybiera jedną ikonę. Frontend i backend walidują pojedynczy widoczny
  glif, zachowując poprawne emoji/ZWJ i flagi.
- Nie zmieniano gameplayu, mapy, OFS, launch receipt ani zapisanych aplikacji.

#### historia dziennika w plikach 
* `doc/history/project_journal_13082026.md`

## 2026-08-14 - Secret Path: lore dla lekkiego oznaczania celu

- Klikniecie nazwy celu w menu hakowania zostalo nazwane ukryta sciezka
  `Secret Path`. Po potwierdzonym zapisie kanonicznego celu mapa uruchamia
  czterosekundowe show z przyciemnieniem, glitchem i sygnetem laczacym tarcze,
  ostrza oraz impuls.
- Dodano szesc losowanych scen lore. Komunikuja naprawienie kanalu celu,
  pominiecie pickera, gotowosc aplikacji pulpitu i terminala oraz przewage
  wynikajaca z odkrycia ukrytej sciezki interfejsu.
- Efekt jest warstwa prezentacyjna: nie zmienia progow zabezpieczen, wyniku
  operacji ani balansu. Odpala sie dopiero po sukcesie `/api/map/aim-target`,
  nie uruchamia mapowego boot loadera i nie przechwytuje interakcji z mapa.

## 2026-08-14 - Sprint 130.8.9: receipt aplikacji związany z celem

- Manualne uruchomienie aplikacji z pulpitu albo terminala dostaje teraz świeży
  `invocation_id` i `launch_receipt`. Receipt jest tworzony raz dla okna i
  przechodzi przez provisional, hydration, content autora, wybór oraz OFS;
  `flow_id` pozostaje wyłącznie korelacją diagnostyczną.
- Receipt zawiera skrót stabilnej tożsamości celu i losową tożsamość wykonania.
  Ponowne otwarcie tej samej aplikacji dla następnego celu nie może już
  odziedziczyć klucza `flowId:appId` ani payloadu poprzedniego celu.
- Backend zapisuje kanoniczny `expected_target_id` przy receipcie. Replay jest
  zwracany tylko dla tego samego receipt i tego samego celu; próba użycia go dla
  innego celu kończy się kontrolowanym `409 receipt_target_mismatch` przed
  odtworzeniem payloadu.
- Trace `APP_FLOW` pokazuje `invocation_id`, receipt, oczekiwany i bieżący cel
  oraz flagi replayu. Dodano regresje kontraktowe frontendu i endpointu dla
  użycia jednego receipt na dwóch celach.
- Capture, progi zabezpieczeń, konflikty, geometria i territory worker nie były
  zmieniane.

## 2026-08-14 - recovery markerów po publikacji konfliktu

- Końcowa delta workera `conflict_consolidated` uruchamia jeden debounced,
  read-only snapshot recovery. Zapobiega to sytuacji, w której geometria
  konfliktu ma już nową wersję, ale registry Leaflet nadal nie zawiera nowych
  filarów i innerów. Request mapy nadal nie wykonuje rebuildu.
- Do mapy dodano kontrolkę `↻` pod kontrolkami Leaflet. Ręczne odświeżenie
  przeładowuje wyłącznie dokument mapy i ponownie pobiera kanoniczne snapshoty,
  przejęte cele oraz aktorów; nie uruchamia deployu ani przebudowy geometrii.

## 2026-08-14 - lekkie oznaczanie celu z menu hakowania

- Nazwa obiektu w nagłówku menu hakowania działa teraz jako bezpośredni skrót
  do ustawienia `aimed_target`. Kliknięcie nie otwiera wyboru narzędzia, nie
  uruchamia aplikacji, OFS, operacji ani kolejki startowej.
- Dodano dedykowany endpoint `POST /api/map/aim-target`, który zapisuje
  kanoniczny cel przez istniejący kontrakt runtime, zachowuje stabilne
  `target_id` oraz kontekst podatności lub konfliktu i publikuje deltę
  `map.target_updated`.
- Frontend aktualizuje lokalny snapshot mapy i dolną belkę celu natychmiast po
  odpowiedzi endpointu. Nagłówek ma blokadę ponownego kliknięcia podczas zapisu
  oraz pozostaje dostępny z klawiatury jako zwykły przycisk.
- Ponowne wskazanie tego samego celu zachowuje jego dotychczasowy postęp
  `actions_allowed` i stan `security`; wskazanie innego celu rozpoczyna czysty
  stan rozpoznania bez wykonywania akcji hakowania.
- Odzyskiwanie postępu toleruje różnicę między identyfikatorem markera
  prezentacyjnego i kanonicznym `target_id`: zgodność pozycji oraz etykiety
  pozwala zachować aktualne `actions_allowed` i `security`, dzięki czemu belka
  pokazuje bieżący poziom rozbrojenia bez ponownego uruchamiania narzędzia.
- Walidacja: `python -m py_compile run.py database.py
  response_network\\territory_delta.py`, 48 testów celowanych oraz
  `git diff --check` — OK.



## 2026-08-14 - audyt zmiany celu: mapa vs pulpit i terminal

- Testy ujawniły, że lekkie wskazanie nowego celu z nagłówka menu mapy zapisuje
  poprawny `aimed_target`, ale kliknięcie opcji w ponownie uruchomionej aplikacji
  może przywrócić wynik dotyczący poprzedniego celu. Objaw obejmuje podmianę
  belki, pozorny sukces bez trwałej kropki oraz brak finalnego capture mimo
  kompletu akcji.
- Ścieżka mapowa pozostaje spójna, ponieważ `/hack-action` kanonizuje cel,
  zapisuje go w `PlayerTargetRuntimeStore` oraz tworzy dla startu aplikacji nowy
  receipt oparty o `flow_id`, `client_action_key` i aplikację. Kolejka przekazuje
  ten receipt dalej do `/gonna-win`.
- Audyt wykazał lukę ścieżki pulpit/terminal: ręczny start dziedziczy globalny
  `__lastHackFlowId`, a gdy nie ma receipt z kolejki, tworzy klucz
  `flowId:appId`. `/gonna-win` wykorzystuje ten klucz jako receipt
  idempotencyjny (TTL 900 s), więc kolejne uruchomienie tej samej aplikacji dla
  nowego celu może dostać replay payloadu wcześniejszego celu. Uruchomienie
  narzędzia z mapy generuje świeży receipt i dlatego wychodzi z impasu.
- Guard odpowiedzi starego okna i klucz okna zawierający tożsamość celu są
  potrzebne, ale nie rozwiązują replayu backendowego: payload jest już
  sklasyfikowany jako duplikat zanim wykonywana jest aktualna akcja.
- Wymagany kontrakt naprawczy: każda manualna instancja działania aplikacji musi
  otrzymać nowy, niezmienny `launch_receipt`, związany jednocześnie z aplikacją i
  stabilną tożsamością celu. Ponowienie tego samego kliknięcia może użyć tego
  samego receipt, ale nowy cel ani nowe uruchomienie nie mogą dziedziczyć receipt
  poprzedniej sesji. Po capture runtime ma zostać wyczyszczony, mapa ma dostać
  deltę, konflikt ma trafić do workera, a kolejny start ma powstać na świeżym
  kontekście.
- Osobno wyrównano projekcję postępu celu: `disarm_progress` ze store jest
  procentem 0-100, a nie surową liczbą wykonanych czterech akcji. Dzięki temu
  belka i cztery kropki opisują ten sam stan autorytatywny.

## 2026-08-15 - Sprint 130.8.9.SFX.1: fundament Game SFX

- Dodano jeden desktopowy właściciel efektów dźwiękowych: `window.GameSfx` w
  `static/js/game_sfx.js`. Moduł ładuje się przed Ghost Radio, OFS i terminalem,
  ale nie jest podpięty do żadnego zdarzenia gameplayowego.
- Dodano pusty produkcyjny manifest `static/audio/sfx/manifest.v1.json` jako
  lokalną allowlistę. Definiuje magistrale `lore`, `gameplay`, `message`,
  `system` i `ui`; payload nie może przekazać własnej ścieżki pliku ani ominąć
  limitów manifestu.
- Silnik obsługuje nieblokujący init i preload, autoplay unlock po pierwszym
  geście, lokalne `enabled` i `volume`, priorytety, limity głosów, cooldown,
  deduplikację `event_id`, ujemny cache brakujących assetów oraz kontrolowane
  wyniki błędów. Brak audio nie rzuca błędu do bootu ani aplikacji.
- Ghost Radio dostało przejściowy `duck_gain` z wieloma niezależnymi uchwytami.
  Efektywna głośność jest liczona oddzielnie od wartości użytkownika, więc
  zakończenie ostatniego SFX przywraca radio bez nadpisania jego ustawień.
- Dodano test kontraktowy modułu i test kolejności skryptów. Manifest pozostaje
  bez eventów i plików MP3 do Sprintu SFX.2, dlatego samo wdrożenie SFX.1 nie
  zmienia dźwięków gry.
- Walidacja dostępna w tej sesji: `node --check static/js/game_sfx.js`,
  `node --check static/js/ghost_radio.js`, `node --check static/js/terminal.js`,
  `node tests/js/test_game_sfx.js`, `node tests/js/test_operation_feedback.js`
  oraz `git diff --check` — OK. Lokalne `python.exe` było niedostępne, więc
  unittest Pythona pozostaje do uruchomienia w środowisku projektu.

## 2026-08-15 - Sprint 130.8.9.SFX.2: sześć scen Secret Path

- Sześć istniejących wariantów wizualnych Secret Path otrzymało stabilne
  `scene_id` i mapowanie 1:1 na `secret_path.scene_01`-`scene_06`. Jeden losowany
  rekord steruje jednocześnie tekstem, sceną i eventem audio; losowanie dźwięku
  nie jest wykonywane osobno.
- Audio jest odblokowywane w geście kliknięcia nazwy celu, lecz startuje dopiero
  po autorytatywnym sukcesie `/api/map/aim-target`. Błąd API, mute, autoplay albo
  brak MP3 pozostawia bez zmian ścieżkę gameplayową i czterosekundowe show.
- Kolejne uruchomienie Secret Path kasuje poprzedni timer i głos magistrali
  `lore`. Event id ma postać `secret-path:<target_id>:<local_sequence>`, a po
  końcu show uchwyt audio i ducking są zwalniane.
- Manifest dostał sześć jawnych lokalnych ścieżek MP3. Pliki należy dostarczyć
  pod `static/audio/sfx/secret_path/` zgodnie z README; bez nich działa
  kontrolowany fallback wizualny.
- Ustawienia pulpitu dostały przełącznik efektów, suwak głośności oraz test
  Secret Path. Wszystkie korzystają z jednego `window.GameSfx`, bez osobnego
  odtwarzacza i bez wpływu na Ghost Radio poza uchwytem duckingu.
- Dodano test kontraktu sześciu scen, kolejności gesture/API/show oraz kontrolek
  Ustawień. Składnia JS, test silnika Node i `git diff --check` są poprawne;
  lokalny `python.exe` ponownie był niedostępny, więc unittest Pythona pozostaje
  do uruchomienia w środowisku projektu.
- Test wdrożeniowy ujawnił cache pustego manifestu SFX.1: moduł i manifest miały
  niezmienione URL-e, a manifest świadomie używa `force-cache`. SFX.2 dostał
  wspólny cache-bust `sfx-secret-path-2`, dzięki czemu przeglądarka pobiera
  sześć nowych wpisów i nie pozostaje na pustej allowliście fundamentu.

## 2026-08-15 - Sprint 130.8.9.SFX.3: autorytatywny capture

- Test produkcyjny potwierdził sześć scen i sześć plików Secret Path; bramka
  SFX.2 została zaakceptowana przed wejściem w dźwięki gameplayowe.
- Każde zatwierdzone przejęcie otrzymuje backendowy `capture_version`, wspólny
  dla odpowiedzi `/gonna-win` i delty `map.target_captured`. Desktop kieruje oba
  sygnały do jednego helpera oraz jednego event id
  `target-captured:<target_id>:<capture_version>`, więc response i delta nie
  odtwarzają efektu podwójnie.
- Jawny `node_role=pillar` wybiera `capture.conflict_pillar`; pozostałe cele
  wybierają `capture.target`. Frontend nie zgaduje innera z ikony, geometrii ani
  położenia.
- `capture.conflict_resolved` jest uruchamiany wyłącznie przez kanoniczną deltę
  `territory.conflict_changed` ze statusem `resolved`. Snapshoty, recovery mapy,
  lokalne kropki i pasek rozbrojenia pozostają ciche.
- Manifest dostał trzy eventy magistrali `gameplay` i cache-bust
  `sfx-capture-3`. Produkcyjne assety są oczekiwane w
  `static/audio/sfx/capture/`; ich brak korzysta z istniejącego bezpiecznego
  negative cache i nie wpływa na capture, konflikty ani przebudowę terytorium.

## 2026-08-15 - Sprint 130.8.9.SFX.4: Cyberner i komunikaty systemowe

- Test wdrożeniowy użytkownika zaakceptował SFX.3; po tej bramce uruchomiono
  warstwę wiadomości bez zmian w gameplayu capture i konfliktów.
- Kanoniczna delta `cyberner.message_created` uruchamia dźwięk incoming tylko w
  trybie live. Pierwszy poll, recovery oraz pierwszy poll po błędzie połączenia
  są celowo ciche, więc historia i cursor catch-up nie tworzą lawiny audio.
- Własna wysłana wiadomość może dostać ciche potwierdzenie dopiero po odpowiedzi
  backendu z trwałym `message_id`. Incoming i sent współdzielą dedupe
  `cyberner:<message_id>`, a dodatkowy cooldown kanału ogranicza serie zdarzeń.
- Poll komunikatów systemowych używa stabilnego ID ze store i odtwarza wyłącznie
  klasy warning/critical; info pozostaje ciche. Boot i reconnect są ciche tak
  samo jak w delcie Cybernera.
- Manifest dostał cztery allowlistowane assety magistral `message` i `system`.
  `system.critical` ma najwyższy priorytet i może przerwać słabsze głosy, które
  zwalniają własne uchwyty duckingu Ghost Radio. Cache-bust zmieniono na
  `sfx-messages-4`.
- Dodano README kontraktu plików `static/audio/sfx/messages/` oraz rozszerzono
  test silnika o globalne przerwanie niższego priorytetu. Audio pozostaje
  niezależne od read cursorów, unread count, otwierania okna i store wiadomości.
- Walidacja: `python -m unittest tests.test_game_sfx_frontend_contract
  tests.test_cyberner_channel_routing` — 15 testów OK; trzy celowane testy
  `SystemMessageStore` i endpointu `/system-messages` — OK; `python -m py_compile
  run.py database.py`, `node --check static/js/game_sfx.js` i `node --check
  static/js/terminal.js` — OK.

### Korekta watchdog audio po testach SFX.3

- Audyt wykazał, że silnik zatrzymywał MP3 sztywno po manifestowym
  `max_duration_ms`, nawet jeżeli metadane assetu wskazywały dłuższy plik. Limity
  2,5–7 s mogły przez to ucinać prawidłowy efekt przed naturalnym `ended`.
- Watchdog jest teraz przeliczany po `loadedmetadata`: wybiera większą wartość
  z limitu manifestu oraz pełnej długości MP3 z zapasem 750 ms. Zachowano
  twardy bezpiecznik 30 s i dotychczasowe sprzątanie głosu oraz duckingu.
- Dodano kontrakt JS dla assetu krótszego i dłuższego od limitu manifestu oraz
  dla bezwzględnego limitu awaryjnego.

## 2026-08-15 - Sprint 130.8.9.SFX.5: OFS i polish

- Domknięto wspólny lifecycle audio aplikacji hookami `ofs.intro`,
  `ofs.choice_available`, `ofs.choice_confirmed`, `ofs.progress_checkpoint`,
  `ofs.success`, `ofs.failure` i `ofs.runtime_warning`. Wszystkie cztery
  renderery wykonawcze korzystają z jednego `OperationFeedbackSession` i
  globalnego `GameSfx`.
- Każda emisja ma dedupe `ofs:<session_id>:<phase>:<sequence>`. Checkpointy są
  ograniczone do trzech na sesję i wyciszone na mobile do 620 px oraz przy
  `prefers-reduced-motion`, bez zmiany scen, requestu lub payloadu.
- Projekcja `feedback_content.audio_events` dopuszcza wyłącznie siedem
  odpowiadających sobie eventów semantycznych. Próby podania URL albo
  podmiany semantyki są ignorowane i korzystają z globalnego fallbacku.
- Manifest dostał siedem eventów magistrali `ui`, cache-bust `sfx-ofs-5` oraz
  README kontraktu assetów `static/audio/sfx/ofs/`. Brak pliku pozostaje
  bezpiecznym, cichym fallbackiem.
- Rozdzielono wynik gameplayowy (`ofs.failure`) od problemu transportu lub
  odpowiedzi runtime (`ofs.runtime_warning`). Critical nadal może przerwać
  OFS, a zwalnianie głosu przywraca ducking Ghost Radio.

### Korekta personalizacji `button_choice`

- Audyt wykazał, że tylko `scan_ports` miał własne pule wyborów. Pozostałe
  akcje uruchomione w aplikacji `button_choice` korzystały ze wspólnego
  fallbacku `feedback.operation.*`, przez co różne narzędzia wyglądały jak
  jedna prezentacja skanera.
- Dodano `button_choice_action_profiles` dla wszystkich 14 akcji OFS, również
  aliasów `scan_hotspots` i `audio_hack`. Każda akcja ma własny prompt,
  przyciski, wartości i jawny schemat wyłącznie prezentacyjnego stanu.
- Walidator wymaga puli `feedback.<action_key>.*` dla każdej akcji i izoluje
  wadliwy profil bez wyłączania pozostałych operacji. Composer wybiera profil
  według bieżącego `action_key`, niezależnie od domyślnego renderera operacji.
- Dodano cache-bust słownika `button-choice-actions-1` oraz regresję JSON/JS
  potwierdzającą kompletność, unikalność i brak współdzielenia pul.

### Korekta terminalnego lifecycle wyborów OFS

- Wynik payloadu, błąd, anulowanie i `dispose` usuwają teraz cały aktywny
  panel `button_choice`, zamiast jedynie blokować jego przyciski. Niewybrana
  decyzja nie pozostaje więc pod autorytatywną sceną końcową.
- Zachowano dotychczasowe potwierdzenie decyzji dla wyboru faktycznie wykonanego
  przez gracza; korekta nie wybiera automatycznie opcji po nadejściu payloadu.
- Dodano regresję JS sprawdzającą usunięcie nierozstrzygniętego panelu przed
  prezentacją sukcesu.
- Przyciski aktywnego wyboru OFS dostały czytelny glow i lekki lift na
  `hover/focus`, a wybrana opcja krótki jitter/glitch w czasie istniejącego
  potwierdzenia. Efekt nie wydłuża requestu i respektuje
  `prefers-reduced-motion`.
- Naprawiono tytuł belki po hydratacji: renderery `terminal`, `button_choice`,
  `window` i `progressbar_random` zachowują publiczną nazwę aplikacji z
  kontekstu startowego zamiast zastępować ją technicznym `app_id`.
## 2026-08-16 - Sprint 130.8.9.fixsprint-lvlrsp.1: trwałe rozliczanie progresji

- Audyt potwierdził, że pełne synchronizacje profilu mogły zapisać bieżące
  `territory_stats.effective_area` pomiędzy capture w `/gonna-win` a publikacją
  geometrii przez workera. Dotychczasowy finalizer widział wtedy przyrost równy
  zero, dlatego LVL i RSP nie rosły mimo poprawnego przejęcia.
- Dodano tabelę `territory_progression_receipts` oraz migrację `008`. Receipt ma
  unikalny event źródłowy, aktora, cel, zakres konfliktów i niezmienny snapshot
  geometrii sprzed transferu. Migracja nie wykonuje historycznego backfillu.
- Zwykły capture rozlicza receipt po lokalnej przebudowie, a conflict capture
  pozostawia go workerowi. Kanoniczny reconciliation-set finalizuje progresję
  po publikacji geometrii; późniejszy retry zwraca zapisany wynik bez ponownego
  zwiększenia `level` lub `respect`.
- Zapis nagrody i przejście receiptu `pending -> applied` odbywają się w jednej
  transakcji SQLite. Finalizer scala tylko pola progresji z aktualnym profilem,
  dzięki czemu nie cofa równoległych zmian aplikacji, operacji ani celu.
- Kilka capture skonsolidowanych w jednym publish korzysta z jednego łącznego
  przyrostu geometrii; pozostałe receipty są konsumowane jako coalesced i nie
  mogą powielić tej samej nagrody.
- Dodano log `[PROGRESSION_SETTLEMENT]` oraz regresje immutable baseline,
  idempotentnego settle i atomowego zapisu profilu. Wysokości nagród i zasady
  gameplayowe pozostały bez zmian; są zakresem osobnego sprintu `.gameplay-lvlrsp.2`.
- Korekta po teście gameplayowym: próg `+1 LVL za 10%` został przeniesiony z
  globalnego `effective_area` na surową powierzchnię konkretnego klastra, który
  objął przejęty punkt. Receipt zapisuje geometrie klastrów i pozycję celu,
  więc zmienne identyfikatory `player_areas` po rebuildzie nie zrywają ciągłości.
  Małe przyrosty jednego klastra kumulują się, a rozrost pozostałych pól nie
  dopina jego progu. RSP pozostaje liczone z efektywnego przyrostu.

## 2026-08-16 - Sprint 130.8.9.gameplay-lvlrsp.2: nagrody strategiczne

- Pełne otoczenie i trwałe wchłonięcie obcego klastra daje `+1 LVL` oraz
  `+1 RSP` za każdy faktycznie przepisany filar. Role pochodzą z immutable
  snapshotu klastra; innery nie zwiększają premii.
- Każdy konflikt zamknięty przez kanonicznego aktora daje `+1 LVL` i RSP równy
  jego poziomowi sprzed całego rozliczenia. Kilka konfliktów zamkniętych jednym
  otoczeniem sumuje się z nagrodą za wchłonięcie.
- Dodano atomowy `settle_strategic` oparty na istniejących progression receipts.
  Klucze zdarzeń zawierają dedupe otoczenia albo `conflict_id` i wersję
  rozwiązania, dlatego retry, restart workera i republikacja nie duplikują LVL
  ani RSP.
- Guard wspólnego klanu działa przed snapshotem, transferem i receiptem.
  Chronione relacje nie generują reward-only eventów.

## 2026-08-17 - Sprint 130.8.9.UX-appcreator.2 i start .3

- Domknięto wspólną prezentację opcji czterech creatorów: zasoby, operacje,
  akcje i cele są grupowane semantycznie, a zabezpieczenia otrzymały nazwy
  gameplayowe. Klucze zapisywane do kontraktu nie zostały zmienione.
- Filtry wykonują deterministyczną sekwencję rodzina → cel → akcja. Ukrywana
  aktywna wartość jest czyszczona i raportowana w statusie `aria-live`, natomiast
  nadal zgodne wybory przetrwają przejście Wstecz/Dalej.
- Krok ryzyka rozdziela pytania mapowane na `interferes_with`, `requires_off`,
  `disables` i `affects`; techniczne nazwy pozostają w podglądzie JSON.
- Rozpoczęto Sprint `.3`: podgląd ma podsumowanie dla gracza i zwijany JSON,
  walidacja wskazuje numer kroku oraz sposób naprawy, dodano stany dostępności
  zakładek i kontrolowany układ małego viewportu.
- `node --check static/js/terminal.js` oraz `git diff --check` przeszły.
  Lokalne testy Python pozostają niewykonane, ponieważ systemowy `python.exe`
  nie uruchamia procesu w tej sesji Windows; zakres zabezpiecza rozbudowany
  `tests/test_creator_ux_contract.py` do uruchomienia w środowisku projektu.
## 2026-08-17 - domknięcie Sprintów 130.8.9.UX-appcreator.1–3

- Audyt odbiorczy wykrył i usunął otwieranie pełnej puli opcji po pustym
  przecięciu filtrów. Aktywne ograniczenie rodziny, celu lub akcji może teraz
  poprawnie dać pusty wynik zamiast proponować nieobsługiwany kontrakt.
- Backend creatora waliduje jawne rodziny, tryby, typ aplikacji oraz wartości
  celów, akcji, operacji i zasobów. Tryb desktopowy nie przyjmuje akcji mapy,
  natomiast mapowy i hybrydowy jej wymagają. Ścieżka legacy bez rodziny nie
  została zmieniona i nie wymaga migracji.
- Zachowano `tracker` w rodzinie Scanner / Recon. Dzięki temu `Namierz cel`
  pozostaje istniejącą akcją `trace` z `generic_trace`, bez tworzenia nowej
  rodziny i bez cichego przepisywania typu przez backend.
- Podgląd gameplayowy obejmuje również ryzyko, wymagania, wyłączane
  zabezpieczenia i wpływ na gracza. Zakładki mają pełne relacje ARIA, obsługę
  strzałek/Home/End, a walidacja oznacza konkretne pole i prowadzi do kroku
  naprawy. Formularze mają kontrolowany scroll oraz jednokolumnowy układ na
  małym ekranie.
- Dodano regresję JS zachowania filtrów i wspólnego podpięcia czterech
  interfejsów oraz backendowe testy odrzucania wadliwego kontraktu i akceptacji
  tracera. `node --check static/js/terminal.js`, test Node creatora i
  `git diff --check` są poprawne. Testy Pythona pozostają do uruchomienia w venv
  CHAOS, ponieważ lokalny alias Windows nie uruchamia interpretera w tej sesji.
## 2026-08-19 - Sprint 130.9.1 Etap 1: gotowość do manualnego gameplayu

- Potwierdzono lokalny runtime w jawnym profilu development: cykl
  `ghostnetwork_0001`, 20 pooled części, valid topology, zero reservations,
  pending i unreconciled effects; `verify` zwraca `READY` przy drop chance 0.25.
- Dry-run `reconcile` i `drain` nie wykazał pracy do wykonania. Nie wykonano
  manualnego aim/hack/capture ani mutującego cleanupu.
- Naprawiono `tools/audit_ghostnetwork_runtime_state.py`, który odwoływał się do
  nieistniejącej metody repository; audyt korzysta teraz z kanonicznego cycle
  service i ma test regresyjny.
- `test_target_persistence` odizolowano od globalnych target/operation store'ów.
  Historyczne asercje map bootstrap, teleportu, recovery scopes i launch queue
  dostosowano do aktualnych kontraktów. Wynik pełnego pliku: `221/221 OK`.
- Przedmanualowa paczka bootstrap/readiness/durability/telemetry/bridge/E2E:
  `17/17 OK`. `py_compile` i `git diff --check` są poprawne.
- Status: `READY FOR MANUAL GAMEPLAY TEST`. Etap 2 czeka na wynik i logi
  użytkownika. Nie wykonano commita, deployu ani produkcyjnego włączenia flag.

### Korekta środowiska manualnego

- Manual przeniesiono z lokalnego runtime na kontrolowany serwer, ponieważ
  lokalnie nie ma territory workera ani właściwych kont testowych.
- Lokalna bramka pozostaje zielona, ale nie jest już końcowym readiness manuala.
  Nowy status: `LOCAL PRE-FLIGHT PASSED — SERVER RC REQUIRED`.
- Dopisano Etap 1B: backup, spójny commit web/workera, jawne flagi RC, testy
  serwerowe, status/verify/audyt, dry-run reconcile/drain, walidację kont oraz
  rollback bez domyślnego kasowania trwałych efektów.
- Commit, push, deploy i restart PM2 nadal nie zostały wykonane; wymagają
  wskazania hosta/procesów oraz jawnej zgody na wdrożenie release candidate.

## 2026-08-19 - Sprint 130.9.1 Etap 2 po manualnym teście serwerowym

- Dwóch testerów otrzymało naturalny drop części GhostNetwork przy chance 0.25.
  Jeden przypadek potwierdził log i frontendowa delta `ghost.part_discovered`;
  drugi potwierdził tester, a log nie był dostępny po odświeżeniu.
- Potwierdzono realny przepływ `map → aim → hack → capture → drop → discovery`.
  Nie ma podstaw do wymagania kolejnego manualnego dropu.
- `version_gap` przy discovery wynika z globalnego domenowego `state_version`:
  wewnętrzne eventy reservation/reward nie muszą tworzyć delty widocznej dla
  gracza. Klient prawidłowo przechodzi wtedy na autorytatywny snapshot recovery.
  Finding nie jest blockerem i nie wymaga przebudowy delta systemu.
- Rozszerzono odczytowy audyt runtime o per-part weryfikację eventu discovery,
  contribution, applied reward, profile history i capture effect exactly-once.
- Regresja: GhostNetwork `144/144`, territory/CAS/reconciliation `134/134`,
  `test_target_persistence` `221/221`, celowane delta/audit `10/10`; `py_compile`
  i `git diff --check` przeszły.
- Serwerowy odczyt potwierdził `READY`, cykl `ghostnetwork_0001`, 20 części
  (`18 pooled`, `1 public`, `1 contained`), dwa discovery oraz zero
  pending/unreconciled effects. Każda część ma pojedynczy event, contribution,
  applied reward i applied capture effect; brak duplikatów.
- Audit znalazł konkretną regresję: oba profile miały `profile_history=0` mimo
  applied ledger i eventu `ghost.player_history_changed`. Późny pełny zapis
  `/gonna-win` nadpisywał historię zapisaną przez reward coordinator.
- Naprawiono monotoniczne zachowanie historii w `UserStore.save_profile()` i
  zachowanie dynamicznych pól GN przez `UserProfileManager`. `reconcile` potrafi
  odczytowo wskazać braki, a z `--apply` odtworzyć samą historię bez ponownego
  RSP, contribution lub discovery.
- Po poprawce: testy celowane `14/14`, GhostNetwork `144/144`,
  `test_target_persistence` `221/221`. Do GO pozostaje wdrożenie poprawki,
  jednorazowy reconcile dwóch historii i końcowe audit/verify; ponowny manual
  drop nie jest potrzebny.

### Wynik serwerowego reconcile

- `reconcile --apply` znalazł i odtworzył dokładnie dwa brakujące wpisy historii:
  `missing_count=2`, `repaired_count=2`.
- Ponowny audit: `discoveries.ok=true`; dla E4 i P5 event, contribution, applied
  reward, profile history oraz applied capture effect mają liczność dokładnie 1.
- Runtime pozostał `READY`: 20 części (`18 pooled`, `1 public`, `1 contained`),
  valid topology, zero reservations i zero pending/unreconciled effects.
- Blocker historii jest zamknięty. Finalny warunek pozostaje otwarty, ponieważ
  serwer raportuje `active=0` i brak eventów lifecycle; nie potwierdzono jeszcze
  `contained → active → module progress`. Wystarczy kontynuować istniejącą część,
  bez kolejnego dropu.

## 2026-08-19 - Dopracowanie Sprintów 130.9.2–130.9.4

- Ujednolicono trzy sprinty presentation-layer z modelem pracy projektu:
  audyt przed implementacją, najmniejsza integracja, testy automatyczne,
  manualna bramka w grze, finalna regresja i osobny werdykt `GO/NO-GO`.
- Dodano wspólny kontrakt authoritative state/event, exactly-once dla efektów
  jednorazowych, idempotentny snapshot/delta/recovery oraz presentation failure
  nieblokujący gameplayu.
- Sprint 130.9.2 rozdzielono na audyt SFX, implementację z fallbackiem, bramkę
  dostarczenia audio i manualny odsłuch w realnym gameplayu.
- Sprint 130.9.3 rozdzielono na audyt payloadu/renderera, testowaną integrację
  warstw terytorium oraz manual desktop/mobile dla normal/active/hostile.
- Sprint 130.9.4 rozdzielono na eksport kanonicznego mapowania części, bramkę
  dostarczenia PNG, integrację renderera/fallbacku/transitions i manual mapy.
- Skrypty techniczne mają być wersjonowane, read-only i nie mogą resetować ani
  modyfikować aktywnego `ghostnetwork_0001`. Po każdym sprincie obowiązują
  aktualizacja dokumentacji, testy celowane, regresja mapy/GN, kontrola składni
  i `git diff --check`.
- Nie wykonano implementacji sprintów, commita ani deployu; zmiana dotyczy
  wyłącznie dopracowania planu pracy.

## 2026-08-19 - Sprint 130.9.2 Etap 1–2: GhostNetwork SFX

- Audyt potwierdził istniejący `window.GameSfx`, manifest v1, bus limits,
  cooldown, dedupe po `event_id`, negative asset cache, radio ducking i
  presentation-only fallback.
- Minimalny hook umieszczono w nadrzędnym state delta consumerze. Audio jest
  dozwolone wyłącznie dla live delty; initial catch-up, reload, snapshot i
  recovery nie odtwarzają historycznych SFX.
- Dodano mapping discovery, contained, activated, hostile/contested, lost,
  module progress, module complete i GhostSignal oraz kontrakt ośmiu MP3 w
  `static/audio/sfx/ghostnetwork/README.md`. Finalnych plików audio nie dodano.
- `ghost.machine_progress_changed` gra tylko, gdy `active_parts` faktycznie
  różni się od `previous_active_parts`.
- Finding: `apply_ghostnetwork_runtime_result()` publikuje deltę tylko eventom z
  `player_id`; eventy owner/public/internal/system bez bezpośredniego gracza nie
  mają jeszcze ogólnego fan-outu. Rozszerzenie audience wymaga osobnej decyzji,
  ponieważ wpływa na widoczność eventów poza warstwą audio.
- Walidacja dostępna lokalnie: `node --check` dla `game_sfx.js` i `terminal.js`,
  `node tests/js/test_game_sfx.js`, `node tests/js/test_operation_feedback.js`,
  walidacja manifestu ośmiu kluczy GN i `git diff --check` — wszystko OK.

### Usunięcie blockera publication bridge

- Ogólny GN bridge rozwiązuje teraz eventy bez `player_id` według istniejącego
  `audience_scope`: `owner`, `clan`, `public` i `player`. Nie dodano ścieżki
  dystrybucji zależnej od SFX.
- `internal` i `system` są bezwarunkowo odrzucane. Discovery zmieniono z legacy
  `system` na `player`; machine progress/online z `internal` na `clan`; wyłącznie
  finalny `ghost.signal_sent` z `system` na `public`.
- Każda publikacja nadal korzysta z `GhostNetworkDeltaPublisher` i osobnego
  viewer projection. Event części bez widocznej projekcji jest pomijany, dzięki
  czemu publiczny fan-out nie ujawnia ukrytej części, topologii ani internal
  `part_id`.
- Dodano testy audience dla `part_contained`, `part_contested`,
  `machine_progress_changed` i `signal_sent`, odrzucenia internal/system,
  stabilnego dedupe per recipient oraz braku publikacji ukrytej części.
- Snapshot/recovery pozostają ciche: SFX działa tylko przy live delta gate, a
  recovery nie wywołuje ani `playGhostNetworkDeltaSfx`, ani `GameSfx.play`.
- Lokalnie brak interpretera Python/WSL, więc nowe testy Python są przygotowane,
  ale wymagają uruchomienia w środowisku serwerowym/CI. Testy Node, składnia JS,
  manifest i `git diff --check` przechodzą.

## 2026-08-22 - Sprint 130.10: manual izolacji sesji i ekran blokady CHAOS

- Manual z `logs/sprint-130-10-monitor-20260822T113207Z-1548831.log`
  potwierdził brak przecieków między kontami. Druga gra w tej samej sesji cookie
  została poprawnie zatrzymana przez `409 missing_generation`, a niezależny
  profil przeglądarki działał równolegle.
- W wycinku było 370 odpowiedzi `200`, 6 kontrolowanych `409`, zero `500`,
  tracebacków, błędów blokady bazy i restartów PM2. Odrzucenia po logout były
  zgodne z durable lineage contract.
- Surowy JSON z formularza logowania zastąpiono ekranem
  `CHAOS // SESSION GATE` wyłącznie dla żądań dokumentu HTML. API i polling nadal
  otrzymują niezmieniony JSON `session_generation_mismatch`; blokada nie wykonuje
  redirectu ani bootstrapu sesji.
- Regresja session generation: isolation `30/30 OK`, łącznie store, precommit
  i isolation `42/42 OK`; `py_compile` i `git diff --check`: OK.
- Bramka manualna izolacji sesji: `SESSION ISOLATION MANUAL PASSED`; pełny Sprint
  130.10 pozostaje otwarty do końcowego Etapu 7 i serwerowego `status/audit/verify`.
- Retest po wyczyszczeniu cache potwierdził ekran bramki i brak przecieków.
  Przycisk `window.close()` zastąpiono komunikatem `ZAMKNIJ TĘ KARTĘ RĘCZNIE`,
  ponieważ karta otwarta ręcznie nie może być niezawodnie zamknięta przez stronę.
- Manual ujawnił selektywny brak warstwy GN na mobile konta `main` przy ciężkiej
  projekcji terytorium (`445 778 521 m²`, 5 klastrów); desktop tego konta i mobile
  pozostałych kont były poprawne. Opcjonalny boot błędnie oznaczał wynik `false`
  jako załadowany, a retry było zablokowane dla scope niekrytycznych.
- Wynik `false` nie trafia już do `loadedScopes`; tylko boot GN wykonuje dwa
  ograniczone retry i loguje `snapshot deferred`, bez stałego pollingu. Cache key:
  `mobile-boot-retry-7`. Regresja Python `55/55 OK`, testy Node mapy i składnia
  JS: OK. Status: `READY FOR MOBILE MAIN GN RETEST`.

## 2026-08-22 - Sprint 130.10: usuniecie pelnego profilu z GN snapshot

- Diagnoza regresji 10x wskazala `/api/ghostnetwork/snapshot`: endpoint ladowal
  caly `profile_json`, walidowal i kopiowal go oraz wykonywal runtime overlay,
  chociaz viewer projection potrzebuje tylko loginu, klanu i profesji. Bounded
  retry mogl zwielokrotnic ten koszt na ciezkim koncie `main`.
- Dodano fail-closed `UserStore.get_profile_identity()` i przelaczono snapshot na
  waska projekcje SQL. Nie ma pelnego profilu, session sync ani canonical runtime
  overlay; istniejacy visibility contract GN pozostaje bez zmian.
- Testy endpointu jawnie odrzucaja probe `load_profile_readonly()`. Projekcja nie
  zwraca `apps`, `files` ani `inventory` i kontrolowanie odrzuca niepoprawne
  metadata oraz malformed JSON.
- Regresja Python: `77/77 OK`; renderer GN Node, `py_compile` i
  `git diff --check`: OK. Status:
  `READY FOR MOBILE MAIN PERFORMANCE + GN RETEST`.

## 2026-08-23 - Sprint 130.10.1: Hot Path Recovery

- Audyt potwierdził, że profile integrity ze Sprintu 130.10 zostało globalnie
  podpięte pod zwykłe runtime reads/writes. Na dużym koncie zwielokrotniało to
  koszt `aim-target` i każdego z dwóch zachowanych requestów `/gonna-win`.
- Przywrócono lekki `UserStore.get_profile()`; pełna walidacja schema/checksum
  pozostaje w jawnym `get_profile_with_revision()` i w każdym guarded write.
- `aim-target`, `operation_only` i częściowe wyniki narzędzi korzystają z
  canonical target/operation stores bez pełnego compatibility profile write.
- `UserProfileManager` nie skanuje już wszystkich kont ani nie uruchamia
  `init_db()` per instancja. Trwały capture zachowuje guarded profile patch.
- Guarded writers przygotowują profil i LKG przed `BEGIN IMMEDIATE`; pod lockiem
  pozostają recheck, session guard, CAS, zapis i commit.
- Hooki GN reużywają process-local service, a telemetryka `[HOT_PATH]` raportuje
  request, full reads/writes, bajty profilu i writer wait.
- Snapshoty `game.sqlite3.server` oraz `game.sqlite3.*` zostały jawnie wyłączone
  z Git. Testy celowane: `267/267 OK`; pełna regresja: `978/978 OK`; testy po
  końcowej zmianie telemetryki: `8/8 OK`.
- Read-only benchmark realnego snapshotu: `main` (`34 580 098 B`) spadł z
  mediany `2490.354 ms` heavy/audit do `460.167 ms` runtime read (`5.41×`);
  mały profil `ania` pozostał w koszcie otwarcia połączenia (`17–21 ms`). Plik
  bazy pozostał niezmieniony. Status:
  `READY FOR SERVER BEFORE → AFTER MEASUREMENT`.

## 2026-08-23 - Sprint 130.10.2: Marked Target Hot Path & Visual Continuity

- Audyt sekwencji `scan → oznacz → szybkie wyczyść scan` wykazał, że menu
  skanu nadal używało legacy `/map-action`, który dla małej zmiany targetów
  czytał i przepisywał pełny profil przez `UserProfileManager`.
- Na snapshotcie konta `main` profil miał `34 596 295 B`, podczas gdy sama lista
  59 targetów około `8 622 B`. Dominujące `operations` miały około 31,8 MB i
  nie powinny uczestniczyć w oznaczaniu celu.
- Dodano canonical `player_marked_targets` z idempotentnym receipt legacy seed.
  `/map-action mark_target` oraz target snapshot nie wykonują full-profile read
  ani write; retry oznaczenia nie publikuje drugiej delty.
- Frontend pokazuje natychmiast glitch marker `LINKING TARGET...`, niezależny od
  warstw skanu. Clear scan wyrejestrowuje starą warstwę, sukces instaluje marker
  interaktywny, a błąd pozostawia krótki `LINK FAILED`.
- Usunięto martwy `mapAction_old`. Dodano read-only/apply tool
  `tools/migrate_marked_targets.py`, testy store/endpoint/dedupe/capture/frontend
  oraz rozszerzono audit, example DB i migration cleanup o nowe tabele.
- Końcowa regresja celowana: `348/348 OK`; `py_compile`, migrator dry-run i
  `git diff --check`: OK.
- Status: `READY FOR SERVER MARK-TARGET RETEST`; bez commita i deployu.

## 2026-08-23 - Bramka heavy-profile dla Sprintów 130.11–138

- Serwerowy gameplay po 130.10.1–130.10.2 został oceniony jako wyraźnie
  szybszy; zgłoszony wcześniej lag zniknął. Wynik traktujemy jako ochronny
  baseline dla dalszych sprintów, nie zgodę na ponowne użycie pełnego profilu.
- Audyt planów 130.11–138 wykrył nieaktualny baseline: dokument 131+ nadal
  wskazywał `load_profile_readonly` dla snapshotu GN. Poprawiono go na aktualny
  integrity-gated `get_profile_identity`.
- Dodano wiążący `doc/architecture/profile_hot_path_contract_130_11_plus.md`: zwykły endpoint,
  snapshot, delta, event hook, publisher i worker mają zero full-profile
  reads/writes, profile bytes, all-user scans i per-recipient profile reads.
- Sprint 130.11 ma jedyny jawny wyjątek: operatorski audit/repair/verify exact
  canonical konta. Heavy helper nie może trafić do runtime ani skanować innych
  profili.
- Sprinty 131–135 dostały bramki lekkiej identity/viewer projection, braku
  `/api/profile` i braku profile refresh w GUI/delta/recovery. Sprint 136 ma
  zakaz `list_profiles()` i per-recipient profile reads; 137 nie czyta profilu w
  workerze; 138 nie wzbogaca feedu/CTA pełnym profilem.
- Każdy kolejny sprint wymaga testu na profilu co najmniej 35 MB oraz raportu
  `PROFILE HOT PATH AUDIT`. Runtime heavy counter różny od zera blokuje GO.

## 2026-08-23 - Sprint 130.11: start read-only recovery gate

- Dodano `tools/repair_trollu2_profile.py` — pierwsza faza udostępnia wyłącznie
  `status`, `audit`, podpisany `plan` i `dry-run`; SQLite jest otwierany
  `mode=ro` + `query_only=ON`.
- Exact canonical login to `trolu2`. Narzędzie nie wykonuje fuzzy match, nie
  skanuje pełnych profili innych kont i nie jest importowane przez web/worker.
- Realny lokalny snapshot potwierdził current checksum/revision, wallet `1000`,
  11 apps, 11 tools, Nmap + Metasploit jako dwie ostatnie receipt-backed
  instalacje, bilet do Tokio i aktywny cykl GN z 20 częściami.
- LKG ma poprawny checksum, ale zawiera canonical mirror i został wykluczony jako
  recovery source; wymagany będzie immutable before-manifest.
- Pierwszy wariant ośmiu filarów kolidował z istniejącym terytorium. Resolver
  deterministycznie przeniósł centrum 3000 m na północ; ponowny dry-run: zero
  kolizji territory/conflict/GN, zero GN writes, zero writes innych profili.
- Testy `tests.test_trollu2_recovery_tool`: `13/13 OK`; pełna celowana regresja
  profile/LKG/wallet/GN/territory: `93/93 OK`; `py_compile`: OK.
- Status: `IN PROGRESS — LOCAL READ-ONLY PLAN/DRY-RUN PASSED`; nie wykonano
  backupu, apply, rebuildów, settlementu, LKG promotion, commita ani deployu.

## 2026-08-23 - Sprint 130.11: controlled recovery pipeline ready

- Domknięto operatorskie `backup/apply/verify/promote-lkg/report/rollback` dla
  exact canonical `trolu2`. Plan, before-manifest, profile revision/checksum,
  wallet version, schema identity, session-generation oraz GN topology są
  fail-closed preconditions.
- Grant Tokio tworzy 8 stabilnych filarów, ownership, captured targets, jeden
  recovery job i step receipt atomowo. Retry jest idempotentny; settlement HC ma
  dokładnie jeden balance event i ledger entry.
- Territory worker dostał wąską gałąź `sprint_130_11` dla exact subject. Nadal
  używa canonical rebuild/publication, ale nie czyta i nie zapisuje pełnego
  profilu ani LKG. Zwykła ścieżka workera zachowuje dotychczasowy kontrakt.
- LKG pozostaje niezmienione do osobnego `promote-lkg` po verify i manualu.
  Rollback odmawia po późniejszej zmianie profilu, walletu albo geometrii.
- Real-schema próba na kopii snapshotu 809 MB doszła poprawnie do
  `AWAITING_TERRITORY_WORKER`: 8 targetów + 1 pending job, bez zmiany walletu,
  RSP i LKG. Kopię i sensitive manifest usunięto po próbie.
- Regresja: recovery/worker `22/22 OK`; sąsiednie kontrakty
  profile/session/wallet/target/territory/GN `441/441 OK`; `py_compile` i
  `git diff --check` OK.
- Status: `READY FOR SERVER DRY-RUN / OPERATOR APPLY`; produkcyjna baza nie
  została zmieniona, nie wykonano commita ani deployu.

## 2026-08-23 - Sprint 130.11: server apply blocker i controlled rollback

- Serwerowy worker po częściowym apply utworzył konflikt
  `territory_conflict_26409afa48525665` z `pies1`, mimo że stary dry-run
  raportował `collisions=[]`. Settlement RSP/wallet/LKG nie został wykonany.
- Root cause: planner sprawdzał tylko polygon nowych filarów, natomiast worker
  budował kanoniczne klastry ze wszystkich stationary targets przy levelu 50.
  Konflikt pochodzi z geometrii istniejących targetów rozszerzonej przez zmianę
  poziomu, więc sama relokacja bonusu Tokio nie może go usunąć.
- Wydzielono czysty `territory_geometry.py`; runtime i recovery używają teraz
  wspólnego algorytmu obszarów oraz przecięć. Plan przechowuje checksum preview i
  fail-closed raportuje `level_50_existing_geometry_conflict`.
- Receipt rozpoznaje wyłącznie dokładną recovery-owned projekcję revision +1.
  Każdy inny checksum, wallet drift, pending progression, capture/action w
  konflikcie albo multi-engagement blokuje rollback.
- Controlled rollback usuwa tylko granty planu, przywraca profil przez CAS i
  kieruje błędny konflikt do kanonicznego `no_active_fronts`. Dodano osobne
  `verify-rollback`; final settlement jest blokowany przez każdy otwarty konflikt
  utworzony przez recovery.
- Regresja recovery i territory: `376/376 OK`; `py_compile` i końcowy pełny
  zestaw testów pozostają bramką przed przekazaniem komend operatorskich.
- Status: `NO-GO — partial apply frozen; controlled rollback pending on server`.
- Techniczne zamknięcie recovery conflict jest profile-neutralne i reward-neutralne:
  nie uruchamia participant rebuild, encirclement ani strategic progression receipt.
- Serwerowy preflight wykrył, że expected revision 3 nie odtwarzał runtime
  normalizacji targetów (`ORDER BY captured_at`, jawne `lat/lng/lon`). Rozdzielono
  rekonstrukcję receipt revision 2 od dokładnej projekcji conflict finalizera.
- Kolejny preflight zawęził diff do `profile.targets`: brakowało canonical
  marked-target overlay z `player_marked_target_state/player_marked_targets`.
  Rekonstrukcja odwzorowuje teraz active filter i `ORDER BY created_at,target_key`;
  pole nadal uczestniczy w pełnym checksumie.

## 2026-08-24 - Sprint 130.11: post-recovery identity presentation gate

- Produkcyjny controlled recovery `trolu2` zakończył się `COMPLETE`: LVL 50,
  RSP 2560, HC 250000, 8 targetów Tokio, 1 area, 0 conflicts, 9/9 retirement,
  LKG promoted i GhostNetwork untouched.
- Manual ujawnił pozostawione starter identity (`NowyHaker`, default avatar).
  Zakres naprawy został odseparowany od zakończonego recovery progression.
- Kontrakt rozdziela provenance: `Trolu 2` jest zatwierdzoną korektą nicku,
  `Socjotechnik` nowym wyborem gracza po recovery, a
  `/static/images/avatar-frakcja-2-player-2.png` wynikiem aktualnego mappingu.
  Profesja nie jest przedstawiana jako odzyskana z historycznego evidence.
- Dodano `tools/repair_trollu2_identity.py`: read-only audit/signed plan/dry-run,
  field-level CAS apply wyłącznie dla `nick/profession/avatar`, durable receipt
  z field provenance, verify i osobną promocję LKG. Clan/fraction oraz cały
  gameplay state są immutable preconditions.
- Plan przypina finalny recovery revision/checksum oraz hashe profilu bez trzech
  pól, walletu, inventory, territory i GN. Drift profilu lub canonical stores
  blokuje apply i nie pozostawia częściowej mutacji.
- Evidence 130.10 pozostaje jawnie ograniczone: archiwa są identity-redacted;
  ewentualne historyczne `fraction.role=2` jest obserwacją, nie recovery source.
- Regresja identity repair: `7/7 OK`; runtime web/worker nie importuje narzędzia. Status:
  `READY FOR SERVER READ-ONLY IDENTITY AUDIT`; bez produkcyjnego apply i deployu.

## 2026-08-24 - Sprint 130.11: post-recovery drift gate

- Identity apply zatrzymany po wykryciu revision 6 → LKG 7 → current 8.
- Dodano read-only, checksumowany `drift-audit`: changed-fields-only diff,
  klasyfikację gameplay/session oraz korelację telemetrii `[PROFILE_WRITE]`.
- `prewrite:profile_manager.update_profile` opisuje zapis tworzący revision 8;
  LKG zawiera stan revision 7 sprzed tego zapisu.
- Live audit potwierdził `protected_gameplay_drift={}`. Późniejszy poprawny
  prewrite LKG revision 7 jest legalnym następcą historycznego recovery LKG 6,
  nie unieważnieniem completed recovery.
- Identity repair jest niezależną field-level operacją na current canonical
  profile. Plan podpisuje bieżący revision/checksum/non-identity SHA i aktualne
  recovery invariants; receipt revision 6 pozostaje historycznym milestone'em.
- Plan wymaga LVL/RSP/HC 50/2560/250000, inventory/apps/tools 11/11, 8 recovery
  targets, 1 area, 0 recovery conflicts i GN recovery references 0. Dalszy
  profile/canonical drift nadal failuje zamknięty.
- Nie wykonano identity apply ani mutacji bazy. Regresja identity + Recovery v2
  + geometry audit: `47/47 OK`.
- Skorygowano instrukcję server drift-audit: jedynym legalnym źródłem jest
  finalne `/home/johndoe/chaos-recovery-13011-v2-20260824T073939Z/plan-v2.json`,
  nie rollbackowany plan recovery v1. Tool failuje przy niezgodności plan ID/SHA
  z completed receipt.
- Regresja dokładnego lifecycle rev6 complete → valid writes rev7/rev8 →
  current identity plan → tylko trzy identity fields: `48/48 OK`.

## 2026-08-24 - Sprint 130.11 COMPLETE

`SPRINT 130.11 — COMPLETE`

`TROLU2 CONTROLLED RECOVERY — COMPLETE`

`IDENTITY REPAIR — COMPLETE`

- Produkcyjny Recovery v2 i identity repair zakończyły się durable receipts
  `complete`, finalnym profile revision 9, dopasowanym LKG oraz
  `blockers=[]`, `ok=true`.
- Root cause class: potwierdzony sparse-profile destructive full-save po GN
  activation reward, po którym template sync materializował starter-like profil;
  korelacja historyczna z konkretnym incydentem pozostaje high-confidence z
  jawną luką pojedynczego write-attemptu.
- Dziewięć historycznych stationary targets przetrwało downgrade i po
  przywróceniu levelu reaktywowało geometrię kolidującą z późniejszą ewolucją
  świata. Controlled retirement 9/9 oraz rebuild usunęły ten legacy input.
- Przyznano bezkolizyjny bonus Tokio: 8 recovery targets, 1 area, 0 conflicts.
  Progression/wallet zakończyły się stanem LVL 50, RSP 2560, HC 250000 i
  EXP `2217312.71 m² efektywne`; apps/tools pozostały 11/11.
- Osobny field-level identity repair ustawił `Trolu 2`, nowy wybór
  `Socjotechnik` oraz canonical avatar
  `/static/images/avatar-frakcja-2-player-2.png`, zachowując Echo Wolności i
  cały non-identity gameplay state.
- GhostNetwork pozostał nietknięty: 20 parts i `recovery_reference_count=0`.
  Historical retirement audit ma 9 wpisów; finalny LKG odpowiada revision 9.
- Produkcyjny manual UI potwierdził nick, avatar, klan, progression, wallet i
  aktywne terytorium. Nie są wymagane dalsze apply ani rollback.

## 2026-08-24 - Formalne zamknięcie Sprintu 130.10

`SPRINT 130.10 — COMPLETE`

`SPRINT 130.10.1 — COMPLETE`

`SPRINT 130.10.2 — COMPLETE`

- Audit aktualnego kodu, testów i późniejszych wpisów journalu potwierdził
  profile revision/checksum/CAS, atomowe LKG, trwałe session generation,
  izolację kart/kont oraz wejściowy i transakcyjny precommit session guard.
- Wallet i inventory pozostają canonical stores z jednokierunkową projekcją;
  test kontraktu zabrania runtime direct writes do `users.profile_json` oraz
  seedowania canonical stores ze zwykłego odczytu profilu.
- Hot Path Recovery usunął pełny profil z `aim-target`, częściowych ścieżek
  `/gonna-win` i hooków GN oraz skrócił writer-lock do recheck/CAS/write/commit.
- Marked Target Hot Path korzysta z canonical `player_marked_targets`, nie
  wykonuje full-profile read/write, deduplikuje delty i zachowuje wizualny
  pending marker po szybkim wyczyszczeniu skanu.
- Manual session isolation zakończył się bez przecieków, błędów 500, restartów
  lub lock contention. Końcowy retest mapy potwierdził menu, actorów oraz części
  GhostNetwork na testowanych kontach; późniejszy serwerowy gameplay potwierdził
  ustąpienie regresji wydajności ciężkiego profilu.
- Nie znaleziono otwartego blockera pozostawionego przez serię 130.10. Dalsze
  sprinty obowiązuje `doc/architecture/profile_hot_path_contract_130_11_plus.md`.
- Podczas formalnego auditu bieżącego worktree uruchomiono zielone testy JS
  session generation, wallet idempotency i renderera GhostNetwork. Lokalne
  środowisko Windows nie udostępniało działającego interpretera Python, dlatego
  nie powtórzono w nim suite Python; podstawą formalnego werdyktu pozostają
  zapisane zielone regresje 956/956, 978/978, 348/348, późniejsze regresje
  incydentowe oraz statyczna rewalidacja aktualnych kontraktów.

Werdykt: `READY TO START SPRINT 131`.

## 2026-08-24 - Porządkowanie dokumentacji

- Płaski katalog `doc/` podzielono według roli dokumentów na: `overview`,
  `gameplay`, `architecture`, `systems`, `sprints`, `audits`, `runbooks`,
  `incidents`, `plans` i `history`.
- Zachowano nazwy wszystkich 101 istniejących dokumentów; zmieniły się wyłącznie
  ich katalogi oraz wersjonowane referencje do ścieżek.
- Dodano `doc/README.md` jako centralny indeks, kolejność startową i mapę źródeł
  prawdy.
- Nie zmieniono runtime, schematu bazy, gameplayu ani konfiguracji procesów.

## 2026-08-24 - Sprint 131: GhostNetwork Suite pre-sprint audit

- Zweryfikowano nowy roadmap `doc/history/game_play_240826.md`, aktualny kod GN,
  Territory Control, map bridge, teleport, desktop lifecycle, delty i testy.
- Potwierdzono sześć relacji `GhostModuleStateService`, wspólny
  `GhostVisibilityService`, frozen conflict context, lekkie
  `/api/ghostnetwork/snapshot?view=suite` oraz viewer-projected delty.
- Potwierdzono brak potrzeby nowego store, visibility resolvera, endpointu
  snapshotu, pollera, mapy i systemu teleportacji.
- Znaleziono blockery kontraktowe: Territory Control czyta pełny profil,
  `/api/blacknet/cta/teleport` czyta i zapisuje pełny profil oraz przyjmuje
  klientowe współrzędne, a owner aliases nie mają bounded batch projection.
- Mapowy `GhostNetworkDeltaClient` musi zostać wydzielony przed Sprintem 135;
  audience fan-out 136 wymaga lekkiego indeksu odbiorców zamiast all-user lub
  per-recipient profile reads.
- Artefakt: `doc/sprints/sprint_131_ghostnetwork_suite_audit.md`.
- Status: `SPRINT 131 AUDIT COMPLETE — NO-GO FOR SPRINT 132`.
- Audit nie zmienił runtime ani bazy.

## 2026-08-24 - Sprint 130.12 rozpoczęty

- Utworzono żywy artefakt `doc/sprints/sprint_130_12_suite_readiness_cutover.md`.
- Rozpoczęto lokalny cutover bounded identity/recipient projection, Territory
  Control, canonical teleportu i shared delta client.
- Nie wykonano deployu, restartu PM2 ani produkcyjnego backfillu; status sprintu
  pozostaje `IN PROGRESS`.

## 2026-08-24 - Sprint 130.12.1 COMPLETE / Sprint 130.12.2 rozpoczęty

`SPRINT 130.12.1 — COMPLETE`

- Produkcyjny manual potwierdził latest-login-wins, natychmiastowe zastąpienie
  poprzedniej niezależnej sesji, relogin bez czyszczenia cookies/cache oraz
  poprawną pracę kilku kart współdzielących jedną sesję przeglądarki.
- Stare requesty pozostały fail-closed bez mutacji danych. Publiczny katalog,
  account-scoped catalog oraz desktop/tile state zachowały docelowy kontrakt.
- Zakres session ownership zostaje zamknięty bez dalszych zmian.

`SPRINT 130.12.2 — IN PROGRESS`

- Rozpoczęto audit call chainów Leaflet/GhostNetwork/territory snapshot oraz
  `/gonna-win`/OFS przed implementacją P0.
- Zakres P1 Sprintu 130.12.3 pozostaje poza bieżącą pracą.
- Bez deployu i restartu PM2 bez osobnej zgody.

## 2026-08-24 - Sprint 130.12.2 READY FOR SERVER VALIDATION

`SPRINT 130.12.2 — READY FOR SERVER VALIDATION`

- Rozszerzono historyczny guard Leaflet `_clipPoints` o transient race zachodzący
  już wewnątrz clippingu, bez maskowania niezwiązanych wyjątków.
- GhostNetwork i territory areas przechodzą przez candidate-first atomic
  replacement; błędny candidate zachowuje ostatnią poprawną warstwę.
- Recovery territory ma jednego właściciela, bounded retry oraz współdzielony
  refresh dla race `in_flight/aborted`.
- `/gonna-win` otrzymał bounded lifecycle telemetry i request ordinal. Receipt
  replay zachowuje canonical `operation_id`, a terminal OFS nie przechodzi w
  false failure po wcześniej potwierdzonym success.
- Celowane regresje: 169 testów Python oraz testy Node map/GN/recovery/OFS — OK.
- Bez deployu, restartu PM2, zmian schematu bazy i bez rozszerzenia o P1 130.12.3.

## 2026-08-24 - Sprint 130.12.2 READY FOR SERVER REVALIDATION

`SPRINT 130.12.2 — READY FOR SERVER REVALIDATION`

- Pierwsza walidacja produkcyjna ujawniła `409` opóźnionego Trace Compass na
  filarze konfliktu oraz pierwszorazowe `409` Browser/Desktop.
- Potwierdzony call chain operacji gubił kanoniczne `target_id/conflict_id`
  pomiędzy markerem mapy, `pending_action`, `aimed_target` i `expected_target`.
  To uniemożliwiało idempotentne rozpoznanie późnego wyniku po wcześniejszym
  przejęciu tego samego filaru.
- `/api/catalog` został sprowadzony do czystego odczytu. Zapis ustawień pulpitu
  używa projekcyjnego CAS patcha z bounded retry i rebase na świeżym profilu.
- Tożsamość filaru jest zachowana przez cały picker/app handoff. Dodano regresje
  dla tego kontraktu, read-only catalog i konfliktu rewizji desktop settings.
- Walidacja lokalna: 231 testów Python oraz testy Node GN renderer, map snapshot
  recovery, OFS i `/gonna-win` lifecycle — OK.
- Bez deployu, restartu PM2, zmian schematu bazy i bez commita.

## 2026-08-25 - Sprint 130.12.2 second operation revalidation correction

`SPRINT 130.12.2 — READY FOR SERVER REVALIDATION`

- Drugi manual potwierdził stabilny rebuild territory/GN bez białego overlaya
  oraz brak startowych `409` Browser/WebDragon.
- Nadal sporadycznie występował `409` Trace Compass wyłącznie dla filarów
  konfliktu; natychmiastowe ponowienie dla tego samego filaru przechodziło.
- Audit wykazał niespójność identity guardów: warstwa domenowa rozpoznawała ten
  sam filar po linii konfliktu i pozycji, lecz `PlayerTargetRuntimeStore` przy
  CAS wymagał identycznego `target_id`. Snapshot sprzed przebudowy/odświeżenia
  mógł więc zostać odrzucony jako `selection_changed` mimo ciągłości filaru.
- Runtime dopuszcza teraz alias wyłącznie przy zgodnej stabilnej linii konfliktu
  albo zgodnym foreign area, tej samej pozycji i bez zmiany właściciela. Inny
  konflikt, pozycja lub właściciel nadal kończą się fail-closed.
- Dodano regresję store i pełnego `/gonna-win`: późny snapshot scala postęp,
  zachowuje nowszy runtime `target_id` i nie wymaga drugiej próby. Frontend loguje
  jawnie status, reason, expected/current target id, receipt result i ordinal.
- Walidacja lokalna: 201 testów Python oraz testy Node `/gonna-win`, OFS i map
  snapshot recovery — OK; bez deployu, restartu PM2 i commita.

## 2026-08-25 - Sprint 130.12.2 final-dot ownership bootstrap correction

`SPRINT 130.12.2 — READY FOR SERVER REVALIDATION`

- Kolejny manual wykazał, że `409` pozostaje dokładnie na ostatniej kropce
  filaru konfliktu. Wcześniejsze kroki kończyły tylko postęp celu; ostatni krok
  jako jedyny wchodził w `TerritoryTargetOwnershipStore.capture()`.
- Root cause: przy braku rekordu ownership finalny request bootstrapował
  canonical row z `captured_targets` jako revision 1, a następnie mógł uznać tę
  revision utworzoną przez siebie za konkurencyjną zmianę wobec legacy revision
  0. Pierwsza próba zwracała `target_state_changed`; retry widział już revision 1
  i przechodził.
- Revision powstała w tym samym atomowym bootstrapie nie jest już traktowana jak
  CAS loss. Canonical owner nadal pochodzi wyłącznie z `captured_targets` i musi
  zgadzać się z expected owner; prawdziwa zmiana ownera/version pozostaje
  fail-closed.
- Dodano regresję finalnego capture z legacy version 0. Zachowano testy
  multi-attacker first-commit-wins, forged owner, stale version i idempotent
  replay.
- Frontend emituje dodatkowo jednoliniowy JSON `[GONNA_WIN_RESPONSE]`, aby status,
  reason, target IDs, receipt result i ordinal były widoczne w kopiowanym logu
  bez rozwijania obiektu DevTools.
- Walidacja lokalna: 210 testów Python oraz Node `/gonna-win` lifecycle i OFS —
  OK; bez deployu, restartu PM2 i commita.

## 2026-08-25 - Sprint 130.12.2 COMPLETE

`SPRINT 130.12.2 — COMPLETE`

- Rozstrzygająca telemetryka wykazała, że powracający `409` ostatniej kropki
  filaru nie pochodził z target/ownership guardów. Canonical capture był już
  zapisany, a odpowiedź psuł późniejszy `ProfileWriteConflict` pełnej projekcji
  profilu poprzedniego właściciela.
- Full-profile writer zastąpiono małym rebasowanym patchem z bounded CAS retry.
  Wyczerpany konflikt wtórnej projekcji nie zmienia canonical success w false
  failure; session/precommit mismatch nadal pozostaje fail-closed.
- Regresje lokalne: 81/81 oraz 305/305 — OK; `py_compile`, `node --check` i
  `git diff --check` — OK.
- Manual produkcyjny potwierdził poprawne finalizacje filarów konfliktu za
  pierwszym razem. Map/GN rebuild pozostał stabilny, bez białego overlaya.
- Trwały opis incydentu i procedura diagnostyczna:
  `doc/hardbugfix/gonna_win_conflict_pillar_final_dot_409_sprint_130_12_2_2026-08-25.md`.

## 2026-08-25 - Sprint 130.12.3 rozpoczęty

`SPRINT 130.12.3 — IN PROGRESS`

- Audit kodu potwierdził, że routing CTA BlackNet do właściwego produktu i
  zakładki GGPL/GX został już naprawiony: dispatcher ma rozdzielone handlery
  Googleplex i Ghost Exchange. Punkt oznaczono jako spełniony bez ponownej
  implementacji.
- Wspólny DOM input `search` nadal przechowuje query obu zakładek, dlatego
  izolacja filtrów GGPL/GX/BlackNet pozostaje w zakresie 130.12.3.
- Rozpoczęto prace nad pozostałymi P1: fail-closed Victim Picker, foreign 403 UX,
  GN visibility, tile scheme persistence/fallback i hot path Cybernera.

## 2026-08-25 - Sprint 130.12.3 READY FOR SERVER VALIDATION

`SPRINT 130.12.3 — READY FOR SERVER VALIDATION`

- CTA BlackNet → GGPL/GX pozostało bez reimplementacji; audit potwierdził
  właściwy produkt i tab. Rozdzielono jedynie query GGPL/GX/BlackNet i zachowano
  type guard katalogu przed `.filter()`.
- Victim Picker i Territory Control odrzucają brak/stale targetu oraz `(0,0)`;
  canonical aktywny target pochodzi z `PlayerTargetRuntimeStore`.
- `foreign_territory_protected` pozostaje poprawnym backendowym 403, a mapa
  pokazuje kontrolowany komunikat systemowy bez wyjątku frontendowego.
- Dotted connection różna dla dwóch kont jest zgodna z viewer visibility:
  connection nie trafia do payloadu, gdy endpoint nie ma exact location.
- Tile scheme zachowuje canonical desktop preference, a awaria providera ma
  runtime fallback do OSM bez zmiany zapisanej preferencji.
- Cyberner usunięto z full-profile hot path: identity, klan i audience korzystają
  z bounded `UserIdentityProjectionStore`. Test z profilem 35 MB: zero full
  read/write/bytes i zero skanów profili.
- Celowane testy Python, regresje Node, `py_compile`, `node --check` oraz
  `git diff --check` przeszły. Bez deployu, restartu PM2 i commita.

## 2026-08-25 - Sprint 130.12.3 COMPLETE

`SPRINT 130.12.3 — COMPLETE`

- Manual produkcyjny potwierdził wszystkie wcześniejsze punkty 130.12.3.
- MARK na obcym terytorium korzysta już z kontrolowanego handlera w obu
  ścieżkach (`/api/map/aim-target` i `/map-action`): system message jest obecny,
  backendowy 403 pozostaje prawidłowy, a wpis sieciowy DevTools nie jest
  blockerem.
- Dyrektywa GhostSignal została doprecyzowana: pełne połączenie dwóch aktywnych
  części jest publicznym globalnym stanem dla same/foreign/neutral viewerów.
  Aktywne endpointy są public/exact, lecz identity, profesja i supermoc nadal
  podlegają istniejącej projekcji.
- Regresje potwierdzają wspólne active connection dla trzech viewerów oraz brak
  zmian dla pooled/hidden/contained/half/inactive connections.
- Walidacja końcowa: 45 testów Python, Node GN renderer i map snapshot recovery,
  `py_compile`, `node --check` oraz `git diff --check` — OK.
- Bez deployu, restartu PM2 i commita.

## 2026-08-26 - Sprint 130.12.3 finalnie zamknięty po hotfixach

`SPRINT 130.12.3 — COMPLETE`

- Produkcyjny manual potwierdził operations capsules/incidents/NPC, lifecycle
  SFX GhostNetwork, public active connections, drop i spatial separation.
- Potwierdzono GX po dużym batch settlement oraz pełny Googleplex travel flow:
  idempotentny zakup, canonical position, `current_city`, travel receipt,
  otwarcie/focus mapy i brak podwójnego obciążenia.
- OSM `403r Referer is required` sklasyfikowano jako konflikt globalnego
  `no-referrer` z polityką providera, nie cache ani powrót Leaflet race. Mapa
  przekazuje wyłącznie origin, bez path/query generation.
- Nie pozostają otwarte manualne blockery w zakresie 130.12.3.

## 2026-08-26 - Sprint 130.12.4 rozpoczęty

`SPRINT 130.12.4 — IN PROGRESS`

- Pod-sprint jest wyłącznie closure/full-validation cutover; nie dodaje nowych
  feature'ów.
- Zakres: pełna regresja Python/JS, heavy-profile measurements, manual session,
  map/GN/territory/operations/OFS, Googleplex/GX/BlackNet, Cyberner, kontrola
  cutover oraz ponowny audit historycznych blockerów Sprintu 131.
- Deploy, restart PM2, backup/migration apply i produkcyjne mutacje nadal
  wymagają osobnej zgody.

### Bramka startowa 130.12.4

- Pierwszy pełny przebieg Python: 1092 testy, 4 failures i 2 errors. Izolowane
  powtórzenia potwierdziły sześć deterministycznych rozjazdów testów po
  wcześniejszych migracjach canonical store'ów; nie znaleziono nowej regresji
  runtime.
- Zaktualizowano wyłącznie fixture'y/allowlistę: Territory Control context,
  marked-target GN E2E, bounded identity reads, desktop bounded projection
  precommit oraz offline identity-recovery CAS exception.
- Wynik po korekcie: 6/6 przypadków i 266/266 testów pełnych modułów — OK;
  13/13 pakietów Node — OK; `py_compile`, `node --check` 27 plików oraz
  `git diff --check` — OK.
- Pełny rerun całego Python suite oraz pozostałe bramki 130.12.4 są nadal
  wymagane przed zmianą statusu.

## 2026-08-26 - Sprint 130.12.4 COMPLETE

`SPRINT 130.12.4 — COMPLETE`

- Pełna regresja po korekcie fixture'ów: 1092/1092 Python — OK; dodatkowa
  bramka heavy-profile/read-path 24/24 — OK; 13/13 pakietów Node — OK.
- `node --check` dla 27 plików, `py_compile` dotkniętych runtime/test modules i
  `git diff --check` — OK.
- Syntetyczny profil 35 MB potwierdził dla Cybernera zero full-profile
  read/write/bytes i zero skanów profili. Statyczne i endpointowe kontrakty
  potwierdzają bounded source dla GN, Territory Control, teleportu, mapy i
  targetów.
- Manual produkcyjny całej serii 130.12 potwierdził session ownership, map/GN,
  territory, operations/OFS, GX/BlackNet/Googleplex, Cybernera, SFX, drop i
  teleport. Nie pozostał zgłoszony blocker gameplayowy.
- Re-audit Sprintu 131 zamknął pięć historycznych blockerów wejścia w 132.
- Bez nowego deployu, restartu PM2, migration apply, produkcyjnych mutacji i
  commita.

`SPRINT 130.12 — COMPLETE`

`SPRINT 131 AUDIT COMPLETE — READY FOR SPRINT 132`

## 2026-08-26 - Sprint 132 rozpoczęty

`SPRINT 132 — IN PROGRESS`

- Rozszerzany jest istniejący `view=suite`; nie powstaje drugi endpoint, store,
  cache ani visibility resolver.
- Legacy suite wrapper kopiował pełne rekordy części do kilku list. Został
  zastąpiony jedną listą `parts[]`, top-level `summary/groups` oraz bezpiecznymi
  per-part `owner/territory/location/actions`.
- Owner aliases korzystają z jednego bounded, revision-aware batch lookupu.
  Exact actions używają opaque `public_entity_id`, a hidden territory-only
  wyłącznie `territory_id`.
- Dodano fail-closed sanitization, limit 20 części, suite health i cache key
  rozdzielający viewer/view oraz owner identity revision.
- Bramki: 31/31 testów suite/visibility/read-path, 217/217 pełnych testów
  GhostNetwork, 35/35 identity/Territory Control oraz 1105/1105 pełnej regresji
  Python — OK.
- GhostNetwork delta client i map renderer, `py_compile`, `node --check` oraz
  `git diff --check` — OK.
- Bez GUI, deployu, restartu PM2 i produkcyjnych mutacji.

`SPRINT 132 — READY FOR SERVER VALIDATION`

## 2026-08-27 - Sprint 132 COMPLETE

`SPRINT 132 — COMPLETE`

- Walidacja serwerowa dla dwóch niezależnych sesji: HTTP 200, `view=suite`,
  `suite_health.ok=true`, bez health errors.
- Potwierdzono unikalność części, limit 20, zgodność summary, reference-only i
  rozłączne groups, exact/territory-only privacy, hidden identity sanitization
  oraz connections bez geometrii.
- Powtórne odczyty zachowały `state_version`, snapshot checksum i suite-scoped
  cache key.
- Zamknięcie nie zmieniło runtime i nie wykonało restartu PM2, produkcyjnych
  mutacji ani commita.

## 2026-08-27 - pre-Sprint 133 app uninstall hotfix

`APP UNINSTALL CANONICAL INVENTORY — READY FOR SERVER VALIDATION`

- Root cause: `/api/apps/uninstall` usuwał aplikację z ciężkiego profilowego
  mirrora, lecz nie odwoływał kanonicznego `player_apps`; overlay mógł ponownie
  wprowadzić launcher do Menu Start.
- Uninstall korzysta teraz wyłącznie z bounded `PlayerInventoryStore` i atomowo
  aktualizuje app, tool oraz storage z session-generation precommit guardem.
- Response i delta przebudowują pulpit/Menu Start bez pełnego profile refreshu;
  retry jest `noop` i nie odejmuje storage ponownie.
- Profil syntetyczny 35 MB: zero full read/write/bytes. Walidacja: 5/5
  celowanych, 69/69 inventory/migration/hot-path, 134/134 gameplay/session oraz
  14/14 pakietów Node — OK; składnia i diff check — OK.
- Artefakt:
  `doc/hardbugfix/app_uninstall_canonical_inventory_pre_sprint_133_2026-08-27.md`.
- Bez deployu, restartu PM2, produkcyjnych mutacji i commita.

Manual serwerowy 2026-08-27 potwierdził poprawne działanie uninstallu.

`APP UNINSTALL CANONICAL INVENTORY — RESOLVED`
## 2026-08-27 — Sprint 133 rozpoczęty

- rozpoczęto desktopową aplikację `ghostnetworkSuite` na projekcji Sprintu 132,
- produkt dołączono do rodziny `ghost_control_suite`, cena `10 000 HC`, odbiorca/fallback `admin`,
- zakres 133 pozostaje read-only: bez profilu, mapy i teleportu.

Implementacja lokalna osiągnęła `SPRINT 133 — READY FOR SERVER VALIDATION`.
Snapshot suite pozostaje jedynym hot pathem; wyszukiwarka nie indeksuje ukrytej
tożsamości, a przyciski mapy i teleportu są disabled bez handlerów. Walidacja:
15/15 testów produktu/projekcji, 34/34 testy siostrzanych aplikacji i 15/15
skryptów JavaScript — OK; kontrole składni i diffu — OK. Bez deployu, restartu
PM2 i commita.

Manual serwerowy potwierdził instalację GhostNetwork Suite, widoczność części
i filtrowanie. `SPRINT 133 — COMPLETE`. Rozpoczęto Sprint 134; akcje mapy oraz
teleportu mają używać ikon zgodnych z Territory Control zamiast napisów.

Implementacja Sprintu 134 podłączyła opaque map focus i canonical teleport,
dodała fail-closed revalidation lifecycle/visibility oraz badge GN w Territory
Control. Ikony akcji są zgodne z Territory Control (`▣`, `➜`). Walidacja:
65/65 GN/Territory, 13/13 endpoint/session i 16/16 pakietów Node — OK;
kontrole składni i diffu — OK. `SPRINT 134 — READY FOR SERVER VALIDATION`.
Bez deployu, restartu PM2 i commita.

Pierwszy manual Sprintu 134 wykazał: exact teleport na kotwicę zamiast w jej
okolicę, niespójną sekwencję otwierania mapy oraz techniczne `none` i powielony
label na kartach. Exact teleport używa teraz stabilnego offsetu 28–46 m, mapa
otwiera się dopiero po zgodzie i canonical success, a eventy przycisków są
izolowane od pulpitu. Renderer pomija `none` i duplikat label/summary. Regresje:
65/65 GN/Territory, 3/3 teleport i 16/16 Node — OK. Sprint pozostaje
`READY FOR SERVER REVALIDATION`; bez deployu, restartu PM2 i commita.

Manual potwierdził teleport i otwieranie mapy na małych oraz dużych kontach.
Responsywny GhostNetwork Suite otrzymał jeden wspólny pionowy scroll całego
wnętrza; nagłówek/filtry przewijają się razem z kartami, bez nested scrolla listy.

Manual ujawnił, że fokus części przy zamkniętej mapie wygasał przed załadowaniem
warstwy GN i pozostawiał widok motocykla. Intencja fokusu jest teraz trzymana do
gotowości terytoriów lub publikacji snapshotu GN i konsumowana po pierwszym
skutecznym ustawieniu widoku. Pełna regresja 16/16 skryptów Node — OK.

Przed kolejnym sprintem usunięto wielokrotną przebudowę DOM markera motocykla.
Zmiany kierunku, aktywność telefonu i animacja trasy aktualizują istniejący sprite
zamiast wywoływać `Leaflet.marker.setIcon()` na głównym wątku. Sprites są
preloadowane, a bazowy motocykl pozostaje tłem awaryjnym podczas dekodowania.

Korekta po manualu: bazowe tło prześwitywało przez przezroczysty sprite kierunkowy
i wyglądało jak drugi nieruchomy motocykl. Tło usunięto; bazowy asset jest teraz
ustawiany wyłącznie przez `img.onerror` po rzeczywistym błędzie ładowania.

## 2026-08-27 — Sprint 135

GhostNetwork Suite został podłączony do wspólnego `GhostNetworkDeltaClient` bez
Leaflet i bez nowego pollera. Backend publikuje bezpieczną projekcję Suite,
visibility cutover zastępuje cały rekord, consumed usuwa opaque ID, a recovery
korzysta tylko z `snapshot?view=suite`. Zamknięcie okna usuwa adapter i retry.

Walidacja: 231/231 testów GhostNetwork, 93/93 Ghost Control/territory/session,
18/18 pakietów Node, `py_compile`, `node --check` i `git diff --check` — OK.

`SPRINT 135 — READY FOR SERVER VALIDATION`

Bez deployu, restartu PM2, produkcyjnych mutacji i commita.

## 2026-08-27 — Sprint 135.1 Ollama Outbox integration audit

`SPRINT 135.1 — COMPLETE`

Następna bramka: `READY FOR SPRINT 135.2`.

- Odzyskano formalnie zamrożony Sprint 84 `Ollama Enriched Signal Ingest +
  Mixed Feed` oraz świadomie odłożony, nienumerowany osobno zakres
  `BlackNet AI Ecosystem (Sprint 21+)`.
- Potwierdzono dwa istniejące mechanizmy: plikowy admin/dev export BlackNet ze
  Sprintu 83 oraz trwały SQLite `ghost_narrative_outbox` ze Sprintu 129.
- Wiążąca decyzja: trwały store Sprintu 129 zostanie rozszerzony do jednej
  canonical kolejki Ollamy; plikowy outbox pozostanie wyłącznie
  jednokierunkowym adapterem diagnostycznym.
- Zdefiniowano pełny flow `canonical event / installed app -> Ollama Outbox ->
  local worker/LLM -> Ollama Inbox -> validation/quarantine -> BlackNet |
  Googleplex News | Cyberner AGI-2108`, bez prawa modelu do mutacji gameplayu.
- Rozdzielono `processor=ollama` od `target_medium`, opisano claim/lease,
  dedupe, receipts, audience projection, truth classes, CTA allowlist i
  bezpieczny ingress z dedykowanej aplikacji instalowanej przez Googleplex.
- Roadmap 135.2-135.6 zastępuje fragmentaryczny plan 136-138: queue
  convergence, producers/app ingress, worker/inbox, publishers oraz hardening.
- Doprecyzowano twardą bramkę 135.2: `zbudować niezawodny transport tasków LLM,
  jeszcze bez LLM`. Sprint obejmuje wyłącznie canonical schema/store,
  enqueue/claim/lease/renew/complete/retry/dead-letter, concurrency/crash
  recovery i diagnostyczny eksport starego BlackNet outboxa. Nie obejmuje
  producentów, aplikacji Googleplex, workera, Inboxu ani publikacji.
- Obowiązkowe invariants 135.2: dokładnie jeden task dla
  `event + audience + target_medium`, dokładnie jeden aktywny lease owner oraz
  brak zgubienia lub zdublowania taska po crashu i wygaśnięciu lease.
- Pozostała decyzja produktowa przed 135.5: minimalny read model i miejsce UI
  dla `Googleplex News`.
- Artefakt:
  `doc/sprints/sprint_135_1_ollama_outbox_integration_audit.md`.
- Audit nie zmienił runtime, bazy i konfiguracji procesów; bez deployu,
  restartu PM2, produkcyjnych mutacji i commita.

## 2026-08-27 — specyfikacje wykonawcze Sprintów 135.2-135.5

- Roadmap z audytu 135.1 rozdzielono na cztery osobne dokumenty sprintów.
- 135.2: canonical transport tasków bez Ollamy, z atomowym
  enqueue/claim/lease/renew/complete/retry/dead-letter i diagnostycznym eksportem
  legacy BlackNet.
- 135.3: producenci GhostNetwork/GhostSignal/BlackNet oraz bounded ingress
  dedykowanej aplikacji Googleplex; nadal bez klienta Ollamy.
- 135.4: pierwszy lokalny worker Ollamy, structured output, canonical Inbox,
  validator i quarantine; bez publikacji dla graczy.
- 135.5: exactly-once publishery do BlackNet, Googleplex News i Cybernera
  AGI-2108, wyłącznie z accepted Inbox candidate.
- Wpis był planistyczny; aktualny status 135.2 znajduje się w późniejszym
  wpisie implementacyjnym. 135.3-135.5 pozostają za exit gates.
- Dokumentacja nie zmieniła runtime, bazy ani konfiguracji procesów.

## 2026-08-27 — rozszerzenie roadmapy Googleplex przed Sprintem 135.5

- Dodano Sprint 135.4.1: projekt i foundation Googleplex Home z osobnym,
  audience-projected News read surface, bez publikacji Ollamy.
- Dodano Sprint 135.4.2: proste narzędzie kupowane i instalowane z Googleplex,
  korzystające z ingressu 135.3 i pokazujące task status, ale jeszcze bez body
  odpowiedzi modelu.
- Sprint 135.5 domyka oba elementy: publikuje accepted candidates na Googleplex
  Home/News i udostępnia owner-scoped result w kupowanym narzędziu oraz
  Cybernerze AGI-2108.
- Kolejność bramek: `135.4 -> 135.4.1 -> 135.4.2 -> 135.5`.
- Wiążącą rewizję oraz mapowanie historycznych Sprintów 136-138 dopisano do
  `doc/history/game_play_240826.md`; stare rozdziały zachowano jako materiał
  źródłowy, ale nie jako równoległy roadmap.
- Bez zmian runtime, bazy i konfiguracji procesów.

## 2026-08-27 — Sprint 135.2 Canonical LLM Task Transport

`SPRINT 135.2 — READY FOR SERVER VALIDATION`

- Rozszerzono addytywnie `ghost_narrative_outbox` ze Sprintu 129 do jednej
  canonical kolejki Ghost Systemu, bez uruchamiania Ollamy.
- Canonical identity gwarantuje jeden task dla `source event/receipt + audience
  + target_medium`; caller nie może podmienić `dedupe_key` ani `task_id`.
- Dodano atomowe `enqueue → claim → processing → complete/retry/dead-letter`,
  owner/lease CAS, renew, deterministic backoff i bounded crash recovery.
- Dwa workery nie mogą posiadać tego samego aktywnego lease. Po wygaśnięciu
  stary owner nie może ukończyć taska przejętego przez nowego workera.
- Migracja normalizuje rekordy Sprintu 129 oraz canonical dedupe dokładnie raz;
  historyczne pseudo-medium `ollama_outbox` jest wycofane jako terminalny
  artefakt diagnostyczny.
- Dodano indeksy ready/lease/source/status i potwierdzono ich użycie przez
  `EXPLAIN QUERY PLAN`, także na fixture 2000 terminalnych tasków.
- Stary plikowy BlackNet outbox jest teraz wyłącznie sanityzowanym eksportem
  DB → JSON. Odczyt i status korzystają z canonical DB; plik nie może zmienić
  lifecycle taska.
- Nie dodano workera Ollamy, requestu HTTP, Inboxu, producentów gameplayowych,
  aplikacji Googleplex ani publikacji dla graczy.
- Walidacja: 243/243 pełnych testów GhostNetwork, 21/21 BlackNet world/outbox,
  16/16 finalnych queue/narrative, `py_compile`, kontrola mojibake i
  `git diff --check` — OK.
- Bez deployu, restartu PM2, produkcyjnych mutacji i commita.

## 2026-08-28 — heavy-profile gate dla roadmapy 135.3–135.6

- Ujednolicono wszystkie wiążące specyfikacje 135.3, 135.4, 135.4.1, 135.4.2
  i 135.5 twardą bramką zgodną z
  `profile_hot_path_contract_130_11_plus.md`.
- Każdy producer, worker, endpoint, read model i publisher ma zakaz używania
  `load_profile*`, `get_profile`, `list_profiles`, per-recipient `profile_json`
  oraz pełnego profilu jako cache/source of truth.
- Każdy sprint wymaga fixture profilu minimum 35 MB i wyników:
  `profile_full_read=0`, `profile_full_write=0`, `profile_bytes=0`,
  `all_user_profile_scan=0`, `per_recipient_profile_read=0`.
- Analogiczną fail-closed bramkę dopisano do planowanego hardening/cutover
  Sprintu 135.6.
- Zmiana jest wyłącznie dokumentacyjna; bez zmian runtime, bazy, deployu,
  restartu PM2 i commita.

## 2026-08-29 — start Sprintu 135.4.1.1 Googleplex Search Presentation Repair

- Status: `SPRINT 135.4.1.1 — IN PROGRESS / READY FOR VISUAL VALIDATION`.
- Dwie odrzucone iteracje prezentacji Search (`595f592`, `eb366df`) cofnięto
  lokalnie do baseline `c07b086`, wyłącznie w rendererze/CSS/testach Search.
- Nie cofnięto Googleplex News, AGI 2108, canonical purchased/install state,
  inventory, backendu ani rankingu wyszukiwania.
- Kolejne etapy mają wprowadzić jeden group engine oraz klasy geometryczne bez
  redukowania danych produktu i dopiero po osobnej walidacji fullscreen,
  start-size i mobile.
- Bez deployu, restartu PM2, zmian bazy, commita i pushu.
- Po baseline dodano jeden mapper paczek `1 HERO + 2 MIDDLE + 3 SMALL`, jeden
  pełny renderer produktu, canonical icon element bez panelu oraz osobną
  geometrię pojedynczego wyniku. Po manualnym wykryciu niepełnego `/all`
  usunięto limit trzech paczek: wszystkie elementy bounded public catalog są
  przekazywane do group engine.
- Automatyczna regresja obejmuje 2/3/4/6/7/12/70 wyników, pełny zestaw pól,
  brak przycinania i brak requestów per karta; 23/23 testów JS przechodzi.
- Sprint pozostaje otwarty do manualnej akceptacji fullscreen, start-size i
  mobile.

## 2026-09-01 — start Sprintu 135.6 Narrative Hardening and Cutover

- Sprint 135.5.2 zamknięto po fizycznym potwierdzeniu publikacji HERO w
  Googleplex News; dalsza kalibracja stylistyczna nie blokuje transportu.
- Legacy BlackNet JSON/file outbox jest już wyłącznie adminowym eksportem
  diagnostycznym. Canonical DB pozostaje jedynym źródłem task status, lease,
  retry, candidate i publication receipt.
- Dodano bounded cutover report, observability task/publication backlogu,
  expired lease/claim, unstaged accepted candidates i pokrycia trzech mediów.
- Dodano jawną, limitowaną operację terminalnego retirement wyłącznie queued
  tasków, których nie może claimować żadna aktywna prompt policy.
- Bramka nadal bezwzględnie zabrania ciężkiego profilu i skanu kont.
- 46 testów cutoveru, kolejki, workera i publishera przechodzi lokalnie. Szerszy
  pakiet ujawnił niezależny istniejący failure Ghost Exchange
  `storage_used=89`, poza ścieżką narracyjną i bez zmian w tym sprincie.
- Status: `ETAP I IMPLEMENTED LOCALLY / SERVER AUDIT PENDING`; bez deployu,
  restartu PM2, commita i pushu.

### 135.6 — wynik canonical server gate

- Wykonano online backup `game.pre-1356-cutover-20260901T1153Z.sqlite3`.
- Audit wykrył 49 wyłącznie historycznych `world_digest` w `ready/retry_wait`;
  wszystkie terminalnie wycofano jako `policy_superseded_cutover`.
- Powtórzony audit `--strict` zwrócił `ok=true`, bez błędów i ostrzeżeń.
- Canonical queue, worker, publisher, prompt registry i pokrycie BlackNet,
  Googleplex News oraz Cyberner mają `SERVER PASS`.
- Heavy profile, account scan, expired task leases, expired publication claims
  i unstaged accepted candidates: zero.
- Pozostaje fizyczny smoke trzech mediów oraz gameplay/SQLite soak przed
  oznaczeniem całego Sprintu 135.6 jako COMPLETE.
- Pierwszy smoke AGI przeszedł transport i retry po timeout, lecz output został
  poprawnie zatrzymany za echo topicu oraz wymyślone CTA. Validator zachowuje
  filtr echa, a przy pustej allowliście bezpiecznie usuwa modelowe CTA do null;
  54 testy policy/workera/cutoveru/publishera przechodzą.
- Powtórzony owner-scoped task AGI został zaakceptowany i opublikowany w
  Cybernerze. Post-cutover Cyberner smoke ma status PASS.
- Nowy incydent został opublikowany w BlackNet oraz Googleplex News. Oba
  post-cutover smoke tests mają PASS; ucięte zakończenie copy GGPL zapisano jako
  nieblokującą kalibrację jakości.
- Końcowy audit po wielogodzinnym soaku zwrócił `ok=true`: 392 publikacje,
  aktywne drenowanie nowych tasków, zero expired leases/claims, zero ineligible
  ready, zero unstaged accepted i zero heavy-profile I/O. Sprint 135.6 oraz
  canonical narrative cutover mają status COMPLETE.

## 2026-09-01 — przygotowanie Sprintu 136 GhostNetwork Domain Narrative Bridge

- Historyczny zakres 136 uzgodniono ze stanem po canonical cutoverze 135.6.
  Nie będzie drugiego outboxa, workera, publishera ani legacy runtime queue.
- Potwierdzono istniejący fundament: `GhostNarrativePublisher`, enqueue po
  zdarzeniu domenowym, canonical dedupe, fail-open, publiczny identyfikator,
  identity projection oraz pełny task/candidate/receipt/medium pipeline.
- Lokalny baseline `test_ghostnetwork_narrative`,
  `test_ghostnetwork_delta_audience_bridge` i `test_llm_event_producers`
  przeszedł: 31 testów PASS.
- Pozostały zakres to jawna polityka eventów i significance, projekcja przez
  visibility service, routing high/critical do istniejącego GGPL News slotu,
  precyzyjne CTA, audience fan-out oraz agregacja low events.
- Wykryto realną rozbieżność nazwy: domena zapisuje
  `ghost.connection_created`, a obecny generic narrative branch oczekuje
  `connection_completed`. `ghost.cycle_activated` również nie jest jeszcze
  obsługiwany narracyjnie.
- Sprint podzielono na dwa etapy. Etap I: bezpieczny public bridge BlackNet i
  Googleplex News. Etap II: clan/owner projection, narrative threads, cooldown
  i agregacja.
- Bezwzględny zakaz ciężkiego profilu pozostaje wiążący dla producerów,
  audience resolvera, tasków, logów i testów. Status: `READY FOR
  IMPLEMENTATION — ETAP I NEXT`.
- Przygotowanie było wyłącznie dokumentacyjne; bez zmian runtime, bazy,
  deployu, restartu PM2, commita i pushu.

### 137–138 — rewizja po canonical workerze i publisherze

- Historyczny Sprint 137 nie tworzy już workera, Inboxa, claim/lease, retry ani
  generic walidatora. Dostarczyły je Sprinty 135.4–135.6. Nowy zakres 137 to
  GhostNetwork-specific registry, prompty, task package i semantic validation.
- Potwierdzono rozbieżność registry: zawiera `connection_completed`, podczas
  gdy domena emituje `ghost.connection_created`; brakuje również
  `cycle_activated` oraz polityk `source_scope=ghostnetwork` dla Googleplex News.
- Historyczny Sprint 138 nie tworzy już publishera ani drugiego feedu.
  Istniejący pipeline ma receipts, exactly-once records, audience filtering,
  BlackNet merge, fact-ref suppression i Googleplex slot CAS.
- Nowy zakres 138 to publication lifecycle: TTL, active/inactive, supersession,
  invalidation, thread continuity, significance-aware mix oraz fizyczne
  dispatchery CTA GhostNetwork.
- Granicę CTA doprecyzowano: 136 zapisuje backend-owned action/payload w tasku,
  137 zachowuje je podczas walidacji, a 138 dodaje allowlistę, dispatcher i
  manualny test UI.
- Rejected/dead-letter nie tworzy automatycznie drugiego postu. Ewentualny
  critical fallback musi dzielić publication identity i nigdy nie dotyczy
  owner-analysis AGI.
- Baseline `test_ollama_policy`, `test_ollama_worker`,
  `test_narrative_publications` i `test_llm_publishers`: 59 testów PASS.
- Oba sprinty zachowują bezwzględny zakaz ciężkiego profilu. Statusy:
  `137 READY — AFTER 136`, `138 READY — AFTER 137`.
- Rewizja była dokumentacyjna; bez zmian runtime, bazy, deployu, restartu PM2,
  commita i pushu.

## 2026-09-02 — Sprint 136 Etap I: public event bridge

- W istniejącym `GhostNarrativePublisher` wdrożono wersjonowaną, code-owned
  politykę 18 publicznych eventów wraz z significance, priority, intentem,
  routingiem i CTA. Eventy techniczne, nieznane oraz błędny historyczny alias
  `connection_completed` kończą się jako ignored bez taska.
- Zastąpiono bezpośrednie składanie generic fact bounded projekcją visibility.
  Test regresyjny wykrył i zamknął przeciek `entity_id` przez pole `signal_id`.
- Eligible eventy trafiają do BlackNetu, a high/critical także do istniejącego
  slotu Googleplex `gp-home-world-grid` z CAS i istniejącym promptem; bez nowej
  powierzchni, kolejki, workera lub publishera.
- Canonical task przechowuje backend-owned CTA, intent, priority, content kind,
  selected source ref/version oraz stabilny narrative thread ID. Migracja jest
  addytywna i nie czyta ani nie zapisuje profili graczy.
- Baseline po zmianie: 35 testów PASS. Commit, push, deploy i restart PM2 nie
  zostały wykonane. Etap I oczekuje na pełną regresję lokalną i walidację
  serwerową.

## 2026-09-02 — Sprint 136.1: remediacja runtime ingress i lineage

- Po produkcyjnym dropie zapisanym jako `event_d695f50fdafa44fa` bez tasków
  potwierdzono, że komponentowy publisher nie był osiągalny ze wszystkich
  realnych producentów.
- Dodano jedną fail-open granicę post-commit opartą o canonical persisted
  `event_id` i bounded zakres `state_version`. Podłączono capture effect,
  territory lifecycle, strategic conflicts, cycle creation/lock i transmission.
- Etap I zawsze tworzy redagowaną projekcję `public`, niezależnie od domenowego
  source audience. Dedupe canonical outboxa zachowuje exactly-once przy retry.
- Worker wykonuje bounded recovery event-to-task przed preflightem Ollamy, a
  strict cutover raportuje brakujące media, osierocone taski i zły audience.
- Naprawiono wykryty regresyjnie dubel wejścia do rewardów: konsument nagród
  pobiera wyłącznie persisted domain events i deduplikuje `event_id`.
- Regresja obejmująca ingress 136.1 oraz downstream 137–138: `87 tests / PASS`;
  pełna regresja 36 modułów GhostNetwork: `250 tests / PASS`.
- Bez commita, pushu, deployu, restartu PM2 i bez czyszczenia danych. Status:
  `LOCAL PASS — SERVER REVALIDATION REQUIRED`.

## 2026-09-02 — Sprint 136.1: rewalidacja serwerowa PASS

- Po deployu i restarcie procesów `chaos`, `chaos-territory-worker`,
  `chaos-ollama-worker` oraz `chaos-narrative-publisher` wszystkie procesy
  wróciły do stanu `online`.
- Bounded recovery utworzył dla historycznego `event_d695f50fdafa44fa`
  dokładnie dwa taski `public`: BlackNet i Googleplex News.
- Strict cutover zwrócił `ok=true`; kompletność lineage, source event, media,
  audience i heavy-profile counters mają wartości zerowe dla błędów.
- Nowy realny drop zapisał `event_5b6d395c4b340577` i bezpośrednio utworzył
  task BlackNet po około 137 ms oraz Googleplex News po około 227 ms. Oba taski
  mają `audience_scope=public`.
- Sprint 136.1 oraz Etap I mają status `COMPLETE — SERVER PASS`. Sprint 137 jest
  gotowy do rozpoczęcia; 138 pozostaje zależny od producer-backed candidates
  Sprintu 137.

## 2026-09-02 — Sprint 136.2: audience projection i low-event aggregation

- Wdrożono niezależne projekcje `public`, `clan` i `owner` rozwiązywane z
  bounded canonical event data, bez profili i bez skanu kont.
- Prywatne taski trafiają wyłącznie do audience-filtered BlackNetu; publiczne
  zachowują pełny routing policy, w tym globalny slot Googleplex News.
- Dodano stabilne thread identity dla cyklu, części, maszyny, konfliktu i
  sygnału; prywatne identyfikatory części są hashowane.
- Low-eventy `connection_created` i `machine_progress_changed` otrzymały
  15-sekundowe okno agregacji w istniejącym outboxie. Nowe lekkie mapowanie
  task-source zachowuje lineage wielu eventów do jednego taska.
- Dodano bounded telemetry bridge'a i rozszerzono strict audit o oczekiwane
  audience identities oraz aggregate source links.
- Lokalnie: `253 GhostNetwork tests / PASS`, `59 downstream tests / PASS`,
  heavy-profile guard bez odczytu. Status: `IMPLEMENTED LOCALLY — SERVER
  VALIDATION REQUIRED`; bez commita, pushu, deployu i restartu PM2.

## 2026-09-02 — Sprint 136.2: server partial pass i korekta reconciler-a

- Po deployu strict audit osiągnął `ok=true`, kompletne lineage `8/8`, pełny
  fan-out `public/clan/owner`, zero błędów audience/medium i zero odczytów
  ciężkiego profilu.
- Pierwszy server probe low-eventów pokazał osobne taski `event_count=1`.
  Następnie kontrolowana aktywacja P2/P4 tej samej maszyny `phantom_veil`
  utworzyła eventy oddalone o `5.306 s` i poprawne agregaty `public/blacknet`
  oraz `clan/blacknet`; oba mają `event_count=2` i dwa source links.
- Jednocześnie telemetryka ujawniła ponowne przetwarzanie kompletnych eventów
  przez okresowy reconciler. Dedupe zapobiegał duplikatom, lecz zawyżał
  liczniki i zwiększał presję zapisu na SQLite.
- Reconciler filtruje teraz eventy według kompletności oczekiwanego lineage,
  z uwzględnieniem aggregate source links. Regresja wymaga, aby drugi przebieg
  wykonał zero publikacji i pozostawił telemetrykę bez zmian.
- Targeted regression: `19 tests / PASS`; remediacja nie została jeszcze
  zacommitowana, wypchnięta ani ponownie wdrożona.
- Fan-out, strict lineage, heavy-profile guard i funkcjonalny merge mają
  serwerowy PASS. Pełne zamknięcie 136.2 czeka wyłącznie na redeploy korekty
  reconciler-a, stabilność telemetryki na bezczynności i końcowy strict audit.

## 2026-09-02 — Sprint 136.2: COMPLETE — SERVER PASS

- Serwer zaktualizowano do `5d883ab`; wszystkie cztery procesy runtime wróciły
  do stanu `online`.
- Reconciler potwierdził stan stabilny: `scanned=13`, `processed=0`,
  `incomplete=0`, `skipped_complete=13`. Kompletne eventy nie są ponownie
  publikowane ani doliczane do telemetryki.
- Końcowy strict audit zwrócił `errors=[]` oraz `ok=true`.
- Sprint 136.2 jest zamknięty z lokalnym i serwerowym dowodem; Sprint 137
  został odblokowany.

## 2026-09-02 — Sprint 137.1: model input i voice contract

- Dodano aktywne prompty v2 dla GhostNetwork eventów BlackNet/Cyberner,
  Googleplex world dispatch oraz GhostSignal/radio. Registry przypisuje v2
  wyłącznie nowym taskom.
- Package v2 przekazuje backend-owned `narrative_intent`, `event_family`,
  `significance`, `tone_hint`, bounded thread context, projected facts oraz
  limity medium. Nie przekazuje raw owner/clan identity, outbox ID ani source
  event ID.
- Dodano addytywną zgodność pełnych tuple polityk v1. Stare taski pozostają
  claimowalne i publikowalne do naturalnego opróżnienia bez zmiany promptu i
  bez masowej regeneracji.
- Registry verification raportuje active/legacy-compatible policies, a status
  kolejki `ready_by_prompt_version` dla bezpiecznego server cutoveru.
- Testy obejmują pełną macierz event/medium, package z realnego producenta,
  brak raw identity, agregat, fail-closed brak intent/family/significance oraz
  udany claim historycznego v1.
- Regresja: `253 GhostNetwork tests / PASS` po core cutover oraz `66 targeted
  policy/worker/publication tests / PASS` po finalnych limitach medium.
- Status: `137.1 LOCAL PASS — SERVER VALIDATION REQUIRED`; bez commita, pushu,
  deployu i restartu PM2. Sprint 137.2 nie został rozpoczęty.

## 2026-09-02 — Sprint 137.1: produkcyjny probe v2 i minimalny package v3

- Server verify i strict cutover dla commita `36b8dab` przeszły: registry
  `33 active + 25 legacy-compatible`, kompletne lineage i zero ineligible.
- Realny `ghost.part_discovered` utworzył cztery pełne łańcuchy v2. Tylko
  `clan/blacknet` został zaakceptowany; owner i Googleplex użyły event ID jako
  fact ref, a public BlackNet ujawnił fragment public entity ID. Wszystkie trzy
  niebezpieczne wyniki zatrzymał validator.
- Rekonstrukcja requestu była zgodna z attempt hash i potwierdziła, że model
  otrzymywał `event_id`, `cycle_id`, `public_entity_id` oraz canonical fact ID,
  mimo braku narracyjnej potrzeby.
- Aktywne prompty podniesiono do v3. Model dostaje task-local aliases `f01`,
  minimalne narrative-safe facts oraz wyłącznie pola sterujące narracją.
  Canonical identity i fixed CTA pozostają w backendzie.
- Validator mapuje zaakceptowane aliasy z powrotem na canonical fact IDs przed
  zapisem candidate. Schema ogranicza refs do aliasów taska i wymusza null CTA.
- Kompatybilność jest addytywna: taski v1 oraz v2 pozostają rozwiązywalne,
  claimowalne i publikowalne przez pełne tuple wersji.
- Regresje: `64 policy/worker/publication/cutover tests / PASS` oraz
  `64 producer/runtime/publisher tests / PASS`. Status v3: lokalny PASS,
  wymagany commit, deploy i ponowny producer-backed server probe.

## 2026-09-03 — 137.pre.1: Shared Semantic Input Layer

- Audyt minimalnego v3 wykazał, że firewall identyfikatorów działał, ale model
  dostawał tylko alias `f01` bez treści canonical fact. Cofnięto zgodę na
  kontynuowanie tuningu 137 i ustanowiono bramkę 137.pre.1.
- Dodano wspólny, bounded kontrakt `chaos-llm-semantic-input-v1`: oddzielne
  `semantic_facts` i control metadata, deterministic domain converter,
  backendową provenance oraz fail-closed technical-ID firewall.
- GhostNetwork jako pierwszy pełny consumer tworzy proste statements dla
  wszystkich aktywnych event families. Audience projection następuje przed
  LLM: public nie dostaje części/maszyny, clan wyłącznie canonical label
  własnego klanu, owner dozwolone labels części, maszyny i klanu.
- Packer v3 serializuje domain-authored semantics oraz lokalne aliasy lineage;
  nie rekonstruuje już Ghost semantics z globalnej listy pól. V1/v2 pozostają
  rozwiązywalne i claimowalne według historycznego kontraktu.
- Dodano konserwatywną inferencję `city/country/country_code` z OSM tags oraz
  bounded retention przez scan response, frontend target, `mark_target`,
  canonical target/capture anchor i finalny semantic package. Konflikt albo
  brak dowodu oznacza brak pola; koordynaty nigdy nie służą do geocodingu.
- Read-only `scripts/audit_semantic_input.py` pokazuje ścieżki
  canonical→semantic→dokładny model input bez wywoływania Ollamy i bez mutacji.
- Producer-backed lokalny test `part_discovered` potwierdza lokalizację,
  canonical labels, rozdział public/clan/owner, brak technicznych ID, bounded
  package, zachowane fact lineage oraz heavy-profile counters równe zero.
- Targeted gate: `86 tests / PASS`; osobna regresja BlackNet/Googleplex/AGI
  producers i endpoints: `38 tests / PASS`; map aim/hot-path retention:
  `19 tests / PASS`. Pełne discovery wykonało `1281` testów i ujawniło `11`
  istniejących/order-dependent problemów poza zakresem 137.pre.1; pięć z nich
  przeszło po izolacji, sześć pozostaje odtwarzalnych w niezmienianych
  kontraktach map animation, operation cancel, profile snapshot, catalog JS i
  Ghost Exchange.
- Commit, push, deploy i restart PM2 nie zostały wykonane. Status:
  `137.pre.1 LOCAL PASS — SERVER EXIT GATE REQUIRED`; Sprint 137 pozostaje
  zatrzymany do strict audytu nowego rzeczywistego `part_discovered`.

## 2026-09-03 — 137.pre.1: server exit gate i naprawa czyszczenia skanu

- Produkcyjny `scripts/audit_semantic_input.py --strict` przeszedł dla czterech
  tasków `part_discovered`: `ok=true`, `errors=[]`, lokalizacja Zakopane,
  rozdzielone projekcje public/clan/owner oraz zero technical identifier leaks.
- Wydruk audytu w kanale kopiowania pokazuje mojibake polskich znaków; przed
  uznaniem tego za dane wejściowe modelu trzeba rozróżnić zawartość UTF-8 od
  kodowania terminala lub kanału kopiowania.
- Odtworzono frontendową regresję po `scan -> Wyczyść scan`: Leaflet 1.9.3
  wchodził w `DomEvent.off(undefined)` dla markera bez `_icon`, przerywając
  pętlę i pozostawiając kolejne markery na mapie.
- `removeMapLayerSafe` oddaje Leafletowi usunięcie aktywnej warstwy przed
  czyszczeniem listenerów, a wąski guard kończy usuwanie już niekompletnego
  markera. Pętla czyszczenia izoluje awarię pojedynczej warstwy i zachowuje ją
  do ponowienia bez blokowania pozostałych.
- Kontrakt hot-path: `10 tests / PASS`. Szerszy plik map-loader nadal zawiera
  niezależną, wcześniej zidentyfikowaną regresję kontraktu animacji motocykla.

## 2026-09-03 — odmrożenie Sprintu 137 po 137.pre.1

- Produkcyjny strict semantic audit został przyjęty jako exit gate 137.pre.1:
  cztery rzeczywiste taski `part_discovered`, kompletne statements i location,
  poprawne projekcje public/clan/owner, `errors=[]` oraz zero technical ID.
- Sprint 137 otrzymał status `ACTIVE`; prace wracają do 137.1, czyli generacji
  i walidacji rzeczywistego outputu modelu. PASS packera nie został błędnie
  uznany za PASS candidate.
- Plan 137 traktuje odtąd `chaos-llm-semantic-input-v1`, domain converter,
  audience projection, backend provenance, local aliases i technical-ID
  firewall jako obowiązkowy fundament wszystkich aktywnych rodzin.
- Plan 138 dziedziczy ten kontrakt: publisher nie rekonstruuje semantyki ani
  location z tekstu, canonical lineage pozostaje backend-only, a read model i
  CTA mogą ujawnić wyłącznie audience-safe projekcję.
- Sprint 138 pozostaje zablokowany na zaakceptowanych producer-backed
  candidates ze Sprintu 137, nie na budowie semantic input.

## 2026-09-03 — Sprint 137.1: zamknięta lokalna bramka generacji

- Dodano read-only `scripts/audit_narrative_generation.py`, który dla eventu
  albo taska łączy task package i request hash z ostatnim attemptem oraz
  candidate. Raport pokazuje semantic facts i finalne title/body/tone.
- Strict gate odrzuca brak kompletnego producer fan-outu, brak attemptu lub
  candidate, niezgodny hash/prompt/audience/medium, stan inny niż completed,
  quarantine/rejection oraz uszkodzone canonical fact lineage.
- Bramka celowo wymaga ręcznej oceny języka i głosu medium; accepted schema nie
  jest automatycznie dowodem jakości BlackNet/Googleplex/Cyberner.
- Testy pokrywają accepted PASS, quarantine z rzeczywistym powodem, ready bez
  generacji i event bez oczekiwanych tasków. Łączna regresja
  policy/worker/semantic/audit: `51 tests / PASS`.
- Status: `137.1 LOCAL PASS — SERVER GENERATION GATE REQUIRED`. 137.2 nie jest
  rozpoczęty, a 138 pozostaje zablokowany do accepted producer candidates.

## 2026-09-03 — Sprint 137.1: techniczny PASS v3, korekta głosu v4

- Produkcyjny generation audit v3 potwierdził pełny fan-out czterech tasków
  `part_discovered`, completed attempts, zgodne request hashes, accepted
  candidates i kompletne lineage (`ok=true`, `errors=[]`).
- Ręczna ocena odrzuciła wynik: clan dopisał własność lokalizacji, owner zrobił
  z powiązanej maszyny sprawcę odkrycia, BlackNet brzmiał raportowo, a tytuł
  Googleplex urwał nazwę `Zakopane` do `Zakopn`.
- Wprowadzono addytywne prompty v4. Semantic converter nadaje wiążące role:
  `lokalizacja zakotwiczenia zdarzenia`, `klan odbiorcy` i `maszyna powiązana z
  elementem`. Prompt zabrania dopowiadania własności, sprawstwa i działania.
- BlackNet ma najwyżej dwa krótkie zdania przechwytu z 2108 bez mechanicznego
  echa statement. Googleplex ma krótki tytuł bez nazw własnych i pełne nazwy
  wyłącznie w leadzie.
- Cutover zachowuje v1/v2/v3. Historyczne v3 nadal używa semantic system prompt
  i minimalnego package; nowe taski dostają v4. Audyty wybierają wyłącznie
  aktywną rodzinę promptów, aby stary v3 nie mógł zaliczyć bramki v4.
- Lokalny targeted gate v4: `52 tests / PASS`; wymagany jest nowy
  producer-backed server probe i ręczny voice PASS przed rozpoczęciem 137.2.

## 2026-09-03 — Sprint 137.1: produkcyjny fail głosu v4 i kontrakt v5

- Deploy `e852f8d` oraz semantic audit nowego `part_discovered` przeszły:
  cztery taski v4, pełny public/clan/owner fan-out, poprawne role, Washington,
  zero technical identifier leaks.
- Pierwszy ukończony public/BlackNet candidate był poprawny faktograficznie i
  accepted, ale nadal stanowił neutralny raport niemal kopiujący statement:
  `Odkryto ukryty element sieci GhostNetwork`. Ręczna bramka v4 została
  odrzucona bez czekania na pozostałe warianty.
- V5 wymusza dla BlackNet tytuł `PRZECHWYT // ...` oraz body zaczynające się od
  `...`. Pierwszy request z regexami JSON Schema dostał produkcyjne
  `ollama_http_500`; Googleplex bez regexów wszedł w processing.
- Regexy usunięto z transportowego schema Ollamy. Ten sam kontrakt jest
  egzekwowany backend-only przez `voice_contract`, więc neutralny raport nadal
  nie może uzyskać accepted, a task w `retry_wait` może zostać wznowiony.
- V1–v4 pozostają addytywnie zarejestrowane; v3/v4 zachowują semantic package.
  Audyty śledzą tylko aktywną rodzinę v5.
- Log produkcyjny ujawnił restarty workera po `database is locked` na `BEGIN
  IMMEDIATE`. PM2 odzyskuje proces i taski postępują, ale przypadek przeniesiono
  jawnie do failure/recovery gate 137.3.
- Lokalna bramka policy/worker/semantic/audit/publication v5: `72 tests / PASS`.
  Wymagany jest ponowny audit istniejącego producer-backed eventu po retry.

## 2026-09-03 — Sprint 137.1: transport v5 PASS, konkretność v6

- Wszystkie trzy BlackNet taski v5 wyczerpały retry i przeszły do dead letter z
  `ollama_http_500: invalid JSON schema in format` przed aktywacją hotfixu.
  Googleplex v5 przeszedł i zwrócił poprawną, pełną depeszę dla Las Vegas.
- Read-only probe tego samego BlackNet taska na `be1bdf3` potwierdził naprawę:
  Ollama przyjęła schema, a backend zwrócił `accepted` z poprawnym canonical
  lineage i fixed CTA.
- Model skopiował jednak dosłownie przykład z promptu (`PRZECHWYT // UKRYTY
  WĘZEŁ`, `...struktura wyszła z cienia`) i pominął dostępne wyróżniki
  `University Medical Center` oraz `Las Vegas`. V5 nie przeszedł ręcznej bramki
  konkretności.
- V6 usuwa gotowy przykład. Jeżeli model widzi entity labels/location, musi użyć
  co najmniej jednej pełnej wartości. Backend-only `voice_contract` egzekwuje to
  błędem `voice_semantic_detail_missing`; prefixy BlackNet pozostają wymagane.
- V1–v5 zachowują pełną zgodność registry, a v3–v5 semantic package. Targeted
  policy/worker/semantic/audit/publication: `72 tests / PASS`. Wymagany jest nowy
  producer-backed event v6 do końcowej oceny wszystkich czterech wariantów.

## 2026-09-03 — Sprint 137.1: techniczny PASS v6, minimalny kontekst v7

- Produkcyjny event v6 przeszedł pełny fan-out czterech tasków, attempt numer 1
  oraz strict audit (`ok=true`, `errors=[]`). Transport, lineage i walidacja
  techniczna są poprawne.
- Ręczna bramka głosu odrzuciła trzy warianty BlackNet. Model kopiował nazwę
  roli semantycznej, powtarzał lokalizację, skrócił nazwę `Acquisition Drive` i
  dopowiedział niewynikające z faktów znaczenie dla bezpieczeństwa. Googleplex
  przeszedł ręczną ocenę.
- V7 minimalizuje input `part_discovered` per audience: public widzi cel, clan
  nie dostaje nazwy klanu odbiorcy, a owner dostaje tylko cel i nazwę części —
  bez powiązanej maszyny oraz klanu.
- `POI-18D194` jest prawidłową frontendową nazwą obiektu świata i może wystąpić
  w body albo title. Nie jest traktowane jak techniczny identyfikator i nie
  może być skracane. Obowiązkowy konkret w body zapobiega nadal pustej depeszy.
- BlackNet v7 ma budżet `48/220`, jedną krótką wypowiedź po prefiksie `...` i
  backendową kontrolę obecności szczegółu w body. Registry zachowuje taski
  v1–v6, w tym semantic package v3–v6.
- Lokalna regresja policy/worker/semantic/audit/publication/producer v7:
  `73 tests / PASS`. Wymagany jest ostatni producer-backed server probe oraz
  ręczny PASS wszystkich czterech wariantów przed zamknięciem 137.1.

## 2026-09-03 — Sprint 137.1: techniczny PASS v7, canonical sentence v8

- Produkcyjny event `event_ed93067dc1c2fb2b` wygenerował cztery taski v7.
  Wszystkie zakończyły się w pierwszym attempt, a strict generation audit
  zwrócił `ok=true`, `errors=[]` i pełne lineage.
- Public, clan i owner BlackNet były krótkie, polskie, bez identyfikatorów oraz
  nieudowodnionych skutków. Googleplex nie przeszedł ręcznej bramki: model
  zmienił miejsce `Barnard Stamp Company` we właściciela elementu. Owner nie
  użył dostępnej nazwy części `Influence Relay`.
- V8 składa dla `part_discovered` jedno audience-safe zdanie canonical po
  stronie backendu. Model nie widzi już osobnych encji i location wymagających
  interpretacji. Owner dostaje w tym zdaniu nazwę części, public/clan wyłącznie
  dozwolony kontekst miejsca.
- Backend wymaga nazwy części w body ownera i odrzuca nieudowodnione formy
  własności przez `voice_unsupported_relation`. Taski v1–v7 pozostają
  addytywnie zarejestrowane, a v3–v7 zachowują semantic package.
- Lokalna regresja v8: `74 tests / PASS`. Do zamknięcia 137.1 pozostaje nowy
  producer-backed server probe oraz ręczna ocena czterech kandydatów v8.

## 2026-09-03 — Sprint 137.1: produkcyjny fail konkretu v8 i kontrakt v9

- Produkcyjny event `event_e3b8955692670276` utworzył pełny fan-out czterech
  tasków v8; wszystkie zakończyły pierwszy attempt. Googleplex został accepted
  i przeszedł ręczną ocenę.
- Clan, owner i public BlackNet zwróciły ten sam ogólny tekst bez `Chez Marlene`;
  owner pominął również `Restoration Engine`. Validator poprawnie ustawił
  `rejected` z `voice_semantic_detail_missing`, a strict generation audit
  zakończył się `ok=false`.
- V9 zachowuje jedno canonical zdanie i dodaje tylko jedną jawną
  `required_phrase`: miejsce dla public/clan albo nazwę części dla ownera.
  Prompt wymaga dokładnego użycia jej w body; backend nadal egzekwuje ten sam
  warunek i nie przepuszcza tekstu ogólnego.
- V8 pozostaje kompatybilną polityką legacy z niezmienionym model input. Nowe
  taski GhostNetwork używają v9. Lokalna regresja policy/worker/publication/audit:
  `64 tests / PASS`; wymagany jest nowy producer-backed server probe v9.
