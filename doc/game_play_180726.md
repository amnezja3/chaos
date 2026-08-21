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


# Profile Store Extraction — Sprinty 130.1–130.5

Data: 2026-07-23

Status: plan implementacyjny

## Cel serii

Ograniczyć używanie `users.profile_json` jako głównego magazynu aktywnego stanu gry.

Docelowo:

```text
dedykowany store = źródło prawdy dla swojego zakresu
profile_json = bootstrap / compatibility / recovery cache
```

Migracja musi być wykonywana stopniowo. Każdy sprint powinien pozostawić działający runtime, kompatybilność ze starymi profilami oraz możliwość wycofania zmiany bez utraty danych.

## Zasady obowiązujące we wszystkich sprintach

Każdy nowy store musi zapewniać:

* własną wersję rekordu,
* atomowe i idempotentne zapisy,
* monotoniczny merge dla postępu,
* ochronę przed nadpisaniem nowszego stanu starszym requestem,
* deltę runtime po zmianie,
* recovery snapshot lub możliwość odbudowy,
* zgodność ze starym `profile_json`,
* brak pełnego `sync_session_profile()` przy zwykłym odczycie,
* test dwóch równoległych zapisów,
* test powtórzonego requestu,
* test odtworzenia sesji po ponownym otwarciu gry.

Nowy store po aktywacji staje się źródłem prawdy. Profil może otrzymywać kopię kompatybilności, ale nie może ponownie nadpisywać store’a swoim starszym stanem.

Po aktywacji store’a `sync_session_profile()` nie może zapisywać wydzielonego
scope’u na podstawie starszego `profile_json`. Pełny profil może być użyty jako
bootstrap albo recovery tylko wtedy, gdy store nie ma jeszcze rekordu albo gdy
operator uruchomi jawne narzędzie naprawcze.

Każdy sprint 130.x musi kończyć się:

* aktualizacją `doc/project_journal.md`,
* aktualizacją dokumentacji właściwego store’a albo migracji,
* opisem wykonanych testów,
* opisem zakresu pozostającego w trybie compatibility,
* potwierdzeniem, że nie dodano nowego pełnego refreshu profilu.

## Tryby cutover

Każdy wydzielany scope powinien przechodzić przez kontrolowane tryby:

```text
observe
mirror_write
store_primary
store_only
```

`observe` tylko mierzy i porównuje stan. `mirror_write` zapisuje nowy store
równolegle do profilu. `store_primary` czyta już ze store’a, a profil traktuje
jako cache kompatybilności. `store_only` usuwa store z zależności runtime od
`profile_json`.

Przejście pomiędzy trybami musi być sterowane feature flagą albo ustawieniem
operacyjnym możliwym do wyłączenia bez deployu.

## Endpointy objęte kontrolą

Seria 130.x musi sprawdzać co najmniej następujące ścieżki:

* `/hack-action`,
* `/command`,
* akcje mapy, w tym travel i teleport,
* `/launch-queue`,
* `/system-messages`,
* `/api/operations?summary=1`,
* `/api/profile`,
* odświeżenie celu na toolbarze,
* File Manager,
* Googleplex,
* Ghost Exchange,
* Victim Picker,
* Territory Control,
* Operation Control.

Każda ścieżka objęta nowym store’em musi mieć test późnego requestu:

```text
request A startuje wcześniej
request B zapisuje nowszy stan
request A kończy później
request A nie może cofnąć stanu ze store’a
```

---

# Sprint 130.1 — Extraction Foundation and Action Receipts

## Cel

Zbudować wspólny fundament pod wydzielanie danych z profilu i zatrzymać duplikaty akcji przed uruchomieniem ciężkiej logiki profilu.

## Zakres

### 1. Wspólny kontrakt store’ów runtime

Wprowadzić wspólne zasady dla nowych store’ów:

* `version`,
* `updated_at`,
* optimistic update albo compare-and-swap,
* idempotency key,
* odrzucenie starszej wersji,
* zapis delty,
* opcjonalny compatibility mirror do profilu.

Dodać helpery do:

* pobrania bieżącej wersji,
* atomowego zwiększenia wersji,
* rozpoznania duplicate/no-op,
* budowania recovery snapshotu,
* kontrolowanego mirrorowania danych do profilu.

Każdy helper musi umieć zwrócić informację, czy zapis:

* utworzył nowy rekord,
* zaktualizował istniejący rekord,
* został odrzucony jako starszy,
* został rozpoznany jako duplicate,
* wymaga recovery.

### 2. `app_action_receipts`

Dodać tabelę:

```text
app_action_receipts(
  receipt_key primary key,
  username text not null,
  app_id text,
  action text,
  target_key text,
  source text,
  status text not null,
  response_json text,
  created_at text not null,
  updated_at text not null
)
```

Obsługiwane statusy:

* `received`,
* `started`,
* `effect_applied`,
* `duplicate`,
* `failed`.

Receipt musi być rozpoznawany przed:

* `sync_session_profile()`,
* odświeżaniem operacji,
* pobieraniem pełnego profilu,
* ponownym wykonaniem efektu aplikacji.

Powtórzony request powinien zwrócić zapisany wynik albo kontrolowaną odpowiedź `duplicate`, bez ponownego uruchamiania gameplayu.

### 3. Obserwowalność

Dodać metryki lub logi:

* liczba nowych receiptów,
* liczba duplicate,
* liczba duplicate zatrzymanych przed profile sync,
* liczba failed,
* czas obsługi duplicate path,
* źródło requestu: mapa, terminal, desktop, launch queue.

### 4. Hooki delta i recovery

Fundament musi przewidzieć wspólny sposób podpinania:

* `record_*_delta`,
* `current_version`,
* `recovery_required`,
* snapshotu per scope.

Nie wolno rozwiązywać braku danych powrotem do pełnego `/api/profile`, jeśli
dany scope ma już własny snapshot recovery.

## Definition of Done

* duplicate aplikacji jest rozpoznawany przed ciężkim profile sync,
* ten sam receipt nie wykonuje efektu drugi raz,
* dwa workery nie mogą jednocześnie zastosować tego samego efektu,
* istnieją testy dla mapy, terminala i desktopu,
* istnieje test późnego requestu dla receiptów,
* duplicate path nie uruchamia `/api/profile` ani `sync_session_profile()`,
* istnieje wspólna baza helperów używana przez następne sprinty,
* stary flow bez receipt key pozostaje kompatybilny przez okres przejściowy,
* brak zmiany zasad gameplayu.

## Poza zakresem

* migracja targetu,
* migracja pozycji,
* migracja operacji,
* usuwanie pól z `profile_json`,
* masowa migracja kont na serwerze.

---

# Sprint 130.2 — Target and Position Runtime Stores

## Cel

Usunąć dwa najczęściej cofające się zakresy stanu: aktualny cel gracza oraz pozycję gracza.

## Zakres

### 1. `player_target_runtime`

Dodać tabelę:

```text
player_target_runtime(
  username text primary key,
  target_key text,
  target_json text,
  security_json text,
  actions_allowed_json text,
  disarm_progress integer not null default 0,
  status text not null,
  version integer not null,
  updated_at text not null
)
```

Obsługiwane statusy:

* `cleared`,
* `aimed`,
* `in_progress`,
* `captured`.

Zasady monotoniczne dla tego samego `target_key`:

* `security=false` nie może wrócić na `true`,
* `actions_allowed=true` nie może wrócić na `false`,
* `disarm_progress` nie może spaść,
* `captured` wygrywa ze starym `aimed`,
* `cleared` wygrywa ze starszym requestem dotyczącym poprzedniego celu,
* stary target nie może zastąpić nowszego targetu o wyższej wersji.

Mapa, terminal, desktop i Victim Picker muszą korzystać z jednego store’a.

Dodać dziennik zdarzeń targetu albo równoważny ledger:

```text
target.aimed
target.progressed
target.captured
target.cleared
```

Ledger ma chronić przed sytuacją, w której zhakowany cel wraca jako namierzony
po późnym zapisie mapy, terminala, desktopu albo refreshu toolbaru.

### 2. `player_positions`

Dodać tabelę:

```text
player_positions(
  username text primary key,
  lat real not null,
  lng real not null,
  source text,
  version integer not null,
  updated_at text not null
)
```

Obsługiwane źródła:

* `travel`,
* `teleport`,
* `blacknet`,
* `terminal`,
* `map`,
* `migration`,
* `recovery`.

Zapisy pozycji muszą być monotoniczne po wersji. Późno zakończony request nie może przywrócić wcześniejszej lokalizacji.

Należy ujednolicić wszystkie aliasy pozycji używane przez:

* mapę,
* motocykl,
* teleport,
* BlackNet,
* terminal,
* player actors.

### 3. Warstwa kompatybilności

Przy odczycie:

1. najpierw sprawdzany jest nowy store,
2. brak rekordu pozwala wykonać kontrolowany fallback do profilu,
3. fallback może utworzyć rekord w store,
4. profil nigdy nie nadpisuje istniejącego rekordu o nowszej wersji.

Mirror do `profile_json` może być wykonywany:

* przy checkpointach,
* przy wylogowaniu,
* w zadaniu recovery,
* poza główną ścieżką teleportu i hackowania.

## Definition of Done

* target nie wraca po zhakowaniu lub wyczyszczeniu,
* kropki zabezpieczeń i postęp rozbrajania nie cofają się,
* teleport nie cofa się po otwarciu mapy,
* travel i teleport nie zapisują pełnego profilu,
* player actors czytają pozycję z lekkiego store’a,
* ponowne otwarcie terminala pokazuje ten sam target co mapa,
* dwa równoległe requesty nie mogą obniżyć postępu,
* późny request nie może przywrócić starego targetu ani starej pozycji,
* `captured_targets` i aktywny target pozostają spójne,
* istnieją testy kompatybilności dla kont bez nowych rekordów.

## Poza zakresem

* przenoszenie operacji,
* migracja system messages,
* inventory aplikacji,
* masowe uruchamianie migracji na produkcji.

---

# Sprint 130.3 — Operations and System Messages Extraction

## Cel

Przenieść operacje oraz wiadomości systemowe z profilu do osobnych, atomowych store’ów.

## Zakres

### 1. `player_operations`

Dodać tabelę:

```text
player_operations(
  operation_id text primary key,
  username text not null,
  target_key text,
  operation_type text not null,
  status text not null,
  operation_json text not null,
  risk_json text,
  version integer not null,
  created_at text not null,
  updated_at text not null
)
```

Dodać dziennik:

```text
operation_events(
  event_id text primary key,
  operation_id text not null,
  event_type text not null,
  dedupe_key text,
  payload_json text not null,
  created_at text not null
)
```

Start, anulowanie i finalizacja operacji muszą być atomowe.

Powtórzenie eventu z tym samym `dedupe_key` nie może:

* uruchomić drugiej operacji,
* wypłacić drugiej nagrody,
* ponownie naliczyć ryzyka,
* dwukrotnie wygenerować incydentu,
* dwukrotnie anulować lub finalizować operacji.

Endpoint summary powinien czytać bezpośrednio z `player_operations`, bez odświeżania i zapisywania pełnego profilu.

### 2. `system_messages`

Dodać tabelę:

```text
system_messages(
  message_id text primary key,
  username text not null,
  dedupe_key text,
  title text,
  body text,
  type text,
  source text,
  status text not null,
  created_at text not null,
  consumed_at text
)
```

Obsługiwane statusy:

* `pending`,
* `delivered`,
* `consumed`,
* `expired`.

Pobranie wiadomości nie może zapisywać pełnego profilu.

Oznaczenie wiadomości jako odczytanej lub zużytej powinno być atomową zmianą pojedynczego rekordu.

Dodać:

* deduplikację po `dedupe_key`,
* TTL dla wiadomości tymczasowych,
* kontrolowane ponowienie dostarczenia,
* możliwość odróżnienia `delivered` od `consumed`.

### 3. Integracja

Przepiąć na nowe store’y:

* Operation Center,
* mapę,
* response network,
* aplikacje uruchamiające operacje,
* endpoint system messages,
* toasty na desktopie.

System messages muszą posiadać deduplikację niezależną od liczby pollerów,
workerów i ponownego renderu okien. Wiadomość wynikająca z jednego zdarzenia
domenowego nie może pojawić się jako kilka toastów tylko dlatego, że frontend
odebrał ją kilka razy.

## Definition of Done

* start/cancel/finalize operacji są idempotentne,
* operation summary nie wywołuje pełnego sync profilu,
* ten sam event nie tworzy dwóch operacji,
* ten sam komunikat nie tworzy dwóch toastów,
* odczyt wiadomości nie zapisuje całego profilu,
* stan operacji jest wspólny dla mapy i Operation Center,
* późny request nie może odtworzyć zakończonej lub anulowanej operacji,
* pobranie `/system-messages` nie duplikuje toastów,
* istnieje recovery dla operacji pozostawionych w stanie przejściowym,
* stare operacje z profilu są obsługiwane przez fallback.

## Poza zakresem

* aplikacje i pliki narzędzi,
* storage,
* wallet,
* desktop settings,
* produkcyjna migracja wszystkich użytkowników.

## Checkpoint 130.3

Wdrożono `PlayerOperationStore` i `SystemMessageStore` jako atomowe store’y
runtime. Operation summary, Operation Center oraz endpoint `/system-messages`
korzystają z nowych tabel bez pełnego zapisu profilu w ścieżkach odczytu.

Legacy `profile_json` pozostaje fallbackiem kompatybilnościowym. Apps, tools,
storage i wallet przechodzą do kolejnego sprintu.

---

# Sprint 130.4 — Apps, Tools, Storage and Wallet Cutover

## Cel

Odłączyć najczęściej używane elementy ekonomii i inventory od pełnego profilu oraz zakończyć runtime’ową część ekstrakcji.

## Zakres

### 1. `player_apps`

Dodać tabelę:

```text
player_apps(
  username text not null,
  app_id text not null,
  app_json text not null,
  status text not null,
  version integer not null,
  updated_at text not null,
  primary key(username, app_id)
)
```

### 2. `player_tool_files`

Dodać tabelę:

```text
player_tool_files(
  username text not null,
  tool_id text not null,
  app_id text,
  tool_json text not null,
  version integer not null,
  updated_at text not null,
  primary key(username, tool_id)
)
```

File Manager nie może być źródłem prawdy dla posiadanych narzędzi. Może prezentować projekcję danych z inventory store.

Install i uninstall muszą być:

* atomowe,
* idempotentne,
* połączone z receipt,
* połączone z aktualizacją storage,
* odporne na dwa równoległe requesty.

### 3. `player_storage`

Dodać tabelę:

```text
player_storage(
  username text primary key,
  capacity integer not null,
  used integer not null,
  unit text not null,
  modifiers_json text,
  version integer not null,
  updated_at text not null
)
```

Źródłem prawdy dla storage muszą być:

* lista zainstalowanych aplikacji,
* tool files,
* produkty zwiększające pojemność,
* inne jawne modyfikatory.

Nie można dopuścić do:

* ujemnego `used`,
* przekroczenia capacity bez jawnego stanu over-limit,
* podwójnego naliczenia pliku,
* utraty modyfikatora po późnym zapisie profilu.

### 4. `wallet_balances`

Dodać tabelę:

```text
wallet_balances(
  username text primary key,
  balance integer not null,
  version integer not null,
  updated_at text not null
)
```

`wallet_transactions` pozostaje ledgerem zdarzeń, a `wallet_balances` staje się lekkim, atomowo aktualizowanym balansem.

Każda zmiana salda musi:

* posiadać transaction key,
* być idempotentna,
* aktualizować ledger i balance w jednej transakcji,
* uniemożliwiać powtórne naliczenie tej samej wypłaty lub opłaty.

Przepiąć:

* Ghost Exchange,
* Googleplex,
* przelewy,
* nagrody operacji,
* kary response network,
* toolbar.

### 5. Ograniczenie `sync_session_profile()`

Po tym sprincie zwykłe odczyty i drobne zmiany w zakresie:

* targetu,
* pozycji,
* operacji,
* wiadomości,
* aplikacji,
* narzędzi,
* storage,
* walleta

nie mogą wymagać pełnego zapisu profilu.

## Definition of Done

* picker narzędzi nie wymaga pełnego `/api/profile`,
* install/uninstall nie zapisuje całego profilu,
* File Manager korzysta z projekcji nowego inventory,
* storage nie cofa się po zakupie produktu,
* saldo nie jest aktualizowane przez bezpośrednią mutację `profile_json`,
* ledger i balance pozostają zgodne,
* istnieją testy równoległego zakupu, instalacji i wypłaty,
* compatibility mirror nie jest źródłem prawdy,
* istnieje dokument wskazujący, które pola profilu są już tylko cache’em.

## Poza zakresem

* desktop settings jako pełny store,
* usuwanie legacy pól z profilu,
* przebudowa identity i progression,
* automatyczna migracja produkcyjnej bazy.

`desktop_settings` pozostają świadomie odłożone po tej serii, chyba że podczas
implementacji okaże się, że pełny profil nadal cofa ustawienia mapy, fullscreen
albo autostart radia. Wtedy należy dopisać osobny mini-sprint albo wydzielić
lekki store ustawień przed produkcyjnym cutoverem.

---

## Checkpoint 130.4

Wdrożono runtime store dla inventory, tool files, storage oraz wallet balance:

* `player_apps`,
* `player_tool_files`,
* `player_storage`,
* `wallet_balances`,
* `wallet_balance_events`.

Delty `apps`, `storage` i `wallet` zapisują teraz odpowiednie projekcje do
nowych tabel. `apply_runtime_stores_to_profile()` nakłada te dane na
kompatybilny profil podczas bootstrapu, dzięki czemu stare widoki dalej widzą
`apps`, `files.tools`, `storage_*` i `hackcoins`, ale źródłem runtime dla tych
scope'ów stają się nowe store'y.

Googleplex install/product purchase przestał używać profilu jako źródła
wiadomości systemowych dla komunikatu instalacji/zakupu; komunikaty trafiają do
`system_messages`.

Stan po sprincie:

* inventory i wallet mają osobne tabele z wersjonowaniem;
* `wallet_transactions` pozostaje ledgerem;
* `wallet_balances` jest lekką projekcją bieżącego salda;
* legacy `profile_json` nadal istnieje jako compatibility mirror i recovery
  cache;
* pełny produkcyjny cutover i migracja istniejących kont pozostają zakresem
  Sprintu 130.5.

---

# Sprint 130.5 — Production Migration and Account Repair Tools

## Status

Tooling / database migration / production operations only.

Sprint nie zmienia zasad gameplayu ani zachowania interfejsu. Jego celem jest przygotowanie narzędzi uruchamianych bezpośrednio na serwerze, które bezpiecznie przeniosą dane istniejących użytkowników z `profile_json` do store’ów utworzonych w Sprintach 130.1–130.4.

## Cel

Dostarczyć idempotentny zestaw narzędzi pozwalający:

* przeanalizować bazę,
* wykonać backup,
* przeprowadzić dry-run,
* migrować pojedyncze konto,
* migrować wszystkie konta partiami,
* wznowić przerwaną migrację,
* zweryfikować wynik,
* naprawić wykryte rozbieżności,
* wygenerować raport,
* wycofać migrację.

## Główne narzędzie

Dodać jeden kontrolowany entrypoint, na przykład:

```text
tools/profile_store_migration.py
```

Narzędzie powinno posiadać tryby:

```text
audit
backup
dry-run
migrate-user
migrate-all
verify-user
verify-all
reconcile
resume
rollback-user
rollback-all
report
```

Każde polecenie ma wykonywać wyłącznie wskazaną operację: `audit` analizuje dane bez zmian, `backup` tworzy kopię bezpieczeństwa, `dry-run` pokazuje plan migracji, `migrate-*` zapisuje nowe store’y, `verify-*` porównuje dane źródłowe i wynikowe, `reconcile` naprawia kontrolowane rozbieżności, `resume` wznawia przerwane partie, a `rollback-*` odtwarza stan sprzed migracji.

## 1. Rejestr migracji

Dodać tabelę techniczną:

```text
profile_store_migrations(
  migration_id text not null,
  username text not null,
  status text not null,
  source_checksum text,
  result_checksum text,
  started_at text,
  completed_at text,
  error_json text,
  backup_json text,
  tool_version text not null,
  primary key(migration_id, username)
)
```

Obsługiwane statusy:

* `pending`,
* `running`,
* `completed`,
* `verified`,
* `warning`,
* `failed`,
* `rolled_back`,
* `skipped`.

Dzięki temu ponowne uruchomienie narzędzia nie może migrować poprawnie zakończonego konta drugi raz bez jawnej flagi.

## 2. Audit przed migracją

Audit ma wykrywać dla każdego użytkownika:

* brak lub uszkodzony `profile_json`,
* nieznane aliasy pozycji,
* niepełny target,
* target już znajdujący się w `captured_targets`,
* duplikaty operacji,
* operacje bez ID,
* duplikaty aplikacji i tool files,
* niespójne `storage_used`,
* capacity mniejsze niż used,
* brakujące modyfikatory storage,
* różnicę pomiędzy `hackcoins` a ledgerem,
* duplikaty system messages,
* niepoprawne typy pól,
* nieznane legacy formaty.

Audit nie może zmieniać bazy.

## 3. Backup

Przed migracją musi powstać:

* kopia całej bazy,
* eksport migrowanych fragmentów profili,
* manifest z datą, wersją narzędzia i checksumą,
* informacja o liczbie kont,
* możliwość odtworzenia pojedynczego użytkownika.

Narzędzie musi odmówić migracji produkcyjnej bez prawidłowego backupu, chyba że operator poda jawną flagę awaryjną.

## 4. Migracja danych użytkownika

Migracja pojedynczego konta powinna odbywać się w jednej kontrolowanej transakcji albo w etapach posiadających checkpointy.

Kolejność:

1. utworzenie wpisu migracji,
2. odczyt i normalizacja profilu,
3. migracja target runtime,
4. migracja pozycji,
5. migracja operacji i eventów,
6. migracja niezużytych system messages,
7. migracja apps i tool files,
8. obliczenie storage,
9. migracja wallet balance,
10. utworzenie compatibility mirror,
11. zapis checksum,
12. weryfikacja,
13. oznaczenie konta jako `verified`.

`app_action_receipts` nie wymaga migracji historycznej i może rozpoczynać jako pusty store.

## 5. Reguły migracji poszczególnych scope’ów

### Target

* nie migrować celu jako aktywnego, jeśli istnieje już w `captured_targets`,
* `captured` i `cleared` wygrywają ze starym `aimed`,
* niepełny target przenieść jako `cleared` albo oznaczyć do ręcznej kontroli,
* zachować stabilny `target_key`, jeśli można go odtworzyć jednoznacznie.

### Position

* rozpoznać wszystkie znane aliasy,
* wybrać najbardziej aktualną poprawną pozycję,
* sprawdzić zakres `lat` i `lng`,
* błędne współrzędne oznaczyć jako warning, bez tworzenia uszkodzonego rekordu.

### Operations

* zachować istniejące operation IDs,
* wygenerować deterministyczne ID tylko dla legacy wpisów bez identyfikatora,
* nie tworzyć dwóch rekordów dla tej samej operacji,
* zakończonych operacji nie przywracać jako aktywnych.

### System messages

* przenieść wiadomości wymagające dalszego dostarczenia,
* wygenerować deterministyczny `dedupe_key`,
* stare, zużyte toasty można pominąć zgodnie z ustaloną polityką TTL.

### Apps i tools

* usunąć duplikaty po stabilnym `app_id` lub `tool_id`,
* nie utracić generated metadata,
* zachować relację pomiędzy aplikacją a plikiem narzędzia.

### Storage

* obliczyć `used` na podstawie rzeczywistego inventory,
* zachować jawne modyfikatory capacity,
* rozbieżności pomiędzy profilem a wyliczeniem zapisać w raporcie,
* nie zmniejszać capacity bez jednoznacznej podstawy.

### Wallet

* porównać `profile.hackcoins` z `wallet_transactions`,
* przy różnicy nie zgadywać automatycznie źródła prawdy,
* użyć jawnej polityki migracyjnej,
* każdą korektę zapisać jako reconciliation transaction,
* nigdy nie zmieniać salda bez wpisu w ledgerze.

## 6. Migracja wszystkich kont

Tryb `migrate-all` musi obsługiwać:

* partie o konfigurowalnym rozmiarze,
* przerwę pomiędzy partiami,
* limit błędów,
* wznowienie od ostatniego checkpointu,
* pomijanie kont już zweryfikowanych,
* migrację wskazanego zakresu użytkowników,
* migrację pojedynczego loginu,
* tryb maintenance,
* tryb online z ochroną przed równoległą zmianą profilu.

W trybie online narzędzie musi wykryć zmianę checksum profilu pomiędzy rozpoczęciem a zakończeniem migracji. Takie konto powinno zostać wycofane z bieżącej próby i ponowione, zamiast zapisywać nieaktualny snapshot.

## 7. Weryfikacja

Weryfikacja powinna sprawdzać:

* liczbę rekordów,
* zgodność username,
* zgodność aktywnego targetu,
* zgodność pozycji,
* liczbę i status operacji,
* liczbę oczekujących wiadomości,
* inventory aplikacji i narzędzi,
* capacity oraz used,
* saldo i ledger,
* wersje rekordów,
* możliwość zbudowania poprawnego bootstrap snapshotu.

Wynik powinien mieć poziom:

* `OK`,
* `WARNING`,
* `FAILED`.

`WARNING` nie może być automatycznie traktowany jako sukces bez zapisania przyczyny.

## 8. Rollback

Rollback pojedynczego konta musi:

* korzystać z backupu zapisanego przed migracją,
* usunąć lub oznaczyć rekordy utworzone przez daną migrację,
* odtworzyć compatibility profile,
* zapisać status `rolled_back`,
* nie usuwać późniejszych, prawidłowych zmian użytkownika bez wykrycia konfliktu wersji.

Pełny rollback wszystkich kont może być wykonany tylko dla wskazanego `migration_id`.

## 9. Raport końcowy

Narzędzie ma generować raport zawierający:

* wersję migracji,
* czas rozpoczęcia i zakończenia,
* liczbę wszystkich kont,
* liczbę kont zweryfikowanych,
* liczbę warningów,
* liczbę błędów,
* liczbę rollbacków,
* rozbieżności walleta,
* naprawione storage,
* pominięte legacy rekordy,
* listę kont wymagających ręcznej kontroli.

Raport nie może ujawniać haseł, tokenów sesji ani innych danych uwierzytelniających.

## 10. Bezpieczeństwo uruchamiania

Narzędzie musi:

* domyślnie działać jako dry-run,
* wymagać jawnej flagi dla zapisu,
* wyświetlać ścieżkę używanej bazy,
* odmówić działania na nieznanym schemacie,
* sprawdzać dostępne miejsce na backup,
* mieć blokadę przed równoległym uruchomieniem dwóch migracji,
* logować operatora, host i wersję kodu,
* nie wypisywać pełnych profili do zwykłego logu,
* zwracać niezerowy exit code przy błędach.

## Definition of Done

* można wykonać audit bez zmiany bazy,
* można wykonać dry-run pojedynczego konta i całej bazy,
* można migrować pojedyncze konto,
* można migrować wszystkie konta partiami,
* przerwaną migrację można bezpiecznie wznowić,
* ponowne uruchomienie nie duplikuje danych,
* istnieje backup i rollback pojedynczego użytkownika,
* istnieje kontrolowany rollback całego `migration_id`,
* każde konto otrzymuje wynik w rejestrze migracji,
* wallet, storage, apps, tools, operations, messages, target i position są weryfikowane,
* konto z błędnym legacy profilem nie zatrzymuje migracji pozostałych kont,
* po migracji bootstrap gry działa bez konieczności zapisania pełnego profilu,
* `sync_session_profile()` nie nadpisuje store’ów po migracji,
* tryb `store_primary` można włączyć i wyłączyć bez utraty danych,
* test migracji działa na kopii produkcyjnej bazy,
* powstaje instrukcja uruchomienia na serwerze oraz checklista operatora.

## Poza zakresem

* zmiany gameplayu,
* usuwanie legacy pól z `profile_json`,
* migracja desktop settings,
* przebudowa identity i progression,
* automatyczne kasowanie starych compatibility snapshots,
* uruchamianie migracji bez backupu i raportu.

## Checkpoint 130.5

Sprint 130.5 dostarcza narzedzia produkcyjnej migracji i naprawy kont bez
zmiany gameplayu. Dodano kontrolowany entrypoint:

```text
tools/profile_store_migration.py
```

Narzędzie obsluguje tryby `audit`, `backup`, `dry-run`, `migrate-user`,
`migrate-all`, `verify-user`, `verify-all`, `reconcile`, `resume`,
`rollback-user`, `rollback-all` oraz `report`.

Dodano rejestr techniczny:

```text
profile_store_migrations
```

Rejestr zapisuje `migration_id`, `username`, status, checksum profilu
zrodlowego, checksum wyniku, backup JSON per user, blad walidacji oraz wersje
narzedzia.

Zasady bezpieczenstwa:

* `audit` i `dry-run` sa read-only;
* komendy zapisujace wymagaja `--write`;
* zapis produkcyjny wymaga `--backup-manifest` albo jawnego
  `--allow-without-backup`;
* narzedzie uzywa locka migracji przy komendach zapisujacych;
* rollback dziala per `migration_id`;
* raport nie wypisuje pelnych profili ani sekretow.

Zakres migracji obejmuje store'y ze Sprintow 130.1-130.4:

* target runtime;
* pozycja gracza;
* operacje;
* system messages;
* apps;
* tool files;
* storage;
* wallet balance.

Instrukcja operatorska znajduje sie w:

```text
doc/profile_store_migration_manual.md
```

## Decyzja po Sprintach 130.1-130.5

Po zakończeniu serii wymagany jest krótki checkpoint architektoniczny:

* które scope’y działają w `store_primary`,
* które nadal działają w `mirror_write`,
* które nadal czytają z `profile_json`,
* czy występują jeszcze cofki targetu, pozycji albo operacji,
* czy system messages nadal potrafią tworzyć duplikaty toastów,
* czy mapa, terminal i desktop widzą ten sam target,
* czy teleport/travel pozostają po ponownym otwarciu mapy,
* czy potrzebny jest mini-sprint dla `desktop_settings`.

# Sprint 130.6 — Motorcycle Travel Queue Refactor

Status: runtime refactor

## Cel

Przebudować sposób poruszania motocykla na mapie tak, aby:

* backend nie sterował każdą kolejną animacją motocykla,
* mapa przechowywała lokalną kolejkę punktów podróży,
* motocykl płynnie przejeżdżał przez wszystkie zaznaczone punkty,
* ostatni punkt kolejki był od razu zapisywany jako aktualna pozycja gracza,
* zamknięcie mapy nie przerywało ani nie cofało podróży,
* ponowne otwarcie mapy pokazywało motocykl w ostatnim zapisanym punkcie.

---

## Obecny model

Aktualny flow działa według schematu:

```text
gracz wskazuje punkt podróży
-> punkt trafia do backendu
-> backend zapisuje lub przetwarza podróż
-> backend wysyła sygnał poruszenia motocykla
-> motocykl rozpoczyna animację
-> po około dwóch minutach dociera do celu
```

Backend uczestniczy bezpośrednio w sterowaniu animacją motocykla.

Powoduje to kilka problemów:

* kolejne punkty podróży zależą od odpowiedzi backendu,
* animacja może rozpocząć się z opóźnieniem,
* zamknięcie mapy może pozostawić niejasny stan podróży,
* pozycja gracza i wizualna pozycja motocykla mogą się rozjechać,
* backend musi obsługiwać stan, który powinien być wyłącznie prezentacją frontendu.

---

## Nowy model

Po refaktorze mapa będzie działała według schematu:

```text
gracz wskazuje punkt podróży
-> punkt zostaje dodany do lokalnej kolejki trasy
-> ostatni punkt kolejki trafia do backendu jako aktualna pozycja
-> backend zapisuje pozycję gracza
-> frontend płynnie animuje motocykl przez wszystkie punkty kolejki
```

Backend nie musi wiedzieć, na którym odcinku animacji aktualnie znajduje się motocykl.

Dla backendu oraz pozostałych modułów gry aktualną pozycją jest zawsze:

```text
ostatni punkt aktywnej kolejki podróży
```

Frontend wykorzystuje całą kolejkę wyłącznie do prezentacji płynnego przejazdu.

---

## Główna zasada

```text
Pozycja logiczna gracza = ostatni punkt kolejki podróży.

Pozycja wizualna motocykla = aktualny punkt animacji pomiędzy początkiem i końcem kolejki.
```

Oznacza to, że pozycja logiczna może znajdować się już w punkcie końcowym, podczas gdy motocykl nadal wizualnie przejeżdża przez wcześniejsze punkty trasy.

---

## Zakres frontendu mapy

### 1. Lokalna kolejka podróży

Mapa utrzymuje lokalną listę punktów:

```text
motorcycleTravelQueue = [
  pointA,
  pointB,
  pointC
]
```

Każdy nowy punkt zaznaczony przez użytkownika zostaje dodany na końcu kolejki.

Kolejka powinna zachowywać:

* `lat`,
* `lng`,
* kolejność punktów,
* identyfikator punktu,
* czas dodania,
* opcjonalne źródło podróży.

Źródłem może być na przykład:

* mapa,
* Victim Picker,
* Territory Controller,
* GhostNetwork Suite,
* BlackNet,
* teleport.

### 2. Ciągła animacja

Motocykl porusza się kolejno:

```text
aktualna pozycja wizualna
-> pierwszy punkt kolejki
-> drugi punkt kolejki
-> trzeci punkt kolejki
```

Animacja nie zatrzymuje się pomiędzy punktami, jeżeli kolejka zawiera następne cele.

Powinna tworzyć jeden płynny przejazd, nawet gdy użytkownik szybko zaznaczy wiele punktów.

Przykład:

```text
Warszawa Centrum
-> Praga
-> Targówek
-> Białołęka
-> Marki
```

Motocykl wykonuje wizualnie pełny slalom przez wszystkie zaznaczone lokalizacje.

### 3. Dodawanie punktu podczas trwającej animacji

Jeżeli użytkownik zaznaczy nowy punkt, gdy motocykl jest już w ruchu:

* trwająca animacja nie jest restartowana,
* nowy punkt trafia na koniec kolejki,
* ostatni punkt kolejki zostaje zapisany w backendzie,
* motocykl po zakończeniu bieżącego odcinka jedzie dalej.

Nie można:

* teleportować wizualnie motocykla do początku nowej trasy,
* resetować postępu bieżącego odcinka,
* usuwać wcześniejszych punktów kolejki,
* uruchamiać kilku niezależnych animatorów.

---

## Synchronizacja z backendem

### 1. Zapis pozycji

Po każdym dodaniu punktu do kolejki frontend wysyła do backendu najnowszy punkt końcowy.

Przykład:

```text
kolejka:
A -> B -> C

pozycja zapisana w backendzie:
C
```

Po dodaniu punktu `D`:

```text
kolejka:
A -> B -> C -> D

pozycja zapisana w backendzie:
D
```

Backend zapisuje punkt jako aktualną pozycję gracza w `player_positions`.

### 2. Backend nie steruje animacją

Backend nie wysyła już polecenia:

```text
move motorcycle
```

Backend:

* przyjmuje nową pozycję,
* waliduje podróż,
* zapisuje ostatni punkt,
* zwiększa wersję pozycji,
* zwraca potwierdzenie zapisu.

Animacja jest odpowiedzialnością mapy.

### 3. Synchronizacja cykli mapy

Podczas cyklicznej synchronizacji mapa otrzymuje pozycję gracza z backendu.

Jeżeli lokalna kolejka podróży jest aktywna:

* synchronizacja nie może przerwać animacji,
* snapshot backendu odpowiada ostatniemu punktowi kolejki,
* motocykl nadal korzysta ze swojej lokalnej pozycji wizualnej.

Jeżeli lokalna kolejka jest pusta:

* motocykl ustawia się na pozycji otrzymanej z backendu.

### 4. Ochrona przed cofnięciem pozycji

Starszy snapshot mapy nie może nadpisać nowszego punktu podróży.

Pozycja powinna korzystać z:

* `version`,
* `updated_at`,
* monotonicznego zapisu w `player_positions`.

Jeżeli frontend posiada potwierdzoną pozycję o wersji `12`, snapshot o wersji `11` musi zostać zignorowany.

---

## Zamknięcie mapy

Jeżeli użytkownik zamknie mapę podczas animacji:

```text
A -> B -> C -> D
       ^
motocykl znajduje się wizualnie tutaj
```

to aktualną pozycją gracza pozostaje:

```text
D
```

Frontend nie musi zapisywać chwilowej pozycji motocykla pomiędzy punktami.

Po zamknięciu mapy:

* lokalna animacja zostaje zakończona razem z widokiem,
* kolejka nie musi być kontynuowana w tle,
* backend zachowuje ostatni punkt jako pozycję gracza,
* pozostałe moduły gry traktują gracza jako znajdującego się w ostatnim punkcie.

---

## Ponowne otwarcie mapy

Po ponownym otwarciu mapy:

* mapa pobiera pozycję z `player_positions`,
* motocykl pojawia się w ostatnim zapisanym punkcie,
* poprzednia animacja nie jest odtwarzana ponownie,
* stara kolejka nie jest odbudowywana,
* nowa kolejka rozpoczyna się od aktualnej pozycji backendowej.

Przykład:

```text
gracz zaznaczył:
A -> B -> C -> D

zamknął mapę podczas przejazdu A -> B

ponowne otwarcie:
motocykl znajduje się w D
```

---

## Czyszczenie kolejki

Po osiągnięciu punktu frontend usuwa go z początku kolejki.

Przykład:

```text
przed osiągnięciem A:
[A, B, C]

po osiągnięciu A:
[B, C]
```

Po dotarciu do ostatniego punktu:

```text
[]
```

Motocykl pozostaje w końcowej pozycji.

Czyszczenie kolejki nie powoduje dodatkowego zapisu do backendu, ponieważ końcowa pozycja została zapisana już w chwili dodania punktu.

---

## Błędy zapisu

Jeżeli backend odrzuci nowy punkt podróży:

* punkt nie powinien pozostać jako zatwierdzony koniec trasy,
* frontend powinien usunąć go z kolejki albo oznaczyć jako odrzucony,
* motocykl nie powinien do niego jechać,
* wcześniejsze zatwierdzone punkty pozostają w kolejce.

Jeżeli zapis zakończy się timeoutem:

* punkt otrzymuje status `pending`,
* frontend może ponowić zapis z tym samym receipt key,
* powtórzenie nie może utworzyć drugiej zmiany pozycji,
* animacja do niepotwierdzonego punktu nie powinna kończyć się uznaniem go za zatwierdzoną pozycję.

---

## Kontrakt punktu podróży

Przykładowy punkt kolejki:

```text
{
  travel_id,
  lat,
  lng,
  source,
  status,
  position_version,
  created_at
}
```

Statusy:

```text
pending
confirmed
animating
completed
rejected
```

Blok opisuje pojedynczy punkt podróży i pozwala oddzielić potwierdzenie backendowe od samego etapu animacji widocznego na mapie.

---

## Integracje

Refaktor powinien objąć wszystkie miejsca, które mogą zmienić pozycję motocykla:

* kliknięcie podróży na mapie,
* teleport,
* Victim Picker,
* Territory Controller,
* GhostNetwork Suite,
* BlackNet,
* terminal,
* inne aplikacje otwierające mapę lub ustawiające cel podróży.

Każda integracja powinna używać jednego wejścia:

```text
enqueueMotorcycleTravelPoint(point)
```

Nie może istnieć kilka niezależnych sposobów uruchamiania animacji motocykla.

---

## Testy wymagane

### Kolejka

* jeden punkt uruchamia jeden przejazd,
* kilka punktów tworzy jeden płynny przejazd,
* nowy punkt podczas animacji trafia na koniec kolejki,
* punkt zakończony znika z początku kolejki,
* po zakończeniu trasy kolejka jest pusta.

### Backend

* ostatni punkt kolejki jest zapisywany jako pozycja gracza,
* dodanie kolejnego punktu aktualizuje pozycję,
* duplicate request nie zwiększa wersji drugi raz,
* starsza wersja nie nadpisuje nowszej,
* snapshot mapy nie cofa aktywnej podróży.

### Zamknięcie mapy

* zamknięcie mapy nie zapisuje chwilowej pozycji animacji,
* po ponownym otwarciu motocykl znajduje się w ostatnim punkcie,
* zamknięcie mapy nie wymaga kontynuowania animacji na backendzie,
* stara kolejka nie odtwarza się po ponownym otwarciu.

### Integracje

* podróż z mapy używa wspólnej kolejki,
* teleport używa wspólnego store’a pozycji,
* Victim Picker nie uruchamia osobnego animatora,
* Territory Controller nie obchodzi kolejki,
* BlackNet i terminal nie nadpisują pozycji starszym snapshotem.

---

## Definition of Done

* backend nie wysyła już sygnału sterującego animacją motocykla,
* mapa posiada jedną lokalną kolejkę punktów podróży,
* motocykl płynnie przejeżdża przez całą kolejkę,
* nowy punkt można dodać podczas trwającej animacji,
* ostatni punkt kolejki jest od razu pozycją logiczną gracza,
* pozycja jest zapisywana w `player_positions`,
* cykliczna synchronizacja mapy nie przerywa animacji,
* starszy snapshot nie cofa motocykla,
* zamknięcie mapy kończy wyłącznie warstwę wizualną,
* ponowne otwarcie mapy pokazuje motocykl w ostatnim punkcie,
* wszystkie źródła podróży używają wspólnego API frontendu,
* nie ma kilku równoległych animatorów motocykla,
* brak zmiany czasu, kosztu oraz zasad dostępności podróży.

---

## Poza zakresem

* zapisywanie chwilowej pozycji motocykla podczas animacji,
* kontynuowanie animacji po zamknięciu mapy,
* odtwarzanie starej trasy po ponownym otwarciu mapy,
* zmiana czasu podróży,
* zmiana kosztu podróży,
* zmiana zasięgu podróży,
* zmiana zasad teleportu,
* zmiana gameplayu motocykla,
* synchronizacja każdego punktu animacji z backendem.


# Sprint 130.7 — Motorcycle Travel Phone Preloader

Status: frontend / visual feedback

## Cel

Dodać nad motocyklem animowany wskaźnik oczekiwania na rozpoczęcie podróży.

Od momentu zlecenia podróży do chwili faktycznego ruszenia motocykla nad jego ikoną pojawia się telefon komórkowy, który:

* lekko drży jak podczas wibracji,
* przechyla się naprzemiennie na boki,
* emituje animowane łuki sygnału dzwonienia,
* pozostaje widoczny do momentu rozpoczęcia ruchu motocykla.

Wskaźnik zastępuje zwykły spinner i komunikuje, że podróż została przyjęta, ale motocykl jeszcze nie rozpoczął jazdy.

---

## Zachowanie

Flow powinien wyglądać tak:

```text
gracz wybiera punkt podróży
-> podróż zostaje przyjęta
-> nad motocyklem pojawia się dzwoniący telefon
-> telefon wibruje i emituje łuki
-> motocykl rozpoczyna animację jazdy
-> telefon natychmiast znika
```

Telefon nie pokazuje czasu pozostałego do rozpoczęcia podróży.

Jest wyłącznie wizualnym stanem:

```text
podróż oczekuje na ruszenie motocykla
```

---

## Wygląd

Preloader powinien składać się z:

* prostej ikony telefonu komórkowego,
* dwóch lub trzech łuków po bokach telefonu,
* opcjonalnego delikatnego tła zwiększającego czytelność,
* lekkiego przesunięcia nad motocyklem.

Ikona musi pasować do interfejsu CHAOS:

* cyberpunkowa,
* techniczna,
* czytelna w małym rozmiarze,
* bez dużego panelu i bez tekstu,
* nie może zasłaniać motocykla ani istotnych elementów mapy.

Przykładowa struktura wizualna:

```text
      ))) 📱 (((
          🏍
```

Łuki powinny wyglądać jak promieniujący sygnał dzwonienia, a nie jak radar albo skanowanie mapy.

---

## Animacja telefonu

Telefon powinien wykonywać krótką, zapętloną animację:

1. lekki obrót w lewo,
2. szybki powrót,
3. lekki obrót w prawo,
4. szybki powrót,
5. krótka pauza,
6. ponowienie cyklu.

Animacja powinna naśladować telefon leżący na powierzchni i drżący podczas połączenia.

Nie powinna:

* wykonywać dużych obrotów,
* skakać wysoko,
* przesuwać się po mapie,
* wyglądać jak uszkodzony element UI,
* działać zbyt szybko i agresywnie.

---

## Animacja łuków

Łuki sygnału powinny:

* pojawiać się kolejno od telefonu na zewnątrz,
* delikatnie zwiększać skalę,
* stopniowo zanikać,
* powtarzać się w rytmie wibracji telefonu.

Cykl może wyglądać tak:

```text
telefon drży
-> pojawia się pierwszy łuk
-> pojawia się drugi łuk
-> pojawia się trzeci łuk
-> łuki zanikają
-> krótka przerwa
-> kolejny cykl
```

Łuki mogą znajdować się po jednej albo po obu stronach telefonu.

Preferowany jest symetryczny układ, o ile pozostaje czytelny przy małej ikonie.

---

## Pozycjonowanie

Preloader musi być zakotwiczony do aktualnej wizualnej pozycji motocykla.

Podczas oczekiwania:

* porusza się razem z markerem motocykla,
* pozostaje nad jego ikoną,
* uwzględnia skalę i przesunięcie markera,
* nie zmienia pozycji przy odświeżeniu warstw mapy,
* nie zostaje w starej lokalizacji po zmianie pozycji motocykla.

Preloader nie może być osobnym markerem niezależnym od motocykla.

Powinien być elementem jego warstwy wizualnej albo bezpośrednio powiązanym overlayem.

---

## Moment uruchomienia

Preloader pojawia się, gdy:

* użytkownik zlecił podróż,
* punkt został przyjęty do kolejki,
* motocykl jeszcze nie rozpoczął animacji ruchu.

Nie powinien pojawiać się już przy samym kliknięciu miejsca na mapie, jeżeli podróż nie została jeszcze zatwierdzona.

Najbezpieczniejszy stan wejściowy:

```text
travel accepted / queued
```

---

## Moment wyłączenia

Preloader znika w chwili, gdy:

* animator motocykla rozpocznie pierwszy realny odcinek ruchu,
* motocykl zmieni swoją wizualną pozycję,
* podróż zostanie anulowana,
* backend odrzuci punkt podróży,
* mapa zostanie zamknięta,
* marker motocykla zostanie usunięty.

Nie należy czekać na zakończenie podróży.

Telefon informuje wyłącznie o oczekiwaniu na start, a nie o trwającej jeździe.

---

## Integracja z kolejką podróży

Preloader powinien być powiązany ze stanem kolejki motocykla.

Przykładowe stany:

```text
idle
waiting_to_start
moving
paused
completed
rejected
```

Telefon jest widoczny wyłącznie dla:

```text
waiting_to_start
```

Dla pozostałych stanów:

```text
idle             -> brak telefonu
moving           -> brak telefonu
paused           -> brak telefonu, chyba że powstanie osobny sprint
completed        -> brak telefonu
rejected         -> telefon znika
```

Blok stanów oddziela preloader startu od samej animacji jazdy i zapobiega pozostawaniu telefonu nad motocyklem po rozpoczęciu ruchu.

---

## Kolejne punkty podróży

Jeżeli motocykl już jedzie, a użytkownik dodaje kolejny punkt do kolejki:

* telefon nie powinien pojawiać się ponownie,
* motocykl kontynuuje aktywną animację,
* nowy punkt trafia na koniec kolejki.

Telefon pojawia się tylko wtedy, gdy motocykl rzeczywiście stoi i oczekuje na rozpoczęcie pierwszego odcinka.

Jeżeli motocykl zakończy trasę, zatrzyma się i powstanie nowa podróż, preloader może zostać pokazany ponownie.

---

## Obsługa błędów

Jeżeli podróż zostanie odrzucona:

* telefon znika,
* kolejka nie rozpoczyna animacji,
* nie pozostaje osierocony overlay.

Jeżeli odpowiedź backendu się opóźnia:

* telefon pojawia się dopiero po potwierdzeniu podróży,
* przed potwierdzeniem może pozostać obecny systemowy stan oczekiwania,
* nie można równocześnie pokazywać kilku preloaderów nad motocyklem.

Jeżeli animator nie wystartuje z powodu błędu:

* telefon nie może działać bez końca,
* stan powinien zostać zakończony przez timeout techniczny,
* błąd powinien zostać zapisany w logu,
* UI może przejść do istniejącego komunikatu błędu podróży.

Timeout techniczny nie zmienia zasad gameplayu i służy tylko do usunięcia zawieszonego efektu.

---

## Wydajność

Animacja powinna być wykonana głównie w CSS.

Preferowane właściwości:

* `transform`,
* `opacity`.

Nie należy animować:

* położenia przez `top` i `left`,
* ciężkich filtrów,
* dużych rozmyć,
* wielu elementów SVG na każdej klatce,
* efektów wymagających ciągłego przeliczania layoutu mapy.

Na mapie może istnieć tylko jeden aktywny preloader motocykla gracza.

---

## Dostępność i ustawienia systemowe

Dla użytkowników z włączonym:

```text
prefers-reduced-motion: reduce
```

telefon powinien:

* pozostać widoczny,
* nie wykonywać intensywnych drgań,
* używać spokojnego pulsowania albo statycznych łuków.

Wskaźnik nadal musi komunikować oczekiwanie, nawet bez pełnej animacji.

---

## Testy

### Uruchomienie

* potwierdzona podróż pokazuje telefon,
* niepotwierdzona podróż nie pokazuje telefonu,
* odrzucona podróż usuwa telefon,
* jeden request tworzy tylko jeden preloader.

### Animacja

* telefon drży w krótkiej pętli,
* łuki pojawiają się i zanikają,
* animacja nie przesuwa markera motocykla,
* preloader pozostaje poprawnie zakotwiczony podczas synchronizacji mapy.

### Rozpoczęcie ruchu

* telefon znika przy rozpoczęciu pierwszego odcinka,
* telefon nie jest widoczny podczas jazdy,
* dodanie punktu podczas jazdy nie pokazuje telefonu ponownie,
* po zakończeniu trasy nowa podróż może pokazać nowy preloader.

### Zamknięcie mapy

* zamknięcie mapy usuwa preloader,
* ponowne otwarcie mapy nie odtwarza starej animacji telefonu,
* brak osieroconego timera lub listenera.

### Błędy

* błąd animatora kończy preloader po kontrolowanym timeoutcie,
* anulowanie podróży natychmiast usuwa telefon,
* usunięcie motocykla usuwa również jego overlay.

---

## Definition of Done

* nad motocyklem pojawia się ikona telefonu po przyjęciu podróży,
* telefon wykonuje czytelną animację wibracji,
* animowane łuki imitują dzwonienie telefonu,
* preloader jest widoczny do chwili rozpoczęcia ruchu,
* preloader znika natychmiast po ruszeniu motocykla,
* kolejny punkt dodany podczas jazdy nie uruchamia telefonu ponownie,
* telefon jest zakotwiczony do markera motocykla,
* synchronizacja mapy nie tworzy drugiej kopii efektu,
* anulowanie lub odrzucenie podróży usuwa animację,
* zamknięcie mapy czyści animację i listenery,
* efekt jest wykonany lekko, głównie przy użyciu CSS,
* obsłużony jest `prefers-reduced-motion`,
* brak zmiany czasu, kosztu i logiki podróży.

---

## Poza zakresem

* odtwarzanie prawdziwego dźwięku telefonu,
* sterowanie głośnością,
* wibracje urządzenia mobilnego,
* komunikaty tekstowe nad motocyklem,
* licznik czasu do rozpoczęcia podróży,
* animacja telefonu podczas całej jazdy,
* zmiana motoryki motocykla,
* zmiana kolejki punktów podróży,
* zmiana backendowego kontraktu pozycji,
* preloader dla innych graczy i NPC.


# Sprinty 130.8.1–130.8.4 — refaktor konfliktów terytorialnych

## Wspólny cel

Przebudować wyłącznie domenę konfliktów terytorialnych i jej projekcję na mapę.

Nie przebudowujemy całego systemu terytoriów, zasad tworzenia klastrów, przejmowania zwykłych obiektów ani geometrii pól graczy.

Po zakończeniu serii sprintów:

* konflikt posiada stabilny `conflict_id`,
* geometria nie określa tożsamości konfliktu,
* filary są przechowywane po stabilnym `target_id`,
* przejęcie filaru nie przebudowuje wielokrotnie całej domeny,
* konflikt i geometria posiadają niezależne wersje,
* backend publikuje spójny snapshot konfliktu,
* frontend aktualizuje warstwy po stabilnych identyfikatorach,
* starszy snapshot nie może nadpisać nowszego,
* awaria przebudowy nie usuwa ostatniej poprawnej projekcji.

## Obowiązkowe artefakty przed każdym sprintem

Przed rozpoczęciem każdego sprintu 130.8.x należy ponownie sprawdzić spójność z:

* `doc/clans_machines.md`,
* `doc/ghostnetwork_architecture.md`,
* `doc/ghost_control_suite_contract_audit.md`,
* `doc/victim_picker_audit.md`,
* `doc/incidents_npc_technical_architecture.md`,
* aktualnym kontraktem delt terytoriów i mapy.

## Niezmienniki gameplayowe serii

Refaktor nie może zmienić ani amputować:

* czterech etapów hackowania filaru, `actions_allowed`, zabezpieczeń celu, postępu i finalnego przejęcia,
* możliwości wybrania filaru lub innera konfliktu w Victim Pickerze i uruchomienia akcji `territory_contest`,
* aktywnych operacji, incydentów i `aimed_target` wskazujących na konflikt albo filar,
* reguł odbicia filaru, nagród, RSP, plików, komunikatów i deduplikacji efektów,
* semantyki ALARM/KOLIZJA oraz liczników konfliktów w Territory Control,
* pełnego otoczenia klastra, ochrony pól znajomych i członków tego samego klanu oraz transferu po poprawnym otoczeniu,
* rozróżnienia kanonicznej własności terytorium od tymczasowej projekcji obszaru spornego,
* zdarzeń i projekcji używanych przez GhostNetwork, BlackNet, Cyberner, Radio i narracyjny outbox,
* działania istniejących snapshotów startowych i recovery mapy.

Filar nie może zniknąć tylko dlatego, że po zmianie geometrii znalazł się poza aktualnym polygonem frontu. Jeżeli nadal należy do aktywnego konfliktu lub prowadzi do obcego klastra, pozostaje w rejestrze i musi być osiągalny przez istniejące interfejsy gameplayowe.

## Strategia wdrożenia bez amputacji

Każdy etap musi posiadać feature flagę i kill switch. Migracja działa idempotentnie, a przed przełączeniem zapisu wykonywane jest porównanie shadow starego i nowego modelu. Odczyt mapy zawsze może wrócić do ostatniego poprawnego snapshotu; nie wolno uruchamiać ciężkiej naprawy ani pełnej przebudowy w `GET /api/map/player-areas`.

Koordynacja przebudowy nie może opierać się na pamięci procesu. Przy wielu workerach Gunicorna kolejka, lease, deduplikacja i wersja żądania muszą być trwałe i współdzielone.

## Kolejność analizy kodu

Kod należy czytać w tej kolejności:

1. `detect_territory_conflicts()` — `run.py:4157`
2. `territory_conflict_key()` — `run.py:3989`
3. `build_contested_area()` — `run.py:3994`
4. `merge_conflict_target_statuses()` — `run.py:4109`
5. `capture_conflict_pillar()` — `run.py:4316`
6. `rebuild_conflict_polygons()` — `run.py:4293`
7. `TerritoryConflictStore` — `database.py:1763`
8. `/api/map/player-areas` — `run.py:19537`
9. `refreshPlayerAreas()` — `map_template.html:6989`

`un.py` z wcześniejszego odnośnika traktujemy jako literówkę — endpoint znajduje się w `run.py`.

---

# Sprint 130.8.1 — Stabilna tożsamość i lifecycle konfliktu

## Cel

Oddzielić tożsamość konfliktu od jego aktualnej geometrii, nie zmieniając jeszcze zachowania gameplayu ani sposobu renderowania mapy.

Po tym sprincie ponowne przeliczenie tych samych pól nie może tworzyć nowego konfliktu tylko dlatego, że zmieniły się wierzchołki polygonu.

## Problem obecnej implementacji

Obecny `territory_conflict_key()` buduje klucz z:

* właściciela pola,
* wszystkich wierzchołków pola,
* aktualnej kolejności i wartości współrzędnych.

Zmiana geometrii oznacza więc zmianę `conflict_key`.

W konsekwencji system może:

* utworzyć nowy rekord dla istniejącego konfliktu,
* oznaczyć poprzedni konflikt jako nieaktualny,
* utracić powiązanie z historią filarów,
* wygenerować kilka konfliktów reprezentujących ten sam spór.

## Zakres

### 1. Nowy kontrakt rekordu konfliktu

`TerritoryConflictStore` powinien przechowywać co najmniej:

* `conflict_id`,
* `conflict_key`,
* `legacy_conflict_key`,
* `participant_key`,
* `participants`,
* `status`,
* `conflict_version`,
* `geometry_version`,
* `geometry_status`,
* `created_at`,
* `updated_at`,
* `resolved_at`,
* `closed_at`,
* `last_actor_username`,
* `source_event`.

`conflict_id` jest trwałym identyfikatorem rekordu.

`participant_key` jest deterministyczną, posortowaną sygnaturą stron konfliktu. Nie może zawierać geometrii.

`legacy_conflict_key` może przechowywać stary klucz zależny od polygonów wyłącznie na potrzeby migracji i diagnostyki.

### 2. Lifecycle konfliktu

Wprowadzamy jawne statusy:

* `detected`,
* `active`,
* `changing`,
* `resolving`,
* `resolved`,
* `closed`.

W tym sprincie istniejący runtime może nadal używać głównie `active` i `resolved`, ale store oraz normalizatory muszą już akceptować pełny lifecycle.

### 3. Wersjonowanie

Każdy konflikt otrzymuje:

* `conflict_version`, początkowo `1`,
* `geometry_version`, początkowo `1` dla istniejącej opublikowanej geometrii.

`conflict_version` zwiększa się po zmianie domenowej.

`geometry_version` zwiększa się wyłącznie po opublikowaniu nowej geometrii.

Samo ponowne wykrycie identycznego stanu nie może zwiększać żadnej wersji.

### 4. Odszukiwanie trwającego konfliktu

`detect_territory_conflicts()` nie powinno już zaczynać od szukania rekordu wyłącznie przez klucz zawierający geometrię.

Detekcja powinna:

1. wyznaczyć uczestników,
2. zbudować `participant_key`,
3. poszukać aktywnego lub zmieniającego się konfliktu dla tej sygnatury,
4. zachować jego `conflict_id`,
5. dopiero potem zaktualizować bieżący opis geometrii.

Nowy `conflict_id` powstaje tylko wtedy, gdy:

* nie istnieje ciągły, niezakończony konflikt tych stron,
* poprzedni konflikt ma status `closed`,
* wykryto rzeczywiście nowy spór.

### 5. Migracja istniejących rekordów

Dla istniejących konfliktów należy:

* zachować dotychczasowe `id` jako `conflict_id`, jeżeli jest stabilne i unikalne,
* utworzyć `participant_key`,
* przenieść obecny `conflict_key` do `legacy_conflict_key`,
* ustawić brakujące wersje,
* ustawić poprawny lifecycle,
* nie usuwać historii ani obecnych targetów.

Migracja musi być idempotentna.

### 6. Zgodność przejściowa

Istniejące funkcje i endpointy nadal mogą otrzymywać:

* `id`,
* `conflict_key`,
* `intersection`,
* `intersections`,
* `targets`.

Nowe pola są dodawane obok starego kontraktu.

Frontend nie jest jeszcze zmieniany.

### 7. Ciągłość referencji i lifecycle legacy

`participant_key` służy do znalezienia kandydata konfliktu, ale nie jest samodzielnym globalnym identyfikatorem. Nie może połączyć nowego sporu z konfliktem już zamkniętym ani skleić niezależnych cykli konfliktu.

Migracja zachowuje aliasy pozwalające rozwiązać stare `conflict_key` i `id` w:

* aktywnych operacjach i incydentach,
* `aimed_target` i targetach mapowych,
* projekcji Victim Pickera i Territory Control,
* zdarzeniach, ledgerze i topologii GhostNetworku.

Stan `resolved_by_encirclement` nie może zostać zgubiony. W nowym lifecycle jest reprezentowany jako `status = resolved` z jawnym `resolution_reason = encirclement` albo przez zgodnościowy alias o identycznej semantyce.

## Testy

Należy dodać testy potwierdzające, że:

* zmiana wierzchołków nie zmienia `conflict_id`,
* zmiana kolejności pól nie zmienia `participant_key`,
* ponowna detekcja nie tworzy duplikatu,
* ponowna detekcja identycznego stanu nie zwiększa wersji,
* konflikt zamknięty nie jest ponownie otwierany,
* nowy spór po zamknięciu otrzymuje nowy `conflict_id`,
* migracja starych rekordów może zostać wykonana wielokrotnie,
* aktywna operacja i incydent nadal rozwiązują stare ID do tego samego konfliktu,
* konflikt rozwiązany przez otoczenie zachowuje przyczynę rozwiązania,
* migracja nie emituje ponownie nagród, komunikatów ani zdarzeń GhostNetworku.

## Kryteria zakończenia

Sprint jest zakończony, gdy:

* geometria nie uczestniczy w tworzeniu `conflict_id`,
* istniejący konflikt zachowuje identyfikator po przebudowie pól,
* stare payloady mapy nadal działają,
* gameplay przejmowania filarów nie został jeszcze zmieniony,
* nie występuje migracyjne tworzenie duplikatów.

## Poza zakresem

* osobna tabela filarów,
* fronty konfliktu,
* konsolidacja geometrii,
* zmiany w `refreshPlayerAreas()`,
* delty konfliktów stosowane bezpośrednio na mapie.

---

# Sprint 130.8.2 — Rejestr filarów i atomowe przejęcie

## Cel

Oddzielić stan filarów od geometrii i od głównego dokumentu konfliktu.

Po tym sprincie przejęcie filaru ma aktualizować jeden rekord filaru oraz wersję konfliktu, zamiast przeszukiwać i przepisywać całą listę `targets`.

## Problem obecnej implementacji

Obecne `capture_conflict_pillar()`:

* przegląda wszystkie aktywne konflikty,
* dopasowuje filar po współrzędnych,
* przebudowuje całą tablicę `targets`,
* ponownie zapisuje cały konflikt,
* po zapisie uruchamia pełną przebudowę polygonów uczestników.

Dodatkowo `merge_conflict_target_statuses()` zachowuje historię przejęcia przez dopasowanie pozycji, więc przesunięcie, zaokrąglenie lub zmiana etykiety może rozłączyć ten sam obiekt od jego wcześniejszego stanu.

## Zakres

### 1. Stabilny `target_id`

Każdy filar konfliktu musi posiadać stabilny `target_id`.

Źródłem `target_id` powinien być istniejący identyfikator gameplayowego obiektu, na przykład:

* `vulnerability_id`,
* identyfikator przejętego targetu,
* stabilny identyfikator POI,
* istniejący `build_operation_target_id()` jako kontrolowany fallback.

Współrzędne nie mogą być podstawowym identyfikatorem filaru.

### 2. Rejestr filarów konfliktu

W `TerritoryConflictStore` lub w osobnym store należy utworzyć rekord filaru zawierający:

* `conflict_id`,
* `target_id`,
* opcjonalny `front_id`,
* `owner_username`,
* `previous_owner_username`,
* `attacker_username`,
* `status`,
* `captured`,
* `captured_by`,
* `last_changed_version`,
* `geometry_applied_version`,
* `created_at`,
* `updated_at`,
* `captured_at`,
* snapshot publicznych danych targetu.

Unikalność:

```text
UNIQUE(conflict_id, target_id)
```

### 3. Migracja obecnych `targets`

Obecne elementy `conflict.targets` należy przenieść do rejestru filarów.

Migracja:

* ustala `target_id`,
* zachowuje właściciela i historię przejęcia,
* nie tworzy dwóch rekordów dla tego samego targetu,
* zostawia zgodnościową projekcję `targets` dla starego endpointu.

Po migracji tablica `targets` nie jest już źródłem prawdy.

### 4. Nowe zachowanie `merge_conflict_target_statuses()`

Funkcja nie powinna dalej scalać historii po współrzędnych.

Docelowo powinna zostać:

* zastąpiona projekcją rejestru filarów,
* albo ograniczona do zgodnościowej normalizacji starych danych.

Stan filaru jest pobierany po:

```text
conflict_id + target_id
```

### 5. Atomowe `capture_conflict_pillar()`

Operacja przejęcia wykonuje jedną transakcję:

1. odczytuje konflikt po `conflict_id`,
2. sprawdza, czy konflikt jest aktywny,
3. odczytuje filar po `target_id`,
4. weryfikuje aktualnego właściciela,
5. aktualizuje wyłącznie rekord filaru,
6. zwiększa `conflict_version`,
7. ustawia konflikt na `changing`,
8. ustawia `geometry_status = dirty`,
9. zapisuje zdarzenie przejęcia,
10. rejestruje jedno żądanie przebudowy.

Operacja nie może wykonywać bezpośrednio pełnej pętli przebudowy wszystkich uczestników.

### 6. Idempotencja przejęcia

Przejęcie musi posiadać `action_id`, `receipt_id` albo deterministyczny klucz operacji.

Ponowienie tej samej operacji:

* zwraca wcześniejszy wynik,
* nie podbija wersji,
* nie dopisuje drugiej historii,
* nie emituje drugiego zdarzenia,
* nie uruchamia drugiej przebudowy.

### 7. Zdarzenia domenowe

Minimalny zestaw:

* `conflict.pillar_registered`,
* `conflict.pillar_captured`,
* `conflict.pillar_recaptured`,
* `conflict.updated`,
* `conflict.rebuild_requested`.

Każde zdarzenie zawiera:

* `conflict_id`,
* `target_id`,
* `conflict_version`,
* `geometry_version`,
* `actor_username`,
* `event_id`.

### 8. Zgodnościowa projekcja

Stare miejsca korzystające z `conflict.targets` otrzymują listę zbudowaną z rejestru filarów.

Nie wolno utrzymywać dwóch niezależnych źródeł prawdy.

### 9. Niezmienniki gameplayu filaru

Rejestr filarów przechowuje również stabilne dane potrzebne przez istniejący runtime: `source_type`, źródłowy identyfikator targetu, `foreign_area_id`, właściciela klastra, pozycję oraz publiczny snapshot etykiety. Zmiana `front_id` nie zmienia `target_id`.

Przejęcie filaru nie może skracać ścieżki gameplayowej. Nadal obowiązują:

* kolejne etapy narzędzi i kropki `actions_allowed`,
* aktualizacja zabezpieczeń oraz prawdy celu,
* utworzenie i zakończenie właściwej operacji,
* pojedynczy efekt pliku, nagrody, RSP i wiadomości,
* odbicie filaru przez drugą stronę.

Aktywne operacje rozpoczęte przed migracją muszą zakończyć się na tym samym `target_id`. Ponowienie requestu, replay zdarzenia albo recapture nie może podwoić efektów gameplayowych.

## Testy

Należy sprawdzić:

* przejęcie filaru po `target_id`,
* brak zależności od etykiety i współrzędnych,
* ponowienie tego samego przejęcia,
* próbę przejęcia już przejętego filaru,
* odbicie filaru,
* aktualizację tylko jednego rekordu,
* dokładnie jeden wzrost `conflict_version`,
* brak zmiany `geometry_version`,
* ustawienie `geometry_status = dirty`,
* jedną emisję `conflict.rebuild_requested`,
* zachowanie filaru po przesunięciu go między frontami albo poza bieżący overlap,
* pełny cykl czterech etapów hackowania z mapy, terminala i pulpitu,
* zachowanie aktywnej operacji przez migrację rejestru,
* brak podwójnych plików, nagród, RSP i komunikatów po retry lub recapture,
* poprawny kandydat `territory_contest` w Victim Pickerze.

## Kryteria zakończenia

Sprint jest zakończony, gdy:

* filary posiadają własny rejestr,
* `conflict.targets` jest tylko projekcją,
* przejęcie filaru jest atomowe i idempotentne,
* przejęcie nie uruchamia bezpośrednio starej wielokrotnej pętli detekcji,
* geometria może chwilowo pozostać w poprzedniej wersji, ale konflikt jawnie informuje, że wymaga przebudowy.

## Poza zakresem

* docelowe fronty,
* podział i łączenie frontów,
* atomowy snapshot geometrii,
* bezpośrednie aktualizacje warstw mapy.

## Status implementacji

Status: zrealizowany.

Implementacja pozostaje zgodna z kontraktami `clans_machines.md` oraz
`ghostnetwork_architecture.md` i nie rozpoczyna zakresu Sprintu 130.8.3.

Wdrożono:

* kanoniczny rejestr `territory_conflict_pillars` z unikalnością
  `(conflict_id, target_id)` oraz zgodnościową projekcją `conflict.targets`;
* idempotentną migrację legacy `targets`, zachowującą właściciela, historię
  przejęcia, publiczny snapshot oraz stabilny `target_id`;
* scalanie stanu wyłącznie po `target_id`; zmiana współrzędnych lub etykiety
  nie zmienia tożsamości filaru ani nie cofa przejęcia;
* atomowe przejęcie i odbicie pojedynczego filaru z jednym wzrostem
  `conflict_version`, bez zmiany `geometry_version`;
* ustawienie konfliktu na `changing`, geometrii na `dirty` oraz pojedyncze
  zdarzenie `conflict.rebuild_requested`;
* receipt oparty na jawnej tożsamości akcji. Retry tej samej akcji jest
  no-op, natomiast późniejsze prawdziwe odbicie bez `action_id` nie jest
  blokowane trwałym, sztucznym kluczem;
* zapis stanu filaru przed przebudową terytorium w ścieżce `/gonna-win`, aby
  spóźniony snapshot geometrii nie mógł przywrócić starego właściciela;
* zdarzenia `conflict.pillar_registered`, `conflict.pillar_captured`,
  `conflict.pillar_recaptured`, `conflict.updated` i
  `conflict.rebuild_requested`.

Testy kontraktu obejmują dokładne przejęcie po `target_id`, niezależność od
współrzędnych, retry, próbę ponownego przejęcia już posiadanego filaru,
recapture, ochronę przed cofnięciem stanu przez stary snapshot geometrii,
wersjonowanie oraz liczbę żądań przebudowy.

---

# Sprint 130.8.3 — Konsolidacja geometrii, fronty i atomowy snapshot

## Cel

Zastąpić wielokrotne przebudowy jedną skonsolidowaną operacją dla konkretnego konfliktu.

Po tym sprincie seria zmian filarów ma prowadzić do jednej publikacji spójnej geometrii.

## Problem obecnej implementacji

Obecne `rebuild_conflict_polygons()`:

1. przebudowuje pola każdego uczestnika,
2. pobiera jeden wspólny zestaw obszarów,
3. uruchamia `detect_territory_conflicts()` osobno dla każdego uczestnika.

Ta sama geometria może być więc analizowana wiele razy, a każdy przebieg może:

* wykonać `upsert`,
* opublikować deltę,
* dezaktywować konflikt uznany chwilowo za stary,
* zapisać inną wersję targetów.

## Zakres

### 1. Koordynator przebudowy

Wprowadzamy pojedynczy punkt wejścia, przykładowo:

```text
request_conflict_rebuild(conflict_id, reason, requested_version)
consolidate_conflict_rebuild(conflict_id)
```

Koordynator:

* deduplikuje żądania,
* nie pozwala na dwie równoległe przebudowy tego samego konfliktu,
* zapamiętuje najwyższą żądaną `conflict_version`,
* wykonuje jedną przebudowę,
* uruchamia kolejny przebieg tylko wtedy, gdy podczas pracy pojawiła się nowsza zmiana.

### 2. Jedna detekcja po serii zmian

Nie wykonujemy `detect_territory_conflicts()` osobno dla każdego uczestnika.

Przebudowa:

1. pobiera konflikt,
2. blokuje jego wersję wejściową,
3. pobiera aktualnych uczestników i filary,
4. przebudowuje wymagane pola graczy,
5. pobiera obszary jeden raz,
6. buduje graf przecięć jeden raz,
7. wyznacza wszystkie fronty konfliktu,
8. zapisuje wynik jako jeden snapshot.

### 3. Oddzielenie detekcji od publikacji

`build_contested_area()` pozostaje funkcją geometryczną.

Nie może:

* tworzyć konfliktu,
* zmieniać lifecycle,
* zapisywać filarów,
* emitować delt.

`detect_territory_conflicts()` powinno zwracać wynik detekcji albo plan zmian.

Dopiero warstwa domenowa decyduje:

* czy kontynuować konflikt,
* czy utworzyć nowy konflikt,
* czy zamknąć front,
* czy rozwiązać konflikt.

### 4. Rekordy frontów

Każdy konflikt może posiadać wiele frontów.

Rekord frontu przechowuje:

* `front_id`,
* `conflict_id`,
* `status`,
* `geometry_version`,
* `participant_key`,
* `area_ids`,
* `pillar_ids`,
* `geometry`,
* `parent_front_ids`,
* `created_at`,
* `updated_at`,
* `closed_at`.

Front zachowuje `front_id`, jeżeli nowa geometria jest ciągłą aktualizacją tego samego obszaru sporu.

Jeżeli front:

* dzieli się — staremu frontowi nadajemy status `split`, a nowe fronty wskazują `parent_front_ids`,
* łączy się — stare fronty otrzymują status `merged`, a nowy front wskazuje ich identyfikatory,
* znika — otrzymuje status `closed`.

### 5. Dopasowanie frontów

Dopasowanie starego i nowego frontu może korzystać z geometrii, ale geometria nie może być identyfikatorem.

Należy porównać między innymi:

* uczestników,
* powiązane `area_ids`,
* powiązane `target_id`,
* stopień nakładania geometrii,
* ciągłość z poprzednią wersją.

Indeks tablicy nie jest tożsamością frontu.

### 6. Atomowy snapshot

Publikowany snapshot konfliktu zawiera:

* rekord konfliktu,
* aktywne fronty,
* filary,
* geometrie,
* `conflict_version`,
* `geometry_version`,
* `snapshot_version`,
* `generated_at`.

Zapis snapshotu jest atomowy.

Dopiero po poprawnym zapisie:

* zwiększamy `geometry_version`,
* ustawiamy `geometry_status = clean`,
* zmieniamy `resolving` na `active`,
* publikujemy deltę.

Jeżeli przebudowa zakończy się błędem:

* poprzedni snapshot pozostaje aktywny,
* `geometry_version` nie rośnie,
* konflikt pozostaje `changing` albo otrzymuje `rebuild_failed`,
* nowe żądanie może ponowić przebudowę.

### 7. Zakończenie konfliktu

Brak polygonu w jednym nieudanym przebiegu nie zamyka konfliktu.

Konflikt przechodzi do `resolved` dopiero po poprawnie zakończonej konsolidacji potwierdzającej, że:

* nie istnieje żaden aktywny front,
* strony nie posiadają już wspólnego obszaru sporu,
* warunki konfliktu rzeczywiście wygasły.

### 8. Publikowane zdarzenia

Minimalny zestaw:

* `conflict.rebuild_started`,
* `conflict.front_created`,
* `conflict.front_updated`,
* `conflict.front_split`,
* `conflict.front_merged`,
* `conflict.front_closed`,
* `conflict.geometry_rebuilt`,
* `conflict.rebuild_failed`,
* `conflict.resolved`.

### 9. Trwały koordynator dla wielu workerów

Żądania przebudowy, lease wykonawcy, najwyższa oczekująca wersja i deduplikacja muszą być zapisane w trwałym store. Dwa workery nie mogą równolegle publikować geometrii tej samej wersji, a śmierć workera nie może na stałe zablokować konfliktu.

Koordynator działa poza endpointem odczytowym mapy. Brak gotowej nowej geometrii oznacza publikację ostatniego poprawnego snapshotu z informacją o stanie `dirty/changing`, a nie ciężki fallback w requestcie.

### 10. Otoczenie, relacje chronione i własność

Konsolidacja po zmianie terytorium uruchamia dokładnie jeden przebieg reguł otoczenia. Musi zachować:

* ochronę pól znajomych i członków tego samego klanu,
* atomowy transfer pełnego klastra po rzeczywistym otoczeniu,
* usunięcie wkładu rozwiązanych frontów i konfliktów,
* `resolution_reason = encirclement`,
* jedną deltę, audit i zestaw powiadomień.

Obszar sporny pozostaje nakładką. Nie wolno odejmować go od kanonicznego pola właściciela przed poprawnym przejęciem albo rozwiązaniem konfliktu.

### 11. Budżet wydajności i zdarzenia downstream

Detekcja ogranicza kandydatów przestrzennie do zmienionych klastrów i ich sąsiedztwa. Nie wykonuje pełnego porównania wszystkich pól świata dla każdego filaru. Należy mierzyć czas detekcji, budowy grafu, konsolidacji i publikacji snapshotu.

Zdarzenia zachowują stabilne identyfikatory dla Territory Control, incydentów i GhostNetworku. Replay albo scalanie frontów nie może tworzyć drugiego wpisu ledgeru, sygnału BlackNetu ani nagrody.

## Testy

Należy sprawdzić:

* wiele żądań przebudowy tego samego konfliktu,
* dwie zmiany filarów podczas jednej przebudowy,
* jedną publikację dla jednej wersji,
* brak równoległych przebudów,
* wzrost `geometry_version` dopiero po sukcesie,
* pozostawienie starego snapshotu po błędzie,
* przesunięcie istniejącego frontu,
* podział jednego frontu na dwa,
* połączenie dwóch frontów,
* zamknięcie frontu,
* brak fałszywego rozwiązania konfliktu po błędzie geometrii,
* wyścig dwóch workerów i przejęcie wygasłego lease,
* deduplikację wielu żądań tej samej oraz kolejnych wersji,
* chronioną relację klan/znajomy i pełne otoczenie obcego klastra,
* pozostawienie kanonicznej własności podczas aktywnego sporu,
* brak podwójnych zdarzeń GhostNetworku i incydentów,
* czas konsolidacji dla dużego konfliktu w ustalonym budżecie.

## Kryteria zakończenia

Sprint jest zakończony, gdy:

* `rebuild_conflict_polygons()` nie wykonuje detekcji osobno dla każdego uczestnika,
* istnieje jedna konsolidacja na konflikt i wersję,
* fronty posiadają stabilne identyfikatory,
* geometria i filary są publikowane w jednym snapshotcie,
* poprzednia poprawna geometria przeżywa błąd przebudowy,
* nie występują wielokrotne delty tego samego wyniku.

## Poza zakresem

* docelowy patch warstw Leaflet,
* bezpośrednie stosowanie wszystkich delt na froncie,
* usuwanie starego formatu payloadu endpointu.

## Decision po realizacji

Status: complete / backend foundation.

Wdrożono trwały, wersjonowany koordynator przebudowy konfliktu z deduplikacją
żądań, wyłącznym lease, przejęciem wygasłego lease i ponownym przebiegiem tylko
dla nowszej oczekującej wersji. Seria zmian przebudowuje pola uczestników,
pobiera obszary i buduje plan detekcji jeden raz, a następnie publikuje każdy
konflikt przez atomowy snapshot magazynu.

Fronty otrzymały stabilne `front_id`, historię rodziców oraz stany
`split`, `merged` i `closed`. Publikacja no-op nie podnosi wersji i nie emituje
drugiego zdarzenia. Błąd przebudowy pozostawia ostatni poprawny snapshot i nie
podnosi `geometry_version`. Reguły otoczenia uruchamiane są raz po całej serii,
z zachowaniem ochrony znajomych i członków klanu.

Koordynator zwraca pomiary faz: przebudowa uczestników, pobranie obszarów,
detekcja, przygotowanie frontów, publikacja oraz czas całkowity. Zachowano
zgodność z `clans_machines.md` i `ghostnetwork_architecture.md`: konflikt jest
nakładką na kanoniczną własność, a GhostNetwork otrzymuje wyłącznie stabilne
zdarzenia po udanej publikacji.

Frontend, endpoint mapy i warstwy Leaflet nie zostały przełączone. Cutover i
recovery po stabilnych identyfikatorach pozostają zakresem Sprintu 130.8.4.

---

# Sprint 130.8.4 — Projekcja API, delty i stabilne warstwy mapy

## Cel

Przestawić `/api/map/player-areas` i `refreshPlayerAreas()` na spójny, wersjonowany snapshot konfliktów oraz aktualizację warstw po stabilnych identyfikatorach.

Po tym sprincie zmiana jednego frontu lub filaru nie może powodować migania i pełnego kasowania wszystkich warstw konfliktów.

## Problem obecnej implementacji

Obecny frontend:

* po `territory.conflict_changed` nie aktualizuje konfliktu,
* uruchamia pełny snapshot recovery,
* podczas każdego `refreshPlayerAreas()` usuwa wszystkie obszary konfliktów,
* usuwa wszystkie markery contested i captured,
* tworzy warstwy ponownie,
* identyfikuje strefę jako `conflict_id:index`.

Indeks nie jest stabilny. Po zmianie kolejności tablic frontend może uznać istniejący front za nowy.

## Zakres

### 1. Kontrakt snapshotu endpointu

`/api/map/player-areas` pozostaje endpointem tylko do odczytu.

Nie może:

* wykrywać konfliktów,
* przebudowywać geometrii,
* zmieniać lifecycle,
* naprawiać targetów podczas odczytu.

Endpoint pobiera ostatni opublikowany snapshot.

Minimalny kontrakt konfliktu:

```json
{
  "conflict_id": "conflict_...",
  "status": "active",
  "conflict_version": 14,
  "geometry_version": 8,
  "snapshot_version": 22,
  "participants": [],
  "fronts": [],
  "pillars": [],
  "generated_at": "..."
}
```

Minimalny kontrakt frontu:

```json
{
  "front_id": "front_...",
  "conflict_id": "conflict_...",
  "status": "active",
  "geometry_version": 8,
  "geometry": [],
  "participant_ids": [],
  "pillar_ids": []
}
```

Minimalny kontrakt filaru:

```json
{
  "target_id": "target_...",
  "conflict_id": "conflict_...",
  "front_id": "front_...",
  "status": "captured",
  "owner_username": "...",
  "previous_owner_username": "...",
  "last_changed_version": 14,
  "target": {}
}
```

### 2. Zgodność payloadu

Przez okres przejściowy endpoint może nadal zwracać:

* `territory_conflicts`,
* `conflict_areas`,
* `revealed_conflict_targets`,
* `captured_conflict_pillars`.

Pola te muszą być jednak generowane z jednego snapshotu.

Nie wolno osobno odczytywać filarów, frontów i geometrii z różnych wersji.

### 3. Rejestry frontendowe

Frontend utrzymuje osobne rejestry:

```text
territoryConflictRegistry[conflict_id]
territoryFrontLayers[front_id]
territoryConflictPillarLayers[target_id]
```

Nie używamy już:

```text
conflict_id:index
```

jako tożsamości warstwy.

### 4. Aktualizacja frontów

Dla każdego frontu frontend wykonuje:

* brak lokalnej warstwy — tworzy warstwę,
* istnieje warstwa i wersja jest nowsza — wywołuje `setLatLngs()`,
* wersja jest identyczna — nic nie robi,
* snapshot jest starszy — odrzuca zmianę,
* status `closed` — usuwa wskazany `front_id`.

Nie wolno usuwać wszystkich warstw przed rozpoczęciem aktualizacji.

### 5. Aktualizacja filarów

Markery filarów są aktualizowane po `target_id`.

Zmiana właściciela:

* zmienia styl istniejącego markera,
* aktualizuje tooltip,
* zachowuje tę samą instancję warstwy, jeżeli pozycja się nie zmieniła.

Usunięcie filaru następuje tylko po jawnej informacji:

* `removed`,
* `detached`,
* `resolved`.

### 6. Obsługa delt

`territory.conflict_changed` nie powinno automatycznie oznaczać pełnego recovery.

Delta powinna zawierać:

* `conflict_id`,
* `conflict_version`,
* `geometry_version`,
* `snapshot_version`,
* rodzaj zmiany,
* zmienione fronty,
* zmienione filary,
* zamknięte identyfikatory.

Frontend stosuje deltę, jeżeli posiada wymagany poprzedni stan.

Recovery snapshotu jest uruchamiane tylko wtedy, gdy:

* brakuje konfliktu lub frontu wymaganego przez deltę,
* wykryto lukę wersji,
* payload jest niepełny,
* lokalna wersja jest spoza retencji,
* backend jawnie zwrócił `recovery_required`.

### 7. Monotoniczność wersji

Frontend przechowuje ostatnie wersje per konflikt.

Odrzuca:

* starszy `conflict_version`,
* starszy `geometry_version`,
* starszy `snapshot_version`.

Nowy stan domenowy z niezmienioną geometrią może zaktualizować filary bez ruszania polygonu.

### 8. Zachowanie UI

Aktualizacja konfliktu nie może:

* zmienić środka ani zoomu mapy,
* zamknąć niezwiązanego tooltipa,
* usunąć zaznaczenia konfliktu,
* resetować wszystkich animacji,
* powodować migania wszystkich polygonów,
* kasować markerów niezwiązanych z konfliktem.

### 9. Usunięcie starej ścieżki

Po przejściu testów należy usunąć:

* pełne czyszczenie `conflictAreaLayers` przy każdej zmianie konfliktu,
* indeks jako część identyfikatora frontu,
* automatyczny snapshot recovery dla każdej delty konfliktu,
* martwy kod znajdujący się po `return` w pętlach renderujących terytoria i konflikty.

Pełne czyszczenie może pozostać wyłącznie jako jawny tryb recovery lub inicjalny bootstrap mapy.

### 10. Konsumenci poza Leafletem

Przełączenie projekcji obejmuje test zgodności wszystkich istniejących konsumentów:

* Victim Picker nadal pokazuje filary i innery jako `territory_contest`,
* Territory Control pokazuje prawdziwe ALARM/KOLIZJA i liczniki per klaster,
* Operation Control zachowuje odwołania aktywnych operacji i incydentów,
* `aimed_target` i pasek CEL nie cofają się do nieaktualnego konfliktu,
* GhostNetwork, BlackNet, Cyberner, Radio i outbox otrzymują jeden spójny wynik bez duplikatów.

### 11. Cutover, recovery i bezpieczeństwo bootu

Nowa projekcja jest najpierw uruchamiana w trybie shadow i porównywana ze starą pod kątem liczby konfliktów, frontów, filarów, właścicieli oraz stanów przejęcia. Cutover następuje dopiero po zgodności scenariuszy gameplayowych.

Brudny albo nieudany rebuild nie blokuje bootu mapy. Endpoint zwraca ostatni poprawny snapshot i jawny stan świeżości. Rollback feature flagi nie usuwa nowych danych i pozwala wrócić do starej projekcji bez utraty postępu.

## Testy

Należy sprawdzić:

* inicjalny bootstrap mapy,
* aktualizację jednego frontu,
* dodanie frontu,
* zamknięcie frontu,
* zmianę stanu jednego filaru,
* przejęcie i odbicie filaru,
* odrzucenie starszego snapshotu,
* wykrycie luki wersji,
* recovery po brakującej warstwie,
* zachowanie zoomu i środka mapy,
* brak migania pozostałych konfliktów,
* brak duplikatów po snapshot + delta,
* mapę desktopową i mobilną,
* Victim Picker i wszystkie etapy `territory_contest`,
* flagi i liczniki Territory Control,
* aktywną operację podczas cutoveru i recovery,
* pełne otoczenie klastra oraz relację chronioną,
* ciągłość GhostNetworku i brak podwójnego RSP,
* ostatni poprawny snapshot po błędzie rebuilda,
* boot mapy podczas stanu `dirty/changing`,
* shadow compare oraz rollback feature flagi.

## Kryteria zakończenia

Sprint jest zakończony, gdy:

* endpoint publikuje jeden spójny snapshot konfliktów,
* frontend używa `conflict_id`, `front_id` i `target_id`,
* normalna delta nie powoduje pełnego odświeżenia mapy,
* warstwy są aktualizowane, a nie kasowane i tworzone od początku,
* starsze wersje są odrzucane,
* pełny snapshot służy bootstrapowi i recovery, a nie każdej zmianie.

## Realizacja Sprintu 130.8.4

Status: zakończony.

Wdrożono:

* `/api/map/player-areas` jest ścieżką tylko do odczytu i pobiera ostatnie
  opublikowane, atomowe snapshoty konfliktów bez detekcji, przebudowy,
  `sync_session_profile()` ani naprawiania świata podczas requestu;
* endpoint publikuje kanoniczne `territory_conflict_snapshots`, a przejściowe
  pola legacy generuje z dokładnie tych samych snapshotów;
* dodano flagę cutoveru pozwalającą wrócić do starej projekcji bez usuwania
  nowych danych i bez utraty postępu;
* frontend utrzymuje rejestry po `conflict_id`, `front_id` i `target_id`,
  aktualizuje istniejące warstwy przez `setLatLngs()` i `setLatLng()` oraz
  usuwa wyłącznie jawnie zamknięte lub brakujące elementy konfliktu;
* delta `territory.conflict_changed` przenosi kompletny snapshot i aktualizuje
  tylko wskazany konflikt; starsze wersje snapshotu, domeny i geometrii są
  odrzucane, a recovery uruchamia się dla luki albo niepełnego payloadu;
* zachowano kompatybilność Victim Pickera, Territory Control, Operation
  Control i konsumentów GhostNetworku przez wspólną projekcję legacy;
* zwykła delta nie zmienia środka ani zoomu mapy i nie wykonuje pełnego
  kasowania kanonicznych warstw konfliktów.

Walidacja:

* sprawdzono zgodność z `clans_machines.md` oraz
  `ghostnetwork_architecture.md`: konflikt nadal jest nakładką, a read model
  nie zmienia kanonicznej własności ani lifecycle;
* `python -m py_compile database.py run.py response_network/territory_delta.py`:
  OK;
* 42 testy identity, Territory Control, territory delta i map cutover: OK;
* testy obejmują spójność snapshotu i pól legacy, read-only endpoint,
  kompletność delty, stabilne rejestry, wersjonowanie oraz recovery;
* nie wykonano commita ani deployu.

---

# Reguły obowiązujące we wszystkich czterech sprintach

## Brak lokalnych protez

Nie dodawać nowych wyjątków opartych na:

* współrzędnych jako tożsamości,
* kolejności elementów tablicy,
* etykiecie targetu,
* aktualnym polygonie,
* indeksie frontu,
* ponownym dopisywaniu przejętego targetu do całego dokumentu konfliktu.

## Read model nie zmienia świata

`/api/map/player-areas` pozostaje ścieżką tylko do odczytu.

Naprawy, migracje, detekcja i przebudowy mają działać przed publikacją snapshotu, a nie podczas otwierania mapy.

## Zachowanie źródła prawdy

Źródłami prawdy są:

* rekord konfliktu,
* rejestr frontów,
* rejestr filarów,
* opublikowany snapshot.

Warstwa Leaflet jest wyłącznie projekcją.

## Kolejność wersji

Po przejęciu filaru:

```text
conflict_version += 1
geometry_version bez zmiany
geometry_status = dirty
```

Po udanej konsolidacji:

```text
geometry_version += 1
snapshot_version += 1
geometry_status = clean
```

Po błędzie konsolidacji:

```text
geometry_version bez zmiany
poprzedni snapshot pozostaje aktywny
```

## Granica całego refaktoru

Po Sprincie 130.8.4 nie powinien pozostać mechanizm, w którym:

```text
aktualna geometria
→ tworzy tożsamość konfliktu
→ odtwarza historię filarów
→ decyduje o lifecycle
→ wymusza pełny rerender mapy
```

Docelowy przepływ powinien wyglądać tak:

```text
zmiana filaru lub terytorium
→ aktualizacja domeny konfliktu
→ wzrost conflict_version
→ jedno żądanie konsolidacji
→ nowy atomowy snapshot
→ wzrost geometry_version
→ delta po stabilnych identyfikatorach
→ punktowa aktualizacja mapy
```


# Sprint 130.8.5 — Conflict Contract Hardening

## Cel sprintu

Domknąć kontrakt konfliktów terytorialnych po wdrożeniu Sprintów `130.8.1–130.8.4`.

Sprint nie przebudowuje ponownie domeny konfliktów i nie zmienia zasad gameplayu. Jego zadaniem jest usunięcie pozostałych nieszczelności pomiędzy:

* stabilną tożsamością konfliktu,
* aktualnym stanem filarów,
* opublikowanym snapshotem,
* deltami wysyłanymi do klientów,
* recovery frontendu,
* wersją kodu rzeczywiście działającą na workerach.

Po zakończeniu sprintu konflikt musi zachowywać ten sam `conflict_id` przez cały aktywny cykl, a frontend musi zawsze otrzymywać jednoznaczną informację, czy przekazany stan jest kompletny, aktualny i bezpieczny do zastosowania.

---

## Stan wejściowy

Kod się kompiluje, a podstawowe testy konfliktów, mapy i Territory Control przechodzą.

Potwierdzone lokalnie:

* `python -m py_compile database.py run.py response_network\territory_delta.py`
* `python -m unittest tests.test_territory_conflict_identity tests.test_territory_conflict_map_cutover tests.test_territory_control`
* 37 testów zakończonych powodzeniem,
* `git diff --check` bez błędów,
* wyłącznie ostrzeżenie o zmianie końców linii `CRLF → LF` w `templates/map_template.html`.

Rdzeń refaktoru jest poprawny, ale pozostały cztery realne nieszczelności kontraktu:

1. delta po przejęciu filaru może publikować stary snapshot,
2. wybór otwartego konfliktu nadal może zależeć od geometrii,
3. snapshot zawsze deklaruje `complete: true`,
4. deduplikacja delt używa `conflict_key` zamiast `conflict_id`.

---

# 1. Świeża delta po przejęciu filaru

## Problem

`record_territory_conflict_delta()` próbuje najpierw pobrać `latest_snapshot(reference)`.

Jeżeli filar został właśnie przejęty, konflikt może już posiadać:

* nowy `conflict_version`,
* stan `changing`,
* `geometry_status = dirty`,
* zaktualizowany rekord filaru,

ale ostatni opublikowany snapshot nadal przedstawia poprzednią geometrię i poprzedni stan filarów.

W takim przypadku delta może wysłać frontendowi stary snapshot jako bieżący.

Objawy:

* zhakowany filar znika z mapy,
* marker wraca do poprzedniego stanu,
* stara geometria pozostaje do ponownego otwarcia mapy,
* frontend nie wie, że otrzymał stan sprzed przejęcia.

## Wymagane zachowanie

Delta konfliktu musi rozróżniać:

* aktualny stan domenowy,
* ostatnią poprawną geometrię,
* ostatni kompletny snapshot.

Po przejęciu filaru delta powinna zawierać aktualny stan filaru i aktualną wersję konfliktu nawet wtedy, gdy geometria nie została jeszcze przebudowana.

Nie wolno przedstawiać starego snapshotu jako aktualnego kompletnego stanu.

## Zakres implementacji

`record_territory_conflict_delta()` powinno:

1. odczytać aktualny rekord konfliktu,
2. odczytać aktualne filary z rejestru po `conflict_id`,
3. porównać `conflict_version` ze snapshotem,
4. sprawdzić `geometry_status`,
5. określić kompletność payloadu,
6. dopiero wtedy zdecydować, czy użyć:

   * pełnego aktualnego snapshotu,
   * domenowej delty z ostatnią poprawną geometrią,
   * sygnału `recovery_required`.

Jeżeli snapshot ma starszy `conflict_version` niż aktualny konflikt:

* nie może zostać opublikowany jako `complete`,
* jego geometria może zostać dołączona wyłącznie jako `last_valid_geometry`,
* aktualne filary muszą pochodzić z rejestru filarów,
* payload musi informować, że rebuild jest w toku.

## Docelowy kontrakt delty po capture

Payload powinien zawierać co najmniej:

* `conflict_id`,
* `conflict_version`,
* `geometry_version`,
* `snapshot_version`,
* `status`,
* `geometry_status`,
* `complete`,
* `recovery_required`,
* `changed_pillars`,
* `fronts`,
* `last_valid_geometry`,
* `reason`.

Przykładowa semantyka:

* `complete: false`,
* `geometry_status: dirty`,
* `recovery_required: false`,
* aktualny filar w `changed_pillars`,
* ostatnia poprawna geometria pozostaje widoczna,
* frontend oczekuje na późniejszą deltę `geometry_rebuilt`.

Frontend nie powinien usuwać aktualnej geometrii tylko dlatego, że snapshot domenowy jest niekompletny.

---

# 2. Stabilne wybieranie otwartego konfliktu

## Problem

`select_open_conflict()` nadal próbuje odnaleźć konflikt głównie przez:

* `conflict_key`,
* `area_ids`,
* referencje zależne od aktualnej geometrii.

Jeżeli po zmianie terytoriów nie ma dopasowania po tych polach, funkcja może zwrócić `None`, mimo że istnieje aktywny konflikt tych samych uczestników.

Może to spowodować:

* utworzenie nowego `conflict_id`,
* rozdzielenie historii jednego konfliktu,
* utratę ciągłości filarów,
* duplikaty aktywnych konfliktów,
* błędne rozdzielenie zdarzeń i snapshotów.

## Wymagane zachowanie

Otwarty konflikt musi być wybierany przede wszystkim po stabilnej tożsamości domenowej.

Kolejność dopasowania:

1. jawny `conflict_id`,
2. aktywny `participant_key`,
3. ciągłość lifecycle konfliktu,
4. dopiero pomocniczo `conflict_key`,
5. pomocniczo `area_ids`,
6. pomocniczo sygnatura geometrii.

Geometria i aktualne `area_ids` nie mogą być warunkiem zachowania istniejącego `conflict_id`.

## Reguły `participant_key`

`participant_key`:

* zawiera posortowanych uczestników,
* nie zawiera wierzchołków polygonu,
* nie zawiera `area_ids`,
* nie zależy od kolejności wejścia,
* nie zmienia się przy przesunięciu granicy,
* nie zmienia się po przejęciu filaru.

Przykładowa postać:

`player_a::player_b`

Dla konfliktu wielostronnego:

`player_a::player_b::player_c`

## Zasady wyboru konfliktu

`select_open_conflict()` powinno zwrócić istniejący konflikt, jeżeli:

* status konfliktu jest jednym z:

  * `detected`,
  * `active`,
  * `changing`,
  * `resolving`,
* `participant_key` jest zgodny,
* konflikt nie został jawnie zamknięty,
* nie istnieje nowszy otwarty cykl dla tych samych uczestników.

Nowy konflikt może zostać utworzony dopiero wtedy, gdy:

* poprzedni konflikt ma status `closed`,
* poprzedni cykl został faktycznie zakończony,
* nie istnieje żaden otwarty konflikt o tym samym `participant_key`.

## Ochrona przed duplikatami

Store powinien zabezpieczać sytuację, w której dwa workery jednocześnie próbują utworzyć konflikt dla tych samych uczestników.

Wymagane jest trwałe zabezpieczenie bazodanowe, na przykład:

* unikalny indeks dla otwartego `participant_key`,
* transakcja z ponownym odczytem po konflikcie zapisu,
* blokada lub compare-and-swap na poziomie store.

Blokada wyłącznie w pamięci procesu nie wystarcza przy wielu workerach.

---

# 3. Prawdziwy status kompletności snapshotu

## Problem

`project_territory_conflict_snapshot()` zawsze zwraca:

`complete: true`

Nawet jeżeli konflikt jest:

* `changing`,
* `resolving`,
* `dirty`,
* po nieudanym rebuildzie,
* ze snapshotem starszym od bieżącego `conflict_version`.

Frontend posiada mechanizm recovery dla niekompletnego stanu, ale backend praktycznie nie dostarcza mu poprawnego sygnału.

## Wymagane zachowanie

`complete` musi być wartością wyliczaną z rzeczywistego stanu konfliktu.

Snapshot jest kompletny tylko wtedy, gdy:

* posiada rekord konfliktu,
* posiada wszystkie aktywne fronty,
* posiada wszystkie aktualne filary,
* snapshot odpowiada bieżącemu `conflict_version`,
* geometria odpowiada zadeklarowanemu `geometry_version`,
* `geometry_status = clean`,
* rebuild nie jest w toku,
* ostatnia przebudowa nie zakończyła się błędem,
* snapshot został atomowo opublikowany.

## Minimalne pola diagnostyczne

Snapshot powinien zawierać:

* `complete`,
* `geometry_status`,
* `rebuild_status`,
* `recovery_required`,
* `last_valid_snapshot_version`,
* `last_valid_geometry_version`,
* `current_conflict_version`,
* `snapshot_conflict_version`,
* `rebuild_requested_version`,
* `rebuild_error`,
* `generated_at`.

## Przykładowe stany

### Stan kompletny

* `complete: true`
* `geometry_status: clean`
* `recovery_required: false`
* `snapshot_conflict_version == conflict_version`

### Capture przed rebuildem

* `complete: false`
* `geometry_status: dirty`
* `recovery_required: false`
* aktualne filary są dostępne
* ostatnia poprawna geometria pozostaje dostępna

### Rebuild w toku

* `complete: false`
* `geometry_status: rebuilding`
* `recovery_required: false`
* frontend zachowuje ostatnią poprawną geometrię

### Rebuild zakończony błędem

* `complete: false`
* `geometry_status: failed`
* `recovery_required` zależy od dostępności poprzedniego snapshotu
* `last_valid_snapshot` pozostaje aktywny

### Brak spójnego snapshotu

* `complete: false`
* `recovery_required: true`
* frontend uruchamia pełne recovery

## Zachowanie frontendu

Frontend nie może interpretować `complete: false` jako polecenia natychmiastowego usunięcia konfliktu.

Powinien:

* zastosować aktualne zmiany filarów,
* zachować ostatnią poprawną geometrię,
* oznaczyć konflikt jako oczekujący na synchronizację,
* wykonać recovery tylko przy `recovery_required: true` albo wykrytej luce wersji.

---

# 4. Deduplikacja delt po `conflict_id`

## Problem

Deduplikacja w `territory_delta.py` korzysta z `conflict_key`.

`conflict_key` może być:

* kluczem legacy,
* kluczem cyklu,
* wartością zależną od poprzedniego modelu,
* wartością zmieniającą się po rebuildzie.

W rezultacie dwa zdarzenia tego samego konfliktu mogą otrzymać różne klucze deduplikacji.

## Wymagane zachowanie

Podstawą tożsamości delty jest zawsze stabilny `conflict_id`.

Dedupe key powinien uwzględniać:

* `conflict_id`,
* typ zdarzenia,
* `conflict_version`,
* `geometry_version`,
* opcjonalny `target_id`,
* opcjonalny `front_id`.

Przykładowa semantyka:

`territory:conflict:<conflict_id>:<event_type>:cv<conflict_version>:gv<geometry_version>`

Dla filaru:

`territory:conflict:<conflict_id>:pillar:<target_id>:cv<conflict_version>`

Dla frontu:

`territory:conflict:<conflict_id>:front:<front_id>:gv<geometry_version>`

`conflict_key` może pozostać w payloadzie diagnostycznym, ale nie może sterować deduplikacją.

## Wymagania dodatkowe

Ponowienie publikacji tej samej wersji:

* nie tworzy drugiej delty,
* nie wywołuje drugiego efektu gameplayowego,
* nie uruchamia drugiej nagrody,
* nie powoduje drugiej aktualizacji filaru,
* nie generuje drugiego sygnału dla konsumentów.

---

# 5. Ostatni poprawny snapshot

## Cel

Zapewnić, że konflikt zawsze posiada jednoznacznie wskazany ostatni kompletny snapshot, do którego można wrócić po błędzie.

## Wymagany kontrakt

Store powinien jawnie przechowywać:

* `latest_snapshot_version`,
* `latest_complete_snapshot_version`,
* `latest_complete_geometry_version`,
* `latest_complete_conflict_version`,
* `latest_rebuild_status`,
* `latest_rebuild_error`,
* `latest_rebuild_started_at`,
* `latest_rebuild_finished_at`.

Nie wolno nadpisywać ostatniego poprawnego snapshotu niekompletnym wynikiem.

## Publikacja

Nowy snapshot zostaje oznaczony jako ostatni poprawny dopiero po:

1. zapisaniu konfliktu,
2. zapisaniu frontów,
3. zapisaniu filarów,
4. zapisaniu geometrii,
5. sprawdzeniu wersji,
6. zakończeniu transakcji,
7. walidacji kompletności.

Jeżeli którykolwiek etap zawiedzie:

* poprzedni kompletny snapshot pozostaje aktywny,
* nowa wersja otrzymuje status `failed`,
* frontend dostaje aktualny stan domenowy i poprzednią geometrię,
* `geometry_version` nie zostaje fałszywie zwiększone.

---

# 6. Trwała koordynacja pomiędzy workerami

## Problem

Poprawność konfliktów nie może zależeć od blokad w pamięci pojedynczego procesu.

Przy kilku workerach możliwe są:

* dwa równoległe rebuildy,
* podwójne utworzenie konfliktu,
* nadpisanie nowszego snapshotu starszym,
* podwójna publikacja delt,
* utrata żądania przebudowy.

## Wymagane zachowanie

Koordynacja rebuildów musi być trwała.

Rekord koordynacji powinien przechowywać:

* `conflict_id`,
* `requested_version`,
* `processing_version`,
* `completed_version`,
* `worker_id`,
* `lease_until`,
* `status`,
* `attempt_count`,
* `last_error`,
* `updated_at`.

Worker może rozpocząć rebuild tylko wtedy, gdy:

* uzyska lease,
* nie istnieje aktywny lease innego workera,
* jego `requested_version` nie jest starsze od `completed_version`.

Po wygaśnięciu lease inny worker może bezpiecznie przejąć zadanie.

Zapis wyniku musi sprawdzić, czy przetwarzana wersja nadal jest aktualna.

Starszy worker nie może nadpisać wyniku nowszego rebuilda.

---

# 7. Bezpieczny cutover i rollback

## Cel

Zapewnić, że poprawki kontraktu mogą zostać wdrożone bez ryzyka uszkodzenia aktywnych konfliktów.

## Feature flag

Należy wprowadzić flagę, przykładowo:

`TERRITORY_CONFLICT_CONTRACT_V2`

Tryby:

* `off` — stary odczyt kontraktu,
* `shadow` — nowy kontrakt jest wyliczany i walidowany, ale nie steruje frontendem,
* `on` — nowy kontrakt jest źródłem payloadów i delt.

## Shadow validation

W trybie `shadow` należy porównywać:

* `conflict_id`,
* uczestników,
* liczbę filarów,
* właścicieli filarów,
* `conflict_version`,
* `geometry_version`,
* liczbę frontów,
* kompletność snapshotu.

Rozbieżności trafiają do logów diagnostycznych, ale nie zmieniają gameplayu.

## Rollback

Rollback do poprzedniego trybu nie może:

* usuwać nowych danych,
* cofać wersji konfliktu,
* przywracać starego właściciela filaru,
* odtwarzać efektów gameplayowych.

Po rollbacku stary read model powinien być budowany z nowego źródła prawdy albo z ostatniego kompletnego snapshotu.

Nie wolno wracać do mutowania konfliktu przez endpoint mapy.

---

# 8. Weryfikacja działającego deploymentu

## Problem operacyjny

Lokalny `/api/map/player-areas` nie uruchamia już `refresh_stale_territory_polygons()`.

Jeżeli stack produkcyjny nadal pokazuje wywołanie tej funkcji z endpointu mapy, oznacza to:

* stary kod na serwerze,
* nieprzeładowany worker,
* częściowo wdrożoną wersję,
* różne wersje kodu pomiędzy workerami.

## Wymagane zabezpieczenia

Endpoint diagnostyczny lub log startowy workera powinien pokazywać:

* commit hash,
* build tag,
* PID workera,
* czas uruchomienia,
* wersję schematu konfliktów,
* stan feature flagi,
* identyfikator wdrożenia.

Każda odpowiedź `/api/map/player-areas` powinna opcjonalnie zawierać diagnostykę w trybie dev:

* `app_version`,
* `git_commit`,
* `worker_pid`,
* `conflict_contract_version`.

Po wdrożeniu wszystkie workery muszą raportować tę samą wersję.

## Procedura deploymentu

1. uruchomić migracje,
2. włączyć tryb `shadow`,
3. przeładować wszystkie workery,
4. zweryfikować commit na każdym workerze,
5. uruchomić testy smoke,
6. sprawdzić logi rozbieżności,
7. przełączyć flagę na `on`,
8. wykonać test przejęcia filaru,
9. sprawdzić snapshot i deltę,
10. pozostawić możliwość natychmiastowego przełączenia na `shadow` lub `off`.

---

# 9. Testy regresyjne

## Stabilna tożsamość

Dodać testy:

* konflikt zachowuje `conflict_id` po zmianie `area_ids`,
* konflikt zachowuje `conflict_id` po zmianie polygonu,
* konflikt zachowuje `conflict_id` po zmianie kolejności uczestników,
* dwa workery nie tworzą dwóch konfliktów,
* zamknięty konflikt nie zostaje ponownie otwarty,
* nowy cykl otrzymuje nowy `conflict_id`.

## Capture i delta

Dodać testy:

* capture zwiększa `conflict_version`,
* capture nie zwiększa `geometry_version`,
* delta zawiera aktualny filar,
* delta nie przedstawia starego snapshotu jako kompletnego,
* stara geometria pozostaje jako `last_valid_geometry`,
* po rebuildzie przychodzi kompletna delta,
* ponowienie capture nie publikuje drugiej delty.

## Snapshot completeness

Dodać testy dla stanów:

* `clean`,
* `dirty`,
* `rebuilding`,
* `failed`,
* brak snapshotu,
* snapshot starszy niż konflikt,
* snapshot zgodny z konfliktem.

## Deduplikacja

Dodać testy:

* zmiana `conflict_key` nie zmienia tożsamości delty,
* ta sama wersja konfliktu nie publikuje się drugi raz,
* zmiana filaru posiada dedupe po `target_id`,
* zmiana frontu posiada dedupe po `front_id`.

## Rebuild pomiędzy workerami

Dodać testy:

* jeden worker uzyskuje lease,
* drugi worker nie zaczyna tego samego rebuilda,
* wygasły lease może zostać przejęty,
* starszy worker nie nadpisuje nowszej wersji,
* nowe żądanie podczas rebuilda powoduje kolejny przebieg,
* błąd nie usuwa ostatniego kompletnego snapshotu.

## Frontend

Dodać testy:

* `complete: false` nie usuwa geometrii,
* aktualny filar jest aktualizowany mimo starej geometrii,
* `recovery_required: false` nie uruchamia pełnego recovery,
* `recovery_required: true` uruchamia recovery,
* starsza delta jest odrzucana,
* kompletna delta po rebuildzie zamyka stan oczekiwania.

## Gameplay i konsumenci

Należy ponownie uruchomić regresje dla:

* pełnego cyklu hakowania filaru,
* `actions_allowed`,
* `aimed_target`,
* aktywnych operacji,
* incydentów,
* Victim Pickera,
* `territory_contest`,
* Territory Control,
* etykiet `ALARM` i `KOLIZJA`,
* encirclement całego klastra,
* relacji chronionych,
* nagród i RSP,
* generowania plików,
* deduplikacji efektów,
* GhostNetwork,
* BlackNetu,
* Cybernera,
* Radia.

---

# 10. Kryteria zakończenia sprintu

Sprint `130.8.5` jest zakończony, gdy:

* otwarty konflikt jest wybierany po stabilnym `conflict_id` lub `participant_key`,
* zmiana geometrii nie tworzy nowego konfliktu,
* delta po capture zawiera aktualny stan filaru,
* stary snapshot nie jest publikowany jako kompletny,
* `complete` odzwierciedla rzeczywisty stan konfliktu,
* deduplikacja delt używa `conflict_id`,
* ostatni kompletny snapshot jest zachowywany po błędzie,
* rebuildy są koordynowane pomiędzy workerami,
* starszy worker nie może nadpisać nowszego wyniku,
* frontend zachowuje ostatnią poprawną geometrię podczas dirty/rebuilding,
* recovery jest uruchamiane tylko wtedy, gdy jest rzeczywiście wymagane,
* wszystkie workery działają na tej samej wersji kodu,
* cutover można bezpiecznie wycofać bez utraty danych i efektów gameplayowych,
* pełne testy konfliktów i zależnych konsumentów przechodzą.

---

# Poza zakresem

Sprint nie obejmuje:

* ponownego projektowania geometrii terytoriów,
* zmiany zasad powstawania klastrów,
* zmiany balansu przejmowania filarów,
* przebudowy nagród,
* nowego interfejsu konfliktów,
* nowej wizualizacji frontów,
* zmian lore,
* rozszerzania GhostNetwork o nowe mechaniki.

To jest sprint stabilizacyjny i kontraktowy.

Nie dodajemy nowych funkcji, dopóki bieżący konflikt nie posiada jednoznacznej tożsamości, aktualnych filarów, prawidłowej kompletności snapshotu i bezpiecznej publikacji pomiędzy workerami.

Tak — rozbiłbym to dokładnie w tej kolejności: najpierw czysta detekcja bez wpływu na gameplay, potem trwała nakładka `engagement`, następnie widoczność i relacje, później atomowy capture wielostronny, a na końcu frontend i pełny cutover.

## Audyt spójności serii 130.8.5.1-130.8.5.5 z aktualnym runtime

Audyt kodu przed implementacją wykazał, że wersjonowanie, fronty, snapshoty,
delty i workerowy rebuild nadają się do rozszerzenia, ale obecna detekcja nie
realizuje jeszcze najważniejszej granicy tej serii.

`build_territory_conflict_detection_plan()` buduje graf nakładających się pól,
łączy cały spójny komponent i tworzy jeden plan z sumą uczestników. Następnie
`materialize_territory_conflict_plans()` zapisuje go jako jeden
`territory_conflict`, którego `participant_key` może zawierać więcej niż dwóch
graczy. Jest to sprzeczne z docelową zasadą:

```text
1 konflikt 1v1 = 1 stabilny conflict_id
```

Sprint `130.8.5.1` musi więc rozdzielić detekcję par pól i konfliktów
bilateralnych od detekcji nakładania ich opublikowanych frontów. Engagement nie
może powstawać bezpośrednio z obecnego wieloosobowego komponentu pól.

Audyt potwierdził elementy, które należy zachować:

* `conflict_id`, `front_id`, wersje i snapshoty nie zależą od geometrii;
* `territory_owners_are_protected_relation()` chroni obecnie wyłącznie członków
  tego samego klanu; znajomość nie daje immunitetu strategicznego;
* `/api/map/player-areas` pozostaje read-only, a przebudowy wykonuje worker;
* projekcja per viewer jest właściwą granicą widoczności, ale musi stać się
  wspólną polityką mapy, Victim Pickera i Territory Control;
* engagement wymaga osobnego typu delty i osobnego registry warstw;
* reconciler pozostaje diagnostyczny i read-only — nie zmienia ownership ani
  geometrii.

Istniejące otwarte rekordy z więcej niż dwoma uczestnikami wymagają migracji.
Nie wolno ich przemianować na engagement ani usunąć. Shadow audit wskazuje
pary/fronty składające się na rekord, a migracja tworzy stabilne konflikty
bilateralne z aliasami starego ID dla operacji, incydentów i aimed targetów,
bez ponownego capture, nagród i hooków downstream.

### Wspólny Documentation Gate

Każdy sprint `130.8.5.x` kończy się aktualizacją dokumentacji w tym samym
wdrożeniu co kod:

* `doc/game_play_180726.md` — Decision, rzeczywisty kontrakt i odchylenia;
* `doc/project_journal.md` — zmiany, testy, migracje, flagi i produkcyjne logi;
* `doc/clans_machines.md` — zmiany immunitetu, crew lub własności;
* `doc/ghostnetwork_architecture.md` — nowe eventy, audience i hooki;
* dokumenty Response Network/incydentów — zmiany routingu incydentów/aktorów.

Brak Decision, opisu migracji/rollbacku i wyników regresji oznacza sprint
niezamknięty.

# Sprint 130.8.5.1 — Multi-Conflict Detection Audit

## Cel

Dodać czystą, diagnostyczną detekcję sytuacji, w której dwa lub więcej niezależnych konfliktów 1v1 zaczyna współdzielić realny obszar walki.

Sprint nie zmienia gameplayu i nie tworzy jeszcze trwałego multi-conflict.

Bazowe konflikty pozostają całkowicie niezależne:

```text
A ↔ D
B ↔ D
```

Ich:

```text
conflict_id
participant_key
front_id
versions
pillars
inners
lifecycle
```

nie mogą zostać zmienione przez pojawienie się dodatkowego uczestnika.

## Detekcja

Po opublikowaniu frontów konfliktów worker analizuje ich geometrię.

Potencjalny multi-conflict istnieje tylko wtedy, gdy fronty różnych aktywnych konfliktów mają wspólny obszar o dodatniej powierzchni.

Nie wystarcza:

```text
dotknięcie krawędzi
wspólny punkt
styczność polygonów
chwilowe przecięcie pojedynczej linii
```

Przykład:

```text
A ↔ D ─────┐
           │ wspólny obszar
B ↔ D ─────┘
```

Analizowany jest wyłącznie wspólny obszar frontów, nie całe terytoria A, B i D.

Przed detekcją engagement obecny plan komponentowy należy rozłożyć na wrogie
pary właścicieli. Każda para otrzymuje osobny kandydat konfliktu bazowego i
dwuelementowy `participant_key`. Graf komponentów może pozostać optymalizacją
przestrzenną, ale nie może być tożsamością konfliktu.

Detekcja engagement działa tylko na frontach ze snapshotów `complete=true` i
`geometry_status in {clean, published}`. Snapshot dirty/changing/failed nie
tworzy membership; zachowuje ostatni poprawny wynik do recovery.

Wspólna strefa jest spójnym komponentem polygonów overlapu. Łańcuch overlapów
może utworzyć jeden engagement tylko wtedy, gdy jego wspólne strefy są
przestrzennie połączone. Dwie rozłączne strefy tych samych konfliktów tworzą
dwa kandydaty. Bbox/spatial prefilter jest obowiązkowy — bez pełnego O(n^2)
dla frontów całego świata.

## Wynik diagnostyczny

Detektor powinien zwracać raport zawierający:

```text
member_conflict_ids
participant_usernames
participant_clans
hostile_clan_groups
overlap_geometry
overlap_area
candidate_status
detection_reason
source_snapshot_versions
member_front_ids
overlap_bbox
```

Bez zapisu nowego bytu domenowego.

## Szczególnie sprawdzić

Obecny mechanizm grupowania konfliktów potrafi tworzyć połączone komponenty wielu uczestników.

W tym sprincie należy upewnić się, że taka detekcja:

```text
nie scala conflict_id
nie rozszerza participant_key
nie przenosi filarów pomiędzy konfliktami
nie zamyka istniejących konfliktów
```

## Testy

Scenariusze:

```text
A-D i B-D bez kontaktu → brak multi
A-D i B-D stykają się punktem → brak multi
A-D i B-D dotykają krawędzią → brak multi
A-D i B-D nakładają się powierzchnią → kandydat multi
A-D odsuwa się → kandydat znika
trzy konflikty nakładają się → jeden wspólny kandydat
dwa rozłączne overlapy tych samych konfliktów → dwa kandydaty
niekompletny snapshot frontu → brak nowego membership
stary konflikt z trzema uczestnikami → raport par i aliasów migracyjnych
```

## Dokumentacja i artefakty audytu

Decision i journal zapisują liczbę zastanych konfliktów wieloosobowych, plan
migracji, budżet detekcji, liczbę porównań po prefilterze oraz przykładowe
`member_conflict_ids`, `member_front_ids` i wersje źródłowe. Shadow mode musi
potwierdzić brak mutacji, delt i efektów gameplay.

## Koniec sprintu

Sprint jest zakończony, gdy worker potrafi wiarygodnie powiedzieć:

> te konflikty pozostają niezależne, ale w tym konkretnym miejscu ich fronty tworzą wspólną strefę walki.

Bez jakiejkolwiek zmiany gameplayu.

## Decision 130.8.5.1 — shadow detector (2026-08-08)

Pierwszy etap wdrożono wyłącznie jako obserwator. `run.py` analizuje najnowsze
snapshoty aktywnych konfliktów i dopuszcza tylko `complete=true` oraz
`geometry_status=clean|published`. Fronty różnych `conflict_id` przechodzą
najpierw przez sweep po bbox, a dopiero potem przez obliczenie polygonu
overlapu. Kandydat wymaga dodatniej powierzchni co najmniej 1 m²; punkt i
wspólna krawędź nie tworzą multi-conflict. Przestrzennie połączone overlapy są
grupowane, a rozłączne strefy pozostają osobnymi kandydatami.

Raport zawiera wymagane identyfikatory konfliktów/frontów, uczestników i ich
klany, wersje źródłowe, bbox, powierzchnię i geometrię. Okresowy log workera
pomija pełne współrzędne, aby nie rozdmuchiwać logów; pełny raport można
uruchomić jednorazowo przez:

```bash
./.venv/bin/python scripts/territory_conflict_worker.py --audit-multi
```

Worker uruchamia shadow audit domyślnie co 180 sekund; interwał kontroluje
`CHAOS_TERRITORY_MULTI_AUDIT_SECONDS` (minimum 60 s). Raport jawnie zwraca
`mutations=0`: nie zapisuje engagement, nie publikuje delt, nie kolejkuje
rebuildów i nie zmienia bazowych konfliktów. Zastane rekordy z więcej niż
dwoma uczestnikami są raportowane osobno wraz z parami aliasów migracyjnych.

Lokalna baza audytowa 2026-08-08 nie zawierała aktywnych konfliktów:
`snapshots_seen=0`, `legacy_multi_participant_conflicts=0`, kandydatów `0`.
Test syntetyczny potwierdził bbox prefilter i pełny kontrakt raportu. Migracja
historycznych rekordów wieloosobowych pozostaje świadomie poza shadow mode;
przed 130.8.5.2 wymaga osobnego dry-runu na kopii danych produkcyjnych oraz
rollbacku do niezmienionych rekordów bazowych.

Walidacja: 69 testów celowanych (w tym 7 nowych scenariuszy multi-conflict)
zakończonych `OK`. Ten etap nie zmienia immunitetu klanowego, audience/eventów,
mapy ani routingu Response Network, dlatego dokumenty tych kontraktów nie
wymagają jeszcze aktualizacji.

---

# Sprint 130.8.5.2 — Persistent Multi-Conflict Engagement

## Cel

Na podstawie detektora z `130.8.5.1` utworzyć osobny trwały byt domenowy reprezentujący wspólną strefę walki.

Nie tworzymy nowego wieloosobowego `territory_conflict`.

Wprowadzamy:

```text
territory_conflict_engagement
```

## Model

Minimalny rekord:

```text
engagement_id
status

member_conflict_ids
participant_usernames
hostile_clan_groups

geometry

engagement_version
geometry_version
snapshot_version

created_at
updated_at
resolved_at
```

Członkostwo jest osobną relacją many-to-many:

```text
territory_conflict_engagement_members

engagement_id
conflict_id
front_id
status
joined_at
left_at
```

Pojedyncze pole `engagement_id` na froncie nie może być jedyną relacją. Ten sam
front może uczestniczyć w dwóch rozłącznych strefach.

`engagement_id` jest stabilny przez cały czas istnienia tej konkretnej wspólnej strefy.

ID nie jest hashem geometrii ani bieżącej listy członków. Dopasowanie kolejnej
publikacji korzysta z ciągłości `member_conflict_ids`, `member_front_ids`,
overlapu przestrzennego i lifecycle. Zamknięty cykl nie jest ponownie otwierany.

## Najważniejsza zasada

Bazowy front nadal należy do:

```text
conflict_id
```

i jest kojarzony przez tabelę członkostwa z jednym lub wieloma:

```text
engagement_id
```

Engagement nie przejmuje własności frontu.

Czyli:

```text
front A-D
 ├── conflict_id = A-D
 └── engagement_id = XYZ

front B-D
 ├── conflict_id = B-D
 └── engagement_id = XYZ
```

## Lifecycle

Proponowane statusy:

```text
detected
active
changing
resolving
resolved
closed
```

## Wejście

Engagement powstaje, gdy przez poprawną publikację geometrii zostanie potwierdzony wspólny obszar co najmniej dwóch konfliktów.

## Aktualizacja

Dołączenie kolejnego konfliktu:

```text
A-D
B-D
C-D
```

aktualizuje `member_conflict_ids`, ale:

```text
nie zmienia conflict_id A-D
nie zmienia conflict_id B-D
nie zmienia participant_key bazowych konfliktów
```

## Wyjście

Engagement zostaje rozwiązany, gdy fronty przestają posiadać wspólną powierzchnię.

Wprowadzamy histerezę:

```text
brak overlapu w pierwszej publikacji
→ engagement pozostaje changing

brak overlapu w drugiej kolejnej zgodnej publikacji
→ resolved
```

Zapobiega to miganiu przy granicznych polygonach.

## Konflikty bazowe po rozwiązaniu

Rozwiązanie engagement nie rozwiązuje automatycznie:

```text
A ↔ D
B ↔ D
```

Jeżeli nadal posiadają własne fronty, wracają po prostu do zwykłego trybu 1v1.

## Testy

Obowiązkowo:

```text
stabilność engagement_id
dołączenie konfliktu
odłączenie konfliktu
histereza
split wspólnej geometrii
ponowne połączenie
brak zmiany conflict_id
brak zmiany participant_key
równoległe engagementy z tym samym zestawem konfliktów
lease dwóch workerów i przejęcie wygasłego lease
no-op bez wzrostu wersji i bez drugiej delty
migracja wieloosobowego rekordu bez efektów gameplay
```

## Koordynator i dokumentacja

Engagement posiada trwałą kolejkę/lease albo jawnie uczestniczy w jednym batchu
koordynatora konfliktów. Nie uruchamiamy jego rekursywnej przebudowy osobno z
każdego konfliktu członkowskiego. Publikacja następuje raz po ukończeniu batcha
frontów. Decision dokumentuje schemat, indeksy, migrację, rollback, lifecycle,
wersje i dopasowanie stabilnego ID.

## Decision 130.8.5.2 — persistent engagement (2026-08-08)

Wprowadzono osobny store oraz tabele:

```text
territory_conflict_engagements
territory_conflict_engagement_members
territory_conflict_engagement_coordinator
```

Pierwsza przechowuje lifecycle, zbiory członków, geometrię, bbox i trzy wersje.
Druga jest relacją many-to-many `(engagement_id, conflict_id, front_id)` z
historią `joined_at/left_at`; front nie otrzymał pola właścicielskiego
`engagement_id`. Indeksy obsługują aktywny lifecycle oraz wyszukiwanie
membership po `(conflict_id, front_id, status)`. Trzecia tabela zapewnia jeden
globalny lease publikacji batcha. Lease wygasły może zostać przejęty, a
równoległy aktywny worker dostaje `lease_busy`.

Stabilne `engagement_id` jest losową tożsamością cyklu, nie hashem geometrii.
Kolejna publikacja dopasowuje otwarty cykl przez wspólne `conflict_id`,
ciągłość `front_id` i dodatni overlap bbox. Jedno otwarte engagement może być
dopasowane tylko raz w batchu, dzięki czemu split tworzy drugi równoległy byt.
Rozwiązany cykl nie jest otwierany ponownie. Zmiana członkostwa/statusu podnosi
`engagement_version`, zmiana geometrii `geometry_version`, a każda z nich
`snapshot_version`. Identyczny batch jest prawdziwym no-op: nie zapisuje
rekordu i nie podnosi żadnej wersji.

Brak kandydata po pierwszej zgodnej publikacji ustawia `changing` i licznik 1.
Drugi kolejny brak ustawia `resolved` oraz zamyka aktywne membershipy. Powrót
overlapu przed drugim brakiem przywraca ten sam cykl do `active`. Rozwiązanie
engagement nie zmienia lifecycle konfliktów bazowych.
Snapshot incomplete/dirty/failed chroni powiązane engagementy: nie tworzy
nowego membership i nie zwiększa licznika braku, więc zachowany zostaje
ostatni poprawny stan recovery.

Przed włączeniem persistence domknięto bilateralizację wejścia: graf pól służy
wyłącznie wykrywaniu przestrzennemu, a `build_territory_conflict_detection_plan`
zwraca osobny plan dla każdej wrogiej pary właścicieli. Istniejące konflikty
1v1 zachowują dobór po `participant_key`; zastany rekord wieloosobowy jest
raportowany przez 130.8.5.1 i przy kolejnej kanonicznej detekcji zostaje
zastąpiony planami par bez przepisywania historii capture do engagement.

Migracja schematu jest addytywna (`CREATE TABLE/INDEX IF NOT EXISTS`). Rollback
polega na zatrzymaniu workera i cofnięciu kodu; nowe tabele mogą pozostać
nieaktywne i nie są czytane przez dotychczasowy gameplay. Ich usunięcie nie
jest wymagane i nie powinno być wykonywane automatycznie. Sprint nie publikuje
jeszcze delt engagement ani nie zmienia widoczności/capture — to zakres
130.8.5.3–130.8.5.5.

Walidacja: 78 testów celowanych `OK`, w tym stabilność ID, join/leave,
histereza, recovery, split i równoległe engagementy, przejęcie wygasłego
lease, no-op wersji, brak zmiany `conflict_id/participant_key` oraz
bilateralizacja trzyosobowego komponentu.

---

# Sprint 130.8.5.3 — Multi-Conflict Visibility & Clan Rules

## Cel

Określić dokładnie, co każdy uczestnik widzi i co może zaatakować we wspólnej strefie.

Nie zmieniamy jeszcze capture.

## Reguła relacji bojowej

Jedyną relacją zapewniającą immunitet strategiczny jest wspólny klan.

Relacja społeczna nie blokuje walki.

```text
ten sam gracz        → brak celu
ten sam klan         → brak celu

znajomy, obcy klan   → cel
neutralny, obcy klan → cel
wróg, obcy klan      → cel
```

Znajomy pozostaje `friend`, ale nadal może być przeciwnikiem strategicznym.

Gracz bez klanu stanowi własną grupę bojową; dwa puste kody klanu nie dają
immunitetu. Zmiana klanu podczas aktywnego konfliktu jest oceniana przy kolejnej
kanonicznej przebudowie: wspólny klan wyłącza nowe hostile edges i cele między
graczami, ale nie przepisuje historii capture ani starych eventów.

## Widoczność aktorów

Aktor może być pokazany jako:

```text
crew
friend
intruder
```

`crew` oznacza własny klan.

`friend` oznacza relację społeczną z obcym klanem.

`intruder` oznacza pozostałych obcych uczestników.

## Widoczność celów

Gracz widzi:

```text
filary i innery obrońcy swojego konfliktu
+
filary i innery innych wrogich klanów
znajdujące się we wspólnej geometrii engagement
```

Nie widzi jako celów:

```text
filarów własnego klanu
innerów własnego klanu
historycznych targetów
targetów sąsiedniego konfliktu poza engagement
```

## Ważna granica

Jeżeli B walczy z D kilometr dalej, A nie dostaje celów B tylko dlatego, że oba konflikty dotyczą D.

Cel B staje się widoczny dla A dopiero wtedy, gdy znajdzie się w aktywnej wspólnej strefie.

## Niezmiennik widoczności

Obiekt, który realnie podtrzymuje aktywny front multi-conflict, nie może być jednocześnie:

```text
wrogi
hakowalny według domeny
niewidoczny dla wszystkich przeciwników
```

Jeżeli jest częścią aktywnej walki, musi istnieć przynajmniej jedna wroga strona mogąca go zobaczyć i zaatakować.

To domyka również wcześniejszy problem niewidocznych filarów.

## Territory Control / Victim Picker

Oba narzędzia muszą korzystać z tej samej projekcji widoczności.

Nie może wystąpić sytuacja:

```text
mapa → target niewidoczny
Victim Picker → target widoczny
Territory Control → jeszcze inny status
```

## Testy

Scenariusze:

```text
same clan
friend different clan
neutral different clan
enemy different clan

target inside engagement
target outside engagement

pillar
inner
actor

Victim Picker
Territory Control
map
```

Wszystkie projekcje muszą zgadzać się co do tego samego obiektu.

## Jedna polityka i dokumentacja

Reguły trafiają do jednej backendowej polityki projekcji, nie do warunków
rozsianych po endpointach i JavaScript. Wynik celu zawiera co najmniej:

```text
viewer_relation
combat_relation
visible
attackable
visibility_reason
engagement_ids
source_conflict_ids
```

Mapa, Territory Control i Victim Picker konsumują ten sam wynik. Decision oraz
`clans_machines.md` opisują rozdzielenie `friend` od relacji bojowej.
`ghostnetwork_architecture.md` dokumentuje audience, jeżeli projekcja zasila
zdarzenia GhostNetwork.

## Decision 130.8.5.3 — wspólna polityka widoczności (2026-08-08)

Dodano jedną backendową politykę rozdzielającą dwie osie relacji:

```text
viewer_relation = self | crew | friend | intruder
combat_relation = self | protected_same_clan | hostile
```

`friend` nie daje immunitetu strategicznego. Wspólny niepusty klan daje
`protected_same_clan`; gracze bez klanu są osobnymi grupami i pozostają wobec
siebie `hostile`. Aktualny profil jest odczytywany przy projekcji, dlatego
zmiana klanu od razu ukrywa cele nowego crew, a kolejna kanoniczna detekcja
usuwa również hostile edge bez przepisywania historii capture.

Każdy projektowany target i aktor otrzymuje:

```text
viewer_relation
combat_relation
visible
attackable
visibility_reason
engagement_ids
source_conflict_ids
```

Bezpośrednie cele konfliktu 1v1 zachowują dotychczasową widoczność. Cel z
innego konfliktu jest dokładany wyłącznie, gdy jego `conflict_id` należy do
aktywnego/changing engagementu widza, punkt leży w opublikowanej wspólnej
geometrii i właściciel nie jest członkiem jego klanu. Sam wspólny obrońca albo
odległy konflikt nie wystarcza. Ta sama lista `contested_targets` zasila mapę i
Victim Picker; Territory Control otrzymuje ją jako `visible_targets` w threat
obszaru. Victim Picker nie usuwa już pól polityki podczas serializacji.

Aktor będący uczestnikiem engagementu jest ujawniany w jego geometrii. Crew
pozostaje nieatakowalne, znajomy obcego klanu zachowuje etykietę `friend`, ale
ma bojowe `hostile`, a pozostali są `intruder`. Akcja oznaczenia celu korzysta
z `combat_relation`, a nie z samej relacji społecznej.

Sprint nie zmienia jeszcze transferu własności. Lookup używany przez capture
wywołuje projekcję z `include_engagement=false`; wielostronny target jest więc
widoczny diagnostycznie i w narzędziach, ale jego atomowe przejęcie zostaje
włączone dopiero wraz z CAS i reconciliation set w 130.8.5.4.

Nie dodano audience ani eventów GhostNetwork, więc
`ghostnetwork_architecture.md` pozostaje bez zmiany. Zmieniony kontrakt klanowy
opisano w `clans_machines.md`. Walidacja: 85 testów terytorialnych `OK`, w tym
spójność mapy, Victim Picker i Territory Control dla tego samego celu.

---

# Sprint 130.8.5.4 — Atomic Multi-Party Capture & Reconciliation

## Cel

Obsłużyć sytuację, w której kilku graczy może atakować ten sam obiekt i capture jednego uczestnika wpływa równocześnie na kilka konfliktów.

To jest sprint gameplayowy całej serii.

## Zasada

Capture jest atomowym transferem własności.

Pierwszy poprawnie zapisany transfer wygrywa.

Przykład:

```text
A → filar D
B → filar D
```

Jeżeli A zapisze capture pierwszy:

```text
D → A
```

Żądanie B nie może ponownie wykonać:

```text
D → B
```

na podstawie starego stanu.

B otrzymuje kontrolowany rezultat:

```text
target_state_changed
```

bez:

```text
500
podwójnego RSP
podwójnych plików
podwójnego capture
podwójnych efektów
```

Atomowość wymaga compare-and-swap na kanonicznym rekordzie celu. Klient
przekazuje oczekiwane `target_id`, ownera i znaną wersję, ale backend porównuje
je z aktualnym store. Transfer, event capture, idempotency receipt i enqueue
reconciliation set są jedną transakcją albo korzystają z trwałego outboxa.

## Stan po capture

Obiekt może później zostać zaatakowany przez B, ale już jako:

```text
owner = A
```

i tylko wtedy, gdy aktualna geometria engagement czyni go legalnym celem B.

## Reconciliation set

Po capture worker ustala cały zestaw struktur dotkniętych transferem.

Przykład:

```text
A-D
B-D
engagement A-B-D
```

Capture może wymagać przebudowy:

```text
A-D
B-D
```

a jeżeli powstanie bezpośredni spór A-B:

```text
A-B
```

oraz:

```text
engagement
```

## Ważna zasada

Nie publikujemy częściowego rezultatu typu:

```text
A już widzi nowy stan
B jeszcze stary
D już stracił filar
engagement nadal używa starego ownera
```

Worker najpierw przelicza dotknięty zestaw, a dopiero później publikuje wynik.

Reconciliation set otrzymuje stabilny `set_id`, najwyższą żądaną wersję i jeden
lease. Snapshoty mogą być zapisywane kolejno, ale delty stają się widoczne
dopiero po znaczniku `published` całego zestawu. Recovery wznawia ten sam set i
nie tworzy nowego capture.

## Redukcja pola

Obiekt może podtrzymywać pole tylko wtedy, gdy:

```text
ma kanonicznego właściciela
jest aktywnym filarem lub innerem
należy do aktualnej geometrii
jest dostępny jako cel dla przynajmniej jednej wrogiej strony
```

Niewidoczny historyczny obiekt nie może trzymać pola.

## Konflikty niezależne

Capture w engagement nie daje prawa do przebudowania wszystkich konfliktów uczestnika.

Przebudowywany jest wyłącznie:

```text
dotknięty konflikt
inne konflikty zależne od tego samego transferu
aktywny engagement
```

Front poza engagement pozostaje niezależny.

## Encirclement

Otoczenie nadal jest osobną mechaniczną przyczyną przejęcia całego klastra.

Multi-conflict nie oznacza automatycznego wchłaniania wszystkich pól znajdujących się we wspólnej strefie.

## Efekty gameplayowe

Każdy capture musi nadal zachowywać istniejące zabezpieczenia:

```text
RSP
nagrody
pliki
operations
incidents
aimed_target
actions_allowed
GhostNetwork hooks
BlackNet
Cyberner
Radio
```

Efekt zostaje wykonany dokładnie raz dla zwycięskiego transferu.

## Reconciler bezpieczeństwa

Okresowy reconciler pozostaje ostatnim bezpiecznikiem.

Co kilka minut może sprawdzić:

```text
ownership
geometry
visible pillars
visible inners
engagement membership
```

i wykrywać niemożliwe stany.

Nie jest jednak główną ścieżką gameplayu.

Reconciler wyłącznie raportuje i kolejkuje kanoniczny rebuild. Nie zmienia
ownership, nie redukuje polygonów i nie przepisuje pillar/inner samodzielnie.

## Testy

Najważniejsze:

```text
A i B atakują D jednocześnie
A wygrywa zapis
B dostaje target_state_changed

capture A tworzy front A-B
capture A nie tworzy frontu A-B

capture wpływa na dwa konflikty
capture nie wpływa na odległy konflikt

retry request
worker crash
duplicate job
reconciliation
```

Plus regresje istniejącego 1v1.

## Stan implementacji 130.8.5.4

Capture celu terytorialnego przechodzi przez kanoniczny rekord
`territory_target_ownership` i atomowy compare-and-swap. Bootstrap ownera jest
wykonywany z `captured_targets`, a nie z payloadu klienta. Zwycieski zapis
zwieksza `ownership_version`, aktualizuje projekcje kompatybilnosci i w tej
samej transakcji zapisuje receipt oraz trwaly reconciliation set. Powtorzenie
tego samego `action_id` zwraca idempotentny wynik, natomiast konkurencyjny
request oparty na poprzednim ownerze lub wersji konczy sie kontrolowanym
`target_state_changed` przed nagrodami i pozostanymi efektami gameplay.

Worker w pierwszej kolejnosci odbiera reconciliation set. Zakres rozszerza
wylacznie o aktywne konflikty zawierajace ten sam `target_id` oraz engagementy
tych konfliktow. Rebuildy zestawu nie publikuja delt czastkowych; delty sa
emitowane dopiero po poprawnym przeliczeniu calego zestawu. Lease i stabilny
`set_id` pochodzacy z `target_id + ownership_version` pozwalaja wznowic ten sam
outbox bez ponownego capture. Encirclement pozostaje poza ta sciezka.

Wlaczono capture celow ujawnionych przez engagement dopiero po podpieciu CAS.
Projekcja celu przekazuje `expected_owner_username` i `ownership_version`, ale
backend nadal rozstrzyga na podstawie aktualnego store.

## Dokumentacja i obserwowalność

Decision opisuje `target_state_changed`, retry oraz idempotentny sukces. Journal
zawiera test crash/replay i brak podwójnych nagród. Logi używają `set_id`,
`target_id`, zwycięskiego ownera oraz dotkniętych `conflict_id` i
`engagement_id`, bez logowania całych profili.

---

Tak — `130.8.5.4.1` powinien być sprintem domykającym atomowość całego multi-party capture, czyli nie zmieniać już mechaniki walki, tylko zagwarantować, że capture, efekty gameplayowe, reconciliation, engagement i publikacja snapshotów kończą się razem albo są bezpiecznie wznawiane po awarii.

# Sprint 130.8.5.4.1 — Atomic Capture Completion & Reconciliation Gate

## Cel

Domknąć kontrakt Sprintu `130.8.5.4` po audycie multi-party capture.

Fundament jest już poprawny:

* pierwszy poprawny capture wygrywa,
* canonical ownership jest chroniony przez CAS,
* drugi atakujący nie może przejąć celu na podstawie starego stanu,
* istnieją receipt i lease,
* reconciliation set potrafi zebrać konflikty dotknięte transferem.

Brakuje jednak gwarancji, że cały proces zostanie zakończony dokładnie raz i że żaden gracz nie zobaczy stanu znajdującego się w połowie przebudowy.

Sprint nie zmienia zasad walki. Uszczelnia wykonanie istniejącego kontraktu.

---

## 1. Exactly-once dla efektów capture

### Problem

Aktualnie canonical ownership i receipt capture mogą zostać zapisane wcześniej niż pozostałe efekty gameplayowe.

Możliwy przebieg:

1. A przejmuje filar D.
2. Ownership zostaje poprawnie zmieniony z D na A.
3. Receipt potwierdza wykonany capture.
4. Proces pada przed wykonaniem części dalszych efektów.
5. Request zostaje ponowiony.
6. System widzi istniejący receipt i traktuje operację jako duplicate.
7. Brakujące efekty nie są już wykonywane.

W efekcie ownership jest poprawny, ale mogą nie zostać wykonane:

* RSP,
* nagrody,
* pliki,
* aktualizacja profilu,
* GhostNetwork hooks,
* BlackNet,
* Cyberner,
* Radio,
* inne efekty powiązane z udanym capture.

To łamie zasadę „capture wykonał się dokładnie raz”.

### Docelowe zachowanie

Capture i jego efekty muszą tworzyć jeden trwały proces.

Po zapisaniu transferu system musi wiedzieć nie tylko:

> capture wykonany

ale również:

> które efekty tego capture zostały już wykonane.

Jeżeli proces padnie po zmianie ownership, ponowienie operacji nie wykonuje capture drugi raz, ale kontynuuje niedokończone efekty.

### Wymagany kontrakt

Dla capture musi istnieć trwały zestaw efektów/outbox powiązany z jednym capture receipt.

Powinien rozróżniać przynajmniej:

* ownership committed,
* gameplay effects pending,
* gameplay effects processing,
* gameplay effects completed,
* reconciliation queued,
* reconciliation completed,
* publication completed.

Każdy efekt posiada własny klucz deduplikacji.

Retry:

* nie powtarza transferu ownership,
* nie powtarza ukończonych efektów,
* wykonuje wyłącznie brakujące elementy,
* kończy ten sam capture lifecycle.

### Najważniejszy niezmiennik

Jeżeli canonical ownership wskazuje już nowego właściciela w wyniku konkretnego capture, ten capture musi być możliwy do doprowadzenia do stanu `completed` nawet po restarcie workera lub procesu HTTP.

---

# 2. Engagement jako część reconciliation set

## Problem

Reconciliation set zna obecnie `engagement_ids`, ale faktycznie przebudowuje tylko bazowe konflikty.

Po capture możemy więc mieć:

* A–D już przebudowane,
* B–D już przebudowane,
* ownership już zmieniony,
* ale engagement A–B–D nadal prezentuje poprzednią geometrię albo membership.

Engagement dogania świat dopiero przy późniejszym okresowym audycie.

Przez kilka minut może więc istnieć poprawny stan konfliktów bazowych i nieaktualna wspólna strefa walki.

### Docelowe zachowanie

Engagement należy do tego samego reconciliation set co konflikty dotknięte transferem.

Jeżeli capture wpływa na:

* konflikt A–D,
* konflikt B–D,
* engagement A–B–D,

to cały zestaw traktujemy jako jeden logiczny rezultat.

Worker musi w tym samym przebiegu:

1. przebudować konflikty bazowe,
2. pobrać ich nowe opublikowane fronty,
3. ponownie policzyć membership engagement,
4. ponownie policzyć jego geometrię,
5. ustalić widoczność celów,
6. przygotować jeden spójny wynik zestawu.

Okresowy audit pozostaje zabezpieczeniem, a nie normalnym mechanizmem aktualizacji engagement po capture.

---

# 3. Publication Gate dla snapshotów

## Problem

Delty są już wstrzymywane do zakończenia reconciliation set, ale same snapshoty poszczególnych konfliktów mogą być zapisywane wcześniej.

Przykładowo:

1. przebudowany zostaje A–D,
2. jego nowy snapshot staje się dostępny,
3. B–D jeszcze się liczy,
4. engagement nadal posiada poprzedni stan,
5. klient wykonuje pełny polling `/api/map/player-areas`,
6. otrzymuje mieszankę starego i nowego świata.

Czyli event stream może być spójny, ale read model nadal może ujawnić częściowy wynik.

### Docelowe zachowanie

Reconciliation set otrzymuje własną granicę publikacji.

Snapshot może zostać:

* obliczony,
* zapisany jako przygotowany,
* zwalidowany,

ale nie może stać się bieżącym publicznym snapshotem przed ukończeniem całego zestawu.

Dopiero gdy gotowe są wszystkie:

* dotknięte konflikty,
* fronty,
* engagementy,
* projekcje wymagane przez capture,

reconciliation set przechodzi do `published`.

Wtedy wszystkie nowe snapshoty stają się widoczne jako jedna wersja logicznego świata.

### Read-only mapa

`/api/map/player-areas` nadal niczego nie przebudowuje.

Powinien jednak czytać wyłącznie:

* ostatni opublikowany komplet,
* albo ostatni poprawny snapshot sprzed aktualnie trwającego reconciliation.

Nie może zobaczyć snapshotu oznaczonego jako przygotowywany przez nieukończony set.

### Awaria w połowie

Jeżeli worker padnie po przebudowaniu dwóch z trzech elementów:

* żaden częściowy wynik nie staje się publiczny,
* poprzednie snapshoty nadal reprezentują świat,
* retry przejmuje ten sam reconciliation set,
* brakujące elementy są dokańczane,
* dopiero potem następuje publication gate.

---

# 4. Canonical owner musi pochodzić ze źródła prawdy

## Problem

Dla historycznych albo osieroconych filarów może nie istnieć poprawny wpis w `captured_targets`.

W takim przypadku bootstrap ownership może obecnie przyjąć `expected_owner_username` przekazany przez request.

To jest niebezpieczne, bo dane klienta stają się wtedy źródłem początkowego ownership.

Właśnie przy starych filarach, które wcześniej sprawiały problemy podczas konfliktów, może to doprowadzić do ustanowienia właściciela na podstawie nieaktualnego requestu.

### Docelowe zachowanie

Brak canonical ownera nie oznacza:

> uwierz klientowi.

Oznacza:

> stan celu jest niekompletny i capture nie może zostać wykonany.

Jeżeli ownership nie może zostać potwierdzony z kanonicznego źródła, operacja kończy się kontrolowanym stanem:

`canonical_owner_missing`

Nie wykonujemy:

* capture,
* nagród,
* RSP,
* plików,
* GhostNetwork hooks,
* reconciliation transferu.

Taki przypadek trafia do diagnostyki/reconciliation jako istniejąca niespójność świata.

### Zasada

`expected_owner_username` jest warunkiem compare-and-swap.

Nie jest źródłem własności.

---

# 5. Batch ownership lookup dla projekcji mapy

## Problem

Przy budowaniu projekcji konfliktu mapa pobiera wersję ownership osobnym odczytem dla każdego ujawnionego celu.

Mały konflikt tego nie pokazuje, ale przy większej wojnie:

* wiele frontów,
* engagement,
* kilkadziesiąt filarów,
* innery kilku graczy,

może ponownie stworzyć koszt N+1 na `/api/map/player-areas`.

To jest szczególnie niepożądane, ponieważ endpoint mapy został już odchudzony i pozostaje krytycznym read modelem.

### Docelowe zachowanie

Ownership potrzebny dla całej odpowiedzi powinien zostać pobrany jako jeden zestaw.

W obrębie pojedynczego requestu:

1. zbierane są wszystkie wymagane `target_id`,
2. wykonywany jest jeden odczyt ownership,
3. tworzona jest lokalna mapa wyników,
4. wszystkie projekcje korzystają z tego samego snapshotu danych.

Dzięki temu jeden target posiada tę samą wersję ownership we wszystkich miejscach tego samego response.

Nie tworzymy globalnego cache mogącego być starszym od canonical store. Wystarczy spójny cache requestowy/batch read.

---

# 6. Pełny lifecycle reconciliation set

Po tym sprincie reconciliation set powinien reprezentować cały proces:

* capture committed,
* effects pending,
* effects completed,
* base conflicts rebuilding,
* engagements rebuilding,
* snapshots prepared,
* validation completed,
* published,
* completed.

Awaria na dowolnym etapie nie tworzy nowego procesu.

Worker wznawia ten sam set.

`set_id` pozostaje stabilny od capture aż do końca publikacji.

---

# 7. Reconciler okresowy

Reconciler nadal pozostaje dodatkowym zabezpieczeniem.

Sprawdza między innymi:

* ownership,
* filary,
* innery,
* geometrię,
* membership engagement,
* niedokończone capture effects,
* reconciliation sets pozostawione po awarii.

Nie wykonuje jednak alternatywnej logiki gameplayu.

Jeżeli wykryje niedokończony proces, kolejkuje jego kanoniczne wznowienie.

Nie wykonuje drugiego capture i nie przyznaje efektów poza outboxem.

---

# 8. Testy wymagane do zamknięcia 130.8.5.4

Dotychczasowe testy równoległego capture, CAS i lease pozostają, ale sprint musi dodać scenariusze awaryjne.

### Crash po CAS

Scenariusz:

* ownership zmieniony,
* proces pada przed RSP/nagrodami/hookami,
* retry,
* ownership nie zmienia się ponownie,
* brakujące efekty zostają wykonane,
* każdy efekt dokładnie raz.

### Crash podczas efektów

Część efektów wykonana, część nie.

Po retry:

* wykonane nie powtarzają się,
* brakujące dochodzą,
* końcowy stan jest identyczny jak przy przebiegu bez awarii.

### Crash w reconciliation set

* pierwszy konflikt przebudowany,
* drugi nie,
* engagement nie,
* worker pada.

Klient nadal widzi poprzedni kompletny stan.

Retry kończy set i dopiero wtedy publikuje nową wersję.

### Engagement

Capture zmienia fronty bazowe i engagement.

Test musi potwierdzić, że po publikacji engagement odpowiada tym samym wersjom świata co konflikty członkowskie.

### Polling podczas rebuilda

W trakcie niedokończonego reconciliation:

* pełny endpoint mapy nie pokazuje częściowego stanu,
* delta nie wychodzi przed publication gate.

### Missing owner

Historyczny filar bez canonical ownership:

* nie przyjmuje ownera z requestu,
* zwraca `canonical_owner_missing`,
* brak efektów capture.

### Batch ownership

Duży konflikt z wieloma targetami:

* ownership pobierany zbiorczo,
* brak liczby zapytań rosnącej liniowo z liczbą targetów,
* wszystkie projekcje używają tego samego wyniku requestu.

---

# 9. Regresja gameplayu

Po zmianach ponownie sprawdzić:

* zwykły capture 1v1,
* jednoczesny atak A i B na D,
* `target_state_changed`,
* inner → pillar,
* redukcję terytorium,
* encirclement,
* aimed target,
* actions allowed,
* Victim Picker,
* Territory Control,
* aktywne operacje i incydenty,
* RSP i nagrody,
* generowanie plików,
* GhostNetwork,
* BlackNet,
* Cyberner,
* Radio,
* restart workera w trakcie capture,
* restart workera w trakcie reconciliation.

Najważniejsze jest potwierdzenie, że uszczelnienie transakcyjności nie zmienia samej mechaniki konfliktu.

---

# Kryteria zakończenia

Sprint `130.8.5.4.1` jest zamknięty dopiero wtedy, gdy:

* ownership capture może zostać wykonany tylko raz,
* wszystkie efekty udanego capture ostatecznie wykonują się dokładnie raz,
* retry po crashu wznawia brakujące efekty,
* engagement jest elementem tego samego reconciliation set,
* reconciliation set posiada wspólny publication gate,
* endpoint mapy nie może zobaczyć częściowego zestawu,
* stary kompletny snapshot pozostaje publiczny do czasu ukończenia nowego,
* brak canonical ownera blokuje capture kontrolowanym wynikiem,
* dane requestu nigdy nie ustanawiają ownership,
* ownership mapy pobierany jest batchowo,
* crash na każdym etapie można bezpiecznie wznowić,
* brak podwójnych nagród, RSP, plików i hooków,
* testy awarii i recovery przechodzą.

## Stan implementacji 130.8.5.4.1 — etap 1

Usunięto możliwość ustanowienia początkowego ownership na podstawie
`expected_owner_username` z requestu. Jeżeli kanoniczny owner nie istnieje ani
w `territory_target_ownership`, ani w źródłowym `captured_targets`, CAS zapisuje
idempotentny receipt z wynikiem `canonical_owner_missing` i nie tworzy
reconciliation set. Endpoint zwraca kontrolowane 409 przed capture i efektami.

Projekcja widoczności pobiera ownership jednym odczytem `list_map()` na kontekst
requestu. Wszystkie targety odpowiedzi korzystają z tej samej mapy wersji;
usunięto otwieranie osobnego połączenia SQLite dla każdego filaru/innera.

Etap nie zamyka sprintu. Effects outbox, engagement rebuild w tym samym set oraz
publication gate snapshotów pozostają kolejnymi obowiązkowymi krokami 4.1.

## Stan implementacji 130.8.5.4.1 — etap 2

Reconciliation set posiada teraz trwałe snapshot gates. Przy dodaniu konfliktu
do setu zapamiętywana jest ostatnia publiczna `snapshot_version`; konflikty
odkryte przez worker są dopisywane do scope przed pierwszym rebuildem. Dopóki
set ma status `pending` albo `processing`, read-only endpoint mapy otrzymuje
snapshot nie nowszy niż zapamiętana wersja. Po `published` gate automatycznie
odsłania najnowszy komplet. Endpoint nadal nie wykonuje żadnego rebuilda.

Worker po przeliczeniu wszystkich konfliktów uruchamia kanoniczny detector i
publikację engagementów w tym samym przebiegu setu. Nie kończy setu, jeżeli
engagement publication nie uzyska `ok`. Okresowy audit pozostaje recovery, a
nie normalną ścieżką capture.

Sprint nadal pozostaje otwarty wyłącznie na trwały effects outbox i testy
crash/replay poszczególnych efektów capture.

Dopiero po tym można uczciwie uznać `130.8.5.4` za zamknięty i przejść do `130.8.5.5`, bo wtedy multi-conflict będzie już nie tylko poprawny przy idealnym przebiegu, ale również odporny na dokładnie te sytuacje, które potem naprawdę zdarzają się przy kilku workerach, retry i długich wojnach na mapie.


---

# Sprint 130.8.5.5 — Multi-Conflict Map, Deltas & Cutover

## Cel

Włączyć multi-conflict do normalnego runtime gry bez zastępowania istniejących warstw konfliktów.

## Warstwa mapy

Engagement otrzymuje osobną projekcję.

Mapa pokazuje równolegle:

```text
terytoria
bazowe fronty 1v1
multi-conflict engagement
filary
innery
aktorów
incydenty
```

Warstwa engagement nie może usuwać ani zastępować frontów bazowych.

## Stabilne identyfikatory

Frontend aktualizuje:

```text
conflict_id
front_id
engagement_id
target_id
```

nie:

```text
indeksy tablic
kolejność elementów
geometrię jako ID
```

## Delta engagement

Minimalnie:

```text
engagement_id
engagement_version
geometry_version
snapshot_version
status

member_conflict_ids
participant_usernames

changed_targets
removed_targets
changed_fronts
removed_fronts

geometry
complete
recovery_required
```

Osobny typ zdarzenia:

```text
territory.engagement_changed
```

Deduplikacja używa `engagement_id` i wersji, nie geometrii ani listy
uczestników. Audience obejmuje uczestników bazowych konfliktów oraz jawnie
wyliczonych odbiorców crew. Payload jest projekcją per viewer albo odsyła do
bezpiecznego snapshotu odbiorcy.

## Jedna projekcja per viewer

Backend przygotowuje wynik względem konkretnego gracza.

Dzięki temu frontend nie podejmuje samodzielnie decyzji:

```text
czy to crew?
czy friend?
czy hostile?
czy można hackować?
```

Dostaje już wynik projekcji.

Frontend utrzymuje osobne registry, np. `territoryEngagementLayers`. Reconcile
engagement nie usuwa wpisów z registry bazowych frontów, markerów ani warstw
terytoriów. Equal-version recovery stosuje mechanizm brakujących warstw znany z
ustabilizowanego konfliktu 1v1.

## Recovery

Pełny snapshot pozostaje mechanizmem:

```text
boot
recovery
version gap
corruption recovery
```

Normalna zmiana engagement powinna być obsługiwana deltą.

## Cutover

Wdrożenie etapami:

```text
1. shadow detection
2. engagement store aktywny bez UI
3. projekcja widoczności w diagnostyce
4. multi-party capture
5. engagement delta
6. mapa
7. pełny runtime
```

W każdym etapie zwykły konflikt 1v1 musi pozostać grywalny bez engagement.

## Stan implementacji — 2026-08-08

Rozpoczęto etapy 5-6 addytywnie. Backend publikuje osobny
`territory.engagement_changed`, deduplikowany przez stabilne `engagement_id` i
`snapshot_version`. Payload jest projektowany per viewer; audience obejmuje
uczestników i crew ich aktualnych klanów, ale nie znajomych z obcych klanów.
Endpoint mapy zwraca `territory_engagement_snapshots` obok niezmienionych
snapshotów konfliktów 1v1.

Frontend utrzymuje wyłącznie dla tej projekcji osobne registry
`territoryEngagementRegistry` i `territoryEngagementLayers`. Boot/recovery
rekoncyliuje pełny zestaw, zwykła zmiana idzie deltą, luka wersji uruchamia
snapshot recovery, a equal-version odtwarza brakującą warstwę Leaflet.
Usunięcie engagement nie usuwa frontów, filarów ani pól bazowego konfliktu.

Effects outbox pozostaje świadomie poza zakresem tego sprintu jako oddzielna
implementacja. Pełny runtime/cutover produkcyjny i test macierzy końcowej nadal
pozostają otwarte.

## Regresja końcowa

Przed zamknięciem serii należy przetestować co najmniej:

```text
1v1 bez engagement
1v1 → multi → 1v1
A-D + B-D
A-D + B-D + C-D

ten sam klan
friend obcego klanu
neutral
enemy

simultaneous capture
encirclement
redukcję pola
inner → pillar

Victim Picker
Territory Control
aimed_target
actions_allowed

operations
incidents
RSP
files

GhostNetwork
BlackNet
Cyberner
Radio

map bootstrap
delta
recovery
reload mapy
kilka workerów
rozłączne engagementy tych samych konfliktów
zmianę klanu podczas engagement
stary klient bez obsługi engagement
```

## Dokumentacja cutoveru

Decision zawiera flagi wdrożeniowe, kolejność włączenia, rollback do samego
1v1, kontrakt snapshot/delta i wynik testu produkcyjnego. Journal odnotowuje
czasy bootu i delt, liczbę warstw Leaflet oraz brak rebuildów w endpointach
mapy. Po cutoverze aktualizujemy dokumenty downstream ze wspólnego
Documentation Gate.

## Kryterium zamknięcia całej serii

Po `130.8.5.5` obowiązuje jedna podstawowa zasada:

```text
1 konflikt 1v1
=
1 stabilny conflict_id
```

Niezależnie od tego, ilu dodatkowych graczy pojawia się obok.

Jeżeli kilka takich konfliktów zaczyna współdzielić pole walki:

```text
conflict A-D ─┐
              ├─ engagement XYZ
conflict B-D ─┘
```

Engagement koordynuje ich wspólną część, ale nie staje się właścicielem historii, filarów ani tożsamości bazowych konfliktów.

To jest najważniejsza granica architektoniczna całych pięciu sprintów — dzięki niej możemy rozwinąć walkę do wielu graczy, nie rozwalając stabilności `conflict_id`, nad którą siedzieliśmy tyle czasu.

# Sprint 130.8.6 — Operation Feedback System MVP

Zakres sprintów `130.8.6.1–130.8.6.6`.

## Decyzja wykonawcza dla CHAOS

Sprinty `130.8.6.1–130.8.6.3` są jednym **implementacyjnym spike'em**
`OFS-SPIKE-01`, działającym wyłącznie za domyślnie wyłączonymi feature flags.
Nie wykonujemy wcześniej osobnego ręcznego proof-of-concept i nie włączamy OFS
produkcyjnie przed decyzją `GO`.

Znaczenie bramki:

```text
130.8.6.1–130.8.6.3 = prototyp runtime za flagą
GO                 = można generalizować engine w 130.8.6.4–130.8.6.6
REVISE             = zatrzymujemy blok i poprawiamy kontrakt/prototyp
```

`GO` nie oznacza automatycznego produkcyjnego cutoveru. Włączenie produkcyjne
pozostaje osobną decyzją po testach, z zachowaniem legacy pending UI jako
rollbacku.

## Źródło security state

OFS nie dodaje security do body `/gonna-win` i nie wykonuje dodatkowego requestu.
Przy starcie okna sesja bierze lokalny snapshot z:

```text
toolbarProfile.aimed_target.security
```

Snapshot jest używany tylko wtedy, gdy aktualny `aimed_target` odpowiada
`expected_target` zapisanemu w launch context. Projekcja dopuszcza wyłącznie
kanoniczne klucze security znane OFS oraz wartości `true`, `false`, `unknown`.
Brak klucza, brak celu lub zmiana tożsamości celu oznacza `unknown`, nigdy
`disabled`.

Snapshot:

* istnieje tylko w lokalnej sesji OFS;
* nie trafia do datasetu DOM, telemetry ani requestu gameplayowego;
* nie jest odświeżany w trakcie tej samej sesji;
* służy do filtrowania narracji, a nie do rozstrzygania gameplayu.

## Deterministyczne testy czasu

Przebiegi szybki, średni i długi testujemy przez wstrzykiwany zegar/timery oraz
kontrolowane Promise odpowiedzi w testach frontendowych. Produkcyjny
`/gonna-win` nie otrzymuje debug delay, dodatkowego endpointu ani sztucznego
timeoutu. Ręczne testy rzeczywistych opóźnień są uzupełnieniem, nie podstawą
walidacji schedulera.

Celem całego bloku nie jest jeszcze stworzenie kompletnej biblioteki treści dla wszystkich 12 operacji.

Celem jest zbudowanie, sprawdzenie i ustabilizowanie **silnika OFS**, który potrafi:

* uruchomić feedback równolegle z `/gonna-win`,
* składać sceny z danych,
* reagować na prawdziwy payload,
* obsługiwać trzy typy prezentacji,
* respektować `security -> interactions`,
* obsługiwać lokalny `presentation_state`,
* wykorzystywać content autora aplikacji,
* bezpiecznie fallbackować do starego pending UI,
* działać dla wszystkich 12 `action_key`.

Równolegle z implementacją każdy sprint musi aktualizować dokumentację powiązaną z OFS i rzeczywistym runtime aplikacji.

Obowiązkowo aktualizowane są co najmniej:

* `operation_feedback_system_production.md` — główny kontrakt architektury, lifecycle, scheduler, renderery, struktura danych, fallback i zasady integracji OFS;
* `project_journal.md` — zapis wykonanych zmian, decyzji architektonicznych, wyników testów, zmian zakresu oraz statusu kolejnych etapów `130.8.6.x`;
* dokumentacja AppForge i kontraktu aplikacji — jeżeli sprint zmienia sposób wykorzystania `interface`, `levels`, `feedback_content`, contentu autora, `buttons`, `options`, `progressbar_random` albo sposobu uruchamiania aplikacji;
* dokumentacja runtime aplikacji — jeżeli zmienia się lifecycle okna, integracja z `/gonna-win`, obsługa pending state, cleanup, cancellation, completion, failure albo publikacja wyniku;
* dokumentacja map actions i kontraktu operacji — jeżeli zmienia się mapowanie `action_key`, presentation mode, security, interactions albo sposób przekazywania kontekstu operacji do aplikacji;
* dokumentacja frontendowego flow / `APP_FLOW` — jeżeli sprint dodaje telemetry, nowe zdarzenia sesji OFS albo zmienia istniejący przebieg uruchomienia aplikacji;
* pozostałe istniejące pliki dokumentacji bezpośrednio opisujące element runtime'u zmieniany w danym sprincie.

Dokumentacja musi być aktualizowana razem z kodem, a nie zbiorczo po zakończeniu całego bloku. Po każdym sprincie `130.8.6.x` opis w dokumentach ma odpowiadać faktycznie zaimplementowanemu stanowi.

Jeżeli implementacja wymusi zmianę wcześniejszego założenia z `operation_feedback_system_production.md`, zmiana musi zostać najpierw jawnie opisana jako decyzja kontraktowa i odnotowana w `project_journal.md`. Nie należy zostawiać lokalnych wyjątków w kodzie, które nie istnieją w dokumentacji.

Po zakończeniu `130.8.6.6` dokumentacja ma przedstawiać rzeczywisty stan produkcyjnego MVP OFS, w szczególności:

* aktualny lifecycle sesji,
* strukturę `operation_feedback.v1.json`,
* trzy renderery,
* kontrakt `security -> interactions`,
* `presentation_state`,
* integrację z contentem autora aplikacji,
* fallback i feature flags,
* telemetry,
* integrację z `/gonna-win`,
* zasady cleanup i cancellation,
* profile wszystkich 12 `action_key`.

Pełne ręczne uzupełnienie słownika treści dla wszystkich operacji będzie osobnym sprintem po zakończeniu `130.8.6.6`. Ten późniejszy sprint rozszerza content według ustalonego kontraktu, ale nie powinien już wymagać przebudowy architektury OFS.


---

# Sprint 130.8.6.1 — OFS Core + scan_ports Session

## Cel

Zbudować minimalny działający rdzeń Operation Feedback System i uruchomić go wyłącznie dla `scan_ports`.

To jest pierwszy techniczny krok implementacyjnego `OFS-SPIKE-01`. Powstaje
minimalny engine runtime, ale pozostaje nieaktywny bez jawnego włączenia obu
flag i nie stanowi jeszcze zgody na produkcyjny cutover.

Nie budujemy jeszcze pełnego systemu scen ani rozbudowanego UI.

Najpierw udowadniamy podstawową rzecz:

> OFS może działać równolegle z `/gonna-win`, zostać przerwany payloadem w dowolnym momencie i nie wpływać na gameplay.

## Zakres

Powstaje podstawowy `OperationFeedbackSession`.

Sesja otrzymuje minimum:

```text
session_id
action_key
presentation_mode
app_id
flow_id
launch_receipt
renderer_host
security_state
```

`security_state` jest niemutowalną, lokalną projekcją opisaną w decyzji dla
całego bloku. Sesja nie może pobrać go ponownie ani zastąpić snapshotem innego
celu po zmianie `aimed_target`.

Obsługiwany jest lifecycle:

```text
idle
starting
running
awaiting_payload
completing
failed
cancelled
disposed
```

Na tym etapie można technicznie uprościć wewnętrzną implementację, ale zachowanie zewnętrzne musi odpowiadać temu kontraktowi.

## Integracja z `/gonna-win`

Dla `scan_ports`:

1. użytkownik uruchamia aplikację,
2. tworzona jest OFS Session,
3. request `/gonna-win` startuje natychmiast,
4. OFS rozpoczyna prezentację,
5. payload albo błąd kończy OFS,
6. obecny handler `/gonna-win` publikuje wynik dokładnie jak przed zmianą.

Completion OFS nie może wstrzymać publikacji payloadu. Jeżeli pokazujemy krótką
animację końcową, działa ona obok aktualizacji wyniku i może zostać natychmiast
przerwana przez cleanup okna.

### Adapter do obecnych interfejsów

OFS owija istniejący punkt wysłania requestu; nie tworzy drugiej ścieżki
`/gonna-win`:

* `terminal` — zastępuje bezpośredni start `notifyGonnaWin()` wspólnym wrapperem
  session + request;
* `window` i `button_choices` — sesja startuje dopiero po istniejącym wyborze
  gameplayowym, bez przejmowania jego `choice_id`;
* `progressbar_random` — przy aktywnym OFS fikcyjne kroki nie blokują już startu
  requestu; request i sesja zaczynają się razem, a stary progress pozostaje
  wyłącznie ścieżką flag-off/fallback;
* presentation mode `button_choice` nie zmienia `app.interface` ani kontraktu
  launchera — renderer OFS montuje się w istniejącym viewporcie.

Wspólny wrapper musi zachować aktualne `flow_id`, `launch_key`,
`launch_receipt`, `expected_target`, kolejkę/idempotencję oraz dokładnie jeden
request na rzeczywisty wybór aplikacji.

OFS nie może:

* opóźniać requestu,
* wykonywać własnego requestu gameplayowego,
* zmieniać body requestu,
* interpretować gameplayu,
* zatrzymywać publikacji wyniku.

## Minimalny renderer

Na tym etapie tylko `button_choice`, ponieważ pierwszym profilem jest `scan_ports`.

Renderer powinien już działać w istniejącym viewporcie aplikacji.

Nie tworzymy nowego okna.

Minimalna scena może zawierać:

* tytuł/stan,
* 2–5 linii,
* clear/replace,
* completion.

Jeszcze bez rozbudowanej dramaturgii.

## Cancellation

Każdy delay, timeout i callback musi być związany z sesją.

Po:

```text
payload
error
window_closed
new_request
dispose
```

stara sesja nie może już zmienić DOM.

To jest jeden z głównych warunków sprintu.

## Fallback

Jeżeli:

* profil nie istnieje,
* renderer nie istnieje,
* OFS rzuci wyjątek,
* host został usunięty,

frontend natychmiast wraca do obecnego pending UI.

Request `/gonna-win` działa dalej.

## Feature flag

Wprowadzić minimum:

```text
CHAOS_OPERATION_FEEDBACK_ENABLED
CHAOS_OPERATION_FEEDBACK_SCAN_PORTS
```

Domyślnie wyłączone.

## Wynik sprintu

Po `130.8.6.1` można uruchomić `scan_ports` i zobaczyć prostą prezentację OFS trwającą dokładnie tyle, ile faktycznie trwa request.

Szybka odpowiedź kończy ją szybko.

Długa odpowiedź pozwala jej pracować dalej.

Zamknięcie okna pozostawia czysty runtime.

Gameplay pozostaje bez zmian.

## Status realizacji — 2026-08-09

Zrealizowano rdzeń spike'a za dwiema domyślnie wyłączonymi flagami. Dodano
`OperationFeedbackSession`, minimalny renderer `button_choice`, lifecycle,
session-owned timery i cleanup dla `payload`, błędu, zamknięcia okna, nowego
requestu oraz auto-close.

Istniejące ścieżki `notifyGonnaWin()` i `sendGonnaWinRequest()` zostały owinięte
adapterem bez dodawania drugiego requestu. `window` i `button_choices` startują
sesję po wyborze, `terminal` po zamontowaniu okna, a `progressbar_random` przy
aktywnym OFS nie opóźnia requestu fikcyjnymi krokami. Przy flag-off albo błędzie
startu OFS pozostaje dotychczasowy pending UI.

Akcja mapy jest zachowywana w launch queue. Lokalny `security_state` jest
zamrożoną projekcją zgodnego `aimed_target`, nie trafia do body `/gonna-win` ani
do datasetu DOM. Payload jest publikowany przez dotychczasowe handlery przed
krótkim wizualnym domknięciem sesji.

---

# Sprint 130.8.6.2 — Scene Composer + Security Matrix

## Cel

Zamienić prostą prezentację z poprzedniego sprintu w rzeczywiście składany z danych przebieg `scan_ports`.

To jest właściwy środek `OFS-SPIKE-01`.

Silnik ma przestać odtwarzać gotową sekwencję i zacząć komponować sceny według ograniczeń.

## Kontrakt JSON MVP

Powstaje roboczy:

```text
static/data/operation_feedback.v1.json
```

Na tym etapie plik może zawierać tylko dane potrzebne dla `scan_ports`.

Minimalne sekcje:

```text
defaults
duration_profiles
scene_library
security_library
choice_library
completion_library
failure_library
operations
```

`transport_library` może istnieć w wersji minimalnej.

## Scene library

Scena opisuje dramaturgię, a nie technikę operacji.

Przykładowe rodziny MVP:

```text
boot
probe
security_contact
verification
payload_wait
```

Scena określa np.:

```text
sequence
min_lines
max_lines
pause range
transition
allow_choice
```

Nie zawiera wiedzy o firewallu ani konkretnym celu.

## Security library

Dla `scan_ports` wystarczą minimum trzy zabezpieczenia.

Proponowany zestaw:

```text
scan_detection
firewall
firewall_core
```

Opcjonalnie:

```text
network_anomaly_detection
system_visibility
vpn_blocker
```

Najważniejsza jest jawna macierz:

```text
scan_detection
    -> probe
    -> detect

firewall
    -> probe
    -> bypass
    -> route

firewall_core
    -> probe
    -> enumerate
```

Nie istnieje niezależne:

```text
security_keys[]
interaction_types[]
```

które scheduler później dowolnie łączy.

Scheduler zawsze robi:

```text
security
-> interaction dozwolony dla tego security
-> wariant treści
```

## Composer

Scheduler powinien już potrafić:

* wybierać rodzinę sceny,
* unikać identycznej sceny dwa razy z rzędu,
* dobrać właściwe security,
* dobrać właściwą interaction,
* wybrać wariant tekstu,
* dobrać timing,
* sprawdzić cancellation przed i po `await`,
* zakończyć wszystko natychmiast po payloadzie.

## Anti-repeat MVP

Wystarczy krótka lokalna historia:

```text
last_scene
last_security
last_line
```

Nie budujemy jeszcze skomplikowanego algorytmu różnorodności.

Chodzi o wyeliminowanie najbardziej widocznych powtórzeń.

## Profile czasu

Silnik zaczyna adaptować zachowanie do czasu, który faktycznie upłynął.

Minimum:

```text
instant
short
medium
long
very_long
```

Nie zakładamy z góry, ile potrwa request.

Scheduler jedynie zmienia dostępne pule scen zależnie od `elapsed_ms`.

Przykład:

pierwsze sekundy:

```text
boot
probe
```

później:

```text
security_contact
verification
```

jeszcze później:

```text
payload_wait
```

## Payload priority

Payload musi przerwać:

* delay,
* scenę,
* wybór kolejnej sceny,
* przejście,
* pending render.

Po payloadzie scheduler nie może wygenerować nawet jednej kolejnej linii.

## Wynik sprintu

Po `130.8.6.2` wielokrotne uruchomienie `scan_ports` powinno już generować kilka różnych, ale technicznie zgodnych przebiegów.

Nie chodzi jeszcze o piękne treści.

Chodzi o udowodnienie kompozycji.

## Status realizacji — 2026-08-09

Zrealizowano roboczy kontrakt `static/data/operation_feedback.v1.json` wyłącznie
dla `scan_ports`. Plik zawiera wymagane biblioteki, pięć adaptacyjnych profili
czasu, pięć rodzin scen i jawną macierz sześciu zabezpieczeń. Interakcje są
wybierane dopiero po security; profil nie posiada niezależnych list tworzących
przypadkowy iloczyn kombinacji.

Session ładuje i waliduje profil asynchronicznie, a composer dobiera scenę,
security, dozwoloną interaction, wariant tekstu i timing. Krótka historia
`last_scene`, `last_security`, `last_line` ogranicza bezpośrednie powtórzenia.
Brak aktywnego, znanego security prowadzi do neutralnej linii operacyjnej, nie
do zgadywania stanu zabezpieczenia.

Każdy callback schedulera pozostaje własnością sesji. Payload lub błąd najpierw
czyści timery i zmienia stan, a nierozwiązany loader i callbacki sprawdzają stan
przed renderem. Biblioteka transportowa nie jest losowana; w tym sprincie służy
wyłącznie jako przygotowany kontrakt dla prawdziwych sygnałów runtime.

---

# Sprint 130.8.6.3 — Interactive scan_ports + Presentation State + GO/REVISE

## Cel

Domknąć `OFS-SPIKE-01` jako działający MVP.

Dodajemy prawdziwe narracyjne decyzje użytkownika, lokalny `presentation_state`, content aplikacji oraz testujemy, czy model rzeczywiście daje różnorodne i sensowne przebiegi.

Po tym sprincie musi zapaść decyzja:

```text
GO
```

albo:

```text
REVISE
```

dla dalszej architektury.

## Choice library

Dodać minimum trzy narracyjne wybory dla `scan_ports`.

Przykładowe kierunki:

```text
MASKUJ / KONTYNUUJ
PONÓW / POMIŃ
TRYB CICHY / TRYB SZYBKI
```

Nie muszą to być dokładnie te teksty.

Każdy choice posiada:

```text
choice_id
effect_scope = presentation
options
timeout_ms
default_value
presentation_state mutation
```

Każdy `choice_id` ma prefix:

```text
feedback.
```

## Timeout

Brak reakcji użytkownika:

* nie zatrzymuje sceny,
* wybiera default,
* zapisuje wynik lokalnie,
* przechodzi dalej.

Payload podczas countdownu:

* natychmiast blokuje przyciski,
* kończy countdown,
* przechodzi do completion.

## Presentation state

MVP musi udowodnić, że wybór użytkownika wpływa na dalszą narrację.

Przykład:

```text
MASKUJ
```

ustawia:

```text
scan_mode = masked
```

i przez następne sceny scheduler może preferować warianty:

```text
masked probe sequence
reduced probe frequency
low visibility route
```

Jeżeli user wybierze:

```text
KONTYNUUJ
```

takie warianty nie powinny się pojawiać.

Ten stan:

* nie trafia do backendu,
* nie trafia do trwałego storage,
* nie zmienia kosztu,
* nie zmienia wyniku,
* nie zmienia czasu gameplayowego,
* znika po `dispose`.

## Content autora aplikacji

W tym sprincie sprawdzamy także drugą bardzo ważną część modelu.

Minimum dwie różne aplikacje obsługujące `scan_ports` powinny korzystać z jednego profilu technicznego OFS, ale zachowywać inny charakter.

Na MVP można wykorzystać projekcję istniejącego `levels`:

```text
title
text
description
command
logs
list
steps
```

Content autora może wypełniać neutralne sloty:

```text
boot
operation
transition
```

ale nie może sam stwierdzać sukcesu ani tworzyć security/interactions spoza profilu.

## Test trzech przebiegów

Wygenerować i obejrzeć minimum:

### szybki

Backend odpowiada w kilka sekund.

### średni

Backend odpowiada po kilkunastu/kilkudziesięciu sekundach.

### długi

Backend pozostaje pending wystarczająco długo, żeby wejść w dodatkowe security/verification/payload_wait.

Każdy przebieg musi:

* być rozpoznawalny jako `scan_ports`,
* wyglądać inaczej,
* nie kłamać o stanie backendu,
* nie używać obcego security,
* poprawnie reagować na wybory.

## GO / REVISE

`GO`, jeżeli:

1. scheduler potrafi stworzyć co najmniej trzy różne sensowne przebiegi;
2. nie potrzeba specjalnych hardcoded scenariuszy;
3. security i dramaturgia pozostają rozdzielone;
4. wybory zmieniają lokalną narrację;
5. content dwóch aplikacji nadaje im różny charakter;
6. payload może przerwać każdą scenę;
7. silnik nie wpływa na wynik `/gonna-win`.

Jeżeli którykolwiek z fundamentów wymaga wyjątków per aplikacja albo per scena:

```text
REVISE
```

i najpierw poprawiamy kontrakt.

## Wynik sprintu

Po `130.8.6.3` mamy działający `scan_ports` MVP oraz potwierdzony albo odrzucony model architektoniczny.

Dopiero `GO` otwiera sprint `130.8.6.4`.

## Status realizacji — 2026-08-09

`OFS-SPIKE-01` zakończony decyzją architektoniczną `GO`. Decyzja otwiera
generalizację w `130.8.6.4`, ale nie włącza produkcyjnego cutoveru.

Dodano trzy wybory `feedback.*` z timeoutem i domyślną wartością. Mutacje są
walidowane przez `presentation_state_schema`, istnieją tylko w sesji i znikają
przy dispose. Payload czyści countdown, blokuje przyciski i uniemożliwia dalszy
render. OFS nie posiada ścieżki `/gonna-win`, a dane wyboru nie trafiają do body
istniejącego requestu.

Prywatny snapshot contentu aplikacji korzysta z priorytetu
`app_structured -> app_legacy -> global_fallback`. Projekcja legacy obejmuje
neutralne pola `command/logs/list/steps/text/description`, pomija gameplayowe
`buttons/options`, filtruje HTML, fałszywy sukces i zdarzenia transportowe.
Completion autora jest używany dopiero po prawdziwym payloadzie.

Deterministyczne przebiegi szybki, średni i długi oraz listę świadomych luk
zapisano w `doc/operation_feedback_spike_01_results.md`. Dwie syntetyczne
aplikacje zachowują odmienne głosy bez duplikowania profilu lub schedulera;
`MASKUJ` wpływa na kilka kolejnych scen.


# Sprint 130.8.6.3.1 — Unified Launch Context + Provisional Application Window

## Cel

Usunąć czarną dziurę występującą pomiędzy wyborem aplikacji przez użytkownika a faktycznym uruchomieniem jej przez launcher.

Obecnie dla operacji uruchamianych z mapy przebieg wygląda w uproszczeniu:

```text
map action
→ map pending
→ application picker
→ wybór aplikacji
→ długie oczekiwanie na launcher
→ pojawienie się aplikacji
→ OFS
→ payload
```

OFS obsługuje już oczekiwanie po uruchomieniu aplikacji, ale nie obsługuje czasu pomiędzy:

```text
picker
→ launcher
```

Celem sprintu jest przeniesienie momentu pojawienia się aplikacji na frontend.

Po wyborze narzędzia użytkownik powinien zobaczyć jego okno natychmiast, korzystając z danych aplikacji już dostępnych lokalnie.

Backend nadal pozostaje źródłem prawdy dla faktycznego uruchomienia aplikacji.

## Dostosowanie do aktualnego runtime CHAOS

Audyt kodu wykazał, że obecna czarna dziura nie jest pojedynczym oczekiwaniem
na „launcher”. Mapowy flow przechodzi dziś przez:

```text
/hack-action
→ zapis do transient launch_queue
→ polling /launch-queue (do 10 s)
→ /command z source=launch_queue
→ applicationEffect
→ launchApplicationEffect()
→ app_window / app_progressbar_random / app_terminal / app_button_choices
```

Sprint nie zastępuje tego autorytatywnego łańcucha. Dodaje lokalne okno po
read-only preflighcie, ale przed wykonawczym requestem `/hack-action` z
`selected_app_id`. Wynik `applicationEffect` pozostaje do hydracji w
`130.8.6.3.2`.

Obecnie preflight kończy się odpowiedzią tylko przy wielu dopasowaniach. Przy
jednej aplikacji ten sam request przechodzi od razu do mutacji i kolejki, więc
frontend nie dostaje chwili na bezpieczne utworzenie okna. 6.3.1 ujednolica tę
granicę: request bez `selected_app_id` jest wyłącznie discovery/preflightem i
zwraca jeden albo wiele bezpiecznych snapshotów; mutacja zaczyna się dopiero w
requestcie z jawnym `selected_app_id`.

Zakres implementacyjny 6.3.1 obejmuje najpierw mapowy flow, bo tam występuje
realna luka UX. `desktop`, `start_menu` i `terminal` muszą być poprawnymi
wartościami kontraktu, ale ich pełny cutover nie jest warunkiem zamknięcia tego
sprintu.

---

## 1. Unified Launch Context

Wprowadzić wspólny frontendowy kontekst uruchomienia aplikacji.

Powinien on rozróżniać co najmniej źródło startu:

```text
map
desktop
start_menu
terminal
```

Kontekst nie powinien tworzyć osobnych ścieżek runtime dla każdego źródła.

Ma normalizować wejście do wspólnego launch flow.

Powinien zawierać dostępne informacje, np.:

```text
launch_source
app_id
app_snapshot
target_snapshot
requested_action
flow_id
launch_receipt, jeśli już istnieje
```

Zakres informacji zależy od źródła uruchomienia.

Brak celu nie jest błędem.

---

## 2. Uruchomienie z mapy

W przypadku uruchomienia z mapy frontend zna:

* wybraną akcję,
* target,
* listę pasujących aplikacji,
* aplikację wybraną w pickerze,
* jej podstawowy snapshot.

Po kliknięciu `Użyj` w pickerze:

1. picker kończy własny pending state;
2. frontend natychmiast tworzy okno wybranej aplikacji;
3. okno przechodzi do lokalnego stanu `launching`;
4. request launchera trwa równolegle;
5. użytkownik nie pozostaje bez aktywnego UI.

Launcher nie powinien już być warunkiem utworzenia pierwszego widocznego okna.

Obie mapowe ścieżki muszą wejść do tej samej funkcji `beginProvisionalLaunch`:

### Kilka pasujących aplikacji

```text
matching_apps.length > 1
→ picker
→ Użyj
→ provisional window
→ /hack-action
```

### Dokładnie jedna pasująca aplikacja

```text
matching_apps.length === 1
→ bez pickera
→ automatyczny wybór jedynej aplikacji
→ provisional window natychmiast
→ wykonawczy /hack-action z selected_app_id
```

Brak pickera nie może oznaczać starego oczekiwania na `launch_queue`. Skrót
pomija wyłącznie ekran wyboru, a nie launch context, idempotencję, provisional
session ani request backendowy. Dla zera pasujących aplikacji pozostaje
dotychczasowy komunikat/fallback.

W obu wariantach okno powstaje po odpowiedzi discovery, ale przed rozpoczęciem
oczekiwania na odpowiedź wykonawczego `/hack-action`. Samo jego utworzenie nie może wykonywać `/gonna-win`,
`notifyGonnaWin`, `operation_only`, `/command` ani drugiego `/hack-action`.

Frontend nie odtwarza backendowych reguł dopasowania aplikacji. Jedyny
kandydat musi pochodzić z tego samego `get_apps_for_map_action()` i
`serialize_tool_selection_app()`, które obsługują picker. Odpowiedź może jawnie
oznaczyć `auto_select: true`; nie jest to potwierdzenie launchu ani sukcesu.

---

## 3. Provisional Application Window

Powstające lokalnie okno jest początkowo `provisional`.

Oznacza to:

> użytkownik poprosił o uruchomienie tej aplikacji, ale backend jeszcze nie potwierdził pełnego launch state.

Provisional window może korzystać wyłącznie z danych znanych frontendowi.

Może pokazać:

* nazwę aplikacji,
* ikonę,
* autora, jeśli jest dostępny,
* opis,
* rodzaj interfejsu,
* podstawowy content autora,
* lokalny launch/boot feedback.

Nie może jeszcze prezentować jako prawdziwych informacji wymagających odpowiedzi launchera.

Provisional window jest rejestrowane w pamięci pod stabilnym lokalnym kluczem
sesji. Dla mapy klucz powstaje z istniejącego `flow_id` / `_client_action_key`
oraz `app_id`, a po odpowiedzi może zostać związany z `launch_receipt`.

Nie używamy jako tożsamości samego `interface:app_id`, tytułu ani nazwy.
Obecne `beginApplicationWindowLaunch()` deduplikuje okna po `interface:app_id`;
ta ochrona pozostaje dla legacy, ale nie może być rejestrem provisional
session ani blokować dwóch niezależnych launchy tej samej aplikacji.

---

## 4. Pierwsza faza prezentacji — Launch

Po utworzeniu okna uruchamiana jest krótka prezentacja launch.

Nie jest ona jeszcze operacją hackowania.

Jej zadaniem jest przejście pomiędzy:

```text
wybrałem aplikację
```

a:

```text
aplikacja została przygotowana do działania
```

Przykładowy charakter prezentacji:

```text
V-MAP
created by admin

inicjalizacja środowiska
ładowanie lokalnego profilu
przygotowanie interfejsu
```

Treści muszą wynikać z rzeczywiście znanych frontendowi danych albo bezpiecznej globalnej biblioteki launch.

Nie wolno symulować:

```text
backend connected
launch confirmed
remote session established
```

jeżeli nie zostało to faktycznie potwierdzone.

W 6.3.1 launch/boot jest minimalnym, bezpiecznym shellem. Pełne rozkładanie
contentu autora, fazy lifecycle i przejście do OFS należą do 6.3.2. Dzięki temu
nie budujemy tymczasowego drugiego schedulera tylko po to, aby usunąć lukę UX.

---

## 5. Boot jako scena frontendowa

Po fazie launch może rozpocząć się `boot`.

Boot nie powinien być starym sztywnym loaderem aplikacji.

Powinien korzystać z tego samego kierunku prezentacyjnego co OFS:

* krótkie sceny,
* content autora,
* zmienne rytmy,
* brak nieskończonego logu,
* brak fikcyjnego procentu postępu.

Dopuszczalny jest wizualny activity bar lub segmentowy loader, ale nie powinien sugerować rzeczywistego procentowego postępu, jeżeli takiej informacji nie dostarcza backend.

---

## 6. Content autora

Na etapie provisional można wykorzystać bezpieczne elementy istniejącego snapshotu aplikacji:

```text
title
description
text
command
logs
list
steps
```

Ich wykorzystanie zależy od interfejsu.

Content autora nadal podlega regułom bezpieczeństwa semantycznego.

Nie wolno przed potwierdzeniem runtime wyświetlać jako fakt:

```text
success
failure
target compromised
security disabled
operation completed
```

---

## 7. Rozróżnienie celu operacji

Launch context powinien zachowywać informację, dlaczego aplikacja została uruchomiona.

Szczególnie przy uruchomieniu z mapy nie wystarcza samo:

```text
app_id
```

Potrzebny jest kontekst:

```text
target
+
requested action
+
capability aplikacji
```

Ta sama aplikacja może w przyszłości być wykorzystywana w różnych kontekstach celu.

Nie należy wyprowadzać działania wyłącznie z nazwy aplikacji.

---

## 8. Uruchomienie z desktopu i terminala

Sprint nie musi jeszcze domykać pełnej logiki działania tych źródeł, ale Unified Launch Context musi być zaprojektowany tak, aby ich później nie traktować jako osobnych runtime'ów.

Uruchomienie z desktopu:

* okno aplikacji może pojawić się natychmiast;
* jeżeli istnieje aktywny cel, może zostać dołączony do launch context;
* jeżeli celu brak, aplikacja uruchamia się w neutralnym kontekście.

Uruchomienie z terminala:

* powinno finalnie przechodzić przez ten sam launch lifecycle;
* terminal jest wyłącznie innym źródłem intencji uruchomienia.

---

## 9. Boundaries

Sprint nie zmienia:

* wyniku gameplayu,
* działania `/gonna-win`,
* receiptów,
* idempotencji,
* mechaniki hackowania celu,
* działania Centrum Operacji,
* reguł pełnego przejęcia obiektu.

Nie wdrażamy jeszcze całej generalizacji 12 operacji.

Nie przebudowujemy jeszcze trzech rendererów.

Nie zmieniamy formatu `launch_queue`, atomowego consume w store ani pollingu
na push. Nie wykonujemy ciężkich operacji w preflighcie i nie przenosimy autorytatywnego launchu
do frontendu. Zamknięcie provisional window sprząta prezentację, ale nie
anuluje już wysłanego `/hack-action`; późniejszy wynik obsłuży tombstone/fallback
zdefiniowany w 6.3.2.

Całość pozostaje za osobną, domyślnie wyłączoną flagą provisional launch.
Awaria tworzenia shella ma pozwolić przejść istniejącemu flow do klasycznego
okna z `applicationEffect`.

## 10. Plan wejścia w kod i testy

Najbardziej wrażliwe miejsca tego sprintu:

* `run.py` — read-only preflight `/hack-action`, także dla jednego kandydata;
* `templates/map_template.html` — rozpoznanie wyniku discovery i przekazanie go
  do desktopu bez kopiowania reguł aplikacji;
* `static/js/terminal.js` — wspólna ścieżka manualnego i automatycznego wyboru,
  launch context, provisional registry, cleanup i feature flag;
* istniejące testy idempotencji `/hack-action` — muszą potwierdzić, że discovery
  nie zapisuje idempotency result, nie tworzy operacji i nie dotyka celu;
* nowe testy frontendowe — dokładnie jedno okno przed requestem wykonawczym,
  0/1/wiele aplikacji, podwójny klik, zamknięcie oraz flaga off.

Nie wykonujemy testu wyłącznie przez liczenie okien. Asercje obejmują liczbę
requestów, `selected_app_id`, `flow_id`, client action key, stan registry oraz
brak `/gonna-win` przed wejściem aplikacji w prawdziwą interakcję.

---

## 11. Dokumentacja

Sprint musi zaktualizować:

* `operation_feedback_system_production.md`,
* `project_journal.md`,
* dokumentację launchera aplikacji,
* dokumentację AppForge / kontraktu aplikacji, jeżeli wykorzystanie snapshotu lub `levels` zostanie doprecyzowane,
* dokumentację runtime aplikacji,
* dokumentację map action flow, jeżeli zmienia się relacja picker → launcher → app window.

Dokumentacja ma przedstawiać rzeczywisty flow po sprincie, a nie historyczny model, w którym launcher zawsze tworzy okno dopiero po własnej odpowiedzi.

---

## Definition of Done

Sprint jest gotowy, gdy:

1. wybór aplikacji w pickerze natychmiast tworzy provisional window;
2. użytkownik nie pozostaje w czarnej dziurze podczas oczekiwania na launcher;
3. launcher nadal wykonuje swój dotychczasowy autorytatywny proces;
4. provisional window używa tylko danych dostępnych frontendowi;
5. istnieje wspólny `launch context`;
6. źródło launchu jest jawnie rozróżniane;
7. boot aplikacji może rozpocząć się przed odpowiedzią launchera;
8. nie pojawia się fałszywe potwierdzenie launchu;
9. awaria provisional UI nie blokuje requestu;
10. zamknięcie provisional window poprawnie czyści jego lokalny lifecycle;
11. działający `scan_ports` z `130.8.6.3` pozostaje bez regresji;
12. ścieżka z jedną pasującą aplikacją omija picker i natychmiast tworzy ten sam typ provisional session;
13. skrót jednej aplikacji nie wykonuje dodatkowego requestu gameplayowego;
14. dwa niezależne flow tej samej aplikacji nie są utożsamiane po samym `interface:app_id`;
15. wykonawczy request `/hack-action` rozpoczyna się niezależnie od powodzenia animacji provisional;
16. flaga off zachowuje obecny picker/launch_queue/applicationEffect flow;
17. request bez `selected_app_id` nie mutuje celu i zwraca jednoznaczny discovery wynik także dla jednej aplikacji;
18. frontend nie duplikuje backendowych reguł `get_apps_for_map_action()`;
19. dokumentacja odpowiada nowemu flow.

## Stan realizacji — 2026-08-09

Sprint zaimplementowany za domyślnie wyłączoną flagą
`CHAOS_PROVISIONAL_APP_LAUNCH_ENABLED`.

Backend zwraca read-only discovery także dla jednego kandydata i oznacza go
`auto_select=true`. Desktop kieruje auto-select oraz wybór z pickera przez
wspólne `selectMapActionTool()`, tworzy lokalny provisional shell przed
wykonawczym `/hack-action`, przechowuje sesję pod client action key + app id i
sprząta ją przy zamknięciu. Awaria shella nie blokuje requestu. Content opisu
przechodzi przez filtr OFS, a shell nie wywołuje `/gonna-win`.

Hydration przez `applicationEffect`, tombstone i eliminacja późniejszego
klasycznego duplikatu pozostają świadomie w 130.8.6.3.2. Z tego powodu flaga
6.3.1 nie jest jeszcze kandydatem do samodzielnego produkcyjnego cutoveru.

---

# Sprint 130.8.6.3.2 — Launcher Hydration + Unified Application Presentation Lifecycle

## Cel

Połączyć nowy provisional launch z istniejącym OFS tak, aby aplikacja posiadała jeden ciągły frontendowy lifecycle od chwili wyboru przez użytkownika aż do prawdziwego wyniku.

Docelowy przebieg:

```text
launch intent
→ provisional window
→ launch
→ boot
→ launcher hydration
→ author content
→ gameplay interaction
→ operation feedback
→ payload
→ result
```

Nie tworzymy kolejnego loadera.

Budujemy jeden prezentacyjny lifecycle aplikacji.

## Dostosowanie do aktualnego runtime CHAOS

W CHAOS hydration nie przychodzi jako osobny endpoint. Autorytatywnym
materiałem jest obecny `applicationEffect`, otrzymany po consume
`/launch-queue` i wykonaniu `/command`. `pollLaunchQueue()` nie może od razu
wołać klasycznego `launchApplicationEffect(appData)`, jeżeli istnieje zgodna
provisional session. Najpierw próbuje:

```text
normalizeLaunchQueueItem
→ resolve provisional session po receipt/flow/app
→ hydrate istniejące okno
→ dopiero przy braku zgodnej sesji legacy launchApplicationEffect
```

Nie zmieniamy backendowego kontraktu `/command` ani `applicationEffect`, jeśli
audyt implementacyjny nie wykaże braku pola niezbędnego do jednoznacznej
korelacji. Preferujemy istniejące `receipt`, `flow_id`, `app_id` i action.

---

## 1. Launcher przestaje tworzyć drugi egzemplarz okna

Jeżeli frontend utworzył już provisional window dla danego launch flow, odpowiedź launchera nie może uruchomić drugiego klasycznego okna.

Launcher powinien odnaleźć istniejącą sesję i wykonać jej `hydration`.

Czyli:

```text
provisional app
+
authoritative launch payload
=
hydrated app
```

Nie:

```text
provisional app
+
new app window
```

---

## 2. Tożsamość launch session

Hydration musi odnaleźć dokładnie tę sesję, której dotyczy odpowiedź.

Należy wykorzystać stabilne identyfikatory istniejącego flow.

Nie wolno opierać tego wyłącznie o:

* nazwę aplikacji,
* tekst tytułu,
* indeks okna,
* target label.

Równoległe uruchomienie dwóch takich samych aplikacji nie może prowadzić do hydracji złego okna.

Korelacja ma następujący priorytet:

```text
launch_receipt
→ dokładny local launch key (_client_action_key + app_id)
→ flow_id + app_id + requested_action, tylko gdy wynik jest jednoznaczny
→ brak dopasowania i bezpieczny fallback
```

`recentLaunchQueueReceipts`, `recentLaunchQueueApps` i
`beginApplicationWindowLaunch` pozostają zabezpieczeniami przed replayem, ale
nie mogą skonsumować odpowiedzi przed próbą hydracji. Potrzebny jest jawny
rejestr sesji oraz krótkotrwały tombstone po dispose.

---

## 3. Hydration

Po nadejściu odpowiedzi launchera provisional session zostaje wzbogacona o autorytatywne informacje.

Mogą to być m.in.:

* rzeczywisty launch state,
* wybrany level,
* pełniejszy content aplikacji,
* parametry runtime,
* informacje wymagane przez dalszą interakcję.

Hydration nie resetuje całego okna.

Nie powinno być wizualnego:

```text
stare okno znika
→ nowe okno pojawia się od zera
```

Aktualne okno ma płynnie przejść do kolejnej fazy.

Hydration jest idempotentna. Powtórzony receipt aktualizuje najwyżej tę samą
sesję i nie resetuje scen, nie duplikuje przycisków, nie odpala ponownie
`notifyGonnaWin` oraz nie tworzy drugiego OFS.

---

## 4. Jeden Application Presentation Lifecycle

Wprowadzamy jawne fazy prezentacji aplikacji.

Proponowany model MVP:

```text
launching
booting
hydrating
presenting
interactive
executing
completing
failed
disposed
```

Nie musi to być osobny gameplay state machine.

Jest to frontendowy lifecycle prezentacji.

Lifecycle ma jednego właściciela per launch session. OFS zachowuje własny
wewnętrzny lifecycle requestu, ale jest podpinany wyłącznie w fazie
`executing`; nie powstają dwa konkurencyjne schedulery piszące do tego samego
kontenera. Każde przejście fazy musi być walidowane, logowane przez istniejący
`APP_FLOW` i odporne na callback po `disposed`.

Każda faza odpowiada na inne pytanie.

### `launching`

Użytkownik wyraził intencję uruchomienia aplikacji.

### `booting`

Frontend prezentuje lokalny boot z danych, które posiada.

### `hydrating`

Odpowiedź launchera jest łączona z istniejącą sesją.

### `presenting`

Pokazywany jest właściwy content autora aplikacji.

### `interactive`

Pojawiają się prawdziwe elementy interakcji aplikacji, np. gameplayowe buttons/options.

### `executing`

Po wysłaniu właściwego requestu działania uruchamia się Operation Feedback System.

### `completing`

Przyszedł autorytatywny payload.

### `failed`

Prawdziwy błąd.

### `disposed`

Sesja zakończona i nie może już zmieniać DOM.

---

## 5. Content autora jako część lifecycle

Content autora nie powinien być jednym statycznym ekranem pojawiającym się po boot.

Powinien stać się materiałem używanym przez prezentacyjny runtime.

Przykład:

autor podał:

* nazwę,
* opis,
* trzy logi,
* dwa steps,
* trzy gameplayowe buttons.

Frontend może rozłożyć to na:

```text
launch
→ title + author
→ description
→ boot
→ log 1
→ log 2
→ transition
→ log 3
→ rzeczywiste buttons
```

Nie oznacza to losowego przepisywania intencji autora.

Renderer i scheduler jedynie organizują jego content w czasie.

---

## 6. Gameplay buttons pozostają gameplay buttons

Istniejące:

```text
buttons
options
```

nie stają się automatycznie wyborami narracyjnymi OFS.

Po wejściu w fazę `interactive` pojawiają się jako rzeczywiste elementy aplikacji.

Dopiero ich użycie może uruchomić właściwy request działania.

Narracyjne `feedback.* choices` pozostają osobnym mechanizmem prezentacyjnym.

---

## 7. Przejście do istniejącego OFS

Po wykonaniu prawdziwej akcji użytkownika aplikacja przechodzi do:

```text
executing
```

i uruchamia działający już engine OFS.

W przypadku `scan_ports` powinien zostać wykorzystany mechanizm zatwierdzony decyzją `GO` po `130.8.6.3`.

Nie tworzymy drugiego systemu oczekiwania.

Nowy lifecycle po prostu przekazuje kontrolę istniejącemu OFS.

---

## 8. Launch source a operation context

Lifecycle powinien zachowywać źródło uruchomienia i context operacji przez cały przebieg.

### Map

Mamy jawny:

```text
target
requested action
selected app
```

### Desktop / Start

Aplikacja może zostać uruchomiona bez targetu.

Jeżeli istnieje aktywny target, frontend może próbować zbudować operation context na podstawie rzeczywiście dostępnych danych aplikacji i celu.

Nie należy zgadywać operacji wyłącznie po nazwie aplikacji.

### Terminal

Docelowo ten sam model.

Źródło jest inne.

Lifecycle pozostaje ten sam.

---

## 9. Capability resolution

Sprint powinien przygotować miejsce na rozpoznanie, do czego dana aplikacja jest używana w aktualnym kontekście.

Nie chodzi jeszcze o pełną przebudowę systemu hackowania.

Chodzi o to, aby runtime nie zakładał:

```text
aplikacja X = zawsze action Y
```

Jeżeli aplikacja posiada kilka możliwości albo jest uruchomiona na celu o określonych właściwościach, operation context powinien móc określić właściwą ścieżkę.

W przypadku braku jednoznacznego kontekstu stosowany jest bezpieczny tryb domyślny lub neutralny.

---

## 10. Brak zmiany gameplayu

Nowy presentation lifecycle nie decyduje:

* czy obiekt jest w pełni shakowany,
* które „kropki” zostały przejęte,
* czy obiekt może być filarem,
* czy generuje pliki,
* jaki daje loot,
* czy operacja się udała.

Może natomiast użyć znanego frontendowi kontekstu tych elementów do dobrania właściwej prezentacji.

Prawda gameplayowa pozostaje backendowa.

---

## 11. Failure paths

Trzeba rozróżnić:

### Launcher failure

Provisional window już istnieje, ale launcher odrzuca uruchomienie.

Okno przechodzi do `failed` i pokazuje rzeczywisty błąd.

Nie udaje, że aplikacja została poprawnie uruchomiona.

### Window closed

Session zostaje disposed.

Późniejsza odpowiedź launchera nie może odtworzyć zamkniętego okna bez jawnej reguły runtime.

### Hydration mismatch

Jeżeli odpowiedzi nie da się jednoznacznie powiązać z provisional session, system nie powinien zgadywać.

Uruchamia diagnostykę/fallback zgodnie z istniejącymi zasadami.

### Jedna aplikacja bez pickera

Automatyczny wybór korzysta z identycznej hydration i failure path jak wybór
manualny. Jeżeli `/hack-action` odrzuci start, provisional window pokazuje
rzeczywisty błąd i nie czeka bez końca na wpis, który nigdy nie trafi do
`launch_queue`.

### Launch queue replay lub opóźniony polling

Powtórzony receipt nie tworzy okna. Późna odpowiedź hydratuje aktywną sesję;
jeżeli sesja ma tombstone po świadomym zamknięciu, nie zostaje wskrzeszona.
Brak sesji i brak tombstone uruchamia dotychczasowy legacy renderer.

---

## 12. Fallback

Jeżeli Unified Application Presentation Lifecycle nie może zostać użyty:

* requesty pozostają bez zmian,
* możliwy jest powrót do klasycznego launch flow,
* gameplay nie jest blokowany.

Nie usuwamy jeszcze legacy launch UI.

Fallback jest jednokierunkowy dla pojedynczego receiptu: albo hydration, albo
legacy launch. Nigdy oba. Błąd warstwy prezentacyjnej nie może usuwać wpisu z
kolejki przed wykorzystaniem autorytatywnego `applicationEffect`.

## 13. Plan wejścia w kod i testy

Najbardziej wrażliwe miejsca tego sprintu:

* `static/js/terminal.js` — `pollLaunchQueue()`, kolejność receipt dedupe,
  `launchApplicationEffect()`, `beginApplicationWindowLaunch()` i cztery
  istniejące renderery aplikacji;
* `static/js/operation_feedback.js` — wyłącznie granica start/complete/dispose;
  OFS nie przejmuje odpowiedzialności za launcher registry;
* `static/css/style.css` — stan provisional/hydrating bez fikcyjnego procentu;
* testy kontrolowanego pollingu i Promise — hydration przed/po zamknięciu,
  replay, mismatch, dwa równoległe okna tej samej aplikacji i flaga off;
* regresja czterech interfejsów oraz `scan_ports`, ze szczególnym sprawdzeniem
  `button_choices`, bo jego buttons/options są gameplayem, nie narracją.

Test ręczny obejmuje co najmniej: jedną aplikację bez pickera, kilka aplikacji
z pickerem, polling natychmiastowy i bliski 10 s, zamknięcie przed hydration,
ponowiony receipt oraz dwa równoległe flow tej samej aplikacji.

---

## 14. Dokumentacja

Sprint aktualizuje obowiązkowo:

* `operation_feedback_system_production.md`,
* `project_journal.md`,
* dokumentację launchera,
* dokumentację runtime aplikacji,
* dokumentację AppForge,
* dokumentację terminalowego launch flow,
* dokumentację mapowego picker flow,
* dokumentację desktop/start-menu launch flow,
* pozostałe pliki opisujące lifecycle, które zmieniła implementacja.

Po tym sprincie dokumentacja powinna już opisywać aplikację jako jeden frontendowy lifecycle, a nie osobne niezależne etapy launchera, bootu i OFS.

---

## Definition of Done

Sprint jest gotowy, gdy:

1. odpowiedź launchera hydratuje istniejące provisional window;
2. launcher nie tworzy duplikatu aplikacji;
3. istnieje jeden spójny lifecycle prezentacji;
4. boot płynnie przechodzi do contentu autora;
5. content autora może zostać rozłożony na sceny;
6. prawdziwe gameplayowe buttons/options pojawiają się dopiero we właściwej fazie;
7. po wykonaniu działania aplikacja przechodzi do istniejącego OFS;
8. payload nadal ma absolutny priorytet;
9. source `map / desktop / terminal` nie wymusza trzech osobnych runtime'ów;
10. operation context może zachować target i requested action;
11. zamknięcie okna poprawnie kończy cały lifecycle;
12. późna odpowiedź launchera nie ożywia disposed session;
13. brak jednoznacznego kontekstu nie powoduje losowego przypisania operacji;
14. istniejący `scan_ports` pozostaje zgodny z wynikiem `GO`;
15. wszystkie nowe ścieżki posiadają fallback;
16. auto-launch jednej pasującej aplikacji hydratuje to samo okno bez pickera;
17. powtórzony receipt nie duplikuje okna, contentu, przycisków ani requestu;
18. kilka równoległych launchy tej samej aplikacji hydratuje właściwe sesje;
19. hydracja jest próbowana przed legacy dedupe/launch;
20. aktywny tombstone blokuje wskrzeszenie świadomie zamkniętego okna;
21. testy obejmują discovery dla 0/1/wielu aplikacji, wykonawczą odpowiedź `/hack-action` oraz polling 0–10 s;
22. dokumentacja odpowiada rzeczywistej implementacji.

---

# Efekt po 130.8.6.3.2

Przed zmianą:

```text
MAP
→ picker
→ .......... czarna dziura ..........
→ aplikacja
→ OFS
→ wynik
```

## Stan implementacji 130.8.6.3.2

Sprint zaimplementowano za istniejącą, domyślnie wyłączoną flagą
`CHAOS_PROVISIONAL_APP_LAUNCH_ENABLED`. `pollLaunchQueue()` rozstrzyga sesję
przed legacy launch i hydratuje dokładnie ten provisional DOM. Korelacja używa
receiptu, local client action key i jednoznacznego fallbacku flow/app/action.
Jawny tombstone przez 120 sekund blokuje późne wskrzeszenie zamkniętego okna.

Cztery istniejące renderery korzystają ze wspólnego adaptera okna, więc nie
powielają contentu, przycisków ani requestów. `button_choices` zachowuje
autorytatywne options autora. Faza `executing/completing/failed` jest spięta z
istniejącą granicą OFS, a brak lokalnej sesji nadal prowadzi do legacy renderera.
Backendowy format kolejki, `/command`, `/gonna-win` i źródło prawdy gameplayu
nie zostały zmienione.

Po zmianie:

```text
MAP
→ picker
→ aplikacja pojawia się natychmiast
→ launch
→ boot
→ hydration
→ content autora
→ interaction
→ OFS
→ wynik
```

Dla desktopu i terminala będzie można następnie wejść w ten sam lifecycle od odpowiedniego punktu.

Dopiero po tym rozszerzeniu sensowne będzie przejście do `130.8.6.4` i generalizacja rendererów, ponieważ wtedy renderer będzie obsługiwał nie tylko „oczekiwanie po kliknięciu”, ale pełny prezentacyjny runtime aplikacji.

# Sprint 130.8.6.3.3 — Pre-Execution Scene System

## Status

Etap bazowy zamknięty. Composer i handoff do hydration są zaimplementowane
za istniejącą, domyślnie wyłączoną flagą `CHAOS_PROVISIONAL_APP_LAUNCH_ENABLED`.
Dalszy lift rendererów, profili i contentu przechodzi do 6.4–6.6.

## Cel

Zapewnić prezentację od utworzenia provisional window do hydration, bez
sugerowania postępu lub wyniku, którego backend jeszcze nie potwierdził.

```text
map action
→ read-only discovery
→ provisional window
→ pre-execution scenes
→ applicationEffect hydration
→ autorski interface i content
→ interakcja gameplayowa
→ OFS podczas /gonna-win
→ autorytatywny wynik
```

## Granice odpowiedzialności

Provisional presentation w `terminal.js` jest właścicielem faz `launching`,
`booting`, `hydrating`, `presenting` i `interactive`. Korzysta z lokalnego
snapshotu discovery, targetu, requested action i bezpiecznej projekcji contentu
autora. Nie wykonuje operacji gameplayowej.

OFS w `operation_feedback.js` zaczyna się przy prawdziwym requestcie
`/gonna-win` i jest właścicielem fazy `executing`. Sprint nie dodaje drugiego
schedulera do OFS ani scen launchera do profilu `scan_ports`.

Backend pozostaje właścicielem launch queue, hydration payloadu, operacji i
wyniku. Sprint nie zmienia endpointów, receiptów ani idempotencji.

## Kontrakt scen

| Rodzina | Faza | Dozwolona treść |
|---|---|---|
| `app_identity` | launching | nazwa, opis i ikona aplikacji |
| `local_init` | booting | lokalne przygotowanie interface |
| `context_bind` | booting | target i requested action |
| `runtime_prepare` | booting | gotowość lokalnego widoku |
| `hydration_wait` | booting | neutralne oczekiwanie na launcher |
| `ready` | hydrating/presenting | tylko po `applicationEffect` |

Pre-execution nie komunikuje rozpoczęcia skanu lub exploita, wyniku, capture,
błędu transportu bez sygnału, wyłączenia zabezpieczenia ani procentu postępu.
Pulsujące segmenty oznaczają aktywność, nie progress.

## Content

Priorytet: snapshot discovery → bezpieczny opis autora → interface → target i
requested action → neutralny fallback.

Gameplayowe `buttons/options`, completion i wykonawcze logi nie są renderowane
przed hydration. Pełny content autora przychodzi w `applicationEffect` i jest
renderowany przez istniejący interface w tym samym DOM.

## Scheduler i handoff

Scheduler jest lokalny dla provisional session i nie współdzieli stanu z OFS.

* hydration natychmiast przerywa scenę i nie czeka na animację;
* `hydration_wait` zwalnia maksymalnie do jednego ekranu na 9 sekund;
* dispose czyści timer;
* callback sprawdza sesję i DOM;
* równoległe uruchomienia mają niezależne schedulery;
* tombstone z 6.3.2 blokuje późne wskrzeszenie.

`applicationEffect` zawsze wygrywa:

```text
stop pre-execution timer
→ ten sam app-window
→ hydration
→ autorski renderer
→ interactive albo executing
```

## Fallback

Błąd composera pozostawia prosty provisional shell i nie blokuje
`/hack-action`, launch queue ani legacy renderera. Flaga wyłączona zachowuje
dotychczasowy launch flow.

## Zakres

1. Lokalny composer i anulowalny scheduler w provisional registry.
2. Viewport scen w istniejącym provisional window.
3. Cleanup przy hydration, dispose i błędzie.
4. Bezpieczna projekcja aplikacji, targetu, akcji i interface.
5. Handoff do czterech rendererów bez zmiany gameplayu.
6. Testy pollingu, zamknięcia, replayu i równoległych sesji.
7. Dokumentacja lifecycle i AppForge content boundary.

Poza zakresem: generalizacja rendererów 6.4, push/nowy endpoint, procentowy
progress, zmiana wyniku, profile każdej aplikacji i security przed `/gonna-win`.

## Test ręczny

Sprawdzić jedną aplikację bez pickera, wybór z pickera, cztery interface,
hydration po około 1 s i po co najmniej 20 s, zamknięcie przed hydration, dwa
równoległe uruchomienia tej samej aplikacji, `scan_ports` z OFS i flag-off.

## Definition of Done

1. Provisional window pokazuje znaczące sceny zamiast samego activity indicator.
2. Sceny korzystają z aplikacji, interface, targetu i requested action.
3. Content autora jest filtrowany semantycznie.
4. Nie pojawia się fałszywy progress, wynik ani stan transportu.
5. Hydration zatrzymuje scheduler, a długie oczekiwanie nie zalewa UI.
6. Dispose usuwa wszystkie timery.
7. Przyciski gameplayowe pojawiają się dopiero z autorytatywnym rendererem.
8. Jeden viewport ma jednego właściciela prezentacji.
9. Cztery interface i `scan_ports` nie mają regresji.
10. Flaga off, legacy fallback, testy i dokumentacja odpowiadają kodowi.

# Sprint 130.8.6.4 — Renderer Abstraction: ofs_provisional / terminal / button_choice / window

## Status

Zakończony. Wspólny scene envelope obsługują cztery odseparowane
renderery: `ofs_provisional`, `terminal`, `button_choice` i `window`.
`OperationFeedbackSession` deleguje DOM do fabryki rendererów, a dotychczasowy
`scan_ports` zachowuje tryb `button_choice` bez cutoveru pozostałych akcji.

## Cel

Oderwać engine od `scan_ports` i renderer `button_choice` od konkretnej operacji.

Zbudować cztery uniwersalne tryby prezentacji. `terminal`, `button_choice` i
`window` obsługują wykonawczy OFS. `ofs_provisional` obsługuje wyłącznie czas od
lokalnego launch intentu do autorytatywnej hydration.

Od tego momentu engine nie może wiedzieć, czy obsługuje port scanner, exploit, kamerę czy samochód.

## Tryb `ofs_provisional`

`ofs_provisional` jest adapterem Application Presentation Lifecycle, a nie
sesją wykonawczą `/gonna-win`. Korzysta z provisional registry z 6.3.1–6.3.3 i
posiada własny renderer scen przed wykonaniem.

Renderer odpowiada za:

* sceny `app_identity`, `local_init`, `module_boot`, `context_bind`,
  `author_manifest`, `runtime_prepare`, `launcher_sync`, `hydration_wait`;
* jeden viewport wewnątrz istniejącego provisional window;
* przejścia `replace`, `clear`, `fade` i `append_short`;
* natychmiastowy stop przy hydration, failure lub dispose;
* zachowanie tego samego DOM podczas handoffu do właściwego interface;
* reduced motion i neutralny extended wait.

Nie odpowiada za security interactions, choices, wynik, transport ani request
gameplayowy. Nie może używać completion/failure bez prawdziwego sygnału.

Kontrakt rendererów zostaje rozdzielony:

```text
ofs_provisional → launch/boot/hydration wait
terminal        → executing
button_choice   → executing + presentation choices
window          → executing/panel state
```

## Renderer `button_choice`

Istniejący MVP zostaje oczyszczony z logiki `scan_ports`.

Renderer odpowiada wyłącznie za:

* linie kontekstu,
* prompt,
* przyciski,
* countdown,
* blokadę po payloadzie,
* clear/replace.

Nie wybiera security ani tekstów.

## Renderer `terminal`

Powstaje uniwersalny terminal OFS.

Zasady:

* 3–6 widocznych linii,
* brak nieskończonego scrolla,
* sceny zastępują się lub częściowo czyszczą,
* brak narracyjnych wyborów,
* obsługa `replace`, `clear`, `fade`, `append_short`.

Renderer nie posiada własnych logów operacyjnych.

Wszystko pochodzi ze słownika/contentu.

## Renderer `window`

Powstaje renderer bardziej panelowy.

Powinien obsługiwać stabilne elementy typu:

```text
title
stage
channel
source
activity
status
```

Nie musi mieć dokładnie takich pól w każdej aplikacji.

Ma posiadać uniwersalny mechanizm slotów.

Nie tworzy fikcyjnego progressu.

## `progressbar_random`

Legacy `progressbar_random` zostaje przygotowany do mapowania na `window`.

Jeżeli brak prawdziwego procentu backendowego:

```text
0–100%
```

nie jest pokazywane.

Zamiast tego pokazywany jest etap/aktywność.

## Reduced motion

Wszystkie cztery renderery respektują:

```text
prefers-reduced-motion
```

Wtedy:

* brak agresywnych fade,
* brak pulsowania,
* brak szybkich animacji,
* informacje pozostają czytelne.

## Wynik sprintu

Po `130.8.6.4` scene envelope może zostać skierowany do właściwego z czterech
rendererów bez wiedzy o strukturze konkretnej aplikacji. Scheduler provisional
i scheduler wykonawczy pozostają oddzielne i nigdy nie piszą jednocześnie do
jednego viewportu.

`scan_ports` pozostaje działającą regresją.

## Realizacja

* renderer nie wybiera scen ani security; otrzymuje wyłącznie walidowany,
  zamrożony envelope;
* `terminal` utrzymuje krótki bufor bez nieskończonego scrolla;
* `button_choice` jako jedyny posiada prompt, przyciski i countdown;
* `window` posiada neutralne sloty `key -> value` i nie generuje procentu;
* `progressbar_random` ma jawne mapowanie kompatybilności do `window`;
* każdy viewport posiada jednego właściciela, zwalnianego przez `dispose`;
* wszystkie tryby obsługują `replace`, `clear`, `fade`, `append_short` oraz
  `prefers-reduced-motion`;
* błąd fabryki/renderera pozostawia istniejący legacy pending UI.

Sprint 6.4 nie przełącza jeszcze profili innych operacji. Dobór rendererów
dla 12 `action_key` należy do 6.5.

---

# Sprint 130.8.6.5 — Generalizacja na 12 action_key + profile skeleton

## Status

Zakończony. Wszystkie 12 `action_key` posiada walidowany profil wykonawczy,
macierz security, mapowanie renderera i oddzielny skeleton provisional
`launch_150s`. Pełny content osi 150 sekund pozostaje zakresem 6.6.

## Cel

Rozszerzyć engine z jednego `scan_ports` na pełny katalog 12 operacji, ale bez ręcznego produkowania kompletnej biblioteki treści.

Powstaje **struktura profili**, a nie pełny content.

## Obsługiwane action keys

```text
scan_ports
exploit
sniff
trace
trace_gps
trace_device
mic_sniff
atm_logs
install_sniffer
camera_stream
camera_shutdown
car_hack
```

Każdy `action_key` musi:

* posiadać profil,
* posiadać presentation mode,
* posiadać macierz `security -> interactions`,
* posiadać podstawowe scene pools,
* posiadać completion/failure,
* przejść walidację.

## Profile mogą być ubogie

Na tym etapie pozostałe 11 operacji mogą mieć minimalną liczbę wariantów.

Np.:

* 1–2 boot,
* 1–2 operation,
* kilka security lines,
* jeden fallback,
* completion/failure.

Nie produkujemy jeszcze finalnych 5–10 wariantów na każdą kategorię.

To będzie osobna praca nad słownikiem.

## Presentation mapping

Docelowe MVP:

```text
scan_ports         -> button_choice
exploit            -> terminal
sniff              -> terminal
trace              -> window
trace_gps          -> window
trace_device       -> window
mic_sniff          -> terminal
atm_logs           -> terminal
install_sniffer    -> button_choice
camera_stream      -> window
camera_shutdown    -> button_choice
car_hack           -> button_choice
```

Każdy profil operacji otrzymuje dodatkowo `provisional_profile`, niezależny od
wykonawczego `presentation_mode`. Pozwala to uruchomić `ofs_provisional` przed
hydration niezależnie od tego, czy właściwa aplikacja później przejdzie do
terminala, panelu czy wyborów.

Minimalny skeleton:

```text
action_key
  provisional_profile
    scene_pool
    interface_voice
    target_context
    author_content_policy
    timeline_profile: launch_150s
  execution_profile
    presentation_mode
    security -> interactions
```

`provisional_profile` nie zawiera security matrix, completion ani gameplayowych
choice. Walidator musi odrzucić takie pola w tej gałęzi.

## Pokrycie czasu provisional

Każdy z 12 profili wskazuje sekwencję zdolną utrzymać sensowną prezentację przez
minimum 150 sekund bez sztucznego progressu. W 6.5 wystarcza skeleton i fallback
rodzin scen; konkretne warianty tekstowe zostaną domknięte w 6.6.

Wymagane przedziały:

```text
0–15 s    identity + local init
15–45 s   interface/module boot + context bind
45–90 s   author manifest + local validation
90–120 s  runtime prepare + launcher sync
120–150 s hydration wait o zwalniającym rytmie
>150 s    extended wait bez limitu czasu i bez fikcyjnego błędu
```

## Security matrix

Każda operacja dostaje jawny skeleton właściwych połączeń.

Nie wolno na tym etapie wracać do globalnych luźnych list.

Przykład:

```text
exploit:
    kernel_guard:
        probe
        bypass
        verify

    memory_guard:
        probe
        inject
        verify
```

Dokładne treści mogą być jeszcze fallbackowe.

## Validator

Walidator powinien teraz sprawdzać wszystkie 12 profili.

Minimum:

* istniejący renderer,
* istniejąca scena,
* istniejące security,
* istniejąca interaction,
* poprawna para security/interactions,
* poprawne choice,
* poprawny `presentation_state_schema`,
* brak HTML,
* poprawny timing.

Uszkodzenie jednego profilu nie może wyłączyć całego OFS.

Wyłączana/fallbackowana jest konkretna operacja.

## Feature flags

System powinien umożliwiać osobne włączanie profili.

Nie muszą powstać ręcznie nazwane flagi dla wszystkich 12, jeżeli obecna infrastruktura pozwala przekazać mapę enabled operations.

Ważne jest zachowanie:

```text
global OFS
+
operation-specific enable
```

## Wynik sprintu

Po `130.8.6.5` wszystkie 12 akcji można technicznie przepuścić przez jeden engine.

Nie wszystkie muszą jeszcze wyglądać pięknie.

Mają działać poprawnie semantycznie i infrastrukturalnie.

Każda z nich posiada również walidowany skeleton `ofs_provisional`, więc długi
launch nie wraca do jednego migającego komunikatu.

## Realizacja

* `operation_feedback.v1.json` zawiera 12 profili oraz wspólny timeline
  `launch_150s` od `app_identity` do `extended_wait`;
* każda operacja posiada `duration_scene_pools`, jawną macierz
  `security -> interactions`, completion/failure i deklarację renderera;
* `provisional_profile` nie może zawierać security, choice ani wyniku;
* validator sprawdza wszystkie profile i zastępuje wyłącznie uszkodzony
  profil wpisem `enabled=false + validation_error`;
* błąd profilu podczas sesji zwalnia renderer i uruchamia legacy fallback;
* wybór renderera wynika z `action_key`, a nie z przypadkowego interface
  aplikacji; `scan_ports` pozostaje na `button_choice`;
* flaga globalna jest uzupełniona listą
  `CHAOS_OPERATION_FEEDBACK_ACTIONS`, a stara flaga
  `CHAOS_OPERATION_FEEDBACK_SCAN_PORTS` pozostaje kompatybilna;
* generyczne sceny 6.5 są celowo ubogie. Produkcyjna różnorodność treści
  i pełne pre-execution 150 s należą do 6.6.

---

# Sprint 130.8.6.6 — Full MVP Cutover Architecture + Content Contract

**Status: zakończony lokalnie 2026-08-09; oczekuje na test produkcyjny i stopniowy cutover flagami.**

## Cel

Domknąć OFS jako gotową platformę pod dalsze ręczne wypełnianie słownika.

Nie rozbudowujemy już mechaniki engine'u.

Porządkujemy integrację, fallbacki, content autora, telemetry, testy i strukturę danych tak, żeby kolejny sprint mógł być praktycznie „content sprintem”.

## Pakiet `ofs_provisional.launch_150s`

Domknąć pierwszy produkcyjny pakiet konkretnych scen pre-execution. Pakiet ma
pokrywać co najmniej 150 sekund, ale nie zakłada, że hydration nastąpi dopiero na
końcu. Każda scena jest przerywalna, a payload zawsze wygrywa.

Minimalna oś scen:

| Czas orientacyjny | Rodzina | Przykładowa treść |
|---:|---|---|
| 0 s | `app_identity` | `{app_title}` / `Profil autora: {description}` |
| 3 s | `local_init` | `Inicjalizacja lokalnego profilu.` |
| 8 s | `interface_boot` | `Przygotowanie widoku {interface}.` |
| 14 s | `author_manifest` | `Odczyt manifestu aplikacji.` |
| 21 s | `context_bind` | `Cel: {target_label}` |
| 29 s | `context_bind` | `Profil działania: {action_label}` |
| 38 s | `module_boot` | `Przygotowanie lokalnych modułów narzędzia.` |
| 48 s | `local_validation` | `Walidacja lokalnej konfiguracji.` |
| 60 s | `runtime_prepare` | `Budowanie widoku sesji.` |
| 73 s | `author_content` | `Ładowanie bezpiecznego contentu autora.` |
| 88 s | `local_validation` | `Sprawdzanie spójności lokalnego profilu.` |
| 104 s | `runtime_prepare` | `Lokalny kontekst aplikacji jest gotowy.` |
| 121 s | `launcher_sync` | `Oczekiwanie na stan launchera.` |
| 138 s | `hydration_wait` | `Utrzymanie kontekstu aplikacji.` |
| 150 s | `extended_wait` | `Autorytatywny stan uruchomienia pozostaje oczekiwany.` |

Po 150 sekundach renderer rotuje neutralne warianty `extended_wait` co 12–20
sekund. Nie zwiększa częstotliwości i nie powtarza tej samej linii bezpośrednio.

Pakiet musi zawierać warianty głosu dla:

* `terminal` — sesja, manifest, lokalny profil poleceń;
* `button_choices` — przygotowanie interfejsu decyzji bez pokazywania options;
* `window` — przygotowanie panelu i slotów;
* legacy `progressbar_random` — etapy/aktywność bez wartości procentowej.

Placeholdery są ograniczone do danych discovery: `app_title`, `description`,
`interface`, `target_label`, `action_label`. Brak wartości usuwa linię lub używa
neutralnego fallbacku; nie wolno renderować `undefined` ani pustego celu.

Validator sprawdza:

* pokrycie timeline do co najmniej 150 sekund;
* monotoniczny `start_after_ms`;
* dozwolone rodziny i placeholdery;
* brak completion/security/transport fiction;
* co najmniej trzy neutralne warianty extended wait;
* timing extended wait 12–20 sekund;
* natychmiastową cancelowalność każdej sceny.

## Priorytet contentu

Silnik musi obsługiwać kolejność:

```text
app_structured
-> app_legacy
-> global_fallback
```

### `app_structured`

Jeżeli aplikacja posiada przyszły:

```text
feedback_content
```

korzystamy z niego.

### `app_legacy`

Jeżeli nie:

bezpiecznie projektujemy istniejące:

```text
title
text
description
command
logs
list
steps
```

### `global_fallback`

Jeżeli content aplikacji jest pusty albo niepoprawny:

korzystamy z OFS global library.

## Ważna granica gameplayowa

Istniejące:

```text
buttons
options
```

należące do aplikacji nie mogą automatycznie zostać potraktowane jako wybory OFS.

Narracyjne wybory pochodzą wyłącznie z:

```text
choice_library
```

i mają prefix:

```text
feedback.
```

## Transport events

Domknąć rozdzielenie narracji i prawdziwego transportu.

Losowane:

```text
probe
verification
bypass attempt
channel selection
correlation
```

Wyłącznie prawdziwe:

```text
network_error
offline
http_error
invalid_payload
aborted
retry
response_delayed
```

W szczególności nie wolno generować dla klimatu:

```text
connection lost
packet loss
worker restart
reconnect
retry
```

jeżeli runtime tego nie potwierdził.

## Completion / failure

Completion pojawia się dopiero po prawdziwym payloadzie.

Failure rozróżnia:

```text
gameplay failure
HTTP failure
network failure
invalid response
abort
```

OFS nie interpretuje domenowych statusów typu:

```text
duplicate
superseded_by_capture
invalid_target
target_state_changed
```

Pozostają w istniejącym runtime.

## Telemetria

Wpiąć minimalny zestaw do `APP_FLOW`:

```text
feedback_session_started
feedback_profile_loaded
feedback_scene_started
feedback_choice_shown
feedback_choice_selected
feedback_choice_timed_out
feedback_extended_wait_entered
feedback_payload_received
feedback_failed
feedback_cancelled
feedback_disposed
```

Bez payloadu, współrzędnych i security celu.

Przydatne szczególnie:

```text
action_key
presentation_mode
scene_id
content_source
elapsed_ms
completion_reason
```

## Cleanup

Po każdym zakończeniu musi być gwarancja:

* brak timerów,
* brak intervali,
* brak aktywnych button handlerów OFS,
* brak callbacków modyfikujących usunięty DOM,
* brak pozostawionego presentation state.

## Legacy coexistence

Nie usuwamy jeszcze:

```text
APP_WAIT_LOG_MESSAGES
startAppWaitLog()
legacy spinnerów
progressbar_random
```

jeżeli są potrzebne jako fallback.

OFS przejmuje tylko operacje, dla których profil jest aktywny i poprawny.

Legacy wygaszamy dopiero po osobnym pełnym cutoverze.

## Test końcowy MVP

Przetestować przynajmniej:

* wszystkie 12 `action_key`,
* wszystkie trzy presentation modes,
* `ofs_provisional` dla wszystkich 12 action keys,
* szybki payload <300 ms,
* 5 s,
* 30 s,
* 90 s,
* 180 s,
* hydration na granicach 1 s, 14 s, 60 s, 149 s i po 150 s,
* payload podczas choice,
* zamknięcie okna,
* kilka równoległych aplikacji,
* HTTP error,
* non-JSON response,
* network reject,
* invalid profile,
* invalid app content,
* reduced motion,
* mobile.

Najważniejsza regresja:

> wynik `/gonna-win` z OFS i bez OFS musi być identyczny.

## Wynik sprintu

Po `130.8.6.6` mamy:

* jeden wspólny engine,
* dwa rozdzielone schedulery: provisional i execution,
* cztery renderery, w tym oddzielny `ofs_provisional`,
* 12 profili operacji,
* validator,
* cancellation lifecycle,
* presentation state,
* content projection,
* telemetry,
* fallback,
* feature flags,
* działający `scan_ports` z pełniejszym MVP contentem,
* minimalne profile pozostałych operacji,
* pakiet konkretnych scen provisional na minimum 150 sekund oraz extended wait.

OFS jest wtedy gotowy infrastrukturalnie.

---

# Następny osobny sprint — OFS Execution Content Population

Nie należy mieszać go z `130.8.6.1–130.8.6.6`.

Jego zadaniem będzie ręczne uzupełnienie treści wykonawczej. Produkcyjny pakiet
`ofs_provisional.launch_150s` powstaje wcześniej w 6.6 i nie jest odkładany do
tego sprintu.

```text
operation_feedback.v1.json
```

według gotowej struktury.

Czyli:

* więcej wariantów security interactions,
* więcej scen,
* więcej przejść,
* więcej pytań,
* różne tone/style,
* warianty zależne od presentation state,
* autorski feedback content aplikacji,
* anti-repeat content,
* dopracowanie polskich/angielskich komunikatów,
* ręczna kontrola semantyczna.

Dzięki temu w sprintach `130.8.6.x` nie mieszamy dwóch różnych problemów:

**budowy maszyny**

oraz

**pisania paliwa dla tej maszyny**.

Najpierw udowadniamy, że mechanizm poprawnie składa treść.

Dopiero później produkujemy dużą bibliotekę treści.

---

# Logika całego 130.8.6 w jednym ciągu

```text
130.8.6.1
Session + lifecycle + /gonna-win + cancellation

        ↓

130.8.6.2
JSON + scenes + security matrix + scheduler

        ↓

130.8.6.3
choices + app content + provisional lifecycle/hydration + bazowe pre-execution

        ↓

130.8.6.4
4 renderery, w tym oddzielny ofs_provisional

        ↓

130.8.6.5
12 action_key + execution/provisional profile skeletons + validator

        ↓

130.8.6.6
launch_150s + content contract + telemetry + fallback + pełny MVP
```

Po tym:

```text
ENGINE GOTOWY
↓
OSOBNY SPRINT
↓
RĘCZNE WYPEŁNIENIE SŁOWNIKA
↓
TESTY NARRACJI
↓
CUTOVER KOLEJNYCH OPERACJI
```

---

# OFS Presentation Lift Challenger — 130.8.6.7–130.8.6.11

Pełny kontrakt czterech sprintów znajduje się w
`doc/ofs_presentation_lift_challenger.md`.

```text
130.8.6.7  lifecycle faz, timing i bezpieczny hydration handoff
130.8.6.8  adaptacyjne paczki ofs_provisional dla czterech interface voices
130.8.6.9  unikatowe template'y button_choice/random_progress/terminal/window
130.8.6.10 język efektów mapy, eskalacja czasu i production hardening
130.8.6.11 generator czołówki oraz trwałego brandingu header/footer z ikony i nazwy aplikacji
```

Blok nie zmienia gameplayu ani kontraktów aplikacji. Obowiązuje kolejność:
provisional, hydration, content autora, execution OFS, autorytatywne completion.
Wszystkie fazy używają jednego shellu właściwego dla typu aplikacji. Execution
ma timing minimum `×3`, a aktywny choice zamraża content i utrzymuje przyciski
w stałym action docku do kliknięcia albo timeoutu.

---

# Sprint 130.8.7 — Cyberner Channel Delivery Isolation & Recovery

Sprint naprawczy po audycie niedochodzących wiadomości na kanale `WORLD` i
pozostałych kanałach grupowych.

## Problem

Obecny Cyberner prezentuje trzy niezależne kanały:

* `WORLD`,
* `KLAN`,
* `ZNAJOMI`.

Pod spodem nie są one jednak wystarczająco odseparowane. `WORLD` korzysta z
legacy `scope = group`, ale wiadomości są kopiowane wyłącznie do kontaktów
nadawcy. Kanał opisany jako publiczny nie obejmuje więc całej gry. Kanały
grupowe korzystają również z zapisu wielu kopii wiadomości, ciężkich zapisów
pełnych profili oraz wspólnej ścieżki powiadomień. Awaria jednego odbiorcy może
pozostawić zapis wiadomości bez delty, zwrócić błąd nadawcy albo zatrzymać
powiadamianie kolejnych odbiorców.

Frontend odbiera delty wątków, ale otwarty kanał nie renderuje od razu nowej
wiadomości. Czeka na okresowy bootstrap i kolejny request historii. Daje to
wrażenie, że wiadomość nie dotarła, mimo że została już zapisana.

## Cel

Rozdzielić kanały według ich prawdziwego zasięgu i źródła prawdy:

```text
WORLD
→ jeden globalny strumień całej gry
→ osobna tabela

KLAN
→ jeden strumień dla całego klanu
→ osobna tabela

ZNAJOMI
→ lokalny kanał profilu gracza
→ odbiorcy wyznaczani z zaakceptowanych relacji
→ istniejący per-user inbox/fan-out

DIRECT
→ istniejący prywatny thread
→ bez zmian kontraktu
```

Kanały muszą działać niezależnie. Błąd, przeciążenie albo brak uprawnień w
jednym kanale nie może blokować wysłania, odczytu ani odświeżenia innego.


# Podział implementacyjny:
  * 130.8.7.1 — tabele, store’y, indeksy i migracja.
  * 130.8.7.2 — routing oraz atomowe wysyłanie.
  * 130.8.7.3 — live delty i frontend recovery.
  * 130.8.7.4 — cutover, testy produkcyjne i rollback.


## 1. Twardy kontrakt kanałów

### WORLD

`WORLD` jest publicznym kanałem całej gry.

Każdy istniejący, aktywny profil może:

* odczytać wspólną historię,
* wysłać wiadomość,
* otrzymać deltę nowej wiadomości,
* utrzymywać własny stan przeczytania.

Lista kontaktów, klan i status przyjaźni nie mogą wpływać na widoczność
wiadomości `WORLD`.

Wiadomość jest zapisywana jeden raz. Nie wolno tworzyć jednej kopii na profil.

### KLAN

`KLAN` jest wspólnym kanałem wszystkich aktualnych członków jednego klanu.

Uprawnienie do zapisu i odczytu wynika z aktualnego `clan_id` albo stabilnego
klucza klanu profilu. Nick, nazwa prezentacyjna i lista kontaktów nie mogą być
kluczem autoryzacji.

Wiadomość jest zapisywana jeden raz dla klanu. Zmiana klanu natychmiast zmienia
dostęp do kanału:

* po odejściu gracz nie odczytuje dalszych wiadomości starego klanu,
* po dołączeniu odczytuje kanał nowego klanu zgodnie z ustaloną polityką
  historii,
* gracz bez klanu nie może wysyłać ani pobierać kanału `KLAN`.

### ZNAJOMI

`ZNAJOMI` pozostają kanałem lokalnym względem nadawcy.

Odbiorcy są snapshotem zaakceptowanych, wzajemnych relacji w chwili wysłania.
Kanał nie jest globalnym pokojem posiadającym jedną stałą listę członków.

Wiadomość może nadal korzystać z per-user fan-out w istniejącym
`chat_messages`, ale:

* trafia tylko do zaakceptowanych znajomych,
* nie trafia do kontaktów jednostronnych ani pending,
* nie zależy od tabel `WORLD` i `KLAN`,
* awaria powiadomienia jednego znajomego nie cofa zapisu dla pozostałych.

### DIRECT

Prywatne rozmowy zachowują:

```text
scope = direct
peer_name = username
```

Sprint nie przebudowuje poprawnie działających rozmów prywatnych ani contact
flow.

## 2. Model danych

### cyberner_world_messages

Minimalny kontrakt:

```text
id                  INTEGER PRIMARY KEY
message_id          TEXT UNIQUE NOT NULL
sender_username     TEXT NOT NULL
subject             TEXT NOT NULL DEFAULT ''
body                TEXT NOT NULL
created_at          TEXT NOT NULL
client_message_id   TEXT
```

`client_message_id` albo równoważny klucz idempotencji zabezpiecza ponowienie
requestu po timeout lub zerwanym połączeniu.

### cyberner_clan_messages

Minimalny kontrakt:

```text
id                  INTEGER PRIMARY KEY
message_id          TEXT UNIQUE NOT NULL
clan_key            TEXT NOT NULL
sender_username     TEXT NOT NULL
subject             TEXT NOT NULL DEFAULT ''
body                TEXT NOT NULL
created_at          TEXT NOT NULL
client_message_id   TEXT
```

Wymagany indeks:

```text
(clan_key, id)
```

Idempotencja musi być ograniczona co najmniej do nadawcy i kanału, aby dwa
klany nie kolidowały tym samym kluczem klienta.

### cyberner_channel_cursors

Wspólne wiadomości nie mogą używać `read_at` na rekordzie wiadomości, ponieważ
każdy gracz czyta je niezależnie.

Minimalny kontrakt kursora:

```text
username            TEXT NOT NULL
channel_type        TEXT NOT NULL
channel_key         TEXT NOT NULL
last_read_message_id INTEGER NOT NULL DEFAULT 0
updated_at          TEXT NOT NULL
PRIMARY KEY (username, channel_type, channel_key)
```

Przykłady:

```text
main | world | global       | 481
neo1 | clan  | Echo Wolnosci | 92
```

`ZNAJOMI` i `DIRECT` pozostają na lokalnym `read_at` w `chat_messages`.

## 3. Store'y

Dodać jawne, małe store'y:

```text
CybernerWorldStore
CybernerClanStore
CybernerChannelCursorStore
```

Nie tworzyć jednego store'a z rozgałęzieniem wszystkich zasad w środku.

Każdy store odpowiada tylko za:

* idempotentny zapis,
* stronicowany odczyt,
* kursor `after_id` / `before_id`,
* limit historii,
* stabilny `message_id`.

Store nie zapisuje profilu, nie buduje kontaktów i nie publikuje toastów.

## 4. Routing backendu

Endpoint może pozostać wspólny:

```text
GET  /api/chats/messages
POST /api/chats/messages
```

ale router musi jawnie delegować:

```text
scope=world lub legacy group/global
→ CybernerWorldStore

scope=clan / channel=clan
→ CybernerClanStore

scope=channel / peer=friends
→ lokalny fan-out ZNAJOMI

scope=direct
→ istniejący MailStore
```

Legacy `scope=group, peer=global` może być przyjmowane na wejściu, ale po
normalizacji nie może uruchamiać logiki kontaktów.

Backend ma zwracać kanoniczny kontrakt:

```json
{
  "source": "world",
  "channel": "world",
  "scope": "world",
  "peer": "global"
}
```

Frontend nie powinien zgadywać rodzaju kanału z tytułu.

## 5. Atomowość wysłania

Request wysłania ma trzy fazy:

```text
1. autoryzacja i normalizacja kanału
2. atomowy, idempotentny zapis wiadomości
3. best-effort publikacja delt i powiadomień po commit
```

Sukces gameplayowy oznacza commit wiadomości, nie sukces każdego toasta.

Po commicie awaria delty albo powiadomienia:

* nie zmienia odpowiedzi na fałszywy błąd wysłania,
* nie powoduje ponownego zapisu wiadomości,
* jest logowana z `message_id`, kanałem i odbiorcą,
* zostaje naprawiona przez polling/recovery.

Nie wolno zapisywać `system_messages` przez odczyt i zapis pełnego profilu dla
każdego odbiorcy. Powiadomienia korzystają z istniejącego lekkiego
`SystemMessageStore` albo są generowane z delty kanału.

## 6. Delty

Każdy zapis publikuje stabilne zdarzenie:

```text
cyberner.message_created
```

Minimalny payload:

```json
{
  "message_id": "...",
  "channel": "world|clan|friends|direct",
  "channel_key": "global|clan:<id>|friends:<sender>|direct:<peer>",
  "sender": "...",
  "subject": "...",
  "body": "...",
  "created_at": "..."
}
```

Zasady audience:

* `WORLD` — wszyscy gracze; dopuszczalny jest globalny cursor/feed bez
  materializowania eventu osobno dla każdego profilu,
* `KLAN` — aktualni członkowie wskazanego klanu,
* `ZNAJOMI` — snapshot zaakceptowanych odbiorców z chwili wysłania,
* `DIRECT` — nadawca i odbiorca.

Delta zawiera pełną wiadomość potrzebną rendererowi. Nie może być wyłącznie
sygnałem zmiany podglądu wątku.

## 7. Frontend i natychmiastowe dostarczenie

Po odebraniu `cyberner.message_created` frontend:

1. sprawdza stabilny `message_id`,
2. deduplikuje wiadomość,
3. aktualizuje preview i unread,
4. jeżeli właściwy kanał jest otwarty — od razu dokłada wiadomość do DOM,
5. zachowuje pozycję scrolla,
6. aktualizuje kursor przeczytania, jeżeli użytkownik faktycznie widzi thread.

Okresowy polling pozostaje recovery, a nie główną drogą dostarczenia.

Refresh Cybernera musi mieć:

* jeden request `inFlight` na typ snapshotu,
* ochronę przed odpowiedzią starszą od już zastosowanej wersji,
* `AbortController` przy zamknięciu okna,
* `try/catch/finally`,
* brak nakładających się interwałów,
* osobny błąd per kanał bez czyszczenia pozostałych danych.

## 8. Bootstrap

`/api/mail/bootstrap` nie pobiera pełnej historii każdego kanału.

Zwraca:

* definicje dostępnych kanałów,
* ostatni preview każdego kanału,
* unread per kanał,
* stabilne wersje/cursory,
* kontakty i pending threads dla lokalnej części społecznej.

Historia jest pobierana dopiero po otwarciu kanału.

Awaria odczytu `WORLD` nie usuwa `KLAN`, `ZNAJOMI` ani `DIRECT` z UI. Każdy
kanał ma własny stan:

```text
ready | loading | stale | recovery | unavailable
```

## 9. Unread

### WORLD i KLAN

Unread wynika z różnicy pomiędzy:

```text
latest_message_id
last_read_message_id użytkownika
```

Nie wykonujemy pełnego `COUNT(*)` przy każdym dziesięciosekundowym bootstrapie,
jeżeli wystarczy licznik lub zakres identyfikatorów.

### ZNAJOMI i DIRECT

Pozostaje lokalne `read_at`, ale zapytania muszą posiadać indeksy zgodne z:

```text
(owner_username, scope, peer_name, id)
(owner_username, scope, peer_name, read_at)
```

## 10. Migracja

Migracja jest addytywna i odwracalna.

1. Utworzyć nowe tabele i indeksy.
2. Zachować odczyt legacy `group/global` jako recovery.
3. Jednorazowo skopiować unikalną historię `WORLD` z per-user
   `chat_messages` do `cyberner_world_messages`.
4. Deduplikować legacy kopie po stabilnym zestawie pól albo wygenerowanym
   kluczu migracji.
5. Nie usuwać starych rekordów w tym sprincie.
6. Włączyć nowy zapis za flagą.
7. Po walidacji przełączyć odczyt.

Flagi:

```text
CHAOS_CYBERNER_CHANNEL_STORE_ENABLED
CHAOS_CYBERNER_WORLD_STORE_ENABLED
CHAOS_CYBERNER_CLAN_STORE_ENABLED
CHAOS_CYBERNER_LIVE_DELIVERY_ENABLED
```

`ZNAJOMI` nie wymagają flagi nowej tabeli, ponieważ pozostają lokalną ścieżką.

## 11. Obserwowalność

Log wysłania:

```text
[CYBERNER_SEND]
message_id=
channel=
channel_key=
sender=
recipient_count=
stored=true|false
duplicate=true|false
delta_published=
elapsed_ms=
```

Log recovery:

```text
[CYBERNER_RECOVERY]
channel=
after_id=
fetched=
deduplicated=
cursor_updated=
elapsed_ms=
```

Metryki:

* czas request → commit,
* commit → delta,
* delta → render,
* liczba duplikatów idempotency,
* liczba recovery fetch,
* liczba błędów per kanał,
* liczba aktywnych klientów Cybernera.

## 12. Testy

### Macierz odbiorców

* `WORLD` dociera do gracza bez kontaktu z nadawcą.
* `WORLD` dociera do gracza z innego klanu.
* `WORLD` nie tworzy kopii per profil.
* `KLAN` dociera do wszystkich członków tego samego klanu.
* `KLAN` nie dociera do obcego klanu ani gracza bez klanu.
* `ZNAJOMI` docierają wyłącznie do relacji wzajemnie zaakceptowanych.
* `ZNAJOMI` nie docierają do pending ani kontaktu jednostronnego.
* `DIRECT` zachowuje dotychczasowe działanie.

### Niezależność

* awaria store'a `WORLD` nie blokuje `KLAN`, `ZNAJOMI` ani `DIRECT`,
* awaria store'a `KLAN` nie blokuje `WORLD`,
* błąd powiadomienia odbiorcy nie zmienia zapisanego wyniku,
* błąd jednej delty nie przerywa publikacji pozostałych,
* bootstrap częściowy zachowuje działające kanały.

### Idempotencja i kolejność

* ponowienie tego samego `client_message_id` zapisuje jedną wiadomość,
* wiadomości mają stabilną kolejność po `id`,
* delta i recovery nie tworzą duplikatu w DOM,
* starszy snapshot nie nadpisuje nowszej delty,
* równoczesne wysłanie wielu graczy nie gubi wiadomości.

### Unread

* każdy gracz ma niezależny kursor `WORLD`,
* każdy członek klanu ma niezależny kursor `KLAN`,
* odczyt jednego kanału nie zeruje unread innego,
* otwarty i widoczny kanał aktualizuje kursor,
* kanał działający w tle zwiększa unread.

### Wydajność

* setki odbiorców `WORLD` nie powodują setek zapisów profilu,
* wysłanie `WORLD` wykonuje jeden zapis wiadomości,
* bootstrap nie skanuje całej tabeli wiadomości,
* polling nie nakłada requestów,
* test dużej historii potwierdza użycie indeksów.

## 13. Kolejność implementacji

### 130.8.7.1 — Stores and additive migration

* tabele `WORLD`, `KLAN` i cursorów,
* indeksy,
* modele wiadomości,
* idempotencja,
* narzędzie migracji legacy bez kasowania danych.

Stan implementacji 2026-08-10: zakończony lokalnie.

* `database.py` tworzy addytywnie tabele `cyberner_world_messages`,
  `cyberner_clan_messages` i `cyberner_channel_cursors` wraz z indeksami pod
  historię, unread oraz idempotencję `client_message_id`.
* `CybernerWorldStore` zapisuje jedną kopię wiadomości dla całej gry, a
  `CybernerClanStore` jedną kopię dla stabilnego klucza klanu. Oba store'y mają
  stabilną paginację po `id`, odczyt najnowszego okna i licznik wiadomości po
  cursorze.
* `CybernerChannelCursorStore` utrzymuje niezależny, monotoniczny cursor dla
  pary użytkownik–kanał. Cursor nie może cofnąć się przy spóźnionym zapisie.
* Migracja `005_cyberner_channel_stores.py` jest powtarzalna i nie kasuje
  legacy `chat_messages`. Rozpoznaje stare kopie fan-out kanału globalnego i
  zapisuje pojedynczy rekord kanoniczny; tryb dry-run nie zapisuje danych.
* Polityka startowego unread po migracji zostaje świadomie odłożona do cutover
  130.8.7.4. Migracja 7.1 nie przesuwa cursorów i nie oznacza historii jako
  przeczytanej.
* Endpointy Cybernera nadal korzystają z legacy routingu. Ich przełączenie nie
  należy do 7.1 i rozpocznie się dopiero w 130.8.7.2.
* Walidacja celowana: sześć testów store'ów, izolacji klanów, paginacji,
  idempotencji, cursorów i powtarzalnej migracji przechodzi lokalnie.

### 130.8.7.2 — Backend routing and atomic send

* jawny router kanałów,
* niezależna autoryzacja,
* zapis przed notyfikacją,
* brak pełnych zapisów profilu,
* recovery-compatible response.

Stan implementacji 2026-08-10: zakończony lokalnie, domyślnie za wyłączonymi
flagami shared store.

* Wspólne endpointy `GET/POST /api/chats/messages` normalizują wejście przez
  jawny router. `group/global` oraz `scope=world` prowadzą do `WORLD`, aktualny
  `clan:<klucz>` do store'u klanu, `channel/friends` pozostaje lokalnym
  fan-outem zaakceptowanych znajomych, a `direct` zachowuje `MailStore`.
* Autoryzacja `KLAN` porównuje żądany stabilny klucz z aktualnym klanem profilu.
  Gracz spoza klanu nie może odczytać ani zapisać jego kanału.
* Przy włączonych flagach `WORLD` i `KLAN` zapisują dokładnie jeden rekord.
  Opcjonalny `client_message_id` zapewnia idempotentny retry, a odpowiedź
  zwraca `message_id`, `idempotent_replay`, kanoniczny opis kanału i cursor
  recovery.
* Commit wiadomości następuje przed toastami i deltami kompatybilności. Awaria
  pojedynczego powiadomienia jest logowana z `message_id`, ale nie zmienia
  udanego requestu w fałszywy błąd ani nie ponawia zapisu.
* Powiadomienia Cybernera używają lekkiego `SystemMessageStore`; ścieżka nie
  zapisuje już pełnego `profile_json` każdego odbiorcy. Lista odbiorców WORLD
  pochodzi z tabeli użytkowników, a KLAN z bieżącego członkostwa.
* Odczyt wspólnego kanału przesuwa wyłącznie jego monotoniczny cursor danego
  użytkownika. Unread WORLD i KLAN jest liczony niezależnie; odczyt jednego nie
  zeruje drugiego ani lokalnych kanałów.
* Nowy routing jest chroniony przez `CHAOS_CYBERNER_CHANNEL_STORE_ENABLED` oraz
  flagi per kanał. Przy wyłączonym bezpieczniku endpoint zachowuje dotychczasową
  ścieżkę legacy, dzięki czemu wdrożenie kodu nie wykonuje automatycznego
  cutoveru danych.
* Live event `cyberner.message_created`, frontendowy `client_message_id` i
  dedupe DOM pozostają zakresem 130.8.7.3.

### 130.8.7.3 — Live deltas and frontend recovery

* `cyberner.message_created`,
* natychmiastowy render otwartego kanału,
* dedupe po `message_id`,
* `inFlight`, wersje i AbortController,
* polling jako recovery.

Stan implementacji 2026-08-10: zakończony lokalnie, nadal za wyłączoną flagą
`CHAOS_CYBERNER_LIVE_DELIVERY_ENABLED`.

* Po commicie backend publikuje `cyberner.message_created` z pełną kanoniczną
  wiadomością. Payload zawiera stabilne `message_id`, kanał, `channel_key`,
  nadawcę, temat, treść i czas, więc renderer nie musi dociągać danych przed
  pierwszym pokazaniem wiadomości.
* Audience WORLD obejmuje wszystkich użytkowników tylko przy aktywnym shared
  store. KLAN obejmuje wyłącznie bieżących członków tego klanu. Przy rollbacku
  do legacy WORLD zachowuje dawny zakres kontaktów i nie ujawnia wiadomości
  profilom, które nie otrzymały kopii legacy.
* Awaria publikacji delty po commicie jest logowana per odbiorca i nie zmienia
  sukcesu wysłania. Ponowienie requestu może bezpiecznie ponowić publikację,
  ponieważ dedupe delty zawiera odbiorcę i stabilne `message_id`.
* Frontend nadaje każdej próbie wysłania `client_message_id`. Ten sam klucz jest
  zachowany po niejednoznacznym błędzie transportowym i czyszczony dopiero po
  potwierdzonym sukcesie albo jednoznacznym błędzie 4xx.
* Otwarty kanał renderuje pełną deltę natychmiast, deduplikuje po `message_id`,
  zachowuje scroll i uruchamia cichy GET jako potwierdzenie cursora. Snapshot
  rozpoczęty przed nowszą deltą jest scalany, a nie może nadpisać wiadomości
  dostarczonej później.
* Bootstrap i historia mają osobne stany `inFlight`, wersje requestów oraz
  `AbortController`. Zmiana threadu abortuje starszy request historii, a
  zamknięcie okna abortuje oba typy requestów.
* Nakładający się `setInterval` został zastąpiony rekurencyjnym `setTimeout`:
  następny polling zaczyna się dopiero po zakończeniu poprzedniego. Polling i
  `/api/mail/bootstrap` pozostają ścieżką recovery, a nie live delivery.
* Globalny delta-feed przekazuje do klienta także wersję eventu. Chroni ona
  lokalny stan przed odpowiedzią snapshotu rozpoczętego przed deltą.

### 130.8.7.4 — Cutover and production audit

* porównanie legacy i nowych read modeli,
* migracja produkcyjna,
* flagowany cutover,
* test wielu równoczesnych graczy,
* obserwowalność i plan rollbacku,
* aktualizacja `doc/cyberner.md`, `doc/cyberner_channels_audit.md` oraz
  `doc/project_journal.md` zgodnie z faktycznie wdrożonym stanem.

Stan implementacji: **DONE / READY FOR CONTROLLED CUTOVER**.

* Migracja `006` przenosi deduplikowaną historię `KLAN`, a istniejącym graczom
  zakłada baseline cursorów `WORLD` i właściwego klanu. Dane legacy nie są
  usuwane.
* `scripts/audit_cyberner_cutover.py --strict` porównuje kanoniczną historię
  legacy ze shared stores i sprawdza pokrycie cursorów przed aktywacją flag.
* Bootstrap pobiera tylko preview `WORLD`. Błąd odczytu jednego shared kanału
  jest raportowany w `channel_states` i nie blokuje pozostałych kanałów.
* Test współbieżności potwierdza jeden zapis dla retry tego samego
  `client_message_id` oraz niezależne zapisy wielu graczy.
* Sekwencję wdrożenia, obserwowalność i ograniczenia rollbacku opisuje
  `doc/cyberner_cutover_runbook.md`. Sprint nie przełącza flag produkcyjnych.

## Poza zakresem

Sprint nie dodaje:

* szyfrowania rozmów,
* moderacji i banów kanału,
* edycji i usuwania wiadomości,
* reakcji, załączników i typing indicators,
* nowych kanałów frakcji, rynku albo operacji,
* narracyjnego outboxa,
* przebudowy rozmów prywatnych.

## DoD

Sprint jest zakończony, gdy:

1. `WORLD` jest jednym prawdziwie globalnym strumieniem całej gry.
2. `KLAN` jest jednym strumieniem całego właściwego klanu.
3. `ZNAJOMI` działają lokalnie i niezależnie według zaakceptowanych relacji.
4. Awaria jednego kanału nie blokuje pozostałych.
5. Wiadomość zapisana po stronie backendu nie kończy się fałszywym błędem z
   powodu późniejszej notyfikacji.
6. Otwarty Cyberner pokazuje nową wiadomość bez oczekiwania na pełny bootstrap.
7. Polling potrafi odzyskać pominiętą deltę bez duplikatu.
8. Unread jest niezależny per użytkownik i per kanał.
9. Produkcyjna migracja nie usuwa legacy historii i posiada rollback przez
   feature flags.
---


# Sprint 130.8.8 — Captured Object Menu & Security Read-Path Cutover

Sprint naprawczo-liftowy dla przejętych obiektów widocznych na mapie. Nie
zmienia zasad przejmowania, zabezpieczeń, konfliktów ani budowania terytorium.
Usuwa ciężką pracę z prawego kliknięcia, blokuje wielokrotne kopie panelu i
wprowadza jednoznaczne menu przejętego obiektu.

## Problem

Prawy klik na przejętym obiekcie wywołuje `POST /target-security-status`, a ten
uruchamia pełne `sync_session_profile()` z przebudową terytorium, normalizacją i
zapisem profilu. Read-only odczyt zabezpieczeń może przez to trwać ponad 250
sekund.

Frontend nie posiada blokady requestu ani singletonu panelu. Kolejne kliknięcie
w czasie oczekiwania wysyła następny request, a każda późniejsza odpowiedź
tworzy osobną kopię panelu.

Istniejące `/secure-action` i `/secure-preset` korzystają z podobnie ciężkiej
ścieżki profilu. Istnieje również kanoniczna akcja porzucenia w Territory
Control, ale obecnie wykonuje przebudowę geometrii i wykrywanie konfliktów
bezpośrednio w requeście.

## Cel

```text
prawy klik przejętego obiektu
→ natychmiastowe lokalne menu PO
→ ZABEZPIECZ | PORZUĆ

ZABEZPIECZ
→ lekki read-only odczyt TerritoryStore
→ jeden panel dla stabilnego target_id

PORZUĆ
→ potwierdzenie
→ atomowy zapis intencji/usunięcia
→ delta punktowa
→ dirty + kolejka workera
→ przebudowa terytorium i konfliktów poza requestem
```

## 1. Menu przejętego obiektu

Marker `hackedTargetMarker` nie otwiera od razu panelu zabezpieczeń. Pokazuje
małe menu kontekstowe:

```text
📦 <nazwa obiektu>
🛡 Zabezpiecz
× Porzuć
```

Menu powstaje lokalnie, bez oczekiwania na backend. Ma korzystać z istniejącego
mechanizmu zamykania menu mapy i nie tworzyć nowego systemu okien.

`Zabezpiecz` otwiera dotychczasową siatkę flag oraz presetów. `Porzuć` zawsze
wymaga osobnego potwierdzenia z nazwą obiektu i informacją, że operacja może
zmienić terytorium oraz aktywny konflikt.

## 2. Stabilna tożsamość i autoryzacja

Każda akcja używa w pierwszej kolejności stabilnego `target_id`. Współrzędne i
etykieta pozostają wyłącznie fallbackiem zgodności dla starych rekordów.

Backend przed odczytem albo zmianą potwierdza, że:

* użytkownik jest zalogowany,
* obiekt istnieje w `TerritoryStore`,
* obiekt należy aktualnie do użytkownika,
* przesłany `target_id` odpowiada rekordowi kanonicznemu.

Frontendowy marker ani wpis w `session["profile"]` nie są źródłem własności.

## 3. Lekki odczyt zabezpieczeń

Odczyt stanu zabezpieczeń jest czystym read-path:

* bez `sync_session_profile()` w trybie przebudowy,
* bez `rebuild_player_areas_with_territory_delta()`,
* bez `notify_encircled_area_owners()`,
* bez zapisu profilu,
* bez wykrywania konfliktów,
* bez budowania pełnego snapshotu mapy lub Territory Control.

Odpowiedź pochodzi bezpośrednio z kanonicznego rekordu przejętego celu i
zawiera minimalnie:

```json
{
  "success": true,
  "target_id": "...",
  "ownership_version": 4,
  "security": {},
  "security_version": 7
}
```

Jeżeli trzeba uzupełnić rekord legacy, migracja nie może odbywać się w
read-only requeście mapy.

## 4. Singleton panelu i deduplikacja requestów

Frontend utrzymuje rejestr paneli oraz requestów według `target_id`.

Zasady:

* jeden cel może mieć najwyżej jeden otwarty panel zabezpieczeń,
* ponowne kliknięcie aktywuje lub przenosi istniejący panel na wierzch,
* podczas requestu kolejne kliknięcie nie wysyła drugiego requestu,
* odpowiedź nie może utworzyć panelu, jeżeli request został anulowany albo cel
  utracił własność,
* zamknięcie panelu czyści kontroler i wpis rejestru,
* zmiana `map.target_captured`, `map.target_removed` lub właściciela unieważnia
  cache i nieaktualny panel.

Klucz deduplikacji nie może opierać się wyłącznie na `lat/lng`.

## 5. Lekki zapis flag i presetów

`/secure-action` i `/secure-preset` nie uruchamiają pełnej synchronizacji
profilu ani geometrii. Aktualizują zabezpieczenia kanonicznego przejętego celu
atomowo, z kontrolą:

```text
target_id
owner_username
expected security_version lub ownership_version
```

Po zapisie publikowana jest punktowa delta `map.target_updated`. Zmiana samych
flag bezpieczeństwa nie może automatycznie przebudowywać terytorium, jeśli nie
zmienia filaru ani własności.

Odpowiedź `409 stale_version` powoduje pojedynczy ponowny odczyt panelu, a nie
automatyczne powtarzanie mutacji.

## 6. Porzucenie obiektu

Istniejąca mechanika Territory Control pozostaje źródłem reguł, ale ścieżka
mapy nie może kopiować jej ciężkiego requestu.

Porzucenie:

1. wymaga `confirm: true`, stabilnego `target_id` i oczekiwanej wersji
   własności,
2. atomowo usuwa albo oznacza porzucenie kanonicznego celu,
3. czyści `aimed_target`, jeżeli wskazuje ten sam stabilny cel,
4. publikuje `map.target_removed`,
5. oznacza dotknięte terytorium i konflikty jako `dirty/changing`,
6. kolejkuje przebudowę workera,
7. zwraca szybkie potwierdzenie przyjęcia, bez czekania na nową geometrię.

Worker wykonuje:

* przebudowę obszaru właściciela,
* ponowne wykrycie i rekonstrukcję dotkniętych konfliktów,
* publikację nowych wersji geometrii i snapshotów,
* recovery, jeżeli zadanie zostało przerwane.

Akcja jest idempotentna. Ponowienie tego samego żądania nie usuwa innego celu i
nie tworzy kolejnego zadania workera.

## 7. Zachowanie w aktywnym konflikcie

Nie wprowadzamy ukrytej blokady porzucania filaru konfliktowego. Backend ma
jawnie zwrócić jedną z decyzji kontraktu:

```text
allowed
blocked_active_capture
blocked_stale_owner
blocked_conflict_transition
```

Na start rekomendowana jest ostrożna reguła: przejęty obiekt można porzucić,
jeżeli nie trwa na nim aktywne przejęcie CAS. Porzucenie strategiczne jest
dozwolone, ale zawsze przechodzi przez `dirty/changing` i worker, dzięki czemu
nie pozostawia starego frontu ani widma pola.

## 8. UX stanów

Menu i panel pokazują rozłączne stany:

```text
loading security
ready
saving
stale — refreshing
abandon confirmation
queued for territory rebuild
ownership lost
error + retry
```

Kliknięcia podczas `saving` i `abandon confirmation` są blokowane lokalnie.
Nie wolno otwierać drugiego panelu jako wizualnego fallbacku.

## 9. Obserwowalność

Dodać lekkie logi czasowe bez pełnych payloadów profilu:

```text
[CAPTURED_OBJECT_MENU] action=security_read target_id=... elapsed_ms=...
[CAPTURED_OBJECT_MENU] action=security_write target_id=... result=...
[CAPTURED_OBJECT_MENU] action=abandon target_id=... job_id=...
```

Frontend w trybie diagnostycznym raportuje `target_id`, stan singletonu,
`in_flight` i czas odpowiedzi. Nie loguje kompletnego zestawu zabezpieczeń ani
danych sesji.

## 10. Testy

Minimum:

* prawy klik pokazuje menu bez requestu,
* podwójny prawy klik nie tworzy dwóch requestów ani dwóch paneli,
* dwa różne cele mogą mieć niezależne stany, ale po jednym panelu na cel,
* security read nie wywołuje rebuildów, zapisów profilu ani detekcji konfliktu,
* zmiana flagi i presetu aktualizuje tylko właściwy `target_id`,
* stale version nie nadpisuje nowszego stanu,
* utrata własności zamyka/unieważnia panel,
* porzucenie wymaga potwierdzenia,
* porzucenie jest idempotentne i kolejkuje dokładnie jeden rebuild,
* delta usuwa marker bez pełnego reloadu mapy,
* worker publikuje końcową geometrię i konflikt bez widma,
* regresja Territory Control: zabezpieczanie i porzucanie nadal działają,
* endpointy mapy pozostają wolne od ciężkich rebuildów.

## 11. Walidacja produkcyjna

Sprawdzić osobno:

1. obiekt zwykły poza konfliktem,
2. inner aktywnego konfliktu,
3. przejęty filar konfliktu,
4. dwa szybkie kliknięcia tego samego markera,
5. równoległe otwarcie dwóch różnych przejętych obiektów,
6. zmianę własności przy otwartym panelu,
7. porzucenie zmieniające kształt klastra,
8. recovery po restarcie workera.

Oczekiwany budżet odczytu panelu w normalnych warunkach lokalnych:

```text
p50 < 100 ms
p95 < 500 ms
brak przebudowy terytorium w stacku requestu
```

## Poza zakresem

* nowe typy zabezpieczeń,
* zmiana kosztów i balansu presetów,
* zmiana zasad przejmowania obiektu,
* synchroniczna przebudowa geometrii z mapy,
* przebudowa całego Territory Control,
* globalny reload mapy po zapisie.

## DoD

Sprint jest zakończony, gdy prawy klik reaguje natychmiast, menu PO oferuje
`Zabezpiecz` i `Porzuć`, jeden cel nie może utworzyć więcej niż jednego panelu
ani requestu, odczyt i zapis zabezpieczeń nie uruchamiają ciężkiego runtime
profilu, a porzucenie kończy się spójną deltą i rekonstrukcją workera bez
blokowania requestu mapy.

---

# Sprint 130.8.9 — Target-Bound Application Receipt Cutover

Status lokalny: IMPLEMENTED / oczekuje na walidację produkcyjną dwóch kolejnych
celów tą samą aplikacją.

Sprint naprawczy dla hakowania celu ustawionego lekkim kliknięciem nazwy w menu
mapy, a następnie obsługiwanego aplikacjami uruchamianymi z pulpitu albo
terminala. Nie zmienia balansu zabezpieczeń, capture, konfliktów, geometrii ani
pracy territory workera.

## Problem

`POST /api/map/aim-target` zapisuje poprawny kanoniczny `aimed_target`, jednak
ręczne uruchomienie aplikacji bez wpisu z `launch_queue` może odziedziczyć
globalny `__lastHackFlowId`. Frontend tworzy wtedy zastępczy klucz:

```text
flowId:appId
```

i wysyła go do `/gonna-win` jako `launch_key`, który backend traktuje jak
`launch_receipt`. Receipt nie zawiera tożsamości celu ani odrębnej instancji
manualnego uruchomienia.

Backend przechowuje wynik receipt przez 900 sekund. Ponowne uruchomienie tej
samej aplikacji dla kolejnego celu może więc otrzymać replay payloadu
poprzedniego celu, zanim endpoint zsynchronizuje profil i wykona guard
`expected_target`.

Skutki:

* po kliknięciu opcji aplikacji belka wraca do poprzedniego celu,
* aplikacja pokazuje sukces, lecz kropka znika po odświeżeniu prawdy,
* ostatnia akcja nie domyka capture,
* komplet kropek i 100% mogą opisywać payload innego celu,
* uruchomienie narzędzia z mapy wychodzi z impasu, ponieważ `/hack-action`
  generuje świeży receipt z `client_action_key`.

## Cel

Każde wykonanie aplikacji mapowej ma posiadać niezmienny kontekst:

```text
application invocation
├── invocation_id
├── launch_receipt
├── app_id
├── action_key
├── target_identity
├── flow_id — diagnostyka i korelacja
└── source — map / desktop / terminal
```

Retry tego samego wykonania jest idempotentny. Nowe uruchomienie albo nowy cel
zawsze otrzymują nowy receipt.

## 1. Stabilna tożsamość celu w receipt

Do korelacji używać tej samej funkcji tożsamości, która chroni
`PlayerTargetRuntimeStore` i `/gonna-win`:

```text
target_id
lub kanoniczny fallback pozycji/trybu celu
```

Receipt manualnego uruchomienia musi być generowany z co najmniej:

```text
username
invocation_id
app_id
target_identity
```

`label`, skrócona nazwa na belce ani sam `flow_id` nie są tożsamością receipt.

## 2. Nowa instancja manualnego uruchomienia

Start aplikacji z pulpitu i terminala tworzy świeży `invocation_id` przed
otwarciem lub hydratacją okna. Jedna instancja zachowuje ten identyfikator przez:

* provisional,
* hydration,
* content autora,
* wybór opcji,
* OFS,
* retry tego samego requestu,
* scenę końcową.

Nie wolno generować nowego receipt osobno przy każdym renderze sceny lub
kliknięciu tego samego przycisku. Nie wolno też dziedziczyć receipt po zamkniętej
albo zakończonej aplikacji.

## 3. Oddzielenie flow od idempotencji

`flow_id` pozostaje identyfikatorem diagnostycznym `APP_FLOW`, ale nie może być
samodzielnym kluczem efektu gameplayowego.

```text
flow_id        = śledzenie całej podróży UI
invocation_id  = pojedyncze uruchomienie aplikacji
launch_receipt = idempotencja jednego efektu na jednym celu
```

`getCurrentAppFlowId()` może nadal korzystać z ostatniego flow do logów, lecz
manualny `launch_receipt` nie może powstawać jako `flowId:appId`.

## 4. Kontekst okna aplikacji

`buildApplicationLaunchContext()` zapisuje pełny, zamrożony kontekst celu:

```json
{
  "target_id": "...",
  "lat": 0.0,
  "lng": 0.0,
  "label": "...",
  "target_mode": "..."
}
```

Kontekst jest przypisany do konkretnego okna oraz invocation. Hydration nie
może zastąpić go globalnym `__pendingApplicationLaunchContext` innej aplikacji.

Okno istniejącej aplikacji może zostać podniesione na wierzch tylko wtedy, gdy
zgadzają się jednocześnie:

* `app_id`,
* interfejs,
* stabilna tożsamość celu,
* aktywna instancja uruchomienia.

Zakończone okno poprzedniego celu nie może wykonywać następnej akcji.

## 5. Guard replayu przed zwróceniem payloadu

Backend przed zwróceniem istniejącego `app_action_receipt` porównuje:

```text
receipt.username
receipt.app_id
receipt.target_identity
request.expected_target
aktualny PlayerTargetRuntimeStore
```

Dozwolone wyniki:

```text
same invocation + same target  → idempotent replay
target already captured        → superseded_by_capture
receipt belongs to other target → 409 receipt_target_mismatch
current selection changed      → 409 target_selection_changed
```

Backend nie może zwrócić starego `target` w odpowiedzi 200 dla nowej selekcji.
Guard działa przed ścieżką `gonna_win_receipt_replay`.

## 6. Jedna ścieżka aplikacji po wyborze celu

Obie drogi mają kończyć się tym samym kontraktem:

```text
A. mapa → /hack-action → picker → launch_queue → aplikacja
B. nazwa celu → /api/map/aim-target → pulpit/terminal → aplikacja

→ frozen expected_target
→ target-bound launch_receipt
→ /gonna-win
→ monotonic actions_allowed + security
→ PlayerTargetRuntimeStore
→ profil legacy jako projekcja
→ capture albo dalszy postęp
```

Ścieżka B nie kopiuje całego `/hack-action`. Ma jedynie dostarczyć aplikacji
ten sam poziom korelacji celu i idempotencji.

## 7. Pasek, kropki i odpowiedzi spóźnione

Belka korzysta wyłącznie z aktualnego autorytatywnego celu. Odpowiedź aplikacji
może ją zaktualizować tylko wtedy, gdy jej zamrożony `expected_target` odpowiada
bieżącemu targetowi.

Replay albo spóźniona odpowiedź poprzedniego celu:

* nie zmienia belki,
* nie dodaje ani nie usuwa kropki,
* nie zmienia `disarm_progress`,
* nie odtwarza wyczyszczonego `aimed_target`,
* nie uruchamia animacji capture,
* nie publikuje delty nowego celu.

Po capture cel jest czyszczony w runtime i profilu, marker dostaje deltę, a
następna aplikacja rozpoczyna świeżą instancję.

## 8. Capture i terytorium — bez zmiany zasad

Po spełnieniu dotychczasowych warunków:

```text
>= 70% security off
+ scan_ports
+ exploit
+ sniff
+ trace
```

pozostaje obecny pipeline:

1. atomowy capture celu,
2. `PlayerTargetRuntimeStore.mark_captured`,
3. `map.target_captured`,
4. capture filaru konfliktu, jeśli dotyczy,
5. dirty/changing i enqueue workera,
6. publikacja nowej geometrii oraz snapshotu,
7. gotowość na wskazanie kolejnego celu.

Sprint nie dodaje synchronicznych rebuildów do `/gonna-win`, `/hack-action`,
`/api/map/aim-target` ani endpointów mapy.

## 9. Obserwowalność

Rozszerzyć istniejące `APP_FLOW` bez logowania całego profilu:

```text
[APP_INVOCATION] created source=desktop app_id=... target_id=... invocation_id=...
[GONNA_WIN_RECEIPT] new receipt=... target_id=...
[GONNA_WIN_RECEIPT] replay receipt=... target_id=...
[GONNA_WIN_CONFLICT] reason=receipt_target_mismatch expected=... receipt=...
```

Frontendowy trace dla odpowiedzi zawiera:

```text
invocation_id
launch_receipt
expected_target_id
current_target_id
duplicate
idempotent_replay
```

## 10. Testy kontraktowe

Minimum:

1. Lekko wskazany cel A + cztery różne aplikacje z pulpitu kończą capture A.
2. Lekko wskazany cel A + aplikacje z terminala kończą capture A.
3. Mix pulpit/terminal zachowuje jeden cel i monotoniczne kropki.
4. Po capture A lekkie wskazanie B i użycie tej samej aplikacji nie odtwarza A.
5. Ten sam app i choice na A oraz B mają różne receipty.
6. Retry jednego kliknięcia na A ma ten sam receipt i dokładnie jeden efekt.
7. Odpowiedź A po wskazaniu B nie zmienia belki ani runtime B.
8. Backend odrzuca replay receipt A przesłany z `expected_target` B.
9. Capture zakończony przed spóźnioną odpowiedzią daje
   `superseded_by_capture`, bez odtworzenia celu.
10. Dwa równoległe okna różnych aplikacji na tym samym celu zachowują własne
    invocation, ale wspólny monotoniczny postęp celu.
11. Dwa różne cele nie współdzielą okna, receipt ani payloadu.
12. Ścieżka mapowa `/hack-action` nadal działa bez zmiany receiptów kolejki.
13. Zwykły cel, vulnerability, filar i inner konfliktu przechodzą oba warianty.
14. Capture filaru nadal kolejkuje worker i nie robi geometrii w requeście.
15. Cztery kropki, procent, runtime i profil legacy pokazują ten sam cel.

## 11. Walidacja produkcyjna

Test ręczny w jednej sesji, bez przeładowania desktopu:

```text
cel A → xmapper → sniff → capture
cel B → xmapper → sniff → capture
cel C → mix terminal/pulpit → capture
cel D konfliktowy → mix terminal/pulpit → worker rebuild
```

Przy każdym kroku sprawdzić w trace:

* nowy `invocation_id` dla nowego uruchomienia,
* różny receipt pomiędzy celami,
* stały receipt podczas retry jednego kliknięcia,
* brak `gonna_win_receipt_replay` z payloadem innego targetu,
* brak powrotu poprzedniego celu na belkę,
* brak konieczności ratowania procesu triggerem z mapy.

## 12. Kolejność wdrożenia

1. Test odtwarzający replay poprzedniego celu.
2. Generator manualnego invocation i target-bound receipt.
3. Przeniesienie kontekstu przez wszystkie cztery typy aplikacji i hydration.
4. Backendowy guard receipt przed replayem.
5. Testy pulpit/terminal/mapa i odpowiedzi spóźnionych.
6. Produkcyjny test dwóch kolejnych celów tą samą aplikacją.

Nie usuwać istniejącego guardu `expected_target`, target-aware klucza okna ani
CAS capture. Nowy receipt jest dodatkowym brakującym poziomem korelacji.

## Poza zakresem

* zmiana OFS i timingów prezentacji,
* nowe aplikacje lub nowe typy interfejsu,
* balans zabezpieczeń i próg capture,
* zmiana zasad konfliktów lub multi-conflict,
* przebudowa geometrii w requestach,
* migracja historycznych receiptów,
* zmiana TTL innych klas idempotencji.

## DoD

Sprint jest zakończony, gdy lekko wskazany cel można konsekwentnie przejąć
aplikacjami z pulpitu, terminala albo ich miksem; ponowne użycie tej samej
aplikacji dla następnego celu nie może odtworzyć starego payloadu; retry jednego
kliknięcia pozostaje idempotentne; pasek, kropki, runtime i capture dotyczą
zawsze tego samego celu; a ścieżka mapowa oraz worker terytoriów działają bez
regresji i bez nowych rebuildów w requestach.

---

# Sprint 130.8.9.fixsprint-lvlrsp.1 — trwałe rozliczanie LVL i RSP

Status lokalny: IMPLEMENTED / READY FOR TESTS.

Sprint naprawczy przywraca naliczanie istniejącej progresji terytorialnej. Nie
zmienia jeszcze wysokości nagród ani nie dodaje nowych zdarzeń gameplayowych.

## Problem

Aktualna progresja opiera się na różnicy pomiędzy bieżącym
`effective_area` i wartością zapisaną wcześniej w `territory_stats`.
Jednocześnie część zwykłych endpointów wywołuje pełne
`sync_session_profile()`, które:

* przebudowuje terytorium;
* zapisuje aktualny `effective_area`;
* przesuwa punkt odniesienia przed rozliczeniem właściwego zdarzenia.

W konflikcie przejęcie i naliczenie są rozdzielone pomiędzy request
`/gonna-win` i territory workera. Jeżeli pomiędzy nimi nastąpi pełna
synchronizacja profilu, worker otrzymuje:

```text
current_effective_area == previous_effective_area
effective_gain == 0
respect_gain == 0
levels_gained == 0
```

Problem dotyczy nowych i istniejących profili. Nie jest błędem prezentacji
belki — wartości nie trafiają do źródła prawdy.

## Cel

Rozdzielić trzy operacje, które obecnie są połączone:

```text
read profile snapshot
refresh derived territory metrics
settle progression reward
```

Odczyt profilu i zwykłe endpointy nie mogą konsumować ani przesuwać podstawy
nierozliczonej progresji.

## 1. Kanoniczny receipt progresji

Każda trwała zmiana własności, która może zmienić progresję, tworzy
idempotentny receipt:

```text
progression_receipt
├── receipt_id
├── event_type
├── source_event_id
├── actor_username
├── affected_usernames
├── territory_version_before
├── territory_version_after
├── effective_area_before
├── effective_area_after
├── status: pending | applied | rejected
├── reward_payload
└── applied_at
```

`receipt_id` albo `source_event_id` posiada trwały UNIQUE/dedupe. Retry requestu,
restart workera i reconciler nie mogą wypłacić nagrody drugi raz.

## 2. Niezmienny stan before

`effective_area_before` musi zostać utrwalone przed zmianą własności albo razem
z eventem zmiany. Nie wolno odtwarzać go później z aktualnego
`profile.territory_stats`, ponieważ ten profil może zostać w międzyczasie
odświeżony przez inny worker lub request.

Stan `after` może zostać obliczony po publikacji poprawnej geometrii, ale musi
być związany z oczekiwaną `territory_version_after`.

## 3. Read-only profile sync

Endpointy, które tylko czytają profil, katalog aplikacji, stan zabezpieczeń,
operacje albo dane UI, korzystają z lekkiej ścieżki:

```text
sync_session_profile(rebuild_territory=False, ...)
```

Pełny sync może odświeżyć metryki prezentacyjne, lecz nie może:

* oznaczyć pending receipt jako rozliczonego;
* nadpisać `effective_area_before`;
* wyzerować nierozliczonego przyrostu;
* przyznać nagrody bez eventu źródłowego.

## 4. Jeden finalizer progresji

Wprowadzić jeden serwis rozliczający wszystkie receipt’y, używany przez zwykły
capture i territory workera. Finalizer:

1. blokuje albo atomowo claimuje receipt;
2. sprawdza oczekiwaną wersję terytorium;
3. oblicza istniejącą nagrodę z trwałego `before/after`;
4. zapisuje razem profil, wynik receipt i komunikat systemowy;
5. publikuje deltę profilu dopiero po commicie;
6. przy retry zwraca zapisany wynik bez ponownej wypłaty.

Nie wolno rozdzielać zapisu `respect`, `level` i statusu receipt na niezależne
transakcje.

## 5. Zgodność istniejących profili

Migracja nie może ponownie nagrodzić całej historycznej powierzchni.

* profil bez baseline otrzymuje baseline z aktualnego opublikowanego snapshotu;
* profil z baseline zachowuje go;
* tylko nowe eventy po cutover tworzą receipt’y;
* brak receipt oznacza brak automatycznej wypłaty historycznej;
* wartości `level` i `respect` zapisane przed sprintem pozostają bez zmian.

## 5.1. Baseline LVL per rozwijany klaster

Próg awansu nie jest liczony z sumy wszystkich pól gracza. Receipt przechowuje
snapshot każdego klastra sprzed transferu oraz pozycję przejmowanego celu.
Po publikacji geometrii finalizer wybiera klaster zawierający ten punkt i tylko
jego wzrost porównuje z jego własnym baseline.

```text
cluster_total_area_after >= cluster_level_baseline * 1.10
```

Próg LVL korzysta z surowej powierzchni klastra. Nie używa mnożnika gęstości
ani bieżącego LVL, dzięki czemu sam awans i wynikająca z niego zmiana zasięgu
motocykla nie mogą dopchnąć kolejnego poziomu. Mniejsze przyrosty tego samego
klastra kumulują się. Inne klastry gracza nie pomagają i nie przeszkadzają w
domknięciu progu. RSP nadal korzysta z efektywnego przyrostu całej rozliczanej
operacji.

## 6. Recovery i obserwowalność

Worker okresowo sprawdza receipt’y `pending`, ale nie skanuje profili w celu
zgadywania nagród. Log rozliczenia zawiera:

```text
[PROGRESSION_SETTLEMENT]
receipt_id
source_event_id
actor_username
before_effective_area
after_effective_area
effective_gain
respect_gain
levels_gained
status
reason
```

Reconciler raportuje również receipt’y z niezgodną wersją i pozostawia je jako
retryable zamiast zerować nagrodę.

## Testy Sprintu 130.8.9.fixsprint-lvlrsp.1

Minimum:

* zwykłe przejęcie nalicza dotychczasowy RSP i LVL;
* konfliktowy capture rozliczony przez workera nalicza je dokładnie raz;
* `/api/profile`, `/resources.json` i polling pomiędzy capture a workerem nie
  zmieniają wyniku;
* retry `/gonna-win` nie nalicza drugi raz;
* restart workera przed finalizacją nie gubi receipt;
* dwa równoległe capture mają osobne receipt’y;
* stary i nowy profil przechodzą tę samą ścieżkę;
* przegrany uczestnik nie otrzymuje nagrody atakującego;
* frontend otrzymuje aktualne `level`, `respect` i `territory_stats` po commicie;
* endpointy mapy pozostają read-only i nie uruchamiają ciężkiego rebuilda.

## DoD

Sprint jest zakończony, gdy żaden odczyt ani synchronizacja profilu nie może
wyzerować nierozliczonego przyrostu, każda nagroda ma trwały receipt, zwykłe i
konfliktowe przejęcia używają jednego finalizera, a test współbieżnego pollingu
potwierdza dokładnie jednokrotne naliczenie na nowych i starszych kontach.

---

# Sprint 130.8.9.gameplay-lvlrsp.2 — nagrody za otoczenie, filary i konflikty

Status lokalny: COMPLETE (2026-08-16); zależność
`130.8.9.fixsprint-lvlrsp.1` ukończona.

Sprint dodaje jawne nagrody strategiczne do naprawionego, idempotentnego
finalizera progresji. Nie zmienia geometrii, kwalifikacji filarów, zasad
multi-conflict ani mechanizmu przejmowania obiektów.

Jest to świadomy wyjątek od dotychczasowej ogólnej zasady GhostNetwork, według
której pojedyncze zdarzenie nie przyznaje bezpośrednio LVL. Po wdrożeniu sprintu
ten wyjątek dla zwycięstw terytorialnych trzeba dopisać również do
`doc/clans_machines.md`; do czasu wdrożenia obecna reguła produkcyjna pozostaje
bez zmian.

## Zasady nagród

### 1. Pełne otoczenie i wchłonięcie terytorium

Gracz, który domknął pełne otoczenie obcego klastra i doprowadził do jego
trwałego wchłonięcia, otrzymuje:

```text
+1 LVL
+1 RSP za każdy faktycznie przepisany filar
```

Do premii filarowej liczą się wyłącznie obiekty, które w snapshotcie
otoczenia miały `node_role: pillar` i których własność została skutecznie
przeniesiona na zwycięzcę. Innery nie zwiększają tej premii.

Przykład:

```text
wchłonięto 4 filary i 7 innerów
nagroda: +1 LVL, +4 RSP
```

### 2. Ochrona własnego klanu

Nie wolno otoczyć, wchłonąć ani otrzymać nagrody za terytorium gracza z tego
samego klanu.

Guard `territory_owners_are_protected_relation(...)` musi działać przed:

* utworzeniem snapshotu zwycięstwa;
* transferem obiektów;
* zamknięciem konfliktu;
* utworzeniem progression receipt;
* wypłatą LVL lub RSP.

Brak transferu oznacza brak nagrody. Nie wolno tworzyć reward-only eventu dla
chronionej relacji. Zmiana klanu po zdarzeniu nie zmienia już prawidłowo
rozliczonego historycznego wyniku.

### 3. Rozwiązanie konfliktu

Gracz zapisany jako autor trwałego rozwiązania konfliktu otrzymuje za każdy
unikalnie rozwiązany `conflict_id`:

```text
+1 LVL
+(1 RSP × LVL gracza)
```

Mnożnik RSP wykorzystuje LVL gracza z początku atomowego rozliczenia, przed
dodaniem bonusowego poziomu za rozwiązanie tego konfliktu.

Przykład:

```text
LVL przed rozliczeniem: 12
nagroda konfliktowa: +1 LVL, +12 RSP
LVL po rozliczeniu: 13
```

Autorem jest kanoniczny `last_actor_username` albo `closing_player_id` zapisany
w zdarzeniu rozwiązania, nie właściciel profilu aktualnie obsługiwanego przez
request lub worker.

### 4. Łączenie nagród

Jeżeli jedno pełne otoczenie jednocześnie wchłania klaster i rozwiązuje aktywny
konflikt, obie nagrody są należne i sumują się:

```text
otoczenie/wchłonięcie: +1 LVL + RSP za filary
rozwiązanie konfliktu: +1 LVL + RSP według LVL sprzed całego rozliczenia
```

Wszystkie składniki zapisuje jeden receipt albo jedna grupa receiptów związana
tym samym `source_event_id`. Każdy komponent posiada osobny `reward_key`, aby
retry nie wypłacił części nagrody ponownie.

### 5. Multi-conflict

Każdy faktycznie rozwiązany konflikt posiada osobne rozliczenie. Jeden ruch
może zamknąć kilka konfliktów i wtedy przyznaje premię za każdy unikalny
`conflict_id`, ale tylko jeżeli:

* status przeszedł z aktywnego do rozwiązanego;
* gracz jest zapisanym autorem rozwiązania;
* uczestnicy nie są chronieni relacją własnego klanu;
* dany `conflict_id + resolution_version` nie został wcześniej nagrodzony.

Samo przeliczenie geometrii, ponowna publikacja snapshotu albo reconciler nie
tworzą kolejnej nagrody.

## Model reward payload

```text
reward_payload
├── territory_progression
│   ├── respect_gain
│   └── levels_gained
├── encirclement
│   ├── levels_gained: 1
│   ├── transferred_pillar_count
│   └── respect_gain: transferred_pillar_count
├── conflict_resolutions[]
│   ├── conflict_id
│   ├── resolution_version
│   ├── level_before
│   ├── levels_gained: 1
│   └── respect_gain: level_before
└── totals
    ├── respect_gain
    ├── levels_gained
    ├── level_before
    └── level_after
```

Belka i komunikaty systemowe pokazują sumę, ale historia progresji zachowuje
osobne źródła nagrody.

## Komunikaty

Przykład otoczenia:

```text
TERYTORIUM WCHŁONIĘTE
+1 LVL
Przejęte filary: 4
+4 RSP
```

Przykład rozwiązania konfliktu:

```text
KONFLIKT ROZWIĄZANY
+1 LVL
Bonus strategiczny: +12 RSP
```

Komunikat jest emitowany po trwałym zapisie profilu i receipt, nigdy przed
commitem geometrii lub transferu własności.

## Testy Sprintu 130.8.9.gameplay-lvlrsp.2

Minimum:

* otoczenie obcego klastra daje dokładnie `+1 LVL`;
* trzy przepisane filary dają dokładnie `+3 RSP`;
* innery nie zwiększają premii filarowej;
* otoczenie członka własnego klanu nie przenosi obiektów i nie daje nagrody;
* rozwiązanie konfliktu na LVL 8 daje `+1 LVL` i `+8 RSP`;
* mnożnik korzysta z LVL sprzed bonusu;
* otoczenie rozwiązujące konflikt wypłaca oba składniki;
* multi-conflict rozlicza każdy naprawdę zamknięty konflikt dokładnie raz;
* retry, restart workera i reconciler nie duplikują LVL ani RSP;
* ponowna publikacja tego samego snapshotu niczego nie wypłaca;
* właściwym odbiorcą jest `closing_player_id`/`last_actor_username`;
* przegrany, obserwator i pozostali uczestnicy multi-conflict nie dostają
  nagrody zwycięzcy;
* delta profilu aktualizuje belkę bez globalnego reloadu;
* mapa i endpointy odczytowe nie wykonują rozliczenia nagrody.

## Dokumentacja po wdrożeniu

Zaktualizować `doc/clans_machines.md` i `doc/project_journal.md`, zapisując
wyjątek bezpośredniego LVL dla pełnego otoczenia oraz rozwiązania konfliktu,
kolejność mnożnika RSP, ochronę własnego klanu i zasady kumulacji nagród.

## DoD

Sprint jest zakończony, gdy pełne otoczenie obcego terytorium daje `+1 LVL`
i `+1 RSP` za każdy przepisany filar, własny klan pozostaje chroniony przed
otoczeniem i farmingiem, każde trwałe rozwiązanie konfliktu daje `+1 LVL` oraz
RSP równy LVL gracza sprzed rozliczenia, a wszystkie wypłaty są atomowe,
wersjonowane i dokładnie jednokrotne również w multi-conflict i po retry
workera.

---

# Sprinty 130.8.9.SFX.1 — fundament - 130.8.9.SFX.5 — OFS i polish

Kanoniczną specyfikację wdrożeniową opisuje `doc/system_audio.md`, a wyniki
audytu i szersze uzasadnienie architektury pozostają w
`doc/game_sound_effects_system.md`.

Pierwszym wdrożeniem systemu jest czterosekundowe show `Secret Path`, uruchamiane
po lekkim oznaczeniu celu przez kliknięcie nazwy w menu hakowania. Dokument
opisuje przede wszystkim sześć scen backdoora, ale kontrakt od początku obejmuje
również przejęcie celu, wiadomości Cybernera i zdarzenia systemowe.


### Sprint SFX.1 — fundament

- `game_sfx.js`, manifest v1, unlock autoplay, preload i ustawienia lokalne;
- magistrale, dedupe, cooldown, voice limit;
- podstawowy kontrakt duckingu Ghost Radio;
- testy modułu bez podpinania gameplayu.

### Sprint SFX.2 — sześć scen Secret Path

- stabilne identyfikatory scen;
- sześć dostarczonych MP3;
- wspólne losowanie obrazu i audio;
- synchronizacja 4 s, restart sceny i fallback bez audio;
- kontrolki SFX w Ustawieniach.

### Sprint SFX.3 — capture

- zwykły capture, filar, konflikt resolved;
- dedupe po target/version;
- weryfikacja z worker recovery i delta feed.

### Sprint SFX.4 — Cyberner i system

- incoming, sent, warning i critical;
- cisza przy hydratacji/backlogu;
- priorytety i antyspam.

### Sprint SFX.5 — OFS i polish

- semantyczne hooki aplikacji;
- normalizacja głośności assetów;
- testy mobile, wielu okien, radia i długiej sesji.


# Sprinty 130.8.9.UX-appcreator.1–3 — refaktor UX creatorów aplikacji

Status: `DONE (2026-08-17)`.

Dokumentem źródłowym kierunku UX jest
`doc/Refaktor_UX_creatorów_CHAOS.md`. Poniższy zapis jest jego adaptacją do
aktualnej architektury CHAOS i stanowi kanoniczny plan realizacji.

## Aktualny punkt architektoniczny

CHAOS nie utrzymuje czterech niezależnych silników creatorów. Formularze
aplikacji `progressbar_random`, `window`, `terminal` i `button_choices` korzystają
ze wspólnego dziewięciokrokowego wizarda w `static/js/terminal.js`, a wynik
przechodzi przez backendowe `build_generated_app()` i
`normalize_app_contract()`. Refaktor ma rozwijać ten wspólny przepływ, a nie
tworzyć kolejne warianty logiki dla poszczególnych prezentacji.

Warstwa UX może zmieniać nazwy, opisy, ikony, grupowanie, filtry i sposób
wyboru. Nie może zmieniać istniejących kluczy runtime, znaczenia kontraktu ani
payloadu publikowanej aplikacji. W szczególności cztery podstawowe akcje mapy
pozostają jednym kontraktem:

| Klucz runtime | Etykieta gameplayowa | Rodzina creatora |
| --- | --- | --- |
| `scan_ports` | Przeskanuj porty | Scanner / Recon |
| `exploit` | Zainstaluj exploit | Exploit |
| `sniff` | Śledź ruch | Sniffer |
| `trace` | Namierz cel | Scanner / Recon, typ tracer |

`trace` nie staje się nową rodziną narzędzia. Creator ma jedynie jasno
pokazywać, że tracer/namierzanie celu powstaje w rodzinie Scanner / Recon.

## Twarde granice całego pakietu

- bez zmian mechaniki gameplayowej, kosztów, ryzyka, wyniku operacji i uprawnień;
- bez zmian GhostLab, `pro-system-tools`, GhostNetwork, konfliktów i endpointów mapy;
- bez zmian semantyki OFS, provisionala, launch receipt i kolejki uruchomień;
- bez automatycznej migracji bazy; stare i już zainstalowane aplikacje muszą
  pozostać uruchamialne;
- jedna wspólna definicja etykiet, ikon i opisów zamiast kopii w czterech
  formularzach;
- jedna aplikacja ma jedną ikonę będącą jednym widocznym glifem;
- backend pozostaje autorytetem walidacji, frontend daje wcześniejszy i
  zrozumiały komunikat;
- implementacja nie może dokładać ciężkich odczytów profilu ani blokować
  bootu desktopu.

---

## Sprint 130.8.9.UX-appcreator.1 — wspólny fundament UX

Status: `DONE (2026-08-17)`.

### Cel

Utworzyć jedną, bezpieczną warstwę prezentacji opcji creatora i poprawić
czytelność wizarda bez zmiany zapisywanego kontraktu aplikacji.

### Zakres

1. Przeprowadzić audyt wszystkich czterech formularzy, wspólnego wizarda,
   podglądu, publikacji i backendowej normalizacji. Zapisać macierz: pole UI,
   klucz runtime, typ wartości, wartość domyślna i miejsce walidacji.
2. Scentralizować deskryptory opcji: klucz runtime, etykieta gameplayowa, ikona,
   krótki opis, grupa oraz ograniczenia. Istniejące stałe mogą zostać
   scalone, ale serializowane wartości nie mogą się zmienić.
3. Zachować dziewięć kroków wizarda. Każdy krok ma otrzymać stały tytuł,
   krótkie wyjaśnienie intencji i informację, jaki wpływ ma wybór na
   kolejne kroki.
4. Zbudować wspólny selektor `OFF/ON` dostępny z klawiatury. Może on
   wizualnie zastąpić checkbox, ale pod spodem ma zachować dotychczasową
   semantykę formularza i payloadu.
5. Przygotować jedną paletę około 40 ikon zgodną z istniejącym systemem
   ikon CHAOS. Nie kopiować palety pomiędzy creatorami i nie wprowadzać
   osobnego pipeline'u assetów.
6. Dodać spójną walidację ikony po stronie klienta i serwera: jeden widoczny
   glif, w tym poprawna pojedyncza sekwencja emoji; odrzucane są puste wartości,
   tekst, kontrolne znaki i wiele glifów.
7. Uporządkować nazewnictwo Scanner / Recon i tracer zgodnie z tabelą
   podstawowych akcji mapy, bez dodawania czwartej rodziny backendowej.

### Walidacja i regresja

- test kontraktu deskryptorów: każda opcja ma unikalny klucz i kompletną
  prezentację;
- test zgodności payloadu przed i po refaktorze dla wszystkich czterech typów
  interfejsu;
- test klienta i backendu dla ikon ASCII, emoji, emoji z variation selector/ZWJ,
  pustej ikony i wielu znaków;
- `node --check static/js/terminal.js`;
- `python -m py_compile run.py` wyłącznie jeżeli zmienił się backend;
- celowane testy creatorów, kontraktu aplikacji, provisionala i OFS;
- `git diff --check`.

### Dokumentacja i DoD

- uzupełnione `doc/app_contract.md` o mapę etykieta ↔ klucz runtime oraz
  kontrakt ikony;
- `doc/Refaktor_UX_creatorów_CHAOS.md` oznaczony jako artefakt kierunkowy, a ten
  plan jako specyfikacja wykonawcza;
- wpis w `doc/project_journal.md` z zakresem, testami i znanymi ograniczeniami;
- wszystkie cztery creatory korzystają z jednego fundamentu, a stare aplikacje
  otwierają się i uruchamiają bez migracji.

---

## Sprint 130.8.9.UX-appcreator.2 — migracja wizarda i semantyka wyborów

Status: `DONE (2026-08-17)`.

### Cel

Przenieść wszystkie kroki creatora na wspólne kontrolki i opisy tak, aby gracz
wybierał intencję gameplayową, a nie musiał znać nomenklatury backendu.

### Zakres

1. Zmigrować cztery typy interfejsu na wspólne komponenty bez kopiowania
   rendererów, listenerów i filtrów.
2. Zastąpić ściany checkboxów czytelnymi macierzami `OFF/ON`, z jednoznacznymi
   stanami `OFF`, `ON`, `hover`, `focus` i `disabled`. Stan nie może być
   komunikowany wyłącznie kolorem.
3. W kroku celu rozdzielić etykietami: rodzaj celu, miejsce uruchomienia,
   akcję mapy, operację desktopową i wymagane zasoby. Nazwy techniczne mogą
   pozostać wyłącznie w rozwijanym podglądzie kontraktu.
4. Zgrupować zasoby według faktycznej semantyki, np. lokalizacja, urządzenie,
   media, konta i finanse. Grupy są prezentacją istniejących kluczy, nie nowym
   modelem danych.
5. Przepisać krok ryzyka na pytania gameplayowe, zachowując dokładne
   mapowanie do obecnych pól: zabezpieczenia celu, wymagania narzędzia, wpływ
   na gracza oraz efekt operacji nie mogą zostać ze sobą pomylone.
6. Filtrować dalsze opcje na podstawie rodziny, celu i akcji. Ukrycie opcji ma
   jawnie czyścić niezgodną wartość albo zachować ją z widocznym
   ostrzeżeniem; nie wolno pozostawiać niewidocznego, aktywnego pola.
7. Zachować wybory przy przechodzeniu `Wstecz/Dalej`, o ile nadal są zgodne.
   Zmiana nadrzędnej decyzji ma powodować deterministyczną rekalkulację,
   a nie losowe zerowanie formularza.

### Walidacja i regresja

- macierz tworzenia dla `progressbar_random`, `window`, `terminal` i
  `button_choices`;
- dla każdego typu: utworzenie scanner, exploit, sniffer oraz tracer przez
  Scanner / Recon;
- przejście przód/wstecz, szybkie przełączanie opcji, zmiana rodziny po
  wypełnieniu dalszych kroków i odtworzenie formularza po błędzie walidacji;
- publikacja, instalacja, uruchomienie z desktopu i terminala oraz uruchomienie
  akcji mapy bez zmiany docelowego klucza;
- regresja starych aplikacji i inferencji legacy;
- standardowe `node --check`, celowane testy jednostkowe i `git diff --check`.

### Dokumentacja i DoD

- `doc/app_contract.md` opisuje grupy UX oraz ich niezmienne mapowanie na pola
  kontraktu;
- w `doc/project_journal.md` zapisano listę zmigrowanych ekranów i wynik macierzy
  regresji;
- w tym pliku status sprintu i faktyczny zakres zostają zaktualizowane po
  walidacji;
- użytkownik może zbudować cztery podstawowe narzędzia mapy bez znajomości
  kluczy backendowych.

---

## Sprint 130.8.9.UX-appcreator.3 — podgląd, walidacja i production polish

Status: `DONE (2026-08-17)`.

Wynik: wspólny wizard czterech creatorów ma podsumowanie gameplayowe, zwijany
kontrakt techniczny, deterministyczne filtry rodzina → cel → akcja oraz
walidację kierującą do pola wymagającego poprawy. Backend odrzuca nieznane
rodziny, tryby, typy i wartości spoza jawnego kontraktu rodziny; legacy bez
jawnego `tool_family` zachowuje dotychczasową ścieżkę i nie wymaga migracji.
`Scanner / Recon` dopuszcza zarówno typ `scanner`, jak i `tracker`, dzięki czemu
`Namierz cel` nadal powstaje jako akcja `trace`, a nie nowa rodzina.

### Cel

Domknąć creator czytelnym podsumowaniem, walidacją kontekstową,
responsywnością, dostępnością i pełną regresją przepływu publikacji.

### Zakres

1. Podgląd przed publikacją zaczynać od podsumowania dla gracza: nazwa,
   rodzina, cel, miejsce startu, akcje, zasoby, ryzyko, ikona i typ prezentacji.
   Surowy JSON pozostaje dostępny jako zwijany widok techniczny.
2. Dodać walidację kontekstową przed publikacją: komunikat wskazuje krok,
   pole, oczekiwaną wartość i sposób naprawy. Backend nadal powtarza
   krytyczne walidacje i nie ufa payloadowi klienta.
3. Domknąć inteligentne filtry rodziny i celu na podstawie obecnego kontraktu,
   bez heurystyk tworzących nieobsługiwane kombinacje runtime.
4. Dopracować układ dla pełnego desktopu, małego ekranu, mapy otwartej obok
   creatora oraz niskiego viewportu. Wizard ma mieć kontrolowaną wysokość,
   lokalny pionowy scroll i nie może tworzyć poziomego overflow.
5. Zapewnić obsługę klawiaturą, widoczny focus, poprawne etykiety i stan
   kontrolek dla technologii asystujących. Dynamiczne filtry i błędy mają
   aktualizować właściwe atrybuty dostępności.
6. Dodać wspólne testy kontraktowe zabezpieczające zgodność frontendowych
   deskryptorów, backendowej normalizacji i faktycznego payloadu publikacji.
7. Wykonać ręczną regresję: tworzenie, podgląd, publikacja, instalacja,
   uruchomienie z mapy/desktopu/terminala, edycja jeżeli jest dostępna, powrót
   kroków, reload i stare aplikacje.

### Walidacja końcowa

- testy creatorów oraz `tests.test_target_persistence` w zakresie generowanych
  aplikacji;
- testy `tests.test_provisional_application_launch_contract` i
  `tests.test_operation_feedback_frontend_contract` dla wszystkich czterech
  prezentacji;
- testy walidacji backendowej i kompatybilności legacy;
- `node --check static/js/terminal.js`;
- `python -m py_compile run.py database.py` tylko gdy pliki zostały zmienione;
- `git diff --check`;
- smoke test na koncie nowym i istniejącym, na desktopie i mobilnym viewportcie.

### Dokumentacja i DoD

- zaktualizowane `doc/app_contract.md`, ten plan oraz
  `doc/Refaktor_UX_creatorów_CHAOS.md`, bez sprzecznych statusów i nazw;
- `doc/project_journal.md` zawiera wynik walidacji, znane ograniczenia i informację
  o braku migracji lub opis migracji, jeżeli audyt jednak wykaże jej potrzebę;
- brak zmian kontraktu runtime, gameplayu, mapy, OFS, GhostLab i pro-tools;
- creator jest zrozumiały bez znajomości backendu, a podgląd jednoznacznie
  pokazuje, co zostanie opublikowane.

## Procedura realizacji i odbioru

Każdy z trzech sprintów rozpoczyna się od `git status --short`, ponownego
odczytania aktualnego wizarda, `build_generated_app()`,
`normalize_app_contract()` i testów kontraktowych. Zmiany mają być małe,
etapowe i nie mogą cofać cudzych modyfikacji.

Po implementacji obowiązują testy celowane, kontrola składni plików dotkniętych
zmianą oraz `git diff --check`. Domknięcie sprintu zawsze aktualizuje:

1. status i wynik sprintu w `doc/game_play_180726.md`;
2. kontrakt w `doc/app_contract.md`, jeżeli zmieniła się prezentacja lub
   walidacja danych;
3. `doc/project_journal.md` z wykonanym zakresem i wynikiem testów;
4. artefakt źródłowy, jeżeli wdrożenie ujawni zmianę założeń.

Commit, push, deploy, migracja danych i restart procesów nie należą do
automatycznego domknięcia sprintu i wymagają osobnej decyzji użytkownika.


# Sprint 130.9 — GhostNetwork Runtime Enablement

Status: `DONE (2026-08-19)`.

Foundation (`130.9.1`–`130.9.3` oraz read-only część `130.9.12`):
`GO (2026-08-19)`. Dostarczono jawny operatorski bootstrap, walidację
konfiguracji dropów, bezpieczną telemetrię aim/capture, runtime readiness,
endpoint administracyjny i testy. Dropy pozostają domyślnie wyłączone w
produkcji.

Durability, Runtime bridge i End-to-end: `GO (2026-08-19)`. Kanoniczny capture
tworzy trwały effect, a reconciler potrafi odtworzyć brakujący effect z
committed ownership/captured target oraz aktywnej reservation. Publikacje
post-130 obszarów i konfliktów sterują istniejącym lifecycle, module progress,
reward/contribution i osiągalnym endgame. Test E2E przechodzi przez Target
Registry, `/gonna-win`, receipt, outbox, snapshot repository i retry.

## Cel

Uruchomić istniejący GhostNetwork w prawdziwym runtime gry i doprowadzić system do stanu, w którym można go testować end-to-end bez ręcznego ingerowania w bazę, wymuszania stanów testowych ani korzystania z izolowanych harnessów.

Sprint nie projektuje GhostNetwork od nowa.

Nie zmieniamy:

* katalogu części,
* repository,
* modelu visibility,
* snapshotów,
* UI mapy,
* podstawowych kontraktów sprintów 110–130,

o ile test integracyjny nie wykaże konkretnego błędu wymagającego naprawy.

Bazujemy na wynikach audytu:

* brak aktywnego cyklu,
* brak 20 runtime instances części,
* dropy domyślnie wyłączone,
* `drop chance = 0`,
* brak produkcyjnego bootstrapu cyklu,
* post-130 territory/CAS runtime nie publikuje części wymaganych eventów do GhostNetwork,
* istnieje luka exactly-once pomiędzy capture a efektem GhostNetwork.

## Kontrakt realizacji sprintu

Sprint realizujemy etapami `130.9.1`–`130.9.12`, ale nie traktujemy numeracji
jako zgody na wdrożenie wszystkiego naraz. Każdy etap rozpoczyna się od
`git status --short`, odczytania aktualnego diffu i wskazania istniejących
testów oraz kontraktów, które zabezpieczają zmieniany fragment. Nie cofamy
lokalnych ani cudzych zmian i nie porządkujemy kodu niezwiązanego z etapem.

Obowiązuje rozdział odpowiedzialności:

* proces webowy i worker mogą jedynie sprawdzać readiness; ich zwykły start
  nie może samodzielnie tworzyć cyklu, migrować schematu ani naprawiać danych;
* mutujący bootstrap, migracje i reconciliation uruchamia operator przez
  jawny, idempotentny skrypt techniczny;
* każdy trwały efekt ma kanoniczny identyfikator idempotencji i stan możliwy
  do odczytu diagnostycznego;
* feature flagi oddzielają wdrożenie kodu od włączenia dropów, adaptera
  terytoriów, rewards i endgame;
* tryb testowy nie może być osiągalny tylko przez payload klienta ani działać
  w środowisku oznaczonym jako produkcyjne;
* skrypty mutujące domyślnie wykonują `--dry-run`, wymagają jawnego trybu
  wykonania i drukują podsumowanie zmian bez sekretów oraz hidden topology.

Każdy etap kończy się małym, sprawdzalnym diffem, testami celowanymi,
`git diff --check` i aktualizacją dokumentacji. Pełna regresja GhostNetwork
jest bramką przed przejściem do wdrożenia, nie zamiennikiem testów celowanych.

---

# 130.9.1 — Runtime bootstrap GhostNetwork

Wprowadzić jawny i idempotentny bootstrap GhostNetwork.

Przed włączeniem gameplayu musi istnieć dokładnie jeden poprawny aktywny cykl.
Start procesu sprawdza ten warunek i w razie jego niespełnienia zgłasza
`NOT READY`; utworzenie lub naprawa cyklu należy do jawnego kroku operatorskiego.

Bootstrap:

1. sprawdza, czy istnieje aktywny cykl,
2. jeśli istnieje — waliduje go,
3. jeśli nie istnieje — tworzy nowy,
4. tworzy dokładnie 20 instancji części zgodnie z katalogiem,
5. generuje / waliduje topology,
6. potwierdza readiness GhostNetwork.

Bootstrap nie może tworzyć drugiego aktywnego cyklu przy:

* restarcie aplikacji,
* restarcie workera,
* równoległym starcie kilku procesów.

Mechanizm musi opierać się na ograniczeniu lub blokadzie w trwałym storage,
a nie wyłącznie na blokadzie procesu. Dwa równoległe wywołania skryptu mają
zakończyć się jednym cyklem i tym samym wynikiem readiness.

Stan poprawny:

`1 active cycle`
`20 part instances`
`valid topology`
`0 duplicate active cycles`

Jeżeli runtime nie może osiągnąć tego stanu, GhostNetwork ma zgłosić wyraźny stan:

`NOT READY`

z konkretnym powodem.

---

# 130.9.2 — Jawna konfiguracja dropów

Przenieść GhostNetwork z bezpiecznego trybu development-disabled do jawnej konfiguracji runtime.

Nie ustawiaj przypadkowej wartości balansu.

Wprowadzić czytelne ustawienia:

`GHOSTNETWORK_DROPS_ENABLED`
`GHOSTNETWORK_DROP_CHANCE`

oraz walidację przy starcie.

Jeżeli:

`drops_enabled = true`

to:

`drop_chance` musi być `> 0` i `<= 1`.

W przeciwnym przypadku readiness ma zgłosić błąd konfiguracji.

Na potrzeby testów development/test można użyć kontrolowanej wartości pozwalającej realnie uzyskać części podczas sesji.

Nie hardcodować wysokiego chance w logice produkcyjnej.

---

# 130.9.3 — Telemetria drop pipeline

Dodać obserwowalność pełnego pipeline.

Dla każdego aim kwalifikowanego przez GhostNetwork zapisujemy wynik techniczny, np.:

* `no_active_cycle`
* `not_eligible`
* `missing_player_clan`
* `drops_disabled`
* `roll_missed`
* `reserved`
* `reservation_conflict`
* `no_candidate_part`

Po capture:

* `no_matching_reservation`
* `reservation_expired`
* `part_discovered`
* `already_discovered`
* `discovery_reconciled`

Telemetria nie może ujawniać graczowi:

* ukrytego `part_id`,
* przyszłych części,
* topologii,
* wyniku rolla przed discovery.

Ma służyć diagnostyce systemowej.

Po tym sprincie musi być możliwe stwierdzenie:

`100 hacków`
→ `X eligible aims`
→ `Y rolls`
→ `Z reservations`
→ `N discoveries`

bez zgadywania.

---

# 130.9.4 — Durable GhostNetwork capture effect

Naprawić lukę exactly-once wykrytą w audycie.

Aktualny problem:

`capture committed`
→ proces pada
→ GhostNetwork hook nie dochodzi do discovery
→ retry widzi receipt jako duplicate/in-flight
→ capture nie jest ponownie wykonywany
→ efekt GN może zostać utracony.

GhostNetwork discovery musi stać się trwałym efektem skorelowanym z kanonicznym capture.

Preferowany model:

`canonical capture`
→ `durable GN effect record / outbox`
→ `GN discovery execution`
→ `effect acknowledged`

Retry/reconciliation musi móc rozpoznać:

`target captured`
+
`valid committed Ghost reservation`
+
`brak ghost.part_discovered`

i bezpiecznie dokończyć discovery.

Wymagania:

* brak podwójnego discovery,
* brak podwójnej części,
* brak podwójnej nagrody,
* retry jest idempotentny,
* crash w dowolnym miejscu nie może trwale zgubić efektu.

---

# 130.9.5 — Post-130 territory adapter bridge

Podłączyć GhostNetwork do nowego runtime terytoriów po refaktorze 130.

Nie przywracać starej logiki terytoriów.

Nowy runtime:

* ownership CAS,
* conflicts,
* engagements,
* reconciliation,
* territory publication,

ma publikować kanoniczne zdarzenia potrzebne przez GhostNetwork.

Zbudować cienki adapter:

`post-130 territory event`
→ `GhostTerritoryAdapter`
→ `GhostNetwork lifecycle`

Zweryfikować co najmniej zdarzenia:

* territory stabilized,
* territory owner changed,
* territory contested,
* territory released,
* conflict started,
* conflict resolved.

Nie duplikować source of truth terytoriów w GhostNetwork.

GhostNetwork ma konsumować wynik systemu terytoriów, a nie samodzielnie go obliczać.

---

# 130.9.6 — Public → contained → active

Po discovery część nie może kończyć życia na statusie `public`.

Zintegrować istniejący lifecycle z nowymi eventami terytorialnymi.

Zweryfikować realną ścieżkę:

`pooled`
→ `reserved`
→ `public`
→ `contained`
→ `active`

oraz drogi odwrotne wynikające z utraty / konfliktu terytorium.

Każda zmiana statusu:

* musi być idempotentna,
* musi pochodzić z kanonicznego eventu,
* musi mieć poprawny event domenowy,
* musi aktualizować snapshot/delta.

---

# 130.9.7 — Module progress i abilities

Po aktywacji części sprawdzić istniejący `GhostModuleStateService`.

Nie przepisywać go.

Podłączyć go do realnych zmian lifecycle tak, aby aktywne części faktycznie aktualizowały stan maszyny.

Zweryfikować:

* 0/5,
* 1/5,
* ...
* 5/5,

zgodnie z kontraktem konkretnej maszyny.

Ability może zostać aktywowana wyłącznie wtedy, gdy istniejący kontrakt sprintów 124+ mówi, że warunki zostały spełnione.

Ten sprint nie projektuje nowych abilities.

---

# 130.9.8 — Rewards i contribution

Podłączyć istniejące:

* contribution ledger,
* reward service,
* RSP,
* permanent participation history,

do realnych eventów runtime.

Rewards muszą być exactly-once.

Retry tego samego zdarzenia nie może:

* zwiększyć RSP drugi raz,
* utworzyć drugiego contribution,
* zmienić historii dwa razy.

Bieżący stan GhostNetwork nadal nie może zostać zapisany do profilu.

Profil pozostaje jedynie konsumentem trwałych efektów gracza.

---

# 130.9.9 — Closure i transmission

Doprowadzić do osiągalności istniejący endgame GhostNetwork.

Nie przebudowywać mechaniki.

Podłączyć realny runtime do:

`20/20 condition`
→ `cycle closure`
→ `transmission`
→ `GhostSignal`
→ `narrative`
→ `archive`

Zweryfikować idempotencję całej ścieżki.

Jedno zamknięcie cyklu nie może wygenerować:

* dwóch transmisji,
* dwóch sygnałów,
* dwóch zestawów nagród,
* dwóch archiwizacji.

Nie uruchamiać automatycznie kolejnego cyklu, jeżeli nie było to częścią dotychczas zatwierdzonego kontraktu.

Jeżeli auto-start kolejnego cyklu nadal jest poza zakresem — pozostawić go poza zakresem.

---

# 130.9.10 — Real integration test

Zbudować jeden test, który używa możliwie produkcyjnej ścieżki.

Nie wolno testować wyłącznie przez bezpośrednie wywołania service methods.

Scenariusz minimalny:

1. runtime posiada aktywny cykl,
2. istnieje 20 części,
3. gracz posiada clan identity,
4. gracz wybiera zwykły hackowalny target mapy,
5. target przechodzi przez Target Registry / aimed runtime,
6. GhostNetwork wykonuje eligibility,
7. test deterministycznie wymusza pozytywny roll,
8. powstaje reservation,
9. gracz kończy realną ścieżkę capture,
10. receipt zostaje zapisany,
11. część przechodzi do `public`,
12. event jest opublikowany,
13. snapshot/API pokazuje część zgodnie z visibility,
14. delta dociera do konsumenta,
15. event terytorialny przeprowadza część do `contained`,
16. kolejny poprawny event przeprowadza ją do `active`,
17. module progress zmienia się,
18. reward/contribution wykonuje się dokładnie raz.

Dodatkowo test retry:

* ten sam capture zostaje wysłany drugi raz,
* nie powstaje druga część,
* nie powstaje drugi reward,
* status pozostaje spójny.

---

# 130.9.11 — Dev test mode

Dodać bezpieczny sposób testowania GN bez wykonywania kolejnych 500 hacków.

Development/test mode może umożliwiać:

* zwiększony drop chance,
* deterministic RNG,
* wskazanie konkretnego testowego targetu,
* szybkie wywołanie warunków terytorialnych,

ale wyłącznie za jawnie włączoną flagą development/test.

Nie może istnieć możliwość przypadkowego uruchomienia tego trybu jako produkcyjnego gameplayu.
Runtime ma odrzucić start, jeżeli flaga testowa jest aktywna w środowisku
produkcyjnym. Deterministyczny RNG wstrzykujemy po stronie serwera; klient nie
może wybrać wyniku rolla, części ani statusu lifecycle.

Test mode nie może zmieniać kontraktu domenowego.

Ma jedynie skracać drogę do zdarzeń.

---

# 130.9.12 — Readiness endpoint / diagnostics

Rozszerzyć diagnostykę GhostNetwork.

Read-only stan powinien pokazywać co najmniej:

* `ready`
* `active_cycle_id`
* `parts_total`
* `pooled`
* `reserved`
* `public`
* `contained`
* `active`
* `drops_enabled`
* `drop_chance`
* `topology_valid`
* `pending_effects`
* `unreconciled_effects`
* `last_event`
* `warnings`

Stan:

`ready=true`

jest możliwy wyłącznie wtedy, gdy:

* istnieje dokładnie jeden aktywny cykl,
* istnieje dokładnie 20 części,
* topology jest poprawna,
* konfiguracja dropów jest poprawna,
* repository jest dostępne.

Endpoint jest read-only, dostępny zgodnie z istniejącym kontraktem
administracyjnym i nie ujawnia identyfikatorów ukrytych części ani topology.
Readiness rozróżnia błąd krytyczny od ostrzeżenia oraz zwraca stabilne kody
powodów, które mogą konsumować monitoring i skrypty wdrożeniowe.

---

# Narzędzia serwerowe i operacje

W ramach sprintu powstają cienkie skrypty korzystające z tych samych serwisów
aplikacyjnych co runtime. Nie wolno duplikować w nich reguł domenowych ani
wykonywać ad-hoc SQL poza jawną migracją.

Minimalny zestaw operacyjny:

* `status` — read-only readiness, liczniki lifecycle, stan flag, kolejki
  efektów i ostatni bezpieczny event;
* `bootstrap --dry-run|--apply` — idempotentne utworzenie albo walidacja
  aktywnego cyklu i 20 instancji;
* `reconcile --dry-run|--apply` — odnalezienie i dokończenie committed capture
  bez acknowledged GN effect;
* `drain` — wstrzymanie nowych reservations i bezpieczne dokończenie już
  zapisanych efektów przed restartem lub rollbackiem;
* `verify` — niezmieniająca danych kontrola topology, duplikatów, osieroconych
  reservations/effects i exactly-once keys.

Każdy skrypt ma kod wyjścia przydatny dla automatyzacji, `--help`, czytelny
wynik tekstowy lub JSON, test CLI na tymczasowej bazie i odmowę mutacji przy
niepełnej konfiguracji. Dokumentacja podaje dokładne komendy dla środowiska
development, test i produkcja, ale nie zawiera danych dostępowych.

# Migracje, rollout i rollback

Jeżeli durable effect/outbox, ograniczenie jednego aktywnego cyklu lub
telemetria wymagają zmiany schematu, dostarczamy migrację do przodu oraz
sprawdzony plan zgodności ze starą wersją procesu. Migracja nie może włączać
gameplayu ani samoczynnie tworzyć cyklu.

Kolejność rollout:

1. wdrożenie zgodnego wstecz schematu i kodu przy wyłączonych nowych flagach;
2. `verify`, migracja danych i operatorski `bootstrap`;
3. obserwacja readiness oraz telemetrii przy wyłączonych dropach;
4. włączenie durable capture effect i reconciliation;
5. kontrolowane włączenie dropów, następnie adaptera territory;
6. osobne włączenie module progress/rewards;
7. endgame dopiero po przejściu testu closure/transmission.

Rollback wyłącza nowe reservations, lecz nie usuwa cyklu, odkrytych części,
ledgerów ani outboxu. Najpierw wykonuje się `drain` i `verify`; zapisane efekty
pozostają możliwe do ponowienia po powrocie poprawnej wersji. Każda flaga ma
opisaną wartość bezpieczną oraz zależności od pozostałych flag.

# Dokumentacja wymagana w sprincie

Implementacja aktualizuje równolegle:

* ten plan — status, faktyczny zakres i odstępstwa;
* `doc/ghostnetwork_architecture.md` — ownership, przepływ eventów,
  exactly-once/outbox, granice adapterów i source of truth;
* `doc/ghostnetwork_endgame_runbook.md` — closure, transmission, retry,
  operator recovery i zakaz automatycznego kolejnego cyklu;
* dokument konfiguracji/deploymentu — flagi, wartości bezpieczne, kolejność
  rollout/rollback i komendy skryptów technicznych;
* `doc/project_journal.md` — zmiany, migracje, uruchomione testy z wynikami,
  readiness oraz znane ograniczenia;
* kontrakty API/eventów/delt, jeżeli ich pola albo semantyka ulegną zmianie.

Dokumentacja opisuje stan faktycznie wdrożony, nie planowany. Nazwy eventów,
flag, liczników i kodów readiness muszą być identyczne w kodzie, testach oraz
runbooku.

# Kolejność implementacji i bramki

Prace dzielimy na cztery odbieralne paczki:

1. **Foundation:** `130.9.1`–`130.9.3` i read-only część `130.9.12`.
   Bramka: jeden cykl/20 części, jawna konfiguracja i obserwowalny pipeline,
   nadal bez obowiązku włączenia dropów.
2. **Durability:** `130.9.4`, migracja/outbox, reconciliation i skrypty
   `verify/drain`. Bramka: testy crash-point oraz retry bez utraty i duplikacji.
3. **Runtime bridge:** `130.9.5`–`130.9.8`. Bramka: kanoniczne eventy
   territory prowadzą `public → contained → active`, a progress i rewards są
   exactly-once.
4. **End-to-end:** `130.9.9`–`130.9.12`, test realnej ścieżki, bezpieczny dev
   mode, closure i runbook. Bramka: automatyczny E2E oraz manualny smoke bez
   bezpośredniej ingerencji w bazę.

Po każdej paczce zapisujemy werdykt cząstkowy `GO/NO-GO`. `NO-GO` nie jest
obchodzone przez ręczne poprawienie rekordów; problem otrzymuje test
reprodukcyjny i wraca do właściwej paczki.

## Wynik implementacji 130.9

* `ghost_capture_effects` jest durable outboxem skorelowanym z capture key,
  graczem, targetem i reservation. Statusy `pending/applied/failed`, liczba prób
  i acknowledgement są widoczne w readiness.
* `reconcile` porównuje aktywne reservations z kanonicznym ownership store albo
  `captured_targets`; naprawia także crash przed samym enqueue. `drain --apply`
  wykonuje reconciliation i idempotentnie przetwarza pending/failed effects.
* Zwykły capture oraz ownership CAS enqueue'ują effect przed synchroniczną próbą
  discovery. Replay in-flight/completed receipt nie powiela części ani reward.
* `record_territory_areas_delta()` i `record_territory_conflict_delta()` są
  rzeczywistymi post-130 publication boundaries. Cienki bridge przekazuje
  kanoniczne polygon/owner/clan/version/conflict do istniejącego adaptera GN.
* Publikacja pełnego zbioru stabilnych obszarów obsługuje stabilization, owner
  change, release i reconciliation. Publikacja konfliktu zamraża części, a
  resolved publication odtwarza stan z aktualnego territory source of truth.
* Lifecycle emituje istniejące eventy i aktualizuje snapshot/delta oraz
  `GhostModuleStateService`. Rewards/contribution korzystają z istniejących
  dedupe keys; profil otrzymuje tylko trwałe RSP/history, nigdy stan cyklu.
* Abilities pozostają zgodne ze Sprintem 124: resolve bazuje na aktywnym module,
  a adapter `apply_modifier()` pozostaje no-op tam, gdzie nie zatwierdzono
  jeszcze mechaniki lub balansu. Sprint nie dodał nowych abilities.
* Po realnym 20/20 publication bridge wywołuje istniejący atomowy lock,
  transmission, GhostSignal, narrative i archive. Retry nie tworzy drugiego
  sygnału; kolejny cykl nie startuje automatycznie.
* Runtime readiness wymaga aktywnego cyklu, 20 części, poprawnej topologii,
  włączonych i poprawnie skonfigurowanych dropów oraz zera pending/failed
  capture effects. Test mode w produkcji daje `NOT READY`.
* Lokalny bootstrap utworzył `ghostnetwork_0001`: 1 aktywny cykl, 20 pooled
  parts, poprawna topologia. Developerski verify z chance `0.25` zwrócił
  `READY`; override nie został zapisany jako produkcyjny balans.

Walidacja końcowa:

* nowe testy 130.9: Target Registry → `/gonna-win` → receipt → outbox →
  discovery/reward, crash→reconcile→drain, publication→contained→active→
  contest/resolution/release i runtime closure/transmission;
* pełne `test_ghostnetwork*.py`: 143/143 OK;
* post-130 territory/CAS/reconciliation: 58/58 OK;
* `py_compile` i `git diff --check`: OK;
* zbiorczy legacy `tests.test_target_persistence` ma istniejące zależności od
  kolejności/globalnego stanu; dotknięte testy przechodzą osobno, a nowy E2E
  posiada izolowane stores i receipt.

---

# Testy regresyjne

Obowiązkowo sprawdzić:

Macierz walidacji obejmuje:

* testy jednostkowe reguł eligibility, lifecycle, idempotencji i readiness;
* testy repository/migracji na świeżej bazie oraz bazie z danymi sprzed 130.9;
* testy współbieżności bootstrapu, reservation, capture effect i rewards;
* testy crash-point przed i po każdym trwałym zapisie outbox/ack;
* testy kontraktowe publisher → adapter → GhostNetwork oraz snapshot/delta;
* testy CLI dla `--dry-run`, `--apply`, kodów wyjścia i odmowy pracy przy
  błędnej konfiguracji;
* test bezpieczeństwa blokujący test mode w produkcji i wycieki hidden data;
* jeden E2E przez publiczną ścieżkę aplikacji oraz manualny smoke z runbooka;
* pełną istniejącą regresję sprintów 110–130 po przejściu testów celowanych.

Testy używają izolowanej bazy i kontrolowanego zegara/RNG. Nie zależą od
kolejności uruchomienia, nie pozostawiają aktywnego cyklu w bazie developerskiej
i nie uzyskują pozytywnego wyniku przez bezpośrednią korektę rekordów.

### Cycle

* restart nie tworzy drugiego cyklu,
* concurrency nie tworzy drugiego cyklu,
* cykl zawsze posiada 20 części.

### Drop

* disabled = brak rolla,
* chance 0 = brak rolla,
* chance 1 = reservation,
* nieeligible target = brak rolla,
* own-clan exclusion działa,
* brak dostępnych części daje poprawny reason.

### Reservation

* aim tego samego targetu nie rezerwuje kilku części,
* expiration działa,
* capture innego targetu nie konsumuje reservation.

### Capture

* discovery exactly-once,
* duplicate receipt nie duplikuje części,
* crash przed discovery jest reconciled.

### Territory

* stabilize,
* conflict,
* owner change,
* release,
* rebuild/reconciliation,

muszą utrzymywać poprawny lifecycle części.

### Delta / snapshot

* część widoczna tylko dla właściwego viewer projection,
* delta po commit,
* brak hidden topology leak.

### Rewards

* exactly-once,
* retry-safe.

### Closure

* 20/20 zamyka cykl dokładnie raz,
* transmission dokładnie raz,
* narrative dokładnie raz.

---

# Acceptance criteria

Sprint 130.9 jest zakończony dopiero wtedy, gdy można uruchomić grę i wykonać prawdziwy test bez bezpośredniej ingerencji w bazę.

Minimalny test manualny:

`login`
→ `map`
→ `target`
→ `aim`
→ `hack`
→ `successful capture`
→ `GhostNetwork part discovered`
→ `part visible in GN`
→ `territory condition`
→ `part contained`
→ `part active`
→ `machine progress updated`

oraz automatyczny integration test potwierdza tę samą ścieżkę.

Dodatkowo diagnostyka runtime musi pokazać:

`ready=true`

oraz faktyczne liczniki:

`aim`
`eligible`
`roll`
`reservation`
`discovery`

---

# Definition of Done

Sprint można zamknąć tylko jeżeli:

* GhostNetwork bootstrapuje się bezpiecznie,
* istnieje aktywny cykl,
* istnieje dokładnie 20 części,
* topology jest valid,
* dropy mogą realnie działać,
* prawdziwy aim wykonuje roll,
* prawdziwy capture odkrywa część,
* crash/retry nie gubi discovery,
* post-130 territory runtime jest podłączony do GN,
* część może przejść `public → contained → active`,
* module progress działa z realnych eventów,
* rewards są exactly-once,
* snapshot i delta pokazują aktualny stan,
* integration test przechodzi,
* manualny test w grze przechodzi,
* migracja została sprawdzona na bazie świeżej i zgodnej ze stanem sprzed sprintu,
* skrypty `status/bootstrap/reconcile/drain/verify` mają testy i runbook,
* rollout i rollback zostały przećwiczone bez utraty trwałych efektów,
* dokumentacja architektury, konfiguracji, endgame i journal odpowiada kodowi,
* nie pozostają nieudokumentowane flagi, ręczne kroki SQL ani wymagane
  działania operatorskie wykonywane automatycznie przy starcie procesu.

Na końcu sprintu wypisz:

* wszystkie znalezione dodatkowe problemy,
* wykonane zmiany,
* testy i ich wyniki,
* wykonane migracje i wynik próbnego rollbacku,
* użyte wartości flag bez sekretów,
* wynik `status`, `verify` i stan pending/unreconciled effects,
* aktualny runtime readiness,
* `git diff --stat`,
* oraz werdykt:

`GO — GhostNetwork ready for gameplay testing`

albo

`NO-GO — GhostNetwork still not testable end-to-end`.

## Ograniczenie

Nie rozszerzaj zakresu sprintu o nowe feature'y GhostNetwork.

130.9 ma **uruchomić i połączyć istniejące elementy sprintów 110–130 z runtime po refaktorze 130**, a nie wymyślać GhostNetwork po raz drugi.

# Sprint 130.9.1 — GhostNetwork Gameplay Validation

**Status:** `SERVER RECONCILE DONE — LIFECYCLE VALIDATION PENDING` (2026-08-19).

**Typ sprintu:** walidacja runtime, domknięcie integracji i naprawa wykrytych
regresji. To nie jest sprint feature'owy ani deploymentowy.

**Stan wejściowy:** Sprint 130.9 jest zakończony, lokalny runtime ma aktywny
cykl `ghostnetwork_0001`, 20 części, poprawną topology i readiness `READY`.
Ten stan trzeba ponownie potwierdzić przed pierwszą próbą; zapis w dokumencie
nie zastępuje odczytu z bieżącej bazy.

**Podział wykonania:** Etap 1A kończy lokalną walidację kodu i testów. Etap 1B
wdraża release candidate na kontrolowany serwer z działającym procesem web,
territory workerem i wskazanymi kontami testowymi. Manualną ścieżkę na serwerze
wykonuje użytkownik. Etap 2 rozpoczyna się dopiero po otrzymaniu wyniku i logów
z manuala; obejmuje analizę, poprawki w zakresie sprintu, pełną regresję,
cleanup serwerowego runtime i końcowy werdykt.

## Wynik Etapu 1

Etap przygotowawczy zakończono bez wykonywania manualnej ścieżki gracza:

* `verify = READY` przy jawnym profilu development,
* aktywny cykl `ghostnetwork_0001`, 20 części w stanie `pooled`, valid topology,
* `pending_effects = 0`, `unreconciled_effects = 0`, brak aktywnych reservations,
* dropy development włączone z `drop_chance = 0.25`, test mode wyłączony,
* telemetryka gotowa; przed manualem brak eventów jest stanem oczekiwanym,
* dry-run `reconcile` i `drain` zakończony bez planowanych efektów,
* naprawiono odczytowy audyt runtime i dodano jego test regresyjny,
* `test_target_persistence`: `221/221 OK` po odizolowaniu trwałych store'ów i
  aktualizacji historycznych asercji do obecnych kontraktów,
* celowana paczka runtime/telemetry/bridge/E2E: `17/17 OK`,
* `py_compile` i `git diff --check`: OK.

Lokalny wynik nie daje jeszcze zgody na manual: lokalnie nie działa territory
worker i nie ma właściwych kont. Manual zostaje przeniesiony na kontrolowany
serwer. Proces webowy i territory worker muszą działać z tym samym jawnym
profilem RC:

```powershell
$env:CHAOS_GHOSTNETWORK_RUNTIME_MODE='development'
$env:CHAOS_GHOSTNETWORK_DROPS_ENABLED='true'
$env:CHAOS_GHOSTNETWORK_DROP_CHANCE='0.25'
```

Nie ustawiamy `CHAOS_GHOSTNETWORK_TEST_MODE`; manual ma przejść naturalny roll
i normalny pipeline gameplayowy. Przed wdrożeniem wymagane są osobna zgoda na
commit/push/deploy, wskazanie docelowego hosta/procesów PM2 oraz nazwy kont
testowych. Etap 1B pozostaje `WAITING FOR SERVER ROLLOUT`.

## Etap 1B — serwerowy release candidate przed manualem

Serwerowy pre-flight wykonujemy bez modyfikowania gameplayu:

1. zanotować bieżący commit na serwerze, branch, procesy PM2 i ścieżkę bazy,
2. potwierdzić działanie procesu web oraz `territory_conflict_worker.py`,
3. wykonać spójny backup SQLite wraz z WAL/SHM,
4. wdrożyć dokładnie zatwierdzony commit RC; wszystkie procesy muszą raportować
   tę samą wersję,
5. ustawić trzy flagi GhostNetwork w lokalnym `ecosystem.config.js` dla weba
   i workera oraz pozostawić test mode wyłączony,
6. uruchomić testy składniowe i celowaną paczkę 130.9.1 na serwerze,
7. wykonać odczytowe `status`, `verify` i audyt runtime,
8. jeżeli brak cyklu, uruchomić najpierw dry-run `bootstrap`; `--apply` wymaga
   oceny planu i osobnej zgody operatorskiej,
9. wykonać dry-run `reconcile` i `drain`,
10. potwierdzić co najmniej jedno konto testowe z klanem/profesją i narzędziami
    mapowymi oraz konto/stan pozwalający przejść territory lifecycle,
11. zrestartować oba procesy przez istniejącą konfigurację PM2 z `--update-env`,
12. po restarcie ponownie uzyskać `verify = READY` i dopiero wtedy przekazać
    serwer do manuala.

Nie uruchamiamy przy tej okazji ogólnego cleanupu aplikacji, syncu katalogu ani
niezwiązanych migracji. Nie resetujemy istniejących kont. Jeżeli potrzebne jest
konto techniczne, tworzenie/reset musi być jawną, osobną operacją z backupem.

Rollback serwerowego RC: wyłączyć dropy, wykonać dry-run `drain`, w razie
pending effects zastosować kontrolowany drain/reconcile, zachować bazę do
analizy, przywrócić poprzedni commit i konfigurację PM2, zrestartować web oraz
workera i potwierdzić health. Backup bazy przywracamy wyłącznie przy potwierdzonej
korupcji lub nieodwracalnej mutacji, nie jako domyślny sposób wycofania kodu.

## Wynik manuala serwerowego i Etapu 2

Manual na serwerowym RC potwierdził rzeczywisty pipeline:

`map → aim → hack → capture → drop → discovery`.

Dwóch testerów otrzymało naturalny drop przy `drop_chance = 0.25`. Jeden drop
został potwierdzony logiem i deltą `ghost.part_discovered`; drugi został
potwierdzony przez testera, ale odpowiadający log nie był już dostępny po
odświeżeniu. Nie wymaga to ponownego manualnego dropu.

Frontend dla pierwszego discovery zgłosił recovery `reason=version_gap`.
Analiza wykazała, że `state_version` jest globalną wersją domenową, natomiast
nie każdy wewnętrzny event aim/reservation/reward jest publikowany jako delta
widoczna dla danego gracza. `ghost.part_discovered` może więc prawidłowo
przeskoczyć o więcej niż jeden numer. Klient w takim przypadku odrzuca częściową
deltę i pobiera autorytatywny `/api/ghostnetwork/snapshot`. Jest to oczekiwany,
bezpieczny fallback; nie znaleziono podstaw do przebudowy systemu delta.

Odczytowy `tools/audit_ghostnetwork_runtime_state.py` raportuje teraz dla każdej
odkrytej części liczbę discovery events, contributions, rewards, wpisów profile
history oraz applied capture effects. Etap 2 kończy się po uruchomieniu tego
raportu na serwerze i potwierdzeniu `discoveries.ok=true`, `count=2`, pojedynczych
efektów exactly-once oraz końcowego `verify=READY`.

Końcowa regresja lokalna po manualu:

* GhostNetwork: `144/144 OK`,
* territory/CAS/reconciliation/progression: `134/134 OK`,
* Target Registry, `/gonna-win`, receipts, delta/snapshot i profile w
  `test_target_persistence`: `221/221 OK`,
* celowane testy audytu i delta/recovery: `10/10 OK`,
* `py_compile` i `git diff --check`: OK.

Serwerowy audit po manualu potwierdził cykl `ghostnetwork_0001`, 20 części
(`18 pooled`, `1 public`, `1 contained`), dwa discovery, zero reservations,
pending i unreconciled effects, valid topology oraz `READY`. Obie części mają
po jednym discovery event, contribution, applied reward i applied capture
effect. Nie ma duplikatów.

Audit wykrył jednak `profile_history=0` dla obu testerów. Przyczyną był późny
pełny zapis profilu przez `/gonna-win`: reward coordinator zapisywał historię,
po czym wcześniej utworzony `UserProfileManager` nadpisywał profil starszą
kopią. Ledger i event `ghost.player_history_changed` pozostawały poprawne.

Poprawka chroni historię rewardów monotonicznie w `UserStore.save_profile()` i
pozwala `UserProfileManager` zachować dynamiczne pola GhostNetwork. `reconcile`
raportuje brakujące wpisy w dry-run, a `reconcile --apply` odtwarza wyłącznie
historię z applied ledger — bez ponownego RSP, contribution ani discovery.
Po poprawce: testy celowane `14/14`, GhostNetwork `144/144` oraz
`test_target_persistence` `221/221`. Ponowny manual drop nie jest wymagany.

Serwerowy `reconcile --apply` odtworzył dokładnie dwa brakujące wpisy historii
(`missing=2`, `repaired=2`). Ponowny audyt potwierdził dla obu części dokładnie
po jednym discovery event, contribution, applied reward, profile history i
applied capture effect; `discoveries.ok=true`, bez błędów. Końcowe verify nadal
zwraca `READY`, 20 części, valid topology i zero pending/unreconciled effects.

Do finalnego GO pozostaje wyłącznie walidacja dalszego lifecycle na istniejącej
części: raport pokazuje `1 contained`, `0 active` i pustą telemetrykę lifecycle,
więc nie ma jeszcze dowodu `contained → active → module progress`. Nie wymaga to
nowego dropu ani ponawiania ścieżki discovery.

## Cel

Zweryfikować GhostNetwork **na prawdziwym lokalnym runtime gry**, z użyciem normalnej ścieżki gracza:

`map`
→ `target`
→ `aim`
→ `hack`
→ `capture`
→ `GhostNetwork drop`
→ `discovery`
→ `territory`
→ `contained`
→ `active`
→ `module progress`

Sprint 130.9 udowodnił poprawność architektury i integracji testami automatycznymi.

Sprint 130.9.1 ma odpowiedzieć na inne pytanie:

**czy gracz faktycznie może wejść do gry i przejść tę ścieżkę bez żadnej ingerencji developerskiej w trakcie działania?**

Nie dodajemy nowych feature'ów.

Nie przebudowujemy GhostNetwork.

Nie zmieniamy kontraktów sprintów 110–130.

## Model wykonania

Pracę prowadzimy małymi, zamykanymi etapami. Każdy etap kończy się:

1. zapisaniem obserwacji lub odtworzeniem błędu,
2. minimalną poprawką wyłącznie wtedy, gdy test ujawni regresję,
3. testem celowanym na poprawiony kontrakt,
4. testem sąsiedniej integracji,
5. `git diff --check`,
6. aktualizacją checklisty i dokumentacji, jeżeli zmieniło się rzeczywiste
   zachowanie, procedura operatorska albo znane ograniczenie.

Nie cofamy zastanych lokalnych zmian i nie maskujemy błędu przez ręczną zmianę
danych. Przed edycją sprawdzamy `git status --short` oraz diff dotykanych
plików. Commit, push, deploy, restart serwera i mutacje poza lokalnym runtime
pozostają osobnymi decyzjami użytkownika.

## Kolejność i bramki etapów

Sprint wykonujemy w następujących bramkach:

* **Gate A — runtime:** `.1` musi zakończyć się `READY`; w przeciwnym razie
  zatrzymujemy gameplay i diagnozujemy runtime,
* **Gate B — drop:** `.2–.4` muszą potwierdzić naturalny aim, reservation,
  capture i dokładnie jedno discovery,
* **Gate C — lifecycle:** `.5–.7` muszą potwierdzić przejście pozytywne,
  cofnięcie stanu oraz recovery przez aktualny bridge terytorialny,
* **Gate D — durability:** `.8–.9` muszą potwierdzić retry/reconcile oraz
  usunąć zależność testów od kolejności,
* **Gate E — odbiór:** `.10–.13` obejmują obserwację drop-rate, pełną regresję,
  cleanup runtime, synchronizację dokumentacji i raport końcowy.

Nie przechodzimy do kolejnej bramki z niewyjaśnionym błędem poprzedniej.
Finding wymagający nowej mechaniki trafia do backlogu i nie rozszerza sprintu.

## Artefakty i dowody

Raport nie może opierać się wyłącznie na komunikacie UI. Dla każdego istotnego
przejścia zapisujemy skorelowane dowody z co najmniej dwóch warstw:

* wejście gracza lub event gameplayowy,
* rezultat API/read modelu,
* rekord repository albo trwały effect,
* telemetria z reason code,
* snapshot/delta widoczny dla UI.

Dowody identyfikujemy bez sekretów przez `cycle_id`, `operation_id`,
`target_id`, `part_id` oraz znaczniki czasu. Nie zapisujemy hidden topology,
tokenów sesji ani pełnych payloadów zawierających dane prywatne.

## Narzędzia techniczne

Do diagnostyki wykorzystujemy kanoniczne, wersjonowane wejścia operatorskie:

* `tools/ghostnetwork_runtime.py` — `status`, `verify`, domyślny dry-run
  `bootstrap`, `reconcile` i `drain`,
* `tools/audit_ghostnetwork_runtime_state.py` — odczytowy audyt pipeline i
  trwałych efektów.

Jeżeli podczas sprintu potrzebna jest powtarzalna diagnostyka, rozszerzamy
istniejący skrypt albo dodajemy mały skrypt w `tools/` z `--help`, czytelnymi
kodami wyjścia i bezpiecznym trybem odczytowym jako domyślnym. Nie zostawiamy
tymczasowych poleceń SQL ani jednorazowych skryptów poza repozytorium.

Skrypt mutujący musi wymagać jawnego `--apply`, rozpoznawać tryb środowiska,
drukować plan przed zmianą i nadawać się do ponowienia. Test gameplayowy nie
może używać narzędzia operatorskiego do sztucznego zaliczenia ścieżki gracza.

---

# 130.9.1.1 — Pre-flight runtime verification

Przed rozpoczęciem testów gameplayowych sprawdź stan GhostNetwork.

Wykonaj:

`python tools/ghostnetwork_runtime.py status`

oraz:

`python tools/ghostnetwork_runtime.py verify`

Oczekiwany stan:

* dokładnie 1 aktywny cykl,
* `cycle_id = ghostnetwork_0001` lub aktualny aktywny cykl,
* dokładnie 20 części,
* poprawna topology,
* `pending_effects = 0`,
* `unreconciled_effects = 0`,
* developerskie dropy aktywne,
* readiness = `READY`.

Jeżeli stan nie jest READY:

**nie rozpoczynaj testu gameplayowego.**

Najpierw ustal przyczynę.

---

# 130.9.1.2 — Gameplay smoke test

Uruchom normalnie aplikację i wykonaj test przez rzeczywisty interfejs gry.

Bez:

* ręcznych insertów do bazy,
* ręcznego tworzenia reservation,
* bezpośredniego wywoływania GhostNetworkService,
* wymuszania `part_id`,
* manipulacji statusami części.

Scenariusz:

1. zaloguj gracza,
2. otwórz mapę,
3. wybierz zwykły hackowalny target,
4. uruchom normalne narzędzie,
5. wykonaj hack,
6. zakończ capture,
7. sprawdź rezultat GhostNetwork.

Przy developerskim:

`drop_chance = 0.25`

wykonaj serię normalnych hacków do momentu pierwszego discovery.

Nie zwiększaj drop chance tylko dlatego, że pierwsze kilka prób nie da części.

---

# 130.9.1.3 — Obserwacja realnego drop pipeline

Podczas testu sprawdź telemetrykę 130.9.

Musimy widzieć faktyczne przejścia:

`aim`
→ `eligible`
→ `roll`
→ `reserved`
→ `capture`
→ `discovered`

oraz zatrzymania:

* `not_eligible`,
* `roll_missed`,
* `no_candidate_part`,
* `no_matching_reservation`,
* inne reason codes.

Po kilku hackach wykonaj krótkie zestawienie:

* liczba aim,
* liczba eligible,
* liczba rolli,
* liczba miss,
* liczba reservations,
* liczba captures,
* liczba discoveries.

To ma być pierwszy realny sanity check drop-rate.

---

# 130.9.1.4 — Pierwszy prawdziwy drop

Po uzyskaniu pierwszej części potwierdź:

* część istnieje w repository,
* status = `public`,
* jest przypisana do właściwego cyklu,
* posiada właściwy anchor/target,
* istnieje tylko jedna instancja discovery,
* contribution zostało naliczone dokładnie raz,
* reward został naliczony dokładnie raz,
* history została zmieniona dokładnie raz.

Następnie sprawdź:

* GhostNetwork snapshot,
* delta,
* API,
* warstwę/UI GhostNetwork.

Część musi być widoczna dokładnie zgodnie z istniejącym visibility contract.

---

# 130.9.1.5 — Territory lifecycle w prawdziwej grze

Doprowadź odkrytą część przez aktualny system terytorialny.

Nie wywołuj adaptera GN bezpośrednio.

Test musi przejść przez aktualne post-130 boundaries:

`ownership CAS`
→ `territory publication`
→ `GhostNetwork bridge`

Potwierdź:

`public`
→ `contained`

a następnie:

`contained`
→ `active`

zgodnie z istniejącymi warunkami gameplayowymi.

Po każdym kroku sprawdź:

* repository,
* event,
* delta,
* snapshot,
* module state.

---

# 130.9.1.6 — Module progress

Po przejściu części do `active` sprawdź rzeczywisty progress maszyny.

Oczekiwane:

`0/5`
→ `1/5`

dla właściwej maszyny / modułu.

Nie wystarczy sprawdzić wpisu w bazie.

Zweryfikuj także read model używany przez UI/API.

Jeżeli istnieje aktualizacja delty dla module progress, sprawdź jej publikację.

---

# 130.9.1.7 — Contest / release smoke test

Na tej samej części wykonaj co najmniej jeden realny przypadek cofnięcia lifecycle.

Przykład:

`active`
→ territory contested

lub:

`contained`
→ owner changed

lub:

`contained/active`
→ release

Sprawdź, czy GhostNetwork otrzymuje właściwy event z nowego systemu terytoriów i zmienia stan zgodnie z kontraktem.

Następnie doprowadź stan ponownie do poprawnego właściciela / stabilizacji i sprawdź recovery.

Celem nie jest pełny stress test konfliktów.

Celem jest potwierdzenie, że bridge działa również **w drugą stronę**, a nie tylko przy pozytywnej aktywacji.

---

# 130.9.1.8 — Crash / retry manual sanity check

Nie trzeba niszczyć runtime w losowych miejscach.

Wykorzystaj istniejące narzędzia diagnostyczne 130.9.

Zweryfikuj operatorsko:

`reconcile`

oraz dry-run:

`drain`

Jeżeli bezpieczne środowisko developerskie pozwala zasymulować pending effect:

1. pozostaw jeden efekt jako pending,
2. uruchom reconciliation,
3. wykonaj `drain --apply`,
4. sprawdź, czy efekt został wykonany dokładnie raz,
5. wykonaj drain ponownie.

Drugi drain powinien mieć:

`0 effects to apply`

lub równoważny stan.

---

# 130.9.1.9 — Legacy test_target_persistence

Sprint 130.9 ujawnił istniejący problem:

`test_target_persistence`

zależy od:

* kolejności testów,
* globalnego stanu,
* wcześniejszych side effectów.

To należy uporządkować przed deployem.

Znajdź wszystkie przypadki, które:

* przechodzą osobno,
* ale zawodzą w zbiorczej regresji,
* zależą od kolejności,
* zostawiają globalny state,
* wykorzystują współdzielony singleton/cache/storage.

Napraw izolację testów.

Nie zmieniaj produkcyjnego zachowania tylko po to, aby stary test był zielony.

Preferowane:

* właściwy setup/teardown,
* izolowana baza,
* reset global state,
* deterministic fixtures,
* brak zależności test A → test B.

Po naprawie cały `test_target_persistence` musi przechodzić niezależnie od kolejności uruchomienia.

---

# 130.9.1.10 — Drop-rate observation

Developerski drop chance wynosi obecnie:

`0.25`

Nie traktuj tego automatycznie jako wartości produkcyjnej.

Podczas manualnego testu zbierz pierwsze rzeczywiste dane:

* eligible aims,
* rolls,
* discoveries.

Nie próbujemy jeszcze robić pełnego balansu statystycznego.

Chcemy jedynie stwierdzić:

* czy 0.25 działa zgodnie z oczekiwaniem,
* czy gracz nie dostaje części absurdalnie często,
* czy discovery nie jest zbyt rzadkie do testowania.

Na końcu przygotuj rekomendację dla **osobnej decyzji deploymentowej**:

`recommended production drop range`

ale **nie zmieniaj produkcyjnego drop-rate bez decyzji**.

---

# 130.9.1.11 — Full regression

Po manualnej walidacji uruchom ponownie regresję.

Minimum:

* wszystkie `test_ghostnetwork*.py`,
* nowe testy Sprintu 130.9,
* `test_target_persistence`,
* Target Registry,
* `/gonna-win`,
* receipts,
* capture,
* ownership CAS,
* territory conflicts,
* reconciliation,
* delta,
* snapshot,
* rewards/profile integration.

Dodatkowo:

`py_compile`

oraz:

`git diff --check`

Nie uznawaj sprintu za GO, jeżeli testy przechodzą pojedynczo, ale zbiorczy suite pozostaje zależny od kolejności.

---

# 130.9.1.12 — Runtime cleanup

Po zakończeniu testów sprawdź:

* pending effects,
* unreconciled effects,
* failed effects,
* reservations,
* cycle integrity,
* parts count,
* topology.

Końcowe:

`verify`

musi zwrócić:

`READY`

Nie pozostawiaj runtime w stanie powstałym wskutek sztucznej symulacji awarii.

---

# 130.9.1.13 — Dokumentacja, skrypty i handoff

Po zakończeniu walidacji zsynchronizuj dokumentację z faktycznie sprawdzonym
runtime:

* `doc/game_play_180726.md` — status etapów, wynik i nierozwiązane findings,
* `doc/ghostnetwork_architecture.md` — tylko jeśli zmienił się kontrakt lub
  przepływ odpowiedzialności,
* `doc/ghostnetwork_endgame_runbook.md` — rzeczywiste komendy pre-flight,
  diagnostyki, cleanupu, rollbacku i recovery,
* `doc/project_journal.md` — data, zakres, testy, wynik i decyzja GO/NO-GO.

Sprawdź, czy wszystkie użyte kroki serwerowe są odtwarzalne z repozytorium.
Każda nowa komenda techniczna musi mieć opis wejścia, skutku, trybu dry-run,
kodu wyjścia i przykładu bez sekretów. Usuń zależność runbooka od wiedzy
przekazywanej wyłącznie ustnie.

Handoff zawiera:

* warunki startu lokalnego serwera i jawne wartości niesekretnych flag,
* komendy testów celowanych i pełnej regresji,
* wynik końcowego `status` oraz `verify`,
* listę zmienionych plików i uzasadnienie każdej poprawki,
* znane ograniczenia oraz findings odłożone poza sprint,
* procedurę przywrócenia bezpiecznego stanu: wyłączenie dropów, `drain`,
  `reconcile`/`verify`; bez kasowania cyklu i trwałych efektów.

---

# Acceptance criteria

Sprint 130.9.1 kończy się `GO`, jeżeli ręcznie z poziomu gry uda się potwierdzić:

`normal target`
→ `aim`
→ `eligible`
→ `roll`
→ `reservation`
→ `hack`
→ `capture`
→ `discovery`
→ `public`
→ `contained`
→ `active`
→ `module progress`

oraz:

* UI/API pokazuje poprawny stan,
* delta działa,
* reward jest exactly-once,
* contribution jest exactly-once,
* contest/release wpływa poprawnie na lifecycle,
* reconciliation nie tworzy duplikatów,
* `test_target_persistence` nie zależy już od kolejności,
* pełna regresja jest zielona,
* runtime kończy test jako `READY`.

Dodatkowo:

* wszystkie kroki operatorskie są odtwarzalne z wersjonowanych skryptów i
  runbooka,
* dokumentacja odpowiada kodowi oraz rzeczywistemu wynikowi testów,
* nie pozostają tymczasowe skrypty, ręczne poprawki SQL ani nieopisane flagi,
* istnieje raport dowodowy pozwalający odróżnić sukces UI od trwałego efektu,
* rollout/deploy nie został wykonany bez osobnej decyzji użytkownika.

---

# Poza zakresem

Nie wykonuj w tym sprincie:

* produkcyjnego deployu,
* commita bez naszej decyzji,
* finalnego ustalania balansu drop-rate,
* automatycznego startu kolejnego cyklu,
* nowych abilities,
* nowych nagród,
* nowych zasad terytorialnych,
* zmian lore,
* przebudowy GhostNetwork UI.

Jeżeli podczas manualnego testowania wykryjesz bug istniejącej ścieżki — napraw go.

Jeżeli potrzebna byłaby nowa mechanika — zapisz jako osobny finding.

---

# Definition of Done

Na końcu przedstaw raport:

## Gameplay

* liczba wykonanych hacków,
* eligible,
* rolls,
* reservations,
* discoveries,
* pierwszy realny drop,
* status części,
* przejście `public → contained → active`,
* wynik module progress.

## Runtime

* cycle id,
* parts total,
* statusy części,
* pending effects,
* unreconciled effects,
* topology,
* readiness.

## Exactly-once

Potwierdzenie:

* discovery,
* reward,
* contribution,
* history,
* reconcile/drain.

## Testy

Podaj wszystkie uruchomione zestawy i wyniki.

W szczególności osobno podaj wynik:

`test_target_persistence`

oraz pełnej regresji GhostNetwork.

## Kod

Podaj:

* zmienione pliki,
* przyczynę każdej dodatkowej poprawki,
* `git diff --stat`,
* `git diff --check`.

## Drop rate

Podaj obserwację developerskiego `0.25` i rekomendowany zakres do późniejszej decyzji produkcyjnej.

Nie ustawiaj go jeszcze jako produkcyjnego.

# Końcowy werdykt

Jeden z:

`GO — GhostNetwork validated in real gameplay`

albo:

`NO-GO — GhostNetwork runtime integration still has gameplay blockers`

Nie commituj.

Nie deployuj.


---

# GhostNetwork — Feedback Layer

GhostNetwork działa już na rzeczywistym serwerowym runtime:

* części naturalnie wypadają,
* części publiczne są widoczne na mapie,
* można je otaczać terytorium,
* lifecycle i integracja z post-130 runtime są aktywne.

Sprinty 110–130 powstawały jednak przed obecnym systemem SFX i przed częścią późniejszych efektów wizualnych CHAOS.

Dlatego przed przejściem do kolejnych mechanik GhostNetwork dokładamy brakującą warstwę feedbacku.

Te sprinty **nie zmieniają mechaniki GhostNetwork**.

Nie zmieniamy:

* drop rate,
* drop policy,
* eligibility,
* lifecycle,
* reguł containment,
* reguł activation,
* ownership CAS,
* rewards,
* topology,
* cycle state.

Pracujemy wyłącznie nad prezentacją istniejących stanów.

---

# Model realizacji Sprintów 130.9.2–130.9.4

Te trzy sprinty są sprintami presentation-layer i realizujemy je kolejno. Każdy
ma własny audyt, implementację, testy automatyczne, manualną bramkę w grze i
osobny werdykt. Nie łączymy ich w jeden niepodzielny pakiet zmian.

## Wspólny kontrakt pracy

1. Przed zmianą zapisz `git status --short` i przejrzyj istniejący diff. Nie
   cofaj ani nie nadpisuj zmian spoza bieżącego sprintu.
2. Najpierw ustal rzeczywiste źródło danych, istniejący renderer/player,
   snapshot, deltę, recovery, dedupe, layering i fallback. Dopiero potem wybierz
   najmniejszy punkt integracji.
3. Nie zmieniaj kanonicznego lifecycle ani danych gameplayowych dla potrzeb
   prezentacji. Frontend konsumuje authoritative state/event i nie wylicza
   własnej wersji prawdy.
4. Efekty jednorazowe uruchamiaj wyłącznie z nowego eventu/delty. Snapshot,
   initial load, reload i recovery odtwarzają stan trwały, ale nie transition ani
   SFX.
5. Każdy consumer musi być idempotentny: powtórzona delta nie może utworzyć
   drugiego markera, overlayu ani odtworzyć drugi raz dźwięku.
6. Błąd assetu lub presentation layer jest nieblokujący dla capture, territory,
   lifecycle, rewards, delty oraz GhostNetwork runtime.
7. Jeżeli do powtarzalnego sprawdzenia potrzebny jest stan serwerowy, dodaj lub
   rozszerz wersjonowany, read-only skrypt diagnostyczny. Nie twórz doraźnych
   poleceń modyfikujących bazę i nie resetuj `ghostnetwork_0001`.
8. Test manualny wykonuje użytkownik po jasnej bramce. Agent przygotowuje build,
   fixture/dev harness, instrukcję i oczekiwany wynik, ale nie uznaje oględzin za
   wykonane bez raportu użytkownika.
9. Po każdym sprincie uruchom testy celowane, właściwą regresję mapy/GN,
   `py_compile` dla zmienionych plików Python, kontrolę składni JavaScript oraz
   `git diff --check`.
10. Zaktualizuj tę specyfikację i `doc/project_journal.md`. Jeżeli zmienia się
    kontrakt eventów, assetów, delty lub renderera, zaktualizuj także właściwą
    dokumentację architektury/runbook.
11. Nie commituj i nie deployuj bez osobnego polecenia użytkownika.

## Wspólne statusy

Przed manualnym testem podaj dokładnie:

`READY FOR MANUAL GAMEPLAY TEST — Sprint 130.9.x`

Jeżeli sprint czeka na pliki użytkownika, podaj:

`READY FOR ASSET DELIVERY — Sprint 130.9.x`

Po manualu i finalnej regresji zakończ sprint jednym z werdyktów:

`GO — Sprint 130.9.x validated in real gameplay`

albo:

`NO-GO — Sprint 130.9.x still has presentation blockers`

`GO` wymaga testów automatycznych i manualnego potwierdzenia zachowania w grze.
Brak opcjonalnego assetu nie jest blockerem, jeżeli sprint jawnie dopuszcza
fallback; brak obowiązkowego assetu oznacza `READY FOR ASSET DELIVERY`, nie
fałszywe `GO`.

---

# Sprint 130.9.2 — GhostNetwork SFX

**Status:** `DONE / GO` (2026-08-21).

## Etapy realizacji

### Etap 1 — audyt i kontrakt

Udokumentuj istniejący przepływ `authoritative event → delta consumer → SFX
helper → registry → asset`, klucz dedupe i zachowanie przy snapshot/recovery.
Przed implementacją przygotuj tabelę `event → logical key → consumer → dedupe`.

### Etap 2 — implementacja bez finalnych assetów

Dodaj mappingi, hooki, dedupe i bezpieczny fallback. Testy mają używać mocka lub
testowego playera, a nie wymagać finalnych plików audio. Nie publikuj sztucznych
eventów gameplayowych tylko po to, aby uruchomić dźwięk.

### Bramka assetowa

Po implementacji podaj kompletny raport assetów i status:

`READY FOR ASSET DELIVERY — Sprint 130.9.2`

Użytkownik przygotowuje pliki audio. Po ich dostarczeniu sprawdź nazwy, format,
ścieżki, registry i brak 404/decode errors.

### Etap 3 — manual i domknięcie

Przygotuj krótki test w grze dla realnych przejść dostępnych w bieżącym cyklu.
Manual ma potwierdzić głośność względną, rozróżnialność, exactly-once oraz brak
audio przy reload/snapshot recovery. Nie wymagaj ponownego naturalnego dropu,
jeżeli istniejący event można bezpiecznie zweryfikować na aktualnej części.

## Cel

Podłączyć GhostNetwork do **istniejącego systemu SFX CHAOS**.

Nie buduj osobnego systemu audio dla GhostNetwork.

Nie twórz nowego registry, dispatchera, event busa ani warstwy audio, jeżeli obecna architektura tego nie wymaga.

Najpierw sprawdź, jak SFX działa już w projekcie, a następnie dodaj GhostNetwork dokładnie według istniejącego wzorca.

## Zakres

1. Przeprowadź krótki audyt istniejącego systemu SFX.

   Znajdź:

   * gdzie znajduje się obecny registry/katalog dźwięków,
   * gdzie znajdują się pliki audio,
   * jak nazywane są assety,
   * jak frontend uruchamia SFX,
   * jak inne moduły mapują zdarzenie na dźwięk,
   * czy istnieje wspólny helper/player,
   * czy istnieje cooldown,
   * czy istnieje dedupe,
   * jak rozwiązany jest brak assetu,
   * jak SFX wykorzystuje mapa,
   * jak SFX wykorzystuje OFS.

2. Wykorzystaj istniejącą architekturę.

   Jeżeli obecny system wymaga dopisania tylko:

   * kilku wpisów w registry,
   * kilku plików audio,
   * jednego hooka w konsumencie delty,

   to wykonaj tylko tyle.

   Nie projektuj nowego frameworka SFX dla GhostNetwork.

3. Dodaj obsługę zdarzenia odkrycia części.

   Preferowany logical asset key:

   `ghostnetwork.part_discovered`

   Dźwięk ma wystąpić przy rzeczywistym:

   `ghost.part_discovered`

4. Discovery SFX ma wystąpić dokładnie raz dla zdarzenia.

   Nie może zostać ponownie odtworzony przez:

   * reload strony,
   * ponowne otwarcie mapy,
   * snapshot,
   * snapshot recovery,
   * delta recovery,
   * ponowne wyrenderowanie istniejącej części.

5. Dodaj SFX dla przejścia części do `contained`.

   Preferowany logical asset key:

   `ghostnetwork.part_contained`

   Dźwięk informuje, że część została objęta właściwym stanem terytorialnym.

6. Dodaj SFX dla aktywacji.

   Preferowany logical asset key:

   `ghostnetwork.part_activated`

   Odtwarzany dopiero przy rzeczywistym:

   `contained → active`

   Ma być wyraźniejszy od `part_contained`.

7. Dodaj SFX dla stanu hostile / under fire.

   Preferowany logical asset key:

   `ghostnetwork.part_hostile`

   Zdarzenie dotyczy sytuacji, gdy terytorium obejmuje część obcego klanu i powstaje strategiczny stan zagrożenia.

8. Dodaj SFX utraty stanu.

   Preferowany logical asset key:

   `ghostnetwork.part_lost`

   Może odpowiadać utracie:

   * containment,
   * activation,
   * wymaganej stabilności terytorium.

9. Dodaj SFX postępu maszyny.

   Preferowany logical asset key:

   `ghostnetwork.module_progress`

   Odtwarzany tylko przy rzeczywistej zmianie postępu, np.:

   `1/5 → 2/5`

10. Dodaj SFX ukończenia maszyny/modułu, jeżeli istniejący runtime publikuje jednoznaczne zdarzenie tego typu.

    Preferowany logical asset key:

    `ghostnetwork.module_complete`

11. Podłącz istniejący końcowy event GhostSignal do SFX, jeżeli obecny kontrakt endgame daje odpowiedni event frontendowi.

    Preferowany logical asset key:

    `ghostnetwork.signal`

12. SFX musi być presentation effect.

    Brak pliku audio lub błąd playera nie może zatrzymać:

    * lifecycle,
    * delty,
    * mapy,
    * capture,
    * GhostNetwork.

13. Dedupe oprzyj o istniejące mechanizmy projektu, jeżeli już istnieją.

    Nie twórz drugiego systemu dedupe wyłącznie dla audio, jeżeli obecna architektura potrafi rozwiązać problem.

14. Jeżeli potrzebne jest lokalne zabezpieczenie przed replayem tego samego eventu, powinno być minimalne i ograniczone do presentation layer.

## Testy

Sprawdź:

1. `part_discovered` uruchamia właściwy SFX,
2. ten sam event nie odtwarza SFX dwa razy,
3. snapshot nie odtwarza discovery,
4. recovery po `version_gap` nie odtwarza discovery ponownie,
5. `contained` uruchamia właściwy SFX,
6. `active` uruchamia właściwy SFX,
7. hostile uruchamia właściwy SFX,
8. utrata stanu uruchamia właściwy SFX,
9. module progress nie odtwarza się bez zmiany progress,
10. brak pliku SFX nie powoduje błędu gameplayowego.

Dodatkowo uruchom regresję consumerów delta/snapshot, mapy, OFS SFX i
GhostNetwork lifecycle. Jeżeli istnieje wspólny test playera/dedupe, rozszerz go
zamiast tworzyć osobny harness wyłącznie dla GN.

## Raport assetów po sprincie

Na końcu Sprintu 130.9.2 **nie twórz za mnie finalnych plików audio**.

Na podstawie rzeczywiście istniejącej architektury CHAOS podaj listę assetów, które mam przygotować.

Dla każdego assetu podaj:

* logical asset key,
* dokładną nazwę pliku,
* format wymagany przez obecny system,
* dokładną ścieżkę docelową w repozytorium,
* zdarzenie, które go uruchamia,
* krótki opis charakteru dźwięku.

Format raportu:

```text
Asset:
Key:
Filename:
Target path:
Triggered by:
Suggested character:
```

Przykład struktury raportu — nazwy i ścieżki ustal dopiero po audycie kodu:

```text
Asset:
Key: ghostnetwork.part_discovered
Filename: ...
Target path: ...
Triggered by: ghost.part_discovered
Suggested character: ...
```

Nie wymyślaj ścieżek przed sprawdzeniem aktualnego systemu assetów.

## Definition of Done

Sprint jest zakończony, gdy:

* rzeczywiste eventy GN są podłączone do istniejącego systemu SFX,
* recovery i snapshot nie powodują ponownego audio,
* brak assetu nie wpływa na gameplay,
* istnieje konkretna lista plików audio, które mam przygotować,
* dla każdego pliku znam dokładną ścieżkę docelową.

Finalne `GO` wymaga dostarczonych assetów i manualnego odsłuchu. Bez assetów
sprint kończy etap implementacyjny statusem `READY FOR ASSET DELIVERY`, przy
zachowaniu sprawnego i przetestowanego fallbacku.

### Wynik rozpoczęcia sprintu

Audyt potwierdził jeden wspólny `window.GameSfx`, manifest v1, dedupe po
`event_id`, bezpieczny missing-asset fallback oraz live/catch-up gate nadrzędnego
state delta consumera. Dodano osiem logical keys i hook kanonicznych eventów GN.
Snapshot, reload i recovery omijają hook audio. Machine progress gra tylko przy
zmianie liczby aktywnych części.

Finding delivery został usunięty w ogólnym GhostNetwork publication bridge, bez
fan-outu specjalnego dla SFX. Resolver obsługuje `player`, `owner`, `clan` i
`public`; `internal/system` nie trafiają do klienta. `part_contained`,
`part_contested`, `machine_progress_changed` i `signal_sent` mają testowany live
delivery do właściwych odbiorców. Każdy odbiorca nadal otrzymuje indywidualny
viewer projection, a event części bez bezpiecznej projekcji jest pomijany bez
ujawnienia internal `part_id`. Dedupe zachowuje stabilny klucz per odbiorca.

### Wynik końcowy

Sprint został domknięty po dostarczeniu i walidacji wszystkich ośmiu finalnych
assetów MP3. Manifest `static/audio/sfx/manifest.v1.json` wskazuje istniejące,
niepuste pliki z prawidłowym nagłówkiem ID3 dla wszystkich logical keys:

* `ghostnetwork.part_discovered`,
* `ghostnetwork.part_contained`,
* `ghostnetwork.part_activated`,
* `ghostnetwork.part_hostile`,
* `ghostnetwork.part_lost`,
* `ghostnetwork.module_progress`,
* `ghostnetwork.module_complete`,
* `ghostnetwork.signal`.

Manual serwerowy potwierdził dokładnie jeden live SFX przy containment. Delivery
zachowuje visibility/projection contract i dedupe per odbiorca; eventy
`internal/system` nie są publikowane do klienta, a snapshot, reload i recovery
nie odtwarzają historycznego audio. Brak lub błąd assetu pozostaje nieblokującym
presentation failure.

Końcowa regresja 2026-08-21:

* GhostNetwork SFX/delta/lifecycle/module/territory/map: `58/58 OK`,
* wspólny player JS: `game_sfx contract ok`,
* składnia `static/js/terminal.js`: OK,
* komplet manifestu i MP3: `8/8 OK`.

`GO — Sprint 130.9.2 GhostNetwork SFX validated in live gameplay`

---

# Sprint 130.9.3 — GhostNetwork Territory Visual States

**Status:** `DONE / GO` (2026-08-21).

## Wynik Etapu 1–2

Backend nie wymaga zmiany kontraktu. Viewer projection już dostarcza kanoniczne
`module_state`, `territory_id` i `conflict_state`; frontend nie wylicza lifecycle
z geometrii ani ownership.

| Stan kanoniczny GN | Snapshot/delta | Dotknięte pole | Presentation |
| --- | --- | --- | --- |
| pozostałe / brak `territory_id` | projekcja części | brak | `normal`, bez klasy GN |
| `module_state=active` | projekcja części | `territory_id` | `ghostnetwork-territory-active` |
| `module_state=blocked` | projekcja części | `territory_id` | `ghostnetwork-territory-hostile` |

Stan jest agregowany po wszystkich widocznych projekcjach części; `hostile` ma
priorytet nad `active`. Klasa trafia na istniejący kanoniczny polygon Leaflet,
więc nie powstaje drugi overlay, a fill i stroke właściciela pozostają źródłem
informacji o ownership. ACTIVE używa zielonego pulse/glow, HOSTILE czerwonego
alarmowego glow z linią przerywaną. Oba efekty respektują
`prefers-reduced-motion`.

Snapshot GN, part delta oraz przebudowa snapshotu terytoriów korzystają z tego
samego rejestru i funkcji `refreshGhostTerritoryStates()`. Usunięcie, zmiana
territory, deaktywacja i pełny snapshot czyszczą stary stan. W trakcie testu
naprawiono również routing part delta, który mógł błędnie uznać ogólne
`payload.projection` za projekcję połączenia.

Automatyczna regresja:

* renderer JS: snapshot/delta, `normal/active/hostile`, priorytet wielu części,
  cleanup i territory rebuild — OK,
* kontrakt map/visibility/delta: `37/37 OK`,
* GN lifecycle/territory oraz Target Registry/conflict/multi-conflict/map loader:
  `178/178 OK`,
* składnia `static/js/map/ghostnetwork.js`: OK.

Sprint 130.9.3 does not require new external assets.

`READY FOR MANUAL GAMEPLAY TEST — Sprint 130.9.3`

### Finding manualny 2026-08-21 — territory action gate i stare markery MC

Manual potwierdził działanie efektu ACTIVE/HOSTILE, ale ujawnił dwa blockery:

* obiekt na terytorium wrogiego klanu można było zeskanować i oznaczyć przez
  ścieżki bez wspólnej bramki, a vulnerability omijało końcową blokadę hacku,
* przy włączonych kanonicznych conflict snapshots odpowiedź mapy nadal zawierała
  równoległe legacy `contested_targets`, więc drugi zestaw markerów przeżywał
  przebudowę rejestrów MC.

Serwerowa polityka blokuje teraz `scan`, `mark_target`, lekkie `aim` i
`hack-action` na aktywnym lub encircled terytorium wrogiego klanu. Ten sam klan
pozostaje relacją chronioną, a jedynym wyjątkiem ofensywnym jest cel rozwiązany
kanonicznie przez `find_contested_target()` dla aktywnego konfliktu. Sam status
vulnerability nie omija ochrony terytorium.

W snapshot mode backend nie publikuje już legacy `contested_targets`; markery
filarów/innerów pochodzą wyłącznie z kanonicznego snapshotu konfliktu, a pełny
refresh usuwa brakujące conflict/engagement IDs.

Regresja poprawki:

* action gate + MapAimTarget + hack idempotency: `42/42 OK`,
* conflict cutover/multi visibility/context: `41/41 OK`,
* wcześniejsza regresja territory/conflict: `74/74 OK`,
* `py_compile run.py` i renderer JS: OK.

Manual retest: próba `scan → mark → aim → hack` na zwykłym obiekcie wrogiego
terytorium ma zostać zablokowana; kanoniczny filar aktywnego konfliktu ma nadal
być atakowalny. Po rebuildzie/snapshot refreshu stare oznaczenia MC mają zniknąć.

### Wynik końcowego manuala

Użytkownik potwierdził po wdrożeniu, że poprawka działa prawidłowo:

* efekt ACTIVE/HOSTILE jest widoczny i reaguje na kanoniczny stan GN,
* zwykłe obiekty na terytorium wrogiego klanu nie omijają już blokady przez
  `scan → mark → aim → hack`,
* kanoniczna ścieżka konfliktowa pozostaje dostępna,
* stare oznaczenia multi-conflict znikają po przebudowie.

Snapshot, delta, reload/recovery i cleanup mają jedno źródło prezentacji, nie
powstają równoległe legacy markery, a kolor ownership pozostaje czytelny.

`GO — Sprint 130.9.3 GhostNetwork Territory Visual States validated in gameplay`

## Etapy realizacji

### Etap 1 — audyt danych i renderera

Zapisz macierz `kanoniczny stan GN → payload snapshot/delta → dotknięte
territory_id → klasa/warstwa presentation`. Potwierdź, że backend już dostarcza
informację wystarczającą do rozróżnienia `none/active/hostile`. Jeżeli nie,
dodaj minimalne pole projekcji z testem kontraktu, bez zmiany lifecycle.

### Etap 2 — implementacja i testy automatyczne

Dodaj stan do istniejącego rejestru warstw i aktualizacji inkrementalnej. Testy
muszą pokryć identyczny wynik snapshotu i delty, usuwanie starego efektu,
ownership change, brak duplikatów oraz layering. Preferuj fixture renderera lub
istniejący map harness; nie opieraj regresji wyłącznie na selektorach tekstowych.

### Etap 3 — manual mapy

Po automatycznej regresji zatrzymaj się na:

`READY FOR MANUAL GAMEPLAY TEST — Sprint 130.9.3`

Użytkownik sprawdza desktop i mobile oraz co najmniej: normal, active, hostile,
powrót do normal, reload i recovery. Raport powinien zawierać zrzuty ekranu lub
krótkie nagranie oraz informację o zoomie i schemacie mapy. Po manualu popraw
wyłącznie znalezione regresje z zakresu sprintu i wykonaj finalną regresję.

## Cel

Dodać na mapie czytelną informację o strategicznym stanie GhostNetwork terytorium.

Obecnie terytoria pokazują:

* właściciela,
* klan,
* kolor użytkownika/klanu,
* normalne stany konfliktowe.

Tego nie zmieniamy.

GhostNetwork ma być **dodatkową warstwą wizualną**, dzięki której od razu widać:

* zwykłe terytorium,
* terytorium z aktywną częścią,
* terytorium znajdujące się pod strategicznym zagrożeniem przez obcą część.

## Stany

1. Normal territory.

   Brak specjalnego strategicznego stanu GN.

   Terytorium wygląda dokładnie tak jak obecnie.

2. GhostNetwork active territory.

   Na terytorium znajduje się część właściwego klanu i lifecycle osiągnął:

   `active`

3. GhostNetwork hostile / under fire territory.

   Terytorium obejmuje część obcego klanu.

   Pole pozostaje własnością obecnego gracza/klanu, ale strategicznie znajduje się pod ostrzałem GhostNetwork.

## Implementacja

4. Najpierw sprawdź aktualny renderer terytoriów.

   Znajdź:

   * sposób nadawania kolorów,
   * SVG/Canvas/Leaflet layers,
   * style polygonów,
   * klasy CSS,
   * pane/layers,
   * delta update,
   * snapshot rebuild,
   * conflict presentation states.

5. Nie zastępuj obecnego koloru właściciela.

   Bazowy kolor nadal odpowiada na pytanie:

   `czyje jest to pole?`

6. GhostNetwork ma odpowiadać dodatkowo na pytanie:

   `co strategicznie dzieje się na tym polu?`

7. ACTIVE musi mieć dodatkowy efekt wizualny.

   Może to być, zależnie od obecnej architektury:

   * dodatkowy border,
   * glow,
   * pulse,
   * pattern,
   * overlay,
   * efekt linii.

   Wybierz rozwiązanie pasujące do istniejącego renderera.

8. HOSTILE / UNDER FIRE musi być wyraźnie inny od ACTIVE.

   Charakter powinien być bardziej:

   * ostrzegawczy,
   * niestabilny,
   * zagrożony,
   * alarmowy.

9. Można wykorzystać istniejący glitch/jitter/pulse używany już w mapie lub innych systemach, jeżeli pasuje.

10. Nie twórz nowego systemu animacji, jeżeli efekt już istnieje w CHAOS.

11. Stan wizualny musi wynikać z kanonicznego lifecycle GhostNetwork.

    Front nie może sam zgadywać, czy część jest aktywna.

12. Jeżeli potrzebny jest presentation state, może zostać przekazany jako coś w rodzaju:

```text
none
active
hostile
```

```
ale tylko jeśli pasuje to do istniejącego kontraktu danych.
```

13. Snapshot i delta muszą prowadzić do identycznego końcowego wyglądu.

14. Reload mapy musi poprawnie odtworzyć stan.

15. Recovery delty musi poprawnie odtworzyć stan.

16. Usunięcie strategicznego stanu musi usunąć efekt wizualny bez pozostawiania starych klas lub overlayów.

17. Nie twórz nowego pollera.

18. Nie przebudowuj wszystkich pól mapy przy pojedynczej zmianie GN, jeżeli obecna delta pozwala zaktualizować tylko dotknięte terytorium.

19. Efekt nie może przykrywać:

* markerów części,
* motocykla,
* konfliktów,
* ważnych markerów mapy.

## Wizualne przejścia do sprawdzenia

1. `normal → active`
2. `active → normal`
3. `normal → hostile`
4. `hostile → normal`
5. zmiana ownership przy obecnym stanie GN
6. reload mapy
7. snapshot recovery
8. delta update

## Testy

Sprawdź:

1. normal territory nadal wygląda jak wcześniej,
2. bazowy kolor właściciela nie znika,
3. active jest jednoznacznie rozpoznawalne,
4. hostile jest jednoznacznie rozpoznawalne,
5. active i hostile nie wyglądają tak samo,
6. stan znika po odpowiednim lifecycle event,
7. snapshot odtwarza poprawny wygląd,
8. delta odtwarza poprawny wygląd,
9. recovery nie pozostawia starej warstwy,
10. nie powstają duplicate overlays.

Regresja obejmuje również Target Registry, istniejące conflict overlays,
markery graczy/motocykla, schematy mapy używane na serwerze oraz delta/snapshot
recovery. Jeżeli backend payload się zmienia, dodaj test serializacji i
read-only diagnostykę pozwalającą wypisać strategiczny stan terytoriów.

## Raport assetów po sprincie

Jeżeli wybrany efekt wymaga nowych assetów graficznych, nie twórz ich za mnie.

Na końcu Sprintu 130.9.3 podaj dokładną listę potrzebnych plików.

Dla każdego podaj:

```text
Asset:
Purpose:
Filename:
Format:
Dimensions:
Target path:
Used by:
Transparency required: yes/no
Notes:
```

Jeżeli sprint można wykonać w całości istniejącym CSS/SVG bez nowych plików, napisz jednoznacznie:

`Sprint 130.9.3 does not require new external assets.`

Nie wymuszaj tworzenia assetów, jeżeli nie są potrzebne.

## Definition of Done

Gracz patrzący na mapę musi natychmiast rozróżnić:

* zwykłe terytorium,
* terytorium z aktywną częścią GN,
* terytorium pod ostrzałem przez obcą część GN,

a jednocześnie cały czas widzieć, do kogo należy pole.

DoD wymaga manualnego potwierdzenia czytelności. Testy DOM/CSS potwierdzają
kontrakt, ale nie zastępują oceny, czy ACTIVE i HOSTILE faktycznie da się szybko
rozróżnić w grze.

---

# Sprint 130.9.4 — GhostNetwork Part Visual Upgrade

**Status:** `READY FOR MANUAL GAMEPLAY TEST` (2026-08-21).

## Wynik Etapu 1 — kanoniczny kontrakt assetów

Audyt wykazał 20 semantycznie różnych części: cztery maszyny/klany po pięć
unikalnych `part_code`, nazw i `icon_key`. Wspólny obraz per machine usunąłby
tożsamość części, dlatego wymagane jest 20 indywidualnych PNG.

Dodano read-only eksporter:

```bash
python tools/export_ghostnetwork_part_assets.py
python tools/export_ghostnetwork_part_assets.py --db-path /path/to/chaos.db
python tools/export_ghostnetwork_part_assets.py --cycle-id ghostnetwork_0001
```

Eksporter łączy kanoniczny katalog z rzeczywistym `cycle_id` i `part_id` po
`part_code`; nie tworzy, nie resetuje i nie aktualizuje cyklu. Dla aktywnego
`ghostnetwork_0001` identyfikatory mają postać `ghostnetwork_0001_<code>`.

Wspólny kontrakt wszystkich plików:

* format: PNG RGBA z przezroczystością,
* rozmiar źródłowy: `128×128 px`, istotna sylwetka w safe area `108×108 px`,
* katalog: `static/images/ghostnetwork/parts/`,
* bez wypalonego tła, halo, ramki stanu i tekstu,
* bez osobnych wariantów `public/contained/active/hostile`; lifecycle nakłada CSS,
* finalny marker zachowa fallback obecnego symbolu, click/popup i pane 625.

| Part / machine | Part ID w cyklu 0001 | Filename | Visual subject |
| --- | --- | --- | --- |
| V1 Ledger Nexus / VIREX ORACLE | `ghostnetwork_0001_v1` | `v1_ledger_nexus.png` | cybernetyczny węzeł księgi i przepływów |
| V2 Backdoor Forge / VIREX ORACLE | `ghostnetwork_0001_v2` | `v2_backdoor_forge.png` | kuźnia z ukrytym portem serwisowym |
| V3 Mimicry Engine / VIREX ORACLE | `ghostnetwork_0001_v3` | `v3_mimicry_engine.png` | rdzeń projekcji z podwójną sylwetką |
| V4 Acquisition Drive / VIREX ORACLE | `ghostnetwork_0001_v4` | `v4_acquisition_drive.png` | napęd przejęcia z chwytającymi segmentami |
| V5 Probability Core / VIREX ORACLE | `ghostnetwork_0001_v5` | `v5_probability_core.png` | rdzeń prawdopodobieństwa i rozgałęzione trajektorie |
| E1 Breach Voice / ECHO LIBERTAS | `ghostnetwork_0001_e1` | `e1_breach_voice.png` | emiter przebijający zamkniętą osłonę |
| E2 Influence Relay / ECHO LIBERTAS | `ghostnetwork_0001_e2` | `e2_influence_relay.png` | przekaźnik fal narracyjnych |
| E3 Truth Lens / ECHO LIBERTAS | `ghostnetwork_0001_e3` | `e3_truth_lens.png` | wielowarstwowa soczewka ujawniająca rdzeń |
| E4 Resonance Beacon / ECHO LIBERTAS | `ghostnetwork_0001_e4` | `e4_resonance_beacon.png` | beacon z koncentrycznym sygnałem rezonansu |
| E5 Spark Chamber / ECHO LIBERTAS | `ghostnetwork_0001_e5` | `e5_spark_chamber.png` | komora iskrowa inicjująca łańcuch impulsów |
| P1 Mirage Projector / PHANTOM VEIL | `ghostnetwork_0001_p1` | `p1_mirage_projector.png` | projektor widma z przesuniętym odbiciem |
| P2 Glitch Reactor / PHANTOM VEIL | `ghostnetwork_0001_p2` | `p2_glitch_reactor.png` | pęknięty reaktor cyfrowych zakłóceń |
| P3 Paranoia Loop / PHANTOM VEIL | `ghostnetwork_0001_p3` | `p3_paranoia_loop.png` | zamknięta pętla fałszywych tropów |
| P4 Fracture Engine / PHANTOM VEIL | `ghostnetwork_0001_p4` | `p4_fracture_engine.png` | rozszczepiony silnik sieciowy |
| P5 Mirror Kernel / PHANTOM VEIL | `ghostnetwork_0001_p5` | `p5_mirror_kernel.png` | lustrzany rdzeń odbijający impuls |
| S1 Deep Sensor / SENTINEL AEGIS | `ghostnetwork_0001_s1` | `s1_deep_sensor.png` | głęboki sensor skanujący warstwy integralności |
| S2 Bastion Matrix / SENTINEL AEGIS | `ghostnetwork_0001_s2` | `s2_bastion_matrix.png` | modułowa matryca tarczy bastionu |
| S3 Restoration Engine / SENTINEL AEGIS | `ghostnetwork_0001_s3` | `s3_restoration_engine.png` | silnik rekonstrukcji składający segmenty |
| S4 Accord Relay / SENTINEL AEGIS | `ghostnetwork_0001_s4` | `s4_accord_relay.png` | dwa bezpiecznie spięte węzły przekaźnika |
| S5 Judgment Core / SENTINEL AEGIS | `ghostnetwork_0001_s5` | `s5_judgment_core.png` | rdzeń kwarantanny z izolującym pierścieniem |

Każdy wiersz ma logical key `ghostnetwork.part.<icon_key>`, dokładną ścieżkę
`static/images/ghostnetwork/parts/<filename>`, transparency `yes` i
`State variants required: no`.

Testy Etapu 1: eksport + katalog `15/15 OK`, `py_compile` eksportera — OK.

`READY FOR ASSET DELIVERY — Sprint 130.9.4`

## Wynik Etapu 2 — renderer PNG i lifecycle presentation

Dostarczono i zweryfikowano `20/20` finalnych plików: każdy ma dokładną nazwę,
`128×128 px`, PNG color type 6 (RGBA z kanałem alpha) i niezerowy rozmiar.

Jedno źródło kontraktu ścieżek znajduje się w
`ghostnetwork/part_assets.py`. Viewer projection v2 przekazuje
`visual_asset_key` i `visual_asset_url` wyłącznie wtedy, gdy
`identity_visible=true`; ukryta część nie ujawnia tożsamości nazwą pliku.

Renderer:

* używa indywidualnego PNG w istniejącym `ghostNetworkPartPane` 625,
* renderuje marker `54×54 px` na desktopie i `48×48 px` na mobile,
* zachowuje click/popup i ograniczony hitbox,
* po błędzie ładowania PNG pokazuje dotychczasowy geometryczny fallback,
* aktualizuje istniejący marker przy delcie zamiast tworzyć duplikat,
* PUBLIC ma subtelny CSS jitter, CONTAINED halo/pulse, ACTIVE stabilniejszy
  float/energy, a CONTESTED alarmowy warning,
* nie tworzy timera JavaScript per marker i respektuje reduced motion,
* containment/activation transition dodaje wyłącznie obsługa nowej live delty;
  snapshot, reload i recovery odtwarzają tylko stan trwały.

Walidacja Etapu 2:

* PNG dimensions/alpha/names: `20/20 OK`,
* GN asset/catalog/visibility/delta/lifecycle/territory/map/conflict:
  `124/124 OK`,
* renderer JS: OK,
* `node --check` i `py_compile`: OK.

Manual powinien sprawdzić public/contained/active/hostile, click/hover/popup,
kilka zoomów, desktop/mobile, reduced motion, reload/recovery oraz współdziałanie
z territory visual states 130.9.3.

`READY FOR MANUAL GAMEPLAY TEST — Sprint 130.9.4`

## Etapy realizacji

### Etap 1 — audyt katalogu i specyfikacja assetów

Przed zmianą renderera wygeneruj z kanonicznego katalogu pełne mapowanie 20
części do planowanych assetów. Jeżeli repo nie ma odpowiedniej diagnostyki,
dodaj read-only skrypt eksportujący `cycle_id`, `part_id`, `part_code`, clan,
machine/module i logical asset key. Skrypt nie może modyfikować cyklu.

Na podstawie audytu przygotuj listę PNG i zatrzymaj się na:

`READY FOR ASSET DELIVERY — Sprint 130.9.4`

Nie implementuj fikcyjnych nazw ani nie duplikuj placeholdera jako dwudziestu
rzekomo finalnych plików.

### Etap 2 — renderer, fallback i transitions

Po dostarczeniu assetów zweryfikuj wymiary, przezroczystość, nazwy i mapowanie,
a następnie zintegruj PNG z istniejącym markerem. Fallback musi pozostać
funkcjonalny. Trwały stan markera wynika ze snapshotu; jednorazowy transition
wyłącznie z nowej delty/eventu.

### Etap 3 — manual mapy i wydajność

Po testach automatycznych podaj:

`READY FOR MANUAL GAMEPLAY TEST — Sprint 130.9.4`

Manual obejmuje public/contained/active/hostile, click/hover/popup, kilka zoomów,
desktop/mobile, reduced motion, reload i recovery. Sprawdź również nakładanie z
territory visual states ze Sprintu 130.9.3. Po raporcie użytkownika napraw błędy
w zakresie sprintu i uruchom końcową regresję.

## Cel

Przebudować wizualnie samą część GhostNetwork na mapie.

Obecny marker jest zbyt mały i zbyt prosty jak na jeden z najważniejszych strategicznych obiektów gry.

Część ma:

* być większa,
* być oparta na PNG,
* być łatwo rozpoznawalna,
* posiadać efekt drżenia/jitter,
* wizualnie reagować na lifecycle,
* współgrać ze stanem terytorium.

## Audyt przed implementacją

1. Najpierw sprawdź obecny renderer części GhostNetwork.

2. Sprawdź katalog 20 części i sposób ich identyfikacji.

3. Sprawdź, czy części są logicznie pogrupowane według:

   * klanu,
   * maszyny,
   * modułu,
   * konkretnego `part_id`.

4. Sprawdź aktualny system assetów mapy.

5. Sprawdź istniejące efekty:

   * jitter,
   * shake,
   * pulse,
   * glitch,
   * glow.

6. W szczególności sprawdź efekty wykorzystywane już:

   * na mapie,
   * w OFS,
   * w innych elementach UI CHAOS.

7. Nie twórz nowego efektu drżenia, jeżeli odpowiedni już istnieje.

## PNG marker

8. Marker części ma korzystać z PNG.

9. Nie hardcoduj ścieżek PNG w wielu miejscach.

10. Mapowanie:

`part definition → visual asset`

powinno posiadać jedno źródło prawdy zgodne z obecną architekturą projektu.

11. Na podstawie realnego katalogu zdecyduj, czy właściwe jest:

* 20 indywidualnych PNG,
* zestaw PNG per machine,
* inny wariant wynikający bezpośrednio z istniejącego modelu.

12. Nie upraszczaj 20 różnych części do jednego assetu, jeżeli ich tożsamość ma znaczenie dla gracza.

13. Nie wymyślaj 20 assetów tylko dlatego, że istnieje 20 rekordów, jeżeli obecny design mówi inaczej.

14. Brak pliku PNG musi uruchomić istniejący/fallback marker zamiast ukrywać część.

## Rozmiar

15. Zwiększ rozmiar części względem obecnego markera.

16. Część ma być ważniejsza wizualnie od standardowego POI.

17. Rozmiar powinien zachowywać się sensownie przy różnych zoomach.

18. Marker nie może zasłaniać dużej powierzchni małego terytorium.

## Renderer

19. Renderer części powinien logicznie pozwalać na połączenie:

* PNG,
* glow/halo,
* lifecycle class,
* jitter/motion,
* transition effect.

20. Nie dodawaj informacji gameplayowych wyłącznie na potrzeby renderera.

## Jitter / drżenie

21. Część ma posiadać charakterystyczne lekkie drżenie.

22. Użyj istniejącego mechanizmu jitter/shake, jeśli istnieje.

23. Jeżeli kilka systemów posiada prawie identyczną implementację, można wydzielić minimalny współdzielony utility/class, ale bez dużego refaktoru animacji całej gry.

24. Jitter ma być subtelny.

25. Nie może wyglądać jak ciągły agresywny shake.

26. Preferowany jest lekko nieregularny efekt, jeżeli aktualny system animacji to umożliwia.

27. Animacja nie może wymagać osobnego timera JavaScript dla każdej części, jeżeli można wykorzystać CSS lub istniejący scheduler.

## Stan PUBLIC

28. `public` powinien wyglądać jak obiekt:

* odkryty,
* niezabezpieczony,
* niestabilny.

29. Preferowany charakter:

* lekki jitter,
* delikatny glow,
* subtelna niestabilność.

## Stan CONTAINED

30. `contained` musi być wizualnie inne od `public`.

31. Preferowany charakter:

* mocniejszy halo,
* pulse,
* zmiana intensywności,
* nadal obecne lekkie drżenie.

32. Przy rzeczywistym przejściu:

`public → contained`

można wykonać jednorazowy transition effect.

## Stan ACTIVE

33. `active` musi być najbardziej jednoznacznym stanem.

34. Preferowany charakter:

* mocniejszy/stabilniejszy glow,
* wyraźna energia,
* mniej chaotyczny jitter,
* jednorazowy activation pulse.

35. Przy:

`contained → active`

wykonaj wyraźny jednorazowy transition.

36. Nie odtwarzaj transition po reloadzie lub snapshot recovery.

## Hostile context

37. Jeżeli część znajduje się w hostile/under-fire context, marker może otrzymać dodatkowy warning presentation state.

38. Nie zmieniaj lifecycle części wyłącznie dla wyglądu.

## Klikalność

39. Sprawdź:

* click,
* hover,
* tooltip,
* popup,
* hitbox.

40. Powiększony PNG nie może zablokować kliknięć w nieproporcjonalnie dużym obszarze mapy.

## Layering

41. Sprawdź istniejące Leaflet pane / z-index / layer rules.

42. Część musi znajdować się:

* nad polygonem,
* nad GN territory visual effect,

ale bez łamania obecnego systemu warstw.

43. Nie używaj arbitralnych ekstremalnych `z-index`.

## Wydajność

44. Preferuj animowanie:

* `transform`,
* `opacity`.

45. Unikaj kosztownego ciągłego layout/reflow.

46. Delta nie może tworzyć nowego markera, jeśli może zaktualizować istniejący.

47. Snapshot recovery nie może zostawiać duplikatu.

48. Przy większej liczbie części renderer musi pozostać lekki.

## Reduced motion

49. Jeżeli istnieje wspólny mechanizm `prefers-reduced-motion`, respektuj go.

50. Nie twórz nowego frameworka accessibility tylko dla GhostNetwork.

## Testy

Sprawdź:

1. PNG ładuje się poprawnie,
2. brak PNG uruchamia fallback,
3. marker jest większy,
4. click działa,
5. hover działa,
6. tooltip/popup działa,
7. public ma prawidłowy presentation state,
8. contained różni się od public,
9. active różni się od contained,
10. jitter wykorzystuje istniejący mechanizm,
11. transition odpala się tylko przy realnej zmianie,
12. reload nie odpala transition,
13. snapshot recovery nie odpala transition,
14. delta nie tworzy duplicate marker,
15. pane/layering jest poprawne,
16. recovery pozostawia dokładnie jeden marker.

Dodatkowo sprawdź stabilność liczby warstw/markerów po serii delta → snapshot →
recovery oraz brak osobnych timerów JavaScript per marker. Jeżeli repo posiada
profiling mapy lub licznik layerów, wykorzystaj go i zapisz wynik w journalu.

## Raport assetów po sprincie

To jest obowiązkowy element Sprintu 130.9.4.

Po przeanalizowaniu rzeczywistego katalogu części przygotuj dla mnie **pełną listę PNG, które muszę stworzyć**.

Dla każdego assetu podaj:

```text
Part / machine:
Part ID:
Filename:
Target path:
Recommended dimensions:
PNG transparency:
Visual subject:
State variants required: yes/no
Notes:
```

Jeżeli jeden PNG jest współdzielony przez kilka części, wypisz dokładnie które.

Jeżeli potrzebne są osobne PNG dla wszystkich 20 części, przygotuj pełną listę 20 pozycji.

Jeżeli potrzebne są np. 4 lub 5 assetów bazowych, również podaj pełne mapowanie:

`part_id → filename`

Nie zostawiaj tego w formie ogólnego:

`assets should be created later`.

Po tym raporcie mam móc stworzyć pliki i wrzucić je do wskazanego katalogu bez szukania w kodzie, jak mają się nazywać.

Nie generuj PNG za mnie.

## Definition of Done

Sprint jest zakończony, kiedy:

* renderer obsługuje PNG,
* część jest większa,
* działa jitter,
* public/contained/active mają różne presentation states,
* transitions są event-driven,
* snapshot/recovery nie powtarzają efektów,
* nie ma duplicate markerów,
* istnieje kompletna lista PNG do stworzenia,
* każdy PNG ma podaną dokładną nazwę i ścieżkę docelową.

DoD nie może zostać oznaczone jako wykonane wyłącznie na placeholderach. Przed
dostarczeniem PNG prawidłowym wynikiem jest `READY FOR ASSET DELIVERY`; finalne
`GO` następuje po integracji realnych plików, manualu i regresji.

---

# Sprint 130.9.2.fix.all.1 — GhostNetwork Stability and Performance Recovery

## Status i powód otwarcia

**Status:** `IN PROGRESS — P0 and P1 DONE; remaining sprint gates pending`

**P0:** `DONE — server concurrency confirmed`

**P1:** `DONE — durable delivery and server performance gate confirmed`

**P2:** `DONE LOCALLY — stable renderer and bounded recovery; manual server gate pending`

Kolejny manual ujawnił nakładanie conflict/engagement polygonów oraz brak
tranzycji GN po otoczeniu przez właściwy klan. Pełny snapshot czyścił wyłącznie
legacy arrays, pozostawiając canonical Leaflet registries. Teraz przed
autorytatywnym renderem usuwa wszystkie front, pillar i engagement layers.
Audyt nie wykazał bezwarunkowego worker self-enqueue: no-op publication kończy
job, a multi audit ma lease i interwał.

Brak tranzycji GN miał niezależną przyczynę: territory publication budowała
identity map z `profile_json.username`. Realny profil nie musi duplikować loginu
z kanonicznej kolumny `users.username`, więc jego terytorium mogło zostać
pominięte. Publication i engagement audience korzystają teraz z
`list_profile_entries()`. Regresja: GhostNetwork `178/178 OK`,
conflict/engagement/abandon `48/48 OK`.

Drugi finding manuala dotyczył nieskonfliktowanego `Porzuć`. Rebuild nie
następował także po reload/logout/restart, ponieważ zwykły target ma zwykle
`ownership_version=0`, a deterministyczny job ID był ponownie używany po
capture→abandon tego samego obiektu. Stary rekord `complete` powodował
`ON CONFLICT DO NOTHING`: target znikał, lecz worker nie otrzymywał pracy.

Abandon job jest teraz związany z konkretnym durable capture row ID. Każde nowe
przejęcie otrzymuje inny rebuild receipt, a nieoczekiwana kolizja rollbackuje
delete. Dla geometrii osieroconej przed poprawką narzędzie
`repair_territory_visibility.py --username <login> --enqueue` zapisuje jawny
worker-owned recovery job; read path nadal pozostaje bez side effectów.

Manual serwerowy P2 potwierdził poprawny live event i SFX
`ghost.part_contained`, ale ujawnił blocker odświeżania polygonu. Kompaktowe
`territory.updated` nie zawiera vertices, a klient aktualizował istniejącą
warstwę tylko częściowym payloadem. Recovery było ograniczone do abandon i
encirclement, więc `pillar_captured`/`conflict_consolidation` stawały się
widoczne dopiero po ponownym otwarciu mapy.

Naprawa rozszerza istniejący publication contract: każda finalna publikacja area
sygnalizuje jeden debounced read-only snapshot pełnej geometrii. Pominięcie z
powodu in-flight albo abort ma bounded retry `0.9/1.8/3.5 s`; nie powstał nowy
poller. Regresja po findingu: capture/territory/map `247/247 OK`, GhostNetwork
`177/177 OK`, publication/recovery `40/40 OK`. Bramka manualna P2 pozostaje do
powtórzenia po wdrożeniu poprawki, bez resetowania cyklu.

## Server finding po pierwszym teście współbieżności — NO-GO

Test dwóch graczy ujawnił opóźnienie około pięciu minut; jeden profil z dużą
liczbą targetów potrzebował około dwóch minut. Logi rozdzieliły problem od GN:

* obie kolejki GN miały `depth=0`, bez failed jobs,
* GN snapshot trwał `262–1721 ms`, bez SQLite `locked/busy`,
* `/system-messages` zwracający `[]` trwał `11–35 s`,
* clan vulnerabilities trwało `7–23 s`,
* dokument `/map` miał `4.7 MB` dla `run`, ale aż `36.9 MB` dla `main`,
* player actors trwało `3.1–4.8 s`.

Root cause był złożony:

1. Folium generowało każdy target jako HTML, po czym pełne targety były ponownie
   osadzane w `profileData`; koszt dokumentu zależał od profilu.
2. Pusty system-message poll otwierał `BEGIN IMMEDIATE`, czyli globalny writer
   lock SQLite co 10 sekund dla każdego gracza.
3. „Read-only” profil pollerów nakładał runtime stores, a clan vulnerability
   używało synchronizacji zdolnej zapisać wielomegabajtowy profile JSON.
4. Player actors wykonywało N zapytań pending-contact dla każdego aktora.

Naprawa lokalna:

* targety/captured targets przeniesiono do lekkiego
  `/api/map/target-snapshot`; `/map` osadza wyłącznie mały boot profile,
* boot targetów renderuje markery z JSON zamiast server-side Folium,
* pusty system-message poll jest czysto odczytowy i nie pobiera writer locka,
* system-message poll nie czyta pełnego profilu, clan vulnerabilities nie
  nakłada ani nie zapisuje runtime stores,
* player actors pobiera pending-contact names jednym zapytaniem,
* map request nie zapisuje pełnego profilu do filesystem session.

Test regresyjny z `500` targetami i prywatnym payloadem potwierdza, że rozmiar
dokumentu mapy nie skaluje się z kolekcją targetów. Target snapshot przepuszcza
tylko jawnie dozwolone pola klienta.

Historyczny wynik `NO-GO` został zamknięty po wdrożeniu `984ba0f` i ponownym
teście dwóch graczy. Obie mapy otworzyły się w około 10 s. Dokument `/map`
zmniejszył się z `36.1 MB` do około `399 KB`, a sam endpoint odpowiadał w
`0.1–1.5 s`. GN snapshot mieścił się w `0.27–0.93 s`; nie odnotowano timeoutu
ani SQLite `locked/busy`. Wcześniejsza kontrola kolejek wykazała `depth=0` i
brak failed jobs. Manualna bramka wydajności P1 jest zaliczona.

Nieblokujące obserwacje do dalszego profilowania: player actors `2.96–5.72 s`,
pojedynczy target snapshot ciężkiego profilu `5.43 s` oraz pusty
system-message poll `2.45 s`. Nie powodowały już blokady ani wielominutowego
otwierania mapy.

## Stan wykonania — 2026-08-19

Zrealizowano pierwszy pakiet odzyskiwania stabilności:

* publikacje territory nie wykonują już synchronicznego GN reconcile,
  reward/endgame ani fan-out w Gunicornie,
* dodano trwałą, idempotentną kolejkę `ghostnetwork_territory_jobs` z lease,
  retry limit i stanem terminalnym `failed`,
* istniejący `chaos-territory-worker` jest jedynym konsumentem kolejki i przed
  konfliktem ponownie odczytuje kanoniczny snapshot,
* `sync_session_profile()` ma bezpieczny domyślny tryb odczytowy; rebuild
  pozostaje jawną operacją w ścieżkach mutacji,
* publikacja GN odczytuje profile jednym zapytaniem zamiast osobnego połączenia
  SQLite dla każdego ownera,
* `ghostnetwork_runtime status/verify/reconcile/drain` raportuje backlog kolejki,
  a `verify` blokuje GO przy terminalnych jobach `failed`.

Regresja lokalna: GhostNetwork `161/161 OK`, territory `121/121 OK`, pakiet
granicy request/worker oraz boot/delta `24/24 OK`, `test_target_persistence`
`221/221 OK`, `py_compile` i
`git diff --check` `OK`.

Drugi pakiet stabilizacyjny domknął kolejne wymagania Etapów 0–3 i 6:

* retry kolejki ma wykładniczy, ograniczony backoff oraz maksymalnie pięć prób,
* scheduler przepuszcza najwyżej jeden GN job przed conflict candidate, więc
  backlog GN nie zagłodzi podstawowego territory pipeline,
* diagnostyka kolejki raportuje depth, oldest age, stany oraz trwałe
  `processing_ms` p50/p95/max,
* `player_areas` otrzymało monotoniczną `publication_version` per owner;
  identyczna geometria nie jest kasowana/wstawiana ponownie, zachowuje ID i nie
  generuje fałszywej publikacji,
* encirclement aktualizuje tylko rekordy, których status naprawdę się zmienił,
  i podbija publication version dokładnie raz; ponowny odczyt nie powoduje
  zapisu ani churnu timestampów,
* krytyczny endpoint player areas pobiera profile właścicieli i intruderów
  zbiorczo, z fallbackiem wyłącznie dla brakującego rekordu, zamiast N+1
  połączeń SQLite,
* krytyczne `/map`, state changes i GN snapshot są objęte bezpiecznym timingiem
  bez logowania payloadu,
* dodano dynamiczne testy potwierdzające zero rebuild/bridge podczas read path,
* CLI rozdziela `capture-reconcile`, `reward-history-reconcile` oraz
  `territory-reconcile`; legacy `reconcile` nie wykonuje territory recovery.

Regresja po drugim pakiecie: GhostNetwork `168/168 OK`, territory `123/123 OK`,
`test_target_persistence` `221/221 OK`. Lokalne uruchomienie trzech procesów CLI
po regresji zostało chwilowo zablokowane przez Windows App Execution Alias
(`python.exe`: wygasła sesja logowania), nie przez kod aplikacji; kontrakt CLI
został zaimportowany i wykonany w testach jednostkowych.

Trzeci pakiet domknął P1 delivery/publication bridge:

* canonical GN event enqueue'uje jeden idempotentny
  `ghostnetwork_delta_delivery_jobs` zamiast wykonywać synchroniczny fan-out,
* job przechowuje wyłącznie bezpieczne viewer contexts, cursor i server-side
  internal snapshot; snapshot nie jest wystawiany klientowi,
* batch jest ograniczony (`25` domyślnie, twarde maksimum `100`) i wykonuje
  najwyżej jeden internal snapshot read dla całego eventu, także przy wielu
  batchach,
* częściowo wykonany batch jest retryowany z tym samym dedupe per odbiorca;
  lifecycle i reward nie są wykonywane ponownie,
* delivery, territory GN oraz zwykłe conflict jobs mają fairness i nie mogą się
  wzajemnie zagłodzić,
* `status/verify` raportuje osobno delivery depth/age/published/skipped/timing i
  blokuje GO przy terminalnym `failed`,
* restart odzyskuje wyłącznie zapisane pending jobs; nie skanuje historycznych
  eventów, więc snapshot/recovery nie odtwarza SFX.

Regresja kończąca P1: GhostNetwork `171/171 OK`, territory `124/124 OK`,
`test_target_persistence` `221/221 OK`; `py_compile`, składnia ecosystem/JS oraz
`git diff --check` `OK`.

P1 jest zakończone lokalnie i potwierdzone na serwerze równoległym testem dwóch
graczy. Zaobserwowany czas około 10 s spełnia bramkę gameplayową; próbka nie
jest laboratoryjnym pomiarem statystycznego p95, lecz nie wykazała timeoutów,
failed jobs ani ponownego wzrostu do 2–5 minut.

P2 ustabilizowało presentation consumer bez dokładania pollera lub zwiększania
timeoutów:

* niepełny albo starszy snapshot nie czyści ostatniej dobrej warstwy,
* równoległe żądania recovery współdzielą jeden request,
* brak projekcji uruchamia najwyżej jedno recovery zamiast dwóch,
* snapshot starszy od zaakceptowanej delty nie nadpisuje nowszego renderu,
* pending territory registry ma limit 20 części i usuwa wpis razem z markerem,
* zmiana cyklu czyści dedupe poprzedniego cyklu,
* snapshot/recovery pozostają poza live SFX gate.

Test behawioralny renderera pokrywa poprawny, niepełny i stary snapshot,
coalescing recovery oraz bounded cleanup. Regresja: GhostNetwork `177/177 OK`,
SFX/territory/worker `34/34 OK`, test JS renderera i GameSfx `OK`, składnia JS
oraz `git diff --check` `OK`.

Kod jest gotowy do manualnej bramki P2 na serwerze. Manual powinien potwierdzić
zachowanie części podczas `public -> contained -> public`, przejście
marker ↔ territory badge, brak znikania ostatniej dobrej warstwy przy przerwanym
recovery oraz brak SFX wywołanego samym snapshotem/recovery.

Sprint naprawczy zostaje otwarty po nieudanym manualnym domknięciu prezentacji
GhostNetwork. Objawy na serwerze:

* czas otwierania mapy wzrósł z około `4–12 s` do kilku minut,
* `player actors`, operacje i delta feed okresowo nie kończą requestów,
* części znikają lub zamieniają reprezentację po zmianie lifecycle,
* `public/contained/active` nie reagują stabilnie,
* live `ghost.part_contained` nie gwarantuje SFX,
* Gunicorn kończy workery oczekujące w kodzie SQLite/JSON po timeoutach lub
  restartach.

Priorytetem sprintu nie jest kolejny efekt wizualny. Priorytety są następujące:

1. stabilność istniejącej mapy i operacji,
2. odzyskanie czasu startu mapy,
3. poprawny i exactly-once lifecycle części,
4. dopiero potem delta, marker i SFX.

Sprinty `130.9.3` i `130.9.4` pozostają wstrzymane do czasu uzyskania końcowego
GO tego sprintu. Nie dokładamy PNG, jittera, territory overlays ani nowych SFX.

## Wynik audytu 130.9*

### P0 — GN wykonuje zapisujący globalny reconcile w ścieżkach webowych

Obecny przepływ:

```text
sync_session_profile / capture / abandon / rebuild
  -> rebuild_player_areas_with_territory_delta
  -> record_territory_areas_delta
  -> bridge_ghostnetwork_territory_publication
  -> list wszystkich player_areas
  -> odczyt profilu każdego ownera
  -> reconcile wszystkich 20 części z apply=True
  -> reward/endgame
  -> snapshot/projection/fan-out delta
```

`sync_session_profile()` nie jest komendą domenową GN. Jest używany także przy
zwykłym odczycie profilu i inicjalizacji UI. Po integracji 130.9 zwykłe otwarcie
mapy może więc uruchomić globalne mutacje GN. To narusza zasadę read path bez
side effectów i wiąże latencję mapy z całym runtime GN.

`record_territory_areas_delta()` łączy publikację podstawowej delty terytorium z
GN w jednym `try`. Błąd lub opóźnienie GN może sprawić, że wywołujący zobaczy
pusty wynik, mimo że podstawowa delta została już zapisana.

### P0 — web i territory worker konkurują o ten sam SQLite write path

GN reconcile może być uruchamiany zarówno przez proces webowy, jak i przez
`chaos-territory-worker`, ponieważ oba importują `run.py` i wywołują wspólne
funkcje publikacji. Gunicorn ma cztery procesy, worker jest piątym procesem.
Globalny reconcile, reward/profile save i delta fan-out otwierają kolejne
transakcje w tym samym pliku SQLite.

Kod nie ustanawia pojedynczego właściciela GN territory mutation ani durable
kolejki/coalescingu. Jest to najbardziej prawdopodobne wyjaśnienie wspólnego
timeoutu map actors, operacji i delta feed. Hipoteza musi zostać potwierdzona
pomiarami `elapsed_ms`, SQLite busy/locked oraz request p95 przed implementacją.

### P0 — worker nie ma procedury GN territory reconcile po wdrożeniu

`tools/ghostnetwork_runtime.py reconcile` uzgadnia capture outbox i reward
history. Nie wykonuje `reconcile_parts_with_territories()`.

`chaos-territory-worker` po starcie:

* odtwarza rollback targets,
* cyklicznie uzgadnia konflikty,
* audytuje multi-conflict,
* przetwarza rebuild/reconciliation jobs.

Nie wykonuje jawnego startup GN territory reconcile, nie posiada osobnej
durable kolejki GN i nie raportuje backlogu GN. Po deployu istniejące części
zmieniają stan dopiero przy przypadkowym kolejnym rebuildzie pola. Nazwa
operatorskiego `reconcile` tworzy obecnie fałszywe oczekiwanie.

### P1 — publication bridge korzysta z derived/legacy granic danych

`build_ghostnetwork_territory_publication()`:

* skanuje całe `player_areas`, choć trigger dotyczy zwykle jednego ownera lub
  jednego territory,
* dołącza clan przez pełny JSON profilu w Pythonie,
* miesza legacy display clan (`clan/fraction`) z canonical GN identity
  (`ghost_clan_code/clan_code`),
* tworzy `territory_state_version` przez hash `updated_at/id`, zamiast użyć
  monotonicznej wersji kanonicznej publikacji terytorium,
* traktuje materialized `player_areas` jak event source bez trwałego receiptu
  wskazującego konkretną wersję geometrii.

`player_areas` może pozostać źródłem geometrii do odczytu, ale GN mutation musi
być zasilana przez zakończony worker-owned publication/rebuild receipt, nie przez
profile sync ani dowolny renderer snapshot.

### P1 — błędne granice dedupe i transport version

Audyt wykazał:

* stały `source_event_id=reconcile:<cycle>` blokował kolejne legalne oscylacje
  `public -> contained -> public -> contained`,
* lifecycle zapisywał event, ale wynik adaptera nie niósł eventu do publication
  bridge,
* hidden viewer projection nie posiada internal `part_id`, a publisher próbował
  szukać części właśnie po nim,
* klient traktował luki globalnego GN `state_version` jako utratę transportu,
  mimo że `internal/system` oraz eventy innych odbiorców są celowo filtrowane.

W efekcie snapshot recovery czyścił warstwy przy poprawnych lukach domenowych,
a SFX zależał od eventu, który często nie docierał do state delta bus.

Te poprawki muszą zostać scalone w jeden testowany kontrakt, a nie wdrażane jako
niezależne łatki presentation layer.

### P1 — nieograniczony synchroniczny fan-out

Pierwsza wersja bridge wykonywała pełny internal snapshot osobno dla każdego
odbiorcy i osobne zapytanie `get_profile()` dla każdego konta. Nawet po
optymalizacji do jednego snapshotu indywidualne projekcje i zapisy delta nie mogą
pozostać częścią requestu mapy/capture.

Public/clan fan-out jest pracą workera. Musi mieć:

* bounded batch,
* trwały cursor/backlog,
* dedupe per odbiorca,
* metryki czasu i liczby odbiorców,
* retry bez ponownego lifecycle/reward.

### P2 — presentation naprawiało skutki zamiast źródła

Pending territory badges, CSS badge i wydłużanie timeoutów poprawiają wyłącznie
objawy. Nie mogą być kryterium zamknięcia sprintu, dopóki backend nie zapewnia
stabilnego snapshotu i live delta. Timeoutów nie wolno dalej zwiększać w celu
ukrycia blokady serwera.

## Docelowa granica odpowiedzialności

```text
WEB REQUEST
  commit capture / territory mutation
  record existing territory/map delta
  enqueue/coalesce durable GN territory publication job
  return response

TERRITORY WORKER (single writer for GN territory integration)
  claim completed canonical territory publication version
  read only affected territories plus parts in affected bounds/previous owner
  reconcile lifecycle exactly once
  persist canonical GN events/rewards
  enqueue/publish bounded per-viewer deltas
  acknowledge job

MAP READ PATH
  read snapshots only
  zero territory rebuild
  zero GN mutation
  zero reward/fan-out
```

Nie tworzymy osobnego workera SFX. Audio pozostaje presentation consumerem
istniejącej live delty.

## Etap 0 — freeze i reprodukowalny baseline

1. Wstrzymać implementację `130.9.3/130.9.4`.
2. Nie resetować cyklu `ghostnetwork_0001` ani 20 części.
3. Zachować aktualny stan i zebrać przed zmianą:

   * `pm2 status`, restarts, memory i CPU,
   * czasy `/map`, `/api/map/player-areas`, player actors, active operations,
     `/api/state/changes` i `/api/ghostnetwork/snapshot`,
   * Gunicorn `WORKER TIMEOUT`, request path i elapsed,
   * SQLite busy/locked oraz długość transakcji,
   * częstotliwość `sync_session_profile`, territory rebuild i GN reconcile,
   * liczbę snapshot reads, profile reads, delta writes i odbiorców na event.

4. Dodać read-only diagnostykę timing/query-count. Nie logować pełnych profili,
   ukrytych części ani topologii.
5. Porównać HEAD z ostatnim stabilnym pre-SFX/GN-publication baseline. Pomiar ma
   rozdzielić koszt podstawowej mapy od kosztu włączonego bridge.

## Etap 1 — odcięcie GN od read path i request latency

1. `sync_session_profile()` nie może wywoływać GN mutation ani globalnego
   territory publication. Docelowo również sam rebuild geometrii powinien być
   wyprowadzony z read path; jeżeli to większy zakres, minimum tego sprintu to
   brak GN side effectu podczas profile/map reads.
2. Rozdzielić `record_territory_areas_delta()` od GN. Sukces podstawowej delty
   nie może zależeć od GN.
3. Web po committed territory change tylko enqueue'uje trwały, idempotentny job.
4. Job identyfikuje canonical territory/publication version i affected IDs.
5. Wielokrotne rebuildy tej samej wersji muszą się coalesce'ować.
6. Żaden endpoint mapy, operacji, profilu ani delta polling nie może wykonywać
   `reconcile_parts_with_territories(apply=True)`.

Gate:

* test śledzący zero GN writes podczas GET map/profile/snapshot,
* request capture nie czeka na GN projection/fan-out,
* mapa wraca do budżetu przedregresyjnego.

## Etap 2 — worker-owned GN territory pipeline

1. Rozszerzyć istniejący `chaos-territory-worker`; nie tworzyć kolejnego
   specjalnego procesu.
2. Worker claimuje durable GN territory jobs po finalnej publikacji geometrii.
3. Reconcile ma być inkrementalny:

   * części w bounds zmienionego territory,
   * części wcześniej przypięte do tego territory,
   * pełny reconcile tylko jako jawna komenda recovery.

4. Lifecycle, reward i event są jedną logiczną operacją exactly-once.
5. Delta fan-out następuje po commit i jest retryable bez ponownej nagrody.
6. Backlog ma bounded batch oraz nie może zagłodzić conflict/rebuild jobs.
7. Worker raportuje:

   * queue depth,
   * oldest job age,
   * claimed/applied/skipped/failed,
   * lifecycle changes,
   * recipients i delta writes,
   * elapsed p50/p95/max.

8. Awaria GN nie zatrzymuje podstawowego territory worker loop; job pozostaje do
   retry z backoffem.

## Etap 3 — canonical data contract

1. Spisać jedno źródło dla:

   * ownership targetu,
   * finalnej geometrii pola,
   * territory publication version,
   * player GN clan identity,
   * lifecycle part status.

2. Nie odczytywać `profile.hacked` jako authority; capture authority pozostaje w
   `territory_target_ownership`/SQLite store, zgodnie z post-130 CAS.
3. `player_areas` jest materialized geometry read model. GN przyjmuje wyłącznie
   wersję opublikowaną przez worker po zakończeniu rebuilda.
4. Usunąć hash timestampu jako wersję. Użyć monotonicznego durable
   publication/geometry version.
5. Normalizować clan przez jeden canonical adapter GN; display names nie są
   kluczami domenowymi.
6. Nie kopiować bieżącego stanu GN do profilu. Profile history pozostaje
   projection exactly-once, zgodnie z 130.9.1.

## Etap 4 — lifecycle, delta i SFX

1. Pokryć sekwencje:

   * `public -> contained`,
   * `contained -> public`,
   * `public -> active`,
   * `active -> public`,
   * wielokrotne legalne oscylacje,
   * conflict freeze/resolution.

2. Każda rzeczywista tranzycja ma jeden nowy canonical event i jeden stabilny
   dedupe key. Retry tej samej tranzycji nie tworzy drugiego eventu.
3. Wynik worker reconcile niesie event do publication pipeline; nie skanujemy
   historii w poszukiwaniu „ostatniego” eventu.
4. Viewer projection wiąże hidden part przez publiczny, deterministyczny ID bez
   ujawnienia internal `part_id` lub exact coordinates.
5. Transport continuity należy do per-user delta bus. Globalny domain version
   może mieć luki po visibility filtering i nie wymusza recovery.
6. Snapshot/recovery nie odtwarza SFX. Wyłącznie zaakceptowana nowa live delta
   uruchamia audio.
7. Event bez bezpiecznej projekcji nie trafia do klienta. `internal/system`
   pozostają niewidoczne.

## Etap 5 — stabilny renderer

1. Snapshot jest autorytatywny, ale nie czyści ostatniej dobrej warstwy po
   timeout/abort/5xx/niepełnym payloadzie.
2. Delta aktualizuje marker po stabilnym `public_entity_id`; zmiana visibility
   nie może tworzyć drugiej tożsamości markera.
3. `territory_only` może korzystać wyłącznie z już widocznego polygonu i nie
   ujawnia exact part position.
4. Pending badge ma bounded registry i jest czyszczony po usunięciu części,
   zmianie cyklu oraz zamknięciu mapy.
5. Brak CSS/assetu daje widoczny lekki fallback, ale nie wpływa na lifecycle.
6. Nie dodawać nowego pollera ani timera per marker.

## Etap 6 — procedury workera po wdrożeniu

Worker ecosystem musi zachować jeden proces `fork`, interpreter `.venv`, cwd,
`PYTHONUNBUFFERED=1` oraz te same flagi GN co web. `TEST_MODE` pozostaje false.

Po deployu obowiązuje kolejność:

1. restart weba z wersjonowanego ecosystemu,
2. restart workera z `ecosystem.territory-worker.config.js`,
3. potwierdzenie dokładnie jednego workera i braku restart loop,
4. `status` oraz `verify`,
5. osobny read-only `territory-reconcile` dry-run pokazujący plan zmian części,
6. jawne enqueue/apply recovery tylko jeżeli dry-run wykrywa drift,
7. oczekiwanie na pusty GN territory queue i zero failed jobs,
8. ponowne `verify` oraz pomiar endpointów mapy.

Istniejącego `reconcile` nie wolno opisywać jako territory reconcile. CLI musi
otrzymać rozłączne nazwy, np.:

* `capture-reconcile`,
* `reward-history-reconcile`,
* `territory-reconcile --dry-run|--enqueue`,
* `drain` dla już zapisanych durable jobs/effects.

Startup workera nie może wykonywać nieograniczonego globalnego apply przed
rozpoczęciem pętli. Recovery jest jawne, mierzone i bounded.

## Budżety wydajności i testy

Budżety należy potwierdzić na kopii danych zbliżonej do serwera, a nie tylko na
pustej bazie testowej:

* otwarcie mapy: wraca do `<=12 s` w scenariuszu dotychczas mieszczącym się w
  `4–12 s`,
* `/api/state/changes`: p95 `<1 s`, bez seryjnych abortów,
* active operations i player actors: p95 `<3 s` przy otwartej mapie,
* GN snapshot: p95 `<2 s` dla 20 części,
* web request wykonuje zero full GN reconcile,
* jeden GN event wykonuje maksymalnie jeden internal snapshot read,
* public/clan fan-out jest poza requestem i ma bounded batch,
* brak `WORKER TIMEOUT` w teście obciążeniowym,
* brak wzrostu SQLite lock/busy względem baseline.

Automatyczna regresja obejmuje:

* wszystkie `test_ghostnetwork_*.py`,
* Target Registry i `test_target_persistence`,
* `/gonna-win`, receipts i capture CAS,
* territory conflict/rebuild/reconciliation,
* delta/snapshot/recovery,
* operations/player actors/map boot,
* rewards/profile history exactly-once,
* SFX live/dedupe/no recovery playback,
* worker restart/crash/backlog retry,
* query-count i timing harness,
* `py_compile`, `node --check`, `git diff --check`.

## Etapy manualne

### Manual A — stabilność i szybkość bez wymuszania dropu

Tester wykonuje kilka razy:

```text
login -> desktop -> map -> operations -> close -> reopen map
```

Raport zawiera czasy, console, Network waterfall i PM2/Gunicorn timing. Brak
części nie blokuje tego etapu; najpierw podstawowa mapa musi być stabilna.

Gate:

`READY FOR MANUAL PERFORMANCE TEST — Sprint 130.9.2.fix.all.1`

### Manual B — lifecycle istniejących części

Bez resetu cyklu tester zmienia geometrię tak, aby potwierdzić:

```text
public -> contained -> public -> contained
public/contained -> active -> public
```

Dla każdej tranzycji zapisuje marker, popup state/relation, event delta i SFX.
Nie wymagamy nowego naturalnego dropu.

Gate:

`READY FOR MANUAL GN LIFECYCLE TEST — Sprint 130.9.2.fix.all.1`

## Definition of Done

Sprint może otrzymać GO tylko wtedy, gdy:

* map/profile/operations read paths nie mutują GN,
* web nie wykonuje globalnego GN territory reconcile ani fan-outu,
* worker jest jedynym właścicielem GN territory integration writes,
* istnieje durable, bounded i obserwowalna kolejka,
* CLI rozróżnia capture/reward/territory reconcile,
* mapa wróciła do uzgodnionego budżetu,
* lifecycle oscyluje poprawnie exactly-once,
* public i ukryte części są stabilne po snapshot/delta/reload,
* live zmiana odtwarza dokładnie jeden SFX,
* recovery nie odtwarza SFX,
* pozostałe operacje mapy nie są zagładzane,
* pełna regresja i oba manuale przeszły.

Końcowy werdykt:

`GO — Sprint 130.9.2.fix.all.1 restored GhostNetwork stability and map performance`

albo:

`NO-GO — Sprint 130.9.2.fix.all.1 still has runtime or performance blockers`

Do GO nie wystarcza zielony unit test na małej bazie. Wymagane są pomiary na
serwerowym kształcie danych i manual gameplay.

## Wynik końcowy — 2026-08-20

Serwerowy hot sprint audit/fix otrzymuje GO. Manual z równoległym gameplayem
potwierdził stabilną mapę, poprawne przebudowy, lifecycle części oraz live SFX
containment. Ostatnia bramka writer-lock/GN została wykonana na wycinku logów
rozpoczętym od zapisanych offsetów PM2.

Porównanie runtime `przed -> po`:

* GN jobs: p50 `~2300 -> 2228 ms`, p95 `~8200 -> 3860 ms`, max
  `~19200 -> 3860 ms`,
* `events_rewards`: p95 `7295 -> 1710 ms`,
* `reward_repository_transaction`: p95/max `138 ms`,
* `upsert_aimed` hold max `2688 -> 1420 ms`,
* `upsert_operations` hold max `~1486 -> 522 ms`,
* worker: `13` jobów, `failures=0`, `busy=0`, jedno poprawne coalescing,
* kolejka po chwilowym backlogu wróciła do `depth=0`,
* log nie zawiera `database_contended`, `OperationalError` ani `Traceback`,
* web i `chaos-territory-worker` pozostały `online`.

Historyczne `processing_ms.p95=8215` i `max=19168` w diagnostyce kolejki są
agregatem obejmującym stare próbki sprzed naprawy. Wynik bieżącego okna pochodzi
z analizatora 13 nowych jobów i nie jest przez nie dyskwalifikowany.

Pozostałe koszty `audience_profiles` i `publication_read` są obserwowalne, ale
nie blokują tej bramki. Zgodnie z decyzją zamknięcia nie rozpoczynają kolejnej
rundy optymalizacji.

`GO — Sprint 130.9.2.fix.all.1 restored GhostNetwork stability and map performance`

Sprint 130.9.2 — GhostNetwork SFX jest domknięty: live containment odtwarza
SFX, delivery zachowuje visibility/dedupe, a snapshot/recovery nie odtwarza
historycznego dźwięku. Sprinty 130.9.3 i 130.9.4 zostają odblokowane.

---

# Kolejność realizacji

Realizuj kolejno:

1. Sprint 130.9.2.fix.all.1 — Stability and Performance Recovery.
2. Domknięcie Sprintu 130.9.2 — GhostNetwork SFX dopiero po GO fixa.
3. Sprint 130.9.3 — GhostNetwork Territory Visual States.
4. Sprint 130.9.4 — GhostNetwork Part Visual Upgrade.

Do czasu GO `130.9.2.fix.all.1` sprinty 130.9.3–130.9.4 są formalnie
wstrzymane, a 130.9.2 pozostaje ponownie otwarty jako blocker runtime.

Nie twórz własnych nowych subsystemów, jeżeli CHAOS posiada już odpowiedni mechanizm.

Najpierw audytuj istniejące rozwiązanie, potem wykonuj najmniejszą poprawną integrację.

Po każdym sprincie:

* uruchom testy celowane,
* uruchom potrzebną regresję mapy/GhostNetwork,
* zaktualizuj project journal,
* przygotuj listę wymaganych assetów i ich docelowych ścieżek,
* nie commituj,
* nie deployuj.

Jeżeli dany sprint nie wymaga nowych assetów, napisz to wprost.

Nie zatrzymuj się pomiędzy pracami automatycznymi z pytaniem o zgodę. Zatrzymaj
się wyłącznie na jawnej bramce manualnej, assetowej albo przy rzeczywistym
blockerze architektonicznym. Nie rozpoczynaj kolejnego sprintu, dopóki poprzedni
nie ma werdyktu `GO` albo użytkownik jawnie zaakceptuje odłożenie findingu.

---

# Końcowy oczekiwany efekt

Discovery:

`part discovered`
→ SFX discovery
→ większy marker części
→ PNG
→ jitter
→ stan `public`

Containment:

`public → contained`
→ SFX contained
→ transition części
→ contained visual state markera
→ odpowiednia warstwa terytorium

Activation:

`contained → active`
→ SFX activated
→ activation transition
→ active marker
→ active territory state
→ module progress SFX

Obca część:

`foreign part + territory`
→ hostile state
→ hostile SFX
→ hostile territory visual state
→ odpowiedni warning context markera części

Utrata stanu:

`active/contained → lost/contested/released`
→ odpowiednia zmiana visual state
→ SFX lost
→ bez pozostawienia starego overlayu lub markera.

---

# Końcowy raport

Po wykonaniu wszystkich trzech sprintów podaj:

1. zmienione pliki,
2. rzeczywiste miejsca integracji z istniejącym systemem SFX,
3. event → SFX mapping,
4. wykorzystany mechanizm audio,
5. wykorzystany istniejący jitter/shake,
6. presentation states części,
7. presentation states terytoriów,
8. sposób obsługi snapshot/delta/recovery,
9. wyniki testów,
10. `git diff --stat`,
11. `git diff --check`,
12. remaining findings.

Na samym końcu dodaj osobną sekcję:

# ASSETS TO CREATE

Podziel ją na:

## AUDIO

Dla każdego pliku:

```text
Filename:
Target path:
Used by:
Suggested character:
```

## PNG

Dla każdego pliku:

```text
Filename:
Target path:
Mapped to:
Recommended dimensions:
Transparency:
Visual description:
```

## OTHER

Tylko jeśli faktycznie są potrzebne inne assety.

Lista ma być kompletna.

Po jej otrzymaniu mam móc utworzyć wszystkie brakujące assety i wkleić je dokładnie we wskazane miejsca bez ponownego analizowania kodu.

Nie commituj.

Nie deployuj.


---


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
