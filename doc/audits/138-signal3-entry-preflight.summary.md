# 138.signal.3 — podsumowanie preflight entry

Źródło: `138-signal3-entry-preflight.json`, HEAD produkcyjny
`2585da54a65bcd161c7c947b68abe30180a57760`.

## Wynik raportu

Raport zwrócił `ok=false`, więc nie zezwala jeszcze na aktywację części P2.

Potwierdzone poprawne elementy:

- aktywny cykl: `ghostnetwork_0001`;
- stan wejściowy: `19/20`, P2 pozostaje `public`;
- maszyny: Echo, Sentinel i Virex `5/5`; Phantom `4/5`;
- topologia: 20 części, 20 połączeń, zamknięty ring i zgodny checksum;
- brak locka, GhostSignalu, rankingu, show i territory consumption;
- brak pending reward projection oraz delta jobs;
- SQLite `quick_check=ok`, około 89 GB wolnego miejsca;
- świeży, czytelny backup z `quick_check=ok`;
- procesy 13, 14, 17 i 18 są online;
- audyt był read-only: `mutations={}`.

## Trzy zgłoszone blokady i ich interpretacja

1. `exactly_one_conflict_blocker=false` — błąd skryptu audytowego. Skrypt czytał
   nieistniejące pole `blocking_conflicts`, podczas gdy canonical conflict gate
   zwraca `blockers`. Jednocześnie machine progress potwierdza jedną część
   Sentinel w stanie contested. Poprawiono odczyt na `conflict_gate.blockers`.
2. `no_rewards_for_active_cycle=false` — warunek był zbyt szeroki. W cyklu
   istnieje 45 prawidłowych, historycznych nagród gameplayowych, wszystkie bez
   pending projection. Preflight powinien blokować tylko istniejące nagrody typu
   `ghost_signal_*`, nie wszystkie nagrody cyklu. Warunek został zawężony.
3. `territory_executor_enabled=false` — skrypt uruchomiony z powłoki czytał env
   własnego procesu, a nie env działających procesów PM2. Ecosystem deklaruje `1`.
   Poprawiono audyt tak, aby sprawdzał wartość niezależnie w PM2 `chaos` oraz
   `chaos-territory-worker`.

## Dodatkowa obserwacja

Plan wejściowy zawiera jeden blocking warning dla P2 bez terytorium. Jest to
oczekiwane, dopóki P2 pozostaje publiczne. W trybie `--expect blocked`, już po
legalnej aktywacji P2, plan musi być kompletny i nie może zawierać żadnego
blocking warning.

## Decyzja

Stan danych wygląda zgodnie z przygotowaniem scenariusza, ale aktywacja P2 jest
wstrzymana do ponownego uruchomienia poprawionego strict preflightu i uzyskania
`ok=true`.
