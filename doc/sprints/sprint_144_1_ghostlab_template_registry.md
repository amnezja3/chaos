# Sprint 144.1 — GhostLab: wspólny rejestr szablonów systemowych

Status: **IMPLEMENTACJA LOKALNA / ODBIÓR SERWEROWY OTWARTY**, 25 IX 2026.
Rejestr, endpoint, wspólna walidacja/compiler/publisher oraz formularz oparty na
schemacie zaimplementowane. [Runbook i test serwerowy](../runbooks/sprint_144_1_ghostlab_registry.md).
Intruder Kicker pozostaje planowany do 144.3; runtime pięciu rodzin nadal pending.
Widok admina i końcowa integracja 11 produktów są zakresem 144.3.
To osobny etap, nie dawna sekcja „144.1 — kontrakt projektu i migracja” w planie bazowym.
Następny: [144.2 — kreator oparty na rejestrze](sprint_144_2_ghostlab_template_authoring.md).

## Cel

System dostarcza logikę i reguły, gracz nadaje produktowi markę, wybiera dozwolone
warianty i publikuje wersje. Dodanie szablonu nie wymaga kolejnej osobnej ścieżki
CRUD/compile/publish. Nowa mechanika nadal wymaga wykonawcy backendowego.

Uściślenie użytkownika z 25 IX: narzędzia, logikę i kontrakty nadal dopisujemy
w kodzie, jak dotychczas. Dla każdego pro-system-tool jawnie określamy GLab
lub nie-GLab. Panel admina jest widokiem szablonów i ich potomstwa, a nie
edytorem logiki, kontraktów czy procesem ręcznej certyfikacji.

## Zakres

- Jeden wersjonowany rejestr backendowy zastępuje rozproszone listy szablonów
  w routes, policy, compilerze i frontendzie. Endpoint udostępnia tylko publiczny opis.
- Przy dodaniu narzędzia w kodzie wymagana jawna klasyfikacja GLab/nie-GLab.
  Narzędzie GLab wskazuje istniejący kontrakt template_id; samo oznaczenie nie
  tworzy logiki wykonania. Test rejestru wykrywa brak decyzji i niepoprawne powiązanie.
  Dla istniejących pro-toolsów wykonać jawny przegląd przypisań, bez automatycznego
  udostępnienia wszystkich. Szablon może też istnieć bez odpowiednika pro-tool.
- Wpis określa template_id, wersję schematu i polityki, opis celu, target_kind,
  launch_mode, schemat dozwolonych ustawień, domyślne wartości, branding,
  dozwolone presentation_id, identyfikator wykonawcy i kontrakt wyniku.
- Oddzielne stany: dostępny do tworzenia, do publikacji, do wykonania.
  Brak wykonawcy lub wspieranej wersji zawsze oznacza runtime pending/odmowę.
  Aktywacja przez konfigurację serwera; zmienne wdrożeniowe w ecosystemach.
  Panel admina nie służy do dodawania wykonawców ani zmiany kontraktu. Certyfikacja
  oznacza walidację i testy definicji w kodzie, nie nowy obieg zatwierdzania w panelu.
- Przenieść pięć istniejących szablonów do rejestru bez zmiany ich balansu,
  project_id, app_id, zakupów i instalacji. Istniejące artefakty wymagają jawnej
  zgodności wersji; nie przepisywać niezmiennych buildów ani ponownie migrować kont.
- Oddzielić parametry autora od serwerowych zasad poziomu, uprawnień, ryzyka,
  cooldownu i kosztów. Request twórcy nie może zmieniać zablokowanych zasad.
- Artefakt wiąże template/schema/policy, dozwolone ustawienia i prezentację.
  Jawna aktualizacja produktu/instalacji; nowa definicja nie zmienia wykonania
  już zainstalowanej wersji po cichu. Nieobsługiwana wersja daje czytelną odmowę.

## Admin — lista GLab i potomstwa

Tutaj definiujemy kontrakt danych widoku; integrację z pełnym katalogiem 11
pro-toolsów i końcowy odbiór admina domyka [144.3](sprint_144_3_pro_tools_glab_alignment.md).

- Lista szablonów GLab z opcjonalnym powiązaniem do pierwotnego pro-toolsa;
  po rozwinięciu produkty graczy utworzone na danym szablonie.
- Przy produkcie: nazwa produktu, autor (login i nazwa wyświetlana), liczba
  pobrań, data stworzenia produktu, aktualna cena katalogowa i stan publikacji.
  Daty stworzenia nie zastępować datą aktualizacji/ponownej publikacji. Dla legacy
  bez wiarygodnej daty pokazać brak danych, nie datę migracji jako datę stworzenia.
- Relacja rodzic–produkt wynika z trwałego template_id i wersji kontraktu,
  nie z nazwy ani slugu. Kolejne buildy i republish nie tworzą nowego potomka.
- Pobrania zgodne z istniejącym licznikiem katalogowym (opisać jego semantykę);
  szkice bez produktu nie otrzymują fikcyjnej ceny lub liczby pobrań.
- Widok tylko dla admina, stronicowany, oparty na canonical store i małych
  projekcjach autora. Brak pełnych profili i skanowania wszystkich inventory.

## Próba rozszerzalności — definicje kontraktów, bez aktywacji gameplayu

| Rodzina | Ustawienia twórcy | Reguły systemowe |
|---|---|---|
| Bilet | branding, miejsce z zatwierdzonego katalogu | transport, dostępność, zużycie biletu |
| Porządkowanie własnego systemu | branding, dozwolona kategoria plików | kwalifikacja zbędnych plików, ochrona core, rzeczywisty wynik |
| Rozszerzenie dysku | branding, wariant dostępny na danym poziomie | pojemność, progi, kumulowanie i jednokrotne przyznanie |
| Skan markerów dekoracyjnych | branding, celownik/pulsacja/radar | zakres, dozwolone markery, brak nadania dostępu do celu |
| Deep Scanner | branding, prezentacja wyniku | wykrywanie awatarów, stealth, zasięg i uprawnienia |

Niesprzedawalny plik nie jest automatycznie zbędny. Cleaner własnego systemu
jest osobnym kontraktem od Arsenal Cleaner atakującego inventory celu.
Animacja skanu nie zwiększa radaru. „Optymalizacja” bez rzeczywistego skutku
musi być opisana jako prezentacja; nie raportować fikcyjnie odzyskanej pojemności.
Balans nowych rodzin wymaga osobnego uzgodnienia przed aktywacją.

## PASS

1. Pięć istniejących szablonów korzysta z jednego rejestru; stare projekty nadal działają.
2. Testowa nowa definicja pojawia się w katalogu bez dopisywania list w routes/UI;
   nie wykonuje nic bez zarejestrowanego i włączonego wykonawcy.
3. Podrobione parametry policy, nieznane prezentacje i wersje są odrzucane.
4. Wyłączenie tworzenia/publikacji/wykonania ma niezależne, przetestowane skutki
   i nie usuwa projektów ani zakupów.
5. Udokumentowana instrukcja dodania szablonu oraz zgodność istniejących artefaktów.
6. Dodanie nowego pro-toolsa wymusza jawną decyzję GLab/nie-GLab w kodzie;
   narzędzie nie-GLab nie pojawia się w kreatorze. Samodzielny szablon jest obsługiwany.
7. Admin widzi szablony i poprawne potomstwo z autorem, pobraniami, datą i ceną;
   zmiana nazwy, aktualizacja i wycofanie nie zrywają relacji ani nie dublują produktu.

Obowiązuje [zero ciężkiego profilu](../plans/creator_ghostlab_zero_heavy_profile_contract.md).
Naruszenia naprawiamy w tym etapie z regresją; żadnych fallbacków pełnego profilu.
