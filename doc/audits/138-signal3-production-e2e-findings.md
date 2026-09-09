# 138.signal.3 — audyt pierwszego produkcyjnego GhostSignalu

Data: 2026-09-09  
Cykl: `ghostnetwork_0001`  
Wynik scenariusza: **E2E FAIL / P0 premature transmission**  
Wynik skutków post-commit: **COMPLETE**

## Przebieg potwierdzony

1. Entry preflight był poprawny i read-only: `19/20`, jedna publiczna część,
   dokładnie jeden blocker `territory_conflict_5145c32c3e634c66` na S1, brak
   locka, sygnału, nagród oraz pending endgame work.
2. Ostatnią część aktywowano normalnym gameplayem. Immutable lock wskazuje P3,
   gracza `iasny`, klan `phantom_mesh` i territory `450134` jako closer.
3. Nie uzyskano wymaganego checkpointu `20/20 + conflict blocked`. Generic
   territory reconciliation wyczyściło projekcję konfliktu S1. Lock powstał
   `2026-09-09T14:24:40.266174+00:00` już z pustą listą konfliktów.
4. Produkcyjny konflikt nie został wcześniej rozwiązany przez gracza. Signal
   ruszył automatycznie, a konflikt został rozstrzygnięty dopiero jako skutek
   konsumpcji terytorium. Jest to odwrócenie wymaganej kolejności.
5. GhostSignal wysłano o `2026-09-09T14:24:42.174376+00:00`. Uruchomił się
   globalny show `ghost_show_13a1d78f794c6b62ecca`, wersja `1.0.1 -> 1.0.2`,
   a Signal Registry pojawił się na pulpicie.
6. Po show cykl zamknięto o `2026-09-09T14:39:42.928618+00:00` i utworzono
   dokładnie jeden aktywny cykl `ghostnetwork_0002`.

## Skutki mechaniczne

- 20/20 części ma stan `consumed` i poprawne `consumed_signal_id`;
- 20 historycznych node snapshots zapisano;
- 20 połączeń zamknięto;
- plan obejmował 23 terytoria: 20 `primary` i 3 `allied_overlap`;
- wykonano 23/23 receipts konsumpcji;
- immutable reward plan zawierał 20 node-holder, 23 territory i 1 closer;
- settlement widzi 44/44 właściwe nagrody sygnałowe;
- pełny ledger cyklu zawiera 90 rekordów `applied`, ponieważ obejmuje również
  wcześniejsze nagrody cyklu, a nie tylko finałowy plan;
- ranking istnieje, checksum rankingu jest poprawny;
- all-time odbudowuje się z jednego snapshotu: 8 graczy i 4 klany;
- show zakończony, pending work puste, hard settlement `ok=true`.

Sam stan po sygnale jest mechanicznie spójny i nie wymaga rollbacku naprawczego.
Jednak dalsza bramka `138.2` wymaga prawdziwego producer-backed `ghost.signal_sent`
oraz powstałych z niego tasków Ollamy. Pozostawienie `ghostnetwork_0002` odebrałoby
testowi jego canonical trigger. Dlatego program testowy wymaga kontrolowanego,
pełnego restore bazy do zweryfikowanego snapshotu sprzed emisji — po zachowaniu
obecnej bazy jako forensic post-signal. Nie wolno odtwarzać wyłącznie tabel
GhostNetwork ani ręcznie wstrzykiwać eventu lub tasków.

Snapshot restore musi offline potwierdzić: cykl `ghostnetwork_0001` active,
`19/20`, jedną publiczną część zamykającą, realny otwarty konflikt S1, brak
lock/signal/show/ranking/consumption oraz GhostSystem `1.0.1`. Dopiero po deployu
P0 fixu i takim restore można powtórzyć pełną sekwencję, włącznie z linią
`ghost.signal_sent -> Ollama task -> candidate -> receipt -> medium record`.

Kandydatem wybranym do restore jest
`data/backups/game-pre-138-signal3-20260909T115552Z.sqlite3`. Backup
`game_pre_135_2_20260828_074012.sqlite3` jest zbyt stary i pozostaje wyłącznie
historycznym punktem recovery; jego użycie cofnęłoby również sprinty 135–138.

## Dwa fałszywe alarmy pierwszej wersji postflightu

Pierwszy raport wskazał `required_events_exactly_once=false` oraz
`signal_checksum_valid=false`. Oba wynikały z błędów audytora:

- timeline `list_events(..., limit=5000)` jest kanonicznie ograniczony do 1000
  najstarszych eventów, więc nie zawierał końcowych zdarzeń cyklu;
- audyt liczył SHA-256, podczas gdy transmisja zapisuje SHA-1 z canonical
  `dumps_json`.

Postflight używa teraz selektywnego, nieuciętego odczytu wymaganych typów eventów
i wspólnej funkcji checksumu transmisji.

## Przyczyna P0

`bridge_ghostnetwork_territory_publication()` wykonywał generic rebuild `areas`
i przekazywał wynik do `maybe_finalize_ghostnetwork_cycle()`. Adapter uznawał
każdy zwykły wynik `active/contained/public` za dowód rozwiązania stanu
`contested` i wywoływał `resolve_after_conflict()`. Closure ufał następnie tylko
projekcji GhostNetwork/strategic conflicts i nie sprawdzał niezależnie otwartego
rekordu w `territory_conflicts`.

## Zabezpieczenie

- generic territory reconcile nie ma prawa czyścić `conflict_state`;
- tylko jawna publikacja `resolved/closed` otrzymuje `resolve_conflicts=true`;
- release obszaru nie rozbraja części zamrożonej konfliktem;
- closure wykonuje drugi, niezależny gate na produkcyjnych statusach
  `detected/active/changing/resolving`, powiązanych przez conflict ID lub
  territory ID;
- postflight sprawdza, czy każdy produkcyjny konflikt dotyczący terytoriów
  locka był rozwiązany nie później niż `locked_at`.

Surowy raport dowodowy pozostaje w
`doc/audits/138-signal3-postflight-ghostnetwork_0001.json`.
