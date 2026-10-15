# 156.4.2 — scroll bramki i otwarty odbiór Androida

15 X 2026. Użytkownik potwierdził instalację Windows. Nie oznacza to pełnego
odbioru wszystkich scenariuszy PWA 156.5. Android Chrome/DuckDuckGo: zgłoszony
brak opcji wskazanej w instrukcji; przyczyna na urządzeniu jeszcze nieustalona.

Poprawka lokalna: pionowy scroll bramki desktopowej zamiast overflow:hidden;
bez przebudowy strony. Instrukcja Androida nie obiecuje opcji menu ani natywnego
prompta w każdej przeglądarce. Dostępny event nadal otwiera bezpośrednią instalację.
Katalogi 156.4.2 i wersjonowane zasoby 156-4-2.

Test przeglądarkowy rozszerzony o realny wheel i osiągnięcie końca dokumentu.
Automatyczne przewijanie locatorów i pełnostronicowe screenshoty same w sobie
nie wykrywają blokady przewijania użytkownika.

Wyniki lokalne: Chrome/Playwright PL 1280 px i EN 390 px PASS, rzeczywisty wheel
osiąga dół dokumentu, zero błędów JS i nieoczekiwanych błędów konsoli.
10 testów Python installation+i18n PASS, Node izolacji SW PASS.
Nie testowano fizycznego telefonu Android; nie deklarujemy naprawy jego instalacji.

Backlog: osobny projekt strony głównej gry (prezentacja gry, logowanie i instalacja).
Użytkownik chce go w niedalekim terminie; nie realizujemy przebudowy w tej łatce
i nie nadajemy samodzielnie numeru nowego sprintu.

Źródło referencyjne: [Google — web apps na Androidzie](https://support.google.com/chrome/answer/9658361?co=GENIE.Platform%3DAndroid&hl=en-0).
Udokumentowana ścieżka Chrome nie stanowi dowodu dostępności na zgłoszonym telefonie.
