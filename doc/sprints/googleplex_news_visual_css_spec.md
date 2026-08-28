# Googleplex News — Visual/CSS Specification
## Kontrakt wizualny dla strony Home/News

Status dokumentu: handoff implementacyjny dla frontendu.

Cel: odwzorować układ i klimat zatwierdzonej wizualizacji Googleplex News bez zmiany istniejących funkcji Googleplex. Dokument opisuje wyłącznie warstwę wizualną, CSS, sizing, hierarchy, asset placement, responsywność i zachowanie interakcyjne elementów UI.

Nie kopiujemy literalnych nazw, tekstów ani przykładowych treści z mockupu. Mockup jest wzorcem układu, hierarchii i stylu.

---

# 1. Główna zasada wizualna

Googleplex News ma wyglądać jak:

- hackerski portal informacyjny z 2108 roku,
- social/news hub żyjący danymi z całego CHAOS,
- dynamiczna strona redakcyjna, a nie równa siatka dashboardu,
- komiksowy layout z silną hierarchią paneli,
- czarny terminalowy fundament,
- wyraziste panele o różnej wadze,
- nieregularna kompozycja przypominająca stronę magazynu / komiksu,
- neonowe kolory używane jako kod znaczenia, nie jako dekoracja wszystkiego.

Nie tworzymy symetrycznej tablicy identycznych kart.

Wymagana hierarchia rozmiarów:

```text
1 × HERO / XL
2 × LARGE
3 × MEDIUM
pozostałe × SMALL
```

To jest podstawowa reguła kompozycji.

---

# 2. Układ strony

Główna kolejność:

```text
WEB DRAGON / browser chrome
↓
Googleplex masthead + account/status
↓
główna nawigacja produktu
↓
ISTNIEJĄCA WYSZUKIWARKA GOOGLEPLEX
↓
NEWS MASONRY / EDITORIAL GRID
↓
GLOBAL STATUS STRIP
↓
PROTOCOL / integrity footer
```

Wyszukiwarka pozostaje w górnej części strony i zachowuje obecną funkcję.

Statystyki globalne, które wcześniej znajdowały się u góry dashboardu, trafiają do dolnego status stripu.

---

# 3. Maksymalna szerokość i viewport

Desktop:

```css
--gp-page-max: 1600px;
--gp-page-min: 1180px;
--gp-gap: 10px;
--gp-section-gap: 12px;
```

Główna powierzchnia powinna zajmować praktycznie całe wnętrze WebDragona.

Nie stosować dużych pustych marginesów bocznych.

```css
.googleplex-home {
  width: 100%;
  max-width: var(--gp-page-max);
  margin: 0 auto;
  padding: 8px 10px 10px;
}
```

Na szerokim desktopie layout powinien rosnąć głównie przez szerokość kart i assetów, a nie przez zwiększanie fontów.

---

# 4. System siatki

Rekomendowany fundament:

```css
.googleplex-news-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  grid-auto-flow: dense;
  gap: var(--gp-gap);
}
```

Nie stosować Flexboxa jako głównego mechanizmu kompozycji feedu.

Grid ma pozwalać na nieregularny editorial layout.

Przykładowe klasy rozmiarów:

```css
.news-card--xl {
  grid-column: span 5;
  grid-row: span 2;
  min-height: 500px;
}

.news-card--large {
  grid-column: span 3;
  min-height: 260px;
}

.news-card--medium {
  grid-column: span 3;
  min-height: 210px;
}

.news-card--small {
  grid-column: span 2;
  min-height: 170px;
}
```

Dokładne span mogą być dopasowane do realnej szerokości WebDragona, ale proporcja wizualna musi pozostać:

```text
HERO ≈ 35–42% szerokości pierwszej strefy
LARGE ≈ 22–28%
MEDIUM ≈ 18–24%
SMALL ≈ 12–18%
```

---

# 5. Reguła kompozycji pierwszego ekranu

Pierwszy viewport powinien wyglądać jak okładka newsowa.

Preferowany układ:

```text
┌──────────────── HERO ────────────────┬──── LARGE ────┬──── LARGE ────┐
│                                     │               │               │
│                                     ├──── MEDIUM ───┼──── MEDIUM ───┤
│                                     │               │               │
└─────────────────────────────────────┴───────────────┴───────────────┘
```

Poniżej:

```text
SMALL | SMALL | SMALL | MEDIUM | SMALL | SMALL | SMALL
```

Nie wszystkie rzędy mają mieć tę samą wysokość.

Nieregularność jest zamierzona.

---

# 6. Masthead Googleplex

Masthead powinien być wyraźniejszy niż zwykły nagłówek aplikacji.

Elementy:

- logo/wordmark Googleplex,
- krótki tagline,
- opcjonalny mikrostatus Grid,
- saldo / tożsamość gracza po prawej,
- subtelna tekstura tła.

Styl:

```css
.googleplex-masthead {
  position: relative;
  display: grid;
  grid-template-columns: minmax(260px, 420px) 1fr auto;
  align-items: center;
  min-height: 94px;
  border-bottom: 1px solid rgba(95,255,55,.22);
  background:
    linear-gradient(90deg, rgba(52,90,20,.08), transparent 38%),
    #020403;
  overflow: hidden;
}
```

`::before`:

- raster / halftone,
- opacity 0.04–0.08,
- `pointer-events:none`,
- bez blokowania czytelności.

`::after`:

- cienka linia świetlna / scanline przy dolnej krawędzi.

---

# 7. Wyszukiwarka Googleplex

Wyszukiwarka pozostaje funkcjonalnie istniejącą wyszukiwarką.

W News Home ma dostać bardziej „command/search hub” wygląd.

Układ:

```text
label
[ ikona ][ input................................ ][ SZUKAJ ][ filters ]
```

Desktop:

```css
.googleplex-search {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: stretch;
  gap: 8px;
  margin: 10px 0 12px;
}
```

Input:

```css
.googleplex-search input {
  height: 44px;
  border: 1px solid rgba(120,255,80,.26);
  background: rgba(0,7,3,.92);
  color: #d8e3d5;
  font: 14px/1.2 var(--gp-font-mono);
  padding: 0 14px 0 42px;
  outline: none;
}
```

Focus:

```css
.googleplex-search input:focus {
  border-color: rgba(110,255,65,.78);
  box-shadow:
    inset 0 0 0 1px rgba(110,255,65,.18),
    0 0 18px rgba(80,255,40,.08);
}
```

Placeholder:

- szary/oliwkowy,
- opacity 0.65,
- nie neonowo zielony.

Po wpisaniu tekstu wyszukiwarka przełącza powierzchnię na istniejący widok wyników. CSS nie może zmieniać tej logiki.

---

# 8. Podstawowa karta News

Każda karta ma wspólny shell:

```css
.news-card {
  --accent: #6eff42;

  position: relative;
  overflow: hidden;
  min-width: 0;
  background:
    linear-gradient(180deg, rgba(255,255,255,.018), transparent 22%),
    #020403;
  border: 1px solid color-mix(in srgb, var(--accent) 34%, #172019);
  box-shadow:
    inset 0 0 0 1px rgba(255,255,255,.018),
    0 1px 0 rgba(255,255,255,.015);
}
```

Każda karta musi mieć:

- kategorię / eyebrow,
- tytuł,
- asset lub wizualizację,
- jeden główny komunikat,
- maksymalnie 1 blok danych wtórnych,
- CTA tylko jeśli karta jest interaktywna.

---

# 9. Comic-book treatment

Komiksowość ma wynikać z kompozycji i faktury, nie z kreskówkowych fontów.

Dozwolone:

- halftone dots,
- grunge/noise,
- ostre kadrowanie assetów,
- diagonale w tle,
- silne kontrasty,
- kolorystyczne dominanty kart,
- duże headline'y w HERO,
- pasy / warning strips,
- lekko przesunięte pseudo-warstwy.

Unikać:

- zaokrąglonych kart SaaS,
- pastelowych gradientów,
- szkła typu glassmorphism,
- wielkich blurów,
- miękkich shadowów,
- emoji jako głównych ikon.

Pseudo-warstwa:

```css
.news-card::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 30% 20%, rgba(255,255,255,.07) 0 1px, transparent 1.3px);
  background-size: 5px 5px;
  opacity: .06;
  pointer-events: none;
  mix-blend-mode: screen;
}
```

Druga warstwa:

```css
.news-card::after {
  content: "";
  position: absolute;
  inset: auto 0 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  opacity: .28;
  pointer-events: none;
}
```

---

# 10. Kolory

Kolor główny:

```text
Grid / Googleplex green
#6EFF42 – aktywne CTA / sukces / Googleplex
```

Kolory funkcjonalne:

```text
green      normal / growth / system ok
red        conflict / critical / attack
orange     data/package/commerce
purple     underground/tool/download
cyan       Cyberner/network/communication
yellow     warning/attention
white      editorial headline
grey       metadata/secondary text
```

Nie wolno kolorować całej karty jednym neonem.

Reguła:

```text
80–90% powierzchni = black / dark graphite
5–15% = neutral text / lines
1–5% = accent
```

---

# 11. Typografia

Rodziny:

```text
1. mono / terminal
2. condensed display dla największych headline
```

Nie więcej niż dwie rodziny fontów w tym widoku.

Skala:

```text
12 px  metadata
13 px  labels / stats
14 px  body
16 px  small-card title
19–22 px medium title
24–30 px large title
42–58 px HERO headline
```

Desktop HERO może używać uppercase.

Tekst główny:

```css
line-height: 1.32–1.45;
letter-spacing: .01em;
```

Metadata:

```css
letter-spacing: .04em;
text-transform: uppercase;
```

---

# 12. Limity tekstów

Frontend powinien zakładać twarde limity prezentacyjne niezależnie od backendu.

HERO:

```text
eyebrow       max 32 znaki
headline      max 72 znaki / 2–3 linie
summary       max 220 znaków / 4–5 linii
CTA           max 22 znaki
```

LARGE:

```text
eyebrow       max 28
title         max 54 / 2 linie
summary       max 130 / 3 linie
stat label    max 22
```

MEDIUM:

```text
eyebrow       max 24
title         max 44 / 2 linie
summary       max 90 / 2–3 linie
```

SMALL:

```text
title         max 32 / 2 linie
label         max 20
stat          1–2 wartości
body          opcjonalnie max 48
```

CSS:

```css
.card-title {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.news-card--large .card-title {
  -webkit-line-clamp: 2;
}

.news-card--small .card-title {
  -webkit-line-clamp: 2;
}
```

Nie pozwalać dynamicznemu tekstowi zwiększać wysokości kart bez końca.

---

# 13. HERO asset

Hero jest jedynym assetem mogącym zająć całą powierzchnię karty.

```css
.news-card--hero .card-asset {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: var(--asset-focus-x, 50%) var(--asset-focus-y, 50%);
}
```

Overlay:

```css
.news-card--hero .card-asset::after {}
```

Nie tworzyć pseudo-elementu na `img`; overlay na wrapperze.

```css
.hero-media::after {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(0,0,0,.90) 0%, rgba(0,0,0,.44) 44%, rgba(0,0,0,.10) 75%),
    linear-gradient(0deg, rgba(0,0,0,.82), transparent 50%);
}
```

Headline i summary powinny być osadzone w bezpiecznym obszarze, nie centralnie na twarzy/obiekcie.

---

# 14. Assety kart LARGE

Asset może:

- zajmować 45–58% szerokości,
- wychodzić poza dół,
- być kadrowany,
- być lekko przesunięty.

```css
.news-card--large .card-asset {
  position: absolute;
  right: -2%;
  bottom: -4%;
  width: 52%;
  max-height: 88%;
  object-fit: contain;
  transform-origin: 60% 80%;
}
```

Tekst otrzymuje maksymalnie 52–58% szerokości.

---

# 15. Assety MEDIUM

Asset:

```text
30–45% karty
```

Może być:

- mapą,
- mini-chartem,
- symbolem,
- fragmentem screenshotu,
- renderem przedmiotu.

Powinien wspierać dane, a nie dominować tytułu.

---

# 16. Assety SMALL

Standard:

```text
64–120 px desktop
```

Małe karty powinny używać rodzin assetów:

- icon,
- emblem,
- micro-map,
- donut,
- sparkline,
- mini-object,
- stamped illustration.

Nie stosować pełnych scen w małej karcie.

---

# 17. Rodziny assetów

Każdy asset powinien mieć `asset_family`.

Operacyjna lista assetów, ich stan produkcji, logo, ikonografia, cztery warianty
`neutral/danger/victory/defence` oraz grupy rotacyjne są utrzymywane w
`static/images/googleplx/readme.md`. Ten plik jest wiążącym handoffem dla
tworzenia grafik i przyszłego code-owned registry.

Rekomendowane rodziny:

```text
scene          – pełna scena / lokacja / wydarzenie
character      – postać / avatar / persona
tool           – narzędzie / aplikacja / produkt
map            – konflikt / podróż / terytorium
clan           – emblemat / symbol klanu
package        – paczka danych / plik / artefakt
storage        – dysk / hardware / capacity
market         – exchange / wykres / ticker
network        – Cyberner / komunikacja / sygnał
system         – integrity / status / maintenance
stamp          – czysto informacyjny znak
```

## 17.1. Wiążąca macierz formatów i proporcji

Rodzina określa semantykę oraz dozwolony typ assetu. Nie określa wielkości
karty — za nią odpowiada niezależne `presentation_weight`.

| `asset_family` | Zastosowanie | Preferowany format | Proporcje / rozmiar źródła | Typowa ekspozycja |
| --- | --- | --- | --- | --- |
| `scene` | pełna scena, lokacja, duży event | WebP | `16:9` lub `4:3`, minimum około `1200×700` | głównie HERO, cover |
| `character` | postać, persona, operator, NPC | transparent WebP albo PNG | pionowe `3:4` lub `4:5` | LARGE/MEDIUM |
| `tool` | aplikacja, narzędzie, hardware | transparent PNG albo WebP | `1:1`, render `256–512 px` | LARGE/MEDIUM/SMALL |
| `map` | konflikt, podróż, terytorium, heatmapa | SVG lub render HTML/Canvas; WebP tylko dla statycznej ilustracji | `4:3` lub `1:1` | HERO/LARGE/MEDIUM |
| `clan` | emblemat, znak klanu | SVG; fallback transparent PNG | `1:1` | MEDIUM/SMALL |
| `package` | paczka danych, plik, artefakt, skrzynka | transparent PNG albo WebP | `1:1` lub lekka izometria | LARGE/MEDIUM/SMALL |
| `storage` | dysk, serwer, pamięć, capacity | transparent PNG albo WebP | zwykle `1:1`; procenty i paski poza assetem | MEDIUM/SMALL |
| `market` | Ghost Exchange, ticker, wykresy, ekonomia | SVG/Canvas/HTML | zależne od komponentu; dynamiczne dane nie są rastrem | LARGE/MEDIUM/SMALL |
| `network` | Cyberner, połączenia, sygnały, komunikacja | SVG albo PNG | zwykle `1:1`; opcjonalna mała animacja CSS | MEDIUM/SMALL |
| `system` | status, maintenance, integrity, bezpieczeństwo | SVG | minimalistyczny symbol, zwykle `1:1` | SMALL/status strip |
| `stamp` | badge, verified, read-only, znak informacyjny | SVG | mały, lekki, zwykle `1:1` | SMALL/protocol footer |

Obowiązują trzy główne standardy produkcyjne:

```text
duże ilustracje i sceny
→ WebP

postacie, przedmioty, aplikacje i hardware
→ transparent PNG/WebP

ikony, emblematy, statusy i wektorowe elementy mapowe
→ SVG
```

Wykresy, tickery, procenty, paski capacity, heatmapy zależne od danych i inne
dynamiczne statystyki powstają z danych przez CSS/SVG/Canvas/HTML. Nie wolno
pakować ich jako gotowych screenshotów lub rasterów udających aktualny stan.

SVG jest code-owned/local albo pochodzi z jawnego, oczyszczonego registry. UI
nie renderuje dowolnego SVG/URL dostarczonego przez wpis News.

## 17.2. Rodzina a format prezentacyjny

`asset_family` i `presentation_weight` są niezależnymi osiami:

```text
asset_family
→ co przedstawia asset i jaki pipeline pliku jest legalny

presentation_weight
→ jak duża jest karta i ile powierzchni otrzymuje asset
```

Ten sam `tool` może wystąpić jako LARGE, MEDIUM albo SMALL bez tworzenia nowej
rodziny. Sposób ekspozycji:

| `presentation_weight` | Ekspozycja assetu |
| --- | --- |
| `hero` | asset `cover`, może zajmować całą kartę z bezpiecznym gradientem pod tekstem |
| `large` | zwykle około `45–58%` powierzchni karty |
| `medium` | zwykle około `30–45%` powierzchni karty |
| `small` | asset około `64–120 px`; bez pełnej sceny |

Jeden plik może być kadrowany w różnych wagach prezentacyjnych. Nie tworzymy
osobnych kopii tylko po to, aby zmienić crop.

## 17.3. Code-owned asset registry

`asset_id` musi rozwiązywać się przez lokalny/allowlisted registry zawierający
co najmniej:

```text
asset_id
asset_family
path
mime_type
native_width
native_height
native_aspect_ratio
has_transparency
```

Registry weryfikuje zgodność formatu z rodziną. Nieznany `asset_id`, niedozwolony
MIME albo błędna proporcja daje kontrolowany placeholder rodziny, a nie próbę
zgadywania pliku lub pobierania z sieci.

CSS powinien mieć warianty po rodzinie:

```css
[data-asset-family="character"] .card-asset {}
[data-asset-family="tool"] .card-asset {}
[data-asset-family="map"] .card-asset {}
```

---

# 18. Asset focus i focal point

Każdy wpis z assetem musi móc podać:

```text
asset_focus_x
asset_focus_y
asset_scale
asset_rotation
```

Pola są częścią kontraktu prezentacyjnego i pozwalają użyć jednego pliku w
różnych kartach. Nie wolno losować ich po stronie klienta ani generować osobnej
wersji grafiki wyłącznie dla innego kadru.

CSS variables:

```css
.card {
  --asset-focus-x: 50%;
  --asset-focus-y: 50%;
  --asset-scale: 1;
  --asset-rotation: 0deg;
}
```

```css
.card-asset {
  object-position: var(--asset-focus-x) var(--asset-focus-y);
  transform:
    scale(var(--asset-scale))
    rotate(var(--asset-rotation));
}
```

---

# 19. Rotacje assetów względem stanu

Rotacja jest subtelna.

Normal:

```text
-1deg … +1deg
```

Trending / active:

```text
-2deg … +2deg
```

Critical/conflict:

```text
-3deg … +3deg
```

Stamp/system:

```text
0deg
```

Nigdy losowo przy każdym renderze.

Rotacja musi być deterministyczna z config/state.

Przykład:

```css
[data-state="critical"] {
  --asset-rotation: -1.5deg;
}

[data-state="trending"] {
  --asset-rotation: .8deg;
}
```

---

# 20. Hover interaktywnych kart

Tylko karty posiadające prawdziwe action/target dostają hover.

```css
.news-card[data-interactive="true"] {
  cursor: pointer;
  transition:
    border-color 120ms ease,
    transform 120ms ease,
    background-color 120ms ease;
}
```

Hover:

```css
.news-card[data-interactive="true"]:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--accent) 75%, white);
}
```

Asset:

```css
.news-card[data-interactive="true"]:hover .card-asset {
  transform:
    scale(calc(var(--asset-scale) * 1.018))
    rotate(var(--asset-rotation));
}
```

Nie stosować zoom > 1.03.

---

# 21. Hover pseudo-elements

Interaktywna karta:

```css
.news-card[data-interactive="true"]:hover::after {
  opacity: .75;
}
```

Opcjonalny comic slash:

```css
.news-card[data-interactive="true"] .hover-slash {
  position: absolute;
  inset: 0 auto 0 -20%;
  width: 14%;
  transform: skewX(-18deg);
  background: linear-gradient(90deg, transparent, rgba(110,255,66,.08), transparent);
  opacity: 0;
  pointer-events: none;
}

.news-card[data-interactive="true"]:hover .hover-slash {
  animation: gpSlash 320ms ease-out;
}
```

Animacja ma być subtelna i krótka.

---

# 22. Karty stamp-only

Karta bez action:

```css
.news-card[data-interactive="false"] {
  cursor: default;
}
```

Nie może udawać buttona.

Brak:

- translate on hover,
- glowing CTA,
- pointer cursor.

Może mieć tylko subtelne podbicie borderu wynikające ze stanu feedu.

---

# 23. CTA

CTA wyłącznie dla karty interaktywnej.

Styl:

```css
.card-cta {
  display: inline-flex;
  min-height: 30px;
  align-items: center;
  padding: 0 10px;
  border: 1px solid var(--accent);
  background: rgba(0,0,0,.58);
  color: var(--accent);
  font-weight: 700;
  text-transform: uppercase;
}
```

Hover:

```css
.card-cta:hover {
  background: var(--accent);
  color: #020402;
}
```

Nie więcej niż 1 główne CTA na kartę.

---

# 24. Statystyki globalne — footer strip

Przenosimy kompaktowe global stats pod główny news grid.

Układ:

```css
.googleplex-global-stats {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  border: 1px solid rgba(110,255,66,.22);
  background: #020403;
}
```

Każda komórka:

- ikona,
- label,
- główna wartość,
- delta,
- opcjonalny sparkline.

Wysokość:

```text
62–78 px
```

To ma być status strip, a nie druga sekcja kart.

---

# 25. Dolny protocol footer

Najniższa sekcja jest wizualnym stemplem systemowym.

Elementy:

- source/integrity,
- encryption,
- access mode,
- update time,
- ewentualny disclaimer.

Nie musi być interaktywna.

Wysokość:

```text
48–70 px
```

---

# 26. Stany kart

Każda karta może mieć:

```text
normal
trending
hot
warning
critical
new
verified
stale
disabled
```

CSS przez:

```text
data-state
```

Przykład:

```css
.news-card[data-state="critical"] {
  --accent: #ff4034;
}

.news-card[data-state="warning"] {
  --accent: #ffb52e;
}

.news-card[data-state="verified"] {
  --accent: #66ff44;
}
```

Stan nie może zmieniać geometrii karty.

---

# 27. Empty / loading / error

Empty:

- nie usuwa wyszukiwarki,
- nie rozciąga jednego pustego boxa na całą wysokość,
- pokazuje 1–3 lekkie placeholder/stamp cards.

Loading:

- skeleton bez shimmer disco,
- subtelny scanline.

Error:

- kontrolowany panel systemowy,
- bez stack trace,
- pozostały Googleplex nadal działa.

---

# 28. Responsive

Desktop >= 1200:

```text
12 columns
pełna hierarchia XL/L/M/S
```

Tablet 768–1199:

```text
8 columns
XL = 8
L = 4
M = 4
S = 2–4
```

Mobile <768:

```text
1 kolumna
```

Na mobile nadal zachowujemy hierarchię:

```text
HERO
LARGE
LARGE
MEDIUM ×3
SMALL...
```

Nie robimy masonry side-by-side.

Jeden główny scroll.

---

# 29. Motion

Dozwolone:

- hover 100–160 ms,
- asset scale 1.01–1.02,
- scanline,
- sparkline,
- status pulse dla live/critical,
- jeden subtelny comic slash.

Zakazane:

- ciągłe glitchowanie całego UI,
- mocne shake,
- przesuwające się tła,
- migające duże powierzchnie,
- animacje powodujące layout shift.

`prefers-reduced-motion` musi wyłączać dekoracyjne motion.

---

# 30. CSS architecture

Rekomendowany podział:

```text
googleplex-news.tokens.css
googleplex-news.layout.css
googleplex-news.cards.css
googleplex-news.assets.css
googleplex-news.states.css
googleplex-news.motion.css
googleplex-news.responsive.css
```

Nie wrzucać wszystkiego do jednego istniejącego globalnego pliku, jeśli projekt pozwala na modułowy podział.

Nazewnictwo:

```text
gp-news-*
gp-home-*
```

Unikać generycznych `.card`, `.title`, `.grid` jeśli mogą kolidować z istniejącą grą.

---

# 31. Visual acceptance gate

Implementacja jest zgodna z wizualizacją, jeśli:

- istnieją dokładnie 4 poziomy ważności geometrycznej,
- pierwszy ekran ma wyraźny HERO,
- dwa LARGE są zauważalnie większe niż reszta,
- trzy MEDIUM tworzą drugi poziom narracji,
- reszta jest kompaktowa,
- wyszukiwarka Googleplex pozostała na górze,
- global stats są w dolnym stripie,
- layout nie wygląda jak równa tabela dashboardu,
- assety są częścią kompozycji, a nie ikonami doklejonymi obok tekstu,
- assety spełniają format i proporcję przypisaną do swojej rodziny,
- rodzina assetu pozostaje niezależna od `presentation_weight`,
- dynamiczne wykresy i statystyki nie są rasteryzowanymi screenshotami,
- jeden asset może być bezpiecznie kadrowany przez focus/scale/rotation,
- hover istnieje tylko tam, gdzie istnieje realne action,
- stamp-only cards nie udają linków,
- mobile ma jeden scroll,
- wygląd zachowuje terminalowy charakter CHAOS, ale jest znacznie bardziej editorial/comic niż obecny katalog.
