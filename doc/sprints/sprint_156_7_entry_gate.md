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
