# 156.4.3 — zdarzenie instalacji po cichym starcie

Zgłoszenie: Redmi A5, Android 15, zwykła karta Chrome. Kliknięcie Android pokazuje
wyłącznie instrukcję; brak systemowego prompta. Windows zainstalowany według użytkownika.

Odtworzono lokalny błąd w Chrome: launch montuje pulpit przez document.open(),
co usuwa listenery dokumentu i window. Globalny ChaosInstall pozostaje i jego
guard pomijał ponowną inicjalizację. Późniejsze beforeinstallprompt nie docierało
do panelu Ustawień. Test regresji przed poprawką: timeout oczekiwania na widoczny
przycisk instalacji po wysłaniu zdarzenia w pulpicie.

Poprawka: idempotentny rebind listenerów i odświeżenie tekstów/montażu panelu,
z zachowaniem wcześniej odroczonego prompta. Bez ponownej rejestracji SW,
bez wymuszenia instalacji, bez zmian sesji. Skrypt install.js?v=156-4-3;
publiczny cache pozostaje na wersji 156-4-2 (install.js nie jest w jego allowliście).

Nie uznajemy tego za potwierdzoną jedyną przyczynę na Redmi. Potrzebny ponowny
odbiór urządzenia po wdrożeniu; test przeglądarkowy symuluje event, nie instalację OS.

Po poprawce Chrome/Playwright PASS: PL desktop 1280 px i EN mobile 390 px,
późny event w Ustawieniach pokazuje przycisk, kliknięcie wywołuje prompt dokładnie
raz. Zero błędów JS i nieoczekiwanych błędów konsoli. Scroll, offline, cache,
wycofanie SW i poprzednie scenariusze nadal PASS. Node izolacji SW PASS.

Referencja: [MDN — document.open](https://developer.mozilla.org/en-US/docs/Web/API/Document/open),
usuwanie listenerów document/window, zweryfikowano 15 X 2026.
