# Consequences Show — assety PNG

Miejsce na grafiki autora do efektów mapowych konsekwencji, sprint **143.5a**.
Zapisuj gotowe PNG bezpośrednio w tym katalogu. Na tym etapie przygotowano
kontrakt plików; wrzucenie obrazów nie uruchamia jeszcze show w grze.

Ścieżka repozytorium: `static/images/consequences/show/`.
Ścieżka HTTP: `/static/images/consequences/show/<nazwa_pliku>.png`.

Dźwięki MP3 mają te same nazwy bazowe i osobny katalog
`static/audio/sfx/consequences/`. [README SFX](../../../audio/sfx/consequences/README.md)
opisuje wszystkie dziewięć plików, charakter dźwięku i zalecane długości.
Aktualny komplet i pomiary: [audyt 23 IX 2026](../../../../doc/runbooks/sprint_143_5a_asset_audit.md).

## Nazwy i przypisanie

Każdy stopień konsekwencji ma osobny obraz. Numery 01–09 to stopnie kary,
nie poziomy incydentu L1–L5. Zachowaj dokładnie nazwy: małe litery,
podkreślenia, bez spacji i polskich znaków.

| Stopień | Nazwa pliku | Motyw show / przyznana konsekwencja |
|---|---|---|
| 1 | `consequence_01_fine.png` | Mandat ×1 |
| 2 | `consequence_02_fine.png` | Wyższy mandat ×2 |
| 3 | `consequence_03_confiscation.png` | Konfiskata jednego narzędzia |
| 4 | `consequence_04_confiscation.png` | Konfiskata dwóch narzędzi |
| 5 | `consequence_05_confiscation_fine.png` | Konfiskata trzech narzędzi i mandat ×3 |
| 6 | `consequence_06_detention.png` | Wniosek sądu o areszt — obecnie 5 minut online |
| 7 | `consequence_07_detention.png` | Wniosek sądu o areszt — obecnie 10 minut online |
| 8 | `consequence_08_detention.png` | Wniosek sądu o areszt — obecnie 15 minut online |
| 9 | `consequence_09_detention.png` | Wniosek sądu o areszt — obecnie 20 minut online |

Docelowa zawartość:

```text
README.md
consequence_01_fine.png
consequence_02_fine.png
consequence_03_confiscation.png
consequence_04_confiscation.png
consequence_05_confiscation_fine.png
consequence_06_detention.png
consequence_07_detention.png
consequence_08_detention.png
consequence_09_detention.png
```

## Przygotowanie grafiki

- Format PNG, przestrzeń barw sRGB, przezroczystość alpha dla grafiki nakładanej na mapę.
- Zalecany wspólny format roboczy: **1024×1024 px**, centralny symbol/emblemat.
  To rekomendacja dla nowych grafik, nie ograniczenie silnika. Jeżeli gotowe
  materiały mają inne proporcje, zachowaj oryginał i dopisz rozmiary tutaj.
- Zostaw około 10% marginesu wokół ważnego motywu, aby skalowanie na telefonie
  nie obcinało ilustracji. Unikaj bardzo drobnych szczegółów i małych napisów.
- Styl CHAOS, zgodny z Secret Path i Super Powers. Referencje PNG Super Powers:
  [static/images/ghostnetwork/superpower](../../ghostnetwork/superpower/).
- PNG przedstawia motyw kary. Nagłówek, opis, kwota HC, nazwy/liczba narzędzi,
  czas aresztu i kaucja będą nakładane przez renderer na podstawie backendu.
  **Nie wypalaj tych zmiennych danych w obrazie**, również „5 min” itp.
- Animacje glitch/pulse, ramki i przejścia będą adaptowane z istniejących show.
  Nie trzeba dostarczać klatek animacji ani wariantów mobile/desktop.
- Jeden gotowy plik na stopień; wersje robocze trzymaj poza tym katalogiem.
  Nie twórz pustych plików PNG jako placeholderów.

## Kontrakt uruchomienia — do implementacji w 143.5a

- **Ciemne tło z alpha 60%**, np. `background: rgba(0, 0, 0, 0.6)`.
  Mapa pozostaje widoczna przez tło (40% przepuszczalności). To krycie
  osobnej warstwy tła, nie `opacity: 0.6` całego show: PNG i tekst zachowują
  własną alpha oraz pełną czytelność. Nie wypalać tła w PNG.
- **Czas show = rzeczywisty czas przypisanego SFX**. Obraz i audio mają
  wspólny start; wszystkie animacje wejścia/wyjścia mieszczą się w długości
  dźwięku. Bez dodatkowego hold, dolnego limitu czasu, zapętlania i ucinania
  dłuższych SFX. Źródłem czasu jest zdekodowane audio w GameSfx.
- Przy wyciszeniu/blokadzie autoplay zachować długość właściwego MP3,
  korzystając z metadanych, a przy błędzie ładowania z zapisanej długości
  tego assetu. Nie odtwarzać dźwięku później ani nie przedłużać show.
- Dostarczony komplet ma **540×540 px**, nie 1024×1024. Zachować proporcje;
  preferować wyświetlanie do 540 px szerokości, z dopasowaniem do telefonu.
  Ładować potrzebną parę PNG/SFX, nie wszystkie dziewięć obrazów przy wejściu
  na mapę. Obecna waga nie wymaga zmiany plików ani stratnej optymalizacji.

Renderer wybiera obraz po stopniu faktycznie wykonanej kary i uruchamia go
po potwierdzeniu commit, dla ukaranego gracza. Retry/reconnect nie odtwarzają
ponownie tej samej kary. Wariant „wniosek sądu o areszt” jest oprawą zdarzenia,
nie nową procedurą zatwierdzania ani dodatkowym losowaniem.

Brak PNG nie blokuje kary ani komunikatu systemowego. Przed podłączeniem
renderer sprawdzi obecność assetów; nie należy zakładać, że wszystkie pliki
istnieją tylko dlatego, że zostały wymienione w README.

Zakres i kryteria odbioru: [Sprint 143, punkt 143.5a](../../../../doc/sprints/sprint_143_response_consequences_expansion.md).
