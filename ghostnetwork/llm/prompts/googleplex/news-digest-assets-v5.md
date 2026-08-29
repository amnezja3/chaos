prompt-version: googleplex-news-assets-prompt-v5

Napisz po polsku krótki wpis Googleplex News oparty wyłącznie na przekazanych
canonical facts. Wybierz dokładnie jeden fact_ref i oprzyj cały tytuł oraz
treść tylko na presentation-safe title, label i stat z tego samego faktu.
Bezwzględnie zachowaj title_chars i body_chars z output_limits. Nie ujawniaj
fact ID ani żadnego fragmentu fact_ref w title/body. Nie ujawniaj receipt, task,
event, signal ani token-like technical identifiers. Nie wymyślaj zdarzeń,
liczb, osób, miejsc ani wniosków. Zachowaj truth class i audience. Jeżeli
wybierasz CTA, jego wiersz musi wskazywać ten sam fact_ref co tablica fact_refs;
w przeciwnym razie zwróć cta_ref=null. asset_ref jest obowiązkowy i musi być
dokładnie jedną wartością z allowed_asset_refs. Odpowiedź musi spełniać
code-owned JSON Schema.
