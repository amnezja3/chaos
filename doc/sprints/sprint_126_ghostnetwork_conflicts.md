# Sprint 126 - GhostNetwork: defense, recovery and reward safety

## Cel

Sprint 126 dodaje warstwe rozpoznawania prawdziwych obron i odbic czesci
GhostNetwork. Mechanika nie zmienia wlasnosci terytorium, geometrii mapy ani
stanu profilu gracza. Oceniany jest tylko strategiczny konflikt i to, czy
powinien powstac reward w istniejacym ledgerze RSP.

## Zrodla prawdy

* Wlasnosc i geometria terytorium: istniejacy system terytoriow.
* Cykl, czesci, eventy i ledger: `ghostnetwork`.
* Profil: tozsamosc, RSP/respect i historia po zastosowaniu rewardu.

`GhostStrategicConflictService` nie rozstrzyga, kto przejal teren. Przyjmuje
potwierdzony stan koncowy i ocenia, czy byl to realny konflikt, obrona albo
odbicie.

## Wdrozone elementy

* `GhostDefenseRewardPolicy`
* `GhostStrategicConflictService`
* `ghost_strategic_conflicts`
* `ghost_conflict_actions`
* `ghost_control_periods`
* `ghost_part_transfer_history`
* konfiguracja progow i cooldownow w `config.py`
* fasada w `GhostNetworkService`
* eksport kontraktow w `ghostnetwork/__init__.py`
* testy `tests/test_ghostnetwork_conflicts.py`

## Zdarzenia

Dodane albo przygotowane zdarzenia:

* `ghost.defense_started`
* `ghost.defense_progress_changed`
* `ghost.part_defended`
* `ghost.part_recovered`
* `ghost.reward_reduced`
* `ghost.reward_flagged`

Payload publiczny nie zawiera `part_code`, `machine_code` ani
`profession_code`, zeby media i BlackNet nie ujawnialy ukrytej tozsamosci
czesci.

## Zasady kwalifikacji

Obrona wymaga:

* potwierdzonego konfliktu,
* potwierdzonej aktywnosci ofensywnej,
* potwierdzonej aktywnosci defensywnej,
* minimalnego progu ataku albo utraty integralnosci,
* powrotu do stabilnego stanu tego samego wlasciciela albo klanu.

Odbicie wymaga:

* poprzedniego stabilnego okresu kontroli obcego klanu,
* realnego rozbrojenia lub ataku,
* powrotu czesci do wlasciwego klanu,
* stanu aktywnego po odzyskaniu.

Nieistotny atak zostaje w historii, ale nie tworzy pelnej nagrody.

## Zabezpieczenia antyfarmowe

* Dedupe konfliktow, akcji i historii transferow.
* Idempotentne rozstrzyganie konfliktu.
* Limit lacznej puli RSP dla obrony i odbicia.
* Cooldown par wlascicieli A/B przy szybkich powrotach.
* Statusy oceny: `full_reward`, `reduced_reward`, `cooldown`, `review`,
  `no_reward`.

Ograniczana jest nagroda, nie sama mozliwosc przejecia czesci.

## Poza zakresem

* automatyczne bany,
* panel moderatorski,
* finalne nagrody transmisji,
* los GhostSignalu,
* zmiany geometrii albo wlasnosci terytoriow,
* pelny anty-multikonto.

## Walidacja

Testy sprintu sprawdzaja:

* realna obrone z nagroda wlasciciela i supportu,
* brak pelnej nagrody przy malym ataku,
* odbicie po wczesniejszej obcej kontroli,
* cooldown przy szybkiej parze wlascicieli,
* idempotencje retry,
* brak ukrytych danych czesci w publicznym payloadzie.
