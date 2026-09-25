# Sprint 146.3 — GhostLab: konserwacja firmware i domknięcie nowych szablonów

Status: **ZAPLANOWANY**, 25 IX 2026. Po [146.2](sprint_146_2_ghostlab_system_maintenance.md).
Następny: [147 — polityka kreatorów](sprint_147_creator_gameplay_policy.md).

## Cel i zakres

- Szablon pseudo-aktualizacji firmware z logiką dostarczaną w kodzie oraz
  własnym brandingiem potomka. Wykorzystać model konserwacji z 146.2.
- Proponowane MVP: własny sprzęt/system w grze. Przed implementacją ustalić
  konkretny typ celu; rozszerzenie na cudze urządzenia wymaga osobnego kontraktu
  dostępu, nie wynika automatycznie ze słowa „firmware”.
- Dozwolone profile urządzeń i pakiety/wersje definiuje system. Twórca wybiera
  wyłącznie warianty kontraktu. Brak dowolnych komend, binariów i wykonywalnego
  kodu gracza. Nie aktualizujemy rzeczywistego sprzętu użytkownika.
- Jawnie określić, czy rezultat jest prezentacją czy zapisanym stanem gameplayu.
  Nie przyznawać domyślnie pojemności, mocy skanu, odporności ani lepszej wydajności.
  Wersja firmware celu jest odrębna od wersji artefaktu narzędzia i kontraktu.
- Jeżeli rezultat zmienia stan, canonical rekord urządzenia/własnego systemu,
  kontrola zgodności i wersji oraz idempotentny commit. Brak danych daje odmowę,
  bez fallbacku ciężkiego profilu lub wymyślania urządzenia.
- Zachować zasady instalacji, rozliczeń, ograniczeń aresztu i limitów rodziny.
- Domknąć instrukcję dodawania kolejnych szablonów na przykładach biletu,
  czyszczenia, aktualizacji systemu i firmware, wraz z widokiem potomstwa w adminie.

## PASS

Potomek zachowuje ikonę/opis autora i prawidłowo działa tylko na kwalifikującym
się celu. Niekompatybilny wariant nie daje sukcesu. Retry/reconnect oraz dwa
produkty tej samej rodziny nie powielają skutku ani obchodzą limitu.
Regresje sześciu rodzin PvP i trzech nowych etapów; podział launcherów na
PvP/podróż/własny system. Raport realnych skutków oddzielony od pokazów.
Zatwierdzony zakres efektu i balans wymagane przed aktywacją, runbook i odbiór UI.

Rozszerzenia dysku i skanery markerów/awatarów pozostają kandydatami następnych
etapów; te trzy sprinty ich nie implementują ani automatycznie nie włączają.
Obowiązuje [zero-heavy](../plans/creator_ghostlab_zero_heavy_profile_contract.md);
naprawy naruszeń są częścią tego etapu, nie odroczonym długiem.
