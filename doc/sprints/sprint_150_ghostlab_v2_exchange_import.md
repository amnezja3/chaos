# Sprint 150 — GhostLab v2.0: Official Exchange, pakiety i import

Status: **ZAPLANOWANY**, 26 IX 2026. Po PASS
[149](sprint_149_ghostlab_v2_research.md); następny [151](sprint_151_ghostlab_v2_community_versions.md).

## Cel

Ghost Exchange w laboratorium staje się działającą biblioteką zasobów.
Pozostaje odrębny od rynku danych Ghost Exchange w Web Dragonie i od sprzedaży
gotowych aplikacji w Googleplexie. Eksport `.glab` otrzymuje pełną ścieżkę importu.

## 150.1 — katalog Official i kontrakt pakietu

- Zastąpić statyczne karty katalogiem z rejestru kodu: szablony, blueprinty,
  profile walidacji i dokumentacja. Lista pokazuje rzeczywisty stan dostępności,
  wersję, zgodność i wymagania Research, a nie stałe installed/active.
- Manifest: ID, wersja, źródło, kontrakt/schemat, zależności, minimalna wersja
  laboratorium i integralność. Pakiet dostarcza dane; wykonawca nadal pochodzi z kodu.
- Official i przyszłe Community używają jednego modelu pakietu i instalacji.
  Nowa logika nadal wymaga implementacji w repo i jawnego GLab/non-GLab.

## 150.2 — pobieranie i aktualizacje

- Pobranie tworzy projekt lub zasób biblioteki zgodnie z typem pakietu;
  nie instaluje automatycznie aplikacji gameplayowej. Jasne etykiety przycisków.
- Jawna aktualizacja, porównanie wersji, kompatybilność i przypięte zależności.
  Nie nadpisywać własnych edycji: aktualizacja tworzy nową rewizję lub nowy projekt
  po wyborze użytkownika. Retry nie tworzy duplikatu i nie mnoży pobrań.
- Wycofany pakiet znika z nowych pobrań; istniejące projekty i zainstalowane
  aplikacje zachowują ważne artefakty. Osobno obsłużyć wyłączenie wadliwego kontraktu.

## 150.3 — export → import

- Limit rozmiaru, wersji schematu, liczby pól i zagnieżdżeń. Migratory obsługiwanych
  formatów, raport błędów, podgląd przed importem. Nie wykonywać tekstu jako kodu.
- Import tworzy nową tożsamość projektu i przypisuje właściciela z sesji.
  Nie importuje uprawnień Research, publikacji, receipts, sald ani cudzych ID instalacji.
- Zachować deklarowane pochodzenie jako informację; plik nie jest dowodem autorstwa
  lub certyfikacji Official. Branding i blueprint podlegają bieżącej walidacji.
- Brak unlocku pozwala obejrzeć projekt z wyjaśnieniem, ale nie obchodzi bramki compile.

## 150.4 — odbiór

Desktop/mobile: Official → pobranie → edycja → export → import na drugim koncie →
compile → publish → zakup/użycie. Sprawdzić stare formaty, uszkodzony i zbyt duży plik,
nieznany kontrakt, brak Research, kolizję nazwy, retry, aktualizację zmodyfikowanego
projektu i wycofanie zasobu. PASS wymaga rzeczywistego działania biblioteki.

Obowiązuje [zero-heavy](../plans/creator_ghostlab_zero_heavy_profile_contract.md),
naprawa naruszeń od razu, paginowane katalogi, atomowe zapisy i ograniczone delty.
Runbook zawiera kopię, dry-run migracji, aktywację i rollback bez utraty projektów.
