# Sprint 146.2 — GhostLab: konserwacja własnego systemu

Status: **ZAPLANOWANY**, 25 IX 2026. Po [146.1](sprint_146_1_ghostlab_travel_tickets.md).
Następny: [146.3 — firmware](sprint_146_3_ghostlab_firmware_maintenance.md).

## Cel

Systemowe szablony konserwacji: czyszczenie zbędnych plików,
aktualizacja systemu oraz automatyczne przywracanie zabezpieczeń gracza.
Gracz tworzy osobny produkt o jednym celu, z własną
nazwą, ikoną i opisem. To nie Arsenal Cleaner atakujący inną osobę.

## Zakres

- Trzy kontrakty: czyszczenie własnych plików, aktualizacja własnego systemu
  i automatyczne przywracanie zabezpieczeń własnego konta.
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

## Trzecia grupa — automatyczne przywracanie zabezpieczeń

Dodana decyzją użytkownika. Osobny szablon GLab, który po uruchomieniu
automatycznie przywraca zabezpieczenia własnego konta, np. po ingerencji PvP.
Autor branduje produkt; nie definiuje dowolnych pól profilu ani reguł uprawnień.

- Użyć canonical security store i istniejącej macierzy konfliktów zabezpieczeń.
  Przywracanie nie oznacza włączenia wszystkich przełączników, w tym wzajemnie
  sprzecznych. Nie przyznawać niedostępnych graczowi funkcji ani uprawnień.
- Punkt odniesienia zatwierdzony przez użytkownika: systemowe zestawy
  **OPEN, LOW, REGULAR, ALL**. Użyć istniejących definicji presetów i ich reguł;
  nie dodawać SECURE do tej grupy. Wybrany zestaw musi być jawny przed operacją.
  Nie odtwarzać historycznej konfiguracji gracza ani nie czytać ciężkiego profilu.
  ALL również respektuje systemową macierz konfliktów i dostępne uprawnienia.
- Operacja sprawdza wersję aktualnych zabezpieczeń przed zapisem. Równoległa
  zmiana przez gracza lub Proxy nie może zostać po cichu nadpisana starym stanem.
- Raport pokazuje faktycznie przywrócone ustawienia, brak potrzebnych zmian
  albo powód odmowy. Stan własnego panelu zabezpieczeń synchronizuje się po zapisie.
- Ustalić czas działania i cooldown razem z pozostałymi grupami. Automatyczne
  przywrócenie po uruchomieniu nie oznacza stałej ochrony w tle ani odporności
  na następne ataki; taki tryb wymagałby osobnego ustalenia.

## PASS

Wszystkie trzy szablony przechodzą branding → publish → zakup → instalacja → użycie.
Chronione pliki zostają; rzeczywista zmiana odpowiada raportowi. Brak kandydatów
jest poprawnym wynikiem. Retry/restart nie powtarza skutku/opłaty; równoległa
operacja nie traci potrzebnych plików. Demonstracja nie zmienia inventory ani HC.
Admin poprawnie pokazuje potomstwo; testy desktop/mobile i runbook wyłączenia.

Dla przywracania zabezpieczeń: każdy z OPEN/LOW/REGULAR/ALL po ingerencji PvP, zachowanie
macierzy konfliktów i uprawnień, zgodność raportu z panelem, brak zmian gdy stan
jest już prawidłowy, odmowa nadpisania równoległej zmiany oraz bezpieczny retry.

Obowiązuje [zero-heavy](../plans/creator_ghostlab_zero_heavy_profile_contract.md).
Nie czytać ani nie modyfikować profile.files; naprawiać naruszenia od razu.
