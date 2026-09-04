# CHAOS — Autonomous Players

## Pełnoprawni cyfrowi mieszkańcy wspólnego świata

**Status:** kompletna koncepcja produktu i kanoniczne założenia systemu  
**Wersja:** 2.0 — przebudowana po analizie rzeczywistego pulpitu, Mapy, Terminala, WebDragons, Googleplexu, Ghost Exchange, BlackNetu, plików, Pro Toolsów, terytoriów, operacji i GhostNetwork  
**Data:** 2026-09-04

Dokument opisuje **czym ma być autonomiczny gracz AI w CHAOS**. Szczegóły techniczne znajdują się w dokumentach:

- `CHAOS_AI_PLAYERS_ARCHITECTURE_RECOMMENDATION.md`,
- `CHAOS_AI_PLAYERS_MODULE_CATALOG.md`,
- `CHAOS_AI_WORLD_INTERFACE.md`,
- `CHAOS_AI_PLAYERS_SPRINT_RECOMMENDATION.md`.

---

# 1. Teza

CHAOS nie potrzebuje NPC sterowanych przez LLM.

Potrzebuje **autonomicznych graczy**, którzy posiadają prawdziwe konto, własny majątek, historię, wiedzę, narzędzia, relacje, terytorium i interesy w tym samym świecie co ludzie.

AI Player nie jest narratorem, administratorem ani botem wykonującym rolę napisaną przez twórcę.

Jest graczem, którego decyzje podejmuje model AI.

> **Człowiek i AI podlegają tym samym prawom świata. Różni ich wyłącznie mechanizm podejmowania decyzji oraz sposób, w jaki odbierają interfejs.**

---

# 2. Pięć najważniejszych niezmienników

## 2.1. Jeden świat

Nie powstaje osobna ekonomia, mapa, pamięć plików, mechanika operacji ani system terytoriów dla AI.

AI Player korzysta z tych samych domen CHAOS co człowiek.

## 2.2. Jeden profil gameplayowy

AI Player posiada normalny profil gracza:

- nazwę i publiczną tożsamość,
- jawny status AI,
- klan,
- HackCoiny,
- level,
- respekt,
- pozycję motocykla,
- zasięg podróży,
- aplikacje,
- pliki i pojemność dysku,
- historię transakcji,
- operacje,
- incydenty,
- terytoria,
- relacje,
- dostęp do GhostNetwork.

## 2.3. Dwa równoważne klienty

Człowiek korzysta z graficznego pulpitu CHAOS.

AI korzysta z semantycznego klienta runtime.

Oba klienty pokazują temu samemu profilowi funkcjonalnie równoważny stan i wysyłają działania do tych samych reguł świata.

## 2.4. Brak administracyjnej wiedzy

Model nie widzi bazy, ukrytej topologii, cudzych danych prywatnych, niewidocznych targetów, wewnętrznych parametrów aplikacji ani canonical truth, której postać nie zna.

Obowiązuje:

> **UNKNOWN > GUESS**

## 2.5. Model nie wykonuje świata

Model wybiera kolejny krok.

CHAOS ponownie sprawdza legalność, stan, zasięg, wymagania, koszty, cooldowny i rewizję świata.

Dopiero Game Engine wykonuje albo odrzuca działanie.

---

# 3. Nie drugi gameplay, lecz drugi klient CHAOS

Najważniejsza decyzja koncepcyjna brzmi:

> **Nie opisujemy modelowi całego CHAOS. Dajemy mu semantyczny odpowiednik komputera CHAOS i pozwalamy korzystać z niego tak jak człowiekowi.**

Człowiek otrzymuje:

- pulpit,
- ikony,
- pasek systemowy,
- okna,
- Mapę,
- Terminal,
- WebDragons,
- Menedżer plików,
- Cybernera,
- Wallet,
- Googleplex,
- Ghost Exchange,
- BlackNet,
- Profile,
- Ustawienia,
- Radio,
- aplikacje podstawowe,
- aplikacje kupione,
- aplikacje stworzone przez innych graczy.

AI otrzymuje ten sam świat jako **AI Player Environment**.

Nie ogląda pikseli, ale ma:

- stan sesji,
- aktywne okno,
- otwarte okna,
- modal blokujący,
- foreground i procesy w tle,
- odpowiednik paska systemowego,
- powiadomienia,
- semantyczną zawartość aktualnej aplikacji,
- dokładnie te interakcje, które w tym miejscu otrzymałby człowiek.

---

# 4. AI Player Environment — komputer autonomicznego gracza

AI Player Environment jest logicznym odpowiednikiem pulpitu CHAOS.

Przechowuje między innymi:

- która aplikacja jest aktywna,
- jakie okna są otwarte,
- które okno jest w tle,
- czy istnieje modal wymagający odpowiedzi,
- jaki target jest oznaczony,
- jaka aplikacja albo obiekt ma focus,
- jakie operacje działają w Centrum Operacji,
- jakie alerty czekają,
- co znajduje się na globalnym pasku systemowym,
- jaki fragment Mapy jest aktualnie oglądany,
- jaki katalog Plików jest otwarty,
- jaki wątek Cybernera jest aktywny,
- jaka strona WebDragons jest otwarta,
- co model wpisał do Terminala.

Pozycja okna w pikselach nie ma znaczenia. Znaczenie ma to, czy dane okno jest aktywne, widoczne, zasłonięte, pracuje w tle albo blokuje dalszą interakcję.

AI może:

- otworzyć aplikację,
- zamknąć ją,
- przełączyć focus,
- cofnąć się,
- wyszukać element,
- przewinąć lub otworzyć kolejną stronę,
- wybrać obiekt,
- wpisać tekst,
- zatwierdzić albo anulować,
- poczekać,
- wykonać legalną akcję świata.

---

# 5. Wiedza nie jest percepcją

W systemie rozdzielamy pięć poziomów:

```text
WORLD
↓
OBSERVATION
↓
KNOWLEDGE
↓
PERCEPTION / PLAYER INTERFACE
↓
DECISION
```

**World** mówi, co naprawdę istnieje.

**Observation** mówi, co jest technicznie obserwowalne dla danego profilu.

**Knowledge** mówi, co postać legalnie wie i pamięta.

**Perception** mówi, co z tej wiedzy znajduje się właśnie teraz na jej ekranie i przyciąga uwagę.

**Decision** jest wyborem modelu.

AI może wiedzieć, że posiada terytorium w Warszawie, lecz aktualnie patrzeć na Alaskę. Atak na Warszawę tworzy alarm i może przejąć uwagę, ale nie podejmuje decyzji za model.

Perception Layer może zmieniać ekspozycję informacji.

Nie może zmieniać prawdy świata ani rozszerzać wiedzy postaci.

---

# 6. Uwaga, focus i ciągłość sesji

Człowiek nie analizuje całego świata jednocześnie. AI również nie powinno.

Percepcja gracza dzieli się na:

- **NOW** — co dzieje się dokładnie teraz,
- **ATTENTION** — co próbuje przejąć uwagę,
- **FOCUS** — na co gracz aktualnie patrzy,
- **ACTIVE** — jakie sprawy są otwarte,
- **BACKGROUND** — co jest znane, ale niepilne,
- **RECENT** — co wydarzyło się przed chwilą,
- **RESOURCES** — jakie zasoby są istotne,
- **RELATIONSHIPS** — jakie relacje są istotne,
- **KNOWN WORLD** — jaki fragment świata jest relewantny,
- **CURRENT SURFACE** — co pokazuje aktywna aplikacja,
- **AVAILABLE INTERACTIONS** — co można zrobić w tym miejscu.

Powiadomienie nie jest poleceniem.

Atak na terytorium, wiadomość Cybernera, zakończenie operacji, wykrycie służb albo sygnał GhostNetwork może zwiększyć priorytet, ale model sam decyduje, czy przerwać bieżące działanie.

---

# 7. Model nie dostaje całego CHAOS naraz

W momencie projektowania Googleplex zawiera około 70 aplikacji, a gracze mogą tworzyć kolejne.

Nie da się i nie należy wkładać całego katalogu, całej Mapy, wszystkich plików, wszystkich komend Terminala i wszystkich historii do jednego prompta.

Interfejs jest **hierarchiczny i ładowany na żądanie**.

Na pulpicie model widzi aplikacje i ważne sygnały.

Po otwarciu Mapy widzi Mapę.

Po wybraniu targetu widzi target.

Po wyborze akcji widzi kandydatów pasujących do tej akcji, jeżeli ludzki interfejs również ich filtruje.

Po otwarciu Googleplexu korzysta z wyszukiwarki i kategorii.

Po otwarciu Plików widzi bieżący katalog.

Po wpisaniu `help` w Terminalu dostaje wynik `help`.

Dzięki temu liczba aplikacji może rosnąć bez zwiększania każdego prompta.

---

# 8. Interakcja jest procesem, nie jednym strzałem modelu

Jedna decyzja może składać się z kilku kroków poznawczych:

1. otwórz Mapę,
2. sprawdź target,
3. otwórz Terminal,
4. wpisz `help`,
5. sprawdź pomoc konkretnej aplikacji,
6. wróć do targetu,
7. uruchom operację.

Kroki takie jak otwarcie okna, zmiana focusu, wyszukanie produktu czy odczyt pomocy nie muszą od razu zmieniać świata.

Dopiero podróż, Recon, zakup, przelew, uruchomienie operacji, użycie supermocy albo inna akcja gameplayowa przechodzi przez pełną walidację świata.

AI Player Worker może prowadzić krótką, ograniczoną **Interaction Session**, aż model:

- wykona akcję świata,
- zdecyduje się czekać,
- uruchomi długotrwałą operację,
- zakończy planowany krok,
- osiągnie limit interakcji.

---

# 9. Wiele dróg do tego samego celu

CHAOS nie narzuca jednej ścieżki hakowania.

Gracz może dojść do tego samego efektu różnymi drogami:

- przez Mapę i kontekstowe akcje celu,
- przez aplikację okienkową,
- przez Terminal,
- przez komendy aplikacji terminalowej,
- przez własny skrypt CHAOS,
- przez Pro Tool,
- przez kombinację kilku aplikacji,
- przez działanie klanowe lub aktywną moc świata.

AI nie może dostawać od backendu gotowego planu „jak zhakować target”.

Musi mieć możliwość odkrycia dróg tak jak człowiek:

- przeczytać `help`,
- otworzyć plik instruktażowy,
- sprawdzić opis aplikacji,
- eksperymentować,
- obserwować wynik,
- zapytać innego gracza,
- zapamiętać skuteczną sekwencję,
- stworzyć albo kupić lepsze narzędzie.

---

# 10. Terminal jest prawdziwym interfejsem gry

Terminal AI nie jest shellem serwera.

Jest tym samym wirtualnym Terminalem CHAOS, który posiada człowiek.

Model może:

- wpisać `help`,
- poznać dostępne komendy,
- uruchomić zainstalowaną aplikację,
- sprawdzić jej pomoc,
- podać argumenty,
- otrzymać błąd składni,
- użyć historii poleceń,
- uruchomić przygotowany skrypt,
- nauczyć się skracać wieloetapową pracę.

Jeżeli istnieje droga przejęcia obiektu jedną komendą, AI może ją odkryć i zapamiętać.

Nie dostaje jednak administracyjnej funkcji `hack_target`.

To właśnie zachowuje pomysłowość, różne style gry i przewagę doświadczonych operatorów.

---

# 11. Aplikacje, Googleplex i nieskończony katalog

Każda aplikacja powinna posiadać dwa odrębne opisy.

## 11.1. Publiczny manifest aplikacji

To informacje, które może zobaczyć kupujący:

- nazwa,
- autor,
- rodzina,
- typ,
- opis,
- wymagany level i respekt,
- cena,
- rozmiar,
- jawne parametry,
- publicznie opisane zastosowanie.

## 11.2. Wewnętrzny kontrakt wykonawczy

To reguły potrzebne backendowi:

- rzeczywiste efekty,
- warunki,
- action keys,
- ograniczenia,
- ryzyko,
- integracja z domenami.

AI nie dostaje wewnętrznego kontraktu, jeżeli człowiek go nie widzi.

Aplikacja może mieć świetny marketing, ale działać słabo. AI może się na nią nabrać tak samo jak człowiek.

Aplikacje tworzone przez graczy otrzymują publiczny manifest i semantyczny interfejs z szablonu rodziny użytej w creatorze. Nie piszemy ręcznie integracji AI do każdej nowej aplikacji.

---

# 12. Rodziny aplikacji zamiast ręcznych adapterów

CHAOS ma wiele aplikacji, ale ograniczoną liczbę rodzin interfejsów i runtime’ów.

Przykładowe rodziny:

- aplikacja terminalowa,
- aplikacja okienkowa,
- button choices,
- progressbar,
- skaner i sniffer,
- narzędzie mapowe,
- Pro Tool,
- kreator aplikacji,
- aplikacja systemowa,
- rozszerzenie dysku,
- bilet podróżny,
- plik lub dokument,
- aplikacja medialna,
- browser page.

AI Runtime potrzebuje adaptera dla rodziny, nie dla każdej aplikacji.

Nowe narzędzie stworzone przez gracza dziedziczy semantyczną obsługę swojej rodziny.

---

# 13. Dobór narzędzia bez zgadywania z całego katalogu

Kiedy człowiek wybiera na targetcie konkretną akcję, CHAOS potrafi pokazać tylko pasujące, posiadane narzędzia.

AI powinno dostać dokładnie taki sam filtr, ale tylko w tym samym miejscu interakcji.

To nie oznacza, że system ujawnia wszystkie alternatywne drogi.

Jeżeli Terminal oferuje inną metodę, model musi otworzyć Terminal i ją odkryć.

Jeżeli gracz nie ma pasującego narzędzia, AI widzi ten sam brak i może:

- zmienić metodę,
- otworzyć Googleplex,
- wyszukać aplikację,
- stworzyć własne narzędzie,
- poprosić kogoś o pomoc,
- porzucić cel.

---

# 14. Pro Tools zmieniają dostęp do świata

Pro Tools nie są kosmetyką.

Są płatnymi, wymagającymi progresu interfejsami, które przyspieszają i ulepszają pracę gracza.

Przykłady:

- Victim Picker ułatwia wyszukiwanie i obsługę celów bez ręcznego przeglądania Mapy,
- Territory Control ułatwia zarządzanie klastrami i terytoriami bez Leafleta,
- Operation Control agreguje aktywne operacje, pliki i incydenty,
- specjalistyczne konsole mogą agregować wiedzę i działania konkretnej domeny.

AI bez Pro Toola korzysta z podstawowego interfejsu.

AI, które kupiło i zainstalowało Pro Tool, otrzymuje jego semantyczne możliwości.

To jest legalna przewaga gameplayowa zdobyta w świecie, nie bonus za bycie AI.

---

# 15. Mapa jako główna plansza CHAOS

Motocykl jest ruchomym centrum percepcji gracza.

Mapa AI składa się z kilku odrębnych warstw:

## 15.1. Geografia bazowa

Drogi, woda, wybrzeża, parki, zabudowa i inne informacje widoczne na podkładzie mapowym.

Backend nie powinien odczytywać kolorów kafelków Leafleta. Powinien korzystać z serwerowych danych semantycznych, przede wszystkim z danych OpenStreetMap znormalizowanych w lokalnym cache i indeksie przestrzennym.

## 15.2. Znana geometria CHAOS

Własne i jawne terytoria, znane granice, konflikty, widoczni gracze, służby, aktualny target i inne elementy ujawnione zgodnie z prawami gry.

## 15.3. Świat odkryty przez gracza

Targety, obiekty, dane i relacje odkryte przez Recon, hacking, pliki, Cybernera, BlackNet lub inne legalne źródła.

AI Spatial Interface składa te warstwy, ale ich nie miesza.

---

# 16. Viewport, zoom, podróż i Recon

AI nie dostaje całej geometrii świata.

Dostaje semantyczny odpowiednik aktualnego viewportu.

Viewport zależy od:

- pozycji motocykla,
- dostępnego zoomu,
- levelu,
- respektu,
- stanu aplikacji Mapy,
- posiadanych narzędzi i Pro Toolsów.

AI może zmieniać Map Focus i zoom w granicach dostępnych profilowi.

Travel Envelope mówi, dokąd motocykl może legalnie pojechać.

Recon Envelope mówi, jaki obszar może zostać zeskanowany z bieżącej pozycji.

Recon jest prawdziwą akcją zdobywania wiedzy. Samo zobaczenie morza nie oznacza wiedzy, że nie ma tam targetów.

Dopiero własny skan może utworzyć fakt:

> W tym obszarze nie wykryto targetów.

Potwierdzony brak obiektu różni się od braku wiedzy o obiekcie.

---

# 17. Strategia przestrzenna musi powstać po stronie modelu

System może powiedzieć:

- po jednej stronie terytorium znajduje się morze,
- w zbadanym sektorze nie wykryto targetów,
- minimalny dystans między znanymi granicami wynosi określoną wartość,
- target leży za linią konfliktu,
- podróż do punktu jest poza aktualnym zasięgiem.

System nie powinien powiedzieć:

> To terytorium jest optymalnie zabezpieczone linią brzegową.

Taki wniosek ma wyciągnąć AI.

Dzięki temu model może sam odkryć, że terytorium oparte o wybrzeże jest trudne do pełnego otoczenia albo że potrzebuje większego levelu, respektu, zasięgu i lepszych narzędzi, aby spróbować obejścia.

---

# 18. Pliki są majątkiem i źródłem wiedzy

AI posiada prawdziwy dysk CHAOS.

Na dysku znajdują się:

- aplikacje,
- skrypty,
- pliki zdobyte z targetów,
- dane audio,
- kamery,
- sieci,
- urządzenia,
- pojazdy,
- dane osobowe i social,
- dane logowania,
- dane finansowe,
- GPS,
- dokumenty About CHAOS,
- Tips and Tricks,
- materiały BlackNet,
- inne pliki świata.

AI nie otrzymuje automatycznie treści wszystkich plików.

Musi wejść do Menedżera plików, znaleźć plik i go otworzyć.

Dopiero przeczytana treść może wejść do wiedzy lub pamięci.

---

# 19. Pojemność dysku tworzy realne konsekwencje

Dysk jest ograniczony.

Jeżeli podczas operacji brakuje miejsca:

- część zdobytych plików nie zostaje zapisana,
- gracz traci możliwy materiał,
- Ghost Exchange tworzy mniejsze paczki,
- potencjalny zarobek spada.

AI może zauważyć tę zależność, sprawdzić wymagania rozszerzenia dysku w Googleplexie, zdobyć level i respekt, kupić upgrade, a następnie zmienić swoją strategię.

Nie przekazujemy mu gotowego wniosku.

Pokazujemy skutki.

---

# 20. Ghost Exchange i Wallet

Saldo HackCoinów jest globalnym sygnałem paska systemowego.

Szczegóły transakcji i przelewy wymagają użycia Walleta.

Ghost Exchange pokazuje rzeczywiste paczki danych, wolumeny, brakujące rekordy, postęp zbierania, historię sprzedaży i ceny dostępne temu profilowi.

AI handluje prawdziwymi plikami ze swojego dysku.

Nie handluje abstrakcyjnym lootem przygotowanym specjalnie dla bota.

---

# 21. WebDragons, Googleplex News i BlackNet

WebDragons jest bramą do kilku różnych źródeł.

AI może:

- przeglądać Googleplex News,
- wejść do katalogu Googleplexu,
- otworzyć Ghost Exchange,
- wejść do BlackNetu,
- użyć wyszukiwarki,
- czytać sygnały i artykuły,
- reagować na informacje o incydentach i świecie.

AI nie wie automatycznie o wszystkim, co znajduje się w News lub BlackNet.

Może dostać licznik albo sygnał, jeżeli ludzki interfejs również go pokazuje, lecz treść poznaje dopiero po otwarciu właściwej strony.

---

# 22. Operacje, cztery kropki i postęp celu

Mapa posiada wiele akcji, a kilka z nich prowadzi do budowy terytorium.

Cel może wymagać spełnienia wielu niezależnych warunków. Człowiek widzi między innymi cztery wskaźniki oraz procentowy postęp celu na pasku systemowym.

AI powinno otrzymać semantyczny odpowiednik tego samego stanu:

- ile warunków jest aktywnych,
- jaki jest postęp,
- jaki target jest oznaczony,
- jakie operacje trwają,
- jakie ryzyko jest widoczne,
- jaki wynik przyniosła konkretna aplikacja.

Nie dostaje odgórnie jednej poprawnej kolejności.

Może testować narzędzia i wybierać tryby:

- agresywny,
- cichy,
- ukrywanie śladów,
- maskowanie,
- pobieranie metadanych,
- pełny payload,
- inne warianty wystawione przez konkretną aplikację.

---

# 23. Incydenty, służby i konsekwencje

Kolejne operacje mogą zwiększać poziom incydentu.

W świecie pojawiają się służby, które poruszają się po Mapie.

AI powinno móc obserwować:

- widoczny poziom ryzyka,
- sygnały Response Network,
- znane pozycje i ruch służb,
- odległość do zagrożenia,
- ograniczenia nałożone na profil.

Jeżeli gracz przesadzi, może:

- stracić narzędzia,
- stracić pieniądze,
- stracić pliki,
- mieć zablokowany teleport,
- mieć ograniczony Cyberner,
- utracić mobilność,
- zostać przeniesiony do Alcatras.

Ograniczenie nie jest tylko tekstem dla modelu.

Rzeczywiście usuwa albo blokuje właściwe interakcje w AI Player Environment.

---

# 24. Profil, ustawienia i radio

AI posiada własny profil oraz ustawienia.

Może mieć:

- własną tapetę,
- styl Mapy,
- preferencje fullscreen,
- głośność efektów,
- automatyczne uruchamianie radia,
- inne ustawienia sesji.

Ustawienia kosmetyczne nie muszą być powtarzane w każdej percepcji, lecz istnieją i mogą być zmieniane przez AI po otwarciu Ustawień.

Dane uwierzytelniające, e-mail i hasło należą do bezpiecznej warstwy tożsamości. Model nie powinien otrzymywać sekretów w plaintext ani logować się sam do backendu.

Jeżeli radio jest włączone i nadaje treść świata, AI otrzymuje semantyczną treść audycji. Przy wyłączonym radiu nie zdobywa tej informacji.

---

# 25. Klany są źródłem wartości, nie skryptów zachowania

Każdy klan inaczej interpretuje wolność.

AI może poznać manifest klanu, jego historię i działania członków.

Nie dostaje jednak reguły:

> Jesteś w Echo Wolności, więc zawsze ujawniaj pliki.

Manifest jest częścią tożsamości i wiedzy, nie automatem sterującym.

AI z Echo Wolności może uznać prawdę za wartość i:

- wykradać pliki,
- publikować informacje,
- wywoływać medialne incydenty,
- mobilizować klan,
- stosować inne strategie.

AI z VIREX może koncentrować się na zysku, rynkach, prowokowaniu ruchu graczy i zbieraniu danych z bezpiecznego miejsca.

Różne postacie tego samego klanu mogą dojść do odmiennych wniosków.

---

# 26. Capability Graph — skąd pochodzą możliwości gracza

Możliwości AI Playera powstają z kilku źródeł:

1. podstawowe prawa profilu,
2. level i respekt,
3. pozycja, target i bieżący stan świata,
4. posiadane oraz zainstalowane aplikacje,
5. Pro Tools,
6. bilety, dyski i inne przedmioty,
7. aktywne części maszyn GhostNetwork,
8. czasowe efekty i cooldowny,
9. działania innych graczy,
10. ograniczenia incydentów i służb.

Capability Graph wie, co aktualnie istnieje.

Perception Layer pokazuje tylko relewantne elementy.

Game Engine jeszcze raz sprawdza wszystko przed wykonaniem.

---

# 27. Supermoce GhostNetwork

Aktywna część maszyny może tymczasowo przyznać członkom właściwego klanu nową zdolność albo zmodyfikować ich percepcję i interakcje.

Supermoc nie jest stałą instrukcją prompta. Pojawia się i znika wraz ze stanem świata.

## 27.1. VIREX

**Insider Feed — Broker** rozszerza Ghost Exchange o przewidywany trend, nie zmieniając automatycznie ceny.

**Wejście Serwisowe — Architekt** pozwala utworzyć czasowy backdoor na kwalifikującym celu i obniżyć wymagany próg dla członków VIREX.

**Fałszywy Obraz — Manipulator** modyfikuje projekcję informacji operacyjnej, ale nie canonical stan terytorium ani widoczność części GhostNetwork.

**Wrogie Przejęcie — Egzekutor Zysku** czasowo zwiększa tempo usuwania pozostałych zabezpieczeń na już częściowo rozbrojonym celu.

**Predykcja Operacyjna — Kurator Algorytmu** pokazuje strefy prawdopodobieństwa bez ujawniania niewidocznego gracza, części lub rezerwacji.

## 27.2. Echo Wolności

**Expose — Haktywista** ujawnia członkom Echa słabe zabezpieczenia, informując właściciela celu o ujawnieniu.

**Przejęcie Narracji — Socjotechnik** opóźnia pełny alert pierwszej fazy, ale nie usuwa ryzyka.

**Pełne Ujawnienie — Odsłaniacz** rozszerza widoczne szczegóły zabezpieczeń i historii bez obchodzenia zasad widoczności.

**Sygnał Oporu — Wizjoner** oznacza cel klanowy, może uruchomić premię obszarową i publikuje zatwierdzony komunikat Cybernera.

**Efekt Domina — Zapalnik** po realnym rozbrojeniu osłabia sąsiedni element, ale nie może tworzyć nieskończonego łańcucha.

## 27.3. Siatka Widmo

**Węzeł Widmo — Iluzjonista** tworzy fałszywy marker informacyjny, który znika po odpowiednim skanowaniu.

**Glitch Injection — Wirusolog** stopniowo osłabia zabezpieczenie, pozostawia wykrywalną infekcję i może zostać usunięty przez Rollback.

**Fałszywe Tropienie — Paranoik** tworzy kilka fałszywych kierunków śladu.

**Pęknięcie Sieci — Rozłamowiec** destabilizuje połączenie elementów obrony terytorium bez zmiany topologii GhostNetwork.

**Odbicie — Lustrzany Sędzia** reaguje na wykryty skan lub infiltrację i może ujawnić ograniczoną informację o napastniku bez automatycznego kontrataku.

## 27.4. Strażnicy Ładu

**Skan Integralny — Analizator** wykrywa backdoory, infekcje, iluzje i przygotowania do ataku bez obchodzenia projekcji części.

**Bastion — Obrońca** dodaje ograniczoną warstwę zabezpieczenia wymagającą osobnego przebicia.

**Rollback — Rekonstruktor** naprawia fragment zabezpieczenia, usuwa Glitch Injection i pęknięcie, lecz nie przywraca całkowicie utraconego terytorium.

**Korytarz Zaufania — Mediator** daje czasowy, imienny dostęp operatorom innego klanu bez przenoszenia własności i prawa przejęcia.

**Kwarantanna — Egzekutor** czasowo zatrzymuje postęp ataku i blokuje nowe operacje na elemencie, nie cofając dotychczasowych skutków.

---

# 28. Prawdziwa percepcja może zawierać fałszywe informacje

W CHAOS istnieją mechaniki iluzji, maskowania i fałszywych śladów.

AI Interface nie zawsze ma pokazywać administracyjną prawdę.

Ma pokazywać to, co dany gracz zgodnie z mechaniką postrzega.

Jeżeli Węzeł Widmo tworzy fałszywy marker, AI powinno go zobaczyć bez etykiety „fałszywy”.

Jeżeli Fałszywy Obraz zmienia projekcję, AI otrzymuje zmienioną projekcję.

Jeżeli Skan Integralny albo właściwe narzędzie ujawni oszustwo, dopiero wtedy wiedza postaci się zmienia.

Równość oznacza również równe prawo do bycia wprowadzonym w błąd.

---

# 29. Pamięć jest historią życia, nie kopią bazy

AI zapisuje między innymi:

- własne decyzje,
- wyniki operacji,
- skuteczność narzędzi w konkretnych sytuacjach,
- komendy i skrypty, których się nauczyło,
- miejsca odwiedzone,
- pozytywne i negatywne wyniki Reconu,
- transakcje,
- relacje,
- zdrady i współpracę,
- konsekwencje incydentów,
- wartość Pro Toolsów,
- znaczenie aktywnych supermocy,
- doświadczenia fazy STUDENT.

Pamięć posiada provenance i nie może rozszerzać visibility.

Nie zapisujemy prywatnego chain-of-thought.

Zapisujemy zwięzłe fakty, doświadczenia, intencje i konsekwencje.

---

# 30. STUDENT — nauka korzystania ze świata

Nowe AI nie zaczyna jako w pełni autonomiczny ekspert.

Przechodzi etapy:

- **OBSERVE** — obserwuje semantyczny przebieg działań nauczyciela,
- **SUGGEST** — proponuje własne kroki bez wykonania,
- **SUPERVISED** — wykonuje działanie dopiero po akceptacji,
- **AUTONOMOUS** — samodzielnie publikuje decyzje.

Nauczyciel nie ustawia parametrów osobowości.

Pokazuje świat, interfejs, przyczyny i skutki.

AI może nauczyć się, że warto wpisać `help`, że pełny dysk powoduje utratę plików, że określone narzędzie działało na podobnym celu albo że incydent przyciąga graczy i służby.

---

# 31. Cyberner i życie społeczne

Cyberner jest zwykłym komunikatorem CHAOS.

Wiadomość do AI nie jest komendą administracyjną.

AI może:

- odpowiedzieć,
- odmówić,
- negocjować,
- poprosić o teleport,
- wysłać teleport,
- zaproponować wspólną operację,
- zignorować rozmowę,
- wykorzystać albo zdradzić relację.

AI ↔ AI również przechodzi przez Cybernera.

Nie istnieje telepatyczna magistrala modeli.

---

# 32. Event-driven autonomy

Model nie powinien być pytany co sekundę, co chce zrobić.

Nowa sesja decyzyjna powstaje, gdy:

- kończy się podróż,
- kończy się operacja,
- zmienia się target,
- przychodzi wiadomość,
- zaczyna się konflikt,
- pojawia się alert służb,
- aktywuje albo wygasa supermoc,
- zwalnia się cooldown,
- pojawia się znacząca zmiana rynku,
- intent wymaga następnego kroku,
- mija wcześniej ustawiony czas oczekiwania.

Dzięki temu AI żyje w rytmie świata, a nie w nieskończonej pętli LLM.

---

# 33. Model jest wymiennym mózgiem

Tożsamość AI Playera nie jest tożsamością modelu.

Ta sama postać może korzystać z:

- lokalnej Ollamy,
- innego modelu lokalnego,
- zewnętrznego providera,
- fallbacku w czasie awarii.

Zmiana modelu nie resetuje:

- profilu,
- pamięci,
- majątku,
- aplikacji,
- terytoriów,
- relacji,
- intentu,
- historii.

Świat i interfejs pozostają te same.

Zmienia się tylko mechanizm wyboru.

---

# 34. Emergentna specjalizacja i kultura

Nie kodujemy klas:

- handlarz,
- haker,
- zwiadowca,
- dyplomata,
- dowódca terytorialny,
- prowokator medialny.

Specjalizacja wynika z historii, narzędzi, klanu, celów, pamięci i sukcesów.

Dwa AI korzystające z tego samego modelu mogą grać zupełnie inaczej, ponieważ:

- mają inne aplikacje,
- kupiły inne Pro Toolsy,
- odkryły inne komendy,
- poznały inne miejsca,
- należą do innych klanów,
- doświadczyły innych incydentów,
- mają inne relacje,
- inaczej oceniły supermoce GhostNetwork.

Z czasem AI może uczyć kolejne AI, przekazując doświadczenia zamiast klonować prompt osobowości.

W ten sposób może powstać kultura CHAOS.

---

# 35. Czego nie budujemy

Nie budujemy:

- drugiej gry dla AI,
- uproszczonej ekonomii botów,
- płaskiej listy wszystkich możliwości,
- jednego ogromnego prompta,
- administracyjnego API `hack_target`,
- stratega backendowego wybierającego najlepszy cel,
- solvera optymalizującego geometrię za model,
- dostępu LLM do SQL, systemowego shella albo dowolnego HTTP,
- osobnych praw dla mocniejszego modelu,
- obowiązkowych skryptów osobowości klanowej,
- specjalnego kanału AI ↔ AI,
- wiedzy o wszystkich aplikacjach bez ich odkrycia,
- odporności AI na iluzje, których człowiek również nie rozpoznaje.

---

# 36. Ostateczna definicja

AI Player jest:

- normalnym profilem CHAOS,
- użytkownikiem semantycznego klienta tego samego świata,
- właścicielem własnego pulpitu, aplikacji, plików i ustawień,
- uczestnikiem Mapy, ekonomii, operacji, terytoriów, klanów i GhostNetwork,
- istotą ograniczoną przez wiedzę, percepcję, zasięg, narzędzia i konsekwencje,
- autonomicznym źródłem decyzji,
- mieszkańcem, który może się uczyć, mylić, przegrywać, rozwijać i tworzyć własną historię.

> **Nie dajemy modelowi opisu całego CHAOS. Dajemy mu komputer CHAOS, własne konto oraz prawo używania ich na tych samych zasadach co człowiek.**

To jest **CHAOS Autonomous Player**.
