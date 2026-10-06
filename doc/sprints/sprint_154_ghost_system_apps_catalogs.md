# Sprint 154 — Ghost System: aplikacje, narzędzia i katalogi PL/EN

Status: **ZAPLANOWANY**, 6 X 2026. Po PASS
[153](sprint_153_ghost_system_i18n_foundation.md), przed
[155](sprint_155_ghost_system_content_acceptance.md).

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
