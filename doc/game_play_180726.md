# game_play_180726.md

Kontynuacja planu z `doc/game_play_260626.md`.

`doc/game_play_260626.md` zamyka aktywny plan na Sprincie 103. Ten plik zaczyna
nowy etap od Sprintu 104.

---

# Faza J - Ghost Control Suite / Mapless Control Layer

Faza J rozwija narzedzia kontroli gry bez koniecznosci stalego otwierania mapy.

Cel etapu:

* Victim Picker wybiera cel bez Leafleta,
* Territory Control zarzadza przejetym terenem,
* Operation Control pilnuje trwajacych operacji i incydentow,
* mapa pozostaje zrodlem przestrzeni, ale nie musi byc jedynym panelem pracy,
* aplikacje korzystaja z istniejacych zrodel prawdy i nie tworza drugiego
  runtime terytoriow, operacji ani incydentow.

Zasada Fazy J:

```text
Mapa pokazuje swiat.
Ghost Control Suite pozwala nim operacyjnie zarzadzac.
```

---

**Victim Picker wybiera cel, Territory Control zarządza przejętym terenem, a Operation Control pilnuje trwających operacji i incydentów bez ładowania mapy.**

# Rodzina: Ghost Control Suite

Nazwy robocze:

* **Victim Picker** — `100 000 HC`
* **Territory Control** — `50 000 HC`
* **Operation Control** — `20 000 HC`

Wszystkie pozostają:

```text
type: pro-system-tool
category: pro-system-tools
```

Nie tworzymy nowej kategorii gameplayowej ani nowego typu aplikacji. Rodzina może dostać wyłącznie metadane prezentacyjne:

```text
family_id: ghost_control_suite
icon_pack: ghost_control
```

Dzięki temu Googleplex, zakup i instalacja nadal używają obecnego systemu `PRO_SYSTEM_TOOLS`, a aplikacje mają wspólny wygląd i zestaw ikon.

---

# Sprint 104 — Ghost Control Suite: audyt i wspólny kontrakt

## Cel

Przed budową dwóch aplikacji dokładnie ustalić istniejące źródła prawdy dla:

* klastrów terytorium,
* filarów i obiektów wewnętrznych,
* konfliktów i ataków,
* zabezpieczeń przejętych obiektów,
* porzucania obiektów,
* aktywnych operacji,
* plików generowanych przez operacje,
* incydentów powiązanych z operacjami,
* anulowania pojedynczego i grupowego.

Sprint jest audytowy. Nie buduje jeszcze nowych okien.

## 1. Audyt klastrów terytorium

Sprawdzić, czym w aktualnym systemie jest pojedynczy „klaster”:

* rekordem `player_area`,
* spójną grupą przejętych obiektów,
* wielokątem wyliczonym z filarów,
* wynikiem `rebuild_player_areas`,
* czy połączeniem powyższych elementów.

Nie tworzyć nowego modelu klastra, jeżeli obecny `TerritoryStore` i `player areas` już posiadają stabilną tożsamość.

Aktualny endpoint mapy zwraca obszary gracza, ich identyfikatory, centroidy, powierzchnię, status, konflikty i sporne cele, więc nowa aplikacja powinna korzystać z tej samej warstwy danych, ale z lżejszego payloadu bez Folium. 

## 2. Filar kontra inner

Audyt ma jednoznacznie ustalić, jak rozpoznać:

* **filar** — obiekt budujący zewnętrzną geometrię klastra,
* **inner** — przejęty obiekt znajdujący się wewnątrz klastra, ale niebędący jego filarem.

Nie określać tego na frontendzie na podstawie kolejności listy albo wyglądu markera.

Jeżeli obecny builder terytorium nie zwraca jawnego `node_role`, wydzielić wspólny helper backendowy:

```text
resolve_territory_node_role(cluster, target)
```

Zwracane role:

```text
pillar
inner
```

## 3. Kontrakt stanu zagrożenia klastra

Backend, a nie CSS, wylicza:

```text
neutral
collision
attacked
```

Zasady:

* `neutral` — klaster nie uczestniczy w aktywnym konflikcie,
* `collision` — klaster przecina się z innym aktywnym obszarem, ale żaden należący do gracza filar nie jest obecnie przejmowany lub utracony,
* `attacked` — aktywny konflikt obejmuje należący do gracza filar albo istniejący stan konfliktu wskazuje jego przejęcie, utratę lub aktywny atak.

Priorytet:

```text
attacked > collision > neutral
```

Kolory:

* zielony — `neutral`,
* pomarańczowy — `collision`,
* czerwony — `attacked`.

Istniejący system konfliktów przechowuje przecięcia obszarów oraz stany celów `contested` i `captured`, więc należy z nich utworzyć jeden kanoniczny `threat_state`, zamiast ponownie wykrywać konflikt w aplikacji. 

## 4. Audyt zabezpieczeń obiektów

Znaleźć i opisać dokładne ścieżki:

* odczyt zabezpieczeń przejętego obiektu,
* zmiana pojedynczej wartości,
* preset `open`,
* preset `low`,
* preset `regular`,
* preset `secure`,
* preset `all`,
* zapis do profilu i `TerritoryStore`,
* aktualizacja konfliktów po zmianie obiektu.

Mapa ma już pięć presetów oraz panel wartości zabezpieczeń, więc Territory Control powinien przenieść tę mechanikę do okna, a nie tworzyć własny zestaw poziomów. 

## 5. Audyt porzucania obiektu

Znaleźć faktyczną procedurę usuwania własnego przejętego obiektu.

Porzucenie musi:

* usunąć obiekt z istniejącego magazynu przejętych celów,
* usunąć odpowiedni wpis profilu,
* wyczyścić `aimed_target`, jeśli wskazywał porzucony obiekt,
* przebudować terytorium,
* ponownie wykryć konflikty,
* opublikować delty,
* poinformować aplikację, czy klaster nadal istnieje.

Nie implementować porzucenia jako zwykłego usunięcia elementu z tablicy frontendowej.

Jasne — trzeba to dopisać jako twardą regułę lifecycle klastra, bo inaczej Codex może potraktować dwa filary jak mały klaster albo usunąć je razem z rozpadem obszaru.

### audyt i kontrakt klastra

* Klaster może powstać wyłącznie z **minimum trzech poprawnych filarów**.
* Jeden lub dwa filary nie tworzą klastra, poligonu ani obszaru terytorium.
* Filary niepołączone w klaster otrzymują stan roboczy `alone`.
* Obiekty typu `inner` nie są wliczane do minimalnej liczby filarów.
* Trzeci filar uruchamia istniejącą procedurę przebudowy i dopiero wtedy może powstać klaster.
* Audyt ma potwierdzić, jak obecny builder rozpoznaje trzy filary należące do jednej możliwej struktury.
* Nie wolno tworzyć sztucznego klastra dla dwóch filarów tylko po to, aby pokazać je w Territory Control.
* Należy ustalić zachowanie obiektów `inner` po rozpadzie klastra; nie wolno automatycznie zamieniać ich w filary ani przepisywać do innego klastra.


## 6. Audyt operacji

Prześledzić:

* `operation_type`,
* `map_action_id`,
* `target`,
* aktualną pozycję operacji,
* `resource_types`,
* `resource_buffer`,
* docelową kategorię pliku,
* przewidywany rozmiar,
* pozostały czas,
* ryzyko,
* `operation_risk_meter`,
* `incident_id`,
* warning i Response Network,
* anulowanie operacji.

Aktualne API zwraca aktywne operacje i historię, a osobny endpoint anuluje pojedynczą operację przez istniejący helper profilu. Nowa aplikacja ma tę ścieżkę rozszerzyć, a nie zastąpić. 

## 7. Rodziny operacji

Ustalić jeden centralny mapping, na przykład:

```text
recon
gps
device
camera
audio
network
atm
vehicle
implant
other
```

Grupa nie może być wyliczana z tekstowej nazwy wyświetlanej w GUI.

Powinna wynikać z:

* `operation_type`,
* `map_action_id`,
* `resource_types`,
* rodzaju generowanego pliku.

Przykładowo `vehicle_tracking`, `device_tracking`, `camera_stream`, `atm_log_extraction`, `persistent_sniffer` i inne typy już istnieją jako osobne operacje. 

## 8. Wspólny zestaw ikon

Przygotować kontrakt jednego zestawu:

```text
GHOST_CONTROL_ICONS
```

Ikony wspólne:

* `back`
* `refresh`
* `map`
* `teleport`
* `distance`
* `bike`
* `warning`
* `incident`
* `security`
* `abandon`
* `cancel`
* `cancelGroup`
* `timer`
* `file`
* `loading`
* `error`

Ikony terytorium:

* `territory`
* `cluster`
* `pillar`
* `inner`
* `collision`
* `attacked`
* `neutral`

Ikony operacji:

* `operations`
* `recon`
* `gps`
* `device`
* `camera`
* `audio`
* `network`
* `atm`
* `vehicle`
* `implant`

Pięć presetów zabezpieczeń pozostaje jako krótkie, czytelne etykiety:

```text
OPEN  LOW  REGULAR  SECURE  ALL
```

Nie warto zastępować ich pięcioma abstrakcyjnymi symbolami. Wspólny zestaw ikon dotyczy uniwersalnych akcji i statusów.

## Wynik Sprintu 104

Dokument zawierający:

* istniejące źródła danych,
* stabilny identyfikator klastra,
* sposób przypisywania obiektu do klastra,
* sposób rozróżnienia pillar/inner,
* reguły `threat_state`,
* mapę zabezpieczeń i presetów,
* ścieżkę porzucenia obiektu,
* mapping rodzin operacji,
* mapping plików wynikowych,
* powiązanie operacja–incydent,
* kontrakt wspólnych ikon,
* plan endpointów i testów.

## DoD

Nie ma niejasności, które mogłyby skłonić Codex do stworzenia:

* drugiego systemu terytoriów,
* nowej listy przejętych obiektów,
* nowego systemu zabezpieczeń,
* nowego systemu incydentów,
* alternatywnego mechanizmu anulowania operacji.

Ten sprint opisuje istniejącą mechanikę i miejsca, do których mają zostać podłączone nowe lekkie interfejsy.

---

# Sprint 105 — Territory Control: backend i mechanika

## Cel

Dodać produkt za `50 000 HC` oraz lekkie API pozwalające zarządzać własnymi klastrami i ich obiektami bez uruchamiania mapy.

## 1. Produkt Googleplex

Dodać do `PRO_SYSTEM_TOOLS`:

```text
id: territoryControl
name: Territory Control
price: 50000
family_id: ghost_control_suite
icon_pack: ghost_control
system_launcher: territory_control
```

Opis:

> Lekka konsola zarządzania własnymi klastrami, filarami i zabezpieczeniami przejętych obiektów bez uruchamiania pełnej mapy.

Zachować obecną ścieżkę zakupu, instalacji i ikony pulpitu.

## 2. Lekki endpoint listy klastrów

Dodać lekki odczyt, który nie renderuje mapy i nie wykonuje pełnego snapshotu świata.

Przykładowy kontrakt:

```text
GET /api/pro-system/territory-control
```

Każdy klaster zwraca:

```text
cluster_id
label
status
threat_state
node_count
pillar_count
inner_count
area_size
perimeter
conflict_count
attacked_pillars_count
centroid
navigation_target
distance_from_bike
map_focus
```

`distance_from_bike` liczyć od aktualnej pozycji motocykla do najbliższego własnego obiektu należącego do klastra.

Nie liczyć odległości do losowego narożnika wielokąta.

`navigation_target` powinien wskazywać najbliższy własny węzeł klastra. To do niego prowadzi teleport z listy klastrów.

## 3. Szczegóły klastra

```text
GET /api/pro-system/territory-control/<cluster_id>
```

Zwraca:

* parametry klastra,
* aktualny stan konfliktu,
* wszystkie przejęte obiekty należące do obszaru,
* osobną listę `pillars`,
* osobną listę `inners`.

Każdy obiekt:

```text
target_id
label
icon
source_type
node_role
lat
lng
distance_from_bike
security
security_enabled
security_total
security_percent
is_aimed
can_abandon
disabled_reason
```

Filary są wyróżnione przez `node_role: pillar`, a nie przez dodatkową kopię danych.

## 4. Poziom zabezpieczeń

`security_percent` ma korzystać z tego samego zestawu booleanów co obecny panel zabezpieczeń.

Przykład:

```text
18 aktywnych / 32 dostępne = 56%
```

Pasek nie pokazuje stopnia zhakowania. Pokazuje faktyczny poziom uzbrojenia własnego obiektu.

## 5. Presety

Territory Control używa dokładnie tych samych presetów:

* `open`
* `low`
* `regular`
* `secure`
* `all`

Nie tworzyć endpointów z innymi regułami. Wydzielić wspólny helper używany przez mapę i aplikację albo bezpieczny adapter do istniejącej procedury.

Po zmianie response zwraca:

* nowy stan zabezpieczeń,
* nowy procent,
* reguły konfliktowe, które automatycznie wyłączyły inne zabezpieczenia,
* aktualny snapshot obiektu.

## 6. Porzuć obiekt

Akcja wymaga potwierdzenia.

Po porzuceniu:

1. usunąć obiekt istniejącą ścieżką,
2. przebudować klastry,
3. przebudować konflikty,
4. wyczyścić target, jeśli potrzeba,
5. zwrócić nową listę klastrów.

Jeśli porzucony filar:

* zmieni geometrię,
* podzieli klaster,
* usunie klaster,
* zmieni rolę innych filarów,

aplikacja nie może próbować ręcznie poprawiać starego widoku. Pobiera świeży snapshot.

### Dopisek do Sprintu 105 — backend Territory Control

#### Minimalna liczba filarów

Backend przy budowaniu snapshotu terytorium musi stosować regułę:

```text
pillar_count >= 3 → klaster może istnieć
pillar_count < 3  → klaster nie istnieje
```

* Przy jednym lub dwóch filarach backend zwraca je jako `alone_pillars`.
* `alone_pillars` nie mogą otrzymywać `cluster_id`.
* Dla samotnych filarów nie zwracać sztucznego `area_size`, `perimeter` ani stanu konfliktu klastra.
* Samotne filary zachowują przejęcie, dane obiektu, zabezpieczenia, pozycję i możliwość pokazania na mapie lub teleportu.
* Po pojawieniu się trzeciego poprawnego filaru system wykonuje pełny rebuild i może przenieść wcześniejsze filary `alone` do nowego klastra.

#### Rozpad klastra

Po porzuceniu albo utracie filaru backend musi ponownie przeliczyć klaster.

Jeżeli po operacji pozostają mniej niż trzy filary:

1. klaster zostaje rozwiązany,
2. jego poligon znika,
3. `cluster_id` przestaje być aktywny,
4. stan kolizji lub ataku tego klastra zostaje zamknięty albo przeliczony istniejącą procedurą,
5. pozostałe filary nie są usuwane,
6. pozostałe filary otrzymują stan `alone`,
7. frontend otrzymuje pełny świeży snapshot, a nie częściową poprawkę starego klastra.

Nie wolno usuwać dwóch pozostałych filarów tylko dlatego, że przestały tworzyć obszar.

### Dopisek do kontraktu endpointu

Oprócz listy klastrów odpowiedź powinna zawierać:

```text
clusters
alone_pillars
```

Każdy samotny filar:

```text
target_id
label
icon
lat
lng
distance_from_bike
security
security_percent
state: alone
can_show_on_map
can_teleport
```



## 7. Pokaż na mapie i teleport

`Pokaż klaster na mapie`:

* otwiera mapę dopiero na żądanie,
* przekazuje `cluster_id`,
* ustawia fokus na poligonie lub jego centroidzie,
* nie wykonuje teleportu.

`Teleport do klastra`:

* używa `navigation_target`,
* korzysta z obecnego potwierdzenia,
* korzysta z istniejącej procedury teleportacji.

Dla pozycji obiektu:

* mapa skupia się na konkretnym obiekcie,
* teleport prowadzi do jego współrzędnych.

## Testy Sprintu 105

* gracz bez klastrów,
* jeden neutralny klaster,
* kilka oddzielnych klastrów,
* klaster w kolizji,
* klaster aktywnie atakowany,
* poprawny priorytet czerwonego stanu,
* poprawna liczba filarów i innerów,
* poprawna odległość od motocykla,
* zmiana każdego presetu,
* konflikty zabezpieczeń,
* porzucenie innera,
* porzucenie filaru,
* podział klastra,
* zniknięcie klastra,
* fokus mapy,
* teleport,
* blokada manipulowania cudzym obiektem.

### Dopisek do testów Sprintu 105 

* brak filarów — brak klastra,
* jeden filar — `alone`, brak klastra,
* dwa filary — oba `alone`, brak klastra,
* trzeci filar — powstaje klaster,
* klaster z dokładnie trzema filarami,
* usunięcie innera — klaster nadal istnieje,
* usunięcie jednego z trzech filarów — klaster znika,
* dwa pozostałe filary nadal istnieją jako `alone`,
* ponowne dodanie trzeciego filaru — klaster zostaje odbudowany,
* po rozpadzie znika stary poligon i status konfliktu jest przeliczany,
* aplikacja nie pokazuje nieistniejącego `cluster_id`,
* mapa i Territory Control pokazują ten sam stan,
* żaden przejęty filar nie ginie podczas rozpadu klastra.

Ten dopisek definiuje pełny cykl życia obszaru: **filary `alone` → minimum trzy filary → klaster → utrata filaru → rozpad klastra → pozostałe filary ponownie `alone`**.


## DoD

Backend zwraca prawdziwe klastry gracza, ich zagrożenia oraz zawartość i pozwala zarządzać zabezpieczeniami albo porzucić własny obiekt przez istniejące mechanizmy gry.

---

# Sprint 106 — Territory Control: okno i finalny interfejs

## Cel

Zbudować lekkie, czytelne okno Territory Control korzystające z mechaniki Sprintu 105.

## Ekran 1 — lista klastrów

Nagłówek:

* nazwa aplikacji,
* pozycja motocykla,
* liczba klastrów,
* liczba aktywnych konfliktów,
* odśwież.

Każdy klaster jako kompaktowa karta:

```text
KLASTER 03
12 węzłów · 5 filarów · 7 innerów
18 450 m² · 2,4 km od motocykla
```

Stan karty:

* zielona — neutralna,
* pomarańczowa — kolizja bez aktywnego ataku,
* czerwona — atakowana.

Akcje ikonowe:

* otwórz szczegóły,
* pokaż na mapie,
* teleport.

Kolor karty pochodzi wyłącznie z backendowego `threat_state`.


### GUI

Pod listą zbudowanych klastrów dodać osobną sekcję:

```text
SAMOTNE FILARY
```

* Sekcja pojawia się tylko wtedy, gdy istnieje co najmniej jeden filar `alone`.
* Dwa samotne filary nie są wyświetlane jako zielony klaster.
* Przy sekcji można pokazać komunikat:

```text
2 / 3 filary — dodaj kolejny filar, aby utworzyć klaster
```

* Samotny filar może mieć akcje:

  * pokaż na mapie,
  * teleport,
  * zarządzaj zabezpieczeniami,
  * porzuć.
* Nie pokazuje parametrów obszaru, ponieważ nie należy do istniejącego klastra.
* Po powstaniu trzeciego filaru sekcja odświeża się, a filary pojawiają się w nowo utworzonym klastrze.
* Po rozpadzie klastra widok automatycznie wraca do listy, a pozostałe filary pojawiają się w sekcji `SAMOTNE FILARY`.



## Ekran 2 — zawartość klastra

Nagłówek:

* wróć,
* nazwa klastra,
* stan zagrożenia,
* parametry,
* pokaż cały klaster na mapie,
* teleport do klastra.

Lista jest podzielona na:

```text
FILARY
INNER NODES
```

Filary:

* renderowane jako pierwsze,
* mają mocniejszą ramkę,
* używają ikony `pillar`,
* pokazują badge `FILAR`.

Inner:

* używają ikony obiektu świata,
* mają badge `INNER`.

## Belka pozycji

Każdy obiekt ma:

* ikonę,
* nazwę,
* rolę,
* odległość,
* procent zabezpieczeń,
* pasek zabezpieczeń.

Niżej dokładnie osiem akcji:

```text
OPEN
LOW
REGULAR
SECURE
ALL
PORZUĆ
MAPA
TELEPORT
```

Pierwsze pięć to małe tekstowe presety.

Ostatnie trzy są przyciskami ikonowymi z zestawu Ghost Control Suite.

## Informacja o zmianie

Po użyciu presetu:

* pasek płynnie aktualizuje procent,
* lista zabezpieczeń nie musi być stale rozwinięta,
* kliknięcie paska może otworzyć podgląd wszystkich zabezpieczeń podobny do obecnego panelu ze screena.

Po porzuceniu:

* pokazać wynik,
* pobrać świeży klaster,
* jeśli klaster zniknął, wrócić do listy.



## Responsywność

Desktop:

* około `760–900 px`,
* lista przewijana wewnątrz,
* nagłówek pozostaje widoczny.

Mobilnie:

* akcje w dwóch rzędach,
* presety nadal mają nazwy,
* mapa i teleport pozostają ikonami,
* długie nazwy są skracane.


### Dopisek do testów Sprintu 106

* brak filarów — brak klastra,
* jeden filar — `alone`, brak klastra,
* dwa filary — oba `alone`, brak klastra,
* trzeci filar — powstaje klaster,
* klaster z dokładnie trzema filarami,
* usunięcie innera — klaster nadal istnieje,
* usunięcie jednego z trzech filarów — klaster znika,
* dwa pozostałe filary nadal istnieją jako `alone`,
* ponowne dodanie trzeciego filaru — klaster zostaje odbudowany,
* po rozpadzie znika stary poligon i status konfliktu jest przeliczany,
* aplikacja nie pokazuje nieistniejącego `cluster_id`,
* mapa i Territory Control pokazują ten sam stan,
* żaden przejęty filar nie ginie podczas rozpadu klastra.

Ten dopisek definiuje pełny cykl życia obszaru: **filary `alone` → minimum trzy filary → klaster → utrata filaru → rozpad klastra → pozostałe filary ponownie `alone`**.


## DoD

Gracz może bez mapy:

* ocenić stan wszystkich klastrów,
* szybko zobaczyć, który jest atakowany,
* wejść do klastra,
* rozpoznać filary i inner nodes,
* zarządzać ich zabezpieczeniami,
* porzucać obiekty,
* otwierać je na mapie,
* teleportować się.

# Sprint 106.1 — Territory Control Cluster List Fix

## Cel

Poprawić czytelność ekranu szczegółów klastra bez zmiany backendu i mechaniki
Territory Control.

## Zakres

* Filary i inner nodes mają tworzyć jedną wspólną przewijaną listę.
* Lista jest podzielona nagłówkami kategorii:
  * `FILARY`,
  * `INNER NODES`.
* Kategorie nie mogą tworzyć dwóch osobnych paneli przewijania.
* Nagłówki kategorii są separatorami w tej samej liście.
* Presety, zabezpieczenia, mapa, teleport i porzucenie pozostają bez zmian.
* Nie zmieniać endpointów Sprintu 105.
* Nie zmieniać modelu klastra, filarów ani inner nodes.

## Kryteria akceptacji

* Ekran szczegółów klastra ma jedną listę obiektów.
* Filary są widoczne jako pierwsza kategoria.
* Inner nodes są widoczne jako druga kategoria.
* Przy dużej liczbie filarów lista przewija się cała, bez ucinania pierwszej
  sekcji.
* Mobile/narrow nadal pokazuje akcje w czytelnym układzie.
* Backend pozostaje bez zmian.

# Sprint 106.2 — Territory Control Preset Mini Palette

## Cel

Zmniejszyć przyciski presetów zabezpieczeń w wierszu obiektu, żeby działały jak
mini-paleta obok podglądu flag, a nie jak szeroki blok tekstowych akcji.

## Zakres

* Presety `OPEN`, `LOW`, `REGULAR`, `SECURE`, `ALL` pozostają tymi samymi
  akcjami backendowymi.
* W UI presety mają być małe, zwarte i ułożone w dwóch liniach.
* Pełne nazwy presetów pozostają dostępne w tooltipach.
* Mini-paleta nie może rozpychać wiersza obiektu.
* Podgląd flag zabezpieczeń zostaje obok presetów.
* Backend pozostaje bez zmian.

## Kryteria akceptacji

* Presety są wizualnie mniejsze od głównych akcji `MAPA`, `TELEPORT`,
  `PORZUĆ`.
* Presety układają się w dwóch liniach.
* Wiersz obiektu mieści nazwę, pasek zabezpieczeń, presety, flagi i akcje bez
  poziomego rozjeżdżania.
* Mobile/narrow nadal zachowuje czytelny układ.

# Sprint 106.3 — Territory Control Threat Labels Fix

## Cel

Poprawić etykiety `ALARM` i `KOLIZJA` na liście klastrów Territory Control, żeby
pokazywały wyłącznie faktyczny stan danego klastra.

## Zakres

* `KOLIZJA` może pojawić się tylko wtedy, gdy aktywny konflikt jest przypisany
  do `area_id` tego klastra.
* Jeśli `area_id` klastra zmienił się po przebudowie terytorium, konflikt może
  zostać dopasowany po targetach leżących wewnątrz aktualnego polygonu klastra.
* `ALARM` może pojawić się wtedy, gdy atakowany jest filar danego klastra.
* Jeden klaster może pokazać obie etykiety obok siebie.
* Udział gracza w konflikcie nie może sam z siebie oznaczać wszystkich jego
  klastrów jako `KOLIZJA`.
* Po zmianie presetu zabezpieczeń aktualny ekran ma się odświeżyć na miejscu.
* Nie zmieniać geometrii terytoriów ani mechaniki konfliktów.

## Kryteria akceptacji

* Klaster bez konfliktu nie pokazuje `KOLIZJA`.
* Klaster z konfliktem pokazuje `KOLIZJA`.
* Klaster po przebudowie polygonu nadal widzi swój konflikt, jeżeli target
  konfliktu leży w jego aktualnym obszarze.
* Klaster z atakowanym filarem pokazuje `ALARM`.
* `ALARM` i `KOLIZJA` mogą występować razem.
* Kliknięcie presetu `OPEN/LOW/REGULAR/SECURE/ALL` nie cofa z widoku klastra do
  poprzedniego ekranu, tylko odświeża aktualny widok.

---

# Sprint 107 — Operation Control: backend, pliki i incydenty

## Cel

Dodać produkt za `20 000 HC` oraz lekką warstwę kontroli aktywnych operacji, ich wyników i powiązanych incydentów.

## 1. Produkt Googleplex

```text
id: operationControl
name: Operation Control
price: 20000
family_id: ghost_control_suite
icon_pack: ghost_control
system_launcher: operation_control
```

Opis:

> Konsola aktywnych operacji, generowanych plików i incydentów Response Network z kontrolą pojedynczego oraz grupowego anulowania.

## 2. Rozszerzony snapshot operacji

Oprzeć aplikację na istniejącym runtime operacji i `summarize_operation_for_client`.

Nie budować drugiej tablicy aktywnych operacji.

Każda pozycja powinna zwracać:

```text
operation_id
operation_type
operation_family
target_id
target_label
position
distance_from_bike
status
started_at
expires_at
remaining_seconds
risk
incident
output
can_cancel
disabled_reason
```

Aktualne Centrum Operacji mapy pokazuje już typ, target, czas, pozostały czas, ryzyko i anulowanie, więc nowa aplikacja ma uzupełnić ten sam model o dystans, wynik plikowy i incydent. 

## 3. Pozycja i dystans

Odległość liczyć od aktualnej pozycji motocykla do aktualnej pozycji operacji.

Dla ruchomych operacji używać obecnego runtime pozycji, a nie pierwotnych współrzędnych targetu.

Dla operacji bez pozycji:

```text
distance_available: false
```

Nie pokazywać wtedy sztucznego `0 m`.

## 4. Generowany plik

Dla każdej operacji zwrócić przewidywany rezultat:

```text
file_category
resource_types
directory
preview_mode
expected_size_mb
output_status
```

Przykłady:

* GPS → logi lokalizacji,
* recon → plik systemowy lub stan rozpoznania,
* kamera → camera dump,
* ATM → ATM dump,
* audio → transcript,
* sieć → wifi/network data,
* pojazd → diagnostyka lub GPS.

Źródłem są istniejące `operation_type`, `resource_buffer`, `resource_types` i obecne mechanizmy finalizacji plików.

Nie budować opisów na sztywno wyłącznie w JavaScript.

## 5. Powiązanie z incydentem

Dla każdej operacji zwrócić:

```text
incident.active
incident.incident_id
incident.level
incident.status
incident.warning
incident.arrival_at
incident.response_units
```

Powiązanie ma pochodzić z aktualnego `operation_risk_meter.incident_id`, warning store oraz Incident Store.

System już zapisuje `incident_id` w mierniku ryzyka i na tej podstawie generuje ostrzeżenia Response Network. 

## 6. Anulowanie jednej operacji

Użyć istniejącego:

```text
cancel_profile_operation()
```

oraz obecnej logiki:

* statusu,
* plików częściowych,
* ryzyka,
* warningów,
* incydentów,
* historii.

Nie zmieniać rezultatu anulowania tylko dlatego, że akcja pochodzi z nowego okna.

## 7. Anulowanie grupowe

Dodać jedną transakcyjną operację:

```text
POST /api/pro-system/operation-control/cancel-group
```

Request:

```text
operation_family
operation_ids
```

Backend:

1. ładuje profil raz,
2. ponownie odświeża operacje,
3. sprawdza przynależność każdej pozycji do grupy,
4. anuluje aktywne pozycje tym samym helperem,
5. zapisuje profil raz,
6. zwraca wynik każdej operacji.

Response:

```text
cancelled
already_terminal
not_found
failed
remaining_active
```

Nie wysyłać dziesięciu osobnych requestów `/api/operations/cancel`.

## 8. Bezpieczeństwo anulowania grupowego

Wymagane potwierdzenie zawierające:

* nazwę grupy,
* liczbę operacji,
* przewidywane typy plików,
* informację o aktywnych incydentach,
* ostrzeżenie o możliwej utracie wyniku.

## Testy Sprintu 107

* operacja bez incydentu,
* operacja z warningiem,
* operacja z aktywnym incydentem,
* ruchoma operacja GPS,
* statyczna operacja ATM,
* poprawny dystans,
* poprawny rodzaj pliku,
* pojedyncze anulowanie,
* anulowanie całej grupy,
* grupa zawierająca zakończoną operację,
* operacja kończąca się podczas potwierdzenia,
* częściowy wynik grupy,
* wygaszenie warningu po anulowaniu,
* poprawna historia,
* brak podwójnego wygenerowania pliku.

## DoD

Backend dostarcza pełny, lekki snapshot operacji wraz z dystansem, plikiem wynikowym i incydentem oraz bezpiecznie anuluje pojedyncze operacje i całe grupy.

## Wynik Sprintu 107

Wdrożono backendowy fundament Operation Control:

* produkt Googleplex `operationControl`;
* `GET /api/ghost-control/operations`;
* `POST /api/ghost-control/operations/cancel`;
* `POST /api/ghost-control/operations/cancel-group`;
* aliasy `/api/pro-system/operation-control*`;
* centralny mapping rodzin operacji;
* summary outputu plików i publicznego incident linku;
* testy kontraktu backendowego.

GUI pozostaje zakresem Sprintu 108.

---

# Sprint 108 — Operation Control: GUI i zamknięcie Ghost Control Suite

## Cel

Zbudować finalne okno Operation Control i ujednolicić wszystkie trzy aplikacje rodziny.

## Główny ekran

Nagłówek pokazuje:

* aktywne operacje,
* liczbę operacji z incydentem,
* liczbę grup,
* pozycję motocykla,
* odśwież.

Pod nagłówkiem grupy:

```text
RECON
GPS
CAMERA
NETWORK
ATM
AUDIO
VEHICLE
```

Widoczne są wyłącznie grupy mające aktywne operacje.

## Nagłówek grupy

Pokazuje:

* ikonę grupy,
* nazwę,
* liczbę operacji,
* liczbę aktywnych incydentów,
* łączny przewidywany output,
* przycisk anulowania całej grupy.

Przycisk grupowy używa ikony `cancelGroup` i zawsze wymaga potwierdzenia.

## Wiersz operacji

Każda operacja pokazuje:

* ikonę rodzaju,
* nazwę,
* target,
* odległość od motocykla,
* pozostały czas,
* rodzaj tworzonego pliku,
* przewidywany rozmiar,
* poziom ryzyka,
* stan incydentu,
* przycisk anulowania.

Stan wizualny:

* zielony — brak warningu i incydentu,
* pomarańczowy — próg ostrzeżenia lub służby w drodze,
* czerwony — aktywny incydent przypisany do operacji.

## Incydent

Operacja z incydentem ma wyraźny badge:

```text
INCYDENT L2
```

Po rozwinięciu:

* status,
* ETA,
* promień reakcji,
* powiązany warning,
* jednostki Response Network, jeśli są publicznie dostępne.

Gracz powinien od razu widzieć, którą operację warto anulować, aby ograniczyć dalsze ryzyko.

## Plik wynikowy

Wiersz pokazuje prosty komunikat:

```text
Tworzy: GPS logs
/data/gps
~24 MB
```

Nie pokazywać surowego JSON-a `resource_buffer`.

## Odświeżanie

Operation Control nie może uruchamiać własnego ciężkiego pollera.

Preferowane:

* istniejący delta bus,
* odświeżenie po zmianie operacji,
* lekki okresowy refresh tylko jako zabezpieczenie.

Mapa już odświeża Centrum Operacji przez `/api/operations?summary=1`; aplikacja powinna korzystać z tego samego źródła lub wspólnego rozszerzonego summary. 

## Wspólne elementy trzech aplikacji

Ujednolicić:

* przyciski ikonowe,
* tooltipy,
* focus klawiatury,
* potwierdzenia,
* loadery,
* błędy,
* puste stany,
* wymiary ikon,
* statusy kolorystyczne,
* mobile safe mode.

Każda akcja ikonowa ma:

* `title`,
* `aria-label`,
* tooltip,
* stan hover,
* stan active,
* stan disabled.

## Końcowa regresja rodziny

Sprawdzić:

### Victim Picker

* skan,
* lista VICTIMS,
* ustawianie `aimed_target`,
* fokus mapy,
* teleport.

### Territory Control

* lista klastrów,
* zagrożenia,
* filary i inner nodes,
* presety,
* porzucenie,
* przebudowa terytorium.

### Operation Control

* aktywne operacje,
* dystans,
* output,
* incydenty,
* anulowanie pojedyncze,
* anulowanie grupowe.

### Wspólne

* zakup każdej aplikacji,
* instalacja,
* uruchamianie z pulpitu,
* jedna instancja okna,
* taskbar,
* brak ładowania mapy bez żądania,
* wspólny zestaw ikon,
* brak nowych alternatywnych magazynów danych.

## DoD

Ghost Control Suite działa jako spójna rodzina trzech lekkich aplikacji:

```text
Victim Picker     → kogo namierzyć
Territory Control → czego bronisz
Operation Control → co aktualnie pracuje i co generuje ryzyko
```

Całość daje graczowi prawdziwe centrum dowodzenia bez odbierania znaczenia mapie — mapa pozostaje wizualnym światem gry, a płatne pro-toolsy zapewniają szybszą, lżejszą i bardziej uporządkowaną kontrolę.

## Wynik Sprintu 108

Operation Control zostal domkniety jako trzecia aplikacja Ghost Control Suite.
Frontend korzysta z endpointow przygotowanych w Sprintach 107-107.1 i nie tworzy
osobnego magazynu operacji ani nowego pollera.

Wdrozone:

* uruchamianie aplikacji `operation_control` z pulpitu i launchera systemowego;
* jedno standardowe okno CHAOS z pojedyncza instancja i wpisem taskbara;
* naglowek z liczba aktywnych operacji, incydentow, grup i pozycja motocykla;
* grupy operacji po rodzinach: GPS, RECON, CAMERA, NETWORK, ATM, AUDIO,
  VEHICLE i pozostałe;
* wiersze operacji z targetem, dystansem, czasem, outputem, ryzykiem,
  incydentem i anulowaniem;
* anulowanie pojedynczej operacji oraz calej grupy przez istniejace endpointy;
* stany empty/loading/error/busy oraz mobile safe mode;
* wspolny styl z Victim Picker i Territory Control.

Poza zakresem pozostaje automatyczny poller Operation Control. Aplikacja odswieza
sie przy otwarciu, recznym odswiezeniu i po akcjach anulowania.

---

# Sprint 109 - Ghost Control Suite Polish

## Cel gameplayowy

Dopolerowac wspolne UI aplikacji Ghost Control Suite bez zmiany ich mechaniki.

Zakres dotyczy tylko warstwy prezentacji Victim Picker, Territory Control i
Operation Control.

## Zakres

1. Victim Picker ma dostac unikalna ikone rodziny Ghost Control Suite.
2. Stara ikona Victim Pickera nie moze kolidowac ze standardowymi aplikacjami.
3. Okna Victim Picker, Territory Control i Operation Control maja miec widoczny
   resize corner na desktopie.
4. Mobile safe mode nie korzysta z natywnego resize okien.
5. Ikony akcji zatrzymujacych, anulujacych albo kasujacych maja byc
   pomaranczowe albo czerwone.
6. Nie zmieniac endpointow, danych ani gameplayu aplikacji.

## Kryteria akceptacji

* Victim Picker ma odrebna ikone od standardowych narzedzi.
* Trzy okna Ghost Control Suite mozna rozciagac na desktopie.
* Destrukcyjne akcje sa wizualnie alarmowe.
* Mobile nie dostaje regresji resize.
* Dokumentacja i dziennik sa zaktualizowane.




> Brakująca reguła domykająca konflikty: **pełne otoczenie nie może pozostawiać starego właściciela wewnątrz cudzego pola**, tylko musi być traktowane jak ostateczne zwycięstwo terytorialne.

# Sprint 109.5 — Territory Control: pełne otoczenie i natychmiastowe przejęcie klastra

## Cel sprintu

Dodać jednoznaczną regułę rozstrzygania konfliktu terytorialnego:

> Jeżeli stabilne pole atakującego całkowicie otoczy klaster innego gracza, cały otoczony klaster zostaje natychmiast przejęty przez atakującego.

Przejęcie obejmuje:

* wszystkie filary klastra,
* wszystkie inner nodes,
* wszystkie przejęte obiekty przypisane do klastra,
* strategiczne właściwości tych obiektów,
* komponent GhostNetwork znajdujący się wewnątrz klastra,
* historię zmiany właściciela.

Stary właściciel nie może zachować otoczonych punktów i odzyskać ich wyłącznie przez postawienie jednego filaru poza polem przeciwnika.

Może rozpocząć odbudowę poza obszarem atakującego, ale będzie to nowe terytorium, bez automatycznego połączenia z utraconym klastrem.

Ta reguła powinna powstać przed GhostNetwork, ponieważ GhostNetwork ma traktować istniejący system terytoriów jako źródło prawdy o właścicielu strategicznej lokalizacji. 

## 1. Dwie drogi przejęcia terytorium

Po sprincie istnieją dwie pełnoprawne drogi zwycięstwa.

### Przejęcie punktowe

Atakujący rozbraja i przejmuje:

* poszczególne filary,
* inner nodes,
* zabezpieczenia klastra.

Klaster może stopniowo stracić minimalną liczbę trzech filarów i ulec rozwiązaniu.

### Przejęcie przez otoczenie

Atakujący buduje stabilne terytorium całkowicie obejmujące wrogie pole.

W chwili pełnego otoczenia:

* konflikt zostaje rozstrzygnięty,
* nie trzeba hakować każdego wewnętrznego punktu oddzielnie,
* wszystkie punkty otoczonego klastra przechodzą do atakującego.

Częściowe przecięcie albo otoczenie pojedynczego filaru nie uruchamia tej reguły.

## 2. Kanoniczna definicja otoczenia

Dodać domenowy resolver:

`TerritoryEncirclementResolver`

Minimalny kontrakt:

* `detect_encircled_clusters(changed_territory_id)`
* `is_cluster_fully_encircled(attacker, defender)`
* `resolve_encirclement(attacker_id, defender_id)`
* `build_encirclement_snapshot(...)`

Pełne otoczenie zachodzi, gdy:

1. Atakujący i obrońca są różnymi właścicielami.
2. Atak jest dozwolony przez istniejące reguły relacji graczy i klanów.
3. Pole atakującego posiada ważny klaster.
4. Klaster atakującego ma minimum trzy prawidłowe filary.
5. Poligon atakującego jest poprawny geometrycznie.
6. Klaster obrońcy istnieje i posiada własny kanoniczny poligon.
7. Poligon atakującego obejmuje cały poligon obrońcy.
8. Wszystkie punkty przypisane do klastra obrońcy znajdują się wewnątrz lub na tolerowanej granicy pola atakującego.
9. Wynik opiera się na zapisanej, zatwierdzonej wersji terytoriów, a nie tymczasowej geometrii frontendu.

Nie wystarczy:

* przecięcie poligonów,
* przykrycie centroidu,
* objęcie jednego filaru,
* objęcie większości powierzchni,
* wejście ostatnim punktem do wnętrza pola obrońcy.

## 3. Tolerancja geometryczna

Do sprawdzenia użyć tego samego systemu geometrii co obecne klastry.

Pełne otoczenie powinno wykorzystywać logiczny odpowiednik:

`attacker_polygon covers defender_polygon`

z niewielką, kontrolowaną tolerancją współrzędnych.

Tolerancja ma zapobiegać sytuacji, w której pole nie zostaje uznane za otoczone przez mikroskopijną szczelinę wynikającą z błędów obliczeń.

Nie może jednak pozwalać na przejęcie przy widocznej przerwie w pierścieniu.

Wartość tolerancji trafia do konfiguracji i testów geometrii.

## 4. Moment sprawdzania

Ocena otoczenia uruchamia się po trwałym zdarzeniu:

* dodania filaru,
* przejęcia filaru,
* odbudowy klastra,
* podziału klastra,
* zmiany właściciela punktu,
* zakończenia konfliktu,
* naprawy geometrii.

Najważniejszym triggerem jest zatwierdzenie punktu, który domyka pole atakującego.

Frontend może pokazać animację, ale nie decyduje o przejęciu.

## 5. Ostatni punkt domykający

Zapisać:

* `closing_node_id`,
* `closing_player_id`,
* `attacker_cluster_id`,
* `defender_cluster_id`,
* `territory_state_version`,
* `encircled_at`.

Operator stawiający ostatni punkt jest zapisany jako gracz domykający otoczenie.

Nie oznacza to jednak, że wszystkie punkty powinny być aktualizowane przez frontendowy request ostatniego filaru. Rozstrzygnięcie wykonuje osobny serwis domenowy po zapisaniu klastra.

## 6. Snapshot przed przejęciem

Przed zmianą właściciela utworzyć niezmienny snapshot:

* poligon atakującego,
* poligon obrońcy,
* właścicieli,
* klany,
* wszystkie filary obrońcy,
* wszystkie inner nodes,
* wszystkie obiekty przypisane do klastra,
* stan zabezpieczeń,
* trwające konflikty,
* komponenty strategiczne,
* wersję terytoriów,
* punkt domykający.

Snapshot służy:

* audytowi,
* recovery,
* historii konfliktu,
* nagrodom,
* późniejszej integracji GhostNetwork.

## 7. Zakres przejmowanych punktów

Przejęciu podlegają wyłącznie obiekty, których kanoniczne członkostwo wskazuje:

`cluster_id = defender_cluster_id`

Obejmuje to:

* filary,
* inner nodes,
* obiekty przejęte i przypisane do klastra,
* kotwice strategiczne należące do struktury terytorium.

Nie przejmować automatycznie:

* neutralnych markerów leżących wewnątrz pola,
* punktów innego gracza należących do osobnego klastra,
* niezależnych samotnych filarów,
* aktywnych operacji,
* aktorów mapy,
* NPC.

Jeżeli pole atakującego otacza kilka oddzielnych wrogich klastrów, każdy klaster jest oceniany i rozstrzygany osobno.

## 8. Atomowe przejęcie

W jednej operacji domenowej:

1. Zablokować oba klastry.
2. Ponownie sprawdzić geometrię.
3. Utworzyć snapshot otoczenia.
4. Zamknąć konflikty dotyczące przejmowanego klastra.
5. Zmienić właściciela wszystkich punktów klastra.
6. Usunąć stary klaster obrońcy.
7. Przebudować terytorium atakującego.
8. Przeliczyć role przejętych punktów.
9. Zaktualizować profile i rejestry właścicieli.
10. Przeliczyć konflikty sąsiednich obszarów.
11. Opublikować zdarzenia i delty.
12. Zatwierdzić transakcję.

Nie może powstać stan pośredni, w którym:

* część punktów należy do atakującego,
* część do obrońcy,
* stary klaster nadal istnieje,
* nowy klaster nie uwzględnia przejętych obiektów.

## 9. Wspólny helper przejęcia obiektu

Nie zmieniać właściciela bezpośrednio przez przypisanie pola:

`object.owner = attacker`

Każdy punkt powinien przejść przez kanoniczny helper przejęcia, na przykład:

`capture_territory_object_by_encirclement(...)`

Helper wykorzystuje tę samą ścieżkę aktualizacji co normalne skuteczne przejęcie:

* Target Registry,
* profile właścicieli,
* `own_places`,
* `captured_targets`,
* klasyfikację pillar/inner,
* historię obiektu,
* delty mapy,
* cache terytoriów.

Źródło przejęcia:

`capture_reason = territory_encirclement`

## 10. Zabezpieczenia przejmowanych punktów

Przejęty punkt nie powinien zachowywać aktywnych prywatnych zabezpieczeń poprzedniego właściciela jako gotowej ochrony dla atakującego.

Po przejęciu użyć istniejącego kanonicznego stanu początkowego dla przejętego obiektu.

Jeżeli zwykłe przejęcie ustawia określony preset bezpieczeństwa, otoczenie korzysta z tej samej reguły.

Usunąć lub zakończyć efekty należące do obrońcy:

* prywatne warstwy zabezpieczeń,
* aktywne Bastiony,
* backdoory wymagające poprzedniego właściciela,
* tymczasowe prawa dostępu,
* defensywne cooldowny przypisane do starego klastra.

Historia ich istnienia pozostaje w audycie.

## 11. Przebudowa klastra atakującego

Po przejęciu obiekty nie muszą zachować poprzedniej roli.

Dawny filar obrońcy może stać się:

* inner node nowego dużego klastra,
* filarem granicznym atakującego,
* punktem wewnętrznym bez wpływu na poligon.

Role ustala istniejący `territory rebuild`.

Nie kopiować starego poligonu obrońcy jako osobnej wewnętrznej wyspy.

Docelowo pozostaje jeden kanoniczny układ terytoriów wynikający z aktualnych punktów atakującego.

## 12. Zachowanie punktów obrońcy poza polem

Punkty obrońcy, które nie należały do otoczonego klastra, pozostają jego własnością.

Mogą to być:

* samotne filary,
* drugi klaster w innym miejscu,
* nowy filar postawiony poza polem atakującego.

Po przejęciu obrońca może dalej budować nowe terytorium.

Nie może jednak odzyskać utraconych punktów przez samo połączenie z nowym filarem.

Aby odzyskać stary obszar, musi przeprowadzić normalny atak na aktualnego właściciela.

## 13. Brak „wyjścia z impasu” starymi punktami

Po pełnym otoczeniu:

* stary właściciel nie posiada już otoczonych filarów,
* nie może użyć ich do dalszego rysowania pola,
* nie może hakować ze środka przejętego klastra jako właściciel,
* nowy filar poza obszarem zaczyna nową, niezależną strukturę.

To usuwa sytuację, w której gracz wychodzi poza pole jednym punktem, ale wszystkie wcześniejsze otoczone punkty nadal formalnie należą do niego.

## 14. Konflikty podczas przejęcia

Pełne otoczenie jest końcowym rozstrzygnięciem konfliktu dla danego klastra.

Zamknąć:

* konflikt właścicieli klastrów,
* tymczasowe obszary sporne związane z przejmowanymi punktami,
* postęp ataku na przejęte obiekty,
* obrony przypisane do nieistniejącego klastra.

Status rozstrzygnięcia:

`resolved_by_encirclement`

Nie pozostawiać przejętych punktów w stanie `contested`.

## 15. Trzeci gracz w obszarze

Jeżeli dwa różne hostile klastry jednocześnie mogłyby zostać uznane za otaczające ten sam klaster:

* nie wybierać właściciela na podstawie kolejności iteracji bazy,
* użyć trwałej kolejności zatwierdzonych `territory_state_version`,
* pierwsze poprawnie zatwierdzone pełne otoczenie otrzymuje prawo do przejęcia.

Jeżeli w tej samej wersji stanu nie można jednoznacznie wskazać zwycięzcy:

* zachować konflikt,
* nie wykonywać automatycznego przejęcia,
* uruchomić ponowną ocenę po kolejnej stabilnej zmianie.

Nie może powstać podwójne przejęcie.

## 16. Integracja z GhostNetwork

Sprint powstaje przed implementacją GhostNetwork, ale musi przygotować trwały event:

`territory.encirclement_resolved`

Payload:

* `encirclement_id`,
* `attacker_owner_id`,
* `attacker_clan`,
* `defender_owner_id`,
* `defender_clan`,
* `attacker_cluster_id`,
* `defender_cluster_id`,
* przejęte punkty,
* strategiczne kotwice,
* wersję stanu,
* `resolved_at`.

GhostNetwork po późniejszym wdrożeniu reaguje na to zdarzenie jak na ostateczną stabilną zmianę właściciela.

Nie stosuje zamrożenia konfliktowego, ponieważ konflikt został już rozstrzygnięty.

## 17. Część GhostNetwork w otoczonym polu

Jeżeli klaster przechowuje część:

1. Część nie znika.
2. Nie zmienia kotwicy.
3. Nie wraca do puli.
4. Otrzymuje nowego właściciela terytorialnego.
5. Jej stan jest natychmiast ponownie rozstrzygany.

Możliwe wyniki:

### Atakujący należy do właściwego klanu części

`blocked albo public → active`

Część zostaje aktywowana.

### Atakujący należy do obcego klanu

`active albo public → blocked`

Część zostaje zablokowana.

### Część była aktywna dla obrońcy

Jeżeli atakujący jest obcego klanu:

* moduł zostaje dezaktywowany,
* supermoc zostaje wyłączona,
* pełne linie zostają przerwane,
* postęp maszyny spada.

Nie może pozostać częścią aktywną dawnego właściciela po przejęciu całego klastra.

Raz wyemitowana część musi pozostać możliwa do odbicia i aktywacji przez właściwy klan. 

## 18. Inne strategiczne komponenty

Przygotować ogólny kontrakt:

`territory_payloads`

Może obejmować później:

* GhostNetwork part,
* specjalny węzeł,
* event świata,
* klanowy beacon,
* przyszły quest object.

System otoczenia nie powinien zawierać wielu bezpośrednich warunków:

`if ghost_part`

Publikuje zmianę właściciela lokalizacji, a odpowiedni moduł strategiczny reaguje swoim adapterem.

## 19. Zdarzenia domenowe

Wymagane:

* `territory.encirclement_detected`
* `territory.encirclement_locked`
* `territory.object_captured_by_encirclement`
* `territory.cluster_captured_by_encirclement`
* `territory.encirclement_resolved`
* `territory.cluster_rebuilt`
* `territory.conflict_resolved_by_encirclement`

Każde zdarzenie posiada:

* `encirclement_id`,
* właścicieli,
* klastry,
* `territory_state_version`,
* `source_node_id`,
* `dedupe_key`.

## 20. Deduplikacja

Stabilny klucz:

`encirclement:<attacker_cluster_id>:<defender_cluster_id>:<territory_state_version>`

Ponowne przetworzenie:

* zwraca poprzedni rezultat,
* nie przejmuje punktów drugi raz,
* nie przebudowuje wielokrotnie klastra,
* nie duplikuje nagród,
* nie publikuje drugiego eventu zwycięstwa.

## 21. Delty

Do klientów wysłać jedną grupę transakcyjną:

* usunięcie starego klastra,
* zmianę właścicieli punktów,
* przebudowę pola atakującego,
* zamknięcie konfliktu,
* aktualizację strategicznych badge’y,
* ewentualną zmianę części GhostNetwork.

Frontend nie powinien przez chwilę pokazywać starego klastra i przejętych punktów jednocześnie.

## 22. Informacja dla atakującego

Komunikat:

`TERYTORIUM OTOCZONE`

`KLASTER PRZEJĘTY`

`PUNKTY: [liczba]`

Jeżeli w polu znajduje się komponent strategiczny i gracz ma prawo o nim wiedzieć, może pojawić się dodatkowy status.

Nie ujawniać ukrytej części odbiorcom bez odpowiednich praw.

## 23. Informacja dla obrońcy

Komunikat:

`UTRACONO KLASTER`

`POWÓD: PEŁNE OTOCZENIE`

`PUNKTY PRZEJĘTE: [liczba]`

Dodatkowa informacja:

`PUNKTY POZA OTOCZONYM KLASTREM POZOSTAJĄ AKTYWNE`

Komunikat powinien jasno pokazywać, że nowy filar poza polem nie odzyska automatycznie starego obszaru.

## 24. Territory Control

Karta atakującego klastra może pokazać:

* przejęte punkty,
* czas otoczenia,
* poprzedniego właściciela,
* komponent strategiczny, jeśli widoczny.

Karta obrońcy znika z aktywnych klastrów.

Pozostałe jego samotne filary i inne klastry nadal pozostają na liście.

## 25. Wydajność

Po zmianie klastra sprawdzać tylko:

* nowy lub zmieniony poligon,
* klastry posiadające bounds przecinające jego bounds,
* klastry potencjalnie znajdujące się wewnątrz.

Nie porównywać każdego klastra z każdym polem świata.

Do dokładnej geometrii przechodzą wyłącznie kandydaci z filtra bounding box.

## 26. Recovery

Dodać:

`reconcile_territory_encirclements()`

Tryb dry-run wykrywa:

* klaster w całości otoczony, ale nadal należący do starego właściciela,
* częściowo przejęty klaster,
* stary cluster record bez punktów,
* punkty przejęte bez eventu,
* strategiczny komponent z błędnym właścicielem,
* konflikt, który powinien zostać zakończony przez otoczenie.

Tryb naprawczy korzysta z tego samego resolvera domenowego.

## 27. Migracja istniejącego świata

Przed wdrożeniem uruchomić raport istniejących klastrów.

Nie przejmować automatycznie historycznie otoczonych pól bez jawnej decyzji.

Możliwe tryby:

* `report_only`,
* `apply_from_deployment_time`,
* kontrolowana jednorazowa migracja.

Najbezpieczniej uruchomić regułę wyłącznie dla zmian zatwierdzonych po wdrożeniu, a istniejące anomalie przejrzeć osobno.

## Testy Sprintu 109.5

Minimum:

* częściowe przecięcie — brak przejęcia,
* objęcie jednego filaru — brak przejęcia,
* objęcie dwóch filarów — brak przejęcia,
* pełne pokrycie poligonu — przejęcie,
* wszystkie filary zmieniają właściciela,
* wszystkie inner nodes zmieniają właściciela,
* stary klaster znika,
* klaster atakującego przebudowuje się,
* role pillar/inner są przeliczane,
* punkty obrońcy poza klastrem pozostają jego własnością,
* nowy filar poza polem nie odzyskuje utraconych punktów,
* konflikt zostaje zamknięty,
* brak stanu `contested` po rozstrzygnięciu,
* dwa triggery nie duplikują przejęcia,
* dwóch potencjalnych atakujących nie przejmuje jednocześnie,
* błąd w połowie operacji wykonuje rollback,
* strategiczny komponent pozostaje w tej samej lokalizacji,
* część właściwego klanu atakującego staje się aktywna,
* obca część staje się blokowana,
* aktywna część obrońcy zostaje wyłączona po obcym przejęciu,
* delty tworzą spójny wynik,
* recovery wykrywa częściowo przejęty klaster.

## Poza sprintem

Nie implementować:

* GhostNetwork jako całości,
* nagród RSP za otoczenie,
* nowych supermocy,
* automatycznej narracji BlackNetu,
* specjalnych animacji przejęcia,
* panelu administracyjnego.

Sprint przygotowuje jedynie poprawne eventy i stan, które zostaną później wykorzystane przez GhostNetwork, nagrody i media.

## DoD

Sprint jest zakończony, gdy:

1. Pełne otoczenie klastra jest wykrywane jednoznacznie.
2. Częściowe nakładanie nie powoduje przejęcia.
3. Cały otoczony klaster przechodzi atomowo do atakującego.
4. Wszystkie filary i inner nodes zmieniają właściciela.
5. Stary klaster i jego konflikty zostają zamknięte.
6. Pole atakującego zostaje przebudowane.
7. Punkty obrońcy poza otoczonym klastrem pozostają jego własnością.
8. Postawienie filaru poza polem nie przywraca utraconego klastra.
9. Strategiczny komponent podąża za nową kontrolą terytorialną.
10. Operacja jest idempotentna, audytowalna i możliwa do odtworzenia.
11. Zwykłe przejmowanie pojedynczych punktów nadal działa.
12. Reguła jest gotowa jako stabilne źródło własności dla GhostNetwork.

Ten sprint bardzo dobrze zamyka lukę przed rozpoczęciem Sprintu 110: **otoczenie przestaje być długotrwałą blokadą bez wyjścia i staje się czytelnym, ostatecznym manewrem przejęcia całego pola**.


# Faza GhostNetwork

Po tych trzech sprintach mamy zamknięte fundamenty: wiemy, gdzie moduł dotyka istniejącej gry, mamy bezpieczny magazyn globalnego stanu i dysponujemy pełnym kanonem dwudziestu elementów, ale jeszcze żadna część nie może wypaść ani pojawić się na mapie.

GhostNetwork — audyt integracyjny i kontrakt domeny
GhostNetwork — fundament modułu i repozytorium stanu
GhostNetwork — katalog klanów, maszyn, profesji i części

Lecimy z pierwszą trójką — 110 ustali twarde granice integracji, 111 postawi bezpieczny fundament globalnego stanu, a 112 zamknie kanoniczny katalog czterech maszyn i dwudziestu części.

## Twarda zasada Sprintów 110-130

Przed rozpoczęciem każdego sprintu GhostNetwork od 110 do 130 należy przeczytać
i potwierdzić spójność z artefaktami:

* `doc/clans_machines.md`,
* `doc/ghostnetwork_architecture.md`,
* `doc/sprint_110_integration_audit.md`.

Jeżeli zakres sprintu, implementacja albo wynik audytu są sprzeczne z tymi
artefaktami, sprint zatrzymuje się na wpisie decyzyjnym i korekcie kontraktu.
Nie wolno rozwiązywać sprzeczności przez lokalny wyjątek w kodzie.

Każdy raport końcowy sprintów 110-130 musi zawierać punkt:

```text
Spójność z artefaktami GhostNetwork
```

# Sprint 110 — GhostNetwork: audyt integracyjny i kontrakt domeny

## Cel sprintu

Przeprowadzić audyt istniejącej gry i przygotować jednoznaczny kontrakt techniczny GhostNetwork przed rozpoczęciem implementacji.

Sprint ma ustalić, gdzie GhostNetwork wpina się w aktualne mechanizmy:

* oznaczania celu,
* hackowania obiektów,
* operacji,
* terytoriów i konfliktów,
* profilu gracza,
* RSP i LVL,
* mapy,
* systemu delt,
* BlackNetu,
* Cybernera,
* Radia,
* późniejszego demona Ollamy.

GhostNetwork jest globalnym modułem świata. Profil gracza przechowuje wyłącznie jego klan, profesję, osiągnięcia i trwałą historię udziału. Nie może przechowywać bieżących części, połączeń, topologii ani stanu cyklu. 

## 1. Audyt wyboru klanu i profesji

Sprawdzić aktualne źródła:

```text
profile.clan
profile.profession
```

Audyt ma odpowiedzieć:

* jakie wartości są obecnie zapisywane,
* czy używane są numery, nazwy czy kody techniczne,
* gdzie następuje wybór podczas onboardingu,
* gdzie wartości są później odczytywane,
* czy istnieją starsze profile bez profesji lub klanu,
* jak normalizowane są nazwy czterech frakcji.

Docelowe kody techniczne powinny być stabilne i niezależne od nazw wyświetlanych:

```text
virex
echo_freedom
phantom_mesh
sentinel_order
```

Nie migrować danych w tym sprincie. Przygotować jedynie mapę zgodności aktualnych wartości z przyszłym katalogiem.

## 2. Audyt oznaczania celu

Prześledzić wszystkie ścieżki ustawiające `aimed_target`:

* mapa,
* Victim Picker,
* gracze i intruzi,
* zwykłe POI,
* filary podatności,
* filary konfliktów.

Znaleźć jedno bezpieczne miejsce, w którym po poprawnym oznaczeniu celu będzie można wywołać:

```text
ghostnetwork.on_target_aimed(player, target)
```

Hook nie może:

* zmieniać `aimed_target`,
* rozpoczynać operacji,
* modyfikować zabezpieczeń,
* blokować zwykłej rozgrywki przy błędzie GhostNetwork,
* ujawniać graczowi, że część została zarezerwowana.

Ma jedynie otrzymać kanoniczną tożsamość celu i ewentualnie utworzyć niewidoczną rezerwację części.

## 3. Audyt skutecznego hackowania

Znaleźć wszystkie miejsca, w których obiekt zostaje faktycznie uznany za skutecznie schakowany.

Należy rozróżnić:

* rozpoczęcie narzędzia,
* uruchomienie operacji,
* zakończenie pojedynczego kroku,
* przejęcie obiektu,
* zapis obiektu jako przejętego,
* finalizację operacji długotrwałej.

Audyt ma wskazać jedno miejsce dla wywołania:

```text
ghostnetwork.on_target_hacked(player, target, operation)
```

Tylko potwierdzony sukces może zatwierdzić rezerwację i przypisać część do markera. Oznaczenie celu ani samo rozpoczęcie operacji nie jest emisją części. 

## 4. Audyt kwalifikacji markerów

Ustalić, które cele mogą zostać kotwicą części GhostNetwork.

Sprawdzić:

* zwykłe POI,
* bankomaty,
* kamery,
* restauracje,
* hotspoty,
* urządzenia,
* pojazdy,
* osoby,
* graczy,
* filary konfliktów,
* filary podatności,
* obiekty generowane proceduralnie.

Audyt powinien zakończyć się jawną regułą:

```text
is_ghostnetwork_eligible_target(target) -> bool
```

Wstępnie wykluczyć:

* graczy,
* tymczasowe aktory mapy,
* NPC Response Network,
* aktywne operacje,
* markery incydentów,
* elementy interfejsu,
* obiekty bez poprawnej pozycji,
* techniczne duplikaty tego samego celu.

Nie zapisywać kwalifikacji na frontendzie.

## 5. Audyt tożsamości celu

Sprawdzić istniejący sposób budowania:

```text
target_id
```

GhostNetwork musi przechowywać stabilną kotwicę niezależną od nazwy wyświetlanej.

Audyt ma ustalić:

* czy `build_operation_target_id()` jest wystarczający,
* jak zachować `osm_id`,
* jak zachować współrzędne,
* jak rozpoznać ten sam marker po zmianie nazwy,
* jak uniknąć dwóch części na jednym markerze w jednym cyklu,
* jak zachować kotwicę, jeśli źródłowy obiekt zniknie z mapy.

Raz wyemitowana część nie może zniknąć z powodu zmiany danych zewnętrznych. Musi zostać zachowana jako niezależny `GHOST ANCHOR`. 

## 6. Audyt terytoriów

Prześledzić istniejący lifecycle:

* samotne filary,
* utworzenie klastra z minimum trzech filarów,
* inner nodes,
* przebudowę klastra,
* podział klastra,
* porzucenie filaru,
* zniknięcie klastra,
* powstanie kolizji,
* konflikt aktywny,
* zmianę stabilnego właściciela.

GhostNetwork nie tworzy własnych granic i nie przelicza poligonów.

Audyt ma wskazać miejsca publikujące albo mogące publikować:

```text
territory.stabilized
territory.contested
territory.released
territory.owner_changed
```

W szczególności ustalić:

* kiedy stan obszaru jest już stabilny,
* kiedy konflikt tylko się rozpoczął,
* kiedy można bezpiecznie zmienić stan części,
* jak znaleźć części znajdujące się w dotkniętym obszarze,
* jak uniknąć przeliczania wszystkich 20 części przy każdej zmianie.

Podczas konfliktu część zachowuje stan sprzed walki. Aktywacja, dezaktywacja albo zmiana właściciela następuje dopiero po stabilizacji granic. 

## 7. Audyt klastrów z komponentami

Ustalić sposób rozszerzenia Territory Control o informację:

```text
contains_ghost_part
ghost_part_relation
ghost_part_state
```

Możliwe relacje względem właściciela klastra:

```text
own_clan_part
foreign_clan_part
```

Możliwe stany:

```text
contained
active
contested_frozen
```

Territory Control nie może otrzymywać danych niewidocznych dla aktualnego gracza. Musi korzystać z tej samej projekcji widoczności co mapa i przyszły GhostNetwork Suite.

## 8. Audyt systemu delt

Sprawdzić obecną implementację:

* `GameStateDeltaBus`,
* zakresy delt,
* wersjonowanie,
* recovery,
* deduplikację,
* odbiorców zdarzeń.

GhostNetwork otrzyma osobny scope:

```text
ghostnetwork
```

Audyt ma ustalić kontrakt zdarzeń:

```text
ghost.part_discovered
ghost.part_contained
ghost.part_revealed
ghost.part_activated
ghost.part_deactivated
ghost.connection_changed
ghost.cycle_locked
ghost.signal_sent
ghost.version_changed
ghost.restart_required
```

Każde zdarzenie musi zawierać co najmniej:

```text
event_id
cycle_id
state_version
event_type
entity_id
audience_scope
payload
created_at
```

## 9. Audyt mediów

Znaleźć istniejące punkty integracji z:

* deterministycznym BlackNetem,
* Cybernerem globalnym,
* wiadomościami klanowymi,
* Ghost Hack Radio,
* outboxem Ollamy.

GhostNetwork powinien publikować zatwierdzone fakty, nie gotowe dowolne teksty.

Audyt ma przygotować przykładowe klasy faktów:

```text
part_discovered
part_contained
part_activated
connection_completed
machine_progress_changed
cycle_completed
signal_sent
signal_outcome_resolved
```

Każdy fakt musi posiadać zakres odbiorców zgodny z widocznością części.

## 10. Audyt wydajności

Wskazać operacje, których GhostNetwork nie może wykonywać:

* pełny `sync_session_profile()` przy każdej delcie,
* odczyt wszystkich profili,
* przeliczenie wszystkich terytoriów,
* ciężki polling mapy,
* pełny snapshot świata przy pojedynczej zmianie części,
* renderowanie Folium po stronie domeny.

Przygotować budżet operacji:

* oznaczenie celu — jeden lekki odczyt cyklu i puli,
* sukces hacku — pojedyncza transakcja rezerwacji,
* zmiana terytorium — tylko części w dotkniętym obszarze,
* snapshot — tylko projekcja dla jednego odbiorcy,
* delta — jeden lub kilka zmienionych węzłów i połączeń.

## Artefakty sprintu

Powinien powstać dokument, przykładowo:

```text
doc/ghostnetwork/sprint_110_integration_audit.md
```

Dokument zawiera:

* mapę istniejących funkcji,
* wskazane hooki,
* źródła prawdy,
* diagram przepływu części,
* tabelę odpowiedzialności modułów,
* kontrakt zdarzeń,
* kontrakt widoczności,
* listę ryzyk,
* listę wymaganych migracji,
* plan testów kolejnych sprintów.

## Poza sprintem

Nie tworzyć:

* tabel GhostNetwork,
* aktywnego cyklu,
* katalogu części,
* rezerwacji,
* markerów,
* linii,
* nagród,
* supermocy,
* endpointów gameplayowych.

## DoD

Sprint jest zakończony, gdy jednoznacznie wiadomo:

1. Gdzie część może zostać zarezerwowana.
2. Gdzie może zostać wyemitowana.
3. Jak identyfikowana jest kotwica.
4. Kiedy terytorium może zmienić jej stan.
5. Jak publikowane będą delty.
6. Jak respektowana będzie widoczność.
7. Jak GhostNetwork zintegruje się z trzema desktopowymi narzędziami.
8. Które istniejące helpery zostaną ponownie użyte.
9. Których ciężkich ścieżek GhostNetwork nie może wywoływać.

Ten sprint jest blokadą przed dopisywaniem całej mechaniki bezpośrednio do `run.py` albo tworzeniem alternatywnych źródeł prawdy.

---

# Sprint 111 — GhostNetwork: fundament modułu i repozytorium stanu

## Cel sprintu

Utworzyć izolowany pakiet domenowy GhostNetwork, trwały magazyn stanu oraz podstawowe mechanizmy transakcji, wersjonowania i recovery.

Sprint nie uruchamia jeszcze gameplayu części. Buduje bezpieczny fundament, na którym kolejne sprinty stworzą cykle, dropy, terytoria, topologię i transmisję.

## 1. Pakiet domenowy

Utworzyć katalog dopasowany do struktury projektu, przykładowo:

```text
gameplay/
└── ghostnetwork/
    ├── __init__.py
    ├── models.py
    ├── enums.py
    ├── repository.py
    ├── service.py
    ├── events.py
    ├── visibility.py
    ├── errors.py
    └── contracts.py
```

Na tym etapie moduły mogą pozostać niewielkie, ale należy zachować rozdzielenie:

* modele danych,
* zapis i odczyt,
* reguły domenowe,
* projekcje,
* publikację zdarzeń.

Nie umieszczać całej implementacji w jednym `ghostnetwork.py`.

## 2. Kontrakt serwisu

Dodać centralny punkt wejścia:

```text
GhostNetworkService
```

Minimalny kontrakt:

```text
get_active_cycle()
get_state_version()
get_snapshot_for_viewer(viewer)
health_check()
```

Przyszłe metody mogą zostać zadeklarowane jako jawne placeholdery albo protokoły:

```text
on_target_aimed()
on_target_hacked()
on_territory_event()
resolve_part_state()
attempt_transmission()
```

Nie implementować ich mechaniki w tym sprincie.

## 3. Repozytorium

Dodać:

```text
GhostNetworkRepository
```

Repozytorium ma izolować warstwę domenową od konkretnego magazynu danych.

Minimalne grupy metod:

### Cykle

```text
get_active_cycle()
get_cycle(cycle_id)
create_cycle(...)
update_cycle(...)
lock_cycle(...)
list_cycles(...)
```

### Części

```text
create_parts(...)
get_part(part_id)
list_parts(cycle_id)
find_part_by_target(cycle_id, target_id)
update_part(...)
```

### Rezerwacje

```text
create_reservation(...)
get_active_reservation(...)
commit_reservation(...)
release_reservation(...)
expire_reservations(...)
```

### Zdarzenia

```text
append_event(...)
list_events(...)
```

### Wersja stanu

```text
get_state_version()
increment_state_version()
```

Metody mogą zostać przygotowane bez pełnej logiki katalogu, ale muszą być testowalne.

## 4. Model danych

Utworzyć trwałe struktury odpowiadające co najmniej:

```text
ghost_cycles
ghost_parts
ghost_part_reservations
ghost_connections
ghost_part_events
ghost_signals
ghost_contributions
ghost_reward_ledger
ghost_clan_reputation
ghost_narrative_outbox
```

Jeżeli obecny projekt korzysta z jednego magazynu SQLite lub własnych store’ów, dopasować implementację do tej konwencji zamiast wprowadzać osobny framework ORM.

Nazwy mogą zostać technicznie dostosowane, ale odpowiedzialności nie powinny się mieszać.

## 5. `ghost_cycles`

Minimalne pola:

```text
cycle_id
signal_number
ghostsystem_version
status
topology_seed
state_version
started_at
locked_at
transmitted_at
stabilization_until
closed_at
created_at
updated_at
```

Dozwolone statusy:

```text
preparing
active
transmitting
stabilizing
closed
```

Wymagane ograniczenie:

* maksymalnie jeden aktywny albo przejściowo zamykany cykl.

Za stany blokujące kolejny aktywny cykl uznać:

```text
preparing
active
transmitting
stabilizing
```

## 6. `ghost_parts`

Przygotować pola:

```text
part_id
cycle_id
part_code
clan_code
machine_code
profession_code
status
target_id
latitude
longitude
discovered_by
discovered_at
territory_id
territory_owner_id
territory_clan
activated_at
deactivated_at
created_at
updated_at
```

Minimalne statusy:

```text
pooled
reserved
public
contained
active
contested
consumed
```

Nie tworzyć jeszcze 20 rekordów. Zrobi to kolejny sprint po uruchomieniu katalogu.

Ograniczenia:

* unikalne `cycle_id + part_code`,
* jeden `target_id` może kotwiczyć maksymalnie jedną część w danym cyklu,
* część należy do dokładnie jednego cyklu.

## 7. Rezerwacje

Pola:

```text
reservation_id
cycle_id
part_id
target_id
player_id
player_clan
status
reserved_at
expires_at
committed_at
released_at
operation_id
```

Statusy:

```text
active
committed
released
expired
cancelled
```

Ograniczenia:

* jedna aktywna rezerwacja dla części,
* jedna aktywna rezerwacja dla celu w cyklu,
* zatwierdzona rezerwacja nie może zostać ponownie zatwierdzona,
* wygasła rezerwacja nie może emitować części.

## 8. Połączenia

Przygotować strukturę:

```text
connection_id
cycle_id
part_a_id
part_b_id
position_in_ring
created_at
```

Ograniczenia:

* brak połączenia części z samą sobą,
* brak duplikatu A–B i B–A,
* część może posiadać maksymalnie dwa połączenia,
* wszystkie połączenia należą do jednego cyklu.

Pełna walidacja topologii pojawi się w Sprincie 114.

## 9. Dziennik zdarzeń

`ghost_part_events` ma być append-only.

Pola:

```text
event_id
cycle_id
part_id
event_type
player_id
clan_code
territory_id
state_version
created_at
payload_json
dedupe_key
```

`dedupe_key` musi być unikalny, jeśli został podany.

Nie aktualizować istniejących zdarzeń poza ewentualnym technicznym statusem publikacji.

## 10. Transakcje

Repozytorium musi posiadać jawny mechanizm transakcji dla operacji:

* utworzenie cyklu i jego części,
* rezerwacja,
* zatwierdzenie emisji,
* zmiana stanu części,
* blokada cyklu,
* utworzenie GhostSignalu,
* nagrody.

Przykładowy kontrakt:

```text
with repository.transaction():
    ...
```

Nie wykonywać sekwencji krytycznych jako kilku niezależnych zapisów.

## 11. Wersjonowanie stanu

Każda domenowa zmiana zwiększa:

```text
state_version
```

Wersja powinna być monotoniczna w ramach aktywnego cyklu.

Snapshot zwraca:

```text
cycle_id
state_version
status
ghostsystem_version
```

Każde przyszłe zdarzenie delty będzie zawierać tę samą wersję albo wersję wynikającą z zatwierdzonej transakcji.

## 12. Snapshot techniczny

Dodać wewnętrzny snapshot recovery, bez reguł widoczności części:

```text
repository.build_internal_snapshot(cycle_id)
```

Powinien zawierać:

* cykl,
* części,
* połączenia,
* aktywne rezerwacje,
* wersję stanu.

Nie wystawiać go bezpośrednio graczom.

Publiczna projekcja pojawi się później.

## 13. Health check

Dodać lekki test integralności:

```text
GhostNetworkService.health_check()
```

Sprawdza:

* liczbę aktywnych cykli,
* części bez cyklu,
* duplikaty `part_code`,
* duplikaty `target_id`,
* aktywne rezerwacje po terminie,
* połączenia wskazujące nieistniejące części,
* niepoprawne statusy,
* niespójne wersje stanu.

Wynik:

```text
ok
warnings
errors
metrics
```

Nie naprawia automatycznie danych.

## 14. Zdarzenia domenowe

Przygotować ujednolicony model:

```text
GhostNetworkEvent
```

Pola:

```text
event_id
event_type
cycle_id
part_id
entity_id
state_version
audience_scope
audience_clan
payload
created_at
dedupe_key
```

W tym sprincie zdarzenia mogą być zapisywane do dziennika bez publikowania ich jeszcze do `GameStateDeltaBus`.

## 15. Obsługa błędów

Dodać jawne wyjątki domenowe:

```text
GhostNetworkError
CycleNotFound
CycleAlreadyActive
CycleLocked
PartNotFound
ReservationConflict
ReservationExpired
InvalidStateTransition
RepositoryIntegrityError
```

Endpointy nie powinny później interpretować dowolnych `ValueError` jako reguł GhostNetwork.

## Testy Sprintu 111

Minimum:

* utworzenie repozytorium,
* migracja pustej bazy,
* brak aktywnego cyklu,
* utworzenie jednego cyklu,
* blokada drugiego aktywnego cyklu,
* zapis części testowej,
* blokada duplikatu `part_code`,
* blokada duplikatu `target_id`,
* utworzenie rezerwacji,
* konflikt dwóch rezerwacji,
* zatwierdzenie rezerwacji,
* odrzucenie ponownego zatwierdzenia,
* wygaśnięcie rezerwacji,
* zapis zdarzenia z `dedupe_key`,
* blokada duplikatu zdarzenia,
* monotoniczna wersja stanu,
* rollback całej transakcji po błędzie,
* snapshot techniczny,
* health check poprawnego stanu,
* health check uszkodzonych danych.

## Poza sprintem

Nie implementować:

* katalogu czterech klanów,
* automatycznego tworzenia 20 części,
* losowania dropów,
* integracji z oznaczaniem celu,
* integracji z hackiem,
* terytoriów,
* topologii,
* widoczności gracza,
* endpointu mapy,
* supermocy,
* transmisji.

## DoD

Sprint jest zakończony, gdy GhostNetwork posiada:

1. Izolowany pakiet.
2. Repozytorium z transakcjami.
3. Trwały model stanu.
4. Ograniczenia unikalności.
5. Dziennik zdarzeń.
6. Wersjonowanie.
7. Snapshot recovery.
8. Health check.
9. Testy współbieżności podstawowych zapisów.
10. Brak zależności od pełnego profilu i mapy.

Ten sprint stawia sejf, ale jeszcze niczego do niego nie wkłada.

---

# Sprint 112 — GhostNetwork: katalog klanów, maszyn, profesji i części

## Cel sprintu

Zbudować wersjonowany, kanoniczny katalog definicji GhostNetwork:

* czterech klanów,
* czterech maszyn,
* dwudziestu profesji,
* dwudziestu części,
* relacji część–profesja–maszyna–klan,
* podstawowych kontraktów supermocy,
* pierwszej topologicznej kotwicy katalogu.

Katalog jest stałą definicją świata, a nie bieżącym stanem rozgrywki. 

## 1. Lokalizacja katalogu

Utworzyć wersjonowane źródło, na przykład:

```text
gameplay/ghostnetwork/catalog/
    clans.json
    machines.json
    professions.json
    parts.json
    abilities.json
    loader.py
    validator.py
```

Alternatywnie katalog może być zapisany w Pythonie, jeżeli jest to zgodne z projektem.

Wymagania:

* jeden punkt ładowania,
* jedna wersja katalogu,
* brak duplikowania nazw w `run.py`,
* brak osobnych kopii na frontendzie.

## 2. Wersja katalogu

Dodać:

```text
catalog_version: ghost-canon-1
```

Snapshot cyklu powinien później zapisywać wersję katalogu używaną podczas jego tworzenia.

Zmiana nazwy wyświetlanej nie może automatycznie zmieniać historycznych cykli.

## 3. Cztery klany

Katalog klanów:

### VIREX

```text
code: virex
name: VIREX
machine_code: virex_oracle
```

### Echo Wolności

```text
code: echo_freedom
name: Echo Wolności
machine_code: echo_libertas
```

### Siatka Widmo

```text
code: phantom_mesh
name: Siatka Widmo
machine_code: phantom_veil
```

### Strażnicy Ładu

```text
code: sentinel_order
name: Strażnicy Ładu
machine_code: sentinel_aegis
```

Każdy klan powinien posiadać:

```text
code
name
short_code
machine_code
description
motto
ui_color_token
sort_order
```

Kolor ma być tokenem stylu, nie wartością mechaniczną.

## 4. Cztery maszyny

### VIREX ORACLE

```text
code: virex_oracle
clan_code: virex
function: prediction_and_routing
```

### ECHO LIBERTAS

```text
code: echo_libertas
clan_code: echo_freedom
function: message_assembly_and_transmission
```

### PHANTOM VEIL

```text
code: phantom_veil
clan_code: phantom_mesh
function: concealment_and_route_masking
```

### SENTINEL AEGIS

```text
code: sentinel_aegis
clan_code: sentinel_order
function: integrity_and_protection
```

Każda maszyna:

```text
code
name
clan_code
purpose
risk_extreme
full_function
part_codes
sort_order
```

## 5. Profesje i części VIREX

### V1 — Ledger Nexus

```text
part_code: V1
part_name: Ledger Nexus
profession_code: broker
profession_name: Broker
ability_code: insider_feed
```

### V2 — Backdoor Forge

```text
part_code: V2
part_name: Backdoor Forge
profession_code: architect
profession_name: Architekt
ability_code: service_entrance
```

### V3 — Mimicry Engine

```text
part_code: V3
part_name: Mimicry Engine
profession_code: manipulator
profession_name: Manipulator
ability_code: false_image
```

### V4 — Acquisition Drive

```text
part_code: V4
part_name: Acquisition Drive
profession_code: profit_enforcer
profession_name: Egzekutor Zysku
ability_code: hostile_takeover
```

### V5 — Probability Core

```text
part_code: V5
part_name: Probability Core
profession_code: algorithm_curator
profession_name: Kurator Algorytmu
ability_code: operational_prediction
```

## 6. Profesje i części Echo Wolności

### E1 — Breach Voice

```text
profession_code: hacktivist
profession_name: Haktywista
ability_code: expose
```

### E2 — Influence Relay

```text
profession_code: social_engineer
profession_name: Socjotechnik
ability_code: narrative_takeover
```

### E3 — Truth Lens

```text
profession_code: revealer
profession_name: Odsłaniacz
ability_code: full_disclosure
```

### E4 — Resonance Beacon

```text
profession_code: visionary
profession_name: Wizjoner
ability_code: resistance_signal
```

### E5 — Spark Chamber

```text
profession_code: igniter
profession_name: Zapalnik
ability_code: domino_effect
```

## 7. Profesje i części Siatki Widmo

### P1 — Mirage Projector

```text
profession_code: illusionist
profession_name: Iluzjonista
ability_code: phantom_node
```

### P2 — Glitch Reactor

```text
profession_code: virologist
profession_name: Wirusolog
ability_code: glitch_injection
```

### P3 — Paranoia Loop

```text
profession_code: paranoid
profession_name: Paranoik
ability_code: false_tracking
```

### P4 — Fracture Engine

```text
profession_code: network_splitter
profession_name: Rozłamowiec
ability_code: network_fracture
```

### P5 — Mirror Kernel

```text
profession_code: mirror_judge
profession_name: Lustrzany Sędzia
ability_code: reflection
```

## 8. Profesje i części Strażników Ładu

### S1 — Deep Sensor

```text
profession_code: analyzer
profession_name: Analizator
ability_code: integrity_scan
```

### S2 — Bastion Matrix

```text
profession_code: defender
profession_name: Obrońca
ability_code: bastion
```

### S3 — Restoration Engine

```text
profession_code: reconstructor
profession_name: Rekonstruktor
ability_code: rollback
```

### S4 — Accord Relay

```text
profession_code: mediator
profession_name: Mediator
ability_code: trust_corridor
```

### S5 — Judgment Core

```text
profession_code: executor
profession_name: Egzekutor
ability_code: quarantine
```

## 9. Kontrakt profesji

Każda profesja:

```text
code
name
clan_code
machine_code
part_code
role
play_style
description
ability_code
base_capabilities
sort_order
```

Profesja jest zapisana w profilu przez `code`.

Nie zapisywać pełnej definicji profesji w każdym profilu.

## 10. Kontrakt części

Każda definicja części:

```text
part_code
name
clan_code
machine_code
profession_code
ability_code
function
description
icon_key
sort_order
```

Definicja nie zawiera:

* bieżącego statusu,
* właściciela,
* współrzędnych,
* odkrywcy,
* aktywacji,
* cyklu.

To są dane instancji `ghost_parts`, nie katalogu.

## 11. Kontrakt supermocy

Na tym etapie każda moc otrzymuje opis i techniczny typ efektu.

Przykładowe kontrakty:

```text
market_demand_preview
hack_threshold_modifier
territory_information_mask
territory_attack_window
operation_probability_zone
security_weakness_reveal
operation_alert_delay
scan_detail_modifier
clan_operation_beacon
neighbor_security_reduction
false_activity_marker
territory_stability_damage
false_tracking_traces
territory_connection_disruption
attack_reflection
territory_integrity_scan
territory_defense_layer
territory_repair
trusted_access_corridor
operation_quarantine
```

Katalog efektu:

```text
ability_code
effect_type
name
description
activation_scope
target_scope
requires_active_part
mechanics_status
```

Na tym etapie:

```text
mechanics_status: catalog_only
```

Sprint nie implementuje działania mocy.

## 12. Walidator katalogu

Dodać pełną walidację uruchamianą w testach i opcjonalnie podczas startu aplikacji.

Walidator sprawdza:

* dokładnie cztery klany,
* dokładnie cztery maszyny,
* dokładnie pięć części na maszynę,
* dokładnie dwadzieścia części,
* dokładnie dwadzieścia profesji,
* unikalne kody,
* jedna profesja na część,
* jedna część na profesję,
* zgodność klanu części z maszyną,
* zgodność profesji z klanem,
* istnienie każdej mocy,
* poprawność `sort_order`,
* brak brakujących opisów,
* brak osieroconych rekordów.

## 13. Normalizacja profili

Dodać helper:

```text
normalize_ghostnetwork_profile_identity(profile)
```

Zwraca:

```text
clan_code
profession_code
catalog_valid
validation_errors
```

Powinien obsłużyć starsze warianty nazw, na przykład:

* numery frakcji,
* wcześniejsze nazwy VIREX,
* polskie nazwy klanów,
* warianty pisowni profesji.

Nie zapisuje automatycznie profilu bez jawnej migracji.

## 14. Projekcja katalogu dla onboardingu

Dodać lekki kontrakt:

```text
get_onboarding_catalog()
```

Zwraca:

* cztery klany,
* maszynę każdego klanu,
* pięć dostępnych profesji,
* powiązany moduł,
* status modułu jako `inactive` przed uruchomieniem GhostNetwork.

Nie ujawnia:

* topologii,
* wszystkich połączeń,
* lokalizacji części,
* reguł transmisji.

Onboarding powinien przedstawiać profesję i powiązany moduł, ale nie zdradzać pełnej konstrukcji dwudziestu części. 

## 15. Projekcja administracyjna

Dodać wewnętrzny odczyt:

```text
get_catalog_diagnostics()
```

Zwraca:

```text
catalog_version
clans_count
machines_count
professions_count
parts_count
abilities_count
validation
checksum
```

`checksum` pozwoli później przypisać cykl do konkretnej wersji definicji.

## Testy Sprintu 112

Minimum:

* katalog ładuje się poprawnie,
* cztery klany,
* cztery maszyny,
* pięć części na klan,
* dwadzieścia części,
* dwadzieścia profesji,
* wszystkie kody są unikalne,
* każda profesja ma jedną część,
* każda część ma jedną profesję,
* każda część ma istniejącą moc,
* każda maszyna należy do właściwego klanu,
* `V1` wskazuje Ledger Nexus i Brokera,
* `S5` wskazuje Judgment Core i Egzekutora,
* normalizacja wszystkich aktualnych wariantów klanów,
* odrzucenie nieznanego klanu,
* odrzucenie profesji należącej do innego klanu,
* projekcja onboardingu nie ujawnia topologii,
* diagnostyka zwraca stabilny checksum,
* zmiana katalogu zmienia checksum.

## Poza sprintem

Nie implementować:

* aktywnego cyklu,
* tworzenia rekordów `ghost_parts`,
* topologii,
* dropów,
* markerów,
* aktywacji modułów,
* supermocy,
* RSP,
* reputacji,
* transmisji.

## DoD

Sprint jest zakończony, gdy:

1. Istnieje jedno kanoniczne źródło czterech klanów.
2. Istnieją cztery maszyny.
3. Istnieje dokładnie 20 profesji i 20 części.
4. Każda profesja jest jednoznacznie połączona z częścią.
5. Każda część ma stabilny kod.
6. Każda supermoc ma techniczny kontrakt.
7. Katalog jest wersjonowany i walidowany.
8. Profile można znormalizować do kodów katalogu.
9. Onboarding może pobierać dane bez duplikowania definicji.
10. Katalog nie zawiera żadnego stanu bieżącego świata.



GhostNetwork — cykle, wersje systemu i 20 części
GhostNetwork — topologia zamkniętego obwodu
GhostNetwork — rezerwacja części przy oznaczaniu celu

Po Sprintach 113–115 GhostNetwork posiada już aktywny cykl, komplet 20 części, zamrożoną topologię i pierwszą realną integrację z gameplayem — oznaczenie celu może przygotować przyszły drop, ale dopiero sukces hackowania w kolejnym sprincie zakotwiczy część w świecie.

# Sprint 113 — GhostNetwork: cykle, wersje systemu i 20 części

## Cel sprintu

Uruchomić pierwszy pełnoprawny cykl GhostNetwork oraz utworzyć dokładnie 20 instancji części na podstawie katalogu ze Sprintu 112.

Po tym sprincie backend ma posiadać aktywny cykl, wersję GhostSystemu i kompletną pulę części, ale żadna część nie ma jeszcze lokalizacji ani nie może wypaść z hackowanego obiektu.

GhostNetwork jest globalnym stanem świata. Cykl i części nie mogą być przechowywane w profilach graczy. 

## 1. Serwis cyklu

Dodać wydzielony komponent:

```text
GhostCycleService
```

Minimalny kontrakt:

```text
create_cycle()
get_active_cycle()
activate_cycle()
lock_cycle()
begin_stabilization()
close_cycle()
create_next_cycle()
```

Blok cyklu odpowiada za przejścia statusów, ale nie za dropy, terytoria ani transmisję.

Ten blok tworzy jedno miejsce zarządzające lifecycle cyklu, dzięki czemu endpointy i hooki nie będą samodzielnie zmieniały statusów w bazie.

## 2. Statusy cyklu

Dozwolone przejścia:

```text
preparing
→ active
→ transmitting
→ stabilizing
→ closed
```

Dozwolone skrócone przejście awaryjne:

```text
preparing → closed
```

wyłącznie podczas kontrolowanego anulowania niedokończonego cyklu.

Zablokować:

* `active → preparing`,
* `transmitting → active`,
* `stabilizing → transmitting`,
* ponowne otwarcie `closed`,
* ręczną zmianę statusu bez helpera domenowego.

## 3. Jeden aktywny cykl

W systemie może istnieć tylko jeden cykl w stanie:

```text
preparing
active
transmitting
stabilizing
```

Próba utworzenia kolejnego zwraca błąd domenowy:

```text
CycleAlreadyActive
```

Reguła musi być zabezpieczona ograniczeniem repozytorium lub transakcją, a nie tylko warunkiem `if` przed zapisem.

## 4. Numer GhostSignalu

Każdy cykl otrzymuje kolejny numer transmisji:

```text
signal_number
```

Format techniczny pozostaje liczbą całkowitą:

```text
1
2
3
47
```

Frontend może formatować numer jako:

```text
0001
0047
```

Nie zapisywać zer wiodących w bazie.

Pierwszy cykl środowiska produkcyjnego może rozpocząć się od numeru skonfigurowanego w migracji lub ustawieniu systemowym. Testy nie mogą zakładać konkretnego numeru startowego poza pustą bazą.

## 5. Wersja GhostSystemu

Dodać centralny model wersji:

```text
major
minor
cycle
```

Przykład:

```text
1.0.47
```

Dla zwykłego zakończenia cyklu rośnie ostatnia część:

```text
1.0.47 → 1.0.48
```

Większe zmiany fabularne będą mogły później podnieść `minor` lub `major`, ale Sprint 113 implementuje tylko bezpieczne zwiększanie numeru cyklu.

Numer sygnału i wersja systemu są osobnymi wartościami — dokumentacja przewiduje, że po transmisji GhostSystem zmienia wersję, lecz historia zachowuje oba numery niezależnie. 

## 6. Źródło aktualnej wersji

Wersja nie może być liczona wyłącznie z liczby rekordów cyklu.

Repozytorium przechowuje:

```text
ghostsystem_version
source_version
next_version
```

Nowy cykl zapisuje wersję, z którą został uruchomiony.

Po zakończeniu transmisji dalszy sprint zapisze:

```text
source_version = 1.0.47
next_version = 1.0.48
```

## 7. Utworzenie 20 części

Podczas tworzenia cyklu:

1. Załadować katalog ze Sprintu 112.
2. Zweryfikować jego checksum.
3. Utworzyć rekord cyklu `preparing`.
4. Utworzyć dokładnie 20 rekordów `ghost_parts`.
5. Wszystkim nadać status `pooled`.
6. Zapisać wersję katalogu i checksum.
7. Dopiero po pełnym sukcesie ustawić cykl jako `active`.

Jedna transakcja musi obejmować:

```text
cycle + 20 parts
```

Jeżeli utworzenie choć jednej części się nie powiedzie, nie może pozostać częściowo aktywny cykl.

## 8. Instancja części

Każda instancja dziedziczy z katalogu:

```text
part_code
clan_code
machine_code
profession_code
```

Stan początkowy:

```text
status: pooled
target_id: null
latitude: null
longitude: null
discovered_by: null
territory_id: null
territory_owner_id: null
territory_clan: null
activated_at: null
```

Nie kopiować do instancji długich opisów, nazwy mocy ani tekstów fabularnych, jeśli mogą być odczytane z wersjonowanego katalogu.

## 9. Integralność zestawu

Walidator cyklu sprawdza:

* dokładnie 20 części,
* pięć części każdego klanu,
* pięć części każdej maszyny,
* każdy `part_code` dokładnie raz,
* każda część pochodzi z zapisanej wersji katalogu,
* wszystkie części początkowo mają status `pooled`,
* żadna nie ma kotwicy,
* żadna nie posiada właściciela terytorium.

Nie naprawia automatycznie brakującej części w aktywnym cyklu.

## 10. Statystyki cyklu

Dodać lekki agregat:

```text
parts_total
parts_pooled
parts_reserved
parts_discovered
parts_public
parts_contained
parts_active
parts_consumed
```

Na tym etapie po utworzeniu:

```text
parts_total: 20
parts_pooled: 20
pozostałe: 0
```

Agregat musi być liczony z rekordów części albo aktualizowany atomowo. Nie trzymać drugiej niesynchronizowanej kopii w profilu.

## 11. Automatyczne uruchomienie pierwszego cyklu

Dodać kontrolowany initializer:

```text
ensure_active_ghostnetwork_cycle()
```

Zasady:

* nie tworzy cyklu, jeśli istnieje aktywny lub stabilizujący,
* może utworzyć pierwszy cykl przy starcie aplikacji lub jawnej komendzie administracyjnej,
* musi być idempotentny,
* równoległe wywołania nie mogą utworzyć dwóch cykli,
* błąd GhostNetwork nie może blokować całego startu CHAOS.

Preferowane jest uruchomienie jawne podczas deployu lub inicjalizacji gameplayu, a nie przy każdym żądaniu gracza.

## 12. Komenda diagnostyczna

Dodać bezpieczny odczyt deweloperski:

```text
ghostnetwork cycle status
```

lub odpowiedni testowy endpoint dostępny wyłącznie w dev/staging.

Zwraca:

```text
cycle_id
signal_number
ghostsystem_version
catalog_version
catalog_checksum
status
state_version
parts_summary
started_at
stabilization_until
```

Nie ujawnia przyszłych lokalizacji, bo części nie mają jeszcze kotwic.

## 13. Zdarzenia cyklu

Zapisywać zdarzenia:

```text
ghost.cycle_created
ghost.cycle_activated
ghost.cycle_status_changed
```

Payload zawiera:

```text
cycle_id
signal_number
ghostsystem_version
catalog_version
state_version
previous_status
status
```

W tym sprincie zapis do dziennika domenowego jest wymagany. Publikacja do klientów może pozostać wyłączona do sprintu delt.

## 14. Recovery

Po restarcie serwera:

* aktywny cykl jest odczytywany z repozytorium,
* nie są ponownie tworzone jego części,
* checksum katalogu jest porównywany z zapisanym checksum cyklu,
* różnica katalogu generuje warning,
* bieżący cykl nadal korzysta z zapisanej wersji definicji,
* nie migrować automatycznie aktywnych części na nowy katalog.

## 15. Health check cyklu

Rozszerzyć `health_check()` o:

* brak aktywnego cyklu,
* kilka aktywnych cykli,
* aktywny cykl bez 20 części,
* niepoprawny rozkład klanów,
* duplikat `part_code`,
* część z innej wersji katalogu,
* `pooled` z ustawionym `target_id`,
* niepoprawną wersję GhostSystemu,
* niezgodność `state_version`.

Brak cyklu może być warningiem w środowisku deweloperskim, ale błędem po oficjalnym włączeniu funkcji.

## Testy Sprintu 113

Minimum:

* utworzenie pierwszego cyklu,
* dokładnie 20 części,
* pięć części każdego klanu,
* wszystkie części `pooled`,
* zapis katalogu i checksum,
* aktywacja dopiero po utworzeniu całego zestawu,
* rollback po błędzie części numer 12,
* blokada drugiego aktywnego cyklu,
* idempotentny initializer,
* dwa równoległe initializery,
* odczyt cyklu po restarcie,
* poprawna wersja `1.0.N`,
* zwiększenie wersji helperem bez zamknięcia cyklu jest zablokowane,
* health check kompletnego cyklu,
* wykrycie cyklu z 19 częściami,
* wykrycie duplikatu części.

## Poza sprintem

Nie implementować:

* połączeń,
* rezerwacji,
* dropów,
* oznaczania celu,
* emisji części,
* mapy,
* terytoriów,
* aktywacji,
* transmisji,
* nowego cyklu po stabilizacji.

## DoD

Sprint jest zakończony, gdy:

1. Istnieje jeden aktywny cykl.
2. Cykl ma wersję systemu i numer sygnału.
3. Z katalogu powstaje dokładnie 20 części.
4. Wszystkie części zaczynają w centralnej puli.
5. Utworzenie jest atomowe i idempotentne.
6. Restart serwera nie duplikuje cyklu.
7. Stan można audytować i odbudować.
8. Żadna część nie posiada jeszcze lokalizacji.

Ten sprint ładuje komplet elementów do sejfu zbudowanego w Sprincie 111.

---

# Sprint 114 — GhostNetwork: topologia zamkniętego obwodu

## Cel sprintu

Wygenerować i zapisać stałą topologię jednego zamkniętego obwodu łączącego wszystkie 20 części aktywnego cyklu.

Każda część ma posiadać dokładnie dwóch sąsiadów, żadne połączenie nie może łączyć części tego samego klanu, a topologia pozostaje niezmienna przez cały cykl. 

## 1. Komponent topologii

Dodać:

```text
GhostTopologyService
```

Minimalny kontrakt:

```text
generate_topology(cycle)
validate_topology(cycle_id)
get_neighbors(part_id)
list_connections(cycle_id)
get_ring_order(cycle_id)
```

Ten blok generuje i waliduje logiczny obwód; nie rozstrzyga jeszcze, czy dana linia jest widoczna na mapie.

## 2. Model topologii

Cykl składa się z:

```text
20 części
20 połączeń
1 zamkniętego obwodu
```

Dla każdej części:

```text
degree = 2
```

Połączenie zapisuje:

```text
connection_id
cycle_id
part_a_id
part_b_id
position_in_ring
```

`position_in_ring` opisuje kolejność krawędzi, nie status wizualny.

## 3. Pierwsza topologia kanoniczna

Dla pierwszej wersji GhostSystemu użyć zatwierdzonego układu:

```text
V1 → S5 → E4 → P3 → V2
→ E1 → S4 → P5 → V3 → S2
→ E5 → P1 → V4 → E3 → S1
→ P4 → V5 → S3 → E2 → P2
→ V1
```

To dokładnie 20 węzłów i 20 połączeń. 

Nie generować losowo pierwszego cyklu, jeśli katalog lub konfiguracja wskazuje topologię kanoniczną.

## 4. Kotwica `V1 ↔ S5`

Zachować możliwość stałej kotwicy:

```text
V1 ↔ S5
```

Dla kolejnych generowanych topologii połączenie może pozostać wymagane, jeśli konfiguracja cyklu zawiera:

```text
required_anchor_edges:
  - [V1, S5]
```

Reguła ma być konfigurowalna, a nie zakodowana we wszystkich walidatorach.

## 5. Generator kolejnych topologii

Dodać deterministyczny generator oparty o:

```text
topology_seed
catalog_version
ghostsystem_version
```

Generator musi:

* użyć wszystkich 20 części,
* utworzyć jeden pierścień,
* nie zestawić obok siebie części tego samego klanu,
* zachować wymagane kotwice,
* dawać identyczny wynik dla tego samego seeda,
* dawać możliwość innego wyniku w następnym cyklu.

Nie używać zwykłego globalnego `random` bez jawnego seeda.

## 6. Algorytm budowy pierścienia

Dopuszczalny przepływ:

1. Podzielić części według klanu.
2. Wyznaczyć kolejność klanów bez identycznych sąsiadów.
3. Wstawić części każdego klanu zgodnie z deterministycznym tasowaniem.
4. Sprawdzić również ostatni–pierwszy węzeł.
5. Wymusić wymagane kotwice.
6. Utworzyć 20 krawędzi.
7. Uruchomić pełny walidator.
8. Zapisać połączenia w jednej transakcji.

Jeśli generator nie znajdzie poprawnej topologii w ustalonym limicie prób, zwraca błąd:

```text
TopologyGenerationError
```

Nie zapisuje częściowego obwodu.

## 7. Walidator topologii

Sprawdza:

* dokładnie 20 węzłów,
* dokładnie 20 połączeń,
* wszystkie części aktywnego cyklu występują,
* każda część ma stopień `2`,
* brak pętli do siebie,
* brak powtórzonej krawędzi,
* brak połączeń tego samego klanu,
* graf jest spójny,
* graf posiada dokładnie jeden cykl obejmujący wszystkie węzły,
* pierwszy i ostatni element są połączone,
* wymagane kotwice istnieją,
* wszystkie części i połączenia należą do tego samego cyklu.

Nie wystarczy sprawdzenie liczby krawędzi. Dwa osobne pierścienie po 10 części również miałyby 20 krawędzi, lecz są niedozwolone.

## 8. Niezmienność topologii

Po aktywacji cyklu topologia jest zamrożona.

Zablokować:

* dodawanie nowej krawędzi,
* usuwanie istniejącej,
* zmianę kolejności,
* ponowne generowanie,
* zmianę seeda.

Dopuszczalne wyjątki:

* kontrolowana naprawa administracyjna po wykrytym błędzie danych,
* migracja wykonana przed pierwszą emisją części,
* operacja techniczna zapisana w audycie.

Stan części nie zmienia struktury połączeń. Aktywacja wpływa później wyłącznie na stan wizualny linii.

## 9. Status logiczny połączenia

Dodać helper, ale jeszcze bez projekcji widoczności:

```text
resolve_connection_state(part_a, part_b)
```

Możliwe stany wewnętrzne:

```text
hidden
inactive
half_from_a
half_from_b
active
```

Podstawowe reguły:

* żadna część odkryta — `hidden`,
* obie odkryte, żadna aktywna — `inactive`,
* A aktywna, B odkryta i nieaktywna — `half_from_a`,
* B aktywna, A odkryta i nieaktywna — `half_from_b`,
* obie aktywne — `active`,
* aktywna część nie ujawnia sąsiada nadal znajdującego się w puli.

Pełna projekcja widoczności zostanie wdrożona później. Reguły wynikają z kanonu połączeń GhostNetwork. 

## 10. Brak przecieku części z puli

Publiczny odczyt topologii nie może ujawniać:

* kodu nieodkrytego sąsiada,
* jego przyszłej lokalizacji,
* kolejności całego pierścienia,
* nazw części wciąż znajdujących się w puli.

Na tym etapie istnieje wyłącznie wewnętrzny kontrakt administracyjny.

## 11. Snapshot wewnętrzny

Rozszerzyć wewnętrzny snapshot o:

```text
topology:
  seed
  checksum
  ring_order
  connections
  validation
```

`ring_order` jest informacją techniczną i nie trafia do zwykłego klienta.

## 12. Checksum topologii

Wyliczyć stabilny checksum z uporządkowanej listy krawędzi:

```text
topology_checksum
```

Checksum zapisuje się w cyklu lub metadanych topologii.

Przy recovery:

* odczytać połączenia,
* ponownie zweryfikować,
* porównać checksum,
* zgłosić błąd integralności przy niezgodności.

## 13. Zdarzenie utworzenia topologii

Zapisać:

```text
ghost.topology_created
```

Payload:

```text
cycle_id
topology_seed
topology_checksum
nodes_count
connections_count
catalog_version
state_version
```

Nie publikować pełnej kolejności graczom.

## 14. Integracja z tworzeniem cyklu

Po utworzeniu 20 części w Sprincie 113:

```text
create cycle
→ create 20 parts
→ generate topology
→ validate topology
→ activate cycle
```

Cykl nie może przejść do `active`, jeśli topologia jest niepoprawna.

Jeżeli Sprint 113 został już wdrożony, zmienić initializer tak, aby nowe cykle wymagały topologii przed aktywacją.

Dla istniejącego pustego cyklu deweloperskiego dopuszczalny jest jawny backfill.

## 15. Diagnostyka

Dodać wewnętrzny raport:

```text
ghostnetwork topology validate <cycle_id>
```

Zwraca:

```text
valid
nodes
connections
connected_components
degree_errors
same_clan_edges
duplicate_edges
missing_parts
anchor_errors
checksum_match
```

## Testy Sprintu 114

Minimum:

* kanoniczna topologia pierwszego cyklu,
* dokładnie 20 krawędzi,
* każdy węzeł ma dwóch sąsiadów,
* brak tego samego klanu po obu stronach,
* obwód jest spójny,
* ostatni łączy się z pierwszym,
* istnieje `V1 ↔ S5`,
* ten sam seed daje ten sam pierścień,
* inny seed może dać inny pierścień,
* wymagane kotwice nadal istnieją,
* generator nie tworzy dwóch osobnych obwodów,
* walidator wykrywa brak krawędzi,
* walidator wykrywa trzecią krawędź części,
* walidator wykrywa połączenie własnego klanu,
* walidator wykrywa zmieniony checksum,
* rollback po błędzie generowania,
* cykl bez topologii nie przechodzi do `active`.

## Poza sprintem

Nie implementować:

* rezerwacji,
* odkrycia części,
* markerów,
* publicznych linii,
* aktywacji,
* terytoriów,
* animacji,
* transmisji.

## DoD

Sprint jest zakończony, gdy:

1. Wszystkie 20 części tworzy jeden pierścień.
2. Każda część ma dwóch sąsiadów.
3. Nie istnieją połączenia wewnątrz klanu.
4. Topologia jest deterministyczna i wersjonowana.
5. Pierwsza wersja używa kanonicznego układu.
6. Cykl nie aktywuje się bez poprawnego obwodu.
7. Topologia nie zmienia się podczas cyklu.
8. Dane nieodkrytych części nie są publikowane.

Ten sprint układa przewody pomiędzy częściami, ale nadal żadnego przewodu nie pokazuje graczom.

---

# Sprint 115 — GhostNetwork: rezerwacja części przy oznaczaniu celu

## Cel sprintu

Podłączyć GhostNetwork do istniejącego mechanizmu oznaczania celu i umożliwić niewidoczną, czasową rezerwację jednej części z puli dla kwalifikującego się markera.

Rezerwacja nie jest emisją. Część nie pojawia się na mapie, gracz nie otrzymuje informacji o dropie, a nieudane lub porzucone podejście zwraca część do puli. 

## 1. Centralny hook oznaczania

Wdrożyć:

```text
GhostNetworkService.on_target_aimed(player, target, context=None)
```

Hook ma być wywoływany po poprawnym ustawieniu `aimed_target`, niezależnie od interfejsu:

* mapa,
* Victim Picker,
* przyszłe lekkie aplikacje,
* dozwolona ścieżka terminalowa.

Nie wywoływać go przed walidacją zasięgu i tożsamości celu.

## 2. Jedna wspólna ścieżka

Jeżeli mapa i Victim Picker nadal posiadają dwa osobne endpointy ustawiania celu, wydzielić wspólny helper:

```text
set_player_aimed_target(...)
```

Po poprawnym zapisie helper uruchamia:

```text
ghostnetwork.on_target_aimed(...)
```

Nie dopisywać hooka osobno do kilku fragmentów frontendu, ponieważ łatwo wtedy pominąć kolejną ścieżkę.

## 3. Awaria GhostNetwork nie blokuje celu

Oznaczenie celu jest podstawową mechaniką CHAOS.

Jeżeli hook GhostNetwork zwróci błąd techniczny:

* `aimed_target` pozostaje ustawiony,
* gracz może normalnie hackować,
* błąd jest logowany z `cycle_id`, graczem i `target_id`,
* system nie ujawnia szczegółów rezerwacji,
* frontend nie pokazuje fałszywego sukcesu ani błędu dropu.

GhostNetwork rozszerza zwykły gameplay, ale nie może go zatrzymać przez awarię modułu.

## 4. Kwalifikacja celu

Użyć helpera ustalonego w audycie:

```text
is_ghostnetwork_eligible_target(target)
```

Wymagane warunki:

* poprawny stabilny `target_id`,
* poprawne współrzędne,
* marker może zostać faktycznie schakowany,
* nie jest graczem,
* nie jest NPC,
* nie jest markerem operacji,
* nie jest incydentem,
* nie jest samym terytorium ani linią,
* nie jest częścią GhostNetwork,
* nie jest technicznym duplikatem,
* nie wyemitował już części w tym cyklu.

Dozwolone typy powinny wynikać z audytu, a nie z samej nazwy obiektu.

## 5. Aktywny cykl

Rezerwacja może powstać wyłącznie, gdy cykl ma status:

```text
active
```

Nie rezerwować w stanach:

```text
preparing
transmitting
stabilizing
closed
```

Podczas piętnastominutowej stabilizacji kolejnego cyklu zwykłe hackowanie nadal działa, ale markery nie mogą emitować nowych części. 

## 6. Tylko obca część

Gracz nigdy nie może zarezerwować części swojego klanu.

Przykład:

```text
player.clan = virex
```

Do puli kandydatów trafiają wyłącznie:

```text
echo_freedom
phantom_mesh
sentinel_order
```

Jest to twarda reguła domenowa, ponieważ każdy klan musi otrzymywać informacje o własnych częściach od innych operatorów. 

Jeżeli profil nie ma poprawnego klanu, hook nie tworzy rezerwacji.

## 7. Kandydaci z puli

Do losowania trafiają części:

```text
status = pooled
```

Wykluczyć części:

* już zarezerwowane,
* publiczne,
* contained,
* active,
* contested,
* consumed,
* posiadające kotwicę,
* należące do klanu gracza.

Repozytorium musi wykonać wybór i rezerwację atomowo.

## 8. Prawdopodobieństwo rezerwacji

Dodać konfigurowalny kontrakt:

```text
GhostDropPolicy
```

Minimalne metody:

```text
should_attempt_reservation(player, target, cycle)
choose_candidate(parts, player, target, cycle)
reservation_ttl_seconds(...)
```

Dokładna szansa dropu nie została jeszcze ustalona w kanonie, dlatego:

* nie zapisywać magicznej wartości w endpointzie,
* użyć konfiguracji,
* domyślnie wyłączyć produkcyjny drop flagą,
* w testach umożliwić deterministyczne `0%` i `100%`.

Przykładowa flaga:

```text
GHOSTNETWORK_DROPS_ENABLED
```

## 9. Deterministyczne losowanie

Dla jednej próby użyć stabilnego seeda obejmującego:

```text
cycle_id
player_id
target_id
attempt_nonce
```

Losowanie musi być audytowalne, ale nie przewidywalne z poziomu klienta.

Nie zwracać:

* seeda,
* wylosowanej części,
* wyniku losowania,
* listy dostępnych części.

## 10. Rezerwacja

Tworzony rekord:

```text
reservation_id
cycle_id
part_id
target_id
player_id
player_clan
status: active
reserved_at
expires_at
operation_id: null
```

Jednocześnie część może przejść technicznie:

```text
pooled → reserved
```

albo pozostać `pooled` z aktywną rezerwacją jako osobnym źródłem prawdy.

Wybrać jeden model i używać go konsekwentnie. Preferowane jest jawne `reserved`, ponieważ status części łatwiej audytować, ale repozytorium musi atomowo cofać go do `pooled`.

## 11. Brak wielokrotnego losowania tego samego celu

Jeżeli ten sam gracz ponownie oznaczy ten sam target podczas aktywnej rezerwacji:

* zwrócić istniejącą rezerwację wewnętrznie,
* nie wykonywać kolejnego losowania,
* nie przedłużać automatycznie TTL bez ustalonej reguły,
* nie tworzyć drugiej rezerwacji.

Jeżeli target ma aktywną rezerwację innego gracza:

* nowa rezerwacja nie powstaje,
* zwykłe oznaczenie celu nadal działa,
* drugi gracz nie otrzymuje informacji, że część jest zarezerwowana.

## 12. Jeden marker, jedna część w cyklu

Jeżeli marker wyemitował już część w aktualnym cyklu:

```text
find_part_by_target(cycle_id, target_id)
```

hook natychmiast kończy działanie.

Marker nie bierze ponownie udziału w losowaniu części aż do kolejnego cyklu.

Nie dotyczy to zwykłego lootu z operacji — tylko GhostNetwork.

## 13. Powiązanie rezerwacji z `aimed_target`

Rezerwacja jest powiązana z:

```text
target_id
player_id
```

Zmiana aktywnego celu nie musi od razu zwalniać poprzedniej rezerwacji, jeśli gracz może wrócić do hackowania przed wygaśnięciem.

Docelową zasadę ustawić jawnie:

* rezerwacja trwa przez TTL,
* może zostać przypisana do rozpoczętej operacji,
* wygaśnie, jeśli gracz nic nie zrobi,
* oznaczenie innego celu nie tworzy duplikatu tej samej części.

Nie trzymać `reservation_id` w publicznym `aimed_target`.

## 14. Powiązanie z rozpoczęciem operacji

Przy rozpoczęciu kwalifikującej się operacji na tym samym celu przyszły hook może przypisać:

```text
operation_id
```

do istniejącej rezerwacji.

W tym sprincie przygotować metodę:

```text
attach_reservation_to_operation(
    player_id,
    target_id,
    operation_id
)
```

Nie zatwierdzać jeszcze emisji. Zrobi to Sprint 116 po sukcesie hacku.

## 15. Wygaśnięcie rezerwacji

Dodać:

```text
expire_due_reservations(now)
```

Po wygaśnięciu:

* status rezerwacji → `expired`,
* część → `pooled`,
* zapis zdarzenia,
* brak komunikatu dla gracza,
* część może zostać zarezerwowana przez inny marker.

Mechanizm może być wywoływany:

* przed próbą nowej rezerwacji,
* przez lekki cykliczny cleanup,
* podczas health checku lub recovery.

Nie wymaga częstego pollera.

## 16. Zwolnienie rezerwacji

Przygotować jawne powody:

```text
target_abandoned
operation_cancelled
operation_failed
reservation_expired
cycle_locked
technical_recovery
```

Metoda:

```text
release_reservation(reservation_id, reason)
```

musi być idempotentna.

Ponowne zwolnienie nie może zmienić części już zatwierdzonej.

## 17. Zdarzenia rezerwacji

Zapisywać wewnętrznie:

```text
ghost.part_reserved
ghost.part_reservation_attached
ghost.part_reservation_released
ghost.part_reservation_expired
```

Te zdarzenia:

* nie są publiczne,
* nie trafiają do BlackNetu,
* nie trafiają do Cybernera,
* nie są wysyłane zwykłym graczom,
* służą audytowi, recovery i diagnostyce.

## 18. Brak zmian wizualnych

Po utworzeniu rezerwacji:

* brak markera GhostNetwork,
* brak linii,
* brak badge w Victim Pickerze,
* brak informacji w Territory Control,
* brak zmiany zwykłego markera,
* brak system message,
* brak wpisu BlackNet.

Dopiero potwierdzony hack ujawni część.

## 19. Diagnostyka deweloperska

Dodać ograniczony raport:

```text
ghostnetwork reservations status
```

Zwraca:

```text
active
expired
committed
released
oldest_active_age
parts_reserved
targets_reserved
integrity_errors
```

Pełne dane części dostępne wyłącznie w dev/admin.

## 20. Recovery

Po restarcie serwera:

* aktywne, niewygasłe rezerwacje pozostają aktywne,
* wygasłe są zwalniane przy pierwszym cleanupie,
* `reserved` bez aktywnej rezerwacji jest błędem integralności,
* aktywna rezerwacja części niebędącej `reserved` jest błędem,
* rezerwacje z zamkniętego cyklu są zwalniane,
* `committed` nie wraca do puli.

## Testy Sprintu 115

Minimum:

* oznaczenie kwalifikującego celu przy `100%`,
* brak rezerwacji przy `0%`,
* brak rezerwacji bez aktywnego cyklu,
* brak podczas stabilizacji,
* gracz VIREX nie otrzymuje części VIREX,
* wybór jednej z 15 obcych części,
* brak rezerwacji dla gracza,
* brak rezerwacji dla NPC,
* brak dla celu bez współrzędnych,
* jeden target ma jedną aktywną rezerwację,
* ponowne oznaczenie zwraca istniejący stan,
* drugi gracz nie przejmuje tej samej rezerwacji,
* jedna część nie może być zarezerwowana dwa razy,
* marker, który już wyemitował część, nie losuje ponownie,
* wygaśnięcie zwraca część do `pooled`,
* anulowanie zwalnia część,
* podpięcie `operation_id`,
* błąd hooka nie cofa `aimed_target`,
* frontend nie otrzymuje informacji o rezerwacji,
* równoczesne oznaczenie dwóch celów nie tworzy duplikatu części,
* recovery po restarcie,
* idempotentne zwolnienie.

## Poza sprintem

Nie implementować:

* zatwierdzenia emisji,
* publicznego markera części,
* RSP za odkrycie,
* terytoriów,
* widoczności,
* linii,
* BlackNetu,
* supermocy.

## DoD

Sprint jest zakończony, gdy:

1. Każda poprawna ścieżka oznaczania celu uruchamia wspólny hook.
2. Tylko kwalifikujący marker może otrzymać rezerwację.
3. Gracz może zarezerwować wyłącznie obcą część.
4. Rezerwacja jest atomowa, czasowa i niewidoczna.
5. Jedna część i jeden marker nie mogą zostać zarezerwowane podwójnie.
6. Wygaśnięcie lub anulowanie zwraca część do puli.
7. Rezerwację można powiązać z operacją.
8. Zwykłe oznaczenie celu działa nawet przy awarii GhostNetwork.
9. Żadna część nadal nie jest publicznie widoczna.





GhostNetwork — emisja części po skutecznym hacku
GhostNetwork — lifecycle części i zdarzenia domenowe
GhostNetwork — integracja z terytoriami

Po Sprintach 116–118 części naprawdę wchodzą do świata: wypadają z poprawnie schakowanych obiektów, posiadają pełny audytowalny lifecycle i reagują na tę samą geometrię terytoriów, o którą gracze już walczą.



# Sprint 116 — GhostNetwork: emisja części po skutecznym hacku

## Cel sprintu

Zatwierdzić aktywną rezerwację części dopiero po kanonicznie potwierdzonym przejęciu celu i trwale przypisać część do schakowanego obiektu.

Po emisji część:

* opuszcza centralną pulę,
* otrzymuje stałą kotwicę,
* staje się publiczna,
* zapisuje odkrywcę,
* nie może pojawić się ponownie w innym miejscu,
* pozostaje w świecie do zakończenia cyklu.

Samo oznaczenie celu, rozpoczęcie narzędzia lub częściowe rozbrojenie zabezpieczeń nie może emitować komponentu. Emisja następuje wyłącznie po potwierdzonym sukcesie hackowania. 

## 1. Kanoniczny hook sukcesu

Wdrożyć:

```text
GhostNetworkService.on_target_hacked(
    player,
    target,
    operation=None,
    result=None,
    context=None
)
```

Hook powinien zostać wywołany w jednym wspólnym miejscu, w którym zwykły gameplay uznaje cel za przejęty.

Nie podpinać go bezpośrednio do:

* kliknięcia przycisku aplikacji,
* końca animacji progressbara,
* odpowiedzi frontendu,
* samego `/hack-action`,
* utworzenia operacji,
* ustawienia `aimed_target`.

Źródłem prawdy jest backendowy zapis skutecznego przejęcia obiektu.

## 2. Audytowany punkt sukcesu

Przed implementacją wskazać dokładny istniejący helper lub fragment procesu, który:

1. potwierdza sukces narzędzia,
2. zapisuje cel w przejętych obiektach,
3. aktualizuje profil,
4. emituje odpowiednie delty mapy,
5. przyznaje normalny loot lub RSP.

Hook GhostNetwork uruchamia się dopiero po potwierdzeniu, że ten zapis może zostać zatwierdzony.

Jeżeli istnieje kilka ścieżek sukcesu, wydzielić jeden helper, na przykład:

```text
finalize_successful_target_hack(...)
```

i podpiąć GhostNetwork do niego.

## 3. Rodzaje sukcesu

Rozróżnić:

### Sukces kończący przejęcie celu

Może zatwierdzić część:

```text
target_captured = true
```

### Sukces pojedynczego kroku

Nie emituje części:

```text
scan_ports
sniff
trace
częściowe rozbrojenie
uruchomienie operacji
```

### Operacja długotrwała

Część jest zatwierdzana dopiero wtedy, gdy mechanika danej operacji rzeczywiście kończy przejęcie obiektu.

Nie każda operacja generująca plik jest hackiem przejmującym marker.

## 4. Odszukanie rezerwacji

Po sukcesie hook wyszukuje aktywną rezerwację zgodną z:

```text
cycle_id
player_id
target_id
operation_id, jeśli został przypisany
status = active
```

Preferowana kolejność:

1. dokładne `operation_id`,
2. `player_id + target_id`,
3. brak dopasowania — brak emisji.

Nie wyszukiwać „dowolnej aktywnej rezerwacji gracza”.

## 5. Ponowna walidacja

Przed zatwierdzeniem backend ponownie sprawdza:

* cykl nadal jest `active`,
* rezerwacja nie wygasła,
* część nadal ma status `reserved`,
* część należy do aktywnego cyklu,
* część nie należy do klanu odkrywcy,
* target nadal jest kwalifikującą się kotwicą,
* `target_id` odpowiada rezerwacji,
* współrzędne są poprawne,
* marker nie wyemitował już innej części w tym cyklu,
* część nie została przypisana do innego celu,
* wynik hacku jest faktycznym sukcesem końcowym.

Nie ufać danym zapisanym wyłącznie w request payloadzie frontendu.

## 6. Atomowa emisja

W jednej transakcji:

```text
rezerwacja active → committed
część reserved → public
przypisanie target_id
zapis współrzędnych
zapis odkrywcy
zapis discovered_at
zapis snapshotu kotwicy
zwiększenie state_version
zapis ghost.part_discovered
```

Jeżeli dowolny krok się nie powiedzie, cała transakcja zostaje cofnięta.

Nie może powstać stan:

* committed reservation bez części,
* publiczna część bez kotwicy,
* część z targetem bez zdarzenia odkrycia,
* dwa komponenty na jednym markerze.

## 7. Snapshot kotwicy

Część zapisuje trwałą kopię minimalnych danych celu:

```text
target_id
target_type
source_type
label_at_discovery
icon_key
latitude
longitude
osm_id
node_id
procedural_seed
original_source
```

Dodać pole albo strukturę:

```text
anchor_snapshot_json
```

Snapshot nie zastępuje `target_id`, lecz pozwala zachować część, jeśli zewnętrzne dane mapy zmienią nazwę albo usuną obiekt.

## 8. Ghost Anchor

Raz wyemitowana część nie może zniknąć z powodu braku oryginalnego POI.

Jeżeli źródłowy obiekt przestaje istnieć:

* część zachowuje `target_id`,
* zachowuje współrzędne,
* używa zapisanej nazwy,
* otrzymuje techniczny stan źródła `source_lost`,
* później może być renderowana jako `GHOST ANCHOR`.

Komponent nie wraca do puli i nie jest losowany ponownie. 

## 9. Stan po odkryciu

Bezpośrednio po emisji:

```text
status: public
territory_id: null
territory_owner_id: null
territory_clan: null
activated_at: null
```

Nie zakładać automatycznie, że schakowany obiekt znajduje się poza terytorium.

Po emisji można uruchomić punktową ocenę istniejącej stabilnej kontroli, ale właściwe reguły `public / contained / active` wprowadzi Sprint 118.

Do tego czasu część jest zapisana jako publiczna.

## 10. Odkrywca

Zapisać:

```text
discovered_by
discovered_clan
discovered_at
discovery_operation_id
```

Odkrywca jest stały przez cały cykl.

Nie zmienia się po:

* otoczeniu części,
* przejęciu terytorium,
* odbiciu części,
* aktywacji,
* ponownym ujawnieniu.

## 11. Brak RSP w tym sprincie

Zapis odkrywcy i zdarzenia jest wymagany, ale właściwe naliczanie strategicznego RSP zostaje w Sprincie 125.

Można zapisać przyszły wkład:

```text
contribution_type: part_discovered
status: pending_reward
```

albo polegać na dzienniku zdarzeń.

Nie przyznawać tymczasowej przypadkowej wartości RSP, którą później trzeba będzie migrować.

## 12. Idempotencja

Hook może zostać wywołany ponownie przez:

* retry requestu,
* recovery operacji,
* powtórne przetworzenie delty,
* restart między zapisem profilu a odpowiedzią.

Dodać stabilny klucz:

```text
discover:<cycle_id>:<part_id>:<operation_id>
```

albo:

```text
discover:<cycle_id>:<target_id>
```

Drugie wywołanie zwraca istniejący rezultat i nie:

* tworzy nowego zdarzenia,
* zmienia odkrywcy,
* zwiększa wersji,
* emituje kolejnej części.

## 13. Współbieżność

Obsłużyć sytuacje:

### Dwie operacje kończą ten sam target

Tylko jedna może zatwierdzić rezerwację.

### Dwa targety posiadają błędnie tę samą część

Blokada części pozwala zatwierdzić tylko jedną transakcję.

### Cykl zostaje zablokowany podczas kończenia hacku

Jeśli blokada transmisji nastąpiła wcześniej, emisja jest odrzucona.

Jeśli emisja została zatwierdzona wcześniej, transmisja widzi już nową część.

Kolejność wynika z transakcyjnej blokady cyklu i części.

## 14. Rezerwacja wygasła przed sukcesem

Jeżeli operacja kończy się po `expires_at`:

* rezerwacja zostaje oznaczona `expired`,
* część wraca do `pooled`,
* skuteczny hack nadal zachowuje zwykłe nagrody i loot,
* GhostNetwork nie emituje części,
* gracz nie otrzymuje komunikatu, że „prawie znalazł” komponent.

Nie reaktywować wygasłej rezerwacji po fakcie.

## 15. Brak rezerwacji

Skuteczny hack bez aktywnej rezerwacji:

* działa normalnie,
* nie losuje części po sukcesie,
* nie wykonuje drugiej próby dropu,
* nie tworzy komunikatu błędu.

Szansa na część była rozstrzygana podczas oznaczania celu.

## 16. Zdarzenie odkrycia

Zapisać domenowe:

```text
ghost.part_discovered
```

Minimalny payload wewnętrzny:

```text
cycle_id
part_id
part_code
target_id
latitude
longitude
discovered_by
discovered_clan
operation_id
source_type
state_version
```

Zdarzenie publiczne będzie później przechodziło przez projekcję widoczności.

## 17. Komunikat systemowy

Na tym etapie można zwrócić kontrolowany rezultat do procesu finalizacji:

```text
ghostnetwork_result:
    discovered: true
    part_id
    event_id
```

Nie ujawniać całej topologii ani sąsiadów.

Właściwy komunikat pierwszego odkrycia, marker i prezentacja mapy zostaną podłączone później.

## 18. Cleanup rezerwacji celu

Po zatwierdzeniu części:

* zakończyć rezerwację jako `committed`,
* usunąć lub zamknąć inne nieprawidłowe aktywne rezerwacje tego celu,
* nie zwracać zatwierdzonej części do puli,
* marker uznać za wykorzystany w bieżącym cyklu.

## 19. Recovery

Health check wykrywa:

* część `public` bez `target_id`,
* część `public` bez współrzędnych,
* committed reservation z częścią `reserved`,
* część przypisaną do targetu bez committed reservation,
* dwa komponenty na tym samym targetcie,
* brak `ghost.part_discovered`,
* odkrywcę bez profilu.

Naprawy automatyczne mogą jedynie odtworzyć brakujące dane techniczne z istniejącego zdarzenia. Nie wolno losować zastępczej części.

## Testy Sprintu 116

Minimum:

* emisja po faktycznym przejęciu,
* brak emisji po `scan_ports`,
* brak emisji po rozpoczęciu operacji,
* brak emisji bez rezerwacji,
* brak emisji po wygaśnięciu,
* rezerwacja innego targetu nie zostaje użyta,
* niezgodne `operation_id`,
* atomowe `reserved → public`,
* zapis odkrywcy,
* zapis kotwicy,
* jedna część na target,
* jeden target nie emituje dwa razy,
* drugi retry jest idempotentny,
* równoległe finalizacje,
* blokada cyklu podczas finalizacji,
* normalny hack działa przy błędzie GhostNetwork,
* źródłowy marker może zniknąć po emisji,
* część pozostaje jako Ghost Anchor,
* brak strategicznego RSP przed Sprintem 125.

## Poza sprintem

Nie implementować:

* widocznego markera,
* linii,
* terytorialnej aktywacji,
* supermocy,
* nagród,
* BlackNetu,
* transmisji.

## DoD

Sprint jest zakończony, gdy potwierdzony hack może atomowo zamienić niewidoczną rezerwację w jedną trwałą, publiczną część przypisaną do konkretnego celu i odkrywcy.

Ten sprint po raz pierwszy umieszcza realny komponent GhostNetwork w świecie.

---

# Sprint 117 — GhostNetwork: lifecycle części i zdarzenia domenowe

## Cel sprintu

Zdefiniować i wdrożyć pełną maszynę stanów części od centralnej puli aż do zużycia podczas transmisji oraz spójny, niezmienny dziennik zdarzeń.

Sprint ma zablokować ręczne zmiany statusów wykonywane bez reguł domenowych.

## 1. Osobny serwis części

Dodać:

```text
GhostPartLifecycleService
```

Minimalny kontrakt:

```text
reserve_part(...)
release_reservation(...)
discover_part(...)
contain_part(...)
activate_part(...)
reveal_part(...)
freeze_for_conflict(...)
resolve_after_conflict(...)
deactivate_part(...)
consume_part(...)
```

Każda metoda:

* waliduje stan wejściowy,
* wykonuje jedną transakcję,
* zwiększa `state_version`,
* zapisuje zdarzenie,
* zwraca nowy snapshot części.

## 2. Stan bazowy i konflikt

Nie używać `contested` jako zwykłego zamiennika faktycznego statusu części.

Część podczas konfliktu zachowuje poprzedni stan. Dlatego rozdzielić:

```text
status:
    pooled
    reserved
    public
    contained
    active
    consumed
```

oraz:

```text
conflict_state:
    none
    contested
```

Dodatkowe pola:

```text
frozen_status
conflict_id
contested_at
```

Przykład:

```text
status: active
conflict_state: contested
frozen_status: active
```

Dzięki temu system wie, że część nadal działa podczas sporu, ale nie może zmienić właściciela przed stabilizacją.

Kanon jednoznacznie mówi, że konflikt zamraża stan sprzed rozpoczęcia walki. 

## 3. Dozwolone przejścia

### Pula

```text
pooled → reserved
```

### Zwolnienie

```text
reserved → pooled
```

Powody:

* wygaśnięcie,
* anulowanie,
* błąd operacji,
* recovery.

### Odkrycie

```text
reserved → public
```

Wyłącznie przez zatwierdzony hack.

### Stabilne obce terytorium

```text
public → contained
active → contained
contained → contained
```

### Stabilne właściwe terytorium

```text
public → active
contained → active
active → active
```

### Brak właściciela

```text
contained → public
active → public
public → public
```

### Konflikt

```text
public + contested overlay
contained + contested overlay
active + contested overlay
```

Status bazowy pozostaje niezmieniony.

### Transmisja

```text
public → consumed
contained → consumed
active → consumed
```

Dopiero po atomowym zapisaniu GhostSignalu.

## 4. Niedozwolone przejścia

Zablokować między innymi:

```text
pooled → active
pooled → contained
public → reserved
active → pooled
contained → reserved
consumed → public
consumed → active
```

Próba zwraca:

```text
InvalidPartStateTransition
```

Nie poprawia statusu automatycznie.

## 5. Niezmienna tożsamość części

Po utworzeniu instancji nie mogą zmienić się:

```text
part_id
cycle_id
part_code
clan_code
machine_code
profession_code
```

Po odkryciu nie mogą zmienić się:

```text
target_id
discovered_by
discovered_at
```

Dopuszczalna techniczna migracja kotwicy zachowuje oryginalny `target_id` w historii i tworzy osobne zdarzenie.

## 6. Części nie można usunąć

Nie tworzyć zwykłej metody:

```text
delete_part()
```

Dopuszczalne zakończenie lifecycle:

```text
status = consumed
```

Raz odkrytej części gracz nie może:

* sprzedać,
* przenieść,
* wyrzucić,
* porzucić,
* zniszczyć,
* schować do ekwipunku,
* zastąpić drugą kopią.

Do końca cyklu zmieniają się wyłącznie status, widoczność i kontrola terytorialna. 

## 7. Pola czasowe

Utrzymywać:

```text
reserved_at
discovered_at
contained_at
activated_at
deactivated_at
revealed_at
contested_at
conflict_resolved_at
consumed_at
updated_at
```

Nie nadpisywać pierwszego `activated_at` przy kolejnej aktywacji.

Dodać osobne:

```text
last_activated_at
last_deactivated_at
```

jeżeli potrzebne są statystyki kolejnych odbić.

Pełna historia pochodzi ze zdarzeń.

## 8. Właściciel terytorialny

Pola bieżącego stanu:

```text
territory_id
territory_owner_id
territory_clan
territory_state_version
```

Zmiana właściciela nie modyfikuje odkrywcy ani kotwicy części.

## 9. Dziennik zdarzeń

Rozszerzyć append-only `ghost_part_events`.

Wymagane eventy:

```text
ghost.part_pooled
ghost.part_reserved
ghost.part_reservation_released
ghost.part_discovered
ghost.part_contained
ghost.part_revealed
ghost.part_activated
ghost.part_deactivated
ghost.part_contested
ghost.part_conflict_resolved
ghost.part_owner_changed
ghost.part_anchor_source_lost
ghost.part_anchor_migrated
ghost.part_consumed
```

Każde zdarzenie opisuje fakt, który już został zapisany w stanie części.

## 10. Kontrakt zdarzenia

Minimalny payload:

```text
event_id
event_type
cycle_id
part_id
part_code
previous_status
status
previous_conflict_state
conflict_state
player_id
player_clan
territory_id
territory_owner_id
territory_clan
state_version
created_at
dedupe_key
payload
```

Nie każde zdarzenie wymaga wszystkich pól, ale kontrakt powinien być spójny.

## 11. Audyt przyczyn

W `payload` zapisywać:

```text
reason
source_event_id
source_system
operation_id
conflict_id
previous_owner
new_owner
```

Przykładowe źródła:

```text
target_hack
territory_stabilized
territory_released
territory_owner_changed
territory_conflict_started
territory_conflict_resolved
ghostsignal_transmission
technical_recovery
```

## 12. Idempotencja zdarzeń

Każda zmiana ma stabilny `dedupe_key`, na przykład:

```text
part:<part_id>:discover:<operation_id>
part:<part_id>:territory:<territory_event_id>
part:<part_id>:consume:<signal_id>
```

Ponowne przetworzenie tego samego eventu:

* nie zmienia stanu,
* nie zwiększa wersji,
* nie tworzy duplikatu historii,
* zwraca poprzedni rezultat.

## 13. Jedna wersja na transakcję

Jeżeli jedna domenowa operacja zmienia:

* część,
* właściciela,
* conflict overlay,
* dwa połączenia,

może otrzymać jeden wspólny `state_version`.

Szczegóły aktualizacji połączeń zostaną później opublikowane osobnymi deltami, ale muszą odnosić się do tej samej wersji stanu.

## 14. Podstawowe uprawnienia odbiorców

Zdarzenia otrzymują wstępne oznaczenie:

```text
audience_scope:
    internal
    public
    owner
    clan
```

Pełną projekcję danych wykona Sprint 120.

Na tym etapie wymagane jest, aby wewnętrzne eventy rezerwacji nie trafiły przypadkiem do publicznego streamu.

## 15. Lifecycle aktywacji

Aktywacja zapisuje:

```text
status = active
territory_id
territory_owner_id
territory_clan
activated_at, jeśli pierwsza
last_activated_at
```

Dezaktywacja zapisuje:

```text
status = public lub contained
deactivated_at
last_deactivated_at
```

Supermoc nie jest jeszcze wdrażana, ale zdarzenie aktywacji będzie jej źródłem w Sprincie 124.

## 16. Powrót do publicznego stanu

`reveal_part()`:

* usuwa właściciela terytorium,
* ustawia `status = public`,
* zachowuje kotwicę,
* zachowuje odkrywcę,
* nie tworzy nowego odkrycia,
* nie zwraca części do puli.

## 17. Migracja kotwicy

Dodać kontrolowany proces techniczny:

```text
migrate_anchor(part_id, new_target, reason)
```

Wymagania:

* tylko admin/recovery,
* zachowanie oryginalnego snapshotu,
* zapis starej i nowej pozycji,
* brak zmiany `part_id`,
* brak zmiany odkrywcy,
* event `ghost.part_anchor_migrated`,
* ponowne rozstrzygnięcie terytorium.

Nie udostępniać tego graczom.

## 18. Odbudowa stanu z eventów

Dodać narzędzie diagnostyczne:

```text
replay_part_history(part_id)
```

Powinno odtworzyć:

* status,
* konflikt,
* aktualnego właściciela,
* aktywację,
* kotwicę.

Nie musi być głównym źródłem odczytu runtime, ale pozwala sprawdzić zgodność rekordu części z historią.

## 19. Health check lifecycle

Wykrywa:

* `active` bez właściwego klanu,
* `contained` bez właściciela,
* `public` z aktywnym właścicielem,
* `consumed` przed transmisją,
* `reserved` bez rezerwacji,
* konflikt bez `frozen_status`,
* brak eventu dla ostatniej zmiany,
* `active` z niezgodnym `territory_clan`,
* część z niepoprawnym przejściem w historii.

## Testy Sprintu 117

Minimum:

* wszystkie dozwolone przejścia,
* wszystkie niedozwolone przejścia,
* `active` zachowane podczas konfliktu,
* `contained` zachowane podczas konfliktu,
* zakończenie konfliktu do `public`,
* zakończenie konfliktu do `active`,
* ponowna aktywacja,
* pierwsze i kolejne daty aktywacji,
* odkrywca pozostaje stały,
* kotwica pozostaje stała,
* brak usunięcia części,
* `consumed` jest końcowy,
* idempotentne eventy,
* replay historii,
* wykrycie niespójności health checkiem,
* eventy rezerwacji są internal,
* event aktywacji posiada zakres klanowy i publiczny do dalszej projekcji.

## Poza sprintem

Nie implementować:

* geometrii terytorium,
* wyboru właściciela,
* widoczności nazw części,
* linii frontendowych,
* supermocy,
* nagród,
* transmisji.

## DoD

Sprint jest zakończony, gdy każda część porusza się wyłącznie po zatwierdzonej maszynie stanów, konflikt nie niszczy poprzedniego stanu, a każda zmiana posiada idempotentny zapis w niezmiennej historii.

---

# Sprint 118 — GhostNetwork: integracja z terytoriami

## Cel sprintu

Podłączyć części GhostNetwork do istniejących terytoriów i automatycznie ustalać ich stan na podstawie stabilnej kontroli lokalizacji.

GhostNetwork nie tworzy własnych poligonów, filarów ani klastrów. Odczytuje wynik istniejącego systemu i reaguje wyłącznie na zmianę stabilnego stanu. 

## 1. Adapter systemu terytoriów

Dodać:

```text
GhostTerritoryAdapter
```

Minimalny kontrakt:

```text
on_territory_stabilized(event)
on_territory_contested(event)
on_territory_released(event)
on_territory_owner_changed(event)
resolve_part_territory(part)
resolve_parts_in_changed_area(event)
```

Adapter tłumaczy obecne dane Territory Store na domenowy kontrakt GhostNetwork.

Nie implementuje zasad części samodzielnie — wywołuje `GhostPartLifecycleService`.

## 2. Zdarzenia źródłowe

Po istniejących operacjach terytorium publikować:

```text
territory.stabilized
territory.contested
territory.released
territory.owner_changed
```

Każde zdarzenie powinno zawierać:

```text
territory_event_id
territory_id
owner_username
owner_clan
status
vertices lub bounds
previous_owner
previous_clan
conflict_id
territory_state_version
created_at
```

GhostNetwork nie może polegać wyłącznie na tekstowym statusie zwróconym frontendowi.

## 3. Stabilne terytorium

Za stabilne uznać wyłącznie terytorium, które:

* posiada ważny klaster,
* ma co najmniej trzy filary,
* posiada wyliczony poligon,
* nie znajduje się w nierozstrzygniętym konflikcie,
* ma jednoznacznego właściciela,
* zostało zapisane po zakończeniu rebuilda.

Jeden albo dwa samotne filary nie tworzą klastra i nie mogą zabezpieczyć części GhostNetwork.

## 4. Reguła minimum trzech filarów

GhostNetwork musi respektować lifecycle Territory Control:

```text
pillar_count < 3
→ brak klastra
→ brak stabilnego terytorium
```

Jeżeli część znajduje się pomiędzy jednym lub dwoma filarami `alone`:

* pozostaje `public`,
* nie zostaje `contained`,
* nie zostaje `active`,
* nie otrzymuje `territory_id`.

Dopiero trzeci filar i poprawny rebuild mogą objąć część stabilnym obszarem.

## 5. Rozpad klastra

Jeżeli klaster z trzema filarami straci jeden filar:

1. klaster zostaje rozwiązany,
2. stary poligon przestaje istnieć,
3. pozostałe dwa filary pozostają `alone`,
4. część nie jest usuwana,
5. GhostNetwork ponownie ustala kontrolę lokalizacji.

Jeżeli żaden inny stabilny klaster nie obejmuje części:

```text
active → public
contained → public
```

Nie traktować dwóch pozostałych filarów jako „osłabionego klastra”.

## 6. Punktowa ocena części

Po zmianie terytorium nie przeliczać wszystkich 20 części.

Adapter powinien:

1. odczytać bounds zmienionego obszaru,
2. pobrać tylko odkryte części znajdujące się w bounds,
3. wykonać dokładny `point_in_polygon`,
4. rozstrzygnąć stan wyłącznie tych części.

Dodać repozytoryjne:

```text
list_discovered_parts_in_bounds(
    cycle_id,
    min_lat,
    min_lng,
    max_lat,
    max_lng
)
```

Przy `territory.released` uwzględnić także części wcześniej przypisane do tego `territory_id`, nawet jeśli geometria już nie istnieje.

## 7. Część publiczna

Jeżeli lokalizacja nie ma stabilnego właściciela:

```text
status = public
territory_id = null
territory_owner_id = null
territory_clan = null
```

Dotyczy to:

* świeżo odkrytej części,
* rozpadu klastra,
* całkowitego rozbrojenia terytorium,
* usunięcia stabilnej kontroli,
* rozwiązania konfliktu bez nowego właściciela.

## 8. Obcy klan

Jeżeli stabilne terytorium należy do klanu innego niż klan części:

```text
status = contained
territory_id = cluster_id
territory_owner_id = owner
territory_clan = foreign_clan
```

Część:

* pozostaje nieaktywna,
* nie daje supermocy,
* pozostaje w tej samej lokalizacji,
* nie może zostać usunięta przez właściciela,
* otrzymuje zdarzenie `ghost.part_contained`.

Obcy klan może blokować część bezterminowo, ale nie może jej aktywować. 

## 9. Właściwy klan

Jeżeli stabilne terytorium należy do klanu części:

```text
status = active
territory_id = cluster_id
territory_owner_id = owner
territory_clan = part.clan_code
```

Zapisać:

```text
ghost.part_activated
```

Od tego momentu część jest aktywnym węzłem.

Supermoc, linie i nagrody zostaną podłączone w kolejnych sprintach.

## 10. Konflikt

Po `territory.contested`:

* znaleźć części leżące w obszarze konfliktu,
* ustawić `conflict_state = contested`,
* zachować bieżący status bazowy,
* zapisać `frozen_status`,
* zachować aktualnego właściciela,
* nie aktywować części dla atakującego,
* nie wyłączać części broniącego,
* nie zmieniać widoczności.

Samo rozpoczęcie ataku nie przejmuje komponentu.

## 11. Aktualizacja trwającego konfliktu

Kolejne zmiany geometrii konfliktowej:

* mogą aktualizować `conflict_id`,
* mogą aktualizować metadane,
* nie zmieniają `status`,
* nie naliczają kolejnych aktywacji,
* nie generują wielokrotnie `ghost.part_contested`.

Jedno wejście części w konflikt powinno posiadać jedno zdarzenie z idempotentnym kluczem.

## 12. Rozstrzygnięcie konfliktu

Po stabilizacji granic wykonać ponowną ocenę lokalizacji.

Możliwe wyniki:

### Poprzedni właściciel utrzymał obszar

Stan bazowy pozostaje bez zmian.

### Brak właściciela

```text
→ public
```

### Obcy klan przejął lokalizację

```text
→ contained
```

### Właściwy klan przejął lokalizację

```text
→ active
```

Następnie:

```text
conflict_state = none
frozen_status = null
```

Zapisać:

```text
ghost.part_conflict_resolved
```

oraz odpowiednie zdarzenie aktywacji, dezaktywacji, ujawnienia lub zmiany właściciela.

## 13. Nakładające się obszary

Jeśli więcej niż jedno terytorium różnych właścicieli obejmuje część:

* traktować lokalizację jako sporną,
* nie wybierać właściciela na podstawie kolejności zapytania,
* zachować poprzedni stan części,
* czekać na stabilny wynik Territory Conflict Store.

Jeżeli kilka obszarów tego samego właściciela obejmuje punkt, użyć kanonicznego klastra wskazanego przez system terytorium albo stabilnej reguły wyboru.

## 14. Podział klastra

Jeżeli jeden klaster dzieli się na kilka:

* stary `territory_id` zostaje zwolniony,
* każda część jest oceniana według swojej pozycji,
* może trafić do jednego z nowych klastrów,
* może pozostać publiczna pomiędzy nimi,
* nie może należeć jednocześnie do dwóch klastrów.

Nie kopiować części do każdego nowego obszaru.

## 15. Inner czy filar

Stan GhostNetwork zależy od pozycji części wewnątrz stabilnego poligonu, nie od roli schakowanego obiektu.

Kotwica części może być:

* filarem,
* inner node,
* innym przejętym obiektem znajdującym się w obszarze.

Minimalne trzy filary dotyczą istnienia klastra, nie rodzaju kotwicy komponentu.

## 16. Zmiana klanu właściciela

Jeżeli profil właściciela zmieni klan:

* nie zmieniać stanu części wyłącznie na podstawie starego snapshotu,
* wygenerować zdarzenie ponownej stabilizacji lub audytu,
* przeliczyć klan terytorium,
* dopiero potem zmienić `contained / active`.

Klan terytorium musi być kanonicznie znormalizowany przez katalog GhostNetwork.

## 17. Powiązanie z Territory Control

Przygotować wewnętrzny agregat klastra:

```text
contains_ghost_part
ghost_parts_count
ghost_part_states
ghost_part_relations
```

Relacja względem właściciela:

```text
own_clan
foreign_clan
```

Stan:

```text
public
contained
active
contested_frozen
```

Nie wystawiać jeszcze ukrytej tożsamości części bez projekcji ze Sprintu 120.

Territory Control otrzyma później oznaczenie, że klaster przechowuje komponent własnego albo obcego klanu.

## 18. Zdarzenia terytorialne części

Wymagane:

```text
ghost.part_contained
ghost.part_activated
ghost.part_deactivated
ghost.part_revealed
ghost.part_contested
ghost.part_conflict_resolved
ghost.part_owner_changed
```

Każde zawiera:

```text
source_territory_event_id
territory_id
owner
owner_clan
previous_owner
previous_clan
conflict_id
state_version
```

## 19. Atomowość

Jedno zdarzenie terytorium może zmienić kilka części.

Preferowana transakcja:

```text
lock affected parts
→ resolve all transitions
→ update parts
→ append events
→ increment shared state_version
→ commit
```

Nie pozostawiać połowy części w starym stanie, jeśli obsługiwane zdarzenie obejmuje kilka kotwic.

## 20. Awaria integracji

Błąd GhostNetwork nie może cofać prawidłowej przebudowy zwykłego terytorium.

Preferowana kolejność:

1. system terytorium zatwierdza własną zmianę,
2. publikuje trwałe zdarzenie,
3. GhostNetwork przetwarza je idempotentnie,
4. nieudany handler może zostać ponowiony.

Nie opierać integracji wyłącznie na nietrwałym wywołaniu funkcji po zapisie.

## 21. Recovery

Dodać:

```text
reconcile_parts_with_territories(cycle_id)
```

Tryb recovery:

* pobiera tylko 20 części aktywnego cyklu,
* odczytuje stabilne terytoria,
* wykrywa niezgodne przypisania,
* domyślnie raportuje dry-run,
* jawny tryb naprawczy wykonuje lifecycle transitions,
* każdą poprawkę zapisuje jako `technical_recovery`.

To wyjątkowy przypadek, w którym przeliczenie wszystkich części jest tanie i bezpieczne, bo cykl ma ich dokładnie 20.

## Testy Sprintu 118

Minimum:

* publiczna część bez terytorium,
* część między dwoma filarami `alone`,
* trzeci filar tworzy klaster,
* obcy klan ustawia `contained`,
* właściwy klan ustawia `active`,
* aktywna część zachowuje stan podczas konfliktu,
* contained zachowuje stan podczas konfliktu,
* konflikt nie zmienia widoczności,
* rozstrzygnięcie na korzyść właściciela,
* rozstrzygnięcie bez właściciela,
* przejęcie przez obcy klan,
* przejęcie przez właściwy klan,
* usunięcie jednego z trzech filarów,
* rozpad klastra,
* dwa pozostałe filary `alone`,
* część wraca do `public`,
* podział klastra,
* część trafia tylko do jednego nowego klastra,
* nakładające się obszary nie wybierają losowego właściciela,
* zmiana kilku części jednym eventem,
* retry tego samego eventu,
* błąd handlera nie cofa terytorium,
* recovery dry-run,
* recovery naprawia niespójny stan.

## Poza sprintem

Nie implementować:

* publicznej projekcji tożsamości części,
* markerów mapy,
* linii,
* supermocy,
* RSP,
* reputacji,
* transmisji,
* finalnego rozszerzenia Territory Control.

## DoD

Sprint jest zakończony, gdy odkryta część automatycznie:

* pozostaje publiczna bez stabilnego klastra,
* zostaje zablokowana przez obcy klan,
* zostaje aktywowana przez właściwy klan,
* zachowuje stan podczas konfliktu,
* jest ponownie rozstrzygana dopiero po stabilizacji,
* wraca do publicznego stanu po rozpadzie klastra.


GhostNetwork — neutralne, blokowane i aktywne moduły
GhostNetwork — widoczność danych i projekcje odbiorców
GhostNetwork — markery części i warstwa mapy

Po Sprintach 119–121 GhostNetwork po raz pierwszy staje się widoczny dla graczy: system rozumie strategiczny stan każdej części, bezpiecznie filtruje wiedzę i pokazuje na mapie tylko to, co dany operator naprawdę powinien zobaczyć.



# Sprint 119 — GhostNetwork: neutralne, blokowane i aktywne moduły

## Cel sprintu

Zbudować kanoniczną warstwę strategicznego stanu części, która jednoznacznie odpowiada:

* czy część jest publiczna,
* czy została zabezpieczona przez obcy klan,
* czy została aktywowana przez właściwy klan,
* kto kontroluje jej lokalizację,
* czy moduł daje obecnie supermoc,
* jaki jest postęp każdej z czterech maszyn.

Sprint korzysta z lifecycle części i integracji terytorialnej powstałych wcześniej. Nie wylicza ponownie geometrii i nie implementuje jeszcze widoczności zależnej od odbiorcy.

## 1. Serwis stanu modułów

Dodać:

```text
GhostModuleStateService
```

Minimalny kontrakt:

```text
resolve_part_module_state(part)
resolve_cycle_module_states(cycle_id)
resolve_machine_progress(cycle_id, machine_code)
resolve_clan_machine_progress(cycle_id, clan_code)
```

Ten serwis tłumaczy techniczny stan części na znaczenie strategiczne używane później przez mapę, Territory Control, GhostNetwork Suite, BlackNet i supermoce.

## 2. Trzy główne stany strategiczne

Kanoniczny katalog:

```text
neutral
blocked
active
```

Powiązanie ze stanem części:

```text
part.status = public
→ module_state = neutral
```

```text
part.status = contained
→ module_state = blocked
```

```text
part.status = active
→ module_state = active
```

Nie tworzyć dodatkowych stanów takich jak:

* `owned`,
* `captured`,
* `secured`,
* `activated_by_owner`,
* `foreign_owned`.

Te informacje powinny być przekazywane w osobnych polach.

## 3. Konflikt nie jest czwartym stanem modułu

Podczas konfliktu zachować:

```text
module_state = stan sprzed konfliktu
conflict_state = contested
```

Przykłady:

```text
module_state: active
conflict_state: contested
```

```text
module_state: blocked
conflict_state: contested
```

Nie tworzyć:

```text
module_state: contested
```

jako zamiennika stanu strategicznego, ponieważ konflikt jedynie zamraża poprzedni wynik do stabilizacji granic. 

## 4. Stan neutralny

Część neutralna:

* została odkryta,
* posiada trwałą kotwicę,
* nie znajduje się pod stabilną kontrolą terytorium,
* pozostaje nieaktywna,
* nie daje supermocy,
* nie jest przypisana do właściciela klastra.

Kontrakt:

```text
module_state: neutral
territory_id: null
territory_owner_id: null
territory_clan: null
ability_enabled: false
```

Część neutralna pozostaje w tym stanie bez limitu czasu.

Nie wygasa, nie wraca do puli i nie zmienia lokalizacji.

## 5. Stan blokowany

Część jest blokowana, gdy stabilne terytorium należy do klanu innego niż klan części.

Kontrakt:

```text
module_state: blocked
part_clan: phantom_mesh
territory_clan: virex
territory_owner_id: operator_x
ability_enabled: false
```

Obcy klan:

* może przetrzymywać część dowolnie długo,
* nie otrzymuje jej supermocy,
* nie może jej sprzedać,
* nie może jej przenieść,
* nie może jej zniszczyć,
* nie może przypisać jej do własnej maszyny.

Blokowanie części jest legalną strategią, ale nie jest aktywacją modułu. 

## 6. Stan aktywny

Część jest aktywna, gdy stabilne terytorium należy do właściwego klanu.

Kontrakt:

```text
module_state: active
part_clan: phantom_mesh
territory_clan: phantom_mesh
territory_owner_id: operator_phantom
ability_enabled: true
```

Aktywność jest przypisana do:

* części,
* terytorium,
* klanu kontrolującego lokalizację.

Nie zależy od:

* aktywnej sesji właściciela,
* obecności właściciela online,
* czasu od ostatniego logowania,
* aktywnego okna mapy.

Nieaktywny właściciel nie wyłącza modułu. Moduł pozostaje aktywny, dopóki właściwy klan stabilnie kontroluje lokalizację. 

## 7. Relacja części względem gracza

Dodać osobny resolver:

```text
resolve_part_viewer_relation(part, viewer)
```

Możliwe wyniki:

```text
public_neutral
self_foreign_blocked
self_own_active
clan_own_active
foreign_blocked
foreign_active
```

Znaczenie:

### `public_neutral`

Część nie jest otoczona żadnym stabilnym terytorium.

### `self_foreign_blocked`

Gracz osobiście kontroluje terytorium przechowujące część obcego klanu.

### `self_own_active`

Gracz osobiście kontroluje aktywną część własnego klanu.

### `clan_own_active`

Inny członek klanu kontroluje aktywną część właściwej maszyny.

### `foreign_blocked`

Część jest przetrzymywana przez obcy klan lub innego właściciela, a gracz nie ma pełnych praw właściciela.

### `foreign_active`

Część jest aktywna dla innego klanu.

Ten resolver nie decyduje jeszcze, jakie pola są widoczne. To zadanie Sprintu 120.

## 8. Aktywacja supermocy

Dodać techniczny kontrakt:

```text
ability_enabled
```

Reguła:

```text
module_state == active
→ ability_enabled = true
```

W pozostałych stanach:

```text
ability_enabled = false
```

Nie implementować jeszcze mechanicznego działania mocy.

Sprint przygotowuje źródło prawdy używane później przez rejestr efektów:

```text
klan gracza
+ profesja gracza
+ aktywna część
= dostępna supermoc
```

## 9. Postęp maszyny

Każda maszyna ma dokładnie pięć części.

Dodać agregat:

```text
machine_code
clan_code
parts_total
parts_pooled
parts_reserved
parts_neutral
parts_blocked
parts_active
parts_contested
progress_percent
machine_online
```

`progress_percent` oznacza procent aktywnych modułów:

```text
active_parts / 5 × 100
```

Przykład:

```text
PHANTOM VEIL

MODUŁY ODKRYTE: 4 / 5
MODUŁY AKTYWNE: 2 / 5
MODUŁY BLOKOWANE: 1
POSTĘP MASZYNY: 40%
```

Maszyna jest online dopiero przy:

```text
parts_active == 5
```

Nie oznacza to jeszcze zamknięcia GhostNetwork. Wszystkie cztery maszyny muszą być kompletne.

## 10. Postęp całego cyklu

Dodać agregat:

```text
parts_total: 20
parts_discovered
parts_neutral
parts_blocked
parts_active
parts_contested
machines_online
network_ready
```

Warunek:

```text
network_ready = parts_active == 20
```

Nie uruchamiać jeszcze transmisji. Sprint 127 przejmie blokadę cyklu i finalną kontrolę.

## 11. Aktualizacja po zmianie części

Po zdarzeniach:

```text
ghost.part_discovered
ghost.part_contained
ghost.part_activated
ghost.part_deactivated
ghost.part_revealed
ghost.part_conflict_resolved
```

przeliczyć:

* stan zmienionej części,
* postęp jednej maszyny,
* globalny postęp cyklu,
* stan dwóch sąsiednich połączeń jako wewnętrzną informację.

Nie przeliczać całego świata i wszystkich profili.

Przeliczenie dwudziestu części aktywnego cyklu jest dopuszczalne jako recovery, ale nie jako zwykła reakcja na każde zdarzenie.

## 12. Zdarzenie zmiany maszyny

Zapisać:

```text
ghost.machine_progress_changed
```

Payload:

```text
cycle_id
machine_code
clan_code
previous_active_parts
active_parts
blocked_parts
neutral_parts
machine_online
state_version
```

Zdarzenie powstaje tylko przy realnej zmianie agregatu.

## 13. Zdarzenie ukończenia maszyny

Przy przejściu:

```text
4 / 5 → 5 / 5
```

zapisać:

```text
ghost.machine_online
```

Przy utracie modułu:

```text
5 / 5 → 4 / 5
```

zapisać:

```text
ghost.machine_offline
```

Maszyna może wielokrotnie przechodzić między online i offline podczas cyklu.

Idempotencja musi opierać się na wersji stanu i faktycznej zmianie.

## 14. Oznaczenie klastra w Territory Control

Przygotować bezpieczny wewnętrzny kontrakt klastra:

```text
ghost_components:
    total
    neutral
    blocked
    active
    contested
```

oraz relacje:

```text
contains_own_clan_part
contains_foreign_clan_part
contains_active_part
contains_blocked_part
```

W normalnym stabilnym klastrze część znajdująca się wewnątrz nie będzie `neutral`, ale kontrakt może obsłużyć stan przejściowy lub recovery.

Territory Control ma otrzymać informację, że klaster:

* przechowuje część własnego klanu,
* przechowuje część obcego klanu,
* aktywuje część,
* blokuje część,
* uczestniczy w konflikcie dotyczącym komponentu.

Nie przekazywać jeszcze ukrytej nazwy części bez projekcji widoczności.

## 15. Brak usuwania części przez Territory Control

Jeżeli użytkownik próbuje porzucić obiekt będący kotwicą części:

* sama część nie może zostać usunięta,
* porzucenie zwykłego przejętego obiektu może rozbić terytorium,
* GhostNetwork zachowuje kotwicę,
* po rozpadzie terytorium część staje się publiczna,
* marker może przejść w niezależny `GHOST ANCHOR`.

Territory Control musi otrzymać:

```text
contains_ghost_part: true
ghost_anchor_protected: true
```

Nie wolno użyć tej flagi do zablokowania rozpadu terytorium. Chroni ona komponent przed usunięciem, nie obszar gracza.

## 16. Diagnostyka stanów

Dodać raport:

```text
ghostnetwork modules status
```

Zwraca:

```text
cycle_id
state_version
parts_by_state
machines
network_ready
conflicts_frozen
integrity_errors
```

W trybie admin może pokazywać wszystkie części, ale zwykły endpoint nie może korzystać z tego raportu.

## Testy Sprintu 119

Minimum:

* neutralna część,
* blokowana część,
* aktywna część,
* aktywna część podczas konfliktu,
* blokowana część podczas konfliktu,
* właściciel offline nie wyłącza modułu,
* obcy klan nie otrzymuje aktywacji,
* właściwy klan aktywuje część,
* utrata terytorium dezaktywuje część,
* pięć części uruchamia maszynę,
* utrata jednej wyłącza maszynę,
* cztery maszyny po pięć części dają `network_ready`,
* jeden brakujący moduł blokuje gotowość,
* relacja `self_foreign_blocked`,
* relacja `self_own_active`,
* relacja `clan_own_active`,
* klastry otrzymują poprawne flagi,
* porzucenie kotwicy nie usuwa części.

## Poza sprintem

Nie implementować:

* filtrowania pól dla odbiorców,
* markerów,
* linii,
* supermocy,
* nagród,
* transmisji.

## DoD

Sprint jest zakończony, gdy każda część posiada jednoznaczny stan strategiczny, każda maszyna ma poprawny postęp, a Territory Control może bezpiecznie rozpoznać klaster przechowujący komponent.

Ten sprint zamienia surowe statusy części w mechanikę zrozumiałą dla całej gry.

---

# Sprint 120 — GhostNetwork: widoczność danych i projekcje odbiorców

## Cel sprintu

Zbudować jedno centralne źródło prawdy decydujące, jakie informacje o części może zobaczyć konkretny gracz, klan, właściciel terytorium albo publiczne medium.

Ta sama projekcja musi być używana przez:

* mapę,
* API,
* GhostNetwork Suite,
* Territory Control,
* BlackNet,
* Cyberner,
* Radio,
* narracyjny outbox,
* przyszłą Ollamę.

Frontend nie może samodzielnie ukrywać pól otrzymanych z backendu. Backend nie może wysyłać tajnych danych z założeniem, że CSS ich nie pokaże. 

## 1. Serwis widoczności

Dodać:

```text
GhostVisibilityService
```

Minimalny kontrakt:

```text
project_part_for_viewer(part, viewer)
project_parts_for_viewer(parts, viewer)
project_connection_for_viewer(connection, viewer)
project_machine_for_viewer(machine, viewer)
project_territory_component_for_viewer(cluster, viewer)
```

Wymagane tryby odbiorcy:

```text
player
clan
owner
public
internal
```

## 2. Kontekst odbiorcy

Znormalizowany kontrakt:

```text
viewer_id
viewer_clan
viewer_profession
is_authenticated
is_admin
audience_scope
```

Nie przekazywać do projektora pełnego profilu.

Wystarczą dane potrzebne do reguł widoczności.

## 3. Projekcja wewnętrzna

`internal` może zawierać:

* pełną nazwę części,
* kod,
* maszynę,
* profesję,
* supermoc,
* właściciela,
* stan,
* sąsiadów,
* topologię,
* historię.

Nie może być zwracana zwykłemu endpointowi gracza.

Dostępna wyłącznie:

* domenie,
* testom,
* recovery,
* kontrolowanym narzędziom admina.

## 4. Część neutralna

Neutralna część jest w pełni publiczna.

Każdy odbiorca widzi:

```text
part_id
part_code
name
clan_code
clan_name
machine_code
machine_name
profession_code
profession_name
ability_code
ability_name
ability_description
latitude
longitude
module_state: neutral
territory_id: null
discovered_at
visible_connections
```

Część neutralna nie posiada ukrytej klasyfikacji. Kanon jasno określa, że neutralny komponent jest jawny dla wszystkich. 

## 5. Część blokowana przez obcy klan

### Właściciel terytorium

Właściciel widzi pełne dane:

* nazwę części,
* klan docelowy,
* maszynę,
* profesję,
* supermoc,
* stan połączeń,
* informację, że część jest blokowana.

Projekcja:

```text
visibility_level: full_owner
identity_visible: true
ability_visible: true
```

### Pozostali gracze

Pozostali widzą jedynie:

```text
territory_contains_part: true
part_identity: null
part_clan: null
machine: null
profession: null
ability: null
module_state: blocked
territory_id
territory_owner_id
location lub odniesienie do terytorium
```

Dotyczy to również innych członków klanu właściciela.

Pełną tożsamość zna właściciel konkretnego terytorium, a nie automatycznie cały jego klan. 

## 6. Część aktywna we właściwym klanie

### Właściciel terytorium

Pełne dane.

### Członkowie właściwego klanu

Pełne dane:

* nazwa,
* maszyna,
* profesja,
* supermoc,
* właściciel,
* stan,
* połączenia.

Projekcja:

```text
visibility_level: full_clan
identity_visible: true
ability_visible: true
```

### Pozostałe klany

Widzą:

* lokalizację aktywnego węzła,
* klan,
* właściciela terytorium,
* stan aktywny,
* widoczne linie.

Nie widzą:

* nazwy części,
* profesji,
* supermocy,
* kodu modułu,
* informacji, którzy gracze otrzymali efekt.

Projekcja:

```text
visibility_level: active_foreign
part_code: null
name: null
profession: null
ability: null
clan_code
territory_owner_id
module_state: active
```

## 7. Konflikt

Podczas konfliktu widoczność jest taka sama jak przed jego rozpoczęciem.

Projektor używa:

```text
frozen_status
frozen_visibility_context
```

albo aktualnego stanu bazowego zachowanego przez lifecycle.

Nie zmieniać widoczności tylko dlatego, że:

```text
conflict_state = contested
```

Dodać jedynie publiczną informację:

```text
contested: true
```

jeżeli pozwalają na to reguły terytorium.

## 8. Brak pamięci systemowej

System nie próbuje usuwać wiedzy, którą gracz zdobył wcześniej, gdy część była publiczna.

Nie tworzyć jednak automatycznego pola:

```text
viewer_knows_part_identity
```

na podstawie samego wcześniejszego wyświetlenia.

Gracze mogą:

* zapisać informację,
* przekazać ją na Cybernerze,
* skłamać,
* rozpoznać lokalizację.

Interfejs po ukryciu części stosuje aktualne reguły widoczności, nawet jeśli człowiek pamięta wcześniejszą nazwę.

## 9. Projekcja pozycji

Dla blokowanej części publiczny odbiorca może widzieć:

* terytorium zawierające część,
* strategiczne oznaczenie obszaru.

Nie musi otrzymywać dokładnego `target_id` kotwicy, jeśli ujawniałoby to więcej niż mapa.

Dodać dwa warianty:

```text
location_visibility: exact
location_visibility: territory_only
```

Neutralna:

```text
exact
```

Aktywna:

```text
exact
```

Blokowana dla właściciela:

```text
exact
```

Blokowana dla pozostałych:

```text
territory_only
```

## 10. Projekcja identyfikatorów

Nie wysyłać ukrytych wartości pod neutralnymi nazwami pól.

Błędne:

```json
{
  "part_code": "P3",
  "part_code_visible": false
}
```

Poprawne:

```json
{
  "part_code": null,
  "identity_visible": false
}
```

To samo dotyczy:

* `ability_code`,
* `profession_code`,
* `machine_code`,
* prawdziwego `target_id`,
* ukrytych sąsiadów.

## 11. Projekcja połączeń

Widoczność części nie może zdradzać ukrytej topologii.

Reguły:

* część w puli — brak w publicznym snapshotcie,
* aktywny węzeł z nieodkrytym sąsiadem — brak połowy linii,
* aktywny węzeł z odkrytym sąsiadem — projekcja może pokazać połowę,
* ukryta blokowana część nie może ujawnić nazwy przez dane połączenia,
* pełne połączenie może pokazywać dwa widoczne końce zgodnie z prawami odbiorcy.

Szczegółowy rendering powstanie w Sprincie 122.

## 12. Territory Control

Dla każdego klastra projekcja może zwrócić:

```text
contains_ghost_part
ghost_part_count
ghost_part_relation
ghost_part_state
ghost_part_identity_visible
ghost_part_summary
```

Przykłady:

### Właściciel blokujący obcą część

```text
relation: self_foreign_blocked
identity_visible: true
```

### Właściciel aktywnej części własnego klanu

```text
relation: self_own_active
identity_visible: true
```

### Inny gracz oglądający blokowany klaster

```text
relation: foreign_blocked
identity_visible: false
summary: "TERYTORIUM ZAWIERA CZĘŚĆ GHOSTNETWORK"
```

## 13. GhostNetwork Suite

Przygotować projekcję list desktopowego narzędzia:

```text
public_parts
blocked_parts
active_parts
self_controlled_parts
clan_parts
```

To nie są osobne magazyny danych.

Są to filtrowane widoki tej samej listy części aktywnego cyklu.

Pozycja może zawierać:

```text
part_id lub public_entity_id
display_label
module_state
viewer_relation
visibility_level
clan
owner
territory
latitude
longitude
can_show_on_map
can_teleport
```

Pola nazwy, profesji i mocy zależą od projekcji.

## 14. BlackNet i media

Dodać projekcję faktu:

```text
project_event_fact_for_audience(event, audience)
```

Publiczny BlackNet nie może otrzymać pełnej tożsamości części blokowanej.

Przykład publiczny:

```json
{
  "event_type": "part_contained",
  "territory_contains_part": true,
  "part_identity": null,
  "owner_clan": "virex"
}
```

Przykład prywatny właściciela:

```json
{
  "event_type": "part_contained",
  "part_code": "P3",
  "part_name": "Paranoia Loop",
  "target_clan": "phantom_mesh"
}
```

Najbezpieczniejsza zasada: medium nie otrzymuje informacji, których nie może opublikować. 

## 15. Klasy projekcji

Każda pozycja otrzymuje:

```text
visibility_level
```

Dozwolone:

```text
internal
full_public
full_owner
full_clan
active_foreign
contained_hidden
```

Nie opierać frontendu na zgadywaniu, czy `name == null`.

## 16. Stabilny publiczny identyfikator

Ukryta część może potrzebować identyfikatora do:

* odświeżenia delty,
* oznaczenia terytorium,
* otwarcia mapy.

Nie wolno przy tym ujawniać `part_code`.

Dodać:

```text
public_entity_id
```

Przykład:

```text
ghost-node:8f3a12
```

Identyfikator:

* jest stabilny w cyklu,
* nie zawiera kodu części,
* nie pozwala odtworzyć maszyny,
* może być używany przez delty.

## 17. Cache projekcji

Projekcja może być cache’owana według:

```text
cycle_id
state_version
viewer_id
viewer_clan
audience_scope
```

Zmiana `state_version` unieważnia cache.

Nie cache’ować pełnej projekcji ownera jako publicznej.

## 18. Testy przecieków

Dodać testy zabezpieczające przed ujawnieniem:

* nazwy części,
* kodu części,
* profesji,
* supermocy,
* maszyny,
* ukrytego `target_id`,
* nieodkrytych sąsiadów,
* pełnej topologii.

Test powinien serializować response i sprawdzać brak zabronionych wartości, nie tylko stan pól w Pythonie.

## 19. Snapshot dla odbiorcy

Dodać:

```text
GhostNetworkService.get_snapshot_for_viewer(viewer)
```

Minimalnie:

```text
cycle
progress
machines
parts
connections
visibility_version
state_version
```

Zawiera wyłącznie części i pola widoczne dla odbiorcy.

Nie zawiera aktywnych rezerwacji ani pełnego ring order.

## 20. Recovery projekcji

Jeżeli frontend utraci delty:

* pobiera snapshot dla tego samego odbiorcy,
* nie pobiera snapshotu wewnętrznego,
* odbudowuje markery i warstwy,
* nie wymaga pełnego profilu ani pełnej mapy świata.

## Testy Sprintu 120

Minimum:

* neutralna część pełna dla wszystkich,
* blokowana część pełna dla właściciela,
* blokowana część ukryta dla członka klanu właściciela,
* blokowana część ukryta dla właściwego klanu części,
* aktywna część pełna dla właściwego klanu,
* aktywna część ograniczona dla pozostałych,
* konflikt zachowuje poprzednią widoczność,
* publiczny snapshot nie zawiera rezerwacji,
* publiczny snapshot nie zawiera ring order,
* ukryty `part_code` nie występuje w JSON,
* ukryta moc nie występuje w JSON,
* publiczne media nie otrzymują danych owner-only,
* Territory Control otrzymuje poprawny summary,
* GhostNetwork Suite otrzymuje poprawne grupy,
* cache nie miesza właściciela z publicznym odbiorcą,
* recovery zwraca tę samą projekcję.

## Poza sprintem

Nie implementować:

* markerów,
* linii,
* GUI GhostNetwork Suite,
* supermocy,
* narracji Ollamy,
* transmisji.

## DoD

Sprint jest zakończony, gdy istnieje jedna centralna projekcja, która pozwala wszystkim interfejsom pokazywać dokładnie tyle informacji, ile wolno danemu odbiorcy, bez ryzyka wycieku ukrytej części.

Ten sprint buduje filtr bezpieczeństwa, przez który przejdzie każda informacja GhostNetwork.

---

# Sprint 121 — GhostNetwork: markery części i warstwa mapy

## Cel sprintu

Dodać do istniejącej mapy lekką warstwę GhostNetwork renderującą odkryte części zgodnie z projekcją widoczności odbiorcy.

Mapa nie podejmuje decyzji o stanie części. Otrzymuje gotowe projekcje i jedynie:

* tworzy markery,
* aktualizuje je przez delty,
* pokazuje właściwe panele,
* oznacza terytoria przechowujące komponenty.

Warstwa nie rysuje jeszcze połączeń pomiędzy częściami. Linie powstaną w Sprincie 122.

## 1. Osobny moduł frontendowy

Utworzyć:

```text
static/js/map/ghostnetwork.js
```

Odpowiedzialności:

```text
loadGhostNetworkSnapshot()
renderGhostParts()
applyGhostPartDelta()
removeGhostPartMarker()
renderGhostTerritoryBadge()
openGhostPartPanel()
clearGhostNetworkLayer()
recoverGhostNetworkLayer()
```

Nie dopisywać całej logiki bezpośrednio do `map_template.html`.

## 2. Osobny scope danych

Mapa pobiera:

```text
GET /api/ghostnetwork/snapshot
```

albo wspólny endpoint scope recovery.

Response jest już przefiltrowany przez `GhostVisibilityService`.

Nie wywoływać:

* pełnego `/api/profile`,
* `sync_session_profile()`,
* pełnego renderowania mapy,
* listy wszystkich profili,
* pełnej diagnostyki GhostNetwork.

## 3. Rejestr warstwy

Frontend utrzymuje:

```text
window.ghostNetworkPartLayers
window.ghostNetworkTerritoryLayers
window.ghostNetworkStateVersion
```

Rejestr kluczuje po:

```text
public_entity_id
```

albo widocznym `part_id`.

Nie kluczować po nazwie części ani zaokrąglonych współrzędnych.

## 4. Pane Leafleta

Dodać osobne pane:

```text
ghostNetworkPartPane
ghostNetworkTerritoryPane
```

Proponowana kolejność:

* ponad zwykłymi markerami POI,
* ponad terytoriami,
* poniżej krytycznych overlayów systemowych,
* bez blokowania kontekstowego menu innych elementów poza hitboxem markera.

Nie używać przypadkowego wysokiego `z-index`, który przykryje menu albo Response Network.

## 5. Marker neutralnej części

Neutralna część ma wyraźny publiczny marker.

Marker powinien komunikować:

* część GhostNetwork,
* klan części,
* stan neutralny,
* brak aktywacji.

Dla pełnej projekcji panel pokazuje:

```text
nazwa części
maszyna
klan
profesja
supermoc
odkrywca, jeśli publiczny
status
lokalizacja
```

Nie dodawać akcji:

* podnieś,
* sprzedaj,
* przenieś,
* usuń.

Dostępne mogą być:

* pokaż szczegóły,
* ustaw fokus,
* teleport,
* informacje o terytorium.

## 6. Marker blokowanej części dla właściciela

Właściciel terytorium otrzymuje marker albo oznaczenie wewnątrz własnego klastra z pełnymi danymi.

Wygląd:

* stan `BLOCKED`,
* kolor właściciela terytorium połączony z ostrzeżeniem klanu docelowego,
* brak animacji aktywnego przepływu,
* wyraźna informacja, że moduł jest nieaktywny.

Panel:

```text
KOMPONENT ZABEZPIECZONY
CZĘŚĆ: [pełna nazwa]
KLAN DOCELOWY: [klan części]
STATUS: BLOKOWANY
AKTYWNOŚĆ: 0%
```

## 7. Blokowana część dla pozostałych

Pozostali nie otrzymują dokładnego markera części.

Mapa oznacza klaster:

```text
TERYTORIUM ZAWIERA CZĘŚĆ GHOSTNETWORK
TOŻSAMOŚĆ: UKRYTA
STATUS: NIEAKTYWNA
```

Oznaczenie może być:

* badge przy centroidzie klastra,
* subtelnym symbolem na obramowaniu,
* ikoną strategicznego terytorium.

Nie ujawnia:

* dokładnej kotwicy,
* nazwy,
* kodu,
* klanu docelowego,
* profesji,
* supermocy.

## 8. Marker aktywnej części dla właściwego klanu

Właściwy klan widzi pełny aktywny węzeł:

* nazwę części,
* maszynę,
* profesję,
* aktywną supermoc,
* właściciela,
* stan połączeń.

Marker powinien posiadać:

* mocniejszą poświatę,
* animację aktywnego impulsu,
* kolor klanu,
* badge aktywnego modułu.

Nie przesadzać z animacją, ponieważ docelowo na mapie może być 20 komponentów i wiele linii.

## 9. Marker aktywnej części dla obcych klanów

Obcy klan widzi aktywny strategiczny węzeł, ale bez pełnej tożsamości.

Panel:

```text
AKTYWNY WĘZEŁ GHOSTNETWORK

KLAN: SIATKA WIDMO
WŁAŚCICIEL: operator_x
MODUŁ: ZASZYFROWANY
STATUS: AKTYWNY
```

Marker może korzystać z koloru klanu, lecz nie z ikony konkretnej części, jeśli zdradzałaby jej tożsamość.

## 10. Ghost Anchor

Jeżeli źródłowy marker zniknął:

* warstwa nadal renderuje komponent,
* używa zapisanych współrzędnych,
* używa specjalnej ikony `GHOST ANCHOR`,
* panel pokazuje informację o utraconym źródle.

Przykład:

```text
GHOST ANCHOR
ŹRÓDŁO PIERWOTNE: UTRACONE
KOMPONENT: ZACHOWANY
```

Zakres pozostałych informacji nadal zależy od widoczności.

## 11. Interakcja z istniejącymi markerami

Marker części może znajdować się na tych samych współrzędnych co:

* przejęty obiekt,
* filar,
* inner node,
* zwykły marker mapy.

Nie usuwać ani zastępować istniejącego markera gameplayowego.

Preferowane rozwiązania:

* osobny mały badge GhostNetwork,
* złożony marker,
* kontrolowany offset,
* warstwa nakładana na istniejący cel.

Nie tworzyć sytuacji, w której kliknięcie komponentu uniemożliwia użycie kontekstowego menu obiektu.

## 12. Panel szczegółów

Panel musi renderować wyłącznie pola otrzymane w projekcji.

Nie posiada warunków typu:

```text
if viewerClan === partClan
```

Backend już rozstrzygnął widoczność.

Frontend może jedynie sprawdzić:

```text
visibility_level
identity_visible
ability_visible
location_visibility
```

## 13. Status konfliktu

Część objęta konfliktem:

* zachowuje dotychczasowy wygląd stanu bazowego,
* otrzymuje badge lub subtelny efekt `CONTESTED`,
* nie przełącza się wizualnie między active i blocked przy każdej zmianie granicy,
* nie zmienia informacji do czasu zdarzenia stabilizacji.

To musi odpowiadać zamrożeniu lifecycle.

## 14. Oznaczenia klastrów

Rozszerzyć warstwę terytoriów o:

```text
contains_ghost_part
ghost_part_state
ghost_part_relation
```

Stany wizualne klastra:

### Neutralny klaster bez komponentu

Bez dodatkowego oznaczenia GhostNetwork.

### Klaster blokujący część

Badge komponentu zabezpieczonego.

### Klaster aktywujący część

Badge aktywnego węzła.

### Klaster z komponentem w konflikcie

Badge zachowuje wcześniejszy stan i otrzymuje nakładkę konfliktu.

Kolor zagrożenia Territory Control:

* zielony,
* pomarańczowy,
* czerwony

pozostaje osobnym systemem od koloru części GhostNetwork.

Nie nadpisywać całego koloru klastra kolorem komponentu.

## 15. Ładowanie warstwy

Warstwa może zostać załadowana:

* podczas końcowego etapu bootowania mapy,
* równolegle z opcjonalnymi warstwami,
* po udostępnieniu podstawowego gameplayu mapy, jeśli snapshot jest wolniejszy.

Błąd GhostNetwork:

* nie blokuje mapy,
* pokazuje mały status warstwy,
* pozwala wykonać retry,
* nie usuwa zwykłych terytoriów i markerów.

## 16. Delty

Obsłużyć minimum:

```text
ghost.part_discovered
ghost.part_contained
ghost.part_revealed
ghost.part_activated
ghost.part_deactivated
ghost.part_contested
ghost.part_conflict_resolved
ghost.part_anchor_source_lost
ghost.part_anchor_migrated
ghost.part_consumed
```

Delta zawiera gotową projekcję dla odbiorcy albo identyfikator wymagający punktowego odczytu.

Preferowana jest gotowa bezpieczna projekcja.

## 17. Aktualizacja pojedynczego markera

Po delcie:

1. Sprawdzić `state_version`.
2. Odrzucić starsze zdarzenie.
3. Znaleźć marker przez `public_entity_id`.
4. Zaktualizować ikonę, pozycję i panel.
5. Zaktualizować badge klastra.
6. Nie odświeżać całej mapy.
7. Nie pobierać pełnego profilu.

## 18. Zdarzenie odkrycia

Po `ghost.part_discovered`:

* nowy neutralny marker pojawia się bez przeładowania mapy,
* użytkownik otrzymuje kontrolowany komunikat systemowy,
* mapa może ustawić subtelny fokus, jeśli odkrywcą jest aktualny gracz,
* nie otwiera automatycznie ciężkiego modala podczas innej operacji.

Pierwsze odkrycie w historii gracza może uruchomić osobny onboarding komponentu.

## 19. Zdarzenie ukrycia w terytorium

Po przejściu `public → blocked`:

* dla właściciela neutralny marker zmienia się w marker blokowanego komponentu,
* dla pozostałych dokładny marker znika,
* pojawia się badge terytorium,
* stare popupy i tooltipy są usuwane,
* pamięć frontendowa nie zachowuje ukrytych danych w dostępnym DOM.

## 20. Zdarzenie aktywacji

Po przejściu do `active`:

* pojawia się aktywny węzeł,
* dla właściwego klanu panel jest pełny,
* dla pozostałych moduł pozostaje zaszyfrowany,
* aktualizuje się postęp maszyny,
* przygotowywany jest stan do narysowania połączeń w Sprincie 122.

## 21. Zdarzenie zużycia

Po `ghost.part_consumed`:

* marker części znika z aktywnej warstwy,
* badge klastra zostaje usunięty,
* zwykły obiekt i terytorium pozostają,
* frontend może później dodać historyczny ślad transmisji.

Nie usuwać markera zwykłego POI ani klastra.

## 22. Recovery

Jeżeli frontend wykryje:

* lukę wersji,
* nieznany `public_entity_id`,
* marker bez projekcji,
* błąd zastosowania delty,

pobiera wyłącznie:

```text
ghostnetwork snapshot
```

Następnie:

* czyści warstwę GhostNetwork,
* odtwarza markery i badge,
* nie przeładowuje całej mapy,
* nie wywołuje pełnego bootowania.

## 23. Wydajność

Wymagania:

* maksymalnie 20 aktywnych markerów części,
* brak stałych interwałów animujących każdy marker osobno w JavaScript,
* animacje oparte o CSS,
* jeden listener delt,
* brak ciężkiego pollera,
* brak pełnego re-renderu po pojedynczej zmianie,
* brak odpytywania profilu przy zmianie części.

Architektura GhostNetwork wymaga osobnego snapshotu i scope delt właśnie po to, aby globalna warstwa nie obciążała mapy pełnymi synchronizacjami. 

## 24. Responsywność i dostępność

Marker:

* ma kontrolowany hitbox,
* nie wychodzi poza własny rozmiar,
* nie przechwytuje kliknięć poza ikoną.

Panel:

* działa na desktopie i mobile,
* ma przycisk zamknięcia,
* ma czytelne statusy bez polegania wyłącznie na kolorze,
* pełne dane mają etykiety tekstowe,
* ukryta część nie pozostawia nazwy w `title` ani `aria-label`.

## 25. Testy Sprintu 121

Minimum:

* neutralny marker dla każdego gracza,
* pełne dane neutralnej części,
* blokowana część pełna dla właściciela,
* blokowana część ukryta dla pozostałych,
* aktywna część pełna dla właściwego klanu,
* aktywna część zaszyfrowana dla obcego klanu,
* konflikt zachowuje wcześniejszy marker,
* Ghost Anchor po utracie źródła,
* dwa markery na tych samych współrzędnych nie blokują menu,
* delta odkrycia,
* delta ukrycia,
* delta aktywacji,
* delta dezaktywacji,
* delta migracji,
* delta zużycia,
* starsza delta zostaje odrzucona,
* luka wersji uruchamia recovery,
* recovery nie przeładowuje pełnej mapy,
* ukryta nazwa nie znajduje się w DOM,
* brak ciężkiego pollera,
* mapa działa mimo błędu warstwy GhostNetwork.

## Poza sprintem

Nie implementować:

* linii i łuków połączeń,
* animacji połówek,
* transmisji,
* supermocy,
* nagród,
* finalnego GhostNetwork Suite.

## DoD

Sprint jest zakończony, gdy odkryte części pojawiają się na mapie zgodnie z prawami odbiorcy, blokowane komponenty ukrywają dokładną kotwicę przed nieuprawnionymi graczami, aktywne moduły są czytelnie oznaczone, a cała warstwa aktualizuje się punktowo przez delty.


GhostNetwork — połowy linii, pełne połączenia i animacje
GhostNetwork — delty, snapshot i recovery
GhostNetwork — supermoce profesji i rejestr efektów

Po Sprintach 122–124 GhostNetwork staje się pełną mechaniczną siecią: linie pokazują realne zależności, stan synchronizuje się lekko pomiędzy interfejsami, a aktywowanie modułu daje konkretną przewagę wszystkim operatorom właściwej profesji.

Lecimy dalej — Sprint 122 pokaże żywą topologię sieci, 123 zapewni lekką synchronizację bez przeładowywania mapy, a 124 uruchomi profesje wyłącznie wtedy, gdy odpowiadający im moduł naprawdę pozostaje aktywny.

# Sprint 122 — GhostNetwork: połowy linii, pełne połączenia i animacje

## Cel sprintu

Wyrenderować na mapie połączenia wynikające z zapisanej topologii GhostNetwork oraz aktualnych stanów części.

Warstwa ma obsługiwać:

* brak linii,
* nieaktywną relację,
* połowę połączenia,
* pełne połączenie,
* zerwanie połączenia,
* zmianę kierunku aktywnej połówki,
* animację przepływu pomiędzy aktywnymi węzłami.

Frontend nie wylicza topologii ani nie sprawdza stanów części. Otrzymuje gotową projekcję połączenia dla aktualnego gracza. Każda część posiada dokładnie dwóch sąsiadów, a wszystkie 20 elementów tworzy jeden zamknięty obwód. 

## 1. Backendowy resolver połączeń

Rozszerzyć `GhostTopologyService` o publiczny resolver:

`resolve_connection_projection(connection, viewer_context)`

Każda projekcja połączenia powinna zawierać:

* `connection_id`,
* `public_connection_id`,
* `state`,
* widoczny początek,
* widoczny koniec,
* współrzędne widocznych węzłów,
* kierunek przepływu,
* klany końców,
* poziom widoczności danych,
* integralność,
* wersję stanu,
* informację o konflikcie.

Dozwolone stany projekcji:

* `hidden`,
* `inactive`,
* `half_from_a`,
* `half_from_b`,
* `active`.

Stan `inactive` może istnieć w snapshotcie technicznym, ale nie musi być rysowany na mapie.

## 2. Reguły widoczności linii

### Obie części nieodkryte

`hidden`

Brak jakiegokolwiek elementu na mapie.

### Jedna aktywna, druga nieodkryta

`hidden`

Aktywny węzeł nie może zdradzić lokalizacji części znajdującej się jeszcze w puli.

### Obie odkryte i nieaktywne

`inactive`

Brak widocznej linii.

### A aktywna, B odkryta i nieaktywna

`half_from_a`

Linia rozpoczyna się przy A i kończy w połowie drogi zakłóceniem.

### B aktywna, A odkryta i nieaktywna

`half_from_b`

Kierunek odwrotny.

### Obie aktywne

`active`

Powstaje pełne połączenie z pulsującym przepływem.

Te reguły wynikają bezpośrednio z kanonicznego zachowania GhostNetwork: połówka pojawia się wyłącznie wtedy, gdy jeden koniec jest aktywny, a drugi został już odkryty. 

## 3. Konflikt nie przerywa linii

Jeżeli część pozostawała aktywna przed rozpoczęciem konfliktu:

* jej pełne połączenia nadal działają,
* jej połówki nadal pozostają widoczne,
* linia otrzymuje jedynie stan `contested`,
* nie zmienia długości ani kierunku do czasu stabilizacji granic.

Jeżeli część była blokowana albo neutralna, konflikt również nie aktywuje jej połączeń.

## 4. Zmiana stanu połączenia

Po zdarzeniach części przeliczyć wyłącznie jej dwa sąsiednie połączenia.

Źródłowe zdarzenia:

* `ghost.part_discovered`,
* `ghost.part_activated`,
* `ghost.part_deactivated`,
* `ghost.part_revealed`,
* `ghost.part_contained`,
* `ghost.part_conflict_resolved`,
* `ghost.part_consumed`.

Nie przeliczać wszystkich 20 połączeń po każdej zmianie pojedynczej części.

Recovery może przeliczyć cały pierścień.

## 5. Zdarzenie domenowe

Przy realnej zmianie zapisać:

`ghost.connection_changed`

Payload:

* `cycle_id`,
* `connection_id`,
* `previous_state`,
* `state`,
* identyfikatory końców,
* widoczne współrzędne,
* `flow_direction`,
* `contested`,
* `state_version`,
* `reason`.

Nie publikować kodu nieodkrytej części ani pełnej topologii.

## 6. Warstwa mapy

Rozszerzyć:

`static/js/map/ghostnetwork.js`

o:

* `renderGhostConnections()`,
* `createGhostConnectionLayer()`,
* `updateGhostConnectionLayer()`,
* `removeGhostConnectionLayer()`,
* `applyGhostConnectionDelta()`,
* `animateGhostConnectionPulse()`.

Rejestr:

`window.ghostNetworkConnectionLayers`

Kluczowanie po `public_connection_id`.

## 7. Osobne pane Leafleta

Dodać:

* `ghostNetworkConnectionPane`,
* `ghostNetworkPulsePane`.

Linie powinny być:

* ponad poligonami terytoriów,
* poniżej markerów części,
* poniżej menu i overlayów,
* całkowicie nieinteraktywne poza kontrolowanym hitboxem podglądu.

Nie mogą przechwytywać kliknięć przeznaczonych dla markerów albo mapy.

## 8. Łuki zamiast prostych linii

Połączenia mają być krzywymi łukami.

Dla każdej pary współrzędnych obliczyć deterministyczny punkt kontrolny na podstawie:

* `connection_id`,
* odległości końców,
* pozycji w pierścieniu,
* opcjonalnego znaku wygięcia.

Ten sam connection zawsze powinien wyginać się w tę samą stronę po odświeżeniu.

Nie używać losowej krzywizny przy każdym renderze.

## 9. Pełna linia

Pełne połączenie posiada trzy warstwy:

1. tło stabilizujące,
2. gradient pomiędzy kolorami klanów,
3. animowany impuls GhostSystemu.

Przykładowy przebieg:

`kolor klanu A → GhostSignal → kolor klanu B`

Animacja:

* oparta o CSS lub SVG,
* bez osobnego `setInterval` dla każdej linii,
* prędkość kontrolowana tokenem CSS,
* zatrzymywana przy `prefers-reduced-motion`.

## 10. Połowa linii

Połówka:

* rozpoczyna się przy aktywnym węźle,
* dochodzi do geometrycznego środka łuku,
* stopniowo traci kolor klanu,
* kończy się glitchem lub urwanym impulsem.

Nie powinna dochodzić wizualnie do nieaktywnego węzła.

Nie może ujawniać części, która nie została jeszcze odkryta.

## 11. Zerwanie połączenia

Przy przejściu:

`active → half_from_a`

albo:

`active → half_from_b`

wykonać krótką animację:

* impuls gaśnie od dezaktywowanego końca,
* środkowa część linii rozpada się,
* pozostaje połowa wychodząca od aktywnego węzła.

Przy przejściu:

`active → hidden`

linia zanika całkowicie.

Animacja jest tylko wizualizacją zatwierdzonego stanu backendu.

## 12. Domknięcie pełnego połączenia

Przy przejściu:

`half_from_a → active`

lub:

`half_from_b → active`

brakująca połowa dochodzi od nowo aktywowanego węzła do środka.

Po zetknięciu:

* pojawia się jeden mocniejszy impuls,
* linia przechodzi w zwykły rytm aktywny,
* aktualizuje się licznik pełnych połączeń.

Nie uruchamiać jeszcze globalnej sekwencji transmisji. Ta pojawi się w Sprincie 128.

## 13. Kierunek impulsu

Zwykłe pełne połączenie może posiadać kierunek zgodny z kolejnością pierścienia:

`part_a → part_b`

Kierunek służy:

* późniejszej animacji obiegu całej sieci,
* spójnemu pulsowaniu,
* pokazaniu kolejności transmisji.

Nie oznacza przepływu własności ani ataku.

## 14. Panel połączenia

Kliknięcie kontrolowanego hitboxu pełnej lub połowicznej linii może otworzyć niewielki panel.

Dla niekompletnego połączenia:

* węzeł A: aktywny,
* węzeł B: odkryty / nieaktywny,
* przepływ: 50%,
* stabilność: oczekiwanie.

Dla pełnego:

* węzeł A,
* węzeł B,
* przepływ: stabilny,
* integralność: 100%.

Nazwy końców zależą od projekcji widoczności aktualnego gracza. 

## 15. Liczniki sieci

Snapshot mapy może zawierać:

* `connections_total: 20`,
* `connections_hidden`,
* `connections_half`,
* `connections_active`,
* `circuit_complete`.

`circuit_complete` nie może być liczone wyłącznie na frontendzie.

## 16. Wydajność

Maksymalny stan jednego cyklu:

* 20 części,
* 20 połączeń.

Wymagania:

* jedna warstwa połączeń,
* brak osobnego pollera,
* brak odświeżenia Folium,
* punktowe aktualizacje,
* animacja CSS/SVG,
* brak wielu timerów JavaScript,
* usuwanie starych ścieżek i listenerów.

## 17. Recovery

Po utracie wersji:

1. pobrać GhostNetwork snapshot,
2. usunąć wyłącznie warstwę połączeń,
3. odtworzyć widoczne linie,
4. zachować zwykłą mapę i terytoria,
5. wznowić animację od aktualnego stanu, bez odgrywania historycznych przejść.

## Testy Sprintu 122

Minimum:

* dwie nieodkryte części — brak linii,
* aktywna i nieodkryta — brak linii,
* dwie odkryte nieaktywne — brak renderu,
* A aktywna — połowa od A,
* B aktywna — połowa od B,
* obie aktywne — pełna linia,
* aktywna część traci kontrolę — zerwanie,
* konflikt nie zrywa aktywnej linii,
* stabilizacja zmienia stan,
* połączenie nie ujawnia kodu nieodkrytej części,
* deterministyczna krzywizna,
* brak blokowania kliknięć mapy,
* delta aktualizuje jedną linię,
* recovery odtwarza 20 połączeń,
* `prefers-reduced-motion`,
* brak timerów per linia.

## Poza sprintem

Nie implementować:

* globalnego impulsu transmisji,
* dodatkowej pajęczyny synchronizacyjnej,
* czarnego ekranu,
* restartu,
* historycznych linii.

## DoD

Sprint jest zakończony, gdy mapa pokazuje wyłącznie poprawne połówki i pełne połączenia, reaguje punktowo na aktywację oraz utratę części i nigdy nie zdradza lokalizacji nieodkrytego modułu.

Ten sprint zamienia dwadzieścia osobnych markerów w faktycznie rosnącą sieć.

---

# Sprint 123 — GhostNetwork: delty, snapshot i recovery

## Cel sprintu

Domknąć niezależny kanał synchronizacji GhostNetwork, aby mapa, desktopowe aplikacje i przyszłe media mogły reagować na zmiany bez pobierania pełnego profilu ani ciężkiego stanu mapy.

GhostNetwork otrzymuje osobny scope delty, własny snapshot oraz kontrolowany mechanizm recovery. Architektura wymaga aktualizacji punktowych i zabrania ciężkiego pollera oraz `sync_session_profile()` przy odświeżaniu warstwy. 

## 1. Osobny scope delt

Dodać do `GameStateDeltaBus`:

`ghostnetwork`

Minimalne typy:

* `ghost.cycle_created`,
* `ghost.cycle_activated`,
* `ghost.part_discovered`,
* `ghost.part_contained`,
* `ghost.part_revealed`,
* `ghost.part_activated`,
* `ghost.part_deactivated`,
* `ghost.part_contested`,
* `ghost.part_conflict_resolved`,
* `ghost.connection_changed`,
* `ghost.machine_progress_changed`,
* `ghost.machine_online`,
* `ghost.machine_offline`,
* `ghost.cycle_locked`,
* `ghost.signal_sent`,
* `ghost.version_changed`,
* `ghost.restart_required`.

Wewnętrzne rezerwacje nie trafiają do zwykłego scope gracza.

## 2. Producent zdarzeń

Dodać:

`GhostNetworkDeltaPublisher`

Odpowiada za:

* pobranie zdarzenia domenowego,
* ustalenie odbiorców,
* wykonanie projekcji widoczności,
* zapis bezpiecznego payloadu,
* deduplikację,
* logowanie błędów publikacji.

Warstwa domenowa nie powinna bezpośrednio budować prywatnych payloadów dla graczy.

## 3. Odbiorcy

Możliwe zakresy:

* `public`,
* `clan`,
* `owner`,
* `player`,
* `all_active_players`.

Dla jednego zdarzenia mogą powstać różne projekcje.

Przykład `ghost.part_contained`:

* właściciel otrzymuje pełną tożsamość,
* pozostali otrzymują ukryty badge terytorium,
* publiczne media otrzymują wyłącznie dozwolony fakt.

Nie zapisywać jednego pełnego payloadu i filtrować go później w przeglądarce.

## 4. Kontrakt delty

Każda delta:

* `event_id`,
* `scope`,
* `type`,
* `cycle_id`,
* `entity_id`,
* `state_version`,
* `audience_scope`,
* `payload`,
* `created_at`,
* `dedupe_key`.

Payload może zawierać:

* gotową projekcję części,
* gotową projekcję połączenia,
* agregat maszyny,
* usunięcie elementu,
* wymóg recovery.

## 5. Kolejność wersji

Klient utrzymuje:

`ghostNetworkStateVersion`

Zasady:

* niższa lub równa wersja — odrzucić jako starą albo zduplikowaną,
* kolejna oczekiwana wersja — zastosować,
* luka wersji — zatrzymać punktowe zmiany i uruchomić recovery,
* delta z innego cyklu — porównać z aktualnym snapshotem.

Nie zakładać, że jedna wersja oznacza dokładnie jedno zdarzenie. Jedna transakcja może opublikować kilka delt z tym samym `state_version`.

## 6. Grupowanie delt transakcji

Dodać:

* `transaction_id`,
* `transaction_index`,
* `transaction_size`.

Pozwala to zastosować razem:

* zmianę części,
* zmianę dwóch połączeń,
* zmianę postępu maszyny,
* zmianę globalnego postępu.

Frontend nie powinien przez krótką chwilę pokazywać części aktywnej bez odpowiadających jej połączeń.

## 7. Snapshot gracza

Endpoint:

`GET /api/ghostnetwork/snapshot`

Response:

* `cycle`,
* `ghostsystem_version`,
* `state_version`,
* `visibility_version`,
* `progress`,
* `machines`,
* widoczne `parts`,
* widoczne `connections`,
* `restart_required`,
* `stabilization_until`,
* diagnostykę ograniczoną do danych klienta.

Nie zawiera:

* rezerwacji,
* pełnego katalogu topologii,
* nieodkrytych części,
* ukrytych nazw,
* pełnych eventów historycznych.

## 8. Snapshot lekki dla desktopu

Dodać możliwość ograniczenia projekcji:

`GET /api/ghostnetwork/snapshot?view=suite`

Może zwrócić:

* listy części,
* stany,
* lokalizacje,
* relacje odbiorcy,
* postęp maszyn.

Nie musi zawierać geometrii linii potrzebnej mapie.

Widoki:

* `map`,
* `suite`,
* `territory_summary`,
* `status`.

Wszystkie korzystają z jednej projekcji widoczności.

## 9. Snapshot wewnętrzny

Pozostawić osobny:

`build_internal_snapshot()`

Nie może być wywoływany przez endpoint użytkownika.

Zawiera:

* wszystkie 20 części,
* pełną topologię,
* rezerwacje,
* historię techniczną,
* błędy integralności.

## 10. Recovery klienta

Dodać wspólny klient:

`window.GhostNetworkDeltaClient`

Odpowiedzialności:

* subskrypcja delt,
* kolejka transakcji,
* wersjonowanie,
* deduplikacja,
* dystrybucja zdarzeń do widoków,
* recovery,
* retry z backoffem.

Odbiorcy:

* mapa,
* Territory Control,
* GhostNetwork Suite,
* przyszły panel statusu.

Nie tworzyć osobnego pollera w każdej aplikacji.

## 11. Rejestr widoków

Widoki mogą rejestrować callbacki:

* `onPartChanged`,
* `onConnectionChanged`,
* `onMachineChanged`,
* `onCycleChanged`,
* `onRecovery`.

Po zamknięciu okna muszą się wyrejestrować.

Nie pozostawiać listenerów aplikacji, która została usunięta z DOM.

## 12. Recovery mapy

Po recovery:

* odtworzyć markery części,
* odtworzyć badge terytoriów,
* odtworzyć linie,
* ustawić postęp,
* nie przeładowywać iframe mapy,
* nie pobierać pełnego profilu.

## 13. Recovery desktopowych aplikacji

Po recovery:

* odtworzyć listę części,
* zachować aktualny ekran aplikacji, jeśli element nadal istnieje,
* pokazać komunikat o odświeżeniu stanu,
* nie uruchamiać mapy.

## 14. Recovery po zmianie cyklu

Jeżeli klient posiada cykl A, a delta dotyczy cyklu B:

1. zatrzymać stare delty,
2. pobrać nowy snapshot,
3. usunąć zużyte elementy aktywnego świata,
4. ustawić nową wersję,
5. wznowić nasłuch.

Nie mieszać elementów dwóch cykli.

## 15. Deduplikacja

Dedupe po:

* `event_id`,
* `dedupe_key`,
* `cycle_id + state_version + entity_id + type`.

Ograniczyć rozmiar pamięciowego zbioru przetworzonych eventów.

Po pełnym recovery można wyczyścić starsze identyfikatory poprzedniej wersji.

## 16. Snapshot consistency token

Response może zawierać:

`snapshot_checksum`

Checksum obejmuje publiczne identyfikatory:

* części,
* ich wersje,
* połączenia,
* stan cyklu.

Klient może użyć go diagnostycznie.

Nie jest zabezpieczeniem kryptograficznym ani źródłem autoryzacji.

## 17. Retry i backoff

Przy błędzie snapshotu:

* zachować ostatni poprawny widok,
* oznaczyć dane jako chwilowo nieaktualne,
* ponowić z rosnącym opóźnieniem,
* nie spamować endpointu,
* pozwolić na ręczne odświeżenie.

## 18. Brak ciężkiego pollera

Dozwolone:

* istniejący delta bus,
* recovery po luce,
* bardzo rzadki sanity refresh jako zabezpieczenie, jeśli audyt wykaże potrzebę.

Niedozwolone:

* osobne odpytywanie co kilka sekund w każdej aplikacji,
* odświeżanie pełnej mapy,
* pobieranie pełnego profilu dla części,
* przeliczanie terytoriów przy odczycie snapshotu.

## 19. Publikacja po błędzie

Błąd publikacji delty nie może cofnąć poprawnej transakcji domenowej.

Zdarzenie domenowe pozostaje w dzienniku.

Dodać mechanizm:

* `pending`,
* `published`,
* `failed`,
* retry publikacji.

Można wykorzystać istniejący log zdarzeń jako źródło ponownej publikacji.

## 20. Recovery po stronie serwera

Dodać:

`rebuild_ghostnetwork_delta_projection(cycle_id, from_version=None)`

Może:

* odtworzyć brakujące projekcje z dziennika,
* porównać snapshot z eventami,
* wykryć nieopublikowane zmiany.

Nie powinien ponownie wykonywać efektów domenowych.

## 21. Obserwowalność

Logować:

* event domenowy,
* liczbę odbiorców,
* liczbę projekcji,
* czas publikacji,
* wielkość payloadu,
* błędy widoczności,
* liczbę recovery,
* powód recovery,
* luki wersji.

Każdy log posiada `cycle_id` i `state_version`.

## 22. Testy Sprintu 123

Minimum:

* publiczna delta neutralnej części,
* prywatna delta właściciela,
* ukryta delta pozostałych,
* delta klanowa aktywnego modułu,
* kilka delt z jedną wersją,
* zachowanie kolejności transakcji,
* starsza delta odrzucona,
* duplikat odrzucony,
* luka uruchamia recovery,
* zmiana cyklu uruchamia recovery,
* snapshot mapy,
* snapshot suite,
* snapshot nie zawiera rezerwacji,
* snapshot nie zawiera ukrytych danych,
* wyrejestrowanie zamkniętego okna,
* błąd delty nie cofa domeny,
* retry publikacji,
* recovery nie wywołuje profilu ani pełnej mapy,
* brak pollera per aplikacja.

## Poza sprintem

Nie implementować:

* transmisji końcowej,
* archiwum historycznego,
* Ollamy,
* pełnego GhostNetwork Suite GUI.

## DoD

Sprint jest zakończony, gdy każda zmiana części, połączenia, maszyny i cyklu dociera do uprawnionych klientów jako bezpieczna delta, a utrata zdarzenia prowadzi do lekkiego recovery wyłącznie scope GhostNetwork.

Ten sprint sprawia, że GhostNetwork może działać długo i stabilnie bez zamieniania mapy w ciężki monitor całego świata.

## Checkpoint 123

Wdrozenie ma korzystac z istniejacego `delta_bus`, `GhostVisibilityService` i
readonly snapshotow GhostNetwork. Delta bus pozostaje dziennikiem zmian, a nie
drugim magazynem stanu. Recovery dotyczy tylko scope `ghostnetwork` i nie moze
odpalac pelnego profilu ani reloadu mapy.

---

# Sprint 124 — GhostNetwork: supermoce profesji i rejestr efektów

## Cel sprintu

Uruchomić centralny rejestr efektów profesji, w którym dostęp do supermocy wynika z aktualnego stanu części:

`klan gracza + profesja + aktywny moduł = aktywna supermoc`

Supermoc nie jest trwałym polem profilu. Jeżeli część zostanie dezaktywowana, wszyscy gracze odpowiedniej profesji natychmiast tracą rozszerzenie.

Reguły nie mogą zostać rozrzucone po endpointach jako przypadkowe `if clan` i `if profession`. 

## 1. Centralny rejestr

Dodać:

`GhostAbilityRegistry`

Minimalny kontrakt:

* `register(effect)`,
* `get(ability_code)`,
* `list_for_clan(clan_code)`,
* `resolve_player_abilities(player_context)`,
* `is_ability_active(player_context, ability_code)`,
* `apply_modifier(effect_type, context, value)`,
* `collect_effects(effect_type, context)`.

Rejestr ładuje 20 definicji ze Sprintu 112.

## 2. Kontekst gracza

Minimalny kontrakt:

* `player_id`,
* `clan_code`,
* `profession_code`,
* `level`,
* `target`,
* `territory`,
* `operation`,
* `viewer_context`.

Nie przekazywać całego profilu do każdego efektu.

## 3. Warunek aktywacji

Supermoc jest aktywna tylko wtedy, gdy:

1. profil ma poprawny klan,
2. profil ma profesję należącą do tego klanu,
3. katalog wskazuje odpowiadającą część,
4. część w aktywnym cyklu istnieje,
5. jej `module_state == active`,
6. cykl nie jest zamknięty ani po transmisji.

Właściciel terytorium nie musi posiadać tej profesji.

Aktywna część uruchamia moc dla wszystkich graczy właściwego klanu mających przypisaną profesję.

## 4. Brak zapisu w profilu

Nie zapisywać:

* `active_superpowers`,
* `profession_power_enabled`,
* kopii stanu modułu,
* trwałego bonusu części.

Profil może przechowywać wyłącznie:

* klan,
* profesję,
* historię użyć,
* osiągnięcia.

Stan mocy jest wyliczany.

## 5. Cache uprawnień

Cache może używać klucza:

* `cycle_id`,
* `state_version`,
* `player_id`,
* `clan_code`,
* `profession_code`.

Każda zmiana części unieważnia odpowiedni cache klanu lub profesji.

Nie trzymać uprawnienia dłużej niż wersja stanu.

## 6. Typy efektów

Rejestr powinien obsługiwać co najmniej:

* modyfikator wartości,
* dodatkowy odczyt,
* czasowy stan celu,
* czasową akcję aktywowaną przez gracza,
* reakcję na zdarzenie,
* ograniczoną liczbę aktywnych instancji,
* cooldown.

Przykładowe kontrakty:

* `hack_threshold_modifier`,
* `market_demand_preview`,
* `territory_defense_layer`,
* `operation_alert_delay`,
* `scan_detail_modifier`,
* `territory_repair`,
* `territory_information_mask`,
* `operation_quarantine`.

## 7. Status mechaniki mocy

Każda definicja otrzymuje:

* `catalog_only`,
* `passive_active`,
* `active_command`,
* `event_reaction`,
* `implemented`,
* `disabled`.

Po tym sprincie wszystkie 20 mocy powinno posiadać poprawny kontrakt.

Mechanika może być wdrażana w kontrolowanych adapterach, ale żadna moc nie może być oznaczona jako `implemented`, jeśli nie posiada testów i realnego punktu integracji.

## 8. VIREX — pięć mocy

### Insider Feed — Broker

Typ: `market_demand_preview`.

Efekt:

* rozszerza widok Ghost Exchange o przewidywany trend,
* nie zmienia faktycznej ceny bez dodatkowej aktywacji,
* dane pochodzą z backendu, nie z losowego frontendu.

### Wejście Serwisowe — Architekt

Typ: `hack_threshold_modifier`.

Efekt:

* tworzy czasowy backdoor na kwalifikującym celu,
* obniża wymagany próg zabezpieczeń dla członków VIREX,
* zapisuje właściciela, czas i cel,
* może zostać usunięty lub wygasnąć.

### Fałszywy Obraz — Manipulator

Typ: `territory_information_mask`.

Efekt:

* zmienia wyłącznie projekcję informacji operacyjnej,
* nie zmienia prawdziwego stanu terytorium ani części,
* nie może ukryć danych części wbrew regułom widoczności GhostNetwork.

### Wrogie Przejęcie — Egzekutor Zysku

Typ: `territory_attack_window`.

Efekt:

* czasowo zwiększa tempo usuwania pozostałych zabezpieczeń,
* wymaga już częściowego rozbrojenia,
* nie przejmuje celu automatycznie.

### Predykcja Operacyjna — Kurator Algorytmu

Typ: `operation_probability_zone`.

Efekt:

* pokazuje strefy prawdopodobieństwa,
* nie ujawnia dokładnych części ani graczy,
* nie może przewidzieć niewidocznej rezerwacji konkretnego celu.

## 9. Echo Wolności — pięć mocy

### Expose — Haktywista

Typ: `security_weakness_reveal`.

Efekt:

* ujawnia słabe zabezpieczenia członkom Echa,
* właściciel celu otrzymuje informację o ujawnieniu.

### Przejęcie Narracji — Socjotechnik

Typ: `operation_alert_delay`.

Efekt:

* opóźnia pełny alert pierwszej fazy,
* nie usuwa całego ryzyka operacji,
* może rozszerzać zasięg oznaczonego komunikatu klanowego.

### Pełne Ujawnienie — Odsłaniacz

Typ: `scan_detail_modifier`.

Efekt:

* rozszerza szczegóły zabezpieczeń i historii,
* nie ujawnia części ukrytej przez zasady widoczności.

### Sygnał Oporu — Wizjoner

Typ: `clan_operation_beacon`.

Efekt:

* oznacza terytorium jako cel klanowy,
* może dać premię członkom klanu w określonym promieniu,
* publikuje zatwierdzony komunikat Cybernera.

### Efekt Domina — Zapalnik

Typ: `neighbor_security_reduction`.

Efekt:

* po realnym rozbrojeniu jednego elementu osłabia sąsiedni,
* wymaga istniejącego powiązania terytorialnego,
* nie może tworzyć nieskończonej reakcji łańcuchowej.

## 10. Siatka Widmo — pięć mocy

### Węzeł Widmo — Iluzjonista

Typ: `false_activity_marker`.

Efekt:

* tworzy fałszywy marker informacyjny,
* nie tworzy części ani GhostNetwork node,
* znika po odpowiednim skanowaniu.

### Glitch Injection — Wirusolog

Typ: `territory_stability_damage`.

Efekt:

* stopniowo osłabia stabilność wskazanego zabezpieczenia,
* pozostawia wykrywalną infekcję,
* może zostać usunięty przez Rollback.

### Fałszywe Tropienie — Paranoik

Typ: `false_tracking_traces`.

Efekt:

* tworzy kilka fałszywych kierunków śladu,
* ostrzega gracza o intensywnym skanowaniu jego zasobów.

### Pęknięcie Sieci — Rozłamowiec

Typ: `territory_connection_disruption`.

Efekt:

* destabilizuje połączenie pomiędzy elementami terytorium,
* nie zmienia topologii GhostNetwork,
* wpływa wyłącznie na strukturę obrony terytorium.

### Odbicie — Lustrzany Sędzia

Typ: `attack_reflection`.

Efekt:

* reaguje na wykryty skan lub infiltrację,
* może ujawnić klan, narzędzie albo przybliżony kierunek,
* nie wykonuje automatycznego kontrataku.

## 11. Strażnicy Ładu — pięć mocy

### Skan Integralny — Analizator

Typ: `territory_integrity_scan`.

Efekt:

* wykrywa backdoory, infekcje, iluzje i przygotowania do ataku,
* nie ujawnia tożsamości części wbrew projekcji.

### Bastion — Obrońca

Typ: `territory_defense_layer`.

Efekt:

* dodaje ograniczoną dodatkową warstwę zabezpieczenia,
* wymaga osobnego przebicia,
* liczba aktywnych Bastionów jest ograniczona.

### Rollback — Rekonstruktor

Typ: `territory_repair`.

Efekt:

* odbudowuje fragment zabezpieczenia,
* usuwa Glitch Injection,
* naprawia pęknięcie,
* nie przywraca już całkowicie utraconego terytorium.

### Korytarz Zaufania — Mediator

Typ: `trusted_access_corridor`.

Efekt:

* przyznaje czasowy, imienny dostęp operatorom innego klanu,
* nie przenosi własności,
* nie zezwala na przejęcie części ani terytorium.

### Kwarantanna — Egzekutor

Typ: `operation_quarantine`.

Efekt:

* czasowo zatrzymuje dalszy postęp aktywnego ataku,
* blokuje rozpoczęcie nowych operacji na elemencie,
* nie cofa dotychczasowego postępu,
* posiada twardy cooldown.

Pełne funkcje tych dwudziestu modułów oraz granice ich działania są elementem kanonu maszyn. 

## 12. Adaptery systemów

Dodać wydzielone adaptery:

* `GhostMarketAbilityAdapter`,
* `GhostHackAbilityAdapter`,
* `GhostTerritoryAbilityAdapter`,
* `GhostOperationAbilityAdapter`,
* `GhostVisibilityAbilityAdapter`,
* `GhostCybernerAbilityAdapter`.

Endpointy pytają adapter lub rejestr o efekt.

Nie importują konkretnych klas dwudziestu mocy.

## 13. Efekty pasywne

Modyfikatory pasywne powinny być czystymi funkcjami:

`modified_value = registry.apply_modifier(effect_type, context, base_value)`

Wymagania:

* deterministyczność,
* ograniczenia minimum i maksimum,
* zapis źródła modyfikatora,
* brak trwałej zmiany bazowej konfiguracji.

## 14. Efekty aktywowane

Aktywne moce potrzebują:

* `ability_instance_id`,
* aktywatora,
* celu,
* czasu rozpoczęcia,
* `expires_at`,
* cooldownu,
* statusu,
* limitu równoczesnych instancji,
* dziennika zdarzeń.

Nie przechowywać ich w `ghost_parts`.

Część jedynie włącza dostęp do tworzenia instancji mocy.

## 15. Utrata modułu

Po `ghost.part_deactivated`:

* nowe użycie mocy zostaje zablokowane,
* pasywny modyfikator znika natychmiast,
* aktywne instancje zachowują się zgodnie z definicją:

  * `terminate_on_part_loss`,
  * `persist_until_expiry`,
  * `grace_period`.

Każda moc musi jawnie określić politykę.

Domyślnie:

`terminate_on_part_loss`

## 16. Konflikt

Ponieważ moduł zachowuje aktywność podczas konfliktu, odpowiadająca mu supermoc również pozostaje aktywna do stabilizacji granic.

Nie wyłączać mocy w momencie pojawienia się `conflict_state = contested`.

## 17. Uprawnienia i walidacja

Przed użyciem aktywnej mocy backend ponownie sprawdza:

* gracza,
* klan,
* profesję,
* część,
* stan modułu,
* cooldown,
* limit instancji,
* poprawność celu,
* zasady zasięgu,
* aktualny stan operacji lub terytorium.

Frontend nigdy nie jest źródłem prawdy o dostępności mocy.

## 18. Projekcja dla profilu i GUI

Profil może otrzymać lekki odczyt:

* profesja,
* powiązany moduł,
* stan modułu,
* moc,
* aktywność,
* cooldown,
* dostępne użycia.

Nie zapisywać tam bieżącego stanu jako danych trwałych.

## 19. Delty mocy

Dodać:

* `ghost.ability_enabled`,
* `ghost.ability_disabled`,
* `ghost.ability_activated`,
* `ghost.ability_expired`,
* `ghost.ability_cancelled`,
* `ghost.ability_cooldown_changed`.

Odbiorcy zależą od definicji mocy.

Fałszywe markery i maskowanie informacji wymagają bezpiecznej projekcji, która nie ujawnia przeciwnikowi prawdziwego stanu.

## 20. Audyt i zdarzenia

Każde użycie zapisuje:

* gracza,
* profesję,
* część,
* cel,
* czas,
* wynik,
* przyczynę odrzucenia,
* wpływ,
* `state_version`,
* `dedupe_key`.

Ollama może później otrzymać zatwierdzony fakt o użyciu zdolności, ale nie steruje mocą.

## 21. Balans

Wartości liczbowe:

* premie,
* czasy,
* promienie,
* limity,
* cooldowny

muszą pochodzić z konfiguracji.

Nie umieszczać ich bezpośrednio w endpointach.

Kanon świadomie pozostawia dokładne wartości do późniejszego balansu. 

## 22. Testy Sprintu 124

Minimum:

* profesja bez aktywnej części — brak mocy,
* aktywna część — moc dostępna,
* inna profesja — brak dostępu,
* inny klan — brak dostępu,
* właściciel części bez właściwej profesji — brak osobistej mocy,
* członek klanu z profesją — dostęp,
* właściciel offline nie wyłącza mocy klanowi,
* konflikt nie wyłącza mocy,
* stabilna utrata części wyłącza moc,
* cache unieważniony przez wersję,
* aktywne użycie respektuje cooldown,
* utrata części kończy instancję zgodnie z polityką,
* Pełne Ujawnienie nie omija widoczności części,
* Węzeł Widmo nie tworzy prawdziwego komponentu,
* Pęknięcie Sieci nie zmienia topologii GhostNetwork,
* Korytarz Zaufania nie przenosi własności,
* Kwarantanna nie cofa postępu,
* Rollback nie odzyskuje całkowicie utraconego terytorium,
* wszystkie 20 definicji posiada adapter i test kontraktu.

## Poza sprintem

Nie implementować:

* końcowego balansu liczbowego,
* dedykowanych animacji każdej mocy,
* nagród RSP za użycie,
* narracji medialnej,
* transmisji GhostSignalu.

## DoD

Sprint jest zakończony, gdy wszystkie 20 profesji posiada kanoniczny kontrakt mocy, dostęp jest wyliczany z aktywnego modułu, efekty przechodzą przez centralny rejestr i żaden system nie potrzebuje rozsianych warunków klanowo-profesyjnych.

## Checkpoint Sprintu 124

`GhostAbilityRegistry` jest centralnym punktem rozstrzygania mocy profesji.
Aktywność wynika z katalogu, profesji gracza, aktywnego cyklu i
`module_state == active` odpowiadającej części. Konflikt nie wyłącza mocy, jeśli
zamrożony stan części nadal jest aktywny, a utrata części albo transmisja cyklu
odcina dostęp przy kolejnym resolve.

Efekty przechodzą przez adaptery domenowe `market`, `hack`, `territory`,
`operation`, `visibility` i `cyberner`. Adaptery są na tym etapie bezpiecznym
kontraktem i nie zmieniają jeszcze balansu liczbowego.

Artefakt sprintu: `doc/sprint_124_ghostnetwork_abilities.md`.




GhostNetwork — wkład graczy, RSP i reputacja klanowa
GhostNetwork — obrona, odbicia i zabezpieczenia nagród
GhostNetwork — domknięcie sieci i blokada cyklu

Po Sprintach 125–127 GhostNetwork zna pełny wkład społeczności, nagradza prawdziwe działania, chroni ekonomię przed farmieniem i potrafi bezpiecznie powiedzieć: sieć jest zamknięta — od tej chwili transmisji nie da się już zatrzymać.

Lecimy dalej — Sprint 125 zbuduje uczciwy ledger wkładu i nagród, Sprint 126 rozpozna prawdziwe obrony oraz odbicia bez otwierania farmy RSP, a Sprint 127 atomowo zamknie kompletną sieć i przygotuje niezmienny snapshot do transmisji.

# Sprint 125 — GhostNetwork: wkład graczy, RSP i reputacja klanowa

## Cel sprintu

Zbudować centralny system rejestrowania wkładu operatorów oraz klanów w cykl GhostNetwork i podłączyć go do istniejącego RSP oraz rozwoju LVL.

Nagrody mają dotyczyć faktycznie potwierdzonych wydarzeń strategicznych:

* odkrycia części,
* pierwszego otoczenia,
* pierwszej aktywacji,
* późniejszego odbicia,
* utrzymania aktywnego modułu,
* udziału w obronie,
* utrzymania węzła podczas transmisji,
* domknięcia GhostNetwork.

Sprint nie przyznaje osobnej waluty i nie ustawia LVL bezpośrednio. GhostNetwork zasila istniejący system RSP, który dalej rozwija poziom gracza. 

## 1. Serwis wkładu i nagród

Dodać dwa rozdzielone komponenty:

* `GhostContributionService`
* `GhostRewardService`

Pierwszy zapisuje, **co gracz zrobił**. Drugi decyduje, **czy za to działanie należy się nagroda i w jakiej wysokości**.

Nie łączyć tych odpowiedzialności w jednym helperze typu `give_ghost_rsp()`.

Minimalny kontrakt wkładu:

* `record_contribution(...)`
* `list_player_contributions(...)`
* `list_cycle_contributions(...)`
* `aggregate_player_contribution(...)`
* `aggregate_clan_contribution(...)`

Minimalny kontrakt nagród:

* `evaluate_event_reward(...)`
* `create_reward_entry(...)`
* `apply_pending_reward(...)`
* `apply_pending_rewards(...)`
* `get_player_reward_summary(...)`

Ten podział pozwala zachować pełną historię działania nawet wtedy, gdy nagroda zostanie ograniczona przez cooldown albo zabezpieczenia antyfarmowe.

## 2. Model wkładu

Wykorzystać przygotowane wcześniej `ghost_contributions`.

Każdy wpis powinien zawierać:

* `contribution_id`,
* `cycle_id`,
* opcjonalny `signal_id`,
* `player_id`,
* `clan_code`,
* `profession_code`,
* `contribution_type`,
* opcjonalny `part_id`,
* opcjonalny `territory_id`,
* opcjonalny `operation_id`,
* `score`,
* `weight`,
* `source_event_id`,
* `created_at`,
* `dedupe_key`,
* metadane działania.

Dozwolone typy wkładu na tym etapie:

* `part_discovered`
* `part_first_contained`
* `part_first_activated`
* `part_recovered`
* `part_stable_held`
* `part_defended`
* `defense_support`
* `attack_support`
* `territory_repaired`
* `ability_support`
* `transmission_node_held`
* `network_closer`

Nie wszystkie typy muszą od razu wypłacać RSP.

## 3. Wkład nie jest nagrodą

Wkład zapisuje potwierdzony udział niezależnie od tego, czy przysługuje za niego pełne RSP.

Przykład:

* operator pomaga odbić część,
* jego udział zostaje zapisany,
* zabezpieczenie antyfarmowe ogranicza wypłatę,
* historia i wkład klanowy nadal mogą uwzględnić realne działanie z niższą wagą.

Nie usuwać wpisu wkładu tylko dlatego, że nagroda wyniosła `0`.

## 4. Ledger nagród

Wykorzystać `ghost_reward_ledger`.

Minimalne pola:

* `reward_id`,
* `reward_key`,
* `cycle_id`,
* `signal_id`,
* `player_id`,
* `clan_code`,
* `reward_type`,
* `source_event_id`,
* `base_rsp`,
* `multiplier`,
* `final_rsp`,
* `status`,
* `created_at`,
* `applied_at`,
* `failure_reason`,
* metadane kalkulacji.

Statusy:

* `pending`
* `applied`
* `rejected`
* `failed`
* `cancelled`

`reward_key` musi być unikalny.

Przykład klucza:

`ghost-reward:<cycle_id>:<part_id>:discover:<player_id>`

Ten klucz gwarantuje, że retry zdarzenia odkrycia nie wypłaci nagrody ponownie.

## 5. Skala względem zwykłej operacji

Nie wpisywać wszystkich wartości jako stałe RSP oderwane od reszty progresji.

Dodać resolver:

`resolve_standard_operation_rsp(profile, context)`

oraz konfigurację mnożników GhostNetwork.

Przykładowe kategorie balansu:

* odkrycie części: `5–8 ×` zwykła operacja,
* pierwsze otoczenie: `6–10 ×`,
* pierwsza aktywacja: `10–15 ×`,
* odbicie: `12–18 ×`,
* obrona: `5–12 ×`,
* utrzymanie do transmisji: `25–40 ×`.

Dokładne wartości trafiają do konfiguracji, ponieważ dokument kanoniczny świadomie pozostawia je do balansu. 

## 6. Nagroda za odkrycie części

Źródło:

`ghost.part_discovered`

Warunki:

* część została wyemitowana po skutecznym hacku,
* gracz jest zapisanym odkrywcą,
* zdarzenie pochodzi z aktywnego cyklu,
* nie istnieje wcześniejsza nagroda odkrycia tej części.

Rezultat:

* wpis `part_discovered`,
* jednorazowy strategiczny RSP,
* reputacja klanu odkrywcy,
* statystyka osobista,
* przyszły wpis archiwalny.

Odkrywca otrzymuje nagrodę mimo że część zawsze należy do innego klanu.

## 7. Nagroda za pierwsze otoczenie

Źródło:

pierwsze przejście części z `public` do stabilnego `contained` albo `active`.

Warunki:

* część wcześniej nie posiadała stabilnego właściciela,
* jest to pierwsze stabilne otoczenie w cyklu,
* klaster istnieje naprawdę i ma minimum trzy filary,
* zdarzenie nie jest wynikiem recovery technicznego.

Zapisać trwałe pola historyczne:

* `first_contained_by`,
* `first_contained_clan`,
* `first_contained_territory_id`,
* `first_contained_at`.

Pierwsze otoczenie jest nagradzane zarówno dla części własnego, jak i obcego klanu.

Długoterminowe utrzymanie obcej części nie daje jednak stałego RSP.

## 8. Nagroda za pierwszą aktywację

Źródło:

pierwsze `ghost.part_activated`.

Warunki:

* terytorium należy do właściwego klanu części,
* jest stabilne,
* część nie była wcześniej aktywowana w tym cyklu,
* aktywacja nie jest techniczną naprawą danych.

Rezultat:

* duży RSP właściciela terytorium,
* reputacja właściwego klanu,
* wkład `part_first_activated`,
* zapis pierwszego aktywatora.

Wszyscy gracze właściwej profesji otrzymują dostęp do mocy, ale nie otrzymują automatycznie RSP za cudzą aktywację.

## 9. Utrzymanie aktywnego modułu

Dodać kontrolowane naliczanie okresowe, na przykład w przedziałach godzinnych.

Wymagane warunki:

* część ma `module_state = active`,
* znajduje się na stabilnym terytorium właściwego klanu,
* cykl jest `active`,
* nie zakończono transmisji,
* przedział nie został wcześniej rozliczony.

Idempotentny klucz przedziału:

`ghost-hold:<cycle_id>:<part_id>:<owner_id>:<period_start>`

Naliczanie może uwzględniać progi:

* pierwsza godzina,
* sześć godzin,
* dwadzieścia cztery godziny,
* utrzymanie do transmisji.

Każda część posiada limit RSP za utrzymanie w jednym cyklu.

## 10. Konflikt a punkty utrzymania

Podczas aktywnego konfliktu część zachowuje stan `active`, ale spokojne naliczanie za utrzymanie może zostać wstrzymane.

Dodać konfigurację:

`pause_hold_rewards_during_conflict = true`

W tym okresie gracz może otrzymać osobną nagrodę za skuteczną obronę po rozstrzygnięciu konfliktu.

Nie wypłacać jednocześnie maksymalnej nagrody za bezpieczne utrzymanie i pełnej nagrody obronnej za ten sam czas.

## 11. Statystyki osobiste GhostNetwork

Profil może przechowywać trwały agregat historyczny:

* `parts_discovered`,
* `parts_first_contained`,
* `parts_activated`,
* `parts_recovered`,
* `active_node_seconds`,
* `successful_defenses`,
* `signals_participated`,
* `transmission_nodes_held`,
* `networks_closed`,
* `ghostnetwork_rsp_total`.

Profil nie przechowuje bieżącej części, stanu maszyny ani globalnego postępu cyklu.

Aktualizacja agregatu następuje po zastosowaniu potwierdzonego rewardu albo zatwierdzonego wkładu.

## 12. Źródło RSP

Każda wypłata do istniejącego systemu profilu powinna posiadać źródło:

`ghostnetwork`

oraz metadane:

* `cycle_id`,
* `part_id`,
* `reward_type`,
* `reward_id`.

Dzięki temu profil może później pokazać:

* RSP z operacji regularnych,
* RSP z GhostNetwork.

Nie tworzyć drugiego salda RSP.

## 13. Rozwój LVL

Po dodaniu RSP użyć istniejącej procedury przeliczenia LVL.

Nie implementować osobnych progów poziomu dla GhostNetwork.

Jedna transakcja logiczna powinna:

1. zatwierdzić wpis ledgeru,
2. zwiększyć RSP profilu,
3. przeliczyć LVL,
4. zapisać trwałą statystykę,
5. oznaczyć reward jako `applied`,
6. opublikować deltę profilu.

Przy błędzie profil nie może otrzymać RSP przy pozostawieniu ledgeru jako `pending` bez możliwości bezpiecznego retry.

## 14. Reputacja klanowa

Wykorzystać `ghost_clan_reputation`.

Agregat:

* `clan_code`,
* `total_reputation`,
* `signals_participated`,
* `parts_discovered`,
* `parts_first_contained`,
* `parts_activated`,
* `parts_recovered`,
* `territories_defended`,
* `active_node_seconds`,
* `transmission_nodes_held`,
* `updated_at`.

Reputacja klanowa nie jest walutą.

Nie można jej wydać ani przelać.

Służy:

* rankingom,
* podsumowaniu cyklu,
* narracji,
* historii GhostSignali.

## 15. Punktacja klanowa

Dodać wersjonowany policy object:

`GhostClanReputationPolicy`

Każdy typ wkładu otrzymuje wagę.

Przykład:

* odkrycie części — informacja,
* pierwsze otoczenie — zabezpieczenie,
* aktywacja — rozwój maszyny,
* odbicie — ofensywa,
* obrona — utrzymanie,
* aktywny węzeł przy transmisji — największa waga.

Nie wiązać procentu końcowego wyłącznie z sumą RSP, ponieważ RSP może zależeć od poziomu gracza i mnożników progresji.

## 16. Podsumowanie cyklu

Przygotować agregat:

* wkład każdego gracza,
* wkład każdego klanu,
* procentowy udział klanów,
* najważniejsze zdarzenia,
* odkrywców,
* aktywatorów,
* właścicieli węzłów,
* czas utrzymania.

Procent udziału powinien sumować się do `100%`, z kontrolowanym zaokrągleniem.

Nie oznacza zwycięzcy GhostNetwork — sygnał jest wspólnym wynikiem wszystkich klanów. 

## 17. Delty i komunikaty

Dodać:

* `ghost.contribution_recorded`
* `ghost.reward_pending`
* `ghost.reward_applied`
* `ghost.clan_reputation_changed`
* `ghost.player_history_changed`

Prywatna delta nagrody zawiera RSP gracza.

Publiczna delta reputacji nie musi ujawniać dokładnej prywatnej kalkulacji rewardu.

## 18. Recovery ledgeru

Dodać:

`reconcile_ghost_rewards(cycle_id=None, player_id=None)`

Tryb dry-run sprawdza:

* event bez oczekiwanego wkładu,
* wkład bez rewardu,
* reward `applied` bez zmiany RSP,
* reward `pending` po udanej zmianie profilu,
* duplikaty `reward_key`,
* niezgodną reputację klanu.

Naprawa musi opierać się na zdarzeniach domenowych, nie na ponownym zgadywaniu historii z aktualnego stanu części.

## Testy Sprintu 125

Minimum:

* odkrycie zapisuje wkład,
* odkrycie wypłaca RSP raz,
* retry odkrycia nie płaci ponownie,
* pierwsze otoczenie raz,
* pierwsza aktywacja raz,
* ponowna aktywacja nie udaje pierwszej,
* utrzymanie rozliczane przedziałami,
* brak utrzymania obcej części,
* brak naliczania po transmisji,
* konflikt wstrzymuje spokojne utrzymanie,
* RSP podnosi LVL istniejącą ścieżką,
* ledger pozostaje idempotentny,
* agregat osobisty,
* reputacja klanowa,
* procenty czterech klanów,
* recovery wykrywa niespójność,
* los GhostSignalu nie cofa nagród.

## Poza sprintem

Nie implementować jeszcze:

* szczegółowej obrony,
* odbić,
* antyfarmingu par graczy,
* końcowej nagrody transmisji,
* osiągnięć,
* finalnego balansu mnożników.

## DoD

Sprint jest zakończony, gdy każde podstawowe wydarzenie strategiczne tworzy audytowalny wkład, nagrody trafiają do istniejącego RSP dokładnie raz, a klany posiadają porównywalną reputację niezależną od bieżącego stanu profili.

Ten sprint odpowiada na pytanie: **kto rzeczywiście buduje GhostNetwork i jak duży jest jego udział**.

## Checkpoint Sprintu 125

Wdrożono ledger wkładu i nagród GhostNetwork:

* `GhostContributionService`;
* `GhostRewardService`;
* `GhostClanReputationPolicy`;
* rozszerzony zapis `ghost_contributions`, `ghost_reward_ledger`
  i `ghost_clan_reputation`;
* idempotentne `reward_key` dla odkrycia, pierwszego otoczenia, aktywacji,
  odzyskania i okresowego hold reward;
* eventy `ghost.contribution_recorded`, `ghost.reward_pending`,
  `ghost.reward_applied`, `ghost.clan_reputation_changed`
  i `ghost.player_history_changed`;
* dry-run `reconcile_ghost_rewards(...)`.

RSP trafia do istniejącego pola `respect`, a reputacja klanowa pozostaje
osobnym agregatem narracyjno-rankingowym, nie walutą. Profil nie dostaje kopii
bieżącego stanu części ani maszyn.

Artefakt sprintu: `doc/sprint_125_ghostnetwork_rewards.md`.

---

# Sprint 126 — GhostNetwork: obrona, odbicia i zabezpieczenia nagród

## Cel sprintu

Rozpoznać prawdziwe strategiczne obrony oraz odbicia części, zapisać udział operatorów i przyznać podwyższone nagrody tylko wtedy, gdy doszło do realnego konfliktu.

Sprint ma jednocześnie zabezpieczyć system przed:

* szybką wymianą części między współpracującymi kontami,
* pozorowanymi atakami,
* wielokrotnym przejmowaniem tego samego węzła,
* farmieniem obrony przez nieistotne próby,
* powtarzaniem konfliktu tej samej pary graczy.

Kanon zakłada, że system nie blokuje samej zmiany terytorium — ograniczeniom podlegają wyłącznie sztucznie powtarzane nagrody. 

## 1. Serwis zdarzeń strategicznych

Dodać:

`GhostStrategicConflictService`

Minimalny kontrakt:

* `on_conflict_started(...)`
* `record_conflict_progress(...)`
* `record_defensive_action(...)`
* `record_offensive_action(...)`
* `resolve_conflict_outcome(...)`
* `evaluate_defense_reward(...)`
* `evaluate_recovery_reward(...)`

Serwis nie rozstrzyga własności terenu.

Własność nadal ustala istniejący system terytoriów.

## 2. Snapshot początku konfliktu

Gdy część przechodzi do `conflict_state = contested`, zapisać:

* `conflict_id`,
* `part_id`,
* właściciela początkowego,
* klan początkowy,
* status części przed konfliktem,
* integralność terytorium,
* stan zabezpieczeń filarów,
* aktywne operacje ofensywne,
* uczestników początkowych,
* `started_at`.

Snapshot musi być niezmienny i służyć późniejszej ocenie realnej skali konfliktu.

## 3. Aktywność ofensywna

Rejestrować wyłącznie potwierdzone działania mechaniczne:

* rozbrojenie zabezpieczenia,
* przejęcie filaru,
* atak na inner node,
* użycie zdolności ofensywnej,
* zakończoną operację na terytorium,
* zmianę geometrii konfliktu,
* zniszczenie warstwy obronnej.

Nie zaliczać samego:

* wejścia gracza na mapę,
* otwarcia Territory Control,
* zaznaczenia celu,
* rozpoczęcia operacji bez postępu,
* wiadomości na Cybernerze.

## 4. Aktywność defensywna

Możliwy potwierdzony wkład:

* odbudowa zabezpieczenia,
* Rollback,
* usunięcie infekcji,
* naprawa połączenia terytorium,
* uruchomienie Bastionu,
* Kwarantanna,
* zatrzymanie aktywnej operacji,
* odbicie filaru,
* utrzymanie stabilnej kontroli do końca konfliktu.

Każde działanie zapisuje:

* wykonawcę,
* profesję,
* efekt,
* target,
* wartość mechaniczną,
* czas,
* źródłowy event.

## 5. Minimalny próg realnego ataku

Dodać `GhostDefenseRewardPolicy`.

Konfigurowalne warunki pełnej obrony mogą obejmować:

* minimalny procent utraconej integralności,
* minimalną liczbę rozbrojonych zabezpieczeń,
* minimalny czas konfliktu,
* minimalną liczbę zakończonych operacji ofensywnych,
* minimalną liczbę aktywnych agresorów,
* realne zagrożenie utratą części.

Nie każdy przypadkowy atak daje pełną nagrodę.

Jeżeli próg nie został przekroczony:

* konflikt pozostaje w historii,
* wkład obrońców może zostać zapisany,
* pełny RSP za obronę nie jest przyznawany.

## 6. Skuteczna obrona

Obrona jest skuteczna, gdy:

1. część znajdowała się na stabilnym terytorium,
2. powstał rzeczywisty konflikt,
3. atak przekroczył minimalny próg,
4. po stabilizacji część nadal kontroluje ten sam właściciel albo ten sam klan,
5. terytorium znów jest stabilne.

Zapisać:

`ghost.part_defended`

Payload:

* `part_id`,
* `conflict_id`,
* właściciel,
* klan,
* czas konfliktu,
* maksymalny postęp ataku,
* uczestnicy,
* działania defensywne,
* wynik,
* `state_version`.

## 7. Podział nagrody obronnej

Główna nagroda trafia do właściciela terytorium.

Pomocniczy RSP może otrzymać gracz, którego potwierdzony wkład przekroczył minimalną wagę.

Przykładowy podział policy:

* właściciel — główny udział,
* operatorzy naprawiający — udział pomocniczy,
* operatorzy zatrzymujący działania agresora — udział pomocniczy,
* użycie istotnej supermocy — udział specjalny.

Łączna wypłata posiada limit dla jednego konfliktu.

Nie mnożyć pełnej wartości przez liczbę obrońców.

## 8. Definicja odbicia części

Odbicie strategiczne występuje, gdy część:

1. była stabilnie `contained` przez obcy klan,
2. poprzednie terytorium istniało przez wymagany czas,
3. zostało realnie rozbrojone,
4. utraciło stabilną kontrolę,
5. część została następnie objęta stabilnym terytorium właściwego klanu,
6. osiągnęła stan `active`.

Nie uznawać za odbicie:

* przejścia z neutralnej części bez wcześniejszej blokady,
* pierwszej aktywacji bez obcego właściciela,
* technicznej korekty właściciela,
* natychmiastowej zmiany między współpracującymi profilami bez realnego konfliktu.

## 9. Snapshot poprzedniej blokady

Dla części zapisać historię stabilnych okresów kontroli:

* właściciel,
* klan,
* terytorium,
* status części,
* `started_at`,
* `ended_at`,
* czas trwania,
* sposób zakończenia.

Na tej podstawie system może potwierdzić, że część była naprawdę więziona przez obcy klan.

Nie wystarczy sprawdzenie wyłącznie ostatniego eventu.

## 10. Zdarzenie odbicia

Po spełnieniu warunków zapisać:

`ghost.part_recovered`

Payload:

* `part_id`,
* wcześniejszy właściciel,
* wcześniejszy klan,
* nowy właściciel,
* właściwy klan części,
* czas blokady,
* `conflict_id`,
* aktywator,
* pomocnicy,
* poziom realnego rozbrojenia,
* `state_version`.

Pierwsza aktywacja i odbicie są różnymi kategoriami wydarzeń.

## 11. Nagroda za odbicie

Nagroda powinna być większa niż za pierwsze otoczenie.

Otrzymują ją:

* operator finalizujący właściwe terytorium,
* właściciel nowego klastra, jeśli jest inną osobą,
* potwierdzeni uczestnicy ofensywy według udziału.

Dodać twardy limit całkowitego RSP dla jednego odbicia.

Nie wypłacać każdemu uczestnikowi pełnej wartości.

## 12. Historia par graczy

Dodać zapis relacji:

* `part_id`,
* poprzedni właściciel,
* nowy właściciel,
* poprzedni klan,
* nowy klan,
* czas,
* konflikt,
* wypłacona nagroda.

Policy może wykrywać:

* częste zmiany tej samej pary,
* zmianę A → B → A w krótkim czasie,
* powtarzające się konflikty bez realnego oporu,
* identyczne wzorce operacji.

Nie musi automatycznie blokować przejęcia.

Może:

* obniżyć mnożnik,
* ustawić cooldown,
* oznaczyć reward do review,
* odrzucić jedynie nagrodę.

## 13. Cooldown nagrody za węzeł

Dodać konfigurację:

* cooldown dla tej samej części,
* cooldown dla tej samej pary właścicieli,
* malejący mnożnik powtarzanych odbić,
* reset mnożnika po dłuższym stabilnym okresie.

Przykładowe statusy oceny:

* `full_reward`
* `reduced_reward`
* `cooldown`
* `review`
* `no_reward`

Ocena i powód muszą zostać zapisane w ledgerze.

## 14. Minimalny czas poprzedniego terytorium

Aby odbicie otrzymało pełną nagrodę, poprzednia stabilna kontrola musi trwać określony czas.

Nie oznacza to, że krótsza kontrola nie może zostać przejęta.

Zmiana gameplayowa następuje zawsze.

Ograniczana jest wyłącznie wypłata strategicznego RSP.

## 15. Wykrywanie powiązań kont

Sprint nie musi rozwiązać kompletnego problemu multikont.

Ma jednak przygotować kontrakt risk flags:

* wspólne techniczne fingerprinty, jeśli już istnieją,
* nietypowo powtarzalne interakcje,
* szybkie przekazywanie części,
* identyczne czasy aktywności,
* wzajemne farmienie.

GhostNetwork nie podejmuje na tej podstawie automatycznej decyzji o banie.

Może oznaczyć nagrodę jako `review`.

## 16. Obrona nieaktywnego właściciela

Właściciel nie musi być online, aby moduł pozostał aktywny.

Jeżeli inni członkowie klanu realnie bronią jego węzła:

* właściciel może otrzymać główną nagrodę utrzymania obszaru,
* aktywni obrońcy otrzymują udział pomocniczy,
* brak aktywności właściciela nie unieważnia obrony.

Nie przyznawać właścicielowi bonusu za działania, których faktycznie nie wykonał, poza utrzymaniem własności terytorium.

## 17. Przejęcie przez trzeci klan

Możliwy przebieg:

* klan A blokuje część klanu B,
* klan C przejmuje lokalizację,
* część nadal pozostaje `blocked`,
* później klan B ją odbija.

Historia musi zachować wszystkie okresy kontroli.

Pełne odbicie dla klanu B może odnosić się do ostatniego stabilnego blokującego właściciela i całego łańcucha konfliktów.

## 18. Utrata aktywnej części

Jeżeli właściwy klan traci aktywną część na rzecz obcego klanu:

* część przechodzi do `blocked`,
* aktywna moc zostaje wyłączona po stabilizacji,
* maszyna traci moduł,
* pełne linie zostają przerwane,
* nowy obcy właściciel nie otrzymuje nagrody za aktywację.

Może otrzymać jednorazowy wkład za przejęcie strategiczne, ale nie stałe punkty utrzymania obcej części.

## 19. Delty i media

Dodać:

* `ghost.defense_started`
* `ghost.defense_progress_changed`
* `ghost.part_defended`
* `ghost.part_recovered`
* `ghost.reward_reduced`
* `ghost.reward_flagged`

Media otrzymują wyłącznie fakty zgodne z widocznością części.

Nie ujawniać ukrytej tożsamości blokowanego komponentu w publicznym komunikacie.

## 20. Recovery konfliktów

Dodać:

`reconcile_ghost_conflict_outcomes(conflict_id=None)`

Sprawdza:

* zakończony konflikt bez oceny,
* obronę bez rewardu,
* odbicie bez wkładu,
* reward bez potwierdzonego progu,
* duplikat nagrody,
* aktywny konflikt dotyczący nieistniejącego klastra.

Nie zmienia właściciela terytorium.

## Testy Sprintu 126

Minimum:

* nieistotny atak bez pełnej nagrody,
* realny atak zakończony obroną,
* właściciel otrzymuje główną nagrodę,
* pomocnicy otrzymują udział,
* limit całkowitej nagrody,
* pierwsza aktywacja nie jest odbiciem,
* blokowana część odbita przez właściwy klan,
* obce terytorium istniało za krótko — reduced/no reward,
* A → B → A w cooldownie,
* zmiana właściciela nadal zachodzi mimo braku RSP,
* trzeci klan przejmuje obcą część,
* późniejsze odbicie przez właściwy klan,
* nieaktywny właściciel i aktywni obrońcy,
* utrata aktywnej części wyłącza moduł,
* publiczne eventy nie ujawniają ukrytej części,
* retry rozstrzygnięcia jest idempotentny,
* recovery wykrywa brakującą ocenę.

## Poza sprintem

Nie implementować:

* automatycznych banów,
* pełnego systemu anty-multikonto,
* ręcznego panelu moderatorskiego,
* końcowych nagród transmisji,
* losu GhostSignalu.

## DoD

Sprint jest zakończony, gdy system potrafi odróżnić prawdziwą obronę i odbicie od przypadkowego lub pozorowanego konfliktu, zachowuje pełną historię udziału, a zabezpieczenia ograniczają wyłącznie nagrody — nigdy samą możliwość przejęcia części.

Ten sprint odpowiada na pytanie: **czy gracze rzeczywiście walczyli o strategiczny węzeł, czy tylko przekazywali go sobie dla RSP**.

## Checkpoint Sprintu 126

Wdrożono warstwę rozpoznawania prawdziwych obron i odbić GhostNetwork:

* `GhostStrategicConflictService`;
* `GhostDefenseRewardPolicy`;
* tabele `ghost_strategic_conflicts`, `ghost_conflict_actions`,
  `ghost_control_periods` i `ghost_part_transfer_history`;
* eventy `ghost.defense_started`, `ghost.defense_progress_changed`,
  `ghost.part_defended`, `ghost.part_recovered`, `ghost.reward_reduced`
  i `ghost.reward_flagged`;
* konfigurację progów obrony, odbicia i cooldownów par właścicieli;
* fasadę w `GhostNetworkService`;
* testy `tests.test_ghostnetwork_conflicts`.

Sprint nie zmienia własności terytorium ani geometrii mapy. Ograniczeniu
podlegają wyłącznie nagrody RSP, a nie sama możliwość przejęcia części.

Artefakt sprintu: `doc/sprint_126_ghostnetwork_conflicts.md`.

---

# Sprint 127 — GhostNetwork: domknięcie sieci i blokada cyklu

## Cel sprintu

Wykryć moment, w którym wszystkie 20 części jest stabilnie aktywnych, wszystkie 20 połączeń tworzy pełny zamknięty obwód, a następnie atomowo zablokować cykl przed jakąkolwiek dalszą zmianą strategiczną.

Sprint nie wykonuje jeszcze transmisji, nie usuwa części i nie zmienia wersji GhostSystemu.

Jego wynikiem jest niezmienny, zatwierdzony snapshot gotowy do przekazania do Sprintu 128.

## 1. Serwis gotowości sieci

Dodać:

`GhostNetworkClosureService`

Minimalny kontrakt:

* `evaluate_network_readiness(cycle_id)`
* `attempt_cycle_lock(cycle_id, trigger_event_id)`
* `build_lock_snapshot(cycle_id)`
* `get_locked_cycle_snapshot(cycle_id)`
* `validate_locked_snapshot(cycle_id)`

Serwis musi być jedynym miejscem, które może przełączyć cykl:

`active → transmitting`

Na tym etapie status `transmitting` oznacza: sieć została atomowo zamknięta i oczekuje na wykonanie transmisji przez kolejny sprint.

## 2. Warunki gotowości

Wszystkie warunki muszą być spełnione jednocześnie:

* cykl ma status `active`,
* istnieje dokładnie 20 części,
* wszystkie 20 części zostało odkrytych,
* wszystkie 20 ma `module_state = active`,
* wszystkie 20 ma stabilne terytorium właściwego klanu,
* żadna część nie znajduje się w nierozstrzygniętym konflikcie,
* istnieje dokładnie 20 połączeń,
* wszystkie 20 połączeń ma stan `active`,
* topologia nadal jest jednym zamkniętym obwodem,
* checksum topologii jest poprawny,
* nie istnieje wcześniejsza blokada tego cyklu,
* nie istnieje wcześniejszy GhostSignal tego cyklu.

Nie wystarczy samo `parts_active == 20`.

## 3. Stabilność węzłów

Każda część musi posiadać:

* `territory_id`,
* `territory_owner_id`,
* `territory_clan == part.clan_code`,
* aktualną wersję terytorium,
* brak aktywnego `conflict_state`,
* poprawną kotwicę.

Jeżeli jedna część jest aktywna wyłącznie wskutek niespójnego starego rekordu, health check i closure muszą odrzucić blokadę.

## 4. Sprawdzenie maszyn

Wymagane:

* VIREX ORACLE `5/5`,
* ECHO LIBERTAS `5/5`,
* PHANTOM VEIL `5/5`,
* SENTINEL AEGIS `5/5`.

Każda maszyna musi mieć `machine_online = true`.

Nie zakładać gotowości na podstawie samego globalnego licznika.

## 5. Sprawdzenie obwodu

Walidator ponownie sprawdza:

* jeden komponent spójności,
* 20 węzłów,
* 20 krawędzi,
* stopień każdego węzła równy `2`,
* brak połączeń wewnątrz klanu,
* każdy connection `active`,
* wszystkie końce wskazują aktywne części,
* ring order odpowiada checksumowi cyklu.

Domknięcie obwodu jest faktem backendowym, nie rezultatem animacji linii w przeglądarce.

## 6. Trigger oceny

Ocena gotowości może zostać wywołana po:

* `ghost.part_activated`,
* `ghost.part_conflict_resolved`,
* naprawie recovery,
* kontrolowanej komendzie diagnostycznej.

Najczęstszy trigger to aktywacja ostatniego brakującego modułu.

Nie uruchamiać pełnej oceny przy każdym odczycie snapshotu.

## 7. Ostatnia aktywowana część

Jeżeli zdarzenie aktywacji prowadzi do gotowości sieci, zapisać:

* `closing_part_id`,
* `closing_part_code`,
* `closing_player_id`,
* `closing_territory_id`,
* `closing_event_id`,
* `closed_at`.

Operator zostaje kandydatem do osiągnięcia `Ostatni Obwód` i późniejszej dodatkowej nagrody prestiżowej.

Nie oznacza to, że wysłał sygnał samodzielnie.

## 8. Ponowna walidacja w transakcji

`attempt_cycle_lock()` nie może ufać wynikowi wcześniejszego, niezablokowanego odczytu.

W transakcji:

1. zablokować rekord cyklu,
2. potwierdzić `status = active`,
3. zablokować 20 części,
4. ponownie odczytać statusy,
5. zweryfikować konflikty,
6. zweryfikować 20 połączeń,
7. zweryfikować topologię,
8. sprawdzić brak istniejącego signal/lock snapshotu,
9. dopiero potem zmienić status.

Jeżeli stan zmienił się pomiędzy oceną a blokadą, operacja kończy się bez zamknięcia cyklu.

## 9. Atomowa blokada cyklu

W jednej transakcji:

* `cycle.status: active → transmitting`,
* `cycle.locked_at`,
* `cycle.lock_event_id`,
* `closing_part_id`,
* utworzenie lock snapshotu,
* zwiększenie `state_version`,
* zapis `ghost.cycle_locked`,
* zablokowanie nowych rezerwacji,
* zablokowanie emisji części,
* zablokowanie zmian lifecycle części.

Nie tworzyć jeszcze rekordu `ghost_signals`.

To zrobi Sprint 128 na podstawie zatwierdzonego lock snapshotu.

## 10. Snapshot blokady

Dodać trwały rekord, na przykład:

`ghost_cycle_lock_snapshots`

Minimalna zawartość:

* `lock_snapshot_id`,
* `cycle_id`,
* `signal_number`,
* wersja GhostSystemu,
* katalog i checksum,
* topologia i checksum,
* 20 części,
* ich kotwice,
* odkrywcy,
* aktualni właściciele,
* klany,
* terytoria,
* daty aktywacji,
* czas utrzymania,
* konflikty i obrony,
* aktywne połączenia,
* postęp maszyn,
* wkład operatorów,
* reputacja klanowa,
* closing operator,
* `state_version`,
* `locked_at`,
* checksum snapshotu.

Snapshot musi być niezmienny.

## 11. Snapshot właścicieli węzłów

Dla każdej części zapisać stan dokładnie w chwili blokady:

* `part_id`,
* `part_code`,
* `clan_code`,
* `territory_id`,
* `territory_owner_id`,
* `activated_at`,
* `active_duration_seconds`,
* `successful_defenses`,
* `discoverer`,
* `first_activator`,
* `recovery_history`.

Na tej podstawie Sprint 128 przyzna końcowe nagrody i utworzy archiwum sygnału.

Nie odczytywać później „aktualnego” właściciela, ponieważ po locku transmisja ma opierać się na zamrożonym stanie.

## 12. Snapshot wkładu

Zamrozić:

* sumę wkładu gracza,
* sumę wkładu klanu,
* typy udziału,
* pełne węzły transmisyjne,
* operatora domykającego.

Można później naliczyć finalne rewardy, ale źródłowe wartości nie mogą zmienić się po blokadzie.

## 13. Zakaz zmian po locku

Po statusie `transmitting` zablokować:

* nowe rezerwacje,
* emisję części,
* zmianę właściciela części,
* aktywację i dezaktywację,
* migrację kotwicy,
* zmianę topologii,
* zmianę ring order,
* nowe strategiczne nagrody za utrzymanie,
* nowe konflikty wpływające na zamrożony cykl.

Zwykłe terytoria i gameplay mogą technicznie nadal istnieć, ale nie mogą zmienić wyniku zamkniętego cyklu.

## 14. Wyścig ostatniej części z konfliktem

Możliwa sytuacja:

* część zostaje aktywowana,
* jednocześnie rozpoczyna się konflikt jej terytorium.

Blokada musi rozstrzygnąć kolejność transakcyjnie.

Jeżeli trwały event konfliktu został zatwierdzony wcześniej:

* część ma `conflict_state = contested`,
* sieć nie może zostać zamknięta.

Jeżeli blokada cyklu została zatwierdzona wcześniej:

* cykl jest `transmitting`,
* późniejszy konflikt nie przerywa transmisji.

Kanon przewiduje, że po atomowym zablokowaniu cyklu atak nie może już zatrzymać wydarzenia. 

## 15. Wyścig dwóch triggerów

Dwa równoległe handlery mogą zauważyć `20/20`.

Tylko jeden może utworzyć lock snapshot i przełączyć cykl.

Drugi:

* widzi `status = transmitting`,
* zwraca istniejący lock,
* nie zwiększa wersji,
* nie zapisuje drugiego `ghost.cycle_locked`.

## 16. Błąd po blokadzie

Jeżeli transakcja locku się nie zakończy:

* status pozostaje `active`,
* snapshot nie istnieje,
* sieć może zostać oceniona ponownie.

Jeżeli lock został zatwierdzony, ale publikacja delty się nie udała:

* cykl pozostaje `transmitting`,
* event domenowy pozostaje w logu,
* publisher wykonuje retry,
* nie wolno cofać locku tylko z powodu błędu frontendu.

## 17. Zdarzenie `ghost.cycle_locked`

Publiczny payload:

* `cycle_id`,
* `signal_number`,
* `parts_active: 20`,
* `connections_active: 20`,
* `machines_online: 4`,
* `circuit_complete: true`,
* `closing_public_entity_id`,
* dozwolone dane operatora domykającego,
* `state_version`,
* `locked_at`.

Nie publikować jeszcze pełnego archiwum uczestników.

## 18. Komunikat klienta

Po delcie klienci mogą pokazać:

`GHOSTNETWORK: 20/20`

`OBWÓD CZASOWY: ZAMKNIĘTY`

`PRZYGOTOWANIE TRANSMISJI`

Mapa nie uruchamia jeszcze pełnej animacji wysłania.

Może wejść w stan oczekiwania na event Sprintu 128.

## 19. Timeout transmisji

Dodać diagnostyczne pole:

* `transmission_started_at`,
* `transmission_expected_by`.

Jeżeli cykl długo pozostaje `transmitting` bez utworzonego GhostSignalu:

* health check zgłasza błąd,
* operator może wznowić proces na podstawie istniejącego lock snapshotu,
* nie wykonuje ponownej blokady.

## 20. Recovery blokady

Dodać:

`recover_locked_cycle(cycle_id)`

Możliwe przypadki:

### Status `transmitting`, snapshot istnieje

Proces może przejść do Sprintu 128.

### Status `transmitting`, snapshotu brak

Błąd krytyczny integralności. Nie generować snapshotu z późniejszego stanu bez jawnej procedury recovery.

### Snapshot istnieje, status nadal `active`

Błąd częściowej migracji. Recovery ustala, czy lock został faktycznie zatwierdzony na podstawie eventu i wersji.

### Dwa snapshoty

Błąd krytyczny unikalności.

## 21. Health check closure

Sprawdza:

* `20/20` bez locku,
* lock bez `20/20`,
* transmitting bez snapshotu,
* snapshot o błędnym checksumie,
* dwa lock snapshoty,
* snapshot z 19 częściami,
* nieaktywną część w snapshotcie,
* niepełne połączenie,
* brak closing operatora,
* istniejący GhostSignal przed lockiem.

## Testy Sprintu 127

Minimum:

* 19 aktywnych części — brak locku,
* 20 aktywnych, jedna contested — brak locku,
* 20 aktywnych, 19 pełnych połączeń — brak locku,
* cztery maszyny online,
* poprawny zamknięty obwód,
* aktywacja ostatniej części uruchamia próbę,
* atomowe `active → transmitting`,
* snapshot zawiera 20 części,
* snapshot zawiera 20 połączeń,
* zapis operatora domykającego,
* dwie równoległe próby tworzą jeden lock,
* konflikt zatwierdzony przed lockiem blokuje zamknięcie,
* lock zatwierdzony przed konfliktem pozostaje ważny,
* po locku nie można zmienić części,
* po locku nie można utworzyć rezerwacji,
* błąd delty nie cofa locku,
* recovery z istniejącego snapshotu,
* wykrycie transmitting bez snapshotu,
* poprawny checksum lock snapshotu.

## Poza sprintem

Nie implementować:

* utworzenia GhostSignalu,
* końcowych nagród,
* animacji transmisji,
* błysku i czarnego ekranu,
* zużywania części,
* zmiany wersji,
* restartu,
* stabilizacji kolejnego cyklu.

## DoD

Sprint jest zakończony, gdy backend potrafi jednoznacznie potwierdzić pełne `20/20`, atomowo zamrozić cały stan strategiczny i utworzyć niezmienny snapshot, którego nie może już zmienić żaden atak, konflikt ani późniejsza operacja.

## Realizacja Sprintu 127

Wdrożono backendowy kontrakt domknięcia cyklu:

* `GhostNetworkClosureService`;
* readiness check pełnej sieci `20/20`;
* atomowe przejście `active -> transmitting`;
* tabelę `ghost_cycle_lock_snapshots`;
* walidację lock snapshotu przez checksum;
* event `ghost.cycle_locked`;
* fasadę closure w `GhostNetworkService`;
* testy regresyjne `tests.test_ghostnetwork_closure`;
* artefakt `doc/sprint_127_ghostnetwork_closure.md`.

Status `transmitting` w Sprint 127 oznacza wyłącznie zamrożenie cyklu i
oczekiwanie na Sprint 128. Nie utworzono jeszcze GhostSignalu, nie przyznano
końcowych nagród, nie zużyto części i nie zmieniono wersji GhostSystemu.

Spójność sprawdzono względem `doc/clans_machines.md`,
`doc/ghostnetwork_architecture.md` oraz sprintów 110-126.




GhostNetwork — transmisja GhostSignalu i restart systemu
GhostNetwork — BlackNet, Cyberner, Radio i narracyjny outbox
GhostNetwork — archiwum, testy końcowe i uruchomienie endgame


Po Sprintach 128–130 GhostNetwork jest kompletną pętlą endgame: gracze budują sieć, wysyłają niesyntetyczny sygnał do 2108 roku, GhostSystem ewoluuje, historia zostaje zachowana, a świat automatycznie przygotowuje kolejny cykl.


# Sprint 128 — GhostNetwork: transmisja GhostSignalu i restart systemu

Cel sprintu

Na podstawie niezmiennego snapshotu blokady ze Sprintu 127:

utworzyć rekord GhostSignalu,
przyznać końcowe nagrody,
zużyć wszystkie 20 części,
usunąć aktywne połączenia,
wyłączyć supermoce,
zwiększyć wersję GhostSystemu,
wymusić restart klientów,
rozpocząć 15-minutową stabilizację przed kolejnym cyklem.

Frontend odtwarza wydarzenie, ale nie rozstrzyga, czy transmisja została wykonana. Źródłem prawdy pozostaje backend i trwały rekord sygnału.

1. Serwis transmisji

Dodać:

GhostTransmissionService

Minimalny kontrakt:

start_transmission(cycle_id)
create_signal_from_lock(lock_snapshot)
apply_transmission_rewards(signal_id)
consume_cycle_parts(signal_id)
advance_ghostsystem_version(signal_id)
begin_stabilization(signal_id)
resume_interrupted_transmission(cycle_id)
validate_transmission(cycle_id)

Żaden endpoint ani frontend nie może samodzielnie tworzyć rekordu GhostSignalu.

2. Warunek wejścia

Transmisję można rozpocząć wyłącznie, gdy:

cykl ma status transmitting,
istnieje jeden poprawny lock snapshot,
snapshot ma 20 aktywnych części,
snapshot ma 20 aktywnych połączeń,
wszystkie cztery maszyny są online,
checksum snapshotu jest poprawny,
nie istnieje jeszcze GhostSignal tego cyklu.

Jeżeli warunki nie są spełnione, transmisja nie może budować stanu na podstawie aktualnych danych świata.

3. Rekord GhostSignalu

Utworzyć wpis ghost_signals:

signal_id
signal_number
cycle_id
source_version
target_year = 2108
status = sent
outcome = pending
integrity = null
recipient = null
sent_at
resolved_at = null
next_version
lock_snapshot_id
signal_checksum

Numer sygnału musi pochodzić z cyklu, a nie z liczby istniejących rekordów.

Początkowy rezultat zawsze pozostaje nierozstrzygnięty:

STATUS: WYSŁANY

POTWIERDZENIE Z 2108: OCZEKIWANIE

Dalszy los sygnału będzie osobnym wydarzeniem narracyjnym i nie wpływa na już przyznane nagrody.

4. Idempotencja transmisji

Stabilny klucz:

ghost-signal:<cycle_id>

Ponowne wywołanie:

zwraca istniejący sygnał,
nie tworzy kolejnego numeru,
nie przyznaje ponownie nagród,
nie zużywa ponownie części,
nie zwiększa drugi raz wersji systemu.

Repozytorium musi posiadać ograniczenie: jeden sygnał na cykl.

5. Atomowa sekwencja backendowa

Kolejność:

Zablokować cykl i lock snapshot.
Potwierdzić brak sygnału.
Utworzyć ghost_signals.
Zamrozić końcowy wkład graczy i klanów.
Utworzyć końcowe wpisy reward ledgeru.
Oznaczyć wszystkie 20 części jako consumed.
Wyłączyć aktywne supermoce.
Zamknąć aktywne połączenia.
Zapisać historyczne węzły.
Podnieść wersję GhostSystemu.
Ustawić restart_required.
Przejść do stabilizing.
Ustawić stabilization_until.
Zapisać zdarzenia domenowe.
Zatwierdzić transakcję.

Nie musi to być jedna ogromna transakcja techniczna, jeżeli magazyn na to nie pozwala, ale każda faza musi mieć trwały checkpoint i bezpieczne wznowienie.

6. Końcowe nagrody

Na podstawie lock snapshotu przyznać:

nagrodę właścicielom 20 aktywnych węzłów,
wkład klanom,
premię za utrzymanie części do transmisji,
osiągnięcie uczestnika GhostSignalu,
wyróżnienie operatora domykającego,
trwały wpis do historii gracza.

Reward keys:

ghost-signal:<signal_id>:node:<part_id>:<player_id>

ghost-signal:<signal_id>:closer:<player_id>

Operator domykający otrzymuje prestiżowy bonus, ale nie nagrodę porównywalną z sumą pracy pozostałych właścicieli.

7. Zużycie części

Po trwałym utworzeniu GhostSignalu wszystkie części przechodzą:

active → consumed

Zapisać:

consumed_at
consumed_by_signal_id
końcowego właściciela,
czas aktywności,
liczbę obron,
dane archiwalne.

Nie usuwać rekordów części z bazy.

Z aktywnego świata znikają:

markery części,
badge komponentów,
pełne i połowiczne linie,
aktywne moduły,
supermoce.

Terytoria pozostają bez zmian.

8. Historyczne ślady węzłów

Dodać rekord historycznej kotwicy, na przykład:

ghost_historical_nodes

Każdy zapis:

signal_id
part_id
part_code
współrzędne,
odkrywca,
właściciel podczas transmisji,
klan,
czas aktywności,
obrony,
aktywacje i odbicia,
status spent.

Historyczny ślad nie daje żadnego efektu gameplayowego.

9. Wyłączenie supermocy

Po ghost.part_consumed:

pasywne efekty znikają,
nowe aktywacje mocy są blokowane,
aktywne instancje kończą się zgodnie z ich polityką,
cache uprawnień jest unieważniany.

Nie czekać z wyłączeniem mocy na restart przeglądarki.

10. Zmiana wersji GhostSystemu

Dla standardowej transmisji:

1.0.N → 1.0.N+1

Zapisać:

source_version
next_version
version_changed_at
version_change_reason = ghostsignal_transmission
signal_id

Numer GhostSignalu i wersja systemu pozostają osobne.

11. Restart wymagany

Dodać globalny stan:

restart_required
restart_reason
restart_signal_id
restart_from_version
restart_to_version
restart_required_at

Każdy aktywny klient otrzymuje:

ghost.restart_required

Od tego momentu:

interfejs desktopu zostaje zablokowany,
nie można rozpoczynać nowych operacji,
mapa kończy animację transmisji i przechodzi w czarny ekran,
użytkownik widzi przycisk restartu.

Nie wykonywać automatycznego przeładowania bez działania gracza.

12. Sekwencja frontendowa transmisji

Po ghost.signal_sent uruchomić około 25–35 sekund animacji:

Domknięcie dwóch ostatnich odcinków.
Impuls przechodzący po pełnym pierścieniu.
Wspólny puls 20 węzłów.
Tymczasowe linie synchronizacyjne czterech maszyn.
Komunikaty Oracle, Libertas, Phantom Veil i Aegis.
Numer GhostSignalu.
Globalny błysk.
TRANSMISSION SENT.
Czarny ekran.
Komunikaty aktualizacji i restartu.

Animacja korzysta z zatwierdzonego signal_id i signal_number.

Nie może zostać uruchomiona wyłącznie dlatego, że frontend sam policzył 20/20.

13. Zachowanie radia i audio

Sama mapa nie uruchamia dźwięku.

Jeżeli radio jest aktywne, Sprint 129 może na krótko przerwać kanał zatwierdzonym komunikatem.

Jeżeli radio jest wyłączone lub wyciszone, transmisja pozostaje wizualna.

14. Czarny ekran i blokada

Po błysku ukryć:

mapę,
markery,
terytoria,
menu,
aktywne kontrolki.

Wyświetlać kolejno:

numer GhostSignalu,
status wysłania,
brak potwierdzenia,
zużywanie węzłów,
czyszczenie kotwic,
zapis historii,
aktualizację wersji,
wymagany restart.

Stan czarnego ekranu musi przetrwać odświeżenie strony, jeśli gracz jeszcze nie wykonał restartu.

15. Restart GhostSystemu

Przycisk:

RESTART GHOSTSYSTEM

Uruchamia istniejącą sekwencję bootowania z komunikatami:

montowanie ghost bus,
odczyt nowej wersji,
czyszczenie zużytych komponentów,
przywracanie własności terytoriów,
ładowanie nagród,
oczekiwanie na następny cykl.

Po restarcie:

klient zapisuje potwierdzenie wersji,
restart_required znika dla tego gracza,
pulpit działa normalnie,
mapa nie pokazuje starych aktywnych części,
dostępne jest podsumowanie transmisji.

Gracz offline przechodzi tę samą sekwencję przy następnym logowaniu.

16. Stabilizacja

Po transmisji cykl ma status:

stabilizing

Domyślne okno:

15 minut

W tym czasie:

zwykły gameplay działa,
mapa i narzędzia działają,
można hackować cele,
nie można rezerwować ani emitować nowych części,
media publikują podsumowanie,
system przygotowuje nowy cykl.

Po czasie stabilizacji kolejny sprint cyklu może utworzyć następny zestaw i przejść do active.

17. Zdarzenia

Zapisać i opublikować:

ghost.signal_created
ghost.signal_sent
ghost.parts_consumed
ghost.abilities_disabled
ghost.version_changed
ghost.restart_required
ghost.stabilization_started
ghost.player_restart_confirmed

Każde zdarzenie posiada signal_id, cycle_id i state_version.

18. Recovery transmisji

Proces musi rozpoznawać checkpointy:

lock istnieje, sygnału brak,
sygnał istnieje, nagrody niepełne,
nagrody gotowe, części niezużyte,
części zużyte, wersja niezmieniona,
wersja zmieniona, brak restart flag,
restart flag istnieje, cykl nie jest stabilizing.

resume_interrupted_transmission() wykonuje wyłącznie brakujące fazy.

Nie tworzy nowego GhostSignalu.

19. Health check

Sprawdza:

dwa sygnały dla cyklu,
signal bez lock snapshotu,
sygnał z innym numerem niż cykl,
sent przy aktywnych częściach,
consumed części bez signal_id,
zmienioną wersję bez sygnału,
restart wymagany z błędną wersją,
stabilizing bez stabilization_until,
końcowe nagrody bez wpisów ledgeru.
Testy Sprintu 128

Minimum:

poprawna transmisja 20/20,
jeden sygnał na cykl,
retry jest idempotentny,
końcowe nagrody dokładnie raz,
wszystkie części consumed,
terytoria pozostają,
supermoce znikają,
wersja rośnie dokładnie raz,
restart wymagany dla aktywnego gracza,
restart wymagany przy kolejnym logowaniu,
animacja nie jest źródłem prawdy,
błąd klienta nie cofa transmisji,
recovery z każdego checkpointu,
zwykłe hackowanie podczas stabilizacji,
brak nowych dropów podczas stabilizacji,
brak cofania nagród po późniejszym negatywnym wyniku sygnału.
Poza sprintem

Nie implementować jeszcze:

wyboru rezultatu GhostSignalu,
odpowiedzi z 2108,
pełnych publikacji medialnych,
finalnego archiwum gracza,
kolejnego aktywnego cyklu po stabilizacji, jeśli wymaga osobnego initializer flow.
DoD

Sprint jest zakończony, gdy zablokowany cykl może bezpiecznie i dokładnie raz wysłać GhostSignal, zużyć strategiczny stan świata, podnieść wersję GhostSystemu oraz przeprowadzić każdego gracza przez wymagany restart.

# Sprint 129 — GhostNetwork: BlackNet, Cyberner, Radio i narracyjny outbox

Cel sprintu

Podłączyć GhostNetwork do istniejących mediów tak, aby istotne wydarzenia strategiczne stawały się częścią żywego świata, ale bez ujawniania ukrytych danych i bez oddawania narracji kontroli nad mechaniką.

Backend tworzy fakty. Media renderują komunikaty. Ollama może później rozwinąć narrację, lecz nie może zmieniać stanu gry.

1. Narracyjny publisher

Dodać:

GhostNarrativePublisher

Minimalny kontrakt:

publish_domain_event(event)
build_facts(event, audience)
enqueue_blacknet(...)
enqueue_cyberner(...)
enqueue_radio(...)
enqueue_ollama_outbox(...)
retry_failed_publications(...)

Publisher nie odczytuje pełnych profili ani całej bazy świata.

Korzysta z:

zdarzenia domenowego,
projekcji widoczności,
katalogu GhostNetwork,
zatwierdzonego snapshotu.
2. Jedno źródło faktów

Dla każdego wydarzenia powstaje zestaw zatwierdzonych faktów, na przykład:

part_discovered
part_contained
part_activated
part_revealed
part_recovered
part_defended
machine_online
connection_completed
cycle_locked
signal_sent
version_changed
stabilization_started

Każdy fakt:

ma fact_id,
wskazuje źródłowy event_id,
posiada cycle_id,
ma zakres odbiorców,
posiada klasę prawdziwości,
nie zawiera danych niedozwolonych dla odbiorcy.
3. Klasy prawdziwości

Wspierane:

canonical
interpretation
rumor
propaganda
narrative_deception

Fakty mechaniczne są canonical.

Ollama nie może sama zmienić klasy na bardziej wiarygodną.

Treść mechaniczna i komentarz narracyjny muszą pozostać rozdzielone.

4. BlackNet deterministyczny

Dodać reguły sygnałów dla:

Odkrycia publicznej części

Pokazać:

nazwę części,
klan,
lokalizację,
status neutralny.
Zabezpieczenia przez obcy klan

Pokazać publicznie:

terytorium przechowuje komponent,
właściciela lub klan blokujący, jeśli publiczny,
status nieaktywny.

Nie pokazywać:

nazwy części,
właściwego klanu części,
profesji,
mocy.
Aktywacji

Właściwy klan może otrzymać pełny sygnał.

Pozostali:

klan aktywujący,
lokalizacja,
aktywny węzeł,
zaszyfrowany typ modułu.
Maszyny online

Pokazać postęp:

maszyna,
5/5,
wpływ na sieć.

Zakres danych zależy od odbiorcy.

Transmisji

BlackNet przechodzi w specjalny tryb:

GHOSTNETWORK // 20 WĘZŁÓW

POŁĄCZENIE ZAMKNIĘTE

TRANSMISJA W TOKU

Po restarcie:

GHOSTSIGNAL XXXX

WYSŁANY DO 2108

STATUS: BRAK POTWIERDZENIA

5. BlackNet CTA

Dozwolone CTA:

pokaż publiczną część na mapie,
pokaż aktywny węzeł,
pokaż strategiczne terytorium,
otwórz GhostNetwork Suite,
otwórz archiwum sygnału,
otwórz kanał Cybernera,
uruchom zatwierdzony podcast.

CTA nie może:

teleportować bez potwierdzenia,
przejmować części,
ustawiać właściciela,
przyznawać nagród,
uruchamiać mocy.
6. Cyberner globalny

Publikować komunikaty systemowe:

Pierwsze odkrycie części w cyklu

Krótki komunikat globalny.

Pierwsze połączenie

ANOMALIA GHOSTNETWORK

DWA WĘZŁY UZYSKAŁY POŁĄCZENIE

Domknięcie sieci

Przypięty komunikat:

GHOSTNETWORK XXXX ZAMKNIĘTY

TRANSMISJA DO 2108 ROZPOCZĘTA

Po wysłaniu

GHOSTSIGNAL XXXX WYSŁANY

GHOSTSYSTEM [wersja] OCZEKUJE NA RESTART

Wiadomości graczy nadal działają. Komunikat systemowy nie blokuje kanału.

7. Cyberner klanowy

Właściwy klan może otrzymać pełne informacje o aktywnej części:

nazwa,
profesja,
moc,
właściciel,
połączenia,
stan maszyny.

Właściciel blokującego terytorium może otrzymać prywatną wiadomość z pełną tożsamością obcej części.

Inni członkowie jego klanu nie otrzymują automatycznie danych owner-only.

8. Radio

Radio reaguje wyłącznie, gdy jest uruchomione.

Przy transmisji:

zapamiętać kanał i stan odtwarzania,
przerwać materiał krótkim alarmem,
odtworzyć zatwierdzony komunikat,
wrócić do poprzedniego kanału i miejsca odtwarzania.

Jeżeli radio jest:

wyłączone,
zatrzymane,
wyciszone,

nie uruchamiać dźwięku automatycznie.

9. Komunikaty radiowe

Na początku można użyć krótkich, deterministycznych nagrań lub istniejącego TTS pipeline.

Przykładowe wydarzenia:

pierwsza część cyklu,
pierwsza kompletna maszyna,
wielogodzinna obrona,
ostatni brakujący węzeł,
GhostSignal wysłany,
późniejsza odpowiedź z 2108.

Nie tworzyć audycji dla każdego drobnego eventu.

10. Narracyjny outbox

Wykorzystać ghost_narrative_outbox.

Minimalne pola:

outbox_id
event_id
cycle_id
signal_id
audience_scope
audience_clan
audience_owner
medium
truth_class
facts_json
allowed_actions_json
canon_version
ghostsystem_version
status
created_at
processed_at
validation_json

Statusy:

created
ready
processing
processed
failed
expired
archived
11. Bezpieczne fakty dla Ollamy

Ollama nie otrzymuje:

pełnych profili,
haseł,
maili,
sesji,
ukrytych części,
pełnej topologii, jeśli nie jest publiczna,
danych owner-only w publikacji globalnej,
możliwości zapisania stanu gry.

Pakiet zawiera tylko fakty potrzebne do konkretnego zadania.

Najbezpieczniejsza zasada: model nie dostaje danych, których nie wolno mu opublikować dla wskazanego odbiorcy.

12. Kontrakt wejściowy narracji

Pakiet może zawierać:

task_id
canon_version
ghostsystem_version
cycle_id
signal_id
medium
zakres odbiorców,
typ wydarzenia,
zatwierdzone fakty,
ostatnie publikacje wątku,
reguły redakcyjne,
dozwolone CTA,
limity długości.

Nie przekazywać surowych rekordów bazowych.

13. Wynik modelu

Model zwraca ustrukturyzowany JSON:

content_id
medium
audience
source
truth_class
title
body
tone
fact_refs
cta_action
cta_payload
expires_at

Nie publikować surowego tekstu bez walidacji.

14. Walidacja narracji

Sprawdzić:

strukturę,
dozwolone fact_refs,
zgodność odbiorców,
klasę prawdziwości,
ukryte dane,
CTA,
identyfikatory,
długości,
brak zewnętrznych URL,
brak nowych części i encji,
brak mechanicznych twierdzeń nieobecnych w faktach.

Błędna odpowiedź zostaje odrzucona i nie wpływa na grę.

15. Głosy klanów i MASA

Dodać wersjonowane reguły stylu:

VIREX — aktywa, ryzyko, przepływy, kontrola,
Echo Wolności — prawda, ujawnienie, mobilizacja,
Siatka Widmo — zakłócenia, sprzeczności, niedopowiedzenia,
Strażnicy Ładu — procedury, integralność, stabilność,
MASA — spokojny, opiekuńczy, pozornie racjonalny ton.

Reguły stylu nie mogą zmieniać faktów mechanicznych.

16. Ciągłość wątków

Dodać narrative_thread_id, na przykład:

ghost-cycle-0047
virex-blockade-<part>
signal-reply-0047
masa-counter-signal-12

Outbox może przekazywać:

skrót dotychczasowej historii,
nierozwiązane pytania,
ostatnie publikacje.

Nie potrzebuje pełnej historii świata.

17. Retry i niezależność mechaniki

Błąd:

BlackNetu,
Cybernera,
Radia,
Ollamy

nie może cofnąć:

aktywacji części,
nagrody,
zamknięcia sieci,
transmisji,
zmiany wersji.

Publikacje posiadają retry i niezależne statusy.

18. Obserwowalność

Logować:

event źródłowy,
zakres odbiorcy,
medium,
fact_refs,
wynik projekcji,
status outboxa,
walidację Ollamy,
publikację,
odrzucenie,
czas przetwarzania.
Testy Sprintu 129

Minimum:

publiczne odkrycie pełnej neutralnej części,
ukryta blokowana część bez przecieku,
pełna wiadomość owner-only,
pełna aktywna część dla klanu,
zaszyfrowana aktywna część dla innych,
BlackNet po zamknięciu,
Cyberner globalny,
Cyberner klanowy,
radio aktywne wraca do kanału,
radio wyłączone nie startuje,
outbox zawiera wyłącznie dozwolone fakty,
Ollama nie może dodać części,
niedozwolone CTA zostaje odrzucone,
błędny model nie wpływa na gameplay,
retry publikacji nie duplikuje wiadomości,
mechanika działa przy całkowicie wyłączonej Ollamie.
DoD

Sprint jest zakończony, gdy wszystkie istotne wydarzenia GhostNetwork mają bezpieczny i spójny głos w istniejących mediach, a narracja nigdy nie otrzymuje prawa do zmiany stanu świata.

# Sprint 130 — GhostNetwork: archiwum, testy końcowe i uruchomienie endgame

Cel sprintu

Domknąć pierwszy produkcyjny etap GhostNetwork:

stworzyć trwałe archiwum cykli i sygnałów,
udostępnić historię graczom,
przeprowadzić pełne testy integracyjne i wydajnościowe,
przygotować migracje i recovery,
uruchomić endgame etapami,
potwierdzić, że zwykły gameplay działa również przy wyłączonym GhostNetwork.
1. Archiwum GhostSignali

Dodać publiczny i prywatny odczyt archiwum.

Lista:

numer sygnału,
wersja przed i po transmisji,
data,
początkowy status,
późniejszy outcome,
integralność,
odbiorca, jeśli ujawniony,
udział klanów,
liczba uczestników.

Przykład:

0047 // DOSTARCZONY
0048 // PRZECHWYCONY
0049 // USZKODZONY 43%
0050 // ZMODYFIKOWANY
0051 // BRAK ODPOWIEDZI

Sprint nie musi jeszcze automatycznie rozstrzygać późniejszego outcome, ale archiwum musi być gotowe na jego zmianę.

2. Szczegóły sygnału

Widok sygnału może pokazywać:

20 historycznych części,
odkrywców,
właścicieli transmisyjnych,
aktywatorów,
czas utrzymania,
obrony,
odbicia,
operatora domykającego,
procentowy udział klanów,
wersję katalogu,
wersję GhostSystemu,
późniejsze konsekwencje.

Po zakończeniu cyklu nazwy dawnych części mogą być publiczne.

3. Historia osobista gracza

Profil otrzymuje sekcję:

udział w GhostSignalach,
odkryte części,
aktywowane moduły,
odbicia,
obrony,
aktywne godziny węzłów,
operator domykający,
GhostNetwork RSP,
osiągnięcia.

Nie ładować pełnej historii każdego sygnału przy zwykłym odczycie profilu.

Używać lekkiego agregatu i osobnego endpointu szczegółów.

4. Historia klanów

Dodać:

całkowitą reputację,
liczbę sygnałów,
części odkryte,
części aktywowane,
odbicia,
obrony,
utrzymane węzły,
najlepsze cykle,
procent udziału w kolejnych transmisjach.

Ranking nie wskazuje jedynego zwycięzcy cyklu, ponieważ wszystkie klany są wymagane do wysłania sygnału.

5. Historyczna warstwa mapy

Dodać opcjonalną warstwę:

Historia GhostNetwork

Zasady:

domyślnie wyłączona albo subtelna,
widoczna przy odpowiednim zoomie,
najnowszy sygnał wyróżniony,
starsze węzły uproszczone,
brak aktywnych efektów,
brak kolizji z bieżącymi częściami.

Kliknięcie historycznego węzła otwiera jego wpis archiwalny.

6. Osiągnięcia

Minimum:

Pierwszy Kontakt
Kotwica
Moduł Online
Odzyskany Fragment
Nieprzerwany Węzeł
Linia Obrony
Operator Sygnału
Ostatni Obwód
Weteran GhostSystemu

Każde osiągnięcie:

ma stabilny kod,
jest idempotentne,
wskazuje źródłowy cykl lub sygnał,
nie jest odbierane po utracie części.
7. Kolejny cykl

Po stabilization_until:

zakończyć poprzedni cykl jako closed,
utworzyć kolejny cykl,
utworzyć 20 nowych instancji części,
wygenerować topologię,
zachować historię poprzedniego cyklu,
aktywować dropy,
opublikować ghost.cycle_activated.

Nowy zestaw nie może korzystać ze starych rezerwacji ani aktywnych części.

Terytoria pozostają.

8. Feature flags

Dodać niezależne flagi:

GHOSTNETWORK_ENABLED
GHOSTNETWORK_DROPS_ENABLED
GHOSTNETWORK_MAP_LAYER_ENABLED
GHOSTNETWORK_ABILITIES_ENABLED
GHOSTNETWORK_REWARDS_ENABLED
GHOSTNETWORK_TRANSMISSION_ENABLED
GHOSTNETWORK_MEDIA_ENABLED
GHOSTNETWORK_OLLAMA_ENABLED

Pozwala to uruchamiać warstwy etapami bez wyłączania całej gry.

9. Tryb shadow

Pierwszy etap produkcyjny:

cykl istnieje,
rezerwacje i symulowane dropy są logowane,
części nie są jeszcze emitowane publicznie,
system porównuje oczekiwane hooki i wydajność,
zwykły gameplay pozostaje bez zmian.

Shadow mode ma własne logi i nie przyznaje RSP.

10. Tryb dev/staging

Narzędzia testowe:

wymuszenie rezerwacji,
wymuszenie odkrycia,
ustawienie stanu części,
przypisanie części do klastra,
symulacja konfliktu,
ustawienie 19/20,
aktywacja ostatniego modułu,
test transmisji bez realnych nagród,
czyszczenie testowego cyklu.

Każda akcja jest dostępna wyłącznie w dev/staging i oznaczona w audycie.

11. Migracje

Przygotować:

utworzenie tabel,
indeksy,
ograniczenia unikalności,
inicjalizację wersji,
utworzenie pierwszego cyklu,
backfill klanów i profesji,
rollback migracji bez utraty profili,
backup przed uruchomieniem.

Nie tworzyć aktywnego cyklu automatycznie podczas samego importu modułu.

12. Test pełnego gameplayu

Scenariusz end-to-end:

Gracz wybiera klan i profesję.
Oznacza kwalifikujący cel.
Powstaje niewidoczna rezerwacja.
Skuteczny hack emituje część obcego klanu.
Część pojawia się publicznie.
Gracz otacza ją obcym terytorium.
Część zostaje zablokowana.
Właściwy klan odbija lokalizację.
Część zostaje aktywowana.
Profesja otrzymuje moc.
Linie aktualizują się.
Powstaje obrona i odbicie.
Wkład i RSP naliczają się raz.
Ostatni moduł zamyka sieć.
Powstaje lock snapshot.
GhostSignal zostaje wysłany.
Części zostają zużyte.
Wersja systemu rośnie.
Klient wykonuje restart.
Po stabilizacji powstaje kolejny cykl.
13. Testy współbieżności

Obowiązkowo:

równoległe oznaczenie wielu celów,
dwa hacki tej samej rezerwacji,
równoczesna emisja ostatnich części,
konflikt i aktywacja w tej samej chwili,
dwa triggery 20/20,
retry transmisji,
reward retry,
równoległy restart klientów,
utworzenie kolejnego cyklu przez dwa procesy.
14. Testy widoczności

Dla każdego stanu:

neutralny,
blocked owner,
blocked foreign,
active clan,
active foreign,
contested,
consumed/history.

Sprawdzić serializowany JSON, DOM mapy, BlackNet, Cyberner, outbox i GhostNetwork Suite.

Ukryte dane nie mogą pojawić się nawet w niewidocznym atrybucie HTML.

15. Testy wydajności

Mierzyć:

czas oznaczenia celu z hookiem,
czas rezerwacji,
czas emisji,
czas eventu terytorialnego,
czas snapshotu mapy,
czas snapshotu suite,
rozmiar delt,
czas recovery,
czas locku,
czas transmisji backendowej.

Wymagania:

brak pełnego profilu przy zmianie części,
brak skanowania wszystkich profili,
brak przeliczania wszystkich terytoriów,
brak ciężkiego pollera,
maksymalnie 20 części i 20 połączeń w aktywnym cyklu.
16. Chaos i awarie

Testować restart serwera:

po rezerwacji,
podczas emisji,
podczas zmiany terytorium,
podczas rewardu,
po locku,
podczas tworzenia signal,
po zużyciu części,
przed zmianą wersji,
podczas stabilizacji.

System musi wznowić proces bez duplikacji.

17. Obserwowalność

Dashboard diagnostyczny lub raport:

aktywny cykl,
części według statusu,
rezerwacje,
odkryte części,
maszyny,
połączenia,
konflikty,
pending rewardy,
publikacje medialne,
recovery,
ostatni signal,
stabilizacja,
błędy integralności.

Nie wystawiać pełnego raportu zwykłym graczom.

18. Runbook administracyjny

Dokument:

docs/ghostnetwork/GHOSTNETWORK_RUNBOOK.md

Powinien opisywać:

uruchomienie,
wyłączenie flag,
health check,
recovery,
transmisję przerwaną,
niespójną część,
uszkodzoną topologię,
duplikat rewardu,
problem z widocznością,
wyłączenie Ollamy,
rollback feature flag,
backup i przywrócenie.

Administrator nie może ręcznie uwalniać części tylko dlatego, że gracze zablokowali cykl strategicznie.

19. Kryteria uruchomienia produkcyjnego

Przed pełnym włączeniem:

wszystkie migracje przechodzą,
health check jest zielony,
pełne E2E przechodzi,
brak przecieków widoczności,
shadow mode nie wykazuje brakujących hooków,
transmisja jest idempotentna,
rewards są idempotentne,
recovery działa na każdym checkpointcie,
mapa działa przy wyłączonym module,
zwykłe operacje nie są spowolnione ponad ustalony budżet.
20. Etapowe wdrożenie

Proponowana kolejność:

Fundament i cykl bez dropów.
Shadow reservations.
Publiczne części bez supermocy.
Terytoria i połączenia.
Nagrody.
Supermoce.
Media.
Pierwsza kontrolowana transmisja.
Automatyczny kolejny cykl.
Pełne endgame.
21. Rollback

Wyłączenie feature flag nie może usuwać danych.

Przy awaryjnym wyłączeniu:

części pozostają w bazie,
cykl zostaje zamrożony,
rezerwacje nie powstają,
istniejące terytoria działają,
zwykły gameplay działa,
po ponownym włączeniu GhostNetwork wykonuje recovery.
22. DoD Sprintu 130

Sprint jest zakończony, gdy:

Każdy cykl i sygnał posiada trwałe archiwum.
Gracze widzą swój wkład i osiągnięcia.
Klany posiadają historię reputacji.
Historyczne węzły można obejrzeć bez wpływu na gameplay.
Pełny scenariusz end-to-end przechodzi.
Testy współbieżności nie tworzą duplikatów.
Testy widoczności nie wykazują przecieków.
Recovery działa po przerwaniu każdej krytycznej fazy.
System można uruchomić etapami i bezpiecznie wyłączyć.
Zwykła gra działa nawet przy całkowicie wyłączonym GhostNetwork.
Pierwszy produkcyjny cykl może zostać rozpoczęty świadomie.
Endgame nie wymaga ręcznej ingerencji administratora w normalny przebieg strategiczny.


> Lecimy z całym desktopowym domknięciem GhostNetwork — Sprint 131 ustali bezpieczne relacje i integrację z Territory Control, 132 przygotuje lekki wspólny snapshot, 133 zbuduje właściwe listy części, 134 podepnie mapę oraz teleport, a 135 zamknie GUI, delty i regresję całej rodziny narzędzi.

# Sprint 131 — GhostNetwork Suite: audyt widoczności części i integracja z Territory Control

## Cel sprintu

Przeprowadzić audyt istniejącego GhostNetwork, Territory Control oraz wspólnej infrastruktury desktopowych `pro-system-tools`, a następnie zdefiniować kontrakt nowej aplikacji obserwacyjnej.

GhostNetwork Suite nie tworzy:

* nowego magazynu części,
* własnej klasy widoczności,
* alternatywnego systemu terytoriów,
* kopii właścicieli klastrów,
* osobnego pollera,
* własnej mechaniki teleportu.

Aplikacja jest lekką projekcją istniejącego globalnego stanu GhostNetwork i uzupełnia:

* Victim Picker,
* Territory Control,
* Operation Control.

Stan części nadal należy do GhostNetwork, kontrola obszaru do systemu terytoriów, a frontend wyświetla wyłącznie projekcję zatwierdzoną dla aktualnego operatora. 

## 1. Miejsce produktu w Ghost Control Suite

Potwierdzić wspólną rodzinę aplikacji:

```text
ghost_control_suite
```

Komponenty:

```text
Victim Picker
Territory Control
Operation Control
GhostNetwork Suite
```

Nowa aplikacja pozostaje produktem:

```text
type: pro-system-tool
category: pro-system-tools
```

Nie tworzyć nowej kategorii gameplayowej ani drugiego systemu instalacji.

Audyt ma wskazać:

* obecny kontrakt zakupu w Googleplexie,
* instalację produktu w profilu,
* launcher desktopowy,
* taskbar,
* zachowanie aktywnego okna,
* wspólny icon pack,
* mechanizm aktualizacji przez delty.

Cena produktu pozostaje konfigurowalna i nie jest ustalana w tym sprincie.

## 2. Audyt projekcji widoczności

Sprawdzić implementację ze Sprintu 120:

```text
GhostVisibilityService
```

Nowe narzędzie musi korzystać dokładnie z tych samych reguł co:

* mapa,
* Territory Control,
* BlackNet,
* Cyberner,
* narracyjny outbox.

Nie może samodzielnie wyliczać widoczności na podstawie:

```text
viewer.clan === part.clan
```

Do aplikacji trafia gotowa projekcja.

## 3. Kanoniczne grupy widoku

Ustalić pięć grup wyświetlanych w GhostNetwork Suite.

### Publiczne

Części:

```text
module_state = neutral
```

Nie są otoczone stabilnym terytorium.

Wszyscy widzą pełne dane:

* nazwę,
* klan,
* maszynę,
* profesję,
* supermoc,
* dokładną lokalizację.

### Zablokowane przez inny klan

Części znajdują się na stabilnym terytorium klanu innego niż klan części.

Dla zwykłego obserwatora:

* tożsamość może być ukryta,
* znane jest terytorium,
* znany jest stan `blocked`,
* dokładna kotwica może pozostać niewidoczna.

### Aktywne w naszym klanie

Części własnej maszyny aktywowane przez innego członka klanu.

Aktualny operator widzi pełne dane dzięki przynależności klanowej, ale nie jest właścicielem terytorium.

### Kontrolowane przeze mnie — część obca

Aktualny operator jest właścicielem klastra zawierającego część obcego klanu.

Relacja:

```text
self_foreign_blocked
```

Operator widzi pełną tożsamość komponentu, ponieważ sam go blokuje.

### Kontrolowane przeze mnie — część własna

Aktualny operator jest właścicielem klastra aktywującego część własnego klanu.

Relacja:

```text
self_own_active
```

Część jest aktywna i daje moc właściwej profesji całemu klanowi.

## 4. Brak osobnych list w bazie

Grupy są filtrami jednego snapshotu:

```text
parts[]
```

Nie tworzyć struktur:

```text
public_parts_store
blocked_parts_store
my_parts_store
clan_parts_store
```

Ta sama część może po zmianie terytorium przejść z jednej sekcji do drugiej bez zmiany swojego `part_id`.

## 5. Relacje odbiorcy

Audyt ma potwierdzić i ewentualnie uzupełnić resolver:

```text
resolve_part_viewer_relation(part, viewer)
```

Wymagane wartości:

```text
public_neutral
foreign_blocked
foreign_active
clan_own_active
self_foreign_blocked
self_own_active
```

Opcjonalnie dla spójności:

```text
self_contested
clan_contested
foreign_contested
```

Konflikt pozostaje jednak nakładką, a nie nowym stanem bazowym.

## 6. Audyt danych właściciela

Ustalić kanoniczne pola:

```text
territory_id
territory_owner_id
territory_owner_alias
territory_clan
cluster_id
cluster_label
```

Nie pobierać pełnych profili właścicieli.

Alias i klan muszą pochodzić z lekkiej projekcji przygotowanej na backendzie.

## 7. Audyt integracji z Territory Control

Territory Control ma już oznaczać klastry zawierające komponent.

Potwierdzić pola:

```text
contains_ghost_part
ghost_parts_count
ghost_part_relation
ghost_part_state
ghost_part_identity_visible
ghost_part_summary
```

Dla właściciela klastra dodatkowo:

```text
ghost_part_public_entity_id
ghost_part_name
ghost_part_clan
ghost_part_machine
ghost_part_profession
ghost_part_ability
```

Pola szczegółowe mogą wystąpić tylko wtedy, gdy pozwala na to projekcja widoczności.

## 8. Klaster z własną częścią

Territory Control pokazuje:

```text
GHOST COMPONENT
WŁASNY KLAN
STATUS: AKTYWNY
```

Jeżeli właścicielem jest aktualny operator:

```text
RELACJA: KONTROLOWANY PRZEZE MNIE
```

Jeżeli inny członek klanu:

```text
RELACJA: WĘZEŁ KLANOWY
```

## 9. Klaster z obcą częścią

Dla właściciela:

```text
GHOST COMPONENT
CZĘŚĆ OBCEGO KLANU
STATUS: BLOKOWANY
```

Dla pozostałych:

```text
TERYTORIUM ZAWIERA CZĘŚĆ GHOSTNETWORK
TOŻSAMOŚĆ: UKRYTA
STATUS: NIEAKTYWNA
```

Nie ujawniać kodu części w badge, tooltipie, DOM ani danych aplikacji.

## 10. Konflikt terytorialny

Podczas konfliktu aplikacja pokazuje stan sprzed jego rozpoczęcia:

```text
module_state: active lub blocked
conflict_state: contested
```

Pozycja otrzymuje dodatkowe oznaczenie:

```text
STAN ZAMROŻONY — KONFLIKT
```

Nie przenosić jej między grupami aż do zdarzenia stabilizacji.

Reguła odpowiada kanonowi, według którego konflikt nie zmienia natychmiast właściciela ani aktywności części. 

## 11. Audyt akcji mapy

Sprawdzić wspólny kontrakt używany już przez:

* Victim Picker,
* Territory Control,
* Operation Control.

Wymagane akcje:

```text
show_on_map
teleport
```

Obie muszą używać wspólnego bridge’a desktop–mapa.

GhostNetwork Suite nie może tworzyć własnego iframe ani alternatywnego endpointu teleportacji.

## 12. Audyt teleportu

Teleport ma prowadzić:

* do dokładnej kotwicy, jeśli odbiorca ją zna,
* do pozycji klastra lub bezpiecznego punktu terytorium, jeśli część jest ukryta,
* do aktualnej pozycji historycznej kotwicy Ghost Anchor, jeśli źródło zniknęło.

Aplikacja nie może ujawnić dokładnych współrzędnych ukrytej części przez payload teleportu.

## 13. Audyt lifecycle okna

Sprawdzić wzorce:

* instalacja produktu,
* utworzenie okna,
* jedna instancja aplikacji,
* przywracanie z taskbara,
* focus istniejącego okna,
* zamknięcie,
* wyrejestrowanie listenerów delt,
* restart GhostSystemu.

## 14. Wspólne ikony

Rozszerzyć:

```text
GHOST_CONTROL_ICONS
```

Minimalne klucze:

```text
ghostnetwork
public_part
blocked_part
active_part
self_controlled
clan_controlled
map
teleport
territory
owner
machine
profession
ability
conflict
refresh
```

Ikony inline SVG:

* posiadają `title`,
* `aria-label`,
* stany hover/focus/disabled,
* nie są anonimowymi symbolami.

## 15. Artefakt sprintu

Dokument:

```text
docs/ghostnetwork/sprint_131_suite_audit.md
```

Powinien zawierać:

* źródła danych,
* macierz widoczności,
* mapowanie grup,
* kontrakt Territory Control,
* kontrakt mapy,
* kontrakt teleportu,
* listę wykorzystywanych helperów,
* listę zabronionych duplikatów,
* plan testów 132–135.

## Testy Sprintu 131

Minimum:

* neutralna część trafia do `public_neutral`,
* blokowana część dla właściciela trafia do `self_foreign_blocked`,
* blokowana część dla obcego obserwatora trafia do `foreign_blocked`,
* aktywna część właściciela trafia do `self_own_active`,
* aktywna część członka klanu trafia do `clan_own_active`,
* konflikt nie zmienia grupy bazowej,
* ukryta tożsamość nie przechodzi do Territory Control,
* dokładna pozycja ukrytej części nie trafia do akcji mapy,
* istniejące helpery mapy i teleportu są wskazane,
* brak drugiego źródła danych.

## Poza sprintem

Nie tworzyć jeszcze:

* endpointu snapshotu,
* aplikacji GUI,
* list,
* delty,
* zakupu produktu,
* nowych akcji mapy.

## DoD

Sprint jest zakończony, gdy dokładnie wiadomo:

1. Jak części są grupowane.
2. Kto widzi ich tożsamość.
3. Jak Territory Control oznacza klastry.
4. Jakie dane otrzymuje mapa.
5. Gdzie kieruje teleport.
6. Które istniejące helpery zostaną ponownie użyte.
7. Jak uniknąć przecieku dokładnej pozycji blokowanej części.
8. Jak aplikacja wpina się w Ghost Control Suite.

---

# Sprint 132 — GhostNetwork Suite: lekki snapshot części, właścicieli i stanów terytorialnych

## Cel sprintu

Przygotować lekki backendowy snapshot przeznaczony specjalnie dla desktopowej aplikacji GhostNetwork Suite.

Snapshot ma zawierać jedynie dane potrzebne do:

* wyświetlenia list,
* określenia relacji części względem operatora,
* pokazania właściciela i klastra,
* wykonania akcji mapy oraz teleportu,
* aktualizacji przez delty.

Nie może zawierać:

* pełnej topologii,
* geometrii wszystkich terytoriów,
* rezerwacji,
* pełnego profilu,
* historii wszystkich części,
* danych ukrytych przed odbiorcą.

## 1. Widok snapshotu

Rozszerzyć istniejący endpoint:

```text
GET /api/ghostnetwork/snapshot?view=suite
```

Nie tworzyć zupełnie niezależnego magazynu ani endpointu omijającego `GhostVisibilityService`.

## 2. Kontrakt główny

Response:

```text
cycle
summary
groups
parts
state_version
visibility_version
restart_required
stabilization_until
```

`cycle` zawiera:

```text
cycle_id
signal_number
ghostsystem_version
status
```

`summary`:

```text
parts_total
parts_discovered
parts_public
parts_blocked
parts_active
parts_contested
parts_visible_to_viewer
```

## 3. Rekord części

Każda widoczna pozycja może zawierać:

```text
public_entity_id
part_id
display_label
identity_visible
module_state
conflict_state
viewer_relation
visibility_level
part_clan
machine
profession
ability
territory
owner
location
actions
updated_at
state_version
```

Ukryte pola muszą być `null` albo nieobecne.

Nie wysyłać prawdziwej wartości z dodatkowym `visible: false`.

## 4. Identyfikator aplikacyjny

Aplikacja kluczuje elementy po:

```text
public_entity_id
```

Identyfikator:

* stabilny w cyklu,
* nie zdradza `part_code`,
* działa również dla ukrytej części,
* może zostać użyty w deltach i focusie Territory Control.

## 5. Dane tożsamości

Gdy `identity_visible = true`:

```text
part_id
part_code
part_name
part_clan_code
part_clan_name
machine_code
machine_name
profession_code
profession_name
ability_code
ability_name
ability_description
```

Gdy tożsamość jest ukryta:

```text
part_id: null
part_code: null
part_name: null
machine: null
profession: null
ability: null
```

Dozwolony `display_label`:

```text
NIEZIDENTYFIKOWANY KOMPONENT
```

## 6. Dane terytorialne

Minimalny kontrakt:

```text
territory:
    territory_id
    cluster_id
    cluster_label
    owner_id
    owner_alias
    owner_clan
    threat_state
    pillar_count
    inner_count
    conflict_state
```

Nie przesyłać całej listy wierzchołków klastra.

Do listy wystarczy agregat.

## 7. Pozycja części

Kontrakt:

```text
location:
    visibility
    latitude
    longitude
    map_focus_type
    map_focus_id
```

Dozwolone wartości:

```text
visibility: exact
visibility: territory_only
```

### `exact`

Współrzędne kotwicy są dostępne.

### `territory_only`

Snapshot nie zawiera dokładnej pozycji komponentu.

Może zawierać:

* centroid klastra,
* publiczny identyfikator terytorium,
* bezpieczny punkt teleportu.

## 8. Akcje

Backend zwraca gotowe możliwości:

```text
actions:
    can_show_on_map
    can_teleport
    map_target_type
    map_target_id
    teleport_target_type
    teleport_target_id
```

Frontend nie zgaduje dostępności na podstawie stanu.

## 9. Pokaż na mapie

Dla `exact`:

```text
map_target_type: ghost_part
map_target_id: public_entity_id
```

Dla `territory_only`:

```text
map_target_type: territory
map_target_id: territory_id
```

To zapobiega ujawnieniu dokładnej kotwicy blokowanej części.

## 10. Teleport

Dla `exact` teleport może używać pozycji części.

Dla `territory_only` teleport kieruje do:

* centroidu klastra,
* dozwolonego punktu wejścia,
* publicznej kotwicy terytorium.

Backend ponownie waliduje target przy kliknięciu.

Nie ufać współrzędnym przechowywanym w DOM.

## 11. Grupy snapshotu

Backend może zwrócić gotowe grupowanie:

```text
groups:
    public
    blocked_by_other_clans
    active_in_my_clan
    self_foreign_blocked
    self_own_active
```

Każda grupa zawiera listę `public_entity_id`.

Alternatywnie frontend może filtrować po `viewer_relation`, ale jedna kanoniczna metoda grupowania powinna być współdzielona z testami.

## 12. Brak duplikatów

Jedna część występuje dokładnie raz w głównej liście `parts`.

`groups` zawiera jedynie odwołania.

Nie zwracać pięciu pełnych kopii tego samego rekordu.

## 13. Sortowanie

Backend zwraca stabilne pola sortowania:

```text
distance_from_player
owner_alias
part_clan_sort
module_state_sort
updated_at
```

Odległość liczona jest od aktualnej pozycji motocykla operatora.

Jeżeli część jest `territory_only`, odległość może być liczona do punktu klastra, nie dokładnej kotwicy.

## 14. Aktualna pozycja operatora

Snapshot może zawierać:

```text
viewer_position:
    latitude
    longitude
    updated_at
```

Nie uruchamia pełnej synchronizacji profilu.

Używa lekkiego źródła bieżącej pozycji, tego samego co Victim Picker i Territory Control.

## 15. Ghost Anchor

Dla części ze źródłem utraconym:

```text
anchor_state: source_lost
display_source: GHOST ANCHOR
```

Jej dostępność mapy i teleportu nadal zależy od projekcji.

## 16. Cykl transmitting i stabilizing

Podczas `transmitting`:

* snapshot może zwracać zamrożone 20 części,
* akcje mapy mogą być czasowo wyłączone,
* GUI pokazuje transmisję.

Po `consumed`:

* aktywna lista zostaje wyczyszczona,
* aplikacja pokazuje brak aktywnych części,
* może pokazać odnośnik do archiwum.

Podczas `stabilizing`:

* lista jest pusta,
* widoczne jest odliczanie do kolejnego cyklu.

## 17. Cache

Cache kluczowany:

```text
cycle_id
state_version
viewer_id
viewer_clan
view=suite
```

Nie mieszać snapshotów:

* właściciela,
* członka klanu,
* obcego gracza.

## 18. Rozmiar odpowiedzi

Maksymalnie 20 części.

Nie wysyłać:

* pełnej geometrii,
* event history,
* pełnych definicji katalogu,
* opisów fabularnych większych niż potrzebne w kartach.

Długie opisy supermocy mogą być opcjonalne i pobierane dopiero przy rozwinięciu szczegółów.

## 19. Endpoint punktowy

Dodać opcjonalnie:

```text
GET /api/ghostnetwork/parts/<public_entity_id>?view=suite
```

Służy do:

* punktowego odświeżenia,
* obsługi delty bez pełnego payloadu,
* ponownej walidacji przed otwarciem mapy.

Endpoint nadal stosuje projekcję widoczności.

## 20. Health check snapshotu

Sprawdza:

* duplikaty `public_entity_id`,
* część w dwóch bazowych grupach,
* `exact` bez współrzędnych,
* `territory_only` bez `territory_id`,
* ukrytą część z nazwą,
* self relation bez zgodnego właściciela,
* active clan relation bez zgodnego klanu,
* action target zdradzający ukryty `part_id`.

## Testy Sprintu 132

Minimum:

* snapshot z pustym cyklem,
* snapshot z 20 częściami,
* neutralna część z pełnymi danymi,
* blokowana część dla właściciela,
* blokowana część dla członka klanu właściciela,
* blokowana część dla właściwego klanu części,
* aktywna część własnego klanu,
* aktywna część obcego klanu,
* `self_foreign_blocked`,
* `self_own_active`,
* `territory_only` bez dokładnych współrzędnych,
* mapa wskazuje klaster zamiast kotwicy,
* teleport wskazuje klaster,
* brak pełnego profilu,
* brak geometrii terytorium,
* brak rezerwacji,
* brak duplikatów,
* cache nie przecieka między odbiorcami.

## Poza sprintem

Nie tworzyć jeszcze:

* końcowego GUI,
* paneli list,
* map bridge,
* teleport endpointu,
* delt frontendowych.

## DoD

Sprint jest zakończony, gdy desktopowa aplikacja może jednym lekkim odczytem otrzymać wszystkie części dostępne operatorowi, bez pobierania mapy, pełnego profilu i bez możliwości poznania ukrytej tożsamości albo dokładnej lokalizacji.

---

# Sprint 133 — GhostNetwork Suite: lista części publicznych, blokowanych i aktywnych

## Cel sprintu

Zbudować funkcjonalny frontend desktopowej aplikacji, który prezentuje części GhostNetwork w pięciu jednoznacznych sekcjach i pozwala operatorowi szybko zrozumieć strategiczny stan świata bez otwierania mapy.

Sprint tworzy listy oraz szczegóły, ale akcje mapy i teleportu mogą pozostać jeszcze podłączone do placeholderów kontraktowych do Sprintu 134.

## 1. Okno aplikacji

Dodać:

```text
createGhostNetworkSuite()
```

Zasady:

* tylko jedna instancja,
* ponowne uruchomienie podnosi istniejące okno,
* osobny `data-app`,
* integracja z taskbarem,
* wspólna rodzina `ghost_control_suite`.

## 2. Główny układ

Widok powinien zawierać:

* nagłówek cyklu,
* wersję GhostSystemu,
* licznik odkrytych części,
* licznik aktywnych części,
* sekcje list,
* status aktualizacji,
* przycisk lekkiego odświeżenia.

Nie odwzorowywać ciężkiej mapy ani diagramu pełnej topologii.

## 3. Nagłówek statusu

Przykład:

```text
GHOSTNETWORK // CYKL 0047

ODKRYTE: 13 / 20
AKTYWNE: 7 / 20
BLOKOWANE: 4
PUBLICZNE: 2
```

Dodatkowo:

```text
GHOSTSYSTEM 1.0.47
```

Statusy:

* aktywny,
* transmisja,
* stabilizacja,
* restart wymagany.

## 4. Nawigacja sekcji

Preferowane dwa poziomy:

### Główne filtry

```text
WSZYSTKIE
PUBLICZNE
BLOKOWANE
AKTYWNE
MOJA KONTROLA
```

### Podgrupy

W `MOJA KONTROLA`:

```text
CZĘŚCI OBCE
CZĘŚCI WŁASNE
```

Alternatywnie aplikacja może pokazywać pięć stałych sekcji w jednej przewijanej liście.

Na mobilnym układzie zakładki powinny mieścić się bez szerokich napisów, wykorzystując ikony i krótkie etykiety.

## 5. Sekcja publiczna

Nagłówek:

```text
PUBLICZNE CZĘŚCI
```

Opis:

```text
Odkryte komponenty poza stabilną kontrolą terytorium.
```

Karta pokazuje:

* nazwę,
* kod części,
* klan,
* maszynę,
* profesję,
* moc,
* odległość,
* lokalizację,
* stan neutralny.

## 6. Sekcja blokowana przez inne klany

Nagłówek:

```text
BLOKOWANE CZĘŚCI
```

Karta może być pełna albo ukryta zależnie od projekcji.

Dla ukrytej:

```text
NIEZIDENTYFIKOWANY KOMPONENT

TERYTORIUM: [nazwa]
WŁAŚCICIEL: [alias]
KLAN: [klan kontrolujący]
STATUS: BLOKOWANY
```

Nie pokazywać pustych etykiet:

```text
PROFESJA: —
MOC: —
```

Sekcja szczegółów w ogóle nie powinna ich renderować.

## 7. Sekcja aktywna w naszym klanie

Nagłówek:

```text
AKTYWNE WĘZŁY KLANU
```

Pokazuje części własnej maszyny aktywowane przez innych operatorów klanu.

Karta:

* pełna nazwa,
* właściciel,
* klaster,
* profesja,
* aktywna moc,
* czas aktywności,
* stan konfliktu,
* odległość.

Wyraźnie odróżnić:

```text
WŁAŚCICIEL: INNY OPERATOR KLANU
```

od części kontrolowanej osobiście.

## 8. Sekcja „kontrolowane przeze mnie — obce”

Nagłówek:

```text
BLOKOWANE PRZEZE MNIE
```

Karta zawiera pełne dane części:

* część,
* właściwy klan,
* maszyna,
* profesja,
* supermoc,
* własny klaster,
* czas blokady.

Stan:

```text
MODUŁ NIEAKTYWNY
```

Aplikacja nie sugeruje, że operator otrzymuje moc komponentu.

## 9. Sekcja „kontrolowane przeze mnie — własne”

Nagłówek:

```text
AKTYWNE PRZEZE MNIE
```

Karta:

* część,
* maszyna,
* profesja,
* moc,
* własny klaster,
* czas aktywności,
* liczba obron,
* stan połączeń w formie lekkiego licznika.

Stan:

```text
WĘZEŁ AKTYWNY
```

## 10. Karta części

Minimalna struktura:

```text
ikona stanu
nazwa lub bezpieczny label
klan
właściciel
terytorium
stan
odległość
konflikt
akcje
```

Nie tworzyć rozbudowanego panelu z każdą informacją na stałe.

Dodatkowe dane można otworzyć w rozwijanym szczególe.

## 11. Szczegóły części

Po rozwinięciu:

* maszyna,
* profesja,
* moc,
* odkrywca, jeśli widoczny,
* data odkrycia,
* stan kotwicy,
* właściciel,
* liczba filarów klastra,
* zagrożenie klastra,
* stan konfliktu,
* status połączeń.

Renderować wyłącznie dane obecne w snapshotcie.

## 12. Konflikt

Karta zachowuje kolor stanu bazowego i otrzymuje:

```text
KONFLIKT — STAN ZAMROŻONY
```

Nie przenosić pozycji do innej sekcji przed stabilizacją.

## 13. Puste sekcje

Zamiast pustego panelu:

```text
BRAK PUBLICZNYCH CZĘŚCI
```

```text
NIE BLOKUJESZ ŻADNEGO KOMPONENTU
```

```text
TWÓJ KLAN NIE MA AKTYWNYCH WĘZŁÓW
```

Komunikaty mają być krótkie i zgodne ze stylem GhostSystemu.

## 14. Sortowanie

Domyślne:

1. konflikt,
2. kontrolowane przeze mnie,
3. aktywne,
4. odległość,
5. nazwa.

Dostępne sortowania:

* odległość,
* stan,
* klan,
* właściciel,
* ostatnia zmiana.

Nie sortować ukrytej części po prawdziwej nazwie.

## 15. Filtrowanie

Lekki filtr tekstowy może przeszukiwać wyłącznie widoczne dane:

* nazwę,
* klan,
* właściciela,
* terytorium,
* profesję.

Nie może zwracać ukrytej części po wpisaniu jej prawdziwego kodu.

## 16. Stan ładowania

Aplikacja powinna pokazać kontekstowe logi, na przykład:

```text
SYNCHRONIZACJA GHOSTNETWORK
ODCZYT PROJEKCJI WĘZŁÓW
WERYFIKACJA ZAKRESU ODBIORCY
```

Nie ładować mapy w tle.

## 17. Stan błędu

Przy błędzie snapshotu:

* zachować ostatni widok,
* oznaczyć go jako nieaktualny,
* pokazać retry,
* nie zamykać aplikacji,
* nie otwierać mapy.

## 18. Stan transmisji

Po `cycle.status = transmitting`:

```text
GHOSTNETWORK ZAMKNIĘTY
TRANSMISJA W TOKU
```

Listy mogą zostać zamrożone.

Po zużyciu części:

```text
AKTYWNY CYKL ZAKOŃCZONY
20 WĘZŁÓW ZUŻYTYCH
```

Podczas stabilizacji:

```text
NOWY CYKL OCZEKUJE NA STABILIZACJĘ
```

## 19. Dostępność

Każda akcja:

* ma ikonę,
* `title`,
* `aria-label`,
* stan focus,
* stan disabled z wyjaśnieniem.

Kolor nie jest jedynym komunikatem stanu.

## 20. Testy Sprintu 133

Minimum:

* pięć grup list,
* jedna część tylko w jednej grupie,
* pełna publiczna karta,
* ukryta blokowana karta,
* karta aktywna klanowa,
* karta `self_foreign_blocked`,
* karta `self_own_active`,
* konflikt zachowuje sekcję,
* sortowanie po odległości,
* wyszukiwanie nie ujawnia ukrytego kodu,
* puste stany,
* transmitting,
* stabilizing,
* błąd snapshotu,
* aplikacja nie ładuje mapy,
* jedna instancja okna.

## Poza sprintem

Nie wdrażać jeszcze:

* rzeczywistego show-on-map,
* teleportu,
* finalnych delt,
* pełnej responsywności,
* integracji zakupu produktu.

## DoD

Sprint jest zakończony, gdy operator może bez mapy zobaczyć wszystkie dostępne mu części, rozróżnić elementy publiczne, blokowane, aktywne i kontrolowane osobiście oraz nie otrzymuje żadnej informacji wykraczającej poza jego projekcję.

---

# Sprint 134 — GhostNetwork Suite: mapa na żądanie, teleport i oznaczenia klastrów z komponentami

## Cel sprintu

Podłączyć do każdej pozycji dwie właściwe akcje:

* `Pokaż na mapie`,
* `Teleport`.

Jednocześnie zakończyć integrację z Territory Control tak, aby oba narzędzia korzystały z tych samych oznaczeń komponentów w klastrach.

Mapa pozostaje ładowana wyłącznie wtedy, gdy gracz jawnie wybierze akcję podglądu.

## 1. Wspólny bridge mapy

Użyć istniejącego mechanizmu:

```text
openMapAtTarget(...)
```

lub jego kanonicznego odpowiednika ustalonego w audycie.

Bridge powinien:

1. sprawdzić, czy mapa istnieje,
2. otworzyć ją tylko na żądanie,
3. poczekać na gotowość iframe,
4. wysłać bezpieczny focus target,
5. podnieść okno mapy,
6. nie zmieniać `aimed_target`.

## 2. Pokaż dokładną część

Dla:

```text
location.visibility = exact
```

akcja:

```text
show_on_map(public_entity_id)
```

Mapa:

* otwiera warstwę GhostNetwork,
* centruje część,
* podświetla marker,
* otwiera bezpieczny panel,
* nie ustawia celu hackowania.

## 3. Pokaż terytorium

Dla:

```text
location.visibility = territory_only
```

akcja otwiera:

* klaster,
* badge komponentu,
* panel terytorium.

Nie centruje ukrytej kotwicy.

Komunikat:

```text
DOKŁADNA LOKALIZACJA KOMPONENTU JEST UKRYTA
POKAZANO TERYTORIUM PRZECHOWUJĄCE CZĘŚĆ
```

## 4. Brak przecieku przez map bridge

Payload nie może zawierać:

* ukrytego `part_id`,
* prawdziwych współrzędnych,
* kodu części,
* ukrytej maszyny,
* profesji,
* mocy.

Dla ukrytej części bridge otrzymuje wyłącznie identyfikator terytorium.

## 5. Teleport do części

Dla dokładnej pozycji:

```text
teleport_target_type = ghost_part
```

Backend przed teleportem sprawdza:

* aktywny cykl,
* aktualną projekcję widoczności,
* aktualną pozycję kotwicy,
* poprawność współrzędnych,
* brak stanu restartu,
* możliwość użycia teleportu przez operatora.

Nie ufać starym współrzędnym snapshotu.

## 6. Teleport do klastra

Dla ukrytej części:

```text
teleport_target_type = territory
```

Cel:

* bezpieczny punkt klastra,
* centroid,
* dozwolona kotwica wejścia.

Nie przenosić operatora bezpośrednio na ukrytą część.

## 7. Potwierdzenie teleportu

Przed wykonaniem:

```text
TELEPORT DO WĘZŁA GHOSTNETWORK
```

lub:

```text
TELEPORT DO TERYTORIUM Z KOMPONENTEM
```

Pokazać:

* odległość,
* cel,
* typ lokalizacji,
* ostrzeżenie o konflikcie.

Przyciski:

```text
TELEPORT
ANULUJ
```

## 8. Aktualizacja motocykla

Teleport korzysta z istniejącego procesu przesuwania pozycji motocykla.

Po sukcesie:

* aktualizuje bieżącą pozycję,
* emituje istniejącą deltę pozycji,
* odświeża odległości w Victim Pickerze,
* odświeża odległości w Territory Control,
* odświeża odległości w GhostNetwork Suite,
* nie przeładowuje mapy, jeśli jest zamknięta.

## 9. Brak automatycznego ustawienia celu

Teleport ani pokazanie mapy nie może:

* ustawić `aimed_target`,
* uruchomić hacku,
* zarezerwować kolejnej części,
* rozpocząć operacji.

GhostNetwork Suite jest narzędziem obserwacyjnym i nawigacyjnym.

## 10. Territory Control — badge klastra

Karta klastra otrzymuje ikonę GhostNetwork oraz status.

Możliwe warianty:

```text
CZĘŚĆ WŁASNEGO KLANU // AKTYWNA
CZĘŚĆ OBCEGO KLANU // BLOKOWANA
KOMPONENT NIEZIDENTYFIKOWANY // BLOKOWANY
KOMPONENT // KONFLIKT
```

Badge nie zastępuje istniejącego koloru zagrożenia:

* zielony,
* pomarańczowy,
* czerwony.

## 11. Territory Control — szczegół klastra

W szczególe dodać sekcję:

```text
GHOSTNETWORK
```

Dla pełnej widoczności:

* część,
* klan,
* maszyna,
* profesja,
* moc,
* status,
* czas aktywności lub blokady.

Dla ukrytej:

```text
TERYTORIUM PRZECHOWUJE NIEZIDENTYFIKOWANY KOMPONENT
```

Nie wyświetlać pustych szczegółów.

## 12. Synchronizacja między aplikacjami

Kliknięcie klastra w Territory Control może opcjonalnie otworzyć GhostNetwork Suite i ustawić filtr na powiązaną część.

Kliknięcie części w GhostNetwork Suite może podświetlić powiązany klaster w już otwartym Territory Control.

Nie uruchamiać drugiej aplikacji automatycznie bez akcji gracza.

## 13. Ghost Anchor

`Pokaż na mapie`:

* centruje niezależną kotwicę,
* pokazuje specjalny marker.

Teleport:

* używa zachowanych współrzędnych,
* nadal ponownie je waliduje.

## 14. Konflikt

Podczas konfliktu:

* mapa pokazuje badge sporu,
* teleport jest nadal możliwy, jeśli zwykłe zasady na to pozwalają,
* potwierdzenie ostrzega o aktywnym konflikcie,
* dokładność pozycji nadal zależy od zamrożonej projekcji widoczności.

## 15. Nieistniejący już target

Jeżeli między snapshotem a kliknięciem część została:

* ukryta,
* przeniesiona technicznie,
* zużyta,
* objęta innym terytorium,

backend zwraca aktualną projekcję.

Frontend:

* aktualizuje kartę,
* nie wykonuje starej akcji,
* pokazuje czytelny komunikat.

## 16. Stany przycisków

### Pokaż na mapie

Aktywny, gdy istnieje:

* dokładna część,
* terytorium,
* historyczna kotwica.

### Teleport

Disabled, gdy:

* restart wymagany,
* brak poprawnej lokalizacji,
* stan transmisji blokuje akcje,
* bieżący system teleportu odrzuca cel.

Tooltip wyjaśnia powód.

## 17. Testy Sprintu 134

Minimum:

* mapa nie ładuje się przed kliknięciem,
* dokładna część centruje marker,
* ukryta część centruje terytorium,
* payload nie zawiera ukrytych współrzędnych,
* pokazanie mapy nie ustawia celu,
* teleport do dokładnej części,
* teleport do klastra,
* ponowna walidacja przed teleportem,
* teleport odświeża odległości wszystkich narzędzi,
* konflikt pokazuje ostrzeżenie,
* consumed część blokuje akcję,
* Ghost Anchor działa,
* badge własnej części,
* badge obcej części,
* badge ukrytej części,
* Territory Control i Suite używają tej samej projekcji.

## Poza sprintem

Nie wykonywać jeszcze:

* końcowego polishu GUI,
* pełnej obsługi delt w aplikacji,
* finalnej regresji zakupów i instalacji.

## DoD

Sprint jest zakończony, gdy każda część może bezpiecznie otworzyć właściwy punkt mapy albo terytorium, teleport nie ujawnia ukrytej kotwicy, a Territory Control jednoznacznie pokazuje, które klastry przechowują własne i obce komponenty.

---

# Sprint 135 — GhostNetwork Suite: GUI desktopowe, delty, recovery i regresja całej Ghost Control Suite

## Cel sprintu

Dokończyć produkcyjne GUI GhostNetwork Suite, podłączyć je do wspólnego klienta delt i recovery oraz przeprowadzić regresję całej rodziny czterech narzędzi.

Po tym sprincie zaawansowany operator może obsługiwać większość warstwy strategicznej z lekkiego desktopu, używając mapy tylko do świadomego podglądu przestrzennego.

## 1. Rejestr produktu

Dodać produkt do istniejącego katalogu Googleplex:

```text
type: pro-system-tool
family: ghost_control_suite
app_code: ghostnetwork_suite
```

Produkt ma:

* nazwę,
* opis,
* ikonę,
* cenę z konfiguracji,
* kontrakt instalacji,
* launcher.

Nie tworzyć osobnej procedury zakupu.

## 2. Instalacja i launcher

Po zakupie:

* produkt zapisuje się istniejącą ścieżką,
* aplikacja pojawia się na desktopie,
* launcher używa wspólnego icon packa,
* brak produktu blokuje uruchomienie,
* istniejące profile z przyznanym produktem działają po migracji.

## 3. Finalny układ GUI

Okno powinno być zwarte i czytelne.

Sekcje:

* pasek statusu cyklu,
* szybkie liczniki,
* filtry,
* lista kart,
* rozwijane szczegóły,
* pasek aktualizacji.

Nie robić ogromnej tabeli z dwudziestoma kolumnami.

## 4. Responsive desktop i mobile

Desktop:

* lista i panel szczegółów mogą działać obok siebie.

Węższe okno:

* szczegóły otwierają się pod kartą albo jako osobny ekran,
* przyciski zmieniają się w ikony,
* etykiety nie nachodzą na statusy,
* sekcje są przewijalne.

Nie skalować całego okna transformacją CSS.

## 5. Wspólny klient delt

Aplikacja rejestruje się w:

```text
GhostNetworkDeltaClient
```

Obsługiwane eventy:

* `ghost.part_discovered`
* `ghost.part_contained`
* `ghost.part_revealed`
* `ghost.part_activated`
* `ghost.part_deactivated`
* `ghost.part_contested`
* `ghost.part_conflict_resolved`
* `ghost.part_anchor_migrated`
* `ghost.part_consumed`
* `ghost.machine_progress_changed`
* `ghost.cycle_locked`
* `ghost.signal_sent`
* `ghost.version_changed`
* `ghost.restart_required`
* `ghost.cycle_activated`

## 6. Przenoszenie pozycji między sekcjami

Po zmianie stanu część powinna:

* zaktualizować kartę,
* opuścić poprzednią grupę,
* wejść do nowej grupy,
* zachować rozwinięcie, jeśli nadal jest widoczna,
* nie duplikować się.

Przykład:

```text
PUBLICZNA
→ BLOKOWANA PRZEZE MNIE
→ PUBLICZNA
→ AKTYWNA W KLANIE
```

## 7. Zmiana widoczności

Najważniejszy przypadek:

```text
public → blocked
```

Dla nieuprawnionego operatora karta:

* usuwa nazwę,
* usuwa kod,
* usuwa profesję,
* usuwa moc,
* usuwa dokładną pozycję,
* zmienia akcję mapy na terytorium.

Nie pozostawia starych danych w DOM, datasetach ani tooltipach.

## 8. Recovery

Przy:

* luce wersji,
* nieznanym `public_entity_id`,
* zmianie cyklu,
* niespójnym grupowaniu,
* błędzie zastosowania delty,

aplikacja pobiera:

```text
snapshot?view=suite
```

Następnie:

* odtwarza listy,
* zachowuje aktywny filtr,
* przywraca fokus, jeśli element nadal istnieje,
* nie otwiera mapy,
* nie pobiera pełnego profilu.

## 9. Zamknięcie okna

Po zamknięciu:

* wyrejestrować callbacki,
* usunąć lokalne listenery,
* anulować pending retry widoku,
* zachować wspólnego klienta, jeśli korzystają z niego inne aplikacje.

Nie tworzyć kolejnego delta clienta po każdym uruchomieniu okna.

## 10. Restart GhostSystemu

Po `ghost.restart_required`:

* aplikacja zostaje zablokowana,
* listy pozostają jako końcowy snapshot transmisji,
* przyciski mapy i teleportu są disabled,
* widoczny jest status aktualizacji.

Po restarcie:

* aplikacja może zostać automatycznie zamknięta lub odtworzona na nowym pulpicie zgodnie z istniejącym lifecycle,
* stary cykl nie wraca do aktywnej listy.

## 11. Stabilizacja

Po transmisji:

```text
BRAK AKTYWNYCH CZĘŚCI
NOWY CYKL ZA: [czas]
```

Odliczanie może być lokalne na podstawie `stabilization_until`, ale backend pozostaje źródłem prawdy o rozpoczęciu kolejnego cyklu.

## 12. Wspólne wzorce wizualne

Cztery aplikacje powinny używać:

* tej samej wysokości nagłówków,
* tego samego systemu ikon,
* podobnych przycisków mapy i teleportu,
* wspólnych statusów synchronizacji,
* wspólnych tooltipów,
* tych samych stanów błędu i recovery.

Nie muszą mieć identycznego layoutu, ponieważ obsługują inne dane.

## 13. Regresja Victim Picker

Sprawdzić:

* ustawianie `aimed_target`,
* skan,
* oznaczanie celów,
* mapę na żądanie,
* teleport,
* odległości po zmianie pozycji,
* brak konfliktu listenerów.

GhostNetwork Suite nie może zmieniać celu gracza.

## 14. Regresja Territory Control

Sprawdzić:

* klastry i samotne filary,
* minimum trzy filary,
* badge części,
* własna część,
* obca część,
* ukryta część,
* konflikt,
* porzucenie obiektu,
* rozpad klastra,
* aktualizacja części po stabilizacji,
* wspólna mapa i teleport.

Porzucenie kotwicy nie usuwa części GhostNetwork.

## 15. Regresja Operation Control

Sprawdzić:

* listy operacji,
* grupy,
* anulowanie,
* incydenty,
* odległości,
* aktualizację pozycji,
* brak mieszania delt GhostNetwork z deltami operacji.

## 16. Regresja mapy

Sprawdzić:

* mapa ładuje się wyłącznie na żądanie,
* focus części,
* focus terytorium,
* Ghost Anchor,
* markery,
* linie,
* brak przecieku danych,
* brak wielokrotnego tworzenia iframe,
* powrót do aplikacji po zamknięciu mapy.

## 17. Regresja zakupów

Dla wszystkich czterech produktów:

* zakup,
* brak środków,
* ponowny zakup,
* instalacja,
* istniejący zakup,
* launcher,
* jedna instancja,
* odinstalowanie, jeśli system je obsługuje,
* restart profilu.

## 18. Testy widoczności E2E

Dla jednej części wykonać pełny przebieg:

1. Neutralna — pełna dla wszystkich.
2. Zablokowana przez gracza A — pełna dla A.
3. Zablokowana — ukryta dla członka klanu A.
4. Zablokowana — ukryta dla właściwego klanu części.
5. Aktywna — pełna dla właściwego klanu.
6. Aktywna — zaszyfrowana dla obcych.
7. Kontestowana — widoczność zamrożona.
8. Zużyta — usunięta z aktywnych list.

Sprawdzić snapshot, deltę, GUI, mapę i Territory Control.

## 19. Testy wydajności

Mierzyć:

* czas otwarcia aplikacji,
* czas snapshotu,
* wielkość response,
* czas aktualizacji jednej karty,
* czas przegrupowania,
* liczbę listenerów,
* zużycie pamięci po wielokrotnym otwieraniu,
* brak pełnego profilu,
* brak ciężkiego pollera,
* brak renderowania mapy bez żądania.

## 20. Testy recovery

Minimum:

* utrata jednej delty,
* zmiana widoczności podczas zamkniętego okna,
* otwarcie po zmianie cyklu,
* consumed podczas braku połączenia,
* restart wymagany,
* powrót po restarcie,
* błąd snapshotu,
* retry z backoffem.

## 21. Testy bezpieczeństwa

Sprawdzić, że ukryte dane nie występują w:

* JSON,
* HTML,
* `dataset`,
* `title`,
* `aria-label`,
* logach konsoli,
* bridge mapy,
* payloadzie teleportu,
* cache frontendowym po zmianie widoczności.

## 22. Dokumentacja

Dodać:

```text
docs/ghostnetwork/GHOSTNETWORK_SUITE.md
```

Dokument opisuje:

* przeznaczenie,
* grupy części,
* widoczność,
* mapę,
* teleport,
* integrację z Territory Control,
* delty,
* recovery,
* zależności z pozostałymi narzędziami.

## DoD

Sprint jest zakończony, gdy:

1. GhostNetwork Suite można kupić, zainstalować i uruchomić.
2. Lista prezentuje wszystkie części widoczne dla operatora.
3. Publiczne, blokowane, klanowe i własne części są jednoznacznie rozdzielone.
4. Każda pozycja posiada bezpieczne akcje mapy i teleportu.
5. Ukryta część nigdy nie ujawnia dokładnej kotwicy.
6. Territory Control pokazuje klastry przechowujące komponenty.
7. Delty aktualizują pojedyncze karty bez pełnego odświeżenia.
8. Recovery obejmuje wyłącznie scope GhostNetwork.
9. Zamknięcie okna nie pozostawia listenerów.
10. Cała Ghost Control Suite przechodzi regresję.
11. Mapa nie jest ładowana bez jawnej akcji gracza.
12. Narzędzie nie tworzy żadnego alternatywnego źródła prawdy.

Po Sprintach 131–135 zaawansowany operator dostaje kompletną lekką ścieżkę obserwacji GhostNetwork: widzi, gdzie znajdują się publiczne części, kto blokuje komponenty, które moduły jego klanu są aktywne oraz jakie części kontroluje osobiście — a ciężką mapę otwiera wyłącznie wtedy, gdy naprawdę potrzebuje zobaczyć przestrzenny kontekst.

---

Lecimy z trzema sprintami domykającymi właściwy obieg narracyjny: zdarzenia GhostNetwork trafią jako bezpieczne fakty do istniejącego BlackNet/Ollama inboxa, model przygotuje ustrukturyzowaną narrację, a zwalidowany outbox opublikuje ją jako sygnały `ollama_enriched`.

# Sprint 136 — GhostNetwork: bridge zdarzeń do BlackNet Outbox

## Cel sprintu

Podłączyć zatwierdzone zdarzenia GhostNetwork do istniejącego pipeline’u narracyjnego BlackNetu.

BlackNet Outbox ma od tej pory otrzymywać również fakty dotyczące:

* odkrywania części,
* blokowania komponentów,
* aktywowania modułów,
* walk i obron,
* odbijania części,
* powstawania połączeń,
* postępu maszyn,
* domknięcia sieci,
* transmisji GhostSignalu,
* zmiany wersji GhostSystemu.

Sprint nie uruchamia jeszcze generowania tekstu przez Ollamę. Przygotowuje bezpieczne, wersjonowane zadania narracyjne.

Backend nadal rozstrzyga, co faktycznie się wydarzyło. Ollama może później jedynie opisać zatwierdzone wydarzenie. 

## 1. Integracja z istniejącym outboxem

Nie tworzyć drugiego, konkurencyjnego systemu kolejek, jeżeli BlackNet posiada już działający outbox.

Rozszerzyć istniejący kontrakt o:

```text
source_scope: ghostnetwork
source_event_id
cycle_id
signal_id
part_id
territory_id
state_version
narrative_thread_id
```

Dopuszczalne źródła:

```text
world
blacknet
ghostnetwork
system
```

GhostNetwork ma korzystać z tej samej obsługi:

* statusów,
* retry,
* deduplikacji,
* priorytetów,
* publikacji,
* audytu.

## 2. Bridge zdarzeń domenowych

Dodać komponent:

```text
GhostNetworkBlackNetBridge
```

Minimalny kontrakt:

```text
handle_domain_event(event)
is_narrative_worthy(event)
build_audience_tasks(event)
build_blacknet_facts(event, audience)
enqueue_tasks(tasks)
```

Bridge subskrybuje zapisane wydarzenia domenowe, a nie wywołania frontendu.

## 3. Dozwolone zdarzenia

Podstawowa allowlista:

```text
ghost.part_discovered
ghost.part_contained
ghost.part_revealed
ghost.part_activated
ghost.part_deactivated
ghost.part_defended
ghost.part_recovered
ghost.part_contested
ghost.part_conflict_resolved

ghost.connection_changed
ghost.machine_progress_changed
ghost.machine_online
ghost.machine_offline

ghost.cycle_locked
ghost.signal_sent
ghost.version_changed
ghost.stabilization_started
ghost.cycle_activated
```

Zdarzenia techniczne niewidoczne narracyjnie:

```text
ghost.part_reserved
ghost.part_reservation_released
ghost.part_reservation_expired
ghost.reward_pending
ghost.delta_published
ghost.health_check_completed
```

Nie mogą trafiać do BlackNetu.

## 4. Polityka istotności

Nie każde `ghost.connection_changed` powinno tworzyć osobny sygnał.

Dodać:

```text
GhostNarrativeSignificancePolicy
```

Polityka ocenia:

* typ wydarzenia,
* pierwsze wystąpienie w cyklu,
* wpływ na postęp maszyny,
* zmianę układu strategicznego,
* liczbę uczestników,
* długość konfliktu,
* znaczenie dla domknięcia sieci,
* czas od ostatniego podobnego sygnału.

Poziomy:

```text
ignore
low
normal
high
critical
```

Przykłady:

* pierwsza część cyklu — `high`,
* zwykłe kolejne połączenie — `low`,
* pierwsza kompletna maszyna — `high`,
* odbicie ostatniej brakującej części — `critical`,
* GhostSignal — `critical`.

## 5. Łączenie drobnych wydarzeń

Dodać możliwość agregowania wydarzeń w krótkim oknie.

Przykład:

```text
3 aktywacje części Echo Wolności w ciągu 10 minut
```

mogą utworzyć jeden task:

```text
Echo Wolności uruchomiło trzy kolejne moduły Libertas.
```

Agregator nie zmienia historii domenowej. Łączy wyłącznie zadania narracyjne.

Klucz grupowania może obejmować:

```text
cycle_id
event_family
clan_code
machine_code
time_bucket
```

## 6. Projekcja widoczności przed outboxem

Bridge musi najpierw użyć:

```text
GhostVisibilityService
```

Dopiero potem budować fakty dla konkretnej grupy odbiorców.

Nie wolno umieszczać pełnych danych w outboxie publicznym z założeniem, że Ollama ich nie wykorzysta.

Dla blokowanej części publiczny task może zawierać:

```json
{
  "territory_contains_part": true,
  "part_identity": null,
  "part_clan": null,
  "machine": null,
  "profession": null,
  "ability": null,
  "owner_clan": "virex",
  "module_state": "blocked"
}
```

Właściciel terytorium może otrzymać osobny task z pełną tożsamością.

## 7. Zakresy odbiorców

Dozwolone:

```text
public
clan
owner
player
```

Jedno wydarzenie może utworzyć kilka tasków.

Przykład aktywacji części:

### Publiczny

* aktywny węzeł,
* klan,
* lokalizacja,
* zaszyfrowany moduł.

### Właściwy klan

* pełna nazwa części,
* maszyna,
* profesja,
* supermoc,
* właściciel.

### Właściciel

* pełne dane i wpis o jego terytorium.

Każdy task posiada własny `audience_scope`.

## 8. Kontrakt tasku narracyjnego

Minimalna struktura:

```text
task_id
source_scope
source_event_id
cycle_id
signal_id
state_version

medium
audience_scope
audience_clan
audience_owner

event_family
truth_class
priority
narrative_thread_id

facts_json
allowed_actions_json
editorial_rules_json

canon_version
ghostsystem_version
prompt_version

status
dedupe_key
created_at
expires_at
```

Dla tego pipeline’u:

```text
medium = blacknet
truth_class = canonical
```

Ollama może zwrócić interpretacyjny język, ale nie może zmienić klasy źródłowego faktu.

## 9. Fakty wiążące

Każdy fakt otrzymuje stabilny identyfikator:

```text
fact_id
fact_type
value
visibility_scope
source_event_id
```

Przykład:

```json
{
  "fact_id": "fact-part-activated-9281",
  "fact_type": "part_activated",
  "value": {
    "clan": "phantom_mesh",
    "territory": "territory_441",
    "module_identity_visible": false
  },
  "visibility_scope": "public",
  "source_event_id": "event_9281"
}
```

Późniejszy output Ollamy musi wskazywać użyte `fact_refs`.

## 10. Wątki narracyjne

Dodać stabilne wątki:

```text
ghost-cycle:<cycle_id>
ghost-part:<part_id>
ghost-machine:<cycle_id>:<machine_code>
ghost-conflict:<conflict_id>
ghost-signal:<signal_id>
```

Dzięki temu kolejne sygnały mogą kontynuować historię:

* znalezienie części,
* późniejsza blokada,
* atak,
* odbicie,
* aktywacja,
* utrzymanie podczas transmisji.

Outbox nie potrzebuje pełnej historii. Może otrzymać skrót wątku.

## 11. CTA

Dozwolone akcje dla tasków GhostNetwork:

```text
open_ghostnetwork_suite
open_map_location
open_map_territory
open_territory_control
open_cyberner_thread
open_ghostsignal_archive
```

Model nie może tworzyć dowolnych URL ani endpointów.

Dla ukrytej części:

```text
open_map_territory
```

zamiast dokładnej lokalizacji komponentu.

## 12. Deduplikacja

Przykładowy klucz:

```text
blacknet:ghostnetwork:<event_id>:<audience_scope>
```

Dla agregatu:

```text
blacknet:ghostnetwork:<cycle_id>:<event_family>:<time_bucket>:<audience>
```

Retry eventu nie może utworzyć kolejnego tasku.

## 13. Deterministyczny fallback

Każdy task powinien posiadać:

```text
fallback_template_key
fallback_payload
```

Jeżeli Ollama jest niedostępna, BlackNet może opublikować prosty, deterministyczny sygnał.

Przykład:

```text
fallback_template_key:
ghost_part_activated_public
```

Brak modelu nie może zatrzymać informowania graczy o ważnych zdarzeniach.

## 14. Priorytety

Przykładowe priorytety:

```text
critical:
  cycle_locked
  signal_sent
  restart_required

high:
  machine_online
  part_recovered
  first_part_discovered

normal:
  part_activated
  part_contained
  part_defended

low:
  connection_changed
  machine_progress_changed
```

Critical może ominąć zwykłą kolejkę publikacji i wejść do BlackNetu szybciej.

## 15. Obserwowalność

Logować:

* odebrany event,
* wynik significance policy,
* liczbę tasków,
* zakresy odbiorców,
* `fact_ids`,
* dedupe,
* wybrany fallback,
* czas budowy outboxa,
* odrzucone zdarzenia.

## Testy Sprintu 136

Minimum:

* odkrycie części tworzy task publiczny,
* blokowana część nie ujawnia tożsamości publicznie,
* właściciel otrzymuje pełny task,
* aktywna część tworzy wariant publiczny i klanowy,
* rezerwacja nie tworzy tasku,
* trzy małe zdarzenia mogą zostać zagregowane,
* pierwsza część ma wyższy priorytet,
* GhostSignal ma priorytet critical,
* retry eventu nie duplikuje tasku,
* CTA ukrytej części prowadzi do terytorium,
* każdy task posiada fallback,
* błąd bridge’a nie cofa zdarzenia GhostNetwork.

## DoD

Sprint jest zakończony, gdy BlackNet Outbox otrzymuje bezpieczne, deduplikowane i gotowe do narracyjnego przetworzenia fakty dotyczące ważnych działań GhostNetwork.

---

# Sprint 137 — Ollama Inbox/Outbox: generowanie i walidacja sygnałów GhostNetwork

## Cel sprintu

Rozszerzyć istniejący worker Ollamy tak, aby przetwarzał zadania GhostNetwork z BlackNet Inboxu i zapisywał ustrukturyzowane propozycje sygnałów do Ollama Outboxu.

Model nie otrzymuje dostępu do tabel GhostNetwork ani pełnych profili. Pracuje wyłącznie na zatwierdzonym pakiecie faktów przygotowanym w Sprincie 136. 

## 1. Lifecycle zadania inbox

Dopasować nazwy do istniejącego systemu, zachowując statusy:

```text
queued
claimed
processing
generated
validated
rejected
retry_wait
dead_letter
completed
```

Worker atomowo przejmuje jeden task.

Pola przejęcia:

```text
claimed_by
claimed_at
lease_until
attempt_count
```

Jeżeli worker przestanie działać, task po wygaśnięciu lease może zostać odzyskany.

## 2. Obsługa `source_scope = ghostnetwork`

Worker rozpoznaje:

```text
source_scope: ghostnetwork
medium: blacknet
```

i używa dedykowanego prompt contract:

```text
blacknet_ghostnetwork_signal_v1
```

Nie mieszać tego z promptem zwykłego podsumowania świata.

## 3. Pakiet wejściowy

Ollama otrzymuje:

```text
task_id
medium
audience
truth_class
event_family

canon_version
ghostsystem_version
cycle_id
signal_number

facts
fact_refs
narrative_context
editorial_rules
allowed_actions
output_schema
```

Nie otrzymuje:

* pełnej bazy,
* ukrytych części,
* tabel nagród,
* adresów mailowych,
* danych sesji,
* prywatnych profili,
* dowolnych endpointów.

## 4. Reguły promptu GhostNetwork

Prompt systemowy powinien jasno określać:

* nie dodawaj nowych faktów,
* nie zmieniaj stanu części,
* nie wybieraj wyniku transmisji,
* nie ujawniaj pól `null`,
* nie zgaduj nazwy ukrytej części,
* nie twórz nowych graczy ani lokalizacji,
* użyj wyłącznie podanych `fact_refs`,
* zwróć wyłącznie JSON,
* zachowaj styl BlackNetu,
* nie udawaj komunikatu autorytatywnego backendu.

## 5. Rodziny sygnałów

Obsłużyć co najmniej:

```text
part_discovery
part_blockade
part_reveal
part_activation
part_deactivation
part_defense
part_recovery
connection_progress
machine_progress
machine_online
cycle_closure
signal_transmission
system_version_change
cycle_stabilization
```

Każda rodzina może posiadać własne limity długości i ton.

## 6. Ton sygnału

Dozwolone wartości:

```text
info
warning
critical
victory
mystery
system
clan
```

Przykłady:

* neutralna część — `info`,
* blokada — `warning`,
* odbicie — `victory`,
* pierwsze połączenie — `mystery`,
* transmisja — `critical`,
* stabilizacja — `system`.

## 7. Kontrakt outputu

Model zwraca:

```json
{
  "content_id": "ollama_ghost_0047_018",
  "task_id": "task_018",
  "medium": "blacknet",
  "source": "blacknet_editorial",
  "truth_class": "canonical",
  "audience_scope": "public",
  "signal_type": "ghost_part_activated",
  "title": "WĘZEŁ PHANTOM AKTYWNY",
  "body": "Siatka Widmo uruchomiła kolejny fragment swojej maszyny.",
  "tone": "warning",
  "fact_refs": [
    "fact-part-activated-9281"
  ],
  "cta_action": "open_map_location",
  "cta_payload": {
    "target_id": "ghost-node:8f3a12"
  },
  "thread_id": "ghost-machine:0047:phantom_veil",
  "expires_at": "2026-07-20T12:00:00Z"
}
```

Nie pozwalać na dodatkowe nieznane pola bez jawnej zgody schematu.

## 8. Walidator struktury

Dodać:

```text
GhostNetworkNarrativeOutputValidator
```

Sprawdza:

* poprawny JSON,
* wymagane pola,
* znany `signal_type`,
* dozwolony `tone`,
* poprawny audience,
* poprawną klasę prawdziwości,
* maksymalną długość,
* poprawne CTA,
* zgodny `thread_id`,
* brak zewnętrznego URL.

## 9. Walidator faktów

Każde `fact_ref` musi istnieć w tasku.

Output zostaje odrzucony, jeśli:

* zawiera nieznany fakt,
* nie wskazuje żadnego faktu,
* twierdzi coś sprzecznego z faktami,
* ujawnia ukryty identyfikator,
* zmienia `pending` na `delivered`,
* nazywa niezidentyfikowany komponent,
* przypisuje część niewłaściwemu klanowi.

## 10. Kontrola ukrytych danych

Walidator powinien sprawdzić gotowy tekst pod kątem zabronionych wartości znanych systemowi wewnętrznemu.

Dla publicznego tasku blokowanej części sprawdzić, czy output nie zawiera:

* `part_code`,
* nazwy,
* maszyny,
* profesji,
* supermocy,
* dokładnej kotwicy.

Model nie powinien ich znać, ale walidacja pozostaje dodatkową ochroną.

## 11. Walidacja CTA

CTA musi znajdować się w `allowed_actions`.

Payload musi odpowiadać przekazanemu identyfikatorowi.

Niedozwolone:

```text
teleport
set_aimed_target
purchase
activate_ability
capture_territory
send_hc
external_url
```

Model nie może zamienić obserwacyjnego sygnału w akcję mechaniczną.

## 12. Zapis do Ollama Outbox

Po poprawnej walidacji utworzyć wpis:

```text
output_id
task_id
source_event_id
cycle_id
signal_id
content_json
fact_refs_json
validation_status
validation_report
model_name
model_version
prompt_version
generation_time_ms
created_at
published_at
dedupe_key
```

Statusy:

```text
generated
validated
rejected
published
expired
```

## 13. Idempotencja outputu

Dla jednego tasku może istnieć maksymalnie jeden aktywny zwalidowany output.

Ponowne generowanie po błędzie może utworzyć kolejną próbę, ale tylko jeden wynik zostaje oznaczony:

```text
validated
```

Stabilny klucz:

```text
ollama-output:<task_id>:<prompt_version>
```

## 14. Retry

Retry przy:

* timeout,
* niedostępny model,
* niepoprawny JSON,
* chwilowy błąd walidatora technicznego.

Nie wykonywać automatycznego retry przy:

* ujawnieniu ukrytych danych,
* wymyśleniu faktów,
* niedozwolonym CTA,
* powtarzającym się naruszeniu schematu po ustalonym limicie.

Po limicie task trafia do:

```text
dead_letter
```

i może zostać obsłużony fallbackiem deterministycznym.

## 15. Timeout i limity

Konfiguracja:

```text
OLLAMA_GHOSTNETWORK_TIMEOUT
OLLAMA_GHOSTNETWORK_MAX_ATTEMPTS
OLLAMA_GHOSTNETWORK_MAX_TITLE_LENGTH
OLLAMA_GHOSTNETWORK_MAX_BODY_LENGTH
OLLAMA_GHOSTNETWORK_LEASE_SECONDS
```

Długi task nie może blokować całej kolejki BlackNetu.

## 16. Kolejność priorytetów

Worker powinien przetwarzać najpierw:

1. `signal_transmission`,
2. `cycle_closure`,
3. `machine_online`,
4. `part_recovery`,
5. zwykłe aktywacje i odkrycia,
6. agregaty postępu.

Stary sygnał niskiego priorytetu może wygasnąć, jeśli świat zdążył się znacząco zmienić.

## 17. Kontekst poprzednich publikacji

Worker może otrzymać maksymalnie kilka ostatnich wpisów wątku.

Cel:

* unikać powtarzania tego samego początku,
* utrzymać ciągłość konfliktu,
* nawiązać do wcześniejszej blokady.

Nie przekazywać całego BlackNetu ani pełnej historii cyklu.

## 18. Brak wpływu na gameplay

Awaria workera:

* nie blokuje aktywacji,
* nie blokuje transmisji,
* nie zatrzymuje rewardów,
* nie zmienia wersji,
* nie opóźnia delt gameplayowych.

Pipeline narracyjny pozostaje asynchroniczny.

## 19. Obserwowalność

Logować:

* task,
* model,
* prompt version,
* próbę,
* czas generowania,
* wynik parsowania,
* wynik walidacji,
* zabronione fakty,
* użyte CTA,
* dead letter.

Nie logować pełnych tajnych danych w zwykłym logu aplikacji.

## Testy Sprintu 137

Minimum:

* poprawny task odkrycia,
* poprawny sygnał aktywacji,
* ukryta część pozostaje anonimowa,
* nieznany `fact_ref` odrzucony,
* niedozwolone CTA odrzucone,
* zmiana outcome sygnału odrzucona,
* niepoprawny JSON trafia do retry,
* timeout odzyskuje task po lease,
* tylko jeden validated output,
* fallback po dead letter,
* priorytet transmisji,
* model nie ma dostępu do bazy,
* błąd modelu nie wpływa na mechanikę.

## DoD

Sprint jest zakończony, gdy Ollama może bezpiecznie przekształcić zatwierdzone fakty GhostNetwork w ustrukturyzowane propozycje sygnałów BlackNetu, a każdy output przechodzi walidację faktów, widoczności i CTA.

---

# Sprint 138 — BlackNet: publikacja narracyjnych sygnałów GhostNetwork

## Cel sprintu

Podłączyć zwalidowany Ollama Outbox do istniejącego publishera BlackNetu i publikować sygnały dotyczące GhostNetwork jako wpisy:

```text
ollama_enriched
```

Sygnały mają przeplatać się z deterministycznym BlackNetem, zachowywać ciągłość historii i zawsze posiadać mechaniczny fallback.

## 1. Publisher

Dodać lub rozszerzyć:

```text
BlackNetOllamaOutboxPublisher
```

Minimalny kontrakt:

```text
publish_validated_output(output)
build_blacknet_signal(output)
resolve_signal_priority(output)
deduplicate_signal(output)
publish_fallback(task)
```

Publisher nie interpretuje ponownie faktów.

Korzysta ze zwalidowanego outputu.

## 2. Typ sygnału

Publikowany wpis:

```text
source: ollama
origin: ghostnetwork
signal_class: ollama_enriched
```

Dodatkowo:

```text
source_event_id
cycle_id
signal_id
thread_id
fact_refs
truth_class
```

Pozwala to odróżnić:

* sygnał deterministyczny,
* narrację Ollamy,
* wpis klanowy,
* komunikat systemowy.

## 3. Relacja z sygnałami deterministycznymi

Ważne zdarzenie może stworzyć dwa elementy:

### Natychmiastowy sygnał deterministyczny

Publikowany od razu.

### Późniejszy sygnał narracyjny

Rozwija znaczenie wydarzenia.

Przykład:

```text
SYSTEM:
GHOSTSIGNAL 0047 WYSŁANY.
```

Następnie:

```text
BLACKNET:
Sygnał opuścił naszą warstwę czasu, ale kanał po drugiej stronie nadal milczy.
```

Nie publikować dwóch niemal identycznych wiadomości.

## 4. Deduplikacja semantyczna

Poza `dedupe_key` sprawdzić:

* ten sam event,
* ten sam tytuł,
* bardzo podobne body,
* ten sam thread,
* krótki odstęp czasu,
* identyczne CTA.

Jeżeli narracja nie wnosi nic ponad deterministic fallback, może zostać odrzucona albo opóźniona.

## 5. Typy kompozycji BlackNet

Przygotować layouty dla:

```text
ghost_discovery
ghost_blockade
ghost_activation
ghost_defense
ghost_recovery
ghost_machine_progress
ghost_machine_online
ghost_connection
ghost_cycle_closure
ghost_signal_sent
ghost_version_change
ghost_stabilization
```

Nie wszystkie muszą mieć osobny CSS. Mogą używać wspólnych wariantów z różnymi ikonami i danymi.

## 6. Wizualne dane sygnału

Sygnał może zawierać:

* ikonę klanu,
* ikonę maszyny, jeśli widoczna,
* stan części,
* licznik `N/20`,
* licznik `N/5`,
* status konfliktu,
* właściciela,
* lokalizację,
* numer GhostSignalu,
* wersję systemu.

Nie dołączać danych, których nie było w zwalidowanym outboxie.

## 7. Priorytety publikacji

### Critical

* domknięcie sieci,
* transmisja,
* restart,
* odpowiedź z 2108.

Mogą przerwać zwykłą rotację BlackNetu.

### High

* maszyna online,
* odbicie strategicznej części,
* pierwsza część cyklu.

### Normal

* aktywacja,
* blokada,
* skuteczna obrona.

### Low

* częściowy postęp,
* pojedyncze połączenie,
* agregat mniejszych wydarzeń.

## 8. TTL

Przykładowe zasady:

* odkrycie — średni TTL,
* konflikt — krótki TTL,
* blokada — do zmiany stanu albo określonego limitu,
* aktywacja — dłuższy TTL,
* transmisja — pozostaje do restartu,
* wersja systemu — pozostaje przez okres stabilizacji.

Sygnał może zostać unieważniony przez późniejszy event.

## 9. Unieważnianie

Przykłady:

* sygnał o publicznej części wygasa po jej zablokowaniu,
* sygnał o blokadzie wygasa po ujawnieniu lub aktywacji,
* sygnał o trwającym konflikcie wygasa po stabilizacji,
* sygnał o maszynie online może zostać zastąpiony przez `machine_offline`.

Publisher powinien korzystać z:

```text
supersedes_signal_id
invalidated_by_event_id
```

## 10. Wątki

Sygnały tego samego komponentu lub konfliktu mogą tworzyć ciąg:

```text
ODKRYCIE
→ BLOKADA
→ ATAK
→ ODBICIE
→ AKTYWACJA
→ TRANSMISJA
```

BlackNet może pokazywać oznaczenie:

```text
KONTYNUACJA SYGNAŁU
```

Nie musi wyświetlać pełnej historii na głównej kompozycji.

## 11. CTA

Publisher zachowuje wyłącznie zwalidowane CTA.

Przykłady:

### Publiczna część

```text
POKAŻ NA MAPIE
```

### Ukryta blokada

```text
POKAŻ TERYTORIUM
```

### Aktywny węzeł

```text
OTWÓRZ GHOSTNETWORK SUITE
```

### Konflikt

```text
OTWÓRZ TERRITORY CONTROL
```

### Transmisja

```text
OTWÓRZ ARCHIWUM SYGNAŁU
```

## 12. Widoczność publikacji

Publisher publikuje osobne wpisy dla:

* publicznego feedu,
* feedu klanowego,
* ewentualnie feedu owner-only.

Nie publikuje jednego pełnego wpisu z frontendowym filtrem.

## 13. Fallback

Jeżeli:

* Ollama jest wyłączona,
* task wygasł,
* output został odrzucony,
* worker nie odpowiada,
* outbox jest uszkodzony,

publisher używa deterministycznego szablonu ze Sprintu 136.

W logu zapisuje:

```text
publication_mode: fallback
```

Gracz nadal otrzymuje informację o wydarzeniu.

## 14. Przeplatanie z istniejącymi sygnałami

Dodać politykę rotacji:

```text
BlackNetSignalMixPolicy
```

Uwzględnia:

* sygnały świata,
* sygnały GhostNetwork,
* sygnały klanowe,
* podcasty,
* wpisy deterministyczne,
* `ollama_enriched`.

Nie dopuścić, aby intensywny konflikt GhostNetwork całkowicie zalał pozostały BlackNet.

Możliwe limity:

* maksymalna liczba sygnałów GN w krótkim oknie,
* wyjątek dla priority critical,
* agregowanie powtarzalnych działań.

## 15. Odpowiedź z 2108

Pipeline musi być gotowy na przyszły fakt:

```text
ghost.signal_outcome_resolved
```

Ollama może przygotować wiadomość dopiero po zatwierdzeniu przez backend:

* outcome,
* odbiorcy,
* integralności,
* autentyczności,
* źródła odpowiedzi.

Nie może samodzielnie wybrać, czy sygnał został przechwycony albo dostarczony.

## 16. Regresja GhostNetwork

Pełny test:

1. Część zostaje odkryta.
2. Bridge tworzy task.
3. Ollama generuje output.
4. Walidator akceptuje.
5. Publisher tworzy `ollama_enriched`.
6. BlackNet wyświetla sygnał.
7. CTA otwiera poprawny cel.
8. Zmiana stanu unieważnia poprzedni wpis.

## 17. Testy braku Ollamy

Powtórzyć najważniejsze scenariusze przy:

```text
GHOSTNETWORK_OLLAMA_ENABLED = false
```

Wszystkie wydarzenia:

* nadal zmieniają gameplay,
* nadal publikują sygnały deterministyczne,
* nadal trafiają do archiwum,
* nie generują błędów interfejsu.

## 18. Obserwowalność

Raport pipeline’u:

```text
GN EVENTS
OUTBOX TASKS
OLLAMA CLAIMED
VALIDATED OUTPUTS
REJECTED OUTPUTS
BLACKNET PUBLISHED
FALLBACK PUBLISHED
EXPIRED
DEAD LETTER
```

Metryki:

* czas event → task,
* task → output,
* output → publikacja,
* liczba retry,
* udział fallbacków,
* liczba unieważnionych wpisów.

## 19. Dokumentacja

Dodać:

```text
docs/ghostnetwork/GHOSTNETWORK_OLLAMA_BLACKNET.md
```

Dokument opisuje:

* źródłowe eventy,
* projekcję widoczności,
* inbox,
* worker,
* outbox,
* walidację,
* publisher,
* fallback,
* retry,
* feature flags,
* recovery.

## Testy Sprintu 138

Minimum:

* narracyjne odkrycie części,
* narracyjna blokada bez ujawnienia tożsamości,
* aktywacja pełna dla klanu,
* aktywacja zaszyfrowana publicznie,
* obrona,
* odbicie,
* maszyna online,
* transmisja,
* poprawne CTA,
* unieważnienie starego sygnału,
* brak duplikatu deterministycznego tekstu,
* rotacja nie zalewa BlackNetu,
* fallback przy wyłączonej Ollamie,
* dead letter nie zatrzymuje publishera,
* odpowiedź modelu nie wpływa na mechanikę,
* pełne E2E event → BlackNet.

## DoD

Sprint jest zakończony, gdy ważne działania GhostNetwork automatycznie stają się narracyjnymi sygnałami BlackNetu, przechodzą przez Ollama Inbox/Outbox, respektują widoczność części, posiadają mechaniczny fallback i pozostają całkowicie odseparowane od źródła prawdy gameplayu.

Po Sprintach 136–138 GhostNetwork nie tylko działa jako system strategiczny — zaczyna również sam opowiadać historię swoich konfliktów, aktywacji i transmisji przez żywy strumień BlackNetu.
