# Sprint 140 — szczegółowy scenariusz GhostSignal Final Show

Aktualizacja audio 140.4: autor zatwierdził dźwięk AAC filmu oraz nakładanie
wejścia przez 0,5 s. Obowiązuje fade-out MP3 425–425,5 s, pauza 425,5–463,12 s
i fade-in 463,12–463,62 s. Cztery MP3 kończą się w 897,675376 s; końcowa cisza
to około 2,325 s. Ta decyzja zastępuje wcześniejsze zapisy o wyciszeniu filmu
i pauzie trwającej całe 38,12 s. Kolejność/zakres scen 140.3 zaakceptowane;
tempo podlega odsłuchowi, a stylizacja pozostaje w 140.stylization.1+.

Scenariusz autora przekazany 2026-09-11, dostosowany na jego polecenie do zatwierdzonego Sprintu 139. Plan wykonawczy: [Sprint 140](sprint_140_ghostsignal_15_minute_finale.md). Godziny oznaczają montaż warstwy prezentacji. Backend wysyła sygnał na początku show; późniejsza scena transmisji jest oznaczoną retrospekcją. Nie zmieniamy harmonogramu, deadline'u, settlementu ani restartu 139.


## 1. Cel

Końcowe show GhostSignal nie jest ekranem oczekiwania ani animowanym preloaderem.

Jest to 15-minutowa wizualizacja faktycznego zamknięcia jednego cyklu Ghost Network:

**20 części → 4 maszyny → Ghost Network → uzbrojenie → emisja GhostSignal → rozliczenie starego świata → redukcja świata → nagrody → statystyki → rekonstrukcja CHAOS → ranking → archiwizacja → restart → nowy cykl.**

Show musi wykorzystywać rzeczywiste dane zakończonego cyklu.

Nie powinno się wymyślać dodatkowej narracji, historii części, relacji, wyników, nazw ani danych.

Materiały Ollamy wykorzystywane podczas show to wyłącznie **historyczne, już zapisane teksty i publikacje**.

Ollama nie generuje podczas show dodatkowej narracji.

---

# 2. Najważniejsza zasada techniczna

Show ma własny serwerowy timeline.

Klient nie decyduje sam, że GhostSignal został wysłany.

Moment emisji następuje wyłącznie wtedy, gdy backend faktycznie zakończy operację wysłania i emituje:

`ghost.signal_sent`

Dopiero ten event uruchamia istniejący SFX i akcent potwierdzenia w bieżącej scenie. Utrwalone potwierdzenie pozwala później pokazać w retrospekcji:

* błysk transmisji,
* wizualne wspomnienie emisji bez ponownego odtwarzania SFX,
* zakłócenie interfejsu,
* reakcję mapy,
* zanik obrazu,
* sekwencję terminala,
* ekran potwierdzający wysłanie.

## Zasada bezwzględna

**SFX wysłania sygnału uruchamia `ghost.signal_sent`.**

Nie:

* timer frontendowy,
* dojście animacji do 100%,
* koniec filmu,
* lokalny callback JavaScript.

Film później rekonstruuje już potwierdzony moment emisji. Faktyczny SFX i akcent wysłania na początku show uruchamia wyłącznie:

`ghost.signal_sent`

Jeżeli operacja wysłania nie powiedzie się, show nie może pokazać komunikatu „GhostSignal wysłany”.

---

# 3. Synchronizacja show

Prezentacja potrzebuje następujących informacji. Mapujemy je na istniejące pola/eventy/projekcje 139; lista nie nakazuje dodania osobnego magazynu stanu ani kolumn o identycznych nazwach:

`signal_id`

`cycle_id`

`show_started_at`

`show_stage`

`signal_sent_at`

`future_2108_timestamp`

`settlement_completed_at`

`restart_at`

Dzięki temu:

* gracz obecny od początku ogląda show normalnie,
* gracz odświeżający stronę wraca do aktualnego miejsca,
* gracz logujący się w połowie show dołącza do aktualnego etapu,
* wszyscy gracze widzą ten sam moment emisji,
* wszyscy gracze widzą tę samą datę z 2108 roku.

---

# 4. DATA SHOW SNAPSHOT

Przed skutkami transmisji zachowujemy dane starego świata przez istniejący lock snapshot i projekcje. Logiczny zestaw danych prezentacji nazywamy:

`ghost_signal_show_snapshot`

Snapshot jest podstawą całej prezentacji; nie tworzy równoległej bazy świata i nie wymaga ciężkich profili. Nie blokujemy natychmiastowego show kosztowną agregacją. Wyniki settlementu, nagrody i ranking dołączamy z gotowych, trwałych danych po ich utworzeniu, bez zmieniania obrazu świata sprzed rozliczenia.

Show nie pobiera dynamicznie zmieniającego się świata po rozpoczęciu rozliczenia.

Snapshot powinien zawierać między innymi:

## Ghost Network

* 20 części,
* canonical part ID,
* canonical part name,
* stan końcowy części,
* machine assignment,
* clan assignment,
* owner,
* historia discovery,
* historia containment,
* historia activation,
* miejsca występowania,
* terytoria związane z częścią,
* konflikty,
* istotne timestampy.

## Maszyny

Dla każdej z 4 maszyn:

* canonical machine ID,
* canonical machine name,
* clan,
* lista pięciu części,
* profesja,
* superpower / superpowers,
* końcowy stan,
* właściciele części,
* uczestnicy aktywacji.

## Świat

* terytoria przed rozliczeniem,
* konflikty,
* właściciele,
* klany,
* powierzchnia / miara,
* terytoria przeznaczone do zachowania,
* terytoria przeznaczone do redukcji,
* terytoria konsumowane,
* wynik końcowego settlementu.

## Gracze

* avatar,
* nick,
* clan,
* profession,
* RSP / odpowiednia punktacja,
* udział w Ghost Network,
* części,
* aktywacje,
* terytoria,
* konflikty,
* osiągnięcia,
* nagrody,
* statystyki dostępne w systemie.

## Narracja historyczna

Wyłącznie zapisane już:

* komunikaty Ollamy,
* BlackNet,
* newsy,
* komunikaty Ghost Network,
* komunikaty klanowe,
* wydarzenia związane z częściami,
* wydarzenia związane z maszynami.

Brak generowania nowych tekstów przez Ollamę podczas show.

---

# 5. 00:00–03:00 — CZĘŚCI

## 00:00–00:15 — przejęcie interfejsu

Normalny interfejs CHAOS zostaje przykryty przez show.

Nie robimy klasycznego fade-to-black.

Ekran zaczyna tracić stabilność:

* krótki glitch UI,
* przesunięcia obrazu,
* pojedyncze zakłócenia,
* przygaszenie normalnych elementów interfejsu.

W tle zaczyna być widoczna mapa CHAOS.

Mapa jest celowo niestabilna.

Porusza się bardzo wolno:

* niewielki zoom in,
* zoom out,
* przesunięcie,
* zatrzymanie,
* kolejne przesunięcie.

Nie pokazujemy jeszcze części.

---

## 00:15–00:30 — aktywacja warstwy Ghost Network

Mapa staje się ciemniejsza.

Dochodzi:

* delikatny szum,
* pierwsze zakłócenia mapy,
* bardzo subtelne linie,
* pojedyncze elementy UI Ghost Network.

Na ekranie nie ma jeszcze regularnego wzoru.

Wszystko ma wyglądać jak przygotowanie przestrzeni.

---

## 00:30–01:00 — wejście pierwszych części

Na mapie zaczynają pojawiać się assety części.

Nie pokazujemy ich jako listy.

Pojawiają się w różnych miejscach przestrzeni.

Kolejność może wynikać z historii:

`discovered_at`

Jeżeli kompletna historia nie istnieje, stosujemy canonical ordering.

Nie wymyślamy kolejności.

Każda część może przez chwilę dostać:

* nazwę,
* stan,
* krótki timestamp,
* właściciela, jeżeli dane są publiczne dla show.

---

## 01:00–01:30 — komplet 20 części

W przestrzeni powinno być już widoczne wszystkie 20 części.

Układ pozostaje chaotyczny.

Nie tworzymy jeszcze koła ani symetrii.

Elementy:

* powoli dryfują,
* zmieniają położenie,
* lekko reagują na glitch mapy.

Mapa pozostaje żywa w tle.

---

## 01:30–02:00 — pierwsze połączenia

Pomiędzy częściami zaczynają pojawiać się połączenia.

Połączenia wynikają z przyjętej logiki Ghost Network.

Nie tworzymy losowych relacji tylko dlatego, że dobrze wyglądają.

Połączenia:

* zapalają się,
* gasną,
* powstają ponownie,
* chwilami są przerywane.

Jest to metafora całego przebiegu cyklu.

---

## 02:00–02:20 — historia świata jako tło

W prawym dolnym obszarze lub w podobnym stałym miejscu pojawia się pierwsza warstwa historycznych logów.

Logi:

* przesuwają się bardzo wolno,
* są półprzezroczyste,
* nie konkurują z częściami,
* wyglądają jak zamrożona historia systemu.

Źródła:

* discovery,
* containment,
* activation,
* conflicts,
* BlackNet,
* historyczne komunikaty Ollamy,
* historyczne newsy.

To są prawdziwe zapisane materiały.

---

## 02:20–02:40 — zmiany stanów

Wybrane części wizualnie przechodzą przez swoje historyczne stany.

Przykład:

`discovered → contained → active`

Nie rekonstruujemy całej rozgrywki jeden do jednego.

Jest to skrócona wizualizacja.

Każdy pokazany stan musi jednak istnieć w danych historycznych części.

---

## 02:40–03:00 — przygotowanie do składania maszyn

Części zaczynają się grupować.

Powstają cztery skupiska po pięć części.

Każde skupisko zaczyna dostawać kolorystykę odpowiedniego klanu.

Mapa nadal pozostaje w tle.

Historyczne logi nadal płyną.

---

# 6. 03:00–06:00 — MASZYNY I GHOST NETWORK

## 03:00–03:30 — Machine Group 01

Pierwsze pięć części zostaje wyraźnie wyodrębnione.

Pokazujemy:

* nazwę maszyny,
* pięć części,
* klan.

Nie pokazujemy jeszcze pełnego hero assetu maszyny.

Najpierw widzimy, że maszyna faktycznie powstaje z części.

---

## 03:30–04:00 — Machine Group 02

Analogicznie druga maszyna.

Pozostałe elementy nie znikają całkowicie.

Pozostają w tle i budują wrażenie jednego systemu.

---

## 04:00–04:30 — Machine Group 03

Trzecia grupa pięciu części.

Kolor i efekty odpowiadają klanowi.

---

## 04:30–05:00 — Machine Group 04

Czwarta maszyna.

Na tym etapie wszystkie 20 części zostało już jednoznacznie powiązanych z czterema maszynami.

---

## 05:00–05:20 — rozpad grupowania

Cztery grupy ponownie rozsuwają się.

Nie oznacza to rozpadu maszyn.

To przejście z reprezentacji:

`4 × machine`

do reprezentacji:

`Ghost Network`

Wszystkie 20 assetów ponownie znajduje się na jednej przestrzeni.

---

## 05:20–05:40 — formowanie regularnego układu

Po raz pierwszy w show chaos zaczyna zamieniać się w regularność.

20 części układa się w duży okrąg.

Do tej chwili geometria była nieregularna.

Teraz:

* pozycje stają się symetryczne,
* odległości się wyrównują,
* sieć zaczyna wyglądać na świadomie skonstruowaną.

---

## 05:40–05:50 — naprężenie Ghost Network

Połączenia pomiędzy częściami zostają „naprężone”.

Wizualnie:

* linie stają się bardziej stabilne,
* zanikają przypadkowe przerwania,
* energia / sygnał przechodzi po całym okręgu,
* kolejne węzły odpowiadają sobie.

Logi przyspieszają.

Mapa mocniej glitchuje.

---

## 05:50–06:00 — aktywacja sieci

Sieć osiąga pełną gotowość.

Na chwilę cały regularny wzór jest widoczny jednocześnie.

Następuje:

* jeden mocny glitch,
* gwałtowne ściemnienie,
* prawie cała grafika znika.

Pozostaje tylko niestabilny ślad mapy i Ghost Network.

Przejście do sceny transmisji.

---

# 7. 06:00–08:00 — UZBROJENIE I EMISJA GHOSTSIGNAL

## 06:00–06:15 — maszyna klanu 01

Pojawia się nowy hero asset pierwszej maszyny.

To nie jest już układ pięciu osobnych ikon.

To nowy asset kompletnej maszyny.

Obok pokazujemy dane:

* MACHINE NAME,
* CLAN,
* PROFESSION,
* SUPERPOWER,
* PARTS: 5/5.

Tło:

* glitchowana mapa,
* lekkie logi,
* wyciszone elementy Ghost Network.

---

## 06:15–06:30 — maszyna klanu 02

Ta sama struktura.

Dane pobrane z canonical system configuration.

---

## 06:30–06:45 — maszyna klanu 03

Ta sama struktura.

---

## 06:45–07:00 — maszyna klanu 04

Ta sama struktura.

Po jej zakończeniu wszystkie cztery maszyny zostały zaprezentowane.

---

## 07:00–07:05 — wygaszenie

Maszyna znika.

Mapa pozostaje bardzo ciemna.

Logi zwalniają.

Muzyka / ambient gwałtownie się wycisza.

Przygotowujemy kontrast przed transmisją.

---

## 07:05–07:43,12 — TRANSMISSION VIDEO

Uruchamiany jest dostarczony asset video o długości 38,12 s przygotowany specjalnie dla GhostSignal.

Film:

* znajduje się w wyraźnie zaznaczonej ramce,
* nie zajmuje całego ekranu,
* jest centralnym elementem sceny.

Za nim nadal istnieje żywe tło:

* glitchowana mapa,
* logi,
* zakłócenia,
* Ghost Network telemetry.

Film nie emituje eventu `ghost.signal_sent`.

Film jest wyłącznie wprowadzeniem do retrospekcji potwierdzonej transmisji.

---

## 07:43,12 — RETROSPEKCJA POTWIERDZONEJ EMISJI

Backend wykonał operację zgodnie z kontraktem 139 na początku show. Koniec filmu nie wywołuje żadnej operacji backendu.

Scena odczytuje utrwalony wynik i rzeczywisty signal_sent_at. Jest wizualnym odtworzeniem zdarzenia, nie nową emisją.

### SUCCESS

Backend wcześniej wyemitował:

`ghost.signal_sent`

### FAILURE

Nie emitujemy eventu.

Nie przechodzimy do sceny wysłania.

Show pozostaje w kontrolowanym stanie awaryjnym/recovery istniejącego mechanizmu 139. Nie zmieniamy deadline'u ani nie wymuszamy rolloveru.

---

# 8. EVENT `ghost.signal_sent`

## 07:43,12–07:46,12 — wizualizacja zapisanej emisji

W momencie faktycznego odebrania na początku show:

`ghost.signal_sent`

następują SFX i krótki akcent potwierdzenia. Poniższa rozbudowana sekwencja wizualna stanowi późniejszą retrospekcję o 07:43,12, pod warunkiem istnienia potwierdzenia:

* właściwy SFX GhostSignal został już uruchomiony przez event — nie odtwarzamy go ponownie,
* bardzo jasny błysk,
* mocny glitch,
* przesterowanie całej sceny,
* reakcja mapy,
* reakcja Ghost Network,
* reakcja pozostałych elementów pulpitu.

### SFX

SFX jest uruchamiany dokładnie przez:

`ghost.signal_sent`

Dźwięk:

* wysoki,
* piskliwy,
* przesterowany,
* krótki,
* charakterystyczny,
* dużo mocniejszy niż wcześniejszy ambient.

To jest dźwięk faktycznej emisji. Zachowujemy istniejący asset i jego przypisanie z 139; nie przesuwamy odtworzenia do filmu ani sceny 07:43,12.

---

## 07:46,12–07:49,12 — punkt sygnału

Błysk zaczyna się kurczyć.

Z całego białego ekranu zostaje jeden jasny punkt pośrodku.

Punkt:

* pulsuje,
* zmniejsza się,
* zostawia delikatny ślad,
* znika.

Przez moment ekran jest niemal całkowicie pusty.

---

## 07:49,12–07:57 — TERMINAL 2108

Na ekranie pojawia się konsola.

Tekst pojawia się szybkim efektem typewriter.

Tekst musi pochodzić z wcześniej przygotowanego zestawu komunikatów show.

Nie generujemy go w tej chwili Ollamą.

Charakter komunikacji:

* transmission routing,
* handshake,
* temporal channel,
* remote acknowledgement,
* packet state,
* year 2108.

Tekst ma sprawiać wrażenie komunikacji z przyszłością, ale jego format jest wcześniej zatwierdzony.

Nie dokładamy przypadkowych pseudotechnicznych komunikatów z generacji runtime.

---

## 07:57–08:00 — potwierdzenie GhostSignal

Terminal dostaje silny glitch i znika.

Pojawia się ekran stylizowany wizualnie na:

* Superpowers,
* Secret Path,
* istniejące efekty systemowe CHAOS.

Centralny komunikat:

**GHOSTSIGNAL WYSŁANY**

Pod spodem:

rzeczywista data i godzina transmisji w 2026 roku.

Następnie data przechodzi wizualnie w:

**losową, wcześniej ustaloną datę z roku 2108.**

Przykład:

`11.09.2026 07:24:15`

↓

`27.04.2108 23:17:08`

Nie stosujemy prostego `+82 years`.

Data 2108 jest generowana raz po utworzeniu cyklu/show i zapisywana po stronie backendu.

Wszyscy gracze widzą tę samą datę.

---

# 9. 08:00–12:00 — ROZLICZENIE STAREGO ŚWIATA

Ten etap nie jest jeszcze restartem.

Najpierw CHAOS musi pokazać konsekwencje właśnie zakończonego świata.

---

## 08:00–08:15 — aftershock

Komunikat GhostSignal znika.

Wraca mapa.

Przez chwilę jest niestabilna.

Widoczne są:

* zakłócenia,
* pozostałości linii Ghost Network,
* echa transmisji.

System przechodzi w:

`WORLD SETTLEMENT`

---

## 08:15–08:45 — świat przed rozliczeniem

Pokazujemy stan świata z zamrożonego snapshotu.

Na mapie pokazane zostają terytoria istniejące dokładnie przed rozliczeniem GhostSignal.

Nie pobieramy tu świata po resecie.

---

## 08:45–09:15 — oznaczenie losów terytoriów

Terytoria otrzymują status końcowy.

Przykładowe klasy:

`PRESERVED`

`REDUCED`

`CONSUMED`

`CONFLICT RESOLVED`

Nazwy statusów muszą odpowiadać faktycznej implementacji po audycie.

Nie tworzymy własnej reguły klasyfikacji.

---

## 09:15–09:45 — redukcja

Mapa zaczyna faktycznie wizualizować redukcję.

Elementy świata:

* znikają,
* kurczą się,
* łączą,
* zostają pochłonięte,

zgodnie z wynikiem settlementu.

Animacja ma reprezentować gotowy wynik backendu.

Frontend nie oblicza sam, co ma zostać usunięte.

---

## 09:45–10:15 — konflikty

Pokazujemy konflikty istotne dla końcowego wyniku.

Można wyświetlić:

* strony konfliktu,
* klany,
* terytorium,
* wynik.

Nie odtwarzamy całej historii konfliktów.

Pokazujemy ich wpływ na końcowy świat.

---

## 10:15–10:30 — FINAL WORLD STATE

Mapa stabilizuje się.

Pokazujemy końcowy wynik settlementu starego cyklu.

To jest ostatni obraz starego świata jako struktury terytorialnej.

Po tym momencie nie wracamy już do wersji przed GhostSignal.

---

## 10:30–11:00 — nagrody

Mapa lekko się wycisza.

Pojawia się ledger nagród.

Pokazywane mogą być:

* RSP,
* nagrody cyklu,
* bonusy,
* nagrody Ghost Network,
* inne faktycznie istniejące typy rewardów.

Kwoty i wartości pochodzą z finalnego settlementu.

---

## 11:00–11:20 — gracze

Zaczynają pojawiać się profile graczy.

Nie każdy musi dostać pełnoekranową prezentację.

Może to być szybki przepływ danych

`PLAYER`

`CLAN`

`PROFESSION`

`GHOST NETWORK CONTRIBUTION`

---

## 11:20–11:40 — osiągnięcia

Pokazujemy istotne osiągnięcia zakończonego cyklu:

* części,
* aktywacje,
* maszyny,
* terytoria,
* konflikty,
* udział w GhostSignal.

Wyłącznie dane istniejące w systemie.

---

## 11:40–12:00 — klany

Podsumowanie czterech klanów.

Dla każdego:

* wynik,
* liczba aktywnych graczy,
* udział w Ghost Network,
* miara terytoriów,
* inne wskaźniki zatwierdzone dla rankingu klanów.

To jest początek przejścia z historii pojedynczych graczy do wyników całego cyklu.

---

# 10. 12:00–14:00 — REKONSTRUKCJA CHAOS

Stary świat został już rozliczony.

Teraz system zaczyna się ponownie składać.

---

## 12:00–12:20 — SYSTEM RESET LAYER

Obraz rozpada się na warstwy UI.

Mapa chwilowo schodzi na drugi plan.

Pojawiają się:

* terminal,
* systemowe okna,
* komendy,
* logi.

Wrażenie:

CHAOS wizualnie odtwarza istniejące systemy. Nie budujemy ani nie uruchamiamy nowych podsystemów lub operacji gameplayowych dla tej sceny.

---

## 12:20–12:40 — GOOGLEPLEX

Pojawiają się:

* narzędzia,
* aplikacje,
* assety Googleplex,
* rodzaje software.

Nie pokazujemy kompletnego katalogu.

Elementy szybko przesuwają się przez przestrzeń.

---

## 12:40–13:00 — PRO TOOLS / TERMINAL

Pojawiają się elementy:

* Pro Tools,
* terminal,
* operacje,
* komendy,
* systemowe moduły.

Można wykorzystać istniejące efekty interfejsu.

---

## 13:00–13:20 — FILE SYSTEM / DATA

Pojawiają się:

* pliki,
* typy plików,
* dane,
* logi,
* rekordy,
* krótkie systemowe identyfikatory.

Elementy nie muszą być czytelne wszystkie jednocześnie.

Tworzą wrażenie ponownego składania danych CHAOS.

---

## 13:20–13:40 — BLACKNET / HISTORY

Pojawiają się:

* BlackNet,
* historyczne newsy,
* historyczne komunikaty Ollamy,
* wydarzenia świata.

Znów używamy wyłącznie już zapisanych materiałów.

---

## 13:40–13:55 — składanie pulpitu

Wszystkie warstwy zaczynają wracać na swoje miejsca.

Terminal.

Mapa.

Ghost Network.

Googleplex.

BlackNet.

Systemy CHAOS.

Jeszcze nie uruchamiamy nowego cyklu.

---

## 13:55–14:00 — SYSTEM READY

Krótki komunikat systemowy:

`CHAOS CORE RESTORED`

lub zatwierdzony odpowiednik.

Następuje wejście w podsumowanie.

---

# 11. 14:00–15:00 — RANKING, ARCHIWIZACJA I RESTART

## 14:00–14:15 — ranking graczy

Pokazujemy końcowy ranking starego cyklu.

Ranking korzysta z zamkniętych danych cyklu.

Nie z aktualnego profilu po zmianach wykonywanych podczas restartu.

Przynajmniej:

* miejsce,
* gracz,
* klan,
* wynik.

---

## 14:15–14:30 — ranking klanów

Ranking czterech klanów.

Wykorzystuje ustalony Ghost Network Clan Score / Clan Measure.

Może zawierać:

* wynik,
* udział w sygnale,
* terytoria,
* aktywność,
* contribution.

Dokładne składowe wynikają z osobnego systemu miary klanu.

---

## 14:30–14:40 — statystyki końcowe cyklu

Krótka plansza:

* liczba graczy,
* liczba zdobytych terytoriów,
* liczba konfliktów,
* aktywacje,
* uczestnicy Ghost Network,
* czas trwania cyklu,
* inne zatwierdzone wskaźniki.

---

## 14:40–14:50 — OLD WORLD ARCHIVED

Backend powinien mieć już utrwalone:

* snapshot starego świata,
* wyniki,
* ranking,
* nagrody,
* GhostSignal history record,
* statystyki.

Pojawia się wizualne:

`GHOST NETWORK CYCLE ARCHIVED`

Od tego momentu stary świat traktowany jest jako historyczny.

---

## 14:50–14:56 — wygaszenie świata

UI zaczyna znikać.

Najpierw:

* logi,
* ranking,
* mapa,
* narzędzia.

Zostaje tylko niewielki centralny element Ghost Network.

---

## 14:56–15:00 — restart

Centralny element gaśnie.

Następuje pełne przejście do restartu systemu.

To jest faktyczna granica pomiędzy cyklami.

---

# 12. PO 15:00 — NOWY CYKL

Po restarcie:

* widoczny jest kolejny cykl Ghost Network, który backend aktywował przed restart epoch zgodnie z 139,
* gracz wraca do normalnego CHAOS,
* dostępna jest aplikacja historii poprzedniego GhostSignal,
* dostępne są rankingi zakończonego cyklu,
* dostępne są statystyki,
* stary świat pozostaje w archiwum,
* nowa narracja Ghost Network jest gotowa lub kończona przez Ollamę poza procesem show.

Show nie oczekuje na Ollamę.

---

# 13. NOWE ASSETY WYMAGANE DLA SHOW

## A. Cztery kompletne maszyny

Nowy asset dla każdej maszyny:

`machine_<clan_01>`

`machine_<clan_02>`

`machine_<clan_03>`

`machine_<clan_04>`

Każda powinna stylistycznie wynikać z pięciu istniejących części danego klanu.

---

## B. GhostSignal Transmission Video

Jeden materiał 38,12 s, odtwarzany w oryginalnym tempie, bez dźwięku (SFX pozostaje przy ghost.signal_sent).

Cel:

wizualne przygotowanie momentu wysłania GhostSignal.

Video nie zawiera logiki transmisji.

Nie może samo oznaczać sukcesu wysłania.

---

## C. GhostSignal Sent SFX

Istniejący charakterystyczny efekt transmisji pozostaje bez zmian zgodnie z decyzją operatora po 139. Nie jest wymagany nowy asset SFX.

Uruchamiany:

**WYŁĄCZNIE przez `ghost.signal_sent`.**

---

# 14. ZASADY DLA EFEKTÓW

Powinno się przede wszystkim wykorzystać istniejące efekty CHAOS.

Preferowane ponowne użycie:

* map glitch,
* BlackNet glitch,
* Secret Path,
* Superpowers,
* terminal typewriter,
* standardowe systemowe fade/glitch,
* istniejące komponenty logów,
* istniejące map rendering layers.

Nowe efekty należy tworzyć tylko wtedy, gdy istniejące mechanizmy nie pozwalają osiągnąć scenariusza.

Nie budujemy dla każdej sceny osobnego systemu animacji.

---

# 15. ZASADA DANYCH

Każdy element show musi należeć do jednej z trzech kategorii.

### STATIC ASSET

Przygotowany wcześniej:

* grafika,
* video,
* SFX,
* layout.

### CANONICAL CONFIG

Dane systemowe:

* nazwy części,
* nazwy maszyn,
* klany,
* profesje,
* supermoce,
* relacje part → machine.

### CYCLE SNAPSHOT

Dane konkretnego zakończonego GhostSignal:

* gracze,
* właściciele,
* historia części,
* terytoria,
* konflikty,
* nagrody,
* ranking,
* zdarzenia,
* historyczne narracje.

Jeżeli informacji nie ma w żadnym z tych źródeł:

**nie pokazujemy jej.**

Nie zgadujemy.

---

# 16. NAJWAŻNIEJSZE PUNKTY AUDYTU PRZED IMPLEMENTACJĄ

Przed napisaniem show trzeba ustalić, skąd dokładnie pobieramy:

1. canonical listę 20 części,
2. mapowanie 20 części → 4 maszyny,
3. machine → clan,
4. machine → profession,
5. machine → superpower,
6. historię lifecycle części,
7. historię właścicieli,
8. historię aktywacji,
9. relację części do terytoriów,
10. historię konfliktów,
11. historyczne komunikaty Ollamy,
12. BlackNet history,
13. news history,
14. terytoria przed settlementem,
15. wynik redukcji terytoriów,
16. wynik konfliktów,
17. nagrody,
18. statystyki graczy,
19. statystyki klanów,
20. Ghost Network Clan Measure,
21. dane potrzebne do rankingu,
22. miejsce archiwizacji poprzedniego GhostSignal,
23. procedurę tworzenia nowego cyklu,
24. faktyczne miejsce emisji `ghost.signal_sent`.

Dopiero po tym audycie należy podpinać dane do storyboardu.

---

# 17. LOGIKA STANÓW SHOW

Minimalnie:

`PREPARING`

↓

`PARTS_HISTORY`

↓

`MACHINE_ASSEMBLY`

↓

`NETWORK_FORMATION`

↓

`SIGNAL_ARMED`

↓

`TRANSMISSION_VIDEO`

↓

`WAITING_FOR_SIGNAL_SENT` (tylko jeśli brakuje trwałego potwierdzenia; nie nowa bramka o 07:43,12)

↓

`SIGNAL_SENT`

↓

`WORLD_SETTLEMENT`

↓

`REWARDS`

↓

`PLAYER_SUMMARY`

↓

`CHAOS_RECONSTRUCTION`

↓

`RANKING`

↓

`ARCHIVING`

↓

`RESTARTING`

↓

`COMPLETE`

Powyższe nazwy są etapami prezentacji, nie drugą maszyną stanów backendu. Transmisja backendu zachodzi wcześniej, na początku show. Retrospektywna scena `SIGNAL_SENT` może być pokazana wyłącznie po faktycznym evencie:

`ghost.signal_sent`

---

# 18. FAIL-CLOSED

Szczególnie ważne:

Jeżeli backend nie potwierdzi emisji:

`ghost.signal_sent`

show nie może przejść do:

`SIGNAL_SENT`

`WORLD_SETTLEMENT`

`ARCHIVING`

`RESTARTING`

Nie można wizualnie zamknąć świata, którego GhostSignal faktycznie nie został wysłany.

---

# 19. GŁÓWNA KOMPOZYCJA SHOW

Całość ma wizualnie przejść przez trzy stany.

### CHAOS

00:00–05:20

Części są nieregularne, historia jest nieuporządkowana, połączenia pojawiają się i znikają.

### ORDER / GHOST NETWORK

05:20–07:43,12

System się porządkuje, części tworzą regularną sieć, maszyny stają się pełnymi strukturami, GhostSignal zostaje uzbrojony.

### COLLAPSE → RECONSTRUCTION

07:43,12–15:00

Odtwarzamy wizualnie potwierdzone wysłanie GhostSignal, które nastąpiło na początku show.

Stary świat jest rozliczany i redukowany.

CHAOS rozpada się, a następnie ponownie składa.

Na samym końcu świat zostaje zapisany jako historia i następuje restart.

---

# 20. Najważniejszy moment całego show

Największym punktem nie jest ranking ani zakończenie progressbara.

Jest nim:

**`ghost.signal_sent`**

Rozdzielamy faktyczną chronologię 139 od montażu retrospekcji. Na początku: trwałe show i lock → skutki → backend potwierdza ghost.signal_sent → istniejący SFX i akcent. Około 07:43,12 przedstawiamy retrospekcję:

38,12 s video

↓

chwila ciszy

↓

odczyt potwierdzenia wcześniej wysłanego GhostSignal

↓

`ghost.signal_sent`

↓

bez powtórzenia SFX (zagrał przy rzeczywistym evencie)

↓

biały błysk

↓

glitch całego systemu

↓

jeden punkt światła

↓

ciemność

↓

terminal

↓

komunikacja z 2108

↓

glitch

↓

**GHOSTSIGNAL WYSŁANY**

↓

2026 → 2108

↓

rozliczenie starego świata.

Faktyczny punkt nieodwracalnych skutków pozostaje w istniejącym backendzie 139, na początku show. Retrospekcja jest kulminacją wizualną i nie wykonuje drugiej transmisji ani innych mutacji świata.

## Uzupełnienie audio i pola filmu — 2026-09-11

Pole filmu ma proporcje 3:2, limit 720×480, pomniejszanie na mobile i brak
interakcji/kontrolek odtwarzacza. Cztery kolejne MP3 autora mają łącznie 860 s:
ghostsignal_show_part_01.mp3 do ghostsignal_show_part_04.mp3 w
static/audio/ghostnetwork/show/. Tło zastępuje radio, zatrzymuje się na czas
filmu 425–463,12 s i wraca bez pominięcia muzyki; kończy się w 898,12 s.
Ostatnie 1,88 s pozostaje ciszą. Indywidualne granice MP3 wynikną z metadanych.
Miks zostanie wdrożony w istniejącym GhostRadio w 140.4, z poszanowaniem mute
oraz bez zmiany SFX ghost.signal_sent. Audio samego filmu pozostaje do ustalenia;
w bieżącym 140.2 jest wyciszone. Szczegóły i testy: §11 głównego planu 140.

## Dalsza stylizacja całego show

Decyzją autora bieżący Sprint 140 przygotowuje działający szkielet, dane
oraz synchronizację scen, video i muzyki. Niniejszy scenariusz jest kierunkiem
artystycznym do iteracyjnego dopracowania w
[140.stylization.1+](sprint_140_stylization_1_plus.md), gdzie przejdziemy przez
całe 15 minut. Akceptacja podglądu nie zamraża wyglądu. Kontrakt 139 i bramki
poprawności danych/synchronizacji pozostają obowiązujące już w 140.
