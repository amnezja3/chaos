# BlackNet Prototype Audit - Sprint 74

## Cel

Zamienic prototyp `bn_page.tsx` + `globals.css` w kontrakt implementacyjny
BlackNetu dla CHAOS.

Sprint 74 nie wdraza runtime BlackNetu. To audyt, decyzje i kontrakt.

## Wejscie

Przeanalizowane pliki:

* `static/js/bn_page.tsx`,
* `static/css/globals.css`,
* `doc/blacknet.md`,
* `doc/game_play_260626.md`.

## Charakter prototypu

Prototyp nie jest klasyczna strona internetowa.

To signal bus:

```text
sygnal swiata
↓
radar / status / timer / CTA
↓
inspiracja gameplayowa
↓
przejscie do systemu CHAOS
```

BlackNet ma inspirowac gracza do dzialania, a nie tworzyc drugi system zadan.

## Model danych prototypu

Obecny typ `Signal`:

```text
id
channel
title
label
value
stat
timer
cta
tone
layout
radarSides
nodes
```

Znaczenie:

* `id` - stabilny identyfikator sygnalu.
* `channel` - widoczne zrodlo / kanal BlackNet.
* `title` - glowny temat sygnalu.
* `label` - etykieta metryki.
* `value` - duza wartosc / headline stat.
* `stat` - dodatkowy opis liczbowy.
* `timer` - czas waznosci / okno okazji.
* `cta` - tekst akcji.
* `tone` - kolorystyka nastroju.
* `layout` - wariant kompozycji.
* `radarSides` - ksztalt radaru.
* `nodes` - punkty radaru.

## Kontrakt v0: `blacknet_signal`

Docelowy kontrakt powinien byc jawny i niezalezny od renderera:

```json
{
  "schema": 1,
  "id": "market-gps",
  "source": "ghost_market_watch",
  "channel": "Ghost Market Watch",
  "title": "GPS Logs / Warszawa",
  "label": "Potencjal ceny",
  "value": "+34%",
  "stat": "62 pakiety w ruchu",
  "timer": "08:18",
  "tone": "cyan",
  "layout": 2,
  "radar": {
    "shape": "polygon",
    "sides": 4,
    "nodes": [[19, 57, 2], [31, 31, 4]]
  },
  "cta": {
    "label": "Otworz Ghost Exchange",
    "target": "ghost_exchange",
    "enabled": true
  }
}
```

## Minimalne pola v0

Wymagane:

* `schema`,
* `id`,
* `source`,
* `title`,
* `label`,
* `value`,
* `stat`,
* `tone`,
* `cta`.

Opcjonalne:

* `channel`,
* `timer`,
* `layout`,
* `radar`,
* `expires_at`,
* `priority`,
* `region`,
* `tags`.

## Tone

Prototyp ma cztery tony:

* `lime` - neutralny / informacyjny / okazja.
* `cyan` - rynek / dane / telemetry.
* `amber` - drop / promocja / ograniczona dostepnosc.
* `red` - ryzyko / konflikt / PvP.

Tone jest elementem prezentacji, nie logika gameplayowa.

## Layout

Prototyp posiada warianty `layout` 1-6.

W Sprincie 75-76 trzeba je przeniesc jako klasy CSS CHAOS, ale renderer nie
powinien kodowac sensu sygnalu po numerze layoutu.

## Radar

Radar jest komponentem wizualnym.

W prototypie sklada sie z:

* grid,
* frame,
* accent,
* links,
* nodes,
* satellites,
* core,
* sweep.

Radar nie jest mapa i nie powinien miec w Sprincie 75-76 realnej logiki mapowej.

## Nawigacja

Prototyp obsluguje:

* strzalki,
* WASD,
* pointer drag / swipe,
* przyciski kierunkowe.

W CHAOS v0 wystarczy:

* next,
* previous,
* swipe na mobile,
* klawiatura na desktopie.

## CTA

CTA nie tworzy nowych systemow.

Mapowanie v0:

* `ghost_exchange` -> otworz istniejacy Ghost Exchange.
* `googleplex` -> otworz istniejacy Googleplex.
* `map` -> otworz mape / wskaz region, jesli istnieje bezpieczna sciezka.
* `cyberner` -> otworz istniejacy Cyberner/thread, jesli istnieje.
* `radio` -> otworz Ghost Hack Radio / kanal BlackNet radio, jesli istnieje.
* `disabled` -> pokaz stan niedostepny.

CTA nie generuje misji, operacji ani marketu.

## Elementy UI z prototypu

Do zachowania:

* `BLACKNET` brand,
* channel badge,
* signal strength,
* radar,
* metric headline,
* timer,
* CTA,
* footer counter,
* swipe/keyboard hints.

Do adaptacji:

* styl `Impact` moze byc zbyt obcy dla CHAOS,
* globalne style `html, body` nie moga wejsc do `style.css` bez scope,
* `@import "tailwindcss"` nie pasuje do obecnego runtime,
* klasy musza byc scopingowane, np. `blacknet-*`.

## Problemy prototypu

1. Mojibake w copy:
   * `KANAĹ`,
   * `MOKOTĂ“W`,
   * `PRZECHWYÄ†`,
   * `SYGNAĹ`.
2. Prototyp zaklada React/Next:
   * `use client`,
   * `useState`,
   * `useEffect`,
   * JSX.
3. CSS jest globalny:
   * `html, body`,
   * `button`,
   * `h1`.
4. Nie ma kontraktu source/CTA.
5. Dane sa hardcoded w rendererze.

## Frontend-only w najblizszych sprintach

Moze zostac frontend-only:

* radar,
* animacje,
* layouty,
* nawigacja karuzeli,
* signal strength,
* tymczasowe lokalne sygnaly.

## Wymaga read modelu pozniej

Wymaga osobnego read modelu dopiero po v0:

* realne trendy Ghost Exchange,
* regiony mapy,
* aktywnosc PvP,
* aktywne operacje,
* wygasanie sygnalow,
* AI digest,
* sygnaly personalizowane pod profil.

## Decyzje Sprintu 74

* BlackNet v0 jest signal bus, nie forum i nie drugi marketplace.
* `blacknet_signal` jest kontraktem danych, nie komponentem UI.
* Prototyp nalezy przepisac do natywnego runtime CHAOS.
* CSS musi byc scopingowany.
* CTA prowadza tylko do istniejacych systemow.
* AI content generation pozostaje poza zakresem Fazy H v0.

## Status

Sprint 74 gotowy jako audyt i kontrakt. Kolejny krok: Sprint 75 - BlackNet
Static App Shell.
