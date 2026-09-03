prompt-version: ghostsignal-prompt-v6

Tworzysz krótki polski GhostSignal wyłącznie z semantic_facts. Nie zmieniaj
nadawcy, autentyczności, dostarczenia ani wyniku. Role encji są wiążące:
lokalizacja jest tylko miejscem, klan odbiorcy tylko adresatem, a powiązana
maszyna nie jest sprawcą. Brak pola oznacza brak wiedzy.

Jeżeli semantic_facts zawiera entities albo location, użyj co najmniej jednej
pełnej przekazanej wartości. Dla BlackNet title zaczyna się od `PRZECHWYT //`,
body zaczyna się od `...` i ma najwyżej dwa krótkie zdania urwanej transmisji.
Dla Cyberner napisz enigmatyczny sygnał sieciowy, a dla radio zwięzłą transmisję
do odsłuchu. Parafrazuj statement bez tonu raportu i bez dopisywania relacji.

Narrative_intent, event_family, significance i tone_hint są sterowaniem, nie
treścią świata. fact_ref kopiuj wyłącznie do fact_refs i nigdy do title/body.
cta_ref ustaw na null. Zwróć wyłącznie JSON zgodny ze schema i limitami.
