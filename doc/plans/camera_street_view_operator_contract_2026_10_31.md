# CHAOS — CAMERA STREET VIEW

## Aktualizacja sprintów 164, 165 i 166

### Przejście z prototypowania do właściwej implementacji

### 1. Status projektu — prototyp zaakceptowany

Faza prototypowania wizualnego Camera Street View została zakończona.

Główny podgląd kamery, okno Ghost Systemu, ruch kadru, efekty zakłóceń oraz sześć scenariuszy prezentacji zostały zaakceptowane przez operatora i otrzymały status `PASS`.

**Nie wracamy do projektowania wyglądu.**

Zaakceptowany prototyp jest obowiązującym wzorcem dla dalszej implementacji.

Nie tworzymy nowych demonstratorów, osobnych środowisk prezentacyjnych ani alternatywnych interfejsów.

Wszystkie dalsze prace realizujemy na istniejącym kodzie CHAOS, w kontrolowanym lokalnym środowisku rzeczywistej gry.

Celem jest przygotowanie działającego modułu produkcyjnego, a nie kolejnego prototypu.

---

### 2. Kamera jako normalny element świata CHAOS

Camera Street View musi zostać w pełni zintegrowany z istniejącymi mechanikami kamer.

Kamera pozostaje zwykłym obiektem świata gry.

Może pojawić się przy sklepie, bankomacie lub innym obiekcie zgodnie z istniejącymi zasadami generowania celów i mechaniką świata.

Gracz może wejść z nią w interakcję, przeprowadzić hakowanie, uzyskać dostęp do jej zasobów albo ją wyłączyć.

**Wyłączenie kamery nadal wpływa na istniejący system incydentów.**

Nie wolno zmieniać ani pomijać dotychczasowych mechanizmów odpowiedzialnych za:

* generowanie i identyfikowanie kamer;
* hakowanie i autoryzację operacji;
* wyłączanie kamer;
* obsługę incydentów i eskalacji;
* ryzyko operacji;
* koszty i nagrody;
* pobieranie plików;
* działanie Super Powers.

Camera Street View jest dodatkową nagrodą wizualną wynikającą z poprawnego wykonania istniejących operacji.

Nie jest osobnym mechanizmem hakowania.

### 3. Kanoniczna ścieżka uzyskania podglądu

Docelowy przebieg operacji:

**Kamera → hakowanie → sukces → pobieranie pliku → zakończenie pobierania → jednorazowy podgląd.**

Po skutecznym schakowaniu kamery system uruchamia dotychczasową operację pobierania pliku.

Podgląd nie może zostać udostępniony przed rzeczywistym zakończeniem tej operacji.

Jeżeli hakowanie zakończy się niepowodzeniem, nie rozpoczynamy pobierania ani nie przyznajemy podglądu.

Jeżeli pobieranie nie zostanie ukończone, podgląd pozostaje niedostępny.

Nie należy tworzyć dodatkowego, sztucznego procesu pobierania wyłącznie na potrzeby Camera Street View.

**Obowiązuje rzeczywisty kontrakt pobierania plików Ghost System.**

### 4. Rzeczywisty czas pobierania i Super Powers

To jeden z najważniejszych wymogów implementacji.

Czas oczekiwania na Camera Street View musi pochodzić z istniejącego mechanizmu pobierania plików.

Nie wolno przypisywać stałego czasu 1800 sekund ani wprowadzać osobnego timera.

Przykłady:

Jeżeli normalne pobieranie danego pliku trwa 30 minut, gracz otrzymuje podgląd po 30 minutach.

Jeżeli trwa 5 minut, podgląd staje się dostępny po 5 minutach.

Jeżeli gracz posiada aktywną Super Power przyspieszającą pobieranie plików, czas oczekiwania na podgląd musi zostać skrócony dokładnie według istniejących reguł.

Nie implementujemy ponownie obliczania modyfikatorów.

Nie tworzymy osobnych zasad przyspieszania dla kamer.

Należy odnaleźć kanoniczne źródło informacji o postępie, efektywnym czasie i zakończeniu pobierania.

Camera Street View korzysta z tego samego wyniku.

Jeżeli istniejący system obsługuje zmiany modyfikatorów podczas operacji, nowy moduł musi respektować jego aktualny stan.

**Backend pozostaje źródłem prawdy o zakończeniu pobierania.**

Samo upłynięcie czasu obliczonego w JavaScript nie może przyznawać dostępu do kamery.

---

### 5. Jednorazowa instancja podglądu

Zmienia się dotychczasowe założenie dotyczące ponownego otwierania okna.

Po prawidłowym zakończeniu pobierania gracz otrzymuje możliwość jednorazowego uruchomienia Camera Street View.

Podgląd otwiera się jako nowa instancja standardowego okna Ghost Systemu, zgodnie z zaakceptowanym prototypem.

**Okno pozostaje aktywne tak długo, aż gracz sam je zamknie.**

Nie stosujemy automatycznego zamykania po określonym czasie oglądania.

Zminimalizowanie okna nie oznacza zakończenia podglądu.

Po świadomym zamknięciu instancji dostęp wynikający z tej konkretnej operacji zostaje bezpowrotnie wykorzystany.

Nie można otworzyć podglądu ponownie z tego samego pobranego pliku ani wcześniejszego wyniku hakowania.

Nie można również obejść tego ograniczenia przez odświeżenie strony, ponowne zalogowanie, przywrócenie okna czy ponowne wywołanie endpointu.

Stan jednorazowego wykorzystania musi być zapisany i weryfikowany po stronie backendu.

Dopuszczalne jest techniczne odzyskanie tej samej aktywnej instancji po chwilowym rozłączeniu, o ile nie została świadomie zamknięta i nadal spełnia obowiązujące zasady sesji oraz autoryzacji.

Odzyskanie aktywnego okna nie może utworzyć nowego podglądu.

Zdarzenia zamknięcia muszą być obsługiwane idempotentnie, bez możliwości przyznania drugiego dostępu przez równoległe żądania.

### 6. Ponowne uzyskanie obrazu

Jeżeli gracz chce ponownie obejrzeć obraz z tej samej kamery, musi:

1. Ponownie przeprowadzić hakowanie.
2. Uzyskać poprawny wynik operacji.
3. Ponownie rozpocząć pobieranie pliku.
4. Odczekać rzeczywisty czas pobierania z uwzględnieniem Super Powers.
5. Otrzymać nową, jednorazową instancję Camera Street View.

Nie wolno ponownie wykorzystywać wcześniejszego uprawnienia do otwarcia okna.

Można natomiast ponownie wykorzystać fotografie znajdujące się w archiwum Camera Visual Network.

**Archiwum zdjęć i prawo do uruchomienia podglądu to dwie niezależne rzeczy.**

Współdzielenie materiałów wizualnych nie oznacza współdzielenia uprawnień graczy.

---

### 7. Nowa charakterystyka każdego podglądu

Każde kolejne poprawne uzyskanie dostępu do kamery generuje nową charakterystykę wizualną.

Zgodnie z zaakceptowanym prototypem pojedyncza instancja korzysta z jednego wybranego zdjęcia i animuje jego kadr.

Zdjęcie może zostać wylosowane z dostępnego zestawu materiałów przypisanych do lokalizacji.

Jeżeli dostępnych jest kilka zdjęć, kolejna instancja może otrzymać inne ujęcie.

Jeżeli dostępne jest tylko jedno zdjęcie albo ponownie wylosowano ten sam materiał, system musi wygenerować nowy wariant ruchu.

Dla każdej nowej instancji określamy:

* wybrane zdjęcie;
* pozycję początkową kadru;
* nowy wektor ruchu;
* punkty kontrolne ścieżki;
* charakterystykę przesuwania;
* czas przejścia i powrotu zgodny z przyjętym modelem animacji.

Wykorzystujemy zaakceptowany mechanizm bardzo powolnego ruchu po łuku Béziera, z płynnym przyspieszaniem, hamowaniem i powrotem.

Nie wracamy do automatycznego przełączania trzech zdjęć w jednej instancji, jeśli nie wynika to z zaakceptowanego prototypu.

Parametry ruchu pozostają stabilne przez czas działania konkretnego podglądu.

Nowe losowanie następuje przy uzyskaniu nowego dostępu wynikającego z kolejnej poprawnej operacji.

Celem jest uzyskanie wrażenia, że kolejne włamanie do tej samej kamery daje nieco inną transmisję.

---

### 8. Integracja z aplikacjami kreatorskimi Ghost System

Należy domknąć również kontrakt aplikacji generowanych przez Ghost System.

Aplikacje przeznaczone do obsługi kamer muszą automatycznie otrzymywać obsługę Camera Street View.

Nie wymagamy ręcznego dodawania tej funkcjonalności.

Nie budujemy nowego odtwarzacza dla każdej aplikacji.

Wszystkie kompatybilne aplikacje korzystają ze wspólnego systemu podglądu, archiwum i autoryzacji.

Należy zweryfikować istniejące kontrakty aplikacji i sposób ich generowania.

Sprawdzić również aplikacje utworzone wcześniej i zapewnić kompatybilność tam, gdzie pozwala na to istniejąca architektura.

Posiadanie aplikacji do obsługi kamer nie daje automatycznie prawa do oglądania dowolnego obrazu.

Obowiązuje pełna ścieżka hakowania i pobierania.

---

### 9. Aktualizacja sprintów 164, 165 i 166

Przeanalizuj aktualne pliki sprintów w repozytorium i dostosuj ich zakres do powyższych ustaleń.

Nie zakładaj, że wcześniejsze dokumenty zawierają aktualne reguły gameplayu.

W szczególności usuń lub zastąp nieaktualne założenia dotyczące:

* prototypowania w odrębnym środowisku;
* ponownego otwierania zamkniętego podglądu;
* stałego czasu pobierania;
* wielokrotnego wykorzystywania tego samego wyniku operacji;
* niezależnego od gameplayu przyznawania dostępu;
* automatycznego przełączania zdjęć sprzecznego z zaakceptowanym prototypem.

Zachowaj wszystkie nadal aktualne wymagania dotyczące bezpieczeństwa, optymalizacji, Mapillary, licencji, atrybucji, administracji i archiwizacji.

Sprint 164 powinien domknąć kontrakty, integrację z rzeczywistym gameplayem, pozyskiwanie fotografii i wspólne archiwum.

Sprint 165 powinien wykorzystać zaakceptowany interfejs, zintegrować go z docelowymi mechanizmami i administracją oraz przygotować kontrolowany rollout.

Zakres Sprintu 166 należy zweryfikować względem rzeczywistych plików repozytorium i dostosować do ustalonego workflow, bez wprowadzania niezatwierdzonych funkcjonalności.

Nie przywracaj odłożonego projektu Ghost Lab Camera Creator.

**Tworzenie kamer przez graczy, przesyłanie własnych fotografii, aplikacja fotograficzna GPS oraz moderacja Vision pozostają poza zakresem tych prac.**

Nie aktywuj `PLAYER_UPLOAD`.

---

### 10. Pierwsza kompletna paczka implementacyjna

Przechodzimy do właściwego kodowania.

Nie kończ pracy na aktualizacji dokumentacji.

Po przeanalizowaniu istniejącego kodu przygotuj pierwszą kompletną, lokalną paczkę implementacyjną Camera Street View.

Pakiet powinien zawierać powiązane elementy potrzebne do wykonania pełnego scenariusza:

**Istniejąca kamera → hakowanie → wynik → kanoniczne pobieranie pliku → Super Powers → jednorazowa aktywacja → Camera Street View → zamknięcie → wykorzystanie dostępu.**

Dołącz potrzebne kontrakty, migracje, adapter źródła fotografii, archiwum, integrację aplikacji kreatorskich, kontrole dostępu oraz testy regresyjne.

Zachowaj istniejące efekty wyłączenia kamery na system incydentów.

Nie uruchamiaj prawdziwego API Mapillary podczas lokalnej implementacji.

Używaj fixtures i lokalnych materiałów testowych.

Adapter powinien być jednak przygotowany do podłączenia rzeczywistego API przez konfigurację i sekrety serwera.

Nie wpisuj tokenów do repozytorium ani kodu frontendu.

### 11. Obowiązkowe testy lokalne

Przygotuj automatyczne testy obejmujące co najmniej następujące przypadki:

* Kamera przy sklepie, bankomacie i innym kompatybilnym obiekcie.
* Poprawne i nieudane hakowanie.
* Pobieranie trwające 5 i 30 minut zgodnie z konfiguracją gameplayu.
* Działanie przyspieszenia przez Super Powers.
* Brak dostępu do podglądu przed ukończeniem pobierania.
* Jedno uruchomienie podglądu na jedną poprawną operację.
* Dowolnie długie pozostawienie otwartego okna bez automatycznego zamknięcia.
* Minimalizacja i odzyskanie tej samej aktywnej instancji.
* Zamknięcie i zablokowanie ponownego otwarcia z tego samego uprawnienia.
* Ponowne hakowanie i pobieranie przy kolejnym dostępie.
* Nowy ruch kadru przy kolejnej instancji, również dla identycznego zdjęcia.
* Brak materiałów lub sygnału — zaakceptowane scenariusze awaryjne.
* Zachowanie incydentów po wyłączeniu kamery.
* Kompatybilność aplikacji generowanych przez Ghost System.
* Równoległe żądania, restart, utrata połączenia i ponowne logowanie.
* Brak duplikowania operacji, naliczeń i uprawnień.

Testy czasu powinny wykorzystywać kontrolowany zegar testowy i prawdziwą logikę obliczeń, bez skracania produkcyjnych czasów operacji.

Nie zastępuj testów gameplayu samym sprawdzeniem endpointów.

### 12. Obowiązujący workflow LOCAL-FIRST

Całość powstaje lokalnie.

Nie wdrażamy na VPS pojedynczych fragmentów kodu tylko po to, żeby sprawdzić każdy kolejny element.

Zadania należy grupować w logiczne, kompletne pakiety.

Jeśli potrzebne są rzeczywiste próbki danych lub kontraktów serwera, należy pobrać je w jednej zaplanowanej sesji diagnostycznej, z zachowaniem zasad ochrony danych i sekretów.

Następnie implementujemy i testujemy całość lokalnie.

Przed wdrożeniem przygotuj:

* kompletny kod i migracje;
* wyniki testów lokalnych;
* raport regresji gameplayu;
* konfigurację docelową;
* listę wymaganych sekretów;
* procedurę wdrożenia;
* procedurę rollbacku;
* raport gotowości pierwszej paczki.

Nie wykonuj pushu ani wdrożenia produkcyjnego w ramach samego przygotowania paczki.

### 13. Następny etap — VPS i prawdziwe API

Po lokalnym zakończeniu implementacji oraz zatwierdzeniu paczki nastąpi osobny etap wdrożeniowy.

W jego ramach:

Wykonamy backup i wdrożymy przygotowany kod na VPS.

Skonfigurujemy sekrety dostawcy i uruchomimy adapter Mapillary.

Sprawdzimy rzeczywiste pozyskiwanie, optymalizację, archiwizowanie i wyświetlanie fotografii.

Zweryfikujemy ponowne wykorzystanie materiałów z archiwum oraz działanie systemu przy limitach i błędach API.

Przeprowadzimy testy pełnego gameplayu z rzeczywistym czasem pobierania i Super Powers.

Produkcyjne udostępnianie zdjęć pozostaje uzależnione od zamknięcia wymaganych kwestii licencyjnych, w szczególności niepotwierdzonego sposobu linkowania do Mapillary i zasad retencji.

Nie traktujemy przygotowania sekretów jako automatycznej zgody na uruchomienie publicznego dostępu.

Wdrożenie, aktywacja pilota i szerszy rollout są oddzielnymi decyzjami operatora.

---

## 14. Ostateczne kryterium ukończenia

Camera Street View jest gotowy do pierwszego wdrożenia, kiedy:

**Normalna kamera CHAOS zachowuje cały dotychczasowy gameplay, a poprawne hakowanie i rzeczywiste pobranie pliku dają graczowi dokładnie jeden podgląd, otwarty do chwili świadomego zamknięcia, po którym ponowne uzyskanie obrazu wymaga nowego hakowania i nowego pobrania.**

Każda kolejna instancja otrzymuje nową charakterystykę ruchu kadru.

Wszystkie kompatybilne aplikacje Ghost System korzystają z jednego mechanizmu.

Moduł nie zmienia istniejących zasad incydentów, kosztów, pobierania ani Super Powers.

Zaakceptowany prototyp wizualny pozostaje nienaruszony.

**Priorytet: kompletna implementacja lokalna, pełna regresja gameplayu i jedna spójna paczka gotowa do wdrożenia na VPS.**
