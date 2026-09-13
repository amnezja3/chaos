# GhostSignal — stawki nagród finału ×100

Zgodnie z decyzją użytkownika stawki bazowe wynoszą teraz:

- węzeł: 800 RSP;
- zamknięcie sygnału: 2000 RSP;
- terytorium: 800 RSP.

Zmienione w ecosystem.web.config.js, ecosystem.territory-worker.config.js,
obu aplikacjach ecosystem.config.example.js oraz fallbackach config.py.
Mnożniki ról terytoriów pozostają 1.0. Inne nagrody i reputacja klanów
nie były objęte zmianą.

Plan nagród zostaje zamrożony przy blokadzie cyklu. Nowe stawki dotyczą
nowych planów. Zamknięte archiwum ani istniejący lock/reward_plan nie zostają
przeliczone przez zmianę konfiguracji. Pokaz historyczny zachowuje jego wynik.
Przy 20 węzłach, jednym zamknięciu i 23 terytoriach nowy plan da 36400 RSP.

Po push/pull należy załadować pliki ecosystem, a nie tylko zrestartować PID:

```bash
pm2 reload ecosystem.web.config.js --only chaos --update-env &&
pm2 reload ecosystem.territory-worker.config.js --only chaos-territory-worker --update-env
```

Kontrola wyłącznie trzech stawek w środowisku PM2 (bez pełnego env):

```bash
pm2 jlist | .venv/bin/python -B -c 'import json,sys; keys=["CHAOS_GHOSTNETWORK_SIGNAL_NODE_HOLDER_RSP","CHAOS_GHOSTNETWORK_SIGNAL_CLOSER_RSP","CHAOS_GHOSTNETWORK_SIGNAL_TERRITORY_RSP"]; print(json.dumps([{ "name":p["name"], "rates":{k:p.get("pm2_env",{}).get(k) for k in keys}} for p in json.load(sys.stdin) if p["name"] in ("chaos","chaos-territory-worker")],indent=2))'
```

Oczekiwane wartości dla obu procesów: 800 / 2000 / 800.
Uruchomienie produkcyjnego triggera pozostaje oddzielnym krokiem.
