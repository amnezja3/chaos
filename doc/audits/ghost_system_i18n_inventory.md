# Ghost System PL/EN — mapa zakresu i rejestr startowy Sprintu 153

Stan: **przygotowanie zakresu**, 6 X 2026. Dokument opisuje, co ma otrzymać
wersje językowe; nie potwierdza wykonania tłumaczeń. Podstawa:
[153](../sprints/sprint_153_ghost_system_i18n_foundation.md),
[154](../sprints/sprint_154_ghost_system_apps_catalogs.md),
[155](../sprints/sprint_155_ghost_system_content_acceptance.md).

153: **PASS lokalny**, [rejestr 496 kluczy](sprint_153_key_register.md),
[format v1](../architecture/ghost_i18n_v1.md), [odbiór](sprint_153_acceptance.md).
Fundament i powłoka A01–A11 zakończone. Dalsze obszary tabeli należą do 154/155;
ich opis jest planem, nie deklaracją gotowości angielskiej wersji całej gry.

Przejrzano punkty wejścia szablonów i rendererów oraz plany funkcjonalne.
Poniższe źródła są punktami rozpoczęcia migracji, nie pełnym spisem każdego
literalnego tekstu ani dowodem aktywności wszystkich historycznych plików.
W 153 należy rozwinąć każdy wiersz do rejestru kluczy i scenariuszy.

## Granica wersji językowej

**PL i EN obejmują całą prezentację dostarczaną przez system:** nazwy i opisy
systemowych elementów, nawigację, instrukcje, formularze, statusy, walidację,
błędy, powiadomienia, wyniki operacji, pomoc, dokumentację w grze i narrację.
Obie wersje korzystają z tego samego świata, produktów, kont, operacji i danych.

Wyjątek dla narracji: pojedynczy sygnał BN powstaje
w jednym zatwierdzonym języku. Kolejne publikacje mogą być raz PL, raz EN;
nie generujemy tego samego sygnału w obu językach. Jego otoczka UI jest PL/EN.
Googleplex News ma osobną zasadę: tytuł, lead i treść odpowiadają językowi
ustawionemu przez gracza. To warianty jednej wiadomości, nie kopie w feedzie.
Pozostali wydawcy LLM, w tym GhostSignal, wymagają jawnej polityki medium;
nie dziedziczą automatycznie reguły BN ani Googleplex News.

**Nie tłumaczymy automatycznie twórczości graczy:** produktów i ich opisów,
dokumentów, wiadomości, komentarzy, własnych etykiet, nazw projektów i tekstów
przycisków. To samo dotyczy treści przygotowanej z pomocą AI i zapisanej jako
autorski materiał gracza. Lokalizujemy systemową otoczkę tych treści.

Nazwy własne (np. GhostLab, Googleplex, VW, nick, nazwa sklepu) mogą pozostać
identyczne. Nie zmieniamy identyfikatorów, komend, URL-i, nazw plików na dysku,
kodów akcji, receiptów, salda ani reguł gry. RU/ES są przyszłymi pakietami;
w 153 sprawdzamy gotowość techniczną na dodatkowy język, nie tłumaczymy ich w całości.

## A. Zakres wdrożenia w 153 — fundament i powłoka

W każdym wierszu stan startowy jest taki sam: **istniejący UI wymaga ekstrakcji;
katalogi PL/EN oraz odbiór — DO WYKONANIA**. Klucze są propozycją przestrzeni
nazw, nie już istniejącym API. Obie wersje powstają razem; PL nie jest surowym
tekstem pozostawionym w kodzie jako druga ścieżka implementacji.

| ID / domena | Powierzchnia i teksty | Punkty źródłowe | Odbiór 153 |
| --- | --- | --- | --- |
| A01 `account.entry` | Logowanie, rejestracja, onboarding, pola, placeholdery, wskazówki, walidacja i odmowy | `templates/login.html`, `templates/register.html`, `static/js/register_scripts.js`, odpowiadające endpointy `run.py` | Formularz poprawny i błędny, niezalogowany użytkownik PL/EN |
| A02 `account.session` | Wygasła/zablokowana sesja, ponowne logowanie, odzyskanie połączenia | `templates/session_generation_blocked.html`, `static/js/session_generation.js`, `run.py` | Wygaśnięcie przy otwartym formularzu; poprawny język i brak utraty danych przez samo przełączenie |
| A03 `shell.desktop` | Pulpit, start, launcher, systemowe nazwy aplikacji, belka, cel i statystyki | `templates/index.html`, `templates/linux.html`, `static/js/terminal.js` | Start sesji, otwarcie aplikacji, zmiana języka przy kilku oknach |
| A04 `shell.window` | Zamknij, minimalizuj, powiększ, przywróć, menu kontekstowe, tooltipy i aria-label | `static/js/terminal.js`, szablony okien | Zwykłe/powiększone okno, jedna/dwie linie ikon, mobile, fullscreen gry |
| A05 `account.settings` | Język, dźwięk, pulpit, grafika/fullscreen i wszystkie obecne opcje ustawień | `createSettings()` w `static/js/terminal.js`, writer ustawień w `run.py`; wzorzec testów `tests/test_desktop_settings_writer.py` | Zapis locale, ponowne logowanie, dwa konta z różnymi językami |
| A06 `account.profile` | Systemowe pola profilu, poziom, respect, frakcja/klan, statusy i objaśnienia | `createProfile()`, `static/js/AvatarSelector.js`, projekcje konta w `run.py` | Etykiety PL/EN, nick i własny opis bez zmian |
| A07 `account.wallet` | Portfel, saldo, formularze, potwierdzenia i systemowe etykiety historii | `renderWalletApp()`, `renderWalletHistory()`, endpointy w `run.py` | Lokalny format kwoty; identyczne HC i wynik transakcji; autorski tytuł pozostaje |
| A08 `shell.terminal` | Powitanie, prompt opisowy, pomoc, błędna komenda, status otwierania aplikacji/pliku | `static/js/terminal.js` | Komendy niezmienne, odpowiedzi powłoki PL/EN, zachowany input i historia |
| A09 `shell.files` | Foldery prezentacyjne, typy plików, akcje, filtry, zajętość dysku, puste stany i błędy | `createFileManager()` w `static/js/terminal.js`, endpointy inventory w `run.py` | Te same pliki/ID i ścieżki, lokalne etykiety, treść dokumentu autora bez zmian |
| A10 `common` | Wspólne przyciski, dialogi, ładowanie, brak danych, anulowanie, ponów, zachowaj zmiany | Wspólne renderery `static/js/terminal.js` i używające ich widoki | Ten sam klucz i znaczenie w różnych aplikacjach; niezapisany draft przetrwa zmianę |
| A11 `locale` | Selektor Polski/English, manifest, katalogi, interpolacja, pluralizacja, daty i liczby | Nowy moduł klienta i serwera, integracja bootstrapu i ustawień | Zgodność JS/Python, fallback, cache, wyścig przełączeń, awaria paczki |

Granica A07/A08/A09: w 153 tłumaczymy powłokę, wspólne akcje i bieżące odpowiedzi
jej endpointów. Historyczny opis nagrody w portfelu, raport specjalistycznego
narzędzia w terminalu lub treść systemowego dokumentu nie mogą zostać pominięte
w całym programie — ich konwersja jest przypisana do C01/C03/C04 w 155.

Wyjątek A09/C04: FM `/about` i `/tip&trick` (w kodzie `tips-tricks`) zachowują
obecną zawartość i strukturę. Dodajemy osobne, oznaczone językiem dokumenty
w zatwierdzonych locale, obok oryginałów. Nie podmieniamy treści ani nie ukrywamy
wydań po zmianie języka UI. Nowe pliki mają osobne ID i powiązanie z wersją
źródłową; oryginalne ścieżki/ID pozostają działające. Przygotowanie statycznych
wydań w 155, bez tłumaczenia na żądanie przez Ollamę.

## B. Zakres zinwentaryzowany w 153, wdrażany w 154

Aktualizacja 8 X 2026: implementacja pakietu **154.7.0** domknięta lokalnie.
Pokrycie B01–B15 i dowody testów: [macierz odbioru 154](sprint_154_acceptance.md).
Odbiór produkcyjny nowego pakietu pozostaje otwarty. Poniżej zachowano kontrakt zakresu.

| ID / domena | Zakres wersji językowych | Źródła startowe / odbiór |
| --- | --- | --- |
| B01 `map` | Mapa, skan, legenda, typy scen/obiektów, systemowe nazwy NPC, menu, oznaczenie celu, podróż, podatności | `templates/map_template.html`, `static/js/map/`, endpointy `run.py`; cały przebieg skan → cel → akcja |
| B02 `map.picker` | Wybór narzędzia, nazwa akcji, zgodność z celem, brak narzędzia, niedostępność | `createMapToolPicker()`, kontrakty akcji w `run.py` i `creator_policy.py`; zgodne nazwy w mapie/kreatorze/pickerze |
| B03 `workspace` | Territory Control, Operation Control, Victim Picker, Ghost Network Suit i Signal Registry | Renderery `static/js/terminal.js`, moduły GN; każda zakładka, status i pusty stan |
| B04 `catalog.googleplex` | Nawigacja, kategorie/filtry, aliasy wyszukiwania, parametry oferty, zakup, pobranie, instalacja, aktualizacja, wycofanie | `createBrowser()`, `googleplex_search_presentation.js`, `run.py`; systemowe oferty oraz oferty graczy obok siebie |
| B05 `catalog.exchange` | Ghost Exchange: typy danych, kompletowanie paczki, ceny, sprzedaż, historia i wykresy | `createBrowser()`, rynek w `run.py`; identyczny wynik sprzedaży PL/EN |
| B06 `communications.ui` | Cyberner, BlackNet, kanały, filtry, formularze, wyszukiwanie, status dostarczenia | `createEmailClient()`, `createBrowser()`, `static/js/bn_page.tsx` po potwierdzeniu aktywnego użycia; treść wpisów w C02/C03 |
| B07 `ghostlab` | Projects, Templates, edytor, walidacja, compile, publisher, wersje, Documentation, obecne zakładki Research/Exchange | `renderGhostLabTab()` i renderery edytora w `terminal.js`, `ghostlab_policy.py`; rzeczywista dostępność funkcji |
| B08 `creators` | AppForge, Term Creator, Window Maker, Button Choice: szablony, przeznaczenia, generowanie, płatność, publikacja i błędy | `static/js/creator_editor.js`, `terminal.js`, `creator_policy.py`; własne pola autora nienaruszone |
| B09 `tools.pvp` | System Log Reader, Security Panel Proxy, Financial Sniffer, Friend Kicker, Arsenal Cleaner, Intruder Kicker: opisy, wymagania, instrukcje, cooldown, wynik | Katalog i runtime w `run.py`, rodziny GhostLab; po jednym pełnym scenariuszu każdej rodziny |
| B10 `tools.travel` | Bilety, kierunki, wymagania, wybór i wynik podróży | `ghostlab_travel.py`, `ghostlab_ticket_policy.py`, katalog `run.py`; nazwa miasta pozostaje nazwą własną |
| B11 `tools.service` | Konserwacja, firmware, Deep Scannery, diagnostyka, błędy i recovery | `ghostlab_maintenance.py`, `static/js/ghostlab_maintenance.js`, `ghostlab_firmware.js`, `ghostlab_scanner.js`, `ghostlab_scanner_map.js` |
| B12 `catalog.upgrades` | Dysk/pamięć, mapa, zasięg skanu i pojazdu, wszystkie pozostałe systemowe produkty z katalogu | Rejestry produktów `run.py`, szablony GhostLab; opis efektu i jednostek oraz wynik użycia |
| B13 `radio.channels` | Kanały/filtr PL, EN, ANY; metadane kanału i audycji, systemowe opisy, zapamiętana preferencja, pusty stan | `static/js/ghost_radio.js`, `static/js/admin_radio.js`, endpointy `/api/radio/channels` i `/api/radio/channel/...`; macierz języków i brak przerwania audio po zmianie UI |
| B14 `signal.transmission` | Ghost Signal Sender: systemowa prezentacja nadawania, warunków, blokad, etapów i wyniku; Signal Registry: lista, szczegóły, ranking i archiwum | `ghostnetwork/transmission.py`, `ghostnetwork/show.py`, `run.py`, `loadGhostSignalArchive()` w `static/js/terminal.js`; Sender oznacza ścieżkę transmisji, nie nową aplikację; treść pokazu w C06 |
| B15 `support.reporter` | Dev Bug Reporter z pulpitu: formularz, wskazówki, walidacja, wysyłanie, potwierdzenie i błąd | `createDevBugReporterApp()` w `static/js/terminal.js` i endpoint zgłoszeń; tekst i załączniki gracza bez tłumaczenia; administracja w C07 |

Obowiązek pokrycia dotyczy również systemowych części narzędzi wygenerowanych
przez gracza. Nie ograniczamy go do produktów wystawionych przez system.
Jednak nazwa/opis autora i jego wersjonowany dokument pozostają oryginalne.

## C. Zakres zinwentaryzowany w 153, domykany w 155

Stan wszystkich pozycji: **PLAN / wymagana analiza pochodzenia i trwałych danych**.

| ID / domena | Zakres wersji językowych | Źródła startowe / odbiór |
| --- | --- | --- |
| C01 `events` | Wyniki operacji, nagrody, teren, wtargnięcia, konflikty, sukcesy/odmowy i toasty, także zapisane | `run.py`, `database.py`, `player_progression.py`, `static/js/operation_feedback.js`; jeden event, dwa języki, bez podwójnej nagrody |
| C02 `communications.system` | Systemowe wiadomości Cybernera/World i pozostałych kanałów, powiadomienia bezpośrednie | Store'y i producenci wiadomości w `run.py`/`database.py`, `cyberner_history.py`; zachować read/unread, kursor i limit historii |
| C03 `narrative` | BlackNet: jeden język na sygnał; Googleplex News: treść według locale gracza; AGI 2108, NPC i GhostNetwork: jawna polityka wydawcy | `googleplex_news.py`, `static/js/googleplex_news.js`, `ghostnetwork/`; zgodność z faktami/CTA, brak duplikatów feedu, News dla kont PL/EN |
| C04 `documents.system` | Raporty, instrukcje, tutoriale, dokumenty i pliki dostarczane przez system | Producenci artefaktów i czytniki; wariant treści nie zmienia ID, jakości ani wartości zasobu |
| C05 `consequences` | Response Network, ostrzeżenia, areszt, więzienie, ryzyko, uwolnienie, ograniczenia i recovery | `static/js/detention.js`, `consequence_show.js`, `run.py`; cały przebieg wraz z błędem i wznowieniem |
| C06 `media` | Napisy w canvas/SVG/obrazach, animacjach, wideo i systemowej mowie | `static/js/ghost_signal_show.js`, `ghost_radio.js`, `game_sfx.js`, używane zasoby; tekst i mowa PL/EN, wspólne efekty bez słów |
| C07 `admin` | Aktualnie używane ekrany administracji, bug reports, radio, maintenance/offline, narzędzia operatorskie widoczne w UI | `templates/admin_*.html`, `static/js/admin_panel.js`, `admin_radio.js`, `run.py`; treści zgłoszeń graczy bez tłumaczenia |
| C08 `history` | Migracja starych systemowych tekstów, kompatybilność klienta, rollout i raport kompletności | Store'y zidentyfikowane w 153; dry-run, batche, wznowienie, rollback i brak ponownej emisji |

### Ghost Signal Show / Sender — obowiązkowe rozwinięcie B14/C03/C06/C08

- Nadawanie: komunikaty walidacji i recovery z `ghostnetwork/transmission.py`,
  stan transmisji, potwierdzenie wysłania oraz powiadomienia odbiorców.
- Pokaz: `ghostnetwork/show.py`, `ghostnetwork/show_manifest.py`,
  `static/js/ghost_signal_show.js`, katalog GN i używane zasoby audio/wideo.
  Inwentaryzacja obejmuje nazwy faz i scen, plansze, podpisy maszyn/części,
  odliczanie, statystyki, ranking, nagrody, błędy, przyciski i dostępność.
  Sprawdzić także tekst zaszyty w obrazach i filmie oraz mowę w nagraniach.
- Systemowa prezentacja ma PL/EN; nicki, nazwy klanów i inne dane autorskie
  pozostają oryginalne. Dla narracji GhostSignal trzeba przed generowaniem
  zatwierdzić politykę języka medium, prompt, audio i napisów. Wyjątek BN
  nie rozstrzyga tej polityki. Brak tego kontraktu blokuje odbiór 155.
- Zmiana locale nie restartuje pokazu ani jego zegara, nie wysyła sygnału,
  nie nalicza ponownie nagród i nie zmienia rozliczenia terenu. Zachować
  `signal_id`, `cycle_id`, checksum i deduplikację; lokalizować prezentację.
- Odbiór: PL/EN na dwóch kontach, live → utrata połączenia → wznowienie →
  zakończenie → archiwum/replay; zmiana języka w trakcie, brak audio,
  niekompletny manifest, stare snapshoty i fallback. Replay nie wykonuje
  efektów gry. Rozszerzyć istniejące testy `ghost_signal_show_*`,
  `test_ghostnetwork_signal_show*` i `tests/js/test_signal_registry.js`.

Pulpit ze zrzutu jest pokryty: Terminal A08, Browser B04/B05/B06,
Cyberner B06/C02, Pliki A09/C04, Mapa B01/B02, Profil A06, Wallet HC A07,
Ustawienia A05, Ghost Hack Radio B13/C06, Signal Registry B03/B14,
Dev Bug Reporter B15. Nazwy w launcherze należą dodatkowo do A03.

Zamrożone 149–152 nie są częścią realizacji B/C. Tłumaczymy istniejące zapowiedzi
i status niedostępności, ale nie tworzymy Research Tree, Community, importu,
AI Assistant ani pozostałych odłożonych funkcji.

## Przykłady rozdzielenia pól

Radio ma niezależny wybór PL/EN/ANY. PL i EN obejmują odpowiedni język oraz
kanały neutralne; ANY pokazuje wszystkie kanały, również mieszane. Język
bieżącej audycji jest jawny, a ANY nigdy nie jest językiem generowania Ollamy.
Szczegóły: sekcja radia w 154.

Zakres C03/C06 obejmuje też warianty poleceń narracji: zatwierdzony prompt PL/EN,
jeden `output_locale` na zadanie (BN: publikacja; News: wariant dla locale odbiorcy),
niesprzeczne instrukcje, zgodność z faktami i CTA,
walidację, cache zadania i fallback w przypisanym języku. Źródła startowe:
`ghostnetwork/ollama_policy.py`, `ghostnetwork/ollama_worker.py`,
`ghostnetwork/ollama_client.py`, `scripts/ollama_narrative_worker.py` oraz używane
szablony w `ghostnetwork/llm/prompts/`. Szczegóły: kontrakt 155.2a.

| Przypadek | PL | EN | Co pozostaje niezmienne |
| --- | --- | --- | --- |
| Akcja mapy | Przejmij system pokładowy | Take over vehicle systems | `car_hack`, cel, efekt |
| Kategoria | Bilety | Tickets | ID kategorii i oferty |
| Systemowy tytuł oferty podróży | Bilet: Berlin | Ticket: Berlin | Berlin, cena, kierunek i ID |
| Narzędzie gracza | GX · Zainstalowano | GX · Installed | GX i opis wpisany przez autora |
| Plik autora | Otwórz · moje-notatki.ptk | Open · moje-notatki.ptk | Nazwa, ID i treść pliku |
| Powiadomienie | GRZEGORZ wszedł na kontrolowany przez Ciebie obszar. | GRZEGORZ entered your controlled area. | Nick, event ID i fakt wejścia |
| Licznik plików | 1 plik / 2 pliki / 5 plików | 1 file / 2 files / 5 files | Wartość licznika |

To przykłady kontraktu i terminologii, nie finalny zatwierdzony słownik.
Glosariusz musi rozróżniać np. systemową akcję „Przejmij” od marki/tytułu produktu.

## Co dokładnie rejestrujemy podczas 153

Dla każdego systemowego tekstu lub rodziny szablonów utworzyć rekord:

`ID zakresu → plik/symbol lub producent/store → pole → pochodzenie → klucz →
parametry i ich typy → pluralizacja → odbiorca → renderowanie → trwałość →
sprint → stan PL → stan EN → test/dowód odbioru`.

Pochodzenie ma wartości `system`, `user`, `proper_name`, `technical`, `unknown`.
Pole `unknown` pozostaje oryginalne; nie wysyłać go do automatycznego tłumacza.
Stan tłumaczenia: `do ekstrakcji`, `klucz gotowy`, `PL gotowe`, `EN do review`,
`PL/EN zatwierdzone`, `odbiór zaliczony`. Osobno oznaczyć `nieaktywne` lub
`zamrożone` z uzasadnieniem. Plik o nazwie `*_old` wymaga potwierdzenia braku
użycia, a nie automatycznego usunięcia z audytu.

Każda powierzchnia obejmuje: etykiety, opisy, placeholdery, tooltipy,
aria-label/live, walidację klienta i serwera, ładowanie, pusty wynik, odmowę,
timeout, sukces, anulowanie, ponowienie i pomoc. Nie każdy stan występuje wszędzie;
brak zastosowania zapisać jawnie.

## Gotowość do rozpoczęcia implementacji 153

- A01–A11 mają właściciela modułu, źródła i listę aktywnych ścieżek; B/C mają
  potwierdzony sprint i sposób obsługi tekstu trwałego lub autorskiego.
- Uzgodniony glosariusz, format kluczy i wiadomości, wersjonowanie i sposób
  przechowywania locale w lekkich ustawieniach. Bez parsera pełnego profilu.
- Lista wyjątków zawiera tylko nazwy własne, treści autorów, dane techniczne,
  potwierdzone nieaktywne pliki i zamrożone funkcje — nie brakujące tłumaczenia.
- Przygotowane fixture'y: własna nazwa/tekst wyglądający jak klucz i18n,
  produkt mieszany, stare konto PL, dwa konta PL/EN, brak paczki, długi tekst,
  cyrylica, pluralizacja oraz stara wiadomość systemowa.

## PASS zakresu 153

Wszystkie A01–A11 działają w PL/EN na desktopie i mobile. Przełączanie języka
nie gubi draftu, fokusu ani stanu okna/operacji, także przy klawiaturze ekranowej
i fullscreen gry. Ustawienie przetrwa ponowne logowanie. Parametry gameplayu,
komendy i treści autorskie pozostają identyczne. Testowy dodatkowy pakiet działa
bez dopisywania warunków językowych w aplikacjach.

PASS 153 nie oznacza kompletnego EN całej gry: B/C są jawnie przypisane do
154/155, a angielski pozostaje wersją testową do końcowego odbioru 155.
