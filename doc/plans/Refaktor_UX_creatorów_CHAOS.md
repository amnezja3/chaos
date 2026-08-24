# Refaktor UX creatorów CHAOS — 3 sprinty

> Artefakt kierunkowy. Kanoniczna specyfikacja wykonawcza i status sprintów
> znajdują się w `doc/history/game_play_180726.md`, sekcja
> `130.8.9.UX-appcreator.1–3`. Sprinty `.1–2` wdrażają wspólny katalog
> deskryptorów, selektor OFF/ON, kontrakt pojedynczej ikony, semantyczne grupy
> i deterministyczne filtry rodzina → cel → akcja. Sprint `.3` domknął
> podgląd, walidację frontend/backend, dostępność, responsywność i regresję
> tracera bez zmiany istniejącego kontraktu runtime ani migracji aplikacji.

Chcemy gruntownie dopracować istniejące creatory aplikacji/narzędzi w CHAOS tak, aby tworzenie narzędzia było intuicyjne również dla użytkownika, który nie zna wewnętrznych nazw pól ani kontraktów runtime.

## Zakres

Zmiana dotyczy wszystkich obecnych creatorów aplikacji/narzędzi CHAOS.

Poza zakresem:

* GhostLab
* cały `pro-tools-system`
* zmiana mechaniki gameplayowej
* zmiana istniejących endpointów publikacji, jeżeli nie jest absolutnie konieczna
* przebudowa formatu zapisanych aplikacji bez warstwy kompatybilności

Creator ma nadal produkować dane zgodne z aktualnym runtime.

Najważniejszym celem jest UX, czytelność i spójność nomenklatury.

---

# SPRINT 1 — Creator UX Foundation

Najpierw wykonaj audyt wszystkich creatorów objętych zakresem i zbuduj wspólną warstwę UX, z której później będą korzystać wszystkie formularze.

## 1. Jeden język dla creatora, mapy i runtime

Obecnie creator pokazuje użytkownikowi techniczne lub niejasne nazwy, które nie zawsze odpowiadają temu, co widzi później na mapie.

Przykłady:

* `scan_ports`
* `player_tracking`
* `network_anomaly_detection`
* `system_compromise_level`
* `background_injection`
* `file_visibility`

Nie chcemy usuwać istniejących kluczy runtime.

Oddziel:

`runtime key`

od:

`user-facing label`

Creator powinien pokazywać nazwy zgodne przede wszystkim z nomenklaturą używaną na mapie i w normalnym UI gry.

Przykład:

`scan_ports`
→ `Przeskanuj porty`

`player_tracking`
→ `Śledzenie gracza`

`camera_stream`
→ `Podgląd kamery`

Wykonaj audyt istniejących nazw i przygotuj wspólny słownik labeli używany przez creatory.

Nie duplikuj tłumaczeń w różnych formularzach.

---

## 2. Każdy ekran ma prowadzić użytkownika

Każdy krok creatora powinien odpowiadać na trzy pytania:

1. Co teraz wybieram?
2. Co ten wybór zmieni?
3. Gdzie zobaczę jego efekt w grze?

Zachowaj obecny wizard:

1. Nazwa
2. Rodzina
3. Cel
4. Start
5. Działanie
6. Informacje
7. Ryzyko
8. Podgląd
9. Publikacja

ale popraw jego komunikację.

Każdy ekran powinien posiadać:

* krótki nadtytuł kontekstowy,
* jednoznaczny tytuł,
* krótkie wyjaśnienie,
* informację o konsekwencji wyboru,
* zrozumiałe nazwy pól,
* wizualne zaznaczenie aktualnego kroku.

Tekst ma być krótki i konkretny.

Nie robimy tutoriala technicznego.

Użytkownik ma po kilku sekundach rozumieć, co wybiera.

---

## 3. Napraw wybór ikony

Aktualnie można doprowadzić do sytuacji, w której ikona zawiera kilka znaków.

To jest bug.

Ikona aplikacji może zawierać dokładnie jeden symbol / glyph.

Zablokuj możliwość:

* wpisania kilku emoji,
* wklejenia kilku znaków,
* stworzenia wieloznakowej ikony,
* zapisania nieprawidłowej ikony przez manipulację formularzem.

Walidacja powinna istnieć również przed zapisem/publikacją, nie tylko po stronie UI.

---

## 4. Wspólna paleta ikon

Przygotuj około 40 ikon odpowiadających najczęściej używanym pojęciom CHAOS.

Przykładowe grupy:

* sieć
* porty
* firewall
* tarcza
* kamera
* mikrofon
* GPS
* pojazd
* telefon
* router
* serwer
* gracz
* osoba
* ATM
* Wi-Fi
* logi
* pliki
* pamięć
* proces
* kernel
* implant
* exploit
* skan
* tracking
* stealth
* alert
* blokada
* dostęp
* dane
* baza danych
* komunikator
* e-mail
* audio
* wideo
* lokalizacja
* finanse
* integralność
* wykrycie
* ryzyko
* system

Paleta ma wizualnie pasować do istniejących kompletów ikon CHAOS.

Ikony muszą być używalne również przy późniejszych macierzach wyboru.

Preferuj istniejący system ikon / font / SVG / asset pipeline projektu zamiast tworzenia 40 niezależnych wyjątków.

---

## 5. Wspólny komponent wyboru

Przygotuj reusable komponent zastępujący duże listy checkboxów.

Stan:

`OFF`

* przygaszony
* niski kontrast
* bez aktywnego obramowania

`ON`

* podświetlony
* czytelne obramowanie
* ikona + nazwa
* jednoznaczny stan aktywny

Element powinien wyglądać bardziej jak przełączalny przycisk niż klasyczny checkbox.

Macierz powinna automatycznie układać się zależnie od szerokości okna.

Każdy element:

`[ IKONA ] Nazwa`

Opcjonalnie po hover/focus:

krótki opis.

Nie zmieniaj jeszcze wszystkich formularzy na siłę. W tym sprincie przygotuj fundament, słownik i wspólny komponent.

## Definition of Done Sprint 1

* audyt creatorów objętych zakresem,
* wspólny słownik runtime key → UX label,
* jeden reusable system przycisków ON/OFF,
* paleta około 40 ikon,
* jednoznaczne stany aktywny/nieaktywny,
* naprawiony bug wielu znaków ikony,
* walidacja pojedynczej ikony,
* brak zmian GhostLab,
* brak zmian `pro-tools-system`,
* istniejące zapisane aplikacje nadal działają.

---

# SPRINT 2 — Creator UX Migration

W drugim sprincie wykorzystaj fundament Sprintu 1 i przebuduj właściwe kreatory.

## 1. Usuń checkbox UX

W creatorach objętych zakresem zwykłe listy checkboxów powinny zostać zastąpione macierzami przycisków ON/OFF.

Dotyczy to między innymi:

* target types,
* sposobu uruchamiania,
* operations,
* resource/data types,
* możliwości aplikacji,
* security/risk properties,
* wpływu na gracza,
* innych wielokrotnych wyborów.

Nie chodzi o zmianę HTML dla samej zmiany HTML.

Chodzi o zmianę sposobu myślenia użytkownika:

z:

`zaznacz parametr`

na:

`wybierz możliwości swojego narzędzia`.

---

# 2. Cel

Ekran celu ma używać nazw kojarzących się bezpośrednio z obiektami występującymi w świecie gry.

Np.:

* Obiekt na mapie
* Kamera
* ATM
* Serwer
* Router
* Gracz
* Pojazd
* Telefon
* Osoba
* Miejsce
* Filar konfliktu

Każdy typ powinien posiadać ikonę.

Jeżeli backend korzysta z innego klucza, wykonuj mapowanie wewnętrzne.

---

# 3. Start

Obecne pytanie:

`Skąd gracz ma uruchamiać narzędzie?`

należy dopracować.

Użytkownik powinien rozumieć różnicę między:

* miejscem uruchomienia,
* akcją widoczną na mapie,
* trybem desktopowym,
* operacją wykonywaną wobec celu.

Nazwy akcji muszą odpowiadać nazwom widocznym później na mapie.

Jeżeli na mapie użytkownik widzi:

`Przeskanuj porty`

to creator nie powinien używać zupełnie innego określenia dla tej samej operacji.

---

# 4. Działanie

To ma być najbardziej intuicyjna część creatora.

Nie pytamy użytkownika o techniczne właściwości implementacji.

Pytamy:

`Co ma robić Twoje narzędzie?`

Każda opcja powinna posiadać:

* ikonę,
* nazwę,
* krótki opis efektu gameplayowego.

Np.:

`Śledzenie celu`

`Śledzenie pojazdu`

`Monitoring kamery`

`Nasłuch mikrofonu`

`Czasowe wyłączenie kamery`

`Odczyt logów ATM`

`Implant sieciowy`

`Rozpoznanie sieci`

`Zakłócenie audio`

`Diagnostyka ECU`

Nazwy dopasuj do rzeczywiście obsługiwanych kontraktów.

---

# 5. Informacje

Analogicznie przebuduj ekran danych.

Użytkownik powinien wybierać:

`Jakich informacji szuka narzędzie?`

zamiast zastanawiać się nad wewnętrznym `resource_type`.

Przykładowe grupowanie:

LOKALIZACJA

* Historia lokalizacji
* Logi GPS
* Baza hotspotów

URZĄDZENIE

* Logi urządzenia
* Diagnostyka pojazdu
* Stan rozpoznania

MEDIA

* Transkrypcja audio
* Materiał wideo
* Dump kamery

KONTA I TOŻSAMOŚĆ

* Dane osobowe
* Konta e-mail
* Dane komunikatora
* Dane dostępowe

FINANSE

* Rekordy finansowe
* Dump ATM

Grupowanie powinno wynikać z istniejących danych, a nie tworzyć nowych gameplayowych typów.

---

# 6. Ryzyko — najważniejsza przebudowa

Obecny ekran ryzyka jest nieczytelny.

Pytania typu:

`Co powinno być wyłączone?`

nie mówią użytkownikowi:

* czy chodzi o jego system,
* system celu,
* zabezpieczenie,
* warunek sukcesu,
* efekt exploita,
* ryzyko,
* wymaganie narzędzia.

Ten ekran trzeba zaprojektować od nowa na poziomie UX.

Nie zmieniaj jednak znaczenia istniejącego kontraktu bez potrzeby.

Najpierw ustal semantykę obecnych pól.

Następnie przedstaw ją użytkownikowi w logicznych sekcjach.

Przykładowy kierunek:

### ZABEZPIECZENIA CELU

`Co utrudnia działanie narzędzia?`

Przykład:

🛡 Firewall
👁 Wykrywanie skanowania
🧠 Memory Guard
🔐 Kernel Guard
📡 Network Anomaly Detection

---

### MOŻLIWOŚCI NARZĘDZIA

`Które zabezpieczenia potrafi ominąć lub wyłączyć?`

---

### WPŁYW NA GRACZA

`Jak użycie narzędzia wpływa na operatora?`

Np.:

* anonimowość,
* wykrywalność,
* poziom ryzyka,
* tracking,
* traceability.

---

### EFEKT OPERACJI

`Jakie właściwości systemu mogą zmienić się po użyciu?`

Każdy parametr otrzymuje:

* ikonę,
* normalną nazwę,
* opcjonalny krótki tooltip,
* stan OFF/ON.

Nie pokazuj użytkownikowi surowych nazw takich jak:

`system_compromise_level`

jeżeli można pokazać:

`Poziom przejęcia systemu`.

Surowy klucz pozostaje w danych runtime.

---

# 7. Visual state

Wszystkie wielokrotne wybory mają korzystać ze wspólnego języka wizualnego:

OFF:
`ciemny / wygaszony`

ON:
`zielony / aktywny / podświetlony`

Hover:
`możliwy wybór`

Disabled:
`niedostępny dla obecnej konfiguracji`

Jeżeli wybór wcześniejszego kroku powoduje, że opcja nie ma zastosowania, można ją ukryć albo oznaczyć jako niedostępną — zależnie od tego, co będzie czytelniejsze.

Nie pokazuj użytkownikowi dziesiątek opcji, które nie mają sensu dla aktualnego celu lub rodziny narzędzia.

## Definition of Done Sprint 2

* wszystkie creatory objęte zakresem korzystają ze wspólnego systemu wyboru,
* zwykłe checkbox-wall zostały usunięte,
* pola posiadają ikony,
* nazwy odpowiadają nomenklaturze mapy,
* cel/start/działanie/informacje są zrozumiałe bez znajomości kodu,
* ekran ryzyka jest podzielony semantycznie,
* użytkownik rozumie, czego dotyczy każda grupa ryzyka,
* wcześniejsze wybory filtrują niepasujące opcje,
* runtime keys pozostają kompatybilne,
* GhostLab i `pro-tools-system` pozostają nietknięte.

---

# SPRINT 3 — Creator Polish, Preview & Validation

Po migracji wykonaj pełny polish UX i regresję.

## 1. Podgląd

Obecny podgląd JSON może pozostać jako opcja diagnostyczna, ale nie powinien być głównym sposobem zrozumienia stworzonego narzędzia.

Najpierw pokaż czytelne podsumowanie:

IKONA + NAZWA

Rodzina
Cel
Uruchamianie
Działania
Pozyskiwane informacje
Obsługiwane zabezpieczenia
Ryzyko
Cena
Interface

Dopiero niżej można pokazać:

`Pokaż kontrakt techniczny`

i rozwijany JSON.

Creator powinien pozwalać zrozumieć stworzoną aplikację bez czytania JSON-a.

---

# 2. Walidacja w kontekście

Nie czekaj z większością błędów do publikacji.

Przykłady:

Brak nazwy:

`Nadaj aplikacji nazwę, zanim przejdziesz dalej.`

Brak celu:

`Wybierz przynajmniej jeden typ celu.`

Wybrano działanie niepasujące do celu:

`Podgląd kamery wymaga celu typu Kamera.`

Brak map action dla narzędzia mapowego:

`Narzędzie uruchamiane z mapy potrzebuje przynajmniej jednej akcji.`

Nie używaj komunikatów wynikających bezpośrednio z nazw backendowych pól.

---

# 3. Inteligentne filtrowanie

Wykorzystaj informacje z wcześniejszych kroków.

Jeżeli użytkownik wybierze:

`Vehicle tool`

nie pokazuj mu bez powodu parametrów charakterystycznych wyłącznie dla ATM.

Jeżeli wybierze:

`Camera tool`

wyeksponuj:

* obraz,
* monitoring,
* stream,
* camera dump,
* camera disable,
* audio, jeżeli kamera je wspiera.

Creator ma stopniowo zawężać wybór zamiast prezentować całą bazę kontraktu naraz.

Nie zmieniaj danych runtime — zmieniaj sposób ich prezentacji.

---

# 4. Responsive UX

Sprawdź:

* desktop,
* mniejsze okno desktopowe,
* mapę otwartą obok creatora,
* małe wysokości viewportu,
* scroll,
* długie nazwy,
* tooltipy,
* macierze 2/3/4 kolumnowe zależnie od miejsca.

Nie dopuszczaj do poziomego scrolla całego creatora.

---

# 5. Accessibility i obsługa klawiatury

Przyciski wyboru muszą zachowywać się jak prawdziwe kontrolki.

Zapewnij:

* focus,
* Enter/Space,
* aria state tam, gdzie ma zastosowanie,
* jednoznaczny stan również bez samego koloru.

---

# 6. Regresja

Przetestuj:

* tworzenie aplikacji,
* edycję, jeśli istnieje,
* preview,
* publikację,
* instalację,
* uruchomienie z mapy,
* uruchomienie desktopowe,
* istniejące aplikacje,
* zapis starych runtime keys,
* icon validation,
* wielokrotne szybkie przełączanie opcji,
* cofanie między krokami,
* filtrowanie zależne od celu,
* reload creatora.

Dodaj testy dla wspólnych kontraktów creatora zamiast testować tylko pojedyncze formularze.

---

# Hard Rules

1. Nie modyfikuj GhostLab.
2. Nie modyfikuj `pro-tools-system`.
3. Nie zmieniaj mechaniki gameplayowej tylko po to, aby uprościć formularz.
4. Nie zmieniaj runtime keys, jeśli można zastosować mapping UX label → runtime key.
5. Nie twórz osobnego komponentu dla każdego creatora, jeżeli zachowanie jest wspólne.
6. Nie kopiuj palety ikon między plikami.
7. Jedna aplikacja = jedna ikona = jeden glyph.
8. Nie publikuj surowej nomenklatury backendowej użytkownikowi, jeśli istnieje normalna nazwa gameplayowa.
9. Creator powinien prowadzić użytkownika od intencji do kontraktu, nie od kontraktu do intencji.
10. Zachowaj kompatybilność istniejących aplikacji.

# Oczekiwany rezultat

Po zakończeniu trzech sprintów użytkownik powinien móc wejść do creatora bez znajomości backendu CHAOS i stworzyć narzędzie przez wybieranie wizualnych możliwości:

`co to jest → na czym działa → skąd się uruchamia → co robi → jakie dane daje → jakie zabezpieczenia obsługuje → jakie niesie ryzyko → podgląd → publikacja`.

Creator ma wyglądać jak część gry, a nie jak edytor surowego kontraktu JSON.
