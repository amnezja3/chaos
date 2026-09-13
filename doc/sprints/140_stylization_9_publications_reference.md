# .9 — publikacje i archiwum / para referencyjna

Status: PARA ZAAKCEPTOWANA I WDROŻONA; odbiór runtime otwarty.
[Procedura wdrożenia](../runbooks/deploy_140_stylization_9_publications.md).
Przejście do .9 na polecenie użytkownika; statystyki
cyklu (cycle_statistics) pozostają otwartym elementem .8.

Para: `/static/references/ghostsignal/publications-pair.html?v=publications-ref-1`.
Pełny ekran: `/static/references/ghostsignal/publications.html?v=publications-ref-1`.

Trzy przełączane warianty wspólnej kompozycji:

- Googleplex — źródło, data, nagłówek, fragment artykułu;
- BlackNet — historia sygnału w formie wpisu terminalowego;
- Signal Registry — identyfikator i metryka cyklu, przejście do archiwum.

Desktop: duży tytuł po lewej, treść w ekranie na pierwszym planie,
rejestr źródeł i metryka po prawej. Portrait: tytuł, ekran treści,
indeks źródeł i metryka. Używa istniejącego tła zapisu, OFS i glitch.
Brak nowych bitmap, API, audio i wpływu na trigger/runtime.

Teksty, data i identyfikatory w parze są demonstracyjne. Po akceptacji
implementacja wykorzysta settlement.publications (medium/title/body/published_at)
oraz istniejące dane manifestu. Zachować rzeczywiste źródło i datę; brak
publikacji nie może wyświetlać tekstu referencyjnego. Limit istniejącej
projekcji: 6 publikacji, tytuł 160 i treść 480 znaków — pokazywać jako fragment.
BlackNet nie dodaje znaków prompta do autentycznej publikacji, jeśli nie są
częścią zapisu; tutaj demonstrują wariant graficzny.

Statyczne teksty referencji służą ocenie czytelności. Ewentualny typewriter
przy wdrożeniu musi używać istniejącego zegara show i pozostawić czas na odczyt.

Lokalnie: składnia JS oraz identyfikatory i polecenia wariantów sprawdzone.
Ocena wizualna desktop/portrait pozostaje w przeglądarce.
