# Ghost i18n v1 — fundament 153.2

Stan: PASS lokalny 153, 6 X 2026. Nie jest wydaniem pełnego EN.
Katalogi obejmują zakres powłoki; odbiór w `doc/audits/sprint_153_acceptance.md`.

## Decyzja: jeden format danych, dwa czytniki

Źródłem jest `static/locales/manifest.json` oraz pliki
`static/locales/{locale}/{domain}.json`. Format `1`, wersja treści `153.4`.
Czytniki: `ghost_i18n.py` i `static/js/ghost_i18n.js`. Obecna wersja treści
to `153.4` (foundation/settings/entry/onboarding/shell, 496 kluczy). Nie wymagają nowych
zależności. Oba wykonują te same przypadki z `tests/fixtures/i18n_conformance.json`.

Rejestracja przekazuje zwalidowany locale do `add_new_user(desktop_settings=...)`:
zapis trafia do projekcji już przy utworzeniu konta, z zachowaniem pozostałych
ustawień szablonu. Nie zapisujemy języka późniejszą aktualizacją ciężkiego
profilu (kanoniczna projekcja ma przed nim pierwszeństwo). Endpointy zwracają
tekst dla podanego locale oraz stabilny `error_key`; klient renderuje ten klucz
w aktualnym języku, nawet jeśli został zmieniony w trakcie żądania.

Wybrano ograniczony format wiadomości tekstowych zamiast dwóch osobnych
implementacji ICU. Wiadomość ma semantyczny klucz, deklarację parametrów
`string`/`number` oraz `text` albo `plural` i `forms`. Wstawianie `{name}`
jest jednoprzebiegowe; zawartość parametru nie jest ponownie interpretowana.
Parametry brakujące, nadmiarowe i błędnie typowane są odrzucane. Liczby muszą
być skończone i mieścić się w zakresie bezpiecznym dla JS. Bool nie jest liczbą.

To nie pełny ICU: bez HTML, zagnieżdżonych selektorów ani odmiany rodzaju.
Nie używać tego formatu do treści wymagającej takich konstrukcji bez rozszerzenia
wersji kontraktu i wspólnego testu. Formatowanie prezentacyjne liczb/jednostek/dat zapewniają Intl i helpery
Python na wspólnych regułach manifestu. Przypadki PL/EN sprawdzają oba runtime’y.
UTC i strefa są jawne; locale nie zmienia strefy gracza ani kwoty do zapisu.
Interpolacja liczb w wiadomościach pozostaje kanoniczna; formaty są osobnym API.

Kardynalna liczba mnoga jest określona deklaratywnie w manifeście: uporządkowane
reguły kategorii, koniunkcja warunków, zakresy, negacja i modulo; operand `n`
(wartość bezwzględna), `i` (część całkowita), `integer` (0/1). Pierwsza zgodna
reguła wygrywa, inaczej `other`. PL: one/few/many/other; EN: one/other.
Operujemy na wartościach liczbowych: `1` i `1.0` są tą samą liczbą, nie zachowujemy
liczby zer w zapisie wejściowym. Testowy pakiet z wydłużonym tekstem i cyrylicą
potwierdza dodanie języka wyłącznie przez dane; nie jest tłumaczeniem RU.

`t(key, params, locale)` jest bezstanowe względem odbiorcy. Wariant trwały ma
`{key, params, content_version}`; niezgodna wersja jest odrzucana, nie tłumaczona
według przypadkowego nowego kontraktu. Migracje starych wiadomości należą do 155.
Pakiety niezgodne z manifestem są odrzucane. Fallback: locale → PL →
`common.unavailable`; brak klucza wysyła diagnostykę bez wartości parametrów.
Fallback używa reguł języka źródłowego, nie języka brakującego tłumaczenia.

Wynik jest zwykłym tekstem. Klient musi stosować `textContent` lub escaping
w rendererze, Jinja autoescape. Nigdy `innerHTML = t(...)`, `Markup(t(...))`
ani masowej podmiany polskich napisów w DOM. Nie przepuszczać UGC przez tłumacz.

## Locale i zapis konta

Zalogowany: locale konta, brak/nieobsługiwany zapis → `pl` także przy przeglądarce
EN. Przed logowaniem: obsługiwana preferencja urządzenia → przeglądarka → PL.
Tag regionalny sprowadzamy do języka bazowego (`en-GB` → `en`). `ANY` nie jest
locale, a RU/ES nie są jeszcze dopuszczone do zapisu.

`POST /api/profile/desktop` przyjmuje częściową zmianę `{"locale":"en"}`.
Istniejący writer projekcji zachowuje pozostałe ustawienia, kontrolę sesji
i atomowość; nie zmienia ciężkiego JSON profilu. Lekki bootstrap normalizuje
locale. Błąd ma stabilny `reason: invalid_locale`. Komunikaty walidacji mają wersjonowane klucze; odbiorca renderuje swój język.

Manifest określa status pakietu, nie gotowość całego produktu: PL `partial`,
EN `test`. Dopiero po pełnym odbiorze 155 wolno oznaczyć EN jako kompletne.
Przyszłe radio i Ollama mają oddzielne preferencje i polityki medium, opisane
w 154/155. Czytnik nie ustala języka publikacji BN ani GhostSignal.

## Loader i selektory — wykonany przyrost 153.3

`ghost_i18n_runtime.js` przyjmuje manifest i pełny polski fallback osadzony
przez Jinja. Cache jest lokalny dla instancji manifestu; URL domen zawiera
wersję treści. Zanim jakiekolwiek etykiety się zmienią, cały docelowy pakiet
przechodzi kontrolę wersji, kluczy, parametrów i wszystkich form pluralizacji.
Niekompletny pakiet nie jest zapisywany jako język konta. Żądania pobrania mają
timeout 10 sekund. Wyścigi wyborów są numerowane; zapis odbywa się sekwencyjnie.
Potwierdzony zapis staje się stanem widoku, także gdy późniejszy wybór zawiedzie.

Renderer dotyka tylko elementów oznaczonych w systemowych szablonach
`data-ghost-i18n` i placeholderów. Nie rekonstruuje okien ani pól formularzy.
Nie wolno oznaczać takim atrybutem kontenera z UGC lub elementami interaktywnymi.
`lang` i `dir` zmieniają się razem z pakietem. Etykiety ikon mają oddzielne
`labelKey`; dotychczasowy klucz pozycji ikony nie zmienia się na angielski.

`ghost_i18n_entry.js` przechowuje tylko preferencję sprzed logowania
(`ghost_entry_locale`). Nie ustawia nią języka zalogowanego konta. Ustawienia
używają istniejącej kolejki POST; brak potwierdzonego locale w odpowiedzi
jest błędem zapisu, nie sukcesem. Selektor EN oznaczony jest jako testowy.

Klient używa Intl, serwer `format_number`, `format_unit`, `format_date`.
Testy współdzielą oczekiwane formaty PL/EN; brak jawnej strefy w dacie Python
jest błędem. Wartości ekonomiczne pozostają kanoniczne.

## Ramki, rejestr języków i granice

Mostek `ghost_i18n_frame.js` obsługuje tylko ramki z
`data-ghost-locale-frame`. Weryfikuje origin, contentWindow/parent, nonce,
content_version i rewizję. Przesyła zwalidowany pakiet, nie restartuje operacji.
`ghost_i18n_bindings.js` oznacza wyłącznie systemowe liście tekstu i wartości
formatowane. MutationObserver obsługuje nowe liście, nie dopasowuje tekstów UGC.

Manifest zawiera `approved_for` dla interface/radio/narration;
`approved_locales` i `radio_locale_filters` udostępniają ten sam rejestr.
ANY jest filtrem, nie output_locale. Zastosowanie w radio/publisherach: 154/155.
Nieznane treści pozostają oryginalne. Stare komunikaty/historyczne notatki
bez klucza nie są tłumaczone heurystycznie. EN pozostaje testowe do odbioru 155.
