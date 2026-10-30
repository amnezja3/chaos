# Sprint 165 — Camera Visual Network: terminal, administracja i rollout

Data: 24.10.2026. Status: **PLAN — po akceptacji prototypu 164.0 i archiwum 164**.
Źródło: [koncepcja](../prototypes/camera_view/CHAOS%20%E2%80%94%20CAMERA%20VISUAL%20NETWORK.md).
Zależność: [164](sprint_164_camera_visual_archive.md).
Uzupełnienie 24.10.2026: konspekt operatora „Licencjonowanie Mapillary,
atrybucja i nawigacja zewnętrzna”; bramki dostawcy opisane w 164.1.

## Cel

Dołączyć gotowe archiwum do istniejącego „Podglądu kamery”, w oknie CHAOS,
z lekką symulacją monitoringu oraz kontrolą integracji w adminie.
Sam podgląd i panel informacji pozostają w grze. Wyjście do źródła następuje
wyłącznie po świadomym potwierdzeniu opisanym poniżej. Animacje działają na zdjęciach,
bez serwerowego renderowania wideo, panoram i swobodnego Street View.

Pierwszy krok całego przedsięwzięcia to **prototyp jednej kamery w 164.0
i jawna akceptacja autora**, przed rozbudową infrastruktury. Ten sprint
rozwija zaakceptowany wzorzec, nie odkłada oceny wyglądu na koniec projektu.
Testy techniczne nie zastępują odpowiedzi autora, czy podgląd daje poczucie
przejęcia systemu obserwacyjnego w świecie CHAOS.

Etapy odbioru osobno: zaakceptowany prototyp → archiwum lokalne → pojedynczy pilot
Mapillary → restart/rollback → ograniczony rollout. Nie aktywować dostawcy
ani workera przy samym wdrożeniu schematu i interfejsu.

## 165.0 — integracja z działającą akcją

### Ghost System → aplikacja → operacja → CVN → podgląd

Każda kompatybilna aplikacja do podglądu kamer wygenerowana przez Ghost System
automatycznie korzysta z istniejącego okna i wspólnego archiwum CVN, bez ręcznego
dopisywania funkcji do wydań. Wykorzystać kontrakt/projekcję
`camera_visual_preview` z 164.1, istniejące `map_actions`, walidację celu
i wykonawcę `camera_stream`; nie dodawać równoległego systemu kamer.

Ścieżka odbioru: wygenerowanie/publikacja i instalacja aplikacji → wybór narzędzia
z mapy → autoryzowana istniejąca operacja kamery → wspólny manifest/zadanie CVN
→ istniejący podgląd ze wszystkimi stanami z 165.2, licencją i nawigacją.
Brak zdjęć lub błąd CVN nie zmienia wyniku ani kosztu operacji gry.
Różne interfejsy aplikacji przekazują kontekst do tego samego podglądu;
nie wymagać zmiany `interface` na `window` ani tworzyć drugiej operacji.

Przeprowadzić tę ścieżkę także dla aplikacji wygenerowanych wcześniej,
opublikowanych i już zainstalowanych. Zgodne kontrakty otrzymują podgląd przez
projekcję runtime bez regenerowania, ponownego zakupu i zmiany mechaniki.
Nie obchodzić walidacji `creator_updates.py`/`creator_legacy.py`; niezgodne
wydania zachowują dotychczasowe działanie, a raport wskazuje powód braku CVN.
Ponowne otwarcie albo druga zgodna aplikacja do tej samej kamery korzystają
ze wspólnego archiwum, z niezależną autoryzacją i bez podwójnego naliczenia.

Obowiązują wyłączenia z 164.1: bez CAMERA CREATOR, instalowania kamer,
zdjęć graczy, aparatu/GPS, Vision, zamazywania twarzy/tablic, moderacji
i `PLAYER_UPLOAD`; bez infrastruktury na zapas i bez nowego Sprintu 166.

Po zaakceptowaniu istniejącej operacji kamera może odczytać manifest lub
zgłosić deduplikowane zadanie. Ponowne otwarcie okna nie uruchamia ponownie
operacji gry ani jej efektów. Wspólny archiwalny obraz nie jest zasobem
camera_dump i nie zmienia jego pochodzenia, wartości ani przyznawania.

Planowane endpointy: autoryzowany odczyt manifestu po operation_id/camera_id,
POST zapewniający zadanie (CSRF/idempotencja) i kontrolowany odczyt medium.
Ostateczne nazwy zgodne z istniejącym routerem. Wszystkie ścieżki sprawdzają
aktualne uprawnienie do akcji; trudny do odgadnięcia URL nie zastępuje kontroli
dostępu. Zamykanie okna przerywa polling i animacje, **nie anuluje przyjętego
zadania**. Kolejka realizuje je do READY lub stanu końcowego w limitach 164.3.
Reopen dołącza do istniejącego zadania/archiwum bez nowego kosztu; wygaśnięcie
TTL i anulowanie administracyjne działają niezależnie od okna. Cofnięcie
uprawnień gracza zatrzymuje dalsze udostępnianie, a cofnięcie zgody dostawcy
zatrzymuje także pozyskiwanie/publikację zgodnie z zakresem cofnięcia.

Odświeżanie ma backoff i deadline, tylko przy widocznym oknie; współdzielić
istniejące zdarzenia/delty, jeśli pasują. Przeglądarka nie odpytuje Mapillary
i nie trzyma tokena ani źródłowych podpisanych URL. Media: właściwe nagłówki
cache/autoryzacji, brak publicznego indeksu i globalnego cache service workera
dającego dostęp po wylogowaniu.

## 165.1 — terminal monitoringu PL/EN

Jedno okno na kamerę, zgodnie z istniejącą deduplikacją. Zawartość:
obraz, identyfikator kamery, stan warstwy wizualnej, informacja o położeniu
ujęcia względem celu, data wykonania lub „data nieznana”, źródło, autor,
licencja i odnośnik do oryginału. Atrybucja czytelna również na telefonie.

Stałe oznaczenie **„Materiał archiwalny — symulacja, nie transmisja na żywo”**
(EN odpowiednik). Zegar gry 2108 i status połączenia terminala nie udają
czasu wykonania fotografii. Pozycja zdjęcia nie jest przedstawiana jako
dokładna pozycja fizycznej kamery; tekst „otoczenie lokalizacji”.

Maksymalnie trzy zdjęcia, delikatny pan/zoom w granicach kadru, zmiana ujęcia,
scanlines, szum i sporadyczny glitch. Efekty CSS/canvas, nie nowe wygenerowane
fotografie udające rzeczywiste miejsce. Brak obrazu nigdy nie zastępowany
losowym zdjęciem innego miasta. Przy jednym zdjęciu nie wymuszać zmiany ujęć.
Automatyczne przejścia wykorzystują wyłącznie spójny kierunkowo zestaw z 164.2.
Nie sugerować obrotu fizycznej kamery przez losowy przeskok na przeciwny
kierunek ulicy. Nieznany azymut nie otrzymuje wymyślonej strzałki kompasu.
Kadrowanie nie może usuwać istotnego otoczenia tylko dla dopasowania do HUD.
Do okna trafiają lokalnie przetworzone miniatury, bez oryginałów i ich URL.

Obsłużyć prefers-reduced-motion, pauzę efektów, klawiaturę/focus, czytelny
kontrast, utratę kontekstu canvas i błąd ładowania medium. Domyślnie bez audio;
ewentualny dźwięk wyłącznie po świadomym włączeniu. Zero agresywnego migotania.
Ukryte/zminimalizowane okno wstrzymuje animacje i odpytywanie.

### 165.1a — atrybucja fotografii i kontrolowana nawigacja

Uzupełnienie 30.10.2026: osobny panel **„Licencja i źródło zdjęcia”**,
dostępny przy każdej fotografii, niezależnie od publicznej strony źródeł danych.
Pokazuje prawa CC BY-SA i metadane z 164.1 bez dodatkowego warunku akceptacji
ograniczającego te prawa. Wdrożenie wymaga rozstrzygnięcia **L01** (archiwizacja
i udostępnianie) oraz **L02** (logo i linkowanie) z 164; projekt UX nie stanowi
rozstrzygnięcia żadnej z tych kwestii.

Przy fotografii Mapillary umieścić niewielkie, czytelne logo dostawcy oraz
ikonę informacji. Nie zakrywać ich HUD-em, kadrowaniem ani glitchem. Wygląd
zgodny z CHAOS przy zachowaniu zweryfikowanych zasad używania znaku.
Kliknięcie logo lub ikony otwiera wewnętrzny panel CHAOS, bez nowej karty,
przeładowania gry, zatrzymania podglądu ani nowych operacji gameplayu.

Panel pokazuje dla bieżącego image_id:

- Mapillary, autora, datę wykonania (jeżeli dostępna) i identyfikator fotografii;
- właściwą licencję CC BY-SA wraz ze zweryfikowaną wersją i odnośnikiem;
- rzeczywiste zmiany z manifestu 164.1, w tym skalowanie/konwersję, jeśli wykonane;
- publiczny adres oryginalnej fotografii, „Kopiuj adres” i aktywne „Otwórz źródło”.

Przy zmianie ujęcia aktualizować cały panel razem z obrazem. W chwili kliknięcia
„Otwórz źródło” zamrozić docelowy image_id/URL dla potwierdzenia: automatyczna
zmiana kadru nie może przekierować do innej fotografii niż wybrana.
Kopiowanie ma komunikat sukcesu/błędu obok przycisku; przy braku uprawnień
schowka umożliwić ręczne skopiowanie widocznego URL. Nie kopiować signed URL/tokena.

„Otwórz źródło” wyświetla wewnętrzne potwierdzenie **EXTERNAL CONNECTION**:

> Zamierzasz opuścić środowisko CHAOS i przejść do zewnętrznego serwisu Mapillary.
> Spowoduje to opuszczenie bieżącego widoku gry. W zależności od sposobu
> uruchomienia aplikacji może nastąpić przełączenie do przeglądarki.
> Czy chcesz kontynuować?

Przyciski: **POZOSTAŃ W CHAOS** / **OTWÓRZ MAPILLARY**.

EN:

> You are about to leave CHAOS and visit the external Mapillary service.
> This will leave the current game view. Depending on how the app was launched,
> you may be switched to a browser. Do you want to continue?

Przyciski: **STAY IN CHAOS** / **OPEN MAPILLARY**.

Anulowanie lub Escape zamyka potwierdzenie, przywraca focus i zachowuje stan
gry, kamery i kolejki. Potwierdzenie wykonuje rzeczywistą nawigację do wskazanej
fotografii lub strony dostawcy. Preferować ten sam kontekst nawigacji; nie
używać automatycznego window.open ani target=_blank. Zweryfikować publiczny
HTTPS URL i host źródła, bez dowolnych adresów/schematów z manifestu.
Zachowanie systemowego otwarcia PWA wymaga pomiaru; nie obiecywać pełnej kontroli
nad przeglądarką/OS ani zachowania identycznego z desktopem.
Nie wywoływać logout i nie deklarować automatycznego wylogowania; powrót
podlega normalnym zasadom ważności sesji. Nawigacja nie anuluje przyjętego
zadania archiwizacji, które nadal obowiązują limity i zasady z 164.3.

Dwuetapowy mechanizm linkowania jest wymaganiem produktu, **nie potwierdzonym
stanowiskiem Mapillary**. Wymaga rozstrzygnięcia bramki 164.1 przed produkcją.
Aktywny odnośnik pozostaje dostępny; ostrzeżenie ani tekst URL go nie zastępują.
Jeżeli warunki wymagają bezpośredniego linku logo, wrócić z konkretnym konfliktem
do decyzji operatora, bez cichej zmiany UX. WebDragon, iframe i mechanizm podobny
do OAuth2 pozostają poza zakresem.

### 165.1b — publiczne „Źródła danych” / “Data sources”

Na bramce logowania, obok Polityki prywatności i Warunków korzystania, dodać
link otwierający wewnętrzny panel lub stronę CHAOS dostępną bez logowania.
Użyć istniejącego routingu i stylu gatewaya. Wykaz obejmuje rzeczywiście
wykorzystywanych dostawców, bez przedstawiania planowanych integracji jako aktywnych.
Sekcja Mapillary zawiera logo, opis zastosowania archiwalnych fotografii,
zweryfikowane informacje licencyjne i aktywny link do dostawcy. Przed aktywacją
oznaczyć integrację jako planowaną/testową, jeżeli sekcja jest już publikowana.
Link zewnętrzny korzysta z tej samej świadomej nawigacji; PL/EN i focus/klawiatura
działają także bez sesji. Strona nie ujawnia sekretów ani prywatnych manifestów.
Wykaz źródeł nie zastępuje atrybucji przy każdej prezentowanej fotografii.

## 165.2 — stany i komunikaty

| Stan techniczny | Prezentacja | Zasada |
| --- | --- | --- |
| QUEUED/FETCHING/PROCESSING | SYNCHRONIZING | Ograniczony polling, bez kolejnych pobrań od odświeżenia |
| READY | Archiwalne ujęcia | Widoczna atrybucja i oznaczenie symulacji |
| REVOKED | Materiał wycofany | Usunąć obraz z podglądu i listy ujęć, bez powrotu do jego starej kopii |
| FAILED | SIGNAL LOST / materiał niedostępny | Zakończone zadanie, przyczyna w adminie; bez pętli retry w UI |
| EXPIRED | Przygotowanie wygasło | Zakończony TTL zadania; nowe zlecenie tylko przez normalną walidację i limity |
| NO_COVERAGE | NO SIGNAL | Brak materiału nie wyłącza kamery w gameplayu |
| DEFERRED/budżet/polityka | CAMERA OFFLINE / materiał niedostępny | Bez twierdzenia, że urządzenie zostało wyłączone |
| Timeout/utrata odpowiedzi | SIGNAL LOST | Zachować dozwolony lokalny materiał, jeśli jest dostępny |
| Rzeczywisty błąd pliku | ARCHIVE CORRUPTED | Kwarantanna/naprawa, nie pętla pobierania |
| Efekt estetyczny | SIGNAL UNSTABLE | Nie zmienia technicznego statusu ani mechanik |

Dokładny powód w adminie i logu technicznym. Komunikat gracza przy obrazie
lub przycisku, bez dużej belki na mapie. Pseudolosowe warianty deterministyczne
dla sesji okna i nigdy nie zmieniają autoryzacji. Obowiązujący shutdown pokazuje
dotychczasowy stan gry; obraz nie obchodzi blokady dostępu.

## 165.3 — panel administracyjny

Sekcja „Camera Visual Network” w istniejącym side menu, PL/EN, desktop/mobile.
Ponownie użyć wzorców admin autoryzacji, CSRF, inline messaging i optimistic
revision z POI, ale oddzielić integrację wizualną od hierarchii skanera.
Mapillary nie jest fallbackiem dla POI ani źródłem dowodu world coverage.

- Dostawca: gotowość sekretu (nigdy wartość), stan zatwierdzenia, zakres
  test/search/download/transform/archive/serve, źródła i data przeglądu.
- Osobny stan weryfikacji atrybucji/linkowania, archiwizacji, wycofania i użycia
  w grze; evidence oraz przyczyny niedopuszczenia konkretnych fotografii.
  Sam enabled ani akceptacja dokumentacji nie odblokowują niepotwierdzonych praw.
- Sterowanie osobno: UI, nowe pozyskiwanie, worker, odczyt istniejących zdjęć.
  Wyłączenie acquisition nie usuwa archiwum; cofnięcie prawa serve je blokuje.
- Limity: requests/doba, nowe archiwa/doba, transfer, quota/low-disk,
  concurrency i retry; defaults OFF, bez nieograniczonych wartości.
- Obraz: maksymalny rozmiar, WebP quality, liczba zdjęć, promień;
  dozwolone warianty miniatur i tolerancja kierunku, stan UNKNOWN bez heading;
  zmiana tworzy nową wersję profilu, nie przebudowuje masowo całej bazy.
- Statystyki: archiwa/obrazy/bajty, local hit, brak pokrycia, kolejka,
  ostatni wynik workera, API attempts; zakres czasowy i źródło pomiaru.
- Retry wybranego zadania respektuje limit i backoff. Usunięcie/wycofanie
  ma potwierdzenie oraz przegląd referencji; cofnięcie publikacji natychmiast,
  zwolnienie nieużywanych bajtów przez ograniczony GC.
- Wycofanie pokazuje wszystkie powiązane archiwa i warianty, zakres decyzji,
  blokadę ponownego pobrania oraz postęp usuwania z cache/plików/backupów.
  Osobne statusy L01 i L02 z evidence; nie zastępować ich jednym „enabled”.

Odczyt panelu i statystyk nie generuje zewnętrznego HTTP. Zmiany audytowane
bez tokenów i pełnej historii ruchów graczy. UI pokazuje realną dostępność,
nie sam status „enabled”. Nie budować drugiego menedżera sekretów; wykorzystać
obecną konfigurację serwerową, zapisywać jedynie secret reference.

## 165.4 — testy i pomiary

Realizacja według stałej polityki LOCAL-FIRST z 164: najpierw kompletne pakiety
A/B/C i raport gotowości, następnie zbiorcze wdrożenie/odbiór. Testy możliwe
lokalnie nie są osobnymi sesjami VPS. Przed rolloutem udokumentować:

- Generator/publikację/instalację i uruchomienie z mapy dla każdego wspieranego
  interfejsu oraz zgodnych wydań historycznych; bez ręcznego dopisywania podglądu.
- Pełną ścieżkę Ghost System → istniejąca operacja → CVN → okno, zamknięcie
  i reopen, współdzielenie zdjęć przez dwie aplikacje i dwóch graczy.
- Odmowę dla shutdown-only, sfałszowanej zdolności, cudzej/wygasłej operacji;
  wszystkie stany kolejki/UI, brak podwójnych operacji, opłat i zasobów.
- Porównanie mechaniki i kontraktów przed/po: ceny, czasy, ryzyko, uprawnienia,
  shutdown oraz camera_dump bez zmian. Brak automatycznej przebudowy starych wydań.

Wykorzystać istniejące testy creator policy/routes/legacy, fixture
`tools/creator_browser_fixture.py`, testy runtime kamer i deduplikacji okna.
Dołożyć scenariusze do istniejącej ścieżki, nie budować alternatywnego launchera.

Playwright MCP z izolowanym kontem/danymi: realna akcja → okno → READY,
NO_COVERAGE, błąd, restart/reopen; PL/EN desktop/mobile, mały ekran, reduced
motion, focus, inline feedback, brak nowej karty, brak sekretów/API dostawcy
w ruchu przeglądarki, błędy konsoli i duplikaty okien. Nie wymagać ręcznego
testu użytkownika zamiast dostępnej lokalnej automatyzacji.

Osobna macierz atrybucji/nawigacji: desktop web, telefon web oraz rzeczywiście
zainstalowana PWA na dostępnych platformach. Emulacja viewportu nie zalicza PWA.
Wszystko odtwarzalne lokalnie sprawdzić przed wdrożeniem; rzeczywistą nawigację
zainstalowanej PWA odebrać zbiorczo na dostępnych urządzeniach. Brak urządzenia
pozostaje jawną luką dowodową, nie powodem powtarzania testów na VPS.
Zapisać przeglądarkę/OS/tryb uruchomienia, powrót i stan sesji. Bez środowiska PWA
oznaczyć brak dowodu, nie PASS. Sprawdzić:

- Logo/info otwiera panel wewnętrzny, bez popupu i dodatkowego żądania dostawcy;
  podgląd trwa, gameplay i kolejka pozostają bez dodatkowych skutków.
- Autor/licencja/zmiany odpowiadają każdej z 1–3 fotografii; zmiana zdjęcia
  podczas otwartego panelu nie pozostawia poprzednich metadanych.
- Kopiowanie oraz odmowa schowka; link rzeczywiście istnieje, ma właściwy cel,
  a potwierdzenie nie zmienia go wskutek automatycznej zmiany kadru.
- Anulowanie, Escape i ponowne otwarcie zachowują stan i focus; brak wyjścia.
- Potwierdzenie prowadzi do źródła, bez wymuszonego logout i niekontrolowanych
  dodatkowych okien. Zewnętrzną nawigację najpierw testować na kontrolowanej
  stronie testowej; rzeczywistego Mapillary dopiero w zatwierdzonym odbiorze.
- Publiczne „Źródła danych” bez logowania, PL/EN i mobilnie; działające linki,
  brak zastępowania atrybucji zdjęcia ogólną stroną dostawców.
- Logo pozostaje widoczne w podglądzie na małym ekranie, po zmianie orientacji,
  podczas efektów i zmiany ujęcia; panel licencji działa klawiaturą i dotykiem.
- W zainstalowanej PWA sprawdzić wycofanie podczas podglądu, powrót z tła,
  offline/online i ponowne otwarcie: kontrolowane cache i service worker nie
  przywracają wycofanego zdjęcia. Przed ponownym pokazaniem po wznowieniu
  zweryfikować dopuszczenie; brak weryfikacji oznacza materiał niedostępny.
  Nie obiecywać usunięcia kopii zapisanych samodzielnie poza aplikacją.

Backend: równoległe kamery w tej samej okolicy, read access po wylogowaniu,
shutdown/expiry i zmiana właściciela operacji, cofnięcie zgody w czasie pobrania,
rate limit, brak dysku, wycofanie współdzielonego zdjęcia, restart workera,
backup/restore/GC. Weryfikacja braku dodatkowych efektów operacji i naliczeń.
Osobno: zamknięcie podczas kolejki/pobierania/obróbki, ukończenie bez widza,
reopen z READY, drugi gracz, TTL oczekiwania i brak powtórnego kosztu.
Kontrola wizualna obejmuje zgodność z zaakceptowanym prototypem 164.0;
istotne zmiany rytmu, kadrowania lub HUD wymagają ponownego odbioru autora.

Zmierzyć czas local hit i enqueue, RSS workera, CPU dekodowania, liczbę/bajty
żądań, rozmiar archiwum, płynność UI. Cel pilota: local response p95 <250 ms
na VPS przy opisanym obciążeniu; etap async mieści się w twardym deadline
164, z fallbackiem po timeout. Mała próbka nie wystarcza do deklaracji p95.
Porównać opóźnienia skanera przed/podczas pilota; fotografie nie mogą wyczerpać
zasobów procesu web ani spowodować regresji aktualnych skanów MapLark.

## 165.5 — pilot, wdrożenie i rollback

1. Potwierdzić zapis akceptacji prototypu 164.0, kontrakt i testy offline 164;
   potwierdzić warunki Mapillary, w tym dwuetapowe linkowanie/logo, archiwizację,
   ponowne udostępnianie, wycofanie oraz dostęp zależny od gameplayu,
   token i dozwolone użycie/retencję. Operator zatwierdza ograniczony budżet.
2. Backup spójnej bazy i mediów, dry-run migracji; wdrożenie z flagami OFF.
   Konfiguracja w `ecosystem.web.config.js`; worker w dedykowanej konfiguracji
   ecosystem, bez jednorazowych env jako docelowego źródła ustawień.
3. Jedno wskazane konto i 1–3 kamery; proponowany sufit pilota: 10 archiwów,
   100 żądań API, 100 MiB transferu i concurrency=1. To propozycja do akceptacji,
   nie zgoda na automatyczne pobrania. Osobno mały limit dysku z rezerwą.
4. Pierwsze pozyskanie, kolejne otwarcie bez zewnętrznych żądań, współdzielenie
   między kamerami tylko w poprawnej odległości, restart i odczyt lokalny.
5. Awaria dostawcy/limit → fallback; wyłączenie acquisition → istniejący
   podgląd działa o ile serve nadal dozwolone; cofnięcie serve → zdjęcia niedostępne.
6. Rollback: UI/acquisition/worker OFF, dotychczasowy podgląd i gameplay
   zachowane. Nie cofać bazy w sposób kasujący historię zużycia/praw do materiałów.
7. Odbiór operatora, dopiero potem większy zakres i `pm2 save` po sprawdzeniu
   właściwych procesów. Brak automatycznej publikacji przy commicie/pushu.
   Odbiór obejmuje źródła publiczne, atrybucję każdej fotografii i rzeczywistą
   nawigację desktop/mobile/PWA; nie zamykać bramki PWA samym testem desktopu.

Proponowane flagi: `CHAOS_CAMERA_VISUAL_ENABLED`,
`CHAOS_CAMERA_VISUAL_ACQUISITION_ENABLED`, `CHAOS_CAMERA_VISUAL_WORKER_ENABLED`,
`CHAOS_CAMERA_VISUAL_SERVE_ENABLED`; początkowo wszystkie 0. Nazwy ostateczne
ustalić przy implementacji, nie opisywać ich jako już istniejących.

## Decyzje potrzebne przed pilotem, nie przed pracą offline

Konto/token Mapillary; potwierdzone zasady archiwizacji, modyfikacji i atrybucji;
retencja/usuwanie zdjęć; dozwolony limit dysku i transferu; konto/kamery pilota.
Ewentualne zmiany publicznej polityki prywatności opierają się na rzeczywistym
przepływie (serwer CHAOS → dostawca, współrzędne celu bez nicku/user_id).
Nie przesyłać dostawcy profilu gracza ani jego sesji.

## Definicja ukończenia

164: najpierw zaakceptowany wygląd i zachowanie pojedynczej kamery, następnie
kontrakt, trwałe archiwum i ograniczone pozyskiwanie miniatur z dowodami testów.
165: okno/admin, pomiary, rzeczywisty pilot, odczyt po restarcie oraz rollback
odebrane osobno. Nie zamykać obu sprintów samym screenshotem lub HTTP 200.
Deliverables: kod, fixtures/testy, runbook VPS, evidence, konfiguracja ecosystem
i lista otwartych decyzji. Za zakresem: analiza obrazów AI, nowe mechaniki
wywiadowcze/klanowe, rozpoznawanie osób, panoramy oraz pobieranie całego świata.
Także poza zakresem: WebDragon, iframe i przepływ podobny do OAuth2.
Potwierdzenie planu lub wyglądu prototypu nie jest zgodą na produkcyjne API.
