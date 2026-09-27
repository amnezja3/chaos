# Sprint 146.1 — GhostLab: bilety do miejsc świata

Status: **ZAMKNIĘTY — PASS**, 27 IX 2026, na podstawie końcowego potwierdzenia użytkownika dla całego Travel Ticket. Po bazowym 146.
To rozszerzenie, nie sekcja 146.1 w historycznym planie runtime.
Następny: [146.2 — konserwacja systemu](sprint_146_2_ghostlab_system_maintenance.md).

## Odbiór końcowy

Użytkownik potwierdził: „możemy spokojnie oznaczyć pass dla całego travel template,
wszystko działa poprawnie teraz”. Zakres zaakceptowany po poprawkach obejmuje
tworzenie i blueprint, walidację, kompilację, publikację, zakup, przekazanie HC,
podróż, limit ceny 150 HC, ukrycie współrzędnych w ofercie i potwierdzeniu oraz
trzy reakcje kupującego. Blokada oceny własnego biletu przez autora jest prawidłowa.
Odbiór pochodzi od użytkownika; wyniki lokalnych testów pozostają opisane w runbooku.

## Ustalenia wdrożenia 27 IX

- Potwierdzenie użytkownika: **jeden zakup = jedna podróż od razu**. Bilet nie
  jest instalowaną aplikacją, nie tworzy launchera, pliku ani pozycji PvP.
- Na żądanie użytkownika przebudowana jest także ciężka ścieżka istniejących
  biletów systemowych. Obie korzystają z canonical wallet/position i transakcji
  `travel_purchases`, bez odczytu/zapisu profilu. `/api/catalog` również używa
  wyłącznie małych projekcji wymagań, salda i identyfikatorów własności.
- Jeden projekt Travel Ticket opisuje jedno miejsce. Lista projektów autora
  stanowi jego ograniczony katalog; kolejne miejsca dodaje jako kolejne projekty.
  Identyfikator produktu pozostaje stały, build przypina wersję, a hash danych
  miejsca rozdziela bieżące reakcje od historycznych.
- Wprowadzono trzy reakcje z uprawnieniem wynikającym z trwałego receiptu
  zakończonej podróży. Jedna zmienialna reakcja konta na produkt; autor wykluczony.
- Podgląd pinezki ładuje mapę dopiero na kliknięcie. Bez geokodowania i oceny
  zgodności miasta przez API. Admin widzi miejsce i agregaty reakcji.
- Stare trwałe paragony systemowe blokują ponowne obciążenie/przeniesienie
  po wdrożeniu. Nie migrujemy lustrzanych historii z profili ani nie przyznajemy
  na ich podstawie prawa do oceniania.
- [Runbook wdrożenia i wspólna lista testów](../runbooks/sprint_146_1_ghostlab_travel.md).
  Zawiera wyniki lokalnych testów i końcowe potwierdzenie odbioru użytkownika.

## Model przyjęty przez użytkownika

Twórca ustala nazwę, ikonę i opis biletu oraz sam dodaje lokalizację:
współrzędne, deklarowaną miejscowość/kraj i nazwę miejsca. Gracze tworzą własne
katalogi miejsc i publikują bilety w Googleplexie. Kupujący korzysta ze wspólnej
logiki podróży. Szablon może istnieć bez odpowiednika w pro-toolsach.

Jakość biletu oceniają gracze po odbytej podróży przez trzy reakcje:
**zły / zadowolony / bardzo zadowolony**. Widoczne liczby reakcji pomagają kolejnym
klientom zdecydować o zakupie. Negatywne opinie ograniczają zainteresowanie
produktem przez decyzje kupujących, bez automatycznej kary dla twórcy.

Ten model zastępuje zamknięty katalog miejsc i wcześniejszą propozycję
weryfikacji OSM/Nominatim, gwiazdek, komentarzy oraz rozbudowanych reklamacji.
Nie budujemy zewnętrznej weryfikacji deklarowanego miasta/POI ani kolejki
ręcznego zatwierdzania jakości miejsca jako warunku publikacji.

## Kontrakt i ścieżka twórcy

- Najpierw zinwentaryzować istniejący travel_ticket, zakup, transport i zużycie;
  wykorzystać obecne reguły zamiast tworzyć drugi system podróży.
- Kontrakt GLab obejmuje branding, katalog miejsc autora, wersjonowane
  destination_id oraz dozwolone warianty prezentacji. Pojedynczy bilet wskazuje
  jedno miejsce; katalog autora może zawierać wiele miejsc i produktów.
- Autor podaje punkt i widzi pinezkę przed publikacją. Serwer sprawdza wymagane
  pola, skończone liczby, zakres lat/lng i limity długości. Gdy zamiana osi daje
  nadal poprawne zakresy, nie zgadujemy poprawności — autor sprawdza podgląd.
- Nazwa miejscowości i opis są deklaracją autora. UI nie przedstawia ich jako
  zweryfikowanych geograficznie. Mapa może używać dotychczasowego podkładu;
  rezygnacja z geokodowania nie oznacza usunięcia mapy z podglądu.
- Logika pozostaje w kodzie; miejsca są danymi graczy. Admin widzi szablon,
  potomstwo, lokalizacje i podsumowania reakcji w istniejącym modelu zarządzania.
- Zmiana miejsca wymaga nowej wersji. Zakup zapisuje autora, faktyczną cenę,
  wersję oferty i miejsca. Edycja autora nie zmienia celu już zakupionego biletu.
- Cel transportu pochodzi z zakupionej wersji, nie z nowych współrzędnych
  przesłanych przy użyciu. Zachować reguły aresztu i ograniczenia transportu gry.
- Warunki oraz liczba użyć muszą być widoczne przed zakupem. Jeśli nie wynikają
  z istniejącej polityki biletów, uzgodnić je przed aktywacją.
- Zakup wynagradza autora według wspólnej księgi. Nie dodawać opłat za użycie.
  Odmowa transportu nie zużywa biletu; wyłączone miejsce ma czytelny powód odmowy.
- Transport, zużycie i receipt muszą być spójne przy awarii/retry. Zakup
  wykonuje podróż; bilet nie tworzy launchera ani wpisu na liście PvP.

## Trzy reakcje po podróży

- Przy każdym bilecie w Googleplexie pokazać trzy zrozumiałe ikony z etykietami
  i licznikami: zły, zadowolony, bardzo zadowolony. Nowy bilet ma stan „Brak ocen”,
  nie domyślną ocenę pozytywną. Kolor nie jest jedynym nośnikiem znaczenia.
- Wybór reakcji udostępnić po zakończeniu podróży. Sam zakup, kliknięcie użycia,
  anulowanie lub odmowa nie uprawniają do oceny. Uprawnienie potwierdza serwer
  na podstawie trwałego zapisu udanej podróży.
- Przyjąć jedną aktywną reakcję gracza na produkt. Gracz może zmienić reakcję;
  poprzedni głos jest zastępowany, a nie dodawany. Kolejne podróże, zakupy,
  reconnect i ponowienie requestu nie mnożą głosów. Twórca nie ocenia własnego biletu.
- Reakcja wskazuje podróż i wersję, której dotyczy. Zmiana reakcji na ocenę nowej
  wersji wymaga odbytej podróży tą wersją. Historia produktu nie znika przy
  republish; stare oceny nie mogą być przedstawiane jako oceny nowego miejsca.
  Przy zmianie miejsca odróżnić reakcje dotyczące aktualnego miejsca od historii
  produktu, zachowując trzy proste reakcje bez dodatkowej macierzy ocen.
- Brak gwiazdek, komentarzy i reakcji od kont bez podróży. Brak automatycznego
  zwrotu HC, blokady sprzedaży lub ukrytej kary rankingowej za negatywną reakcję.
  Wcześniejsze propozycje funduszu/rezerwy/reklamacji nie są bramką tego sprintu;
  ewentualny osobny system reklamacji wymaga odrębnego ustalenia.

## Dane i wydajność

Obowiązuje [zero-heavy](../plans/creator_ghostlab_zero_heavy_profile_contract.md),
także dla odziedziczonego transportu. Wykryte naruszenia naprawiamy w tym etapie.
Miejsca, bilety, podróże i reakcje przechowywać w wąskich canonical stores,
nie w ciężkim profilu. Paginować katalogi i historię; karta produktu pobiera
agregaty trzech reakcji, nie całą historię klientów. Atomowa zmiana reakcji
i unikalność głosu muszą chronić przed równoczesnymi requestami.
Brak wywołań geokodowania i zależności od dostępności dostawcy OSM.

## PASS

Autor A dodaje własne miejsce, publikuje bilet; B kupuje, podróżuje i ocenia.
Sprawdzić branding, punkt docelowy i rozliczenie HC do autora.

- Trzy reakcje i liczniki są widoczne przed zakupem; wybór dopiero po podróży.
- Odmowa oceny po samym zakupie, nieudanej podróży, z obcego receiptu i przez autora.
- Zmiana reakcji, dwie karty, retry i reconnect nie zwiększają liczby głosujących.
- Ponowny zakup/republish nie resetuje opinii ani nie mnoży głosów.
- Zmiana miejsca po zakupie nie zmienia posiadanego biletu i nie przypisuje
  historycznych reakcji do nowego miejsca bez oznaczenia.
- Negatywne oceny nie tworzą zwrotów, dodatkowych transakcji ani automatycznych blokad.
- Nieprawidłowe współrzędne, areszt, wyłączone miejsce, brak uprawnienia,
  konfiskata, restart/retry: brak podwójnego transportu/zużycia/płatności.
- Desktop/mobile: mapa, karta biletu i reakcje; runbook aktywacji/wyłączenia.

Brak zgodności opisu z rzeczywistością jest przedmiotem oceny podróżujących,
nie automatycznego testu geograficznego ani certyfikacji systemowej.
