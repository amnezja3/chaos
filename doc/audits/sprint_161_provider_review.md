# 161.2 — przegląd źródeł, 23.10.2026

Przeczytano publiczną dokumentację, bez wywołań danych, kont ani sekretów.
Nie zatwierdzono produkcyjnego dostawcy. Wersja kodu: lokalne adaptery offline v1.

## MapLark

[OpenAPI](https://api.maplark.com/openapi.json): v3 bez cursora; obcięcie przez
limit ujawnia nagłówek X-Has-More; wymagamy też zgodnego X-Returned. Błędy
result_too_large/query_timeout mogą być płatne. v2 jest deprecated.
Pobieramy pełne geometrie bez clipGeometry i zoom. Dane wymagają dowodu
zgodności selekcji i kolejności z Overpass, a nie tylko kompletności HTTP.

[SDK Python](https://github.com/MapLark/osmfeatures-py) i przykłady v2/v3 nie są
w pełni spójne z aktualnym OpenAPI w sprawie podziału/paginacji. Adapter nie
wykonuje automatycznych podziałów obszaru ani ukrytego query_all.

[Schema](https://maplark.com/developer/schema): źródłowe ID typu node/way/relation,
tagi oraz geometrie. Centroid nie jest historycznym bbox center skanera.
Linia i poligon tego samego obiektu wymagają rozstrzygnięcia, nie cichego dedup.

[Pricing](https://maplark.com/pricing): Free 30 000/miesiąc, 10 req/s; rozliczenie
po pracy zapytania, nie stała cena HTTP. Plany płatne dopuszczają nadwyżki.
Nie ustalono gwarantowanego maksimum opłaty jednej operacji; lokalna rezerwacja
nie wymusza zdalnego limitu. Potrzebne potwierdzenie faktycznego konta i limitu
operatora przed próbą. Nie obiecujemy, że mały limit features ogranicza kredyty.

[Terms](https://maplark.com/terms-of-service): wymagane obowiązki OSM/ODbL i
atrybucja; brak automatycznego nadania zgody na storage/background przez ten audyt.

## Geoapify

[Places reference](https://apidocs.geoapify.com/docs/places/): własne kategorie,
offset/limit, maksymalnie 500 wyników strony, deklarowany koszt 1 kredyt/20 miejsc.
Autoryzacja może używać x-api-key. Nie wykazano pełnego profilu tagów CHAOS,
zwłaszcza surveillance, wszystkich ATM ani zgodności selekcji nwr. Krótka strona
nie dowodzi kompletności całego profilu. Geometrię punktową i provider ID
zachowujemy; kategorii nie zamieniamy w zmyślone tagi/ID OSM. Profil pozostaje
UNKNOWN dla pełnego gameplayu. Przywołane 10 km i 5 req/s wymagają potwierdzenia
dla konta/endpointu. Nie zweryfikowano praw osobno dla każdej warstwy świata.

## Macierz wyniku

| Zdolność | MapLark v3 | Geoapify Places |
| --- | --- | --- |
| Oryginalne tagi i tożsamość | Deklaracja dokumentacji, dekoder offline | Raw jeśli obecne; bez rekonstrukcji z kategorii |
| Pełna zgodność skanera | UNKNOWN: selekcja/center/porządek/relacje | UNKNOWN: dodatkowo pokrycie kategorii |
| Drogi/cieki/wody | Kandydat z geometrią; bez odbioru źródła | Nie potwierdzono dla Places |
| Morza/ląd–woda | Nie potwierdzono gotowego produktu | Nie potwierdzono |
| Cena z góry ograniczona | Nieudowodniona | Model zależny od wyniku; potwierdzić konto |
| Live / storage / background w CHAOS | OFF | OFF |

Następny krok wymaga realnych, ograniczonych próbek odpowiedzi z nagłówkami,
potwierdzonego planu oraz budżetu testu. Nie redukować zakresu gry, żeby uzyskać
pozorny PASS. Dostawca może spełniać profil geografii, nie spełniając skanera.
