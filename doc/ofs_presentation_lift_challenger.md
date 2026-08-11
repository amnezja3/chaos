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
