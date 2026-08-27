# Sprint 134 — GhostNetwork Suite: mapa, teleport i Territory Control

**Status:** `SPRINT 134 — READY FOR SERVER VALIDATION`

Sprint podłącza jawne akcje nawigacyjne do bezpiecznej projekcji przygotowanej
w Sprintach 132–133. Mapa jest otwierana wyłącznie po kliknięciu. Teleport wysyła
opaque `public_entity_id` albo `territory_id`; backend ponownie rozwiązuje cel
według aktualnej visibility projection i ignoruje współrzędne klienta.

## Wiążąca korekta UX

Przyciski GhostNetwork Suite używają ikon zgodnych z Territory Control:

- mapa: `▣`,
- teleport: `➜`.

Nie pokazują napisów `MAPA` ani `TELEPORT`. Dostępność zachowują przez `title`,
`aria-label`, focus oraz wyjaśniony stan disabled.

## Bramka bezpieczeństwa

- brak pełnego profilu w hot path,
- brak klientowych współrzędnych w teleport request,
- ukryta część przekazuje wyłącznie `territory_id`,
- focus i teleport nie zmieniają `aimed_target`,
- map bridge nie uruchamia mapy przed jawnym kliknięciem.

Manual doprecyzował, że focus centruje marker części, natomiast teleport prowadzi
do stabilnego punktu w jej okolicy. Po zaakceptowaniu dialogu i canonical success
teleport otwiera mapę na motocyklu; przed zgodą mapa pozostaje zamknięta.

Fokus z zamkniętej mapy jest przechowywany do zakończenia bootu odpowiedniej warstwy. Gotowość terytoriów ponawia fokus ukrytej części, a publikacja snapshotu GhostNetwork ponawia fokus dokładnego węzła; początkowy widok motocykla nie może już wygasić intencji użytkownika.

## Implementacja i walidacja

- dokładna część centruje marker i otwiera bezpieczny panel,
- ukryta część centruje poligon terytorium bez współrzędnych kotwicy,
- teleport dokładnej części i terytorium używa canonical server resolution,
- teleport aktualizuje otwartą mapę i odświeża otwarte narzędzia Ghost Control,
- Territory Control pokazuje canonical badge i szczegóły GN,
- 65/65 testów GN/Territory — OK,
- 13/13 testów endpoint/session — OK,
- 16/16 pakietów regresyjnych Node — OK,
- `py_compile`, `node --check`, `git diff --check` — OK.

Bez deployu, restartu PM2 i commita.

## Korekta po pierwszym manualu

- focus nadal centruje dokładny marker części,
- teleport dokładnej części wybiera deterministyczny punkt 28–46 m od kotwicy,
- obowiązuje kolejność: zgoda → canonical request → success → otwarcie mapy →
  focus motocykla,
- pointer/click akcji nie propaguje do pulpitu ani launchera mapy,
- sentinel konfliktu `none` nie jest renderowany,
- summary identyczne z głównym labelem nie jest renderowane drugi raz.

Ponowna walidacja: 65/65 GN/Territory, 3/3 canonical teleport, 16/16
pakietów Node oraz kontrole składni/diffu — OK.

Manual potwierdził teleport z otwarciem mapy na małych i dużych kontach.
Kolejna korekta responsywna usuwa nested scroll: całe wnętrze Suite jest jednym
przewijanym dokumentem, a lista kart ma `overflow: visible`.
