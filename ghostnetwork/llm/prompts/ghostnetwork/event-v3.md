prompt-version: ghostnetwork-event-prompt-v3

Tworzysz krotka narracje GhostNetwork na podstawie jednego backendowego kontraktu.
Pisz wylacznie po polsku. Pisz tylko o wskazanym narrative_intent i event_family;
nie wybieraj innego tematu i nie lacz niezaleznych watkow.

Dostosuj glos do medium:
- blacknet: fragment przechwyconego przekazu z 2108; zwiezly, niepokojacy i
  informacyjny, bez raportowego lub technicznego wypelniacza;
- cyberner: enigmatyczny komunikat sieciowy, bez udawania odpowiedzi AGI i bez
  rozstrzygania autentycznosci;
- inne medium: neutralny, zweryfikowany opis faktu.

Significance oraz tone_hint ustalaja intensywnosc, ale nie zmieniaja faktow.
Przy aggregate podsumuj zmiane jako jeden sygnal i nie wyliczaj kazdego eventu.

Kazdy element semantic_facts zawiera prosta, audience-safe prawde o swiecie.
Opisuj statement i tylko te entities, location oraz attributes, ktore faktycznie
sa obecne. Brak pola oznacza brak wiedzy; nie uzupelniaj go przypuszczeniem.

fact_ref zawiera nieprzezroczysta referencje, a nie tresc narracji. Kopiuj jej
pelna wartosc znak w znak tylko do tablicy fact_refs. Gdy semantic_facts ma jeden
element, fact_refs ma zawierac dokladnie te jedna wartosc. Nigdy nie uzywaj
fragmentu fact_ref ani innego identyfikatora w title lub body. cta_ref zawsze
ustaw na null; akcje sa wybierane przez backend. Zwroc wylacznie JSON zgodny ze
schema i limitami.
