# GhostLab — zakładki a zakres 146

Audyt kodu i planów, 26 IX 2026. Bez uruchamiania mechanik lub zmiany balansu.

## Wniosek

146 domyka wykonanie sześciu rodzin narzędzi, nie pełną wizję laboratorium.
Audyt z 24 IX zauważył Research/Community i jawnie wyłączył je z pierwszego
domknięcia. Brakowało przypisania tej odłożonej ścieżki do dalszych prac.
Nie ma podstaw do nazywania jej już zaimplementowaną, jedynie wyłączoną funkcją.

Źródła: `static/js/terminal.js` — GHOSTLAB_ROADMAP, GHOSTLAB_V2_ROADMAP,
GHOSTLAB_RESEARCH_BRANCHES, GHOSTLAB_EXCHANGE_OFFICIAL, renderGhostLabTab,
renderGhostLabResearchBranchDetail; `ghostlab_routes.py`, `ghostlab_store.py`,
`ghostlab_policy.py`; `doc/gameplay/action_player.md`, historyczne sprinty 23–25.
Historyczny sprint 24 wprost zakładał Research bez mechaniki.

| Obietnica w UI | Stan obecny | Pokrycie w 146 |
| --- | --- | --- |
| Finance / Intel / Security / Social / Apps | Stałe locked, tier=0, progress=0; kliknięcie pokazuje opis. Brak trwałego postępu i unlocków. | Nie |
| Unlocki zmieniające możliwości narzędzi | Listy tekstów, bez integracji z uprawnieniami compile/runtime. | Nie; 146 tylko interpretuje obecne blueprinty |
| Official w Ghost Exchange | Cztery statyczne karty; brak pobierania lub aktualizowania pakietów w tej zakładce. Rejestr Templates działa osobno. | Tylko ogólna aktualizacja dokumentacji |
| Community / Blueprints / Templates w Exchange | Przyciski informacyjne v2, bez wymiany. | Nie |
| Export / Blueprint Sharing | Eksport JSON istnieje; brak importu `.glab`, forkowania i pochodzenia współdzielonego projektu. | Nie |
| Versioning | Rewizje projektów, niezmienne buildy, wersja instalacji i jawna aktualizacja już istnieją. | Reuse; nie cała pozycja roadmapy jest brakująca |
| Rollback | Wyłączenie runtime opisane operacyjnie; brak przywracania wersji projektu w UI. | Brak produktowego rollbacku |
| Compiler Optimizer / Dependency Graph | Roadmapa, bez wykonawców tych funkcji. | Nie |
| AI Templates / AI Assistant / Plugin SDK | Roadmapa, brak ścieżki funkcjonalnej w badanym module. | Nie |

Ghost Exchange w przeglądarce (`/api/ghost-exchange`) obsługuje rynek danych.
Nie stanowi implementacji biblioteki społecznościowej GhostLaba o tej samej nazwie.

## Niespójności opisów do naprawienia w 146

- `GHOSTLAB_VERSION_NAME` nadal mówi Runtime Pending, mimo odbioru Sysloga.
- Official/Runtime Roadmap opisuje cały custom runtime jako przyszły.
- Documentation opisuje wszystkie Pro System Tools jako wymagające Player Hack
  Access. Wymaganie powinno wynikać z kontraktu; bilety i konserwacja są wyjątkami.
- `ghostlab_policy.validate_ghostlab_blueprint` ma stałe preview
  `Player Hack Access / runtime pending`, niezależne od kontraktu szablonu.
- Oznaczenia done dla Exchange i Research Foundation dotyczą wyłącznie podstaw UI;
  trzeba to nazwać wprost, bez sugerowania gotowej mechaniki.

## Brakująca ścieżka rozwoju — propozycja do osobnego zaplanowania

1. Research: serwerowy katalog gałęzi i odblokowań, trwały postęp i warunki zdobycia;
   powiązanie uprawnień autora z walidacją/compile oraz wersją artefaktu.
   Rozstrzygnąć wpływ późniejszego unlocku na stare buildy i cudze instalacje.
2. Official Exchange i import: zasoby z rejestru, wersjonowanie, walidowany import
   wyłącznie danych projektu do nowej tożsamości; bez importowania autorstwa,
   publikacji, receipts ani uprawnień. Pełna ścieżka export → import → edycja → build.
3. Community i rozwój wersji: udostępnienie blueprintu, fork, pochodzenie i autorstwo,
   wycofanie udostępnienia, historia i przywrócenie jako nowa rewizja.
   Reguły licencji i wynagrodzenia wymagają projektu przed implementacją.
4. Optimizer i zależności: określić mierzalny efekt i kompatybilność, zamiast samego
   procentu jakości lub dekoracyjnego grafu. AI/SDK pozostają osobnymi tematami.

Decyzja użytkownika z 26 IX: realizacja jako **GhostLab v2.0, sprinty 149–152**,
dopiero po PASS kreatorów 147–148. Plany:
[149](../sprints/sprint_149_ghostlab_v2_research.md),
[150](../sprints/sprint_150_ghostlab_v2_exchange_import.md),
[151](../sprints/sprint_151_ghostlab_v2_community_versions.md),
[152](../sprints/sprint_152_ghostlab_v2_completion.md).
152 obejmuje także AI Templates, AI Assistant i SDK, aby domknąć całą roadmapę.
Tabela kosztów/progów badań i efektów optymalizacji pozostaje do ustalenia przed aktywacją.
Nie zajmują 146.1–146.3, które są już przypisane biletom i konserwacji.
Wszystkie wymagają małych canonical stores, zero-heavy, wersjonowanych kontraktów
i odbioru desktop/mobile, łącznie z odmowami, retry i uprawnieniami.

Teksty `conflict rule bypass`, `wallet anomaly bypass`, `recovery blocker` są
pomysłami z roadmapy, nie zgodą na ominięcie serwerowych zabezpieczeń, aresztu,
księgi HC lub ochrony core. Ich przyszły efekt gameplayowy trzeba określić jawnie.

146 może otrzymać PASS jako runtime obecnych rodzin; nie zamyka Research,
Exchange Community ani całej wizji GhostLaba. Ustalona kolejność:
146 → 146.1–146.3 → 147 → 148 → 149 → 150 → 151 → 152.
