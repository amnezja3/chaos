# 143.4 — transport, odliczanie i zwolnienie

Uzupełnienie po 143.5: bramki komunikacji/aplikacji i UI kaucji są już
podłączone; ecosystemy włączają nowe areszty. Aktualne instrukcje wdrożenia
i odbioru są w [143.5](sprint_143_5_detention_capabilities.md).
Poniższy opis flagi dotyczy stanu przy zakończeniu samego 143.4.

Implementacja 22 IX 2026. Nowe wyroki pozostają wyłączone:
`CHAOS_RESPONSE_DETENTION_ENABLED=false` w czterech plikach ecosystem.
Aktywacja w grze dopiero po bramkach komunikacji i aplikacji z 143.5.
Ten etap nie oznacza produkcyjnego PASS ani gotowego interfejsu płacenia kaucji.

## Trwały transport

`response_network/detention.py` nakłada wyrok w transakcji istniejącego
executora konsekwencji. W tej samej transakcji zapisuje losowe więzienie
z zatwierdzonego katalogu, pozycję powrotu, wyrok, kartotekę, pozycję gracza,
prywatną deltę mapy i komunikat. Awaria wycofuje te skutki; trwały rzut
spotkania zostaje do bezpiecznego ponowienia po ponownej kwalifikacji.
Stare wpisy `unsupported` i `not_enabled` nie są wykonywane wstecz.

Transport jest osobnym wewnętrznym writerem `player_positions`. Wymaga
zapisanego wyroku i właściwego statusu; cel pochodzi wyłącznie z zapisanego
więzienia albo pozycji powrotu. Nazwa `source` ani współrzędne żądania
klienta nie omijają bramki ruchu z 143.3.

Mapa odbiera `map.player_forced_position`, przerywa starą animację i kolejkę
trasy oraz centruje widok. Powtórzona lub starsza wersja transportu nie
przerywa nowej trasy. Podczas wyroku nie są tworzone nowe rzuty spotkań;
executor również odmawia dokładania kar.

## Czas online i odzyskiwanie

Pozostały czas pochodzi z serwera, generacji sesji i heartbeatów obecności.
Worker obsługuje ograniczoną partię, rotując po `checked_ms`, przed obsługą
operacji i incydentów. Polling własnego stanu i wylogowanie również próbują
uzgodnić czas. Reconnect ustanawia nową kotwicę; offline nie odlicza.
Przerwy dłuższe niż wiarygodne okno obecności są rozliczane zachowawczo,
bez zaliczania niepotwierdzonego czasu. Restart nie resetuje wyroku.

Zwolnienie, powrót, delta i komunikat są atomowe. Błąd pojedynczego wyroku
wycofuje jego próbę i jest logowany; worker przechodzi do następnych,
a nieudany wyrok pozostaje do ponowienia. Obsługa już zapisanych wyroków
działa również po wyłączeniu flagi nakładania nowych kar.

## Kaucja i API

- `GET /api/response/detention` — stan wyłącznie zalogowanego gracza.
- `GET /api/response/detention/bail-quote?username=robot` — minimalna oferta
  kaucji, bez pozycji powrotu, więzienia i historii gracza.
- `POST /api/response/detention/bail`, JSON `{"sanction_id":"…"}` — płatnik
  wyłącznie z sesji; kwota wyłącznie ze snapshotu wyroku.

Stopnie 6/7/8/9: 5/10/15/20 minut online i odpowiednio
250 000/500 000/750 000/1 000 000 HC kaucji. Płaci aresztowany albo inny
gracz. Obciążenie portfela i powrót są jedną transakcją. Dwie równoczesne
wpłaty nie obciążają dwóch graczy; powtórka nie pobiera ponownie HC.
Wyrok odbyty przed płatnością kończy się bez pobrania kaucji.
Brak środków lub błąd powrotu nie zmienia salda ani osadzenia.
Kartoteka pozostaje po zwolnieniu.

## Walidacja i dalszy odbiór

22 IX 2026: PASS — 46 testów Pythona (transport, sankcje, spotkania,
kwalifikacja i worker) oraz test JS transportu. `git diff --check` bez błędów.

`tests/test_detention_transport.py` obejmuje transakcje, rollback, powrót,
offline/reconnect/restart, wyłączenie flagi, konkurencję płatników, HTTP
i brak nowych rzutów. `tests/js/test_detention_transport.js` sprawdza
obsługę transportu i kolejność wersji na mapie.

Po 143.5: w kontrolowanym teście aktywować flagę w ecosystem web/worker,
nałożyć nowy wyrok, sprawdzić transport i blokadę ruchu, przerwę offline,
powrót po odbyciu oraz osobny wyrok zwolniony kaucją drugiego gracza.
Nie zmieniać starych receiptów ani nie skracać wyroków ręcznym SQL.
