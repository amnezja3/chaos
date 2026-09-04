# 138.getway — lekka bramka supermocy przed pełnym testem GhostSignalu

Status: `REQUIRED / BLOCKING 138.2`
Źródło audytu: `doc/audits/ghostnetwork_superpowers_actual_state_audit.md`
Zakres: `138.getway.0` foundation/pilot, `138.getway.1–4` profesja po profesji
oraz `138.getway.5` polish.

> Sygnatura `getway` jest nazwą przyjętą dla tej bramki i pozostaje niezmienna.

## 1. Decyzja produktowa

Supermoc GhostNetwork ma być przede wszystkim mocnym, czytelnym wydarzeniem na
mapie i prostym, czasowym modyfikatorem istniejącej rozgrywki. Nie budujemy
drugiego systemu efektów, osobnego pipeline'u, workera, kolejki zadań ani nowego
runtime'u świata.

Wzorzec interakcji bierze się z działającego `Secret Path`:

```text
aktywna część + właściwy klan i profesja
  → na mapie pojawia się przycisk z nazwą mocy
  → kliknięcie i potwierdzenie backendu
  → 4–6 sekund: overlay mapowy + asset + CSS + SFX + semantyczny opis
  → overlay znika
  → na mapie zostaje licznik 15:00 → 00:00 i widoczny efekt CSS
  → przez 15 minut istniejące mechaniki odczytują prosty modyfikator
  → koniec efektu; ponowne użycie dopiero po cooldownie
```

Kandydat startowy do testów:

- czas działania: `900 s`;
- cooldown: `3600 s` liczony od aktywacji;
- jeden dostępny przycisk wynikający z profesji gracza;
- jedna aktywna moc na gracza;
- wartości są konfiguracją backendu i mogą zostać skorygowane po pierwszych
  testach frontendowych.

## 2. Nienaruszalne granice architektoniczne

Poniższe reguły są częścią Definition of Done każdego podsprintu. Naruszenie
którejkolwiek z nich blokuje merge i test produkcyjny, nawet jeżeli efekt jest
atrakcyjny wizualnie.

### Dane gracza i heavy profile

1. Ścieżka aktywacji, snapshot mapy, odliczanie i hook efektu nie mogą ładować
   pełnego `profile_json`, jeżeli potrzebne pola mają canonical narrow store lub
   projekcję.
2. Zabronione są `list_profiles()`, account scan, iteracja po wszystkich graczach
   oraz odczyt/zapis całej kolekcji profili w celu znalezienia aktywnej mocy.
3. Nie zapisujemy `active_superpowers`, timerów, cooldownów, syntetycznych
   incydentów ani list dotkniętych obiektów do ciężkiego profilu.
4. Poziom, klan i profesja pochodzą z istniejącej projekcji identity/progression.
   Nie tworzymy ich kopii będącej drugim źródłem prawdy.
5. Pliki i operacje są odczytywane oraz zmieniane przez istniejące narrow stores;
   moc nie hydratuje profilu tylko po to, aby dopisać nagrodę.

### Baza danych i hot path

6. Wspólny rdzeń aktywacji wykonuje bounded lookup po graczu/części oraz jeden
   mały zapis okna mocy. Konkretny adapter może wykonać wyłącznie jawnie
   limitowaną liczbę zapisów domenowych potrzebnych efektowi; nie uruchamia
   globalnego reconcilea ani skanu cyklu.
7. Każdy nowy lookup używany na hot path musi mieć indeks odpowiadający kluczowi
   odczytu, w szczególności `player_id`, `ability_code`, `expires_at`.
8. Nie utrzymujemy transakcji SQLite podczas renderowania, wywołania zewnętrznego,
   SFX, pracy frontendowej ani generowania plików. Transakcje są krótkie i
   obejmują wyłącznie canonical read/check/write.
9. Nie używamy tight loop, aktywnego pollingu ani osobnego procesu do odliczania.
   Frontend odlicza lokalnie od serwerowego `expires_at`, a backend weryfikuje
   czas tylko przy snapshotach i akcjach.
10. Wygaśnięcie nie wymaga masowego cleanupu. Rekord wygasły jest nieaktywny z
    definicji; bounded cleanup może działać przy zwykłym odczycie lub audycie.

### Źródła prawdy i bezpieczeństwo zapisu

11. Frontend nie przesyła klanu, profesji, poziomu, mnożnika, czasu działania,
    cooldownu, kategorii nagrody ani oczekiwanego wyniku efektu.
12. Backend wyprowadza moc z authenticated player identity oraz aktywnej części
    i ponownie sprawdza eligibility bezpośrednio przed zapisem.
13. Moce celu korzystają z canonical `aimed_target` albo jawnego existing target
    contract. Etykieta, współrzędne i stan zabezpieczeń z DOM nie są źródłem
    prawdy.
14. Modyfikacja security, action state, operacji, plików i terytorium zachowuje
    istniejące owner checks, CAS/version oraz monotoniczne reguły danego store.
15. Jedna aktywacja ma stabilny dedupe/idempotency key. Podwójny klik, retry po
    409/timeout oraz reload nie mogą nałożyć bonusu drugi raz.
16. Modyfikator nie może omijać session generation, CSRF/auth, audience safety,
    foreign-territory gate ani istniejących limitów endpointu docelowego.

### Granice systemu

17. Nie powstaje nowy worker PM2, scheduler, task queue, outbox/inbox, publisher,
    event bus, LLM prompt ani osobna baza danych dla supermocy.
18. Nie budujemy generycznego interpretera efektów ani mechanizmu pozwalającego
    konfiguracji YAML/JSON wskazać dowolne pole bazy lub profilu do modyfikacji.
19. Konfiguracja może wybierać wyłącznie zamkniętą rodzinę modyfikatora i bounded
    wartości; sam zapis wykonuje ręcznie napisany adapter przy istniejącym
    call-site.
20. Syntetyczne incydenty/NPC używają istniejącego Response Network i muszą być
    oznaczone jako niekanoniczne dla kar, nagród oraz statystyk realnych zdarzeń.
21. Overlay, asset, CSS, SFX i System Message są prezentacją wyniku potwierdzonego
    przez backend. Awaria prezentacji nie cofa ani nie powtarza aktywacji.
22. Ollama może później opisać zdarzenie poza hot path, ale nigdy nie wybiera
    mocy, targetu, wartości, czasu, nagrody ani powodzenia aktywacji.

### Budżet wydajności i wymagane dowody

23. Snapshot mocy zwraca tylko viewer-safe capability, aktywne okno i cooldown;
    nie dołącza pełnego profilu, historii użyć ani list obiektów świata.
24. Efekt klastrowy jest ograniczony liczbą klastrów i obiektów na aktywację.
    Żadna moc nie wykonuje nieograniczonego fan-out po terytoriach, celach,
    operacjach, plikach lub aktorach.
25. Każdy podsprint dostarcza test potwierdzający bounded liczbę read/write,
    brak heavy-profile read/write/account scan oraz brak regresji SQLite lock.
26. Audit przed `SERVER PASS` raportuje co najmniej:
    `profile_full_read=0`, `profile_full_write=0`, `account_scan=0`, liczbę
    dotkniętych rekordów, czas aktywacji i liczbę odrzuconych duplikatów.

Wyjątek od tych zasad wymaga osobnej decyzji architektonicznej i aktualizacji
tej bramki przed implementacją. Nie wolno przemycić wyjątku jako „tymczasowego”
rozwiązania konkretnej profesji.

## 3. Co dokładnie wykorzystujemy z istniejącego systemu

### Gotowe i przeznaczone do ponownego użycia

| Potrzeba | Istniejący punkt zaczepienia |
| --- | --- |
| Show 4–6 s | `showSecretPathLore()`, overlay `.chaos-secret-path-overlay` i jego lifecycle |
| SFX | wspólne `window.GameSfx`, magistrala `lore`, replace/fade/ducking |
| Asset | istniejące assety 20 części w `static/images/ghostnetwork/parts/` |
| Przycisk mapy | istniejące menu mapy i viewer-safe ability projection |
| Odliczanie | istniejący wzorzec timerów aktywnych operacji na mapie |
| Operacje | `started_at`, `expires_at`, `duration_seconds`, `remaining_seconds` |
| Pliki i nagrody | canonical `player_data_files`, resource buffer i finalizacja operacji |
| Typy danych | camera, audio, credentials, financial, personal, GPS, device, network |
| Hack | istniejący aimed target, action dots/actions i security map |
| Zasięg i zoom | `get_player_action_range()`, `scan_range_bonus`, `get_player_map_zoom()` |
| Incydenty i służby | `IncidentStore`, NPC capsules, snapshot/delta i renderer mapy |
| Aktorzy | `/api/map/player-actors` i istniejący renderer markerów |
| Komunikaty | System Messaging i istniejący kontrakt frontendowego feedbacku |

`bike_range_bonus` jest wprawdzie zapisywany przez sklep, ale audyt nie wykazał
osobnego konsumenta — obecny zasięg działa przez `get_player_action_range()` i
`scan_range_bonus`. Nie uznajemy więc samej nazwy pola za działającą mechanikę.

### Jedyny wspólny stan, którego brakuje

Secret Path jest dziś pokazem prezentacyjnym i nie przechowuje piętnastominutowego
efektu. Dodajemy tylko jeden mały, generyczny rekord okna mocy w istniejącym
repozytorium SQLite GhostNetwork:

```text
player_id
ability_code
source_part_id
activated_at
expires_at
cooldown_until
level_snapshot
target_id?          # tylko gdy moc korzysta z aktualnie oznaczonego celu
```

Nie powstają osobne tabele, klasy instancji i schedulery dla każdej z 20 mocy.
Wygaśnięcie wynika z porównania czasu przy snapshotach i akcjach. Reload mapy
odbudowuje licznik z `expires_at`; frontend nigdy sam nie przedłuża efektu.

## 4. Cienki przepływ wykonania

```text
map capability snapshot
  → przycisk ability_name
  → POST activate (bez mnożnika i bez wyniku przesłanego przez klienta)
  → backend ponownie sprawdza: cykl, część, module state, klan, profesję, cooldown
  → zapisuje jedno okno czasowe
  → zwraca ability_name, semantic_description, asset, expires_at i presentation
  → mapa odgrywa wariant Secret Path
  → istniejące call-site pytają o aktywny, typowany modyfikator
```

Nie dokładamy do tej ścieżki narrative outbox/inbox, Ollamy, publishera,
territory workera ani osobnej kolejki. Opis mocy jest kanonicznym copy z katalogu
lub konfiguracji, a nie generacją LLM.

Moc wymagająca celu korzysta wyłącznie z aktualnego canonical `aimed_target`.
Moc globalna nie otwiera nowego selektora. Dzięki temu `Wejście Serwisowe` działa
na oznaczonym celu, a `Insider Feed` i efekty klastrowe uruchamiają się jednym
kliknięciem.

## 5. Zasady wizualne

1. Przycisk jest widoczny tylko, gdy backend zwraca moc jako dostępną.
2. Tekst przycisku to nazwa mocy, nie techniczny `ability_code`.
3. Show aktywacji trwa domyślnie 5 sekund i blokuje ponowne kliknięcie, ale nie
   zamraża mapy ani operacji.
4. Show używa assetu konkretnej aktywnej części, koloru klanu, krótkiego opisu
   semantycznego i SFX.
5. Po show zostaje zwarty badge mocy z miniaturą assetu aktywnej części, nazwą
   mocy i `MM:SS`. Asset nie znika przez całe okno wpływu, a licznik opiera się
   na czasie serwera.
6. Przez 15 minut mapa utrzymuje lekki efekt CSS właściwy dla mocy. Nie może on
   zasłaniać markerów, menu ani centrum operacji.
7. Koniec okna usuwa CSS i licznik. System Message informuje o aktywacji,
   odrzuceniu i zakończeniu bez spamowania przy każdym ticku.
8. Brak audio lub assetu nie blokuje mechaniki; pozostaje tekstowy fallback.

### Paleta klanów

Każdy overlay, halo, progress/timer ring, aktywny przycisk i piętnastominutowy
efekt CSS musi być dopasowany do klanu części. Nie wybieramy koloru per profesja
i nie losujemy go przy aktywacji.

Źródłem prawdy pozostaje istniejąca paleta terytoriów mapy:

| Klan | Kolor główny / obrys | Kolor głęboki / tło |
| --- | --- | --- |
| VIREX | czerwony `#E53935` | `#A91F24` |
| Echo Wolności | żółty `#FFD43B` | `#C79C00` |
| Siatka Widmo | turkusowy `#00CFA6` | `#008F78` |
| Strażnicy Ładu | niebieski `#238BFF` | `#1665BD` |

Implementacja korzysta ze wspólnych tokenów/palety, a nie kopiuje wartości do
osobnego słownika supermocy. Kolor główny steruje obrysem, światłem, scanline,
progress ringiem i akcentem tekstowym. Kolor głęboki służy do
półprzezroczystego tła. Kontrast komunikatu i timera musi pozostać czytelny.

Badge aktywnego wpływu ma minimalnie:

```text
[asset części 32–40 px]  NAZWA MOCY  14:57
                          cooldown po wygaśnięciu
```

Asset pochodzi z `visual_asset_url`/katalogu części zatwierdzonego przez backend,
nie z nazwy pliku zbudowanej przez frontend. Brak assetu daje istniejący fallback
części, ale nie usuwa nazwy, timera ani koloru klanu.

## 6. Parametry, którymi wolno manipulować

Supermoce korzystają z małego katalogu rodzin modyfikatorów. Każda rodzina ma
konkretny istniejący call-site; nie przyjmujemy ogólnego skryptu modyfikującego
dowolne pole profilu.

Implementacyjnie każda rodzina otrzymuje jeden mały, ręcznie napisany realizer.
Realizer nie jest pluginem ani skryptem konfiguracyjnym: ma zamknięty typ wejścia,
bounded parametry i wskazany istniejący call-site.

```text
ability_code
  → presentation_profile   # asset, paleta, copy, wariant CSS/SFX
  → gameplay_realizer      # jedna z zamkniętych rodzin
  → bounded parameters     # wartości wyłącznie z backendowej konfiguracji
```

| Rodzina | Widoczny efekt dla gracza | Sposób integracji |
| --- | --- | --- |
| `operation_speed` | zegary rozpoczętych operacji wyraźnie przyspieszają | bounded korekta pozostałego czasu; znacznik chroni przed wielokrotnym użyciem |
| `file_yield` | operacja tworzy więcej plików właściwego typu | bonus przy istniejącej finalizacji plików |
| `file_value` | **DEFERRED** — wymaga narrow settlementu Ghost Exchange | nie wchodzi do bieżącej bramki |
| `data_quality` | rośnie kompletność/jakość konkretnych plików | bounded bonus przy finalizacji; istniejące quality/completeness dalej liczy cenę |
| `hack_actions` | mniej kropek pozostaje do wykonania | inicjalizacja/aktualizacja action state oznaczonego celu |
| `target_security` | mniej lub więcej aktywnych zabezpieczeń | ograniczona transformacja istniejącej security map z zachowaniem CAS |
| `operation_risk` | spada/rośnie widoczny heat i ryzyko incydentu | modyfikator w istniejącym risk meterze, przed progami warning/incident |
| `scan_range` | większy promień lub skan niezależny od motocykla | istniejący action range albo jawny bypass tylko dla endpointu skanu |
| `map_zoom` | szerszy widok | istniejący getter zoomu, bez trwałego zakupu w profilu |
| `actor_visibility` | **DEFERRED** — obecny snapshot wykonuje account scan | nie wchodzi do bieżącej bramki |
| `incident_decoy` | **DEFERRED** — globalne listy i write-on-GET | nie wchodzi do bieżącej bramki |
| `territory_defense` | cele zyskują/odzyskują zabezpieczenia | istniejący security store i owner/CAS checks |

Katalog zachowuje 12 rodzin technicznych, ale bieżąca bramka certyfikuje 9.
`file_value`, `actor_visibility` i `incident_decoy` pozostają jawnie odłożone.
Nie muszą odpowiadać 1:1 dwudziestu
częściom. Dwie moce mogą używać tej samej rodziny, ale różnić się typem danych,
target scope, formułą i obserwowalnym wynikiem. Przykład: Echo podnosi
`data_quality` plików camera/audio, a VIREX tę samą rodzinę stosuje wyłącznie do
credentials/personal/financial.

Nowe rodziny są oparte na rzeczywistych mechanizmach:

- `operation_risk` ma istniejące `current_heat`, `warning_threshold`,
  `incident_threshold`, security/conflict modifiers i widoczny risk state;
- `data_quality` ma istniejące `quality_score`, `completeness_percent`, tier i
  mnożniki ceny Ghost Exchange.

Nie wolno bezpośrednio ustawiać końcowej ceny, wyniku detekcji ani statusu
incydentu. Moc dodaje bounded wejściowy modyfikator, a wynik nadal wylicza
istniejący system.

Bonusy do plików są ograniczane do już obsługiwanych kategorii. Przykładowy
kierunek klanów:

- VIREX: przyspieszenie, wartość plików, credentials/personal/financial;
- Echo Wolności: dodatkowe camera/audio/transcript i lepsze ujawnienie;
- Siatka Widmo: miks kategorii, fałszywe incydenty, zdalny skan i chaos mapy;
- Strażnicy Ładu: zabezpieczenia, wykrywanie aktorów, naprawa i ograniczenie
  skutków wrogich działań.

To są rodziny techniczne. Nazwa i opis mocy nadal opowiadają fabułę, natomiast
gracz zawsze widzi co najmniej jeden policzalny albo oczywisty skutek gameplay.

## 7. Balans startowy

### Insider Feed

Pierwszy kandydat do testu:

```text
speed_multiplier = clamp(0.1 × LVL, 1.5, 8.0)
```

Dla poziomu 71 daje `7.1×`. Aktywacja obejmuje operacje już rozpoczęte i nowe
operacje uruchomione podczas aktywnego okna. Technicznie używamy jednorazowej,
idempotentnej korekty pozostałego czasu dla istniejących operacji oraz krótszego
czasu startowego dla nowych. Poziom jest snapshotowany przy aktywacji, więc
reload nie zmienia mnożnika.

Formuła, cap i sposób potraktowania bardzo krótkich operacji są hipotezą do
pierwszego testu frontendowego, nie zamrożonym balansem.

### Wejście Serwisowe

Moc korzysta z aktualnie oznaczonego celu. Na czas okna nowe wejście w hack tego
celu ma wykonane wszystkie action dots; gracz nadal musi rozbroić istniejące
zabezpieczenia. Moc nie przejmuje celu i nie wyłącza security automatycznie.

### Fałszywy Obraz

Moc tworzy syntetyczne incydenty na obrzeżach wszystkich klastrów terytoriów
gracza oraz uruchamia istniejące kapsuły poruszających się służb. Rekordy mają
TTL zgodny z oknem mocy, jawne źródło `ghost_ability`, deterministyczny seed i
nie są liczone jako prawdziwe incydenty do kar/nagród.

## 8. Model profesja po profesji

Każdy efekt katalogowy pozostaje hipotezą do pierwszego testu. W każdym
podsprintcie wykonujemy tylko:

```text
A. wybór jednej istniejącej rodziny parametru
B. cienki prototype: przycisk → show → timer → wizualizacja skutku
C. test frontendowy właściwą profesją
D. KEEP / ADJUST / REPLACE / DEFER
E. mały hook w istniejącym call-site + E2E
```

Nie projektujemy z góry 20 skomplikowanych mechanik. Finalna decyzja o efekcie
zapada po zobaczeniu go na mapie.

Obowiązkowy zapis decyzji:

| Pole | Znaczenie |
| --- | --- |
| `profession_code / part_code` | para katalogowa |
| `ability_name` | nazwa widoczna na przycisku |
| `semantic_description` | krótki opis dla sceny aktywacji |
| `parameter_family` | jedna z rodzin z sekcji 6 |
| `initial_formula` | startowy mnożnik/limit |
| `decision` | `KEEP / ADJUST / REPLACE / DEFER` |
| `frontend_evidence` | screenshot i obserwowany skutek |
| `backend_evidence` | call-site i test E2E |

## 9. 138.getway.0 — foundation i pilot wszystkich realizerów na V1

Status: `IN PROGRESS — 138.getway.0.3 LOCAL PASS / VISUAL SERVER GATE PENDING`

### Cel

Zanim zaczniemy wdrażać moce profesja po profesji, budujemy i certyfikujemy jeden
powtarzalny model produkcyjny. Nośnikiem pilota jest VIREX V1 / `Insider Feed`,
ale w kontrolowanym trybie operatorskim przez tę samą ścieżkę przechodzą kolejno
wszystkie 9 rodzin dopuszczonych do bieżącej bramki.

Nie oznacza to, że produkcyjny `Insider Feed` dostaje dwanaście efektów. Override
realizera istnieje wyłącznie w lokalnym/testowym trybie operatorskim, jest
wybierany po stronie serwera i nigdy nie występuje w publicznym payloadzie ani
menu gracza. Po zakończeniu certyfikacji V1 zostaje związany tylko z finalnym
`operation_speed`.

### Podsprinty

| Podsprint | Zakres | Wynik |
| --- | --- | --- |
| `138.getway.0.1` | **COMPLETE** — audit 12 rodzin i redukcja ryzyka | 9 rodzin w bramce, 3 jawnie `DEFERRED` |
| `138.getway.0.2` | **LOCAL PASS / SERVER GATE PENDING** — wspólne okno aktywacji + light-read restoration | API, narrow capability projection, lekki scan/zoom snapshot, eligibility, expiry, cooldown i dedupe |
| `138.getway.0.3` | **LOCAL PASS / VISUAL SERVER GATE PENDING** — wspólna prezentacja | przycisk `Insider Feed`, Secret Path overlay, cztery palety klanów, asset V1, istniejący SFX, lokalny timer i tekstowy fallback |
| `138.getway.0.4` | certyfikacja realizerów 9/9 | każdy dopuszczony realizer przechodzi przez V1 pilot na fixture/testowej bazie |
| `138.getway.0.5` | finalny vertical slice V1 | prawdziwy `Insider Feed` z `operation_speed`, 15 min i cooldownem |
| `138.getway.0.6` | kontrolowany SERVER PASS | reload, duplikat, expiry, metryki, korekta schematu i `CONTRACT LOCK` |

### Pilot harness

Pilot korzysta z dokładnie tej samej ścieżki co późniejsza produkcja:

```text
V1 eligibility
  → przycisk Insider Feed
  → backend activation
  → VIREX overlay + asset V1 + SFX
  → server-selected test realizer
  → widoczny skutek
  → timer / reload / expiry / cooldown
```

Testowy realizer może zostać wybrany wyłącznie przez jawny tryb operatorski,
allowlistę i konfigurację procesu testowego. Endpoint aktywacji ignoruje albo
odrzuca `realizer`, `family`, `multiplier` i `parameters` przesłane przez klienta.
Production default nie zna override'u i zawsze używa mapowania katalogowego.
W czasie foundation publiczny runtime ma dodatkowo allowlistę kodów mocy;
domyślnie dopuszcza wyłącznie pilot `insider_feed`. Aktywna część z katalogu,
której kod nie jest jeszcze dopuszczony, zwraca `realizer_unavailable` i nie
tworzy okna. Nie istnieje ciężki ani generyczny fallback.

### Macierz certyfikacji 9/9

Każdy wiersz ma fixture wejściowe, obserwowalny wynik, disabled/no-op, bounded
limit, idempotency i test braku heavy profile:

| Realizer | Fixture pilota | Dowód działania |
| --- | --- | --- |
| `operation_speed` | kilka aktywnych operacji o różnych czasach | zegary skracają się dokładnie raz |
| `file_yield` | operacja gotowa do finalizacji | powstaje bounded liczba dodatkowych plików |
| `data_quality` | camera/audio/credentials o znanej jakości | quality/completeness rośnie w granicach 0–100 |
| `hack_actions` | oznaczony cel z niewykonanymi kropkami | właściwe action dots są wykonane, security pozostaje |
| `target_security` | oznaczony cel z wersjonowaną security map | bounded redukcja/wzmocnienie zachowuje CAS |
| `operation_risk` | aktywna operacja z heat blisko progu | risk meter liczy zmienione wejście, nie wymuszony wynik |
| `scan_range` | cel wewnątrz i poza bazowym zasięgiem | tylko dozwolony zakres/bypass zmienia wynik |
| `map_zoom` | znany bazowy zoom | snapshot/UI pokazuje bounded rozszerzenie |
| `territory_defense` | własny cel z security preset | ochrona zmienia się przez istniejący owner/CAS store |

Testy `.0.4` nie czekają na odpowiadające rodzinom części ani profesje. Ich celem
jest udowodnienie realizera i jego punktu integracji, a nie podjęcie finalnej
decyzji produktowej dla 20 mocy.

### Definition of Done 138.getway.0

- wspólna ścieżka aktywacji działa end-to-end na V1;
- wszystkie cztery palety, assety i fallback prezentacji przechodzą test;
- 9/9 dopuszczonych realizerów ma lokalny/integracyjny PASS na tym samym pilot harness;
- trzy odłożone rodziny są nieosiągalne z endpointu i operator harness;
- finalny `Insider Feed` używa wyłącznie `operation_speed`;
- nie istnieje client-selectable realizer ani możliwość podania mnożnika;
- zero pełnych profile reads/writes i account scan;
- brak dodatkowego workera, kolejki, schedulera, LLM i generycznego interpretera;
- kontrolowany test serwera potwierdza timer, reload, expiry, cooldown i dedupe;
- wzorzec zostaje zamrożony jako szablon dla `.1–.4`.

## 10. 138.getway.1 — pięć mocy VIREX

Etap nie buduje już fundamentu. Korzysta z zamrożonego schematu `.0`: dla każdej
profesji wybiera certyfikowany gameplay realizer, presentation profile, bounded
parametry i wykonuje indywidualny test produktowy/E2E.

| Podsprint | Profesja / część | Pierwsza hipoteza do testu |
| --- | --- | --- |
| `.1.1` | Broker / V1 | **Insider Feed** — promocja pilota `.0.5/.0.6`, finalny tuning `operation_speed` |
| `.1.2` | Architekt / V2 | **Wejście Serwisowe** — `hack_actions`, wszystkie kropki oznaczonego celu wykonane |
| `.1.3` | Manipulator / V3 | **Fałszywy Obraz** — hipoteza do ponownego wyboru spośród 9 bezpiecznych rodzin |
| `.1.4` | Egzekutor Zysku / V4 | **Wrogie Przejęcie** — `data_quality`/`file_yield` dla danych przejętych w oknie |
| `.1.5` | Kurator Algorytmu / V5 | **Predykcja Operacyjna** — podgląd i bounded `operation_risk`/`operation_speed` |

DoD etapu: pięć osobnych decyzji po teście, jeden wspólny UX i pięć małych
hooków lub jawne `DEFER`; brak nowej kolejki/workera.

## 11. 138.getway.2 — Echo Wolności

| Podsprint | Profesja / część | Pierwsza hipoteza do testu |
| --- | --- | --- |
| `.2.1` | Haktywista / E1 | **Ujawnienie** — `target_security`, pokazanie/zdjęcie jednej słabości |
| `.2.2` | Socjotechnik / E2 | **Przejęcie Narracji** — `file_yield` i `data_quality` audio/conversation |
| `.2.3` | Odsłaniacz / E3 | **Pełne Ujawnienie** — `file_yield`/`data_quality` camera i pełniejszy skan |
| `.2.4` | Wizjoner / E4 | **Beacon Oporu** — większy `scan_range` klanu i widoczny beacon |
| `.2.5` | Zapalnik / E5 | **Efekt Domina** — ograniczona redukcja security sąsiednich celów |

Echo ma przede wszystkim dawać więcej treści z kamer i rozmów oraz ujawniać
informacje. Nie tworzymy osobnego systemu narracji ani nowych typów plików.

## 12. 138.getway.3 — Siatka Widmo

| Podsprint | Profesja / część | Pierwsza hipoteza do testu |
| --- | --- | --- |
| `.3.1` | Iluzjonista / P1 | **Węzeł Widmo** — hipoteza do ponownego wyboru spośród 9 bezpiecznych rodzin |
| `.3.2` | Wirusolog / P2 | **Glitch Injection** — bounded `target_security` reduction |
| `.3.3` | Paranoik / P3 | **Fałszywe Tropienie** — skan niezależny od pozycji motocykla |
| `.3.4` | Rozłamowiec / P4 | **Pęknięcie Sieci** — miks `scan_range` i zakłóceń markerów |
| `.3.5` | Lustrzany Sędzia / P5 | **Odbicie** — `operation_risk`/`target_security`, bez skanu aktorów |

Siatka Widmo może dawać szeroki i chaotyczny rezultat, ale wyłącznie przez
istniejące typy danych, markery, aktorów, incydenty i zabezpieczenia.

## 13. 138.getway.4 — Strażnicy Ładu

| Podsprint | Profesja / część | Pierwsza hipoteza do testu |
| --- | --- | --- |
| `.4.1` | Analizator / S1 | **Skan Integralności** — `target_security` i stan ochrony własnych celów |
| `.4.2` | Obrońca / S2 | **Bastion** — czasowe `territory_defense` |
| `.4.3` | Rekonstruktor / S3 | **Odtworzenie** — przywrócenie zabezpieczeń istniejącym presetem |
| `.4.4` | Mediator / S4 | **Korytarz Zaufania** — większy `scan_range`/action range na własnym obszarze |
| `.4.5` | Egzekutor / S5 | **Kwarantanna** — ograniczenie startu wrogich operacji na chronionych celach |

Strażnicy wzmacniają istniejące zabezpieczenia i czytelność stanu. Nie powstaje
osobny system fortyfikacji.

## 14. 138.getway.5 — polish

Polish przechodzi profesja po profesji:

```text
.5.01–05  VIREX
.5.06–10  Echo Wolności
.5.11–15  Siatka Widmo
.5.16–20  Strażnicy Ładu
.5.final  cross-clan UX, balans i GO/NO-GO
```

Zakres polish:

- finalne copy semantyczne, asset, SFX i CSS każdej mocy;
- zgodność overlayu, badge'a i efektu 15 min z paletą właściwego klanu;
- miniatura assetu aktywnej części widoczna przy timerze do końca wpływu;
- czytelność przycisku, timera i cooldownu na desktop/mobile;
- korekta mnożników, capów oraz `15 min / 1 h`;
- widoczny dowód działania bez otwierania debuggera;
- fallback przy braku audio/assetu i System Message przy odrzuceniu;
- prosty test reload/restart: serwer zachowuje `expires_at/cooldown_until`;
- sprawdzenie, że syntetyczne incydenty nie wpływają na realne kary/nagrody;
- aktualny audyt 20/20: nazwa, rodzina parametru, call-site i evidence.

Nie są częścią polish: nowy worker, queue, event bus, język skryptowy efektów,
drugi system profili, osobna topologia ani LLM w ścieżce aktywacji.

## 15. Minimalna macierz testowa

Każda moc musi przejść:

1. brak części/zła profesja/zły klan → brak przycisku i fail-closed endpointu;
2. poprawny gracz → dokładnie jedno aktywne okno;
3. show 4–6 s → asset, CSS, SFX albo tekstowy fallback;
4. po show → poprawny timer i widoczny skutek istniejącego mechanizmu;
5. reload → ten sam `expires_at`, bez restartu cooldownu;
6. podwójny klik → brak drugiego efektu;
7. po 15 minutach → brak modyfikatora i CSS;
8. przed końcem cooldownu → czytelne odrzucenie z pozostałym czasem;
9. utrata części/cycle lock → brak nowej aktywacji;
10. żadna moc nie omija owner checks, CAS, audience safety ani session generation.

Nie wymagamy rozbudowanej macierzy crash/replay osobnej dla 20 mocy. Trwałość
sprawdzamy raz dla wspólnego okna, a każdy podsprint testuje tylko swój mały hook.

## 16. Bramka wejścia do 138.2

```text
Secret Path-style activation shell:             PASS
V1 pilot and realizer certification:               9/9 PASS
deferred high-risk families reachable:              0/3
server-only override removed/disabled in prod:   PASS
timer 15 min + cooldown + reload:                PASS
VIREX decisions and visible effects:             5/5 or accepted DEFER
Echo decisions and visible effects:              5/5 or accepted DEFER
Phantom decisions and visible effects:           5/5 or accepted DEFER
Sentinel decisions and visible effects:          5/5 or accepted DEFER
polish profession-by-profession:                  PASS
no parallel ability runtime/pipeline introduced: PASS
heavy profile full reads/writes/account scans:     0 / 0 / 0
bounded DB reads/writes and SQLite lock audit:     PASS
operator decision:                               GO FOR 138.2
```

Do czasu spełnienia bramki obowiązuje `DO NOT TRIGGER 20/20`.
