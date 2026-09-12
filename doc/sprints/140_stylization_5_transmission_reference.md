# 140.stylization.5 — para zapis / film

Status: `REFERENCE ACCEPTED / RECORD RUNTIME IMPLEMENTED / SERVER REVIEW PENDING`.

Zapis autor potwierdził jako gotowy. Kolejna para dotyczy filmu:
[desktop / portrait — rekonstrukcja](../../static/references/ghostsignal/transmission-video-pair.html).
Adres: `/static/references/ghostsignal/transmission-video-pair.html?v=transmission-ref-8`.
Otwiera się bezpośrednio w stanie filmu. To samo tło archiwum, tytuł
REKONSTRUKCJA TRANSMISJI nad centralną ramką, zachowane boczne logi
i dane pod obrazem na portrait. Pole 3:2 jest ograniczone do 720×480
oraz dostępnej wysokości kadru. Przyciski nad parą pozwalają wrócić
do zapisu lub obejrzeć przejście. Film w makiecie jest wyciszony.
Zmiany layoutu filmu są wyłącznie w CSS referencji; oczekują akceptacji.
Korekta v6: desktop zachowuje lewy nagłówek i skalę typografii zapisu.
Korekta v7 zastępuje margines v6: na portrait film ma po 6vw z obu stron,
wyrównany do tytułu. Warstwa filmu jest nad nagłówkiem i może go przykrywać,
zgodnie z decyzją autora.

Korekta v8: portrait zaakceptowany przez autora, pozostaje bez zmian.
Desktop ma ramkę szerszą o 30% (limit 744 → 967,2 px) i pole 2:1.
Obraz wypełnia pole przez centralne kadrowanie `object-fit:cover`, bez
deformowania proporcji źródła 720×480. Ograniczenie dostępnej wysokości
nadal obowiązuje. Desktop v8 oczekuje oceny autora.
Poniższe 3 px dokumentuje wcześniejszy wariant v6.
Na portrait obraz ma po 3 px marginesu od viewport, bez wewnętrznego
paddingu ramki. Decyzja autora zastępuje na portrait wcześniejszy limit
szerokości 720 px; proporcje 3:2 pozostają, bitmapa filmu nie jest zmieniana.

Autor zaakceptował parę słowem „idealnie” i zlecił wdrożenie zapisu.
`transmission_quiet` (420–425 s) korzysta już z zaakceptowanego układu.
Wspólny CSS: `static/css/ghost_signal_archive.css`. Film i dalsze sceny
pozostają w dotychczasowym rendererze. [Wdrożenie i odbiór](../runbooks/deploy_140_stylization_5_archive.md).

[Para desktop 1920×1080 i portrait 1080×1920](../../static/references/ghostsignal/transmission-pair.html).
Po push/pull: `/static/references/ghostsignal/transmission-pair.html?v=transmission-ref-3`.
Przyciski nad parą wybierają zapis, film lub przejście po pięciu sekundach.

Punkty odniesienia autora: `doc/visual/signal_show_14_.png` i
`doc/visual/signal_show_video_.png`. Szkice wyznaczają centralny motyw
archiwum, boczne logi i ramkę filmu; nie są używane jako gotowy ekran.
Zachowano przygaszoną paletę, typografię, wspólne OFS i glitch mapy.
Motyw archiwum pochodzi z dostarczonego przez autora
`static/images/ghostnetwork/signal_sends/write_signal_scena_bg.png`.
Przygaszona saturacja i tonalna nakładka dopasowują go do oprawy show.
Przy wejściu filmu tło ciemnieje; nie dublujemy pierścieni i paneli z bitmapy.
Wariant 3 dodaje miękką łunę na źródle światła (835,357 w obrazie 1678×937).
SVG używa tego samego centralnego kadrowania cover co tło (`xMidYMid slice`),
więc pozycja pozostaje dopasowana również na portrait. Puls 3,6 s zmienia
zasięg i jasność bez przesuwania środka. Przy filmie łuna gaśnie;
reduced motion pozostawia słabe, statyczne światło.

Desktop: boczne logi i parametry, centralne pole filmu. Portrait:
nagłówek, obraz, dane pod obrazem. Film zachowuje 3:2 i maksymalnie
720×480, bez kontrolek, fullscreen, PiP i interakcji. Parametry obrazu
pochodzą z istniejącego pliku; brak fikcyjnych 8K/2,4 GB i statusów sukcesu.

Podgląd jest wyciszony. Nie zmienia istniejącego miksera, audio filmu
ani zatwierdzonych fade 0,5 s. Przejście obrazu trwa 0,65 s;
reduced motion pomija animację przejścia. Oba iframe odtwarzają lokalną
makietę; nie jest to pomiar synchronizacji klientów produkcyjnych.

Do odbioru: hierarchia napisów, wielkość pola filmu, czytelność danych
na portrait, centralny motyw archiwum i przejście do filmu. Sprawdzono
składnię JS i ścieżki zasobów. Odbiór wizualny w przeglądarce otwarty.
Runtime pozostaje bez zmian; trigger odłożony.
