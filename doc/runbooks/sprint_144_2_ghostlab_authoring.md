# Sprint 144.2 — odbiór wspólnego kreatora GhostLab

Status: implementacja lokalna gotowa, odbiór serwerowy otwarty (25 IX 2026).

Potwierdzenie użytkownika (25 IX 2026): **PASS pierwszego testu** — zmiana
ikony i opisu, zapis draftu i zachowanie wartości po ponownym otwarciu projektu.
Potwierdzenie użytkownika (25 IX 2026): **PASS publikacji i kontroli wpisu
Googleplexu** — Friend Kicker 2 z własną ikoną i opisem; cena katalogowa
3600 HC, komunikat o oczekującym custom runtime. Użytkownik potwierdził
krok aktualizacji istniejącego wpisu bez duplikatu.
Potwierdzenie użytkownika (25 IX 2026): **PASS blokady starego buildu** —
po zmianie opisu i zapisie draftu Publish bez nowego Compile odmawia:
„Publisher: zapisz zmiany i skompiluj aktualna rewizje.”
Kontrola eksportu przekazanego przez użytkownika (25 IX 2026): **PASS** —
projekt `glp_176bb6ef4e4543a298ce2d4e9dc48ff3`, rewizja 4, build 3;
`artifact`, `latest_build` i `published_artifact_id` wskazują build 3,
`source_revision=4`. Branding projektu i snapshotu zgodny: Friend Kicker 2,
ikona 🐍, własny opis. Blueprint zgodny ze snapshotem, walidacja bez błędów.
`suggested_price=null` korzysta z ceny szablonu 3600 HC. Runtime pending zgodny
z zakresem etapu. Historia trzech buildów zachowana.
Test dwóch okien GhostLaba niewykonany ręcznie (aplikacja nie pozwala otworzyć
dwóch instancji); konflikt rewizji ma lokalny test automatyczny PASS.
Potwierdzenie użytkownika (25 IX 2026): **PASS withdraw/republish** — po
wycofaniu i ponownej publikacji wrócił ten sam produkt z własną ikoną i opisem,
bez duplikatu w Googleplexie.
Potwierdzenie użytkownika (25 IX 2026): **PASS niezależności dwóch produktów
Friend Kicker** — osobne nazwy, ikony i opisy po zapisie, Compile i Publish;
publikacja drugiego produktu nie zmieniła pierwszego.
Potwierdzenie użytkownika (25 IX 2026): **PASS usunięcia nieopublikowanego
szkicu** — czerwone potwierdzenie CHAOS, szkic znika z Projects, opublikowane
produkty pozostają bez zmian.
Potwierdzenie użytkownika (25 IX 2026): **PASS Financial Sniffer** — utworzenie
projektu, zapis draftu, Compile i Publish bez błędów.
Potwierdzenie użytkownika (25 IX 2026): **PASS Security Panel Proxy** —
utworzenie projektu, zapis draftu, Compile i Publish bez błędów.
Potwierdzenie użytkownika (25 IX 2026): **PASS wszystkich pięciu szablonów** —
Financial Sniffer, Friend Kicker, Security Panel Proxy, System Log Reader
i Arsenal Cleaner; ścieżka utworzenie → zapis draftu → Compile → Publish.
Potwierdzenie użytkownika (25 IX 2026): **PASS starych projektów admina**.
Odbiór mobile: **FAIL** — boczne menu i siatki zachowały układ desktopowy,
ściskając treść i powodując poziome przewijanie.
Poprawka lokalna: układ zależny od szerokości kontenera GhostLaba (do 760 px),
menu nad treścią, jednokolumnowe karty/formularze/podglądy, zawijane przyciski
i długie identyfikatory. Zaktualizowano wersję CSS w obu powłokach gry.
`git diff --check`: PASS. Przeglądarka narzędziowa niedostępna — brak lokalnego
potwierdzenia wizualnego. Pozostaje ponowny odbiór Projects, Templates i edytora
na telefonie oraz po zwężeniu okna na desktopie; sprawdzić zapis draftu.

## Zmiana

Wspólny edytor zapisuje nazwę, ikonę, opis autora, sugerowaną cenę i dozwoloną
prezentację razem z blueprintem, w jednej rewizji. Ikona korzysta z istniejącego
formatu znaku/emoji; ten etap nie dodaje uploadu PNG. Opis funkcji systemowej
pozostaje oddzielony od opisu autora. Obecne szablony dopuszczają prezentację
`default`; kolejne opcje określa rejestr w kodzie.

Build przechowuje własny snapshot brandingu. Publikacja korzysta z tego
snapshotu i aktualizuje dotychczasowy identyfikator produktu. Eksport `.glab`
zawiera branding projektu oraz artefaktu. Starsze projekty bez nowych pól
korzystają z wartości domyślnych bez automatycznego przepisywania artefaktów.

Sugerowana cena podlega dotychczasowej polityce cenowej: puste pole oznacza
cenę szablonu, a `0` nadal podlega minimum systemowemu. Nie zmieniamy tutaj
ekonomii ani zasad darmowych przycisków z późniejszych sprintów kreatorów.
Publikacja pokazuje ostateczną cenę zwróconą przez backend.

Niezapisane zmiany blokują Compile, Publish i eksport. Każde okno używa
rewizji własnego formularza; zapis ze starego okna nie nadpisuje nowej rewizji.
Preview jest demonstracją bez wykonania funkcji i kosztów.

Runtime pozostaje oczekujący. Instalacja i użycie potomstwa będą odbierane
w 145–146, a lista PvP i panel admina w 144.3.

## Weryfikacja lokalna

- 25 testów Python: registry, publikacja, branding/snapshot, walidacja,
  CAS, izolacja autorów, eksport i ścieżka HTTP bez ciężkiego profilu;
  dodatkowo kontrakt produktu i wymagania Googleplexu.
- `node --check static/js/terminal.js` oraz
  `node tests/js/test_ghostlab_publication.js`: PASS.
- Testy uruchamiane przez `tools/run_isolated_tests.py`, bez inicjalizacji
  aplikacji na bazie roboczej.
- Odbiór wizualny desktop/mobile i istniejących projektów admina pozostaje
  do wykonania na serwerze. Automatyczne testy nie zastępują tego odbioru.

## Wdrożenie

Po dostarczeniu kodu na serwer:

```sh
pm2 startOrRestart ecosystem.web.config.js --update-env
```

Odświeżyć grę przez Ctrl+Shift+R. Bez migracji kont i bez restartu workerów
Ollamy/terytoriów. Zmiana nie aktualizuje automatycznie zainstalowanych wersji.

## Odbiór krok po kroku

1. Otworzyć istniejący Friend Kicker Project lub Syslog. Ustawić własną ikonę,
   opis i nazwę; zapisać draft, zamknąć i ponownie otworzyć edytor.
   Wszystkie wartości mają pozostać. Opis funkcji systemowej nadal jest widoczny.
2. Uruchomić Preview: własna nazwa/ikona/opis i oznaczenie demonstracji;
   brak wykonania funkcji. Compile, Publish, odświeżyć Googleplex:
   własna marka w tym samym wpisie, bez duplikatu, runtime nadal oczekuje.
3. Wyeksportować `.glab`; porównać branding projektu i `branding_snapshot`
   artefaktu. Zmienić opis bez zapisu: Compile/Publish/eksport mają odmówić.
   Po zapisie wymagany jest nowy Compile przed Publish.
4. Otworzyć projekt w dwóch oknach. Zapisać zmianę w pierwszym, następnie
   inną w drugim bez odświeżenia. Drugie ma zgłosić konflikt, nie nadpisać danych.
5. Utworzyć dwa produkty tej samej rodziny z różnymi ikonami i opisami.
   Sprawdzić ich niezależność oraz zachowanie marki po withdraw/republish.
   Usunąć osobny nieopublikowany szkic z czerwonym potwierdzeniem CHAOS.
6. Powtórzyć zapis/compile/publish dla pięciu istniejących szablonów;
   sprawdzić stare projekty admina oraz formularz przy wąskim oknie/mobile.
   Nie migrować ponownie kont. Potwierdzić brak zmian sald i zakupionych wersji.

PASS etapu dopiero po potwierdzeniu odbioru serwerowego przez użytkownika.
