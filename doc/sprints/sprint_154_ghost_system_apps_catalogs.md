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
