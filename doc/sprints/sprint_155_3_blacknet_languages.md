# Sprint 155.3 — BlackNet: język źródła i naturalna rotacja sygnałów

Status: IMPLEMENTACJA LOKALNA DO ODBIORU WDROŻENIOWEGO, 14 X 2026.
Osobny podsprint [155](sprint_155_ghost_system_content_acceptance.md).
Nie blokuje dostępności rozgrywki i nie oznacza pełnego PASS 155.
[Inwentarz i dowody](../audits/sprint_155_3_blacknet.md),
[migracja i rollback](../runbooks/blacknet_155_3.md). Poniżej zachowany kontrakt
i bramki planu; stan wykonania opisuje raport dowodów.

## Cel i ustalenia

BlackNet to wskazówki, tropy i ślady z różnych źródeł. Jedna publikacja ma jeden
język. Nie tworzymy automatycznie pary PL/EN tego samego sygnału. Kolejne sygnały
mogą naturalnie zmieniać język spośród zatwierdzonych języków narracji.
Zmiana języka interfejsu nie przepisuje wcześniej opublikowanego sygnału.

- Radio PL → sygnał PL; radio EN → sygnał EN. Używamy języka kanału/źródła,
  nie aktualnego filtra widza ani języka jego interfejsu. ANY jest filtrem lub
  deklaracją neutralności językowej, nigdy językiem generacji ani tłumaczeniem audio.
- Kreatory otrzymają deklarację PL/EN/ANY dla narzędzia/produktu. PL i EN
  określają język źródła sygnału. ANY pozwala wybrać zatwierdzony język dla
  systemowego tekstu sygnału, ale nie uprawnia do tłumaczenia treści autora.
- Sygnały neutralne językowo/heurystyczne GN korzystają z rotacji zatwierdzonych
  języków. Wyboru dokonujemy przy utworzeniu zadania; zapisujemy go trwale.
  Retry, fallback, restart i publikacja nie losują języka ponownie.
- Nazwy, opisy produktów Googleplexa i inne UGC zachowują oryginał. Systemowe
  otoczenie sygnału i etykiety są lokalizowane. Jawne wersje autora są oddzielnymi
  danymi, nie efektem automatycznego tłumaczenia.
- Radio „KANAŁY ONLINE”, „TRACKÓW W ETERZE” i pozostałe systemowe etykiety kart
  muszą mieć PL/EN; także tekst zaszyty w grafice lub szablonie heurystycznym.
- Jeden zestaw faktów, jeden cel/CTA, jeden identyfikator i efekt gameplayu.
  Fallback systemowy zachowuje wybrany język; brak wymogu kreatywności Ollamy.

## Etapy

Szczegółowy kontrakt, zadania i bramki poniżej są planem implementacji.
Wcześniejszy punkt „historia i migracja” w sprincie nadrzędnym pozostaje wymaganiem
przekrojowym; numer 155.3 oznacza odtąd ten podsprint BlackNet.

1. **A — Inwentarz i kontrakt:** wszyscy producenci, pochodzenie języka,
   pierwszeństwo źródeł, brak metadanych i zgodność ze starym kontraktem.
2. **B — Producenci i narracja:** trwały wybór locale, naturalna rotacja,
   idempotencja, radio i bezpieczny fallback.
3. **C — Kreatory i katalog:** deklaracja PL/EN/ANY przenoszona przez wersję
   artefaktu, publikację, zakup, instalację i sygnał BN.
4. **D — Karty i UI:** etykiety wszystkich layoutów, zasoby, mobile/desktop,
   przełączanie locale z zachowaniem oryginalnej publikacji i audio.
5. **E — Migracja i odbiór:** dry-run, integralność, rollback metadanych,
   macierz testów i procedura na obecnym środowisku.

Kolejność: A → B/C/D → E. Każdy pakiet zamykany własnymi dowodami; emisję nowych
sygnałów włączamy dopiero po wspólnym odbiorze. Dokument nie wymaga równoległej
implementacji ani dodatkowej infrastruktury.

## Kryteria PASS

- PL radio zawsze daje PL sygnał, EN radio EN; ANY nigdy nie trafia jako locale
  do modelu. Dziewięć potwierdzonych polskich audycji zachowuje oznaczenie PL.
- Rotacja neutralnych źródeł działa po restarcie i retry bez zdublowania sygnału.
- Produkty PL/EN/ANY przechodzą pełną ścieżkę; UGC pozostaje identyczne.
- Karty radia, GN, GGPL i GX nie mają polskich systemowych etykiet w wariancie EN.
- Brak tytułów skopiowanych z instrukcji i uciętych nazw typu „Can” zamiast
  „Canary Station”. Odrzucona generacja przechodzi do zatwierdzonego szablonu.
- Zmiana UI nie zmienia ID, celu, faktów, nagród, consumed ani języka publikacji.
- Dodanie zatwierdzonego języka korzysta z rejestru, nie z kolejnej gałęzi PL/EN.
- Brak nowej infrastruktury i zatrzymywania gry na czas strojenia narracji.

## Poza tym podsprintem

Automatyczne tłumaczenie UGC, dubbing nagrań, wymiana modelu Ollamy i odblokowanie
zamrożonych sprintów 149–152. Historyczne treści bez udokumentowanego pochodzenia
wymagają przeglądu, nie automatycznego zgadywania języka.

## Audyt wejściowy — 13 X 2026

| Obszar | Potwierdzony stan kodu | Praca w 155.3 |
| --- | --- | --- |
| `run.py`, `BLACKNET_SIGNAL_RULES` | `radio_channels_available` ma literalne `KANALY ONLINE` i `{tracks_total} TRACKOW W ETERZE`; produkt ma m.in. `CENA`, `POBRAN` | Klucze i parametry etykiet wszystkich reguł, inwentarz kart, nie tylko radio |
| `run.py`, `build_blacknet_radio_facts` | Kopiuje kanał i plik audycji, ale pomija ich `language` | Przenieść zweryfikowane metadane konkretnego źródła i stosować kontrakt dopuszczenia audycji |
| `radio_locale.py` | Rozróżnia zatwierdzone locale, `neutral`, `mixed`, `unknown`; filtr ANY nie oznacza neutralnego audio | Wykorzystać istniejący kontrakt, nie zastępować go pojedynczą flagą PL/EN |
| `ghostnetwork/narrative_locale.py` | `freeze_language` zapisuje kontrakt; BN bez jawnego locale wybiera je hashem eventu z puli rollout | Rozszerzyć o pochodzenie wyboru; objąć producentów deterministycznych; brak gwarancji ścisłej naprzemienności |
| `ghostnetwork/repository.py`, worker/publisher | Istnieją zadania, walidacja, fallback i ochrona publikacji | Zachować tożsamość, lease, dedupe, fakty i efekty; nie tworzyć drugiego pipeline'u |
| `creator_routes.py`, `creator_store.py`, `static/js/creator_editor.js` | Deklaracja języka sygnałów wymaga przejścia całej ścieżki artefaktu | Formularz → API → wersja → katalog → zakup → instalacja → BN |
| `static/blacknet_signals.json`, karty w przeglądarce gry | Pozostałe źródła statyczne i renderery wymagają pełnego inwentarza | Oddzielić systemowe etykiety od oryginalnych publikacji i UGC |

Inwentarz A musi zawierać każdy `fact_type`, `signal_type`, producenta, renderer,
fallback, plik/zasób oraz test odbioru. Wiersz bez źródła języka oznacza brak
pokrycia, nie domyślne przypisanie PL. Sprawdzić również allowlisty metadanych,
projekcje API i cache: dodanie pola tylko do producenta nie kończy zadania.

## Kontrakt języka i pierwszeństwo

Trzy niezależne wartości: `ui_locale` gracza (etykiety i przyciski), deklaracja
źródła (treść autora/audio) oraz utrwalone `output_locale` publikacji. Dwa konta
PL/EN czytają ten sam tekst sygnału BN; ramka, licznik i CTA są w języku widza.
Fakt „liczba kanałów” jest parametrem, a `CHANNELS ONLINE` jest etykietą UI.
Nagłówek/treść narracyjna zostaje w języku publikacji. Nie przepuszczać UGC przez
katalog tłumaczeń ani nie tłumaczyć całego wyrenderowanego HTML.

| Źródło nowego sygnału | Wybór języka publikacji |
| --- | --- |
| Konkretny kanał PL/EN i audycja zgodna lub neutralna | Język kanału; zachować wskazanie kanału i pliku w CTA |
| Kanał mixed/unknown z audycją o potwierdzonym PL/EN | Język audycji; nie przypisywać go całemu kanałowi |
| Kanał i audycja jawnie neutralne lub globalny agregat bez wybranego audio | Wybór z aktywnej, zatwierdzonej puli narracji |
| Audycja o nieznanym języku, sprzeczna z kanałem | Nie udawać neutralności: oznaczyć diagnostycznie, pominąć nową promocję tej audycji; reszta feedu działa |
| Produkt/narzędzie z deklaracją PL lub EN | Deklaracja opublikowanej wersji artefaktu |
| Produkt/narzędzie z jawną deklaracją ANY | Systemowa narracja z puli; tekst autora pozostaje oryginalny |
| Neutralny sygnał GN, GX lub heurystyka systemowa | Wybór z puli; bez zależności od użytkownika odczytującego feed |
| Stary rekord bez metadanych | Oryginał pozostaje dostępny; `unknown` do audytu, bez zgadywania i republish |

Jeżeli narzędzie promuje konkretną audycję, kontrakt radia jest nadrzędny.
Nie dopuszczać publikacji nowej konfiguracji z jawną sprzecznością PL/EN;
zwrócić lokalizowany błąd przy niezmienionym stanie. ANY narzędzia pozwala
odziedziczyć język audycji. W przypadku wielu sprzecznych źródeł nie wybierać
pierwszego przypadkowo: zapisać błąd kwalifikacji, pominąć kandydaturę.

Locale musi należeć zarówno do rejestru zatwierdzonej narracji, jak i aktywnego
rolloutu. Źródło EN przy rolloucie tylko PL czeka/pomija nową publikację z jawnym
powodem; nie przełącza się na PL. Już opublikowany EN pozostaje czytelny.
Nowy sygnał bez obsługi jego języka w promptach i bezpiecznym szablonie nie może
wejść do generacji. Błąd jednej kandydatury nie zatrzymuje workera.

### Metadane i trwałość

Poniższe pola są docelowym kontraktem, nie istniejącym dziś API:

- Deklaracja artefaktu `signal_language`: zatwierdzone locale (`pl`, `en`) albo
  `ANY`. Widoczne opcje PL/EN/ANY pochodzą z rejestru. Walidacja serwerowa;
  `unknown` jest stanem odczytu starego rekordu, niedozwoloną nową deklaracją.
- Do istniejącego kontraktu języka zadania dodać pochodzenie: typ i ID źródła,
  wersję źródła, deklarację, powód wyboru i wersję polityki wyboru. Nazwy i format
  pól przypiąć w A przed migracją; czytnik musi obsługiwać dotychczasowy v1.
- `output_locale` zawsze konkretny. Przechodzi bez zmiany przez fakt/zadanie,
  kandydata, fallback, zapis sygnału i odpowiedź API. Dotyczy też ścieżki bez LLM.
- Nowa wersja produktu może zmienić deklarację dla przyszłych zdarzeń. Instalacja
  przechowuje deklarację wersji zakupionej; odczyt katalogu nie zmienia jej wstecz.
- Zapis wyboru jest atomowy i idempotentny według istniejącej tożsamości zdarzenia.
  Locale nie staje się nowym kluczem dedupe BN. Restart, dwaj workerzy i retry
  nie mogą utworzyć dwóch publikacji tego samego sygnału.

Naturalna rotacja oznacza zróżnicowanie kolejnych **neutralnych** sygnałów,
nie wymóg PL, EN, PL, EN i nie pary tłumaczeń. Zachować deterministyczny wybór
oparty o stabilny identyfikator zdarzenia oraz uporządkowaną aktywną pulę.
Wybór utrwalić raz; odczyt i retry nigdy nie przeliczają go z nową pulą.
Testować pokrycie obu języków na stałym zbiorze różnych zdarzeń, nie wymagać
równego podziału w dwóch kolejnych publikacjach. Pusta pula: kontrolowany brak
nowej kandydatury i diagnostyka, bez niezatwierdzonego języka.

## Pakiety wykonawcze i bramki

### A — kontrakt i pełny inwentarz

Przejść źródła świata (operacje, konflikty, system, rynek), GN, radio, GGPL, GX,
kreatory, sygnały statyczne i admin. Dla każdego wskazać rozdział UGC/system,
przepływ metadanych i politykę nieznanego języka. Zinwentaryzować literały
w regułach, HTML, JS, JSON i grafikach. Wynik: tabela pokrycia z dowodami i
wersjonowany kontrakt zaakceptowany przez testy parsera, w tym legacy v1.

### B — producenci, pinning i bezpieczna narracja

Resolver radia korzysta z `radio_locale.py`; CTA i licznik opisują ten sam
wybrany kanał/utwór, bez obchodzenia wykluczeń i reguł języka. Globalne statystyki
muszą pozostać jawnie globalne. GN/GX i producent deterministyczny używają tego
samego wyboru języka co zadania LLM. Cache zawiera tożsamość/wersję kontraktu;
locale widza dotyczy wyłącznie projekcji etykiet, nie ponownej generacji.

Mistral pozostaje główny, Ollama awaryjna w istniejącym budżecie. Odrzucenie
stylistyczne, timeout lub zły JSON kończy się zatwierdzonym szablonem tam, gdzie
jest obsługiwany. Brak szablonu → jawny wynik bez publikacji, bez pętli retry.
Nie obniżać walidacji faktów, CTA, odbiorców ani języka.

Prefiksy stylistyczne przenieść do wersjonowanego kontraktu prezentacji nowych
sygnałów. Składanie dokładnie raz, ze zgodną walidacją; starych tekstów z prefiksem
nie dekorować ponownie. Nazwy własne pozostają całe, UI zawija lub skraca wizualnie,
nie zapisuje obciętej nazwy. Osobno sprawdzić historię oraz fallback.

B PASS: testy resolvera, równoległości, retry i awarii dostawcy; brak podwójnej
publikacji i brak `ANY` w payloadzie modelu. B nie wymaga ponownego strojenia 8B.

### C — kreatory, katalog, zakup i instalacja

Dodać pole z objaśnieniem: „Język systemowego sygnału promującego narzędzie;
nie tłumaczy Twojej treści”. Nowy formularz proponuje język interfejsu, ale
deklaracja jest widoczna, edytowalna i przesyłana jawnie. Stary klient bez pola
zachowuje kompatybilność (`unknown`); publikacja nowej wersji wymagająca sygnału
prosi o deklarację zamiast cicho użyć języka sesji. Brak pola w edycji istniejącej
wersji nie kasuje zapisanej wartości. Niewspierany kod daje błąd walidacji.

Obsłużyć wszystkie kreatory produkujące artefakty promowane w BN, kopię projektu,
szablon, export/import, update i rollback wersji. Przenieść pole przez katalog,
zakup i instalację bez wpływu na cenę, typ celu, prawa i wynik narzędzia.
Nie uruchamiać nowej promocji wskutek samej migracji/odczytu metadanych.

C PASS: po jednym pełnym przebiegu PL, EN i ANY oraz stary artefakt bez pola;
porównanie oryginalnych nazw/opisów i efektów zakupowych przed/po.

### D — karty, UI i materiały

Lokalizować systemowe etykiety i stany wszystkich layoutów (liczniki, pluralizacja,
timer/ważność, empty/loading/error, dostępność, CTA, nawigacja). `KANALY ONLINE`
oraz `TRACKOW W ETERZE` są obowiązkowymi przypadkami regresji. Tekst w obrazach
zastąpić nakładką lokalizowaną lub przygotować warianty zasobów. Nie tłumaczyć
logo, nazwy artysty, tytułu audycji ani samego nagrania.

D PASS: desktop/mobile, zmiana locale na otwartej karcie, bez restartu audio,
resetu zegara, utraty consumed ani zmiany tożsamości CTA. PL/EN gracza zmienia
etykiety, ale zachowuje treść pojedynczej publikacji BN.

### E — migracja, odbiór i wdrożenie

Przygotować narzędzie inventory → dry-run → apply → check → rollback metadanych.
Raport: liczby według źródła i języka, rozpoznane/unknown/sprzeczne, plan pól,
sumy kontrolne treści/ID, bez sekretów. Apply uzupełnia wyłącznie potwierdzone
metadane w ograniczonych transakcjach, jest wznawialny i idempotentny. Dziewięć
audycji 001–009 zachowuje potwierdzone PL; muzyka bez potwierdzenia pozostaje unknown.
Bez heurystycznego rozpoznawania języka UGC, masowego replace i historycznego republish.

Addytywne zmiany schematu/metadanych, domyślnie wyłączona nowa emisja.
Wdrożyć kompatybilne czytniki, potem zapis deklaracji, na końcu kwalifikację
nowych sygnałów. Nazwy flag i dokładne komendy ustalić po implementacji w runbooku
155.3; nie przedstawiać planowanych przełączników jako już działających.
Wyłączenie nowej emisji nie ukrywa historii i nie odrzuca utrwalonych kontraktów.

Procedura na obecnej produkcji: spójny backup SQLite, zapis wersji kodu i ustawień,
dry-run, kontrole integralności, apply, check, próbki bez publikacji, kontrolowana
emisja. Nie stawiać drugiej instancji i nie zatrzymywać gry na czas testów LLM.
Ewentualne krótkie blokady migracji oddzielić od wielominutowego canary.
Rollback wycofuje kwalifikację/zapisy nowych metadanych, pozostawiając czytnik
zgodny z opublikowanymi sygnałami; nie usuwa receiptów, nagród ani historii.
Przywracanie całej bazy po wznowieniu gry nie jest standardowym rollbackiem,
bo utraciłoby nowe działania graczy. Skrypt cofania dotyka tylko swoich zmian
i odmawia nadpisania rekordów zmienionych później.

## Macierz odbioru końcowego

| Scenariusz | Oczekiwany dowód |
| --- | --- |
| Radio PL/EN, zgodna i neutralna audycja | Locale sygnału zgodne z kanałem; CTA trafia do właściwego nagrania |
| mixed/unknown/konflikt metadanych | Reguły tabeli, jawna diagnostyka; brak arbitralnego PL/EN |
| Filtr ANY i zmiana UI PL/EN | Oryginalne audio/tekst, brak nowej generacji i zmiany publikacji |
| Neutralne zdarzenia GN/GX | Oba locale w stałej próbce; restart i dwa workerzy nie zmieniają wyboru |
| Kreator → GGPL → zakup → instalacja → BN | PL/EN/ANY przeniesione; UGC identyczne; niezmienione rozliczenia |
| Legacy, import i zmiana wersji | unknown nie staje się ANY; nowa deklaracja nie zmienia starej instalacji |
| Mistral PL/EN | Akceptacja faktów/języka; próbki BN początkowo `published:false` |
| Ollama odrzuca/timeout/niepoprawny JSON | Test kontrolowanej awarii → bezpieczny szablon, bez powielania prób i emisji |
| Każdy typ karty, desktop/mobile | Systemowe etykiety PL/EN, brak przecieków polskich literałów do EN |
| Migracja wykonana dwukrotnie / rollback | Spójność, identyczne ID/UGC/receipt/read cursor/rewards; brak ponownej emisji |

Testy automatyczne rozszerzyć w istniejących zestawach `test_radio_locale`,
`test_llm_event_producers`, `test_narrative_locale`, `test_mistral_runtime`,
`test_ollama_policy`, testach kreatorów oraz Playwright (`radio_locale.js`,
`blacknet_cta_locale.js` i nowe scenariusze pełnej ścieżki). Ollamę symulować
w macierzy awarii; realny długi test awaryjny nie blokuje dostępności gry.
Raport odbioru rozróżnia dowody automatyczne, próbki realnego modelu i ręczny
odbiór jakości. Przejście jednego z nich nie oznacza przejścia pozostałych.

Do zamknięcia wymagane: uzupełniony inwentarz, migrator i runbook z komendami
„komenda → spodziewany wynik”, testy, audyt PL/EN i aktualizacja dokumentacji
BlackNet/kontraktu radia, journal oraz macierzy odbioru 155. Brakujące EN etykiety
blokują PASS 155.3; awaryjna narracja musi być bezpieczna, nie literacko idealna.
