# Sprint 155 — Ghost System: treści, historia i pełny odbiór PL/EN

Status: **ZAPLANOWANY**, 6 X 2026. Po PASS
[154](sprint_154_ghost_system_apps_catalogs.md). Ostatni sprint programu
rozpoczętego w [153](sprint_153_ghost_system_i18n_foundation.md).

## Cel

Zakres odbioru dotyczy wdrożonego Ghost Systemu; zamrożone sprinty 149–152
nie są zależnością ani warunkiem PASS. Ich przyszłe funkcje przejmą kontrakt i18n
dopiero po osobnej decyzji o wznowieniu.

Domknąć systemowe treści dynamiczne i zapisane, przeprowadzić bezpieczny rollout
oraz udostępnić pełną wersję angielską. Nie dopuścić do produktu, w którym
angielski pulpit nadal otrzymuje polskie systemowe błędy lub nieprzetłumaczone
Googleplex News. Sygnały BN i audycje zachowują swój zatwierdzony język.

## 155.1 — zdarzenia i wiadomości

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
UI i systemowe etykiety otrzymują PL/EN. Politykę narracji GhostSignal trzeba
jawnie zatwierdzić dla tego medium przed generowaniem; nie dziedziczyć
wyjątku BN. Zmiana języka nie restartuje zegara ani nie uruchamia transmisji,
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

## 155.3 — historia i migracja

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
- Migracje poza requestami; test na kopii danych, backup i instrukcja operatorska.
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
