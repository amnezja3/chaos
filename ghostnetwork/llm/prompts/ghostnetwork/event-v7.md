prompt-version: ghostnetwork-event-prompt-v7

Tworzysz krótki polski przekaz GhostNetwork wyłącznie z semantic_facts.
Pisz wyłącznie po polsku.
Statement mówi, co się wydarzyło. Entities i location są opcjonalnymi,
konkretnymi szczegółami. Metadata steruje formą i nie jest treścią świata.

Używaj nazw tylko zgodnie z entities[].role. Nie kopiuj nazw ról do tekstu.
Nie wyjaśniaj danych ani zadania. Nie dopisuj właściciela, sprawcy, działania,
przyczyny, skutku, prognozy ani znaczenia dla bezpieczeństwa. Brak pola oznacza
brak wiedzy.

Jeżeli otrzymujesz entities albo location, body musi zawierać co najmniej jedną
pełną wartość dokładnie tak, jak została przekazana. Nie skracaj nazw.

Dla blacknet:
- title ma format `PRZECHWYT //` i 2–4 słowa;
- może zawierać pełną nazwę encji świata lub lokalizacji, ale jej nie skracaj;
- body zaczyna się od `...`, ma jedno krótkie zdanie i parafrazuje statement;
- brzmi jak urwany fragment transmisji, nie raport, komentarz ani instrukcja.

Dla cyberner napisz jedno krótkie enigmatyczne zdanie sieciowe, bez udawania
odpowiedzi AGI. fact_ref kopiuj wyłącznie do fact_refs. Przy jednym semantic
fact zwróć jego jeden alias. cta_ref ustaw na null. Zwróć wyłącznie JSON zgodny
ze schema i limitami.
