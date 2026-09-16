# 141.5 — przygotowanie domknięcia Sprintu 141

Stan 2026-09-16: plan wykonawczy po odbiorze 141.4, nie deklaracja CLOSED.
Łączy dawne .5–.7. Poprzednie odbiory autora pozostają zaliczone.

## Aktualny checkpoint finalizacji 16 IX

Nowszy odbiór Friend Kickera po 880d7d4: kontakt usunięty, wiadomości nie
zaobserwowano, replay wyniku oceniony jako mylący. Lokalnie poprawiono
blokadę przycisku/409 po użyciu i jawne ID wiadomości per użycie. Trwały
receipt pozostaje wewnętrzny, ponowne kliknięcie nie pokazuje starego losowania.
Trzy testy Python i trzy JS PASS. Oczekuje wdrożenia oraz powtórnego odbioru;
wcześniejsze opisy replay jako odpowiedzi HTTP sukces są historyczne.

Autor potwierdził poprawne działanie okna PvP zgodnie z założeniami po
wdrożeniu `8208b7b`. Odbiór okna zaliczony; nie dopisujemy z tego domyślnie
konkretnych urządzeń, wymiarów ani pomiarów, których autor nie podał.

Pierwszy pakiet finalizacji lokalnie gotowy:
- Sniffer oraz otwieranie Security Proxy czytają projekcje zamiast profili.
- Friend Kicker czyta capability/desktop i do 1000 kontaktów (nadmiar fail-closed).
  Writer-lock obejmuje ponowną kontrolę grantu/instalacji, losowanie, zmianę
  kontaktów obu stron i ich dotychczasową obsługę historii rozmowy, wiadomości
  oraz trwały bezpieczny wynik w istniejącym tool usage. Retry odtwarza wynik.
  Historyczne receipts bez pełnego wyniku nadal zwracają odmowę użycia.
- Sniffer zapisuje deduplikowane powiadomienie przed complete, a replay
  potwierdzonego użycia uzupełnia ewentualną brakującą wiadomość. Pending
  zachowuje wylosowaną kwotę, wallet receipt zapobiega ponownemu transferowi.
- UI blokuje ponowne kliknięcie w trakcie requestu, ignoruje wynik po zmianie
  stanu dostępu lub utracie sesji i rozróżnia nie-JSON od potwierdzonego wyniku.

Walidacja: w regresji 52 testów Python 51 PASS, jeden błąd oczekiwania testu
(Flask zwraca 500 zamiast propagować wymuszony wyjątek). Po poprawce oczekiwania
trzy testy finalizacji PASS, w tym dodatkowy recovery Sniffera; łącznie 53
różne przypadki z potwierdzonym PASS. Osiem zestawów JS PASS: cztery okna/wyniki,
request guard, session isolation, position ordering, gonna-win lifecycle.
Nowe testy używają profili obu stron ≥35 MiB, awarii po wiadomości/transferze
i równoległych wywołań. Nie jest to pełna końcowa regresja całego 141.

Bez nowej tabeli/migracji. Bez deployu. Nadal rozliczyć pełny wynik/recovery
Cleanera (efekt i usage atomowe, powiadomienie poza transakcją), wyścigi
uprawnień dla wszystkich mutacji security, pozostałą macierz błędów/sesji,
przeniesione pomiary mapy oraz wspólne operacje/pliki. Poniższa tabela opisuje
stan wejściowy przeglądu; naprawy powyżej zastępują jej ustalenia dla tego pakietu.

Aktualne procesy po konserwacji serwera 16 IX (lista przekazana przez operatora):
`chaos` = 10, `chaos-territory-worker` = 11, `chaos-ollama-worker` = 12,
`chaos-narrative-publisher` = 13. Stare 13/14/17/18 nie są aktualną mapą.
W poleceniach używać nazw, numery każdorazowo sprawdzać przez pm2 list.
Operator wdrożył `8208b7b` i zrestartował chaos (10); cztery procesy online.
Odbiór wizualny okna PvP nadal pozostaje do potwierdzenia.

Decyzja autora 16 IX: panel Player Access ma korzystać ze standardowego okna
aplikacji i istniejącego mechanizmu okien mobile. Lokalnie podłączono app-window,
makeDraggable i taskbar/mobile safe mode. Desktop: przesuwanie i zachowanie
pozycji przy refresh. Mobile: istniejące dopasowanie okna do ekranu, scroll
zawartości, zawijanie opisów. Minimalizacja nie cofa dostępu; przywrócenie
z paska aplikacji. Tytuł pozostaje stabilny między renderami. Opóźnione
wygaśnięcie poprzedniego grantu nie zamyka nowego. Cztery testy JS PASS
(lifecycle okna oraz wyniki Kickera/Sniffera/Log Readera), składnia JS PASS.
To walidacja lokalna, bez wizualnego odbioru na urządzeniach i bez deployu.

## Co zachowujemy jako potwierdzone

- 141.2: odbiór aktualnej mapy po teleportacji, wtargnięciu i objęciu polem
  oraz alarmu właściciela; migracja mapy wykonana przez operatora.
- 141.3: wybór i blokady celu, osobny postęp celów, kontynuacja rozpoczętego
  hacku poza terytorium/zasięgiem, grant i launcher; migracje operatora READY
  dla 31 kont i czteropunktowy smoke autora PASS.
- 141.4: katalog/bramki odebrane wcześniej, licznik w otwartym Google Plexie
  potwierdzony 16 IX. Bilety teleportacyjne wyłączone.
- Wynik Friend Kickera bez kontaktów jest prawidłowy. Nieudany roll Arsenal
  Cleanera jest wynikiem domenowym. Intruder Kicker ma odbiór działania.

## Pozostałe prace techniczne, w kolejności

| Obszar | Dowód / ograniczenie obecnego stanu | Praca i warunek zamknięcia |
| --- | --- | --- |
| Financial Sniffer | Gałąź tool/use czyta pełny profil ofiary i atakującego. Istnieje test reserve → transfer → complete, który sam nie dowodzi recovery całego requestu. | Zastąpić odczyty właściwymi projekcjami; sprawdzić przerwanie i retry między rezerwacją, transferem, wynikiem oraz powiadomieniem. Bez ponownego losowania lub transferu. |
| Friend Kicker | Pełne profile obu stron; remove_contact i wiadomości poprzedzają osobne record_tool_usage. | Związać wybór kontaktu, roll, obustronną zmianę relacji i receipt atomowo albo sprawdzonym recovery. Test równoległych requestów i awarii po zmianie kontaktu. Odczyty bez pełnych profili. |
| Security Panel Proxy | Samo otwarcie używa get_profile ofiary. Mutacje security mają osobne guarded write ścieżki. | Otwieranie z ograniczonej projekcji; sprawdzić update/preset, CAS, uprawnienia i precommit. Rzeczywistą mutację profile-owned security rozliczyć jako nazwany wyjątek, nie utożsamiać jej z odczytem panelu. |
| Log Reader, Arsenal Cleaner, Intruder Kicker | Istnieją dedykowane testy bounded read, atomowości Cleanera/Kickera, replay i konkurencji. | Zaliczamy istniejące pokrycie; uzupełnić tylko luki stwierdzone przy przeglądzie wyników, w szczególności dwóch atakujących i zmiana stanu w trakcie akcji. |
| Interfejs i recovery | Odbiór gameplayu nie jest zapisem pełnej macierzy urządzeń i błędów transportu. | Sprawdzić każde okno, mały viewport, długie treści, utratę sieci, non-JSON, wygaśnięcie, A → B → A, zmianę sesji i cleanup. Naprawiać potwierdzone problemy. |
| Mapa i wspólne ścieżki | Z .2 przeniesiono ruch w toku, pełne audience, recovery i pomiary opóźnień. | Rozliczyć te próby; dla operacji/pliku wykazać właściwy łańcuch do GX albo jawne „nie dotyczy”. Bez tworzenia fikcyjnych artefaktów dla narzędzi. |

Powyższe obserwacje pochodzą z przeglądu kodu 16 IX. Nie są reprodukcją
awarii na serwerze. Odczyty profili są potwierdzone w kodzie; skutki konkretnego
przerwania i wyścigu wymagają testów. Nie przeprowadzono w tym przygotowaniu
nowego pełnego przebiegu regresji ani audytu działającej produkcji.

## Walidacja techniczna

Używać izolowanego runnera `python -B tools/run_isolated_tests.py`.
Punkty startowe: test_player_hack_read_paths, test_intruder_kicker,
test_player_hack_completion, test_player_hack_access_grant,
test_player_launcher_hot_path, test_player_picker_hot_path,
test_player_target_selection, test_wallet_runtime_cutover oraz właściwe
testy session generation/precommit. Rozszerzać zachowanie, nie same asercje
tekstu kodu. JS: istniejące testy wyników narzędzi, pozycji, alarmu, lifecycle
i sesji. Licznik pozostaje objęty własną regresją.

Mały i ≥35 MiB profil każdej strony: brak pełnych odczytów w zwykłych
ścieżkach; transakcje, receipts, rollback i monotoniczne wersje. Dla zapisów
profile-owned: CAS/LKG, integralność i guard sesji. Wyniki zapisać z zakresem
i ograniczeniami, oddzielnie od historycznych PASS.

## Jeden końcowy odbiór autora

Przygotować po ukończeniu prac technicznych; nie wymagać teraz powtarzania
wcześniejszych zaakceptowanych scenariuszy.

1. Desktop i mobile: pełna sesja PvP z dostępnymi sześcioma narzędziami,
   czytelne wyniki oraz zgodny stan ofiary. Zachować zasady Pickera po wyjeździe.
2. Telefon: narzędzia, formularze security, logi i komunikaty mieszczą się
   w oknie; dotyk, klawiatura ekranowa, obrót i powrót z tła działają.
3. Recovery: przerwać połączenie podczas użycia, wznowić, zmienić cel i wrócić;
   jeden efekt, bez okna poprzedniej ofiary, zawieszonego przycisku i odnowienia grantu.
4. Mapa: rozliczyć pozostałe próby ruchu w toku/audience i zmierzyć opóźnienie
   aktualizacji. Nie odtwarzać historycznych pomiarów z domysłów.

Macierz rozmiarów pozostaje z planu sprintu: 1366×768, 1920×1080, 768×1024,
360×800, 390×844, 844×390; dodatkowo zoom 200%. Emulację odróżnić od fizycznego
telefonu i zapisać faktycznie sprawdzone urządzenia/przeglądarki.

## Warunek zamknięcia

Jedna tabela wymagań z dowodem dla każdego punktu: istniejący zaakceptowany
wynik, nowy test lub nowy odbiór. Brak otwartych blokad integralności/hot path,
rozliczona responsywność i recovery, końcowy odbiór autora. Wtedy zamykamy
141.5 i cały 141. Bez odbioru: gotowość do walidacji, nie PASS.
Brak automatycznego deployu, restartów, migracji, triggerów i działań nagrodowych.
