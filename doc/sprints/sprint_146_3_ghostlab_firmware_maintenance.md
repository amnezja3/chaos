# Sprint 146.3 — GhostLab: konserwacja firmware i domknięcie nowych szablonów

Status: **ZAPLANOWANY — ZAKRES ZAKTUALIZOWANY**, 26 IX 2026. Po [146.2](sprint_146_2_ghostlab_system_maintenance.md).
Następny: [146.4 — DeepScanery](sprint_146_4_ghostlab_deep_scanners.md).

## Cel i zakres

- Ryzykowna aktualizacja firmware własnego systemu gracza. System dostarcza
  wykonawcę, twórca nadaje nazwę, ikonę i opis oraz parametry w granicach kontraktu.
  Brak dowolnych komend, binariów i wykonywalnego kodu gracza; operacja dotyczy gry.
- Twórca ustala procent powodzenia oraz mały przyrost pojemności dysku,
  np. 50 MB lub 100 MB, w systemowych limitach. Sukces daje również niewielki
  trwały przyrost zasięgu skanowania od aktualnej pozycji motocykla.
- Każda udana, odrębnie opłacona próba stopniowo zwiększa parametry gracza.
  To realny zapis gameplayowy, nie pokaz. Wycofanie produktu, jego odinstalowanie,
  restart lub reconnect nie usuwają już zdobytych ulepszeń.
- Porażka daje crash systemu w grze i wymaga restartu; nie przyznaje żadnego bonusu.
  Po cooldownie można ponownie kupić firmware i podjąć nową próbę.
- Zakup daje prawo do jednej próby, zużywane zarówno przy sukcesie, jak i porażce.
  Wersja artefaktu produktu, historia prób i zdobyte modyfikatory to odrębne dane.
  Bezpłatna aktualizacja artefaktu nie odnawia zużytego uprawnienia do próby.
- Przed aktywacją ustalić konkretne granice procentu, dysku, bonus skanu i cooldown.
  50/100 MB to przykłady skali podane przez użytkownika, nie zatwierdzona pełna tabela.
- Zachować kontrolę aresztu, instalacji i dostępności własnego systemu.
  Odmowa przed rozpoczęciem (np. areszt/cooldown) nie zużywa zakupionej próby.
- Domknąć instrukcję dodawania kolejnych szablonów na przykładach biletu,
  czyszczenia, aktualizacji systemu, przywracania zabezpieczeń i firmware,
  wraz z widokiem potomstwa w adminie.

## Efekty i trwałość

- Sukces: atomowo dodać bonus do canonical capacity dysku oraz modyfikatora
  zasięgu skanu. Nie zmieniać zajętości dysku. Raport podaje przyrost i nowy stan;
  FM/dysk oraz mechanizm skanowania korzystają z tych samych danych.
- Zasięg dotyczy skanu gracza od motocykla, nie radaru służb, promienia ich trasy,
  teleportu, automatycznego namierzania ani ogólnego zasięgu wszystkich ataków.
  Przed implementacją zmapować konkretne akcje skanu i ich serwerowe walidatory.
- Porażka: trwały stan wymagający restartu i komunikat CHAOS, zamiast samej animacji.
  Oprzeć działanie na istniejącym mechanizmie restartu systemu gracza, jeśli pasuje.
  Nie wywoływać restartu świata, kasowania plików, cofania zdobytych bonusów,
  dodatkowej utraty HC ani zmiany pozycji bez odrębnego uzgodnienia.
- Backend musi egzekwować stan crash także po reconnectcie. Samo zamknięcie okna
  lub ponowienie requestu nie usuwa wymagania restartu i nie daje nowego losowania.
  Dokończenie restartu nie skraca cooldownu i nie odnawia zużytej próby.
- Wynik losowania zapisać raz wraz z zakupem/uprawnieniem, produktem, artefaktem,
  wersją polityki, szansą, rzutem, efektami i czasem następnej dozwolonej próby.
  UI/show odtwarza zapisany wynik. Techniczna awaria zapisu nie jest porażką
  losowania: transakcja nie może pozostawić zużycia bez wyniku albo połowy bonusów.

## Ekonomia i balans do dopięcia przed aktywacją

- Każda kolejna próba wymaga nowego zakupu; użycie nie nalicza drugiej, ukrytej
  opłaty. Powtórzony request zakupu nie pobiera HC drugi raz. Nowy zakup po
  zużyciu poprzedniego wymaga odrębnego uprawnienia, nie samego wpisu „zainstalowane”.
- Przychód ze sprzedaży trafia do twórcy zgodnie z księgą. Porażka jest zakupionym
  ryzykiem, a nie automatycznym zwrotem ceny.
- Cooldown wspólny dla rodziny firmware na konto; zmiana autora, potomka, nazwy,
  wersji, reinstall lub wcześniejsze kupienie kilku kopii nie pozwalają go ominąć.
  Ustalić czas i stosowanie po sukcesie; cooldown po porażce jest wymaganiem użytkownika.
- Określić dolny/górny próg szansy, dozwolone wartości MB i niewielki bonus skanu.
  Do decyzji pozostaje, czy bonus skanu wybiera twórca w limitach, czy wylicza system.
  Nie pozwalać klientowi zmieniać tych wartości przy użyciu; obowiązuje zakupiony artefakt.
- Oszacować kumulację wielu sukcesów i relację ceny, szansy oraz nagrody. Ewentualny
  limit sumy/diminishing returns wymaga jawnej decyzji; nie wprowadzać go po cichu.
  Przy takim limicie UI musi uprzedzać przed zakupem, gdy bonus nie może już wzrosnąć.

## Zero-heavy i synchronizacja

Wąskie canonical stores: uprawnienia zakupowe, próby firmware, modyfikatory
dysku/skanu oraz stan crash/restart. Brak odczytu lub zapisu pełnego profilu.
Reużyć istniejące źródła storage i skanu; nie tworzyć niezależnych liczników UI.
Wersjonowanie i atomowy commit chronią współbieżne próby/zmiany parametrów;
delta i komunikat wynikają z zapisanego skutku.

## PASS

Potomek zachowuje ikonę/opis autora. Parametry poza limitami nie przechodzą walidacji.
Sukces daje dokładny przyrost pojemności i realnego zasięgu skanu, widoczny także
po reconnectcie, restarcie i odinstalowaniu. Kolejny opłacony sukces kumuluje bonusy.
Porażka nie daje bonusu, zużywa jedną próbę i wymaga restartu. Nowa próba jest możliwa
po cooldownie i nowym zakupie. Retry, dwie karty, drugi produkt tej rodziny,
aktualizacja i reconnect nie powielają skutku ani nie obchodzą ograniczeń.
Sprawdzić skan na granicy starego/nowego zasięgu, ochronę zajętości dysku,
brak wpływu na służby i inne akcje oraz brak zużycia przy odmowie przed startem.
Wymusić awarię zapisu przed commit i utratę odpowiedzi po commit — bez połowicznych
bonusów, ponownego obciążenia, nowego losowania lub obejścia crash/restart.
Regresje sześciu rodzin PvP i trzech nowych etapów; podział launcherów na
PvP/podróż/własny system. Raport realnych skutków oddzielony od pokazów.
Zatwierdzony zakres efektu i balans wymagane przed aktywacją, runbook i odbiór UI.

Małe trwałe rozszerzenia dysku i zasięgu skanu należą teraz do tego sprintu.
Personalizacja domyślnego skanera i jego efekty są zakresem 146.4;
firmware nie odblokowuje automatycznie nowych typów celów.
Obowiązuje [zero-heavy](../plans/creator_ghostlab_zero_heavy_profile_contract.md);
naprawy naruszeń są częścią tego etapu, nie odroczonym długiem.
