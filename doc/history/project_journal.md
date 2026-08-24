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
