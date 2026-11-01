# Camera Street View S1–S3 i CHAOS Links — implementacja lokalna

Data: 01.11.2026. Baza Git: `025fd3f`. Zmiany w working tree, bez commit/push,
VPS, produkcyjnej migracji i wywołań Mapillary. Dokument zastępuje listę braków
implementacyjnych z audytu, ale nie zastępuje odbioru systemowego Sprintu 166.

## Zakres w kodzie

- `camera_visual_instance.py`: kontrakt feed v1 związany z graczem, kamerą,
  operacją, aktywatorem i instancją. Trwałe zdjęcie, motion v2 i profil wizualny.
  Wybór zdjęcia następuje raz z faktycznie dostępnej listy, także po późnym
  nadejściu materiału. Brak modulo trzech fixture zdjęć. Stary aktywny grant
  otrzymuje profil `legacy`; consumed pozostaje consumed.
- `camera_visual.py`, `run.py`: kanoniczne czasy i zapis pliku pozostają bramką
  dostępu. Stronicowanie aktywnych sesji po 64; media wyszukują konkretny receipt.
  Stary transport współrzędnych rozwiązuje wyłącznie jednoznaczny, aktualny
  skan serwerowy. Kamery świata bez materiału nie otrzymują zdjęcia pilota.
  Retry aktywatorów ma limit 32 i odroczenie 30 s, więc pełny dysk jednego gracza
  nie zatrzymuje kolejnych użytkowników. Aliasy receipt nie zajmują retry slots.
- Renderer zachowuje zaakceptowane okno i wolny ruch Béziera ping-pong.
  Nazwa pochodzi z celu, zegar pokazuje UTC. Profil określa jeden z sześciu
  scenariuszy, intensywność, okres i fazę. Wizualny SIGNAL LOST nie mutuje
  kamery ani incydentów. Niedostępność materiału ma pierwszeństwo.
  Porównywarka jest domyślnie ukryta (`CHAOS_CAMERA_DIAGNOSTICS=0`).
- `camera.runtime.config.js`: jedno źródło ustawień dla web, operations i archive;
  walidacja flag/limitów/źródła, wspólne absolutne ścieżki DB i materiałów,
  rozdzielenie ról. Web nie pobiera materiałów, worker archiwum ich nie serwuje.
- Archiwum: proces `work-loop`, watchdog dziecka 90 s, istniejący lease/fencing,
  automatyczne GC co minutę z godzinnym grace period, limit miejsca przed
  transportem, filtrowanie wycofanych zdjęć przed pobraniem miniatury. GC nie
  zatrzymuje się na pierwszych 256 zachowanych plikach. Backup/restore nie
  kopiują wygasłych/wycofanych zdjęć; restore nie cofa tombstones ani budżetu.
- Admin: konfiguracja i limity, stan kolejki, metadane materiałów, retry/expiry,
  stan procesów i identyfikator DB bez ujawniania ścieżki, audit, wycofanie,
  dozwolone retry oraz GC przez admin+CSRF. Ustawienia zmienia operator w jednym
  prywatnym pliku; panel nie tworzy drugiego źródła ustawień. Backup/restore CLI.
  Gateway ma link do publicznej strony źródeł. Token nigdy nie trafia do panelu.

## CHAOS Links

Jeden parser i handler obsługuje `focus:lat:lon`, `teleport:lat:lon`, zapis ze
spacją i opcjonalnymi nawiasami `<lat:lon>`, a także istniejące `cur:loc`.
Cyberner, Googleplex i dokumenty PTK korzystają ze wspólnego komponentu.
W PTK pojedyncze polecenie zapisane jako inline code jest aktywne; fenced code,
edytory i istniejące elementy interaktywne pozostają tekstem.

Focus czeka na iframe mapy i zachowuje ostatni cel do zdarzenia load.
Teleport nadal wywołuje `/api/blacknet/cta/teleport` po potwierdzeniu.
Operator potwierdził zachowanie obecnego kanonicznego teleportu: brak opłaty
i cooldownu dla dopuszczonej sesji. Nie dodano nowej ekonomii teleportu.
Blokada akcji w toku i krótki debounce chronią przed podwójnym wykonaniem.
Treść jest traktowana jako tekst, nigdy jako interpreter poleceń lub HTML.

## Wykonane testy

| Zakres | Dowód lokalny |
| --- | --- |
| Gameplay | 23 testy unittest PASS, następnie celowane testy zmienionych granic oraz nowy test admin/CSRF PASS |
| Kontrakt instancji | 3 testy PASS: zbiory 1/2/3/8, brak ponownego losowania, legacy, sześć profili |
| Archiwum | 13 testów PASS; dodatkowo automatyczny work-loop w osobnym procesie PASS |
| Kamery świata | Skan kamery sklepu, ATM i obiektu commercial; legacy transport, brak materiału, błędne ID — PASS |
| Ochrona incydentów | camera_shutdown 20, exposure 8, camera_incident_audit 3 — PASS |
| JavaScript | target transport, operation delta, window dedupe, role/config validation — PASS; syntax checks PASS |
| Realny desktop / Playwright MCP | 31 sprawdzeń okna PASS: drag/maximize/minimize, obraz, wolny łuk, dokładny powrót, reload, dwie karty, close/consumed, mobile |
| Resize | Ręczna zmiana obu wymiarów, responsywny HUD, dwa linki, niezmieniony motion — PASS |
| Profil i utrata materiału | Playwright: SIGNAL LOST → ONLINE, następnie REVOKED → OFFLINE, bez odtworzenia okna i bez nadpisania revocation przez FX — PASS |
| Linki / Playwright MCP | 32 sprawdzenia PASS: Cyberner, Googleplex, PTK → Focus i zatwierdzony teleport; PTK mobile, reopen, idempotencja, HTML injection, invalid coords, anonymous denial |
| Opóźniona mapa | Focus po zamknięciu i otwarciu mapy z opóźnieniem odpowiedzi 1200 ms — PASS |
| Zamrożony prototyp | 28 SHA256 zgodnych z manifestem — PASS |

Testy interfejsu używały rzeczywistego `/desktop` i API w istniejącej izolowanej
kopii `instance/cvn-gameplay-164`. Treści wiadomości/news/PTK były kontrolowanymi
odpowiedziami odczytu przez rzeczywiste renderery; teleport był rzeczywistym
zapisem lokalnej pozycji, nie stubem. Nie wysyłano wiadomości ani publikacji.
Fixture dokumentu poprawiono tak, aby zachowywał nagłówki generacji sesji.
Fixture profilu czeka na pełny cykl zakłóceń i kończy przechwytywanie dopiero
po obsłudze trwających żądań; nie zmienia zapisanych grantów ani kamery świata.
Negatywny test współrzędnych respektuje istniejący HTTP 404 `unknown_target`.

Konsola: oczekiwane 409 dla reopen, 404 dla błędnego teleportu; lokalny backup
ma również ostrzeżenia niezależnych warstw mapy (ghostnetwork/incidents/npc,
timeout/deferred). Nie deklarujemy PASS całej konsoli ani tych systemów.

## Migracja i deployment

Procedura: [runbook S1–S3](../runbooks/camera_street_view_system_s1_s3.md).
Trzy nowe tabele: `camera_visual_runtime`, `camera_visual_admin_audit`,
`camera_visual_activation_retry`; idempotentny CREATE IF NOT EXISTS. Łącznie
siedem tabel kamer wraz z istniejącymi czterema. Bez kasowania lub resetu sesji,
plików graczy, uprawnień i snapshotu prototypu. Nie dodano zależności Python;
pozostaje istniejący Pillow. Instalacja przeglądarki Playwright dotyczy wyłącznie
lokalnego narzędzia testowego.

## Granice przekazania do 166

Nie wykonano restartu PM2/reboot VPS ani testów z produkcyjnymi sekretami.
Nie wykonano szerokiej macierzy kont, lokalizacji, aplikacji, PWA i obciążenia.
Insider Feed i Operational Prediction używają istniejącej rodziny
`operation_speed`; testy realizera i 300/1800 s są lokalne. Robot z aktywowaną
mocą i rzeczywistym czasem gry pozostaje odbiorem 166.

Kolejka materiałów ma limit 128, maksymalnie dwie próby i TTL 900 s. Odrzucony
przez limit popyt daje niedostępność materiału, nie fałszywy obraz ani sukces
API. Nowe hakowanie może ponowić pozyskanie. Retencja i publikacja Mapillary
nadal wymagają zatwierdzonych L01/L02; kod nie ustanawia nowych praw.
Limity transferu są konserwatywnymi rezerwacjami, nie pomiarem faktury dostawcy.
Backup archiwum obejmuje do 1000 rekordów na kontrolowany zakres; większy zbiór
wymaga operatorskiego planu backupu, nie cichego obcięcia danych.
