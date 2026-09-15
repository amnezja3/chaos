# Sprint 141 — Control Loop: pełna naprawa hakowania gracza

Data: 2026-09-14. Punkt odniesienia kodu: `96dec35`.

Aktualizacja zakresu: 2026-09-15 — pozycja aktora po teleportacji.

Status: **W REALIZACJI — 141.2 zamknięty decyzją autora; 141.3 rozpoczęty (15 IX)**.

Checkpoint techniczny po odbiorze gameplayu: lokalny pakiet Pickera/capture
opisany w [runbooku](../runbooks/sprint_141_3_player_target_selection.md).
Picker i player-mode gonna-win czytają bounded canonical context; zachowano
śledzenie aktywnego celu poza widocznością/zasięgiem. Dostęp, terminal target
i trwały receipt są atomowe. Replay po wygaśnięciu nie przyznaje nowego grantu.
98 różnych testów Python i dwa zestawy JS PASS. Bez deployu.
**141.3 nadal otwarty:** `/hack-action` oraz legacy launch queue/risk_events/
system_messages pozostają sprzężone z profilem i wymagają osobnego cutover.
Nie usuwać samego zapisu profilu, bo zgubiłoby to kolejkę i zdarzenia ryzyka.

Aktualny odbiór 15 IX: migracja security wykonana przez operatora dla 31 kont,
verify READY również po uruchomieniu czterech procesów. Autor potwierdził
wybór intruza, alarm, blokady znajomego/klanu i zachowanie postępu między celami.
Zatwierdzona zasada: po opuszczeniu terytorium cel znika z mapy, ale pozostaje
w Victim Pickerze z odległością; rozpoczęty hack można kontynuować również
poza zasięgiem. Nowe/ponowne oznaczenie wymaga bieżącej widoczności i zasięgu.
Poniższe wcześniejsze checkpointy lokalne opisują stan sprzed tego odbioru.

Zamknięcie 141.2 opiera się na wynikach migracji przekazanych przez operatora,
lokalnych testach oraz odbiorze autora: aktualna mapa po teleportacji, wtargnięciu
i objęciu polem; alarm właściciela potwierdzony. Nie jest deklaracją pełnego
browser E2E. Pozostałe próby ruchu w toku, pełnego audience, recovery i pomiary
opóźnień przechodzą do walidacji 141.7; picker i uprawnienia celu do 141.3.

Pierwszy pakiet 141.3: aktywny grant zachowuje terminy i klucz użycia narzędzi
przy ponownym/równoległym przyznaniu. Sprawdzenie i zapis są w jednej transakcji.
To ograniczona naprawa: trwały replay po wygaśnięciu dostępu, cooldown i luka
grant → receipt operacji nadal wymagają domknięcia razem z autoryzacją capture.

Autor potwierdził przejście scenariusza pierwszego pakietu: odliczanie po
reloadzie, jednokrotne użycie Kickera i rozdzielenie dostępów A/B.

Kolejny pakiet 141.3 (lokalny): wybór celu z mapy używa wspólnej bounded
projekcji aktorów, canonical position/capability i blokad visibility/range/
self/friend/clan. Zapis wyłącznie w target runtime zachowuje postęp przy retry.
Dodano integrity-gated projekcję player_security; **przed uruchomieniem wymaga
jawnego backfill**. [Procedura i zakres](../runbooks/sprint_141_3_player_target_selection.md).
49 różnych testów Python PASS (46 w pierwszym przebiegu; po rozszerzeniu
12 testów selection/identity, w tym trzy dodatkowe). Nadal otwarte: picker,
alternatywne wejście target security, capture i trwały replay grantu.

[Audyt z 15 IX](../audits/sprint_141_player_hacking_audit_2026_09_15.md)
zawiera przegląd kodu i izolowane reprodukcje A01–A08. Uzupełniono pełne
requesty Flask dla pakietu opisanego poniżej. Pozostałe transakcje, baseline
całej ścieżki i browser E2E nadal otwarte; 141.1 nie ma pełnego zamknięcia PASS.

### Checkpoint implementacji — 15 IX: Player Access i Log Reader

Odbiór 15 IX po migracji: autor potwierdził aktualne awatary po teleportacji,
wtargnięciu i objęciu polem. Zgłoszony brak alarmu właściciela naprawiono
lokalnie: wspólny atomowy area event + warning, ID per zdarzenie zamiast
dożywotniej deduplikacji treści, zachowany cooldown 60 s i wykluczenie własnego
klanu. Static intrusion korzysta z ograniczonej projekcji i również alarmuje.
18 testów Python i dwa zestawy JS PASS. Bez nowej migracji. Autor potwierdził
alarm w grze po wejściu Dobrego Robota: „alarm potwierdzony, mamy to”.
Poprawka alarmu odebrana. Nie rozszerzać odbioru awatarów i alarmu na wszystkie
scenariusze opóźnionych odpowiedzi, ruchu w toku i pełnego audience.

Checkpoint 141.2 — 15 IX: usunięto pełne profile z listy aktorów. Ograniczona
projekcja pobiera canonical position wraz z wersją, identity/capability i awatar;
cel pochodzi z target runtime. JS odrzuca starsze pozycje i snapshot rozpoczęty
przed nowszą deltą. **Przed uruchomieniem tego pakietu wymagany jest jawny
backfill projekcji awatarów**: [procedura](../runbooks/sprint_141_2_map_actor_projection.md).
Migrację serwera autor wykonał później 15 IX: 31 projekcji, verify READY.
Ruch w toku, pełne audience i pomiar opóźnień pozostają w walidacji 141.7.
Walidacja końcowa tego pakietu: 46 testów Python i trzy zestawy JS PASS.

Odbiór autora 15 IX: Intruder Kicker zadziałał w grze. Arsenal Cleaner
wyświetlił dla RUN.BASIC NO CHANGE / SILENT przy szansie 80% i rzucie 90:
prawidłowa nieudana próba. Udane usunięcie aplikacji ma dowód w testach
lokalnych, ale nadal czeka na odbiór w grze. Ten odbiór nie zamyka pełnego 141.

Kolejny checkpoint 15 IX — Arsenal Cleaner: A01 usunięty lokalnie przez
wycofanie zbędnego zapisu ciężkiego profilu, odczyty kanonicznego inventory
i ograniczonych projekcji statystyk. Uninstall oraz receipt mają wspólną
transakcję z rollback i ochroną przed równoległym podwójnym efektem.
19 testów read paths/session precommit PASS, w tym udany Cleaner na dwóch
profilach ≥35 MiB, awaria po uninstall, konkurencja, no-apps i failed roll.
Pełny lifecycle nadal otwarty: delty pulpitu ofiary, recovery odpowiedzi oraz
powiadomień po commicie. Nie potwierdzono historycznych efektów błędu na serwerze.
Autor przekazał pozytywny odbiór pozostałych narzędzi przez graczy; brak znajomych
pies1 wyjaśnia poprawny wynik Friend Kickera. Bez rozszerzania tego odbioru
na nieprzetestowane scenariusze ani zamknięcie 141.

- Panel korzysta tylko z pięciu jawnych executorów post-hack. Suite i inne
  aplikacje nie trafiają do tej listy; tool/use odrzuca nieobsługiwany tool ID.
- Odczyt dostępu korzysta z integrity-gated identity obu kont i pięciu
  indeksowanych sprawdzeń `PlayerInventoryStore.has_app`, bez profili/inventory dump.
- Jedna bramka instalacji obejmuje tool/use oraz security update/preset;
  odmowa następuje przed pełnym odczytem do guarded mutacji security.
- Log Reader czyta pięć najnowszych canonical system messages, bez konsumowania
  i bez payload JSON. Title do 256 znaków, body do 4096; UI oznacza skrócenie.
- Naprawiony `id is not defined` w rendererze Log Readera; treść pozostaje escapowana.
- `tools/run_isolated_tests.py` uruchamia wybrane moduły z cwd, SQLite i sesjami
  w temp. Nie importować aplikacji do testów z cwd rzeczywistej bazy.

Walidacja: 6 testów pełnych requestów `test_player_hack_read_paths` PASS:
mały/mały, ≥35 MiB/mały, mały/≥35 MiB, ≥35 MiB/≥35 MiB; błędy instalacji,
niepasujące narzędzie, niewłaściwa ofiara, expiry, stara generacja i uszkodzona
projekcja. Test wymusza brak `get_profile`, `get_profile_with_revision` i
`sync_session_profile`, sprawdza zero profile_bytes oraz brak konsumpcji logów.
Osobny istniejący test reserve → transfer → complete Financial Sniffer PASS.
JS `test_player_hack_log_reader` i składnia terminal.js PASS; diff check PASS.

Nie jest to zamknięcie 141.4 ani 141.5: wykonanie pozostałych narzędzi, A01
Cleaner, atomowość efektów, pozycje 141.2 i responsywność pozostają do naprawy.
Pozostałe gałęzie tool/use nadal mają ciężkie odczyty. Nie wykonano deployu,
browser QA ani pełnego E2E. Cache terminal.js podniesiony w trzech dokumentach.

## 1. Cel i wynik użytkowy

### Rozszerzenie 15 IX — Intruder Kicker (decyzja autora)

Szóste narzędzie post-hack: `intruderKicker`, kupowane i instalowane przez
istniejącą ścieżkę Googleplex, również przez terminalowe `pkg`.
Cena podana przez autora: **7500 HC**. Przyjęte i zakomunikowane założenia
implementacji: poziom 1, respekt 0, pewne wypchnięcie po spełnieniu warunków,
jedno użycie na aktywny dostęp PvP. Autor podał cenę; pozostałe parametry
są założeniami implementacji, a nie osobnym potwierdzeniem balansu.

- Użycie wymaga aktywnego dostępu PvP, instalacji i celu różnego od siebie.
  Cel musi aktualnie znajdować się na aktywnym/okrążonym, nadal kontrolowanym
  terytorium właściciela używającego narzędzia. Sam grant nie daje prawa do
  wyrzucania gracza z dowolnego miejsca mapy.
- Geometria ma korzystać z istniejącego
  `resolve_first_respawn_outside_controlled_territory`, z domyślnym marginesem
  180 m i sprawdzaniem nakładających się kontrolowanych stref. Nie uruchamiać
  rejestracji, respawnu konta ani innej ścieżki resetującej stan gracza.
- Źródło bieżącej pozycji i zapis efektu: `PlayerPositionStore`; źródło
  granic: kanoniczne `player_areas`. Bez pełnego profilu i fallbacku do jego
  historycznych współrzędnych. Niepełny zestaw geometrii ma kończyć się
  kontrolowaną odmową, a nie uznaniem nieznanej przestrzeni za wolną.
- Przed commitem ponownie sprawdzić pozycję/granice/uprawnienia; ruch celu,
  wygaśnięcie dostępu albo zmiana sesji nie mogą prowadzić do stale overwrite.
  Receipt, pozycja i trwałe zdarzenia wyniku wymagają atomowości/recovery.
- Po wypchnięciu intruz otrzymuje wersjonowaną pozycję, właściciel traci
  nieaktualny marker intruza; pozostałe audience podlegają dotychczasowym
  regułom widoczności. Bez ujawniania nowej lokalizacji nieuprawnionym graczom.
  Wiąże się to bezpośrednio z naprawą teleportu w 141.2.
- Wynik okna: wypchnięto / odmowa z powodem / nieudana próba, jeśli autor
  ustali losowość. Testować granice, nakładanie, brak własnego terytorium,
  cel poza terenem, retry, konkurencyjny ruch, utratę delty i heavy profile.

Stan lokalny: katalog Googleplex/Player Access, executor i okno wyniku dodane.
Zapis pozycji, receiptu z odpowiedzią oraz dwóch delt jest atomowy. Powtórzenie
zwraca poprzedni wynik bez kolejnego ruchu. W tej samej transakcji sprawdzane
są instalacja, aktywny grant, aktualna pozycja i geometria. Niepełna geometria
(limit 1000 osiągnięty lub błędny obszar) blokuje wykonanie. Intruz otrzymuje
prywatną wersjonowaną pozycję; właściciel zdarzenie usunięcia markera bez nowej
lokalizacji. Lista aktorów czyta pozycję z PlayerPositionStore, bez fallbacku.
Jej pozostałe ciężkie odczyty profili nadal wymagają cutover w 141.2.

Walidacja: 7 testów geometrii/rejestracji, 5 testów Kickera (HTTP, dwa profile
≥35 MiB, rollback delt/pozycji/receiptu, konkurencja, replay, odmowy i odświeżenie
markera), 10 regresji session precommit PASS. JS wyniku i prywatnego zdarzenia,
marker hitbox, Financial Sniffer PASS. Brak browser E2E i zakupu na serwerze.
Otwarte 141.2/141.7: zderzenie z lokalną animacją/już wysłanym commitem travel,
szersze audience obserwatorów oraz recovery po utracie feedu. Ten checkpoint
nie zamyka całej synchronizacji pozycji ani Sprintu 141.

Uzupełnienie checkpointu 15 IX: po zgłoszeniu pustego Financial Sniffera
naprawiono również niezdefiniowane `id` w jego rendererze. Błąd wyświetlania
potwierdzonego wyniku nie jest już raportowany jako błąd komunikacji.
`tests/js/test_player_hack_financial_result.js` sprawdza render, escapowanie,
błąd renderera, HTTP i sieci oraz brak automatycznego ponowienia; PASS.
Nie zweryfikowano transakcji ze zrzutu na serwerze ani browser QA.
Istniejący `refreshToolbarProfile()` po Snifferze nadal wymaga odchudzenia
w ramach hot path sprintu, z zachowaniem wersjonowania salda.

Domknąć hakowanie obcego gracza, w szczególności intruza z obcego klanu,
jako jedną spójną mechanikę gameplayu. Gracz ma móc wykryć właściwego intruza,
wybrać go, przełamać zabezpieczenia dostępnymi aplikacjami, otrzymać czasowy
dostęp, użyć pasujących narzędzi i zobaczyć rzeczywisty wynik wraz z efektami.
Cała ścieżka ma działać na desktopie i urządzeniach mobilnych.

```text
wykrycie intruza → marker / Victim Picker → wybór właściwego gracza
→ weryfikacja prawa do ataku → przełamywanie zabezpieczeń / operacja
→ potwierdzony dostęp → Player Hack Access → właściwe narzędzie
→ kanoniczny efekt i wynik → aktualizacja obu stron → wygaśnięcie / cooldown
```

Naprawa obejmuje wszystkie ogniwa, a nie tylko CSS panelu albo pojedynczy
endpoint. Nie każdy efekt narzędzia jest długotrwałą operacją i nie każdy
produkuje plik. UI ma rozróżniać postęp ataku, czas dostępu, wynik użycia
narzędzia i stan operacji. Nie tworzymy fikcyjnych operacji, plików ani nagród.

## 2. Stan wejściowy i jakość dowodu

**Zgłoszenie autora:** część narzędzi zwraca błędy, część nie pasuje do panelu,
panel jest niedopracowany i nieresponsywny. Konkretne błędy wymagają odtworzenia
i przypisania do narzędzia, wejścia, odpowiedzi i miejsca awarii.

**Zgłoszenie autora z 15 IX:** po teleportacji aktor nadal jest widziany
w starej pozycji. Ciężki profil jest podejrzewaną przyczyną, nie potwierdzonym
root cause. Trzeba ustalić, czy opóźnia się zapis pozycji, odczyt/projekcja,
dostarczenie delty czy aktualizacja markera, oraz czy obserwacja dotyczy
własnej mapy, mapy innego gracza lub obu. Problem wchodzi do etapu 141.2.

**Potwierdzone statycznym przeglądem kodu, bez uruchomienia E2E:**

- `public_pro_system_tools()` iteruje cały `PRO_SYSTEM_TOOLS`; dostępność
  wyprowadza z instalacji. Ten sam katalog zawiera m.in. `victimPicker`
  i `territoryControl`, czyli aplikacje o innym przeznaczeniu.
- `serialize_player_hack_access()` korzysta z tego zestawu i odczytuje pełne
  profile atakującego i ofiary nawet przy prezentacji aktywnego dostępu.
- `api_player_hack_tool_use()` obsługuje pięć konkretnych narzędzi, ale jego
  końcowy fallback zwraca `success: true` z komunikatem placeholdera.
- `systemLogReader` czyta lustrzane `system_messages` z pełnego profilu;
  wymaga uzgodnienia z kanonicznym `SystemMessageStore`.
- `mark_player_target()` nadal używa `sync_session_profile()` i odczytu profilu
  celu; ciężkie odczyty są też w gałęziach narzędzi. To miejsca wymagające
  naprawy zgodnie z kontraktem 130.11+, nie dowód zmierzonego czasu produkcji.
- `security/update` i `security/preset` sprawdzają dostęp, lecz w samych
  handlerach nie ma sprawdzenia instalacji `securityPanelProxy`. Audyt musi
  objąć pełny łańcuch autoryzacji oraz bezpośrednie wywołanie tych tras.
- Financial Sniffer ma już trwałe usage i klucz transferu walletu; nie wolno
  zastąpić ich lokalną blokadą przycisku. Friend Kicker i Arsenal Cleaner
  wymagają sprawdzenia kolejności efekt → receipt przy równoległych żądaniach.
- Panel ma stałe pozycjonowanie `right: 18px`, `bottom: 122px`, `width: 320px`;
  renderuje przyciski całego otrzymanego zestawu. Ocena faktycznego overflow,
  dostępności i okien wyników wymaga przeglądarki.
- Timer klienta odejmuje sekundy; odpowiedzi narzędzi odświeżają panel.
  Wyścigi odpowiedzi, zmiana ofiary i powrót z tła wymagają testów zachowania.

Istniejące komentarze TODO nie dowodzą braku dostępu: kod wywołuje już
`player_hack_access_store.grant_access()` w `gonna_win`. Audyt ma prześledzić
rzeczywistą gałąź i jej callerów, zamiast implementować drugi grant.

Nie wykonano reprodukcji, pomiarów, testów ani odczytu serwera w ramach
sporządzenia tego planu. Historyczne PASS nie stanowią odbioru Sprintu 141.

## 3. Kontrakty i historia do zachowania

Przed zmianą danego ogniwa przeczytać jego aktualny kontrakt, implementację,
testy oraz późniejsze sprostowania w journalu. Punkty wejścia:

- [Przekazanie projektu](../runbooks/handoff_project_2026_09_14.md)
  i [mapa hot paths](../runbooks/handoff_hotpaths_2026_09_14.md).
- [Wiążący kontrakt profilu 130.11+](../architecture/profile_hot_path_contract_130_11_plus.md).
- [Historyczny rozwój player actors i post-hack tools](../gameplay/action_player.md)
  oraz [audyt Victim Pickera](../audits/victim_picker_audit.md).
  Ich odwołania do profilu i dawnych placeholderów wymagają porównania
  z późniejszymi store’ami; nie są poleceniem przywrócenia legacy.
- [Kontrakt aplikacji](../gameplay/app_contract.md),
  [typy źródeł](../gameplay/source_type_mapping.md),
  [operacje](../gameplay/operations.md), [pliki](../gameplay/file_model.md),
  [ekonomia](../gameplay/data_economy.md) i [ryzyko](../gameplay/risk_events.md).
- [Marked Target 130.10.2](sprint_130_10_2_marked_target_hot_path.md),
  [regresje po 130.10–130.12](../hardbugfix/post_130_10_130_12_runtime_regressions_sprint_130_12_2026-08-26.md),
  [operacje → pliki → GX 135.5](../hardbugfix/heavy_profile_operation_files_gx_regression_sprint_135_5_2026-08-30.md).
- [Marker/menu identity](../hardbugfix/scan_marker_menu_identity_leaflet_dispatch_sprint_138_getway_3_5_2026-09-07.md)
  i [Operation Center / Leaflet](../hardbugfix/138_operation_center_cache_signature_canvas_bounds_2026-09-09.md).
- [Wersjonowanie stanu](../architecture/state_version_contract.md),
  [delta](../architecture/delta_event_schema.md),
  [inwentarz sesji](../architecture/session_generation_endpoint_inventory.md).
  Historyczny opis logowania czytać z naprawą POST index z 13 IX;
  nie cofać obecnych wyjątków i guardów.

## 4. Zakres i kolejność realizacji

Etapy 141.1–141.7 są checkpointami jednego sprintu. Samo zamknięcie panelu
lub backendu nie oznacza zakończenia Sprintu 141.

### 141.1 — reprodukcja, pełny przebieg i macierz narzędzi

1. Odtworzyć ścieżkę na izolowanych kontach: atakujący, intruz z obcego klanu
   i konto kontrolne tego samego klanu; dodatkowo relacja znajomości.
2. Zinwentaryzować oba wejścia: marker mapy oraz Victim Picker, dalszy panel
   przełamywania zabezpieczeń, grant dostępu, Player Hack Access i okna wyników.
3. Dla każdego błędu zapisać kroki, tool ID, stan dostępu, oczekiwany i faktyczny
   wynik, status/reason HTTP, wywołania store’ów oraz test regresyjny do dodania.
   Nie zapisywać prywatnych payloadów ani sekretów.
4. Sporządzić kompletną macierz katalogu, także rekordów GhostLab/custom:
   ID → przeznaczenie → target/mode → instalacja/wymagania → executor
   → koszt/ryzyko/cooldown → efekt/store/receipt → wynik UI → decyzja.
5. Każdy wpis oznaczyć: narzędzie przełamania, narzędzie po dostępie,
   osobna aplikacja pulpitu albo custom bez runtime. Sama kategoria
   `pro-system-tools` nie kwalifikuje do Player Hack Access.
6. Zmierzyć baseline całej ścieżki i helperów dla małego i ≥35 MB profilu
   obu uczestników. Zamknąć listę wymaganych projekcji i wyjątków mutacyjnych.

Wynik: reprodukcje, macierz bez niesklasyfikowanych pozycji, call graph,
baseline i lista konkretnych napraw. Nie zakładać numerów błędów bez pomiaru.

### 141.2 — aktualna pozycja aktora po teleportacji

**ZAMKNIĘTY 15 IX na polecenie autora**, z zakresem dowodów i przekazaniem
pozostałej walidacji opisanymi na początku dokumentu. Poniżej pierwotny zakres.

Cel: po potwierdzonym teleporcie aktor nie pozostaje bieżącym celem w starej
lokalizacji. Własna mapa, uprawniony obserwator, Victim Picker i wybór celu
muszą korzystać ze spójnej, wersjonowanej pozycji i reguł widoczności.

- Odtworzyć problem na dwóch kontach: teleportujący się intruz z obcego klanu
  i obserwator. Porównać pozycję przed/po w canonical store, odpowiedzi teleportu,
  projekcji aktorów, delcie, markerze i pickerze; zapisać wersje i czasy etapów.
- Sprawdzić istniejące wejścia teleportu: terminal/BlackNet, Victim Picker
  i bilet Googleplex. Nie tworzyć drugiego mechanizmu teleportacji.
- Prześledzić `PlayerPositionStore`, `map.player_moved`, audience,
  `/api/map/player-actors`, intrusions, cache/projekcje oraz render markerów.
  Oddzielić aktualną pozycję od historycznego miejsca wykrycia intruza:
  historyczny ślad nie może udawać bieżącej pozycji celu.
- Zweryfikować hipotezę ciężkiego profilu pomiarem całego call chainu,
  również helperów i fan-outu obserwatorów, na małym i ≥35 MB profilu.
  Sprawdzić także stare źródło współrzędnych, brak delty, niewłaściwe audience
  i nadpisanie nowej pozycji opóźnioną odpowiedzią. Nie przesądzać przyczyny.
- Naprawić zapis/projekcję/dostarczenie/render w miejscu potwierdzonej awarii.
  Odczyty zwykłej pozycji nie mogą hydratować profilu ani skanować wszystkich kont.
  Zachować receipt teleportu, CAS, monotoniczne wersje i guardy sesji/epoki.
- Po opuszczeniu obszaru widoczności usunąć lub oznaczyć aktora zgodnie
  z kontraktem widoczności; nie ujawniać nowego położenia nieuprawnionemu
  obserwatorowi. Zasięg i możliwość ataku nie mogą opierać się na starym markerze.
- Zachować tożsamość markera przy przemieszczeniu, bez duplikatu w starej
  pozycji. Nie naprawiać przez pełny rebuild mapy, reload profilu lub większy timeout.
- Testować otwartą/zamkniętą mapę, powrót z tła, dwa szybkie teleporty,
  odwróconą kolejność odpowiedzi, brak delty i bounded recovery, replay receipt
  oraz zmianę konta. Nie cofać pozycji i nie wykonywać teleportu ponownie.
- Przed naprawą przeczytać historyczny hardbugfix Googleplex ticket → live map
  z raportu po 130.10–130.12 i odpowiadające mu testy. Tamten PASS dotyczył
  określonego przebiegu własnej mapy; nie dowodzi aktualizacji obcego aktora dziś.

Odbiór: na desktopie i mobile pozycja uprawnionego obserwatora aktualizuje się
automatycznie w ramach istniejącego cyklu synchronizacji lub bounded recovery,
bez ręcznego reloadu. Zapisać zmierzone opóźnienie przed/po oraz limit wynikający
z kontraktu synchronizacji. Brak starego aktywnego markera, spójny picker i target,
brak ujawnienia pozycji poza audience oraz zera hot path są warunkiem zamknięcia.

### 141.3 — wykrycie, wybór, zabezpieczenia i uzyskanie dostępu

**W REALIZACJI od 15 IX.** Pierwsza poprawka chroni aktywny grant przed
przedłużeniem i zmianą usage key, ma odbiór autora. Drugi pakiet przenosi mark
z mapy na bounded projection i canonical target; migracja i odbiór autora potwierdzone.
Nadal otwarte: picker i alternatywne wejście security, walidacja capture
oraz trwały replay grantu. Nie traktować poprawki mark jako bramki wszystkich wejść.

- Jedna tożsamość od klikniętego aktora przez `target_username`/target ID,
  operację i grant aż do wyniku. Nick, tooltip, pozycja i indeks listy
  nie mogą zastępować identyfikatora gracza.
- Zachować istniejące źródła widoczności intruzów, kontakty, clan relation
  i reguły zasięgu. Obcy klan nie daje automatycznie prawa atakowania
  niewidocznego konta przez ręcznie wpisany username.
- Serwer rozstrzyga uprawnienia: self, friend, same clan, widoczność, pozycja,
  zasięg, aktywny dostęp i cooldown odpowiednio do etapu. Decyzja autora 15 IX:
  widoczność i zasięg blokują nowe/ponowne oznaczenie, ale ich utrata nie
  przerywa rozpoczętego hacku ani nie blokuje jego dokończenia. Kontynuacja
  wymaga kanonicznego stanu rozpoczętego hacku; nie wystarcza flaga UI lub
  dowolnie podany username. Zmiana relacji to odrębna walidacja, nieobjęta
  odbiorem ruchu celu.
- Po wyjeździe z terytorium aktor znika z mapy, lecz rozpoczęty cel pozostaje
  w Victim Pickerze z odległością, umożliwiając dalsze namierzanie, otaczanie
  i dokończenie hacku. Nie usuwać tego wpisu podczas cutover Pickera. Nie
  utożsamiać uprawnień kontynuacji z prawem nowego oznaczenia ani widocznością
  markera. Przełączanie widocznych celów zachowuje ich osobny postęp.
- Dla nieaktualnego intruza, zniknięcia konta, brakującej pozycji i utraty
  możliwości ataku zwracać kontrolowany stan z przyczyną i możliwością odświeżenia.
- Przypisanie aplikacji przełamujących zabezpieczenia wynika z kontraktu
  aplikacja/akcja/target/security. Odrzucone narzędzie ma czytelny powód.
- Zachować kolejkę `gonnaWinRequestQueue`, `operation_only`, postęp częściowy,
  capture i trwałe receipts. Brak narzędzia lub przegrana próba nie otwiera dostępu.
- Grant jest wynikiem potwierdzonego przełamania; retry/reload nie przedłuża
  dostępu ani nie tworzy go ponownie. Sprawdzić awarię między efektem a odpowiedzią.
- Panel otwiera się po potwierdzonym dostępie także przy odzyskaniu stanu po
  reloadzie; nie wymaga ponownego hacku. Przełączanie celu A/B nie miesza grantów.

### 141.4 — właściwy katalog i wspólne bramki użycia

Docelowy rdzeń istniejących narzędzi do pełnej naprawy:

| Narzędzie | Oczekiwany efekt i kontrola |
| --- | --- |
| System Log Reader | Ograniczony odczyt ostatnich 5 dozwolonych komunikatów z canonical store; pusty wynik jest legalny, bez pełnego profilu i prywatnej poczty |
| Security Panel Proxy | Odczyt i dozwolone zmiany security, zgodne reguły konfliktów/presetów; każda trasa sprawdza narzędzie i dostęp |
| Financial Sniffer | Wynik istniejącej próby finansowej, canonical transfer/ledger, usage/receipt, saldo obu stron i powiadomienie zgodnie z wykryciem |
| Friend Kicker | Wynik istniejącej próby usunięcia dozwolonego kontaktu, spójność relacji i prywatność; brak kontaktów jako wynik domenowy |
| Arsenal Cleaner | Wynik próby usunięcia dozwolonej aplikacji, ochrona core, spójność inventory/plików/storage/launchera; brak kandydatów jako wynik domenowy |

- Macierz 141.1 ustala pozostałe wpisy. Aplikacje Suite/pulpitu zachowują swoje
  miejsca uruchamiania, lecz nie udają narzędzi ingerencji w ofiarę.
- Custom `pending_custom_runtime` nie dostaje pozornego wykonania ani
  executorów wybranych po podobieństwie nazwy. Nie rozszerzamy GhostLab o nowy runtime.
- Jeden kontrakt kwalifikacji zasila prezentację i walidację serwera;
  frontend nie ma osobnej, sprzecznej listy dopuszczalnych narzędzi.
- Serwer kontroluje instalację/uprawnienia, zgodność celu, aktywny grant,
  usage i cooldown także dla bezpośredniego requestu i security update/preset.
  Wymagania zakupu i użycia muszą być jawnie rozdzielone według obecnej mechaniki.
- Panel pokazuje używalne narzędzia, a przy właściwych lecz niedostępnych
  wyjaśnia przyczynę. Cena zakupu nie może wyglądać jak koszt pojedynczego użycia.
- Nieobsługiwany tool ID lub brak executora daje kontrolowaną odmowę;
  usunąć sukces-placeholder z tej ścieżki.

### 141.5 — wykonanie, integralność i wynik obu stron

- Każde z pięciu narzędzi przechodzi cały przebieg: request → walidacja → efekt
  → receipt/wersja → odpowiedź → prezentacja → odczyt kanonicznego stanu.
- Wynik losowania, wybrany kontakt/aplikacja i kwota wymagają trwałego związania
  z pojedynczym użyciem przed nieodwracalnym efektem. Retry nie losuje ponownie.
- Efekt i receipt muszą być atomowe albo mieć sprawdzony protokół recovery
  dla używanych store’ów. Testować przerwanie przed efektem, po efekcie i przed
  odpowiedzią, równoległe kliknięcia oraz dwóch atakujących tę samą ofiarę.
- Zachować CAS, LKG, integrity gate oraz precommit generacji/epoki.
  Konflikt zapisu nie może nadpisać późniejszej zmiany ofiary; odtworzenie wyniku
  nie może powtórzyć transferu, usunięcia ani powiadomienia.
- Aktualizować właściwe scope i audience dla atakującego/ofiary; usunięta
  aplikacja nie wraca z legacy mirroru ani spóźnionej odpowiedzi.
- Wynik domenowy bez efektu (np. nieudana próba, brak HC/kontaktu/aplikacji)
  odróżnić od awarii transportu i od odmowy dostępu. Komunikat odpowiada danym.
- Jeżeli dana akcja tworzy operację, sprawdzić start, postęp, cancel/timeout,
  zakończenie i wynik w Operation Control. Jeżeli produkuje plik, wymagany jest
  pełny łańcuch operacja → canonical file → storage → File Manager → GX → HC.
  Dla pozostałych wpisać jawnie „nie dotyczy” z uzasadnieniem, bez fikcyjnego pliku.

### 141.6 — spójny interfejs desktop/mobile i recovery

- Responsywność obejmuje wybór gracza, panel hackowania, Player Hack Access,
  wszystkie okna narzędzi, formularze security i wyniki, nie tylko listę przycisków.
- Czytelna tożsamość celu, postęp przełamania, stan dostępu/czas, narzędzia,
  przyczyny blokad i ostatni wynik. Długie nicki, logi i błędy zawijają się.
- Brak poziomego overflow i kontrolek poza viewportem. Ograniczona wysokość,
  przewidywalny scroll, obsługa safe area, klawiatury ekranowej i orientacji;
  panel nie zasłania trwale podstawowych akcji mapy/pulpitu.
- Dotyk bez zależności od hover i prawego przycisku; cele dotykowe min. 44 px,
  widoczny focus, etykiety, obsługa klawiatury i poprawny powrót focusu.
- Loading, pusty katalog, brak pasujących zainstalowanych narzędzi,
  in-flight, wynik, odmowa, utrata sieci, wygasły grant i cooldown mają jawne stany.
  Zamknięcie/minimalizacja panelu nie wykonuje ani nie anuluje efektu domenowego.
- Odczyt HTTP nie zakłada JSON przy każdym błędzie. Zachować status i reason;
  401, 403, 404, 409, 423, błąd 5xx i timeout nie kończą się surowym wyjątkiem UI.
- W trakcie użycia przycisk nie pozwala wysłać przypadkowego duplikatu;
  trwały dedupe pozostaje po stronie serwera. Po niepewnym wyniku najpierw
  odzyskać stan użycia, zamiast ślepo powtarzać mutację.
- Wykorzystać istniejący most sesji. Odpowiedź starej generacji/epoki/ofiary
  nie otwiera okna ani nie nadpisuje aktualnego panelu. Obsłużyć także A → B → A.
- Countdown jest prezentacją czasu serwera i `hacked_until`; powrót z tła
  wymaga korekty i ograniczonego recovery. Timer nie przyznaje uprawnień.
- Cleanup timerów, listenerów i nieaktualnych odpowiedzi po zamknięciu,
  przełączeniu celu, logout/restart. Bez mnożenia pollingów i odtwarzaczy audio.
- Reuse istniejącej oprawy CHAOS. CSS ograniczony do dotkniętych komponentów;
  nie zmieniać zaakceptowanych show, Signal Registry ani globalnego layoutu.

### 141.7 — regresja, pełne E2E i zamknięcie

Przeprowadzić automatyczne bramki, scenariusze przeglądarkowe i odbiór autora
według poniższej macierzy. Po naprawach sporządzić raport: objaw → przyczyna
→ zmiana → dowód → pozostałe ograniczenie. Zaktualizować kontrakty dotkniętych
obszarów, ten sprint i journal. Nie zamykać funkcji na podstawie samego HTTP 200.

## 5. Źródła prawdy i bramka wydajności

| Zakres | Punkt wejścia do kanonicznych danych |
| --- | --- |
| Tożsamość, klan, poziom, wymagania | Integrity-gated identity/capability projections |
| Pozycja, intruz, relacja | PlayerPositionStore, territory intrusions, MailStore i istniejące reguły klanowe |
| Oznaczenie i postęp | PlayerMarkedTargetStore / PlayerTargetRuntimeStore |
| Czasowy dostęp, cooldown, użycie | PlayerHackAccessStore; rozszerzać istniejący kontrakt, nie tworzyć drugiego store’u dostępu |
| Operacje i pliki | PlayerOperationStore, canonical data files, PlayerInventoryStore |
| Logi, kontakty | SystemMessageStore / MailStore |
| HC | WalletStore, canonical balance/ledger i trwały klucz transakcji |
| Security nadal należące do profilu | Ograniczona projekcja do odczytu; nazwany guarded patch do rzeczywistej mutacji |

Brakująca projekcja wymaga implementacji przed podłączeniem funkcji. Żaden
fallback, poll ani błąd nie może po cichu hydratować pełnego profilu. Zabroniony
jest scan wszystkich kont i odczyt pełnego profilu per kandydat/odbiorca.

Małe konto oraz ≥35 MB: osobno duży atakujący, duża ofiara i oboje duzi.
Dla zwykłych ścieżek wymagane `profile_full_read=0`, `profile_full_write=0`,
`profile_bytes=0`, bounded queries/payload i brak wzrostu pracy z rozmiarem profilu.
Mierzyć także writer wait/czas locka i koszt odświeżeń otwartych paneli.

Dozwolony heavy write ma nazwany callsite i test dokładnie potrzebnego kosztu
jednego konta. Przygotowanie poza `BEGIN IMMEDIATE`, wewnątrz recheck/CAS,
session precommit, zapis i atomowy LKG. Odpowiedź po zapisie nie może ponownie
czytać pełnych profili obu stron. Sparse projection nie zastępuje całego profilu.

## 6. Walidacja i kryteria odbioru

Istniejące punkty startowe testów (rozszerzać właściwe przypadki, nie traktować
samych nazw plików jako dowodu pokrycia):

- `tests/test_victim_picker.py`, `tests/test_target_persistence.py`:
  relacje, targety, aplikacje, `operation_only` i skutki operacji.
- `tests/test_wallet_runtime_cutover.py`:
  `test_financial_sniffer_reserves_usage_before_canonical_transfer`.
- `tests/test_hot_path_recovery.py`, `tests/test_marked_target_hot_path.py`,
  `tests/test_territory_profile_projection_cas.py`.
- `tests/test_session_generation_isolation.py`,
  `tests/test_session_generation_precommit.py`,
  `tests/js/test_session_generation_isolation.js`.
- `tests/js/test_map_target_hitbox.js`, `tests/test_operation_control.py`
  oraz właściwe testy inventory/files znalezione po symbolach finalizacji.

Nowe testy dedykowane player hacking powinny sprawdzać rzeczywiste requesty,
efekty i zachowanie UI, także bezpośrednie wywołania z pominięciem panelu.
Izolowane DB/temp cwd są obowiązkowe; import `run.py` nie może dotknąć realnej bazy.

| Scenariusz | Warunek PASS |
| --- | --- |
| Obcy intruz: mapa i Victim Picker | Ten sam prawidłowy cel, spójne reguły i przejście do hacku |
| Teleport intruza: własna mapa i uprawniony obserwator | Aktualna pozycja bez ręcznego reloadu, brak starego aktywnego markera, zgodny picker/zasięg; opuszczenie audience nie ujawnia nowej lokalizacji |
| Teleport: replay, dwa szybkie ruchy, stale response i brak delty | Jeden efekt per receipt, monotoniczna pozycja, bounded recovery bez pełnego profilu; pomiar opóźnienia przed/po |
| Self / friend / same clan / niedostępny cel | Odmowa serwera i czytelny powód; brak skutków przy ręcznym requestcie |
| Aplikacje przełamujące zabezpieczenia | Wyłącznie zgodne, poprawny postęp; nieudana próba nie przyznaje dostępu |
| Grant, reload, cooldown, wygaśnięcie | Jeden trwały dostęp, poprawny czas, brak ponownego grantowania przez retry |
| Katalog i każde z pięciu narzędzi | Sensowne przypisanie, wykonanie i wynik; niepasujący/custom bez runtime nie zwraca fałszywego sukcesu |
| Brak instalacji, użycie powtórne, security direct API | Serwer egzekwuje bramki, nie tylko disabled w UI |
| HC / contacts / apps / security | Stan ofiary i atakującego zgodny z receiptami i uprawnioną projekcją, brak utraty niezwiązanych danych |
| Double click, dwa requesty, dwóch atakujących, awaria procesu | Brak podwójnego efektu, ponownego losowania i utraty wyniku; recovery sprawdzone |
| Stale response, dwa konta, rollover, zmiana celu | Brak przecieku i cofnięcia stanu, zachowane generation/epoch/version guards |
| Utrata sieci / HTTP / nie-JSON / CAS conflict | Czytelny stan i bezpieczne wznowienie, brak zawieszonego przycisku i surowego wyjątku |
| Operacja i artefakt, jeśli należą do akcji | Zgodny stan końcowy, poprawna finalizacja i GX; brak regresji wspólnych ścieżek |
| Heavy profile obu stron | Zera hot path, bounded work, wymagane wyjątki udokumentowane i przetestowane |
| Powtarzany scan / refresh / zoom | Akcja nadal dotyczy klikniętego markera, zachowane naprawy Leafleta |
| Desktop i mobile | Cały przebieg i każde okno narzędzia dostępne bez overflow, dotykiem i klawiaturą |

Minimalna macierz wizualna: desktop 1366×768 i 1920×1080, tablet 768×1024,
telefon 360×800 i 390×844 oraz landscape 844×390. Dodatkowo małe okno aplikacji,
długi nick/log, powiększenie 200%, klawiatura ekranowa, obrót i powrót z tła.
Emulację odróżniać od testu na fizycznym telefonie. Zapisać urządzenia,
przeglądarki, kroki i wynik, w tym pełną sesję atakującego oraz obserwację ofiary.

**GO / zamknięcie 141:** wszystkie etapy i narzędzia mają dowody wykonania,
bramki integralności/wydajności przechodzą, pełna ścieżka desktop/mobile ma
odbiór autora, a znane błędy blokujące tę mechanikę są usunięte. Sama korekta
CSS, lista narzędzi albo testy jednostkowe nie wystarczają. Niewykonany manual
oznacza READY FOR VALIDATION, nie CLOSED/PASS. Pozostawienie niedziałającego
narzędzia rdzenia wymaga jawnej zmiany zakresu, nie cichego ukrycia usterki.

## 7. Granice sprintu

- Nie zmieniamy arbitralnie balansu kosztów, losowań, cooldownów ani relacji
  klanowych. Niespójność wymagająca decyzji gameplayowej ma osobny zapis
  wariantów i decyzji autora; naprawy zgodne z kontraktem realizujemy w sprincie.
- Nie otwieramy ponownie Sprintów 139–140, stylizacji, Signal Registry ani
  zakończonego recovery Trollu2. Nie przebudowujemy całego GhostLab/sklepu.
- Brak nowych publikacji po triggerze pozostaje osobnym otwartym problemem;
  nie jest warunkiem domknięcia player hacking ani powodem ponownego triggera.
- Bez automatycznego restore, triggera, naliczania nagród, deployu, migracji
  produkcyjnej lub restartów. Ewentualną migrację przygotować jako jawny plan
  z dry-run i walidacją, oddzielnie od wykonania operatorskiego.
- Lokalny kod, testy i konfiguracja nie potwierdzają aktualnego stanu serwera.
  Każdy raport rozdziela reprodukcję, wynik testu, odbiór autora i hipotezę.
