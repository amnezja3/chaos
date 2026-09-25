# Sprint 146.1 — GhostLab: bilety do miejsc świata

Status: **ZAPLANOWANY**, 25 IX 2026. Po bazowym 146.
To rozszerzenie, nie sekcja 146.1 w historycznym planie runtime.
Następny: [146.2 — konserwacja systemu](sprint_146_2_ghostlab_system_maintenance.md).

## Cel i zakres

Twórca branduje bilet i wybiera miejsce z katalogu zatwierdzonego w kodzie;
kupujący korzysta z systemowej logiki podróży. Szablon może istnieć bez pro-toolsa.

- Najpierw zinwentaryzować istniejący travel_ticket, zakup, transport i zużycie;
  wykorzystać istniejące zasady zamiast tworzyć drugi system podróży.
- Zarejestrować kontrakt GLab: branding autora (nazwa, ikona, opis), destination_id,
  dopuszczone warianty prezentacji. Backend rozwiązuje miejsce i uprawnienia;
  opis produktu ani współrzędne klienta nie wyznaczają celu transportu.
- Catalog miejsc i logika dodawane w kodzie. Admin pokazuje szablon i potomstwo
  tak jak dla pozostałych rodzin, bez projektowania mechaniki w panelu.
- Jasno pokazać cel podróży, warunki i liczbę użyć zgodną z systemową polityką.
  Jeśli istniejące bilety nie określają tych reguł, uzgodnić je przed aktywacją.
- Zakup do autora produktu zgodnie ze wspólną księgą; nie mieszać opłaty za
  zakup z ewentualnym kosztem użycia. Brak nowych opłat bez uzgodnienia.
- Transport, kontrola aresztu i zużycie uprawnienia spójne przy awarii/retry;
  odmowa nie może zużyć biletu. Wyłączone miejsce daje czytelny powód.
- Launcher zgodny z kontraktem podróży; bilet nie pojawia się na liście PvP.

## PASS

Autor A publikuje, B kupuje i używa: poprawne miejsce, branding i rozliczenie.
Testy dwóch kart, restartu/retry, aresztu, cofniętego miejsca, braku uprawnienia,
konfiskaty i wersjonowania; brak podwójnego transportu/zużycia/płatności.
Ręczny odbiór desktop/mobile i runbook aktywacji/wyłączenia.

Obowiązuje [zero-heavy](../plans/creator_ghostlab_zero_heavy_profile_contract.md),
także dla odziedziczonego transportu. Wykryte naruszenia naprawiamy w tym etapie.
