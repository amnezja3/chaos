# Sprint 115 - GhostNetwork Reservations Audit

## Cel

Sprint 115 podlaczyl GhostNetwork do istniejacego oznaczania celu.
Oznaczenie celu moze teraz wewnetrznie i niewidocznie zarezerwowac jedna
czesc z aktywnej puli GhostNetwork.

## Wdrozone

* `GhostReservationService` z hookiem `on_target_aimed(...)`.
* `GhostDropPolicy` sterowany konfiguracja:
  * `CHAOS_GHOSTNETWORK_DROPS_ENABLED`,
  * `CHAOS_GHOSTNETWORK_DROP_CHANCE`,
  * `CHAOS_GHOSTNETWORK_RESERVATION_TTL_SECONDS`.
* Wspolny helper `set_player_aimed_target(...)` w `run.py`.
* Bezpieczny wrapper `safe_ghostnetwork_on_target_aimed(...)`.
* Integracja po poprawnym zapisie celu z:
  * map hack-action target flow,
  * player target mark,
  * Victim Picker aim.
* Atomowe przejscie czesci `pooled -> reserved`.
* Zwolnienie/wygasniecie rezerwacji z powrotem do `pooled`.
* Wewnetrzne zdarzenia:
  * `ghost.part_reserved`,
  * `ghost.part_reservation_attached`,
  * `ghost.part_reservation_released`,
  * `ghost.part_reservation_expired`.
* Diagnostyka `get_reservation_status(...)`.
* Rozszerzony `health_check()` o integralnosc rezerwacji.

## Zasady bezpieczenstwa

* GhostNetwork pozostaje globalnym modulem swiata, nie profile cache.
* Rezerwacja nie trafia do publicznego `aimed_target`.
* Blad hooka nie blokuje oznaczenia celu ani hackowania.
* Produkcyjnie dropy sa domyslnie wylaczone.
* Powtorne oznaczenie tego samego celu przez tego samego gracza zwraca
  istniejaca rezerwacje wewnetrznie bez rerollu i bez przedluzania TTL.
* Drugi gracz nie przejmuje aktywnej rezerwacji tego samego targetu.
* Czesci klanu gracza nie sa rezerwowane dla tego gracza.
* Rezerwacje z nieaktywnych cykli sa zwalniane recovery.

## Poza zakresem

Nie wdrozono:

* emisji czesci po hacku,
* publicznych markerow GhostNetwork,
* BlackNet/Cyberner/Radio,
* widocznosci czesci,
* supermocy,
* RSP,
* integracji z terytoriami.

## Testy

Wykonano:

```text
python -m py_compile ghostnetwork\__init__.py ghostnetwork\catalog.py ghostnetwork\contracts.py ghostnetwork\cycles.py ghostnetwork\enums.py ghostnetwork\errors.py ghostnetwork\events.py ghostnetwork\models.py ghostnetwork\repository.py ghostnetwork\reservations.py ghostnetwork\service.py ghostnetwork\topology.py ghostnetwork\visibility.py run.py config.py
python -m unittest tests.test_ghostnetwork_repository tests.test_ghostnetwork_catalog tests.test_ghostnetwork_cycle_service tests.test_ghostnetwork_topology tests.test_ghostnetwork_reservations
```

Wynik: OK.

