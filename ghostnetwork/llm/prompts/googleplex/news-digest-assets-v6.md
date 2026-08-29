prompt-version: googleplex-news-assets-prompt-v6

Napisz po polsku krótki wpis Googleplex News oparty wyłącznie na przekazanych
canonical facts. Wybierz dokładnie jeden fact_ref. Tytuł lub treść musi
dosłownie zawierać czytelny title (możesz pominąć prefiks przed znakiem `/`),
label albo stat z tego samego wiersza faktu. Nie opisuj pozostałych faktów.
Bezwzględnie zachowaj title_chars i body_chars z output_limits. Nie ujawniaj
fact ID ani żadnego fragmentu fact_ref w title/body. Nie ujawniaj receipt, task,
event, signal ani token-like technical identifiers. Nie wymyślaj zdarzeń,
liczb, osób, miejsc ani wniosków. Zachowaj truth class i audience. Jeżeli
wybierasz CTA, jego wiersz musi wskazywać ten sam fact_ref co tablica fact_refs;
w przeciwnym razie zwróć cta_ref=null. asset_ref musi odpowiadać polu
asset_state wybranego faktu zgodnie z asset_refs_by_state albo mieć wartość
`gp_fallback_network`. Odpowiedź musi spełniać code-owned JSON Schema.
