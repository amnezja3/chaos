# Sprint 146.2 — GhostLab: konserwacja własnego systemu

Status: **ZAPLANOWANY**, 25 IX 2026. Po [146.1](sprint_146_1_ghostlab_travel_tickets.md).
Następny: [146.3 — firmware](sprint_146_3_ghostlab_firmware_maintenance.md).

## Cel

Systemowe szablony pseudo-konserwacji: czyszczenie zbędnych plików oraz
aktualizacja systemu. Gracz tworzy osobny produkt o jednym celu, z własną
nazwą, ikoną i opisem. To nie Arsenal Cleaner atakujący inną osobę.

## Zakres

- Dwa kontrakty: czyszczenie własnych plików i aktualizacja własnego systemu.
  Reuse rejestru, kreatora, admina i wykonawcy operacji; bez osobnego frameworka.
- Ustalić katalog kwalifikujących się danych gry. Niesprzedawalny plik nie
  oznacza automatycznie pliku do usunięcia. Chronić core, kupione narzędzia,
  pliki aktywnych operacji i wymagane dane gameplayowe.
- Rozdzielić dwa jawne rezultaty: prezentację konserwacji oraz rzeczywiste
  usunięcie zakwalifikowanych plików. Tryb prezentacji nie udaje odzyskanych MB,
  bonusu bezpieczeństwa, przyspieszenia ani instalacji realnych aktualizacji OS.
- Faktyczne czyszczenie, jeśli wybrane do MVP, korzysta z canonical inventory/storage,
  z podglądem zakresu i potwierdzeniem CHAOS; spójny stan FM, dysku i pulpitu.
- „Aktualizacja systemu” dotyczy świata gry. W kodzie określić rezultat i ewentualny
  zapis wersji konserwacji; nie daje ukrytych statystyk ani uprawnień.
- Przed aktywacją zatwierdzić: które rezultaty mają być wyłącznie pokazem,
  które zmieniają stan, cooldown/czas i ewentualne korzyści. Nie zakładać bonusów.
- Aktualizacja systemu w tym szablonie jest inną funkcją niż aktualizacja
  zakupionego artefaktu aplikacji. Interfejs musi odróżniać te działania.
- Cel to własny system, bez listy PvP; obowiązują aktualne ograniczenia aresztu.

## PASS

Oba szablony przechodzą branding → publish → zakup → instalacja → użycie.
Chronione pliki zostają; rzeczywista zmiana odpowiada raportowi. Brak kandydatów
jest poprawnym wynikiem. Retry/restart nie powtarza skutku/opłaty; równoległa
operacja nie traci potrzebnych plików. Demonstracja nie zmienia inventory ani HC.
Admin poprawnie pokazuje potomstwo; testy desktop/mobile i runbook wyłączenia.

Obowiązuje [zero-heavy](../plans/creator_ghostlab_zero_heavy_profile_contract.md).
Nie czytać ani nie modyfikować profile.files; naprawiać naruszenia od razu.
