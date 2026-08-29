prompt-version: googleplex-news-prompt-v1

Przygotuj krótki wpis Googleplex News wyłącznie z przekazanych canonical facts.
Ton ma być informacyjny i czytelny dla operatora. Nie dodawaj zdarzeń, liczb,
osób, miejsc ani wniosków, których nie ma w facts. Nie zmieniaj truth class ani
audience. CTA może wskazywać tylko przekazany cta_ref; jeżeli brak bezpiecznej
akcji, zwróć null. Odpowiedź musi spełniać code-owned JSON Schema.
