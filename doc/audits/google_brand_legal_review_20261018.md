# CHAOS dokumenty do weryfikacji marki Google

Historyczna notatka z przygotowania. Bieżącą, ograniczoną listę decyzji i osobny backlog zawiera [domknięcie dokumentów](google_publication_decisions.md); wcześniejsze rozbudowane listy poniżej nie są dodatkowymi warunkami publikacji.

Stan na 2026-10-18: propozycja PL/EN w `legal_documents.py` oraz wspólnym szablonie `/privacy` i `/terms`. Nie opublikowano na produkcji, nie zmieniono Google Cloud ani flag wieku. Nie jest jeszcze gotowa do ponownego zgłoszenia: brakujące dane organizacyjne i retencja wymagają ustalenia, a następnie wykonania ustaleń.

## Fakty potwierdzone

- Operator: Michał Cezary Jankiewicz, osoba prywatna; ul. Relaksowa 5 lok. 1, 27-400 Ostrowiec Świętokrzyski, Polska; year2108@chaos.re.
- Projekt niekomercyjny; nie potwierdzono bezpłatności wszystkich funkcji.
- cyber_Folks: VPS w Polsce, DNS i poczta — potwierdzone przez operatora. Backupy: 28 dni; logi czyszczone raz w miesiącu. Umowa powierzenia: niezawarta, w przygotowaniu. Nie przeprowadzono zdalnej weryfikacji konfiguracji.
- Google: `openid email`, podpisany token, sub/email/email_verified, daty powiązania/użycia. Identity nie zapisuje access/refresh tokenów. Nie ma dostępu do Gmaila, Dysku, Kontaktów, Kalendarza ani zdjęcia profilowego.
- Usunięcie powiązania Google nie usuwa osobnego adresu bezpieczeństwa konta. Usunięcie konta pozostawia hash wycofanego identyfikatora dostawcy i blokadę ponownego użycia nazwy. Hash nie jest gwarancją anonimizacji.
- Cleanup Identity uruchamia się przy rozpoczęciu autoryzacji: usuwa wygasłe rekordy i zdarzenia bezpieczeństwa starsze niż 90 dni. To wyzwalanie zdarzeniem, nie potwierdzony harmonogram produkcyjny.
- Proponowana polityka 16+ i ochrona komunikacji pozostają osobnymi, nieaktywowanymi etapami. Aktualizacja dokumentów nie jest akceptacją nowych warunków przez graczy.

## Audyt usług w kodzie

Sprawdzono `templates`, `static` (HTML/JS/CSS), `run.py`, adaptery Identity i narracji. Nie znaleziono integracji Google Analytics, Google Tag Manager, Matomo, Plausible, PostHog, Mixpanel, Hotjar, Clarity, Meta Pixel, Sentry ani Google Ads. To wynik audytu repozytorium, nie konfiguracji VPS, proxy, DNS ani pełnego ruchu podczas rozgrywki.

| Usługa | Dane i wywołanie |
| --- | --- |
| Google, GitHub, Discord, Steam | Wybrana metoda logowania; zminimalizowane dane tożsamości. `identity_gateway/providers.py`. |
| cyber_Folks | VPS w Polsce: dane kont i gry; DNS; poczta: adres odbiorcy, kody/potwierdzenia. Umowa powierzenia niezawarta, w przygotowaniu. |
| OpenStreetMap, OpenTopoMap | Kafelki mapy z przeglądarki: IP, dane żądania i wskazany obszar mapy. `run.py`, `static/map.html`. |
| OpenStreetMap embed | Osadzona mapa w `static/js/terminal.js`. |
| unpkg.com | Leaflet JS/CSS generowane przez `run.py`: IP i dane żądania. |
| ip-api.com | Publiczne IP przesyłane z serwera przy tworzeniu profilu, miasto i współrzędne. `get_start_location_by_ip` w `run.py`. Obecnie HTTP. |
| Mistral | Instrukcje i pakiet wiadomości narracyjnych do api.mistral.ai; pakiet może zawierać etykiety graczy i zdarzenia świata. |
| Ollama | Alternatywny skonfigurowany endpoint; jego fizyczne położenie wymaga potwierdzenia produkcyjnego. |

Nie deklarujemy całkowitej anonimowości danych narracji, braku trenowania u usługodawcy ani lokalizacji w EOG bez umów i konfiguracji. Nie dodajemy Cloudflare jako odbiorcy na podstawie resolvera 1.1.1.1 lub obsługi nagłówka CF-Connecting-IP.

## Retencja do zatwierdzenia i wdrożenia

Poniższe okresy są propozycją minimalizacyjną, a nie opisem obecnej konfiguracji ani ustawowym okresem dla każdej kategorii. Indywidualne zabezpieczenie dowodów wymaga udokumentowanego celu, podstawy, ograniczenia dostępu i daty ponownego przeglądu.

| Kategoria | Stan obecny | Propozycja |
| --- | --- | --- |
| Logi dostępu i błędów proxy/PM2 | Operator potwierdził czyszczenie raz w miesiącu; zakres i maksymalny wiek rekordów do sprawdzenia | Propozycja: maksymalnie 31 dni przy miesięcznym cyklu; bez tokenów, kodów, treści wiadomości i parametrów callback w logach. Nie jest to potwierdzenie już działającego limitu. |
| Zdarzenia bezpieczeństwa Identity | Cleanup usuwa starsze niż 90 dni przy autoryzacji | 90 dni z codziennym zadaniem cleanup. |
| Wygasłe próby, tickety i kody | Cleanup przy autoryzacji; wygaśnięcie nie usuwa natychmiast danych | Codzienne usuwanie, maksymalnie 24 h po wygaśnięciu. |
| Backupy | Operator potwierdził retencję 28 dni | Zastępuje wcześniejszą propozycję 30/14 dni. Zweryfikować wykonanie cyklu dla wszystkich kopii, także wdrożeniowych; szyfrowanie i ograniczony dostęp pozostają zaleceniami do sprawdzenia. |
| Wygasłe sesje na dysku | Ważność 30 dni nieaktywności / 90 dni od logowania; fizyczne sprzątanie do sprawdzenia | Codzienne sprzątanie wygasłych sesji. Nie utożsamiać plików sesji z backupami. |
| Zamknięte zgłoszenia i dowody | Brak zaakceptowanej retencji | 180 dni od ostatecznego zamknięcia; dłużej wyłącznie dla konkretnego udokumentowanego postępowania. |
| Hashe wycofanych tożsamości i tombstone nazwy | Brak automatycznego terminu | Przegląd po 90 dniach; usunięcie zbędnych danych. Wcześniej sprawdzić, czy ponowne użycie nazwy nie odsłania starej historii. Nie włączać automatycznego ponownego użycia nazw bez tej analizy. |
| Wspólna historia i wiadomości u odbiorców | Pozostają po usunięciu konta | Osobny audyt pseudonimizacji/identyfikatorów i procedura żądań; nie deklarować bezterminowego zachowania danych osobowych. |

Po odtworzeniu backupu trzeba ponownie zastosować wykonane żądania usunięcia, aby kopia nie przywracała usuniętych kont lub danych do normalnego użycia. Procedura i minimalny rejestr realizacji wymagają wdrożenia.

## Stan produkcyjny do sprawdzenia

Operator potwierdził VPS cyber_Folks w Polsce, 28 dni retencji backupów i miesięczne czyszczenie logów. Źródłem okresu 28 dni jest potwierdzenie operatora, nie publiczna tabela VPS Root. Umowa powierzenia jest w przygotowaniu i nie została zawarta. Nadal nie sprawdzono zdalnie wykonania retencji ani obsługi kopii po zakończeniu usługi.

Nie uzyskano dostępu do VPS w tym przeglądzie. `ecosystem.config.js` nie znajduje się w lokalnym repozytorium. Nie wykonano zdalnego sprawdzenia retencji.

Operator powinien sprawdzić lokalnie na VPS konfigurację cron/timerów, reguły logrotate, ustawienia pm2-logrotate i listę kopii wdrożeniowych. Przekazuje tylko okresy, częstotliwość i wynik, bez pełnego środowiska PM2, logów żądań, cookies, sekretów lub treści crontab zawierających poświadczenia. Nazwę usługodawcy i kraj należy odczytać z panelu/umowy hostingu. Przy usługach spoza EOG potrzebna jest podstawa transferu i informacja o zabezpieczeniach; nie wnioskujemy jej z samej marki.

## Warunki finalizacji

1. Uzyskać osobne potwierdzenie zawarcia umowy powierzenia z cyber_Folks; do tego czasu status pozostaje „niezawarta, w przygotowaniu”. Potwierdzić pełne przepływy AI, pozostałe umowy i transfery, stan proxy i narzędzi spoza repozytorium.
2. Rozstrzygnąć przesyłanie IP przez HTTP: rekomendacja to usunięcie zależności i użycie istniejącego losowania miasta, jeśli geolokalizacja nie jest konieczna. Zmiana gameplayu nie została wykonana w ramach edycji dokumentów.
3. Zweryfikować wykonanie potwierdzonej retencji backupów 28 dni i miesięcznego czyszczenia logów. Ustalić pozostałe okresy retencji i wdrożyć sprzątanie; nie zmieniać częstotliwości czyszczenia w niepotwierdzony dokładny limit wieku wpisu.
4. Potwierdzić odpłatność, osobę obsługującą zgłoszenia, zasady odwołań i prawa do treści potrzebne do działania gry.
5. Zredagować finalne dokumenty bez notatek audytowych, nadać datę obowiązywania, uzgodnić wersję akceptacji warunków. Nie zmieniać historii zgód ani flag wieku automatycznie.
6. Po zatwierdzeniu i wdrożeniu sprawdzić publiczne strony PL/EN bez sesji oraz linki na bramce. W Google Cloud użyć kanonicznego https://chaos.re, /privacy i /terms. Callback pozostaje /auth/google/callback.
7. Potwierdzić aktualny status Audience oraz Branding oddzielnie. Właściciel Search Console powinien mieć powiązane uprawnienia do projektu. Ponowne zgłoszenie dopiero po wykonaniu poprawek; odczekać 24 h po weryfikacji domeny zgodnie z otrzymaną instrukcją Google.

## Źródła

- [Google brand verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/brand-verification): publiczne strony, zgodność domen, opis dostępu/wykorzystania/przechowywania/udostępniania danych.
- [Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy).
- [RODO](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng), w szczególności art. 5, 6, 12–14, 17 i przepisy o transferach. Oświadczenie wieku nie zastępuje oceny podstaw przetwarzania.

## Weryfikacja lokalna

Playwright MCP: obie strony PL/EN, szerokości 1440 i 390 px (8 wariantów) — HTTP 200, prawidłowy język, canonical, dane kontaktowe, działający spis treści i brak poziomego przepełnienia. Okno dokumentu w rejestracji otwiera się w miejscu i po zamknięciu zachowuje wpisany login. Brak błędów konsoli/JS. Izolowana aplikacja i przeglądarka zamknięte po sprawdzeniu. Dalsze dopisanie informacji o miesięcznym czyszczeniu i ofercie backupu jest zmianą tekstową; sprawdzenie składni i diff wykonane po niej. Nie testowano produkcyjnej konfiguracji ani zgłoszenia Google.
