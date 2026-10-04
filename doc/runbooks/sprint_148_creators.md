# Sprint 148 — stan przygotowania

## Odbiór ATM i poprawki pickera — 4 X

Użytkownik potwierdził plik ATM, kompletowanie paczek i sprzedaż 42 MB za 414 HC.
Ta ścieżka gameplayowa ma PASS; nie oznacza to odbioru wszystkich kreatorów.

Pole ikony i przycisk palety mają po 44×44 px, w jednym rzędzie. Playwright
potwierdził układ przy 390 px oraz wybór ikony z pakietu.

Dla nowych kreatorów odpowiedź wyboru narzędzia zawiera kanoniczną zainstalowaną
definicję aplikacji. Picker buduje interfejs bez oczekiwania na cykliczną kolejkę
i dodatkowe /command. Spóźniona kolejka lub powtórzona odpowiedź nie budują okna
ponownie, a status booting nie nadpisuje zakończonego przekazania.

Macierz backendu (52 kombinacje akcji/interfejsów) oraz bezprofilowy launcher
przeszły testy. Test JS sprawdza ponowienia i zamknięte okno. Playwright sprawdził
przekazanie do rzeczywistego renderera app_window w izolowanym komponencie
z zastąpioną obsługą okien: tytuł, logi i przycisk powstają raz i pozostają
po spóźnionej odpowiedzi kolejki. Pełna ścieżka mapy na produkcji wymaga odbioru.

## Poprawki po pierwszym odbiorze produkcyjnym — 3 X

- Migracja produkcyjna: 13 `adopted`, ponowny odczyt 13 `already_adopted`.
  Backup: `game-before-148-20261003T063959798885Z.sqlite3`, 37 kont, quick_check OK.
  Po rozruchu web odpowiedział HTTP 200 w 0,026 s. Błąd workera w logu był z 26 IX.
- Audyt `gx` na serwerze: instalacja i operacja mają `creates_file=false`, brak
  zasobów, finalizacja timeout zapisana z file_count=0. Nie jest to utrata pliku.
- Nowy edytor: wybór ikon z pakietu, jeden grafem w polu, przyciski przeznaczenia
  i zapisu pliku, jawne TAK/NIE także po generacji, potwierdzenia CHAOS.
- FM wyświetla nazwę/ikonę projektu przy zachowaniu stabilnej tożsamości pliku.
  Katalogi danych czytają kanoniczne player_data_files bez pełnego profilu.
- Launcher /command pomija sync_session_profile dla nowych i adoptowanych
  kreatorów. Usunięto potwierdzony ciężki odczyt; czas produkcyjnego pickera
  wymaga ponownego pomiaru po wdrożeniu poprawki.
- Zbieranie danych bez pliku nie uruchamia operacji. Bez bezpośredniego efektu
  próba kończy się odmową przed zmianą celu i rozliczeniem. Historyczne aplikacje
  zachowują działanie; efekty niezależne od plików (np. kamera) pozostają aktywne.
- Weryfikacja komponentowa Playwright: 75 ikon, limit jednego grafemu, ATM
  creates_file=true oraz atm_dump odczytane z API, dialog CHAOS, jasny hover
  rgb(239,255,242), brak poziomego przepełnienia przy 390 px. To nie jest pełny
  produkcyjny test mapy; testowy host zgłaszał jedynie brak favicon po poprawieniu
  obsługi query string zasobów. Backend: 28 testów tras i płatności PASS przed
  dodaniem blokady pustych operacji. Po dodaniu blokady 28 z 29 testów polityki
  i płatności przeszło od razu; macierz wymagała wskazania prawidłowej opcji
  Button Choice w fixture. Jej osobne ponowienie PASS: cztery interfejsy ATM
  odrzucają wykonanie bez pliku i nie zapisują operacji. Kontrakt JS PASS.

3 X 2026: pakiet przygotowany do kontrolowanego wdrożenia z migracją offline.
Nie jest to produkcyjny PASS gameplayowy. Użytkownik odebrał dotychczasowy
gameplay 147; pełny odbiór pętli następuje po wdrożeniu kompletu 148.

## Zaimplementowane

- Wspólny edytor czterech kreatorów: nazwa, ikona, akcja i tworzenie pliku,
  następnie systemowa generacja i końcowy edytor. Moc i sufit pokazane oddzielnie.
- TermCreator: wiele komend/outputów; WindowMaker: logi i przyciski;
  ButtonMaker: prompt, etykiety, effect i cena opcji; AppForge: logi i wyniki.
  Podgląd tekstów nie uruchamia aplikacji. Tekst trafia do DOM przez textContent.
- Lista projektów, zapis szkicu, ponowne otwarcie nowego projektu z FM,
  widoczność nieopublikowanych szkiców jako plików projektu.
- Sprawdzenie instalacji właściwego kreatora przez API. Brak narzędzia nie
  usuwa projektu. Kontrola rewizji pozostaje po stronie serwera.
- Ceny/efekty blokowane po publikacji; ponowienie publikacji bez edycji
  zachowuje rewizję. Potwierdzenie porzucenia niezapisanych zmian.
- Aktualizacja wersjonowanej aplikacji w Googleplexie: jawne 0 HC, wersja
  zainstalowana i dostępna. Backend wymaga aktywnej instalacji i zgodności
  zamrożonego kontraktu; wersja docelowa nie może zmienić się po cichu.
- Atomowa wymiana instalacji, pliku uruchamiającego, zajętości dysku i delt;
  bez transferu, nowego downloadu i zmiany tożsamości zakupu.
  Wycofanie zachowuje instalację, konfiskata blokuje bezpłatną aktualizację.

## Wykonane sprawdzenia

- 20 testów `test_creator_policy`, `test_creator_migration`, `test_creator_routes`
  na tymczasowej bazie. Nowe scenariusze obejmują szkic w FM, brak kreatora,
  konflikt rewizji, starą kopię po publikacji, aktualizację/retry bez transferu,
  pojedynczy launcher, wycofanie i blokadę po odinstalowaniu.
- `node --check` dla edytora i terminala; `test_creator_ux_contract.js` PASS.
- Playwright: rzeczywisty moduł edytora i API Flask na fikcyjnym koncie,
  w izolowanym hoście testowym (uproszczona rama okna). Utworzenie i publikacja
  wszystkich czterech interfejsów; korekta AppForge do v2 przy czterech projektach
  łącznie; cena po publikacji zablokowana. Na 390 px brak poziomego przepełnienia.
  Konsola: brak błędów JavaScript; jedynie brak favicon hosta testowego (404).
- Test komponentu nie zastępuje pełnej ścieżki logowania, pulpitu, mapy i zakupu
  w działającej grze. Kopia produkcyjna nie była używana do mutacji tych testów.

## Odbiór po kontrolowanym wdrożeniu

1. Odbiór gameplayowy płatnych opcji: implementacja natychmiastowego wyniku
   oraz rezerwacji/finalizacji operacji w tle jest gotowa do dalszych testów.
   Szczegóły i granice potwierdzenia poniżej.
2. Odbiór executorów w pełnym UI gry. HTTP/finalizery mają pokrycie 12 recept
   oraz osobne scenariusze exploita i kamery, z blokadą ciężkiego profilu.
   Macierz launchera obejmuje 52 kombinacje recept/interfejsów oraz osobną
   ścieżkę obserwowanej kamery. To nie jest jeszcze macierz pełnych pętli UI.
3. Prezentacja opłat/odbiorcy przed wykonaniem,
   testy całych pętli czterech kreatorów i aktualizacji na innym koncie.
4. Historyczne aplikacje są przenoszone osobną migracją opisaną poniżej.
   Nie ma lazy migracji ani przeliczania mocy podczas otwierania projektu.

Nie zmieniać flagi rollout na podstawie samego odbioru formularzy.
Nie wykonano commita, pushu ani wdrożenia w tym etapie.

Historyczne projekty: lokalna próba na pełnej kopii 1,8 GB przeniosła 13 projektów;
powtórzenie jest idempotentne. Porównanie sygnatur `users` (rewizja/checksum),
`player_apps` i `json_resources` wykazało brak zmian; `quick_check` OK.
Sprzątanie katalogu tymczasowego wymagało zamknięcia uchwytów SQLite na Windows;
nie był to błąd migracji. Dodatkowa kontrola 95 rzeczywistych instalacji potwierdziła
zgodność z przyszłą aktualizacją. Końcowy zestaw kreatorów/historii/płatności:
45 testów PASS. Playwright potwierdził edycję historycznej v1, publikację v2
i przycisk AKTUALIZACJA 0 HC, który faktycznie zmienia instalację na v2.
Host komponentowy używa rzeczywistego edytora i API, bez pełnej ramy pulpitu.

## Wdrożenie 148 — kolejność

Kod musi najpierw trafić do repozytorium wdrożeniowego. Poniższe polecenia są
przeznaczone dla serwera Linux, w `/home/johndoe/app/chaos`. Domyślna flaga
pozostaje wyłączona. Nie uruchamiać starego kodu przy aktywnych nowych operacjach
płatnych: rollback oznacza wyłączenie edytora, nie cofnięcie schematu lub portfela.

1. Zatrzymać procesy zapisujące i pobrać przygotowany kod:

```bash
pm2 stop chaos chaos-territory-worker chaos-ollama-worker chaos-narrative-publisher
git pull --ff-only
```

2. Wykonać nową kopię bazy przy zatrzymanych procesach:

```bash
.venv/bin/python - <<'PY'
import sqlite3
from contextlib import closing
from pathlib import Path
from datetime import datetime, timezone
source = Path('data/game.sqlite3').resolve(strict=True)
folder = Path('backups'); folder.mkdir(exist_ok=True)
target = folder / ('game-before-148-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.sqlite3')
target.touch(mode=0o600, exist_ok=False)
with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as src, closing(sqlite3.connect(target)) as dst:
    src.backup(dst)
    assert dst.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
print(target)
PY
```

3. Dry-run, następnie migracja i powtórny dry-run. Lista autorów pochodzi
z lokalnej kopii produkcji: nowe konta/projekty wymagają dopisania autora.
`review` lub błąd oznacza zatrzymanie aktywacji i sprawdzenie raportu.

```bash
.venv/bin/python tools/migrate_creator_projects.py --db data/game.sqlite3 --owner admin --owner main --owner run --owner igideberi
.venv/bin/python tools/migrate_creator_projects.py --db data/game.sqlite3 --owner admin --owner main --owner run --owner igideberi --apply
.venv/bin/python tools/migrate_creator_projects.py --db data/game.sqlite3 --owner admin --owner main --owner run --owner igideberi
```

Oczekiwane na kopii z 2 X: 13 `ready`, 13 `adopted`, 13 `already_adopted`.
Migracja nie zmienia ofert, instalacji, profili ani sald. Zachowuje stare nazwy
plików projektu. Zmiana prezentacji publikuje kolejne wydanie tego samego ID.
Historyczne efekty (w tym XMapper) nadal korzystają z historycznego executora.
Aktualizacja sprawdza zamrożoną mechanikę; licznik pobrań nie jest jej częścią.

4. Uruchomić komplet z nowym kodem:

```bash
CHAOS_CREATORS_V2_ENABLED=true pm2 startOrRestart ecosystem.web.config.js --update-env
pm2 startOrRestart ecosystem.territory-worker.config.js --update-env
pm2 startOrRestart ecosystem.ollama-worker.config.js --update-env
pm2 startOrRestart ecosystem.narrative-publisher.config.js --update-env
pm2 list
curl --max-time 15 -sS -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:6666/
```

Kolejne starty z pliku konfiguracji również wymagają jawnego
`CHAOS_CREATORS_V2_ENABLED=true`; bez niego edytor pozostanie wyłączony.
Sprawdzić logi weba/workera, otwarcie historycznego pliku, zachowanie efektów,
nowy projekt każdego kreatora, płatną opcję i bezpłatną aktualizację na nabywcy.
Po potwierdzeniu stabilności można wykonać `pm2 save`.

Wyłączenie nowego edytora bez cofania danych:

```bash
CHAOS_CREATORS_V2_ENABLED=false pm2 startOrRestart ecosystem.web.config.js --update-env
```

Pozostawić worker na nowym kodzie, aby rozliczył rozpoczęte operacje.

## Doprecyzowanie effect — 2 X

Nie tworzymy treści PTK: autorami ewentualnych poradników będą gracze.
Każdy przycisk przyjmuje własne przypisania `klucz=wartość`, rozdzielone przecinkami.
Walidator dopuszcza systemowe klucze zabezpieczeń z booleanami `true`/`false`
oraz całkowity `risk_level` 0–100. Nie używa eval ani wykonania kodu. Sprawdza
również błędną składnię poniżej LVL 100, lecz wtedy nie przyznaje ręcznego efektu.
Od progu ręczny efekt ustawia wskazane wartości bez losowania. Pozostałe pola
obiektu nie są otwartą przestrzenią zapisu. Błąd podaje numer opcji i nie zapisuje
częściowo poprawionego kontraktu. Przed publikacją ponowna kontrola efektów.

23 testy polityki/migracji/API PASS po tej zmianie. Nowe scenariusze: ON i OFF,
dwie odrębne opcje, LVL 99/100, nieprawidłowe typy, zakresy, duplikaty kluczy,
próby wyrażeń oraz HTTP 400 bez zmiany projektu po błędzie drugiej opcji.

## Rozliczenie natychmiastowego wyniku i pliki — dalsza implementacja 2 X

`creator_payments.py` czyta cenę i autora z instalacji, wybiera admin jako
odbiorcę wyłącznie przy nieistniejącym koncie autora i wymaga identyfikatora
użycia. Własna aplikacja nie tworzy sztucznego transferu. Brak odbiorcy także
po fallbacku powoduje odmowę. Receipt zawiera wynik i wiąże żądanie z celem.

`atomic_runtime_transaction` jest opt-in dla płatnych opcji nowego kontraktu.
Łączy wywołania magazynów w jednej bazie przez ContextVar; zagnieżdżone
magazyny mają savepointy, a ich commit nie zatwierdza całej jednostki.
Końcowy commit nadal sprawdza generację sesji. Zmiana zabezpieczeń/przejęcie,
transfer, delty i wynik opcji są zatwierdzane razem. Awaria transferu cofa
przejęcie i receipt: ponowienie może bezpiecznie wykonać całość.
Istniejące bezpłatne/legacy ścieżki nie włączają tej transakcji.

Ważne dla dalszego audytu: transakcja trzyma blokadę zapisu podczas wykonania
opcji. Nie wolno dodawać do niej wywołań sieciowych ani oczekiwania na operację
w tle. Pozostałe warianty przejęć i czas blokady wymagają dalszej weryfikacji
przed aktywacją całego sprintu.

Stan `creator_creates_file` jest zapisany w operacji. Jawne false blokuje
wszystkie dziewięć starszych finalizerów, które wcześniej mogły interpretować
pustą listę zasobów jako wybór domyślnego pliku. Bounded finalizer zapisuje
zakończenie z zerową liczbą plików. Brak znacznika zachowuje legacy.

Weryfikacja: 38 testów kreatorów, migracji, płatności i przejęć PASS, test
kontraktu JS i kontrola składni JS PASS. Test HTTP obejmuje prawdziwą ścieżkę
przejęcia, awarię transferu, rollback i ponowienie. Test równoległy przy saldzie
10 HC dopuszcza jedną z dwóch prób kosztujących po 10 HC. Guard ciężkiego
profilu aktywny w testach wykonania. Playwright sprawdził moduł Button Choice
z prawdziwym API w izolowanym hoście: przycisk przed kliknięciem wyświetla
„10 HC tylko za sukces → admin”; brak błędu JS, jedynie favicon 404.

## Operacje w tle — rezerwacja i finalizacja

- Start płatnej operacji bez natychmiastowego effect zapisuje `wallet_holds`
  i `creator_option_pending` w tej samej transakcji co operację i receipt.
  Saldo nie maleje; rezerwacja ogranicza dostępne HC w obu kanonicznych ścieżkach
  obciążenia portfela. Również `debit_up_to` nie wydaje zarezerwowanych środków.
- Portfel zwraca saldo, rezerwację i dostępne HC; przycisk informuje o rezerwacji
  przed kliknięciem. Własna aplikacja pozostaje bezpłatna.
- Worker rozlicza kolejkę przed i po odświeżeniu operacji. `completed` i normalny
  koniec czasu `timeout` są stanami finalizowalnymi istniejącego runtime.
  Sukces rozlicza cenę zapisaną przy starcie i zapisuje pliki w jednej transakcji.
  Błąd, wykrycie, anulowanie lub brak operacji zwalniają rezerwację bez transferu.
- W razie braku autora przy finalizacji odbiorcą zostaje admin. Jeśli nie istnieje
  także admin lub konto płatnika, rezerwacja jest zwalniana bez udostępniania
  płatnego rezultatu. Zapis rozliczenia zapobiega późniejszemu wygenerowaniu pliku.
- Dopóki płatność oczekuje na finalizację, starsze finalizery nie udostępniają
  plików bokiem. Kolejka nie zależy od aktywnej sesji gracza. Restart po awarii
  ponawia nadal zapisane rozliczenia; już zakończone są idempotentne.
- Przycisk z bezpośrednim effect ma natychmiastowy wynik i jest rozliczany
  natychmiast, nawet jeśli dodatkowo uruchamia operację w tle.
- Konsekwencja rezerwacji: środki objęte rezerwacją nie są dostępne również dla
  innych kanonicznych obciążeń, w tym transferów i obciążenia do wysokości salda.
  To wymaga uwzględnienia w odbiorze gameplayowym łączącym operacje z PvP.

Rzeczywisty test HTTP płatnego trace: utworzenie operacji → rezerwacja bez
transferu → stan końcowy → rzeczywisty plik w inventory i pojedynczy transfer.
Testy awarii, ponowienia i anulowania PASS. Szersza regresja: 89 testów PASS
(kreatory, portfel, kontrola operacji, jakość i mnożenie plików). Playwright
potwierdził aktywny przycisk z komunikatem rezerwacji i odbiorcy.

Uzupełniono również bezpośredni raport `scan_ports` przy `creates_file=true`
oraz zapis `artifact_state` dla zakończenia bez plików. Brak flagi twórcy nadal
zachowuje działanie starych narzędzi. Pełny PASS sprintu pozostaje otwarty.

## Kontynuacja 3 X — granica launcher / wykonanie

- Wybór nowego narzędzia na mapie tylko otwiera aplikację. Nie zalicza kroku,
  nie uruchamia operacji i nie obciąża portfela przed akcją w jej interfejsie.
  Preflight i wybór narzędzia korzystają z projekcji zamiast ciężkiego profilu;
  zapis celu nowego kreatora omija kompatybilnościowy zapis całego profilu.
- Kamera zachowuje kontrolę obserwacji scanu, pozycji i instalacji, ale nowy
  kreator również czeka na wybór opcji. Ponieważ kamera wyłącza się od razu,
  jej opłata jest natychmiastowa i atomowa z wyłączeniem. Nie czeka 15 minut
  na koniec ochrony. Nieudany transfer cofa operację i efekt.
- Ponowienie już działającej kamery nie nakłada kolejnego ręcznego effect
  i nie pobiera kolejnej opłaty. Konfiskowana kopia nie autoryzuje kamery.
- Worker izoluje wyjątek rozliczenia pojedynczego receipt: pozostawia jego
  rezerwację do ponowienia, loguje identyfikator i typ błędu, kontynuuje pozostałe
  wyniki oraz zwykłe operacje. Atomowy rollback zachowuje saldo i rezultat.
- Test sesji sprawdza rollback kanonicznych ustawień pulpitu. Test anonimowej
  telemetrii pełnego zapisu używa ścieżki danych konta, a nie dawnego zapisu pulpitu.
- Finalizer audio obsługuje również `microphone_sniffer`: zadeklarowany przez
  receptę plik audio nie może zniknąć po udanym zakończeniu podsłuchu.
- Recepta zwykłego trace deklaruje `location_history`, zgodnie z wynikiem
  istniejącego executora. GPS pojazdu zachowuje `gps_logs`. Klasyfikacja celu
  rozpoznaje również kanoniczne `venue`, `phone`, `server`, `router`, `pillar`.
- Finalizacja pliku czyta tylko trzy pola stanu dysku, zamiast pełnego snapshotu
  inventory. Test blokuje zarówno ciężki profil, jak i zbędny odczyt inventory.

Weryfikacja: główna regresja **78/78 PASS** (płatności, kamera, sesja, portfel,
API, polityka i migracja). Macierz launchera obejmuje 52 kombinacje w jednym
teście parametryzowanym; nie są doliczane jako 52 osobne testy. Dodatkowa grupa
executorów/polityki/kontroli operacji: **25/25 PASS**, częściowo pokrywa poprzednią
grupę. W teście executorów 12 recept wykonuje rzeczywisty request HTTP i zapis
deklarowanego rezultatu; exploit i kamera mają osobne scenariusze.

Po ograniczeniu odczytu inventory ponownie przeszły macierz executorów oraz
płatny trace. Testy jakości/mnożenia plików: **10/10 PASS** po uzupełnieniu
dwóch starych fixture o jawną projekcję dysku. Runtime przy braku tej projekcji
zgłasza recovery, zamiast przyjmować domyślną pojemność konta.
Kontrola składni obu modułów JS i `git diff --check`: PASS.

Podczas równoległej regresji pojawiło się ostrzeżenie Windows o blokadzie pliku
cache sesji, bez błędu testu. Dalszy przebieg ma jawnie odseparowany
`CHAOS_SESSION_FILE_DIR`, oprócz tymczasowych baz i katalogu roboczego.

Sprawdzenia wykonywane na tymczasowych bazach. Brak zmian produkcyjnych,
commita i pushu. Ten wpis nie jest odbiorem wszystkich historycznych projektów
ani pełnego pulpitu w przeglądarce.
