# Sprint 146.3 — GhostLab: konserwacja firmware i domknięcie nowych szablonów

Status: **PAKIET WDROŻENIOWY PRZYGOTOWANY — ODBIÓR GAMEPLAY PRZED NAMI**, 28 IX 2026. Po [146.2](sprint_146_2_ghostlab_system_maintenance.md).
Następny: [146.4 — DeepScanery](sprint_146_4_ghostlab_deep_scanners.md).

Implementacja: `firmware_update`, zakup jednej próby, trwałe bonusy, 24 h cooldownu
po obu wynikach i crash pulpitu z lokalnym restartem (8 s przygotowania).
Limity dysku stosują istniejące jednostki: 2 TB = 2 097 152 MB.
[Runbook i testy gameplayowe](../runbooks/sprint_146_3_ghostlab_firmware.md).
[Instrukcja rozszerzania szablonów](../plans/ghostlab_template_extension_guide.md).
Odbiór wizualny desktop/mobile po wdrożeniu; nie oznaczać sprintu PASS przed nim.

## Cel i zakres

- Ryzykowna aktualizacja firmware własnego systemu gracza. System dostarcza
  wykonawcę, twórca nadaje nazwę, ikonę i opis oraz parametry w granicach kontraktu.
  Brak dowolnych komend, binariów i wykonywalnego kodu gracza; operacja dotyczy gry.
- Twórca ustala szansę powodzenia 20–80%, przyrost pojemności dysku 50–200 MB
  oraz przyrost zasięgu skanu 10–100 m. Granice są włączne. Sukces daje oba
  trwałe przyrosty; zasięg dotyczy skanowania od aktualnej pozycji motocykla.
- Każda udana, odrębnie opłacona próba stopniowo zwiększa parametry gracza.
  To realny zapis gameplayowy, nie pokaz. Wycofanie produktu, jego odinstalowanie,
  restart lub reconnect nie usuwają już zdobytych ulepszeń.
- Porażka daje crash systemu w grze i wymaga restartu; nie przyznaje żadnego bonusu.
  Po cooldownie można ponownie kupić firmware i podjąć nową próbę.
- Zakup daje prawo do jednej próby, zużywane zarówno przy sukcesie, jak i porażce.
  Wersja artefaktu produktu, historia prób i zdobyte modyfikatory to odrębne dane.
  Bezpłatna aktualizacja artefaktu nie odnawia zużytego uprawnienia do próby.
- Cooldown obowiązuje po każdej zakończonej próbie: sukcesie i porażce,
  minimum 24 godziny. Kumulacja kończy się na 2 TB całkowitej pojemności dysku
  i 30 km całkowitego zasięgu skanu, a nie dopiero sumy bonusów firmware.
- Zachować kontrolę aresztu, instalacji i dostępności własnego systemu.
  Odmowa przed rozpoczęciem (np. areszt/cooldown) nie zużywa zakupionej próby.
- Domknąć instrukcję dodawania kolejnych szablonów na przykładach biletu,
  czyszczenia, aktualizacji systemu, przywracania zabezpieczeń i firmware,
  wraz z widokiem potomstwa w adminie.

## Efekty i trwałość

- Sukces: atomowo dodać bonus do canonical capacity dysku oraz modyfikatora
  zasięgu skanu. Nie zmieniać zajętości dysku. Raport podaje przyrost i nowy stan;
  FM/dysk oraz mechanizm skanowania korzystają z tych samych danych.
- Przy dojściu do limitu przyznać tylko pozostałą część danego bonusu: nie
  przekraczać 2 TB ani 30 km. Osiągnięcie jednego limitu nie blokuje wzrostu
  drugiego parametru. Nie obniżać już istniejących parametrów ponad limitem.
  Przed zakupem pokazać rzeczywisty możliwy przyrost oraz osiągnięte limity.
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

## Ekonomia i balans zatwierdzony 28 IX 2026

- Każda kolejna próba wymaga nowego zakupu; użycie nie nalicza drugiej, ukrytej
  opłaty. Powtórzony request zakupu nie pobiera HC drugi raz. Nowy zakup po
  zużyciu poprzedniego wymaga odrębnego uprawnienia, nie samego wpisu „zainstalowane”.
- Przychód ze sprzedaży trafia do twórcy zgodnie z księgą. Porażka jest zakupionym
  ryzykiem, a nie automatycznym zwrotem ceny.
- Cooldown wspólny dla rodziny firmware na konto; zmiana autora, potomka, nazwy,
  wersji, reinstall lub wcześniejsze kupienie kilku kopii nie pozwalają go ominąć.
  Obowiązuje po sukcesie i porażce, minimum 24 godziny; restart go nie skraca.
- Szansa powodzenia: 20–80%; przyrost dysku: 50–200 MB; przyrost zasięgu: 10–100 m.
  Parametry wybiera twórca, a serwer waliduje granice. Nie pozwalać klientowi
  zmieniać tych wartości przy użyciu; obowiązuje zakupiony artefakt.
- Twarde limity końcowych parametrów: dysk 2 TB, zasięg skanu 30 km.
  Bez wcześniejszego wygaszania bonusów lub dodatkowego limitu liczby sukcesów.
  Przy granicy przyrost jest ograniczony do pozostałego miejsca pod limitem.
  Jednostki MB/TB muszą być spójne z istniejącą reprezentacją pojemności dysku;
  w obliczeniach zasięgu 30 km to 30 000 m.

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
Sprawdzić granice 20/80%, 50/200 MB i 10/100 m oraz odrzucanie wartości poza nimi.
Cooldown minimum 24 h sprawdzić po obu wynikach. Zweryfikować przycięcie przyrostów
przy 2 TB/30 km, dalszy wzrost drugiego parametru po osiągnięciu jednego limitu
oraz brak obniżania parametrów, jeśli wcześniej przekraczały limit.
Wymusić awarię zapisu przed commit i utratę odpowiedzi po commit — bez połowicznych
bonusów, ponownego obciążenia, nowego losowania lub obejścia crash/restart.
Regresje sześciu rodzin PvP i trzech nowych etapów; podział launcherów na
PvP/podróż/własny system. Raport realnych skutków oddzielony od pokazów.
Zakres efektu i balans zatwierdzone; przed aktywacją wymagane runbook i odbiór UI.

Małe trwałe rozszerzenia dysku i zasięgu skanu należą teraz do tego sprintu.
Personalizacja domyślnego skanera i jego efekty są zakresem 146.4;
firmware nie odblokowuje automatycznie nowych typów celów.
Obowiązuje [zero-heavy](../plans/creator_ghostlab_zero_heavy_profile_contract.md);
naprawy naruszeń są częścią tego etapu, nie odroczonym długiem.
