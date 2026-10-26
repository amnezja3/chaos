# Odbiór wdrożonego podzakresu 161–163, 26.10.2026

Operator odebrał wdrożony podzakres zbierania i przygotowania geografii.
Wykorzystanie wszystkich warstw w mechanikach gry pozostaje przyszłym zakresem.

**Korekta po przeglądzie: ten protokół nie zamyka pełnego zakresu 161–163.**
Globalny odczyt repozytorium dla skanera i pozostałe braki opisuje
[aktualna macierz zakresu](world_scope_reconciliation_161_163_20261026.md).

## Potwierdzone na VPS

- Skanowanie MapLark, hakowanie i łączenie terytoriów: odbiór operatora na nowym
  oraz istniejącym koncie. Poprawka renderowania terytorium również odebrana.
- Magazyn, migracje, backup, kontrola integralności, pilotaż odczytu lokalnego
  i wygaszanie: potwierdzone w poprzednich odbiorach 162–163.
- Regularne zbieranie MapLark i Geoapify: działający kolektor, osobny monitor,
  limity wewnętrzne oraz retencja archiwum 7 dni.
- VK: `roads`, `overpass-bbox-geom-v1`, `committed`, odpowiedź kompletna,
  snapshot `b0caa9c460cfd7f0d9625df17624ba1749c3f28d2d02a391f080ff28d760e4fa`.
  Próba rozliczona jako jedno żądanie, bez płatnych kredytów.
- Następne pobranie VK / waterways zakończone POIError. Dokładny błąd nie został
  pokazany w logu; nie nazywamy go automatycznie timeoutem. Circuit zablokował VK,
  a następny cykl zapisał inland_water z MapLark. Potwierdza to przejście na
  źródło zapasowe, nie ukończenie nieudanego zadania waterways.
- Raport odbioru: 20 snapshotów, 562769 bajtów, 8 COMMITTED,
  1 FAILED_TERMINAL, VK 2/120 prób dziennie, warnings=[].

## Granice odbioru i utrzymanie

UNKNOWN oznacza obserwacje, nie certyfikat kompletnej geografii regionu.
Geoapify nie jest pełnym zamiennikiem skanera CHAOS. Inne instancje Overpass
nie zostały tym odbiorem aktywowane. Pięć dawnych operacji Geoapify z rezerwacją
25 kredytów pozostaje nierozstrzygniętych; nie zostały wyzerowane.
Weryfikacja stabilności usług i kosztów pozostaje ciągłym zadaniem utrzymania.
Komunikat `reconciliation_required` po rozliczonej próbie Overpass wymaga
doprecyzowania w przyszłym porządkowaniu diagnostyki.

Następny zatwierdzony zakres: UX paneli Identity Gateway oraz POI / Overpass.
Nie uruchamiamy jeszcze sprintu kamer 164.
