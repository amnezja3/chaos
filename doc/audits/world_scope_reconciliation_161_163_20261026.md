# 161–163: rzeczywisty stan zakresu i korekta odbioru

Data: 26.10.2026. Przegląd lokalnego kodu po `2fa0f20`, planów sprintów,
konfiguracji ecosystem oraz przekazanych wyników VPS. Bez nowego dostępu do VPS,
zmian flag, pobrań dostawców ani deklaracji aktualnego stanu pamięci procesów.

## Wniosek

Na dyspozycję operatora zadania z tego audytu rozpisano w
[planie wykonawczym 163.5](../sprints/sprint_163_5_world_repository_completion.md).
Utworzenie planu nie oznacza zakończenia wymienionych braków.

**Pełny zakres 161–163 nie jest zakończony.** Odebrano działający skaner,
archiwum obserwacji, regularny kolektor, koszty i podstawową administrację.
Nie odebrano globalnej ścieżki „zapis świata → kolejne skany z repozytorium”.
Wpis `world_acceptance_161_163_20261026.md` zamyka tylko wdrożony podzakres.
Nie należy traktować go jako zamknięcia wszystkich C/G/R/D z planów sprintów.

Późniejsza dyspozycja z 25.10 słusznie oddzieliła zbieranie geografii od przyszłych
mechanik dróg/wody. Nie daje to podstaw do nazywania gotową pamięci POI dla skanera.
Nie przenosimy samodzielnie nieukończonego zakresu do nowych sprintów.

## Macierz stanu

| Zakres | Kod / dowody | Produkcja według ostatnich wyników | Pozostało |
| --- | --- | --- | --- |
| 161.0–161.1: kontrakt, ID, tagi, geometrie | WorldObject/ProviderBatch, wersjonowanie, cztery typy geometrii, testy | Skan MapLark odebrany na dwóch kontach | Nie jest to identyczność wszystkich selekcji MapLark i Overpass; zaakceptowany własny profil MapLark |
| 161.2–161.6: MapLark i skaner | Adapter, transport, koszty, cache, eksport do istniejącej gry | Działa dla graczy | Utrzymanie; podstawowy cel przywrócenia skanera spełniony |
| 161: Geoapify | Adapter Places, paginacja diagnostyczna i kolektor commercial | Zapis obserwacji POI działa | Nie jest pełnym fallbackiem skanera; brak zatwierdzonego pełnego profilu CHAOS, nie tylko przełącznika |
| 161/163: Overpass | Gałąź live routera i osobny adapter geometrii | VK roads zapisane; awaria następnej próby, potem MapLark | VK aktywowany tylko dla tła, nie dla skanera; inne instancje nie są automatycznie dopuszczone |
| 162.0–162.1: magazyn | Schemat v2, snapshot/member, indeks przestrzenny, provenance, backup, limity | Wdrożony, ostatnio 20 snapshotów | To ograniczone archiwum, nie wieczysta rosnąca baza; retencja 7 dni zaakceptowana przez operatora |
| 162.2: lokalny planer | Exact POI i obszarowy odczyt certyfikowanej geometrii jednego snapshotu | Pilotaże exact i roads PASS | Brak obszarowej ścieżki POI; regularne obserwacje nie nabywają dowodu pokrycia |
| 162.3–162.4: skaner korzystający z repo | Integracja MapLark istnieje, ale wyłącznie w ograniczonym pilocie | Ingest/read OFF; pilot wcześniej odebrany i wycofany do baseline | Tryb dla wszystkich, integracja z aktywnym routingiem, rollout i odbiór całej ścieżki |
| 162.2-G: drogi, cieki, jeziora, coastline | Pełne geometrie, lokalny odczyt, próbki rzeczywiste dróg/cieków/Polygon z otworami | Kolekcja obserwacji działa | Oddzielny odbiór możliwości regionalnego reuse; rzeczywisty MultiPolygon niepotwierdzony w przejrzanych dowodach |
| 161-G/162-G/163-G: land_water | Kontrakt, walidacja partycji/dependencies, storage/read i testy syntetyczne | Brak podłączonego źródła | Rzeczywisty regionalny produkt, importer/adapter i odbiór; coastline nie zastępuje powierzchni mórz |
| 163.1: zadania i kolektor | Fencing, kolejka, priorytet live, rotacja, limity, worker poza web | Regularny worker i monitor działają | Popyt niezależny od MapLark; pobieranie halo/sąsiadów nie jest wdrożone |
| 163.2: administracja | Registry, zakresy, routing per warstwa/tryb, historia, atlas, budżety, UX PL/EN | Wdrożenia i odbiór UI operatora | Wiarygodny runtime kolektora, pełniejsza diagnostyka; mapa to ograniczony podgląd snapshotów, nie pełne zapytanie przestrzenne wg viewportu |
| 163.3: monitoring | Wewnętrzna księga, osobny proces, metryki world/cache/network i latencji | Działa, limity egzekwowane niezależnie od monitora | Pełny zestaw wzrostu/unikalnych obiektów/WAL/queue p95 i SLO nie jest ukończony |
| 163.4–163.5: rollout | Testy, backupy, kontrolowane pilotaże, odbiór gry i kolektora | Potwierdzone dla wymienionych profili | Globalny local-read i jego rollback/odbiór; produkcyjna obserwacja pełnego cyklu 7 dni jeszcze nieudokumentowana |

## Najważniejsze ustalenia w kodzie

### 1. Flaga repozytorium nie wystarczy

`maplark_pilot.fetch_pilot()` przed odczytem i zapisem woła `world_pilot.allowed()`.
Ta funkcja wymaga konkretnego użytkownika, dokładnego środka skanu, promienia
300 m i ważnego okna do 24 godzin. W ecosystem.web pola pilota są puste,
ingest i repository są ustawione na 0. Tryb ogólny nie został zaimplementowany.
To brak kodu rollout’u, nie wyłącznie oczekiwanie na aktywację flagi.

Źródła: `poi_infrastructure/world_pilot.py`, `maplark_pilot.py`,
`world_shadow.py`, `ecosystem.web.config.js`.

### 2. Regularne archiwum nie jest pełnym POI repo dla skanera

Kolektor zapisuje MapLark/Overpass roads, waterways, inland_water, coastline
i Geoapify commercial POI. `DiscoveryWorker` publikuje je bez SelectionProof:
`coverage=UNKNOWN`. Samo `response_completeness=complete` oznacza kompletność
odpowiedzi, nie zgodność ze skanem wszystkich kategorii gry.
Regularny MapLark POI nie jest obecnie profilem kolektora; routing wyklucza
background POI dla MapLark/Overpass. Geoapify commercial nie obejmuje pełnego
profilu CHAOS. Nie wolno podmienić nim wyniku skanu.

Źródła: `routing.capability()`, `discovery_worker.py`, `regular_discovery.py`.

### 3. 7 dni archiwum nie oznacza 7 dni aktualnego skanu

Regularny worker zapisuje fresh=300 s, usable=1800 s, retain=604800 s.
Pilot POI ma 300/1800 s i nie przekazuje siedmiodniowego retain_until.
`WorldReadPlanner` wymaga ważnego usable_until i zgodnego dowodu. Dlatego
starsze obserwacje archiwalne mogą być dostępne administracyjnie, ale nie
stanowią automatycznie poprawnej odpowiedzi skanera.

Nie wydłużamy świeżości skanu do 7 dni przez pomylenie jej z retencją.
Obecny regularny zbiór odświeża aktywnie odwiedzane sektory co 7 dni;
nie utrzymuje przez cały ten czas regionalnego COMPLETE_FRESH.

### 4. Sąsiedni skan POI nie jest obsługiwany obszarowo

`SelectionProof` pozwala na exact dla POI. AREA_LAYERS zawiera geometrię,
ale nie POI. `world_shadow.read()` używa dokładnego query_key MapLark,
profilu, rewizji i referencji decyzji. Przesunięcie zapytania tworzy inny klucz.
Pilotaż 75 dróg i odczyty 33/54 dowodzą regionalnego odczytu dróg, a nie
sąsiedniego skanu wszystkich POI. Union wielu snapshotów pozostaje niewspierany
w tym planerze; plan 162 dopuszczał jawny wariant jednego snapshotu.

### 5. Aktywny router Overpass nie czyta kanonicznego świata

`Service.fetch()` przy routing=1 przechodzi do `scan_router.fetch_routed()`.
Fazy: **fresh cache → world → network → stale**. W `_overpass()` faza world
nie odczytuje WorldReadPlanner — odczytuje tylko istniejący cache i nie pobiera
sieci w tej fazie. Starsze gałęzie world w Service nie dowodzą działania
kanonicznego repo pod aktywnym routerem.
MapLark ma world hook, lecz ograniczony opisanym pilotem.

To także korekta wcześniejszego uproszczenia „repo → cache → API”: kod obecnie
daje pierwszeństwo świeżemu cache. Nie zmieniamy tej polityki w audycie.

### 6. Skanowanie i odwiedzenie nie są tym samym wyzwalaczem

Jedyny znaleziony runtime zapis popytu to `world_shadow.demand()` wywołany
z MapLark fetch_pilot, przed jego pobraniem. Nie ma równoważnego hooka w
poruszaniu gracza ani w ścieżce Overpass. Brak sukcesu MapLark nie blokuje tego
zapisu, ale obsłużenie skanu przez wcześniejsze źródło może go ominąć.
Regularny worker wybiera do 100 aktywnych komórek 0.01°, TTL popytu 24 h,
pięć profili, bez generowania sąsiadów i bez pobierania land_water.

### 7. Wyłączenie sieci a wyłączenie źródła

Testy potwierdzają lokalny odczyt w pilocie przy zajętej sieci lub braku budżetu.
Wyłączenie providera w registry celowo wyklucza go jednak także z wyboru
MapLark, zanim nastąpi odczyt świata. Nie należy obiecywać, że każdy globalny
„disable provider” zachowuje odczyt archiwum. Potrzebne jest rozróżnienie
zatrzymania nowych pobrań i cofnięcia praw do danych w docelowym rollout.

## Co zrobić dalej — bez nowych sprintów i bez czekania na liczbę rekordów

1. **Domknąć podstawowy local-read POI:** tryb dla wszystkich z osobnym kill
   switchem, automatyczny zapis zgodnych wyników skanera, respektowanie praw,
   rewizji, świeżości i kosztów; cache/world/API w jednej aktywnej ścieżce.
   Najpierw exact MapLark, którego kontrakt i pilot mamy potwierdzone.
2. **Wpiąć pełny profil regionalnego POI:** przygotować/zakwalifikować źródło
   i selekcję zgodne ze skanerem. Dopiero wtedy sąsiedni skan z dowiedzionego
   obszaru bez API. Nie oznaczać kroku 1 jako ukończenia tego kroku.
   Integracja Overpass world pod aktywnym routingiem należy do tego pakietu.
3. **Uzupełnić producenta popytu:** wspólny hook niezależny od providera,
   potem odwiedzenie regionu bez skanu, z dedup i limitami. Halo/sąsiedzi
   pozostają oddzielnym brakującym elementem pierwotnego bounded-prefetch.
4. **Zbiorczy odbiór VPS:** dwa konta; ten sam skan z repo 0 HTTP i bez wzrostu
   kosztu, restart, miss/fallback, wygaśnięcie, błąd magazynu, wyłączenie nowych
   fetchy, rollback bez utraty danych; sąsiedni skan tylko po wdrożeniu kroku 2.
5. **Dokończyć geograficzne braki w zadeklarowanym zakresie:** źródło land_water,
   rzeczywisty multipart, granice regionalnych certyfikatów. To nie wymaga
   nowych mechanik gameplayu ani blokowania działającego skanera.
6. **Domknąć pozostałe kryteria operacyjne:** mapowanie C/G/R/D do konkretnych
   testów i odbiorów, pomiary/SLO w ustalonym oknie, brakujące agregaty panelu.

## Co tylko czeka na obserwację lub decyzję

- Naturalne odświeżenie po 7 dniach i przegląd polityki po 30 dniach: utrzymanie,
  nie brak implementacji regularnego harmonogramu.
- Nierozliczone 5 operacji Geoapify / 25 rezerwacji: zachowane; zagregowany panel
  dostawcy nie rozlicza wiarygodnie pojedynczych operacji.
- Pełny fallback Geoapify: wymaga danych/kontraktu, nie samego klucza lub zgody.
- Pozostałe instancje Overpass: indywidualna dostępność i zakres użycia.
- Bezterminowa baza świata nie jest zaakceptowaną polityką obecnego etapu;
  mamy 7-dniowe archiwum ograniczone limitem pojemności, nie import planety.

## Weryfikacja tego przeglądu

Ponownie uruchomione izolowane testy: world_shadow 9 PASS, world_read 16 PASS,
world_pilot_scope 2 PASS. Transport mockowany, bez wywołań dostawców.
To weryfikacja istniejących ograniczeń, nie dowód nowej aktywacji na VPS.
Nie wykonano zmian runtime ani nowego wdrożenia.
