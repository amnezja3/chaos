# BlackNet Signals

BlackNet jest warstwa sygnalow swiata CHAOS. Nie jest sklepem, nie jest drugim
Ghost Exchange i nie jest osobnym komunikatorem. To radar zdarzen, ktory zbiera
slady z istniejacych systemow gry i pokazuje je jako krotkie, przechwycone
sygnaly.

## Jak czytac sygnal

Kazdy sygnal sklada sie z kilku czesci:

* **Kanal** - skad pochodzi sygnal, np. RUCH OPERACYJNY, GHOST MARKET WATCH,
  KONFLIKT TERYTORIALNY albo BLACKNET AUDIO.
* **Tytul** - najkrotszy opis zdarzenia, np. AKTYWNOSC / PERSISTENT SNIFFER.
* **Liczba** - wartosc sygnalu. Moze oznaczac liczbe operacji, obrot HC, cene,
  numer tracka albo sile aktywnosci.
* **Stat** - dodatkowy kontekst, np. target, sektor rynku, liczba plikow albo
  liczba aktywnych operacji.
* **Timer** - waznosc sygnalu. Po wygasnieciu sygnal nie powinien uruchamiac
  akcji.
* **CTA** - akcja na dole sygnalu. To jedyne miejsce, w ktorym sygnal wykonuje
  ruch w systemie.

## Sygnaly mapy

Nie kazdy sygnal mapy jest punktem na mapie.

### Otworz mape

Sygnaly analityczne otwieraja mape bez centrowania:

* `operations_active_count`
* `operations_top_type`
* `contested_area_alert`

Przyklad:

```text
AKTYWNOSC / PERSISTENT SNIFFER
```

To znaczy, ze BlackNet wykryl dominujacy typ operacji. `persistent_sniffer` jest
typem aktywnosci, nie celem. Taki sygnal powinien otworzyc mape i Centrum
Operacji, ale nie przenosic widoku do konkretnego punktu.

### Pokaz target

Sygnaly punktowe maja target albo wspolrzedne:

* `operation_hotspot_activity`
* `target_operation_burst`
* `conflict_target_alert`

Te sygnaly moga ustawic mape na konkretny obiekt, np. sklep, punkt POI albo
target konfliktu.

## Ghost Exchange

Sygnaly rynku prowadza do istniejacego Ghost Exchange:

* `market_sales_7d` otwiera ogolny widok rynku,
* `market_top_sector_7d` otwiera sektor, np. GPS, Sieci albo Dane logowania.

BlackNet nie sprzedaje plikow samodzielnie. Pokazuje tylko, gdzie rynek ma ruch.

## Googleplex

Sygnal Googleplexa otwiera istniejacy katalog Googleplex.

Jesli sygnal jest ogolny, uzywa filtra:

```text
/all
```

To pokazuje pelny katalog. Produkt widoczny w sygnale jest tylko punktem
zaczepienia, ale zakup nadal odbywa sie w Googleplexie.

## Radio

Sygnaly audio prowadza do Ghost Hack Radio.

BlackNet moze wskazac:

* kanal,
* konkretny plik MP3,
* numer tracka.

Radio powinno odtworzyc wskazany track z kanalu BlackNet, a nie zawsze pierwszy
plik z playlisty.

## Cyberner

Sygnaly systemowe prowadza do Cybernera.

Najczestszy cel to kanal:

```text
WORLD
```

BlackNet nie tworzy nowego inboxa. Pelna rozmowa dalej mieszka w Cybernerze.

## Teleport

Teleport jest akcja decyzyjna.

Jesli sygnal ma prawdziwe wspolrzedne, system powinien zapytac:

```text
OK / ANULUJ
```

Po potwierdzeniu pozycja gracza lub motocykla moze zostac ustawiona w okolice
sygnalu. Bez potwierdzenia BlackNet nie powinien zmieniac pozycji.

## Out of Signal

Jesli BlackNet nie ma realnych danych, pokazuje stan oczekiwania zamiast mocka.

```text
OUT OF SIGNAL
```

To oznacza: system czeka na ruch w grze. Najlepszy sposob, zeby pobudzic
BlackNet, to uruchomic operacje, sprzedac dane, wejsc w konflikt, odebrac
komunikat systemowy albo wlaczyc radio.

## Najwazniejsza zasada

BlackNet nie jest zrodlem prawdy.

Zrodlem prawdy pozostaja:

* mapa,
* aktywne operacje,
* konflikty,
* Ghost Exchange,
* Googleplex,
* Ghost Hack Radio,
* Cyberner,
* system messages.

BlackNet tylko przechwytuje i sklada sygnaly z tych systemow.
