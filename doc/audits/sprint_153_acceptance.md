# Sprint 153 — odbiór lokalny, 6 X 2026

**PASS lokalny zakresu 153.** Pakiet `153.4`, 496 kluczy PL/EN w pięciu
domenach. Nie jest to wdrożenie ani autorski PASS produkcyjny. EN pozostaje
testowe; aplikacje i treści systemowe domykają 154/155. 149–152 zamrożone.

## Implementacja

- Wspólny manifest i katalogi JS/Python, typowane parametry, pluralizacja,
  fallback, wersjonowanie, atomowy loader, cache i kolejka zapisów.
- Lekki bootstrap i kanoniczny zapis locale konta. Stare konta: PL.
  Oddzielna preferencja przed logowaniem; locale zachowane przy recovery.
- Logowanie, onboarding, pulpit/menu/belka, kontrolki okien, ustawienia,
  profil, portfel, terminal i powłoka FM korzystają z kluczy systemowych.
- Formatowanie liczb/dat/jednostek nie zmienia kwot, UTC ani strefy gracza.
- Jawny mostek iframe: origin, źródło, rejestracja ramki, nonce, wersja
  pakietu i monotoniczna rewizja. Zmiana tekstów bez przeładowania.
- Rejestr zatwierdzonych języków UI/radio/narracji. `ANY` tylko jako filtr
  radia. Nie uruchamia to jeszcze publisherów ani funkcji z 154/155.
- Usunięto historyczne poprawianie polskich tekstów w DOM FM, które mogło
  zmieniać treści autora. Aktualizowane są wyłącznie oznaczone etykiety.

## Testy automatyczne

105 testów Python: **OK**. Polecenie wykonywane z repozytorium, dane testowe
oraz sesje w katalogach tymczasowych:

```powershell
python tools/run_isolated_tests.py tests.test_ghost_i18n tests.test_registration_locale tests.test_desktop_settings_writer tests.test_file_manager_inventory tests.test_session_generation_isolation tests.test_terminal_geolocation_command tests.test_shell_locale tests.test_wallet_runtime_cutover tests.test_wallet_canonical_boundary
```

Po końcowym uzupełnieniu odpowiedzi `userdel` i składni poleceń ponownie
uruchomiono 56 testów katalogów/powłoki/sesji/geolokalizacji: **OK**.

Sześć zestawów JS: **PASS**, dodatkowo kontrola składni `terminal.js`:

```powershell
node tests/js/test_ghost_i18n.js
node tests/js/test_ghost_i18n_runtime.js
node tests/js/test_locale_frame.js
node tests/js/test_registration_locale.js
node tests/js/test_terminal_pkg.js
node tests/js/test_wallet_transfer_idempotency.js
node --check static/js/terminal.js
```

Obejmują kontrakt katalogów, braki/typy parametrów, fallback, pluralizację,
odrzucenie starej wersji, formaty, race, awarię pobrania/zapisu i retry,
niezależność kont, rejestrację, recovery, brak ciężkiego odczytu profilu,
niezmienność akcji terminala i idempotencję portfela. Zaktualizowano stare
mocki writera i ścieżki testów sesji; wcześniejsze 65/69 nie jest stanem końcowym.

## Playwright MCP

Rzeczywiste szablony i skrypty pulpitu, localhost, tymczasowe konta/baza:
`python tools/sprint_153_browser_fixture.py` → `http://127.0.0.1:8993/`.
Fixture zastępuje zewnętrzne feedy świata; nie jest serwerem produkcyjnym.
Rejestrację/logowanie zweryfikowano też wcześniejszym izolowanym fixture
`tools/locale_browser_fixture.py` oraz testami zapisu na prawdziwym store.

| Scenariusz | Wynik |
| --- | --- |
| Otwarte terminal, ustawienia, profil, portfel i FM; PL → EN → PL | Te same węzły pól; e-mail, notatka i komenda zachowane |
| Pomoc terminala, `echo <img…>` | Pomoc zmienia język; echo pozostaje tekstem, bez elementu HTML |
| Nick `Własny nick <keep>` | Niezmienny, bez interpretacji HTML |
| FM foldery/metadane i `/about/chaos.ptk` | Etykiety PL/EN; HTML dokumentu identyczny po zmianie locale |
| Jawnie zarejestrowany iframe z rzeczywistym mostkiem | PL/EN bez reloadu; draft i licznik operacji `7` zachowane |
| Zapis EN i odświeżenie pulpitu | Bootstrap ponownie wybiera EN |
| Desktop 1440×900, powiększony terminal | Okno kończy się na 854 px, dokładnie nad belką; input do 844 px |
| Mobile 390×844, zwykły i powiększony terminal | Input do 788 px, belka od 798 px |
| Obszar widoczny 390×480 | Input do 424 px, belka od 434 px; draft zachowany |
| Rzeczywiste `requestFullscreen()` gry + zmiana języka | Input nadal 424 px, belka 434 px |
| Pakiet testowy `zz`, długie napisy i cyrylica | 94 widoczne powiązania; szerokość dokumentu 390 px; draft bez zmian |

Przeglądarka i serwer testowy zamknięte po odbiorze. Czysty przebieg powłoki
bez błędów JS lokalizacji. Atrapa radia zgłaszała ostrzeżenie o pustym schemacie
kanału; radio należy do 154. Po restartach fixture stare karty dostawały
oczekiwany konflikt generacji; właściwy przebieg wykonano na świeżym pulpicie.

Ograniczenia: zmniejszenie viewportu testuje geometrię przy klawiaturze,
nie fizyczną klawiaturę Android/iOS. Mostek ramki sprawdzono na izolowanej
ramce, nie na pełnym świecie OSM. Nie testowano produkcyjnego Ollamy ani
zewnętrznych feedów; nie należą do 153.

## Dalsze sprinty

154: wnętrza aplikacji (w tym GhostSignal Show/Sender/Registry), Pro Tools,
kreatory, katalogi, radio PL/EN/ANY. 155: trwałe komunikaty i narracja,
zatwierdzone polecenia Ollamy, pojedynczy język publikacji BN, GPNews według
locale odbiorcy, osobne wydania FM `/about` i `/tips-tricks`, odbiór pełnego EN.
UGC nigdy nie podlega automatycznemu tłumaczeniu.
