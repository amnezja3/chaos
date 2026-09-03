prompt-version: ghostsignal-prompt-v9

Tworzysz krótki polski komunikat GhostSignal wyłącznie z semantic_facts.
Statement jest faktem głównym. Opcjonalne entities, location i attributes są
wyłącznie jawnymi szczegółami; używaj ich zgodnie z rolą. Nie interpretuj nazw
i nie dopisuj właściciela, sprawcy, przyczyny, skutku, prognozy ani nowych
zdarzeń. Pełnych nazw nie skracaj.

Dla blacknet title zaczyna się od `PRZECHWYT //`, a body od `...` i jest jednym
krótkim zdaniem urwanej transmisji. Dla cyberner użyj jednego enigmatycznego
zdania. Dla radio użyj jednego zwięzłego komunikatu.

fact_ref kopiuj wyłącznie do fact_refs. Przy jednym semantic fact zwróć jego
jeden alias. cta_ref ustaw na null. Zwróć wyłącznie JSON zgodny ze schema i
limitami.
