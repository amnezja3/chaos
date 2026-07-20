# Sprint 124 - GhostNetwork: supermoce profesji i rejestr efektow

## Cel

Sprint 124 dodal centralny `GhostAbilityRegistry`, ktory rozstrzyga dostep do
supermocy profesji na podstawie aktualnego stanu czesci GhostNetwork.

Kanoniczna zasada:

```text
klan gracza + profesja + aktywny modul = aktywna supermoc
```

Rejestr nie zapisuje aktywnej mocy w profilu gracza. Profil pozostaje tylko
zrodlem tozsamosci: klan, profesja, player id i kontekst requestu.

## Zrodla prawdy

Rejestr korzysta z istniejacych modeli:

* katalogu GhostNetwork z 20 czesciami, profesjami i ability_code;
* aktywnego cyklu GhostNetwork;
* stanu czesci wyliczanego przez `GhostModuleStateService`;
* snapshotu repozytorium GhostNetwork.

Nie powstal drugi magazyn stanu profesji.

## Warunek aktywacji

Ability jest aktywne tylko wtedy, gdy:

* gracz ma poprawny klan;
* profesja nalezy do tego klanu;
* katalog laczy profesje z konkretna czescia;
* czesc istnieje w aktywnym cyklu;
* `module_state == active`;
* cykl nie jest zamkniety i nie jest po transmisji.

Wlasciciel terytorium nie musi miec tej profesji. Aktywna czesc uruchamia moc
dla wszystkich czlonkow odpowiedniego klanu z pasujaca profesja.

## Kontrakt

`GhostAbilityRegistry` udostepnia:

* `register(effect)`;
* `get(ability_code)`;
* `list_for_clan(clan_code)`;
* `resolve_player_abilities(player_context)`;
* `is_ability_active(player_context, ability_code)`;
* `collect_effects(effect_type, context)`;
* `apply_modifier(effect_type, context, value)`.

Cache jest kluczowany przez:

* `cycle_id`;
* `state_version`;
* `player_id`;
* `clan_code`;
* `profession_code`.

Zmiana stanu czesci zmienia `state_version`, wiec stare rozstrzygniecie nie jest
ponownie uzywane.

## Adaptery

Dodano lekkie adaptery domenowe:

* `market`;
* `hack`;
* `territory`;
* `operation`;
* `visibility`;
* `cyberner`;
* `generic`.

Adaptery sa punktem integracji dla Sprintow 125+ i na tym etapie nie zmieniaja
jeszcze balansu. `apply_modifier()` pozostaje bezpiecznym no-op, dopoki dana
mechanika nie zostanie wdrozona jawnie.

## Ochrona kontraktu

Nie dodano:

* `active_superpowers`;
* `profession_power_enabled`;
* kopii `module_state` do profilu;
* trwalego bonusu czesci w profilu;
* rozproszonych `if clan` / `if profession` w endpointach.

Konflikt nie wylacza mocy, jezeli zamrozony stan modulu pozostaje aktywny.
Utrata aktywnej czesci natychmiast wylacza dostep przy kolejnym resolve.

## Walidacja

Dodano `tests.test_ghostnetwork_abilities`.

Pokryto:

* brak aktywnej czesci;
* aktywna czesc i poprawna profesja;
* zly klan albo zla profesja;
* wlasciciel bez pasujacej profesji;
* konflikt z zamrozonym aktywnym stanem;
* utrate czesci;
* zamkniecie albo transmisje cyklu;
* centralne `collect_effects()` i `apply_modifier()`.

## Poza zakresem

Sprint 124 nie wdraza jeszcze finalnych liczb balansu, aktywnych komend,
instancji efektow, UI supermocy, nagrod ani ekonomii GhostNetwork.
