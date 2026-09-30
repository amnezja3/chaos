# Sprint 146.5 — domknięcie GhostLab 1.0

Status: **PAKIET DO ODBIORU**, przygotowany i sprawdzony lokalnie 30 IX 2026.
Pakiet i scenariusz odbioru: [runbook 146.5](../runbooks/sprint_146_5_ghostlab_completion.md).
Nie oznacza wdrożenia produkcyjnego ani PASS gameplayowego.

Doprecyzowania autora: PTK można publikować globalnie lub tylko dla swojego klanu.
Wycofanie dowolnej aplikacji ze sprzedaży zachowuje wszystkie zainstalowane kopie.
Kopie PTK pozostają czytelne również po wycofaniu oferty i zmianie klanu czytelnika.
Przyjęte ceny PTK: domyślnie 25 HC, maksymalnie 100 HC, jawne 0 = Open Source.

Kolejność: **146.4 PASS → 146.5 → 147 → 148 → GhostLab v2.0 (149–152)**.
Jeden sprint, kolejne etapy odbioru. Kreatory aplikacji zaczynają się dopiero
po domknięciu ścieżki GhostLab ↔ File Manager ↔ terminal.

## Rezultat i fundament

Gracz otwiera projekt `.lab` z własnego katalogu GhostLaba, edytuje go w GLabie,
publikuje produkt w Googleplexie, a odbiorca pobiera dokument `.ptk` do FM albo
instaluje narzędzie dostępne również z terminala. Każda droga otwarcia korzysta
z tej samej tożsamości projektu/produktu, zainstalowanej wersji i uprawnień.

Obowiązuje [zero ciężkiego profilu](../plans/creator_ghostlab_zero_heavy_profile_contract.md):
małe projekcje list, wydzielone dane projektów i treści dokumentów, canonical
inventory/wallet, ograniczone payloady i delta aktualizacji. Treści MD ani kopii
projektów nie dopisywać do `profile.files.projects` lub pełnego profilu gracza.

Wstępne ustalenia z kodu: FM ma czytnik Markdown i systemowe dokumenty
`static/files/about/chaos.ptk` oraz `static/files/tips-tricks/blacknet.ptk`.
Obecny katalog `projects` obsługuje projekty kreatorów z akcją „Wycofaj”;
nie wolno automatycznie przenieść jej na projekty GLaba. Branding rozróżnia
`suggested_price=None` i liczbę 0, ale np. publiczna oferta biletu wymusza
minimum 5 HC. Sam formularz ceny nie wystarczy do wdrożenia darmowych produktów.
Pełny audyt nazw, komend i ścieżek otwierania jest zadaniem etapu 1, nie gotowym wynikiem.

## 1. Audyt i kontrakt integracji

- Zestawić wszystkie rodziny GLaba: projekt, build, publikacja, zakup/pobranie,
  instalacja, plik FM, uruchomienie z pulpitu/PvP/terminala, aktualizacja,
  wycofanie i usunięcie. Wskazać brakujące oraz rozbieżne drogi.
- Sprawdzić tworzenie, zmianę nazwy, kompilację i publikację pod kątem kolizji
  nazw u jednego autora, między autorami oraz z komendami i narzędziami systemu.
  Zweryfikować faktyczną normalizację terminala (wielkość liter, spacje, Unicode).
- Raport zawiera przykłady istniejących konfliktów i dry-run migracji;
  bez cichego przemianowania lub usunięcia kupionych produktów.
- Roboczy kontrakt: trwałe ID jest tożsamością, nazwa jest prezentacją, a alias
  komendy jest jednoznaczny w ekwipunku użytkownika. Nazwa nie może przejmować
  komendy systemowej. Przy kolizji wymagany jawny wybór albo deterministyczny
  alias pokazany w FM, produkcie i pomocy terminala; nigdy pierwszy wynik `find`.
  Wynik audytu: publikacje nadal wymagają unikalnej nazwy w Googleplexie;
  drafty mogą mieć powtórzone nazwy i odrębne ID. Komendy systemowe są zastrzeżone,
  stare kolizje w instalacjach rozstrzyga jawne `run ID`, bez przemianowywania kopii.

## 2. File Manager ↔ GhostLab i `.lab`

- Osobny katalog **GhostLab** (technicznie proponowane `ghostlab`) z projektami
  autora jako plikami `<nazwa>.lab`. To projekcja kanonicznych projektów, nie
  druga, niezależnie edytowalna kopia. Każdy wpis zawiera niezmienne `project_id`.
- Kliknięcie `.lab` otwiera konkretny projekt w GhostLabie. Istniejące okno
  jest używane ponownie; niezapisane zmiany mają ochronę przed utratą.
- **Brak zainstalowanego GhostLaba:** plik projektu pozostaje w FM, ale próba
  otwarcia pokazuje „Brak narzędzia GhostLab. Zainstaluj je, aby otworzyć projekt.”
  Bez pustego edytora, automatycznej instalacji ani usunięcia projektu. Ten sam
  warunek obowiązuje przy otwarciu przez terminal i bezpośredni odnośnik;
  ponowna instalacja GhostLaba przywraca możliwość otwierania istniejących `.lab`.
- Tworzenie, zmiana nazwy i usunięcie w GLabie aktualizują FM bez ponownego
  logowania. Identyczne nazwy nie mogą nadpisywać wpisów opartych na ID.
- **Jedyna droga usuwania projektu: strefa Danger w GhostLabie.** FM nie pokazuje
  kasowania ani wycofywania projektu; terminalowe `rm`, ogólne API plików,
  czyszczenie systemu oraz operacje zbiorcze nie mogą obchodzić tej zasady.
- Otwarcie sprawdza własność po stronie serwera. Obcy/usunięty projekt zwraca
  czytelny błąd, bez pustego edytora ani ponownego utworzenia.
- Usunięcie projektu i wycofanie publikacji to osobne decyzje. Sprawdzić ochronę
  istniejących zakupów i niezmiennych artefaktów; usunięcie źródła nie może
  pozbawiać kupującego wcześniej nabytego produktu.

## 3. GhostLab ↔ terminal

- Każde zainstalowane narzędzie GLaba dostaje automatyczne, widoczne wywołanie
  terminalowe. Komenda prowadzi do tego samego launchera co pulpit/FM.
- Zachować warunki rodziny: dostęp PvP i wspólny limit rodzica/potomka, pojedynczy
  aktywny skaner, cooldown i restart firmware, stan aktualizacji/konserwacji,
  areszt, konfiskata i wymagania wersji. Terminal nie omija żadnej blokady.
- Dla produktów wykonywanych przy zakupie (np. biletu) komenda nie realizuje
  drugi raz efektu. Dokument otwiera czytnik, nie executor aplikacji.
- Alias pozostaje związany z ID podczas aktualizacji; rename, odinstalowanie
  i konfiskata nie zostawiają aktywnej starej komendy. Pomoc/autouzupełnianie
  pokazuje tylko aktualne instalacje i jednoznaczne nazwy.

## 4. Nowa templatka: dokument PTK

- Materiały graczy: poradnik, Tips and Tricks, mechaniki, strategia, hipoteza,
  przemyślenia i inne teksty. Nazwa, ikona, opis, kategoria oraz treść Markdown.
  Oznaczenie autora odróżnia publikację gracza od oficjalnej dokumentacji.
- Ścieżka: projekt → zapis → walidacja → podgląd w stylistyce CHAOS → kompilacja
  → publikacja pliku do pobrania w Googleplexie. Bez runtime narzędzia/PvP.
- Ponownie użyć czytnika PTK: bez wykonywania HTML, skryptów i osadzonych akcji;
  zweryfikować escaping, linki, bloki kodu, listy, Unicode i długie teksty.
  Limity rozmiaru i obsługiwany podzbiór MD są jawne w edytorze.
- Zakup/pobranie zapisuje receipt i plik `.ptk` w **Dokumenty** (proponowane
  `documents`) w FM. Powiązanie z publikacją, autorem i konkretną wersją;
  treść nie trafia do publicznego payloadu oferty płatnego dokumentu.
- Kliknięcie pliku otwiera czytnik, także na mobile. Treść pochodzi z kupionej
  wersji; nowa publikacja nie podmienia jej bez jawnej aktualizacji.
- Bezpłatny dokument również wymaga poprawnego pobrania i receipt; ponowienie
  nie duplikuje pliku ani opłaty. Dla płatnego transfer do autora i zapis pliku
  tworzą spójną transakcję; brak środków nie daje dostępu do treści.
- Wycofanie sprzedaży blokuje nowe zakupy, zachowuje dostęp wcześniejszych
  odbiorców. Ponowne pobranie już nabytej wersji nie pobiera HC drugi raz.
- Dokumenty: **25 HC domyślnie, 100 HC maksimum**, jawne 0 bezpłatne.
  Taki balans przyjęto w pakiecie 146.5 po zatwierdzeniu rozpoczęcia sprintu.

## 5. Wspólna cena i Open Source

Zakres: templatki bez nadrzędnego produktu w Googleplexie, w tym PTK, Deep
Scannery, konserwacja/upgrade, firmware oraz inne zakwalifikowane w audycie.
Istnienie technicznego `source_tool_id` samo w sobie nie wyznacza wyjątku.
**Wyjątek: rodziny głównych narzędzi PvP z rodzicem — obecna polityka zostaje.**

| Wartość pola | Efekt |
| --- | --- |
| Puste / `null` | Dotychczasowa domyślna cena danej templatki; PTK ma nową, zatwierdzoną osobno wartość. |
| Dokładnie `0` | Cena końcowa 0 HC i oznaczenie **Open Source**. |
| Dodatnia | Dotychczasowa polityka oraz limity rodziny; PTK według tanich widełek. |
| Ujemna / błędna / nieskończona | Błąd walidacji, bez cichej zamiany na domyślną cenę. |

- Jeden kontrakt dla blueprintu, podglądu/quote, buildu, publikacji, karty sklepu,
  potwierdzenia i backendu pobrania. Nie stosować `price or default` dla zera.
- Karta pokazuje Open Source i „Pobierz bezpłatnie”; zero nie tworzy sztucznego
  transferu ani komunikatu o otrzymaniu HC. Nadal obowiązują uprawnienia,
  cooldowny, limity i obsługa powtórzeń.
- Open Source jest tutaj uzgodnionym oznaczeniem bezpłatności produktu.
  Nie oznacza automatycznego udostępnienia prywatnego `.lab`, nadania licencji
  ani wykonania importu/remiksu planowanego w GLab v2.0.
- Przed wdrożeniem macierz wszystkich templatek i wyjątku PvP; sprawdzić bilety
  również w `ticket_price`/`public_ticket`. Nie zmieniać retrospektywnie
  opublikowanych cen; nowe zasady przez jawną publikację nowej wersji.

## 6. Odbiór, migracja i zamknięcie 1.0

Jeden pakiet wdrożeniowy, runbook z backupem, dry-run i rollbackiem. Projekcja
`.lab` obejmuje dotychczasowe projekty bez duplikowania danych. Raport konfliktów
nazw/aliasów i cen musi poprzedzać aktywację; zachować ID i nabyte wersje.

PASS obejmuje:

1. Projekt nowy i historyczny → `.lab` w FM → właściwy projekt w GLabie;
   rename, istniejące okno, niezapisane zmiany, brak kasowania poza Danger;
   brak GhostLaba → komunikat o braku narzędzia, projekt zachowany;
   ponowna instalacja GhostLaba → otwarcie tego samego projektu.
2. Każda rodzina przez terminal → ten sam produkt i wymagania; kolizje nazw,
   komendy zastrzeżone, aktualizacja, odinstalowanie i konfiskata.
3. PTK darmowe i płatne od innego autora → plik w Dokumentach → odczyt na
   desktop/mobile; oba salda, receipt, retry, brak środków, nowa wersja,
   wycofanie, brak dostępu do cudzego projektu i niekupionej treści.
4. Cena pusta / 0 / dodatnia / błędna we wszystkich objętych rodzinach;
   zgodność kwoty na każdym etapie i brak regresji minimum PvP.
5. Zero-heavy również na błędach i retry; browser testy całej ścieżki FM/GLab/
   Googleplex/terminal, stare PTK systemowe, zachowanie limitów gameplayowych.

Zakup po konfiskacie pozostaje osobnym, oczekującym testem gameplayowym autora
(poprawka i testy automatyczne gotowe). Nie oznaczać go jako PASS przy okazji
zamknięcia Deep Scannerów. Uwzględnić ten przypadek w ogólnej regresji 146.5.

Po PASS: **GhostLab 1.0 zamknięty → 147 i 148 (kreatory) → 149–152 (GLab v2.0)**.
