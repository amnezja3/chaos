# Sprint 130.10.2 — Marked Target Hot Path & Visual Continuity

Data realizacji lokalnej: 2026-08-23.

Status: `SPRINT 130.10.2 — COMPLETE`.

## Cel

Usunąć czarną dziurę po sekwencji `scan → oznacz → szybkie wyczyść
scan`: cel ma od razu otrzymać jednoznaczny stan wizualny, a trwałe oznaczenie
nie może czekać na odczyt i przepisanie wielomegabajtowego profilu.

Sprint nie zmienia zasięgu skanu, zasad oznaczania, ochrony obcego terytorium,
hackowania, capture ani timingów aplikacji. Nie cofa profile integrity ze
Sprintu 130.10.

## Diagnoza

1. Menu markera skanu wywoływało legacy endpoint `/map-action`, nie lekki
   `/api/map/aim-target`.
2. Branch `mark_target` wykonywał `sync_session_profile()`, tworzył
   `UserProfileManager`, odczytywał cały profil i zapisywał całą listę
   `profile_json.targets` przez integrity/CAS/LKG.
3. Na realnym snapshotcie konto `main` ma profil `34 596 295 B`, z czego
   `operations` zajmują około `31 810 124 B`; sama lista `targets` ma około
   `8 622 B` i 59 rekordów. Koszt był więc nieproporcjonalny do mutacji.
4. Frontend nie tworzył stanu oczekującego. `clear scan` usuwał marker Leaflet,
   a odpowiedź backendu instalowała trwały marker dopiero po 30–40 sekundach.
5. Usuwana warstwa skanu pozostawała w `targetMarkers`, co mogło kierować
   późniejsze delty do nieistniejącego markera.
6. W template pozostawał nieużywany `mapAction_old` z alternatywnym legacy
   rendererem. Został usunięty, aby istniał jeden frontendowy contract.

## Implementacja

### Canonical marked-target store

Dodano:

- `player_marked_targets` — małe wiersze aktywnych/usuniętych oznaczeń,
  wersja i zapisany payload;
- `player_marked_target_state` — durable receipt jednorazowego importu legacy
  `profile_json.targets` dla konta;
- `PlayerMarkedTargetStore` — `ensure_seeded`, `list_targets`, idempotentny
  `upsert` i `remove_matching`.

Po zapisaniu receipt canonical store jest source of truth. Zwykły hot path nie
parsuje już `profile_json`. Przy następnym rzeczywistym guarded profile write
warstwa canonical overlay odświeża compatibility mirror `targets`; integrity,
checksum, revision/CAS i LKG pozostają aktywne.

### Backend

- `/map-action` rozpoznaje `mark_target` przed `sync_session_profile()`;
- czyta tylko integrity-gated identity projection;
- zachowuje ochronę obcego terytorium, ale sprawdza geometrię przed pobieraniem
  relacji właściciela;
- zapisuje jeden mały rekord i emituje `map.target_marked` tylko dla faktycznej
  zmiany; retry zwraca `duplicate=true` bez drugiej delty;
- `/api/map/target-snapshot` czyta oznaczenia z canonical store bez pełnego
  profilu;
- scan, Victim Picker i capture korzystają z tej samej kolekcji;
- capture oznacza pasujący rekord jako usunięty;
- `/map-action` wszedł do telemetryki `[HOT_PATH]`.

### Frontend

Kliknięcie `Oznacz` natychmiast tworzy nieinteraktywny, glitchujący marker
`LINKING TARGET...`. Marker:

- jest niezależny od `scanResultLayers`, więc `Wyczyść scan` go nie usuwa;
- nie przechwytuje gestów mapy;
- po sukcesie przechodzi w `TARGET LINKED`, a następnie ustępuje trwałemu
  interaktywnemu markerowi;
- po kontrolowanym błędzie pozostaje czerwony przez 4 sekundy z `LINK FAILED`;
- respektuje `prefers-reduced-motion`.

`clearScanResultLayers()` usuwa teraz także wpis starej warstwy z marker
registry. Delta `map.target_marked` potrafi utworzyć brakujący marker, co pokrywa
delivery wyprzedzające odpowiedź HTTP.

## Migracja operatorska

Narzędzie jest domyślnie read-only:

```bash
.venv/bin/python tools/migrate_marked_targets.py --db data/game.sqlite3
```

Jawny, idempotentny import przed manualem:

```bash
.venv/bin/python tools/migrate_marked_targets.py --db data/game.sqlite3 --apply
```

Można ograniczyć go do konta przez `--username main`. Apply nie usuwa cyklu GN,
terytoriów, target runtime ani profili. Pre-seed usuwa jednorazowy koszt parsowania
legacy listy z pierwszego wejścia każdego konta.

## Bramka automatyczna

Wymagane kontrakty:

- mark target: zero `get_profile()`, `sync_session_profile()` i
  `UserProfileManager`;
- target snapshot: zero full-profile read;
- jednorazowy, idempotentny legacy seed;
- duplicate mark: zero duplicate delta;
- capture usuwa tylko pasujące oznaczenie;
- foreign-territory block działa przed zapisem;
- pending marker przeżywa clear scan, a usunięty scan marker nie pozostaje w
  registry;
- brak `mapAction_old`;
- migration dry-run jest read-only.

Wynik lokalny:

- regresja marked-target/map/territory/target/integrity/migration: `348/348 OK`;
- dodatkowy pełny kontrakt loadera i nowy zestaw hot-path: `22/22 OK`;
- `py_compile` i `git diff --check`: OK;
- read-only dry-run migratora dla lokalnego `main`: `ok=true`, `pending=1`,
  bez uruchomienia apply.

## Manual po deployu

1. Otwórz mapę na dużym koncie `main`.
2. Wykonaj scan, wybierz obiekt i kliknij `Oznacz`.
3. Natychmiast kliknij `Wyczyść scan`.
4. Glitch marker ma zostać w tym samym miejscu bez przerwy.
5. Po odpowiedzi ma przejść w trwały marker z menu hackowania.
6. Refresh mapy ma odtworzyć dokładnie jeden marker.
7. Powtórz na małym koncie i spróbuj oznaczenia na chronionym obcym
   terytorium; odpowiedź `403` ma zakończyć pending marker jako failure.

Bramka wydajności: wpis `[HOT_PATH] POST /map-action` dla `mark_target` ma
raportować `profile_full_read=0`, `profile_full_write=0` oraz brak wielkiego
`profile_bytes`. Manual nie wymaga czekania 30–40 sekund na jakikolwiek widoczny
feedback.

Nie wykonano commita ani deployu.

## Formalne zamknięcie — 2026-08-24

`SPRINT 130.10.2 — COMPLETE`

Canonical `player_marked_targets`, idempotentny seed receipt oraz lekki
`mark_target`/target snapshot pozostają source of truth bez pełnego profilu w
hot pathie. Kontrakt frontendowy zachowuje marker `LINKING TARGET...` po
wyczyszczeniu warstw skanu, a sukces zastępuje go interaktywnym markerem bez
duplikowania delty. Późniejszy manual mapy i ocena serwerowego gameplayu nie
wykazały pozostawionego blockera 130.10.2.
