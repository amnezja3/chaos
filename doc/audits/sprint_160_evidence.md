# Sprint 160 — macierz dowodów

2026-10-18. Status: realizacja lokalna, bez pełnego PASS i wdrożenia. [Plan wykonawczy](../sprints/sprint_160_poi_world_repository_provider_control.md), [koncepcja](../prototypes/poi/sprint_160_poi_world_repository_provider_control.md), [kontrakt i wyniki](sprint_160_0_contract_baseline.md).

| Etap | Status | Dowód do uzupełnienia |
| --- | --- | --- |
| 160.0 | W toku | Operator dostarczył sześć niezależnych odpowiedzi Overpass 0.7.62.3 na syntetycznym OSM; hash wejścia i zapytania zgodne. [Dowód geometrii](sprint_160_geometry_reference.md). |
| 160.1 | Częściowo zaimplementowane | Exact snapshoty i membership, fencing w tej samej bazie, backup/restore: 7 testów PASS. Brak certyfikacji przestrzennej i pełnego odbioru rozmiaru/WAL. |
| 160.2 | Lokalna integracja PASS w przetestowanym zakresie | Referencja wide z VPS, zgodność pięciu sąsiednich skanów i fasady. Jeden fill dla czterech procesów, wspólny deadline/próby z exact fallback, scope i anulowanie. Nowe flagi OFF; szerszy zakres geometrii i pilotaż pozostają otwarte. |
| 160.3 | W toku | Registry, scope, rewizje, audyt, admin PL/EN i CSRF; bez zatwierdzonych produkcyjnych źródeł. Pełny TLS/rebinding i multiworker do domknięcia. |
| 160.4 | W toku | Historia rzeczywistego transportu, ograniczony probe i monitor tick; agregaty i pełny odbiór do domknięcia. |
| 160.5 lokalnie | Do realizacji | W07/U01 i komplet regresji 158/159. |
| 160.5 produkcyjnie | Do realizacji | O01: kontrolowany rollout, restart/restore, metryki, rollback i odbiór operatora. |

Operator potwierdził wizualny PASS 159. Zgłoszony brak odpowiedzi endpointów Overpass nie jest potwierdzeniem przyczyny ani globalnej awarii. Nie wykonano w ramach planowania 160 zapytań do dostawców, zmian konfiguracji, migracji ani wdrożenia. Status VK Maps z koncepcji pozostaje kandydatem POLICY_PENDING; nie nadano żadnej zgody na ruch.

Pierwsza regresja pakietu: `test_poi*.py` 47 PASS (36,316 s), w tym nowe testy repozytorium, rejestru i endpointu admina. Kolejne zmiany wymagają aktualizacji wyniku. Dry-run `tools/poi_world.py`: integrity/foreign keys OK, źródło niezmienione. Narzędzia nie aktywują flag. Bieżący kod nie jest jeszcze kompletnym pakietem wdrożeniowym 160.

Po przyjęciu referencji VPS: `test_poi*.py` **61 PASS (63,694 s)**, w tym 9 testów
geometrii/pokrycia i trwałości. W pakiecie także testy przypiętego IP/TLS i odczytu
zmiany konfiguracji przez cztery istniejące procesy. `git diff --check` bez błędów.
Weryfikacja UI z poprzedniego etapu pozostaje osobnym dowodem; ta zmiana nie
modyfikowała UI i nie wykonywano ponownego testu przeglądarkowego.

## Integracja wide i przygotowanie pierwszego wdrożenia

- Najnowsza regresja: **69 testów PASS (65,309 s)**; zastępuje wcześniejsze liczby
  jako wynik bieżącego pakietu. Cztery procesy startują równolegle i wykonują
  cztery różne skany, transport jest wywołany dokładnie raz.
- Po wyłączeniu providera i odtworzeniu obiektu Service sąsiednie skany nadal
  zwracają identyczne dane lokalnie bez dodatkowego HTTP.
- Sprzątanie wygasłych snapshotów kaskaduje membership/coverage; aktywne dane
  pozostają czytelne. Odczyt wybiera pokrycie przed wczytaniem payloadu.
- Ponownie wykonano Playwright `tests/browser/poi_admin.js`: PL/EN, 1440/390,
  zapis kandydata, odmowa niezatwierdzonej aktywacji przy przycisku, brak overflow,
  20 odświeżeń bez nowych probe; pageErrors puste. HTTP 400 jest oczekiwanym
  wynikiem celowej próby niedozwolonej aktywacji. Przeglądarkę i fixture zamknięto.
- Dry-run aktualnego schematu: integrity/foreign_keys OK, źródło niezmienione.
- [Runbook](../runbooks/poi_world_repository_160.md) gotowy dla pierwszego
  kontrolowanego wdrożenia z flagami OFF. Nie wykonano commita, pusha ani deploya.
- To nie zamyka pełnego 160: zatwierdzenie rzeczywistych źródeł, pilotaż,
  produkcyjne metryki, rozszerzenia panelu/monitoringu i pełny odbiór są otwarte.
