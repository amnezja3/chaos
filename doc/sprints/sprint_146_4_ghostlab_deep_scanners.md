# Sprint 146.4 — GhostLab: DeepScanery w menu mapy

Status: **ZAPLANOWANY**, zakres użytkownika, 26 IX 2026.
Po [146.3 — firmware](sprint_146_3_ghostlab_firmware_maintenance.md).
Następny: [147 — kreatory](sprint_147_creator_gameplay_policy.md).

## Cel

Potomek DeepScanera zastępuje prezentację domyślnego skanera z menu pustego
pola mapy. Przykład: „🪮 Czesacz” zamiast „🔎 Skanuj”. Zachowuje istniejącą
logikę wykrywania; twórca personalizuje nazwę, ikonę, animację i komunikaty.
To osobny kontrakt GLab, bez pozycji na liście narzędzi PvP.

**Warunek obowiązkowy: wpływ na menu mapy, animację i komunikaty istnieje
wyłącznie podczas działania otwartego okna aplikacji DeepScanera. Zamknięcie
okna natychmiast usuwa ten wpływ. Jednocześnie może działać tylko jedna aplikacja
modyfikująca DeepScan/menu mapy; uruchomienie drugiej jest blokowane.**

## Pola twórcy

| Pole | Kontrakt |
|---|---|
| Nazwa | Maksymalnie 12 widocznych znaków po przycięciu białych znaków, walidacja klient/serwer zgodna dla Unicode. |
| Ikona | Osobna ikona/emoji według wspólnego brandingu GLab; nie wlicza się do 12 znaków nazwy. |
| Opis | Własny opis produktu w Googleplexie. |
| Animacja | Jedna z systemowej allowlisty: regular, pulse, wave, viewfinder, direct. |
| Dodatkowe retry API | Opcjonalnie +1, +2 lub +3 ponowienia ponad bazową politykę skanu; brak zmiany = 0. |
| Wydłużenie timeoutu | Opcjonalnie do +10 sekund ponad bazowy timeout API skanu; brak zmiany = 0. |
| Komunikat bez wykrycia | Np. „Naładuj baterię” lub „Spróbuj jeszcze raz za chwilę”. |
| Komunikat sukcesu | Np. „Coś jest, znajdź ten przeklęty marker”. Pod nim pozostaje systemowy wynik, np. „Wykryto 16 obiektów”. |
| Komunikat błędu API | Np. „Problemy z siecią, ktoś może zagłuszać sygnał. Bądź czujny”. |

Komunikaty są opcjonalne; puste pole daje aktualny tekst systemowy.
Ustalić krótkie limity długości spójne z istniejącymi toastami. Brak HTML/JS,
własnego CSS, zewnętrznych skryptów lub dowolnych animacji twórcy.

## Podłączenie istniejącego skanu

Wstępnie zidentyfikowane punkty w `templates/map_template.html`:
menu pustego pola buduje dziś sztywne „🔎 Skanuj” i wywołuje `mapAction('scan', ...)`;
efekt obsługują `ensureMapScanOverlay`, `beginMapScanEffect` oraz
`finishMapScanEffectAfterPaint`. Podczas implementacji prześledzić pełną odpowiedź
API i odróżnić sukces, pusty wynik, odmowę i awarię.

- Zastąpić nazwę/ikonę istniejącej pozycji menu, bez dodawania drugiej akcji skanu.
  „Podróżuj”, „Wyczyść skan” i „Pobierz teleport” pozostają istniejącymi akcjami.
- Samo zainstalowanie lub wybranie produktu nie aktywuje jego wpływu.
  Aktywacja następuje po uruchomieniu jego okna, a nie przez trwałe ustawienie
  domyślnego skanera. Przejście do okna mapy nie oznacza zamknięcia DeepScanera.
- Uruchomienie drugiej aplikacji wpływającej na DeepScan/menu mapy jest blokowane
  komunikatem CHAOS wskazującym już działającą aplikację. Bez automatycznej zamiany
  i bez nakładania efektów. Aby użyć innego potomka, najpierw zamknąć obecny.
  Ponowne otwarcie tego samego produktu kieruje do istniejącego okna zamiast
  tworzyć drugą instancję. Blokada jest wspólna dla wszystkich punktów uruchomienia.
- Zamknięcie aktywnego okna przywraca „🔎 Skanuj”, systemowe komunikaty i regular,
  usuwa nakładki/animacje potomka oraz zwalnia blokadę uruchomienia. Synchronizować
  wszystkie otwarte okna mapy, także już widoczne menu. Nowo otwarta mapa pobiera
  stan rzeczywiście działającej aplikacji.
- Gdy aktywny potomek zostanie odinstalowany lub skonfiskowany, wraca domyślny
  skaner. Wycofanie sprzedaży działa zgodnie z polityką wcześniej kupionych narzędzi.
- Zastosować wspólny model publikacji, zakupu, przychodu autora, admina i jawnej
  aktualizacji zainstalowanego artefaktu. Republish nie zmienia sam instalacji.
- Zasięg, źródło pozycji, koszt/cooldown i wykrywalne obiekty pozostają domeną
  obecnego skanu, z uwzględnieniem bonusu firmware z 146.3. Szablon nie podnosi
  mocy i nie gwarantuje wykrycia; nie odblokowuje prywatnych markerów/awatarów.
- Obowiązują areszt, uprawnienia i walidacja serwera. Tekst „Naładuj baterię” jest
  narracją autora, nie dodaje nowego zasobu baterii ani obowiązku jego ładowania.

## Retry i timeout API

Twórca może zwiększyć odporność skanu na przejściowe błędy: ustawić **+1 do +3
dodatkowych retry** i wydłużyć **timeout pojedynczej próby o maksymalnie 10 s**.
Oba parametry są opcjonalne, niezależne i zapisane w artefakcie produktu.

- Podczas implementacji ustalić bazowe retry/timeout istniejącej ścieżki.
  Efektywne wartości = baza systemowa + dozwolony dodatek aktywnego potomka.
  Nie mnożyć ponowień w zagnieżdżonych warstwach klienta i serwera; jeden
  koordynator odpowiada za budżet prób, odstępy i całkowity czas operacji.
- System waliduje zakresy przy kompilacji i użyciu: retry jako liczba całkowita
  0–3, dodatkowy timeout 0–10 s. Brak dowolnych parametrów HTTP od twórcy.
- Ponawiać wyłącznie błędy przejściowe wskazane przez systemową politykę API,
  np. timeout lub dopuszczony błąd serwera. Respektować limity dostawcy i Retry-After.
  Brak retry dla sukcesu z zerem obiektów, aresztu, cooldownu, odmowy uprawnień
  lub niepoprawnych danych wejściowych. Komunikat błędu autora dopiero po
  wyczerpaniu dozwolonych prób albo błędzie niepodlegającym ponowieniu.
- Wszystkie próby należą do jednego logicznego skanu. Zachować idempotencję:
  brak kolejnej opłaty, odnowienia cooldownu, dodatkowego losowania konsekwencji
  lub duplikowania markerów wskutek retry. Jeśli istniejące API tego nie zapewnia,
  przygotować wspólny identyfikator operacji i deduplikację przed aktywacją opcji.
- Obliczyć skończony budżet całej operacji z liczby prób, timeoutów i odstępów.
  Animacja nadal nie opóźnia otrzymanego wyniku; dłuższe oczekiwanie wynika
  wyłącznie z zatwierdzonej polityki API. Nie dopuszczać nieograniczonej pętli.
- Dodatki obowiązują tylko przy otwartym oknie aktywnego DeepScanera. Po jego
  zamknięciu nie rozpoczynać kolejnych retry z jego dodatku; anulować timery
  i lokalne oczekiwanie należące do aplikacji. Zatwierdzony już skan serwerowy
  nie jest cofany i nie wolno uruchamiać nowego skanu w jego zastępstwie.
  Zmiana aplikacji nie resetuje budżetu trwającej operacji.

## Efekty i komunikaty

### Wykonanie pięciu systemowych wzorców

To zadanie implementacyjne sprintu, nie tylko wartości w selektorze autora.
Najpierw zinwentaryzować aktualny efekt skanu; zachować go jako regular i reużyć
jego warstwy/lifecycle, a brakujące cztery warianty wykonać w kodzie.

| Wzorzec | Zakres graficzny |
|---|---|
| regular | Obecna systemowa animacja skanowania; punkt odniesienia i fallback. |
| pulse | Rozchodzące się, wygasające pierścienie od źródła skanu, w rytmie impulsów. |
| wave | Płynna fala/pas światła przechodzący przez obszar skanu, z krótką zanikającą poświatą. |
| viewfinder | Narożniki celownika obejmujące obszar skanu, ruch linii przeszukiwania i krótkie potwierdzenie zakończenia. |
| direct | Wąska wiązka przesuwająca się kierunkowo po obszarze skanu; wyłącznie prezentacja, bez zawężenia wykrywania. |

- Wszystkie warianty w stylu CHAOS, z jednolitą paletą i czytelną mapą pod efektem.
  Nie zmieniają zasięgu ani nie sugerują wykrycia obiektu przed odpowiedzią serwera.
- Źródło/obszar animacji odpowiada rzeczywistemu źródłu/obszarowi obecnego skanu.
  Nakładka nie przechwytuje kliknięć i nie zmienia geometrii ani warstw wyników.
- Wspólny renderer z wyborem pattern_id z allowlisty i wspólnymi operacjami
  start/finish/dispose. Jeden efekt na skan, bez osobnego API dla każdego wzorca.
- Efekt towarzyszy istniejącemu requestowi. Zakończenie odpowiedzi/przerwanie
  steruje wygaszeniem; animacja nie opóźnia wyników ani nie uruchamia kolejnego skanu.
- Ograniczona liczba warstw i jedna kontrolowana pętla animacji; zatrzymywać
  requestAnimationFrame/timery i usuwać warstwy/listenery przy dispose.
  Reduced motion otrzymuje spokojny, statyczny wariant bez intensywnych pulsów.
- Edytor GLab pokazuje podgląd każdego wzorca jako demonstrację: bez requestu
  skanu, kosztu, markerów i zmiany aktywnego skanera gracza. Ta sama implementacja
  wzorca obsługuje podgląd i mapę, z osobnym cyklem życia podglądu.
- Odbiór każdego wzorca osobno na desktop/mobile: start, sukces, brak trafień,
  błąd, zamknięcie aplikacji/mapy, szybkie ponowienie i brak pozostałych warstw.

### Wyniki i komunikaty

- Pięć wariantów renderuje system: regular (dotychczasowy), pulse, wave,
  viewfinder, direct. Reużyć obecny lifecycle nakładki; brakujący wariant
  zaimplementować w kodzie, nie zakładać, że wszystkie pięć już istnieje.
- Sam wzorzec zmienia tylko prezentację. Liczbę prób i czas oczekiwania mogą
  zmienić wyłącznie jawne dodatki retry/timeout opisane powyżej, nie animacja.
  Każdy wariant musi zakończyć się i posprzątać warstwy po sukcesie, błędzie,
  przerwaniu lub zamknięciu mapy. Uwzględnić mobile i reduced motion.
- Sukces z obiektami: nagłówek autora, pod nim systemowa liczba rzeczywiście
  wykrytych obiektów. Twórca nie może podmienić liczby ani dopisać fikcyjnych trafień.
- Poprawny skan bez trafień: tekst autora dla nieudanego wykrycia i systemowy
  wynik „Wykryto 0 obiektów”. Pusty wynik to nie awaria sieci.
- Błąd API/sieci: tekst autora plus właściwa informacja systemowa o nieukończeniu
  skanu. Nie pokazywać sukcesu, zera trafień ani wymyślonego wykrycia zagłuszania.
- Areszt, brak uprawnień i cooldown zachowują własne systemowe komunikaty;
  komunikat autora nie może ukryć rzeczywistej blokady ani mechanizmu kaucji.
- Jeden skan używa spójnego snapshotu aktywnego produktu/wersji. Zmiana skanera
  lub aktualizacja podczas requestu nie miesza animacji i tekstów dwóch produktów.
- Zamknięcie aplikacji w trakcie skanu natychmiast wygasza jej efekt. Spóźniona
  odpowiedź nie przywraca starych animacji/tekstów ani nie przejmuje prezentacji
  nowo uruchomionego potomka. Prawidłowy wynik trwającego skanu można pokazać
  systemowo; zamknięcie okna nie ponawia operacji ani nie cofa jej kosztów.
- Bez aktywnego potomka działa obecny wariant i komunikaty. Liczniki i markery
  wynikają z tej samej odpowiedzi systemowej niezależnie od użytej prezentacji.

## Dane i zero-heavy

Aktywny skaner i wąskie dane prezentacji pochodzą z canonical instalacji/artefaktu.
Aktywność jest stanem działania konkretnego okna w bieżącej sesji, nie trwałą
preferencją profilu. Zamknięcie desktopu, wylogowanie, zmiana sesji lub utrata
instalacji usuwa aktywację i blokadę; reconnect nie zostawia osieroconego efektu.
Nie pobierać pełnego profilu, inventory ani całego katalogu przy otwarciu menu.
Reużyć lekką projekcję i zdarzenia uruchomienia/zamknięcia/aktualizacji/usunięcia.
Nie tworzyć pollingu per marker, niekontrolowanych duplikatów zapytań skanu ani historii w profilu.
Obowiązuje [zero-heavy](../plans/creator_ghostlab_zero_heavy_profile_contract.md);
wykryte naruszenia naprawiamy w tym etapie.

## PASS

- Autor tworzy, waliduje, kompiluje i publikuje; drugi gracz kupuje, instaluje
  i uruchamia okno skanera. Nazwa/ikona w menu odpowiadają aktywnej wersji produktu.
- Instalacja bez otwarcia okna nie zmienia mapy. Otwarcie aktywuje wpływ;
  zamknięcie usuwa go we wszystkich mapach i przywraca domyślny skaner.
- Drugi DeepScaner nie uruchamia się, dopóki pierwszy jest otwarty. Sprawdzić
  wszystkie launchery, szybkie/równoczesne otwieranie oraz brak duplikatu tego
  samego okna. Po zamknięciu pierwszego drugi daje się uruchomić.
- Limit 12 znaków także z polskimi znakami i emoji; brak pustych nazw i HTML/JS.
- Wszystkie pięć animacji: sukces, brak trafień, timeout/błąd i cleanup.
- Retry: 0/+1/+2/+3, sukces po ponowieniu, wyczerpanie prób oraz brak ponawiania
  wyniku pustego i odmów. Timeout: baza oraz +10 s, odrzucenie wartości ponad limit.
  Retry nie powiela kosztów, cooldownu, konsekwencji ani wyników; zamknięcie
  aplikacji zatrzymuje dodatkowe ponowienia i nie odnawia budżetu operacji.
- Teksty autora i systemowa liczba obiektów zgodne z rzeczywistym wynikiem;
  odmowa aresztu/cooldownu pozostaje czytelna.
- Wynik i zasięg identyczne z domyślnym skanem przy tych samych warunkach;
  bonus firmware uwzględniony przez serwer, nie zależy od brandingu.
- Wiele potomków, zmiana aktywnego, aktualizacja, wycofanie publikacji,
  konfiskata/uninstall, reconnect i powrót do domyślnego wariantu.
- Skan w trakcie zmiany produktu, ponowienie i zamknięcie mapy: bez dodatkowego
  kosztu/requestu, osieroconych efektów i mieszania rezultatów.
- Desktop/mobile, brak ciężkiego profilu, poprawny przychód twórcy i widok admina.
