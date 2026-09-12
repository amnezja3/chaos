# Załącznik do `140.stylization.1+`
## GhostSignal Show — system layoutu, responsywności i polityka assetów

**Status:** `DESIGN CONTRACT / ATTACHMENT`  
**Powiązanie:** `140.stylization.1+ — stylizacja całego GhostSignal show`  
**Zakres:** wszystkie template’y `.1–.9` oraz montaż `.10`  
**Cel:** ustalić jeden spójny system kompozycji dla desktopu i urządzeń mobilnych oraz ograniczyć liczbę nowych assetów do absolutnego minimum.

---

## 1. Zasada nadrzędna

GhostSignal Show nie jest zbiorem statycznych slajdów ani zestawem osobnych ekranów projektowanych niezależnie.

Całość działa jako **jeden system prezentacyjny**, w którym:

- layout i oprawę buduje głównie CSS,
- dane pochodzą z istniejących projekcji i runtime CHAOS,
- hero wykorzystują przede wszystkim istniejące assety gry,
- nowy asset przygotowywany specjalnie do sceny powinien być z zasady ograniczony do **tła sceny**,
- ta sama scena musi być czytelna i atrakcyjna zarówno na pełnym desktopie, jak i na wąskim pionowym ekranie telefonu,
- zmiana formatu nie może oznaczać prostego zmniejszenia desktopu ani jego brutalnego cropowania.

Show ma zachować ten sam język wizualny w obu orientacjach, ale może zmieniać kolejność, wielkość i położenie elementów.

---

# 2. Paleta systemowa

## 2.1. Kolory neutralne

Neutralne sceny GhostSignal korzystają głównie z:

- czerni,
- grafitu,
- szarości,
- przygaszonej bieli,
- hakerskiej zieleni.

Zieleń jest kolorem systemowym / technicznym i może oznaczać m.in.:

- aktywny proces,
- poprawny stan,
- transmisję systemową,
- terminal,
- potwierdzony sygnał,
- dane runtime.

Neutralna część show **nie korzysta z żółtego jako domyślnego akcentu**.

## 2.2. Kolory klanowe

Kolor klanu pojawia się dopiero wtedy, gdy scena, obiekt, część, maszyna, ranking lub informacja faktycznie dotyczy danego klanu.

| Klan | Kolor |
| --- | --- |
| Echo Libertas / Echo Wolności | żółty |
| Virex | czerwony |
| Siatka Widmo | turkus |
| Strażnicy Ładu | niebieski |

Kolor klanowy może sterować:

- glow,
- obrysem,
- liniami połączeń,
- wyróżnieniem CTA,
- stanem aktywnego elementu,
- światłem maszyny,
- detalami wykresu,
- aktywnym rekordem listy.

Nie powinien automatycznie zmieniać całego tła sceny.

---

# 3. Polityka assetów

## 3.1. Assety istniejące w grze

Show powinien w pierwszej kolejności wykorzystywać istniejące assety CHAOS:

- części maszyn,
- kompletne maszyny,
- avatary graczy,
- emblematy / symbole klanów,
- istniejące ikony systemowe,
- video GhostSignal,
- muzykę GhostSignal,
- istniejące dane / publikacje / rekordy,
- materiały dostępne już w aplikacjach i systemie gry.

Te zasoby są traktowane jako **systemowe assety gry**, a nie jako nowe assety show.

## 3.2. Nowe assety

Dla konkretnej sceny lista nowych wymaganych assetów powinna domyślnie zawierać tylko:

> **BACKGROUND / SCENE BACKGROUND**

Pozostałe elementy wizualne mają być budowane przez:

- CSS,
- HTML,
- SVG generowane przez frontend,
- maski,
- gradienty,
- linie,
- ramki,
- pseudo-elementy,
- clipping,
- blend modes,
- blur,
- grain,
- halftone,
- scanlines,
- glitch,
- typografię,
- istniejące assety gry.

## 3.3. Zasada reuse

Nie zakładamy automatycznie osobnego tła dla każdej z 49 scen.

Preferowana kolejność:

1. istniejące tło może zostać ponownie użyte,
2. jedno tło może obsłużyć kilka scen jednego template’u,
3. wariant może powstać przez CSS,
4. dopiero gdy kompozycja tego wymaga, przygotowujemy nowe tło.

Celem jest **maksymalna różnorodność scen przy minimalnej liczbie plików graficznych**.

---

# 4. System responsywny

## 4.1. Dwa referencyjne canvas’y

Projektujemy równolegle dla dwóch bazowych układów:

### Desktop
`1920 × 1080`

### Mobile / portrait
`1080 × 1920`

Nie oznacza to dwóch niezależnych projektów. Oba warianty korzystają z tych samych:

- danych,
- assetów,
- hierarchii informacji,
- języka wizualnego,
- stanów scen.

Zmienia się kompozycja.

---

# 5. Zasada reflow zamiast scale

Na desktopie scena może działać horyzontalnie:

`informacja → hero → parametry`

Na mobile ten sam układ przechodzi np. w:

`CTA → hero → główne dane → szczegóły → micro-log`

Nie skalujemy całego desktopowego ekranu do szerokości telefonu.

Elementy powinny mieć:

- odrębne reguły pozycji,
- limity `min/max`,
- niezależne font-size,
- kontrolowane `aspect-ratio`,
- osobne reguły kolejności.

---

# 6. Warstwy wspólne

Każda scena może korzystać z następujących logicznych warstw:

1. `scene-background`
2. `dark-overlay`
3. `texture-layer`
4. `system-grid`
5. `accent-geometry`
6. `hero-layer`
7. `primary-message`
8. `secondary-data`
9. `micro-data`
10. `show-progress`
11. `show-time`
12. `system-tag`

Warstwy 2–12 powinny być w większości tworzone przez CSS i runtime.

---

# 7. Stałe elementy desktopu

Bazowy canvas: `1920 × 1080`.

## 7.1. Stałe strefy

| Strefa | Referencyjny obszar |
| --- | --- |
| safe margin | ok. 60 px |
| lewa strefa komunikatu | `60,55 → 620,955` |
| centralna strefa hero | `560,35 → 1400,935` |
| prawa strefa danych | `1390,55 → 1860,905` |
| dolna strefa pomocnicza | `620,905 → 1410,1015` |
| progress | `1450,1012 → 1810,1016` |
| timer | okolice `1450,1026` |
| system tag | okolice `60,1010` |

To są strefy referencyjne, a nie obowiązkowe ramki.

CTA i hero mogą z nich wychodzić.

---

# 8. Stałe elementy mobile

Bazowy canvas: `1080 × 1920`.

## 8.1. Safe area

Minimalny wizualny margines:

- poziomo: `48–64 px`,
- pionowo: zależnie od systemowych insetów urządzenia.

## 8.2. Domyślne strefy

| Strefa | Referencyjny obszar |
| --- | --- |
| CTA / heading | `60,100 → 1020,390` |
| hero | `70,360 → 1010,1160` |
| główne dane | `60,1170 → 1020,1540` |
| micro-data | `60,1540 → 1020,1770` |
| progress | `660,1820 → 1000,1824` |
| timer | okolice `660,1840` |
| system tag | `60,1825 → 500,1870` |

W scenach, gdzie hero jest tekstem, strefa hero może zostać przejęta przez typografię.

W scenach z maszyną, mapą lub video hero dostaje pierwszeństwo nad panelami danych.

---

# 9. Progress i czas

Progress show jest jednym z nielicznych elementów, które powinny pozostawać konsekwentne przez cały spektakl.

Na desktopie i mobile:

- ten sam styl,
- ta sama relacja do dolnej krawędzi,
- ten sam sposób animacji,
- subtelny charakter,
- brak konkurowania z hero.

Progress nie powinien być kolorowany klanowo.

Kolor neutralny:

- szarość,
- przygaszona zieleń,
- biel o niskiej jasności.

---

# 10. Typografia

Typografia ma działać jak element plakatu.

Hierarchia:

### Level A — Hero CTA
Największy element tekstowy sceny.

### Level B — Scene title
Nazwa systemu, maszyny, procesu lub etapu.

### Level C — Primary data
Najważniejsze liczby, aliasy, rankingi, status.

### Level D — Secondary data
Krótkie dane opisowe.

### Level E — Micro-data
Logi, identyfikatory, timestampy, techniczne śmieci wizualne.

Micro-data nie muszą być w całości czytelne. Ich funkcją jest również budowanie atmosfery.

Na mobile Level E może być mocniej redukowany.

---

# 11. Ruch i różnorodność

Różnorodność nie powinna wynikać z tworzenia nowych assetów.

Powinna wynikać przede wszystkim z:

- zmiany pozycji CTA,
- zmiany strony hero,
- zmiany skali hero,
- wejść i wyjść,
- focusu,
- przejścia od pełnego obiektu do detalu,
- zmiany aktywnego koloru klanowego,
- odsłaniania kolejnych warstw,
- zmian stanu,
- ruchu linii,
- animacji tekstu,
- światła,
- CSS geometry.

W kolejnych scenach duży komunikat może przechodzić między:

- lewy górny,
- prawy górny,
- lewy środek,
- prawy środek,
- lewy dół,
- prawy dół,
- środek,
- pozycję nałożoną częściowo na hero.

Na mobile pozycje są redukowane do logicznego pionowego rytmu, ale różnorodność zachowujemy przez alignment, skalę, asymetrię i relację tekstu z hero.

---

# 12. Template `.1` — przejęcie i stan interfejsu

Sceny:

- `takeover`
- `network_layer`
- `system_layers`
- `desktop_assembly`
- `system_ready`
- `shutdown`
- `restart`

## Hero

Hero stanowią:

- komunikat,
- fragmenty systemu,
- logi,
- elementy desktopu,
- istniejące ikony systemowe.

Nie wymaga osobnego hero assetu.

## Desktop

Dominują duże komunikaty oraz asymetryczne warstwy systemu.

CTA może zajmować nawet 40–55% szerokości sceny.

## Mobile

Domyślna kolejność:

1. CTA,
2. stan systemu,
3. warstwy / log,
4. drobne informacje.

## Nowe assety

**Tylko tło sceny / grupy scen.**

---

# 13. Template `.2` — katalog i historia części

Sceny:

- `parts_enter`
- `parts_complete`
- `history_logs`
- `part_states`

## Hero

Istniejące assety 20 części GhostNetwork.

## Desktop

Stała logiczna pozycja 20 slotów.

Zmienia się:

- aktywność,
- skala,
- opacity,
- glow,
- stan,
- linie,
- opisy.

## Mobile

Siatka przechodzi w:

- mniejszą siatkę,
- kolumny,
- grupy,
- albo sekwencyjne odsłanianie.

Nie próbujemy utrzymać desktopowych 20 elementów w jednym poziomym układzie.

## Nowe assety

**Tylko tło.**

---

# 14. Template `.3` — sieć i połączenia

Sceny:

- `connections`
- `network_expand`
- `network_ring`
- `network_tension`
- `network_ready`

## Hero

Hero jest generowane przez CSS/SVG:

- węzły,
- ringi,
- linie,
- impulsy,
- stany części.

## Desktop

Topologia ma jedną stałą przestrzeń logiczną.

Kolejne sceny zmieniają jej stan, nie tworzą nowej przypadkowej sieci.

## Mobile

Topologia zostaje przeskalowana i uproszczona.

Węzły mogą mieć mniej opisów jednocześnie.

Micro-data może być ukryte lub przeniesione pod sieć.

## Nowe assety

**Tylko tło.**

---

# 15. Template `.4` — maszyny

Sceny:

- `machine_groups`
- `machine_group_1`
- `machine_group_2`
- `machine_group_3`
- `machine_group_4`
- `machine_hero_1`
- `machine_hero_2`
- `machine_hero_3`
- `machine_hero_4`

## Hero

Istniejące assety:

- 4 maszyny,
- 20 części,
- symbole klanów.

## Desktop

Maszyna może osiągać około `70–78%` wysokości ekranu.

Układ referencyjny:

- nazwa / CTA po jednej stronie,
- hero centralnie lub asymetrycznie,
- dane techniczne jako druga warstwa,
- grupa pięciu części jako element pomocniczy.

Każda z czterech prezentacji maszyn ma inną kompozycję.

Nie robimy czterech identycznych ekranów z podmienionym PNG.

## Mobile

Maszyna jest dominującym pionowym hero.

Dane techniczne schodzą pod asset.

Elementy opisowe nie mogą pomniejszyć maszyny do roli miniatury.

## Kolor

Akcent klanowy zgodny z właścicielem maszyny.

## Nowe assety

**Tylko tło.**

---

# 16. Template `.5` — transmisja

Sceny:

- `transmission_quiet`
- `transmission_video`
- `transmission_replay`
- `signal_point`

## Hero

Istniejące video GhostSignal oraz CSS.

Video zachowuje kontrakt proporcji `3:2` i maksymalne pole `720 × 480` na desktopie.

## Desktop

Film nie przechodzi do fullscreen.

Oprawa jest budowana przez CSS:

- ramkę,
- timecode,
- scanlines,
- zakłócenia,
- opis transmisji,
- telemetrykę.

## Mobile

Video zachowuje proporcje.

Może zajmować niemal pełną szerokość content area, ale bez utraty proporcji i bez sztucznego rozciągnięcia.

Dane transmisji przechodzą pod video.

## Nowe assety

**Tylko tło.**

Video jest istniejącym assetem systemowym.

---

# 17. Template `.6` — terminal i komunikaty systemowe

Sceny:

- `terminal_2108`
- `signal_confirmation`
- `pro_tools`
- `file_system`

## Hero

Tekst, terminal, dane runtime i istniejące ikony.

## Desktop

Terminal nie jest klasycznym oknem z ramką.

Ma być częścią całej kompozycji ekranu.

## Mobile

Linie terminala:

- mogą być krótsze,
- mogą zawijać się kontrolowanie,
- mogą mieć mniej kolumn,
- nie mogą wymagać poziomego scrolla.

`signal_confirmation` może przejąć prawie cały viewport jednym wielkim komunikatem.

## Nowe assety

**Tylko tło.**

---

# 18. Template `.7` — mapa i rozliczenie świata

Sceny:

- `aftershock`
- `world_before`
- `territory_outcomes`
- `territory_reduction`
- `conflict_results`
- `world_final`

## Hero

Dostępna reprezentacja świata / mapy oraz dane systemowe.

Nie tworzymy brakującej geometrii tylko dla efektu wizualnego.

## Desktop

Mapa / reprezentacja świata jest centrum sceny.

Panele stanu pozostają wtórne.

## Mobile

Mapa nie może zostać ściśnięta pomiędzy dwa duże panele.

Domyślna kolejność:

1. CTA,
2. mapa / świat,
3. settlement status,
4. legenda / log.

## Nowe assety

**Tylko tło**, jeśli tło jest w ogóle potrzebne.

Jeżeli mapa sama wypełnia przestrzeń sceny, można całkowicie zrezygnować z dodatkowego background assetu.

---

# 19. Template `.8` — wyniki i uczestnicy

Sceny:

- `reward_ledger`
- `players`
- `achievements`
- `clans`
- `player_ranking`
- `clan_ranking`
- `cycle_statistics`

## Hero

Dane runtime oraz istniejące:

- avatary,
- symbole klanów,
- aliasy,
- rekordy wyników.

## Desktop

Najważniejsza liczba lub rekord powinny być traktowane plakatowo.

Listy są warstwą wtórną.

## Mobile

Najważniejsze rekordy dostają osobne duże bloki.

Pełna lista może być wizualnie skrócona w obrębie sceny, o ile nie zmienia to danych prezentowanych przez scenariusz.

Nie budujemy desktopowej szerokiej tabeli pomniejszonej do telefonu.

## Nowe assety

**Tylko tło.**

---

# 20. Template `.9` — publikacje i archiwum

Sceny:

- `googleplex`
- `blacknet_history`
- `archive`

## Hero

Treści już istniejące w systemie.

## Desktop

Materiał wygląda jak przechwycona publikacja / zapis, nie jak zwykły screenshot aplikacji.

## Mobile

Publikacja przechodzi w pionową formę:

1. źródło,
2. główny fragment,
3. metryka,
4. identyfikator archiwum.

## Nowe assety

**Tylko tło.**

---

# 21. Template `.10` — montaż całości

`.10` nie wprowadza nowego języka wizualnego ani nowych assetów.

Jego zadaniem jest:

- połączenie zatwierdzonych template’ów,
- wyrównanie rytmu,
- sprawdzenie desktop/mobile,
- sprawdzenie audio,
- sprawdzenie przejść,
- sprawdzenie seek/recovery,
- usunięcie przypadkowych różnic,
- kontrola liczby i pamięci assetów.

Nowe assety w `.10` powinny być wyjątkiem wymagającym osobnej decyzji.

---

# 22. Macierz wymaganych nowych assetów

| Grupa | Nowy asset obowiązkowy | Pozostałe źródła |
| --- | --- | --- |
| `.1 Interfejs` | background | CSS + UI CHAOS |
| `.2 Części` | background | 20 części + CSS |
| `.3 Sieć` | background | CSS/SVG + części |
| `.4 Maszyny` | background | maszyny + części + symbole klanów |
| `.5 Transmisja` | background | video + CSS |
| `.6 Terminal` | background | dane runtime + CSS |
| `.7 Świat` | background opcjonalny | mapa / dane świata + CSS |
| `.8 Wyniki` | background | avatary + symbole + dane |
| `.9 Archiwum` | background | publikacje / dane + CSS |
| `.10 Montaż` | brak | przyjęte template’y |

To jest **górny limit oczekiwań**, nie minimalna liczba plików. Jeżeli jedno tło działa dla kilku scen lub całego template’u, należy je ponownie wykorzystać.

---

# 23. Co powinien generować CSS

Bez nowych bitmap frontend powinien umieć tworzyć:

- ramki techniczne,
- narożniki,
- linie celownicze,
- grid,
- rastry,
- separatory,
- pionowe indeksy,
- ringi,
- wykresy prostych parametrów,
- paski,
- markery,
- labels,
- pointers E1–E5,
- timecode,
- progress,
- logi,
- paski transmisji,
- glitch,
- scanline,
- noise,
- halftone,
- przyciemnienia,
- gradienty,
- clan glow,
- status glow,
- pseudo-wykresy,
- tło tekstowe / micro-data.

Dzięki temu zmiana kompozycji nie wymaga produkcji kolejnego zestawu grafik.

---

# 24. Reguła hero

Każda scena ma jeden wizualny priorytet.

Hero może być:

- maszyną,
- częścią,
- grupą części,
- siecią,
- mapą,
- video,
- avatarem,
- rankingiem,
- wielką liczbą,
- komunikatem tekstowym.

Jeżeli wszystko wygląda jak hero, scena nie ma hierarchii.

---

# 25. Reguła backgroundu

Tło sceny:

- buduje świat,
- ustala nastrój,
- może zawierać architekturę / przestrzeń / teksturę,
- nie powinno zawierać danych, które runtime musi aktualizować,
- nie powinno zawierać napisów, które później mają być zmieniane,
- nie powinno zawierać ramek interfejsu możliwych do wykonania CSS-em,
- powinno tolerować zmianę proporcji i crop między desktopem a mobile.

Najlepiej projektować je z:

- ważnym detalem poza skrajnymi krawędziami,
- ciemniejszą przestrzenią pod tekst,
- neutralnym środkiem pozwalającym na różne położenia hero.

---

# 26. Mobile — dodatkowe ograniczenia

Na pionowym ekranie:

- nie używamy mikrofontów wymagających zoomu,
- nie budujemy sześciu równorzędnych paneli,
- nie zachowujemy tabel szerokich jak desktop,
- nie blokujemy hero dużą liczbą ramek,
- nie wymagamy landscape,
- CTA powinno być czytelne bez przewijania,
- najważniejszy stan sceny powinien być zrozumiały w ciągu kilku sekund.

Elementy dekoracyjne mogą zostać ograniczone, jeśli zwiększa to czytelność.

---

# 27. Desktop — dodatkowe zasady

Desktop wykorzystuje szerokość do budowania napięcia i asymetrii.

Nie oznacza to obowiązku wypełnienia całego ekranu.

Duże obszary czerni są dozwolone i pożądane, jeżeli:

- budują rytm,
- eksponują hero,
- poprawiają czytelność,
- przygotowują następną scenę.

---

# 28. Reduced motion

Każda scena musi mieć stan reprezentacyjny niezależny od animacji.

Przy `prefers-reduced-motion`:

- hero pozostaje widoczne,
- CTA pozostaje widoczne,
- dane pozostają czytelne,
- animowane linie mogą zostać zastąpione stanem statycznym,
- glitch nie jest wymagany,
- puls może zostać zredukowany,
- przejścia mogą zostać skrócone.

Animacja nie może być jedynym nośnikiem znaczenia.

---

# 29. Recovery / seek

Po wejściu w środek sceny przez seek lub reconnect:

- layout musi odtworzyć właściwy stan,
- części muszą znajdować się we właściwym statusie,
- sieć musi odpowiadać bieżącemu etapowi,
- hero nie może zależeć od obejrzenia poprzedniej animacji,
- CSS powinien umieć odtworzyć stan końcowy lub pośredni na podstawie czasu sceny.

---

# 30. Kryteria odbioru wspólnego systemu

System stylizacji jest zaakceptowany, gdy:

1. Każdy template działa na `1920×1080`.
2. Każdy template działa na `1080×1920`.
3. Mobile nie jest mechanicznym pomniejszeniem desktopu.
4. CTA pozostaje czytelne w obu wariantach.
5. Hero pozostaje najważniejszym elementem sceny.
6. Neutralne sceny nie używają koloru żadnego klanu jako domyślnego motywu.
7. Kolory klanowe są semantyczne.
8. Progress zachowuje stałe położenie i styl.
9. CSS odpowiada za większość oprawy.
10. Sceny ponownie wykorzystują istniejące assety CHAOS.
11. Nowy asset sceny jest zasadniczo ograniczony do backgroundu.
12. Backgroundy są ponownie wykorzystywane tam, gdzie ma to sens.
13. Brak assetu ma jawny fallback.
14. Reduced motion zachowuje informację.
15. Seek/reconnect odtwarza poprawny stan.
16. Styl nie pogarsza wydajności ani czasu ładowania show.

---

# 31. Zasada produkcyjna

Przy projektowaniu każdej kolejnej sceny pytamy w tej kolejności:

1. **Co jest hero tej sceny?**
2. **Który istniejący asset CHAOS możemy wykorzystać?**
3. **Co możemy zbudować CSS-em?**
4. **Czy możemy ponownie wykorzystać istniejące tło?**
5. **Dopiero na końcu: czy naprawdę potrzebujemy nowego background assetu?**

Jeżeli scena wymaga nowej grafiki poza tłem, powinno to być traktowane jako wyjątek i świadoma decyzja, a nie domyślny sposób projektowania show.

---

## Decyzja projektowa

GhostSignal Show ma wyglądać jak duża, żyjąca transmisja przejmująca interfejs CHAOS, a nie jak kolekcja prerenderowanych plansz.

**Assety gry dostarczają świata. CSS dostarcza języka wizualnego. Background dostarcza atmosfery. Runtime dostarcza prawdy.**
