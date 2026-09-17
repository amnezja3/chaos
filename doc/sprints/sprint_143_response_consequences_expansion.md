# Sprint 143 — tabela konsekwencji, recydywa, ograniczenia i więzienia

Status: ZAPLANOWANY, zależny od produkcyjnego PASS sprintu 142.
Rozszerzony audyt wejściowy ukończony przed developmentem; decyzje reuse
i granice obecnego MVP opisuje [raport](../audits/response_consequences_2026_09_16.md).
Sprint realizuje nowe sankcje, nie służy odkrywaniu istniejącego mechanizmu.
Cel: rozszerzyć sprawdzony executor przez wersjonowane rodzaje sankcji,
bez osobnego systemu kar i bez pełnych odczytów profilu.

Zakres zatwierdzony: coraz surowsze kary zależne od przewinienia, eskalacji
i recydywy; blokady ruchu/teleportów/systemu, w tym Cybernera, oraz osadzenie
w więzieniach z zatwierdzonego katalogu. Wylogowanie nie kasuje sankcji.

## 143.1 — wersjonowana tabela konsekwencji i recydywa

Tabela jest konfiguracją backendu, nie zestawem warunków w frontendzie.
Każda decyzja zapisuje wersję policy, użyte współczynniki i wybrany poziom.

| Wejście | Źródło/zasada |
|---|---|
| Poziom i eskalacja incydentu | Canonical stan i historia incydentu z 142 |
| Liczba incydentów gracza | Unikalne inicjacje przypisane graczowi; bez duplikatów publikacji |
| Kolejne zatrzymania/recydywa | Trwałe receipts zatrzymań, nie liczba requestów detektora |
| Kamery | Liczba wykrytych/wyłączonych, skuteczność i aktualność osłony z 142 |
| Rola gracza | Inicjator/postronny; szansa 80/30 oddzielona od surowości kary |
| Pozostałe modyfikatory | Wyłącznie zweryfikowane reguły współdzielone z aktywnymi częściami/Super Powers |

Propozycja tabeli do balansu — podane przez autora 5/10/15/20 minut są
przykładowymi progami; dokładne kryteria, zestawy i czasy zatwierdzić przed
aktywacją, nie traktować poniższej propozycji jako działającego gameplayu:

| Poziom | Przykładowy czas | Proponowany zestaw |
|---|---|---|
| 1 | 5 min | Czasowa blokada ruchu i teleportów |
| 2 | 10 min | Osadzenie + blokada ruchu i teleportów |
| 3 | 15 min | Osadzenie + powyższe + blokada Cybernera |
| 4 | 20 min | Osadzenie + ograniczenie aplikacji do Web Dragona i radia |

Recydywa zwiększa surowość według jawnych progów/okna historii i limitów,
bez wielokrotnego liczenia tego samego spotkania. Jedna kara nie może
samoczynnie generować kolejnych zatrzymań w więzieniu. Ustalić reset/decay
recydywy, łączenie kar i maksymalny czas; wykorzystać tabelę reuse z 142.

## 143.2 — trwały model sankcji i czas odbywania

Mały canonical store: sanction_id, actor, encounter/receipt, rodzaj, powód,
starts_at, duration_seconds, remaining_seconds, rozliczony czas obecności,
status, wersja, parametry oraz historia zmian. Sam wall-clock expires_at
nie wystarcza: wylogowanie na 2–3 h nie może automatycznie odbyć wyroku.
Proponowana realizacja: serwerowe rozliczanie czasu online, pauza offline,
kontynuacja po powrocie; granice heartbeat/timeout i wiele kart wymagają
jednoznacznej reguły. Nie ufać timerowi ani deklaracji online klienta.
Indeks aktywnych sankcji po graczu; typy movement_block,
teleport_block, incarceration, communication_block i ograniczenia aplikacji.
Idempotentne nałożenie, przedłużenie według jawnej reguły i zwolnienie.

## 143.3 — egzekwowanie ruchu i teleportów

Jedna backendowa bramka we wszystkich drogach zmiany pozycji: jazda,
ustawienie pozycji, bilety/teleport, CTA BlackNet/GN, narzędzia i inne
przeniesienia. Najpierw zinwentaryzować wszystkie writery pozycji.
Kontrola przed zakupem/pobraniem kosztu oraz przed commit; zero utraty
biletu/HC po odmowie, race z nakładaniem sankcji rozstrzygany atomowo.
Odróżnić dobrowolny ruch od uprawnionego transportu do/z więzienia:
wewnętrzna capability serwera, nigdy flaga bypass z klienta.
UI: wspólny powód blokady i czas; serwer egzekwuje też bez UI.

## 143.4 — więzienia i zwolnienie

Katalog v1 dodany 16 IX 2026: `response_network/prison_catalog.py` zawiera
10 więzień z zatwierdzonej listy autora, z zachowaniem ID, nazw, typów
i współrzędnych. `fullName` ujednolicono do `full_name`; alias zachowany.
`list_prisons()` i `get_prison(id)` zwracają niezależne słowniki bez odczytów
profilu/bazy. Nieznany ID oznacza KeyError, bez losowego zastępstwa.
Katalog nie nakłada sankcji, nie publikuje markerów ani nie teleportuje.
Punkty bezpiecznego zwolnienia pozostają do określenia — podane współrzędne
są miejscami osadzenia, nie automatycznymi miejscami powrotu.
W jednej transakcji zapisać sankcję, miejsce powrotu, przemieszczenie,
zatrzymanie jazdy/tras i outbox mapy. Nie resetować przypadkowo PvP/cooldownów.
Backendowy stan pozostałej kary, odporny na zmianę zegara klienta, restart
i disconnect. Jeden idempotentny mechanizm zwolnienia, bounded worker i kontrola
przy wznowieniu sesji. Bez kar dla nieobecnych z zaległych wykryć.

Do decyzji przed kodem: dokładne progi/czasy tabeli; wybór więzienia; punkt
powrotu; łączenie/przedłużanie sankcji i techniczne rozliczanie obecności.
Odrzucona wcześniejsza propozycja: automatyczne upływanie wyroku w czasie
offline. Brak nowych kar offline nie usuwa wcześniej nałożonych sankcji.
Cykl publicznego incydentu jest niezależny od odbywania kary: uwięzienie ani
wylogowanie inicjatora nie usuwa publicznego miejsca i jego odbiorców.

## 143.5 — ograniczenia systemowe i komunikacja

Przygotować rejestr typów sankcji i jeden kontrakt capability. Tabela określa
dostęp do ruchu, teleportów, Cybernera oraz pozostałych aplikacji. Dla
najostrzejszego poziomu gameplay pozostawia Web Dragona i radio; obsługa
sesji, wyroku, komunikatów systemowych i bezpiecznego wyjścia nadal działa.
Backend blokuje niedozwolone akcje z mapy, terminala, desktopu i bezpośredniego
API, także z wcześniej otwartego okna. UI pokazuje powód i pozostały czas.
Sprecyzować odczyt/wysyłkę i kanały Cybernera; nie tworzyć furtki przez inny
launcher. Zweryfikować rzeczywistą tożsamość aplikacji Web Dragon w katalogu.

## 143.6 — testy, migracja, odbiór

- Każda droga ruchu/teleportu odmawia podczas sankcji, działa po końcu;
  próba bezpośredniego POST nie omija blokady.
- Wygaśnięcie dokładnie na granicy czasu, reconnect, restart workera,
  powtórny transport/zwolnienie, brak lub zmiana miejsca powrotu,
  dwie sankcje równolegle, race z zakupem i zmianą pozycji.
- Wylogowanie na 2–3 h: pozostała kara nie zeruje się; publiczny incydent
  nadal podlega własnemu cyklowi, inni gracze widzą miejsce. Wiele kart nie
  przyspiesza odbywania wyroku, fałszywy heartbeat nie zmienia wyniku.
- Granice poziomów 5/10/15/20, recydywa i dedupe zatrzymań, liczby kamer,
  aktywne Super Powers, powody decyzji; Web Dragon/radio dostępne, zabronione
  aplikacje blokowane również przez bezpośrednie API i już otwarte okna.
- Desktop/mobile: timer i wyjaśnienie; mapy innych graczy otrzymują delta
  pozycji zgodnie z widocznością; żadnych nowych wycieków pozycji więźnia.
- Profile 35 MB: zero full read/write, bounded liczba zapytań i pracy workera.
- Migracja jawna z backup/verify i flagami per typ; kill switch nowych kar
  nie może uniemożliwiać zwolnienia już uwięzionych.

DoD: canonical efekty i recovery PASS, wszystkie writery zabezpieczone,
uzgodniony balans i reguły wyroków, odbiór autora, runbook ręcznego zwolnienia
z audytem i kontrolą uprawnień, bez kasowania dowodów naliczonych kar.
