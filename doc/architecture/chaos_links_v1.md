# Linki CHAOS — standard systemowy (rozszerzenie v2)

Wspólny komponent: `static/js/chaos_links.js` i `static/css/chaos_links.css`.
Link jest prawdziwym elementem `a`, z klasą `chaos-link` i `data-chaos-link`.
Akcja uruchamia się wyłącznie po kliknięciu/aktywacji klawiaturą. Parsowanie
odrzuca nieznane akcje, dodatkowe argumenty i współrzędne spoza zakresu.

| Widoczna postać | href | Zachowanie |
| --- | --- | --- |
| focus:lat:lon | chaos:focus/48.86417:2.33050 | Automatycznie rozpoznawany tekst; otwiera mapę i ustawia fokus |
| teleport:lat:lon | chaos:teleport/48.86417:2.33050 | Automatycznie rozpoznawany tekst; dialog potwierdzenia, potem kanoniczny teleport |
| focus cur:loc | chaos:focus/cur:loc | Geolokalizacja urządzenia przez istniejącą obsługę uprawnień, potem fokus |
| teleport cur:loc | chaos:teleport/cur:loc | Geolokalizacja urządzenia, potwierdzenie i kanoniczny teleport |

`cur:loc` nie oznacza pozycji awatara ani lokalizacji kamery. Zachowuje semantykę
istniejących poleceń terminala. Wyświetlana współrzędna może być zaokrąglona;
href przenosi pełną dostępną precyzję. Samo renderowanie linku nie pyta o GPS
i nie wysyła polecenia teleportu.

Wygląd: mały badge, delikatna turkusowa ramka, radius 5 px, stonowany glow,
widoczny focus klawiatury. Dedykowane SVG: celownik Focus i błyskawica Teleport
w `static/images/system/chaos-actions.svg`. Wariant kompaktowy zawiera ikonę
i krótką nazwę; zwykły link tekstowy również zaokrąglone współrzędne. Pełna
precyzja jest w href/title/aria-label. `ChaosLinks.create()` jest wspólną fabryką.

`ChaosLinks.enhance()` rozpoznaje pełne frazy w węzłach tekstowych okien
`.app-window`, `.terminal` oraz jawnych obszarów `[data-chaos-text]`.
MutationObserver obsługuje tylko zmienione teksty/poddrzewa, także nowe wiadomości
i lokalizację UI. Bez skanowania całego desktopu przy każdym ticku. Cyberner
i Google Plex korzystają z tej samej automatycznej warstwy.

Renderer tworzy DOM, nie interpretuje HTML tekstu. Pomija istniejące linki,
przyciski, edytory, input/textarea, code/pre, SVG i `[data-chaos-no-links]`.
Ponowny render jest idempotentny. Przechwycenie kliknięcia akcji zapobiega
jednoczesnemu uruchomieniu akcji otaczającej karty. Google Plex News używa
article z osobnym przyciskiem CTA, aby nie zagnieżdżać linków w button.
Komunikaty trafiają do `[data-chaos-link-output]`; komponent tworzy ten obszar
w aplikacji, jeśli go brakuje. Samo rozpoznanie frazy nigdy nie wykonuje akcji.

Camera Network pokazuje wyłącznie Focus i Teleport do kamery, na górze okna.
Warianty cur:loc pozostają kompatybilnością standardu, nie przyciskami kamery.
„O materiale” jest lokalnym przyciskiem rozwijającym opis, nie akcją lokalizacji.
