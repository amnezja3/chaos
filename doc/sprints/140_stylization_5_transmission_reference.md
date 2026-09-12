# 140.stylization.5 — para zapis / film

Status: `REFERENCE ACCEPTED / RECORD RUNTIME IMPLEMENTED / SERVER REVIEW PENDING`.

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
