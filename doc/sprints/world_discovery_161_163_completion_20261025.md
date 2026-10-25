# 161–163 — zakres uruchomienia mechanizmu, 25.10.2026

Aktualna dyspozycja operatora: zakończyć mechanizm zbierania i przygotowania
geografii. Konsumpcja warstw przez gameplay będzie osobnym przyszłym zakresem.
Praca etapami: kod → wdrożenie → uruchomienie → zbiorcze testy → kolejne
aktywacje. Ciągła kontrola kosztów i obserwacja operacyjna nie czekają na sprint.
Ten dokument koryguje kolejność i kryteria odbioru wcześniejszych planów,
nie deklaruje zakończenia brakujących integracji ani aktywacji na produkcji.

## Co faktycznie istnieje

Przejrzano moduły routing/scan_router/geoapify/discovery_worker/discovery_queue,
konfigurację web, fixtures oraz lokalne instance/provider-captures.
Nie jest to nowa inspekcja VPS ani aktualne badanie dostępności publicznych API.

| Obszar | Mamy | Konkretny brak |
| --- | --- | --- |
| MapLark POI | Skaner live, OSM ID/tagi, koszt/rezerwacje/cache, odbiór dwóch kont | Podłączenie do aktywnej wspólnej hierarchii zamiast osobnej ścieżki |
| MapLark geografia | Worker obserwacji roads/waterways/inland_water/coastline, permit sektor/warstwa, kolejka, storage | Worker jest obecnie zatrzymany; regularny ograniczony zbiór wymaga konfiguracji zakresu i retencji |
| Drogi | Prawdziwy bbox 76 surowych/75 wybranych, testy i pilot lokalnego odczytu | Nie jest to dowód globalnej kompletności dostawcy; nie blokuje zbierania obserwacji |
| Wody | Ciek przekraczający bbox, cztery poligony, jezioro z dwoma otworami, restore PASS | W sprawdzonych lokalnych capture brak rzeczywistego MultiPolygon; obsługa tego typu jest przetestowana syntetycznie |
| Overpass | Istniejący skaner, transport, circuit, registry, gałąź wspólnego routera live | capability blokuje warstwy poza POI, worker nie pobiera z Overpass geometrii. To brak integracji, nie tylko niestabilność sieci |
| Geoapify | Adapter i normalizacja Places, OSM ID/tagi w próbie commercial 63 Point, paginacja, wspólna księga | Kod służy diagnostyce. capability zawsze odrzuca Geoapify POI jako unverified. Brak kolektora obserwacji i dopuszczonego profilu fallback dla skanera |
| Ląd–morze | Kontrakt wersjonowanego regionalnego produktu, walidacja topologii/dependencies, storage/read i testy syntetyczne | W lokalnych capture nie ma rzeczywistego produktu ani podłączonego źródła. Nie wyprowadzać oceanu z braku danych |
| Regiony | Siatka 0.01°, anonimowy popyt, permit do 10 komórek, osobne warstwy i budżety | Worker używa obecnie radius 300 m od środka komórki, nie pobiera całego bbox; ta różnica musi być jawna i wersjonowana |
| Hierarchia | Kolejność per warstwa/live/background, rewizje, historia, rollback, bounded fallback Overpass/MapLark | Produkcyjna flaga routing OFF; brak wykonania Geoapify i geografii Overpass, worker tylko MapLark |
| Koszty i obserwacja | Atomowe budżety, rezerwacje, metryki live, zdrowie źródeł i panel | Stała procedura operacyjna/raportowanie niezależne od odbiorów; nie udawać, że osobny proces monitorujący już działa |

Geoapify: 4 nierozstrzygnięte operacje/20 zarezerwowanych kredytów to stan
księgi znany z ostatniego raportu, nie dowód awarii adaptera ani braku danych.
Nie resetować ich. Nowy profil musi mieć jawny budżet i zachować tę historię.
Nie szukać nowych kluczy u operatora, jeżeli istnieją w konfiguracji procesu;
sprawdzać wyłącznie obecność referencji, nigdy nie wypisywać wartości sekretów.

## Dwa różne zastosowania danych

1. **Zbiór obserwacji:** poprawna geometria i identyfikacja, pochodzenie,
   zakres zapytania, czas, kompletność odpowiedzi i ograniczenia. Można zapisać
   UNKNOWN/PARTIAL bez twierdzenia, że poznano cały region. Brak wersji całego
   datasetu albo brak rzeczywistej próbki jednego typu nie blokuje wszystkich
   innych typów i warstw. Obserwacja Point z Geoapify nie staje się poligonem.
2. **Odpowiedź na skan gry lub kompletne regionalne coverage:** wymaga zgodności
   danego profilu i odpowiedniego dowodu. Nie wolno zastąpić pełnego skanu
   wynikiem commercial ani wyczyścić istniejących markerów na podstawie
   niepełnej alternatywy. Połączenie obu zastosowań nie znosi tych różnic.

Użycie dróg/wód/mórz w mechanikach gry oraz globalna kwalifikacja wszystkich
regionów nie są warunkiem zamknięcia mechanizmu kolekcji 161–163.
Rzeczywisty MultiPolygon pozostaje luką próbki dostawcy, a nie blokadą zbioru
zweryfikowanych Polygon/LineString. Weryfikację takiej próbki wykonać, gdy
pojawi się w rzeczywistym zbiorze, bez zapytań w pętli wyłącznie po PASS.

## Wspólny porządek źródeł

- Najpierw odpowiednie dane lokalne; cache i magazyn nie są dostawcą HTTP.
- Dla obsługiwanego profilu: dopuszczony, dostępny Overpass → MapLark →
  Geoapify. To cel konfiguracji, nie twierdzenie o obecnej konfiguracji VPS.
- Overpass nie zużywa płatnych kredytów API, ale podlega limitom operatora,
  ograniczeniom serwera, circuit i wspólnemu deadline. Niedostępnego źródła
  nie testować od nowa przy każdej próbie; automatyczny powrót wymaga jawnej,
  ograniczonej polityki prób po cooldownie, nie ręcznego sprintu.
- Zdolności per profil/warstwa decydują, kto może wziąć udział w łańcuchu.
  Geoapify Places nie jest źródłem pełnych dróg ani mórz. Brak takiej zdolności
  oznacza pominięcie, nie próbę wysłania nieobsługiwanego zapytania.
- Wspólny deadline i limit wywołań; fallback po błędzie dostępności lub
  braku dopuszczalnej odpowiedzi. Brak niejawnego łączenia sprzecznych źródeł,
  kasowania niepewnych kosztów ani odnawiania czasu na każdym adapterze.
- Źródło użyte do zbioru i źródło użyte do gameplay mają odrębny status.
  Trzeba podłączyć Geoapify do kolekcji obsługiwanego POI; dopuszczenie go do
  pełnego skanera wymaga osobnego profilu, nie zmiany flagi unverified w ciemno.

## Jeden pakiet kodowania

1. Uporządkować kontrakt zbioru: sektor zapotrzebowania, faktyczny envelope
   zapytania, warstwa/profil, provider i rewizja, czas źródłowy/pozyskania,
   observation vs reusable coverage. Reuse istniejących WorldObject,
   ProviderBatch, Registry, Routing i magazynu v2; bez drugiego repozytorium.
2. Dokończyć integrację wykonawców: regionalny zbiór MapLark, obsługiwane
   geometrie Overpass, obserwacje POI Geoapify. Nie używać tych punktów jako
   zamiennika pełnych geometrii. Wspólne sloty, priorytet gracza, koszty,
   wersjonowane klucze zadań i kontrola wycofania konfiguracji.
3. Regiony dopuszczać konfiguracją dla wybranego dostawcy/profilu, z ograniczonym
   obszarem, czasem, liczbą zadań i budżetem. Sam popyt nie stanowi zgody na
   płatne pobranie. Zbiór wynika z popytu, bez rekurencyjnego odkrywania planety.
4. Oddzielić retencję zebranej geometrii od świeżości wyniku skanera. Obecne
   300/1800 s nie są polityką trwałego archiwum świata. Najpierw sprawdzić
   obowiązujące storage approvals/konfigurację, potem jawnie ustalić okres
   i ograniczenie pojemności; bez deklaracji wieczystego zapisu.
5. Złożyć odbiór i rollback w jeden pakiet. Używać istniejących migracji,
   ecosystem.web.config.js oraz osobnego ecosystemu workera; flagi widoczne
   w konfiguracji, nie wyłącznie w ręcznym env jednej powłoki.

Nie czekać na uruchomienie konsumentów geometrii w grze. Nie dokładać nowych
funkcji kamer, oceanicznej rekonstrukcji z coastline ani przebudowy Identity.

## Wdrożenie, uruchomienie i zbiorcze testy

1. Jeden push/pull, backup, kontrola migracji i konfiguracji, pakiet testów
   lokalnych/izolowanych na VPS. Obecny gameplay ma już PASS na dwóch kontach.
2. Włączyć wspólną hierarchię tylko dla gotowych profili; sprawdzić symulowane
   odmowy i fallback bez wielokrotnego sondowania publicznych API.
3. Uruchomić ograniczony zbiór w uzgodnionych sektorach. Łącznie odebrać:
   pobranie → zapis obserwacji → odczyt administracyjny → restart → zachowanie
   stanu → stop/rollback. Odczyt administracyjny nie wymaga aktywacji geometrii
   w gameplay ani fałszywego COMPLETE całego regionu.
4. Zweryfikować wspólny koszt, brak duplikatów i pierwszeństwo graczy;
   porównać kolejkę/metryki przed i po. Jeden krótki test gry po zmianie runtime.
5. Kolejne elementy aktywować w ramach tego samego planu, gdy ich warunki są
   spełnione. Kontrolny test pośredni tylko gdy jego wynik blokuje dalszy kod.

## Ciągłe utrzymanie i późniejszy polish

Budżet musi być egzekwowany w ścieżce każdego requestu, także gdy monitor
nie działa. Osobny ciągły proces operacyjny obserwuje zużycie, kolejkę, błędy,
stan magazynu i aktualność źródeł; odczyt panelu/raportu nie wykonuje nowych
płatnych zapytań. Dzienny reset nie usuwa nierozstrzygniętych kosztów.
Tych działań nie zamykamy razem ze sprintem i nie powtarzamy jako bramki
przy każdym commicie. Aktywne probe mają oddzielne limity i uzasadnienie.

Polish po uruchomieniu: czytelny panel „Skaner / Zbieranie świata / Dane /
Źródła i fallback / Koszty / Stan”, objaśnienia pól, jednoznaczny stan ON/OFF,
powód pominięcia źródła i odłożenia zadania, PL/EN i mobile. W bieżącym
pakiecie poprawiać tylko niezbędną czytelność kontroli operacyjnej.

## Warunek zamknięcia mechanizmu

Kod, wdrożenie i odbiór działającego zbioru z podłączonymi obsługiwanymi
profilami, trwałym zapisem zgodnym z ustaloną retencją, hierarchią/fallbackiem,
kosztami i zatrzymaniem. Udokumentowane nieobsługiwane warstwy pozostają
jawne; nie deklarujemy działających mórz bez źródła. Nie wymagamy mechanik
gry korzystających z geografii ani wszystkich możliwych regionów świata.

Do ustalenia z istniejących danych/konfiguracji przed pytaniem do operatora:
storage/background scopes i retencja źródeł, dostępne regionalne produkty,
obecność klucza Geoapify, zapisane profile/kolejność i aktualny limit konta.
Jeżeli konkretnej informacji zabraknie również tam, zebrać ją w jedną listę
decyzji przed uruchomieniem; nie deklarować jej na podstawie przypuszczenia.
