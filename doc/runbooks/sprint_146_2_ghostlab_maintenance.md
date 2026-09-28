# Sprint 146.2 — własny system

Stan: **ZAMKNIĘTY — PASS**, 27 IX 2026, na podstawie potwierdzenia użytkownika:
„mamy pass dla 146.2”. Odbiór obejmuje trzy szablony, trwały stan aktualizacji,
wybór presetów security z logami zmian oraz UX projektów i mobile.
Poniższe instrukcje i checklisty pozostają do regresji; nie oznaczają oczekiwania na odbiór.

## Zawartość

Trzy osobne szablony: **File Cleanup**, **System Update**, **Security Restore**.
Branding → Save Draft → Validate → Compile → Opublikuj build → zakup → instalacja → pulpit.
Narzędzia nie pojawiają się na liście PvP i nie wymagają celu. Każdy korzysta
wyłącznie z wersji faktycznie zainstalowanej; nowy build wymaga jawnej, bezpłatnej
aktualizacji aplikacji. Wycofanie sprzedaży nie odbiera wcześniej zakupionej wersji.

Uruchomienie nie pobiera HC, nie przyznaje statystyk i nie ma dodatkowego cooldownu.
Obowiązuje areszt. Runtime jest dostępny dla wszystkich kont przy obecnym `ACTORS="*"`.
Okna korzystają ze stylu Pro Tools i istniejącego pełnego widoku mobile.

## Wdrożenie

Po przeglądzie i wykonaniu commita/pusha przez operatora, na serwerze:

```bash
git pull
pm2 startOrRestart ecosystem.web.config.js --update-env
pm2 logs chaos --lines 60 --nostream
```

Standardowa kopia bazy przed deployem. Inicjalizacja SQLite tworzy automatycznie
`ghostlab_maintenance_receipts`, `ghostlab_system_updates` i `player_data_file_tombstones`; nie ma migracji
profili ani przepisywania katalogu. Tabele są wymagane dla idempotencji
i ochrony przed ponownym pojawieniem się usuniętych danych.
Szablony można publikować od razu. Pliki JS mają nową wersję cache na obu desktopach.

Wyłączenie wykonawcy: ustawić `CHAOS_GHOSTLAB_MAINTENANCE_RUNTIME_ENABLED: "false"`
w `ecosystem.web.config.js` i wykonać ten sam restart z `--update-env`.
Instalacje i publikacje zostają. Nie usuwać tabel z wynikami/tombstone podczas rollbacku.
Rollback aplikacji nie przywraca fizycznie usuniętych plików; do tego potrzebna jest kopia bazy.

## Czyszczenie — zakres rzeczywistych danych

| Wybór autora | Dane kwalifikowane przez serwer |
|---|---|
| Kamery | Niesprzedawalne pozostałości w `camera` |
| Obiekty | Niesprzedawalne pozostałości w `gps`, `device`, `personal`, `atm`, `financial`, `credentials`, `network`, `vehicle`, `audio` |
| Recon | `system` z wyłącznie `internal_recon_state`, po zakończonej operacji |
| System | `system` jawnie oznaczone `disposable=true`, z wyłączeniem Reconu i danych chronionych |
| Instalatory | Dane w `installers` jawnie oznaczone `disposable=true`; nigdy pliki aplikacji w `player_tool_files` |

Każdy plik musi mieć `sellable=false` i przejść dodatkowe sprawdzenie faktycznej
sprzedawalności Ghost Exchange. Wartościowe paczki kamer/obiektów zostają nawet
przy starym `sellable=false`. Nie wystarczy brak oferty. Powiązania z aplikacją,
projektem, artefaktem, zakupem oraz oznaczenia ochrony blokują usunięcie.
Aktywna lub nierozpoznana operacja chroni dane. Nieznane typy są chronione.
Instalatory/system bez jawnego oznaczenia zbędności pozostają — samo rozszerzenie
`.sh` nie dowodzi, że plik jest niepotrzebny. Brak takich pozostałości jest poprawnym
pustym wynikiem, nie powodem usuwania zainstalowanych narzędzi.

Podgląd obejmuje maks. 250 kandydatów z inventory do 5000 plików; przy większym
inventory operacja jawnie odmawia, bez częściowego usuwania. Po usunięciu partii
można odświeżyć podgląd i wyczyścić następną. Podpisany podgląd jest ważny 10 minut.
Potwierdzenie CHAOS poprzedza operację. Przy zapisie serwer ponownie sprawdza
wersję i kwalifikację każdego pliku; nowe pliki nie wchodzą do starego potwierdzenia.
Raport pokazuje faktyczne usunięcia i odzyskane MB. Pusty stan:
„System jest już czysty — nie ma czego usuwać.”

Jedna transakcja obejmuje pliki, dysk, tombstone, wynik oraz zdarzenie UI.
Retry tego samego podglądu odtwarza zapisany wynik. Nowe uruchomienie wymaga
nowego podglądu. Stara kopia profilu i ponowienie finalizacji operacji nie
przywracają usuniętych identyfikatorów. Otwarty FM i zajętość dysku otrzymują zmianę.

## Aktualizacja systemu i zabezpieczenia

Aktualizacja systemu jest prezentacją: 4 logi autora, po maks. 180 znaków,
600 ms na etap, pasek progresu. Logi są zwykłym tekstem. Nie wykonują HTML,
komend ani instalacji OS; nie zmieniają dysku, HC, zasięgu ani zabezpieczeń.
Przycisk aktualizacji zainstalowanej aplikacji jest osobny. Każdy artefakt aktualizacji
można wykonać tylko raz na konto i produkt. Po wykonaniu okno pokazuje „System jest
aktualny” i blokuje ponowne pobieranie, także po odświeżeniu, restarcie i reinstalacji.
Nowa publikacja autora udostępnia nową wersję aplikacji; po jej jawnej aktualizacji
można wykonać nowy pakiet. Stan wykonania, wynik i delta są zapisywane atomowo;
dwa różne podglądy nie pozwalają zainstalować tego samego artefaktu dwukrotnie.
Śledzenie wersji obowiązuje od tej poprawki. Starsze wyniki prezentacji nie zawierały
identyfikatora artefaktu, więc nie przypisujemy im wstecz niepotwierdzonej wersji.

Security Restore: autor wybiera domyślny preset. Użytkownik ma w aplikacji przyciski
`Open`, `Low`, `Regular`, `All` i może zmienić zestaw przed wykonaniem.
Wybór pobiera nowy podpisany podgląd z wersją security i różnicami przed/po.
Po zapisie log pokazuje rzeczywiste zmiany, np. `firewall: OFF → ON`.
Przy zgodnym stanie przycisk wykonania jest nieaktywny; nadal można wybrać inny
zestaw lub odświeżyć po zmianie ustawień. Istniejący systemowy generator zestawów
działa wyłącznie na dostępnych kluczach; wynik przechodzi macierz konfliktów.
`ALL` nie pozostawia jednocześnie włączonych sprzecznych ustawień.
Zmiana manualna/Proxy po podglądzie powoduje konflikt wersji i wymaga odświeżenia.
Raport zawiera listę zmienionych kluczy oraz stan kanoniczny; otwarty profil
odświeża przełączniki. Nie ma ciągłej ochrony w tle.

## Skoordynowany odbiór

Wystarczą autor i drugie konto kupującego; nie trzeba odnawiać dostępu PvP.

1. Stwórz, skompiluj i opublikuj po jednym produkcie wszystkich trzech rodzin.
   Sprawdź branding, listę grup czyszczenia, cztery logi oraz listę czterech presetów.
2. Drugie konto: kup i zainstaluj; sprawdź HC autora i brak ponownej opłaty za uruchomienie.
   Uruchom z pulpitu bez dostępu PvP. Nowych produktów nie ma na liście PvP.
3. Cleanup: otwórz FM/dysk, podgląd, anuluj — bez zmian. Potwierdź — tylko wybrane
   niesprzedawalne pozostałości znikają, MB odpowiadają raportowi. Sprzedawalne dane,
   aplikacje i dane aktywnych operacji pozostają. Otwórz FM ponownie/odśwież desktop.
4. Cleanup ponownie: pusty wynik. Po nowej zakończonej operacji nowe pozostałości
   znów można usunąć. Ponowienie tego samego żądania nie dubluje efektu.
5. System Update: kolejne logi/pasek, brak zmian parametrów. Tekst `<b>test</b>`
   pokazuje się dosłownie. Zamknięcie podczas animacji przerywa przygotowanie.
6. System Update: ponownie otwórz aplikację — system aktualny, pobieranie zablokowane.
   Nowy build i publikacja autora → aktualizacja aplikacji → nowy pakiet do wykonania.
   Security Restore: wybierz kolejno cztery presety bez ponownej publikacji.
   Sprawdź podgląd różnic, log przed/po, stan w otwartym profilu, konflikty i blokadę zbędnej operacji.
   Zmień ręcznie zabezpieczenie po podglądzie — zapis ma odmówić; odśwież i wykonaj.
7. Wycofaj publikację: posiadana wersja działa. Odinstaluj: wykonanie jest blokowane.
   Areszt: wykonanie blokowane. Zmieniony build: stary podgląd nie działa po aktualizacji.
8. Mobile: okno od brzegu do brzegu, przyciski mieszczą się, długie logi i nazwy
   nie poszerzają ekranu. Rodziny z 146/146.1 nadal działają.

### Widok projektów — poprawka UX

- Na szerokim oknie lista przewija się po lewej, a krótki podgląd jest po prawej,
  bez własnego przewijania. Na mobile lista nie ma limitu wysokości ani wewnętrznego
  scrolla; przewija się cały widok GhostLaba.
- `New Project` → nazwa → wybór templatki → automatyczne otwarcie nowego edytora.
  Anulowanie przed wyborem templatki nie zapisuje pustego projektu `custom`.
- `Open Project` otwiera zaznaczony projekt. Nazwę i opis zmienia się w edytorze.
- `Delete Project` jest wyłącznie w sekcji `Danger` na dole edytora i wymaga
  potwierdzenia. Opublikowane projekty pozostają archiwum zakupionych wersji;
  interfejs wyjaśnia blokadę ich usunięcia.
- Automatyczny test `tests/js/test_ghostlab_projects_flow.js`: PASS. Sprawdzić
  szerokie okno i telefon z długą listą projektów; przeglądarka do wizualnego
  odbioru nie była dostępna w sesji przygotowującej zmianę.

## Weryfikacja lokalna

Poprawka trwałego stanu i presetów: **25 testów backendu PASS** (18 maintenance,
7 registry), testy JS maintenance, runtime i publication: PASS. Pokrycie obejmuje
reinstalację, nowy opublikowany build, dwa równoległe podglądy aktualizacji,
rollback, oddzielenie kont/produktów, wybór czterech presetów i logi przed/po.

Wynik 27 IX 2026: **PASS** — 14 testów nowego wykonawcy, wymieniona poniżej
regresja GLab i 5 skryptów Node (w tym `test_consequence_inventory_delta.js`).
Dodatkowo PASS: canonical consequences, finalizacja PvP, wallet runtime cutover
oraz 17 testów boot/profile. Test boot/profile używa teraz ścieżek względem pliku
testowego, dzięki czemu działa z izolowanego katalogu runnera.
Kontrola składni JS i `git diff --check`: PASS. Odbiór końcowy w grze potwierdził
użytkownik po wdrożeniu; agent nie wykonywał osobnego testu wizualnego w przeglądarce.

Backend przez izolowany runner: `tests.test_ghostlab_maintenance` oraz regresja
registry, alignment, publication, runtime, mutation_runtime i travel.
Nowe testy obejmują transakcje/rollback, retry równoległe, pusty i nowy stan,
sprzedawalność, aktywne operacje, stare lustro profilu, CAS zabezpieczeń,
areszt, instalację przez drugie konto i aktualizację artefaktu. Hot path ma strażnika
zakazującego `profile_json`, pełnego odczytu/zapisu profilu i `sync_session_profile`.
Node: `test_ghostlab_maintenance.js`, `test_ghostlab_runtime.js`,
`test_ghostlab_publication.js`, `test_ghostlab_travel.js`.
