# Sprint 144.2 — odbiór wspólnego kreatora GhostLab

Status: implementacja lokalna gotowa, odbiór serwerowy otwarty (25 IX 2026).

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
