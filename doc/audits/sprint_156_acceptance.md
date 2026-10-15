# Sprint 156 — zamknięcie implementacji i odbiór produkcyjny

15 X 2026. Decyzja autora: domknąć 156, pozostawić Linux i iOS do testów.
**Implementacja i wdrożenie zamknięte; odbiór platform częściowy.** Nie oznacza
pełnego PASS wszystkich scenariuszy ani automatycznego rozpoczęcia Sprintu 157.

## Potwierdzone dowody

| Obszar | Wynik | Źródło i ograniczenia |
| --- | --- | --- |
| Backend na serwerze | PASS | 39 testów izolowanych przed migracją |
| Backup | PASS | `~/chaos-backups/156-20261015T135040Z/game.sqlite3`, integralność/FK OK; `flask-session.tar.gz`, 516 wpisów |
| Migracja | PASS | applied, pięć kolumn TTL, original_data_unchanged:true |
| Sekret | Skonfigurowany | Prywatny plik serwera 0600, restart czterech procesów z nowym sekretem; starych logowań nie przenoszono |
| Trwałe sesje | PASS zgłoszonego smoke | Autor: gameplay działa normalnie po włączeniu |
| Cichy start | PASS użytkownika | /launch bez loginu, reload/powrót przeglądarki, mapa, logout; wszystkie cztery kroki PASS |
| Windows | Instalacja PASS | Potwierdzenie autora; brak pełnych wersji OS/przeglądarki i osobnego protokołu restartu urządzenia |
| GrapheneOS + Chrome | PASS zgłoszonego cyklu | Autor po instrukcji instalacja → ikona → login → zamknięcie/powrót: „grapOS przetestowany pass”; wersje niepodane |
| Samsung + Chrome | Instalacja PASS | Autor: „na samsungu na chromie też działa”; model i wersje niepodane, nie rozszerzamy na wszystkie testy trwałości |
| Redmi A5 / Android 15 / Chrome 155.0.8059.79, 32-bit | Problem zgodności otwarty | Brak prompta i pozycji menu również dla niezależnego demo MDN; dokładna przyczyna OS/Chrome/launchera niepotwierdzona |
| Redmi — obejście | Dostęp działa | Widżet zakładek Chrome z CHAOS; nie jest instalacją PWA ani samodzielną ikoną aplikacji |
| Linux / Ubuntu 24 | PENDING | Tester pobrał Type=Link .desktop; brak potwierdzonej przeglądarki/desktopu i instalacji |
| iOS / iPadOS | PENDING | Brak testu fizycznego urządzenia i osobnego storage |

Na produkcji sprawdzono publiczną bramkę w zwykłych tymczasowych profilach Chrome:
HTTP 200, brak błędów manifestu/instalowalności, aktywny SW, rzeczywisty
beforeinstallprompt i widoczny przycisk. Emulacja Androida na desktopowym Chrome
nie jest dowodem działania na Redmi. Produkcja serwowała install.js?v=156-4-3.

## Poprawki odbiorowe

- 156.4.1: formularz i panel bez nakładania, jawny przycisk instalacji.
- 156.4.2: scroll bramki, instrukcja Androida bez gwarantowania opcji menu.
- 156.4.3: ponowne podłączenie eventów po document.open; test przed poprawką
  odtwarzał brak przycisku, po poprawce późny event uruchamia prompt dokładnie raz.
- Lokalnie: 10 testów installation+i18n, Node izolacji SW, Chrome/Playwright
  PL 1280 i EN 390 PASS; prawdziwy wheel, cache, offline, settings i rollback.

Nie przeprowadzono fizycznego upływu 30/90 dni; granice TTL potwierdzają testy
z kontrolowanym zegarem. Nie uzupełniamy brakujących dowodów urządzeń symulacją.

## Pozostawione odbiory

Linux i iOS: instalacja, ikona, login, zamknięcie/powrót, logout, aktualizacja,
offline; dla iOS szczególnie oddzielny magazyn sesji. Zanotować wersje OS i
przeglądarki. Redmi pozostaje osobnym problemem zgodności, nie blokuje gameplayu.
Zapis końcowych trzech flag w dump PM2 wymaga potwierdzenia operatora — wcześniejszy
pm2 save dotyczył konfiguracji przed ich włączeniem. Instrukcja w runbooku 156.6.

Osobny przyszły zakres: pełna strona główna gry. Nie wdrażamy jej w 156.
