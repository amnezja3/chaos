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


Faza GhostNetwork

Po tych trzech sprintach mamy zamknięte fundamenty: wiemy, gdzie moduł dotyka istniejącej gry, mamy bezpieczny magazyn globalnego stanu i dysponujemy pełnym kanonem dwudziestu elementów, ale jeszcze żadna część nie może wypaść ani pojawić się na mapie.

GhostNetwork — audyt integracyjny i kontrakt domeny
GhostNetwork — fundament modułu i repozytorium stanu
GhostNetwork — katalog klanów, maszyn, profesji i części

Lecimy z pierwszą trójką — 110 ustali twarde granice integracji, 111 postawi bezpieczny fundament globalnego stanu, a 112 zamknie kanoniczny katalog czterech maszyn i dwudziestu części.

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
docs/ghostnetwork/sprint_110_integration_audit.md
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

Lecimy dalej — Sprint 116 zakotwiczy część po prawdziwym sukcesie, 117 zamknie jej pełny cykl życia, a 118 podepnie stan części pod istniejące klastry, konflikty i stabilną kontrolę terytorium.

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





GhostNetwork — połowy linii, pełne połączenia i animacje
GhostNetwork — delty, snapshot i recovery
GhostNetwork — supermoce profesji i rejestr efektów


GhostNetwork — wkład graczy, RSP i reputacja klanowa
GhostNetwork — obrona, odbicia i zabezpieczenia nagród
GhostNetwork — domknięcie sieci i blokada cyklu


GhostNetwork — transmisja GhostSignalu i restart systemu
GhostNetwork — BlackNet, Cyberner, Radio i narracyjny outbox
GhostNetwork — archiwum, testy końcowe i uruchomienie endgame

GhostNetwork Suite — audyt widoczności części i integracja z Territory Control
GhostNetwork Suite — lekki snapshot części, właścicieli i stanów terytorialnych
GhostNetwork Suite — lista części publicznych, blokowanych i aktywnych

GhostNetwork Suite — mapa na żądanie, teleport i oznaczenia klastrów z komponentami
GhostNetwork Suite — GUI desktopowe, delty, recovery i regresja całej Ghost Control Suite