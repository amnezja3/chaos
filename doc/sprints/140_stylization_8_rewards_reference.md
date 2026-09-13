# 140.stylization.8 — nagrody finału / para referencyjna

Status: DO OCENY desktop + portrait. Scena runtime pozostaje bez zmian.

Para: `/static/references/ghostsignal/rewards-pair.html?v=rewards-ref-1`.
Pełny ekran: `/static/references/ghostsignal/rewards.html?v=rewards-ref-1`.

Tytuł NAGRODY / FINAŁU; centrum pokazuje RSP wybranej kategorii,
liczbę zapisów nagród i krótki opis. Rejestr po prawej (portrait: na dole)
zawiera wszystkie trzy kategorie, aktywny wiersz jest podświetlony OFS.
Suma finału pozostaje stała. Pasek pokazuje udział kategorii w sumie RSP.
Wspólne tło i glitch oraz przygaszone światło, ramki i puls napisów
pochodzą z dotychczasowej oprawy. Bez dodatkowych odznak ani nowych assetów.

Kategorie odpowiadają istniejącemu reward_groups:

- ghost_signal_node_holder — kontrola węzłów;
- ghost_signal_closer — zamknięcie sygnału;
- ghost_signal_territory_consumed — terytoria finału.

Referencja używa przykładowych wartości: 200 + 40 + 124 = 364 RSP,
20 + 1 + 23 = 44 zapisy nagród. Liczba zapisów nie oznacza liczby graczy.
Przyciski pary: jeden przebieg po 10 s na kategorię, pauza, kolejna kategoria.
Oba widoki otrzymują wspólne polecenie startu. Nie ma API gry ani audio.

Implementacja po akceptacji korzysta z istniejącej projekcji settlement,
zachowuje kwoty archiwalne i obsługuje brak danych oraz dodatkowe typy nagród
bez pomijania ich w sumie. Ta para nie obejmuje rankingu klanów.

Sprawdzenie lokalne: składnia JS, zgodność identyfikatorów HTML/JS i diff check.
Ocena wizualna pozostaje po stronie przeglądarki desktop/portrait.
