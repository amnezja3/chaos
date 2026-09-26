# Sprint 152 — GhostLab v2.0: optimizer, zależności, AI/SDK i pełny odbiór

Status: **ZAPLANOWANY**, 26 IX 2026. Po PASS
[151](sprint_151_ghostlab_v2_community_versions.md).
To końcowa bramka GhostLab v2.0, po kreatorach 147–148 i pracach 149–151.

## Cel i granica domknięcia

Domknąć wszystkie pozycje roadmapy zakładek Research, Ghost Exchange i Documentation.
Żadnego PASS przy pozostawieniu którejkolwiek z poniższych funkcji jako coming soon.
Nowe pomysły spoza tej listy nie rozszerzają automatycznie zakresu v2.0.

## 152.1 — Compiler Optimizer

- Jawne profile optymalizacji z kodu, wymagania Research, deterministyczny wynik
  i mierzalny wpływ na parametry produktu. Przed aktywacją ustalić tabelę korzyści
  i kosztów; nie dodawać arbitralnej mocy lub premii do sukcesu.
- Preview porównuje przed/po i wyjaśnia kompromisy. Wynik zapisany w niezmiennym
  artefakcie, rzeczywiście używany przez runtime/instalator. Respektować limity
  rodziny, politykę poziomu gracza i maksymalne możliwości z 147–148.
- Ponowne compile nie kumuluje bonusów. Rollback projektu z 151 daje przewidywalny wynik.

## 152.2 — Dependency Graph

- Graf rzeczywistych zależności: pakiet, szablon, kontrakt, wersja i wymagany unlock.
  Pochodzenie forka pokazywać oddzielnie od zależności wykonawczej.
- Przypięte wersje, wykrywanie cykli, braków, niezgodności i wycofanego kontraktu;
  deterministyczna walidacja przed compile i raport wpływu aktualizacji.
- Żadnego niejawnego pobierania lub wykonywania kodu z zależności. Graf ma
  ograniczenia rozmiaru i czytelny widok mobile, nie jest tylko dekoracją.

## 152.3 — AI Templates i AI Assistant

- Asystent tworzy propozycję brandingu/blueprintu z dozwolonych kontraktów,
  wyjaśnia walidację i sugeruje poprawki. AI Templates są sprawdzonymi propozycjami
  na tym samym modelu projektu, nie osobnym wykonawcą.
- Podgląd różnic i jawne zastosowanie przez twórcę. Brak automatycznej publikacji,
  płatności, przyznawania Research, zmiany polityk i wykonywania kodu modelu.
- Użyć istniejącej infrastruktury AI, po audycie dostępności i kosztów; ograniczony
  kontekst projektu, bez prywatnych wiadomości, sekretów i pełnych profili.
- Timeout, limit wywołań, anulowanie i niedostępność modelu nie psują edytora.
  Testy kontraktu mogą używać stubu; PASS serwerowy wymaga działającej integracji,
  nie statycznego placeholdera. Modelowy wynik przechodzi tę samą walidację serwerową.

## 152.4 — Plugin SDK

- SDK jest kontraktem programistycznym dla logik dodawanych w repo przez zespół,
  zgodnie z decyzją: system dostarcza logikę, gracz ją branduje i konfiguruje.
  Nie jest uploadem dowolnego kodu użytkownika ani edytorem logiki w adminie.
- Manifest i wersjonowanie: GLab/non-GLab, schema/branding, cel, launch, executor,
  Research, zależności, preview, receipt, delty, błędy i wyłączenie funkcji.
- Gotowy szkielet modułu, instrukcja i testy zgodności. Przeprowadzić przykład
  rozszerzenia od rejestracji do wykonania bez dopisywania osobnych ścieżek UI.
  Korzystać z istniejącego wykonawcy testowego, bez dokładania nieuzgodnionego balansu.

## 152.5 — dokumentacja i pełny odbiór

| Obietnica v2.0 | Etap realizacji |
| --- | --- |
| Research Tree | 149 |
| Official Exchange i import | 150 |
| Ghost Exchange Community / Blueprint Sharing | 151 |
| Versioning / Rollback | 151, na istniejących fundamentach 144–145 |
| Compiler Optimizer / Dependency Graph | 152.1–152.2 |
| AI Templates / AI Assistant | 152.3 |
| Plugin SDK | 152.4 |

- UI, tutoriale i Documentation opisują stan rzeczywisty: co robi aplikacja,
  wymagania, ryzyko, wynik, aktualizacja, cofnięcie i zakres uprawnień.
- Usunąć statyczne statusy, martwe przyciski i pozorne procenty. Każda obietnica
  ma ścieżkę w kodzie, test i dowód serwerowy; braki blokują PASS 152.
- Macierz minimum trzech kont i dwóch sesji, desktop/mobile: Research → Official/
  import/Community → fork → AI/propozycja → optimizer → compile → publish → zakup →
  instalacja → rzeczywisty efekt → aktualizacja → przywrócenie → wycofanie.
- Regresja sześciu rodzin PvP, biletów, konserwacji, firmware i kreatorów 147–148;
  areszt, brak uprawnień/środków/miejsca, retry, restart, współbieżność i stare artefakty.
- Osobne flagi funkcji, migracje dry-run/checkpoint, diagnostyka bez treści prywatnych,
  rollback bez cofania legalnych skutków, HC i zakupów. Sprawdzić wydajność na
  dużych katalogach i profilach 35 MB oraz ograniczone koszty AI.

Obowiązuje [zero-heavy](../plans/creator_ghostlab_zero_heavy_profile_contract.md).
Wykryte naruszenie naprawić od razu. PASS 152 oznacza **GhostLab v2.0 zamknięty**,
wyłącznie po odebraniu całej powyższej macierzy i aktualizacji dokumentacji.
