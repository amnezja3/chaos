# 138.getway — mapa profesja → gameplay realizer

Status: `PROPOSAL / DECISION ARTIFACT`

Ten artefakt przypisuje każdej z 20 profesji jedną główną rodzinę wpływu z
certyfikowanego katalogu `138.getway.0.4`. Nie jest jeszcze mapowaniem
produkcyjnym. Każdy wiersz staje się kontraktem dopiero po teście frontendowym
w odpowiednim podsprincie i decyzji `KEEP / ADJUST / REPLACE / DEFER`.

## 1. Granice rozwiązania

- jedna moc ma jedną główną rodzinę gameplayową;
- kilka mocy może używać tej samej rodziny, ale zawsze z identycznym zakresem,
  parametrami i skutkiem gameplayowym; różnić może się wyłącznie prezentacja;
- mapowanie `ability_code → family` jest statyczne i wyłącznie serwerowe;
- klient nie przesyła rodziny, mnożnika, limitu ani target scope;
- używamy wspólnego okna 15 minut, cooldownu 1 godziny, prezentacji, SFX,
  idempotencji, CAS i bounded telemetry z `138.getway.0`;
- nie powstaje interpreter efektów, plugin runtime, nowa kolejka ani worker;
- runtime nie czyta ciężkiego profilu. Eligibility korzysta wyłącznie z lekkich
  identity/capability projections, części, okna i właściwego canonical store;
- `file_value`, `actor_visibility` i `incident_decoy` pozostają `DEFERRED` i nie
  mogą wejść pod inną nazwą;
- efekt nie omija owner checks, target version, CAS, session generation,
  audience safety ani istniejących kalkulatorów wyniku;
- utrata aktywnej części zatrzymuje dalsze stosowanie mocy, zachowuje cooldown i
  nie cofa wcześniej zatwierdzonych mutacji.

Przed wdrożeniem `.1.2` aktywne okno porównuje token aktywacji części
`last_activated_at` z czasem utworzenia okna. Dzięki temu utrata i ponowne
odzyskanie części nie wskrzesi starego okna. Nie używamy do tego
`source_state_version`, ponieważ jest wersją całego cyklu i unieważniałby moc po
niezwiązanym zdarzeniu świata.

## 2. Certyfikowane rodziny

### Nadrzędny invariant rodziny

Po uzyskaniu `SERVER E2E PASS` rodzina realizera jest jednym, niepodzielnym
kontraktem gameplayowym. Każda profesja przypisana do tej rodziny otrzymuje
dokładnie ten sam call-site, zakres celu, sposób mutacji, limity, mnożniki,
semantykę expiry/part-loss oraz dowód działania w UI. Przykładowo wszystkie
przypisania `operation_risk` używają `heat -15`, wszystkie przypisania
`operation_speed` używają `clamp(0.1 × LVL, 1, 20)`, a wszystkie przypisania
`target_security` wyłączają pełny boolean security bar i pozostawiają kropki.

Profesja i część zmieniają wyłącznie warstwę narracyjną: nazwę mocy, tagline,
opis, asset, SFX, etykietę efektu i kolor klanu. Klucze polityk per
`ability_code` mogą istnieć technicznie dla routingu, telemetry i prezentacji,
ale muszą być aliasami tych samych parametrów rodziny i nie mogą służyć do
strojenia profesji osobno.

Zmiana parametru, limitu, zakresu celu albo zachowania dla jednej profesji
oznacza utworzenie nowej nazwanej rodziny lub nowej wersji kontraktu oraz pełną
ponowną certyfikację wszystkich jej przypisań. Nie wolno wprowadzać takiej
różnicy jako „polityki profesji”. Dzięki temu kolejne podsprinty są montażem
przetestowanego realizera, a nie tworzeniem nowych odmian gameplayu.

| Rodzina | Zamrożona granica techniczna |
| --- | --- |
| `operation_speed` | do 8 aktywnych operacji, jednorazowy marker, mnożnik `clamp(0.1 × LVL, 1, 20)` |
| `file_yield` | dokładnie 2 kopie każdego bazowego pliku GX (`backup`, `fullbackup`), stabilne ID; operacja oznaczona w oknie zachowuje bonus do finalizacji |
| `data_quality` | każdy plik finalizowanej operacji: bazowo `quality/completeness +10`; kategorie misyjne mocy mogą dostać `+30`; clamp `0–100`, maks. 16 plików na operację |
| `hack_actions` | cztery action dots ustawione jako wykonane; security i wynikający z niego pasek rozbrojenia bez zmian |
| `target_security` | exact target i CAS; polityki E1, E5 i P2 wyłączają cały boolean security bar, pozostawiając action dots |
| `operation_risk` | bounded wejście `heat -15`; kalkulator nadal wyznacza wynik i progi |
| `scan_range` | bounded zasięg wywołania skanu, bez account/global scan i bez zwiększania lokalnego promienia wyników; polityka E4: `min(10 000 km, 25 km × LVL)` |
| `map_zoom` | proporcjonalny boost odejmowany od zwykłego `min_zoom`; kotwice efektu: LVL `1→17`, `9→13`, `10→12`, `50→7`, `100→6`, `200+→5`; cap oddalenia `5` |
| `territory_defense` | jedno zgłoszenie publikuje obrys tego samego serwerowego skanu: 1–3 punkty w całości, większy scan maks. 8 punktów; sojusznik przejmuje cały rój jednym hakiem, wróg tylko jeden punkt i uruchamia alarm; filary i ich security bez zmian |

Limity powyżej były punktami startowymi do chwili certyfikacji. Po certyfikacji
nie wolno ich zmieniać w podsprincie profesji. Każda zmiana limitu lub scope
wymaga wersjonowania rodziny i ponownej wspólnej certyfikacji.

## 3. Proponowane mapowanie 20 profesji

### 3.1 VIREX ORACLE

| Sprint | Część / profesja | Moc | Rodzina | Widoczny skutek i początkowy scope | Ocena |
| --- | --- | --- | --- | --- | --- |
| `.1.1` | V1 Ledger Nexus / `broker` | Insider Feed | `operation_speed` | istniejące i nowe operacje przyspieszone `0.1 × LVL`, cap `20×`, maks. 8 | `LOCKED / SERVER PASS` |
| `.1.2` | V2 Backdoor Forge / `architect` | Wejście Serwisowe | `hack_actions` | cel obecny przy aktywacji oraz każdy cel oznaczony w 15-minutowym oknie natychmiast dostaje cztery kropki; zabezpieczenia pozostają | `LOCKED / SERVER PASS` |
| `.1.3` | V3 Mimicry Engine / `manipulator` | Fałszywy Obraz | `operation_risk` | istniejące i nowe aktywne operacje mają `heat -15`; jeden lekki odczyt okna na gracza/tick, widoczny maskowany risk | `LOCKED / SERVER PASS` |
| `.1.4` | V4 Acquisition Drive / `profit_enforcer` | Wrogie Przejęcie | `file_yield` | każda operacja dotknięta w oknie zachowuje wyróżnienie i przy finalizacji tworzy `oryginał + backup + fullbackup` każdego bazowego pliku GX | `LOCKED / SERVER PASS` |
| `.1.5` | V5 Probability Core / `algorithm_curator` | Predykcja Operacyjna | `operation_speed` | dokładnie ten sam certyfikowany realizer, mnożnik i cap co V1; odrębny wyłącznie UX V5 | `LOCKED / SERVER E2E PASS` |

`false_image` nie używa `incident_decoy`: obraz zastępczy jest opowiedziany przez
overlay i obniżenie heat, bez fałszywych globalnych rekordów. V4 nie tworzy
gotowych paczek. `backup` i `fullbackup` są osobnymi kopiami tego samego materiału,
a istniejący Ghost Exchange sam składa je z oryginałem w paczki sprzedażowe.
V5 nie używa `operation_risk`: ta rodzina pozostaje domeną V3. Probability Core
ponownie wykorzystuje pełny kontrakt `operation_speed` z V1. Techniczny klucz
V5 jest aliasem tych samych parametrów; różni się wyłącznie prezentacją.

### 3.2 ECHO LIBERTAS

| Sprint | Część / profesja | Moc | Rodzina | Widoczny skutek i początkowy scope | Ocena |
| --- | --- | --- | --- | --- | --- |
| `.2.1` | E1 Breach Voice / `hacktivist` | Ujawnienie | `target_security` | cały pasek boolean security aktualnego i każdego kolejnego celu `aimed` w oknie zostaje wyłączony; cztery action dots pozostają do wykonania | `LOCKED / SERVER E2E PASS` |
| `.2.2` | E2 Influence Relay / `social_engineer` | Przejęcie Narracji | `operation_risk` | istniejące i nowe aktywne operacje mają `heat -15`; wynik nadal wyznacza standardowy risk engine | `LOCKED / SERVER E2E PASS` |
| `.2.3` | E3 Truth Lens / `revealer` | Pełne Ujawnienie | `data_quality` | każdy plik operacyjny `+10/+10`; `camera`, `audio`, `network`, `personal` dostają `+30/+30`; maks. 16 plików na operację | `LOCKED / SERVER E2E PASS` |
| `.2.4` | E4 Resonance Beacon / `visionary` | Beacon Oporu | `scan_range` | przez 15 minut gracz aktywujący może wywołać skan do `min(10 000 km, 25 km × LVL)` od motocykla; lokalny promień wyników pozostaje `300 m` | `LOCKED / SERVER E2E PASS` |
| `.2.5` | E5 Spark Chamber / `igniter` | Efekt Domina | `target_security` | aktualny i każdy kolejny cel `aimed` w oknie ma wyłączony cały pasek security; cztery action dots pozostają do zhakowania | `LOCKED / SERVER E2E PASS` |

E2 wykorzystuje pełny certyfikowany w V3 realizer `operation_risk`. Techniczny
klucz `narrative_takeover` jest aliasem rodziny. Modyfikator wynosi `heat -15`
i obejmuje operacje istniejące oraz nowe w 15-minutowym oknie. Nie wymusza
detekcji ani jej braku: ostrzeżenia i incydenty nadal wyznacza standardowy risk
engine. E2 nie może być strojone niezależnie od V3 ani innych przypisań rodziny.

E5 korzysta z tego samego canonical `aimed` hooka i pełnego wariantu
`target_security`, który został sprawdzony przez E1. Nie mutuje niewybranego
sąsiedniego markera i nie wymaga utrwalania postępu wielu celów. Efekt domina
powstaje przez szybkie przechodzenie gracza przez serię celów A → B → C w
15-minutowym oknie. E4 nie wzmacnia całego klanu w pierwszej wersji, bo
wymagałoby per-recipient reads; wspólnotowy charakter zapewnia prezentacja.

### 3.3 PHANTOM VEIL

| Sprint | Część / profesja | Moc | Rodzina | Widoczny skutek i początkowy scope | Ocena |
| --- | --- | --- | --- | --- | --- |
| `.3.1` | P1 Mirage Projector / `illusionist` | Węzeł Widmo | `operation_risk` | istniejące i nowe aktywne operacje mają `heat -15`; standardowy risk engine nadal wyznacza wynik | `LOCKED / SERVER E2E PASS` |
| `.3.2` | P2 Glitch Reactor / `virologist` | Glitch Injection | `target_security` | cały boolean security bar aktualnego i każdego kolejnego celu `aimed` zostaje wyłączony przez CAS; cztery kropki pozostają | `LOCKED / SERVER E2E PASS` |
| `.3.3` | P3 Paranoia Loop / `paranoid` | Fałszywe Tropienie | `scan_range` | identycznie jak E4: `25 km × level_snapshot`, cap `10 000 km`, bez teleportu i bez zmiany lokalnego fetch radius | `LOCKED / SERVER E2E PASS` |
| `.3.4` | P4 Fracture Engine / `network_splitter` | Pęknięcie Sieci | `map_zoom` | przez 15 minut strategiczny zoom-out: od miasta na LVL 10, przez kraj i Europę, do całego świata na LVL 200+ | `KEEP / LOCKED / SERVER E2E PASS` |
| `.3.5` | P5 Mirror Kernel / `mirror_judge` | Odbicie | `territory_defense` | jedno zgłoszenie wystawia publiczny, geometryczny rój maks. 8 podatności; sojusznik przejmuje cały rój jednym hakiem, wróg pojedynczy punkt i uruchamia alarm; satelity wygasają przy końcu cooldownu | `LOCKED / SERVER E2E PASS` |

P1 nie tworzy fałszywego markera, P3 nie wykonuje skanu niezależnego od pozycji,
a P5 nie mutuje filarów; relację klanową odczytuje dopiero canonical capture/alarm
roju, bez account scan. To świadome bezpieczne zamienniki rodzin
`incident_decoy` i `actor_visibility`. Jeżeli efekt nie obroni się w grze,
wybieramy `REPLACE` albo `DEFER`, bez rozszerzania ciężkiego runtime.

P1 wykorzystuje dokładnie ten sam certyfikowany kontrakt `operation_risk` co V3
i E2. Klucz `phantom_node` jest technicznym aliasem. Modyfikator `heat -15` obejmuje
operacje istniejące przy aktywacji oraz nowe, rozpoczęte w 15-minutowym oknie.
Nie powstają fałszywe incydenty, markery świata ani skan aktorów. Widocznym
dowodem jest turkusowe wyróżnienie kart, `WĘZEŁ WIDMO` i `RUCH POZORNY`.

P3 wykorzystuje dokładnie ten sam certyfikowany kontrakt `scan_range` co E4.
Klucz `false_tracking` jest aliasem routingu i UX; nie zmienia mnożnika, capu,
scope, expiry ani call-site. Różnicę klanową stanowią wyłącznie nazwa, tagline,
asset, SFX i paleta Siatki Widmo.

P2 wykorzystuje dokładnie ten sam pełny kontrakt `target_security` co E1/E5.
Klucz `glitch_injection` jest technicznym aliasem. Wyłącza wszystkie aktywne flagi
boolean security dokładnego celu przez CAS, ustawiając pasek na 100%.
Nie zmienia `actions_allowed`, liczbowego `security_level` ani celów sąsiednich.
Każdy cel dotknięty w aktywnym oknie zachowuje zmianę; po expiry lub utracie
części nowe cele nie są już modyfikowane.

P4 definiuje `map_zoom` jako boost istniejącej progresji, a nie skok kamery.
Backend najpierw liczy zwykły `min_zoom(level)`, a następnie odejmuje interpolowany
`p4_zoom_out_bonus(level_snapshot)`. Kotwice bonusu to LVL `1→1`, `9→3`,
`10→4`, `50→7`, `100→8`, `200+→9`; wynik ma cap `min_zoom=5`.
Daje to efektywne punkty kalibracyjne `1→17`, `9→13`, `10→12`, `50→7`,
`100→6`, `200+→5`. Efekt trafia do serwerowego `min_zoom` przed utworzeniem
mapy Folium, więc mapa i warstwa kafelków otrzymują ten sam zakres. Frontend nie
wylicza zoomu i nie wywołuje `fitBounds`, `fitWorld`,
`setView` ani `panTo`: po 6-sekundowym show prezentuje narracyjny handoff
`AKTYWACJA DODATKOWYCH SATELIT` z dużym impulsem rozszerzającego się zoomu,
a następnie przeładowuje dokument mapy z zachowaniem aktualnego kadru. Naturalny
reload jest finałem efektu wizualnego P4 i nie powtarza się na już przebudowanej
mapie. Gracz sam decyduje, czy i kiedy oddalić widok. Przez aktywne
okno standardowy auto-return zoomu jest wyłączony.
Expiry lub utrata części przywraca bazowy limit oddalenia, bez teleportowania
motocykla, zmiany punktu obserwacji, zasięgu skanu, action range i danych mapy.

P5 ustanawia wspólny kontrakt `territory_defense` oparty na publicznych
podatnościach. Ostatni scan gracza jest zapisywany na serwerze pod nieprzenośnym
`scan_id` i wygasa po godzinie. Jedno poprawne zgłoszenie w aktywnym oknie P5
publikuje wszystkie 1–3 wyniki albo uproszczony obrys maksymalnie 8 punktów dla
większego zbioru. Wybrany punkt zawsze pozostaje w roju. Markery korzystają
z istniejącego minimalnego security, publicznej mapy oraz alarmów; dzięki temu
klan może szybko budować małe terytoria osłonowe wokół strategicznego obszaru.
Pierwotna podatność jest klasycznym, trwałym zgłoszeniem. Dodatkowe markery roju
żyją do `cooldown_until`; niewykorzystane wygasają wtedy automatycznie. Przejęcie
jednego punktu przez członka tego samego klanu przejmuje cały aktywny rój i buduje
z niego punkty terytorium. Atak obcego klanu generuje deduplikowany alarm, lecz
przejmuje wyłącznie hakowany punkt. Każde przyszłe przypisanie rodziny ma zachować
identyczny call-site, selekcję geometryczną, relacje klanowe, limit i lifecycle.
Publiczna etykieta każdego punktu roju kończy się stabilnym sufiksem klanu:
`VIREX`, `Echo`, `Phantom` albo `Sentinel`, np. `Virtual Router Sentinel`.
Sufiks jest wyłącznie prezentacją i nie zmienia kanonicznego `label`,
`vulnerability_id`, deduplikacji ani target identity. Glow roju jest clan-only:
widzą go wyłącznie właściciel i członkowie klanu wystawiającego. Intruz widzi tę
samą publiczną podatność i sufiks klanu, lecz jako zwykłą kapsułę bez glow.

### 3.4 SENTINEL AEGIS

| Sprint | Część / profesja | Moc | Rodzina | Widoczny skutek i początkowy scope | Ocena |
| --- | --- | --- | --- | --- | --- |
| `.4.1` | S1 Deep Sensor / `analyzer` | Skan Integralności | `scan_range` | certyfikowany zasięg strategiczny `25 km × level_snapshot`, ograniczony do `10 000 km`; bez account scan | `STRONG FIT` |
| `.4.2` | S2 Bastion Matrix / `defender` | Bastion | `territory_defense` | ten sam rój publicznych podatności z jednego skanu co P5 | `STRONG FIT` |
| `.4.3` | S3 Restoration Engine / `reconstructor` | Odtworzenie | `hack_actions` | ten sam komplet czterech odblokowanych akcji celu co V2; działa na każdy `aimed` podczas okna | `LOCKED / SERVER E2E + GAMEPLAY PASS` |
| `.4.4` | S4 Accord Relay / `mediator` | Korytarz Zaufania | `operation_risk` | certyfikowane `heat -15` dla maks. 8 istniejących oraz wszystkich nowych operacji podczas okna | `LOCKED / SERVER E2E + GAMEPLAY PASS` |
| `.4.5` | S5 Judgment Core / `executor` | Kwarantanna | `map_zoom` | ten sam certyfikowany strategiczny zoom co P4, skalowany poziomem i ograniczony do produkcyjnego maksimum | `LOCKED / SERVER E2E + GAMEPLAY PASS` |

Każdy montaż zachowuje pełny kontrakt certyfikowanej rodziny niezależnie od
profesji: S2 dziedziczy `territory_defense` z P5, S3 `hack_actions` z V2, S4
`operation_risk` z V3/E2/P1, a S5 `map_zoom` z P4. Różnice obejmują wyłącznie
nazwę, asset, SFX, paletę i narrację. S4 nie przyznaje uprawnień innemu graczowi
ani klanowi, ponieważ cross-player/cross-clan grant nie należy do kontraktu
`operation_risk`.

W rodzinie `hack_actions` cztery kropki akcji i pasek zabezpieczeń są dwoma
niezależnymi kontraktami. Realizer ustawia wyłącznie `actions_allowed`. Pasek
rozbrojenia jest wyliczany z faktycznych flag boolean `security`, a przy ich
braku z jawnego `disarm_progress`; komplet kropek nigdy nie oznacza wizualnego
`100%`. Zasada obowiązuje identycznie V2 i S3.

## 4. Semantyka utraty części

| Typ realizera | Po utracie `active` |
| --- | --- |
| ciągły odczyt: `operation_risk`, `scan_range`, `map_zoom` | znika przy następnym snapshotcie/call-site |
| jednorazowa mutacja: `operation_speed`, `hack_actions`, `target_security` | wykonana zmiana zostaje; nie powstają dalsze zmiany |
| publikacja: `territory_defense` | pierwotna podatność zostaje; dodatkowe punkty roju wygasają przy `cooldown_until`; wykorzystane przez sojusznika są przejmowane jako cały rój |
| trwały marker + hook finalizacji: `file_yield` | operacja dotknięta przed expiry lub utratą części zachowuje bonus do finalizacji; nowe operacje nie są już oznaczane |
| trwały marker + hook finalizacji: `data_quality` | operacja dotknięta przed expiry lub utratą części zachowuje bonus do finalizacji; nowe operacje nie są już oznaczane; zapisane pliki zostają |

Cooldown zawsze biegnie do pierwotnego `cooldown_until`. Utrata części nie usuwa
okna i nie pozwala ominąć cooldownu.

Dla E1 `target_security` jest lustrzanym odpowiednikiem V2: `expose` wyłącza
wszystkie aktywne flagi boolean security dokładnego celu, ale nie zmienia
`actions_allowed`. Gracz nadal zapala cztery kropki istniejącymi narzędziami, więc
jakość narzędzi zachowuje znaczenie. Każdy cel dotknięty przed expiry pozostaje
rozbrojony; po expiry lub utracie części nowe cele nie są zmieniane.

## 5. Kolejność produkcji jednego podsprintu

1. Potwierdzić aktywną część i właściwą profesję na koncie testowym.
2. Zamrozić `ability_code → family`, scope, limit oraz 2–3-wyrazowy tagline.
3. Dodać mały produkcyjny adapter do właściwego canonical store/call-site.
4. Dodać marker idempotencji i bounded telemetry bez identyfikatorów gracza.
5. Udowodnić brak ciężkiego profilu oraz brak parametrów sterowanych klientem.
6. Przetestować przycisk, 6-sekundowy show, SFX, timer, efekt gameplayowy,
   reload, expiry, cooldown i utratę części.
7. Zapisać `KEEP / ADJUST / REPLACE / DEFER` wraz z frontend/backend evidence.

Nie powtarzamy pełnej certyfikacji wspólnego okna dla każdej części. Każdy
podsprint certyfikuje wyłącznie swoje statyczne mapowanie, mały adapter oraz
obserwowalny efekt.

## 6. Pokrycie rodzin w propozycji

| Rodzina | Proponowane części |
| --- | --- |
| `operation_speed` | V1, V5 |
| `file_yield` | V4 |
| `data_quality` | E3 |
| `hack_actions` | V2, S3 |
| `target_security` | E1, E5, P2 |
| `operation_risk` | V3, E2, P1, S4 |
| `scan_range` | E4, P3, S1 |
| `map_zoom` | P4, S5 |
| `territory_defense` | P5, S2 |

Wszystkie 9 certyfikowanych rodzin ma zastosowanie. Trzy rodziny odłożone mają
zero przypisań.
