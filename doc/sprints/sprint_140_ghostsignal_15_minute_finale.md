# Sprint 140 — GhostSignal: pełny 15-minutowy finał CHAOS

Status: `IN PROGRESS / 140.1 SERVER TESTS PASS / 140.2 LOCAL TESTS PASS / VISUAL GATE PENDING`

Bramka Sprintu 139 zaliczona 2026-09-11; dowody:
`doc/audits/139-4-production-e2e-summary.md`.
Decyzja operatora: zachować istniejące przypisanie SFX sygnału do
`ghost.signal_sent` i wykorzystać ten moment w reżyserii Sprintu 140.

Źródło produktowe: `doc/sprints/sprint_139_opis_15-minutowe_show.md`

Szczegółowy scenariusz autora (aktualizacja 2026-09-11):
[GhostSignal Final Show — pełny przebieg](sprint_140_ghostsignal_szczegolowy_scenariusz.md).
Zawiera wszystkie przedziały scen, teksty, dane, assety i reguły awaryjne.
Jest obowiązującym rozwinięciem reżyserii; poniższy plan określa jej realizację
w istniejących mechanizmach. Realizacja 140.1 i wyniki kontroli są opisane
poniżej; nie wykonano wdrożenia produkcyjnego w ramach implementacji.

## 1. Cel sprintu

Zastąpić techniczny ekran z paskiem i rotującymi logami największym wydarzeniem
gry: piętnastominutową, server-clock reżyserią, która pokazuje zamknięcie
GhostNetwork, emisję GhostSignal, rozliczenie starego świata i boot nowego cyklu.

Show ma wykorzystywać istniejący język wizualny CHAOS — mapę, BlackNet,
Secret Path, terminal, Googleplex, pliki, narzędzia, glitche, radio i SFX — ale
każdy efekt musi wynikać z bieżącego etapu opowieści:

```text
części -> maszyny -> sieć -> uzbrojenie -> transmisja
       -> rozpad świata -> rozliczenie -> rekonstrukcja -> ranking -> reboot
```

## 2. Twarde zasady realizacji

### 2.1. Reżyser sterowany stanem i czasem serwera

Frontend nie prowadzi własnego niezależnego zegara. Dostaje durable manifest
show, milestone'y i czas serwera. Po reloadzie lub wybudzeniu telefonu oblicza
aktualną scenę i przechodzi do niej bez odtwarzania całych wcześniejszych minut.

Obowiązuje zatwierdzony kontrakt 139: trwały show i blokada, skutki transmisji,
ghost.signal_sent, stabilizacja, settlement/rollover, restart epoch, boot/ACK.
Faktyczne ghost.signal_sent wyzwala istniejący SFX oraz krótki wizualny akcent
potwierdzenia w aktualnej scenie. Timer, 100% animacji i koniec filmu nie mogą
wywołać transmisji ani zastąpić jej potwierdzenia.

Brak opcjonalnego źródła degraduje tylko warstwę wizualną. Brak potwierdzenia
transmisji zatrzymuje przejście do SIGNAL_SENT, WORLD_SETTLEMENT, ARCHIVING
i RESTARTING. Deadline nie wymusza sukcesu. Korzystamy z istniejącej blokady,
recovery i warunków rolloveru 139. Nie dodajemy przesuwania deadline'u ani
nowej bramki transmisji na potrzeby filmu. Opcjonalne sceny dopasowują się do
utrwalonych show_started_at/show_ends_at; nie opóźniają poprawnego restartu.

Scenariusz dostosowujemy do 139, nie odwrotnie. Transmisja zachodzi na początku
show zgodnie z backendem; odcinek 06:00–08:00 jest retrospekcją złożenia maszyn
i już potwierdzonej emisji. Film 07:05–07:43,12 i wizualizacja około 07:43,12
nie oznaczają nowej próby wysłania. Nie opóźniamy ani nie powtarzamy SFX.
Scena korzysta z utrwalonego potwierdzenia i rzeczywistego signal_sent_at.

### 2.2. Brak Ollamy na ścieżce krytycznej

W trakcie show nie zlecamy modelowi narracji dotyczącej właśnie zakończonego
sygnału. Reżyser czyta wyłącznie utrwalone materiały:

- immutable lock snapshot i signal payload;
- historyczne eventy, logi i publikacje cyklu;
- zaakceptowane teksty Ollamy z rozegranego świata;
- ranking, reward ledger, archive i territory consumption receipts;
- gotowe teksty awaryjne zapisane w repozytorium.

Ollama może w tle przygotowywać materiały nowego cyklu, ale jej brak, timeout lub
wyłączony worker nie wpływa na przebieg show i restart.

### 2.3. Jeden manifest zamiast ciężkich profili

Backend buduje viewer-safe, bounded `ghostsignal-show-manifest-v2` z immutable
danych. Manifest zawiera sceny, cue, identyfikatory assetów i niezbędne
statystyki. Nie wolno podczas każdej fazy skanować ciężkich profili wszystkich
graczy ani pełnego archiwum eventów.

Dane prywatne pozostają poza publicznym show. Nick, klan, profesja, SP i wynik
pojawiają się tylko w zakresie dopuszczonym przez snapshot/ranking audience.

`ghost_signal_show_snapshot` oznacza zamrożony zestaw danych prezentacji,
oparty o istniejące snapshoty, projekcje i archiwum, nie nowy równoległy magazyn
świata. Dane sprzed rozliczenia utrwalamy przed jego skutkami; nie opóźniamy
natychmiastowego lock/show ciężką agregacją. Wyniki, które jeszcze nie istnieją
w T0, dołączamy z finalnych ledgerów/receipts jako osobną, wersjonowaną część
projekcji. Nie udajemy, że finalny settlement był znany przed transmisją.

Każdy element ma źródło: STATIC ASSET, CANONICAL CONFIG albo CYCLE SNAPSHOT.
Jeśli danych brak, pomijamy element; nie wymyślamy nazw, relacji, historii,
wyników ani wskaźników. Prezentacja gracza korzysta z lekkiej projekcji,
nigdy z pełnego profilu. Układ połączeń pochodzi z kanonicznej topologii.

Kontrakt synchronizacji ma udostępnić signal_id, cycle_id, show_started_at,
show_stage, signal_sent_at, future_2108_timestamp, settlement_completed_at
i restart_at. Są to wymagania semantyczne: w 140.1 mapujemy je na istniejące
pola, eventy i zegar, bez dublowania authority. Datę w roku 2108 ustalamy raz
po stronie backendu i utrwalamy dla show; nie jest to dodanie 82 lat ani
losowanie osobno w przeglądarkach. Rzeczywistą datę transmisji wyświetlamy
z signal_sent_at (rok 2026 w obecnym scenariuszu, nie stała zaszyta w kodzie).

### 2.4. Graceful degradation

Minimalna ścieżka awaryjna nadal pokazuje fazę, czas, canonical fakty i końcowy
restart. Brak radia, pojedynczego assetu, WebGL/canvas lub dźwięku nie może
odblokować gameplayu ani wywalić całego show.

## 3. Reżyseria 15 minut

### 00:00–03:00 — dwadzieścia części

- natychmiastowe przejęcie pulpitu po `T0` przez glitch, przesunięcia i
  przygaszenie UI, bez klasycznego fade-to-black;
- ambient wejścia jest odrębny od SFX wysłania, który czeka na ghost.signal_sent;
- 20 części buduje jeden układ; pokazujemy aktywacje i połączenia;
- tło: odkrywcy, właściciele, klany, miejsca, konflikty i historyczne logi;
- konflikt zamykający i ostatnia część dostają wyraźny, lecz krótki akcent;
- nie prezentujemy fałszywych stanów, których nie ma w lock snapshotcie.

Odcinki: 00:00–00:15 przejęcie UI i powolny ruch mapy; 00:15–00:30
aktywacja warstwy sieci; 00:30–01:00 wejście części według discovered_at
(przy niepełnej historii canonical ordering); 01:00–01:30 komplet 20 części
w nieregularnym układzie; 01:30–02:00 rzeczywiste połączenia; 02:00–02:20
półprzezroczyste logi w stałym obszarze; 02:20–02:40 skrót zapisanych zmian
stanów; 02:40–03:00 grupowanie 4 × 5 w barwach klanów.

### 03:00–06:00 — maszyny i GhostNetwork

- części składają się w cztery maszyny;
- maszyny łączy topologia GhostNetwork;
- mapa przechodzi przez kontrolowane glitche i warstwy połączeń;
- wykorzystujemy estetykę BlackNetu i Secret Path bez otwierania zwykłych,
  interaktywnych aplikacji;
- logi opisują realną topologię, progres i lineage zakończonego cyklu.

03:00–05:00: cztery grupy po 30 s, z nazwą maszyny, klanem i pięcioma
częściami, jeszcze bez hero assetu. 05:00–05:20 rozsunięcie grup w jedną
sieć; 05:20–05:40 pierwszy regularny okrąg 20 części; 05:40–05:50 naprężenie
połączeń i przepływ energii; 05:50–06:00 aktywacja, mocny glitch i wygaszenie.
Regularność pojawia się dopiero od 05:20; geometria nie tworzy nowych relacji.

### 06:00–08:00 — uzbrojenie i wysłanie GhostSignal

- sieć osiąga pełną synchronizację i przechodzi w stan uzbrojenia;
- pulpit, mapa i GhostNetwork reagują wspólną sekwencją zakłóceń;
- canonical `signal_sent` wyzwala najmocniejszy cue transmisji: błysk, glitch,
  załamanie UI, SFX i zmianę warstwy muzycznej;
- moment nie jest przedstawiony jako zwykłe dojście paska do 100%;
- jeżeli commit `signal_sent` nastąpił wcześniej, reconnect pokazuje właściwy
  późniejszy stan bez ponownego emitowania kulminacyjnego SFX.

06:00–07:00: cztery hero assety maszyn po 15 s (nazwa, klan, profesja,
superpower/superpowers, PARTS 5/5 z canonical config). 07:00–07:05
wygaszenie i wyciszenie ambientu. 07:05–07:43,12: 38,12 s filmu w centralnej ramce,
z żywą mapą, logami i telemetrią w tle, bez pełnoekranowego zastąpienia sceny.
Film jest rekonstrukcją wizualną potwierdzonego zdarzenia, nie przygotowaniem
przyszłej operacji backendu. Retrospekcja jest czytelnie oznaczona.

Przy istniejącym potwierdzeniu ghost.signal_sent: 07:43,12–07:46,12 wizualny replay
błysku/glitchu bez ponownego SFX i bez drugiej emisji,
07:46,12–07:49,12 kurczenie światła do punktu i ciemność, 07:49,12–07:57 terminal 2108
z zatwierdzonym tekstem/typewriter, 07:57–08:00 „GHOSTSIGNAL WYSŁANY”
w estetyce Secret Path/Superpowers oraz przejście daty transmisji w datę 2108.
Te czasy dotyczą montażu retrospekcji, nie momentu emisji. Bez potwierdzenia
scena nie pokazuje sukcesu i pozostaje w istniejącym trybie recovery 139.

### 08:00–12:00 — rozliczenie starego świata

- wizualizujemy terytoria zachowane, skonsumowane i zredukowane;
- pokazujemy konsekwencje konfliktów i zmianę mapy jako replay z receipts, nie
  jako żywą, interaktywną mapę;
- pojawiają się nagrody, uczestnicy, klany, profesje, SP i udział w sieci;
- dane przechodzą stopniowo w ranking; UI zachowuje czytelność na mobile;
- sekwencja nie zdradza informacji spoza publicznego/audience-safe manifestu.

08:00–08:15 aftershock / WORLD SETTLEMENT; 08:15–08:45 mapa sprzed
rozliczenia ze snapshotu; 08:45–09:15 oznaczenie losów terytoriów;
09:15–09:45 animacja rzeczywistej redukcji/konsumpcji; 09:45–10:15 wpływ
konfliktów; 10:15–10:30 FINAL WORLD STATE, po którym nie wracamy do starej
mapy; 10:30–11:00 ledger nagród; 11:00–11:20 gracze; 11:20–11:40 osiągnięcia;
11:40–12:00 wyniki klanów. PRESERVED/REDUCED/CONSUMED/CONFLICT RESOLVED
są propozycjami etykiet, które muszą mieć potwierdzenie w istniejących danych.
Frontend odtwarza wynik backendu; nie rozstrzyga losu terytoriów ani nagród.

### 12:00–14:00 — odbudowa CHAOS

- rekonstrukcja terminala, Googleplexu, Pro Tools, aplikacji, plików, logów,
  BlackNetu i newsów;
- istniejące efekty Secret Path i systemowe logi są odtwarzane przez director,
  a nie przez uruchamianie ich gameplayowych side effects;
- pulpit składa się warstwami do wersji docelowej;
- radio prowadzi napięcie do końcowej fazy; utwory są wybierane z manifestu.

12:00–12:20 SYSTEM RESET LAYER; 12:20–12:40 Googleplex; 12:40–13:00
Pro Tools/terminal; 13:00–13:20 pliki i dane; 13:20–13:40 BlackNet/history;
13:40–13:55 składanie pulpitu; 13:55–14:00 „CHAOS CORE RESTORED” lub
zatwierdzony odpowiednik. To reprezentacja istniejących systemów,
bez uruchamiania nowych podsystemów, operacji gry lub nowego cyklu.

### 14:00–15:00 — ranking, shutdown i nowy cykl

- finalny ranking graczy, klanów, terytoriów i wyników;
- potwierdzenie Signal Registry oraz identyfikatora zakończonego sygnału;
- domknięcie rekonstrukcji, kontrolowany shutdown i boot vNext;
- po durable `next_cycle_active` wykonanie kontraktu restartu ze Sprintu 139;
- pierwszy nowy pulpit pokazuje ikonę Signal Registry i nie wznawia starych
  okien mapy/narzędzia.

14:00–14:15 ranking graczy; 14:15–14:30 ranking klanów według istniejącej
miary; 14:30–14:40 statystyki cyklu; 14:40–14:50 „GHOST NETWORK CYCLE
ARCHIVED”, wyłącznie przy gotowym archiwum/wynikach; 14:50–14:56 wygaszenie
logów, rankingu, mapy i narzędzi; 14:56–15:00 shutdown.
Po granicy cyklu wraca normalny CHAOS, Signal Registry, wyniki i statystyki.
Zachowujemy kolejność 139: backend waliduje settlement i aktywuje następcę,
publikuje restart epoch, klient wykonuje boot i ACK. Opis „nowy cykl po
restarcie” oznacza doświadczenie gracza, nie tworzenie cyklu przez klienta.

## 4. Warstwy realizacyjne

### 4.1. GhostSignal Show Director

Jeden director odpowiada za:

- wybór sceny z czasu serwera;
- exactly-once cue dla krytycznych SFX/glitch/transmission;
- wejście/wyjście warstw mapy, pulpitu i terminala;
- catch-up po reconnect oraz synchronizację wielu kart;
- obsługę prefers-reduced-motion, wyciszenia i utraty focusu;
- telemetrię scen, brakujących assetów i błędów renderera.

Director jest rozwinięciem istniejącego kontrolera show; nie tworzymy drugiego
silnika stanów, schedulerów ani osobnego systemu receiptów. Nie mutuje gameplayu
i nie jest źródłem danych rozliczeniowych. Stany scen są projekcją prezentacji.

### 4.2. Biblioteka istniejących efektów

Przed montażem powstaje katalog reusable cue:

- BlackNet overlays i typografia;
- map glitch, linie, obszary, wygaszanie markerów;
- Secret Path/SP boot, logs, scanlines, distortion;
- terminal streams i system reconstruction;
- desktop shutdown/boot;
- radio beds, stingers i GhostSignal SFX.

Każdy asset ma identyfikator, format, długość, koszt pamięci, wariant mobile,
fallback oraz informację o prawach/licencji. Nie kopiujemy efektów ad hoc między
plikami.

### 4.3. Dodatkowe assety od autora

Wymagane: cztery hero assety kompletnych maszyn, stylistycznie wywiedzione
z ich pięciu części, oraz dostarczony film 38,12 s w ramce do retrospekcji
transmisji. Zachowujemy istniejący SFX sygnału. Terminal 2108 korzysta
z zatwierdzonego zestawu tekstów; żaden asset nie zawiera logiki emisji.

Nowe materiały trafiają przez manifest zawierający:

```text
asset_id
scene/cue
file + format
duration
desktop/mobile variant
loop/fade rules
audio loudness
fallback_asset_id
license/source
```

Brak jeszcze niedostarczonego assetu nie blokuje implementacji mechaniki; scena
używa jawnego placeholdera/fallbacku możliwego do późniejszej podmiany.

## 5. Podział sprintu

### 140.1 — audyt źródeł, manifest i rozwinięcie istniejącego kontrolera

- utrwalić format manifestu v2 i audience projection;
- wykonać pełny audyt 24 źródeł wymienionych w §16 szczegółowego scenariusza:
  katalog/topologia, lifecycle/właściciele, terytoria/konflikty, historia
  publikacji, rewards, statystyki/miara klanu, ranking/archiwum i call flow;
  przy każdym wskazać istniejące źródło, publiczność, limit i zachowanie przy braku;
- zinwentaryzować istniejące efekty, SFX i radio;
- rozwinąć istniejący kontroler o server-clock seek i deduplikację cue
  przez istniejące mechanizmy, bez nowej authority dla restartu/transmisji;
- przygotować low-cost fallback dla każdego segmentu.

### 140.2 — części, maszyny, sieć i transmisja (00–08)

- zmontować 20 części oraz cztery maszyny z prawdziwych danych;
- dodać topologię, map glitch, BlackNet i Secret Path layers;
- zbudować kulminację uzbrojenia i `signal_sent`;
- potwierdzić natychmiastowy show oraz SFX wyłącznie przy ghost.signal_sent;
  scena retrospekcji nie ponawia dźwięku ani operacji.

### 140.3 — świat, wyniki i rekonstrukcja (08–14)

- replay konsumpcji/redukcji terytoriów z receipts;
- nagrody, uczestnicy i ranking preview;
- warstwowe odtworzenie aplikacji, plików, terminala i newsów;
- wykorzystać historyczne, zaakceptowane narracje bez nowych model calls.

### 140.4 — ranking, radio, reboot i dostępność (14–15)

- finalny ranking i Signal Registry handoff;
- dedykowana ścieżka radiowa/SFX i reguły miksu;
- shutdown/boot spięty z kontraktem 139;
- reduced motion, captions, mute, przerwanie audio i wznowienie aplikacji.

### 140.5 — mobile performance, soak i production polish

- test Redmi/telefon o ograniczonej pamięci oraz desktop;
- profil CPU, GPU, pamięci, liczby DOM nodes i canvas layers;
- preload tylko najbliższego segmentu, zwalnianie zasobów po scenie;
- recovery po background/foreground, zmianie orientacji i utracie sieci;
- pełny 15-minutowy E2E z zapisem telemetrii i ręcznym odbiorem artystycznym.

## 6. Budżety jakości

- brak długiej pracy synchronicznej blokującej UI;
- brak ciężkich odczytów profili w pętli renderera;
- bounded manifest i lazy preload scen;
- utrzymanie zegara mimo spadku FPS;
- brak powtórnego kulminacyjnego SFX po reloadzie;
- czytelny wariant mobile bez nakładania tekstów i uciętych nazw;
- warstwa audio respektuje ustawienia użytkownika i politykę autoplay;
- błąd opcjonalnego efektu jest raportowany i izolowany.

## 7. Testy i odbiór

Automatyczne:

- phase/seek na granicach każdej sceny;
- event cue exactly-once i reconnect catch-up;
- transmisja nadal zachodzi według 139, a film/replay nie wywołuje operacji
  ani ponownego SFX; brak potwierdzenia nigdy nie daje ekranu sukcesu;
- jedna trwała data 2108 dla wszystkich klientów, również po reconnect;
- replay świata sprzed settlementu nie pobiera zmienionego świata live;
- manifest schema, audience safety i bounded payload;
- brak model calla z show directorem;
- asset fallback i awaria pojedynczej warstwy;
- restart handoff do Sprintu 139;
- desktop/mobile viewport i reduced motion.

Manualne:

- pełne 15 minut bez pustych, statycznych odcinków;
- moment `signal_sent` jest bezdyskusyjnie kulminacją;
- historia pozostaje czytelna bez znajomości logów technicznych;
- efekty są spójne z CHAOS, a nie zbiorem przypadkowych animacji;
- radio i SFX wspierają tempo, nie zagłuszają informacji;
- po finale nowy pulpit i Signal Registry pojawiają się automatycznie.

## 8. Definition of Done

Sprint 140 otrzymuje `PASS`, gdy jeden canonical production E2E potwierdzi:

- natychmiastowe przejęcie ekranu zapewnione przez Sprint 139;
- ciągłą, piętnastominutową reżyserię wszystkich sześciu segmentów;
- zgodność scen z prawdziwymi danymi zakończonego cyklu;
- poprawne zachowanie po reloadzie, uśpieniu telefonu i drugim urządzeniu;
- brak wpływu Ollamy i opcjonalnych assetów na mechaniczny settlement;
- stabilny mobile/desktop runtime;
- automatyczny shutdown, reboot, nowy cykl i Signal Registry.

## 9. Poza zakresem

- zmiana mechaniki GhostNetwork, nagród i rankingu;
- publikowanie niezweryfikowanych treści modelu w trakcie finału;
- interaktywna gra podczas show;
- dokładanie nowych mediów narracyjnych niezwiązanych z finałem;
- restart usług serwerowych jako element oprawy.

## 10. Realizacja 140.1 — 2026-09-11

Audyt źródeł i materiałów:
[140.1 — sources and assets](../audits/140-1-show-sources-and-assets.md).
Sprawdzono 24 pozycje scenariusza, call flow show, kontroler, katalog,
ścieżkę SFX i kontrakt lekkich profili. Wcześniejsze lokalne zmiany
scenariusza autora zachowano. Nie zmieniono transmisji, locka, deadline'u,
settlementu, restart epoch ani ACK z 139.

Dodano bounded manifest v2 do istniejącego /api/ghostnetwork/show: 49 scen,
publiczny katalog części/maszyn/profesji/zdolności, status sent/rankingu,
stałe identyfikatory pięciu oczekiwanych assetów i ich fallbacki.
Osobny moduł show_manifest zawiera wyłącznie definicje i budowę projekcji;
nie jest nowym systemem runtime. Istniejący kontroler używa sceneAt do seek
według show_started_at/show_ends_at oraz offsetu serwera. Nie uruchamia SFX,
operacji, preloadu ani nowych timerów. Po deadline nadal oczekuje na 139.

Renderer 140.1 jest tekstowym fallbackiem scen. Invalid/missing manifest
zachowuje renderer 139. Sceny od retrospekcji emisji wymagają potwierdzenia
signal_sent; bez niego wyświetlają oczekiwanie. Nie twierdzą, że zakończenie
filmu oznacza wysłanie. Wersja cache skryptu: signal-show-140-1.

Złożone dane cyklu mają jawny status scene_projection_pending: projekcje
historii, mapa przed settlementem, nagrody i ranking będą podpinane z
audytowanych źródeł w etapach scen. Data 2108 nie jest jeszcze generowana
ani prezentowana; jej trwały kontrakt musi być gotowy przed sceną terminala.
Nie ma fallbacku do profili/live world ani gotowych fikcyjnych danych.

Walidacja: baseline show/transmisja 23 PASS (43,276 s); regresja manifest,
show, HTTP, client restart i transmisja 40 PASS (140,060 s).
Frontend show, recovery/lock/iframe, manifest seek/gate/fallback, delta client
oraz node --check PASS. Pomiar projekcji: dwa SELECT-y i cztery PRAGMAs,
niezależnie od 8 B / 35 MB danych; brak odczytu signal payload/ranking JSON.
Końcowy test wymusza zera metryk heavy profile i all-user scan.
Po końcowym doprecyzowaniu lookupu canonical eventu i kopiowania list katalogu:
2 testy manifestu PASS (1,655 s), py_compile PASS; manifest 15 694 B.

### Pierwsza bramka serwerowa 140.1

Po operatorskim commit/push i pullu, przed reloadem web:

```bash
.venv/bin/python -B - <<'PY'
import os, shutil, sys, tempfile, unittest
root = os.getcwd()
sys.path[:0] = [root, os.path.join(root, "tests")]
with tempfile.TemporaryDirectory(prefix="chaos140-1-") as tmp:
    try:
        os.makedirs(os.path.join(tmp, "static", "js"))
        for name in ("session_generation.js", "terminal.js"):
            shutil.copyfile(os.path.join(root, "static", "js", name),
                            os.path.join(tmp, "static", "js", name))
        shutil.copyfile(os.path.join(root, "run.py"), os.path.join(tmp, "run.py"))
        os.chdir(tmp)
        os.environ["CHAOS_SESSION_FILE_DIR"] = os.path.join(tmp, "sessions")
        names = ["test_ghostnetwork_show_manifest", "test_ghostnetwork_signal_show",
                 "test_ghostnetwork_signal_show_http", "test_ghostnetwork_client_restart",
                 "test_ghostnetwork_transmission"]
        result = unittest.TextTestRunner().run(
            unittest.defaultTestLoader.loadTestsFromNames(names))
    finally:
        os.chdir(root)
sys.exit(not result.wasSuccessful())
PY
node tests/ghost_signal_show_frontend.test.js
node tests/ghost_signal_show_recovery.test.js
node tests/ghost_signal_show_manifest.test.js
node tests/js/test_ghostnetwork_delta_client.js
node --check static/js/ghost_signal_show.js
```

Brak nowej migracji bazy. Po PASS wystarcza reload chaos; kod workera/SFX
nie zmienia się. Smoke: zwykły desktop/mobile, brak błędów API/show,
wejście do mapy, oraz frontendowy podgląd manifestu bez triggera świata.
Mieszane wersje po pullu są obsługiwane przez legacy fallback. Nie trzeba
przywracać bazy ani wysyłać nowego GhostSignal dla tej bramki.
Pełny produkcyjny odbiór reżyserii pozostaje w 140.5.

### Wynik serwerowy 140.1 i odbiór assetów — 2026-09-11

Operator wdrożył `7a7d03c`: 40 testów Python PASS (222,790 s), cztery
zestawy JS PASS, node --check bez błędów. Reload chaos potwierdzony, PM2 13
online. Nie zgłoszono jeszcze osobnego wyniku smoke/podglądu scen manifestu.

Dostarczono osiem PNG w static/images/ghostnetwork/signal_sends: po jednym
wariancie podstawowym i _active dla czterech maszyn. Warianty podstawowe
1254×1254 mają rzeczywisty kanał alfa; _active 1672×941 nie mają kanału alfa.
Istniejące 20 części w parts/ ma 128×128 i przezroczystość. W pullu nie ma
nowych osobnych plików części; nie zakładamy istnienia dodatkowych wersji
o większej rozdzielczości. Film 30 s jest przygotowywany przez autora.
Pliki zinwentaryzowane; manifest nadal ma fallback do czasu podłączenia
rendererów/assetów. Nie wykonano zmian runtime w ramach tego odbioru.

## 11. Realizacja 140.2 — pierwszy montaż 00:00–08:00

Zachowano lokalne wpisy odbioru 140.1. Operator sprostował, że nowe
przezroczyste assety dotyczą maszyn, nie części. Wykorzystano cztery
podstawowe maszyny RGBA oraz istniejące części 128×128; warianty _active
są zarejestrowane w metadanych, ale nie są ładowane jako nieprzezroczyste
nakładki. Film autora jest podłączony jako wyciszony zapis archiwalny, bez wywoływania emisji.

### Dane i call flow

Istniejący rekord ghost_signal_shows rozszerzono o scene_snapshot_json.
Transmisja przygotowuje małą projekcję z już odczytanego lock snapshotu
przed writerem i zapisuje ją razem z show. Kolejność commitów/effects,
deadline, SFX, settlement, rollover i restart/ACK 139 nie zmieniają się.
Nie dodano osobnego magazynu, workera ani silnika scen.

Projekcja zawiera maksymalnie 20 części (kod, stan w locku, rzeczywiste daty
discovery/activation, poprawne współrzędne), 20 kodów ring topology oraz
jedną datę 2108, wybraną deterministycznie na backendzie z signal_id i zapisaną
z show. Nie stosuje +82 lata ani losowania w przeglądarce. Brak właścicieli,
profili, target payloadów, live world i generacji Ollamy. Historyczne show
nie są backfillowane; bez projekcji działają canonical/text fallbacki.

### Montaż w istniejącym kontrolerze

- 00–03: stopniowe przejęcie UI, wejście części według kompletnych dat
  discovery lub porządku katalogu, rzeczywiste połączenia, zapisane daty
  w logach oraz grupowanie 4 × 5. Nie pokazuje nieistniejącej historii containment.
- 03–06: wyróżnienie kolejnych grup, wspólna sieć i regularny ring według
  snapshotu. Bez topologii nie rysuje się wymyślonych krawędzi.
- 06–07: przezroczyste hero assety maszyn, nazwa/klan/części i pięć profesji
  oraz zdolności odpowiadających częściom.
- 07–08: pełny film 38,12 s z tekstowym fallbackiem, wizualny replay emisji bez SFX,
  punkt światła, terminal odtwarzany według czasu serwera oraz faktyczna data
  wysłania i trwała data 2108. Brak sent utrzymuje istniejące oczekiwanie.

Warstwa tła pokazuje zapisane pozycje węzłów na siatce współrzędnych;
nie jest pełną mapą terytoriów. Pełny zamrożony świat i rozliczenie mapy
pozostają w 140.3. Logi 140.2 obejmują dostępne daty części; dodatkowe
historyczne publikacje nadal wymagają projekcji audience-safe.
Brak nowych fetchy gameplayowych, nowych timerów i odtwarzania audio.
Obrazy ładowane tylko dla widocznej sceny, usuwane przy zmianie/ukryciu;
onerror daje tekst. Tekst podsumowania/lock działa również po awarii montażu.
Reduced motion wyłącza dryf i błysk replayu; mobile ma pionowy układ hero.

### Walidacja lokalna

25 testów show/manifest/transmisja PASS (74,223 s), następnie regresja
53 testów Python PASS (154,451 s): HTTP, restart, transmisja i strict audyty.
Po dodaniu testu migracji końcowe 4 testy PASS (4,254 s).
Pięć zestawów JS PASS: frontend, recovery, manifest/layout, montage/fallback,
delta. node --check, py_compile oraz generowanie podglądu PASS.
Test potwierdza przygotowanie projekcji poza writerem, jej niezmienność
po konsumpcji i retry, brak prywatnych ownerów, datę 2108 i poprawną topologię.
Migracja domyślnie read-only, idempotentna, zachowuje historyczne rekordy.

Browser skill nie znalazł dostępnej przeglądarki (lista pusta). Nie wykonano
automatycznego ani operatorskiego odbioru wizualnego 140.2. Etap nie jest
zamknięty; lokalne testy nie zastępują oceny kompozycji i mobile.

### Bramka serwerowa 140.2

Po commit/push i pull, przed reloadem: uruchomić izolowane testy z §10,
dodając do listy names `test_ghostnetwork_endgame_audits` (łącznie 54 testy),
oraz `node tests/ghost_signal_show_montage.test.js` do zestawów JS.
Następnie plan migracji:

```bash
.venv/bin/python -B scripts/migrate_ghostsignal_scene_snapshot.py --db data/game.sqlite3
```

Przed apply obowiązuje świeży backup SQLite, quick_check i SHA-256 według
handoffu. Zakres: jedno pole scene_snapshot_json, zero backfillu starego show.
Po zatwierdzeniu planu:

```bash
.venv/bin/python -B scripts/migrate_ghostsignal_scene_snapshot.py --db data/game.sqlite3 --apply
.venv/bin/python -B scripts/migrate_ghostsignal_scene_snapshot.py --db data/game.sqlite3
```

Po schema_change=false i PASS testów przeładować chaos oraz
chaos-territory-worker, ponieważ przygotowanie projekcji działa w transmisji.
Nie reloadować workerów narracji. Zwykły desktop/mobile smoke, brak nowych
błędów; SFX bez zmian. Nie uruchamiać nowego finału dla podglądu.

### Podgląd scen bez transmisji

Generator tworzy stronę demonstracyjną, bez dostępu do bazy i bez eventów:

```bash
.venv/bin/python -B tools/build_ghostsignal_show_preview.py --output static/previews/ghostsignal-140-2.html
```

Otworzyć `/static/previews/ghostsignal-140-2.html` na wdrożonej aplikacji.
Strona jest jawnie oznaczona jako demo, korzysta z katalogu i jego topology
anchor, nie z historii produkcyjnego cyklu. Ma wybór scen, suwak 0–479 s
i przełącznik potwierdzenia sygnału. Wszystkie fetch w tej osobnej stronie
są lokalną atrapą; nie zmienia globalnego fetch w prawdziwych sesjach gry.
Nie nadpisuje istniejącego pliku podglądu. Wygenerowanego HTML nie commitować.
Sprawdzić: 20 części, cztery grupy, ring, cztery hero, brak SFX przy seek,
film (w tym seek w jego środek), terminal i potwierdzenie, powrót do wcześniejszej sceny,
wariant mobile oraz waiting przy odznaczeniu potwierdzenia emisji.

### Film autora i korekta montażu — 2026-09-11

`static/video/ghostsignal_transmission_video.mp4`: ffprobe potwierdza 38,120 s,
H.264/yuv420p, 720×480, 25 fps, AAC, 7 003 148 bajtów; dodatkowy strumień MJPEG
jest okładką. Źródło pozostaje niezmienione. Film wyciszony, playsinline,
object-fit: contain. Odtwarzanie 07:05–07:43,12 w oryginalnym tempie;
replay 07:43,12–07:46,12, punkt do 07:49,12, terminal do 07:57,
potwierdzenie do 08:00. Zegar 900 s i kontrakt 139 pozostają bez zmian.

Seek/recovery koryguje currentTime istniejącym tickiem, również po późnym
załadowaniu metadanych. Błąd zasobu lub odmowa autoplay daje tekst zastępczy.
Zmiana sceny/ukrycie zatrzymuje film i zwalnia src; koniec filmu nie emituje
eventów. Testy JS obejmują wejście w środek, korektę czasu, cleanup i onerror.
Odbiór wizualny autoplay/mobile wymaga podglądu na serwerze.

Końcowa regresja po podłączeniu filmu: 54 testy Python PASS (170,769 s),
pięć zestawów JS i node --check PASS. Pełne dekodowanie MP4 przez ffmpeg
bez błędów. Kompletna procedura: [deploy_140_2.md](../runbooks/deploy_140_2.md).

### Doprecyzowanie autora: pole filmu i cztery MP3

Kod 678e82f został przez operatora opublikowany i pobrany na serwerze.
Sam pull nie potwierdza migracji, reloadu ani odbioru wizualnego.
Dalsza poprawka 140.2: pole filmu 3:2, maksymalnie 720×480 CSS px,
responsywne pomniejszanie bez rozciągania i kadrowania. Brak kontrolek,
fokusu, interakcji wskaźnika, fullscreen, PiP i remote playback w odtwarzaczu.
Wbudowane mechanizmy przeglądarki/rozszerzeń pozostają poza kontrolą strony.

Autor podał łączny czas czterech MP3: 14:20 (860 s). Nazwy docelowe:

- static/audio/ghostnetwork/show/ghostsignal_show_part_01.mp3
- static/audio/ghostnetwork/show/ghostsignal_show_part_02.mp3
- static/audio/ghostnetwork/show/ghostsignal_show_part_03.mp3
- static/audio/ghostnetwork/show/ghostsignal_show_part_04.mp3

Pliki to kolejne części jednej ścieżki; ich indywidualne długości i granice
zostaną odczytane po dostarczeniu, bez założenia czterech równych odcinków.
860 s muzyki + 38,12 s filmu = 898,12 s. Ostatnie 1,88 s show pozostaje ciszą.
Nie zmieniamy deadline 900 s ani restartu/ACK 139.

Plan 140.4 rozszerza istniejący GhostRadio (ghost_radio.js), jego ustawienia
volume/mute i mechanizm requestDuck/releaseDuck; bez osobnego radia lub miksera.
Show czasowo zastępuje program radia, zachowuje poprzedni stan i nie zapisuje
tej zamiany jako preferencji użytkownika. Po show/nowym boot przywraca zwykłą
politykę radia, także gdy przed show było zatrzymane lub wyciszone.

Od 425 do 463,12 s tło jest niesłyszalne i zatrzymane. Po filmie wraca od
tego samego miejsca. Pozycja ścieżki przy reconnect wynika z zegara show:
t dla t<425; 425 podczas filmu; t-38,12 po filmie; po 860 s ścieżki cisza.
Wybór części i offset wynikają z sum zmierzonych długości MP3, nie z callbacku
ended. Spóźnione ładowanie/seek nie restartuje muzyki i nie przesuwa scen.
Brak assetu/autoplay nie blokuje show. Preferencje mute pozostają nadrzędne.
SFX ghost.signal_sent zachowuje własny istniejący trigger i nie jest częścią MP3.
Dźwięk AAC filmu wymaga jeszcze ustalenia z autorem; bieżące 140.2 nadal
odtwarza film wyciszony. Przełączenie miksu nastąpi razem z obsługą tła.

140.3 pozostaje etapem rozliczenia świata; 140.4 obejmuje powyższą integrację
całego 15-minutowego audio, ranking i restart. Odbiór: radio gra/nie gra/mute,
cztery przejścia plików, pauza i wznowienie przy filmie, reconnect w każdej
części i filmie, brak podwójnego audio w iframe, cleanup/restart, autoplay
zablokowane i brak MP3. Końcowe E2E pozostaje w 140.5.

### Odbiór czterech MP3 — pomiar plików

Wszystkie pliki w static/audio/ghostnetwork/show/ przeszły pełne dekodowanie
ffmpeg bez błędów. MP3 stereo, 44,1 kHz, około 128 kb/s.

| Plik | Bajty | Czas [s] |
| --- | ---: | ---: |
| ghostsignal_show_part_01.mp3 | 3259935 | 203,702813 |
| ghostsignal_show_part_02.mp3 | 3376128 | 210,964875 |
| ghostsignal_show_part_03.mp3 | 3746022 | 234,083250 |
| ghostsignal_show_part_04.mp3 | 3381561 | 211,304438 |

Łącznie 13 763 646 B (13,76 MB), 860,055376 s. Wcześniejsze 860 s było
zaokrągleniem autora. Z filmem 38,12 s otrzymujemy 898,175376 s, więc końcowa
cisza wynosi około 1,825 s. Dla integracji 140.4 obowiązują zmierzone długości;
nie przycinamy muzyki do zaokrąglonego czasu. Pliki gotowe do publikacji,
bez potrzeby dodatkowej kompresji na tym etapie. Ładowanie scenami/częściami,
z przygotowaniem następnej części, bez jednoczesnego pobierania całego pakietu.
To odbiór techniczny zasobów, nie potwierdzenie wdrożenia miksu audio.
