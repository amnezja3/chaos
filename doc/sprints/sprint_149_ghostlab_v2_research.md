# Sprint 149 — GhostLab v2.0: Research i rozwój laboratorium

Status: **ZAPLANOWANY**, 26 IX 2026. Start dopiero po PASS
[148 — kreatory](sprint_148_creator_ux_runtime_completion.md).
Następny: [150 — biblioteka i import](sprint_150_ghostlab_v2_exchange_import.md).
Podstawa: [audyt zakładek](../audits/ghostlab_tabs_scope_2026_09_26.md).

## Cel

Research przestaje być makietą: gracz rozwija laboratorium, odblokowuje konkretne
możliwości kontraktów, tworzy nowy build i obserwuje jego rzeczywisty efekt.
Zakres v2.0 jest domykany przez 149–152; nie zastępuje kreatorów 147–148.

## 149.1 — katalog badań i zasady progresji

- Zmapować Finance, Intel, Security, Social i Apps oraz każdy unlock obecny w UI
  na konkretną funkcję, wymagania, poziomy i limity. Kontrakty dla nowych rodzin
  muszą dać się dodać w kodzie bez przebudowy Research.
- Przed aktywacją ustalić tabelę kosztów, źródeł postępu i progów; nie naliczać
  postępu za odświeżanie, powtarzanie receipt ani własne fikcyjne transakcje.
- Poziom gracza i polityka mocy z 147–148 pozostają nadrzędnymi ograniczeniami.
  Research odblokowuje dozwolone warianty, nie tworzy drugiej sprzecznej macierzy mocy.
- Każdy dawny tekst, np. conflict rule bypass, otrzymuje jawny efekt gameplayowy
  zgodny z regułami serwera albo zostaje zastąpiony nazwanym wariantem. Żaden unlock
  nie omija kontroli własności, aresztu, ochrony core ani księgi HC.

## 149.2 — trwały postęp

- Dedykowany store postępu, wersja polityki, historia przyznania, unikalny receipt
  zdarzenia i atomowa płatność, jeśli badanie jest płatne. Systemowe HC trafiają do admin.
- Obsłużyć częściowy postęp, restart, dwie sesje, retry i jednorazowy unlock.
  Nowe konto zaczyna od jawnego poziomu bazowego; żadnych domyślnych odblokowań
  na podstawie legacy profilu. Migracja istniejących kont ma dry-run i raport.

## 149.3 — compile, artefakt i runtime

- Uprawnienia autora sprawdza backend przy zapisie/compile/publikacji; build zapisuje
  snapshot użytych unlocków i wersję polityki. Kupujący dostaje możliwości produktu,
  ograniczone własnymi wymaganiami uruchomienia; nie dziedziczy badań autora.
- Nowy unlock nie zmienia już opublikowanego ani zainstalowanego artefaktu.
  Zmiana wymaga compile → publish → jawnej aktualizacji. Serwerowy kill switch
  może zablokować niedozwolony kontrakt, ale nie przepisywać historycznego buildu.
- Opisać wpływ zmiany polityki badań na stare produkty i zapewnić czytelną odmowę
  zamiast milczącej utraty lub rozszerzenia funkcji.

## 149.4 — UI i odbiór serwerowy

Research pokazuje rzeczywisty postęp, wymagania, koszt, następny unlock i jego
znaczenie dla kreatora. Nie pokazuje technicznej macierzy ryzyka do ręcznej edycji.
Desktop/mobile: badanie → unlock → zmiana dostępnego wariantu → nowy build →
publikacja → zakup na drugim koncie → wykonanie na trzecim. Stara instalacja
pozostaje niezmieniona. PASS obejmuje retry, brak środków, restart i próbę
podrobienia unlocku. Każda gałąź musi mieć odebraną ścieżkę.

## Bramka jakości

Obowiązuje [zero-heavy](../plans/creator_ghostlab_zero_heavy_profile_contract.md):
wykryte naruszenie naprawić w tym samym etapie. Ograniczone zapytania, paginacja,
brak pełnych profili, delty zakresowe. Aktywacja kontrolowana, instrukcja migracji
i wyłączenia nowych badań bez kasowania postępu i prawidłowych transakcji.
