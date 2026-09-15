# Terminal — pakiety Googleplex

Dodano 2026-09-15 jako osobny update terminala, poza implementacją Sprintu 141.

| Komenda | Działanie |
| --- | --- |
| `pkg list-all` | Wszystkie opublikowane pozycje katalogu Googleplex: nazwa, ID i cena HC |
| `pkg search <nazwa>` | Wyszukiwanie fragmentu nazwy lub ID, bez rozróżniania wielkości liter; jawny komunikat braku wyników |
| `pkg install <nazwa>` | Dokładna nazwa lub ID; nazwy ze spacjami można podać także w cudzysłowie |

Przykład: `pkg search log`, następnie `pkg install "System Log Reader"`.
Przy kilku identycznych nazwach należy użyć ID. Częściowe dopasowanie nie kupuje
automatycznie produktu; terminal wyświetla propozycje. `apps` nadal pokazuje
aplikacje już zainstalowane, a `help` opisuje nowe komendy.

Obsługa znajduje się w terminalu przeglądarkowym przed delegacją do `/command`.
Katalog pochodzi z istniejącego `/resources.json`, tego samego co sklep,
bez odczytu profilu ani osobnego katalogu pakietów. Wyniki są escapowane.

Instalacja otwiera istniejący `showInstallAppProgress` i czeka na zakończenie;
terminal także wypisuje wynik. Zachowuje `/install-app`, klucz akcji/retry,
serwerowe ceny i wymagania, rozliczenie HC, inventory, aktualizację launchera
i efekt produktu. Potwierdzenie zakupu jest wymagane dla travel ticket i
`purchase_confirmation`, jak w sklepie. Nie powstaje drugi mechanizm instalacji.
GhostScript czeka na instalator, a błąd lub anulowanie zatrzymuje sekwencję.

Nowe listowanie/wyszukiwanie nie odczytuje konta. Koszt dotychczasowych gałęzi
instalatora pozostaje jego istniejącym kontraktem; zmiana nie stanowi audytu
ani dowodu usunięcia wszystkich ciężkich zapisów instalacji.

Walidacja: `tests/js/test_terminal_pkg.js` sprawdza wyszukiwanie, nazwy/ID,
niejednoznaczność, escapowanie, anulowanie, błędy i delegację do instalatora.
Ręczny zakup w przeglądarce i odbiór produkcyjny wymagają osobnego potwierdzenia.
