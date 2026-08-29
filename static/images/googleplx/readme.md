# Googleplex News — asset registry source

Status katalogu: `PRODUCTION PLACEHOLDERS READY / FINAL ASSETS IN PREPARATION`.

Ten katalog jest jedynym code-owned źródłem assetów dla Googleplex Home/News.
Nazwa katalogu `googleplx` jest kontraktem ścieżki i nie powinna być poprawiana
ani dublowana wariantem `googleplex` bez migracji registry.

Referencje projektowe:

- `doc/visual/ggpl_news.png` — zatwierdzona kompozycja;
- `doc/sprints/googleplex_news_visual_css_spec.md`;
- `doc/sprints/googleplex_news_functional_spec.md`;
- `doc/sprints/sprint_135_4_1_googleplex_home_news_foundation.md`.

Makieta jest referencją stylu i układu. Nie jest źródłem literalnych newsów,
statystyk, nazw wydarzeń ani mechanik gameplayowych.

## Zasada wyboru assetu

Rodzina i stan są niezależne od wielkości karty:

```text
asset_family
→ co przedstawia asset

asset_state
→ neutral | danger | victory | defence

presentation_weight
→ hero | large | medium | small
```

Jeden `asset_id` może być użyty w kilku wagach prezentacyjnych dzięki:

```text
asset_focus_x
asset_focus_y
asset_scale
asset_rotation
```

Nie tworzymy osobnej kopii pliku wyłącznie dla innego kadru.

## Cztery stany wizualne

Stany nie zmieniają canonical gameplay state. Są wyłącznie zatwierdzoną
interpretacją wizualną istniejących facts.

| Stan | Znaczenie wizualne | Akcent | Dozwolone użycie |
| --- | --- | --- | --- |
| `neutral` | zwykły stan, informacja, stabilność | green/cyan/white | domyślny fallback każdej rodziny |
| `danger` | konflikt, awaria, utrata, alarm | red/orange | tylko gdy canonical facts opisują zagrożenie |
| `victory` | sukces, odzyskanie, ukończenie, wzrost | lime/white/gold | tylko po canonical success/verified outcome |
| `defence` | ochrona, containment, odporność, integralność | cyan/blue/lime | tylko przy canonical defence/protection facts |

Nie wolno wywnioskować `victory` lub `danger` wyłącznie z tonu tekstu modelu.
Stan musi pochodzić z backendowej projekcji facts/truth.

## Ollama — bezpieczny kontrakt doboru

Ollama nie otrzymuje ścieżek katalogu i nie może wymyślić nazwy pliku.
Task/publisher przekazuje bounded listę:

```text
allowed_asset_refs[]
```

Każda pozycja zawiera najwyżej:

```text
asset_ref
asset_family
asset_state
allowed_presentation_weights[]
```

Model może zwrócić wyłącznie:

```text
asset_ref: <jedna wartość z allowed_asset_refs>
```

Backend ponownie weryfikuje wybór w registry. Nieznany ref, niedozwolona rodzina,
stan lub weight kończy się canonical fallbackiem albo brakiem assetu — nigdy
odczytem arbitralnej ścieżki lub URL-a.

W Sprincie 135.4.1 Home nie wywołuje Ollamy. Kontrakt przygotowuje bezpieczny
dobór dla przyszłego publishera 135.5.

## Macierz 11 rodzin i stanów

Legenda realizacji wariantu:

```text
DEDICATED  → osobny plik wariantu jest uzasadniony
COMPOSED   → jeden neutralny asset + code-owned CSS/SVG/HTML state treatment
OPTIONAL   → tworzyć tylko dla konkretnego zatwierdzonego zastosowania
```

| Rodzina | Format | `neutral` | `danger` | `victory` | `defence` | Stan produkcji |
| --- | --- | --- | --- | --- | --- | --- |
| `scene` | WebP `16:9`/`4:3`, min. `1200×700` | DEDICATED | DEDICATED | DEDICATED | DEDICATED | `READY PLACEHOLDER` |
| `character` | transparent WebP/PNG `3:4`/`4:5` | DEDICATED | OPTIONAL | OPTIONAL | OPTIONAL | `READY SYMBOL` |
| `tool` | transparent PNG/WebP `1:1`, `256–512 px` | DEDICATED | COMPOSED | COMPOSED | COMPOSED | `READY SYMBOL` |
| `map` | SVG/HTML/Canvas; statycznie WebP `4:3`/`1:1` | COMPOSED | COMPOSED | COMPOSED | COMPOSED | `READY SYMBOL` |
| `clan` | SVG, fallback transparent PNG `1:1` | DEDICATED | COMPOSED | COMPOSED | COMPOSED | `READY SYMBOL` |
| `package` | transparent PNG/WebP `1:1`/izometria | DEDICATED | COMPOSED | COMPOSED | COMPOSED | `READY SYMBOL` |
| `storage` | transparent PNG/WebP; dane w CSS/HTML | DEDICATED | COMPOSED | COMPOSED | COMPOSED | `READY SYMBOL` |
| `market` | SVG/Canvas/HTML | COMPOSED | COMPOSED | COMPOSED | COMPOSED | `READY SYMBOL` |
| `network` | SVG/PNG `1:1`, opcjonalny CSS motion | DEDICATED | COMPOSED | COMPOSED | COMPOSED | `READY SYMBOL` |
| `system` | minimalistyczny SVG | DEDICATED | COMPOSED | COMPOSED | COMPOSED | `READY SYMBOL` |
| `stamp` | mały lekki SVG | DEDICATED | DEDICATED | DEDICATED | DEDICATED | `READY SYMBOL` |

`neutral` jest obowiązkowym fallbackiem każdej rodziny. Dedykowane cztery
warianty HERO są obowiązkowe dla `scene`. Pozostałe rodziny używają osobnego
pliku stanu tylko tam, gdzie rzeczywiście zmienia się przedstawiany obiekt;
sam kolor, obramowanie, badge lub wykres należy komponować w UI.

## Planowana struktura

```text
static/images/googleplx/
├── readme.md
├── asset_registry.json              # przyszły code-owned manifest
├── brand/
├── icons/
├── scene/
├── character/
├── tool/
├── map/
├── clan/
├── package/
├── storage/
├── market/
├── network/
├── system/
└── stamp/
```

Puste podkatalogi nie są tworzone przed dodaniem pierwszego assetu.

## Nowe logo Googleplex News

Wizualizacja wprowadza odrębny editorialowy masthead Googleplex News. Należy
przygotować:

| Planowany `asset_id` | Plik | Format | Użycie | Stan |
| --- | --- | --- | --- | --- |
| `gp_brand_wordmark_primary` | `brand/googleplex-news-wordmark.svg` | SVG | pełny masthead desktop | `READY PLACEHOLDER` |
| `gp_brand_mark_primary` | `brand/googleplex-news-mark.svg` | SVG | kompaktowy/mobile mark | `READY PLACEHOLDER` |
| `gp_brand_wordmark_mono` | `brand/googleplex-news-wordmark-mono.svg` | SVG | reduced/print/fallback | `MISSING` |
| `gp_brand_favicon` | `brand/googleplex-news-favicon.svg` | SVG | WebDragons/tab/icon | `READY PLACEHOLDER` |

Logo zachowuje estetykę z `ggpl_news.png`: mocny editorialny wordmark, terminalowy
kontrast i czytelność na czarnym tle. Tagline, aktualny czas, HC, rank i dane
konta pozostają tekstem HTML, nie częścią grafiki logo.

## Ikonografia z wizualizacji

Ikony są lokalnymi SVG, bez emoji i bez zewnętrznego icon CDN. Placeholdery są
obecnie symbolami w `icons/googleplex-news-icons.svg`; finalny pack może zachować
sprite albo rozdzielić pliki bez zmiany `asset_id`.

| Planowany `asset_id` | Plik | Funkcja | Stan |
| --- | --- | --- | --- |
| `gp_icon_search` | `icons/googleplex-news-icons.svg#search` | wyszukiwanie Googleplex | `READY PLACEHOLDER` |
| `gp_icon_filter` | `icons/googleplex-news-icons.svg#filter` | filtr/sort feedu | `READY PLACEHOLDER` |
| `gp_icon_grid` | `icons/googleplex-news-icons.svg#grid` | Home/grid | `READY PLACEHOLDER` |
| `gp_icon_product` | `icons/googleplex-news-icons.svg#product` | aplikacja/produkt | `READY PLACEHOLDER` |
| `gp_icon_blacknet` | `icons/googleplex-news-icons.svg#blacknet` | teaser BlackNet | `READY PLACEHOLDER` |
| `gp_icon_exchange` | `icons/googleplex-news-icons.svg#ghost-exchange` | teaser Ghost Exchange | `READY PLACEHOLDER` |
| `gp_icon_map_focus` | `icons/googleplex-news-icons.svg#map-focus` | focus mapy/regionu | `READY PLACEHOLDER` |
| `gp_icon_travel` | `icons/googleplex-news-icons.svg#travel` | podróż/trasa | `READY PLACEHOLDER` |
| `gp_icon_clan` | `icons/googleplex-news-icons.svg#clan` | klan | `READY PLACEHOLDER` |
| `gp_icon_package` | `icons/googleplex-news-icons.svg#package` | paczka/plik | `READY PLACEHOLDER` |
| `gp_icon_storage` | `icons/googleplex-news-icons.svg#storage` | dysk/capacity | `READY PLACEHOLDER` |
| `gp_icon_cyberner` | `icons/googleplex-news-icons.svg#cyberner` | sieć/Cyberner | `READY PLACEHOLDER` |
| `gp_icon_integrity` | `icons/googleplex-news-icons.svg#integrity` | integrity/protocol | `READY PLACEHOLDER` |
| `gp_icon_verified` | `icons/googleplex-news-icons.svg#verified` | canonical/verified | `READY PLACEHOLDER` |
| `gp_icon_read_only` | `icons/googleplex-news-icons.svg#read-only` | STAMP_ONLY | `READY PLACEHOLDER` |
| `gp_icon_warning` | `icons/googleplex-news-icons.svg#warning` | warning/danger | `READY PLACEHOLDER` |
| `gp_icon_defence` | `icons/googleplex-news-icons.svg#defence` | protection/defence | `READY PLACEHOLDER` |
| `gp_icon_victory` | `icons/googleplex-news-icons.svg#victory` | success/victory | `READY PLACEHOLDER` |
| `gp_icon_open` | `icons/googleplex-news-icons.svg#open` | canonical open/detail CTA | `READY PLACEHOLDER` |

CTA może użyć jednej ikony i krótkiej etykiety. Ikona sama nie tworzy action;
widoczność i interaktywność wynikają z canonical `ACTIONABLE`.

## Googleplex Search UI chrome — sockety ikon aplikacji

Karty produktów Googleplex Search zachowują dokładnie ikonę wybraną przez autora
aplikacji. Emoji, runa, pojedynczy znak Unicode albo inny canonical `item.icon`
nie są zamieniane, filtrowane ani wpisywane do assetu. Pięć lokalnych socketów
stanowi wyłącznie dekoracyjną warstwę HUD renderowaną pod prawdziwą ikoną:

| Socket | Plik | Domyślne zastosowanie |
| --- | --- | --- |
| `core` | `icons/app-sockets/01_icon_socket_core.svg` | `HERO` i pojedynczy wynik |
| `side` | `icons/app-sockets/02_icon_socket_side.svg` | `SIDE` / `MIDDLE` |
| `compact` | `icons/app-sockets/03_icon_socket_compact.svg` | `SMALL` |
| `hex` | `icons/app-sockets/04_icon_socket_hex.svg` | stabilny wariant rodzin system/custom/exploit |
| `target` | `icons/app-sockets/05_icon_socket_target.svg` | stabilny wariant rodzin scanner/tracker |

Sockety są code-owned UI chrome, a nie narracyjnymi assetami Googleplex News.
Nie należą do `allowed_asset_refs`, nie są wybierane przez Ollamę i celowo nie
mają rekordów w `asset_registry.json`. Dobór wariantu odbywa się wyłącznie po
code-owned klasie prezentacyjnej lub stabilnej rodzinie produktu; nie może być
losowy ani zależny od tekstu wygenerowanego przez model.

Każdy plik ma transparentne tło i widok `256×256`. Zawiera tylko lekką geometrię
HUD, pozostawia czystą strefę centralną dla ikony i nie może zawierać:

- ikon użytkownika ani przykładowych emoji;
- tekstu, liczb lub fake gameplay data;
- bitmap, fontów, skryptów, `foreignObject` ani zewnętrznych odwołań;
- ciężkich filtrów, blurów lub wypalonego koloru stanu.

Warstwa socketu powinna być używana jako CSS mask albo transparentny obraz
tintowany filtrem do istniejącego akcentu produktu. Prawdziwa ikona pozostaje
osobnym elementem DOM nad dekoracją.
Socket ma `pointer-events: none` i jest `aria-hidden`; nie jest dodatkowym
panelem, ramką produktu ani źródłem semantyki. `background-image` nie może być
nakładany na kartę lub canonical user icon — URL socketu należy wyłącznie do
dekoracyjnej warstwy maski.

## HERO — obowiązkowy pierwszy zestaw

Pierwszy minimalny asset pack musi zawierać cztery sceny:

| Planowany `asset_id` | Plik | Stan | Focal default | Stan produkcji |
| --- | --- | --- | --- | --- |
| `gp_scene_world_neutral_01` | `scene/world-neutral-01.webp` | `neutral` | `50% 50%` | `READY PLACEHOLDER` |
| `gp_scene_world_danger_01` | `scene/world-danger-01.webp` | `danger` | `58% 48%` | `READY PLACEHOLDER` |
| `gp_scene_world_victory_01` | `scene/world-victory-01.webp` | `victory` | `50% 42%` | `READY PLACEHOLDER` |
| `gp_scene_world_defence_01` | `scene/world-defence-01.webp` | `defence` | `55% 48%` | `READY PLACEHOLDER` |

Każda scena musi pozostawiać text-safe area zgodną z layoutem HERO. Gradient pod
tekst powstaje w CSS, nie jest wypalony w WebP.

## Assety rotacyjne i zfocusowane sekcje

Rotacja oznacza deterministyczny wybór z małej allowlisty, a nie losowanie przy
każdym renderze.

```text
rotation_key = news_id + state_version + presentation_slot
→ stabilny indeks w rotation_group
```

Dla niezmienionego snapshotu, reopen, resize i rerender wybierają ten sam asset.
Zmiana jest dozwolona dopiero przy nowym `state_version` lub nowym wpisie.

Planowane grupy:

| `rotation_group` | Sloty | Rodziny | Minimalna liczba | Stan |
| --- | --- | --- | --- | --- |
| `gp_hero_neutral` | HERO | scene | 2 | `MISSING` |
| `gp_hero_danger` | HERO | scene/map | 2 | `MISSING` |
| `gp_hero_victory` | HERO | scene/character | 2 | `MISSING` |
| `gp_hero_defence` | HERO | scene/map | 2 | `MISSING` |
| `gp_focus_products` | LARGE/MEDIUM | tool | 4 | `MISSING` |
| `gp_focus_world` | LARGE/MEDIUM | map/scene | 4 | `MISSING` |
| `gp_focus_market` | LARGE/MEDIUM | market/package | 4 | `MISSING` |
| `gp_focus_network` | LARGE/MEDIUM | network/character | 4 | `MISSING` |
| `gp_focus_system` | MEDIUM/SMALL | system/storage/stamp | 4 | `MISSING` |

Każdy wpis registry należący do grupy rotacyjnej zapisuje osobne bezpieczne
presety kadru dla obsługiwanych slotów:

```text
focus_presets.hero
focus_presets.large
focus_presets.medium
focus_presets.small
```

Preset zawiera `focus_x`, `focus_y`, `scale` i `rotation`. CSS może nałożyć
subtelny state treatment, ale nie przesuwa semantycznego focal pointu.

## Kontrakt przyszłego `asset_registry.json`

Minimalny rekord:

```json
{
  "asset_id": "gp_scene_world_neutral_01",
  "asset_family": "scene",
  "asset_state": "neutral",
  "path": "/static/images/googleplx/scene/world-neutral-01.webp",
  "mime_type": "image/webp",
  "native_width": 1600,
  "native_height": 900,
  "native_aspect_ratio": "16:9",
  "has_transparency": false,
  "allowed_presentation_weights": ["hero", "large"],
  "rotation_group": "gp_hero_neutral",
  "focus_presets": {
    "hero": {"focus_x": 50, "focus_y": 50, "scale": 1.0, "rotation": 0},
    "large": {"focus_x": 52, "focus_y": 48, "scale": 1.06, "rotation": 0}
  },
  "status": "ready"
}
```

Dozwolone `status`:

```text
missing
draft
review
ready
retired
```

Tylko `ready` może trafić do produkcyjnego `allowed_asset_refs`.

## Definition of ready dla assetu

Asset jest `ready`, gdy:

- leży pod `/static/images/googleplx/`;
- ma unikalny `asset_id` i rekord registry;
- format, MIME, proporcja i przezroczystość pasują do rodziny;
- ma zatwierdzony `asset_state`;
- ma co najmniej jeden focus preset;
- nie zawiera dynamicznych liczb ani tekstu zależnego od danych;
- nie ujawnia hidden gameplay topology ani prywatnych metadata;
- ma potwierdzone prawa/licencję albo jest code-owned;
- przechodzi fallback i responsive crop test;
- nie jest wybierany, dopóki status nie wynosi `ready`.

## Aktualny stan katalogu

```text
logo/brand placeholders:  3 ready / 1 final mono pending
iconography:              19 ready placeholder symbols in one sprite
11 family fallbacks:      11 ready symbols
4 HERO state assets:      4 ready WebP placeholders
rotation groups:          4 HERO groups seeded / expanded pools pending
asset_registry.json:      ready, code-owned, fail-closed
```

Ten stan nie blokuje backend/read-model foundation. Do czasu przygotowania
asset packu UI używa code-owned placeholderów CSS/SVG. Pełna visual acceptance
Sprintu 135.4.1 wymaga jednak gotowego minimalnego zestawu HERO, logo,
ikonografii i co najmniej neutralnego fallbacku dla każdej użytej rodziny.


---
notes:

Jasne — z README wychodzi nam całkiem konkretny backlog assetów Googleplex News i najlepiej robić go partiami, żeby od razu domykać kolejne wymagania wizualne. 

Na start proponuję taką listę produkcyjną:

1. **BRAND — 4 assety**

   * `gp_brand_wordmark_primary` — pełne logo Googleplex News
   * `gp_brand_mark_primary` — sam znak / wersja kompaktowa
   * `gp_brand_wordmark_mono` — wersja monochromatyczna
   * `gp_brand_favicon` — mała ikona aplikacji

2. **HERO SCENES — 4 obowiązkowe sceny**

   * `gp_scene_world_neutral_01`
   * `gp_scene_world_danger_01`
   * `gp_scene_world_victory_01`
   * `gp_scene_world_defence_01`

   To są najważniejsze duże grafiki: WebP, najlepiej **1600×900 / 16:9**, bez tekstu i bez wypalonego gradientu pod tekst. Każda ma mieć wyraźnie inny klimat odpowiadający stanowi.

3. **IKONY UI — 19 SVG**

   * search
   * filter
   * grid
   * product
   * blacknet
   * ghost-exchange
   * map-focus
   * travel
   * clan
   * package
   * storage
   * cyberner
   * integrity
   * verified
   * read-only
   * warning
   * defence
   * victory
   * open

4. **NEUTRALNE ASSETY RODZIN — 11 bazowych**

   * `scene`
   * `character`
   * `tool`
   * `map`
   * `clan`
   * `package`
   * `storage`
   * `market`
   * `network`
   * `system`
   * `stamp`

   Tutaj ważna rzecz: nie każda rodzina wymaga osobnego obrazka dla danger/victory/defence — w większości przypadków stan zrobi CSS/SVG/UI, więc przede wszystkim potrzebujemy **dobrego neutralnego wzorca**. 

5. **ROTACJA HERO — jeszcze minimum 4 assety**
   README wymaga minimum dwóch pozycji w każdej grupie HERO, więc poza pierwszą czwórką potrzebujemy:

   * `gp_scene_world_neutral_02`
   * `gp_scene_world_danger_02`
   * `gp_scene_world_victory_02`
   * `gp_scene_world_defence_02`

6. **FOCUS PRODUCTS — minimum 4**
   Rodzina `tool`, pod karty LARGE/MEDIUM.
   Tu mogą wejść bardzo efektowne „produkty Googleplex”: aplikacje, terminal tools, skanery, exploitery itd.

7. **FOCUS WORLD — minimum 4**
   `map/scene`

   * fragment miasta
   * region konfliktu
   * podróż / trasa
   * obiekt lub terytorium

8. **FOCUS MARKET — minimum 4**
   `market/package`

   * paczka danych
   * zaszyfrowany kontener
   * pakiet marketplace
   * wizualizacja transakcji / rynku

9. **FOCUS NETWORK — minimum 4**
   `network/character`

   * Cyberner / sieć
   * komunikacja
   * węzły
   * postać lub operator sieciowy

10. **FOCUS SYSTEM — minimum 4**
    `system/storage/stamp`

    * integrity
    * storage
    * system state
    * verified/read-only/protocol element

Czyli jeśli liczyć tylko **konkretne minimum pierwszego pełnego packu**, mamy około:

**4 brand + 19 ikon + 8 HERO + 11 baz rodzin + 20 focus = 62 assety**, przy czym część z tych 11 baz może jednocześnie wejść do grup focus, więc realnie możemy zejść niżej, jeśli od początku będziemy je projektować wielokrotnego użytku. 

Ja bym teraz leciał kolejnością: **HERO 4 → logo 4 → neutralne assety rodzin → rotacja/focus → ikony na końcu**, bo właśnie HERO i bazowe rodziny najbardziej definiują język wizualny całego Googleplex News.
