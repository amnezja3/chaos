# CHAOS — CAMERA VISUAL NETWORK

### System wizualnego podglądu kamer i archiwizacji rzeczywistych lokalizacji

## Koncepcja projektu

Wprowadzamy do świata CHAOS nową warstwę wizualną istniejącego systemu kamer, pozwalającą graczom zobaczyć rzeczywiste otoczenie miejsca, w którym uruchomili narzędzie mapowe „Podgląd kamery”.

Nie tworzymy nowego mechanizmu rozgrywki ani nie przebudowujemy istniejącego systemu kamer. Rozbudowujemy jego możliwości o prezentację rzeczywistych fotografii lokalizacji, połączonych z efektami symulującymi cyfrowy monitoring, zakłócenia transmisji i pracę systemów obserwacyjnych.

Podstawowym źródłem fotografii będzie platforma Mapillary, udostępniająca zdjęcia ulic, dróg i innych przestrzeni geograficznych wraz z informacjami o ich lokalizacji.

Naszym celem nie jest jednak stworzenie odpowiednika Google Street View ani umożliwienie graczom swobodnego poruszania się po panoramach 360 stopni.

Potrzebujemy jedynie dwóch lub trzech fotografii przedstawiających rzeczywiste otoczenie wskazanego miejsca.

Na ich podstawie system CHAOS będzie generował własną, krótką animację przypominającą transmisję z kamery monitoringu.

W ten sposób prawdziwe miejsca na świecie zyskają dodatkową reprezentację wizualną w świecie gry.

## Integracja z istniejącym gameplayem

Kamery stanowią już istotny element mechaniki CHAOS i są powiązane z istniejącymi narzędziami mapowymi oraz zasadami rozgrywki.

Nowa funkcjonalność nie może ingerować w te mechanizmy.

Po uruchomieniu narzędzia „Podgląd kamery” gra będzie wykonywała wszystkie dotychczasowe operacje, a dodatkowo uruchomi system odpowiedzialny za przygotowanie i wyświetlenie rzeczywistego obrazu lokalizacji.

Gracz zobaczy niewielki interfejs przypominający terminal monitoringu, w którym pojawi się obraz z wybranego miejsca.

Nie będzie to transmisja na żywo. Będzie to symulacja obrazu z kamery, stworzona na podstawie archiwalnych fotografii.

Jest to świadomy element projektu.

System może wykorzystywać zdjęcia wykonane wiele miesięcy lub lat wcześniej, dlatego nie będzie przedstawiał ich jako aktualnej sytuacji w danej lokalizacji.

Jednocześnie wygląd interfejsu, cyfrowe zakłócenia i sposób prezentacji sprawią, że materiał będzie naturalnie wpisywał się w estetykę świata CHAOS.

## Pozyskiwanie obrazów z Mapillary

Kiedy gracz uruchomi kamerę, backend CHAOS sprawdzi współrzędne geograficzne miejsca obserwacji.

Następnie zweryfikuje, czy dla tej lokalizacji istnieje już przygotowany materiał wizualny w archiwum gry.

Jeżeli materiał istnieje, system natychmiast udostępni go graczowi.

Jeżeli nie, backend sprawdzi możliwość pobrania nowych fotografii z Mapillary.

System wyszuka obrazy znajdujące się możliwie blisko wskazanych współrzędnych.

W pierwszej kolejności będziemy preferować fotografie należące do tej samej sekwencji, ponieważ pozwoli to uzyskać kilka spójnych ujęć tego samego miejsca.

Docelowo wybierane będą maksymalnie trzy fotografie.

Nie wymagamy pełnych panoram ani bardzo wysokiej rozdzielczości.

Wystarczą zwykłe fotografie uliczne przedstawiające dany obszar.

System powinien również kontrolować odległość między lokalizacją kamery a miejscem wykonania zdjęć, aby nie prezentować przypadkowych obrazów z odległych punktów.

Jeżeli nie znajdziemy fotografii spełniających wymagania, kamera przejdzie do jednego z przygotowanych scenariuszy braku obrazu.

## Przetwarzanie i optymalizacja fotografii

Bardzo ważnym elementem całego rozwiązania będzie automatyczny system przetwarzania pobieranych zdjęć.

Nie chcemy przechowywać na serwerze CHAOS oryginalnych fotografii w pełnej rozdzielczości.

Byłoby to niepotrzebne obciążenie przestrzeni dyskowej, transferu i infrastruktury.

Dlatego wszystkie pobrane materiały będą trafiały najpierw do serwerowego procesu obróbki.

Proces ten zostanie uruchomiony w tle, niezależnie od głównej obsługi rozgrywki.

Po pobraniu fotografii system przeskaluje ją do ustalonej maksymalnej rozdzielczości. Wstępnie przyjmujemy 960 na 540 pikseli, z zachowaniem oryginalnych proporcji obrazu.

Następnie fotografia zostanie skonwertowana do formatu WebP.

Początkowa jakość kompresji zostanie ustawiona na około 70 procent, co powinno zapewnić dobry kompromis między jakością wizualną a wielkością plików.

Wszystkie te parametry będą konfigurowalne z poziomu administracyjnego.

Proces przetwarzania będzie również usuwał zbędne metadane z plików graficznych.

Informacje potrzebne do identyfikacji źródła, autora, lokalizacji, daty wykonania zdjęcia i licencji zostaną zachowane osobno w bazie danych.

Po prawidłowym przetworzeniu i zapisaniu zoptymalizowanych materiałów pliki źródłowe zostaną usunięte z przestrzeni tymczasowej.

Docelowo w archiwum CHAOS pozostaną wyłącznie zoptymalizowane obrazy.

Dodatkowo zastosujemy mechanizm deduplikacji, dzięki któremu identyczne materiały nie będą wielokrotnie zapisywane.

Kilka kamer obserwujących ten sam obszar będzie mogło korzystać ze wspólnego zestawu fotografii.

Dzięki temu rozbudowa sieci kamer nie będzie powodowała niekontrolowanego wzrostu zajętości dysku.

## Archiwum wizualne świata CHAOS

Każda lokalizacja, dla której system przygotuje zestaw obrazów, zostanie zarejestrowana w archiwum wizualnym CHAOS.

Archiwum będzie przechowywało powiązanie między lokalizacją geograficzną, kamerą oraz przygotowanymi fotografiami.

W bazie znajdą się między innymi współrzędne geograficzne, identyfikatory obrazów, źródło fotografii, data wykonania, data archiwizacji oraz informacje o przetworzonych plikach.

Dzięki temu kolejne uruchomienia podglądu w tej samej lokalizacji nie będą wymagały ponownego pobierania zdjęć z Mapillary.

Z czasem powstanie w ten sposób rozbudowane archiwum rzeczywistych miejsc na świecie.

Co istotne, archiwum będzie rozwijało się organicznie, wraz z aktywnością graczy.

Każde uruchomienie kamery w nowym miejscu może prowadzić do pozyskania kolejnego zestawu fotografii.

Gracze, korzystając ze standardowych mechanik rozgrywki, będą więc pośrednio rozbudowywali wizualną reprezentację świata CHAOS.

Nie będziemy pobierać całej bazy Mapillary ani masowo archiwizować świata z wyprzedzeniem.

Materiały będą pozyskiwane na żądanie, wyłącznie tam, gdzie rzeczywiście zostanie wykorzystane narzędzie podglądu kamery.

Sposób przechowywania i ponownego udostępniania materiałów musi oczywiście pozostawać zgodny z aktualnymi warunkami API oraz licencjami fotografii Mapillary. Przed wdrożeniem produkcyjnym zweryfikujemy dopuszczalność takiego archiwum, zasady oznaczania autorów i ewentualne wymagania dotyczące materiałów przetworzonych.

## Generowanie obrazu monitoringu

Po przygotowaniu zdjęć system będzie prezentował je jako symulowany obraz z kamery.

Nie planujemy generowania osobnych plików wideo.

Byłoby to niepotrzebne i zwiększałoby wykorzystanie zasobów serwera.

Zamiast tego wykorzystamy dwa lub trzy nieruchome obrazy oraz animacje wykonywane bezpośrednio w przeglądarce użytkownika.

Fotografie będą zmieniały się w określonych lub nieregularnych odstępach czasu.

Dodamy bardzo delikatne przesunięcia kadru, cyfrowe przybliżenia, krótkie zatrzymania obrazu oraz efekty przypominające niestabilną transmisję.

Na obraz zostanie nałożony interfejs monitoringu CHAOS.

Może on zawierać identyfikator kamery, współrzędne GPS, oznaczenie aktywnego połączenia, wskaźnik jakości sygnału i elementy interfejsu charakterystyczne dla świata gry.

Całość uzupełnimy subtelnymi zakłóceniami cyfrowymi, szumem, liniami skanowania i sporadycznymi glitchami.

Ważne, aby efekty te nie były przesadzone.

Gracz powinien przede wszystkim zobaczyć rzeczywiste otoczenie lokalizacji.

Animacje mają budować atmosferę, a nie zasłaniać właściwy obraz.

Ponieważ wszystkie efekty będą realizowane po stronie przeglądarki, obciążenie serwera pozostanie niewielkie.

## System zakłóceń i scenariusze awaryjne

Nie każda próba uruchomienia podglądu zakończy się wyświetleniem rzeczywistych fotografii.

Może się zdarzyć, że dla danej lokalizacji Mapillary nie posiada zdjęć.

Może również wystąpić problem z połączeniem z zewnętrznym API, przekroczenie limitu zapytań, brak dostępnego budżetu integracji albo chwilowa niedostępność usługi.

Dlatego przygotujemy kilka niezależnych scenariuszy wizualnych.

Pierwszym będzie klasyczny czarny ekran z komunikatem „NO SIGNAL”.

Drugim ekran z intensywnym szumem przypominającym zakłócenia starej telewizji.

Trzecim scenariuszem będzie „CAMERA OFFLINE”, czyli ciemny ekran z niewielką kontrolką informującą o niedostępności obrazu.

Kolejny wariant to „SIGNAL LOST”, w którym obraz zanika, pojawiają się krótkie trzaski i komunikat o utracie połączenia.

Możemy również wykorzystać scenariusz „SIGNAL UNSTABLE”, gdzie obraz pojawia się na moment, ulega zakłóceniom, a następnie ponownie znika.

Dodatkowym wariantem będzie „ARCHIVE CORRUPTED”, wykorzystujący uszkodzone fragmenty obrazu, cyfrowe przesunięcia i glitche.

Scenariusze będą wybierane przez system według ustalonych zasad.

Niektóre mogą być przypisane do określonych stanów kamery, a inne wybierane pseudolosowo.

Ważne jednak, aby wizualny komunikat nie był traktowany jako rzeczywisty raport techniczny.

Przykładowo brak fotografii w Mapillary nie oznacza, że kamera w świecie gry została wyłączona.

Dlatego stan gameplayu i stan warstwy wizualnej muszą pozostać niezależne.

Administracja będzie zawsze znała faktyczną przyczynę problemu, nawet jeżeli gracz zobaczy jedynie klimatyczny ekran zakłóceń.

## Zarządzanie integracją w panelu administracyjnym

Cały system będzie kontrolowany z poziomu istniejącego panelu administracyjnego CHAOS.

Dodamy sekcję odpowiedzialną za integrację z Mapillary i zarządzanie archiwum kamer.

Administrator będzie mógł włączać i wyłączać integrację, kontrolować dostępność dostawcy oraz ustalać maksymalną liczbę zapytań do API.

Wprowadzimy również własny system limitów i budżetów.

Nie zakładamy, że Mapillary musi być usługą rozliczaną za każde pobranie. Chodzi o stworzenie niezależnego mechanizmu kontroli zużycia zasobów, który będzie działał także wtedy, gdy dostawca zmieni zasady dostępu.

Administrator będzie mógł ustawić maksymalną liczbę nowych archiwów w ciągu doby, limity zapytań oraz sposób zachowania systemu po ich przekroczeniu.

Jeśli dostępny limit zostanie wyczerpany, backend przestanie inicjować nowe pobrania.

Istniejące materiały archiwalne nadal będą dostępne.

Dla lokalizacji, które nie posiadają jeszcze własnego archiwum, system uruchomi odpowiedni scenariusz zakłóceń.

W panelu znajdą się również ustawienia przetwarzania obrazów.

Będzie można zmieniać maksymalną rozdzielczość, jakość kompresji WebP, liczbę zapisywanych fotografii oraz ograniczenia przestrzeni dyskowej.

Administrator zobaczy także liczbę zarchiwizowanych lokalizacji, liczbę obrazów, zajętość dysku i statystyki wykorzystania API.

Przewidujemy również narzędzia pozwalające usuwać niepotrzebne archiwa, ponawiać nieudane pobrania i zarządzać stanem całego systemu.

## Architektura i bezpieczeństwo działania

Integracja będzie działała po stronie backendu CHAOS.

Klucze dostępowe Mapillary nie będą udostępniane przeglądarce gracza.

Wszystkie zapytania przejdą przez naszą warstwę serwerową, która będzie kontrolowała limity, uprawnienia i dostępność materiałów.

Pobieranie oraz obróbka fotografii zostaną przeniesione do osobnego procesu działającego w tle.

Jeżeli kilka osób jednocześnie uruchomi kamery w tej samej lokalizacji, system powinien rozpoznać istniejące zadanie i uniknąć wielokrotnego pobierania tych samych materiałów.

Każde zadanie będzie miało określony stan, od oczekiwania na pobranie, przez przetwarzanie, aż po gotowe archiwum lub błąd.

Podczas przygotowywania nowych fotografii gracz może zobaczyć animację synchronizacji albo niestabilnego sygnału.

Po zakończeniu przetwarzania interfejs automatycznie przełączy się na gotowy podgląd.

Najważniejsza zasada architektoniczna jest jednak bardzo prosta.

Awaria Mapillary, brak fotografii, przekroczenie limitu albo błąd przetwarzania obrazów nie mogą zakłócić podstawowych mechanik gry.

Warstwa wizualna będzie dodatkiem do istniejącego systemu kamer, a nie jego techniczną zależnością.

Jeżeli integracja przestanie działać, gracz nadal będzie korzystał z kamery zgodnie z dotychczasowymi zasadami gameplayu.

Zmieni się wyłącznie sposób prezentacji obrazu.

## Znaczenie systemu dla świata CHAOS

Najciekawszym elementem całego rozwiązania nie jest sama możliwość wyświetlania zdjęć ulic.

Znacznie ważniejsze jest to, że CHAOS zacznie gromadzić własną wizualną pamięć rzeczywistego świata.

Każda nowa lokalizacja odwiedzona za pomocą narzędzia podglądu kamery może zostać zapisana w archiwum.

Po pewnym czasie powstanie sieć setek lub tysięcy punktów obserwacyjnych, których zawartość będzie dostępna bez konieczności ponownego korzystania z zewnętrznego dostawcy, w granicach dozwolonych przez jego licencje.

To archiwum będzie powstawało naturalnie, bez konieczności ręcznego przygotowywania materiałów przez administratorów.

Co więcej, cały system będzie powiązany z istniejącymi zasadami świata CHAOS.

Dostęp do kamer, możliwość ich wykorzystania, przejmowania czy hakowania pozostaną uzależnione od aktualnych mechanik rozgrywki.

Nie tworzymy nowego, niezależnego systemu uprawnień.

Rozszerzamy możliwości elementu, który już istnieje i odgrywa ważną rolę w grze.

Jednocześnie archiwum nie musi być traktowane wyłącznie jako zbiór fotografii.

W przyszłości może stać się podstawą kolejnych mechanik związanych z rozpoznaniem terenu, analizą lokalizacji, informacją wywiadowczą czy działalnością klanów.

Nie wprowadzamy jednak tych funkcji w pierwszym etapie.

Na początek skupiamy się na stabilnym pozyskiwaniu, przetwarzaniu, przechowywaniu i wyświetlaniu obrazów.

## Podsumowanie i kierunek realizacji

System CAMERA VISUAL NETWORK będzie niewielkim, ale istotnym rozszerzeniem istniejących kamer w CHAOS.

Jego zadaniem będzie dodanie rzeczywistego obrazu otoczenia do narzędzia mapowego „Podgląd kamery”.

Fotografie będą pozyskiwane z Mapillary wyłącznie wtedy, gdy będzie to potrzebne.

Każda nowa lokalizacja otrzyma maksymalnie trzy wybrane obrazy, które zostaną automatycznie zoptymalizowane i zapisane w archiwum CHAOS, pod warunkiem spełnienia wymagań licencyjnych.

Zamiast generowania materiałów wideo wykorzystamy lekkie animacje przeglądarkowe, cyfrowe zakłócenia i stylistykę monitoringu.

Cały proces będzie nadzorowany przez panel administracyjny, w którym znajdą się limity API, ustawienia optymalizacji, kontrola zasobów i zarządzanie archiwami.

W przypadku braku obrazu system wyświetli jeden z kilku przygotowanych scenariuszy awaryjnych.

Nie wpłynie to jednak na podstawową funkcjonalność kamery ani pozostałe mechaniki rozgrywki.

**Ostatecznie chcemy osiągnąć jeden efekt: gracz uruchamia kamerę w dowolnym miejscu świata CHAOS i, jeżeli dostępne są odpowiednie materiały, widzi rzeczywiste otoczenie tej lokalizacji przedstawione jako przechwycony obraz z systemu monitoringu.**

Bez ciężkich panoram, bez transmisji wideo, bez niepotrzebnego obciążania serwera.

A przy okazji każde takie uruchomienie może wzbogacać wspólne archiwum wizualne świata gry.

**CHAOS nie tylko korzysta z rzeczywistej mapy świata. Zaczyna również zapamiętywać, jak ten świat wygląda.**
