# Sprint 116 - GhostNetwork: emisja czesci po skutecznym hacku

## Zakres wdrozony

Sprint 116 domknal pierwszy realny moment wejscia czesci GhostNetwork do swiata:
aktywnie zarezerwowana czesc moze zostac zatwierdzona dopiero po kanonicznym
sukcesie przejecia celu.

Wdrozone elementy:

* `GhostNetworkService.on_target_hacked(player, target, operation, result, context)`;
* repozytoryjny commit odkrycia `discover_reserved_part(...)`;
* odszukanie aktywnej rezerwacji po `cycle_id`, `player_id`, `target_id` oraz
  preferencyjnie `operation_id`;
* atomowe przejscie rezerwacji `active -> committed`;
* atomowe przejscie czesci `reserved -> public`;
* trwala kotwica czesci na celu: `target_id`, `latitude`, `longitude`;
* audyt odkrycia: `discovered_by`, `discovered_clan`,
  `discovery_operation_id`, `anchor_snapshot_json`;
* event domenowy `ghost.part_discovered`;
* idempotencja przez dedupe key `discover:<cycle>:<part>:<operation>` albo
  `discover:<cycle>:<target>`;
* diagnostyka integralnosci publicznych czesci i rezerwacji;
* hook w `/gonna-win` po `territory_store.save_captured_target(...)`.

## Kanoniczny punkt sukcesu

Hook GhostNetwork zostal podpiety w `/gonna-win`, po zapisaniu celu przez:

```text
territory_store.save_captured_target(...)
```

To jest backendowy moment, w ktorym zwykly gameplay uznaje obiekt za przejety.
Hook nie jest podpinany do klikniecia, animacji, frontendu, samego startu
operacji ani `aimed_target`.

## Zasady bezpieczenstwa

Emisja czesci nie zachodzi, gdy:

* nie ma aktywnego cyklu;
* cykl nie ma statusu `active`;
* target nie jest kwalifikowalny;
* brak aktywnej rezerwacji;
* rezerwacja wygasla;
* wynik nie zawiera finalnego `target_captured`;
* czesc nalezy do klanu gracza;
* target nie ma poprawnych wspolrzednych;
* ten target juz wyemitowal czesc.

Blad GhostNetwork nie cofa zwyklego przejecia celu.

## Poza zakresem

Nadal nie wdrozono:

* publicznych markerow czesci na mapie;
* linii topologii;
* RSP lub nagrod za odkrycie;
* aktywacji terytorialnej;
* supermocy czesci;
* BlackNetu, Cybernera i Radia dla czesci.

## Walidacja

Uruchomiono:

```text
python -m py_compile run.py config.py ghostnetwork\repository.py ghostnetwork\service.py ghostnetwork\reservations.py
python -m unittest tests.test_ghostnetwork_repository tests.test_ghostnetwork_catalog tests.test_ghostnetwork_cycle_service tests.test_ghostnetwork_topology tests.test_ghostnetwork_reservations tests.test_ghostnetwork_discovery
```

Wynik:

```text
OK - 56 testow GhostNetwork
```
