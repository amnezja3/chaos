# OFS Presentation Lift Challenger

Status: plan produkcyjny do realizacji po `130.8.6.6`.

Zakres: sprinty `130.8.6.7–130.8.6.10`.

## Kontrakt wspólny

Blok rozwija istniejący `OperationFeedbackSession`, composer, scene envelope,
renderery i `ofs_provisional`. Nie tworzy drugiego silnika ani requestu.

Provisional, content autora, OFS i wynik nie mogą wyglądać jak cztery doklejone
moduły. Każdy typ aplikacji otrzymuje jeden trwały shell, layout, typografię i
język animacji. Zmieniają się fazy i dane, ale użytkownik przez cały lifecycle
ma widzieć jeden spójny interface.

```text
launch intent
→ provisional dobrany do interface i realnego czasu hydration
→ hydration tego samego okna
→ jedna scena contentu autora
→ wykonawcze sceny OFS
→ autorytatywna scena końcowa z payloadu
→ dispose
```

Zasady:

* payload zawsze wygrywa z animacją;
* hydration anuluje przyszłe provisional bez sztucznego opóźnienia;
* szybki launch nie czeka na zakończenie dekoracji;
* completion/failure nie wolno losować;
* `buttons/options` autora pozostają gameplayem;
* animujemy wnętrze `.operation-feedback-host`, nigdy `.app-window`, drag handle,
  jego `transform` ani `pointer-events`;
* procent nie może udawać rzeczywistego postępu requestu backendowego;
* `random_progress` może pokazywać lokalny, prezentacyjny procent każdej linii
  autora, jeżeli jest jawnie odseparowany od stanu backendu;
* visual lift pozostaje niezależny od wyniku operacji i rollbackowalny flagą.

Mapowanie docelowe:

```text
button_choices    → button_choice
progressbar_random → random_progress
terminal          → terminal
window            → window
```

`random_progress` jest template'em prezentacyjnym. Nie zmienia zapisanego
`app.interface = progressbar_random`.

## Sprint 130.8.6.7 — Presentation Timeline & Handoff Contract

Status: zaimplementowany lokalnie 2026-08-11; oczekuje na test produkcyjny.

Cel: jedna maszyna faz dla wszystkich rodzajów aplikacji.

Fazy:

```text
provisional → hydrating → author_intro → executing → completing
→ completed | failed | cancelled | disposed
```

Zakres:

* jeden właściciel viewportu, cancel token i `elapsed_ms` na fazę;
* jawne dozwolone przejścia i idempotencja duplicate receipt/payload;
* hydration kasuje provisional; transition może domknąć tylko bezpieczną klatkę
  do maksymalnie `200–300 ms`;
* po hydration dokładnie jedna plain-text scena autora z priorytetem
  `feedback_content → structured → legacy → fallback`;
* payload przed pierwszą sceną OFS prowadzi po scenie autora prosto do completion;
* payload podczas choice blokuje wybór i przejmuje completion;
* aktywny choice zamraża scenę OFS: content nie zmienia się przed kliknięciem
  albo timeoutem, a następna scena może wejść dopiero po rozstrzygnięciu;
* zamknięcie okna usuwa timery, listenery i presentation state;
* faza/template/wait band są atrybutami wewnętrznego hosta, nie okna;
* handoff zachowuje istniejące okno, jego nagłówek i uchwyt drag.

Timing wykonawczy zostaje spowolniony co najmniej `×3` względem obecnego OFS.
Oprócz mnożnika obowiązuje minimalny czas czytelności zależny od treści:

```text
krótka linia             2.5–3 s
zwykła scena             4–6 s
scena wieloliniowa       6–9 s
ważny opis               8–12 s
prompt przed choice      minimum 2 s
aktywny choice           8–15 s albo jawny timeout profilu
potwierdzenie wyboru      0.6–1.2 s
completion/failure       minimum 4–6 s
```

Glitch może akcentować wejście i wyjście, lecz nie zasłania całego czasu
czytania. Payload przejmuje stan logiczny natychmiast, ale renderer może wykonać
krótkie, nieinteraktywne przejście do wyniku bez opóźniania gameplayu.

Testy: hydration `<300 ms`, `2 s`, `15 s`, `60 s`, `149 s`, `>150 s`, race na
granicy sceny, duplicate receipt/payload, kilka okien, zamknięcie i drag przed,
w trakcie oraz po hydration, pomiar czasu czytelności oraz zakaz zmiany sceny
podczas aktywnego choice.

DoD: content autora pojawia się raz, kolejność faz jest stabilna, a prezentacja
nie opóźnia backendu i nie odbiera oknu uchwytu.

Realizacja:

* execution posiada jawne fazy zapisane na wewnętrznym hoście i telemetry
  `feedback_phase_changed`;
* provisional raportuje `provisional → hydrating → author_intro → executing`
  oraz osobny `feedback_provisional_handoff`;
* właściwy renderer zaznacza autorski content jako pokazany; sesja OFS nie
  powiela go, a fallbackowe `author_intro` działa tylko bez wcześniejszej sceny;
* execution composer nie miesza ponownie ogólnych linii autora po intro;
* aktywny choice zatrzymuje scheduler do kliknięcia albo timeoutu;
* opóźnienie scen jest maksimum z czasu czytelności i dotychczasowego timingu
  pomnożonego przez trzy;
* completion/failure pozostaje widoczne minimum 4.5 s;
* dispose usuwa timery, choice i ownership bez ingerencji w drag handle.

## Sprint 130.8.6.8 — Adaptive Provisional Scene Packs

Status: zaimplementowany lokalnie 2026-08-11.

Cel: cztery rozpoznawalne głosy istniejącego `ofs_provisional.launch_150s`,
dobierane do rzeczywistego czasu oczekiwania.

Pasma:

```text
instant 0–1.5 s | short 1.5–8 s | medium 8–30 s
long 30–90 s | extended 90–150 s | overdue >150 s
```

Jeden scheduler korzysta z:

```text
provisional_timelines.launch_150s
provisional_scene_library
provisional_voice_packs.{terminal,button_choices,window,progressbar_random}
```

Każdy voice otrzymuje kilka scen rodzin `app_identity`, `local_init`,
`interface_boot`, `author_manifest`, `context_bind`, `module_boot`,
`local_validation`, `runtime_prepare`, `launcher_sync`, `hydration_wait` i
`extended_wait`.

Charakter:

* `button_choices`: przygotowanie kart i slotów decyzji bez options gameplay;
* `progressbar_random`: moduły, checkpointy i etapy bez fikcyjnego procentu;
* `terminal`: prompt, boot i krótki kontrolowany bufor;
* `window`: panel, sloty i lokalny stan przygotowania.

Anti-repeat: brak bezpośredniego powtórzenia, rotacja wariantów przed ponownym
użyciem, rytm zwalnia przy długim wait, a `extended_wait` działa co `12–20 s`.
Brak voice używa `default`; nie zatrzymuje launchera. `150 s` oznacza dostępne
pokrycie, nigdy obowiązkowy czas odtwarzania.

Testy: cztery voice dla sześciu pasm, trzy różne przebiegi tej samej akcji,
brak placeholdera, uszkodzony wariant, natychmiastowy cancel po hydration,
reduced motion oraz zakaz fikcyjnego transport error/progress.

DoD: każdy interface jest rozpoznawalny przed hydration i obsługuje zarówno
`200 ms`, jak i kilka minut oczekiwania.

Realizacja:

* `operation_feedback.v1.json` definiuje sześć progów czasu oraz kompletne
  pakiety `terminal`, `button_choices`, `window` i `progressbar_random`;
* każdy pakiet pokrywa wszystkie rodziny `launch_150s` co najmniej trzema
  wariantami, a brak rozpoznanego voice wraca do istniejącego `default`;
* scheduler wybiera pasmo z faktycznego czasu od otwarcia okna i przekazuje je
  do envelope, DOM oraz telemetrii bez wpływu na request i hydration;
* rotacja pamięta sześć ostatnich wariantów i zużywa pulę przed powtórką;
* walidator odrzuca brakujące rodziny, zbyt małe pule, błędne progi,
  niedozwolone placeholdery oraz fikcyjny outcome/transport.

## Sprint 130.8.6.9 — Four Application Presentation Templates

Status: zaimplementowany lokalnie 2026-08-11.

Cel: cztery unikatowe layouty CSS i zachowania scen przy wspólnym envelope.

### `button_choice`

Prompt i decyzje są centrum layoutu. Ten sam shell obsługuje provisional,
content autora, przyciski, OFS i wynik. Układ przycisków zależy od liczby opcji:

```text
1       jeden duży przycisk centralny
2–4     panel dużych przycisków
5+      stabilna, przewijalna lista przycisków
```

Przyciski mają focus/hover/pressed/disabled i stały action dock niezależny od
długości contentu. Content posiada własny obszar oraz limit/scroll i nigdy nie
wypycha przycisków spod kursora. Po pokazaniu choice prompt i scena zostają
zamrożone do kliknięcia albo timeoutu; nie wolno w tym czasie zmieniać tekstu,
kolejności, rozmiaru ani położenia przycisków.

Po kliknięciu wybrana opcja otrzymuje krótkie potwierdzenie, przyciski są
blokowane, a ich scena zostaje zastąpiona scenami OFS. Payload przywraca scenę
autora jako końcowy, nieinteraktywny stan z zaznaczonym wyborem oraz prawdziwym
`DONE/FAILED/result`. Nie przywraca aktywnych przycisków do ponownego requestu.

### `random_progress`

Osobny renderer dla `progressbar_random`: executor celu w jednym shellu od
provisional do wyniku. Każda linia contentu autora posiada własny pasek,
procent i lokalny status. Wszystkie paski startują razem, ale rosną niezależnymi,
losowymi i monotonicznymi skokami, mają różne pauzy oraz kończą się w różnej
kolejności. Każde uruchomienie może mieć inny przebieg.

Te procenty opisują wyłącznie prezentacyjne wykonanie linii autora, nie stan
requestu backendowego. Przed payloadem paski mogą zwalniać i czekać poniżej
końca. Success dociąga pozostałe do `100%` krótką sekwencją i pokazuje scenę
wyniku. Failure zatrzymuje lub domyka je zgodnie z template'em błędu i pokazuje
prawdziwy błąd. Animacja nie może opóźniać obsługi payloadu.

### `terminal`

Prompt, cursor, typowane linie komendy/odpowiedzi/warning/result i limit bufora.
Content autora jest manifestem lub skryptem startowym. Prawdziwy transport error
ma inny styl niż narracyjne ostrzeżenie. Provisional, autor i OFS są jednym
strumieniem terminalowym. Obecny spinner znika; zastępuje go sysinfo/status,
np. `READY`, `RUNNING`, `SENT`, `DONE`, `COMPLETE`, `FAILED`. Polecenia autora
zachowują animację pisania, ale respektują minimalny czas czytelności.

### `window`

Stabilny panel z sekcjami i slotami `label/value`. Content autora tworzy główny
obszar, a jego przyciski pozostają rozróżnione i umieszczone pod nim. Po wyborze
część robocza przechodzi do OFS, przyciski są blokowane lub ukryte zgodnie z
kontraktem, a payload przywraca panel autora w stanie końcowym. Zachowanie jest
relatywnie podobne do `button_choice`, lecz decyzje nie dominują layoutu.
Completion zmienia stan panelu zamiast zamieniać go w terminal.

Wspólne tokeny: accent, danger, warning, success, surface, grid, glitch level i
motion scale. Selektory są ograniczone do hosta/template'u. Wszystkie layouty
muszą obsługiwać desktop, małe okno, narrow/mobile, klawiaturę, widoczny focus,
kontrast i `prefers-reduced-motion`.

Testy: DOM contract wszystkich faz, author structured/legacy/fallback, układ
choice dla `1`, `2–4` i `5+` opcji, nieruchomy action dock, freeze contentu do
kliknięcia/timeoutu, random progress wielu linii i różne sekwencje skoków,
payload success/failure w połowie progresu, terminal bez spinnera, limit bufora,
window z przyciskami i bez slotów, mobile, reduced motion i równoległe aplikacje.

DoD: typ aplikacji można rozpoznać po wyglądzie i ruchu, ale gameplay, payload,
composer i lifecycle pozostają wspólne.

Realizacja:

* provisional i autorytatywny renderer zachowują na tym samym oknie klasę
  template'u: `terminal`, `button-choice`, `window` lub `progressbar-random`;
* `progressbar_random` ma własny execution renderer, a nie alias `window`;
* button choice rozkłada jedną opcję centralnie, 2–4 w gridzie i 5+ w
  przewijalnej liście; action dock i content mają niezależną geometrię;
* terminal zachowuje pisanie poleceń, lecz spinner zastąpiły jawne stany
  `RUNNING`/`SENT`/`COMPLETE`/`FAILED`;
* random progress uruchamia osobny, monotoniczny pasek dla każdej linii autora,
  zatrzymuje go przed końcem do payloadu i dopiero sukces domyka do `100%`;
* window posiada stabilny author content, action dock, result i sloty OFS;
* payload blokuje ponowne użycie autorskich przycisków, zatrzymuje timery
  progresu i nie czeka na zakończenie animacji;
* CSS jest ograniczony do `.ofs-app-template`, obsługuje małe okna, focus oraz
  `prefers-reduced-motion`.

## Sprint 130.8.6.10 — Map FX Language & Production Hardening

Status realizacji (2026-08-11): zaimplementowany lokalnie, oczekuje na
potwierdzenie macierzą produkcyjną po wdrożeniu.

Zrealizowano:

* semantyczne role i ikony linii bez HTML pochodzącego z contentu autora;
* eskalację efektu wyłącznie podczas provisional oraz reset wait bandu przy
  hydration;
* warning pulse zależny od prawdziwego tonu `warning` oraz success/failure burst
  dostępny dopiero w scenie wyniku payloadu;
* maksymalnie jedną animowaną dekorację albo linię na host, limity bufora scen i
  kroków progressu oraz cleanup datasetów;
* telemetrię `scene_dom_nodes` i `visual_lift`;
* niezależny rollback `CHAOS_OFS_VISUAL_LIFT_ENABLED=0`, który nie wyłącza OFS,
  provisional ani requestu gameplay;
* pełne wyłączenie ruchu przez `prefers-reduced-motion` bez utraty treści.

Cel: połączyć aplikacje z językiem mapy CHAOS i bezpiecznie zakończyć cutover.

Wspólne elementy:

* semantyczne ikony przy liniach (`identity`, `module`, `target`, `author`,
  `command`, `decision`, `checkpoint`, `warning`, `success`, `failure`);
* scanline/grid/noise wyłącznie w hoście sceny;
* krótki glitch wejścia sceny;
* warning pulse tylko dla prawdziwego warningu;
* success/failure burst dopiero po payloadzie;
* jitter ikony lub wewnętrznej linii, nigdy całego okna.

Intensywność wynika z wait band: short jest czysty, medium dostaje delikatny
pulse, long micro-jitter, extended glitch przy zmianie sceny, overdue osiąga
ograniczony bezpieczny poziom i wolniejszy rytm. Po hydration intensywność wait
jest zerowana; execution reaguje już tylko na tone i prawdziwe eventy.

Wydajność:

* bez stałego JS/requestAnimationFrame dla glitcha;
* maksymalnie jedna aktywna dekoracja animowana na host;
* bez layout thrash i bez nieograniczonego DOM;
* cleanup w `dispose`;
* kilka okien nie może opóźniać mapy ani desktopu.

Cutover zachowuje obecne flagi i dodaje niezależny rollback visual liftu.
Macierz testowa obejmuje `4 template'y × 4 czasy hydration × success/failure/
HTTP error/abort × desktop/mobile/reduced motion`, drag/resize, picker cleanup,
author content raz, brak podwójnego okna/requestu, wszystkie 12 action keys,
brak 409/500 wywołanego prezentacją, timing co najmniej `×3`, nieruchome choice
buttons oraz pomiar CPU/DOM.

DoD: cztery template'y są unikatowe i należą do świata CHAOS, efekt narasta z
czasem bez fałszowania stanu, a lift można wyłączyć bez wyłączania OFS.

## Lift Sprint 130.8.6.11 — Application Title Sequence Generator

Cel: zbudować generowaną czołówkę aplikacji, która płynnie otwiera ten sam,
stabilny viewport używany później przez content autora, OFS i finał. Nazwa
aplikacji jest jedynym inicjatorem kompozycji: nie dodajemy ręcznych wariantów
dla konkretnych aplikacji i nie wiążemy czołówki z gameplayem.

### Wejście generatora

Generator otrzymuje wyłącznie bezpieczne dane prezentacyjne:

* pełną nazwę aplikacji;
* ikonę aplikacji albo neutralny fallback;
* rzeczywisty `interface` wybierający rodzinę template'u;
* opcjonalny krótki opis autora, pokazywany dopiero po czołówce.

Z nazwy wyliczane są: `character_count`, `word_count`, `space_count`, długość
najdłuższego słowa oraz stabilny lokalny hash. Hash nie służy do losowania
wyniku — wybiera jedynie powtarzalny wariant ruchu. Ta sama nazwa i template
muszą zawsze tworzyć tę samą czołówkę, także po ponownym otwarciu aplikacji.

### Model generowanego brandingu

Generator nie tworzy wyłącznie jednorazowej planszy. Przy hydration buduje jeden
niemutowalny model identyfikacji aplikacji, wykorzystywany przez czołówkę,
content autora, execution OFS i finał. Model powstaje raz dla konkretnego okna;
zmiana sceny nie może ponownie losować proporcji ani położenia logo.

Minimalny kontrakt prezentacyjny:

```json
{
  "schema_version": "1.0.0",
  "identity_seed": "stable-local-hash",
  "name_metrics": {
    "character_count": 9,
    "word_count": 1,
    "space_count": 0,
    "longest_word": 9,
    "name_class": "compact-mark"
  },
  "title_sequence": {
    "layout": "horizontal-lockup",
    "motion": "icon-lock",
    "duration_band": "short",
    "duration_ms": 5000,
    "map_duration_ms": 12000,
    "readable_ms": 5000
  },
  "author_logo_header": {
    "mode": "icon_text_horizontal",
    "font_weight": 800,
    "font_scale": "compact",
    "icon_text_ratio": "1:0.72",
    "icon_position": "leading",
    "anchor": "start"
  },
  "author_footer": {
    "mode": "signature_compact",
    "font_weight": 700,
    "font_scale": "micro",
    "icon_text_ratio": "1:0.58",
    "icon_position": "leading",
    "anchor": "end"
  }
}
```

Czołówka trwa co najmniej 5 s. Dla uruchomienia z mapy stabilny hash marki
wybiera czas 12–60 s; nie zmienia to wyniku ani momentu rozpoczęcia requestu.
Wewnątrz planszy działają cykliczne mikro-sceny identyfikacji, kanału, autora i
handshake'u. Kolejno podświetlają linie, poruszają wyłącznie ikoną oraz wykonują
krótki glitch tekstu. Shell i rozmiar okna pozostają nieruchome.

`ofs_provisional.launch_150s` zachowuje nazwę kontraktową, ale jego produkcyjna
oś ma pokrycie 180 s. Kolejne sceny otrzymują 12–18 s na odczyt, a ich linie
prowadzą własne, wolne show. Payload nadal natychmiast kończy provisional.

Po autorytatywnym sukcesie lub błędzie ostatnia scena odpowiedzi pozostaje w
viewportcie. Auto-close nie tworzy następnej sceny: jest półprzezroczystą,
nieinteraktywną nakładką z odliczaniem sekund nad finałem.

Wartości są tokenami z zamkniętego słownika. Autor aplikacji nie przekazuje
dowolnego CSS, wymiarów, pozycji ani animacji. `font_weight`, `font_scale`,
`icon_text_ratio`, `icon_position` i `anchor` są wyliczane deterministycznie z
nazwy oraz ograniczane przez template interface'u.

### Reguły budowy logo

Budujemy automatyczny lockup z istniejącej ikony i nazwy aplikacji. Nie
generujemy nowego pliku graficznego i nie modyfikujemy źródłowej ikony.

* krótka nazwa, domyślnie do 12 znaków i maksymalnie jednego odstępu, używa
  `icon_text_horizontal`: ikona po lewej, napis po prawej na wspólnym baseline;
* bardzo krótka nazwa jednowyrazowa może dostać większy `font_weight` i bardziej
  zwarty stosunek ikony do tekstu;
* nazwa 13–18 znaków może pozostać pozioma tylko wtedy, gdy pomiar szerokości
  mieści się w bezpiecznym limicie konkretnego template'u;
* długa, gęsta albo wielowierszowa nazwa używa `icon_only`; pełna nazwa nadal
  pozostaje w czołówce, title barze, `title` i nazwie dostępnej dla ARIA;
* brak ikony uruchamia jeden neutralny fallback wspólny dla OFS; brak nazwy
  tworzy dostępny label `Aplikacja`, ale nie zapisuje go jako nowej nazwy autora;
* header i footer zawsze korzystają z tej samej ikony, wagi bazowej, proporcji i
  strony zakotwiczenia. Footer może jedynie zmniejszyć skalę, nie może tworzyć
  innego logo.

`author_logo_header` jest głównym, spokojnym lockupem widocznym nad sceną autora
i jako subtelna identyfikacja w execution OFS. `author_footer` jest małą
sygnaturą przy dolnej krawędzi viewportu. Oba elementy pozostają nieruchome w
czasie zmiany wewnętrznych scen i nie mogą przesuwać action docku.

### Dziedziczenie brandingu przez show

```text
title_intro       → duży lockup i animacja wejścia
author_intro      → author_logo_header + content autora + author_footer
execution OFS     → mały author_logo_header + sceny OFS + author_footer
completion/failure→ ten sam lockup, zmienia się wyłącznie prawdziwy tone wyniku
```

Kolor tonu sukcesu, warningu lub failure nie nadpisuje bazowej tożsamości logo.
Może jedynie dodać krótkie obramowanie lub impuls do istniejącego lockupu po
autorytatywnym payloadzie. Provisional przed hydration korzysta z bezpiecznej
projekcji nazwy i ikony; hydration potwierdza model i nie może spowodować skoku
geometrii, jeśli dane są identyczne.

### Klasy kompozycji nazwy

* `compact-mark`: jedno słowo krótsze od ustalonego progu; duży bold, układ
  poziomy ikona + nazwa;
* `single-wide`: jedno dłuższe słowo; ikona nad nazwą, kontrolowane zwężenie
  fontu i skalowanie bez łamania viewportu;
* `word-pair`: dwa słowa; duża ikona centralna, nazwa pod nią w dwóch logicznych
  segmentach;
* `multi-word`: trzy lub więcej słów; mniejsza ikona, blok tytułowy o stałej
  szerokości i maksymalnie dwóch liniach;
* `dense-title`: bardzo długa nazwa albo długie słowo bez spacji; bezpieczne
  skrócenie wizualne, pełna nazwa pozostaje dostępna w `title`/ARIA.

Próg i reguły są wspólne dla wszystkich aplikacji. Niedozwolone są wyjątki po
`app_id`, ręczne CSS-y dla nazw oraz zmiana tekstu dostarczonego przez autora.

### Rodziny animacji wejścia

Stabilny hash nazwy przypisuje jedną rodzinę w obrębie klasy kompozycji:

1. `icon-lock`: ikona materializuje się, wykonuje krótki lock/pulse, następnie
   wjeżdża nazwa;
2. `title-slide`: nazwa wjeżdża poziomo, ikona pojawia się po zakotwiczeniu
   baseline'u;
3. `split-reveal`: segmenty wielowyrazowej nazwy odsłaniają się kolejno wokół
   nieruchomej ikony;
4. `blink-sync`: ikona i tytuł pojawiają się krótkimi, malejącymi blinkami,
   kończąc w stabilnym stanie;
5. `glitch-anchor`: pojedynczy kontrolowany glitch ustala pozycję ikony, potem
   nazwa jest odsłaniana bez dalszego skakania;
6. `type-lock`: krótka nazwa składa się znak po znaku, a ikona potwierdza ją
   jednym impulsem.

Liczba słów i spacji ustala kierunek oraz punkty zakotwiczenia animacji. Długa
nazwa nie może wykonywać tego samego szerokiego wjazdu co krótki znak. Animacja
może poruszać ikoną lub wewnętrznym blokiem tytułu, ale nigdy `.app-window`,
title barem ani pozycją drag/resize.

### Sekwencja scen

```text
provisional
→ hydration
→ title_intro: ikona + wygenerowana kompozycja nazwy
→ author_intro: treść przygotowana przez autora
→ po akcji author content zostaje ukryty
→ execution OFS przejmuje ten sam viewport
→ completion / failure / transport error
```

`title_intro` jest podfazą prezentacyjną istniejącego `author_intro`, a nie nowym
stanem gameplay ani osobnym requestem. Payload zawsze może przerwać czołówkę i
natychmiast pokazać prawdziwy finał. Czołówka nie może opóźniać requestu.

### Timing i stabilność

* cała czołówka trwa docelowo 1,8–3,8 s zależnie od długości nazwy;
* nazwa pozostaje w pełni czytelna minimum 900 ms przed przejściem dalej;
* maksymalnie jedna animowana dekoracja i jeden blok tekstowy naraz;
* stała wysokość viewportu w pionie, kwadracie i poziomie;
* content autora ma wewnętrzny scroll i nigdy nie rozpycha okna;
* równoległe okna posiadają niezależne timery, właścicieli i cleanup;
* brak `requestAnimationFrame`; animacje CSS są jednorazowe i ograniczone;
* `prefers-reduced-motion` pokazuje natychmiastową, statyczną kompozycję z tym
  samym czasem czytelności;
* zamknięcie, abort, hydration oraz payload czyszczą timery i klasy animacji.

### Style rodzin interface

Generator zachowuje wspólną gramatykę, ale dziedziczy charakter template'u:

* terminal — type-lock, prompt/cursor i sysinfo;
* button choice — mocny znak, centralny lock i wejście jak panel decyzyjny;
* window — warstwowe odsłonięcie ikony oraz nagłówka modułu;
* progressbar random — sekwencja boot/checkpoint bez fikcyjnego procentu wyniku.

Nazwa wybiera wariant czołówki, natomiast `interface` dostarcza kolory, font,
siatkę i dozwolony zestaw ruchu. Dzięki temu aplikacja zachowuje własną
tożsamość bez utraty spójności OFS.

### Testy

Macierz kontraktowa:

* nazwy: 1 krótki wyraz, 1 długi wyraz, 2 wyrazy, 3+ wyrazy, bardzo długa nazwa,
  znaki specjalne i brak nazwy;
* cztery template'y oraz pion/kwadrat/poziom/mobile;
* deterministyczny wariant dla tej samej nazwy;
* stabilny i identyczny `author_logo_header` oraz `author_footer` we wszystkich
  fazach jednego okna;
* granice logo: 12 znaków, przedział 13–18, długa nazwa, wiele spacji, długie
  słowo bez spacji, brak ikony i brak nazwy;
* przełączenie `icon_text_horizontal → icon_only` bez zmiany wymiaru okna;
* tokeny brandingu z allowlisty i brak surowego CSS/HTML w modelu;
* brak zależności od `app_id`, gameplay payloadu i security state;
* payload podczas każdej części czołówki;
* wiele równoległych okien bez wspólnego timera lub ownera;
* zamknięcie, abort, failure i ponowne otwarcie;
* klawiatura, ARIA, pełna nazwa dense-title oraz reduced motion;
* stały rozmiar `.app-window`, brak prześwitu mapy i brak layout shift;
* brak drugiego requestu, dodatkowego `/gonna-win`, 409 lub 500 wywołanego
  prezentacją.

### Rollback i DoD

Czołówka otrzymuje osobną flagę podrzędną wobec visual liftu. Jej wyłączenie
pomija `title_intro` i przechodzi bezpośrednio do contentu autora, nie wyłączając
template'u, provisional ani OFS.

DoD: po samej ikonie, nazwie i ruchu można rozpoznać wejście aplikacji; okno nie
zmienia wymiarów między czołówką, autorem, OFS i finałem; równoległe aplikacje
rozpoczynają lokalny show natychmiast i nie czekają na wspólną kolejkę requestów.

### Stan realizacji 2026-08-11

Sprint zaimplementowany. Model brandingu jest wyliczany deterministycznie raz na
okno i przechodzi z provisionala przez hydration. Stały shell zawiera nieruchomy
`author_logo_header`, wspólny viewport scen oraz `author_footer`; autor, OFS i
finał wymieniają wyłącznie zawartość viewportu. Czołówka jest lokalną podfazą
`author_intro`, nie wykonuje requestu i jest przerywana przez autorytatywny payload.
Rollback: `CHAOS_OFS_TITLE_SEQUENCE_ENABLED=0`.
