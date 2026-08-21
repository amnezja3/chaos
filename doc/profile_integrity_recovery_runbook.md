# Sprint 130.10 — runbook bezpiecznego zebrania dowodów

## Cel i granica etapu

Ten runbook służy wyłącznie do zebrania zredagowanych dowodów integralności
profilu na serwerze. Nie wykonuje recovery, migracji, naprawy profilu, restartu
aplikacji ani deployu. Po wykonaniu procedury należy zatrzymać się na bramce:

`READY FOR READ-ONLY SERVER FORENSICS — Sprint 130.10`

Narzędzie `tools/audit_profile_integrity.py` otwiera SQLite przez `mode=ro`, ustawia
`PRAGMA query_only=ON`, pracuje w jednej transakcji odczytowej i nie importuje
modułów runtime `database` ani `run`. Raport jest zredagowany: nie zawiera surowego
loginu, credentials, pełnego JSON-u profilu, współrzędnych ani topologii targetów.

## Warunki wstępne

- Wykonuj komendy z katalogu głównego właściwego checkoutu aplikacji, czyli z
  miejsca, w którym istnieje `tools/audit_profile_integrity.py`.
- W placeholderze `<EXACT_CANONICAL_LOGIN>` wpisz dokładny canonical login,
  z zachowaniem wielkości liter. Nie używaj aliasu, fragmentu loginu ani fuzzy
  match.
- Domyślna baza to `data/game.sqlite3`. Jeżeli produkcja używa innej ścieżki,
  ustaw wcześniej `CHAOS_DB_PATH` na tę ścieżkę.
- Nie używaj `set -e`: kod wyjścia `1` z `verify` jest wynikiem dowodowym i nie
  powinien przerwać zapisania manifestu oraz sum kontrolnych.
- Katalog `/tmp/chaos-13010-evidence` musi nie istnieć przed rozpoczęciem. Jeżeli
  istnieje, zatrzymaj się i zachowaj poprzedni capture; nie nadpisuj go i nie
  mieszaj dwóch przebiegów.

## Jednorazowy capture na serwerze

Poniższy blok zapisuje wyłącznie zredagowane raporty i metadane do
`/tmp/chaos-13010-evidence`. Nie kopiuje bazy ani plików sesji.

```bash
(
set -u
umask 077

EVIDENCE_DIR='/tmp/chaos-13010-evidence'
DB_PATH="${CHAOS_DB_PATH:-data/game.sqlite3}"
PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
CANONICAL_LOGIN='<EXACT_CANONICAL_LOGIN>'

if [ "$CANONICAL_LOGIN" = '<EXACT_CANONICAL_LOGIN>' ]; then
  printf '%s\n' 'STOP: replace <EXACT_CANONICAL_LOGIN> with the exact canonical login.' >&2
  exit 2
fi

if [ -e "$EVIDENCE_DIR" ]; then
  printf '%s\n' "STOP: $EVIDENCE_DIR already exists; preserve it and do not overwrite it." >&2
  exit 2
fi

if [ ! -f 'tools/audit_profile_integrity.py' ]; then
  printf '%s\n' 'STOP: run this block from the application repository root.' >&2
  exit 2
fi

if [ ! -x "$PYTHON_BIN" ]; then
  printf '%s\n' 'STOP: configured Python interpreter is not executable.' >&2
  exit 2
fi

if [ ! -r "$DB_PATH" ]; then
  printf '%s\n' 'STOP: configured SQLite database is not readable.' >&2
  exit 2
fi

mkdir -m 700 "$EVIDENCE_DIR"

{
  printf '[capture]\n'
  date -u '+captured_at_utc=%Y-%m-%dT%H:%M:%SZ'
  printf 'repository_root='
  pwd
  printf 'python='
  "$PYTHON_BIN" --version 2>&1
  printf '\n[revision]\n'
  git rev-parse --verify HEAD
  printf '\n[worktree]\n'
  git status --short --branch --untracked-files=all
  printf '\n[unstaged_diff_stat]\n'
  git diff --no-ext-diff --stat
  printf '\n[staged_diff_stat]\n'
  git diff --cached --no-ext-diff --stat
} > "$EVIDENCE_DIR/revision-worktree.txt" 2> "$EVIDENCE_DIR/revision-worktree.stderr.txt"

sha256sum tools/audit_profile_integrity.py > "$EVIDENCE_DIR/tool-source.sha256"

"$PYTHON_BIN" tools/audit_profile_integrity.py status \
  --db "$DB_PATH" \
  > "$EVIDENCE_DIR/status.json" \
  2> "$EVIDENCE_DIR/status.stderr.txt"
STATUS_RC=$?

"$PYTHON_BIN" tools/audit_profile_integrity.py audit \
  --db "$DB_PATH" \
  --username "$CANONICAL_LOGIN" \
  > "$EVIDENCE_DIR/audit.json" \
  2> "$EVIDENCE_DIR/audit.stderr.txt"
AUDIT_RC=$?

"$PYTHON_BIN" tools/audit_profile_integrity.py verify \
  --db "$DB_PATH" \
  --username "$CANONICAL_LOGIN" \
  > "$EVIDENCE_DIR/verify.json" \
  2> "$EVIDENCE_DIR/verify.stderr.txt"
VERIFY_RC=$?

printf 'status=%s\naudit=%s\nverify=%s\n' \
  "$STATUS_RC" "$AUDIT_RC" "$VERIFY_RC" \
  > "$EVIDENCE_DIR/exit-codes.txt"

sha256sum \
  "$EVIDENCE_DIR/revision-worktree.txt" \
  "$EVIDENCE_DIR/revision-worktree.stderr.txt" \
  "$EVIDENCE_DIR/tool-source.sha256" \
  "$EVIDENCE_DIR/status.json" \
  "$EVIDENCE_DIR/status.stderr.txt" \
  "$EVIDENCE_DIR/audit.json" \
  "$EVIDENCE_DIR/audit.stderr.txt" \
  "$EVIDENCE_DIR/verify.json" \
  "$EVIDENCE_DIR/verify.stderr.txt" \
  "$EVIDENCE_DIR/exit-codes.txt" \
  > "$EVIDENCE_DIR/SHA256SUMS"

printf '%s\n' "Evidence written to $EVIDENCE_DIR"
printf 'status=%s audit=%s verify=%s\n' "$STATUS_RC" "$AUDIT_RC" "$VERIFY_RC"
unset CANONICAL_LOGIN
)
```

Nie zmieniaj kolejności `--db` i komendy na nieudokumentowany wariant. Obsługiwane
i użyte powyżej formy to dokładnie:

```text
.venv/bin/python tools/audit_profile_integrity.py status --db <database-path>
.venv/bin/python tools/audit_profile_integrity.py audit --db <database-path> --username <EXACT_CANONICAL_LOGIN>
.venv/bin/python tools/audit_profile_integrity.py verify --db <database-path> --username <EXACT_CANONICAL_LOGIN>
```

## Weryfikacja sum po capture

Weryfikacja dotyczy wyłącznie wygenerowanych raportów i metadanych, nie surowej
bazy:

```bash
sha256sum -c /tmp/chaos-13010-evidence/SHA256SUMS
```

Każdy wpis powinien zakończyć się `OK`. Nie dopisuj później danych do raportów;
ponowny capture wymaga osobnego, pustego katalogu uzgodnionego z operatorem.

## Znaczenie kodów wyjścia

| Kod | Znaczenie |
| --- | --- |
| `0` | Narzędzie wykonało komendę i zapisało poprawny JSON. Dla `status` i `audit` nie oznacza to automatycznie braku findings. Dla `verify` oznacza brak account-level blockera; wynik może nadal być `unknown`, jeżeli historia albo opcjonalny scope są niepełne. |
| `1` | Dotyczy `verify`: odczyt i raport zakończyły się technicznie, ale `account_integrity_status` ma wartość `blocked` (w tym nieudany `quick_check` albo brak exact account). Jest to wynik dowodowy, nie awaria narzędzia. |
| `2` | Błąd wejścia/wykonania albo nieobsługiwany core schema `users`, np. brak bazy, pusty exact login, błąd SQLite lub naruszenie założenia read-only. Nie przechodź do recovery; zachowaj JSON/stderr i wyjaśnij błąd. Niepoprawna składnia CLI również kończy się kodem `2`. |

W szczególności `verify=1` w `exit-codes.txt` może być prawidłowo zebranym dowodem
na blocker. Nie uruchamiaj w odpowiedzi migracji, automatycznego fallbacku ani
naprawy profilu.

## Dozwolony handoff

Do analizy przekazuje się wyłącznie zawartość katalogu dowodowego utworzoną przez
powyższy blok: trzy raporty JSON, pliki stderr, status rewizji/worktree, kody
wyjścia i `SHA256SUMS`. Przed przekazaniem należy potwierdzić sumy kontrolne.

Nie kopiuj, nie archiwizuj i nie przesyłaj w ramach tego etapu:

- `data/game.sqlite3` ani innej surowej bazy;
- plików `*-wal` lub `*-shm`;
- `data/flask_session`, `flask_session` ani pojedynczych plików sesji;
- cookies, SID, tokenów/generation, credentials, pełnego profilu lub surowych
  logów graczy.

Nie wykonuj `VACUUM`, checkpointu WAL, `.backup`, eksportu SQL, migracji, importu
modułów aplikacji, restartu ani żadnego endpointu recovery. Metadane obecności WAL
i SHM raportowane przez narzędzie są wystarczające dla tej bramki; runbook nie
zgłasza bitowej niezmienności aktywnego filesystemu.

Po przekazaniu materiału pozostaje status:

`READY FOR READ-ONLY SERVER FORENSICS — Sprint 130.10`

Dopiero osobna analiza dowodów i jawna decyzja mogą zmienić go na
`FORENSICS CAPTURED — Sprint 130.10`. Ten dokument nie autoryzuje żadnej naprawy.
