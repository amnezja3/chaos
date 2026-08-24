# WebDragons External Browser Plan

## Cel

Przygotowac WebDragons jako hybrydowy browser CHAOS:

* fikcyjne adresy `xhttp://...` renderuja lokalne aplikacje gry,
* prawdziwe adresy `https://...` moga otwierac zewnetrzne strony w iframe,
* `xhttp://webdragons.hck` zawsze wraca do lokalnego WebDragons.

## Zasada

WebDragons nie staje sie pelna przegladarka internetowa.

To nadal okno gry z routerem adresow:

```text
adres
↓
route local / external
↓
render CHAOS app albo iframe
```

## Routing v0

* `xhttp://webdragons.hck` -> Googleplex / Ghost Exchange.
* `webdragons`, `home`, pusty adres -> `xhttp://webdragons.hck`.
* `https://heretyk.smallhost.pl` -> external iframe, jesli strona pozwala.
* inne zewnetrzne adresy -> allowlist albo komunikat blokady.

## UI

* pasek adresu aktywny,
* Enter nawiguje,
* przyciski back / forward korzystaja z historii WebDragons,
* dropdown zakladek:
  * WebDragons,
  * Heretyk,
  * przyszle strony CHAOS / BlackNet,
* komunikat, gdy strona nie pozwala na iframe.

## Ograniczenia

Nie kazda strona pozwoli na osadzenie w iframe.

Blokady moga wynikac z:

* `X-Frame-Options`,
* `Content-Security-Policy: frame-ancestors`.

Dla wlasnych stron produkcyjnych nalezy ustawic naglowki tak, aby dopuszczaly
osadzenie z domeny CHAOS.

## Backend

Sprint v0 moze byc frontend-only.

Opcjonalnie pozniej:

* lista zakladek w configu,
* allowlist domen,
* per-profile favorite sites.

## Poza zakresem v0

* pelny internet browser,
* proxy backendowe,
* obchodzenie zabezpieczen iframe,
* zapisywanie historii w profilu,
* integracja z BlackNet.

## Kryteria przyszlego sprintu

* `xhttp://webdragons.hck` nadal dziala jako lokalny adres.
* Wpisanie zewnetrznego URL probuje otworzyc iframe.
* Back / forward dzialaja w historii WebDragons.
* Dropdown adresow pozwala skoczyc do znanych stron.
* Blokada iframe pokazuje czytelny komunikat i opcje otwarcia poza CHAOS.
