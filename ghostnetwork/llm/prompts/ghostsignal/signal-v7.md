prompt-version: ghostsignal-prompt-v7

Tworzysz krótki polski GhostSignal wyłącznie z semantic_facts. Nie kopiuj nazw
ról i nie dopisuj relacji, sprawcy, przyczyny, skutku ani prognozy.

Jeżeli entities albo location istnieją, body zawiera co najmniej jedną pełną
przekazaną wartość. Dla BlackNet title ma format `PRZECHWYT //` plus 2–4 słowa
bez nazw własnych, a body zaczyna się od `...` i jest jednym urwanym zdaniem.
Dla Cyberner napisz jedno enigmatyczne zdanie, a dla radio jedną zwięzłą
transmisję. Nie skracaj nazw.

fact_ref kopiuj wyłącznie do fact_refs. cta_ref ustaw na null. Zwróć wyłącznie
JSON zgodny ze schema i limitami.
