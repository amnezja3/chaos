# Sprint 133 — GhostNetwork Suite desktop

**Status:** `SPRINT 133 — COMPLETE`

## Zakres

Sprint buduje lekką, desktopową aplikację `ghostnetworkSuite` na projekcji
`GET /api/ghostnetwork/snapshot?view=suite` przygotowanej w Sprincie 132.
Produkt należy do rodziny `ghost_control_suite` razem z Victim Picker,
Territory Control i Operation Control.

Kontrakt produktu:

- cena: `10 000 HC`,
- konto zakupu/fallback: `admin`,
- launcher: `createGhostNetworkSuiteApp`,
- jedna instancja okna i integracja z taskbarem,
- brak odczytu pełnego profilu,
- brak uruchamiania mapy i teleportu w Sprincie 133.

## Widok

Aplikacja prezentuje filtry: wszystkie, publiczne, blokowane, aktywne i moja
kontrola. Korzysta wyłącznie z pól ujawnionych przez projekcję suite. Wyszukiwarka
nie indeksuje ukrytej tożsamości, profesji ani zdolności.

Akcje MAPA i TELEPORT pozostają wyłączone i nie mają handlerów sieciowych.
Ich canonical bridge należy do późniejszego zakresu.

## Walidacja

- kontrakt produktu, ceny i odbiorcy HC,
- podział referencji na sekcje bez duplikacji,
- aktywna część foreign pozostaje widoczna w sekcji aktywnych,
- brak wyszukiwania po ukrytej tożsamości,
- tylko endpoint `view=suite`, bez `/api/profile`, mapy i teleportu,
- pojedyncza instancja okna,
- `py_compile`, `node --check`, `git diff --check`.

Wynik lokalny 2026-08-27:

- 15/15 testów produktu i projekcji suite — OK,
- 34/34 testy Victim Picker, Territory Control i Operation Control — OK,
- 15/15 skryptów regresyjnych JavaScript — OK,
- `py_compile`, `node --check`, `git diff --check` — OK.

Nie wykonano deployu, restartu PM2 ani commita.

Manual serwerowy potwierdził poprawną instalację, widoczność części i filtry.
