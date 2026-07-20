# GhostNetwork Endgame Runbook

## Cel

Runbook opisuje bezpieczne uruchamianie pierwszego etapu endgame GhostNetwork
po Sprint 130.

## Kolejnosc uruchamiania

1. `GHOSTNETWORK_ENABLED`
2. `GHOSTNETWORK_DROPS_ENABLED`
3. `GHOSTNETWORK_MAP_LAYER_ENABLED`
4. `GHOSTNETWORK_ABILITIES_ENABLED`
5. `GHOSTNETWORK_REWARDS_ENABLED`
6. `GHOSTNETWORK_TRANSMISSION_ENABLED`
7. `GHOSTNETWORK_MEDIA_ENABLED`
8. `GHOSTNETWORK_OLLAMA_ENABLED`

Kazda flaga powinna byc wlaczana osobno i obserwowana przed przejsciem dalej.

## Readiness check

Przed publicznym wlaczeniem endgame sprawdz:

```text
GET /api/ghostnetwork/archive/readiness
```

Wymagane:

* `ok = true`;
* `health.ok = true`;
* katalog GhostNetwork jest poprawny;
* endpoint archiwum nie zwraca bledu;
* zwykly gameplay dziala przy wylaczonych flagach GhostNetwork;
* endpointy mapy nie maja nowych regresji wydajnosci.

## Rollback

W razie problemu:

1. Wylacz `GHOSTNETWORK_MEDIA_ENABLED`.
2. Wylacz `GHOSTNETWORK_TRANSMISSION_ENABLED`.
3. Wylacz `GHOSTNETWORK_REWARDS_ENABLED`.
4. Wylacz `GHOSTNETWORK_ABILITIES_ENABLED`.
5. Jesli problem dotyczy mapy, wylacz `GHOSTNETWORK_MAP_LAYER_ENABLED`.
6. Jesli problem dotyczy calego systemu, wylacz `GHOSTNETWORK_ENABLED`.

Rollback nie usuwa archiwum ani historycznych sygnalow.

## Recovery

Archiwum mozna odtworzac idempotentnie przez:

```text
GhostNetworkService().finalize_signal_archive(signal_id)
```

Osiagniecia maja `dedupe_key`, wiec ponowna finalizacja nie powinna tworzyc
duplikatow.

## Zakazy

* Nie wlaczac Suite UI przed osobnym sprintem.
* Nie dawac Ollamie prawa do zmiany mechaniki.
* Nie kasowac historycznych wezlow przy rollbacku.
* Nie budowac drugiego stanu GhostNetwork poza repozytorium i snapshotami.
