# 142.3 — unieważnianie narracji przez aktualizacje mapy

Produkcja: sześć kolejnych tasków GooglePlex News z 17.09, 15:06–16:21 UTC,
zakończyło się `incident_source_superseded`; cztery przed pierwszą próbą,
dwa po jednej próbie. Incydenty nadal miały stan `escalated`. Zegary serwera
i przeglądarki są zgodne; NTP działa. Odczyt historycznych tasków nie pozwala
odtworzyć każdej zmiany źródła, ale kod i test reprodukują mechanizm blokady.

## Przyczyna

Środek incydentu jest średnią pozycji operacji ważoną bieżącym heat.
Zmiany heat przesuwają środek i zwiększają `publication_version`, nawet gdy
poziom, stan oraz miejsca operacji pozostają takie same. Ta sama wersja
chroniła zadania Ollamy, wynik generacji i publikację. Generacja mogła zostać
unieważniona szybciej, niż model zdążył ją ukończyć.

## Poprawka

- Wersja mapowa pozostaje bez zmian. `narrative_version` zależy od stanu,
  poziomu, promienia oraz zbioru pozycji operacji. Dla źródeł bez pozycji
  operacji bierze pod uwagę środek. Jest przechowywana w istniejącym JSON-ie.
- Nowe zadania używają wersji narracji przy claim, po generacji, podczas
  sprzątania oraz atomowego zatwierdzania publikacji. Stare zadania zachowują
  ścisłą kontrolę poprzedniej wersji; nie przywracamy rekordów dead-letter.
- Idempotency źródła nie zależy już od przesunięć ważonego środka. Aktualizacja
  mapy nie zastępuje identycznego, trwającego zadania nową kopią.
- Punkt CTA jest przeliczany z bieżącego incydentu w transakcji publikacji,
  wspólną funkcją używaną również przy budowaniu faktów BlackNetu.
- TTL, zakończenie cooling, zamknięcie źródła i istotna zmiana narracji nadal
  blokują publikację. Brak odczytów pełnych profili i nowego globalnego skanu.

## Odbiór

Walidacja lokalna: 85 testów PASS (77,161 s): incident_narrative_retirement,
incident_lifecycle_publications, narrative_freshness, narrative_publications,
llm_event_producers, incident_pipeline_audit. Po dodaniu obsługi źródeł
bez zapisanego narrative_version: 7 testów modułu retirement PASS (8,369 s).
Wszystkie przez `tools/run_isolated_tests.py`, na tymczasowych bazach.

Test regresji zmienia środek podczas generacji, publikuje oba media,
sprawdza aktualny punkt CTA, zachowanie wpisu po delcie mapowej oraz jego
unieważnienie po zmianie poziomu. Osobne przypadki sprawdzają deduplikację
i zmianę wersji przy zmianie stanu, promienia i pozycji operacji.

Po wdrożeniu kodu zrestartować chaos, territory worker, Ollama worker i
publisher z ich plików ecosystem przez `startOrRestart ... --update-env`.
Nowy task GooglePlex News powinien zakończyć generację i publikację przy
stabilnym stanie incydentu, mimo zmian heat/środka. Potwierdzić widoczny wpis
w News i poprawny odnośnik do mapy. Sam status `created` nie stanowi PASS.
142.4 pozostaje poza tym hotfixem; odbiór produkcyjny publikacji jest otwarty.
