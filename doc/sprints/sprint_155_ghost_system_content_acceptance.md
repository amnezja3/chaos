# Sprint 155 — Ghost System: treści, historia i pełny odbiór PL/EN

Status: **LOKALNY PAKIET DO ODBIORU PRZEDWDROŻENIOWEGO — bez pełnego PASS**,
12 X 2026. [Aktualna macierz dowodów i bramek](../audits/sprint_155_acceptance.md).
[154](sprint_154_ghost_system_apps_catalogs.md) ma PASS użytkownika.
Autor zezwolił na rozpoczęcie po działających generacjach Mistrala i zapisie
sekretu web/workera w PM2 (zgodne klucze; autostart enabled/active).
Nie oznacza to automatycznie pełnego odbioru macierzy polityk i 30 minut ruchu
[154.8 — Mistral API i fallback Ollama](sprint_154_8_narrative_providers_mistral.md).
Zakres językowy 155 pozostaje bez zmian. Ostatni sprint programu
rozpoczętego w [153](sprint_153_ghost_system_i18n_foundation.md).

## Cel

Aktualizacja 13 X: rozgrywka wznowiona, odbiór narracji prowadzony osobno.
[155.3 — BlackNet: język źródła i naturalna rotacja sygnałów](sprint_155_3_blacknet_languages.md)
wydziela radio, heurystyki GN i deklaracje języka w kreatorach. Zakres zaplanowany,
nie zaliczony; pełny PASS 155 nadal wymaga odbioru. Fallback Ollamy nie ma być
powodem dalszego zatrzymywania gry ani nieskończonego strojenia stylu.

### Postęp 12 X — implementacja lokalna, bez pełnego PASS

- Pakiet 155.2.0: bazowe karty Googleplex News, loading/error/empty, CTA,
  licznik, statystyki i etykiety PL/EN. Copy techniczne zastąpione tekstem gracza.
- Neutralna etykieta redakcyjna zamiast mylącego oznaczenia Ollamy; zachowane
  istniejące techniczne pola kompatybilności. Produkty graczy nie są tłumaczone.
- Przełączenie locale przerysowuje bazowe treści w otwartym News bez wywołania LLM.
- Testy Python i JS oraz Playwright na izolowanym komponencie desktop/mobile.
  Pełny odbiór zalogowanego pulpitu i produkcji pozostaje do wykonania.
- Komunikaty instalacji obu ścieżek zapisują metadane `system_copy` w store;
  toasty PL/EN zmieniają język bez zmiany nazwy UGC i bez ponownej emisji.
  Odczyt dokładnie rozpoznanych starszych wpisów źródła `googleplex_install`
  dodaje metadane bez zapisu, resetu statusu lub zmiany ID. Niejednoznaczne
  i autorskie wpisy pozostają bez tłumaczenia. Pełna migracja historii nadal osobno.
- Rozszerzono ścisłe rozpoznawanie trwałych komunikatów. Nie obejmuje jeszcze
  wszystkich zdarzeń i historii; cały sprint i pełne EN nie mają PASS.
- Warstwa wariantów News: tabela `ghost_news_locale_variants` z kluczem
  publikacja/weryfikowana wersja źródła/locale. `save_reviewed_variant` służy
  do zapisu po przeglądzie redakcyjnym; nie publikuje ani nie wywołuje modelu.
  Endpoint odczytuje warianty dopiero po ograniczeniu widoczności publikacji.
  Stary wariant nie pasuje po zmianie faktów, tekstu lub CTA. Zmiana PL/EN
  w otwartym Home zachowuje identyfikator, pozycję, datę i akcję.
- Dla istniejących opisów funkcji systemu bez EN: zatwierdzony szablon tylko
  po dopasowaniu kanonicznego source_ref. Pozostałe braki EN są jawnie opisane,
  bez polskiego tekstu udającego tłumaczenie. Ten komunikat przejściowy nie
  zalicza pełnego odbioru treści 155. Oryginały legacy nadal dostępne w PL.
- Asynchroniczny worker wariantów EN News jest opt-in: wspólny router dostawców,
  osobne EN warstwy promptów, ograniczone retry, lease i kontrola wersji/ważności
  źródła. Nie tłumaczy produktów graczy. Wymaga odbioru rzeczywistych generacji.
- Narzędzie backfillu: metadata-only inventory, dry-run, batche do 100 wpisów,
  checkpoint, idempotencja i rollback tylko nowych wariantów. Historia nie została
  jeszcze uzupełniona na produkcji. FM otrzymał osobne edycje EN about/tips-tricks.
- Show: zatwierdzona polityka tekstów według języka gracza, oryginalne media;
  49 scen PL/EN, archiwalne News powiązane z zamrożoną wersją publikacji.
  Playwright potwierdził ciągłość filmu bez odłączania video oraz brak overflow
  w 390×844. To odbiór komponentu, nie pełnego zalogowanego pulpitu.
- Regresja rozszerzonego etapu: 106 testów Python i osiem zestawów JS PASS.
  Dawny test filaru naprawiony przez aktualizację mocka ograniczonej projekcji
  profilu; mechanika endpointu bez zmian. Nowe testy wygaśnięcia źródła oraz
  odczytu zamrożonego archiwum również PASS.
  Końcowa regresja News/Show/dostawców: 92 testy PASS (zestawy częściowo
  pokrywają wcześniejsze 106; nie sumować jako unikalnych testów).
- [Przygotowanie wdrożenia i pozostałe bramki](../runbooks/ghost_content_155.md).
  Kolejny przyrost dodał trwały kontrakt języka i EN instrukcje wszystkich 11
  aktywnych wersji promptów, fallbacki, metadane publikacji, migrację ich języka,
  metadane systemowych wiadomości Cybernera, kolejne komunikaty terenu/więzienia
  oraz deklaratywne locale narracji/News. Testy dodatkowego locale bez nowych
  gałęzi aplikacji i [procedura](../runbooks/add_ghost_locale.md) są gotowe.
  Playwright sprawdził FM i Cyberner w pełnym rendererze izolowanego pulpitu.
  Pozostały końcowy audyt pokrycia wiadomości i historii, żywe próbki modeli,
  pełna pętla gry, fizyczne mobile i porównanie wydajności.

Zakres odbioru dotyczy wdrożonego Ghost Systemu; zamrożone sprinty 149–152
nie są zależnością ani warunkiem PASS. Ich przyszłe funkcje przejmą kontrakt i18n
dopiero po osobnej decyzji o wznowieniu.

Domknąć systemowe treści dynamiczne i zapisane, przeprowadzić bezpieczny rollout
oraz udostępnić pełną wersję angielską. Nie dopuścić do produktu, w którym
angielski pulpit nadal otrzymuje polskie systemowe błędy lub nieprzetłumaczone
Googleplex News. Sygnały BN i audycje zachowują swój zatwierdzony język.

## 155.1 — zdarzenia i wiadomości

- Potwierdzony przy odbiorze 154 brak: trwałe powiadomienia po instalacji
  narzędzi (`googleplex_install`: „Instalacja zakończona”, „Aplikacja … została
  poprawnie zainstalowana”). Objąć obie ścieżki instalacji, nowe wpisy i historię;
  zachować autorską nazwę aplikacji, identyfikator zdarzenia i deduplikację.
  Odpowiedź instalatora `shop.installed` jest już lokalizowana w 154.

- Komunikaty operacji, logi widoczne graczowi, nagrody LVL/RSP/HC, terytoria,
  wtargnięcia, konflikty, Response Network, konsekwencje, zatrzymanie i więzienie,
  reputacja, portfel, questy/tutoriale oraz GhostNetwork mają klucze i parametry.
  Logi techniczne dla operatora mogą pozostać w jednym języku; tekst pokazany
  graczowi jest częścią zakresu PL/EN.
- Szablonowe powiadomienia systemowe Cybernera, World i innych kanałów są
  lokalizowane per odbiorca. BlackNet: systemowe etykiety lokalizowane per
  odbiorca, sygnał publikowany raz
  w przypisanym języku. Googleplex News wyświetla tytuł, lead i treść zgodnie
  z językiem ustawionym przez gracza. Wiadomości użytkowników,
  klanowe dokumenty i komentarze pozostają oryginalne. Mieszany kanał musi
  poprawnie obsługiwać oba pochodzenia obok siebie.
- Trwały event przechowuje identyfikator, wersję schematu treści, klucz/parametry
  albo referencję do pojedynczej publikacji z jej językiem. Język nie wchodzi do dedupe key,
  payment key, receipt ani tożsamości zdarzenia. Odczyt w EN nie tworzy drugiej
  nagrody, alarmu lub wiadomości ani nie odtwarza już zużytego toastu.
- Feed/delta/recovery korzystają z tego samego kontraktu. Zmiana języka
  przerysowuje dostępne wpisy historii, ale zachowuje read cursor, unread,
  kolejność i limity historii World (100 / 14 dni, fallback 10).
- Lokalizowane są również systemowe raporty i dokumenty dostarczane jako pliki.
  Widok/eksport wybiera język, nie zmienia identyfikatora pliku, rozmiaru
  gameplayowego, jakości, zasobów ani wartości paczki na rynku.

### Dokumentacja FM — `/about` i `/tip&trick`

- Decyzja autora: zachować obecne foldery, dokumenty i sposób ich otwierania.
  Aktualny techniczny klucz drugiego folderu to `tips-tricks`; nie zmieniać
  ścieżek ani istniejących odwołań w ramach lokalizacji.
- Dodawać kolejne wydania w zatwierdzonych językach jako osobne dokumenty
  w tych samych folderach, z czytelnym oznaczeniem języka. Oryginały pozostają
  dostępne; zmiana locale nie zastępuje ich treści i nie ukrywa innych wydań.
- Wersje językowe przygotować i zatwierdzić jako statyczne materiały systemowe.
  Bez generowania/przekładu przez Ollamę podczas otwierania pliku.
- Nowe wydania mają własne niekolidujące identyfikatory i odniesienie do
  dokumentu źródłowego oraz jego wersji. To wyjątek od prezentowania tego samego
  pliku w różnych językach: nie nadpisywać ID ani zawartości istniejącego pliku.
- Odbiór: oryginały nadal otwierają się dawnymi odwołaniami, obok dostępne są
  zatwierdzone wydania językowe, a przełączenie PL/EN nie zmienia otwartego tekstu.
  Żadne dokumenty graczy nie są objęte tym uzupełnieniem.

## 155.2 — narracja LLM i multimedia

- Rozdzielić kanoniczne fakty/CTA publikacji od tekstu. Jedna publikacja BlackNet
  ma jeden zatwierdzony język: np. sygnał BN A po polsku, sygnał BN B po angielsku.
  Nie tworzyć tłumaczonych kopii tego samego sygnału per język lub odbiorca.
  Język UI nie zmienia oryginalnej narracji BN. Tekst musi odpowiadać faktom i CTA.
  **Wyjątek medium: Googleplex News** ma wariant treści dla locale odbiorcy,
  opisany poniżej; reguły pojedynczego języka BN nie stosować do News.
- Generowanie systemowej prozy wykonać asynchronicznie przy publikacji
  lub kontrolowanym backfillu, z cache, limitami kolejki, retry i walidacją.
  Nie wywoływać Ollamy przy otwarciu aplikacji ani zmianie języka; nie podwajać
  publikacji per odbiorca. Uwzględnić ograniczenie zasobów Ollamy opisane
  w [hardbugfixie](../hardbugfix/ollama_cpu_quota_2026-10-05.md).
- Gdy model nie dostarczy poprawnego tekstu, użyć zatwierdzonego szablonu
  w języku przypisanym do publikacji. Nie przełączać języka podczas retry.
  Awarię oraz użycie szablonu mierzyć, bez ujawniania prywatnych treści.
- Własne dokumenty, opisy i wiadomości graczy nie trafiają do tego pipeline'u.
  Zgoda na użycie asystenta kreatora nie oznacza zgody na tłumaczenie publikacji.
- Zinwentaryzować napisy w obrazach, canvas/SVG, animacjach, filmach i wypowiedziach
  systemowych. Tekst przenieść do renderowania językowego albo przygotować
  wersje zasobów UI. Mowa i napisy narracyjnej audycji mają język tej publikacji;
  efekty bez słów i uzgodnione nazwy własne pozostają wspólne.

### Kontrakt 155.2a — zatwierdzone polecenia narracji Ollamy

Ghost Signal Show / Sender ma osobny obowiązkowy odbiór, opisany w B14/C06
[rejestru](../audits/ghost_system_i18n_inventory.md): transmisja, manifest,
sceny, odliczanie, plansze, podpisy, audio/wideo, wynik i archiwum/replay.
Decyzja autora 12 X 2026: teksty systemowe i plansze według języka gracza
(`reader_locale`); oryginalne audio i wideo pozostają wspólne
(`original_language`). Nie tworzymy drugiej transmisji ani drugiego wyniku.
Nie dziedziczymy wyjątku BN dla tekstów systemowych. Zmiana języka nie
restartuje zegara ani nie uruchamia transmisji,
nagród lub rozliczenia terenu. Testy obejmują zmianę locale w trakcie,
recovery, brak mediów i stare snapshoty, bez powtórzenia efektów gry.

- Zlecenie zawiera również `medium` i wynikającą z niego politykę językową:
  `blacknet = original_language`, `googleplex_news = reader_locale`.
  Dla pozostałych wydawców rejestr ustala politykę jawnie; nie dziedziczą
  automatycznie wyjątków BN lub News.
- Wspólny rejestr określa zatwierdzone języki wyjściowe i wersje promptów:
  początkowo PL/EN. Każda rodzina narracji ma zatwierdzony wariant polecenia
  PL i EN, wspólny schemat wyniku, glosariusz i reguły faktów. Dodanie locale
  do selektora UI nie uprawnia automatycznie do generowania narracji w tym języku.
- Zlecenie zawiera `event_id`, `content_version`, `facts_version`, `output_locale`
  oraz `prompt_version`. Locale przechodzi allowlistę serwera; `ANY`, dowolny
  tekst gracza i niezatwierdzony język nie są poprawnym językiem generowania.
- Audyt obejmuje wszystkie warstwy polecenia: system prompt, instrukcję zadania,
  przykłady, schemat odpowiedzi, retry i fallback. Dla EN nie może pozostać
  nadrzędne „odpowiadaj tylko po polsku”; wariant PL nie dostaje przeciwnych
  instrukcji z szablonu EN. Polityki bezpieczeństwa i reguły świata są wspólne.
- Dla BN język wybiera polityka wydawcy/kanału spośród zatwierdzonych locale i zapisuje
  w zadaniu przed generowaniem. Kolejne sygnały mogą mieć różne języki;
  jeden sygnał nie ma obowiązkowej pary PL/EN. Reguły wyboru są jawne i testowane,
  bez uzależnienia wspólnego feedu od języka osoby, która właśnie go otwiera.
- „Niewykluczające się” dotyczy instrukcji promptu: polecenie systemowe, zadanie,
  przykłady i retry są zgodne z jednym `output_locale` i wspólnymi zasadami świata.
  Walidacja porównuje tekst z faktami jego wydarzenia, nie z drugim tłumaczeniem.
- Dla BN publikacja ma jedną tożsamość `(event_id, content_version)` i przypisany język.
  Retry zachowuje `output_locale`; język ani zmiana promptu nie tworzą drugiej
  publikacji lub nagrody. Cache zadania uwzględnia locale i wersję promptu,
  a opóźniony wynik starszej wersji nie zastępuje aktualnej treści.
- Przed publikacją sprawdzić język, wymagane pola, parametry i zgodność z faktami.
  Ocena semantyczna próbek PL/EN jest częścią odbioru; samo wykrycie języka nie
  dowodzi zgodności narracji. Błędny wariant nie trafia do kanału: ograniczony
  retry lub zatwierdzony szablon w wymaganym języku.
- Radio PL emituje publikacje polskie, EN angielskie. Nie tłumaczy automatycznie
  tej samej audycji na drugi kanał. ANY pozwala
  słuchać różnych kanałów/języków, ale nie miesza wariantów w jedno polecenie
  modelu i nie wymusza powtarzania każdej audycji w obu językach.
- Testy kontraktu: osobne sygnały PL i EN bez kopii językowych, sprzeczne instrukcje promptu,
  niezatwierdzony locale, `ANY`, zmiana faktów podczas generowania, retry,
  timeout, zachowanie języka retry, niezgodne CTA/liczby i duplikat publikacji. Próbki
  z rzeczywistej Ollamy muszą przejść odbiór językowy; stub nie wystarcza do PASS.

### 155.2b — Googleplex News zgodne z ustawieniem gracza

#### Uzupełnienie audytu 12 X 2026 — karty bazowe i placeholdery

- Objąć zatwierdzonym copy PL/EN wszystkie 12 bazowych slotów z
  `build_googleplex_news_snapshot` w `googleplex_news.py`: world-grid, blacknet,
  exchange, map, cyberner, featured, operations, packages, storage, clans,
  integrity i protocol. Są renderowane także bez publikacji LLM, więc ich
  odbiór nie może zależeć od wygenerowania narracji. W `featured` tłumaczyć
  wyłącznie systemowy fallback katalogu; nazwy/opisy produktów graczy zachować.
- Zastąpić robocze opisy implementacji tekstem przeznaczonym dla gracza
  (m.in. „News nie jest source of truth”, „Capacity jest prezentowane bez odczytu
  profilu”, „Pliki pozostają w swoich canonical surfaces”, „Audience projection”).
  Nie tłumaczyć tych technicznych placeholderów dosłownie jako finalnego copy.
  Nie sugerować prawdziwego zdarzenia ani aktualnej statystyki, gdy karta jest
  tylko stałym wejściem do aplikacji lub informacją o braku danych.
- W `static/js/googleplex_news.js` objąć PL/EN loading, error, empty, niepoprawny
  snapshot, nagłówek i licznik SIGNALS (pluralizacja), CTA, READ ONLY, kategorie,
  etykiety statystyk, aria-labels, tekstowy fallback grafiki i stopkę protokołu.
- Usunąć mylące oznaczenia gracza `OLLAMA_ENRICHED`, `OLLAMA ENRICHED` oraz
  `OLLAMA: ACTIVE/NOT USED`. Obecnie `merge_googleplex_narrative_publications`
  ustawia `source=ollama_enriched` i `ollama_used=true` dla scalonych publikacji
  bez rozróżnienia dostawcy, a renderer pokazuje je wprost. Użyć neutralnego,
  lokalizowanego oznaczenia redakcyjnego. Jeżeli dostawca jest potrzebny w
  diagnostyce, brać go z metadanych konkretnej próby/kandydata, nie z aktualnej
  konfiguracji ani historycznej nazwy pola; nie zgadywać dostawcy starych wpisów.
  Zachować kompatybilność technicznych pól/ID i odwołań do publikacji.
- Odbiór obejmuje puste publikacje, wszystkie sloty bazowe, mieszany feed
  bazowy + Mistral/Ollama/szablon deterministyczny, brak EN, awarię API i brak
  grafiki. Dwa konta PL/EN i przełączenie locale w otwartym News mają zachować
  ID, kolejność, CTA i brak ponownej publikacji. Brak modelu nie może ujawniać
  polskiego ani technicznego placeholdera w EN. Testy UI desktop/mobile.
- Polecenia i odbiór językowy 155.2a dotyczą wspólnego adaptera narracji po
  154.8: Mistrala oraz fallbacku Ollamy. Wzmianki o Ollamie w starszym opisie
  nie ograniczają zakresu do lokalnego modelu. Żaden dostawca nie jest wywoływany
  podczas otwierania News lub zmiany języka.

#### Kontrakt treści i publikacji

- Ustawienie Polski wyświetla systemowe newsy po polsku, English po angielsku:
  tytuł, lead, treść, systemowe kategorie i etykiety CTA. Zmiana języka
  przełącza prezentację także już otwartej wiadomości.
- Jedna wiadomość News ma jedno `publication_id` i warianty PL/EN tej samej
  wersji faktów. Nie tworzą one dwóch pozycji feedu, nowych nagród lub CTA.
  Język nie zmienia daty, kolejności ani tożsamości wiadomości.
- Zatwierdzony prompt odpowiada wybranemu wariantowi News; przygotowanie
  wariantów asynchroniczne, cache po publikacji, wersji i locale. Brak wywołania
  Ollamy podczas czytania lub przełączania języka. Nie generować osobno dla kont.
- Gdy brakuje poprawnego wariantu, użyć zatwierdzonego szablonu w języku gracza,
  opartego na faktach tego newsa. Nie zastępować go cicho tekstem w innym języku.
  Tytuły produktów, nicki i dosłowne cytaty graczy zachowują oryginał.
- Idempotencja przygotowania wariantu uwzględnia locale; idempotencja publikacji
  i efektu CTA pozostaje wspólna. To jawne odstępstwo od reguły BN „jeden język”.
- Odbiór: dwa konta PL/EN widzą ten sam news w swoim języku; przełączenie
  otwartego artykułu, brak wariantu, retry i starsza wersja nie duplikują feedu.

## Historia i migracja — wymagania przekrojowe 155

Pierwotnie punkt 155.3. Od 13 X numer 155.3 oznacza osobny
[podsprint BlackNet](sprint_155_3_blacknet_languages.md); poniższe wymagania
pozostają obowiązujące dla całości 155, także dla migracji BN.

- Inwentaryzacja istniejących wiadomości, szablonów i produktów przed migracją:
  źródło, liczba, rozmiar, identyfikatory, możliwość odzyskania klucza/parametrów.
- Jednoznaczne stare komunikaty systemowe mapować po źródle i kontrakcie na
  klucze; nie wykonywać globalnego replace polskich słów. Historycznej narracji
  nie tłumaczyć ani nie publikować ponownie: uzupełnić metadane języka tam,
  gdzie można go wiarygodnie ustalić. Wyjątek Googleplex News: przygotować
  brakujące warianty językowe dostępnej historii offline, zachowując ID,
  datę, oryginał i wersję dla audytu; bez ponownej publikacji.
- Niejednoznaczne wpisy pozostają bez zmian do ręcznego rozstrzygnięcia
  pochodzenia. Znane, nadal dostępne graczowi systemowe treści bez EN blokują
  pełny PASS, z wyjątkiem narracji publikowanej jednokrotnie w swoim języku.
  Oznaczenie zwykłego komunikatu UI jako „legacy” nie zwalnia z zakresu.
- Skrypt: dry-run z raportem, ograniczone batche, checkpoint, idempotencja,
  możliwość wznowienia i rollback wyłącznie nowych danych lokalizacji.
  Brak ponownego wysyłania wiadomości, resetu read cursor i naliczania nagród.
- Migracje poza requestami; izolowana regresja, dry-run, backup i instrukcja operatorska.
  Decyzja autora 12 X: bez dodatkowej instancji gry/katalogu aplikacji/portu.
  Izolowane testy lokalne, spójny backup, dry-run schematu i migracja na obecnej
  produkcji. Kontrole hash/integralności i rollback: [komendy](../runbooks/ghost_content_155.md).
  Nie modyfikować hurtowo profili, artefaktów graczy ani podpisów kontraktów.

## 155.4 — pełne pokrycie i rollout

- Zamknąć rejestr z 153: aktywne interfejsy, administracja, odzyskanie sesji,
  serwis/offline, ekran startowy, pomoc i treści niedostępne dla zwykłego konta
  muszą mieć pokrycie. Archiwalne, nieużywane pliki oznaczyć jako takie z dowodem,
  aby nie zawyżały deklarowanego pokrycia.
- CI: zgodność kluczy i parametrów PL/EN, wszystkie formy pluralizacji,
  brak uszkodzonych placeholderów, skan nowych literalnych tekstów systemowych,
  kontrola wyjątków oraz test nietłumaczenia UGC. Skan literalów jest pomocą,
  nie dowodem kompletności bez testów działającej aplikacji.
- Playwright i odbiór językowy: pełna pętla gry po angielsku i regresja po polsku,
  desktop/mobile, powiększone okna, fullscreen gry, klawiatura ekranowa,
  długi tekst, różne strefy czasowe. Test automatyczny viewportu uzupełnić
  odbiorem na fizycznym Androidzie i iOS; wyników nie zastępować deklaracją.
- Równoczesne konta PL/EN widzą ten sam świat i saldo. Zmiana języka podczas
  operacji, odbioru delty, tworzenia projektu, podróży i sprzedaży nie powiela
  działań, nie resetuje postępu i nie gubi draftu.
- Porównać baseline czasu startu pulpitu, wielkości bootstrapu/paczek, liczby
  requestów i czasu renderowania. Katalogi domen ładowane na żądanie i cache'owane;
  brak pełnych profili i wywołań tłumacza w zwykłych odczytach.
- Rollout: środowisko testowe → konta testowe PL/EN → włączenie EN dla graczy
  po odbiorze. Rollback wyłącza wybór EN i przywraca PL, zachowując stan gry,
  ustawienia i oryginalne treści. Braki tłumaczeń mają raport z kluczem/domeną,
  bez treści prywatnych wiadomości w telemetrii.

## 155.5 — procedura dodania kolejnego języka

Runbook opisuje: rejestrację locale i kierunku pisma, komplet katalogów,
pluralizację i formaty, fonty/glyphy, zatwierdzone prompty narracji i media, kontrolę jakości,
testy oraz dopuszczenie do selektora. Zademonstrować dodanie testowego pakietu
przez manifest i katalogi bez nowej gałęzi logiki w aplikacjach. Gotowa wersja
rosyjska/hiszpańska nie jest częścią tych trzech sprintów.

## Twarda bramka końcowa

**PASS 155 / pełne PL–EN** dopiero po spełnieniu wszystkich warunków:

1. 100% wymaganych pozycji inwentarza systemowego ma zatwierdzone PL i EN,
   włącznie z treściami trwałymi, komunikatami błędów i zasobami multimedialnymi.
   Narracja jest wyjątkiem: jedna publikacja w jednym zatwierdzonym języku,
   poprawne metadane i prompt; nie wymaga odpowiednika w drugim języku.
   Wyjątek nie obejmuje Googleplex News — jego treść musi odpowiadać locale gracza.
2. Brak nieuzgodnionych braków EN maskowanych polskim fallbackiem.
3. UGC i nazwy własne zachowane, kontrakty i skutki gameplayowe identyczne.
4. Migracja i rollback sprawdzone; brak ponownej emisji historycznych zdarzeń.
5. Automatyczne testy i odbiór językowy oraz mobilny zaliczone, dowody w raporcie.
6. README, journal, glosariusz, rejestr pokrycia i runbook nowego języka aktualne.

Brak powyższych warunków oznacza dalszą wersję testową, nie częściowe „pełne EN”.
