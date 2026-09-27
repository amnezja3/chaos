# Sprint 146.2 — GhostLab: konserwacja własnego systemu

Status: **PAKIET DO WDROŻENIA — ODBIÓR W GRZE DO WYKONANIA**, 27 IX 2026. Po [146.1](sprint_146_1_ghostlab_travel_tickets.md).
Następny: [146.3 — firmware](sprint_146_3_ghostlab_firmware_maintenance.md).

Implementacja: `file_cleanup`, `system_update`, `security_restore`. Wspólna flaga
`CHAOS_GHOSTLAB_MAINTENANCE_RUNTIME_ENABLED=true`; aktualna lista runtime `*` obejmuje wszystkich graczy.
Instrukcja wdrożenia, mapowanie kategorii i testy: [runbook 146.2](../runbooks/sprint_146_2_ghostlab_maintenance.md).
Bez dodatkowej opłaty i cooldownu za uruchomienie; zakup/instalacja według istniejącej polityki aplikacji.
Animacja ma etapy po 600 ms: 4 logi aktualizacji (maks. 180 znaków każdy), 2 etapy pozostałych operacji.
Zmiany przygotowane lokalnie, bez commita i pusha przez agenta.

## Cel

Systemowe szablony konserwacji: czyszczenie zbędnych plików,
aktualizacja systemu oraz automatyczne przywracanie zabezpieczeń gracza.
Gracz tworzy osobny produkt o jednym celu, z własną
nazwą, ikoną i opisem. To nie Arsenal Cleaner atakujący inną osobę.

## Zakres

- Trzy kontrakty: czyszczenie własnych plików, aktualizacja własnego systemu
  i automatyczne przywracanie zabezpieczeń własnego konta.
  Reuse rejestru, kreatora, admina i wykonawcy operacji; bez osobnego frameworka.
- Czyszczenie łączy animację z rzeczywistym usuwaniem zakwalifikowanych plików.
  Aktualizacja systemu jest prezentacją z paskiem postępu i logami autora.
  Przywracanie zabezpieczeń rzeczywiście ustawia istniejący systemowy zestaw.
- Aktualizacja systemu w tym szablonie jest inną funkcją niż aktualizacja
  zakupionego artefaktu aplikacji. Interfejs musi odróżniać te działania.
- Cel to własny system, bez listy PvP; obowiązują aktualne ograniczenia aresztu.

## Pierwsza grupa — czyszczenie własnych plików

- Twórca wybiera z systemowej listy typy plików czyszczonych przez jego produkt.
  Zakres wskazany przez użytkownika: pozostałości skanów kamer i obiektów,
  Reconu, zbędne pliki systemowe oraz niepotrzebne instalki. Podczas implementacji
  przypisać te etykiety do rzeczywistych typów danych gry; autor nie podaje
  dowolnych ścieżek, komend ani reguł kasowania.
- Plik kwalifikuje się tylko wtedy, gdy należy do wybranego typu, nie można
  go sprzedać ani w Googleplexie, ani w Ghost Exchange i nie jest chroniony.
  Sprawdzać rzeczywistą możliwość sprzedaży, a nie sam brak wystawienia oferty.
- Chronić core, kupione/zainstalowane narzędzia, dane aktywnych operacji i dane
  wymagane przez gameplay. „Pliki systemowe” oznaczają zbędne artefakty gry,
  nie niezbędne składniki systemu. Instalator nie oznacza zainstalowanej aplikacji.
- Animacja towarzyszy faktycznej operacji w canonical inventory/storage.
  Podgląd zakresu i potwierdzenie CHAOS poprzedzają usunięcie; raport pokazuje
  rzeczywiście usunięte pliki i zwolnioną przestrzeń. FM i zajętość dysku
  synchronizują się z wynikiem serwera.
- Stan wynika z trwałego inventory i zapisu operacji. Po usunięciu wszystkich
  kandydatów kolejne uruchomienie bez nowych plików zwraca komunikat:
  **„System jest już czysty — nie ma czego usuwać.”** Nie powtarzać raportu
  poprzedniego czyszczenia jako nowego skutku ani fikcyjnie odzyskanych MB.
- Nowe kwalifikujące się pliki ponownie podlegają czyszczeniu; jednorazowa flaga
  „wyczyszczono” nie może blokować przyszłych operacji. Retry tego samego żądania
  zwraca jego zapisany wynik, a nowe uruchomienie sprawdza aktualny stan.
- Przed usunięciem ponownie sprawdzić kwalifikację. Plik, który w międzyczasie
  stał się sprzedawalny, chroniony lub potrzebny aktywnej operacji, musi pozostać.

## Druga grupa — prezentacja aktualizacji systemu

- Prosty pasek progresu z etapami pobierania i instalowania aktualizacji w grze.
- Twórca przygotowuje kilka własnych logów wyświetlanych podczas prezentacji.
  Są to teksty z ograniczeniami długości/liczby i bezpiecznym renderowaniem,
  nie wykonywalny kod, HTML ani polecenia systemowe.
- Efektem jest zakończenie prezentacji. Brak bonusów do parametrów, zmian plików,
  zabezpieczeń i instalacji rzeczywistych aktualizacji systemu operacyjnego.
- Nie mylić tego przebiegu z aktualizacją wersji zakupionego produktu ani
  z ryzykownym firmware'em i trwałymi ulepszeniami z 146.3.

Czasy animacji i ewentualne cooldowny nie zostały jeszcze określone liczbowo.
Nie stanowią zgody na dodatkowe opłaty za uruchomienie ani bonusy statystyk.

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
operacja nie traci potrzebnych plików. Prezentacja aktualizacji nie zmienia inventory ani HC.
Admin poprawnie pokazuje potomstwo; testy desktop/mobile i runbook wyłączenia.

Dla czyszczenia: wybrane i niewybrane typy, możliwość sprzedaży na obu rynkach,
ochrona plików, faktycznie odzyskana przestrzeń, ponowne uruchomienie z wynikiem
„system jest już czysty” oraz kolejne czyszczenie po pojawieniu się nowych plików.
Dla aktualizacji: pasek postępu, własne logi autora w kolejnych etapach,
bezpieczne wyświetlanie tekstu i brak zmian parametrów systemu.

Dla przywracania zabezpieczeń: każdy z OPEN/LOW/REGULAR/ALL po ingerencji PvP, zachowanie
macierzy konfliktów i uprawnień, zgodność raportu z panelem, brak zmian gdy stan
jest już prawidłowy, odmowa nadpisania równoległej zmiany oraz bezpieczny retry.

Obowiązuje [zero-heavy](../plans/creator_ghostlab_zero_heavy_profile_contract.md).
Nie czytać ani nie modyfikować profile.files; naprawiać naruszenia od razu.
