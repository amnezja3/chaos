# Przejęcie pojazdu uruchamiało efekty terytorialne

## Zgłoszenie i diagnoza

2026-10-05: operator zgłosił alarmy o wcześniejszych wtargnięciach po każdym
zhakowanym samochodzie oraz komunikaty o rozszerzeniu terenu i nagrodach LVL/RSP.

W kodzie `/gonna-win` po pełnym przejęciu także cel generowany uruchamiał
przebudowę obszarów, wyszukiwanie konfliktów i rozliczenie progresji terenu.
Statyczna synchronizacja intruzów traktowała gracza stojącego w obszarze jako
kandydata do kolejnego alarmu; deduplikacja zdarzeń chroniła tylko przez 60 sekund
i uwzględniała ID obszaru, które może zmienić się po przebudowie.

Flaga `stationary` wynikała głównie z `generated`. Samochód z historycznego
markera bez tej flagi mógł zostać zapisany jako punkt terytorium. Ponadto receipt
mobilnego przejęcia nie wykluczał naliczania przyrostu geometrii powstałego
w międzyczasie z innych operacji. Brak odczytu bazy produkcyjnej nie pozwala
ustalić, który wariant spowodował konkretne zgłoszone nagrody.

## Poprawka

- Pojazdy i osoby nie są punktami terytorium, także bez `generated`.
  Zapis i budowanie geometrii korzystają ze wspólnej klasyfikacji.
- Przejęcie celu nieterytorialnego pomija przebudowę i wyszukiwanie konfliktów.
  Receipt zapisuje zerową nagrodę terytorialną bez nadpisywania statystyk terenu.
- Statyczne wykrywanie intruzów porównuje pozycję z geometrią sprzed przebudowy,
  także przy przejęciu przez okrążenie. Istniejąca obecność nie jest nowym wejściem.
  Rzeczywiste wejścia z ruchu oraz gracze objęci nowym terenem nadal wywołują alarm.

## Weryfikacja i wdrożenie

Regresje obejmują HTTP `/gonna-win` dla pojazdu bez `generated`, brak przebudowy
i nagród terenu, odrzucenie przyrostu z równoległej operacji, stare alarmy po
wygaśnięciu cooldownu i zmianie ID obszaru oraz ostrzeżenie przy rozszerzeniu.
Sprawdzane są też dotychczasowe przejęcia punktów i konflikty terytorialne.

Zmiana wymaga wdrożenia backendu. Nie usuwa historycznych nagród ani komunikatów
już zapisanych w kolejce. Nie wykonywano migracji ani korekty kont produkcyjnych.
Komunikat Response Network o aktywności przy samochodzie dotyczy osobnego
mechanizmu konsekwencji i nie został wyłączony przez tę poprawkę.
