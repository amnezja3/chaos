# Audyt ryzyka integracji progresji — 2 X 2026

Zakres zatwierdzony przez autora: lokalna integracja ze wspólną warstwą profili,
pod warunkiem audytu i zastosowania jego wyników w tym samym etapie.
Bez wdrożenia, commita i pusha.

## Ustalenia i wymagane zabezpieczenia

| Ryzyko | Wymagana poprawka / dowód |
| --- | --- |
| Nagroda naliczona drugi raz po zapisaniu profilu | Checkpoint sum nagród; overlay idempotentny; test nagroda → zapis nicku → kolejna nagroda |
| Stary zapis nadpisuje awans | Nagroda zwiększa rewizję CAS bez zmiany pełnego JSON; test starego pełnego zapisu |
| Pulpit, kreator i mapa widzą różne LVL/RSP | Projekcje odczytują przyrosty względem zapisanego checkpointu, bez pełnego profilu |
| Zmiana innych pól profilu utrwala nagrodę dwukrotnie w projekcji | Jeden checkpoint dla utrwalonego dokumentu i jego projekcji; nie nakładać nagród ponownie w builderze projekcji |
| Jawny zapis respektu jest ignorowany | Overlay przed top-level patchem, potem zapis checkpointu; test wydania RSP |
| Nagroda bez komunikatu lub receipt po błędzie | Jedna transakcja SQLite; test wymuszonego błędu komunikatu i rollbacku |
| Uszkodzony lub przyszły checkpoint odejmuje nagrody | Odrzucać nieprawidłowe typy, ujemne wartości i checkpoint wyprzedzający ledger |
| Brak ledgera po utracie danych jest traktowany jak nowe konto | Checkpoint bez ledgera wymaga recovery; istniejące konta migrować jawnie offline |
| Migracja nadpisuje nagrody lub importuje zmieniony profil | Brak nadpisywania istniejącego wiersza; CAS rewizji i checksumy; jawna lista kont i dry-run |
| Overlay miesza statystyki z dwóch chwil | Odczyt odczytanych checkpointów i ledgera w tym samym snapshotcie transakcji |
| Zbyt szeroka aktywacja | Nie podłączać rozliczeń gry przed testami kompatybilności; flaga kreatorów pozostaje wyłączona |

## Granice odbioru

Testy samego ledgera nie potwierdzają zgodności wszystkich writerów profilu.
Po integracji wymagane są testy guarded writers, projekcji, równoległych nagród,
starego zapisu i migracji. Test pominięty w poprzednim etapie należy włączyć.
Cały 147 wymaga dodatkowo usunięcia ciężkich zależności przejęć i workerów;
zamknięcie tego audytu nie oznacza automatycznie PASS całego sprintu.

## Zastosowane wyniki audytu

- Integrację zastosowano lokalnie po zatwierdzeniu autora; bez wdrożenia.
- `overlay_row` odrzuca uszkodzony/przyszły checkpoint i checkpoint bez ledgera.
  Nie naprawia brakujących wymaganych LVL/RSP ani nie zmienia ich typów.
- Odczyty profilu i małych projekcji pobierają nagrody w spójnym snapshotcie.
  Pulpit, capabilities i tożsamość twórcy uwzględniają checkpoint.
- Patch nakłada przyrosty przed zmianą danych. Retry zachowuje nagrody przyznane
  po pierwszej próbie, również przy jawnym zapisie wartości RSP. Stary pełny zapis
  jest odrzucany przez CAS. Kod budujący absolutną zmianę ze wcześniejszego odczytu
  nadal powinien przekazywać jego `expected_revision`; brak CAS nie dowodzi świeżości
  takiej wartości sprzed wywołania metody zapisu.
- `settle` i `settle_strategic` delegują do nowej transakcji. Nagroda strategiczna
  liczy się z LVL odczytanego pod blokadą zapisu; zachowano kontrolę sesji przed commitem.
- Inicjalizacja wiersza jest tylko w jawnej rejestracji (obie istniejące ścieżki)
  lub migracji offline, nigdy przy backfillu projekcji. Usunięcie konta usuwa wiersz;
  pozostawiony osierocony wiersz blokuje ponowne wykorzystanie tożsamości.
- Statystyki zmienione przez poprawny legacy writer synchronizują się z ledgerem
  tylko przy zgodnym checkpointcie.
- Migracja i przełączenie wymagają zatrzymania writerów starej wersji. Cofnięcie
  do kodu bez odczytu ledgera po przyznaniu nagród nie jest bezpiecznym rollbackiem.

Dwa wcześniejsze błędy testów guarded writers odtworzono także na `HEAD:database.py`.
Oczekiwania dostosowano do istniejącego canonical security: invalid candidate usuwa
teraz wymagane `desktop_settings`, a lista overlays uwzględnia `security`.
Nie usunięto testów walidacji ani ochrony przed destrukcyjnym zapisem.

## Wynik weryfikacji

**80 testów PASS, bez pominięć**: progresja, receipts terytorialne, guarded writers,
profile manager, projekcje tożsamości, statyczny kontrakt zapisów i moduły/API kreatorów.
`git diff --check` bez błędów. Testy używały odizolowanych baz; migracji produkcyjnej
ani wdrożenia nie wykonano. Ten wynik dotyczy opisanej integracji, nie całego 147.

## Uzupełnienie: przejęcia i workery

Wyniki audytu zastosowano w kodzie:

- Usunięto pełne odczyty z przejęć, finalizacji geometrii, odczytu poziomu do
  otoczenia i audiencji klanowej. Resolver używa wcześniej utworzonych magazynów.
- Test wykrył lazy import oznaczonych celów z profilu. Przejęcie wymaga teraz
  wcześniejszej migracji, sprawdzanej przed zmianą stanu.
- Błąd zapisu celu lub operacji nie tworzy sukcesu tylko w pamięci. Błąd
  czyszczenia celu w workerze pozostawia zadanie do ponowienia.
- Nagrody GhostNetwork otrzymały kanoniczne statystyki i receipts. RSP i receipt
  zapisują się atomowo. Finalizacja klanu jest idempotentna, również po awarii.
  Historyczne receipts migrują bez wypłat. Applied bez dowodu wypłaty wymaga
  recovery zamiast zgadywania, czy ponownie doliczyć RSP.
- Zbiorcze przejęcia miały okno awarii między nagrodą a zużyciem dalszych receipts.
  Grupa zapisuje się teraz atomowo; test błędu późniejszego receipt potwierdza
  rollback całej grupy.
- Ranking GhostNetwork odczytuje avatar i poziom z małych projekcji, nie z profilu.

Testy starych luster zastąpiono asercjami kanonicznego stanu. Zachowano scenariusze
awarii, retry, reputacji klanu i neutralności kontrolowanej odbudowy. Guard SQL
wykrywa także ciężkie odczyty ukryte przez przechwycony wyjątek.

Końcowa weryfikacja cutoveru: **123 testy PASS, bez pominięć** (zestawy 67 + 55
oraz dodatkowy test pełnego przejęcia cudzego punktu). `git diff --check` czysty.
Zakresy: progresja i writers, polityka/migracja/API kreatorów, pełne przejęcia,
scoped runtime, kontrola terytorium, finalizacja konfliktu, GhostNetwork bridge,
ranking, operacje i ekspozycja kamer. To nie jest PASS całego sprintu 147.
