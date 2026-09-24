# Audyt kreatorów gameplayowych — 24 IX 2026

Zakres: Window Maker, AppForge, Button Maker, Term Creator. Przegląd lokalnego
kodu i historii UX, siedem istniejących testów oraz izolowana diagnostyka helperów.
Bez zmian runtime, wdrożenia i testowania kont produkcyjnych.

## Wniosek

Wspólny wizard i cztery formy prezentacji istnieją. Poprzedni refaktor celowo
nie zmieniał mechaniki gameplayowej. Obecne wymaganie jest zmianą kontraktu
backendu, a następnie uproszczeniem formularzy — samo ukrycie przełączników
pozostawiłoby stare możliwości w API.

Plany wykonawcze: [147 — kontrakt i polityka backendu](../sprints/sprint_147_creator_gameplay_policy.md)
oraz [148 — interfejs, opłaty i odbiór](../sprints/sprint_148_creator_ux_runtime_completion.md).

## Co istnieje

| Obszar | Ustalenie |
| --- | --- |
| Wspólny wizard | Dziewięć kroków, selektory rodziny/celu/startu/akcji, preview i publikacja. |
| Wspólny backend | `/api/apps/generate` → `build_generated_app` → katalog; instalator i launcher wspólne z innymi aplikacjami. |
| AppForge | `progressbar_random`: kroki i teksty wyniku; odrębne od rzeczywistego skutku backendu. |
| Window Maker | `window`: tytuł, logi/lista, przyciski; `close` zamyka, `run_generated` uruchamia domyślną akcję. |
| Button Maker | `button_choices`: tytuł, tekst, opcje zawierające label/effect/price. |
| Term Creator | `terminal`: wiele par command/logs; renderer już losuje jedną parę i animuje wpisywanie. |

Źródła: `static/js/terminal.js:13142`, `:14086`, `:14361–14462`,
`:5006`, `:8514`, `:8620`; `run.py:19868`, `:28929`.
Historia: `doc/plans/Refaktor_UX_creatorów_CHAOS.md` odsyła do
`130.8.9.UX-appcreator.1–3` i jawnie wyklucza zmianę mechaniki runtime.

## Ustalenia do rozstrzygnięcia w implementacji

### A. Kontrakt dopuszcza wiele niezależnych możliwości

`run.py:19753–19835`: allowlisty rodzin kontrolują przynależność elementów,
ale wymagają tylko co najmniej jednego celu i operacji. Nie wymuszają jednego
przeznaczenia ani pełnej zgodności kombinacji akcja → operacja → zasób → cel.
Rodzina custom/niepodana wraca bez tej walidacji. Wybór family/mode nie jest
jeszcze zamkniętym przepisem gameplayowym.

Wniosek: wprowadzić jeden wersjonowany profil działania wybierany z backendowego
katalogu. Grupa „obiekty świata” może mapować się na kilka zgodnych technicznych
typów, ale nie daje przy okazji kamery, pojazdu, mikrofonu i gracza.

### B. Macierz „ryzyka” miesza warunki, skutki i parametry

`static/js/terminal.js:14162–14167` nadal pozwala ręcznie ustawiać
`interferes_with`, `requires_off`, `disables`, `affects` z tego samego zbioru kluczy.
Builder (`run.py:19868`) zapisuje dostarczone listy. UI opisuje `interferes_with`
jako przeszkody, a gałąź wykonania (`run.py:30886`) po spełnieniu `requires_off`
ustawia te zabezpieczenia na False. To konkretna rozbieżność semantyczna.

Wymagane: backend wyprowadza warunki, moc, efekty i profil ekspozycji z poziomu
autora i jednego celu aplikacji. UI pokazuje opis, nie edycję wewnętrznej macierzy.
Ryzyko konkretnego użycia nadal zależy od celu i aktualnego świata, np. kamer.

### C. Obecna moc nie jest wyłącznie funkcją poziomu

`calculate_creator_power` (`run.py:11519`) używa
`20 + level*2 + respect/25 + min(12, HC/10000)`, z ograniczeniem do 100.
Quality/reliability są liczone osobno i uwzględniają także złożoność aplikacji.

Potwierdzono helperem: poziom 1, respekt 0, HC 0 → moc 22;
poziom 1, respekt 2500, HC 200000 → moc 100; poziom 40 bez dodatkowych zasobów → 100.
Obecna formuła nie spełnia nowej zasady odblokowywania możliwości przez poziom.
Zmiany nie należy rozlać przypadkowo na GhostLab i inne systemy używające helpera.

### D. `price` przycisku nie ma potwierdzonej ścieżki transferu

`parse_option_lines` (`run.py:19734`) zapisuje integer bez zakresu.
W sprawdzonej gałęzi `choice_id` (`run.py:30900`) backend stosuje effect, ale
nie odczytuje ceny opcji ani nie wykonuje z niej przelewu do autora.
Renderer (`static/js/terminal.js:8620`) pokazuje label bez kwoty.
Istniejący transfer przy zakupie aplikacji jest osobnym mechanizmem.

Diagnostyka buildera potwierdziła zapis ceny -5 i 999999999 oraz efektu
`access_level=9999`. Nie jest to dowód wykonania takiej wartości na produkcji;
pokazuje brak ograniczeń na etapie budowania opcji. Parser efektów przyjmuje
dowolny klucz, a sprawdzona gałąź wykonawcy kopiuje go do security celu.

Wymagane: allowlista efektów/pól i zakresów zależna od profilu działania,
serwerowa wycena opcji, jawna cena przed użyciem, atomowy lub odzyskiwalny zapis
efektu i płatności, jednokrotne obciążenie mimo retry.

### E. Cena katalogowa zero nie oznacza obecnie darmowej aplikacji

`enforce_generated_app_price_floor` (`run.py:11697`) stosuje
`max(current_price, price_hint)` także dla zera. W diagnostyce cena 0 została
zmieniona na 280 HC. To odrębna cena od ceny użycia przycisku.
Nowy kontrakt musi zachować 0 jawnie oraz niezależnie opisać obie opłaty.

### F. Akcje Window Makera są surowymi identyfikatorami

Pole action jest tekstowe; renderer specjalnie obsługuje `close`, a wykonawca
normalizuje `run_generated` do działania domyślnego. Inne wartości są wysyłane
jako choice_id, co nie stanowi kompletnego katalogu akcji Window Makera.
Nie znaleziono `rank_generated` w przeszukanym kodzie i dokumentacji tych ścieżek.
Najbliższy istniejący identyfikator to `run_generated`; nie należy przypisywać
nieznanej fladze efektu rangi lub nagrody.

### G. Pasek 100% i sukces aplikacji mają różne znaczenia

`database.py:13392` liczy disarm progress z wyłączonych wartości boolean security.
Kropki dostępnych akcji są celowo oddzielne. Sprawdzona gałąź przejęcia
`run.py:31000` używa progu 70% krytycznych zabezpieczeń oraz czterech dostępnych
akcji. Uruchomienie operacji może zwrócić sukces bez przejęcia celu.

To wyjaśnia, dlaczego „wszystkie checkboxy” nie są kontraktem pełnego przejęcia.
Nie odtworzono konkretnego przypadku zgłoszonego przez autora; dokładna przyczyna
niedojścia paska do 100% wymaga testu na kontrolowanym celu. Nie naprawiać tego
samym ustawieniem paska na 100. Level 40 oznacza pełny dopuszczony wpływ narzędzia
w jego celu, a nie automatyczne przejęcie wszystkiego przez dowolną aplikację.

### H. Publikacja nadal ma legacy zapis

`/api/apps/generate` aktualizuje całą listę app_config, potem osobno files profilu.
W planie uwzględnić idempotencję, współbieżność i wznowienie przerwanej publikacji;
wykorzystać rozwiązania Sprintu 144, bez kopiowania osobnego Publishera.

## Wykonana weryfikacja

Uruchomiono przez izolowany runner siedem metod `TargetPersistenceHelpersTest`:

- PASS: `test_creator_rejects_contract_outside_selected_family`.
- PASS: `test_generated_app_quality_depends_on_creator_power`.
- PASS: `test_generated_app_price_uses_balance_floor` (potwierdza starą regułę).
- FAIL: cztery `test_*_generated_app_keeps_*_runtime_content` dla Button Maker,
  Term Creator, Window Maker i AppForge, wszystkie na instalacji: HTTP 409 zamiast 200.

Ponowiony test Button Makera z odczytem odpowiedzi wskazał
`payment_recipient_unavailable` — brak odbiorcy płatności w tym izolowanym scenariuszu.
Nie dowodzi to awarii czterech kreatorów na produkcji. Testy nie dotarły do końcowej
weryfikacji command/launch; wymagają fixture z rzeczywistym odbiorcą canonical wallet.
Nie obchodzono bramki płatniczej i nie oznaczono tych testów jako PASS.

Diagnostyka cen, poziomu i parsowania odbyła się w osobnym procesie po zmianie cwd
na katalog tymczasowy. Nie zmieniono kodu gry ani produkcyjnych sald.
