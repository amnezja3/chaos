# Sprint 164 — Camera Visual Network: prototyp kamery, kontrakt i archiwum

Zasada workflow 164–166: „paczka implementacyjna” to zamknięty, zintegrowany
i lokalnie przetestowany zakres w repozytorium. Wdrożenie przez standardowy
Git commit/push po decyzji operatora; bez ZIP-ów i kopii repozytorium.
Powiązane podetapy realizujemy i odbieramy zbiorczo.

Data: 24.10.2026. Aktualizacja 31.10.2026: **164.0 PASS operatora; pierwsza paczka 165.1 zweryfikowana lokalnie**.

[Raport paczki i granice PASS](../audits/camera_street_view_package_165_1.md).
Adapter sprawdzony na fixtures; odbiór rzeczywistego źródła pozostaje w 166.

## Aktualny kontrakt — Camera Street View (nadrzędny)

Operator zaakceptował podgląd, okno, zakłócenia i brak sygnału. Zabezpieczony
[snapshot prezentacji](../prototypes/camera_view/accepted_164_0_2026_10_31/README.md)
jest wzorcem dalszego kodu. Poniższe wcześniejsze opisy stałych 30 minut oraz
ponownego otwierania są historią pilota, zastąpioną tym kontraktem:

- Kamera jest istniejącym obiektem świata, również generowanym przy POI.
  Tożsamość i skan pochodzą z CameraContractStore. Shutdown i wpływ na incydenty
  pozostają w Response Network.
- Sukces → SESSION CLOSE → jedna kanoniczna operacja pobrania → potwierdzony
  zapis aktywatora → automatyczne otwarcie jednej instancji.
- Czas pochodzi z terminów operacji gameplayu (np. 1800 lub 300 s), z tego samego
  realizera Super Powers, także dla przyspieszenia trwającej operacji.
- Ręczne zamknięcie zużywa dostęp trwale. Retry, stare pliki i reopen nie
  uruchamiają go ponownie. Reload/utrata połączenia nie są ręcznym zamknięciem.
- Nowe hakowanie po zamknięciu daje nową operację, pobranie, instancję i losowy
  tor na jednym wybranym zdjęciu. Retry jednego receipt pozostaje idempotentne.
- 164: kontrakt, zabezpieczenie prezentacji, kanoniczny lifecycle, adapter i archiwum lokalne.
  165: integracja kamer świata, regresja i pierwsza paczka VPS.
  [166](sprint_166_camera_street_view_live.md): podłączenie prawdziwego źródła
  przez sekrety, kontrolowany odbiór VPS i rollout. Bez fotografii graczy.

Pozostały zakres archiwum/adaptora poniżej jest planem dalszej integracji,
nie deklaracją gotowego dostawcy ani zgody na wywołania API.

## Historia planu i pilota
Aktualizacja 31.10.2026: **164.0 działający pilot lokalny — DO ODBIORU autora**.
[Implementacja i testy na rzeczywistym pulpicie](../audits/camera_visual_gameplay_164_0.md).
Osobne demonstratory A/B nie realizowały tego etapu; ich rozwój jest zatrzymany.
[Historia prób i ograniczenia dowodów](../audits/camera_visual_prototype_164_0.md).
164.1–164.5 nadal PLAN, bez rozpoczęcia infrastruktury i bez aktywacji dostawcy.
Źródło: [Camera Visual Network](../prototypes/camera_view/CHAOS%20%E2%80%94%20CAMERA%20VISUAL%20NETWORK.md).
Kontynuacja: [165 — interfejs, administracja i rollout](sprint_165_camera_visual_network_rollout.md).
Uzupełnienie 24.10.2026: konspekt operatora „Licencjonowanie Mapillary,
atrybucja i nawigacja zewnętrzna”. Wymagania produktu przyjęte do planu;
warunki dostawcy wymagają odrębnej weryfikacji przed aktywacją.

## Cel i granice

Przygotować archiwum maksymalnie trzech fotografii rzeczywistego otoczenia
kamery, pozyskiwanych na żądanie przez backend. Pierwszym dostawcą jest
Mapillary. Efektem jest zestaw zoptymalizowanych zdjęć i manifest pochodzenia,
nie transmisja live ani plik wideo. Zdjęcie ulicy w pobliżu nie jest dowodem
widoku z konkretnego urządzenia monitoringu.

Warstwa wizualna nie zmienia kosztów, czasu, uprawnień, shutdown, heat,
eskalacji, nagród, fragmentów camera_dump ani mechanik PvP. Błąd pozyskiwania
nie cofa poprawnie wykonanej operacji gry. Nie dodajemy rozpoznawania twarzy,
tablic, śledzenia osób ani AI analizującego fotografowane osoby.

Prace offline nie wymagają zamknięcia całego 161–163. Rzeczywiste pobrania
wymagają odrębnego zatwierdzenia dostawcy i limitu pilota. Nie zużywają
budżetów MapLark/Geoapify i nie uruchamiają World Discovery background.

## Kolejność realizacji — najpierw doświadczenie gracza

### Stała zasada realizacji CHAOS: LOCAL-FIRST

Polityka dotyczy również kolejnych sprintów rozwijających istniejące systemy:
repozytorium i lokalne środowisko są podstawowym miejscem implementacji oraz
regresji; VPS służy odbiorowi gotowej integracji i pomiarom wymagającym serwera.
W ramach tej aktualizacji zapisujemy politykę wyłącznie w sprintach 164–165.
Nie zmienia ona poniższej obowiązkowej kolejności prototypu 164.0.

Po akceptacji prototypu przygotować kompletne pakiety:

- **A — backend:** kontrakty Ghost System i dostawcy, adapter, dobór miniatur,
  optymalizacja, wspólne archiwum, deduplikacja, kolejka/worker, wycofania, migracje.
- **B — integracja:** wygenerowane aplikacje, istniejąca operacja i okno kamery,
  stany awaryjne, licencje/nawigacja, administracja i publiczne źródła danych.
- **C — odbiór lokalny:** fixtures, testy jednostkowe, integracyjne, bezpieczeństwa,
  regresja gameplayu, backup/restore na danych testowych i Playwright MCP.

Pakiety można realizować ciągle, z testami wewnętrznymi, bez wdrożenia każdego
podetapu. Jeśli brakuje danych, przygotować jedną listę i zebrać je w opcjonalnej
sesji diagnostycznej, preferując odczyt, anonimowe próbki i konfigurację bez
sekretów; nie kopiować zbędnych danych graczy. Przed wdrożeniem jeden raport:
ukończony zakres, wyniki testów i poprawki, zgodność gameplayu, migracje/env,
rollback, otwarte kwestie oraz uzasadnione testy możliwe dopiero na serwerze.
Lokalne błędy blokują wdrożenie; test wymagający rzeczywistego środowiska musi
mieć jawnie zapisany wyjątek, a nie fikcyjny PASS.

Domyślnie 2–3 zaplanowane sesje dla całego zakresu: opcjonalna diagnostyka,
wdrożenie kompletnego pakietu i kontrolowany pilot/odbiór. To plan, nie zakaz
reakcji na awarię. Błąd VPS: zebrać diagnostykę, poprawić lokalnie, wykonać
regresję i wrócić z poprawionym pakietem. Nie powtarzać na VPS sprawdzeń
dostępnych lokalnie. Wyjątki: awarie krytyczne i problemy nieodtwarzalne lokalnie.

**164.0 działający pilot jednej kamery w grze → jawna akceptacja autora →
164.1–164.5 rozbudowa infrastruktury → 165 rozszerzenie integracji i rollout.**
Nie rozpoczynać rozbudowy kolejki, archiwum i panelu przed zaakceptowaniem pilota.
Już 164.0 wymaga rzeczywistej integracji aplikacji, autoryzacji, operacji,
zapisu aktywatora i okna. Wykonać niezbędne zmiany istniejącego runtime oraz
trwałego stanu; nie odkładać tej ścieżki do 165. Nie tworzyć osobnego serwera
demonstracyjnego, launchera, imitacji pulpitu ani zastępczego Centrum Operacji.
Zatwierdzenie planu nie jest akceptacją wyglądu ani odbiorem działania.

## 164.0 — grywalny prototyp pojedynczej kamery i obowiązkowy odbiór

Bieżąca praca, wybrany przypadek, zadania i dowody:
**[wspólna tablica pilota 164.0](../plans/camera_visual_pilot_164_0_board.md)**.
Aktualizować ją po każdym spójnym pakiecie; ten sprint pozostaje kontraktem zakresu.

**Decyzja operatora 31.10.2026, nadrzędna wobec wcześniejszego przebiegu:**
success aplikacji referencyjnej → jej końcowy stan → widoczne SESSION CLOSE
(obecny standard 5 s) i zamknięcie → pobieranie aktywatora w Centrum Operacji
przez rzeczywisty czas operacji z Super Powers, postęp 0–100% → potwierdzony zapis na dysku gracza → automatyczne
otwarcie **nowej, osobnej instancji standardowego okna Ghost System**, interface
`window`. Failure pozostawia referencję w końcowym stanie, bez auto-close,
pobierania i viewera. Nie przekształcać okna referencji w okno kamery.
Trwały stan ma przetrwać close/reload/logout/restart, a receipt i deduplikacja
muszą wykluczać drugi aktywator/download/viewer od retry lub drugiej karty.
100% bez potwierdzenia zapisu nie wystarcza do uruchomienia. Aktywator nie jest
camera_dump; nie dodawać drugiego naliczenia ani drugiego 30-minutowego etapu.
Nowa decyzja zmienia moment prezentacji CVN; zachować uprawnienia i ekonomię gry.
Rewizja B demonstrowała ten przebieg poza grą; jej PASS dotyczy wyłącznie
tamtego harnessu i nie zalicza integracji ani odbioru 164.0.

Pierwszy rezultat to jeden rzeczywisty przypadek na normalnym pulpicie gry:
istniejąca aplikacja **Glass Eye (`admin_seed_camera_stream_v1`)**, konto `main`
i wskazana przez operatora **Kamera sklepu**, `48.864173348628704, 2.330499567661377`.
Cel istnieje w backupie w historii operacji `op_20261031061759_202628`
(status `cancelled`); nie traktować tego statusu jako autoryzacji podglądu.
Pełne `target_id`: `map:48.864173348628704:2.330499567661377:Kamera sklepu`.
Nowy request operatora ma receipt `47b35865a4fb7612587a` i pochodzi już po
backupie; receipt nie występuje w tym backupie. Nie fabrykować jego sukcesu.
Historyczny cel nie zawiera `camera_id`/`scan_id`; podczas integracji zachować
weryfikację serwerowego celu i obsłużyć istniejący kontrakt legacy zamiast
wymyślać identyfikator obserwacji. Nie tworzyć nowej kamery demonstracyjnej.
Obsługa ma wynikać z kontraktu `camera_stream` dla zgodnych aplikacji,
nie z nazwy Glass Eye ani sztywnego app_id. Wybór ten zastępuje CamStream
wskazany wcześniej roboczo; obowiązuje również w odwołaniach 165 i handoffu.

Uruchomienie przez istniejącą akcję mapy i aplikację referencyjną ma przejść
przez rzeczywiste rozstrzygnięcie serwera, SESSION CLOSE, istniejące Centrum
Operacji i dysk gry. Dopiero potwierdzony zapis aktywatora otwiera osobną
instancję standardowego `window`, z normalną belką, taskbarem, przeciąganiem,
minimalizacją, maksymalizacją i zamykaniem. Interfejs aplikacji referencyjnej
pozostaje zgodny z jej kontraktem; nie zamieniać jej okna w viewer.
Nie stosować selektora wyniku success/failure jako gameplayu.

Lokalne, izolowane konto i dane są dozwolone w **rzeczywistej aplikacji gry**,
z jej routerami, sesją i komponentami. Zdjęcie testowe musi mieć znane prawa
i jawne pochodzenie; nie przedstawiać go jako live ani dokładnego widoku
urządzenia. Pilot obejmuje jeden podgląd, NO SIGNAL i ponowne otwarcie.
Automatyczne dołączenie podglądu opierać na zweryfikowanym kontrakcie
`camera_stream`, nie nazwie aplikacji; ograniczenie do jednej kamery/aplikacji
wyznacza zakres pilota, nie osobny mechanizm demonstracyjny.

Warunki odbioru już w 164.0:

- Sukces i porażka rozstrzygnięte przez realną ścieżkę aplikacji; porażka nie
  inicjuje pobierania i nie otwiera podglądu, referencja pozostaje w stanie końcowym.
- Pobieranie 1800 s z postępem 0–100% w istniejącym Centrum Operacji;
  100% bez potwierdzenia zapisu, brak miejsca i błąd zapisu nie otwierają okna.
- Zamknięcie okien, reload i ponowne logowanie zachowują przyjęty stan;
  retry i równoległe karty nie dublują operacji, aktywatora ani instancji viewera.
- Nowe okno używa normalnego mechanizmu Ghost Systemu; poprzednia instancja
  znika zgodnie z SESSION CLOSE, bez przekształcania jej w podgląd.
- Playwright MCP uruchamia scenariusz na właściwym lokalnym `/desktop`;
  testy samego hosta A/B i wyciągniętych funkcji renderera nie zaliczają E2E.
- Wąskie kanoniczne store'y, bez ciężkiego profilu, dawnych kolejek,
  zdjęć graczy, aktywacji dostawcy i procedur VPS.

Przejąć atmosferę nieautoryzowanego terminala obserwacyjnego: identyfikator
kanału, oszczędny HUD, krótkie przejście do obrazu i kontrolowany glitch.
Zdjęcie pozostaje najważniejsze; szum, tekst i ramki nie mogą go zagłuszyć.
Oznaczenie archiwum i atrybucja są czytelne, wkomponowane w terminal.
Nie prezentować zwykłego slideshow jako ukończonego doświadczenia kamery.
Prototyp obejmuje także dyskretne oznaczenie źródła, wewnętrzny panel informacji
o bieżącym zdjęciu, kopiowanie URL i scenariusz EXTERNAL CONNECTION z 165.1a.
Materiały własne/testowe oznaczyć zgodnie z ich rzeczywistym pochodzeniem;
nie podpisywać ich jako fotografie Mapillary. Makieta logo nie stanowi
potwierdzenia dopuszczalności docelowego sposobu linkowania.

Przed odbiorem sprawdzić prototyp przez Playwright MCP na desktopie i telefonie,
w PL/EN i reduced-motion. Autor otrzymuje działający podgląd oraz zrzuty lub
krótkie nagranie. Osobista akceptacja kierunku artystycznego jest obowiązkowa
i nie zastępuje automatycznych testów. Kryteria: wrażenie przejętego systemu
CHAOS, czytelne otoczenie, wiarygodny rytm przejść, brak męczących efektów,
dobry stan bez zdjęcia oraz wygodne zamknięcie/powrót.

Zapisać zaakceptowaną wersję, materiały porównawcze, datę i uwagi autora.
Bez akceptacji iterować wyłącznie ten działający przypadek w grze;
nie rozwijać osobnego demonstratora ani całej sieci kamer.
W 165 wdrożyć zaakceptowany język wizualny, bez ponownego projektowania go
od zera. Późniejsze istotne odstępstwo wizualne wraca do odbioru autora.

### Minimalny kontrakt integracji i stan wyjściowy

Prześledzić camera_stream od akcji mapy do istniejącego okna i operacji;
zapisać baseline oraz wskazać jedno miejsce dołączenia warstwy wizualnej
po zatwierdzeniu akcji. Nie zakładać, że kontrakt shutdown automatycznie
autoryzuje stream. Backend ustala pozycję ze zweryfikowanego celu/operacji,
nigdy z dowolnego URL albo współrzędnych przesłanych przez klienta.

| Istniejący moduł | Ponowne wykorzystanie |
| --- | --- |
| `response_network/camera_contract.py` | Stabilna tożsamość kamery i obserwacji; ocena przydatności do stream |
| `response_network/camera_exposure.py` | Nienaruszalny kontrakt ryzyka; test regresji bez nowego naliczania |
| `run.py`: `ensure_camera_stream_fragments`, `finalize_camera_stream_file`, runtime operacji | Dotychczasowe skutki operacji i zasoby pozostają źródłem prawdy |
| `static/js/terminal.js`, testy `test_camera_window_dedupe.js` | Istniejące okno, transport celu, jedna instancja na kamerę |
| `poi_infrastructure/discovery_jobs.py` | Wzorzec lease, fencing, idempotencji; osobna kolejka obrazów, bez kopiowania tabel POI |
| `secure_transport.py`, `credit_budget.py`, `upstream_priority.py` | Wykorzystać zweryfikowane mechanizmy po wydzieleniu interfejsu, bez podawania zdjęć do adaptera POI |

Odbiór: dokument kontraktu wejścia/wyjścia, scenariusz istniejącego stream,
zestaw regresji akcji i operacji oraz lista faktycznie współdzielonych funkcji.
Nie planować refaktoru całego `run.py`.

## 164.1 — kontrakt materiału i dostawcy

### Ghost System — wspólny kontrakt podglądu

Rozpoznanie repozytorium 30.10.2026: `creator_policy.py` zawiera recepturę
`camera_stream` z celem `camera`, operacją `camera_stream` i zasobem `camera_dump`.
`doc/gameplay/app_contract.md` wskazuje `map_actions` jako router mapy;
`interface` określa prezentację, nie uprawnienia. Publikacja przechodzi przez
`creator_routes.py` i `build_creator_edition`. `creator_updates.py` chroni
zgodność zamrożonego `creator_contract`, a `creator_legacy.py` sprawdza mechanikę
historycznych wydań. Uwzględnić te ścieżki, nie tworzyć nowego generatora kamer.

- Zdefiniować roboczą zdolność `camera_visual_preview` jako serwerowo wyznaczaną
  zdolność prezentacji dla zweryfikowanego kontraktu obsługującego `camera_stream`.
  Docelowe miejsce i wersjonowanie ustalić w istniejącej normalizacji kontraktu;
  nie zakładać, że pole już istnieje. Bez ręcznej opcji w każdej aplikacji,
  heurystyki nazwy/opisu ani zaufania do flagi przysłanej przez klienta/LLM.
- Sam `camera_shutdown`, typ interfejsu albo etykieta „kamera” nie nadają prawa
  do podglądu. Obowiązuje istniejąca walidacja aplikacji, celu i aktywnej operacji.
- Wejście do CVN wiąże zweryfikowane app_id, operation_id oraz kanoniczną
  tożsamość kamery z istniejącego kontraktu. Nie tworzyć camera_id per aplikacja;
  nie utożsamiać kamery wyłącznie z nazwą lub swobodnymi współrzędnymi klienta.
- Wszystkie aplikacje używają jednego repozytorium zdjęć, manifestu i kolejki.
  app_id służy kontekstowi/autoryzacji, nie osobnej bazie ani kopii archiwum.
  Wspólny materiał nie przenosi uprawnień między graczami lub operacjami.
- Preferować zgodną projekcję zdolności podczas normalizacji/odczytu starych
  kontraktów, bez ich przepisywania i bez ponownego generowania aplikacji.
  Nie omijać porównania zamrożonej mechaniki w aktualizatorze. Jeśli migracja
  jest konieczna: dry-run, lista zgodnych/odrzuconych wydań z powodami, backup,
  idempotencja i rollback. Niejednoznaczny kontrakt nie otrzymuje nowych praw.

Odbiór kontraktu: nowa i zgodna historyczna aplikacja wskazują tę samą kamerę
i współdzielą materiał, przy osobnej kontroli dostępu. Definicja zdolności
nie zmienia kosztu, ryzyka, czasu, zasobów ani wykonawcy operacji gry.

### Zakres wyłączony — Ghost Lab i fotografie graczy

W 164–165 nie powstają CAMERA CREATOR, instalowanie nowych kamer przez graczy,
upload fotografii, aplikacja aparat/GPS, analiza Vision, wykrywanie/zamazywanie
twarzy i tablic, moderacja zdjęć graczy ani źródło `PLAYER_UPLOAD`.
Nie przygotowywać tabel, endpointów, kolejek ani innych elementów wyłącznie
pod te przyszłe rozwiązania. Sprint 166 otrzymał od operatora zakres odbioru
Camera Street View na VPS, nie uploadu. Integracja istniejących aplikacji Ghost System nie oznacza
rozbudowy Ghost Laba o tworzenie kamer.

### Manifest

Manifest zawiera: archive_id, wersję kontraktu i przetwarzania, camera binding,
pozycję celu, image_id i sequence_id dostawcy, pozycję zdjęcia, odległość,
azymut zdjęcia (nullable), źródło/wiarygodność kierunku, kierunek referencyjny
zestawu, różnicę kątową i powód wyboru, wariant miniatury i jego wymiary,
datę wykonania (nullable), datę pozyskania, autora, źródłowy odnośnik,
licencję/atrybucję, wymiary, format, rozmiar i hash pliku po przetworzeniu.
Brak daty lub autora nie może być zastąpiony wymyśloną wartością. Wymagane
pola licencyjne zależą od zweryfikowanych warunków; brak wymaganych danych
blokuje publikację. Oddzielić położenie zdjęcia od położenia kamery.

### Manifest atrybucji i dopuszczenie publikacji

Dla każdego zdjęcia przechowywać osobno, również przy deduplikacji pliku:

- Mapillary image_id oraz rzeczywistą identyfikację autora i wymagany credit.
- Publiczny URL strony oryginalnej fotografii, odrębny od tymczasowego URL CDN.
- Nazwę licencji, jej wersję i URL warunków; nie wpisywać wersji na podstawie
  przypuszczenia. CC BY-SA jest założeniem konspektu do sprawdzenia dla materiału.
- Datę wykonania, jeśli dostępna; daty pozyskania i przetwarzania.
- Listę faktycznie wykonanych zmian: np. skalowanie, konwersja do WebP,
  usunięcie metadanych, kadrowanie, jeśli zostało wykonane; wersję transformacji.
  Efekty prezentacji CHAOS opisać oddzielnie od zmian w zapisanym pliku.
- Stan dopuszczenia publikacji, przyczynę blokady/wycofania, datę oceny oraz
  odniesienie do zweryfikowanych warunków dostawcy i praw do materiału.

Gotowy plik nie oznacza zgody na publikację. Brak wymaganej identyfikacji autora,
źródła, licencji lub wersji blokuje udostępnienie fotografii; nie uzupełniać
braków nazwą CHAOS, fikcyjnym autorem ani domyślną licencją. Brak opcjonalnej
daty wykonania pokazać jako nieznany, bez wymyślania daty. Przy zmianie ujęcia
obraz i manifest atrybucji muszą być przekazywane jako zgodna para.

Przed rzeczywistym pilotem zapisać datowane źródła warunków API i fotografii:
pobieranie, transformacja, trwały zapis, ponowne udostępnianie, atrybucja,
ważność URL, usuwanie/wycofanie materiału i limity. Nie zakładać, że dostępny
thumbnail daje prawo do bezterminowego archiwizowania. Jeśli archiwum nie jest
dozwolone, przedstawić ograniczony wariant do decyzji zamiast ukrytej zmiany.

### Uzupełnienie 30.10.2026 — zachowanie praw i dwie otwarte kwestie

Wymaganie dla materiałów CC BY-SA: przechowywać razem z fotografią autora,
źródło, dokładną wersję licencji, jej odnośnik oraz oznaczenie wykonanych zmian.
Przy udostępnianiu przekształconego materiału zachować wymagania ShareAlike
w zakresie wynikającym ze zweryfikowanej licencji. Deduplikacja, konwersja
i usunięcie EXIF nie mogą usuwać tych informacji z manifestu ani prezentacji.
Nie nakładać na odbiorcę dodatkowych ograniczeń praw do materiału CC BY-SA;
uprawnienia do akcji w grze oddzielić od praw licencyjnych do otrzymanych zdjęć.
Nie wywodzić z licencji fotografii automatycznej zmiany licencji kodu całej gry.
Operacyjnego wycofania z CHAOS nie przedstawiać jako automatycznego cofnięcia
praw wcześniej przyznanych odbiorcom.

Aktualizacja na podstawie przekazanego przez operatora podsumowania odpowiedzi
Semira Kahrimanovica z Mapillary z 26.10.2026 (nie niezależna weryfikacja treści
korespondencji): pojedyncze zdjęcia i serwowanie z własnego serwera są przewidziane
w warunkach deweloperskich, skalowanie/konwersja zasadniczo dopuszczalne,
materiały standardowych użytkowników wskazano jako CC BY-SA 4.0 z atrybucją.
Nie oznacza to jednakowych praw do każdego materiału ani wieczystej retencji.
Przed pilotem do evidence dołączyć korespondencję/referencję i właściwe warunki.

Pozostają **dwie bramki z częściowo rozstrzygniętym zakresem**:

- **L01 — częściowo rozstrzygnięta:** powyższe pobieranie, transformacje
  i własne serwowanie mają potwierdzenie w przekazanym podsumowaniu. Otwarte:
  konkretna retencja, zasady wycofania/zastępowania i backupów oraz dopuszczenie
  docelowego zastosowania przy zachowaniu praw odbiorcy CC BY-SA.
- **L02 — logo i nawigacja:** czy widoczne logo Mapillary może otwierać osobny
  panel licencji, z którego aktywny link prowadzi do źródła po potwierdzeniu,
  czy wymagany jest bezpośredni odnośnik z logo.
  **L02 pozostaje otwarta:** przekazana rekomendacja to logo-link do dostawcy
  i osobny panel informacji; dwuetapowe wyjście nie ma jednoznacznej akceptacji.
  Nie zmieniać samodzielnie uzgodnionego UX; konflikt przedstawić operatorowi.

Dla obu zapisać źródło rozstrzygnięcia, datę, zakres i wynik przed produkcyjnym
pozyskiwaniem/publikacją. Poniższa tabela rozwija kontrolę L01 i L02;
wycofanie oraz użycie w grze są częściami L01.

### Rozdzielenie wymagań produktu od otwartych warunków Mapillary

Potwierdzone decyzje operatora: miniatury zamiast oryginałów, jawne pochodzenie,
widoczne oznaczenie przy zdjęciu, informacje wewnątrz CHAOS i świadome wyjście
do źródła. Nie są one same w sobie potwierdzeniem zgodności z licencją/API.
Przed produkcyjnym pobieraniem i publikacją zapisać aktualne źródła, datę,
zakres oceny i rozstrzygnięcie następujących kwestii:

| Obszar | Pytanie do warunków / Mapillary | Warunek odbioru |
| --- | --- | --- |
| Atrybucja i link | Czy widoczne logo otwierające panel, a w nim aktywny odnośnik z potwierdzeniem wyjścia, spełnia wymogi? Czy logo musi prowadzić bezpośrednio do dostawcy? | Odpowiedź dostawcy lub jednoznaczny zapis aktualnych warunków; bez domniemania zgody |
| Archiwizacja (L01) | Własne serwowanie i transformacje opisano powyżej jako częściowo potwierdzone. Jakie są dokładne warunki retencji i ponownego użycia? | Evidence zakresu archive/transform/serve; jawna retencja i obowiązki po zmianach, bez założenia wieczystego archiwum |
| Wycofanie | Jak obsługiwać usunięcie fotografii, cofnięcie dostępu i kopie zapasowe? | Procedura wycofania i retencja zgodna ze zweryfikowanymi warunkami |
| Gra | Czy archiwalna symulacja monitoringu i dostęp zależny od uprawnień w niekomercyjnej grze są dopuszczalne przy zachowaniu praw odbiorców CC BY-SA? | Udokumentowane rozstrzygnięcie; mechaniki gry nie przedstawiane jako ograniczenie praw licencyjnych |

Samo skopiowanie URL ani ostrzeżenie nie zastępuje aktywnego odnośnika.
Brak rozstrzygnięcia linkowania/archiwizacji pozostaje bramką wdrożeniową.
Do tego czasu rozwijać i testować prototyp na własnych materiałach o znanych
prawach, bez produkcyjnego pozyskiwania Mapillary. Nie dodawać WebDragona,
iframe ani mechanizmu podobnego do OAuth2 jako obejścia.

## 164.2 — wyszukiwanie i dobór zdjęć

Adapter serwerowy: kontrolowane wyszukanie blisko celu, ograniczona lista
kandydatów, odległość liczona geograficznie, preferencja wspólnej sekwencji,
deduplikacja image_id i deterministyczny wybór maksymalnie trzech obrazów.
Jedno dopuszczalne zdjęcie wystarcza; brak trzech nie wywołuje nieograniczonego
poszerzania promienia. Panoramy nie trafiają do zwykłego kadru bez jawnie
zaprojektowanej transformacji; pierwsza wersja może je pomijać.

**Kierunek jest częścią doboru, nie tylko odległość.** Jeśli istniejący cel ma
wiarygodny azymut obserwacji, preferować zgodne ujęcia według minimalnej
różnicy kątowej modulo 360 (np. 359° i 1° różnią się o 2°). Jeśli brak
azymutu kamery, najbliższe dopuszczalne zdjęcie z kierunkiem wyznacza
referencję zestawu; nie przedstawiać tego jako rzeczywistej orientacji kamery.
Nie utożsamiać kierunku patrzenia zdjęcia z namiarami od zdjęcia do celu.

Po filtrze odległości: zgodność kierunku, spójność sekwencji i czasu,
odległość oraz stabilny image_id jako rozstrzygnięcie remisu. Proponowana
tolerancja kierunku 45° do sprawdzenia w prototypie/pilocie. Ujęcia przeciwne
nie przeplatają się automatycznie. Mniejszy spójny zestaw wygrywa z trzema
sprzecznymi kadrami. Brak heading oznacza UNKNOWN: można użyć pojedynczego
zdjęcia otoczenia, ale nie deklarować zgodności kierunku. Ta sama sekwencja
nie jest sama w sobie dowodem zgodnego patrzenia. Współdzielenie archiwum
uwzględnia również kierunek/profil, nie sam sektor geograficzny.

**Pobierać miniatury dostawcy, nie oryginały.** Wybrać najmniejszy dostępny
wariant wystarczający do zaakceptowanego podglądu, w granicach limitu wymiarów
i transferu. Nazwy pól/wariantów potwierdzić w aktualnym kontrakcie Mapillary.
Nie pobierać pełnej rozdzielczości tylko po to, by następnie ją zmniejszyć.
Gdy odpowiednia miniatura jest niedostępna, użyć mniejszej bez powiększania
lub pominąć obraz; żadnego automatycznego fallbacku do oryginału.

Proponowane wartości pilota, do potwierdzenia pomiarem i warunkami dostawcy:
promień 100 m, twardy limit 250 m; najwyżej 30 kandydatów, jedna strona
wyszukiwania; maksymalnie trzy pobrania obrazów. Każde dodatkowe zapytanie
metadanych również wlicza się do twardego limitu żądań zadania.
Brak odpowiednich zdjęć daje `NO_COVERAGE`, a nie obraz z dalszego miasta.

## 164.3 — kolejka i ograniczony worker

Wspólny słownik backend/worker/API/UI: QUEUED → FETCHING → PROCESSING → READY;
NO_COVERAGE, FAILED, EXPIRED i REVOKED kończą bieżące zadanie. DEFERRED oznacza
odroczenie budżetu/polityki z terminem ponownej kwalifikacji, bez aktywnego HTTP.
FAILED oznacza zakończoną nieudaną próbę po wyczerpaniu dozwolonego retry;
EXPIRED — przekroczony TTL, REVOKED — administracyjnie/polityką wycofany materiał.
Techniczny powód zapisany
osobno od wizualnego scenariusza. Rezerwacja limitu przed HTTP, licznik
rzeczywistych prób, respektowanie Retry-After i bounded backoff; bez pętli
retry z przeglądarki. Negatywny cache i czas następnej dopuszczalnej próby.

Dedup obejmuje obszar, profil wyboru, dostawcę i wersję przetwarzania;
współdzielenie archiwum wymaga ponownego sprawdzenia odległości dla nowej
kamery. Dwóch graczy nie tworzy dwóch pobrań tego samego materiału.
Zamknięcie lub minimalizacja okna zatrzymuje wyłącznie animacje i polling.
Zatwierdzone zadanie QUEUED/FETCHING/PROCESSING pozostaje w trwałej kolejce
i kończy przygotowanie współdzielonego archiwum w swoich limitach, nawet bez
otwartego okna. Zamknięcie przed przyjęciem żądania nie tworzy zadania.
Odzyskanie niezamkniętej instancji dołącza do tego samego zadania albo odczytuje READY,
bez nowego pozyskania zdjęć. Ręcznie zamknięty feed wymaga nowego hakowania
i pobrania pliku gameplayu; archiwum można współdzielić. Nie przedłuża deadline ani liczby prób.
Proponowany TTL oczekiwania QUEUED: 15 minut; po nim EXPIRED bez HTTP.
To osobny limit od 90 s wykonania. Wyłączenie pozyskiwania, cofnięcie zgody
dostawcy lub anulowanie administracyjne nadal zatrzymują pracę. Zamknięcie
okna nie jest cofnięciem autoryzowanego zlecenia; dalszy dostęp gracza zawsze
wymaga ponownej kontroli uprawnień, nawet jeśli archiwum już powstało.
Lease/fencing, heartbeat, odzyskanie po awarii, ponowne sprawdzenie polityki
przed pobraniem i publikacją. HTTP i obróbka poza transakcją SQLite.

Najpierw jednorazowy CLI worker na fixtures; stały proces dopiero w 165.
Wstępnie concurrency=1, deadline zadania 90 s, do dwóch prób; ograniczyć
osobno czas połączenia, odczytu i dekodowania. Nie zajmować workerów Gunicorna
obróbką obrazu. Osobne limity obrazów, API requests, bajtów i nowych archiwów;
nie nazywać wewnętrznego limitu gwarancją kosztu dostawcy.

## 164.4 — bezpieczne przetwarzanie i trwałość

Domyślnie obraz mieści się w 960×540, zachowane proporcje, bez powiększania;
WebP quality=70. Jawne ustawienia w zakresie min/max. Limit źródła proponowany
10 MiB/miniaturę, 20 megapikseli po dekodowaniu, max trzy obrazy; to bezpieczniki,
nie docelowy rozmiar pobierania ani pozwolenie na oryginały. Wartości
zweryfikować pomiarem pamięci, nie traktować samej kompresji jako ochrony.

Wyłącznie HTTPS i dozwolone hosty API/CDN ustalone z dokumentacji/próbki;
ochrona SSRF także przy redirect, bez prywatnych adresów, URL od użytkownika
i tokenów w logach. Walidacja MIME oraz rzeczywistego dekodera, ograniczenie
decompression bomb, odrzucenie animacji/nieobsługiwanych formatów. Token
wyłącznie serwerowy, źródłowe signed URLs nie trafiają do klienta.

Usunąć EXIF i zbędne metadane z pliku, zachować potrzebne pochodzenie w DB.
Pliki tymczasowe z ograniczonym TTL; atomowy rename i publikacja manifestu
dopiero po weryfikacji wszystkich wybranych plików. Deduplikacja hash + wersja
transformacji; osobne referencje/atrybucja nawet przy identycznych bajtach.
Crash pomiędzy plikiem a DB odzyskiwany przez reconcile; GC nie usuwa plików
aktywnie używanych przez inne archiwa. Ścieżki spoza publicznego static.

Osobna baza/metadane i katalog mediów proponowane jako
`data/camera_visual.sqlite3` oraz `data/camera_visual/`; ustalić before migration.
Backup manifestu i plików jako spójny zestaw, kontrola integralności i restore.
Quota oraz low-disk zatrzymują nowe zadania, nie istniejącą rozgrywkę.
Retencja zdjęć wymaga jawnej decyzji zgodnej z warunkami; nie dziedziczy
automatycznie 28-dniowej retencji backupów ani TTL cache POI.

### Wycofanie ze współdzielonych archiwów

- Wycofanie identyfikuje materiał przez dostawcę i image_id, obejmuje wszystkie
  jego warianty oraz referencje we wszystkich archiwach kamer. Najpierw blokuje
  publikację i odczyt, potem usuwa materiał z manifestów i kolejki doboru.
- Zachować trwały wpis blokujący ponowne pozyskanie (tombstone), powód, czas
  i zakres decyzji. Worker sprawdza go także bezpośrednio przed publikacją;
  zadanie rozpoczęte wcześniej nie może odtworzyć wycofanego materiału.
- Deduplikacja plików nie scala tożsamości ani atrybucji. Usunąć wszystkie
  referencje wycofanego źródła; współdzielony plik można zachować tylko dla
  niezależnych, nadal dopuszczonych referencji, zgodnie z zakresem wycofania.
  Nie może to pozwalać na odczyt wycofanego materiału przez stare archiwum/URL.
- Fizyczne usunięcie nieużywanych plików i wariantów wykonuje ograniczony GC.
  Runbook określa terminy czyszczenia cache i backupów zgodnie z L01, oddzielając
  natychmiastową blokadę od zakończenia usuwania. Restore stosuje aktualny rejestr
  wycofań przed uruchomieniem odczytu; sam stary backup nie przywraca publikacji.
- Zostawić minimalny ślad audytowy bez wycofanych zdjęć. Raport pokazuje liczbę
  dotkniętych archiwów, usuniętych referencji i plików oraz zaległe czyszczenie.

## 164.5 — testy i kryteria zamknięcia

- Adapter fixtures: 0/1/3 zdjęcia, poza promieniem, różne sekwencje, panorama,
  brak daty/atrybucji, duplikaty, malformed metadata, odrzucony host/CDN.
- Kierunek: 359°/1°, przeciwne ujęcia, brak heading, zakręt w jednej sekwencji,
  brak orientacji kamery; stabilny wybór i brak fałszywej zgodności.
- Miniatury: wybór wariantu, brak odpowiedniego rozmiaru, brak oryginału
  w żądaniach HTTP, limity bajtów oraz wymiary po dekodowaniu.
- Worker: równoległe żądania, utrata lease, restart w każdej fazie, budżet,
  429/timeouts, cofnięcie zgody, zapełniony dysk, brak ponownego podwójnego kosztu.
- Zamknięcie na każdej fazie, reopen i drugi odbiorca: jedno zadanie/pobranie;
  TTL kolejki bez odbiorcy, administracyjne anulowanie i odczyt po utracie praw.
- Media: duży/dekompresujący plik, błędny format, EXIF, checksum, atomic publish,
  referencje i GC, backup/restore. Pomiar RSS/czasu/rozmiaru na VPS w pilocie.
- Autoryzacja: brak sesji, obcy operation_id, wygasły dostęp, podmieniony cel;
  archiwum współdzielone nie daje prawa odczytu zdjęć poza akcją gracza.
- Regresja stream/shutdown/ryzyka, bez zmian zasobów gry po błędzie zdjęć.
- Manifest: brak autora/wersji licencji/źródła blokuje publikację; prawdziwe
  daty i zmiany; atomowa zgodność image_id, obrazu i atrybucji przy zmianie ujęcia;
  deduplikacja nie usuwa osobnych credits; cofnięcie zgody blokuje serve.

- Wycofanie: jedno zdjęcie w kilku archiwach i wariantach, równoległa publikacja,
  ponowne wyszukanie, stary URL, restart i restore. Brak ponownego udostępnienia;
  niezależne dopuszczone materiały zachowują własną atrybucję i referencje.
- Ghost System: nowe i historyczne kontrakty, cztery interfejsy creatora,
  identyczna tożsamość kamery i deduplikacja między aplikacjami, odrzucona
  podszyta zdolność, shutdown bez stream, cudza/wygasła operacja; brak zmiany
  kosztów, zasobów i zamrożonych kontraktów podczas kompatybilnego odczytu.
- CC BY-SA: zgodność autora/źródła/wersji/licencji/zmian po transformacji,
  deduplikacji i odtworzeniu; rozstrzygnięcia L01/L02 zapisane jako osobne bramki.

Deliverables: zaakceptowany prototyp jednej kamery i zapis odbioru, adapter,
manifest/repository, worker CLI, migracja dry-run/backup,
fixtures, testy, evidence i runbook. **Offline PASS** nie oznacza Mapillary
live PASS. Bez dostępu/licencji sprint może mieć gotowy kod i otwartą bramkę
pilota; nie deklarujemy zakończenia rzeczywistego pozyskiwania.
Do evidence dołączyć rozstrzygnięcia powyższych kwestii i kontrakt metadanych
dla panelu 165. Akceptacja dokumentów nie uruchamia integracji produkcyjnej.
