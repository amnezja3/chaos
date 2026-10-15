# 156.6 — wdrożenie i utrwalenie konfiguracji

Wdrożenie na istniejącej produkcji wykonane wspólnie z operatorem 15 X 2026.
[Macierz dowodów i otwarte odbiory](../audits/sprint_156_acceptance.md).
Bez drugiej instancji gry. Domyślne flagi w kodzie pozostają OFF.

Wykonano: pull 135af92 (bazowe 156), 39 testów, dry-run, zatrzymanie czterech
writerów CHAOS, spójny backup SQLite przez backup API i archiwum sesji, migracja
pięciu kolumn z integralnością/FK i zachowaniem danych, restart z trwałym sekretem,
następnie etapowe włączenie persistence → launch → install. Przejściowy 503 po
restarcie ustąpił; launch HTTP 200 i odbiór użytkownika PASS.

## Ostatni krok operatora — zapis aktualnych flag

Po pozytywnym odbiorze działającego systemu:

```bash
(
  umask 077
  pm2 save
)
```

→ PM2 potwierdza zapis. Nie publikować dump.pm2: zawiera sekrety.

```bash
.venv/bin/python - <<'PY'
import json, os
from pathlib import Path
root = Path(os.environ.get('PM2_HOME') or Path.home() / '.pm2')
for name in ('dump.pm2', 'dump.pm2.bak'):
    path = root / name
    if path.exists():
        path.chmod(0o600)
rows = json.loads((root / 'dump.pm2').read_text())
row = next(r for r in rows if r.get('name') == 'chaos')
env = {**row.get('env', {}), **row}
for key in ('CHAOS_PERSISTENT_SESSION_ENABLED', 'CHAOS_LAUNCH_CONTROLLER_ENABLED', 'CHAOS_INSTALL_UI_ENABLED'):
    value = str(env.get(key, '')).lower()
    assert value in ('1', 'true', 'yes', 'on'), key + ': flaga nie jest włączona'
    print(key + ': ON')
expected = (Path.home() / '.config/chaos/session-secret.env').read_text().strip().split('=', 1)[1]
assert expected and env.get('CHAOS_SECRET_KEY') == expected, 'Niezgodny sekret'
print('saved_secret_matches: True')
PY
```

→ trzy flagi ON i saved_secret_matches:True. Przy błędzie nie deklarować trwałości
konfiguracji po restarcie hosta; ustalić różnicę. Nie zmieniać sekretu przy wdrożeniach.
Plik sekretu sam się nie ładuje: PM2 ma go w zapisanym env. Przy odtworzeniu procesu
z ecosystem trzeba dostarczyć ten sam sekret i zatwierdzone flagi.

## Wycofanie funkcji

```bash
CHAOS_INSTALL_UI_ENABLED=0 pm2 restart chaos --update-env
```

→ panel wyłączony, /chaos-sw.js nadal HTTP 200 z workerem wycofującym własny cache.
Zachować endpoint; offline klient odbierze zmianę po powrocie online.

```bash
CHAOS_INSTALL_UI_ENABLED=0 CHAOS_LAUNCH_CONTROLLER_ENABLED=0 pm2 restart chaos --update-env
```

→ przywrócone stare wejście dla nowych dokumentów, /launch nadal obsługiwany.
W razie potrzeby zatrzymania wydawania trwałych sesji wyłączyć także
CHAOS_PERSISTENT_SESSION_ENABLED. Zachować guard TTL i kolumny bazy dla już
wydanych sesji. Po potwierdzeniu zdrowia zapisać PM2 i zabezpieczyć dump jak wyżej;
kontrola trzech flag ON dotyczy wyłącznie udanego rollout, nie rollbacku.

Nie przywracać starej bazy, ownership ani katalogu sesji po nowych transakcjach
i logowaniach: cofnęłoby to postęp i mogłoby przywrócić unieważnione sesje.
Nie cofać kodu do wersji ignorującej TTL. Nie zmieniać sekretu w ramach rollbacku.
Migracja jest addytywna; preferowany rollback to wyłączenie flag.
