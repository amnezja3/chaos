# Sprint 166 — Camera Street View: odbiór systemowy i pełny rollout

## Aktywny zakres — branding i checkpoint 166.1 (01.11.2026)

Stan lokalny: branding i linki LOCAL PASS; nowa kamera wybrana z backupu,
rzeczywiste pozyskanie i odbiór VPS oczekują. [Raport 166.1](../audits/camera_street_view_checkpoint_166_1.md).

Zatwierdzono IMPLEMENTATION + SYSTEM ACCEPTANCE, LOCAL-FIRST → kontrolowany VPS.
Najpierw aktualizacja 164–166, następnie oficjalny branding Mapillary i zewnętrzne
linki EXTERNAL CONNECTION według sprintu 165, lokalny odbiór i standardowy Git.
Nie powtarzać paryskiego pilota ani cofać jego PASS. Globalny dostęp OFF.

| Checkpoint | Zakres i dowód |
| --- | --- |
| 166.1 — bieżący | Jedna nowa rzeczywista kamera poza pilotem, zweryfikowane ID/pozycja/gameplay, jeden gracz. Brak archiwum → automatyczne żądanie i worker → API → do 3 zdjęć → WebP/checksum/READY → poprawny hack → rzeczywisty download → jednorazowy podgląd. Branding i aktywne linki desktop/mobile, zachowana sesja |
| 166.2 — później | Niezależne zdjęcie, trajektoria, FX/offline i trwałość po reload |
| 166.3 — później | Wiele kont/aplikacji i Super Powers, w tym Insider Feed |
| 166.4 — później | Uprawnienia, duplikaty, consumed, ponowny hack, camera_off/incydenty |
| 166.5 — później | Recovery, wydajność, PWA, limity, raport i decyzja globalna |

166.1: zachować limity/dysk, sekrety i konfigurację procesów, testową retencję
24 h. Bez fikcyjnych celów, ręcznego work-once, skracania timera lub rozszerzania
pilota. NO_COVERAGE udokumentować i wybrać kolejny rzeczywisty cel w budżecie.
Brak zdjęć nie zmienia gameplayu/incydentów. Wynik końcowy: zbiorczy raport
pochodzenia logo/warunków użycia, testów linków i sesji, nowej kamery,
automatycznego pozyskania, optymalizacji/archiwizacji, gameplayu i ograniczeń.
L02 otwarte; nie deklarować PASS bez dowodu. Po raporcie 166.1 zatrzymać zakres,
bez globalnej aktywacji i szerokich kolejnych testów bez decyzji operatora.

## Odbiór VPS 56d5af0 — aktualizacja 01.11.2026

Konfiguracja trzech procesów, heartbeat/DB, HTTP i PM2 save potwierdzone przez
operatora. Token został sprawdzony w działającym archive worker i zapisanym
stanie PM2. Nadal main/pilot, global OFF; pozyskiwanie ON z retencją testową 24 h.
Istniejący materiał: READY, dwa checksum OK. Nie jest to PASS nowego pozyskania.

Operator zaliczył obserwację braku podglądu po niepoprawnej odpowiedzi i UI failed,
mimo zakończonego pobierania 30 min. Współistnienie failed i rozpoczętej operacji:
WYJAŚNIONE — nie regresja. Status etapu aplikacji nie anuluje rezerwacji należącej
do ciągłości mapy → OFC → pickera → desktopu. Nie dodajemy takiego anulowania.
Cztery przekazane rekordy mają server_success=true, timeout i aktywator;
nie dokumentują kanonicznego failure ani przyczyny komunikatu UI. Sama rezerwacja
nie omija sukcesu backendu, czasu pobierania, weryfikacji aktywatora ani consumed.
Kontrola kodu i pokrycie istniejącymi testami opisane w journalu z 01.11.2026.
Następna próba tej samej kamery: success → kolejny pełny download 30 min →
automatyczne otwarcie podglądu — PASS operatora, potwierdzony screenshotem.
Widoczne standardowe okno Camera Network, Mapillary, ONLINE/REC, UTC,
Focus/Teleport, logi oraz autorstwo/licencja. Nowe pozyskanie, trwałość profilu
i close/consumed nie zostały osobno udokumentowane dla tego konkretnego grantu;
wcześniejsze zaliczone testy zachowują swój zakres. Pełny odbiór 166 nadal otwarty.

## Przekazanie z implementacji S1–S3 — 01.11.2026

[Kod i wyniki lokalne](../audits/camera_street_view_system_implementation_2026_11_01.md)
oraz [jedna procedura wdrożenia](../runbooks/camera_street_view_system_s1_s3.md)
są przygotowane w repo. Następny odbiór dotyczy kompletnego systemu:
wielu graczy/kamer/aplikacji, rzeczywistych czasów, Insider Feed i Operational
Prediction, restartów trzech procesów, awarii, PWA i obciążenia.
Lokalne fixtures nie zaliczają tych prób live. Push/deploy i globalne flagi
pozostają decyzją operatora; brak nowej zgody licencyjnej L01/L02.

## Obowiązujący zakres od 01.11.2026

**Pilot main/Paryż: PASS operatora. Odbiór systemowy: NIEZAKOŃCZONY.**
[Audyt 164–166](../audits/camera_street_view_system_audit_2026_11_01.md).
Źródło rzeczywiste, dwa zwykłe 30-minutowe przebiegi, consumed i brak powrotu
zamkniętego okna zostały odebrane. Nie wznawiamy fazy prototypu.

166 zaczyna szeroką macierz odbioru dopiero po zintegrowaniu 164.S i 165.S.
Insider Feed/robot i inne Super Powers testujemy na właściwym systemie,
nie w kolejnej rozbudowie ograniczonego pilota. Zgoda operatora na wszystkie
niezbędne testy 164–166 pozostaje ważna; nie żądać osobnych zgód na każdą próbę.
Nie utożsamiać jej z dowodem PASS ani automatycznym uruchomieniem globalnego rollout.

### 166.S — jedna zbiorcza macierz po implementacji

| Grupa | Obowiązkowy odbiór |
| --- | --- |
| Konta/aplikacje | Różni gracze, nowe i zgodne historyczne aplikacje, wspólne archiwum bez wspólnego dostępu, komplet interfejsów |
| Kamery/lokalizacje | Sklep, ATM, inne POI, kanoniczne i obsługiwane legacy, różne lokalizacje/coverage/kierunki/proporcje fotografii |
| Czas i moce | Zwykłe 30 min, inne rzeczywiste czasy, robot z insider_feed, moc przy starcie i w trakcie; jeden kanoniczny zegar |
| Profil feedu | 1/2/3 zdjęcia, nowe losowanie foto+motion+FX/offline, utrwalenie po reconnect, nowy tor przy tym samym zdjęciu; brak losowania po retry |
| Lifecycle | Failure, pełny dysk, późny aktywator/materiał, dwie karty, wiele okien, restart osobnych procesów, close/relogin/new hack; bez duplikatów |
| Incydenty | camera_off/shutdown/risk i czas oddziaływania bez zmian; wizualne offline nie zmienia świata ani kosztów |
| Źródło i utrzymanie | 429/timeout/no coverage/withdraw/expiry/GC/restore, budżety/fairness, brak ponownego pozyskania wycofanego materiału, sekrety i CDN |
| UI i skala | PL/EN, desktop/mobile/PWA, reduced-motion/focus, nawigacja/atrybucja, p95/CPU/RSS/polling, brak regresji skanera |

Lokalne scenariusze wykonać w kontrolowanej grze/fixtures przez Playwright MCP
i właściwe testy domenowe. VPS służy nowym dowodom integracji procesów,
rzeczywistego API/PWA i obciążenia; nie powtarzać całej historii bez przyczyny.

### 166.R — przygotowanie i wdrożenie globalne

1. Jeden raport gotowości dla S1–S3: kod, migracja/kompatybilność grantów,
   macierz testów, konfiguracja trzech ról procesów, limity/retencja/sekrety,
   rollback zachowujący consumed i tombstones oraz jawne braki dowodów.
2. Standardowy commit/push/deployment po decyzji operatora; żadnych ZIP-ów
   i alternatywnych kopii repo. Zbiorcze wdrożenie i odbiór zamiast drobnych sesji.
3. Docelowe prawa/retencja/backup i L01/L02 muszą mieć evidence; testowe 24 h
   i działający token nie są polityką globalnej publikacji.
4. Docelowy zakres obejmuje wszystkie kamery i wszystkich użytkowników.
   Kontrolowane uruchomienie/monitoring to sposób odbioru, nie trwała lista main.
   Dopuszczenie nowych kamer nie wymaga ręcznego enqueue lub konfiguracji kont.
5. Defekty: diagnostyka → poprawka lokalna → właściwa regresja → kontrolowane
   wdrożenie; wznowienie od miejsca błędu. Bez resetowania danych dla PASS.

Zamknięcie 166 wymaga całej macierzy lub jawnie uzgodnionego wyłączenia
konkretnego wymagania. Nie oznaczać DONE na podstawie samej globalnej flagi,
pilota jednej kamery ani samego screenshotu. Zachować zakaz zdjęć graczy,
Camera Creator, Vision, ciężkich profili i historycznych kolejek/procedur.

## Historyczny plan pierwszego pilota (31.10.2026)

Poniższe etapy źródła dotyczą pierwszego zakresu 165.1; ich aktualne dowody
i niewykonane elementy rozdziela audyt z 01.11. Zastępuje je powyższy plan systemowy.

31.10.2026. PLAN, nowy zakres nadany przez operatora; nie sprint zdjęć graczy.
Zależności: lokalny pakiet 164–165, PASS prezentacji, decyzja o wdrożeniu.

Pakiet/paczka oznacza zakres kodu w repo, nie ZIP. Obowiązuje standardowy Git:
zatwierdzenie → commit/push → zbiorcze wdrożenie OFF → pilot rzeczywistego API.
[Wspólna procedura dwóch sesji i rollback](../runbooks/camera_street_view_package_165_1.md).
Defekty odbioru poprawiamy lokalnie i wdrażamy kontrolowaną aktualizacją;
nie rozbijamy zakresu na dziesiątki sesji ani nie ponawiamy PASS bez przyczyny.

1. Wdrożyć gotową paczkę po poleceniu operatora, z backupem i rollback.
2. Odebrać na rzeczywistym źródle adapter i archiwum przygotowane lokalnie
   w 164–165. Zamknąć bramki L01/L02: retencja, wycofania i linkowanie.
   Implementacja adaptera i testy fixtures należą do pierwszej paczki, nie do tego etapu.
3. Podłączyć sekret istniejącym mechanizmem środowiska. Klucz tylko na backendzie,
   diagnostyka present/valid, nigdy sekret w przeglądarce lub repo.
4. Kontrolowany pilot jednej kamery: skan/serwerowa tożsamość → aplikacja →
   sukces → rzeczywisty czas pobrania z mocami → plik → jednorazowe okno.
5. Zweryfikować brak pokrycia, timeout, limity, prawa/źródło, wycofanie obrazu,
   restart, ponowne logowanie, zamknięcie i nowe hakowanie. Potem ograniczony rollout.

Osobne statusy: LOCAL PASS / wdrożone / live provider PASS / VPS PASS.
Żaden dotychczasowy PASS syntetycznych zdjęć nie dowodzi działania API.
Brak zgody na zdjęcia graczy, aparat/GPS, Vision, rozpoznawanie osób i moderację.
Nie uruchamiać historycznych procedur VPS ani dawnych kolejek.
