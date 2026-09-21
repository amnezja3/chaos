# 143.1 — wspólna tabela i kontrakt aresztu

Status 21 IX 2026: reguły 143.1 zatwierdzone i zapisane w konfiguracji; areszt i kaucja nie są jeszcze aktywne.

## Już obowiązujące zasady

Reuse: `config.py:RESPONSE_CONSEQUENCE_TABLE`, `plan_consequence`,
`CriminalRecordStore.prepare/record_executed` i `CanonicalConsequenceExecutor`.
Nie tworzymy drugiej kartoteki ani osobnego losowania dla aresztu.
L2/L3/L4/L5 startują od 1/3/5/6; każda wykonana kara dodaje jeden stopień,
limit 9. Stopnie 6–9: 5/10/15/20 minut online, pauza offline, kontynuacja
pozostałego czasu po powrocie. Licznik lifetime, bez resetu/decay.
Rzut 80/30 raz na gracza i incydent, niezależnie od surowości.

Kamery i aktywne części/Super Powers są już wejściem do operation_risk_meter
(camera_modifier i ability_heat_modifier), potem canonical incident heat/level.
Nie dodawać ponownie ich wpływu przy wymierzaniu stopnia bez osobnej decyzji
balansowej. Sama liczba inicjacji incydentów również nie jest zatwierdzonym
dodatkowym mnożnikiem: obowiązuje licznik wykonanych kar. Zachować rozróżnienie
tych danych w historii i dokumentacji.

Aktualny initializer generuje L1–L4. Obsługa L5 w tabeli nie oznacza
automatycznego uruchomienia generowania L5 ani zmiany progów heat.
Dziesięć więzień w prison_catalog.py jest katalogiem, bez wykonania transportu.

## Zatwierdzone reguły autora — konfiguracja consequences-v2

1. Ograniczenia wszystkich aresztów: ruch i teleporty zablokowane.
   World: stopień 6 odczyt i pisanie, 7 tylko odczyt, 8–9 zablokowany.
   Stopień 9 pozostawia Web Dragon/radio oraz wyjątek komunikacji opisany poniżej,
   z obsługą sesji i komunikatów systemowych.
2. Losowy wybór więzienia, utrwalony dla wyroku; po zwolnieniu powrót do
   zapisanej pozycji sprzed zatrzymania.
3. Brak nowych losowań/kar podczas trwającego aresztu; po zwolnieniu zwykła
   kwalifikacja. Dotychczasowy wynik tego samego incydentu nigdy nie jest resetowany.

Wszystkie kanały poza World traktujemy jako prywatne, w tym klanowe i grupowe.
Łącznie można wysłać jedną wiadomość do dowolnego z nich na cały wyrok,
nie po jednej na kanał lub odbiorcę. Reconnect i restart nie odnawiają limitu.
Odbiór i czytanie tych kanałów są zawsze dostępne na wszystkich stopniach,
także po wykorzystaniu wysłania oraz mimo ograniczenia aplikacji na stopniu 9.
World ma osobną regułę stopnia i nie zużywa limitu prywatnego.
To ograniczenie aresztu nie daje dostępu do cudzych rozmów lub klanów.
Konfiguracja nie uruchamia jeszcze tego mechanizmu.

| Stopień | Czas online | Kaucja HC |
|---|---|---|
| 6 | 5 minut | 250 000 |
| 7 | 10 minut | 500 000 |
| 8 | 15 minut | 750 000 |
| 9 | 20 minut | 1 000 000 |

Kaucję może zapłacić aresztowany lub inny gracz. Zapłata kończy bieżący
areszt i uruchamia normalny powrót; nie kasuje kartoteki. Dostęp do kaucji
pozostaje dostępny na każdym stopniu. Implementacja musi atomowo powiązać
obciążenie płatnika ze zwolnieniem, aby retry lub dwóch płatników nie
pobrało opłaty ponownie. Zwolnienie po upływie czasu nie może pobrać kaucji.

## Granice implementacji kolejnych etapów

143.2: mały store sankcji i serwerowe rozliczenie obecności, wspólne conn
z efektem/receiptem/kartoteką. Nie wystarczy obecny ostatni heartbeat, aby
po długiej przerwie udowodnić ciągłą obecność; potrzebne rozliczanie odcinków,
jawny logout/timeout, ochrona przed podwójnym tickiem i wieloma kartami.

143.3: bramka przy canonical zapisie pozycji i przed wydaniem biletu/HC.
Punkty wejścia wymagające pełnej inwentaryzacji: normalizacja pozycji
`normalize_profile_position_update`, BlackNet CTA teleport i bezpośredni
zapis pozycji ofiary przez narzędzia. Normalizacja obecnie łapie wyjątki
store i zwraca legacy pozycję; odmowa sankcji nie może trafić w taki fallback.
To uwaga do dalszego audytu writerów, nie kompletna lista zabezpieczonych dróg.

143.4/143.5: transport/powrót i bramki aplikacji, atomowy zapis pozycji,
wyroku i outbox. Ukończony transport z nadanym wyrokiem jest skutkiem
naliczenia kary; nie czekać z kartoteką do końca odsiadki. Zwolnienie nie
jest nową karą. Kill switch nałożenia nie może blokować zwolnienia.
Implementacja nie może wykonywać starych unsupported/not_enabled z 142.

Reguły zapisano w tej samej wersjonowanej konfiguracji i testach planu;
samo dodanie reguł nie uruchamia aresztu na produkcji.
