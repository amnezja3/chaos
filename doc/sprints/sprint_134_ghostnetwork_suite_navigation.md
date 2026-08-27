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
