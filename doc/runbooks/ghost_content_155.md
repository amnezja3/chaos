# Sprint 155 — wdrożenie na obecnej produkcji

Pakiet lokalny **155.2.0**. Procedura przygotowana, **niewykonana na serwerze**.
Bez drugiej instancji gry i dodatkowego portu. Katalog poniżej służy backupom.
EN pozostaje `test` do odbioru rzeczywistych treści. Komendy: Bash, `johndoe`,
ta sama sesja SSH. Każdy blok wykonuj osobno. Niezgodny wynik oznacza STOP.
Linii „Spodziewane” nie wklejaj do terminala. Najpierw wypchnij lokalny commit 155.

## 1. Stan początkowy

```sh
cd ~/app/chaos
git status --short
git fetch origin
git log -1 --oneline origin/main
git merge-base --is-ancestor HEAD origin/main
pm2 ls
df -h . "$HOME"
```

Spodziewane: czysty Git, właściwy commit 155, ostatnia komenda Git z kodem 0.
PM2 zawiera `chaos`, `chaos-ollama-worker`, `chaos-narrative-publisher`.
Zapewnij miejsce na backup, ewentualną kopię przed rollbackiem i tymczasowe
pliki SQLite. Nie zmieniamy usług innych aplikacji ani serwera Ollamy.

```sh
umask 077
export DEPLOY_BACKUP="$HOME/chaos-backups/155-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$DEPLOY_BACKUP"
git rev-parse HEAD > "$DEPLOY_BACKUP/old-commit"
git rev-parse origin/main > "$DEPLOY_BACKUP/new-commit"
pm2 jlist > "$DEPLOY_BACKUP/pm2-before.json"
git show origin/main:tools/ghost_content_155_migrate.py > "$DEPLOY_BACKUP/db-tool.py"
.venv/bin/python - <<'PY'
import json, os
from pathlib import Path
root = Path(os.environ['DEPLOY_BACKUP'])
rows = json.loads((root/'pm2-before.json').read_text())
apps = [r for r in rows if r.get('pm2_env',{}).get('pm_cwd') and Path(r['pm2_env']['pm_cwd']).resolve()==Path.cwd()]
required = {'chaos','chaos-ollama-worker','chaos-narrative-publisher'}
assert required <= {r['name'] for r in apps}, 'Niepełna lista procesów CHAOS — STOP'
assert all(r['pm2_env']['status']=='online' for r in apps if r['name'] in required), 'Wymagany proces nie jest online — STOP'
names = [r['name'] for r in apps if r['pm2_env']['status']=='online']
assert all('\n' not in n and not n.startswith('-') for n in names)
(root/'processes.txt').write_text('\n'.join(names)+'\n')
print('Procesy do zatrzymania:', ', '.join(names))
print('Backup:', root)
PY
```

Spodziewane: lista wyłącznie procesów z obecnego katalogu gry, dwa commity
i konfiguracja zapisane. `pm2-before.json` zawiera sekrety (uprawnienia 600);
nie wyświetlaj go i nie dodawaj do repo. Jeżeli cron/inny proces również zapisuje
do tej bazy, wstrzymaj go na czas migracji. Nie zatrzymuj całego PM2.

## 2. Przerwa, backup i punkt odniesienia

```sh
(
set -e
while IFS= read -r app; do pm2 stop "$app"; done < "$DEPLOY_BACKUP/processes.txt"
)
pm2 ls
```

Spodziewane: wszystkie wskazane procesy CHAOS `stopped`, inne aplikacje działają.
Zatrzymanie generacji może potrwać do 6 minut. Gra jest niedostępna podczas
przerwy. Nie kontynuuj, jeśli pozostał aktywny proces zapisujący do bazy.

```sh
.venv/bin/python "$DEPLOY_BACKUP/db-tool.py" backup --db data/game.sqlite3 --output "$DEPLOY_BACKUP/game.sqlite3"
.venv/bin/python "$DEPLOY_BACKUP/db-tool.py" check --db data/game.sqlite3 --output "$DEPLOY_BACKUP/before.json"
.venv/bin/python "$DEPLOY_BACKUP/db-tool.py" check --db "$DEPLOY_BACKUP/game.sqlite3" --baseline "$DEPLOY_BACKUP/before.json"
```

Spodziewane: `backed_up`, `integrity: ok`, `foreign_keys: ok`; następnie
`checked` i `baseline_matches: true` dla backupu. SQLite Backup API uwzględnia
zatwierdzone dane WAL. Nie kopiujemy samego pliku bazy. Backup nie może już
istnieć. `before.json` zawiera liczniki i hashe wszystkich pierwotnych kolumn
wszystkich tabel, bez eksportu treści. Obejmuje ID, przeczytania, salda, nagrody
i receipty. Istniejące błędy integralności/FK wyjaśniamy przed migracją.

## 3. Kod, dry-run, migracja

```sh
git merge --ff-only "$(cat "$DEPLOY_BACKUP/new-commit")"
```

Spodziewane: fast-forward do zapisanego commita. Następnie:

```sh
.venv/bin/python tools/run_isolated_tests.py test_ghost_content_155_migrate test_narrative_locale test_narrative_locale_history test_news_locales test_news_generation test_system_message_i18n test_mistral_runtime
```

Spodziewane: testy `OK`. Następnie:

```sh
.venv/bin/python tools/ghost_content_155_migrate.py migrate --db data/game.sqlite3
```

Spodziewane: fast-forward, testy `OK`, migracja `dry_run`,
`original_data_unchanged: true`, integralność/FK `ok`. Testy używają tymczasowych
baz unittest, nie drugiej gry. Dry-run wykonuje DDL na samym schemacie w pamięci,
bez kopiowania historii i bez zapisu do bazy produkcji.

```sh
.venv/bin/python tools/ghost_content_155_migrate.py migrate --db data/game.sqlite3 --apply
```

Spodziewane: `migrated`. Następnie kontrola i sprawdzenie idempotencji:

```sh
.venv/bin/python tools/ghost_content_155_migrate.py check --db data/game.sqlite3 --baseline "$DEPLOY_BACKUP/before.json"
.venv/bin/python tools/ghost_content_155_migrate.py migrate --db data/game.sqlite3 --apply
```

Spodziewane: `migrated`, `baseline_matches: true`, `already_migrated`.
Migracja w jednej transakcji dodaje `chat_messages.system_copy_json`,
`ghost_narrative_medium_records.output_locale` i tabele wariantów/kolejki News
oraz batchy historii. Nie przypisuje języka starym publikacjom, nie tłumaczy UGC,
nie publikuje ani nie nalicza nagród. Błąd cofa niedokończony DDL.

## 4. Próby Mistrala i Ollamy, nadal bez publikacji

Po poprawkach canary można zamiast poniższej pętli zatrzymującej się na pierwszym
odrzuceniu użyć jednej komendy zbierającej cały wynik. Każda próba raz, bez retry:

```sh
.venv/bin/python tools/narrative_locale_matrix.py --db data/game.sqlite3 --pm2-snapshot "$DEPLOY_BACKUP/pm2-before.json" --report "$DEPLOY_BACKUP/canary-$(date -u +%Y%m%dT%H%M%SZ).json" --generate
```

Spodziewane: 12 raportów `published:false`, podsumowanie `passed:12, failed:0`.
Każde odrzucenie pozostaje w raporcie i powoduje końcowy exit 1; nie pomijamy go
w ocenie. Także próbki `accepted` wymagają przeglądu faktów: odkrycie nie oznacza
aktywacji, a brak informacji nie dowodzi braku logów. Nie wykonywać obu wariantów
macierzy jeden po drugim bez potrzeby. Raport nie zawiera sekretu.

Procesy gry nadal zatrzymane. Canary korzysta ze wspólnego routera/walidatora
i syntetycznych faktów; zapisuje diagnostykę oraz zużycie budżetu dostawcy.
Nie dodaje zadań do kolejki ani wiadomości. Nie wymaga części Ghost Signala.
Sekret pobieramy do pamięci procesu z zachowanego środowiska workera.

```sh
.venv/bin/python - <<'PY'
import json, os, subprocess, sys
from pathlib import Path
rows = json.loads((Path(os.environ['DEPLOY_BACKUP'])/'pm2-before.json').read_text())
worker = next(r['pm2_env'] for r in rows if r['name']=='chaos-ollama-worker')
saved = {**worker.get('env',{}), **worker}
env = os.environ.copy()
env.update({k:str(v) for k,v in saved.items() if k.startswith('CHAOS_') and isinstance(v,(str,int,float))})
assert env.get('CHAOS_MISTRAL_API_KEY','').strip(), 'Brak sekretu workera — STOP'
for provider in ('mistral','ollama'):
    for locale in ('pl','en'):
        for medium in ('blacknet','cyberner','googleplex_news'):
            subprocess.run([sys.executable,'tools/narrative_locale_canary.py',
                '--db','data/game.sqlite3','--provider',provider,'--locale',locale,
                '--medium',medium,'--generate','--show-text'],env=env,check=True)
PY
```

Spodziewane: 12 raportów `ok: true`, `published: false`, `generated: true`,
`validation: accepted`, właściwe `provider`/`locale`. Próba Mistrala korzystająca
z fallbacku zwróci błąd, żeby nie pomylić PASS Ollamy z PASS Mistrala. Próby
sekwencyjne zużywają tokeny/czas; pierwsza porażka zatrzymuje blok. Obejrzyj język
i fakty. Nie symulujemy awarii przez usuwanie produkcyjnego sekretu ani zmianę
globalnego budżetu; fallback ma izolowane testy routera. Próbki nie potwierdzają
jeszcze dostarczenia do feedów. Nie uruchamiaj publishera ani `run-once`.

## 5. Web i integracje, publikator nadal zatrzymany

```sh
CHAOS_NARRATIVE_LOCALES=pl CHAOS_NEWS_LOCALE_GENERATION_ENABLED=0 pm2 restart chaos --update-env
pm2 ls
curl -fsS https://chaos.re/static/locales/manifest.json
```

Spodziewane: web online, oba workery narracji stopped, manifest `155.2.0`.
Zachowujemy istniejące środowisko PM2; nie ładujemy ponownie ecosystem ani
nie nadpisujemy sekretu pustą zmienną. Na kontach PL/EN sprawdzamy:

- News: bazowe sekcje, akcje, oryginalne produkty graczy i historię.
- BN: jedna publikacja w swoim języku; Cyberner: systemowe treści według
  odbiorcy, UGC bez tłumaczenia, bez powielania wiadomości/przeczytań.
- FM about/tips-tricks, Show/Sender, admin, areszt i kaucję.
- Zmiana języka nie ponawia nagród, publikacji, instalacji ani consumed.

To odbiór istniejących danych i rendererów, bez ręcznej/automatycznej publikacji.
Gra może tworzyć oczekujące zdarzenia; przy wznowieniu obowiązuje ich TTL.

```sh
.venv/bin/python tools/news_locale_backfill.py inventory --db data/game.sqlite3 --limit 100
.venv/bin/python tools/narrative_language_history.py inventory --db data/game.sqlite3 --limit 100
.venv/bin/python tools/system_copy_inventory.py --db data/game.sqlite3 --kind notifications --limit 100
.venv/bin/python tools/system_copy_inventory.py --db data/game.sqlite3 --kind mail --limit 100
```

Spodziewane: metadane i `next_after`; następna strona przez `--after`.
Nieustalony język wymaga przeglądu. `review_required` w mail obejmuje także UGC,
nie jest automatycznie liczbą brakujących tłumaczeń.

## 6. Wznowienie i stopniowe uruchomienie funkcji

Dopiero po zaakceptowaniu próbek/odczytów:

```sh
(
set -e
while IFS= read -r app; do
  case "$app" in chaos|chaos-narrative-publisher) continue ;; esac
  CHAOS_NARRATIVE_LOCALES=pl CHAOS_NEWS_LOCALE_GENERATION_ENABLED=0 pm2 restart "$app" --update-env
done < "$DEPLOY_BACKUP/processes.txt"
pm2 restart chaos-narrative-publisher
)
pm2 ls
```

Spodziewane: procesy sprzed przerwy online. Restart publishera **wznawia publikację**,
także oczekujących zadań. Sprawdź panel modeli, dostarczenie normalnej narracji do
właściwego medium, brak duplikatów/nagród. Syntetyczny canary nie zastępuje tej próby.

Po odbiorze językowym, osobna decyzja o włączeniu PL/EN:

```sh
(
set -e
while IFS= read -r app; do
  CHAOS_NARRATIVE_LOCALES=pl,en CHAOS_NEWS_LOCALE_GENERATION_ENABLED=0 pm2 restart "$app" --update-env
done < "$DEPLOY_BACKUP/processes.txt"
CHAOS_NEWS_LOCALE_GENERATION_ENABLED=1 pm2 restart chaos-ollama-worker --update-env
pm2 ls
pm2 save
chmod 600 "$HOME/.pm2/dump.pm2"
)
```

Spodziewane: nowe BN wybierają PL albo EN stabilnie dla zdarzenia — nie dwa
tłumaczenia. Warianty News wiążą się z wersją/faktami i powstają poza requestem.
Retry/fallback nie zmienia języka zapisanego zadania. Własne zapytanie bierze
język konta. `ANY` jest filtrem radia. Show/Sender ma tekst według gracza,
wspólne zegar/wynik i oryginalne audio/wideo. Zmiana locale nie odtwarza filmu.

## Historia — osobne, przejrzane batche

Do 100 rekordów/1 MiB. News: `medium_record_id`, `source_version`, `locale`,
`title`, `body`. Języki: pierwsze trzy pola. ID/hash z inventory; przegląd
redakcyjny obowiązkowy. Produkty graczy wyłączone. Przykłady wymagają plików:

```sh
.venv/bin/python tools/news_locale_backfill.py import --db data/game.sqlite3 --input reviewed-news.json --batch news-155-01 --reviewed-by editor
.venv/bin/python tools/news_locale_backfill.py import --db data/game.sqlite3 --input reviewed-news.json --batch news-155-01 --reviewed-by editor --apply
.venv/bin/python tools/narrative_language_history.py import --db data/game.sqlite3 --input reviewed-languages.json --batch language-155-01 --reviewed-by editor
.venv/bin/python tools/narrative_language_history.py import --db data/game.sqlite3 --input reviewed-languages.json --batch language-155-01 --reviewed-by editor --apply
```

Spodziewane: `dry_run`, potem `applied`; powtórka `already_applied`.
Konflikt hash odrzuca batch. Bez ponownej publikacji historii.

## Rollback

**Nieudana migracja przed wznowieniem:** niedokończony DDL cofa transakcja.
Powtórz `check --baseline "$DEPLOY_BACKUP/before.json"`. Przy zgodności wystarczy
naprawa/rollback kodu; nie odtwarzaj automatycznie całej bazy.

**Problem nowej funkcji:** wyłącz warianty i wybór EN dla nowych zadań:

```sh
(
set -e
while IFS= read -r app; do
  CHAOS_NARRATIVE_LOCALES=pl CHAOS_NEWS_LOCALE_GENERATION_ENABLED=0 pm2 restart "$app" --update-env
done < "$DEPLOY_BACKUP/processes.txt"
)
```

Spodziewane: oryginalny pipeline działa, nowe automatyczne zadania PL. Rozpoczęte
zadanie może się jeszcze zakończyć. Istniejący kontrakt i kolejka pozostają.
Tego bloku używaj po wznowieniu, nie w trakcie prób bez publikacji.

**Błędny import:** najpierw dry-run, potem wyłącznie własny batch:

```sh
.venv/bin/python tools/news_locale_backfill.py rollback --db data/game.sqlite3 --batch news-155-01
.venv/bin/python tools/news_locale_backfill.py rollback --db data/game.sqlite3 --batch news-155-01 --apply
.venv/bin/python tools/narrative_language_history.py rollback --db data/game.sqlite3 --batch language-155-01
.venv/bin/python tools/narrative_language_history.py rollback --db data/game.sqlite3 --batch language-155-01 --apply
```

Spodziewane: usunięte własne warianty/cofnięte metadane, oryginały/wiadomości/
nagrody/receipty nienaruszone. Konflikt nowszego źródła wyjaśniamy; nie wymuszamy
nadpisania i nie używamy ponownie wycofanego ID batcha.

**Rollback kodu:** zatrzymaj zapisy, zachowaj stan po wdrożeniu:

```sh
(
set -e
while IFS= read -r app; do pm2 stop "$app"; done < "$DEPLOY_BACKUP/processes.txt"
)
pm2 ls
```

Spodziewane: wszystkie procesy z listy stopped. Następnie:

```sh
(
set -e
.venv/bin/python tools/ghost_content_155_migrate.py backup --db data/game.sqlite3 --output "$DEPLOY_BACKUP/before-rollback.sqlite3"
test -z "$(git status --porcelain)"
git switch --detach "$(cat "$DEPLOY_BACKUP/old-commit")"
CHAOS_NARRATIVE_LOCALES=pl CHAOS_NEWS_LOCALE_GENERATION_ENABLED=0 pm2 restart chaos --update-env
)
```

Spodziewane: poprzedni web, addytywne kolumny/tabele pozostają. Warunek Git:
czysty katalog, brak zmian do zachowania. **Workery i pozostałe procesy pozostają
zatrzymane do oceny kolejki** — stary kod nie może potraktować zapisanych EN zadań
jako PL. Wznowienie wymaga poprawki kompatybilności albo powrotu naprawionego 155.
Nie kasuj kolejki, receiptów, tabel; nie używaj `reset --hard`/`clean`.

**Pełne odtworzenie bazy:** ostatnia opcja. Po wznowieniu gry cofnęłoby postęp
od backupu, więc wymaga decyzji i rozliczenia nowych danych. Poniższy blok dopiero
po zatrzymaniu WSZYSTKICH zapisów (także web), backupie `before-rollback.sqlite3`
i zaakceptowaniu punktu odtworzenia:

```sh
(
set -e
while IFS= read -r app; do pm2 stop "$app"; done < "$DEPLOY_BACKUP/processes.txt"
)
pm2 ls
```

Spodziewane: wszystkie procesy CHAOS stopped. Zachowaj najnowszy stan, również
gdy wcześniej powstała już kopia przed rollbackiem kodu:

```sh
.venv/bin/python "$DEPLOY_BACKUP/db-tool.py" backup --db data/game.sqlite3 --output "$DEPLOY_BACKUP/before-full-restore.sqlite3"
```

Spodziewane: `backed_up`, integralność/FK `ok`. Dopiero po tym:

```sh
.venv/bin/python - <<'PY'
import os, sqlite3
from contextlib import closing
from pathlib import Path
source = Path(os.environ['DEPLOY_BACKUP'])/'game.sqlite3'
assert source.is_file()
with closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True)) as src:
    assert src.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
    with closing(sqlite3.connect('file:data/game.sqlite3?mode=rw',uri=True)) as dst:
        src.backup(dst)
        assert dst.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
        assert dst.execute('PRAGMA foreign_key_check').fetchone() is None
print('restored; procesy nadal zatrzymane')
PY
.venv/bin/python "$DEPLOY_BACKUP/db-tool.py" check --db data/game.sqlite3 --baseline "$DEPLOY_BACKUP/before.json"
```

Spodziewane: `restored`, `baseline_matches: true`. Dopiero potem zgodny kod
i uzgodnione wznowienie. Nie usuwamy ręcznie WAL/SHM. Zapisz stan PM2 przez
`pm2 save` dopiero po uzyskaniu docelowego, sprawdzonego zestawu procesów.

## Odbiór

### Pojedynczy canary po optymalizacji promptów

Po pobraniu poprawki wystarczy jeden rzeczywisty test Ollama / PL / Cyberner.
Nie wznawiaj workerów ani pełnej macierzy na podstawie samego HTTP 200.
Poniższa komenda odtwarza wyłącznie zmienne CHAOS ze snapshotu workera
w procesie testowym; nie zmienia PM2 i nie drukuje sekretów:

```sh
.venv/bin/python - <<'PY'
import json, os, subprocess, sys
from pathlib import Path
rows = json.loads((Path(os.environ['DEPLOY_BACKUP']) / 'pm2-before.json').read_text())
worker = next(r['pm2_env'] for r in rows if r['name'] == 'chaos-ollama-worker')
saved = {**worker.get('env', {}), **worker}
env = os.environ.copy()
env.update({k: str(v) for k, v in saved.items()
            if k.startswith('CHAOS_') and isinstance(v, (str, int, float))})
result = subprocess.run([
    sys.executable, 'tools/narrative_locale_canary.py',
    '--db', 'data/game.sqlite3', '--provider', 'ollama',
    '--locale', 'pl', '--medium', 'cyberner', '--generate', '--show-text',
], env=env)
sys.exit(result.returncode)
PY
```

Spodziewane: `published:false`, `provider:ollama`, `validation:accepted`,
`errors:[]`, `elapsed_seconds` oraz `input_metrics`. `message_bytes` liczy
wszystkie wiadomości wspólnego pakietu, `schema_bytes` osobno schemat;
nie są to liczby tokenów ani pełny rozmiar HTTP. Adapter Mistrala dodatkowo
włącza schemat do instrukcji. `prompt_sha256` identyfikuje dokładną treść
wiadomości i schematu bez ujawniania ich w metrykach.

Sprawdź także próbkę: może mówić o ujawnieniu elementu przy Canary Station,
ale nie o potwierdzeniu w logach, aktywności, autoryzacji lub pomiarach,
których nie było w faktach. Formalne `accepted` nie zastępuje tego odbioru.
Przy timeout lub odrzuceniu zachowaj wynik; nie ponawiaj do losowego sukcesu.
Test zapisuje diagnostykę dostawcy, ale nie kolejkuje ani nie publikuje treści.

[Macierz dowodów](../audits/sprint_155_acceptance.md) rozdziela testy lokalne
od produkcyjnych. Pełny PASS wymaga rzeczywistych próbek rodzin narracji,
przeglądu dostępnej historii, dwóch kont PL/EN i odbioru urządzeń.
Przygotowanie procedury nie oznacza wykonania wdrożenia ani pełnego PASS.
