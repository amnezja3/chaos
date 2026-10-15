# Sprint 156.7 — lift ekranu startowego i instalacji CHAOS

15 X 2026. Implementacja lokalna; bez wdrożenia. Rozszerzenie 156 na polecenie
autora po odbiorze Windows/Android. Linux i iOS nadal wymagają odbioru na sprzęcie.

## Zakres

- Ekran wejścia inspirowany dostarczoną wizualizacją: scena planety i operatora,
  zielony logotyp z efektem glitch, karty świata/narzędzi/frakcji, panel logowania.
- Desktop: dwa panele. Mobile: krótki hero nad formularzem. Przewijanie całej
  strony, bez ucięcia instalacji i bez poziomego overflow.
- PL/EN, prawdziwy odnośnik rejestracji, podgląd hasła, autocomplete, focus,
  komunikaty błędów i istniejący kontrakt POST oraz trwałych sesji.
- Instalacja opcjonalna, zwinięte instrukcje platform; rzeczywisty przycisk
  instalacji tylko po zdarzeniu przeglądarki. Brak fałszywego statusu instalacji.
- Social login pozostaje w 157. Na dodatkowe polecenie autora przygotowano
  przyciski Google/GitHub/Discord/Steam jak w referencji: ikony SVG, Google biały,
  GitHub grafitowy, Discord niebieski, Steam granatowy oraz separator „lub / or”.
  Przyciski są wyłączone i opisane jako wkrótce dostępne. Bez endpointów OAuth,
  atrap resetu hasła i fikcyjnych statystyk świata z referencji.

## Assety i implementacja

- `static/images/entry/chaos-world-156-7.png`: 1024 × 1536, wygenerowany przez
  wbudowane imagegen; scena bez tekstu, elementów formularza i makiety telefonu.
- `static/css/entry_gate.css`: układ, logo glitch, responsywność; ikony kart
  są wektorami SVG w szablonie, teksty pozostają dostępne i tłumaczalne.
- `static/js/entry_gate.js`: podgląd hasła i grupowanie instrukcji instalacji.
- `templates/login.html`: odseparowanie od CSS pulpitu gry. Katalogi PL/EN
  i manifest mają wspólną wersję 156.7.0.

Prompt końcowy imagegen:

> Use case: stylized-concept. Asset type: production background artwork for CHAOS cyberpunk game login website, NOT a UI mockup. Generate a portrait 2:3 cinematic high-detail matte painting. Composition inspired by a dark hacker command center: a solitary hooded operator seen from behind, centered in lower half at a bank of monitors; above him a huge curved Earth at night fills middle and upper half, Europe and nearby continents illuminated with emerald city lights and fine luminous green network connections, a thin icy cyan atmospheric rim. Uppermost 20 percent almost black with subtle teal haze, useful negative space for live HTML logo. Bottom 15 percent dark so text can overlay. Palette black, very dark petroleum teal, emerald neon and restrained icy blue; high contrast but mostly dark, tactile jacket, believable monitor light, sophisticated dystopian thriller visual. Hooded figure has a small abstract emerald angular insect-like emblem on back, no readable words. No text, no letters, no UI controls, no typography, no phone mockup, no borders, no watermark. This is one seamless illustration to use behind real HTML on desktop and crop to the planet area on mobile. Save generated image as project asset.

## Dowody i wdrożenie

### Spójny onboarding i przygotowanie 157

Wszystkie sześć aktywnych kroków `/register` ma wspólny styl bramy: nagłówek
CHAOS, logowanie/rejestracja, przełącznik PL/EN, wskaźnik etapu, fabularna
ilustracja i panel formularza. Kroki: login, frakcja, rola, hasło, e-mail,
nick/podsumowanie. Zachowano istniejące ilustracje fabularne, ID frakcji/ról,
muzykę, walidację i payload backendu. `register_old.html` nie jest aktywną trasą.

CSS przeniesiono z dużego bloku inline do `static/css/onboarding_gate.css`.
Desktop: fabuła obok formularza; mobile: pionowy układ bez ukrywania opisów kart
i blokowania przewijania. Wybór frakcji/roli zawiera podgląd i wyraźne zaznaczenie.
Wpisane dane pozostają po cofnięciu i zmianie języka. Na mobile i przy reduced
motion fabuła wyświetla się od razu, żeby animacja tekstu nie przesuwała pól.

Pierwszy krok używa wspólnego fragmentu przycisków Google/GitHub/Discord/Steam,
z komunikatem dotyczącym **rejestracji**, nadal disabled. Kolejne kroki nie
pokazują tych przycisków. Przyszła zewnętrzna tożsamość nie omija frakcji ani roli:
intencja rejestracji, aktywacja e-maila, połączenia kont i adaptery pozostają w 157.
Nie dodano atrap weryfikacji ani działającego SSO. Katalogi 156.7.3.

Publiczny `/launch` ma pasującą paletę, panel i przyciski; nie dodano ciężkiej
grafiki do cichego bootstrapu ani dodatkowego ekranu wymagającego kliknięcia.

Weryfikacja: 19 testów backendu rejestracji/launch PASS; test JS wszystkich
frakcji/ról/kroków PL/EN PASS. `tools/onboarding_gate_browser_smoke.py` przechodzi
sześć kroków w PL i EN w realnym Chrome na izolowanej bazie, sprawdza szerokości
320/390/768/1280/1920, wymagane pola, niezgodne hasła, wybory i powrót, zmianę
języka bez utraty danych, podsumowanie i ponowienie po błędzie zapisu.
Finalizacja w tym teście UI jest przechwycona (błąd, następnie przekierowanie);
rzeczywiste tworzenie konta pokrywają testy backendu `test_registration_locale`.
Zrzuty `.playwright-mcp/onboarding-{pl,en}-{1..6}.png` sprawdzone wizualnie.
Regresja `session_156_launch_browser_smoke.py` PASS: wznowienie PL/EN,
stary iframe/reload i retry bez utraty cookie; zero błędów JS i nieoczekiwanych
błędów konsoli. Kod pozostaje lokalny, bez wdrożenia.

### Publiczny sygnał BlackNet — read only

Brama losuje jeden sygnał przy każdym renderowaniu, z maksymalnie 100 najnowszych
aktywnych, niewygasłych publikacji BlackNetu o `audience_scope=public`.
Losowanie może ponownie wskazać ten sam sygnał; nie zapisujemy historii gościa.
Brak publicznych publikacji lub niedostępna baza daje „Cisza w eterze”, nie błąd
logowania. Odpowiedź bramy ma `Cache-Control: no-store`.

Publiczna projekcja zawiera wyłącznie tytuł (160 znaków), fragment (280 znaków)
i oryginalny język publikacji. Nie ujawnia owner/clan, identyfikatorów, metadanych,
CTA ani prywatnych publikacji. Tekst escapowany przez Jinja. Sygnał **READ ONLY**:
bez linków, przycisków, otwierania celu i akcji; komunikat PL/EN prosi o logowanie
do pełnego użycia w grze. Zmiana języka interfejsu nie tłumaczy narracji.
Nie ma pollingu, generacji LLM, zapisu odczytu, pinowania języka ani publikowania
podczas wizyty anonimowej. Chronione API BlackNetu pozostaje chronione.

Testy `test_public_blacknet_teaser`: rzeczywista baza sprawdza public/private/clan,
aktywny/wygasły, inne media, brak zapisu i ponowne losowanie; test HTML sprawdza
escaping, brak metadanych i no-store; awaria repozytorium pozostawia formularz.
Chrome/Playwright używa izolowanego publicznego sygnału i wyklucza prywatny;
sprawdza jedną kartę READ ONLY, brak linków/przycisków, PL/EN i responsywność.

- 26 testów: `test_installation`, `test_launch_controller`, `test_ghost_i18n` — PASS.
- `node --check static/js/entry_gate.js`; test izolacji service workera — PASS.
- Lokalny Chrome przez Python Playwright (MCP Playwright niedostępne), izolowana
  baza i konto: PL 1280, EN 390; dodatkowe kontrole 320/768/1920 px, podgląd hasła,
  zmiana języka, formularz, platformy, scroll, `/launch`, offline, późny prompt
  w Ustawieniach, rollback SW. Zero błędów JS i nieoczekiwanych błędów konsoli.
- Podglądy: `.playwright-mcp/entry-156-7-pl.png` i `entry-156-7-en.png`;
  rozwinięte instrukcje: `install-full-pl.png`, `install-full-en.png`.
- Zdarzenia instalacji w teście są symulowane; nie są dowodem instalacji OS.

Bez migracji bazy i nowych flag. Wdrożenie standardową aktualizacją kodu i
restartem procesu web, po decyzji autora. Wycofanie dotyczy szablonu, CSS/JS,
assetu i zgodnego zestawu katalogów; bez przywracania bazy ani cofania sesji.
Hero nie trafia do cache service workera: zachowana lista pięciu publicznych
assetów offline. Przy wolnym łączu pozostaje ciemne tło, formularz jest HTML.
