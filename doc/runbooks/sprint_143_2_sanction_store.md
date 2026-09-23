# 143.2 — trwały model sankcji i czas online

22 IX 2026: zaimplementowano wewnętrzny store i testy. Brak aktywacji
aresztu na produkcji; executor nadal odmawia wykonania stopni więziennych.

`response_network/sanctions.py` przechowuje wyrok, snapshot planu (stopień,
kaucja, ograniczenia, wersja), czas w milisekundach, status, wersję i historię.
Unikalny encounter zapewnia idempotencję. Indeks częściowy pozwala na jeden
otwarty wyrok na gracza, również podczas oczekiwania na powrót.

Wszystkie mutacje wymagają transakcji wywołującego `BEGIN IMMEDIATE`.
Nie ma wewnętrznych commitów, odczytów profilu ani endpointu pozwalającego
klientowi podać czas lub stan online. Schema inicjalizowana przy tworzeniu
store; nie inicjalizować store w transakcji efektów.

## Zegar

`observe_presence` czyta po indeksach `account_login_ownership` i
`mail_presence`. Rozlicza czas nowego heartbeatu, nie czas kolejnego pollingu.
Przedział jest zaliczony tylko między próbkami tej samej sesji, oddalonymi
o maksymalnie 90 s (obecne okno kwalifikacji). Brak obecności, logout,
nowa rewizja sesji lub dłuższa przerwa przerywa ciągłość. Duplikaty i próbki
starsze od ostatniej mutacji są bezskuteczne. Nie dopisujemy czasu po ostatnim
heartbeacie. Przy utracie próbek przez dłuższy przestój nie zgadujemy czasu
online — może to wydłużyć realne oczekiwanie, ale nie odbywa wyroku offline.

Po osiągnięciu zera status to `release_pending`, nie `released`.
Dopiero atomowy powrót gracza w 143.4 kończy sankcję. Kaucja po osiągnięciu
zera jest odrzucana, aby nie pobierać jej za już odbyty wyrok.

## Wiadomość i zwolnienie

Jedna rezerwacja wiadomości na sanction_id, wspólna dla wszystkich kanałów
poza World. Powtórka tego samego message_id nie zużywa limitu ponownie.
Rezerwacja musi należeć do transakcji rzeczywistego zapisu wiadomości;
rollback dostarczenia cofa rezerwację. Odbiór i odczyt nie wywołują tej metody.

`release` jest wewnętrznym prymitywem. Przy kaucji wywołujący musi w tej samej
transakcji zweryfikować i obciążyć portfel oraz zapisać powrót. Samo wywołanie
tej metody nie realizuje płatności ani transportu. Nie udostępniać bezpośrednio API.

## Dalsza integracja i odbiór

- 143.3/143.4: spiąć nałożenie z receiptem, kartoteką, transportem i blokadami.
- Podpiąć regularny worker oraz jawny logout do `observe_presence`; nie
  opierać odliczania na otwartej mapie. Ten etap nie zawiera jeszcze tych hooków.
- 143.5: kanał ustala serwer; podpiąć limit do transakcji dostarczenia,
  zachować zawsze odbiór/odczyt kanałów prywatnych.
- Nie wykonywać starych receipts `unsupported` / `not_enabled` z 142.
- Testy modułu sprawdzają restart, reconnect, logout, przerwę, stare próbki,
  powtarzany heartbeat, wyścig dwóch ticków/wysyłań, idempotencję i rollback.
  Testy produkcyjnego wykonania wymagają pozostałych etapów.
