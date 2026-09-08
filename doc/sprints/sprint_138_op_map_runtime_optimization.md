# 138.op — optymalizacja runtime mapy przed pełnym testem 138.2

Status: `REQUIRED / BLOCKING 138.2`

Źródło: audyt przeciążenia mapy wykonany po wdrożeniu kolejnych mocy
`138.getway`, przy stanie świata obejmującym dziesiątki aktywnych operacji,
kilka konfliktów, aktywne NPC, terytoria oraz około 15 widocznych części
GhostNetwork.

## 1. Cel

Mapa musi zachować pełną informację gameplayową i oprawę CHAOS, ale ruch,
zoom oraz akcje nie mogą zależeć od klasy telefonu lub komputera. Sprint nie
ogranicza liczby operacji, części, konfliktów ani terytoriów. Usuwa koszt
renderowania, który rośnie liniowo wraz z liczbą widocznych obiektów.

Sprint `138.op` jest ostatnią bramką techniczną po `138.getway.0–5`, a przed
pełnym producer-backed E2E/failure/soak `138.2`.

## 2. Ustalenia audytu

Przeciążenie jest przede wszystkim frontendowym kosztem main thread,
kompozycji i paintu, a nie dowodem przeciążenia backendu.

Najważniejsze źródła kosztu:

1. Centrum Operacji używa `backdrop-filter` nad ruchomą mapą, a karty dotknięte
   supermocami mają animowane cienie, gradienty i filtry.
2. NPC konfliktów są aktualizowane cyklicznie; aktualizacja pozycji wykonuje też
   `setIcon()`, czyli odbudowuje DOM ikony, asset, licznik i klasy.
3. Refresh operacji usuwa i odtwarza wszystkie markery oraz cały HTML panelu,
   nawet gdy zmienił się tylko zegar lub jedna operacja.
4. Desktopowa topologia GhostNetwork mnoży jedno połączenie do dwóch lub trzech
   ścieżek SVG z `drop-shadow`, pulsem i animowanym `stroke-dashoffset`.
5. Aktywne/wrogie terytoria używają animowanych filtrów SVG, które zwiększają
   obszar repaintu podczas ruchu i zoomu.
6. Kontrolka aktywnej supermocy co sekundę odbudowuje cały badge wraz z obrazem,
   zamiast zmienić wyłącznie tekst zegara.
7. Warstwowe snapshoty wywołują `invalidateSize()` po zwykłej zmianie danych,
   mimo że rozmiar kontenera mapy się nie zmienił.

Surowa liczba polygonów nie jest sama w sobie główną diagnozą. Problemem jest
połączenie dużego półprzezroczystego panelu, stale animowanych filtrów SVG,
częstych przebudów DOM oraz wielu markerów aktualizowanych pełnym `setIcon()`.

## 3. Granice nienaruszalne

- zero zmian parametrów, czasu, cooldownu i skutku supermocy;
- zero ukrywania informacji gameplayowej po zakończeniu gestu mapy;
- zero limitu liczby operacji, terytoriów, części lub konfliktów w canonical
  store;
- bez nowego workera, pollera, kolejki, store'u i ciężkiego profilu;
- istniejące delty, owner checks, CAS i session generation pozostają authority;
- tryb wydajnościowy może upraszczać dekorację, ale nie stan, kolor klanu,
  pozycję, timer, target ani możliwość wykonania akcji;
- żadna optymalizacja nie może przywrócić problemu z brakującymi terytoriami,
  częściami albo konfliktami po snapshot recovery.

## 4. 138.op.1 — interaction fast path

Status: `IMPLEMENTED / LOCAL PASS / SERVER-DEVICE PARTIAL`

Cel: gest `drag/zoom` ma pierwszeństwo przed dekoracją.

Zakres:

- `dragstart/movestart/zoomstart` ustawia na kontenerze mapy klasę
  `is-map-interacting`;
- w tej klasie wyłączone są `backdrop-filter`, animowane `box-shadow`, filtry
  SVG, pulsy połączeń, drżenie części i animacje kart operacji;
- około 100–200 ms po `dragend/moveend/zoomend` dekoracja wraca bez przebudowy
  warstw;
- na urządzeniu mobilnym/coarse pointer Centrum Operacji stale używa
  nieprzezroczystego lub półprzezroczystego tła bez blur;
- semantyczne wyróżnienie SP pozostaje statyczne podczas gestu: kolor, ramka,
  etykieta i stan nie znikają;
- ruch NPC jest wstrzymany na czas aktywnego gestu i uzgadniany po jego końcu;
- `prefers-reduced-motion` oraz jawny low-power mode korzystają z tego samego
  kontraktu, bez osobnej ścieżki gameplayowej.

### Bramka `.op.1`

- pan i pinch-zoom odpowiadają bez widocznego oczekiwania na blur/glow;
- panel, części, operacje i terytoria zachowują pozycję oraz stan;
- po zatrzymaniu mapy pełna dekoracja wraca tylko tam, gdzie urządzenie nie jest
  w stałym low-power mode;
- brak dodatkowego requestu, snapshotu lub zapisu wywołanego samym gestem;
- desktop, narrow viewport i coarse pointer mają test kontraktowy CSS/JS.

### Implementacja `.op.1`

- wspólny stan `window.chaosMapInteractionState` jest aktywowany przez
  `dragstart/movestart/zoomstart` i wygaszany `160 ms` po ostatnim
  `dragend/moveend/zoomend`;
- klasa `is-map-interacting` trafia równocześnie na kontener Leaflet i `body`,
  dzięki czemu obejmuje warstwy mapy oraz Centrum Operacji bez przenoszenia DOM;
- podczas gestu wyłączone są blur panelu, animacje kart, filtry i animacje GN,
  animacje terytoriów, połączeń, NPC oraz globalnego efektu aktywnej SP;
- obramowanie, kolor, etykieta, timer, pozycja i stan pozostają widoczne;
- pętla pozycji i lokalnej detekcji NPC nie wykonuje pracy podczas gestu. Po
  settle zeruje cadence i uzgadnia stan w następnej klatce animacji;
- coarse pointer i `prefers-reduced-motion` automatycznie włączają trwały
  `is-map-low-power`. Jawny override jest dostępny przez
  `window.setChaosMapLowPowerMode(true|false)` i zapis `chaos_map_low_power`;
- żaden handler fast path nie wykonuje `fetch`, `invalidateSize`, reloadu,
  `setView` ani zapisu gameplayowego.

Lokalna bramka: `110/110` testów Python mapy/NPC/GhostNetwork oraz `10/10`
pakietów JS mapy, snapshot recovery, target hitbox, operacji, SFX i motocykla:
PASS. `git diff --check`: PASS. Do zamknięcia `.op.1` pozostaje test gestów na
serwerze: telefon/coarse pointer oraz komputer referencyjny.

## 5. 138.op.2 — incremental operations and NPC runtime

Status: `IMPLEMENTED / LOCAL PASS / DESKTOP SERVER PASS / MOBILE ZOOM-OUT BLOCKED`

Cel: koszt aktualizacji zależy od liczby zmienionych rekordów, nie od liczby
wszystkich rekordów na mapie.

Zakres:

- markery operacji są uzgadniane po `operation_id`: add/update/remove bez
  `clear all`;
- panel jest przebudowywany tylko po zmianie sygnatury danych; zegary aktualizują
  istniejące text nodes;
- historia nie jest formatowana ani renderowana, gdy aktywna jest zakładka
  bieżących operacji;
- `invalidateSize()` pozostaje wyłącznie dla realnej zmiany wymiaru kontenera;
- NPC używa `setLatLng()` dla ruchu, a `setIcon()` tylko po zmianie
  kierunku, rodziny, stanu lub feedbacku;
- licznik NPC jest aktualizowany w istniejącym DOM nie częściej niż raz na
  sekundę;
- cadence NPC jest ograniczony na słabym urządzeniu, podczas ukrytej karty i
  poza viewportem; lokalna detekcja zachowuje dotychczasową semantykę serwerową;
- badge SP mutuje wyłącznie stan i zegar, bez ponownego tworzenia assetu co
  sekundę;
- snapshot pozostaje recovery baseline, a delty pozostają główną drogą
  małych aktualizacji.

### Bramka `.op.2`

- 30+ operacji nie powoduje cyklicznego znikania i odtwarzania markerów;
- pojedyncza zmiana operacji dotyka jednego markera i jednej karty;
- kilka konfliktów nie powoduje pełnego `setIcon()` każdego NPC w każdym ticku;
- countdown operacji, NPC i SP pozostaje zgodny po reloadzie i po wznowieniu
  ukrytej karty;
- brak regresji anulowania operacji, incydentów, detekcji i lifecycle terytorium.

### Implementacja `.op.2`

- registry markerów operacji jest trwałą mapą `operation_id -> marker`; snapshot
  uzgadnia add/update/remove, ale nie czyści całej warstwy;
- zmiana pozycji operacji używa `setLatLng`, zmiana prezentacji używa `setIcon`,
  a sam countdown mutuje istniejący text node raz na sekundę;
- Centrum Operacji używa sygnatur danych bez pól zegarowych. Niezmienione karty
  zachowują swój DOM, zmieniona operacja wymienia wyłącznie własną kartę, a
  historia jest budowana dopiero po wejściu do zakładki `Historia`;
- kontrolka SP zachowuje asset i strukturę badge'a w obrębie tego samego okna;
  tick zmienia tylko tekst stanu oraz czasu;
- kapsuły Response Network zachowują marker i poruszają go przez `setLatLng`.
  `setIcon` występuje tylko po zmianie rodziny, kierunku, stanu animacji albo
  krótkiego feedbacku detekcji;
- countdown NPC ma osobny, sekundowy update istniejącego DOM. Pozycja pozostaje
  wyliczana z czasu serwera, więc wznowienie karty nie powoduje dryfu;
- cadence wizualny NPC wynosi `240 ms` w aktywnym widoku, `520 ms` w low-power
  i `1000 ms` dla ukrytej karty lub obiektu poza rozszerzonym viewportem.
  Lokalny probe detekcji zachowuje niezależny kontrakt `1200 ms`;
- `invalidateSize()` jest chronione sygnaturą realnych wymiarów kontenera i
  wywoływane przez `ResizeObserver`, a nie przez każdą zmianę warstwy.

Lokalna bramka: `445/445` testów Python GhostNetwork, `10/10` pakietów JS mapy,
delta, operacji, SFX i motocykla oraz `52/52` celowanych kontraktów `.op.2`/NPC/
map loader/SP: PASS. Renderowanie szablonu `/map`: `3/3 PASS`.
`git diff --check`: PASS. Do zamknięcia pozostaje test serwerowy pod obciążeniem
30+ operacji i kilkoma konfliktami, szczególnie na Redmi/coarse pointer.

Test produkcyjny po wdrożeniu potwierdził wyraźną poprawę oraz stabilny desktop.
Na urządzeniu mobilnym agresywna redukcja zoomu nadal może zablokować mapę na
około `10 s`, po czym widok wraca do działania. Test odbył się już po zakończeniu
części operacji, dlatego nie przypisujemy całej poprawy wyłącznie `.op.2`.
Wynik klasyfikujemy jako częściowy pass ścieżki incremental oraz blocker mobilny
przeniesiony do `.op.3`: LOD, viewport culling i ograniczenie kosztu warstw
montowanych/odmalowywanych podczas `zoom-out`.

## 6. 138.op.3 — map LOD, culling i performance gate

Status: `IMPLEMENTED / LOCAL PASS / SERVER-DEVICE TEST PENDING`

Cel: koszt widoku zależy od viewportu i poziomu szczegółowości, a nie od całego
świata zwróconego w snapshotach.

Zakres:

- połączenia GN w interaction/low-power mode używają jednej statycznej ścieżki
  Canvas bez glow i pulse; pełne 2–3 warstwy są dekoracją desktop idle;
- markery operacji, NPC i dekoracyjne części poza rozszerzonym viewportem nie są
  montowane albo nie są aktualizowane do chwili wejścia w widok;
- terytoria zachowują canonical geometrię i kolor klanu, ale animowany filtr
  nie działa podczas gestu ani w low-power mode;
- zoom korzysta z poziomów szczegółowości: daleki widok pokazuje stan
  strategiczny, bliski widok pełne markery i dekorację;
- registry Leafleta pozostają stabilne i nie kumulują historycznych warstw po
  delta recovery, konsolidacji konfliktu i ponownym otwarciu mapy;
- powstaje lekki development probe liczby Leaflet layers, SVG paths, markerów,
  aktywnych animacji, long tasks i czasu reconcile, bez telemetry payloadów
  gracza.

### Implementacja `.op.3`

- mobilny/low-power TileLayer nie aktualizuje kafelków w każdej klatce zoomu;
  pobieranie i montaż następują po uspokojeniu gestu, z buforem ograniczonym do
  jednego pierścienia kafelków;
- terytoria, fronty i obszary konfliktów używają na mobile/low-power wspólnego
  renderera Canvas. Canonical geometria, kolor klanu, dash i semantyczny stan
  pozostają bez zmian;
- wprowadzono trzy poziomy LOD (`detail`, `tactical`, `strategic`) zależne od
  realnego zoomu i klasy urządzenia. Przejście poziomu odbywa się najwyżej raz
  na klatkę i nie uruchamia requestu ani przebudowy snapshotu;
- połączenie GhostNetwork w trybie oddalonym/mobile/low-power jest pojedynczą,
  przycinaną do viewportu ścieżką Canvas. Pełny warstwowy SVG z glow pozostaje
  wyłącznie dekoracją bliskiego widoku na desktopie;
- markery operacji, Response Network, części GN, badge'e terytoriów GN i wyniki
  dużych skanów są wybierane przez rozszerzony viewport oraz ekranową siatkę.
  Poza wyborem pozostają w canonical registry, lecz nie są montowane w DOM;
- nowe markery skanu, operacji i NPC trafiają najpierw do registry, a dopiero
  potem do warstwy mapy po reconcile LOD. Eliminuje to koszt masowego
  `addTo(map)` poprzedzającego natychmiastowe odpięcie;
- odpięcie używa istniejącego obiektu Leaflet, więc zachowuje snapshot kontekstu,
  tooltip, popup oraz powiązanie `marker -> menu`; powrót do viewportu nie tworzy
  nowej tożsamości markera;
- opcjonalny, lokalny probe `window.chaosMapPerformanceProbe()` raportuje liczbę
  warstw, SVG, markerów kanonicznych i zamontowanych oraz Long Tasks. Observer
  działa tylko po ustawieniu `localStorage.chaos_map_perf_probe = '1'` i nie
  wysyła telemetrii.

Lokalna bramka: `114/114` celowanych testów kontraktów LOD, map loadera, menu,
terytoriów i recovery oraz `10/10` pakietów JS mapy/GN/delta/operacji/motocykla:
PASS. Pełna regresja GhostNetwork: `444/445` w pierwszym przebiegu; jedyny błąd
powstał podczas współbieżnej inicjalizacji testowego SQLite na Windows
(`duplicate column name`), a izolowany rerun tego testu: `1/1 PASS`.
`git diff --check` i kontrola składni JS: PASS. Do zamknięcia pozostaje test
serwerowy zoom-out/pan na Redmi oraz desktopie przy obciążeniu referencyjnym.

### Obciążenie referencyjne `.op.3`

```text
active operations:       >= 30
territories:             >= 40
active conflicts:        >= 3
visible GN parts:        15–20
GN connections:          rzeczywista topologia scenariusza
NPC capsules:            rzeczywisty fan-out konfliktów
```

### Bramka końcowa `.op.3`

- telefon/coarse pointer: responsywny pan i pinch-zoom bez wielosekundowej
  blokady wejścia;
- słaby komputer: brak powtarzalnych ponadsekundowych zatrzymań przy refreshu
  operacji i NPC;
- desktop referencyjny: brak widocznych okresowych przycięć mimo pełnej
  dekoracji idle;
- w nagraniu Performance nie występuje pojedynczy powtarzalny long task
  przekraczający 250 ms podczas zwykłego gestu;
- wszystkie warstwy wracają po pan/zoom, reloadzie, delta gap recovery i
  ponownym otwarciu mapy;
- operacje, konflikty, części GN, kolory terytoriów i wszystkie efekty
  supermocy przechodzą gameplay regression;
- operator wykonuje test na co najmniej jednym słabym telefonie i jednym
  komputerze referencyjnym oraz zapisuje wynik jako `SERVER/DEVICE PASS`.

## 7. Kolejność i bramka 138.2

```text
138.getway.0–5 gameplay closure:     REQUIRED
138.op.1 interaction fast path:      REQUIRED / SERVER-DEVICE PASS
138.op.2 incremental runtime:        REQUIRED / SERVER-DEVICE PASS
138.op.3 LOD + load gate:            REQUIRED / SERVER-DEVICE PASS
138.2 producer E2E/failure/soak:     BLOCKED UNTIL ALL ABOVE PASS
```

Implementacja przebiega kolejno `.op.1`, `.op.2`, `.op.3`. Nie łączymy jej z
dalszym montażem profesji, chyba że poprawka jest konieczna do utrzymania
niezmiennego kontraktu wizualnego danego realizera.

## 8. Definition of Done

`138.op` jest zakończony, gdy obciążony rzeczywistym stanem świata widok mapy
jest grywalny na słabym telefonie, nie ma cyklicznych pełnych przebudów warstw,
stosuje statyczny fallback dekoracji podczas gestu/low-power, a po optymalizacji
nie zmienił żadnej reguły gameplay, authority ani trwałego modelu danych.
