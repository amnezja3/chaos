# Kategorie Start

Menu grupuje istniejące launchery; nie zmienia aplikacji ani kontraktu instalacji.
Puste sekcje są pomijane. Wewnątrz sekcji obowiązuje sortowanie według widocznej
nazwy z uwzględnieniem aktualnego języka i liczb. Nazwy autorów pozostają oryginalne.
Każda aplikacja ma dokładnie jedną kategorię, licznik i swój oryginalny launcher.

| Sekcja PL | Sekcja EN | Przypisanie |
| --- | --- | --- |
| Recon / Mapa | Recon / Map | Mapa, skanery, tropienie, podgląd kamer, Deep Scanner |
| Exploity | Exploits | Exploity, wyłączenie kamer, audio hack, car hack |
| Sniffery / Monitoring | Sniffers / Monitoring | Sniffing, mikrofony, logi ATM, Operation Control |
| PvP / Terytoria | PvP / Territories | Dedykowane akcje na graczu, sześć rodzin PvP GhostLaba, Victim Picker, Territory Control |
| OSINT / Analiza | OSINT / Analysis | AGI, narzędzia analizy i dekodowania, dokumenty PTK |
| Finanse / Trading | Finance / Trading | Wallet, giełda, trading |
| Społeczność | Community | Cyberner, radio, komunikatory |
| Kreatory | Creators | AppForge, TermCreator, WindowMaker, ButtonMaker, GhostLab |
| Serwis / Ochrona | Maintenance / Protection | Konserwacja, aktualizacje, firmware, VPN, zabezpieczenia, pliki |
| System | System | Pozostałe launchery systemowe, przeglądarka |
| Dodatki gameplayowe | Gameplay additions | Pozostałe zainstalowane dodatki, bilety, nieznane kontrakty |

Priorytet ma dedykowany kontrakt PvP, potem szablon/identyfikator systemowy,
rodzina i akcje narzędzia. Sama obsługa `player` obok markerów mapowych nie
przenosi uniwersalnego skanera do PvP. Nazwa i opis autora nie są klasyfikatorem.
Financial Sniffer jest narzędziem ataku na gracza i pozostaje w PvP.

Metadane zachowuje `buildIconsFromJsonWithCommand`; wszystkie istniejące ścieżki
odświeżenia instalacji/usunięcia korzystają z `setToolbarLaunchers` i przebudowują
sekcje. Rozwinięcie kategorii zachowuje się w bieżącej sesji podczas odświeżenia
oraz przełączania PL/EN. Natywne details/summary obsługują klawiaturę; menu ma
własne przewijanie i ograniczenie do szerokości/wysokości ekranu mobilnego.

Weryfikacja: test klasyfikacji Node obejmuje kontrakty, starsze typy i cały
statyczny katalog. Playwright: sortowanie, poprawny launcher po sortowaniu,
zmiana PL/EN, zachowanie rozwinięcia, dopisanie instalacji i licznik, mobile
390×844, brak błędów JS. Układ sprawdzony na zrzucie menu.
