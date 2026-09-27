# Sprint 146.1 — bilety graczy i canonical travel

Stan: przygotowany lokalnie 27 IX 2026. **Bez commita, pusha i wdrożenia.**
Odbiór gameplay oraz wizualny desktop/mobile pozostaje do wykonania po wdrożeniu.

## Co wdrażamy

Travel Ticket w GhostLabie: własna nazwa, ikona, opis, kraj, miejscowość, nazwa
miejsca oraz lat/lng. Projekt = jedno miejsce; kolejny projekt dodaje kolejne.
Save Draft → Validate → Compile → Opublikuj build → Googleplex.
Podgląd pinezki jest dostępny przed publikacją, bez geokodowania miasta.

Zakup wymaga potwierdzenia oferty i od razu wykonuje jedną podróż. Nie instaluje
aplikacji ani pliku. Cena podlega obecnej polityce minimum, widocznej w Googleplexie.
Autor otrzymuje płatność w canonical wallet; zakup własnego biletu nie przelewa HC
samemu sobie. Areszt i brak HC blokują podróż bez pobrania opłaty.

Po podróży trzy reakcje: zły / zadowolony / bardzo zadowolony. Jedna aktywna,
zmienialna reakcja konta na produkt. Autor nie ocenia własnego produktu.
Zmiana danych miejsca rozdziela oceny obecnego miejsca od poprzednich.
Zmiana własnej reakcji na ocenę nowego miejsca zastępuje wcześniejszy głos.
Wycofanie sprzedaży nie usuwa opinii ani dowodów podróży.

Istniejące bilety systemowe używają tej samej transakcyjnej ścieżki. Zakup oraz
`/api/catalog` nie czytają i nie zapisują pełnych profili, także przy błędzie.
Pozycja pozostaje kanoniczna; nie zapisujemy starych lustrzanych pól pozycji/miasta.

## Konfiguracja i dane

- `CHAOS_GHOSTLAB_TRAVEL_RUNTIME_ENABLED=true` dodano do `ecosystem.web.config.js`.
- Decyzją użytkownika przed wdrożeniem 146.1 ustawiono
  `CHAOS_GHOSTLAB_RUNTIME_ACTORS=*`: wszystkie sześć rodzin potomków oraz bilety
  twórców są dostępne dla wszystkich kont po restarcie z `--update-env`.
  Nadal obowiązują flagi rodzin, wymagania produktu i reguły gry.
  Flaga i lista kont dotyczą biletów graczy, nie starych biletów systemowych.
- Tabele `travel_purchases` i `travel_reactions` oraz indeksy powstają przy starcie.
  Nie potrzeba migracji pełnych profili. Wymagane istniejące canonical wallet,
  position, inventory i projekcje identity/capability z poprzednich sprintów.
- Przed wdrożeniem wykonać standardowy spójny backup SQLite. Zachować paragony,
  reakcje, opublikowane buildy i dziennik portfela przy ewentualnym rollbacku.
- Po dostarczeniu kodu: `pm2 startOrRestart ecosystem.web.config.js --update-env`.
  Odświeżyć stronę gry; wersje assetów zmieniono w obu szablonach desktopu.
- Stara otwarta karta bez ceny/builda w żądaniu dostaje odmowę `offer_changed`;
  należy odświeżyć stronę i potwierdzić aktualną ofertę.
- Runtime można wyłączyć flagą i restartem z `--update-env`. Odczyt istniejących
  ocen/paragonów pozostaje dostępny; publikacja i wykonanie to osobne przełączniki.

## Test skoordynowany — dwa konta

Autor A i kupujący B muszą być poza aresztem. Dostęp runtime jest ogólny. Wystarczy jeden bilet;
podróże nie zużywają limitów PvP. Zanotować saldo obu kont oraz pozycję B.

1. **Tworzenie:** A tworzy Travel Ticket dla znanego punktu, sprawdza pinezkę,
   zapisuje, waliduje, kompiluje i publikuje. Karta pokazuje opis autora,
   współrzędne, cenę i trzy liczniki początkowo równe zero.
2. **Anulowanie:** B anuluje potwierdzenie. Salda i pozycja bez zmian; oceny
   niedostępne. Próba autora ocenienia własnego biletu również niedostępna.
3. **Zakup:** B potwierdza. Dokładna cena ubywa B i trafia do A, mapa pokazuje
   wskazany punkt. Brak nowej ikony, pliku i pozycji na liście Player Access.
4. **Reakcje:** B wybiera zadowolony, potem zły. Łącznie jeden głos. Odświeża
   Googleplex i drugą kartę — liczby i wybór pozostają zgodne.
5. **Nowy zakup/retry:** następny świadomy zakup to nowa płatna podróż, ale
   nadal tylko jeden głos. Ponowienie tego samego żądania nie pobiera drugi raz
   HC i nie przestawia ponownie pozycji. Reconnect zachowuje stan.
6. **Zmiana miejsca:** A zapisuje i publikuje nowy punkt. Stara otwarta oferta B
   odmawia zakupu bez kosztów. Po ponownym otwarciu Googleplexa widać nowe miejsce
   i osobno historyczne oceny. Ocena nowego miejsca wymaga podróży do niego.
7. **Odmowy:** wycofana publikacja / runtime off / brak HC /
   areszt — brak opłaty i ruchu. Anulowana lub odrzucona podróż nie daje prawa oceny.
8. **Stary bilet:** B kupuje systemowy bilet do Warszawy. Sprawdzić przeniesienie,
   płatność do admina i ponowienie tego samego żądania. Bez pełnego profilu.
9. **Desktop/mobile:** karta, trzy reakcje, potwierdzenie podróży i podgląd pinezki
   mieszczą się w oknie; nazwy i opisy zawijają się. Admin → GhostLab pokazuje
   Travel Ticket, autora, miejsce, build i agregaty reakcji.

## Weryfikacja lokalna

Wynik 27 IX: **69 testów Python PASS, 6 zestawów Node PASS**. Kontrola składni
zmienionych plików JS i `git diff --check` również PASS. Testów wizualnych
w przeglądarce ani testów na produkcyjnym serwerze nie wykonano.

Uruchamiać przez `python -B tools/run_isolated_tests.py`, nigdy import `run`
z katalogu zawierającego produkcyjną bazę.

- `tests.test_ghostlab_travel`: zakup, brak launchera, 35 MB profil, blokada
  ciężkich odczytów/zapisów SQL, niedobór HC, atomowy rollback, współbieżny retry,
  stare paragony, wycofanie, stara oferta, reakcje i ich wersjonowanie, areszt.
- Regresja registry/publication/alignment/mutation runtime i wallet cutover.
- Dostosowane testy `/api/catalog`, blokady biletu podczas aresztu i starego
  zakupu systemowego w `test_target_persistence`.
- Node: `test_ghostlab_travel`, `test_ghostlab_runtime`, `test_ghostlab_publication`,
  `test_googleplex_runtime_bridge`, `test_googleplex_app_purchase_lock`,
  `test_googleplex_download_update`; kontrola składni JS.

Testy transakcji celowo wstrzykują awarię przed commitem; jej wpis ERROR jest
oczekiwany w przebiegu potwierdzającym rollback. Nie oznacza błędu końcowego testu.
