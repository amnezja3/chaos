# SPRINT 135.4.1.1 — Googleplex Search Presentation Repair

Status: `IN PROGRESS — READY FOR VISUAL VALIDATION`

Baseline rozpoczęcia: `c07b086` (stan sprzed dwóch odrzuconych iteracji
presentation layer: `595f592` i `eb366df`). Cofnięcie obejmuje wyłącznie
`static/js/terminal.js`, `static/css/googleplex_news.css` oraz dwa testy
kontraktu Search. Nie cofa Googleplex News, AGI 2108, bounded purchase/install,
canonical inventory ani backendu wyszukiwania.

Stan implementacji 2026-08-29:

- Etap A: complete — oba odrzucone podejścia cofnięto do baseline;
- Etap B: complete — jeden deterministyczny mapper tworzy paczki
  `1 HERO + 2 MIDDLE + 3 SMALL`;
- Etap C: complete — istniejący canonical icon element jest częścią karty,
  bez ramki, panelu i backgroundu;
- Etap D: implemented — jeden CSS/DOM contract dla fullscreen, start-size i
  mobile; wymaga manualnej akceptacji screenshotów;
- Etap E: complete — pojedynczy wynik ma osobny wariant geometryczny, ale ten
  sam renderer i pełny zestaw danych;
- Etap F: automated complete — przypadki 2/3/4/6/7/12/70, pełny content,
  purchased state, brak per-card requestów i cały frontend JS są zielone.

## Cel

Naprawić regresję prezentacji wyników wyszukiwania Googleplex po przebudowie Home/News.

Sprint **nie zmienia mechaniki gry, backendu wyszukiwania, danych produktów, zakupu, instalacji, inventory ani rankingu**.

Naprawiamy wyłącznie sposób prezentacji istniejących wyników.

Punktem odniesienia jest wcześniejsza, poprawna wersja kart Googleplex:

- pełne opisy pozostają;
- pełne parametry pozostają;
- ceny pozostają;
- liczba pobrań pozostaje;
- stany zakupione/zainstalowane pozostają;
- kolory i istniejące style rodzin pozostają;
- przyciski nadal korzystają z istniejącego flow;
- ikony aplikacji mają zostać **wkomponowane w kartę**, a nie używane jako tło.

Najważniejsza zasada:

```text
NIE PRZEBUDOWUJEMY DANYCH KARTY.
NIE REDUKUJEMY TREŚCI.
NIE TWORZYMY NOWEGO MODELU KARTY.

ISTNIEJĄCA TREŚĆ
+ IKONA APLIKACJI
+ KLASA PREZENTACYJNA
+ GRUPOWANIE W PACZKI
+ RESPONSYWNY UKŁAD
```

## 1. Zakres sprintu

Sprint obejmuje:

1. cofnięcie ostatniej błędnej przebudowy presentation layer wyników;
2. przywrócenie poprawnej zawartości kart;
3. poprawne wkomponowanie ikony aplikacji;
4. jeden spójny renderer dla wyników wyszukiwania;
5. deterministyczny podział wyników na `HERO`, `MIDDLE`, `SMALL`;
6. cykliczne grupowanie wyników w paczki;
7. jednoznaczne zachowanie dla jednego wyniku, kilku wyników, `/all`, fullscreen, start-size i mobile;
8. zachowanie istniejących stanów zakupu/instalacji;
9. regresję wydajnościową, aby Googleplex nie uruchamiał ciężkiego profilu ani zbędnego pełnego refreshu.

## 2. Poza zakresem

Nie zmieniamy:

- backendowej logiki wyszukiwania;
- sposobu filtrowania;
- danych aplikacji;
- opisów;
- parametrów;
- cen;
- liczników pobrań;
- systemu purchase/install/uninstall;
- canonical inventory;
- Googleplex News Home;
- BlackNet;
- Ghost Exchange;
- gameplayu;
- LLM;
- publisherów.

Nie projektujemy nowego katalogu.

## 3. Wyszukiwarka — zachowanie

Wyszukiwarka zachowuje dotychczasową funkcję.

Placeholder:

```text
Szukaj aplikacji...   /all - pokaż wszystkie
```

Tryby:

```text
query = ""
→ Googleplex Home / News

query = "/all"
→ wszystkie aplikacje
→ ranking po liczbie pobrań
→ grupowany layout katalogowy

query = zwykła fraza
→ istniejące wyniki wyszukiwania
→ ten sam renderer produktów
```

Nie istnieją osobne renderery dla różnych fraz.

## 4. Jedyny renderer produktu

Każdy produkt korzysta z tej samej pełnej zawartości danych.

Karta zachowuje wszystko, co miała wcześniej:

```text
nazwa
pełny opis
LVL
Respect
Risk
Poziom
Rodzina
Tryb
Tier
Map
Ops
Data
Waga
Instalacja
Jakość
Niezawodność
Moc twórcy
Moc
Cena sugerowana
rodzina / kategoria
liczba pobrań
cena zakupu
stan zakupu
przycisk
ikona aplikacji
```

Jeżeli konkretne pole w danych nie istnieje, zachowujemy obecne zachowanie `-`.

Nie usuwamy pól dlatego, że karta jest `MIDDLE` albo `SMALL`.

`HERO`, `MIDDLE`, `SMALL` są wyłącznie klasami layoutu CSS.

## 5. Ikona aplikacji — kontrakt

Ikona aplikacji jest częścią kompozycji.

Nie jest:

- background-image;
- tłem karty;
- osobnym panelem;
- osobnym boxem;
- elementem w ramce;
- elementem z dodatkowym prostokątnym backgroundem.

Ikona:

```text
transparentna
bez ramki
bez dodatkowego tła
object-fit: contain
nie przykrywa tekstu
nie leży pod tekstem
nie zmienia danych karty
```

DOM:

```html
<img class="gp-search-product__icon" ...>
```

lub istniejący canonical element ikony.

Nie tworzyć dodatkowego wrappera wizualnego udającego kartę wokół ikony.

## 6. Podstawowa paczka wyników

Wyniki są układane w powtarzalne paczki.

Jedna pełna paczka:

```text
1 × HERO
2 × MIDDLE
3–5 × SMALL
```

Potem następna:

```text
1 × HERO
2 × MIDDLE
3–5 × SMALL
```

I dalej ten sam rytm.

Nie istnieje jeden HERO dla całej listy.

Nie istnieje przełączenie po pierwszej paczce na zwykłą tabelę.

Każda kolejna paczka zaczyna się od kolejnego `HERO`.

## 7. Ranking `/all`

Dla `/all`:

```text
downloads DESC
```

Tie-break:

```text
canonical app_id ASC
```

Ranking jest deterministyczny.

Po rankingu wyniki są dzielone kolejno na paczki prezentacyjne.

Przykład przy paczce 6-elementowej:

```text
1      HERO
2–3    MIDDLE
4–6    SMALL

7      HERO
8–9    MIDDLE
10–12  SMALL

13     HERO
...
```

Jeżeli konfiguracja używa 4 albo 5 `SMALL`, rytm pozostaje identyczny:

```text
1 HERO
2 MIDDLE
N SMALL
repeat
```

Liczba `SMALL` w jednej paczce jest stała dla danego breakpointu.

## 8. Zwykłe wyszukiwanie — jedna zasada

Nie tworzymy specjalnego schematu dla 6 wyników, innego dla 5 i jeszcze innego dla 2.

### 0 wyników

Kontrolowany empty state.

### 1 wynik

**Pełna karta produktu.**

Nie HERO editorial.

Nie ma pustej połowy ekranu.

Ma zawierać:

- ikonę po lewej;
- pełną nazwę;
- pełny opis;
- wszystkie istniejące parametry;
- stan zakupiony/niezakupiony;
- cenę;
- liczbę pobrań;
- duży, czytelny przycisk.

Desktop:

```text
┌──────────────────────────────────────────────┐
│ IKONA │ NAZWA                               │
│       │ pełny opis                          │
│       │ pełne parametry                     │
│       │ cena / downloads                    │
│       │                         DUŻY PRZYCISK│
└──────────────────────────────────────────────┘
```

### 2+ wyników

Używamy dokładnie tego samego mechanizmu paczek.

Przykłady:

```text
2 wyniki:
HERO + MIDDLE

3 wyniki:
HERO + 2×MIDDLE

4 wyniki:
HERO + 2×MIDDLE + 1×SMALL

6 wyników:
HERO + 2×MIDDLE + 3×SMALL
```

Nie przełączamy się na inny renderer.

## 9. HERO — kompozycja

HERO jest największą kartą w paczce, ale nie może być gigantycznym pustym prostokątem.

W HERO:

- ikona po lewej;
- treść obok niej;
- pełny opis;
- pełne parametry;
- cena i pobrania;
- stan zakupu;
- duży przycisk.

Desktop/fullscreen:

```text
┌───────────────────────────────────────┐
│  DUŻA IKONA   NAZWA                   │
│  PO LEWEJ     opis                    │
│               parametry               │
│               parametry               │
│               cena / downloads        │
│                         DUŻY PRZYCISK  │
└───────────────────────────────────────┘
```

Ikona nie może znajdować się w oddzielnej ramce.

Proporcje orientacyjne:

```text
ikona: 25–32% dostępnej szerokości karty
content: pozostała część
```

Treść ma być zwarta.

Nie tworzyć ogromnych pustych obszarów.

## 10. MIDDLE — kompozycja

MIDDLE jest sideboxem paczki.

W MIDDLE:

- ikona po lewej;
- nazwa i opis po prawej;
- pełne parametry pod opisem lub w zwartej kolumnie;
- cena/pobrania;
- standardowy przycisk.

Układ:

```text
┌──────────────────────────────┐
│ IKONA │ NAZWA                │
│       │ opis                 │
│       │ parametry            │
│       │ cena/downloads       │
│       │             PRZYCISK │
└──────────────────────────────┘
```

Ikona:

```text
18–28% szerokości sideboxa
```

Nie może być tłem ani być większa niż blok treści.

## 11. SMALL — kompozycja

SMALL jest kompaktową kartą dolnej części paczki.

W SMALL ikona może być wyśrodkowana.

Układ:

```text
┌──────────────────────────┐
│ NAZWA                    │
│ opis                     │
│                          │
│          IKONA           │
│                          │
│ parametry                │
│ cena / downloads         │
│                PRZYCISK  │
└──────────────────────────┘
```

Ważne:

- ikona bez ramki;
- pełne dane pozostają;
- parametry znajdują się pod ikoną lub w dolnym bloku;
- przycisk pod parametrami;
- nie używać ikony jako backgroundu.

## 12. Fullscreen — geometria paczki

Fullscreen ma zachować rytm wizualny Googleplex News.

Jedna paczka:

```text
┌────────────── HERO ──────────────┬──── MIDDLE ────┬──── MIDDLE ────┐
│                                  │                │                │
│                                  ├──── SMALL ─────┼──── SMALL ─────┤
│                                  ├──── SMALL ─────┼──── SMALL* ────┤
└──────────────────────────────────┴────────────────┴────────────────┘
```

`SMALL*` istnieje zależnie od liczby elementów w paczce.

Implementacyjnie można użyć:

```text
group wrapper
├── hero column
└── side grid
    ├── middle
    ├── middle
    └── small grid
```

Nie próbować wymuszać wszystkiego jednym płaskim gridem, jeżeli powoduje to rozpad tekstu.

## 13. Start-size — geometria paczki

Start-size korzysta z tego samego renderera i tej samej kolejności.

Układ:

```text
HERO
↓
2 × MIDDLE obok siebie, jeśli szerokość pozwala
↓
SMALL w 2 kolumnach
↓
następna paczka
```

Jeżeli szerokość jest mniejsza:

```text
HERO
MIDDLE
MIDDLE
SMALL
SMALL
SMALL
```

Treści pozostają pełne.

## 14. Mobile

Mobile jest jednym wspólnym, przewijanym blokiem:

```text
WebDragon header
Googleplex header
tabs
search
results
footer
```

Jeden scroll.

Brak nested scrolli.

### HERO mobile

```text
┌─────────────────────────────┐
│ DUŻA IKONA │ NAZWA          │
│ PO LEWEJ   │ opis           │
│            │ parametry      │
│            │ cena/downloads │
│            │      PRZYCISK  │
└─────────────────────────────┘
```

### MIDDLE mobile

```text
IKONA LEWA
TREŚĆ PRAWA
PRZYCISK PRAWA/DÓŁ
```

Ikona trochę mniejsza niż HERO.

### SMALL mobile

SMALL może używać:

```text
NAZWA
IKONA WYŚRODKOWANA
PARAMETRY
PRZYCISK
```

Nie zmieniamy zawartości danych.

## 15. Rozmiary ikon

Orientacyjne:

```text
HERO fullscreen: 140–220 px
MIDDLE fullscreen: 90–150 px
SMALL fullscreen: 64–110 px

HERO mobile: 84–112 px
MIDDLE mobile: 72–96 px
SMALL mobile: 64–88 px
```

Zawsze:

```css
object-fit: contain;
max-width: 100%;
height: auto;
```

Brak border.

Brak background panel.

Brak box-shadow udającego kartę.

## 16. Przyciski

Nie zmieniamy logiki przycisków.

- HERO — większy wizualnie.
- MIDDLE — standardowy obecny button.
- SMALL — standardowy obecny button.
- Pojedynczy wynik — duży czytelny button.

Stany:

```text
Kup / Zainstaluj
ZAINSTALOWANO
Aplikacja już kupiona.
```

muszą korzystać z istniejącego canonical purchase/install state.

## 17. Purchased / installed state

Dla kupionej aplikacji:

- przycisk disabled;
- tekst `ZAINSTALOWANO`;
- ramka/komunikat `Aplikacja już kupiona.` zgodna z innymi aplikacjami;
- ponowny zakup niemożliwy;
- po canonical uninstall stan może wrócić do kupowalnego zgodnie z istniejącą logiką.

## 18. Brak przycinania danych

Zakazane:

```text
line-clamp opisu w celu dopasowania do karty
usuwanie parametrów
ukrywanie danych w HERO/MIDDLE/SMALL
zmiana danych zależnie od breakpointu
```

Layout ma dopasować się do danych.

Nie odwrotnie.

## 19. Progressive rendering dużych list

Po manualnej walidacji produkcyjnej 2026-08-29 `/all` ma renderować cały
bounded public catalog. Wcześniejszy limit trzech paczek powodował, że widok
deklarował pełną liczbę aplikacji, ale nie pokazywał większości asortymentu.

Aktualny kontrakt:

```text
/all
→ wszystkie wyniki z /resources.json
→ deterministyczny ranking
→ wszystkie paczki presentation
```

Jeżeli w przyszłości katalog przekroczy bezpieczny budżet DOM, progressive
rendering może wrócić wyłącznie jako automatyczne dokładanie przy scrollu,
które gwarantuje osiągalność wszystkich wyników. Nie wolno ponownie wprowadzić
cichego limitu ani wymagać niewidocznego przycisku na końcu bardzo długiej
kolumny.

Historyczna preferencja przed manualem była następująca:

Preferowane:

```text
initial render:
2–3 pełne paczki

następnie:
kolejne paczki dokładane przy scroll/load more
```

Ranking i kolejność pozostają niezmienione.

## 20. Wydajność

Zakazane:

```text
/api/profile
pełny profile refresh po search/render
get_profile()
list_profiles()
profile_json parse per card
pełny catalog reload dla każdej karty
```

Render korzysta z już pobranego bounded datasetu wyników.

Zmiana presentation class nie może wykonywać dodatkowego requestu per produkt.

## 21. Post-install performance audit

Sprawdzić:

```text
purchase response
→ inventory state update
→ card state update
→ launcher update
```

Nie może to powodować:

```text
pełnego profile refresh
pełnego desktop bootstrap
pełnego catalog reload
agresywnego pollingu
```

## 22. CSS architecture

Nie tworzyć kolejnego równoległego systemu kart.

Preferowane klasy:

```text
.gp-search-group
.gp-search-product
.gp-search-product--hero
.gp-search-product--middle
.gp-search-product--small

.gp-search-product__icon
.gp-search-product__content
.gp-search-product__params
.gp-search-product__footer
.gp-search-product__action
```

Wariant geometryczny ma być klasą.

Nie osobnym rendererem.

## 23. Etap A — REVERT

Przed implementacją:

1. zidentyfikować ostatnią zmianę, która zepsuła poprawny grid;
2. cofnąć tylko presentation changes;
3. nie cofać:
   - purchased-state fixów;
   - bounded backendu;
   - Googleplex News;
   - AGI;
   - search logic;
4. przywrócić wersję kart odpowiadającą poprawnym screenshotom.

Exit A:

```text
stary poprawny content renderer wrócił
search działa
/all działa
purchase/install działa
```

## 24. Etap B — GROUP ENGINE

Dodać jeden deterministyczny mapper:

```text
ordered results
→ presentation groups
```

Przykład:

```text
group 1:
  hero: result[0]
  middle: result[1:3]
  small: result[3:6]

group 2:
  hero: result[6]
  middle: result[7:9]
  small: result[9:12]
```

## 25. Etap C — IKONY

Do istniejących kart dodać ikonę.

Nie zmieniać danych tekstowych.

Sprawdzić osobno:

```text
HERO
MIDDLE
SMALL
single result
```

Ikona nie ma żadnej dodatkowej ramki.

## 26. Etap D — RESPONSIVE

Walidować osobno:

1. fullscreen;
2. start-size;
3. mobile.

Nie robić kolejnego refaktoru przed zaakceptowaniem screenshotów wszystkich trzech stanów.

## 27. Etap E — SINGLE RESULT

Warunek:

```text
results.length === 1
```

Prezentacja:

```text
pełna karta produktu
pełne parametry
ikona po lewej
duży button
brak wielkiej pustej przestrzeni
```

Nie traktować pojedynczego wyniku jako HERO z gridu grupowego.

## 28. Etap F — REGRESJA

Obowiązkowe przypadki:

```text
query = ""
query = "/all"
1 wynik
2 wyniki
3 wyniki
4 wyniki
6 wyników
7+ wyników
70 wyników
produkt kupiony
produkt niekupiony
produkt po uninstall
```

Viewport:

```text
fullscreen
start-size
mobile
```

## 29. Testy funkcjonalne

Potwierdzić:

- wyszukiwarka działa jak przed przebudową;
- `/all` pokazuje wszystkie produkty według rankingu;
- zwykła fraza filtruje poprawnie;
- jeden wynik pokazuje pełną kartę produktu;
- 2+ wyników korzysta z jednego group engine;
- nie ma specjalnego renderera wyłącznie dla 6 wyników;
- kolejna paczka ponownie ma HERO;
- ikony są elementem karty, nie tłem;
- żaden opis ani parametr nie znika przez zmianę wariantu;
- purchase/install/uninstall działa;
- installed state pokazuje canonical purchased frame;
- brak dodatkowych requestów per card;
- brak heavy-profile hot path.

## 30. Visual acceptance — fullscreen

Akceptacja tylko jeżeli:

- HERO ma ikonę po lewej;
- 2 MIDDLE są sideboxami;
- SMALL tworzą dolną część paczki;
- ikony nie mają ramek;
- treści są pełne;
- przyciski są czytelne;
- druga paczka ponownie zaczyna się HERO;
- nie występuje ogromna pusta powierzchnia;
- całość wizualnie korzysta z rytmu Googleplex News, ale pozostaje katalogiem produktów.

## 31. Visual acceptance — start-size

Akceptacja tylko jeżeli:

- ten sam content renderer;
- ten sam group engine;
- układ przepływa responsywnie;
- brak poziomego overflow;
- brak rozpadu kolumn tekstowych;
- ikony i buttony pozostają związane ze swoją kartą;
- jeden wspólny scroll.

## 32. Visual acceptance — mobile

Akceptacja tylko jeżeli:

- jedna kolumna;
- jeden scroll;
- HERO: ikona lewa, treść prawa;
- MIDDLE: ikona lewa, treść prawa;
- SMALL: ikona może być centralna, parametry i button pod nią;
- pełne opisy i parametry pozostają dostępne;
- brak nested scroll;
- brak poziomego overflow;
- button nie wychodzi poza kartę.

## 33. Exit gate

Sprint jest zakończony dopiero, gdy:

```text
SEARCH DATA — BEZ ZMIAN
PURCHASE/INSTALL — BEZ ZMIAN
FULL PRODUCT CONTENT — ZACHOWANY
ICON — W KOMPOZYCJI, BEZ RAMKI
1 RESULT — PEŁNA KARTA PRODUKTU
2+ RESULTS — JEDEN GROUP ENGINE
GROUP LOOP — HERO + 2×MIDDLE + 3–5×SMALL + REPEAT
FULLSCREEN — OK
START-SIZE — OK
MOBILE — OK
NO HEAVY PROFILE REGRESSION
NO POST-INSTALL PERFORMANCE REGRESSION
```

Finalny status:

```text
SPRINT 135.4.1.1 — COMPLETE
READY TO RESUME SPRINT 135.4.2 FINAL VALIDATION
```
