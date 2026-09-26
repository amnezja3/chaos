# Sprint 151 — GhostLab v2.0: Community, współdzielenie i wersje

Status: **ZAPLANOWANY**, 26 IX 2026. Po PASS
[150](sprint_150_ghostlab_v2_exchange_import.md); następny [152](sprint_152_ghostlab_v2_completion.md).

## Cel

Twórca udostępnia blueprint, drugi gracz tworzy jego własną wersję, rozwija ją
w ramach swoich uprawnień i publikuje produkt z zachowanym pochodzeniem.
Historia i przywracanie wersji stają się funkcjami użytkowymi.

## 151.1 — publikacja Community

- Pakiety na kontrakcie 150; autor, opis, ikona, data, wersja, pobrania,
  kompatybilność, wymagania i warunki użycia. Wyszukiwanie i paginacja.
- Zdefiniować warunki udostępnienia i dalszej publikacji przed aktywacją.
  Oddzielić pobranie blueprintu od zakupu aplikacji. Nie dodawać automatycznie
  tantiem ani opłat; ewentualna ekonomia wymaga jawnej polityki i księgi.
- Własność z backendu, sprawdzanie uprawnień przy każdej zmianie, zgłoszenie
  nadużycia, moderacja i wycofanie z biblioteki. Treści graczy renderować jako dane.

## 151.2 — Blueprint Sharing i fork

- Udostępnienie nie publikuje prywatnych draftów lub całej historii projektu.
  Fork wskazuje konkretny artefakt źródłowy, daje nowe ID i własne rewizje.
- Autor źródła i autor potomka są rozróżnieni. Nie pozwalać podmienić pochodzenia
  ani odbiorcy HC cudzej aplikacji. Nowy twórca ustala własne dozwolone branding/opis.
- Wycofanie udostępnienia nie usuwa prawidłowych wcześniejszych forków i instalacji;
  blokada wykonawcy jest osobnym mechanizmem. Zachować zgodność warunków licencji.
- Import, fork i aktualizacja nie przenoszą odblokowań Research.

## 151.3 — Versioning i Rollback

- Rozszerzyć istniejące rewizje i buildy o czytelne porównanie blueprintu,
  brandingu, zależności i wymagań. Nie budować drugiego systemu wersjonowania.
- Przywrócenie starej wersji projektu tworzy nową rewizję; wymaga walidacji,
  compile i publikacji. Niezmienne artefakty oraz historia transakcji pozostają.
- Aktualizacja instalacji jest jawna. Przywrócenie projektu nie podmienia cudzego
  produktu ani nie resetuje cooldownów/limitów rodziny. Wyjaśnić różnicę między
  wersją pakietu, projektu, buildu, instalacji i polityki.

## 151.4 — odbiór

Trzy konta: autor → fork → kupujący; desktop/mobile. Potwierdzić pochodzenie,
uprawnienia, pojedyncze pobranie przy retry, konflikt dwóch edycji, przywrócenie
wersji, wycofanie, moderację, odmowę podrobionego autorstwa i brak resetu limitów.
Zweryfikować pełny ciąg Community → fork → Research/compile → Googleplex → runtime.

Obowiązuje [zero-heavy](../plans/creator_ghostlab_zero_heavy_profile_contract.md),
naprawa w bieżącym etapie, małe store/projekcje, indeksy i paginacja. Wymagany
runbook aktywacji oraz rollback bez usuwania pochodzenia i wykonanych płatności.
