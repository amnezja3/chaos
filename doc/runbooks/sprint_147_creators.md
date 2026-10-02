# Sprint 147 — pakiet kreatorów i bramki wdrożenia

Stan 2 X 2026: **W TRAKCIE. Nie aktywować nowego kreatora na produkcji.**
Po zgodzie autora wykonano [audyt ryzyka](../audits/sprint_147_progression_risk_2026_10_02.md)
i lokalną integrację magazynu progresji. Poprzednia blokada kontroli została
rozwiązana. Checkpointy chronią zgodność odczytów i zapisów; `settle` oraz
`settle_strategic` nie czytają ani nie zapisują pełnego profilu.
Przygotowane komponenty nie są jeszcze kompletnym pakietem wdrożeniowym.
`CHAOS_CREATORS_V2_ENABLED=false` w konfiguracji PM2 zachowuje dotychczasowy edytor.
Flaga nie jest potwierdzeniem gotowości pozostałych zmian do wdrożenia.

## Dostarczony kod

- `creator_policy.py`: zatwierdzone sufity LVL, losowanie 50/50, katalog recept,
  whitelist efektów, walidacja interfejsów i wybór efektu z zainstalowanego wydania.
- `creator_store.py`: osobne projekty, rewizje, generacja idempotentna, niezmienne
  wydania, blokada mechaniki/ceny po publikacji i wycofanie samej oferty.
- `creator_routes.py`: API projektów, konfiguracji przed publikacją i publikacji.
  Dane tożsamości/poziomu są pobierane z małych projekcji.
- `creator_migration.py`: dry-run i import historycznych publikacji z kanonicznego
  `app_config`, jawna lista autorów, kontrola źródła i receipt ponownego wykonania.
- `/gonna-win`: nowa polityka efektu zabezpieczeń; zły wybór jest odrzucany przed
  zmianą kropek akcji i utworzeniem operacji. Legacy pozostaje w swoim executorze.

Puste pole ceny używa istniejącej wyceny systemowej; jawne `0` oznacza bezpłatność.
Quote zapisuje się w kontrakcie i nie zmienia przy awansie, retry ani edycji tekstu.
Przed publikacją można ustalić cenę oraz efekty/ceny opcji Button Choice.
Zmiana tej konfiguracji nigdy nie losuje ponownie mocy.

## Otwarte bramki — nadal zakres 147

1. **Przejęcia i workery — cutover wykonany lokalnie 2 X.** `/gonna-win`
   korzysta z kanonicznych instalacji, celu, operacji, progresji i oznaczonych celów.
   Usunięto lustra profilu z utraty punktu, otoczenia i finalizacji geometrii.
   GhostNetwork rozlicza RSP przez trwałe pokwitowania, także po awarii. Ranking
   końcowy odczytuje projekcje. Test przejęcia wykrywa również połknięty ciężki SQL.
2. **Pozostałe executory i pliki.** Zweryfikować każdą receptę od instalacji przez
   uruchomienie do skutku, rezultatów, ryzyka i błędów z blokadą ciężkiego profilu.
   Test pojedynczego efektu zabezpieczeń nie zastępuje tej bramki.
3. **Legacy/XMapper.** Import zachowuje dokładny snapshot, ale nie przekształca
   historycznego projektu do nowego edytowalnego kontraktu. Potrzebna regresja
   rzeczywistego XMappera i raport z docelowego katalogu; definicji tego produktu
   nie ma w repozytoryjnym `static/app_config.json`.
4. **Wersje i rozliczenia.** Odbiór instalacji, kopii starszej wersji i niezmienności
   ceny na rzeczywistym zakupie; płatne opcje i przycisk aktualizacji skoordynować
   z 148. Nowy edytor oraz materiały szkoleniowe PTK pozostają częścią 147–148.

Nie przeniesiono naruszeń zero-heavy do długu ani do kolejnego sprintu.

## Weryfikacja lokalna

PowerShell z katalogu repozytorium:

```powershell
$env:PYTHONPATH='.;tests'
python -m unittest tests.test_creator_policy tests.test_creator_migration tests.test_creator_routes
node tests/js/test_creator_ux_contract.js
node --check static/js/terminal.js
```

Testy `CreatorRoutesTest` używają rzeczywistego małego kontekstu wykonania.
`tests.test_capture_scoped_runtime` sprawdza pełne przejęcie w historycznym
formacie efektu, blokadę ciężkiego SQL, worker konfliktu, migrację starej wypłaty,
restart GhostNetwork i rollback grupy pokwitowań. Nie zastępuje to weryfikacji
produkcyjnego snapshotu XMappera ani wszystkich recept kreatora.

## Migracja — najpierw kopia stagingowa bazy

Podaj rzeczywistą ścieżkę bazy i jawnych autorów. Dry-run otwiera SQLite tylko do
odczytu: nie inicjalizuje schematu ani danych. Nie korzysta z `users.profile_json`.

```sh
python -m creator_migration --db /path/to/staging.sqlite3 --owner main --owner run
```

`review` oznacza brak wymaganych danych, niejednoznaczny identyfikator/nazwę albo
kontrakt wymagający osobnego przeglądu. Kod wyjścia `2` sygnalizuje takie wpisy.
Import na kopii testowej:

```sh
python -m creator_migration --db /path/to/staging.sqlite3 --owner main --owner run --apply
```

Import przenosi tylko jednoznaczne publikacje. Zachowuje ID, ceny, opcje i efekty;
nie modyfikuje kupionych kopii. Ponowienie nie nadpisuje późniejszego wycofania.
Zmiana źródła dla istniejącego receipt przerywa transakcję. Nie używać tego jako
automatycznej migracji przy żądaniu gracza ani jako pełnej migracji projektów.

## Skoordynowany odbiór po zamknięciu bramek

Konta: autor A, kupujący B, cel C; osobne fixture L30, L39, L40, L99 i L100.

1. Kontrolowane losowania maksimum i wariantu słabszego. Retry żądania, edycja
   opisu i publikacja zachowują wynik. Awans A nie zmienia opublikowanej mocy.
2. Wszystkie cztery interfejsy i każda recepta: zgodny cel, niewłaściwy cel,
   brak dostępu, areszt, zmiana celu, ponowienie i awaria zapisu.
3. Exploit 100% i historyczny XMapper: kropka oraz pełny pasek; przejęcie,
   nagrody i notyfikacje obu stron dokładnie raz.
4. Button Choice: próg 99/100, błędny efekt/indeks, cena użycia, brak środków,
   brak ponownego obciążenia przy retry. W innych kreatorach effect odrzucany.
5. B instaluje v1, A publikuje korektę v2 pod tym samym ID. Kopia B pozostaje v1;
   bezpłatna aktualizacja daje v2. Wycofanie oferty zachowuje zainstalowaną kopię.
6. Telemetria i blokady pełnego profilu dla autora, kupującego, celu, odbiorcy
   środków oraz wszystkich wywołanych workerów: zero ciężkich odczytów i zapisów.

## Rollback

**Warunek wdrożenia integracji progresji:** osobna migracja
`python -m tools.migrate_player_progression --db ... --owner ...` dla wszystkich
istniejących kont objętych rozgrywką, z jawnymi partiami do 100 kont. Najpierw
dry-run i kopia bazy. Migrację oraz przełączenie wykonać przy zatrzymanych writerach
gry (web i workery), aby stary kod nie zmienił baseline po migracji. Nowe konta
otrzymują wpis w swojej transakcji rejestracji. Brak migracji istniejącego konta
blokuje nagrodę przez recovery, bez leniwego wczytywania profilu.

Rozliczenia progresji są wspólne dla gry i nie są wyłączane flagą kreatorów.
Po pierwszej nagrodzie zapisanej w ledgerze nie wolno cofać kodu do wersji, która
nie odczytuje checkpointów; taki rollback ukryłby naliczone przyrosty. Wyłączenie
tworzenia aplikacji nie zastępuje kompatybilnej wersji kodu progresji.

Pozostawić/ustawić `CHAOS_CREATORS_V2_ENABLED=false` i przeładować środowisko PM2.
Nie usuwać tabel projektów, wydań, publikacji ani receiptów. Nie przywracać starych
snapshotów użytkowników i nie cofać poprawnych płatności. Po publikacji produktów
v1 kod runtime obsługujący ich kontrakt musi pozostać dostępny również przy
wyłączonym tworzeniu. Cofnięcie do wersji bez tej obsługi nie jest bezpiecznym
rollbackiem już zainstalowanych aplikacji.

## Cutover przejęć i workerów — dodatkowe wymagania

`tools/migrate_player_progression.py` migruje również statystyki i historyczne
pokwitowania GhostNetwork, bez ponownej wypłaty. Konto z ledgerem progresji, ale
bez `player_ghost_reward_state`, ponownie kwalifikuje się do migracji. Migracja
obejmuje wszystkich uczestników gry, nie tylko autorów narzędzi. Najpierw dry-run
na kopii bazy; apply i przełączenie przy zatrzymanych web i workerach starej wersji.

Oznaczone cele wymagają wcześniejszego wykonania `tools/migrate_marked_targets.py`.
Brak migracji blokuje przejęcie przed mutacją; runtime nie importuje profilu.
Ledger poprzedniego właściciela jest sprawdzany przed zmianą własności.

Nagroda GhostNetwork zapisuje RSP, statystyki i receipt atomowo. Restart przed
finalizacją reputacji klanu ponawia finalizację bez drugiej wypłaty. Zbiorcza
finalizacja przejęć zużywa grupę receipts w jednej transakcji. Nie uruchamiać
starego workera lub adaptera wypłat po migracji. Stare mirrory `hacked` i
`aimed_target` nie są autorytetem; czytniki używają kanonicznych magazynów.

Pierwotna weryfikacja dotyczyła backendu na izolowanych bazach SQLite.
2026-10-02 operator potwierdził migrację produkcyjną 37 kont, komplet oznaczonych
celów i projekcji runtime, niezmienione metadane profili oraz `quick_check: OK`.
Po ponownym uruchomieniu usług HTTP odpowiada 200. Flaga nowego kreatora pozostaje
wyłączona; nie oznacza to PASS całego sprintu.

Końcowa weryfikacja cutoveru: **123 testy PASS, bez pominięć** (zestawy 67 + 55
oraz dodatkowy test pełnego przejęcia cudzego punktu). `git diff --check` czysty.
Zakresy: progresja i writers, polityka/migracja/API kreatorów, pełne przejęcia,
scoped runtime, kontrola terytorium, finalizacja konfliktu, GhostNetwork bridge,
ranking, operacje i ekspozycja kamer. To nie jest PASS całego sprintu 147.

## Kontrola konfliktu i naprawa dostarczania GhostNetwork

Operator potwierdził gameplay punktów, terytorium do nagrody x3 i konfliktu.
Log konfliktu potwierdza `respect_gain=25`, `levels_gained=1`, `status=applied`,
`duplicate=False`, publikację zwycięzcy `main` oraz brak kolejnego awansu przy
ponownym przeliczeniu. Wystąpił jednak świeży błąd dostarczania zdarzenia GN:
`GhostNetwork delivery requires event_id and cycle_id`. Końcowe `ok=True` i pusta
kolejka starej wersji nie dowodzą dostarczenia wszystkich zdarzeń.

Przyczyna: rekurencyjny kolektor widział także raporty narracji zawierające
event_id/event_type, ale bez cycle_id. Runtime pobiera teraz pełny kanoniczny
rekord po event_id. Nie dopisuje aktualnego cyklu do starego zdarzenia. Hipoteza
operatora o konflikcie/markerze z poprzedniego cyklu nie jest potwierdzona przez
ten log; regresja obejmuje zachowanie oryginalnego cyklu i brak reaktywacji
historycznej części po rozstrzygnięciu starego konfliktu.

Worker zapisuje kursor ID zdarzenia przed zmianą stanu, odtwarza trwałe zdarzenia
partiami po 250 i przesuwa kursor dopiero po rozliczeniu/dostarczeniu całej partii.
Retry po wypłacie korzysta z istniejących receipts. Rozpoczęte zadania z kursorem
nie są pomijane przy łączeniu kolejki. Sukces nie zwraca już starego pola error.
Nowa tabela `ghostnetwork_territory_event_cursors` powstaje przez init_db; nie
wymaga ponowienia migracji progresji. Nie usuwać historii zdarzeń użytej jako
kotwica niedokończonego zadania.

Ostrzeżenia o obszarach miały też konkretną ścieżkę: świeża geometria zwracana
przez build_player_areas nie ma jeszcze owner_username ani identyfikatora zapisanego
obszaru. Synchronizacja intruzów pobiera kanoniczne obszary właściciela, gdy brak ID;
brakującego właściciela uzupełnia z kontekstu, nie nadpisując jawnego właściciela.
Nie usuwa obszarów i nie zmienia progów aproksymacji dużych skupisk punktów.

Wdrożyć web oraz territory-worker z tej samej wersji; zrestartować oba przez
odpowiednie konfiguracje PM2 z --update-env. Gameplay nie wymaga ponownej migracji.
Już zakończone zadania starej wersji nie mają kursora i nie są masowo odtwarzane.
Dla okna czasowego rozstrzygnięcia uruchomić odczytowy audyt:

```bash
.venv/bin/python tools/audit_ghostnetwork_delivery.py --since '<czas-z-offsetem>' --until '<czas-z-offsetem>'
```

Daty ISO wymagają strefy, np. `2026-10-02T18:00:00+02:00`. Audyt porównuje
kanoniczne event_id/cycle_id z kolejką dostarczeń, nie importuje run.py i nie
migruje bazy. Brak delivery jest kandydatem do sprawdzenia, nie dowodem utraty
nagrody; `truncated=true` wymaga węższego okna. Najpierw przejrzeć wskazane ID,
potem ewentualnie odtworzyć wyłącznie potwierdzone brakujące zdarzenia.

Weryfikacja: zestaw 51 testów backendu PASS (bridge, dostarczenia i retry,
historyczny cykl, audyt tylko do odczytu, scoped capture i fairness workera).
Dodatkowe 8 testów PASS po korekcie identyfikacji świeżych obszarów (7 powtórzonych
testów przejęć i 1 nowy): łącznie 52 różne testy.
Bez testu na produkcyjnej historii; wdrożenie nie odtwarza automatycznie zadań
oznaczonych jako zakończone przez poprzedni kod.

## Poprawka zapisu pulpitu po migracji — szczegóły

Kontrola logów operatora z 2026-10-02: zadania obszarów `kot1` kończą się
`ok=True`, kolejka ma głębokość 0. Zapis pulpitu zwraca 200 bez `PROFILE_WRITE`.
Wyciąg HTTP z 17:47–17:48 nie zawiera samego żądania przejęcia; gameplay PASS
pochodzi z potwierdzenia operatora. Pozostają odczyty `/api/profile` i zgłoszenia
`remote_anomaly` dla dwóch wcześniejszych konfliktów, bez ownership mismatches.

Pierwszy start weba o 17:06:30 ujawnił wyścig dodawania `desktop_settings_json`
przez procesy Gunicorn (`duplicate column name`). Kolejny start oraz restart
o 17:34 przebiegły bez tego błędu. Poprawka inicjalizacji toleruje wyłącznie
potwierdzony duplikat właściwej kolumny TEXT; inne błędy SQL nadal przerywają start.
Nie wymaga ponowienia migracji progresji ani zmian istniejących danych.

Świeże logi ujawniły równoległe zapisy `api.profile.desktop`, konflikty rewizji
i zapisy bez zmian. Endpoint zapisuje teraz wyłącznie niezależną kolumnę
`user_identity_projection.desktop_settings_json`. Nie czyta ani nie przepisuje
`users.profile_json`, nie podnosi rewizji profilu i nie tworzy LKG. Powtórzenie
tych samych ustawień nie wykonuje UPDATE. Częściowe zmiany są scalane w transakcji,
a kontrola sesji przed commit pozostaje aktywna.

Kolumna jest dodawana przez standardowe `init_db` przy starcie. Do pierwszej
zmiany używana jest istniejąca, zweryfikowana projekcja pulpitu. Nie trzeba
powtarzać migracji progresji ani skanować profili. Odczyty profilu i pulpitu
uwzględniają nowe ustawienia, a przebudowa projekcji ich nie nadpisuje.

Frontend kolejkuje zapisy, wysyła zmienione pola i nie dubluje przełączenia
fullscreen przez fetch oraz beacon. Oba szablony pulpitu mają nowy klucz cache JS.
Po wdrożeniu zrestartować web z `--update-env` i odświeżyć otwarte pulpity.
Sprawdzić zachowanie tapety, układu ikon, fullscreen i stylu mapy po przeładowaniu.
Zmiany ustawień nie powinny generować `PROFILE_WRITE` z `api.profile.desktop`.
To nie usuwa niezależnych, pozostałych odczytów `/api/profile`.

Weryfikacja poprawki: **49 testów Python PASS** (13 dla pulpitu/projekcji/pollingu
oraz 36 dla ochrony profilu i progresji), test kolejki Node PASS, kontrola składni
JS i `git diff --check` PASS. Playwright potwierdził kolejność trzech zapisów
z maksymalnie jednym aktywnym żądaniem w izolowanym teście z atrapą fetch.
Nie jest to test pełnego pulpitu zalogowanego gracza na produkcji.
