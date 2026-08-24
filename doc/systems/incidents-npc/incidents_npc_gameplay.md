# CHAOS — incydenty, służby NPC i Response Network

## Status dokumentu

Dokument opisuje docelowy gameplay publicznych incydentów oraz jednostek NPC policji, cyberpolicji i służb specjalnych.

System roboczo nazywa się **Response Network**. Łączy operacje, ryzyko, mapę, BlackNet, teleporty, PvP, terytoria i konsekwencje wykrycia operatora.

Dokument jest podstawą do późniejszego przygotowania architektury technicznej oraz sprintów implementacyjnych.

## Cel systemu

Aktywność gracza nie może pozostawać prywatną animacją widoczną wyłącznie dla niego.

Głośne operacje powinny zostawiać publiczny ślad:

```text
operacja
→ emisja śladu
→ powstanie incydentu
→ reakcja służb
→ publiczna aktywność na mapie
→ sygnał BlackNetu
→ teleporty i napływ graczy
→ ryzyko PvP oraz zatrzymania
```

Response Network ma powodować, że gracze przemieszczają się do aktywnych miejsc, obserwują działania innych operatorów, podejmują ryzyko i nie ograniczają rozgrywki wyłącznie do rozwijania własnego lokalnego terytorium.

## Heat — ślad operacji

Każda operacja może emitować `heat`, czyli poziom wykrywalnej aktywności.

Na wysokość heat wpływają:

- typ hakowanego obiektu;
- rodzaj operacji;
- użyte narzędzie;
- czas działania;
- poziom zabezpieczeń;
- jakość i dyskrecja aplikacji;
- liczba równoczesnych operacji;
- przejmowanie terytorium;
- konflikt PvP;
- obecność części GhostNetwork;
- wcześniejsze wykrycia operatora;
- aktywne wirusy, sniffery i implanty;
- używanie supermocy profesji.

Nie każda operacja powoduje pojawienie się służb. Cicha operacja może zakończyć się bez reakcji. Głośna, długa albo wielokrotnie wykrywana operacja podnosi heat do poziomu tworzącego incydent.

## Incydent

Incydent jest publicznym zdarzeniem świata przypisanym do konkretnego miejsca aktywności.

Przechowuje co najmniej:

- centrum zdarzenia;
- poziom heat;
- priorytet reakcji;
- promień poszukiwań;
- rodzaj służb;
- czas rozpoczęcia;
- przewidywany czas trwania;
- powiązane operacje;
- podejrzanych operatorów;
- aktywne jednostki NPC;
- powiązane terytoria;
- stan eskalacji i wygaszania.

Inni gracze nie widzą automatycznie, kto wywołał incydent. Widzą obecność służb, skalę reakcji oraz przybliżone centrum poszukiwań.

## Źródła incydentów

Incydent może powstać wskutek:

- wykrytego hakowania obiektu;
- długiej operacji zbierającej dane;
- instalowania implantu;
- głośnego przejęcia celu;
- rozbijania terytorium;
- konfliktu kilku operatorów;
- ataku na gracza;
- walki o część GhostNetwork;
- równoczesnych operacji w jednym obszarze;
- narastającego śladu operatora ze statusem `Judgment`.

Kilka operacji wykonywanych blisko siebie powinno zasilać jeden wspólny incydent, zamiast tworzyć osobne grupy NPC dla każdego działania.

## Poziomy reakcji

### Poziom 1 — patrol lokalny

Na mapie pojawiają się zwykłe radiowozy albo patrole.

Charakterystyka:

- mały promień wykrywania;
- wolne przemieszczanie;
- krótki czas reakcji;
- niewielkie konsekwencje;
- słabe rozpoznanie operatorów.

Pojawia się przy pojedynczych, nieostrożnych operacjach.

### Poziom 2 — policja dochodzeniowa

Więcej jednostek patroluje obszar i sprawdza pobliskie cele.

Charakterystyka:

- większy promień;
- dłuższy czas działania;
- lepsze śledzenie;
- możliwość kontroli kilku obiektów;
- większa konfiskata HC;
- ryzyko utraty użytego narzędzia.

### Poziom 3 — cyberpolicja

Pojawiają się wozy techniczne, mobilne stanowiska i taktobusy.

Charakterystyka:

- szeroki zasięg cyfrowego skanu;
- szybsze wykrywanie podejrzanych;
- możliwość wykrywania aktywnych robaków i implantów;
- wysoka szansa konfiskaty narzędzia;
- anulowanie operacji;
- czyszczenie celu z pozostawionego dostępu.

### Poziom 4 — służby specjalne

Pojawiają się nieoznakowane samochody, limuzyny, jednostki obserwacyjne i zespoły specjalne.

Charakterystyka:

- duży promień;
- kilka niezależnych patroli;
- długie utrzymywanie incydentu;
- śledzenie operatorów opuszczających obszar;
- poważne konfiskaty;
- możliwość nadania statusu `Judgment`;
- zainteresowanie powiązanymi operacjami albo klanem.

Nazwy i wygląd jednostek mogą łączyć współczesne służby z projekcją systemów bezpieczeństwa z 2108 roku.

## Jednostki NPC na mapie

Jednostki służb są osobnymi, publicznymi obiektami mapy.

Każda jednostka posiada:

- identyfikator;
- typ;
- aktualną pozycję;
- centrum incydentu;
- prędkość;
- promień patrolu;
- promień wykrywania;
- poziom służby;
- kierunek ruchu;
- listę podejrzanych;
- czas pozostały do wycofania.

NPC nie stoją nieruchomo. Przemieszczają się wokół centrum zdarzenia i aktualizują pozycję przy kontrolowanych krokach świata, podobnie jak inne ruchome sygnały mapy.

W pierwszej wersji nie muszą korzystać z rzeczywistej siatki dróg. Mogą poruszać się w logicznym promieniu wokół celu. Później można dołożyć poruszanie po trasach ulicznych.

## Promień wykrywania

Każda jednostka posiada widoczny albo możliwy do oszacowania promień wykrywania.

Przykładowa skala:

- patrol lokalny: około 50–100 metrów;
- policja dochodzeniowa: około 100–200 metrów;
- cyberpolicja: większy promień cyfrowego skanu;
- służby specjalne: kilka nakładających się stref.

Dokładne wartości będą elementem balansu.

Samo wejście w geometryczny promień nie zawsze oznacza natychmiastowe zatrzymanie. Jednostka musi wykonać skuteczny skan podejrzanego albo wykryć aktywną operację.

## Ostrzeżenie przed reakcją

NPC nie mogą pojawiać się bezpośrednio na operatorze i natychmiast go zatrzymywać.

Podejrzany otrzymuje krótkie ostrzeżenie:

```text
WYKRYTO REAKCJĘ SŁUŻB
CZAS DO PIERWSZEGO PATROLU: 00:18
OPUŚĆ STREFĘ
```

Jednostki pojawiają się na obrzeżu incydentu i rozpoczynają poszukiwania. Gracz może:

- przerwać operację;
- opuścić strefę;
- próbować dokończyć działanie;
- ukryć ślad;
- poprosić innych graczy o pomoc;
- zaryzykować zatrzymanie.

## Podejrzani operatorzy

Incydent przechowuje listę operatorów i operacji, które go wywołały.

Główny sprawca posiada najwyższy poziom podejrzenia. NPC aktywnie szukają przede wszystkim jego.

Inni gracze mogą zostać dopisani do incydentu, jeżeli w strefie służb zaczną:

- hakować cel;
- atakować gracza;
- rozbrajać terytorium;
- instalować narzędzie;
- przejmować obiekt;
- używać agresywnej supermocy;
- emitować własny heat.

Samo obserwowanie incydentu nie oznacza automatycznego wpisania na listę podejrzanych.

## Bezpieczeństwo na własnym terytorium

Gracz jest bezpieczny na swoim stabilnym terytorium, jeżeli aktywny incydent nie dotyczy żadnego z jego terytoriów.

Oznacza to, że policja albo inne służby mogą przejechać w pobliżu lub przez obszar gracza, ale nie zatrzymują właściciela wyłącznie dlatego, że znajduje się on u siebie.

Zasada chroni szczególnie graczy nieaktywnych i offline.

Jeżeli gracz:

- jest wylogowany;
- pozostaje bierny;
- znajduje się na własnym terytorium;
- nie jest podejrzanym w danym incydencie;
- incydent nie jest powiązany z żadnym z jego terytoriów;

nie może zostać aresztowany, ukarany ani pozbawiony narzędzi przez przejeżdżający patrol.

Własne terytorium nie daje jednak pełnej, uniwersalnej nietykalności.

Ochrona nie działa, gdy:

- incydent został wywołany przez operację gracza;
- incydent dotyczy obiektu albo konfliktu na jego terytorium;
- terytorium jest aktywnie przeszukiwane;
- gracz znajduje się na liście podejrzanych;
- gracz rozpoczyna nową nielegalną operację w zasięgu służb;
- gracz atakuje NPC albo innego operatora w strefie;
- jego terytorium uczestniczy w konflikcie związanym z incydentem.

Najkrótsza reguła brzmi:

> Własne terytorium chroni przed przypadkowym zatrzymaniem, ale nie chroni przed konsekwencjami incydentu dotyczącego tego terytorium albo jego właściciela.

## Gracze offline

Gracz offline nie wykonuje aktywnych operacji i nie może reagować na ruch NPC. Dlatego nie może zostać nowym podejrzanym wyłącznie wskutek zmiany pozycji patrolu.

Jeżeli był podejrzanym przed wylogowaniem, jego rozpoczęta wcześniej operacja nadal może zostać przerwana zgodnie z jej zasadami. System nie powinien jednak wykonywać osobnego zatrzymania awatara tylko dlatego, że gracz pozostaje offline na swoim niezwiązanym z incydentem terytorium.

Wylogowanie nie może służyć do natychmiastowego anulowania już rozstrzygniętego wykrycia. Jeżeli skan NPC zakończył się sukcesem przed wylogowaniem, konsekwencje zostają zapisane.

## Warunek zatrzymania

Do zatrzymania dochodzi, gdy łącznie spełnione są odpowiednie warunki:

- operator jest podejrzany albo wykonuje wykrywalną aktywność;
- znajduje się w zasięgu jednostki;
- NPC wykonuje skuteczny skan;
- poziom podejrzenia przekracza próg jednostki;
- nie obowiązuje ochrona niezwiązanego własnego terytorium;
- operator nie zdążył przerwać działania lub opuścić strefy.

## Konsekwencje zatrzymania

Skutki dotyczą operacji, która wywołała wykrycie.

System może:

1. Natychmiast zakończyć operację.
2. Usunąć cel z aktywnych targetów gracza.
3. Cofnąć niezakończony postęp przejęcia.
4. Nie przyznać RSP ani postępu LVL.
5. Nie powiększyć terytorium.
6. Usunąć pozostawiony dostęp do celu.
7. Skonfiskować narzędzie użyte podczas operacji.
8. Skonfiskować część HC.
9. Zapisać zatrzymanie w historii operatora.
10. Nadać status `Judgment` przy poważnym incydencie.

Jeżeli wykrycie dotyczy walki o terytorium, nieukończone przejęcie zostaje przerwane. Zatrzymanie nie powinno automatycznie usuwać wcześniej legalnie zbudowanych, niezwiązanych terytoriów.

## Konfiskata narzędzia

Każda operacja musi przechowywać informację o użytym narzędziu. Konfiskata dotyczy właśnie tego narzędzia, a nie losowej aplikacji z arsenału.

Przykład:

```text
OPERACJA: PRZEJĘCIE CELU
NARZĘDZIE: X-MAPPER
WYKRYCIE: CYBERPOLICJA
SKUTEK: X-MAPPER SKONFISKOWANY
```

Jeżeli skonfiskowane narzędzie jest jedynym podstawowym narzędziem niezbędnym do dalszej gry, gracz powinien zachować słabą wersję awaryjną albo mieć możliwość ponownego zdobycia podstawowego odpowiednika. System nie może trwale zablokować dalszej rozgrywki.

## Konfiskata HC

Wysokość konfiskaty zależy od poziomu reakcji:

- patrol — niewielka część salda;
- policja dochodzeniowa — większy procent;
- cyberpolicja — wysoka kara;
- służby specjalne — prawie całe dostępne saldo.

Kara dotyczy środków znajdujących się aktualnie w Wallet HC. Nie usuwa historii zarobków, zakupionych wcześniej przedmiotów ani osiągnięć.

## Status `Judgment`

Przy poważnym zatrzymaniu operator może otrzymać czasowy status `Judgment`.

Może on powodować:

- większą podatność na kolejne wykrycie;
- dłuższe utrzymywanie śladu;
- wyższy poziom początkowej reakcji;
- ostrzeżenie widoczne w profilu;
- ograniczenie wybranych działań;
- możliwość wykupienia albo odpracowania konsekwencji;
- zainteresowanie BlackNetu oraz innych graczy.

Status nie musi być permanentny. Jest pamięcią systemu o niedawnym zatrzymaniu operatora.

## Publiczny hotspot

Obecność służb informuje świat, że w danym miejscu dzieje się coś ważnego.

Pozostali gracze widzą:

- rodzaj jednostek;
- liczbę patroli;
- poziom reakcji;
- promień aktywności;
- czas trwania incydentu;
- przybliżone centrum poszukiwań.

Nie widzą automatycznie sprawcy ani rodzaju wykonywanej operacji.

Mogą:

- teleportować się do hotspotu;
- obserwować ruch służb;
- szukać podejrzanego;
- próbować przejąć cel;
- atakować innych operatorów;
- bronić członka własnego klanu;
- wykorzystać chaos do własnej operacji.

Każda dodatkowa nielegalna aktywność może podnieść poziom incydentu.

## BlackNet i teleporty

Incydent może automatycznie wygenerować deterministyczny sygnał BlackNetu:

```text
WZROST AKTYWNOŚCI // BERLIN
3 JEDNOSTKI W STREFIE
REAKCJA: CYBERPOLICJA
HEAT: WYSOKI
```

CTA może:

- otworzyć lokalizację na mapie;
- umożliwić zdobycie teleportu;
- otworzyć publiczny widok incydentu.

Teleport nie gwarantuje bezpiecznego wejścia. Gracz trafia w okolice zdarzenia i sam decyduje, czy zbliżyć się do strefy służb.

## PvP w strefie incydentu

Incydent tworzy naturalne miejsce konfliktu pomiędzy graczami.

Operatorzy mogą:

- szukać sprawcy;
- przejąć porzucony cel;
- wykorzystać osłabienie przeciwnika;
- pomóc członkowi klanu opuścić obszar;
- zaatakować graczy skupionych wokół hotspotu;
- odciągnąć uwagę służb własną operacją;
- próbować dokończyć przerwane przejęcie.

NPC nie stają się automatycznie sojusznikami żadnego klanu. Reagują na podejrzanych oraz wykrytą aktywność.

## Terytoria

Incydent może zostać powiązany z terytorium, jeżeli źródłem heat jest:

- przejmowanie obiektu wewnątrz obszaru;
- rozbijanie filarów;
- obrona celu;
- konflikt granic;
- operacja właściciela dotycząca tego obszaru.

W takim przypadku właściciel nie korzysta z ochrony bezpiecznego terytorium dla tego konkretnego incydentu.

Terytoria niezwiązane z incydentem pozostają bezpieczne dla swoich biernych i offline właścicieli.

## GhostNetwork

Walki o części powinny generować szczególnie silny heat.

Jeżeli wielu graczy:

- atakuje strategiczne terytorium;
- rozbraja filary;
- broni aktywnej części;
- używa supermocy;
- wykonuje równoległe operacje;

Response Network może eskalować incydent.

Walka o część przyciąga wtedy:

- służby NPC;
- sygnały BlackNetu;
- graczy innych klanów;
- oportunistów;
- obrońców;
- łowców podejrzanych.

Niższe jednostki reagują na anomalną aktywność bez wiedzy o GhostNetwork. Wyższe poziomy służb mogą fabularnie pozostawać pod wpływem zalążków MASA.

## Łączenie operacji w jeden incydent

Operacje wykonywane blisko siebie i w zbliżonym czasie powinny zasilać wspólny incydent:

```text
kilka operacji w jednym obszarze
→ wspólny heat
→ eskalacja istniejącego incydentu
→ więcej albo silniejsze jednostki
```

Łączenie ogranicza liczbę obiektów NPC i sprawia, że aktywność wielu graczy tworzy jeden czytelny hotspot.

## Wygaszanie incydentu

Jeżeli aktywność ustaje:

- heat stopniowo spada;
- część jednostek odjeżdża;
- promień poszukiwań maleje;
- priorytet reakcji się obniża;
- incydent ostatecznie znika.

Nowa operacja w obszarze może przedłużyć czas albo ponownie podnieść poziom reakcji.

Po zakończeniu incydentu pozostaje zapis historyczny potrzebny do:

- audytu;
- statusu `Judgment`;
- narracji BlackNetu;
- statystyk operatora;
- wykrywania powtarzalnych wzorców.

## Radio i Cyberner

Cyberner może przekazywać:

- publiczne ostrzeżenia;
- komunikaty klanowe;
- informacje o eskalacji;
- wiadomości o zatrzymaniu;
- rozmowy graczy organizujących pomoc albo polowanie.

Radio może relacjonować największe incydenty, ale nie powinno przerywać odtwarzania przy każdym zwykłym patrolu. Komunikaty alarmowe są przeznaczone dla wysokich poziomów reakcji albo wydarzeń GhostNetwork.

## Zasady uczciwości gameplayu

1. NPC nie pojawiają się bezpośrednio na podejrzanym.
2. Podejrzany otrzymuje krótkie ostrzeżenie.
3. Zasięg jednostek jest widoczny albo możliwy do oszacowania.
4. Ruch odbywa się w przewidywalnych krokach.
5. Kara dotyczy konkretnej wykrytej operacji.
6. Konfiskowane jest narzędzie użyte do naruszenia.
7. Incydent niskiego poziomu nie odbiera całego dorobku.
8. Gracz nie może zostać trwale zablokowany przez konfiskatę podstawowego narzędzia.
9. Obserwowanie incydentu nie oznacza automatycznej kary.
10. Nielegalna aktywność obserwatora może uczynić go podejrzanym.
11. Własne niezwiązane terytorium chroni biernego i offline właściciela.
12. Wylogowanie nie anuluje wykrycia rozstrzygniętego przed zakończeniem sesji.

## Integracja z istniejącymi systemami

```text
OPERACJE
generują heat

MAPA
pokazuje służby i hotspoty

BLACKNET
publikuje aktywne miejsca

TELEPORTY
przenoszą graczy w okolice zdarzeń

PVP
pozwala szukać sprawców i wykorzystywać chaos

TERYTORIA
dają kontekst konfliktu i ochronę biernych właścicieli

GHOSTNETWORK
tworzy najgorętsze incydenty strategiczne

GOOGLEPLEX
pozwala ponownie zdobyć skonfiskowane narzędzia

GHOST EXCHANGE
dostarcza HC potrzebne po konfiskacie

CYBERNER
pozwala ostrzegać, organizować pomoc i polować

RADIO
relacjonuje największe wydarzenia
```

## Decyzje wymagające późniejszego balansu

Dokument nie ustala jeszcze:

- liczbowych progów heat;
- dokładnych promieni jednostek;
- częstotliwości kroków ruchu;
- szansy skutecznego skanu;
- czasu ostrzeżenia;
- procentów konfiskaty HC;
- listy narzędzi chronionych przed pełnym softlockiem;
- czasu trwania statusu `Judgment`;
- dokładnych nazw i wyglądu wszystkich służb;
- zasad poruszania po rzeczywistej sieci dróg;
- finalnego algorytmu łączenia kilku operacji w jeden incydent.

Te wartości powinny zostać ustalone w sprintach i testach gameplayowych bez zmiany podstawowych reguł systemu.

## Najważniejsze decyzje

1. Operacje mogą emitować heat widoczny dla Response Network.
2. Incydent jest publicznym zdarzeniem mapy.
3. Jednostki NPC poruszają się i posiadają własne promienie wykrywania.
4. NPC szukają podejrzanych, a nie wszystkich graczy bez wyjątku.
5. Obserwator staje się podejrzanym dopiero po własnej wykrywalnej aktywności.
6. Zatrzymanie przerywa wykrytą operację i odbiera jej przyszłe korzyści.
7. Konfiskata dotyczy narzędzia użytego podczas naruszenia.
8. Poziom służb określa skalę konfiskaty HC i pozostałych konsekwencji.
9. Własne terytorium chroni biernego albo offline właściciela, jeżeli incydent nie dotyczy żadnego z jego terytoriów.
10. Incydent związany z terytorium wyłącza tę ochronę dla właściciela i uczestników operacji.
11. BlackNet może zamieniać incydenty w publiczne hotspoty oraz teleporty.
12. Wiele pobliskich operacji zasila jeden wspólny incydent.
13. Walki o części GhostNetwork generują szczególnie silne reakcje.
14. Incydent wygasa po ustaniu aktywności, ale pozostawia historię.
15. System ma łączyć aktywność jednego gracza z reakcją całej mapy.

> Aktywność operatora przestaje być prywatną animacją. Zostawia publiczny ślad, przyciąga służby i informuje cały świat, że właśnie w tym miejscu dzieje się coś wartego ryzyka.
