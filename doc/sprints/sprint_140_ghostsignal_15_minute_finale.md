# Sprint 140 — GhostSignal: pełny 15-minutowy finał CHAOS

Status: `PLANNED / SPRINT 139 MECHANICS PASS`

Bramka Sprintu 139 zaliczona 2026-09-11; dowody:
`doc/audits/139-4-production-e2e-summary.md`.
Decyzja operatora: zachować istniejące przypisanie SFX sygnału do
`ghost.signal_sent` i wykorzystać ten moment w reżyserii Sprintu 140.

Źródło produktowe: `doc/sprints/sprint_139_opis_15-minutowe_show.md`

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

Zdarzenia faktyczne, takie jak `signal_sent`, ranking gotowy lub next cycle
active, mogą podbić cue wewnątrz przypisanego segmentu. Nie mogą cofnąć osi ani
rozciągnąć globalnego deadline'u. Brak opcjonalnego źródła danych degraduje
warstwę wizualną, ale nie zatrzymuje finału.

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

### 2.4. Graceful degradation

Minimalna ścieżka awaryjna nadal pokazuje fazę, czas, canonical fakty i końcowy
restart. Brak radia, pojedynczego assetu, WebGL/canvas lub dźwięku nie może
odblokować gameplayu ani wywalić całego show.

## 3. Reżyseria 15 minut

### 00:00–03:00 — dwadzieścia części

- natychmiastowy blackout/przejęcie pulpitu po `T0`;
- wejście SFX może działać równolegle, bez opóźniania ekranu;
- 20 części buduje jeden układ; pokazujemy aktywacje i połączenia;
- tło: odkrywcy, właściciele, klany, miejsca, konflikty i historyczne logi;
- konflikt zamykający i ostatnia część dostają wyraźny, lecz krótki akcent;
- nie prezentujemy fałszywych stanów, których nie ma w lock snapshotcie.

### 03:00–06:00 — maszyny i GhostNetwork

- części składają się w cztery maszyny;
- maszyny łączy topologia GhostNetwork;
- mapa przechodzi przez kontrolowane glitche i warstwy połączeń;
- wykorzystujemy estetykę BlackNetu i Secret Path bez otwierania zwykłych,
  interaktywnych aplikacji;
- logi opisują realną topologię, progres i lineage zakończonego cyklu.

### 06:00–08:00 — uzbrojenie i wysłanie GhostSignal

- sieć osiąga pełną synchronizację i przechodzi w stan uzbrojenia;
- pulpit, mapa i GhostNetwork reagują wspólną sekwencją zakłóceń;
- canonical `signal_sent` wyzwala najmocniejszy cue transmisji: błysk, glitch,
  załamanie UI, SFX i zmianę warstwy muzycznej;
- moment nie jest przedstawiony jako zwykłe dojście paska do 100%;
- jeżeli commit `signal_sent` nastąpił wcześniej, reconnect pokazuje właściwy
  późniejszy stan bez ponownego emitowania kulminacyjnego SFX.

### 08:00–12:00 — rozpad i rekonstrukcja świata

- wizualizujemy terytoria zachowane, skonsumowane i zredukowane;
- pokazujemy konsekwencje konfliktów i zmianę mapy jako replay z receipts, nie
  jako żywą, interaktywną mapę;
- pojawiają się nagrody, uczestnicy, klany, profesje, SP i udział w sieci;
- dane przechodzą stopniowo w ranking; UI zachowuje czytelność na mobile;
- sekwencja nie zdradza informacji spoza publicznego/audience-safe manifestu.

### 12:00–14:00 — odbudowa CHAOS

- rekonstrukcja terminala, Googleplexu, Pro Tools, aplikacji, plików, logów,
  BlackNetu i newsów;
- istniejące efekty Secret Path i systemowe logi są odtwarzane przez director,
  a nie przez uruchamianie ich gameplayowych side effects;
- pulpit składa się warstwami do wersji docelowej;
- radio prowadzi napięcie do końcowej fazy; utwory są wybierane z manifestu.

### 14:00–15:00 — ranking, shutdown i nowy cykl

- finalny ranking graczy, klanów, terytoriów i wyników;
- potwierdzenie Signal Registry oraz identyfikatora zakończonego sygnału;
- domknięcie rekonstrukcji, kontrolowany shutdown i boot vNext;
- po durable `next_cycle_active` wykonanie kontraktu restartu ze Sprintu 139;
- pierwszy nowy pulpit pokazuje ikonę Signal Registry i nie wznawia starych
  okien mapy/narzędzia.

## 4. Warstwy realizacyjne

### 4.1. GhostSignal Show Director

Jeden director odpowiada za:

- wybór sceny z czasu serwera;
- exactly-once cue dla krytycznych SFX/glitch/transmission;
- wejście/wyjście warstw mapy, pulpitu i terminala;
- catch-up po reconnect oraz synchronizację wielu kart;
- obsługę prefers-reduced-motion, wyciszenia i utraty focusu;
- telemetrię scen, brakujących assetów i błędów renderera.

Director nie mutuje gameplayu i nie jest źródłem danych rozliczeniowych.

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

### 140.1 — manifest danych, director i asset inventory

- utrwalić format manifestu v2 i audience projection;
- zinwentaryzować istniejące efekty, SFX i radio;
- zaimplementować director, server-clock seek i exactly-once cue receipts;
- przygotować low-cost fallback dla każdego segmentu.

### 140.2 — części, maszyny, sieć i transmisja (00–08)

- zmontować 20 części oraz cztery maszyny z prawdziwych danych;
- dodać topologię, map glitch, BlackNet i Secret Path layers;
- zbudować kulminację uzbrojenia i `signal_sent`;
- potwierdzić równoległy start show/SFX bez race condition.

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
- ciągłą, piętnastominutową reżyserię wszystkich pięciu segmentów;
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
