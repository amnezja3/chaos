# Camera Street View — pierwsza paczka 165.1

31.10.2026. Procedura przygotowana lokalnie; NIE wykonano push/deploy/API.
Kontrakt: [wytyczna operatora](../plans/camera_street_view_operator_contract_2026_10_31.md).
Evidence: [raport paczki](../audits/camera_street_view_package_165_1.md).

„Paczka implementacyjna” oznacza zamknięty zakres funkcjonalny w repozytorium,
wdrażany standardowym commit/push i deploymentem Git. Nie tworzymy ZIP-ów,
kopii repo ani alternatywnej dystrybucji. [Dokładny zakres Git](../audits/camera_street_view_165_1_git_scope.md).

## Zawartość i granice

Zakres ma bazę Git `3556abdcb9603110271e0ea7563fbea4f590ae63`. Do commita
nie włączamy bazy, sesji, sekretów, logów ani zmian
operatora w `doc/prototypes/camera_view/v164_0/preview.css`. Zachowany snapshot
prezentacji jest osobnym, niezmiennym punktem odniesienia, nie środowiskiem demo.

Gameplay: normalny camera_stream, kanoniczne expires_at/started_at i realizery
Super Powers; po potwierdzonym zapisie jednorazowe okno. `viewer_closed=1`
oznacza zużycie także dla starych pilotowych grantów. Nie resetować tego pola.
Nowe hakowanie po zamknięciu tworzy nową operację. Równoległe retry nadal
deduplikowane. Archive failure nie zmienia nagród, ryzyka ani wyniku pobrania.

Archiwum jest w tej samej bazie gry (wybrano istniejące transakcje zamiast
drugiej bazy); prywatne media domyślnie `data/camera_visual/`. Trzy nowe tabele:
archives, withdrawals, budget. Sesje pilota pozostają w camera_visual_sessions.
Worker jest odrębnym CLI, nie żądaniem Gunicorna ani drugim workerem operacji.
Wykonanie CLI ma zewnętrzny limit 90 s, lease 120 s/fencing, najwyżej dwie próby,
TTL kolejki 900 s; jedna strona, do 30 kandydatów i trzech miniatur.

## Konfiguracja

| Klucz | Domyślnie / znaczenie |
| --- | --- |
| CHAOS_CAMERA_STREET_VIEW | 0; gameplay dla kamer z kanonicznego skanu |
| CHAOS_CAMERA_VISUAL_PILOT / _USER | istniejąca bramka lokalnego pilota legacy; na VPS domyślnie nie ustawiona |
| CHAOS_CAMERA_SOURCE | off / fixture / mapillary; fixture tylko do kontrolowanych testów |
| CHAOS_CAMERA_WORKER | 0; worker nie wykonuje pracy |
| CHAOS_CAMERA_ACQUISITION | 0; brak żądań Mapillary |
| CHAOS_CAMERA_SERVE | 0; brak publikacji materiałów Mapillary |
| MAPILLARY_ACCESS_TOKEN | sekret wyłącznie w istniejącym prywatnym środowisku serwera |
| CHAOS_CAMERA_CDN_HOSTS | pusta lista; dokładne hosty HTTPS z zatwierdzonej próbki, bez wildcardów |
| CHAOS_CAMERA_RIGHTS_REFERENCE | puste; identyfikator rozstrzygnięć L01/L02, nie sekret |
| CHAOS_CAMERA_LICENSE / _LICENSE_URL | puste; zatwierdzone prawa do konkretnego źródła |
| CHAOS_CAMERA_RETENTION_SECONDS | 0; brak zatwierdzonej retencji blokuje pozyskiwanie |
| CHAOS_CAMERA_MAX_REQUESTS | 100/dobę UTC, rezerwacje przed HTTP, bez automatycznego zwrotu po awarii |
| CHAOS_CAMERA_MAX_BYTES | 104857600/dobę; konserwatywne rezerwacje limitu odpowiedzi, nie rachunek dostawcy |
| CHAOS_CAMERA_MAX_ARCHIVES | 10 aktywnych archiwów; limit kontrolowanego pilota |
| CHAOS_CAMERA_ARCHIVE_DIR | prywatny katalog, poza static |

Web: `ecosystem.web.config.js`, zachować odebrany profil `world_maplark_region`.
Worker: `ecosystem.camera.config.js`, pojedyncze wykonanie co 2 minuty; konfiguracja
OFF jest dostarczona, proces nie został uruchomiony. Nie przełączać pozostałych
profili, kolektora ani istniejących flag świata. Nie drukować całego środowiska.

## Przygotowanie Git — po decyzji operatora

Przed celowym stagingiem porównać `git status --short`, `git diff` i listę nowych
plików z wykazem zakresu. Nie używać `git add .`: pozostawić osobną zmianę
operatora w preview.css i techniczne logi Playwright. Zachować dowody testowe.
`git diff --cached --check` oraz przegląd staged diff zamykają zakres commita.
Nie powtarzać zaliczonych testów przy samej korekcie dokumentacji; przy zmianach
kodu uruchomić odpowiednie regresje. Zapisać wynikowy SHA jako RELEASE_SHA.
Po zatwierdzeniu: standardowy commit i `git push origin main`.

## Sesja VPS A — zbiorcze wdrożenie OFF, po osobnej decyzji

1. W `/home/johndoe/app/chaos` zapisać aktualny HEAD jako PREVIOUS_SHA,
   sprawdzić `git status --short`, branch i zgodność historii z RELEASE_SHA.
   Przy rozbieżnościach zatrzymać wdrożenie bez nadpisywania zmian.
2. Backup bazy przez SQLite backup API, nie kopiowanie aktywnego pliku z WAL.
   Sprawdzić integrity_check i foreign_key_check, zachować prywatnie.
3. Backup mediów/manifestów i aktualnego rejestru wycofań:

```text
.venv/bin/python tools/camera_archive.py --db data/game.sqlite3 --action backup --directory PRIVATE_BACKUP_DIR --apply
```

   Dla pierwszej instalacji bez tabel najpierw wykonać pełny backup bazy;
   polecenie archive backup stosować po migracji albo przy kolejnych wydaniach.
4. Standardowe `git pull --ff-only`; sprawdzić, że `git rev-parse HEAD` jest
   zatwierdzonym RELEASE_SHA. Zainstalować `.venv/bin/python -m pip install -r requirements.txt`
   i sprawdzić `.venv/bin/python -m pip check`. Nowa zależność: Pillow>=11,<13,
   lokalnie testowano 12.3.0; zapisać wersję zainstalowaną na VPS.
5. Dry-run, potem addytywna migracja po backupie:

```text
.venv/bin/python tools/camera_archive.py --db data/game.sqlite3 --action migrate
.venv/bin/python tools/camera_archive.py --db data/game.sqlite3 --action migrate --apply
```

   Migracja tworzy idempotentnie `camera_visual_sessions`, `camera_visual_archives`,
   `camera_visual_withdrawals`, `camera_visual_budget` i indeksy
   `camera_visual_target`, `camera_archive_pending`. Bez backfill, kasowania,
   resetu grantów lub zmiany tabel incydentów. Zweryfikować schemat i integralność
   bazy po migracji oraz `--action status`.
6. Zachować flagi OFF i nie ustawiać lokalnego CHAOS_DB_PATH na VPS.
   Przeładować tylko web:
   `pm2 startOrReload ecosystem.web.config.js --only chaos --env world_maplark_region --update-env`.
   Nowy worker pozostaje niewłączony. Nie uruchamiać historycznych procedur VPS.
7. W jednym przebiegu smoke sprawdzić HTTP/login/pulpit, skaner, Cyberner,
   camera_off/ryzyko/incydenty na koncie testowym, `/camera-sources` PL/EN
   oraz `/admin?tab=camera` (admin dozwolony, zwykły gracz 403).
   Sprawdzić brak żądań dostawcy przy OFF i nowe logi od czasu wdrożenia.
   Zapisać SHA, migrację, wersje, wyniki i flagi bez wartości sekretów.
   `pm2 save` dopiero po poprawnym odbiorze; awaria → rollback, lokalna poprawka.

## Sesja VPS B — kontrolowany pilot źródła, osobny etap 166

Zamknąć L01/L02, zatwierdzić retencję, limity i hosty CDN. Ustawić sekret w
istniejącym mechanizmie serwera, bez wklejania do Git lub przeglądarki.
Pierwsze wywołanie musi mieć jawnie włączone acquisition i worker; samo
przygotowanie tokena ani wdrożenie kodu nie włącza publikacji.

Sekret wymagany: `MAPILLARY_ACCESS_TOKEN`, dostępny tylko backendowi i workerowi.
Pozostałe klucze z tabeli są konfiguracją. Web i CLI muszą używać tej samej bazy,
prywatnego katalogu mediów i konfiguracji praw/retencji. Katalog musi być zapisywalny
przez worker i czytelny dla web, poza static. Dostęp sieciowy: HTTPS do
graph.mapillary.com i zatwierdzonych dokładnych hostów CDN; brak wildcardów.
PM2 ma jawne wartości OFF w plikach: samo ustawienie zmiennej w powłoce nie
włącza pilota. Po osobnej zgodzie utrwalić uzgodnioną konfigurację istniejącym
mechanizmem, z kontrolą efektywnych flag obu procesów bez drukowania sekretu.
STREET_VIEW=1 włącza ścieżkę dla wszystkich kwalifikujących się kamer/graczy;
nie jest allowlistą kont. Pilot jednej kamery wymaga kontrolowanego środowiska
lub okna testowego; nie przedstawiać tej flagi jako ograniczenia do main.

Zgrupowany odbiór na kontrolowanych kontach i celu:

1. Sprawdzić kontrakt rzeczywistej odpowiedzi, autora/licencję, wybór miniatur,
   limity i koszt; uruchomić pojedyncze `work-once` przed cyklicznym workerem.
2. Skan → aplikacja → success → SESSION CLOSE → rzeczywisty download z mocami
   → zapis pliku → jedna instancja. Failure nie daje dostępu. Materiał z archiwum
   nie daje uprawnień drugiemu graczowi; wspólne zdjęcie nie oznacza wspólnego toru.
3. Reload/reconnect/login/minimalizacja zachowują aktywną instancję. Ręczny close
   zużywa grant; ponowne hakowanie wymaga nowego download i tworzy nowy tor.
4. Brak pokrycia/timeout/limit → NO SIGNAL bez zmiany wyniku operacji;
   późny materiał bez restartu okna; wycofanie blokuje istniejące odczyty.
   Awarie odtwarzać kontrolowanie, bez wyczerpywania limitów płatnego dostawcy.
5. Zweryfikować camera_off/incydenty, panel admina, atrybucję/odnośniki,
   zainstalowaną PWA, RSS/CPU/p95, budżet i lease/restart workera.
   Dopiero po PASS pojedynczej pracy dopuścić `ecosystem.camera.config.js`
   z uzgodnionymi flagami (jedna instancja, co 2 minuty).

Zapisać jeden raport VPS z SHA i wynikami każdego punktu. Przy defekcie:
zatrzymać zależny punkt, zebrać diagnostykę, poprawić lokalnie, wykonać właściwą
regresję i wdrożyć kontrolowany commit po zgodzie; wznowić odbiór od miejsca
błędu. Nie powtarzać zaliczonych kosztownych prób bez nowej przyczyny.

```text
.venv/bin/python tools/camera_archive.py --db data/game.sqlite3 --action status
.venv/bin/python tools/camera_archive.py --db data/game.sqlite3 --action work-once --apply
```

Stan materiału i autoryzacja gracza są niezależne. Dla braku pokrycia/awarii
obowiązuje zaakceptowany NO SIGNAL. Powrót do świadomie zamkniętego okna wymaga
nowego hakowania i pobrania; odzyskanie aktywnej instancji nie wymaga nowego pliku.

## Wycofanie, GC, backup/restore

```text
.venv/bin/python tools/camera_archive.py --db data/game.sqlite3 --action withdraw --source Mapillary --image-id IMAGE_ID --reason REASON --apply
.venv/bin/python tools/camera_archive.py --db data/game.sqlite3 --action gc --apply
.venv/bin/python tools/camera_archive.py --db data/game.sqlite3 --action restore --directory PRIVATE_BACKUP_DIR --apply
```

Tombstone blokuje odczyt i ponowną publikację we wszystkich archiwach. UI przy
następnym zweryfikowanym snapshot pokazuje NO SIGNAL; odzyskanie kontekstu
ponownie sprawdza uprawnienia. Nie obiecujemy usunięcia kopii zapisanych przez
odbiorcę poza aplikacją. GC: do 256 plików na wywołanie, godzinna karencja dla
niepodpiętych plików po awarii. Warunki usuwania prywatnych backupów ustala L01.
Restore jest addytywny, zachowuje bieżące tombstones i większe liczniki budżetu.
Nie przywraca grantów ani zużytego dostępu. Przed restore całej bazy zachować
i nałożyć najnowszy rejestr wycofań; stary backup nie jest zgodą na publikację.

## Rollback

Najpierw STREET_VIEW/acquisition/serve/worker OFF, zatrzymać tylko nowy worker.
Zachować kanoniczne operacje, receipts, pliki gry, zużycia i tombstones. Cofnąć
zmiany wdrożonego commita przez kontrolowany revert w Git i standardowe
wdrożenie; PREVIOUS_SHA jest punktem porównania. Nowe tabele mogą pozostać.
Nie odtwarzać starego pilotowego reopen ani resetować viewer_closed. Nie cofać
całej produkcyjnej bazy w celu wycofania UI — usunęłoby to inne zdarzenia gry.

## Pozostaje do odbioru na VPS

Rzeczywista odpowiedź API/hosty CDN, L01/L02 i rights provenance, RSS/CPU/p95
pod obciążeniem, źródłowe limity, nawigacja zainstalowanej PWA. Lokalne viewporty
nie dowodzą PWA. Publiczna strona `/camera-sources` nie zastępuje atrybucji
fotografii ani akceptacji dostawcy. Brak danych produkcyjnych nie blokuje
przygotowania kodu OFF, ale blokuje publiczne pozyskiwanie/udostępnianie.
