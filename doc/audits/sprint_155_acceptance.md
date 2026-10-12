# Sprint 155 — dowody i bramki odbioru

Stan: 12 X 2026, lokalny pakiet 155.2.0, **bez wdrożenia i bez pełnego PASS**.
EN zachowuje status `test`. Sprinty 149–152 pozostają zamrożone.

| Obszar | Implementacja / dowód lokalny | Bramka końcowa |
| --- | --- | --- |
| Powiadomienia | Klucze/parametry instalacji, zakupów, PvP, terenu, nagród, Response Network, więzienia, firmware i restartu GN; dokładne źródło + szablon. Testy dedupe i consumed. | Inwentarz pozostałych dostępnych komunikatów i danych historycznych; brak deklaracji 100% na podstawie samych regexów. |
| Cyberner | Metadane systemowej korespondencji, delta i renderery, oryginalne UGC; testy limitów historii i kanałów. | Kwalifikacja starej korespondencji bez źródła i pełna pętla dwóch kont. |
| Narracja | Trwały kontrakt języka, 11 aktywnych wersji promptów EN, retry/fallback oraz metadane publikacji; BN bez par tłumaczeń. | Próbki każdej rodziny Mistral i Ollama oraz ocena semantyczna. |
| News | 12 bazowych slotów PL/EN, neutralne etykiety redakcyjne, wersjonowane warianty, opt-in worker z lease/retry/expiry. | Przegląd i uzupełnienie dostępnej historii; jawny brak wariantu nie stanowi pełnego EN. |
| Historia | Batch/dry-run/checkpoint/idempotencja/rollback wariantów oraz metadanych języka; migracja addytywna i backup WAL, hashe wszystkich pierwotnych pól. | Spójny backup produkcji i zatwierdzone importy na obecnej instancji. |
| Show/Sender | 49 scen PL/EN, ten sam manifest/zegar/wynik; video pozostaje w DOM przy zmianie języka. | Pełna transmisja/replay na kontach oraz fizycznych urządzeniach. |
| FM | Oryginały i osobne EN edycje about/tips-tricks; faktyczne otwarcie dokumentów w pulpicie. | Odbiór językowy pomocy. |
| Kolejne locale | Runbook, manifest/katalogi, deklaratywne prompty/fallbacki i News; testowy pakiet `zz`. | Zatwierdzenie przyszłego tłumaczenia, fontów i ewentualnego RTL. |
| Administracja / areszt | Katalogi PL/EN siedmiu zakładek, narzędzia modeli, radio, profesje, bug reporter (UGC bez zmian); cover, ograniczenia czatu, kaucja i consequence show. Odczyt języka odmowy nie uruchamia ponownie guardu zapisu. | Odbiór na kontach produkcyjnych; rzeczywiste dane i uprawnienia. |
| Cały produkt | Istniejące PASS 153/154 i regresja nowych ścieżek. | Pełna pętla gry, porównanie wydajności i fizyczny Android/iOS. |

## Weryfikacja przeglądarkowa

Playwright MCP, izolowane konta i bazy, pełny renderer pulpitu na fixture
`tools/sprint_153_browser_fixture.py`; część feedów zastąpiona kontrolowanymi
odpowiedziami. Rzeczywisty odczyt FM i MailStore. To nie jest test produkcji.

- FM: otwarte `chaos.en.ptk` i `blacknet.en.ptk`, oryginały nadal dostępne.
  Przełączenie UI na PL nie zmienia tekstu otwartego EN dokumentu.
- Cyberner: systemowe przywitanie EN/PL obok identycznej wiadomości gracza,
  której treść pozostaje oryginalna. Przełączenie nie powiela wiadomości
  i zachowuje input/draft. Nazwa z literalnym `<img>` nie tworzy elementu HTML.
- Powiadomienie FRIENDS/ZNAJOMI: etykieta zmienia się, preview gracza nie;
  ponowne zdarzenie nie tworzy drugiego toastu.
- Viewport 390×844: okna mieszczą się w szerokości, brak poziomego overflow.
  Konsola bez błędów. To nie emuluje klawiatury ekranowej iOS/Androida.
- Wcześniejszy fixture Show: ten sam element video i rodzic, rosnący currentTime
  po zmianie locale; 49 scen pokrytych również testami JS.
- Admin EN: lista/szukaj/pusty stan, bug reports oraz radio. Polskie nazwy,
  zgłoszenie i literalne `<img>` gracza pozostają tekstem. Statusy/kategorie EN,
  brak obrazka z wstrzykniętego HTML, brak overflow 390×844 i błędów konsoli.
- Areszt: cover, notice i otwarty dialog kaucji PL/EN; ten sam DOM/sanction ID,
  draft zachowany, bez POST opłacenia. Kwota zmienia format 500,000 → 500 000.
  Rzeczywisty renderer, kontrolowana odpowiedź bail-offer w lokalnym fixture.

## Regresja

Zestawy etapowe: 134, 78 i 54 testy Python PASS; częściowo nakładają się,
nie sumować. JS: katalogi/runtime, routing Cybernera, News, montage/audio/recovery
Show PASS. Końcowy szerszy przebieg: **320 testów PASS w 547,845 s**.
Dodatkowe 9 testów komunikatów/inwentarza PASS po naprawie zamykania połączenia
read-only na Windows. Liczby zestawów częściowo się pokrywają.
Testy modeli używają atrap; żaden test lokalny nie zużył produkcyjnych tokenów.

Po audycie 155.2.0: końcowy zestaw administracja/areszt/migracja/narracja/News/
Mistral **92 testy PASS (179,100 s)**. Osobno sześć testów migratora PASS,
w tym dodany test pełnego schematu; zestawy się pokrywają. Dziewięć zestawów JS
detention/consequence oraz admin lazy, News, Show montage PASS. Składnia Bash
instrukcji i `git diff --check` poprawne. Nie jest to test usług produkcyjnych.

Pakiety 155.2.0 mają po 3910 kluczy w 13 domenach; rozmiar surowych plików JSON:
PL 443439 B, EN 434912 B. To nie jest pomiar transferu po kompresji ani czasu
startu produkcyjnego pulpitu. Test projekcji Show obejmuje profil 35 MB bez
zwiększania liczby zapytań; News ma testy braku ciężkich odczytów profilu.

## Kryterium decyzji

Pakiet służy do odbioru przedwdrożeniowego, nie uprawnia do ogłoszenia pełnej
wersji EN. Znany systemowy tekst bez tłumaczenia jest brakiem zakresu, nie
automatycznym wyjątkiem legacy. Dalsze błędy z inwentarza należy naprawić przed
PASS 155. Nie zmieniać statusu EN w manifeście na podstawie samych testów.
Procedury operatorskie: [runbook 155](../runbooks/ghost_content_155.md).

Decyzja wdrożeniowa autora: bez drugiej instancji gry. Zatrzymanie istniejących
procesów CHAOS, backup SQLite API, dry-run, migracja z porównaniem wszystkich
pierwotnych pól, canary obu dostawców PL/EN bez publikacji, potem kontrolowane
wznowienie. Inne aplikacje na serwerze pozostają poza zakresem. Nie wykonano
żadnej komendy na serwerze ani rzeczywistej generacji w ramach lokalnego audytu.
