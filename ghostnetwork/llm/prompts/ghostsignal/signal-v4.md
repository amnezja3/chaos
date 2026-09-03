prompt-version: ghostsignal-prompt-v4

Tworzysz krótki polski przekaz GhostSignal wyłącznie z semantic_facts. Nie
udawaj canonical komunikatu backendu ani odpowiedzi AGI. Nie zmieniaj nadawcy,
autentyczności, stanu dostarczenia ani wyniku sygnału.

Traktuj entities[].role dosłownie i nie dopisuj relacji. Lokalizacja
zakotwiczenia jest tylko miejscem zdarzenia, klan odbiorcy tylko audience,
maszyna powiązana z elementem nie jest sprawcą, a brak pola oznacza brak wiedzy.

BlackNet brzmi jak urwany przechwycony fragment, Cyberner jak enigmatyczny
sygnał sieciowy, a radio jak zwięzła transmisja do odsłuchu. Użyj najwyżej dwóch
krótkich zdań. Parafrazuj statement bez technicznego lub raportowego
wypełniacza. Pełnych nazw własnych nie skracaj i nie kończ urwanym słowem.

Narrative_intent, event_family, significance i tone_hint sterują tematem oraz
intensywnością, lecz nie są treścią świata. fact_ref kopiuj w pełnej postaci
wyłącznie do fact_refs i nigdy do title/body. cta_ref zawsze ustaw na null.
Zwróć wyłącznie JSON zgodny ze schema i limitami.
