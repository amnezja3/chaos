# Sprint 164 — Camera Visual Network: prototyp kamery, kontrakt i archiwum

Data: 24.10.2026. Status: **PLAN — bez aktywacji integracji**.
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

**164.0 prototyp jednej kamery → jawna akceptacja autora → 164.1–164.5
infrastruktura → 165 integracja i rollout.** Nie rozpoczynać rozbudowy kolejki,
archiwum i panelu przed zaakceptowaniem prototypu. Do prototypu wystarcza
minimalne rozpoznanie istniejącej akcji i okna; nie wymaga działającego API,
migracji ani workera. Zatwierdzenie planu nie jest akceptacją wyglądu.

## 164.0 — grywalny prototyp pojedynczej kamery i obowiązkowy odbiór

Pierwszy rezultat to otwierany z „Podglądu kamery” interaktywny prototyp
jednego okna CHAOS na izolowanych danych, z 1–3 lokalnymi zdjęciami testowymi
o znanym prawie użycia. Obsługuje sekwencję wejścia, synchronizację, ujawnienie
obrazu, delikatne zakłócenia, zmianę ujęcia, NO SIGNAL i ponowne otwarcie.
Nie dodaje fikcyjnego sukcesu włamania przed zatwierdzeniem akcji gameplayu.

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
Bez akceptacji iterować wyłącznie prototyp; nie rozwijać całego systemu.
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

Pozostają **dwie nierozstrzygnięte kwestie**, a nie zgoda na integrację:

- **L01 — archiwizacja i udostępnianie:** dopuszczalność przechowywania miniatur,
  transformacji, deduplikacji i wielokrotnego serwowania w grze; zachowanie praw
  CC BY-SA oraz wymagania wycofania, retencji i kopii zapasowych.
- **L02 — logo i nawigacja:** czy widoczne logo Mapillary może otwierać osobny
  panel licencji, z którego aktywny link prowadzi do źródła po potwierdzeniu,
  czy wymagany jest bezpośredni odnośnik z logo.

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
| Archiwizacja | Czy dozwolone są trwałe, zoptymalizowane kopie na serwerze CHAOS oraz wielokrotne udostępnianie bez ponownego API? | Udokumentowany zakres archive/transform/serve i obowiązki dotyczące licencji po zmianach |
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

Stany: QUEUED → FETCHING → PROCESSING → READY; terminalne NO_COVERAGE,
FAILED, REVOKED oraz DEFERRED dla budżetu/polityki. Techniczny powód zapisany
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
Ponowne otwarcie dołącza do tego samego zadania albo odczytuje READY, bez
nowego pobrania i rezerwacji. Nie przedłuża deadline ani liczby prób.
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
- CC BY-SA: zgodność autora/źródła/wersji/licencji/zmian po transformacji,
  deduplikacji i odtworzeniu; rozstrzygnięcia L01/L02 zapisane jako osobne bramki.

Deliverables: zaakceptowany prototyp jednej kamery i zapis odbioru, adapter,
manifest/repository, worker CLI, migracja dry-run/backup,
fixtures, testy, evidence i runbook. **Offline PASS** nie oznacza Mapillary
live PASS. Bez dostępu/licencji sprint może mieć gotowy kod i otwartą bramkę
pilota; nie deklarujemy zakończenia rzeczywistego pozyskiwania.
Do evidence dołączyć rozstrzygnięcia powyższych kwestii i kontrakt metadanych
dla panelu 165. Akceptacja dokumentów nie uruchamia integracji produkcyjnej.
