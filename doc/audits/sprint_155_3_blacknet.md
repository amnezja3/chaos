# 155.3 — inwentarz i dowody lokalne

14 X 2026, pakiet `155.3.0`. Implementacja lokalna, bez wdrożenia i bez pełnego
PASS 155. Rozgrywka nie jest wstrzymywana. Odbiór publikacji na produkcji jest
oddzielny od testów poniżej.

## Producenci i zakres tekstu

Wszystkie poniższe reguły są w `run.py::BLACKNET_SIGNAL_RULES` i przechodzą przez
`blacknet_signal_from_fact`. Klucze `apps.blacknet.rule.<fact_type>.*` mają PL/EN.
Tytuł jest jedną publikacją w przypisanym języku. Channel/label/stat są systemową
projekcją UI, z zachowaniem nieprzetłumaczonych nazw własnych w parametrach.

| fact_type | signal_type | Producent / źródło | Język |
| --- | --- | --- | --- |
| operations_active_count | operation_activity | Operacje | Neutralna pula |
| operations_top_type | regional_activity | Operacje | Neutralna pula |
| operation_hotspot_activity | operation_hotspot_activity | Operacje / konkretny cel | Neutralna pula; nazwa celu oryginalna |
| operation_hotspot_teleport | teleport_hotspot | Operacje / konkretny cel | Jak wyżej, niezmieniony cel CTA |
| target_operation_burst | target_operation_burst | Operacje | Neutralna pula |
| conflict_target_alert | conflict_target_alert | Konflikty | Neutralna pula |
| contested_area_alert | contested_area_alert | Konflikty | Neutralna pula |
| market_sales_7d | market_watch | Ghost Exchange | Neutralna pula |
| market_top_sector_7d | data_demand | Ghost Exchange | Neutralna pula |
| googleplex_catalog_size | product_opportunity | Katalog systemowy | Neutralna pula |
| googleplex_product_signal | product_opportunity | Wersja produktu GGPL | Deklaracja autora; built-in bez autora jest neutralny |
| radio_channels_available | radio_promotion | Kanał i konkretna audycja | Resolver `radio_locale` + kontrakt źródła |
| system_messages_24h | system_incident | Agregat wiadomości systemowych | Neutralna pula; bez treści prywatnych |
| incident_hotspot_reaction | incident_hotspot | Response Network | Neutralna pula; fakty i CTA bez zmian |

Pozostałe źródła:

- GN: istniejący `freeze_language`, trwałe `validation.language_contract`, te same
  fakty i identyfikatory. Nowe zadania BN mogą korzystać z systemowego prefiksu.
- LLM BN/world digest: `ghostnetwork/producers.py`, `ollama_policy.py`, repozytorium
  i publisher. Sygnał heurystyczny przekazuje wybrane locale do pojedynczego zadania.
  Digest agregatu pozostaje neutralny. Wynik narracyjny nie dostaje tłumaczenia UI
  w miejsce oryginalnego body. Warianty News są osobną ścieżką 155.
- GGPL LLM ingress dopuszcza obecnie medium Cyberner. Nie rozszerzamy uprawnień
  do publicznego BN; promocja narzędzia przechodzi przez fakt katalogu produktu.
- `static/blacknet_signals.json`: 6 demonstracyjnych kart, tekst źródłowy PL,
  klucze otoczenia PL/EN. Statyczny fallback nadal pod istniejącym przełącznikiem;
  nie włączano demonstracyjnych danych w produkcji.
- Pusty feed i awaria ładowania: `out_of_signal`, etykiety PL/EN w rendererze.
- Renderer wszystkich sześciu layoutów: `static/js/terminal.js`; statystyki mają
  pluralizację. Tytuł, body i nazwy nie są obcinane w zapisywanej projekcji BN.
  Karty używają tekstu HTML i CSS, bez tekstowych bitmap wymagających przekładu.

## Kreatory i kompatybilność

TermCreator, WindowMaker, ButtonMaker, AppForge: formularz nowego projektu i edycja
przekazują `signal_language`, serwer sprawdza rejestr. Starszy payload bez pola
nie kasuje istniejącej deklaracji. Stare nieoznaczone produkty nie uzyskują ANY
automatycznie i nie kwalifikują się do nowej emisji jako znane źródło.
Pole w niemodyfikowalnym wydaniu przechodzi do instalacji. Zmiana deklaracji wymaga
nowego wydania; nie zmienia samej mechaniki ani dawnych instalacji.

Legacy formularze generatorów mają to samo pole. GhostLab zapisuje je w marce,
następnie w `branding_snapshot` kompilacji i produkcie. Stary artefakt bez pola
pozostaje nieoznaczony. Przełączenie UI nie tłumaczy opisów autora.
V2 kreatorów nie ma osobnych API importu/klonowania/rollbacku wydania, więc nie
dodawano fikcyjnych ścieżek. Adoptowany projekt legacy zachowuje oryginał i przy
nowej publikacji przenosi jawnie wybraną deklarację. Jawna aktualizacja instalacji
korzysta z nowego snapshotu wydania, tak samo jak pozostałe metadane.

## Trwałość i migracja

`signal_language.py`: radio przed deklaracją produktu, jawne unknown odróżnione
od ANY, whitelist zatwierdzonej i aktywnej puli, deterministyczny wybór neutralnych
sygnałów. `blacknet_signal_languages` przypina locale dla sygnału i tożsamości
źródła (audycja / wydanie produktu). Unikalność i transakcja chronią przed wyścigiem.
To wewnętrzny klucz; locale nie jest dodawane do publicznego klucza dedupe.

`blacknet_language_migrate.py`: inventory, dry-run, addytywna tabela, check,
rollback pustej tabeli. Raportuje brakujące deklaracje, nie zgaduje języka treści.
Zajętej tabeli nie usuwa. Istniejące 9 audycji PL już ma potwierdzone metadane.
Nie ma historycznego republish ani masowej aktualizacji zainstalowanych produktów.
[Instrukcja operatora](../runbooks/blacknet_155_3.md).

## Dowody

- 93 testy: producenci, narracja, polityka walidacji, Mistral/router — PASS.
- 53 testy: kontrakt BN, rzeczywisty producent faktów/sygnałów, publikacja
  GhostLaba i stara ścieżka — PASS.
- 36 testów końcowych: kontrakt BN, kreatory, katalogi/pluralizacja, radio — PASS.
  Zestawy częściowo się pokrywają; nie sumować jako unikalnych testów.
- HTTP PL/EN/ANY: utworzenie → publikacja → zakup/instalacja → ponowienie → nowe
  wydanie z innym językiem. Starsza instalacja zachowuje język, opis autora
  identyczny. Fakt radia → realny producent zadania → dedupe zachowuje locale.
- Równoległe przypisania jednego sygnału, zmiana puli po przypisaniu, różne audycje
  w tym samym slocie, sprzeczne metadane i niezatwierdzone locale — PASS.
- Nowy prefiks jest dekoracją systemową; fałszywe fact_refs nadal trafiają do
  kwarantanny. Dawne zadania bez nowej wersji prezentacji działają jak wcześniej.
- Fallback: kontrolowane 403 Mistrala → Ollama odrzuca / timeout / zły JSON →
  zatwierdzony szablon PL/EN → jedna publikacja; replay `duplicate:true`.
  To sześć przypadków w jednym teście, bez zewnętrznych wywołań modeli.
  Powtórzono dla nowej wersji dekoracji BN: dwa testy / 12 przypadków PASS,
  w tym rzeczywiste odrzucenie niezatwierdzonego tonu (nie tylko brak prefiksu).
- Playwright: cztery kreatory zachowują ANY i UGC przy PL/EN, zapis/publikacja;
  GhostLab zapisuje EN niezależnie od UI, zachowuje szkic i ID artefaktów;
  BN tłumaczy etykiety radia, zachowuje polski tytuł i ID, desktop/mobile PASS.
  Końcowe przebiegi bez błędów JS; w teście błędów kreatora HTTP 409/400 są celowe.
  Pierwsza nawigacja fixture GhostLaba została przerwana, powtórny przebieg PASS.

Pełna emisja na produkcji, jakość nowych publikacji, historia, warianty News oraz
Show/Sender nie są zaliczone tym raportem. Użytkownik odbiera je w normalnej grze,
a Show/Sender po naturalnym zebraniu części; nie przyspieszamy cyklu testami.
