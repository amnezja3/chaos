# Sprint 146.5 — pakiet GhostLab 1.0

Stan: **PASS — zamknięty 1 X 2026**, odbiór zaakceptowany przez autora.
Bez automatycznego commita, pushowania ani wdrożenia produkcyjnego.

Końcowe poprawki: pełnej szerokości edytor Markdown/Render, wybór globalnie/klan
pod edytorem, folder **Plexcak /documents** i uwierzytelniony katalog ofert
w WebDragonie oraz terminalu. Przewijanie pola przechodzi na widok GhostLaba,
gdy treść jest krótka albo osiągnięto jej początek/koniec; 16 scenariuszy
Playwright dla kółka i dotyku przeszło. GhostLab 1.0 zamknięty; dalej sprint 147.

Weryfikacja lokalna 30 IX: testy completion/publication/alignment, regresja firmware,
runtime i zakupów po konfiskacie; sześć zestawów JS (w tym Markdown). Playwright MCP
na czystej tymczasowej bazie i dwóch kontach: projekt → template PTK → zapis →
kompilacja → publikacja → pobranie → czytnik mobile; ochrona niezapisanych zmian,
jedno okno GLaba, bez wykonania HTML i bez błędów konsoli. Przeglądarka i serwer
testowy zamknięte po kontroli. Te wyniki nie zastępują PASS autora w grze.

## Zakres

- File Manager → GhostLab: projekcje `.lab` z kanonicznych projektów, otwarcie po ID,
  jedno okno i ochrona niezapisanych zmian. Brak aplikacji `ghost_lab` daje komunikat
  o konieczności instalacji, nie usuwa projektu. FM nie udostępnia usuwania `.lab`.
- Terminal: nazwa albo `run <ID aplikacji>`, projekty: `open <ID projektu>.lab`.
  Pobrany dokument: `open <ID artefaktu>.ptk` otwiera czytnik, bez executora.
  Duplikaty wymagają ID. Nazwy pojedynczych komend systemowych są zastrzeżone przy
  publikacji; stare kopie pozostają uruchamialne przez ID. Alias pokazany w FM.
- PTK: Markdown do 6000 znaków (obowiązuje też limit rozmiaru requestu), tekst
  renderowany bez wykonywania HTML. Globalnie lub tylko dla aktualnego klanu autora.
  Klan jest przypisywany przez serwer przy publikacji. Oferty prywatne są pomijane
  w publicznym katalogu/newsach; zakup wymaga aktualnego członkostwa w tym klanie.
- Każde pobranie kupuje konkretny build; powtórzenie nie pobiera ponownie HC.
  Nowy build wymaga osobnego świadomego pobrania. Stare wydania pozostają w
  katalogu Plexcak, również po wycofaniu i opuszczeniu klanu. Limit 1000 wydań/konto.
  PTK jest wirtualnym plikiem wskazującym artefakt, bez launchera i narzutu aplikacji.
- Cena PTK: domyślnie 25 HC, dodatnia do 100 HC, zero bezpłatne. Wszystkie
  templatki bez rodzica PvP wspierają jawne zero / Open Source. Pusta cena zachowuje
  dotychczasową politykę. Rodziny PvP z rodzicem zachowują minima.
- `glab_price_policy=1` dotyczy nowych publikowanych buildów; nie zmieniamy cen
  historycznych ofert ani receiptów. Istniejący produkt wymaga zapisania zmian,
  kompilacji i publikacji nowej wersji, żeby przejść na bezpłatną cenę.
- Wycofanie nie usuwa `player_apps`, plików narzędzi ani opublikowanych buildów.
  Runtime rozwiązuje zakupiony artefakt z historii. Firmware zachowuje opłaconą próbę;
  podróż z biletu jest jednorazowym wykonanym świadczeniem. Opublikowanego projektu
  nie można usunąć z archiwum; Danger pozwala usunąć nieopublikowany szkic.

Nowe listy `.lab`, pobranie/odczyt PTK, zakup, autoryzacja klanu i uruchomienie
narzędzia GLab przez terminal nie czytają ciężkiego profilu. Wejście do FM pobiera
kanoniczne narzędzia i storage. Starsze katalogi gameplayowe/kreatorskie pobierają
dotychczasowy profil dopiero po ich wybraniu; ich migracja nie należy do 146.5.

## Wdrożenie

1. Zrób spójny backup SQLite zgodnie z istniejącą procedurą backupu (uwzględnij WAL).
2. Przed aktywacją wykonaj raport tylko do odczytu:

   ```bash
   python tools/audit_ghostlab_completion.py --db data/game.sqlite3
   ```

   Raport podaje zaległe migracje GLaba, duplikaty nazw w ekwipunku i historyczne
   ceny zero wymagające nowej publikacji. Nie przemianowuje produktów ani nie zmienia
   cen. Lokalna archiwalna baza 30 IX miała zaległe migracje i duplikaty testowych
   aplikacji kreatorskich; nie jest dowodem stanu produkcji.
3. Jeśli raport wskazuje zaległą migrację projektu, użyj istniejącego narzędzia
   dla jawnie wybranych kont: najpierw dry-run, potem zastosowanie po przeglądzie:

   ```bash
   python tools/migrate_ghostlab_projects.py --db data/game.sqlite3 --user LOGIN
   python tools/migrate_ghostlab_projects.py --db data/game.sqlite3 --user LOGIN --apply
   ```

4. `CHAOS_GHOSTLAB_PTK_ENABLED=true` jest dodane do `ecosystem.web.config.js`.
   Dotychczasowa lista `CHAOS_GHOSTLAB_RUNTIME_ACTORS` nadal kontroluje pobrania.
   Restart: `pm2 startOrRestart ecosystem.web.config.js --update-env`.
5. Tabela `ghostlab_document_copies` i indeks powstają przy starcie; `.lab` nie wymaga
   kopiowania projektów do profili. Odśwież przeglądarkę, aby pobrać nowy terminal.js.

Wycofanie wdrożenia: wyłącz flagę PTK, zachowaj bazę z receiptami i artefaktami.
Nie usuwaj tabeli ani nie przywracaj starej bazy po zakupach — utraciłoby to nabyte
wydania i rozliczenia. Cofnięcie kodu nie powinno naruszać wcześniej kupionych aplikacji.

## Odbiór w grze

1. FM → GhostLab → `.lab`, rename, ponowne otwarcie, niezapisane zmiany;
   odinstalowanie/reinstalacja GLaba zachowuje ten sam projekt.
2. Każda rodzina uruchamia się przez `run ID`; dwie stare aplikacje o tej samej
   nazwie pokazują wybór ID zamiast uruchamiać pierwszą.
3. PTK globalny oraz klanowy: członek klanu widzi i pobiera; obce konto nie widzi
   oferty i nie pobierze jej bezpośrednim żądaniem. Kontrola po zmianie klanu.
4. PTK płatny na drugim koncie: oba salda, retry, brak środków; bezpłatny: zero
   transferów. Dokument otwiera się w FM na desktop/mobile, HTML pozostaje tekstem.
5. Nowa wersja PTK i wycofanie: stara kopia pozostaje czytelna. Wycofaj po jednej
   zainstalowanej aplikacji każdej rodziny; posiadacz nadal ją uruchamia, nowy zakup
   jest zablokowany. Limity runtime, cooldowny i zużycie nadal obowiązują.
6. Zero/blank/dodatnia cena w niezależnych templatkach; minima potomków PvP bez zmian.

Zakup po konfiskacie ma regresję automatyczną, ale nadal czeka na osobny PASS
gameplayowy autora. Nie zamykać go przy okazji tego sprintu.
