# Sprint 154 — Ghost System: aplikacje, narzędzia i katalogi PL/EN

Status: **IMPLEMENTACJA DOMKNIĘTA LOKALNIE — 154.7.0**, 8 X 2026.
Oczekuje wdrożenia i odbioru produkcyjnego. Po produkcyjnym PASS
[153](sprint_153_ghost_system_i18n_foundation.md), przed
[155](sprint_155_ghost_system_content_acceptance.md).

## Aktualny przyrost: 154.7.0

**2833 klucze PL/EN w 13 domenach.** Pozostałe workspace’y, systemowe katalogi,
zakup/instalacja/aktualizacja/użycie, sześć rodzin PvP, serwis, cztery kreatory
wraz ze starszym fallbackiem oraz historyczne instalacje mają wspólną warstwę
prezentacji. Nie zmieniamy ID produktów, opłat, receiptów ani tekstów graczy.

Szczegółowy zakres i ograniczenia testów opisuje
[macierz odbioru 154.7.0](../audits/sprint_154_acceptance.md).
Regresja frontendu: `node tools/check_sprint154.cjs`, **30/30 PASS**.
Końcowy wspólny przebieg backendu: **287/287 PASS** na izolowanych bazach.
Playwright: rzeczywiste renderery na izolowanym pulpicie, PL/EN, mobile,
zmiana języka przy otwartym formularzu/instalatorze, niezmienne payloady i UGC.
Regresje backendu używają izolowanych baz i kanonicznych transakcji.

EN pozostaje testowe do końca 155. Narracje, trwałe zdarzenia, ich historia,
sceny/media i dokumenty systemowe pozostają w wcześniej uzgodnionym 155.
149–152 nadal zamrożone. **154.7.0 lokalnie, bez commita/pushu/wdrożenia.**
Poniższe wpisy są historią przyrostów; ich dawne listy otwartych prac nie
zastępują aktualnej macierzy odbioru.

## Historia: odbiór 154.5.0 i lokalny przyrost 154.6.0

Autor potwierdził wdrożenie `61f8c63`, manifest `154.5.0`, a następnie
**PASS produkcyjny zakresu 154.5.0** i zgodę na dalsze prace. Nie jest to
zamknięcie całego sprintu ani pełna wersja EN.

Lokalnie `154.6.0`: 886 klucze w 10 domenach. Odpowiedzi `/map-action`
i `/api/map/aim-target` otrzymują jawne klucze i parametry komunikatów
wyboru/oznaczenia celu, skanu, błędów pozycji, zasięgu, nieaktualności celu,
ochrony terenu i podróży. Dotychczasowe statusy HTTP, status/error/scan_outcome,
markery, ID i współrzędne zachowane. Polski wynik skanu ma reguły liczby mnogiej.
Frontend korzysta z nowej koperty; niezgodna wersja zachowuje kompatybilny
komunikat. Parametry nazw i autorskie logi skanerów są escapowane.

Testy katalogów, marked-target hot path i skanerów PASS; trzy zestawy JS PASS.
Playwright `map_results_locale.js`: rzeczywiste funkcje wyboru celu i obsługi
wyników z izolowanymi integracjami/API, identyczne żądania PL/EN, nazwy z HTML,
błąd upstream, brak zasięgu, autorski log i deduplikacja. To nie jest pełny
skan świata ani test podróży. Brak pushu/wdrożenia 154.6.0.
Pozostałe wyniki narzędzi, dialogi i warstwy mapy nadal wymagają migracji;
historia trwałych komunikatów pozostaje w 155.

Kolejny przyrost lokalny:

- Radio: PL/EN/ANY, niezależny zapis filtra, bez przeładowania audio przy zmianie
  języka, pusty stan z jawnym ANY, język audycji, metadane kanałów/programów,
  blokada niezgodnych nagrań w kanale PL/EN, diagnostyka panelu administratora.
  Istniejące 34 nagrania zinwentaryzowane bez zgadywania języka z nazwy.
  Autor potwierdził PL dla wszystkich 9 audycji BlackNet Radio; kanał ma PL.
  Pozostałe 25 nagrań muzycznych ma `unknown` i dostępność pod ANY.
- Dev Bug Reporter: formularz, kategorie/ważność, błędy i potwierdzenie PL/EN;
  wartości kategorii, szkic oraz treść zgłoszenia nie zmieniają się z językiem.
- Operation Control: widok operacji, grupy, ryzyko, pliki, historia, puste stany,
  dialogi anulowania i koperty API PL/EN. Anulowanie używa tych samych ID;
  rezygnacja w dialogu nie wysyła żądania. Błąd sieci zwalnia blokadę przycisków.
- Playwright: `radio_locale.js`, `bug_report_locale.js`,
  `operation_control_locale.js` PASS na izolowanym desktopie, z mockami API;
  radio używa atrapy Audio do sprawdzenia niezmienności źródła/czasu. Sprawdzono
  mobile 390 px i brak wyjątków JS. API i reguły operacji testowane osobno.
- Końcowa regresja: 39 testów Python radia/admina/operacji/zgłoszeń/i18n PASS.
  Testy JS runtime języków, menu akcji oraz ścieżki audio Ghost Signal Show PASS.

**Pełny sprint pozostaje otwarty:** Territory Control, Victim Picker,
Ghost Network Suite/Signal Registry/Sender, pozostałe workspace'y,
katalogi produktów i ich pełne ścieżki zakupu/instalacji/użycia/aktualizacji,
pozostałe dialogi i nazwy mapy oraz macierz odbioru całego zakresu.

7 X: przyrost `154.5.0` przygotowany do wdrożenia na prośbę autora.
Końcowa wspólna regresja: 78 testów Python i dziewięć zestawów JS PASS.
[Instrukcja wdrożenia](../runbooks/deploy_154_5.md),
[aktualny rejestr 718 kluczy](../audits/sprint_154_key_register.md).
Nie oznacza to zamknięcia sprintu ani potwierdzenia wdrożenia produkcyjnego.

## Przyrost 7 X — menu mapy, skan i zabezpieczenia

- Pakiet `154.5.0`, domena `map_workspace`: 51 nowych kluczy, 718 łącznie.
  Menu skanu/podróży/czyszczenia/teleportu, etykieta trwającego skanu,
  menu przejętego obiektu i wycofania oznaczenia, 36 nazw zabezpieczeń
  oraz pięć gotowych ustawień PL/EN. Kody ustawień i zabezpieczeń pozostają stałe.
- Odświeżenie stanu zabezpieczeń zachowuje wiązania językowe oraz wiersz
  i jego blokadę busy. Nazwy obiektów z apostrofem lub HTML pozostają tekstem
  i nie psują kliknięć. Skanery autora zachowują własne nazwy i logi.
- PASS: 8 testów i18n/akcji, 28 regresji przejętych obiektów/skanerów oraz
  5 testów kontraktu frontendu (naprawiono ścieżkę odczytu szablonu w izolowanym
  runnerze). Cztery zestawy JS: loader języków, menu akcji, skaner i jego preview.
- Playwright `tests/browser/map_workspace_locale.js`: rzeczywiste funkcje menu
  wyodrębnione z szablonu, izolowane integracje/odpowiedź stanu zabezpieczeń,
  PL/EN, współrzędne i ID kliknięć, odświeżenie, busy, UGC, mobile 390 px.
  Etykieta skanu przełącza język, autorski log pozostaje dosłowny; osobno adapter
  skanera w iframe. Bez wyjątków JS, ostrzeżenie atrapy radia.
- To test rendererów, nie pełnego skanu świata ani wykonania operacji.
  Nadal otwarte: panel oznaczonego celu, wyniki i błędy backendu mapy,
  dialogi porzucenia/podatności, generowane nazwy, pozostałe workspace'y i radio.
  Zmiany lokalne, bez wdrożenia i bez pełnego PASS 154.

## Aktualny stan — backend kreatorów domknięty lokalnie

- Pakiet `154.4.0`: 667 kluczy PL/EN. Walidacje aktualnego API kreatorów
  używają jawnych kodów i parametrów; numer opcji Button Choice pozostaje
  osobnym kontekstem. HTTP i dotychczasowe `reason` zachowane. Nieoczekiwane
  błędy danych otrzymują lokalizowany komunikat ogólny.
- Nowy projekt zapisuje domyślne teksty w języku tworzenia oraz
  `presentation_locale`. Ponowienie tego samego żądania w innym języku
  zwraca istniejący projekt. Publikacja zachowuje teksty autora; stare
  projekty bez informacji o języku mają fallback PL, snapshoty historycznych
  produktów pozostają w dotychczasowej ścieżce.
- 40 testów regresji Python + 3 nowe testy API PASS (43): walidacje,
  idempotencja, migracje, brak ciężkich odczytów profilu, publikacja domyślnych
  treści we wszystkich czterech interfejsach w PL i EN. Trzy zestawy JS PASS.
- Playwright: cztery edytory, zapis/publikacja na atrapach API, mobile 390 px,
  konflikty, szczegółowy błąd z numerem opcji, zmiana języka bez utraty UGC;
  parametry przypominające HTML pozostają tekstem. Oczekiwane odpowiedzi
  HTTP 400/409 w scenariuszach błędów, bez wyjątków JS.
- **Domknięty ten etap kreatorów, nie cały sprint 154.** Reszta mapy,
  workspace'y, katalogi i radio pozostają otwarte. Zmiany lokalne, bez pushu
  i wdrożenia. Poniższe przyrosty dokumentują kolejne wcześniejsze etapy.

## Przyrost 7 X — menu akcji i picker

- Pakiet `154.1.0`: nowa domena `map_actions`, 28 kluczy PL/EN, łącznie 524.
  Wspólne etykiety i ikony 14 akcji mapy; picker pokazuje nazwę zamiast
  technicznego ID. Menu oznaczenia/podróży/zgłoszenia i otoczenie pickera PL/EN.
- Te same akcje, dobór narzędzi, ID produktów, cele i payloady. Nazwy UGC
  pozostają dosłowne. Zmiana języka zachowuje DOM i blokadę zajętego przycisku.
- PASS lokalny: 20 testów Python (katalogi, pokrycie receptur, regresja polityki
  kreatorów), test JS menu dla ośmiu kategorii celów i test loadera języków.
  Playwright: rzeczywisty renderer menu i pickera na izolowanym pulpicie,
  PL/EN, zachowanie węzłów i UGC, stabilne ID kliknięć, stan busy, mobile 390 px.
  Menu używało atrap integracji z mapą; nie jest to odbiór pełnej ścieżki
  skan → wykonanie w świecie gry. Bez nowych błędów JS; ostrzeżenie atrapy radia.
- Nadal otwarte: reszta mapy/skanu, wyniki działań, etykiety rodzin i trybów,
  pozostałe formularze kreatorów, wszystkie dalsze workspace'y,
  radio i katalogi. **Bez pełnego PASS 154; zmiany lokalne, bez publikacji.**

## Przyrost 7 X — przeznaczenie w kreatorach

- Pakiet `154.2.0`: 27 kolejnych kluczy, łącznie 551. Wspólny edytor
  kreatorów używa nazw 14 akcji zgodnych z mapą i pickerem; opisy grup
  obiektów, wybór akcji i reguły zapisu pliku mają wersje PL/EN.
- Zmiana języka aktualizuje etykiety istniejącego formularza bez odtwarzania
  okna, zmiany przeznaczenia, flagi pliku ani wpisanej nazwy użytkownika.
- Playwright: WindowMaker na izolowanym pulpicie, policy/projects jako
  odpowiedzi testowe. PL → EN → PL, obowiązkowy plik ATM, opcjonalny plik auta,
  zachowanie DOM i UGC, mobile 390 px bez poziomego overflow. Brak błędów JS.
  Test nie obejmuje generowania ani publikacji produktu na backendzie.
- 20 testów Python oraz testy JS menu i loadera PASS. Pozostałe pola edycji,
  publikacja i komunikaty API nadal wymagają lokalizacji. Zmiany lokalne.

## Przyrost 7 X — formularze, publikacja i aktualizacje kreatorów

- Pakiet `154.3.0`, nowa domena `creators`: 70 kluczy, łącznie 621.
  Wspólny edytor czterech kreatorów: pola, przyciski, pomoc, podsumowanie
  mechaniki, zapis, publikacja, podgląd, dialog odrzucenia zmian i karta
  aktualizacji PL/EN. Picker i walidacja ikony również PL/EN.
- 15 znanych kodów błędów ma lokalizowane komunikaty. Nieznane szczegółowe
  błędy walidacji nadal pokazują oryginalną odpowiedź API; nie dopasowujemy
  tłumaczeń po treści. Lokalizacja tych walidacji i domyślnych tekstów
  generowanych przez backend pozostaje otwarta.
- 35 testów Python (i18n, akcje, polityka, API kreatorów) PASS; trzy zestawy JS
  PASS. Playwright: wszystkie cztery edytory, zapis/publikacja z atrapą API,
  PL → EN → PL, niezmienione pola UGC i DOM, blokada ceny po publikacji;
  mobile 390 px: konflikt rewizji zachowuje tekst i zwalnia przyciski.
  Osobno sprawdzone: dialog odrzucenia zmian, karta aktualizacji i walidacja
  ikony. Bez wyjątków JS; oczekiwany HTTP 409 w teście konfliktu i ostrzeżenie
  atrapy radia. Test nie publikuje produktów na produkcji.
- Scenariusz powtarzalny: `tests/browser/creator_editor_locale.js`, uruchamiany
  przez Playwright MCP z `tools/sprint_153_browser_fixture.py`.
  Nadal bez pełnego PASS 154, commita, pushu i wdrożenia.

## Cel

Wszystkie dostarczane przez system aplikacje, produkty i działania mają pełne
odpowiedniki PL/EN na wspólnym kontrakcie z 153. Zmiana języka modyfikuje
prezentację istniejącego obiektu, bez tworzenia angielskiej kopii produktu,
nowej ceny, instalacji, uprawnienia czy wersji mechaniki.

## 154.1 — mapa i główne workspace'y

- Mapa: skan, typy obiektów i scen, generowane etykiety NPC, legenda, marker,
  menu, oznaczenie celu, picker narzędzia, podróż, panel celu i podatności.
  Ta sama akcja ma spójny tekst w mapie, kreatorze, pickerze i wykonaniu.
- Territory Control, Operation Control, Victim Picker, Ghost Network Suit,
  Signal Registry: nazwy sekcji, statystyki, statusy, filtry, opis skutków,
  komunikaty błędów i pustych wyników.
- Googleplex, Ghost Exchange, BlackNet, Cyberner, GhostLab: nawigacja, kategorie,
  wyszukiwanie i filtry, ceny, zakup, pobieranie, instalacja, aktualizacja,
  wycofanie, paczki i sprzedaż, formularze i pomoc. Treści wiadomości/narracji
  są domykane w 155; teksty autorskie pozostają bez tłumaczenia.
- AppForge, Term Creator, Window Maker i Button Choice/obecny Button Maker:
  systemowe szablony, przeznaczenia, walidacja i publikacja; nazewnictwo produktu
  sprawdzić w rejestrze. Nie tłumaczyć wpisanych przez gracza etykiet przycisków.

## 154.2 — kompletny katalog systemowy

Zakres 154.1 obejmuje również Dev Bug Reporter (formularz i odpowiedzi,
bez tłumaczenia zgłoszenia autora) oraz Ghost Signal Sender jako ścieżkę
nadawania: warunki, blokady, etapy, recovery i potwierdzenie. Signal Registry
obejmuje też szczegóły, ranking i archiwum. Systemowe UI lokalizujemy w 154;
sceny Ghost Signal Show, narrację, media i historyczne snapshoty domykamy
w 155 według B14/C06 [rejestru](../audits/ghost_system_i18n_inventory.md).

### Radio — kanały PL, EN i ANY

- Dodać wybór języka kanałów `PL`, `EN`, `ANY`. PL pokazuje kanały polskie
  i neutralne językowo; EN angielskie i neutralne; ANY wszystkie dostępne
  kanały, również wielojęzyczne. ANY nie jest automatycznym tłumaczem audio.
- Kanał i audycja mają metadane języka. Oddzielić `neutral` (bez słownej treści)
  od `mixed` (wiele języków); nie oznaczać nieznanego nagrania jako neutralnego.
  Kanał deklarowany PL/EN nie może emitować systemowej narracji w innym języku.
  Kanał mieszany pokazuje język bieżącej audycji; pojawia się pod ANY.
- Język UI ustawia domyślny filtr przy pierwszym użyciu; późniejszy jawny wybór
  gracza ma pierwszeństwo i jest zapamiętany niezależnie od języka interfejsu.
  Zmiana języka UI nie restartuje odtwarzania. Zmiana filtra nie przerywa
  aktualnego utworu; wybór innego kanału następuje jawnie.
- Nazwy i opisy kanałów systemowych mają PL/EN, a tytuły utworów i autorskie
  materiały pozostają oryginalne. Brak kanału w wybranym języku daje czytelny
  pusty stan i możliwość wyboru ANY, bez cichego przełączenia na inny język.
- Panel radia waliduje metadane playlist i kanałów oraz zgodność systemowych
  audycji z deklaracją. Istniejące kanały zinwentaryzować przed nadaniem języka.
  Rejestr pozwala dodać RU/ES po zatwierdzeniu pakietu bez nowych gałęzi UI.
- Odbiór: macierz PL/EN/ANY × kanał PL/EN/neutral/mixed, zapis preferencji,
  brak kanału, zmiana UI w trakcie odtwarzania, etykieta bieżącej audycji.

Rejestr z 153 musi objąć co najmniej:

| Rodzina | Zakres |
| --- | --- |
| Pro Tools PvP | System Log Reader, Security Panel Proxy, Financial Sniffer, Friend Kicker, Arsenal Cleaner, Intruder Kicker; wymagania, opis, ryzyko, wynik, cooldown |
| Bilety i podróż | Systemowe oferty, wybór miasta, zakup, użycie, ograniczenia i wynik podróży |
| Serwis | Konserwacja, firmware, diagnostyka, skanery, naprawy, błędy i recovery |
| Ulepszenia | Pamięć/dysk, mapa, zasięg skanu i pojazdu, parametry i efekty |
| GhostLab | Wszystkie obecnie wdrożone szablony, rodziny, funkcje i teksty widoczne w UI; funkcjonalność v2 z 149–152 pozostaje zamrożona |
| Pozostałe aplikacje wbudowane | Każdy systemowy produkt ujawniony w audycie, również niedostępny na bieżącym poziomie testera |

Nazwy własne produktów mogą pozostać identyczne w PL/EN zgodnie z glosariuszem;
ich opisy i instrukcje muszą być dwujęzyczne. Dostępność produktu nie zwalnia
z tłumaczenia, np. blokada poziomem lub klanem też wymaga pełnego tekstu.

## 154.3 — kontrakt danych i kompatybilność

Istniejące zapowiedzi niedostępnych funkcji GhostLab otrzymują PL/EN z prawdziwym
statusem. Nie realizować odłożonych funkcji z 149–152 w celu zaliczenia lokalizacji.

- Dodać lokalizowane pola prezentacji według jawnego rejestru systemowych
  produktów/szablonów. Nie tłumaczyć zapisanych `app_id`, family, action,
  operation/resource/target type, wersji, nazw komend i kluczy plików.
- Instalacje historyczne i kopie systemowych narzędzi korzystają z tego samego
  słownika prezentacji bez reinstalacji i bez zmian gameplayowej wersji.
  UGC zachowuje niezmienny branding konkretnej zainstalowanej edycji.
- Dla produktu mieszanego rozdzielić opis autorski i systemową specyfikację
  działania. Fork/import nie nadaje automatycznie tekstowi autora statusu
  systemowego; jawnie śledzić nadpisane pola i wersję szablonu.
- Kategorie i akcje wyszukiwane przez stabilne ID oraz aliasy PL/EN; zwykłe
  wyszukiwanie nazw/opisów UGC przeszukuje oryginał, bez wysyłania go do tłumacza.
  Sortowanie językowe nie zmienia trwałej tożsamości ani kursorów paginacji.
- Endpointy zwracają stabilny kod wyniku i klucz z parametrami, z warstwą
  kompatybilności dla wcześniejszego klienta. Nie sterować akcją porównaniem
  przetłumaczonej etykiety. Cache katalogu i odpowiedzi rozróżnia locale,
  gdy odpowiedź zawiera już wyrenderowany tekst.
- Usunąć obejścia oparte na polskich nazwach obiektów, zastępując je metadanymi.
  Historyczne identyfikatory wyprowadzone z nazw wymagają aliasu/mapowania,
  a nie wygenerowania nowego ID po przełączeniu języka.

## Testy i warunki PASS

- Tabela pokrycia: każdy systemowy produkt i action w PL/EN, w tym nazwa,
  opis, wymagania, rezultat, błąd i pomoc. Nie wystarczy tłumaczenie katalogu.
- Playwright PL/EN: skan → oznaczenie → picker → aplikacja → wynik;
  tworzenie pliku → paczka → sprzedaż; zakup → instalacja → użycie → aktualizacja.
- Reprezentant każdej rodziny serwisu, biletu, Pro Tool i kreatora, wraz
  z odmową dostępu/cooldownem. Parametry i skutki identyczne w obu językach.
- Nazwy/teksty gracza porównane przed i po zmianie języka, publikacji, imporcie
  i aktualizacji; oryginał nie może być nadpisany, także gdy przypomina klucz i18n.
- Desktop/mobile: długie etykiety, tooltipy, formularze, menu mapy, klawiatura,
  taskbar i fullscreen. Dostępna pełna nazwa tam, gdzie UI stosuje wielokropek.
- Regresje: pełne profile nie wracają na hot path, zakup i operacja pozostają
  idempotentne, język nie zmienia opłat, efektów ani czasu operacji.

**PASS 154:** kompletne PL/EN wszystkich systemowych interfejsów i katalogów
według rejestru. Każda pozycja ma test lub jawny scenariusz odbioru; brak
przenoszenia pominiętych produktów do nieokreślonego „później”.
