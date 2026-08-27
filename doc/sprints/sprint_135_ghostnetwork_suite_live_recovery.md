# Sprint 135 — GhostNetwork Suite live deltas i recovery

Status: `SPRINT 135 — READY FOR SERVER VALIDATION`

## Zakres wykonany

- Suite rejestruje adapter w istniejącym `GhostNetworkDeltaClient`.
- Mapa i Suite zachowują osobne baseline bez obniżania wspólnej state version.
- Backend publikuje bezpieczną `suite_part_projection` obok projekcji mapowej.
- Lifecycle delty zastępują kartę, przeliczają grupy/liczniki i nie wykonują
  pełnego reloadu.
- Visibility cutover usuwa stare pola identity/location przez replacement,
  nigdy przez merge.
- Consumed usuwa kartę przez opaque `public_entity_id` bez wycieku wewnętrznego
  `part_id`.
- Nieznana lub zbiorcza zmiana uruchamia bounded recovery z `view=suite`.
- Recovery zachowuje UI i nie uruchamia mapy ani SFX.
- Zamknięcie okna usuwa adapter i retry, pozostawiając shared client dla mapy.
- Globalne recovery scope `ghostnetwork` obejmuje równocześnie otwartą mapę i
  otwarte Suite.

## Invarianty

```text
delta jednej części -> replacement jednej projekcji -> regroup -> render
visibility downgrade -> brak starych sekretów w modelu i DOM
unknown/gap/cycle cutover -> suite snapshot recovery
snapshot/recovery -> SFX 0
close -> Suite adapter 0, shared client nadal aktywny
profile full read/write -> 0
additional poller -> 0
```

## Walidacja

- pełna regresja `test_ghostnetwork*.py`: 231/231,
- Victim Picker, Territory Control, Operation Control, territory delta i session
  isolation/precommit: 93/93,
- wszystkie pakiety JavaScript: 18/18,
- `py_compile ghostnetwork/deltas.py`: OK,
- `node --check` dla shared clienta, map adaptera i terminala: OK,
- `git diff --check`: OK.

Bez deployu, restartu PM2, produkcyjnych mutacji i commita.

## Manual server validation

1. Otworzyć mapę i Suite; lifecycle jednej części ma zmienić oba widoki bez
   pełnego przeładowania i bez podwójnego SFX.
2. `public -> blocked` dla foreign viewer: karta traci identity i exact location,
   przechodzi do BLOKOWANE, a mapa/teleport używają terytorium.
3. `contained -> active`: karta przechodzi do AKTYWNE i pozostaje pojedyncza.
4. Consumed usuwa kartę; offline/catch-up kończy się tym samym snapshotem.
5. Zasymulowana luka/restart odtwarza Suite przez `view=suite`, zachowując filtr,
   scroll oraz rozwinięcie, bez otwarcia mapy i bez lifecycle SFX.
6. Zamknąć i otworzyć Suite kilka razy: dokładnie jeden aktywny adapter, brak
   wzrostu liczby requestów `/api/state/changes`.
