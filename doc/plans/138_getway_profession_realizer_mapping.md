# 138.getway — mapa profesja → gameplay realizer

Status: `PROPOSAL / DECISION ARTIFACT`

Ten artefakt przypisuje każdej z 20 profesji jedną główną rodzinę wpływu z
certyfikowanego katalogu `138.getway.0.4`. Nie jest jeszcze mapowaniem
produkcyjnym. Każdy wiersz staje się kontraktem dopiero po teście frontendowym
w odpowiednim podsprincie i decyzji `KEEP / ADJUST / REPLACE / DEFER`.

## 1. Granice rozwiązania

- jedna moc ma jedną główną rodzinę gameplayową;
- kilka mocy może używać tej samej rodziny z innym zakresem i copy;
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

| Rodzina | Zamrożona granica techniczna |
| --- | --- |
| `operation_speed` | do 8 aktywnych operacji, jednorazowy marker, mnożnik `clamp(0.1 × LVL, 1, 20)` |
| `file_yield` | dokładnie 2 kopie każdego bazowego pliku GX (`backup`, `fullbackup`), stabilne ID; operacja oznaczona w oknie zachowuje bonus do finalizacji |
| `data_quality` | maksymalnie 16 plików; `quality/completeness +20`, clamp `0–100` |
| `hack_actions` | cztery action dots ustawione jako wykonane; security bez zmian |
| `target_security` | maksymalnie 2 zabezpieczenia wyłączone, exact target i CAS |
| `operation_risk` | bounded wejście `heat -15`; kalkulator nadal wyznacza wynik i progi |
| `scan_range` | `base + clamp(20 × LVL, 150, 1500)`, wynik maksymalnie `6000 m`, bez globalnego skanu |
| `map_zoom` | bounded zmiana o 2 poziomy na lekkim capability snapshotcie |
| `territory_defense` | maksymalnie 2 zabezpieczenia przywrócone/włączone na własnym celu, owner check i CAS |

Limity powyżej są punktem startowym. Podsprint może je obniżyć. Podniesienie
limitu lub rozszerzenie kategorii/scope wymaga ponownego testu tej odmiany
rodziny, ale nie przebudowy wspólnego runtime.

## 3. Proponowane mapowanie 20 profesji

### 3.1 VIREX ORACLE

| Sprint | Część / profesja | Moc | Rodzina | Widoczny skutek i początkowy scope | Ocena |
| --- | --- | --- | --- | --- | --- |
| `.1.1` | V1 Ledger Nexus / `broker` | Insider Feed | `operation_speed` | istniejące i nowe operacje przyspieszone `0.1 × LVL`, cap `20×`, maks. 8 | `LOCKED / SERVER PASS` |
| `.1.2` | V2 Backdoor Forge / `architect` | Wejście Serwisowe | `hack_actions` | cel obecny przy aktywacji oraz każdy cel oznaczony w 15-minutowym oknie natychmiast dostaje cztery kropki; zabezpieczenia pozostają | `LOCKED / SERVER PASS` |
| `.1.3` | V3 Mimicry Engine / `manipulator` | Fałszywy Obraz | `operation_risk` | istniejące i nowe aktywne operacje mają `heat -15`; jeden lekki odczyt okna na gracza/tick, widoczny maskowany risk | `LOCKED / SERVER PASS` |
| `.1.4` | V4 Acquisition Drive / `profit_enforcer` | Wrogie Przejęcie | `file_yield` | każda operacja dotknięta w oknie zachowuje wyróżnienie i przy finalizacji tworzy `oryginał + backup + fullbackup` każdego bazowego pliku GX | `LOCKED / SERVER PASS` |
| `.1.5` | V5 Probability Core / `algorithm_curator` | Predykcja Operacyjna | `operation_risk` | niższe ryzyko dzięki przewidywaniu przebiegu operacji; wynik nadal liczy risk meter | `STRONG FIT` |

`false_image` nie używa `incident_decoy`: obraz zastępczy jest opowiedziany przez
overlay i obniżenie heat, bez fałszywych globalnych rekordów. V4 nie tworzy
gotowych paczek. `backup` i `fullbackup` są osobnymi kopiami tego samego materiału,
a istniejący Ghost Exchange sam składa je z oryginałem w paczki sprzedażowe.

### 3.2 ECHO LIBERTAS

| Sprint | Część / profesja | Moc | Rodzina | Widoczny skutek i początkowy scope | Ocena |
| --- | --- | --- | --- | --- | --- |
| `.2.1` | E1 Breach Voice / `hacktivist` | Ujawnienie | `target_security` | maks. 1 zabezpieczenie oznaczonego celu zostaje ujawnione jako wyłączone | `STRONG FIT / LIMIT 1` |
| `.2.2` | E2 Influence Relay / `social_engineer` | Przejęcie Narracji | `operation_risk` | opóźniona reakcja systemu przez `heat -15`; bez wymuszania wyniku detekcji | `STRONG FIT` |
| `.2.3` | E3 Truth Lens / `revealer` | Pełne Ujawnienie | `data_quality` | `+20` jakości i kompletności dla maks. 16 plików camera/audio | `STRONG FIT` |
| `.2.4` | E4 Resonance Beacon / `visionary` | Beacon Oporu | `scan_range` | widocznie większy promień skanu, maks. `6000 m`; tylko gracz aktywujący | `SAFE FIRST SLICE` |
| `.2.5` | E5 Spark Chamber / `igniter` | Efekt Domina | `target_security` | po rozbrojeniu celu wyłączone maks. 1 zabezpieczenie jednego sąsiedniego celu | `CONDITIONAL SELECTOR` |

E5 wymaga małego, deterministycznego selektora jednego sąsiedniego celu. Dopóki
nie ma narrow adjacency query z limitem 1, moc pozostaje `DEFER`, zamiast skanować
terytorium lub listę celów. E4 nie wzmacnia całego klanu w pierwszej wersji, bo
wymagałoby per-recipient reads; wspólnotowy charakter zapewnia prezentacja.

### 3.3 PHANTOM VEIL

| Sprint | Część / profesja | Moc | Rodzina | Widoczny skutek i początkowy scope | Ocena |
| --- | --- | --- | --- | --- | --- |
| `.3.1` | P1 Mirage Projector / `illusionist` | Węzeł Widmo | `operation_risk` | pozorny ruch maskuje prawdziwą operację przez `heat -15` | `SAFE SUBSTITUTE` |
| `.3.2` | P2 Glitch Reactor / `virologist` | Glitch Injection | `target_security` | maks. 2 zabezpieczenia oznaczonego celu zostają wyłączone przez CAS | `STRONG FIT` |
| `.3.3` | P3 Paranoia Loop / `paranoid` | Fałszywe Tropienie | `scan_range` | większy promień pozwala wcześniej dostrzec ślady; bez bypassu pozycji motocykla | `SAFE SUBSTITUTE` |
| `.3.4` | P4 Fracture Engine / `network_splitter` | Pęknięcie Sieci | `map_zoom` | bounded zmiana perspektywy mapy o 2 poziomy; CSS pokazuje rozszczepienie | `VISUAL/GAMEPLAY PROXY` |
| `.3.5` | P5 Mirror Kernel / `mirror_judge` | Odbicie | `territory_defense` | maks. 2 warstwy ochrony wracają na oznaczonym własnym celu | `SAFE SUBSTITUTE` |

P1 nie tworzy fałszywego markera, P3 nie wykonuje skanu niezależnego od pozycji,
a P5 nie odczytuje atakującego. To świadome bezpieczne zamienniki rodzin
`incident_decoy` i `actor_visibility`. Jeżeli efekt nie obroni się w grze,
wybieramy `REPLACE` albo `DEFER`, bez rozszerzania ciężkiego runtime.

Kierunek `map_zoom` trzeba potwierdzić wizualnie w `.3.4`: Leaflet interpretuje
większą wartość jako bliższy widok. Podsprint zamraża właściwy znak zmiany po
teście, nadal z twardym zakresem `1–20`.

### 3.4 SENTINEL AEGIS

| Sprint | Część / profesja | Moc | Rodzina | Widoczny skutek i początkowy scope | Ocena |
| --- | --- | --- | --- | --- | --- |
| `.4.1` | S1 Deep Sensor / `analyzer` | Skan Integralności | `scan_range` | głębszy skan przez zwiększony promień, maks. `6000 m`; bez account scan | `STRONG FIT` |
| `.4.2` | S2 Bastion Matrix / `defender` | Bastion | `territory_defense` | maks. 2 zabezpieczenia włączone na oznaczonym własnym celu | `EXACT FIT` |
| `.4.3` | S3 Restoration Engine / `reconstructor` | Odtworzenie | `territory_defense` | maks. 2 brakujące zabezpieczenia przywrócone na jednym uszkodzonym własnym celu | `STRONG FIT` |
| `.4.4` | S4 Accord Relay / `mediator` | Korytarz Zaufania | `operation_risk` | bezpieczny korytarz zmniejsza heat własnej bieżącej operacji o 15 | `SAFE FIRST SLICE` |
| `.4.5` | S5 Judgment Core / `executor` | Kwarantanna | `territory_defense` | maks. 2 warstwy ochrony na jednym aktualnie zagrożonym własnym celu | `SAFE SUBSTITUTE` |

S3 i S5 mogą później dostać narrow selektor: odpowiednio ostatnio uszkodzony oraz
aktualnie atakowany własny cel, zawsze limit 1. Pierwsza wersja korzysta z celu
oznaczonego przez gracza. S4 nie przyznaje uprawnień innemu klanowi, ponieważ
cross-player/cross-clan grant nie jest częścią certyfikowanej rodziny.

## 4. Semantyka utraty części

| Typ realizera | Po utracie `active` |
| --- | --- |
| ciągły odczyt: `operation_risk`, `scan_range`, `map_zoom` | znika przy następnym snapshotcie/call-site |
| jednorazowa mutacja: `operation_speed`, `hack_actions`, `target_security`, `territory_defense` | wykonana zmiana zostaje; nie powstają dalsze zmiany |
| trwały marker + hook finalizacji: `file_yield` | operacja dotknięta przed expiry lub utratą części zachowuje bonus do finalizacji; nowe operacje nie są już oznaczane |
| hook finalizacji: `data_quality` | ukończenia po utracie części nie dostają bonusu; wcześniej zapisane pliki zostają |

Cooldown zawsze biegnie do pierwotnego `cooldown_until`. Utrata części nie usuwa
okna i nie pozwala ominąć cooldownu.

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
| `operation_speed` | V1 |
| `file_yield` | V4 |
| `data_quality` | E3 |
| `hack_actions` | V2 |
| `target_security` | E1, E5, P2 |
| `operation_risk` | V3, V5, E2, P1, S4 |
| `scan_range` | E4, P3, S1 |
| `map_zoom` | P4 |
| `territory_defense` | P5, S2, S3, S5 |

Wszystkie 9 certyfikowanych rodzin ma zastosowanie. Trzy rodziny odłożone mają
zero przypisań.
