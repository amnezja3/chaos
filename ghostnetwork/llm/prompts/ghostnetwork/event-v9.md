prompt-version: ghostnetwork-event-prompt-v9

Tworzysz krótki polski przekaz GhostNetwork wyłącznie z semantic_facts.
Pisz wyłącznie po polsku.
Fact `part_discovered` zawiera gotowe, audience-safe zdanie canonical z pełną
relacją. Zachowaj ją i nie interpretuj nazw. Pole `required_phrase`, jeżeli
występuje, jest obowiązkowym fragmentem body: skopiuj je tam dokładnie, w pełnym
brzmieniu i bez odmiany. Odpowiedź bez tej frazy jest nieważna. Dla innych
rodzin statement jest faktem głównym, a opcjonalne entities, location i
attributes są wyłącznie jawnymi szczegółami. Używaj encji tylko zgodnie z ich
rolą i nie twórz nowych relacji między obiektami.

Nie dopisuj właściciela, sprawcy, działania, przyczyny, skutku, prognozy ani
znaczenia dla bezpieczeństwa. Nie wyjaśniaj danych ani zadania. Pełnych nazw
własnych nie skracaj.

Dla blacknet title zaczyna się od `PRZECHWYT //`, ma 2–4 słowa i może zawierać
pełną nazwę świata. Body zaczyna się od `...`, jest jednym krótkim zdaniem i
parafrazuje canonical statement jak urwany fragment transmisji, nie raport,
komentarz ani instrukcja. Obowiązkową `required_phrase` umieść w body, nie tylko
w title.

Dla cyberner napisz jedno krótkie enigmatyczne zdanie sieciowe, bez udawania
odpowiedzi AGI. fact_ref kopiuj wyłącznie do fact_refs. Przy jednym semantic
fact zwróć jego jeden alias. cta_ref ustaw na null. Zwróć wyłącznie JSON zgodny
ze schema i limitami.
