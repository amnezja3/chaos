# Sprint 166 — Camera Street View: źródło rzeczywiste i odbiór VPS

31.10.2026. PLAN, nowy zakres nadany przez operatora; nie sprint zdjęć graczy.
Zależności: lokalny pakiet 164–165, PASS prezentacji, decyzja o wdrożeniu.

Pakiet/paczka oznacza zakres kodu w repo, nie ZIP. Obowiązuje standardowy Git:
zatwierdzenie → commit/push → zbiorcze wdrożenie OFF → pilot rzeczywistego API.
[Wspólna procedura dwóch sesji i rollback](../runbooks/camera_street_view_package_165_1.md).
Defekty odbioru poprawiamy lokalnie i wdrażamy kontrolowaną aktualizacją;
nie rozbijamy zakresu na dziesiątki sesji ani nie ponawiamy PASS bez przyczyny.

1. Wdrożyć gotową paczkę po poleceniu operatora, z backupem i rollback.
2. Odebrać na rzeczywistym źródle adapter i archiwum przygotowane lokalnie
   w 164–165. Zamknąć bramki L01/L02: retencja, wycofania i linkowanie.
   Implementacja adaptera i testy fixtures należą do pierwszej paczki, nie do tego etapu.
3. Podłączyć sekret istniejącym mechanizmem środowiska. Klucz tylko na backendzie,
   diagnostyka present/valid, nigdy sekret w przeglądarce lub repo.
4. Kontrolowany pilot jednej kamery: skan/serwerowa tożsamość → aplikacja →
   sukces → rzeczywisty czas pobrania z mocami → plik → jednorazowe okno.
5. Zweryfikować brak pokrycia, timeout, limity, prawa/źródło, wycofanie obrazu,
   restart, ponowne logowanie, zamknięcie i nowe hakowanie. Potem ograniczony rollout.

Osobne statusy: LOCAL PASS / wdrożone / live provider PASS / VPS PASS.
Żaden dotychczasowy PASS syntetycznych zdjęć nie dowodzi działania API.
Brak zgody na zdjęcia graczy, aparat/GPS, Vision, rozpoznawanie osób i moderację.
Nie uruchamiać historycznych procedur VPS ani dawnych kolejek.
