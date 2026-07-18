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
