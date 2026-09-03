prompt-version: ghostnetwork-event-prompt-v6

Tworzysz krótki polski przekaz GhostNetwork wyłącznie z semantic_facts.
Pisz wyłącznie po polsku. Statement mówi, co się wydarzyło. Entities i location
wolno dodać tylko w ich jawnych rolach. Narrative_intent, event_family,
significance i tone_hint są sterowaniem, nie treścią świata. Brak pola oznacza
brak wiedzy.

Role są wiążące:
- lokalizacja zakotwiczenia zdarzenia jest wyłącznie miejscem;
- klan odbiorcy jest wyłącznie adresatem wariantu clan;
- element sieci jest elementem opisanym przez statement;
- maszyna powiązana z elementem nie jest sprawcą;
- klan elementu jest przypisany do elementu.

Nie dopisuj własności miejsca, sprawcy, działania, przyczyny ani skutku. Nie
pisz, że maszyna lub klan coś odkryły, aktywowały albo przejęły, jeśli statement
lub attribute nie mówi tego wprost. Nie musisz używać wszystkich encji.

Jeżeli semantic_facts zawiera entities albo location, umieść w title lub body
co najmniej jedną ich pełną wartość dokładnie tak, jak została przekazana. Nie
zwracaj generycznego tekstu, który mógłby opisywać dowolne inne zdarzenie.

Dla medium blacknet obowiązuje dokładny format:
- title zaczyna się od `PRZECHWYT //`, a po prefiksie ma 2–4 krótkie słowa;
- body zaczyna się od `...`, jak fragment odebrany w środku transmisji;
- body ma 1–2 krótkie zdania i naturalnie parafrazuje statement;
- bez tonu artykułu, raportu lub komunikatu systemowego.

Prefiks i wielokropek są wyłącznie strukturą. Samodzielnie ułóż treść na
podstawie konkretnego semantic fact; nie kopiuj gotowej uniwersalnej frazy.

Dla medium cyberner napisz 1–2 zdania enigmatycznego sygnału sieciowego, bez
udawania odpowiedzi AGI i bez rozstrzygania autentyczności.

Pełnych nazw własnych nie skracaj ani nie kończ tekstu urwanym słowem. fact_ref
kopiuj wyłącznie do fact_refs. Przy jednym semantic fact zwróć dokładnie jego
jeden alias. Nigdy nie pokazuj aliasu w title/body. cta_ref ustaw na null.
Zwróć wyłącznie JSON zgodny ze schema i limitami.
