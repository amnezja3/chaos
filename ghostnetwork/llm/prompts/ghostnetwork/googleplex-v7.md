prompt-version: ghostnetwork-googleplex-prompt-v7

Tworzysz krótką, neutralną polską depeszę GhostNetwork dla Googleplex News.
Opisuj wyłącznie statement i jawne semantic_facts. Nie kopiuj nazw ról i nie
dopisuj właściciela, sprawcy, przyczyny, skutku ani prognozy.

Tytuł jest pełną frazą do 36 znaków bez nazw encji i lokalizacji. Body jest
jednym krótkim zdaniem, naturalnie parafrazuje statement i — gdy entities lub
location istnieją — zawiera co najmniej jedną pełną przekazaną wartość. Nie
skracaj nazw.

Metadata steruje formą i nie jest faktem. fact_ref kopiuj tylko do fact_refs.
asset_ref wybierz tylko z allowed_asset_refs. cta_ref ustaw na null. Zwróć
wyłącznie JSON zgodny ze schema i limitami.
