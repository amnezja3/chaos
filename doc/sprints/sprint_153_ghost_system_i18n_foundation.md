# Sprint 153 — Ghost System: fundament języków i pulpit PL/EN

Status: **ZAPLANOWANY**, 6 X 2026. Pierwszy z trzech sprintów lokalizacji,
niezależny od zamrożonych decyzją autora sprintów 149–152; dalej
[154](sprint_154_ghost_system_apps_catalogs.md) i
[155](sprint_155_ghost_system_content_acceptance.md).
To plan prac, nie deklaracja istniejącej wersji angielskiej.

[Przegląd gotowości 6 X 2026](../audits/sprint_153_readiness_2026_10_06.md):
gotowi do rozpoczęcia 153.1–153.2; ekstrakcja kluczy i wybór wspólnego formatu
poprzedzają masową migrację UI.

## Cel

Wprowadzić wspólną infrastrukturę języków dla JS, HTML/Jinja i backendu Python,
zlokalizować podstawową powłokę Ghost Systemu i ustalić kompletny rejestr treści.
Docelowy produkt ma pełne wersje PL i EN. Kolejne języki, np. rosyjski i hiszpański,
mają wymagać pakietu tłumaczeń i rejestracji, bez kopii aplikacji lub mechaniki gry.

## 153.1 — inwentaryzacja i granica autorstwa

Przygotowano [mapę zakresu i rejestr startowy](../audits/ghost_system_i18n_inventory.md):
A01–A11 do wdrożenia w 153, B01–B15 do 154 oraz C01–C08 do 155.
To mapa obszarów, nie zakończona ekstrakcja wszystkich tekstów. W 153 rozwinąć
rejestr do poziomu kluczy: moduł, źródłowy plik/store,
rodzaj treści, właściciel tekstu, sposób renderowania, klucze, sprint migracji,
stan PL/EN i scenariusz odbioru. Uwzględnić ścieżki ukryte: pusty stan, walidację,
brak uprawnień, timeout, offline, recovery, pomoc, tooltip i aria-label.
Rejestr obejmuje aktualnie wdrożone funkcje. Nie implementować zamrożonych
sprintów 149–152 w ramach lokalizacji. Po ich ewentualnym wznowieniu nowe
funkcje muszą korzystać z kontraktu i18n i uzupełniać rejestr.

| Treść | Zasada |
| --- | --- |
| UI, opisy mechaniki, systemowe nazwy kategorii, produktów i wyników | Klucze tłumaczeń systemowych |
| Szablonowe komunikaty systemowe | Lokalizowane PL/EN dla odbiorcy |
| Narracja LLM, np. sygnały BlackNet | Jedna publikacja w jednym zatwierdzonym języku; kolejne mogą mieć inny, bez kopii PL/EN |
| Googleplex News | Treść zgodna z językiem ustawionym przez odbiorcę; warianty jednej publikacji, bez duplikatów feedu |
| FM `/about` i `/tip&trick` (klucz `tips-tricks`) | Zachować obecne foldery i materiały; dodawać osobne wersje dokumentów w zatwierdzonych językach |
| Nazwa, opis, dokument, wiadomość lub przycisk napisany przez gracza | Zachować dokładny tekst autora; bez automatycznego tłumaczenia |
| Systemowy opis efektu wewnątrz narzędzia gracza | Tłumaczyć opis; zachować branding i własne teksty gracza |
| Nick, marka auta, nazwa miejscowości, nazwa własna POI/OSM, nazwa pliku użytkownika | Zachować nazwę; tłumaczyć jedynie systemową etykietę i kategorię |
| Kod, komenda, identyfikator produktu/akcji/zasobu, receipt, ścieżka API | Stabilna tożsamość techniczna niezależna od języka |

Pochodzenie musi być jawne na poziomie pola/kontraktu. Nie klasyfikować po tym,
czy tekst wygląda na polski, jest w Googleplexie, został kupiony lub pochodzi
z konta o nazwie `admin`. Materiał AI przygotowany na zlecenie gracza i zapisany
jako jego produkt/dokument też jest treścią autorską. Dla nieznanego pochodzenia
domyślnie zachować oryginał do czasu audytu.

## 153.2 — kontrakt i katalogi

- Stabilne klucze semantyczne, np. `map.action.car_hack.label`, podzielone na
  domeny: shell, map, operations, catalog, ghostlab, creators, communications,
  territory, consequences, account, admin. Żadnej zamiany tekstów w gotowym DOM.
- Jeden format źródłowy katalogów, np. `locales/{locale}/{domain}.json`, oraz
  manifest języka: tag, nazwa własna, kierunek pisma, wersja, stan kompletności.
  Z katalogów powstają paczki klienta i odczyt serwerowy. Nie prowadzić osobnych,
  rozchodzących się ręcznie słowników JS i Python.
- Wspólna semantyka `t(key, params)` i komunikatu `{key, params, content_version}`.
  Parametry nazwane i typowane; całe zdania w katalogu, bez sklejania odmian.
  Liczba mnoga musi obsługiwać PL i EN oraz kategorie wymagane przez przyszłe
  języki. Formatowanie dat/liczb/jednostek jest prezentacją; UTC i wartości
  kanoniczne nie zmieniają się. Język nie zmienia strefy czasowej gracza.
- W 153 wybrać i przypiąć implementację formatu wiadomości dla obu runtime'ów;
  wspólne testy zgodności liczby mnogiej i interpolacji są warunkiem wyboru.
  Interpolować bezpieczny tekst, nie wykonywać HTML z parametrów. Dopuszczone
  formatowanie bogate musi mieć jawny kontrakt i sanitizację.
- Rozwiązanie locale: język konta → preferencja urządzenia przed logowaniem
  → obsługiwany język przeglądarki → `pl`. Po zalogowaniu preferencja konta
  ma pierwszeństwo. Stare konta bez ustawienia zachowują `pl`.
  Nieobsługiwany wariant regionalny sprowadzić do obsługiwanego języka bazowego.
- Awaryjny fallback klucza: wybrany język → PL → kontrolowany komunikat ogólny
  i diagnostyka brakującego klucza. Fallback nie oznacza kompletności EN;
  brakujące obowiązkowe tłumaczenia blokują wydanie w 155.
- Ustawienie języka zapisać małą, kanoniczną mutacją ustawień konta i udostępnić
  w lekkim bootstrapie/projekcji. Nie czytać całego profilu dla tłumaczenia.
  Obowiązuje [kontrakt hot path](../architecture/profile_hot_path_contract_130_11_plus.md).
- Wersjonowanie paczek, cache po języku i wersji, walidacja manifestu, kontrola
  wyścigu szybkiego przełączania PL → EN → PL. Niedostępna paczka pozostawia
  ostatni kompletny język i czytelny komunikat; bez połowy przełączonego pulpitu.

## 153.3 — ustawienia i podstawowa powłoka

W 153 zdefiniować także wspólny rejestr zatwierdzonych języków dla interfejsu,
radia i narracji Ollamy. Język UI, filtr kanałów radia i język konkretnej
publikacji to oddzielne pola. `ANY` jest wyborem radia, nie językiem tłumaczenia
ani wartością `output_locale` dla modelu. Szczegóły: 154 (radio) i 155.2a (Ollama).

Selektor Polski / English w ustawieniach gry i na wejściu przed logowaniem.
Zmiana odświeża otwarte interfejsy i iframe'y bez restartowania operacji,
zamknięcia okien, wylogowania lub utraty wpisanego tekstu. Przekazywanie języka
do iframe ma jawny, kontrolowany kontrakt. Ustawić `lang` i kierunek dokumentu.

Przenieść do katalogów logowanie, rejestrację, onboarding, sesję/wygaszenie,
podstawową pomoc, pulpit, menu start, belkę, menu kontekstowe, kontrolki okien,
ustawienia, profil, portfel oraz systemowe elementy terminala i File Managera.
Nie zmieniać nazw komend ani rzeczywistych ścieżek katalogów; tłumaczyć ich
etykiety prezentacyjne. Nie utracić poprawki mobilnej klawiatury z 6 X.

Wyjątek FM: `/about` i `/tip&trick` pozostają w obecnej postaci. Ich dokumenty
nie są automatycznie podmieniane po zmianie języka UI. W 155 dołączamy osobne,
oznaczone językiem wydania obok oryginałów; bez usuwania i nadpisywania materiałów.

## Artefakty i odbiór

- Katalogi PL/EN dla całego zakresu 153, rejestr źródeł, glosariusz terminów
  gameplayowych i lista nazw własnych pozostających bez tłumaczenia.
- Testy wspólnego formatu, fallbacku, braków i nadmiarowych parametrów,
  pluralizacji, escapingu, cache i ustawienia po ponownym logowaniu.
- Playwright: oba języki, desktop/mobile, zwykłe i powiększone okno, fullscreen
  gry, przełączanie przy otwartym terminalu i niezapisanym formularzu.
- Równoczesne sesje PL/EN nie zmieniają sobie języka; payloady mutacji,
  klucze idempotencji i reguły balansu są identyczne.
- Pakiet testowy języka z wydłużonym tekstem i cyrylicą sprawdza mechanizm
  dodania locale bez zmian logiki aplikacji. Nie jest wydaniem RU/ES.

**PASS 153:** działający fundament i pełny zakres powłoki, bez utraty stanu.
EN pozostaje oznaczone jako wersja testowa do pełnego odbioru 155.
