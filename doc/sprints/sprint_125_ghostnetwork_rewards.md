# Sprint 125 - GhostNetwork Contribution + Reward Ledger

## Cel

Sprint 125 dodaje uczciwy ledger wkładu i nagród GhostNetwork bez tworzenia
drugiej waluty, drugiego systemu poziomow ani osobnego stanu profilu.

Zrodlem prawdy pozostaje repository GhostNetwork oraz istniejacy profil gracza.
GhostNetwork moze zapisac wklad i przygotowac nagrode, ale RSP trafia do
istniejacego pola `respect`.

## Wdrozone komponenty

* `GhostContributionService`
* `GhostRewardService`
* `GhostClanReputationPolicy`
* `resolve_standard_operation_rsp(profile, context)`
* rozszerzone tabele:
  * `ghost_contributions`
  * `ghost_reward_ledger`
  * `ghost_clan_reputation`

## Kontrakt wkładu

Wklad zapisuje fakt udzialu, nawet jesli nagroda zostanie odrzucona albo wyniesie
`0`.

Publiczne wejscia:

* `record_contribution(...)`
* `list_player_contributions(...)`
* `list_cycle_contributions(...)`
* `aggregate_player_contribution(...)`
* `aggregate_clan_contribution(...)`

Wpisy sa deduplikowane przez `dedupe_key`.

## Kontrakt nagród

Nagroda jest osobnym wpisem ledgeru i moze przejsc przez statusy:

* `pending`
* `applied`
* `rejected`
* `failed`
* `cancelled`

Publiczne wejscia:

* `evaluate_event_reward(...)`
* `create_reward_entry(...)`
* `apply_pending_reward(...)`
* `apply_pending_rewards(...)`
* `get_player_reward_summary(...)`
* `reconcile_ghost_rewards(...)`

`reward_key` blokuje podwojna wyplate RSP dla tego samego strategicznego
zdarzenia. Dla odkrycia, pierwszego otoczenia, pierwszej aktywacji i odzyskania
klucz jest zwiazany z czescia, graczem i typem nagrody, a nie z retry eventu.

## Zdarzenia domenowe

Dodano publikacje eventow:

* `ghost.contribution_recorded`
* `ghost.reward_pending`
* `ghost.reward_applied`
* `ghost.clan_reputation_changed`
* `ghost.player_history_changed`

Sa to eventy informacyjne. Nie sa drugim magazynem stanu.

## Decyzje

* profil nie przechowuje bieżącego stanu czesci ani maszyn;
* ledger nagrod nie ustawia LVL bezposrednio;
* RSP trafia do istniejacego pola `respect`;
* reputacja klanowa nie jest waluta;
* spokojne nagrody hold sa wstrzymywane podczas konfliktu zgodnie z configiem;
* foreign hold nie daje stalej nagrody za utrzymanie;
* recovery w tym sprincie dziala jako dry-run i wykrywa niespojnosci.

## Poza zakresem

* szczegolowa obrona;
* odbicia;
* antyfarming par graczy;
* koncowa nagroda transmisji;
* finalny balans mnoznikow;
* osobny UI historii nagrod.

## Walidacja

Dodano `tests/test_ghostnetwork_rewards.py`.

Pokrycie:

* idempotencja wkladu;
* agregaty gracza i klanu;
* odkrycie czesci placi RSP dokladnie raz;
* retry odkrycia nie placi ponownie;
* pierwsze otoczenie i aktywacja maja oddzielne reward key;
* hold reward jest okresowy;
* konflikt wstrzymuje hold reward;
* obcy hold nie daje stalej nagrody;
* zastosowana nagroda zwieksza reputacje klanu;
* recovery dry-run wykrywa wklad bez rewardu.

