# Sprint 160 — ręczny test pełnego zapytania POI

2026-10-19: operator zgłosił udane probe na VPS: Overpass DE HTTP 200 / 25,31 s
oraz VK HTTP 200 / 15,62 s. To dowody dla małego zapytania, nie pełnego skanowania.

`tools/poi_controlled_scan.py` przygotowuje jeden ręczny test diagnostyczny na
stałym publicznym punkcie Warszawy (52.2319, 21.0067), z promieniem 300 m i
filtrami obecnego skanera. Nie korzysta ze współrzędnych graczy. Generowanie
zapytania pochodzi z POIFetcher; limit wykonania zapytania podniesiono do 25 s.
Odczyt HTTP: 25 s, deadline procesu potomnego: 35 s, wspólny slot: 42 s.

```bash
cd ~/app/chaos
git pull --ff-only
.venv/bin/python tools/poi_controlled_scan.py --db data/poi_cache.sqlite3 --provider overpass-vk
.venv/bin/python tools/poi_controlled_scan.py --db data/poi_cache.sqlite3 --provider overpass-vk --execute
```

Domyślnie dry-run nie wykonuje HTTP ani zapisów. `--execute` oznacza świadome
uruchomienie wyłącznie tego ręcznego testu, zgodnie ze zleceniem operatora.
Wymagany jest aktualny zatwierdzony i udany small_probe. Narzędzie nie rozszerza
trwale zakresów registry, nie włącza dostawcy i nie zatwierdza ruchu gameplay,
wide fetch ani storage. Dotychczasowe ustalenia dotyczące VK pozostają otwarte
przed takim uruchomieniem.

Wynik zawiera tylko status, czas, liczby obiektów i ich typów. POI nie trafiają
do cache/world ani do pliku. Do bazy POI trafiają blokady, stan circuit i obserwacja
`controlled_scan`. Obowiązuje wspólny slot transportu i osobny limit jednego
ręcznego pełnego testu na operatora na 15 minut, bez automatycznych ponowień.
Restart web i zmiany flag nie są potrzebne.

Walidacja lokalna: 3 testy PASS (transport mockowany, bez publicznych zapytań):
dry-run/powyższe ograniczenia; timeout i zwolnienie slotu; HTTP 200 z `remark`
nie jest uznawane za sukces. Wynik z VPS pozostaje do zebrania. To nie jest
odbiór kosztów/tokenów, markerów ani całego cyklu skanowania w gameplayu.

Ważne przed kolejnym krokiem: skaner gry ma nadal domyślnie odczyt HTTP 8 s
(`CHAOS_OVERPASS_TIMEOUT_SECONDS`) i limit zapytania 15 s. Zmiana limitów probe
nie zmieniła tych ustawień. Nie aktywowano teraz ruchu gry.

## Wyniki operatora i kolejna diagnostyka

Pełne zapytanie na VK zakończyło się `http_read_timeout` przy odczycie 25 s.
DE zwrócił HTTP 502 po 0,727 s. Nie stanowi to dowodu blokady IP ani błędnej
składni zapytania. Dotychczas transport pomijał treść odpowiedzi non-200.

Dodano opcjonalny odczyt maksymalnie 2049 bajtów błędu (publikowany fragment
do 2048 bajtów) z timeoutem 2 s ograniczonym wspólnym deadline. Błąd odczytu
treści zachowuje oryginalny status HTTP. Opcja jest domyślnie wyłączona i
włączana tylko przez narzędzie CLI; nie zmienia transportu gameplayu.

Następny pojedynczy pomiar, po upływie limitu 15 minut dla DE:

```bash
.venv/bin/python tools/poi_controlled_scan.py --db data/poi_cache.sqlite3 --provider overpass-de --query simple --execute
```

`simple` wybiera tylko node z tagiem amenity w tym samym promieniu i miejscu.
`full` zachowuje dotychczasowe filtry i nwr. Nie zmieniono timeoutów, wspólnego
slotu, circuit ani limitu częstotliwości; warianty nie obchodzą tego limitu.
Narzędzie wypisuje `query_kind` oraz `diagnostic` dla odpowiedzi non-200.
Pomiary nie są równoczesne: sukces prostego zapytania tylko zawęzi diagnozę,
nie dowiedzie sam w sobie przyczyny wcześniejszego błędu.

Walidacja lokalna: 9 testów secure transport i 4 testy controlled scan PASS,
bez publicznego HTTP. Potwierdzono ograniczenie fragmentu, zachowanie statusu
po timeoutcie treści błędu, pojedynczy POST i wybór prostego zapytania.
