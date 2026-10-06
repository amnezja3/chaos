# Sprint 153 — przegląd gotowości, 6 X 2026

Werdykt: **gotowi do rozpoczęcia 153.1 i 153.2**. Zakres i decyzje produktowe
są zapisane; brak blokady ze strony zamrożonych 149–152. Nie jest to PASS
implementacji ani gotowość do udostępnienia EN graczom.

## Sprawdzony zakres

- Plany 153–155 i [rejestr zakresu](ghost_system_i18n_inventory.md): 11 obszarów
  powłoki/fundamentu, 15 grup aplikacji/katalogów/radia, 8 grup treści i odbioru.
- Źródła ustawień: `normalize_desktop_settings()` i writer w `run.py`,
  `UserIdentityProjectionStore.update_desktop_settings()`, testy
  `tests/test_desktop_settings_writer.py`. Istnieje lekka ścieżka zapisu
  ustawień i bootstrapu; należy rozszerzyć ją o locale i testy, zamiast czytać
  pełny profil lub tworzyć równoległy store preferencji.
- Punkty wejścia powłoki, FM, radia i rendererów w `static/js/terminal.js`,
  `static/js/ghost_radio.js` oraz szablonach. Rejestr źródeł wymaga dalszego
  rozwinięcia do konkretnych kluczy; nie ma jeszcze wdrożonych katalogów i18n.
- Usunięto z planu 155 ogólne sformułowania sprzeczne z wyjątkiem BN oraz
  rozdzielono szablonowe powiadomienia Cybernera od sygnałów narracyjnych.

## Obowiązująca macierz decyzji

Ponowny przegląd objął wszystkie 11 pozycji pulpitu ze zrzutu oraz Ghost Signal
Show / Sender. Znaleziono zbyt ogólne pokrycie pokazu i brak osobnej pozycji
Dev Bug Reportera. Uzupełniono B14/B15 i scenariusze odbioru C06. Sprawdzono
`ghostnetwork/transmission.py`, `show.py`, `show_manifest.py`, renderer pokazu
i archiwum. Sender jest tu ścieżką transmisji, nie postulatem nowej aplikacji.
Usunięto też z rejestru nieuprawnione rozszerzenie wyjątku BN na wszystkie
publikacje LLM. Polityka języka narracji GhostSignal pozostaje do jawnego
zatwierdzenia przed jej generowaniem; nie blokuje rozpoczęcia fundamentu 153,
ale blokuje pełny odbiór 155. Nie potwierdzono kompletności każdego tekstu
w kodzie ani zasobach multimedialnych — temu służy inwentaryzacja 153.

| Obszar | Reguła |
| --- | --- |
| UI, systemowe nazwy/opisy i komunikaty | PL/EN według ustawienia gracza |
| Treści graczy | Oryginał, bez automatycznego tłumaczenia |
| Googleplex News | Tytuł i treść według locale odbiorcy; jedna publikacja, warianty językowe |
| BlackNet | Jeden sygnał w jednym zatwierdzonym języku; kolejne mogą być w innych |
| Radio | Niezależny wybór PL/EN/ANY; metadane języka kanału i audycji; bez automatycznego przekładu nagrań |
| Ollama | Zatwierdzony prompt i locale zadania, niesprzeczne instrukcje; odrębna polityka News i BN, ANY nie jest językiem modelu |
| FM `/about`, `/tip&trick` | Oryginały zostają; osobne zatwierdzone wydania językowe obok nich |
| 149–152 | Zamrożone do odwołania; nie realizować ich funkcji w ramach i18n |

## Kolejność pierwszych prac

1. **153.1:** przejść aktywne ścieżki A01–A11 i rozwinąć rejestr do pól/kluczy.
   Ustalić pochodzenie tekstu, parametry i test. Sporządzić glosariusz oraz
   listę nazw własnych. Potwierdzić nieaktywne pliki historyczne.
2. **153.2:** wybrać wspólny format źródłowy i realizację JS/Python. Zapisać
   decyzję techniczną z przykładami liczby mnogiej PL/EN, interpolacji,
   escapingu, dat i fallbacku. Najpierw mały test zgodności obu runtime'ów,
   dopiero potem masowa ekstrakcja tekstów.
3. Rozszerzyć istniejący writer ustawień i lekki bootstrap o locale. Ustalić
   zachowanie sesji przed logowaniem, starego konta PL, wielu kart, iframe'ów
   i wylogowania. Nie dopuścić do przecieku języka między kontami.
4. Wdrożyć selektor i przełączanie paczek bez utraty stanu. Przeprowadzić
   pionowy scenariusz: ustawienia → zmiana języka → terminal/FM → ponowne logowanie.
5. Przenieść resztę A01–A11; uruchomić testy jednostkowe i Playwright na desktopie
   i mobile, także z klawiaturą i fullscreen gry. EN nadal oznaczone jako testowe.

To zadania rozpoczynające sprint, nie brakujące zgody użytkownika. Przed masową
migracją trzeba domknąć punkty 1–2, aby nie tworzyć dwóch niezgodnych słowników.

## Otwarte prace późniejszych etapów

- Zatwierdzenie metadanych istniejących kanałów i audycji radia w 154.
- Audyt promptów wszystkich aktywnych wydawców w 155. Każdy ma jawne medium
  i politykę językową; nie przenosić automatycznie zasad BN na pozostałe kanały.
- Próby rzeczywistej Ollamy, zgodność narracji z faktami, kolejki/cache/fallback
  oraz koszt generowania News w zatwierdzonych językach.
- Audyt danych historycznych, dry-run migracji i odbiór tłumaczeń. Nie da się
  potwierdzić kompletności historii produkcyjnej na podstawie samego repozytorium.
- Fizyczny Android/iOS i odbiór językowy przed pełnym PASS 155.

Przegląd dotyczył dokumentacji i punktów integracji w kodzie. Nie uruchamiano
testów nieistniejącej jeszcze wersji językowej ani migracji danych produkcyjnych.
