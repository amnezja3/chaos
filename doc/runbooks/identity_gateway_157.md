# 157 — wdrożenie Identity Gateway

Procedura do wspólnego wykonania na istniejącym serwerze. Nie wykonano jej
podczas implementacji. Bez drugiej instancji gry i bez przywracania starej bazy
na aktywny świat. Dowody lokalne: `doc/audits/sprint_157_evidence.md`.

## Przygotowanie bez zatrzymywania gry

Callbacki w aplikacjach dostawców, dokładnie bez końcowego ukośnika:

| Dostawca | Callback |
| --- | --- |
| Google | `https://chaos.re/auth/google/callback` |
| Discord | `https://chaos.re/auth/discord/callback` |
| GitHub | `https://chaos.re/auth/github/callback` |
| Steam OpenID 2.0 | `https://chaos.re/auth/steam/callback` |

Steam: realm `https://chaos.re/`, bez OAuth client secret i bez klucza Web API.
Google/Discord/GitHub mają osobne client ID i secret. Nie wpisywać ich w repo,
czat lub formularze graczy. `config/identity_gateway.env.example` jest wzorem.
Konfiguracja poczty jest w **Admin → Identity Gateway → Konfiguracja poczty**;
SMTP nie wymaga edycji kodu ani restartu. Początkowo wysyłka pozostaje wyłączona.

Zachować dotychczasowy `CHAOS_SECRET_KEY`: nim szyfrowane jest hasło SMTP.
Zmiana/utrata tego klucza oznacza utratę możliwości odczytu tego hasła i sesji.
Hasło nie jest wysyłane z powrotem do panelu; puste pole przy zapisie zachowuje
sekret, jawny checkbox go usuwa. Zapis konfiguracji wymaga świeżego reauth.

Przed odbiorem live proxy nie może zapisywać query stringów `/auth/`.
W nginx użyć dla tych żądań formatu zawierającego `$uri`, nie `$request_uri`
ani `$request`; nie logować nagłówków Authorization/Cookie. Filtr aplikacji
redaguje query callbacków w loggerach Werkzeug/Gunicorn, ale nie w nginx/CDN.
Przed przeładowaniem konfiguracji proxy: `sudo nginx -t` → successful.

## Zapis stanu i kontrola kodu

```bash
cd ~/app/chaos
git status --short
git fetch origin
git log -1 --oneline origin/main
git merge-base --is-ancestor HEAD origin/main
df -h . "$HOME"
```

→ znany commit 157, brak konfliktujących zmian śledzonych, ostatnie polecenie
Git zakończone kodem 0. Nie usuwać lokalnych baz, cookies ani backupów.

```bash
umask 077
export DEPLOY_BACKUP="$HOME/chaos-backups/157-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$DEPLOY_BACKUP"
git rev-parse HEAD > "$DEPLOY_BACKUP/old-commit"
pm2 jlist > "$DEPLOY_BACKUP/pm2-before.json"
.venv/bin/python - <<'PY'
import json, os
from pathlib import Path
root=Path(os.environ['DEPLOY_BACKUP'])
rows=json.loads((root/'pm2-before.json').read_text())
apps=[r for r in rows if r.get('pm2_env',{}).get('pm_cwd') and
      Path(r['pm2_env']['pm_cwd']).resolve()==Path.cwd()]
assert any(r['name']=='chaos' for r in apps), 'Nie znaleziono procesu gry'
names=[r['name'] for r in apps if r['pm2_env'].get('status')=='online']
assert all(n and not n.startswith('-') and '\n' not in n for n in names)
(root/'processes.json').write_text(json.dumps(names))
print('Procesy do zatrzymania:', ', '.join(names))
PY
```

→ wyłącznie procesy CHAOS z tego katalogu. Procesy już zatrzymane nie są
powodem błędu i nie zostaną automatycznie uruchomione. PM2 snapshot zawiera
sekrety: pozostaje w prywatnym backupie. Wstrzymać również inne znane writery
tej bazy (np. cron), jeśli działają poza PM2.

## Krótka przerwa: backup, kod, migracja

```bash
.venv/bin/python - <<'PY'
import json, os, subprocess
from pathlib import Path
for name in json.loads((Path(os.environ['DEPLOY_BACKUP'])/'processes.json').read_text()):
    subprocess.run(['pm2','stop',name],check=True)
PY
git pull --ff-only
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
```

→ procesy z listy stopped, fast-forward, zależności zainstalowane, pip check
bez konfliktów. Nie zmieniać pozostałych aplikacji PM2. Wymagany Python ≥3.10.

```bash
.venv/bin/python tools/identity_157_migrate.py --db data/game.sqlite3 --backup "$DEPLOY_BACKUP/game.sqlite3"
.venv/bin/python - <<'PY'
import json, os, tarfile
from pathlib import Path
root=Path(os.environ['DEPLOY_BACKUP'])
rows=json.loads((root/'pm2-before.json').read_text())
row=next(r['pm2_env'] for r in rows if r['name']=='chaos')
env={**row.get('env',{}),**row}
path=Path(env.get('CHAOS_SESSION_FILE_DIR') or 'data/flask_session').resolve()
assert path.is_dir(), 'Nie znaleziono katalogu sesji — ustal ścieżkę'
with tarfile.open(root/'flask-session.tar.gz','x:gz') as archive:
    archive.add(path,arcname='flask_session')
print('session_backup: OK')
PY
```

→ `backed_up`, integralność/FK OK, plik `game.baseline.json`, backup sesji OK.
Backup SQLite korzysta z API backup, uwzględnia WAL; pliku docelowego nie nadpisuje.

```bash
.venv/bin/python tools/identity_157_audit.py --db data/game.sqlite3 > "$DEPLOY_BACKUP/identity-audit.json"
.venv/bin/python tools/identity_157_migrate.py --db data/game.sqlite3
```

→ audyt `ok:true`; obejrzeć lokalnie raport kolizji/braków bez publikowania ID.
Nie scalać ani przemianowywać starych kont. Kolizje wymagają rozstrzygnięcia
przed otwarciem nowych rejestracji; nie blokują logowania po istniejącym username.
Dry-run → `status:dry_run`, `original_data_unchanged:true`, integrity/FK OK.
Dry-run używa pełnego snapshotu w RAM; przy braku pamięci STOP, bez zmian źródła.

```bash
.venv/bin/python tools/identity_157_migrate.py --db data/game.sqlite3 --apply
.venv/bin/python tools/identity_157_migrate.py --db data/game.sqlite3 --check --baseline "$DEPLOY_BACKUP/game.baseline.json"
.venv/bin/python tools/identity_157_migrate.py --db data/game.sqlite3 --apply
```

→ `migrated`, następnie `baseline_matches:true`, następnie `already_migrated`.
Po dowolnym błędzie nie przechodzić do włączania funkcji. Apply jest transakcyjne.
Baseline porównujemy tylko przed wznowieniem zapisów; późniejsze postępy gry
naturalnie zmieniają skróty danych.

## Wznowienie i konfiguracja

```bash
.venv/bin/python - <<'PY'
import json, os, subprocess
from pathlib import Path
for name in json.loads((Path(os.environ['DEPLOY_BACKUP'])/'processes.json').read_text()):
    subprocess.run(['pm2','restart',name],check=True)
PY
pm2 ls
curl -sS -o /dev/null -w 'Launch HTTP: %{http_code}\n' https://chaos.re/launch
```

→ wcześniejsze procesy online; po rozgrzaniu `/launch` 200. Jednorazowe 503
tuż po restarcie sprawdzić ponownie; trwałe 503 wymaga diagnostyki. Flagi 157
domyślnie OFF. Potwierdzić dotychczasowy login i rozgrywkę przed włączeniem OAuth.

Sekrety przygotować w prywatnym pliku `$HOME/.config/chaos/identity.env`
na podstawie wzoru (uprawnienia 600). Zostawić registration/linking na 0.
Nie kopiować wzoru nad istniejącym plikiem z sekretami. Wpisać właściwe wartości
client ID/secret i flagi Google/Discord/GitHub; Steam może mieć flagę 1 bez sekretu.

```bash
set -a
. "$HOME/.config/chaos/identity.env"
set +a
.venv/bin/python tools/identity_157_audit.py --config
```

→ cztery dokładne callbacki; trzej dostawcy `configured:true`, Steam również;
żadnych wartości sekretów w wyniku. Audyt sprawdza bieżącą powłokę, nie PM2.

W panelu **Admin → Identity Gateway** zapisać SMTP i nadawcę po potwierdzeniu
hasłem admina, następnie wysłać test na kontrolowany adres. Odbiór wiadomości
w skrzynce jest osobnym dowodem; sama odpowiedź SMTP nie gwarantuje doręczenia.
SMTP nie należy konfigurować z trybem `mock` na produkcji.

```bash
CHAOS_IDENTITY_ENABLED=1 CHAOS_IDENTITY_LINKING_ENABLED=1 CHAOS_IDENTITY_REGISTRATION_ENABLED=0 pm2 restart chaos --update-env
```

→ aktywne skonfigurowane przyciski i link w Ustawienia → Konto. Najpierw na
kontach testowych: podłącz czterech dostawców po świeżym reauth, następnie
wyloguj i zaloguj każdą metodą; ID, saldo, nagrody i postać pozostają te same.
Przycisk niedostępnego dostawcy pozostaje nieaktywny.

Po odbiorze podłączeń, SMTP, treści warunków `157-v1` i audycie kolizji:

```bash
CHAOS_IDENTITY_REGISTRATION_ENABLED=1 pm2 restart chaos --update-env
```

→ nowy dostawca prowadzi do nicku/e-maila/frakcji/roli/zgody. Steam wymaga kodu
e-mail; adres potwierdzony przez innego dostawcę można wykorzystać bez kodu,
ale jego zmiana wymaga potwierdzenia. Brak SMTP nie może być pozornym sukcesem.

## Odbiór live i utrwalenie

Macierz: czterej dostawcy × istniejący/nowy gracz; anulowanie, wygasły callback,
inny kontekst cookies, link/unlink, ostatnia metoda, hasło i revocation,
potwierdzenie/zmiana e-maila, admin, usunięcie konta testowego. Sprawdzić PL/EN
oraz prawdziwe Windows/Linux/Android/iOS/PWA. Powrót w obcym magazynie cookies
ma czytelny błąd i ponowienie w pierwotnym oknie; nie kopiuje sesji przez URL.
Nie usuwać realnych kont testerów dla testu. Nie przyspieszać cykli gameplayu.

```bash
umask 077
pm2 save
.venv/bin/python - <<'PY'
import os
from pathlib import Path
root=Path(os.environ.get('PM2_HOME') or Path.home()/'.pm2')
for name in ('dump.pm2','dump.pm2.bak'):
    path=root/name
    if path.exists(): path.chmod(0o600)
print('PM2 dump permissions: OK')
PY
```

→ zapis konfiguracji PM2 i prawa 600. Nie wklejać zawartości dumpów.

## Wycofanie / ograniczenie funkcji

Najpierw zamknąć nowe rejestracje i podłączenia, zachowując logowanie już
powiązanych kont i SMTP potrzebne do reauth:

```bash
CHAOS_IDENTITY_REGISTRATION_ENABLED=0 CHAOS_IDENTITY_LINKING_ENABLED=0 pm2 restart chaos --update-env
```

→ nowe konta/podłączenia niedostępne; istniejące metody nadal działają.
Nie wyłączać globalnej flagi/dostawcy ani nie wracać do starego kodu, jeśli
odcina to konta external-only. Wówczas stosować poprawkę zgodną z nowymi danymi.
Flagi nie usuwają powiązań i nie cofają postępu.

Przed powstaniem jakichkolwiek powiązań/kont zewnętrznych można wyłączyć
globalną flagę i wrócić do zapisanego commita. Dodatkowe tabele pozostają.
Przy błędzie transakcyjnej migracji sprawdzić integralność; nie zakładać
konieczności odtwarzania bazy. Restore pełnego backupu wyłącznie jako osobna,
kontrolowana operacja przy zatrzymanych writerach i po uwzględnieniu nowych danych.

## Utrzymanie

Intencje/granty/kody wygasają serwerowo niezależnie od cleanup. Cleanup przy
rozpoczęciu logowania usuwa wygasłe rekordy, liczniki starsze niż dobę i zdarzenia
starsze niż 90 dni. Tombstones username i skróty usuniętych tożsamości pozostają,
aby stare callbacki nie odtwarzały dostępu; nie są automatycznie ponownie przypisywane.
Wspólne wiadomości/historyczne referencje i księgowe dowody innych graczy nie
są usuwane przy usunięciu konta. Pełny PASS 157 dopiero po odbiorze live.
