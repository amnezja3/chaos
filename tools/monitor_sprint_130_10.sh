#!/usr/bin/env bash

# Sprint 130.10 manual gate monitor.
# Run this file as a process (`bash tools/monitor_sprint_130_10.sh`), never source it.

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
    printf '%s\n' 'Uruchom monitor jako osobny skrypt, nie przez source ani wklejanie do sesji SSH.' >&2
    return 2
fi

set -Eeuo pipefail

usage() {
    cat <<'EOF'
Uzycie:
  bash tools/monitor_sprint_130_10.sh [plik-wynikowy]

Domyslnie wynik trafia do:
  logs/sprint-130-10-monitor-<UTC>-<PID>.log

Opcjonalne zmienne:
  CHAOS_MONITOR_PM2_NAMES     Lista procesow PM2, domyslnie:
                             chaos,chaos-territory-worker
  CHAOS_MONITOR_START_LINES  Liczba poprzednich linii do sprawdzenia, domyslnie 0

Monitor zakoncz przez Ctrl+C. Plik wynikowy zostanie domkniety automatycznie.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi
if (( $# > 1 )); then
    usage >&2
    exit 2
fi

for required_command in pm2 node tail awk date wc tr realpath mktemp mkfifo rm rmdir; do
    if ! command -v "$required_command" >/dev/null 2>&1; then
        printf 'Brak wymaganej komendy: %s\n' "$required_command" >&2
        exit 2
    fi
done

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
FILE_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
PM2_NAMES="${CHAOS_MONITOR_PM2_NAMES:-chaos,chaos-territory-worker}"
START_LINES="${CHAOS_MONITOR_START_LINES:-0}"

if [[ ! "$START_LINES" =~ ^[0-9]+$ ]]; then
    printf 'CHAOS_MONITOR_START_LINES musi byc liczba >= 0.\n' >&2
    exit 2
fi

if (( $# == 1 )); then
    if [[ "$1" = /* ]]; then
        OUTPUT_FILE="$1"
    else
        OUTPUT_FILE="$REPO_ROOT/$1"
    fi
else
    OUTPUT_FILE="$REPO_ROOT/logs/sprint-130-10-monitor-${FILE_STAMP}-$$.log"
fi

if [[ -e "$OUTPUT_FILE" || -L "$OUTPUT_FILE" ]]; then
    printf 'Plik wynikowy juz istnieje; nie nadpisuje: %s\n' "$OUTPUT_FILE" >&2
    exit 2
fi

if ! PM2_JSON="$(pm2 jlist 2>/dev/null)"; then
    printf 'Nie udalo sie odczytac konfiguracji przez pm2 jlist.\n' >&2
    exit 2
fi

if ! LOG_SPECS="$({ printf '%s' "$PM2_JSON"; } | MONITOR_PM2_NAMES="$PM2_NAMES" node -e '
let raw = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", chunk => { raw += chunk; });
process.stdin.on("end", () => {
    let apps;
    try {
        apps = JSON.parse(raw);
    } catch (error) {
        console.error("pm2 jlist nie zwrocil poprawnego JSON: " + error.message);
        process.exitCode = 2;
        return;
    }
    const wanted = String(process.env.MONITOR_PM2_NAMES || "")
        .split(",")
        .map(value => value.trim())
        .filter(Boolean);
    const pathModule = require("path");
    const output = [];
    const failures = [];
    for (const wantedName of wanted) {
        const matches = apps.filter(app => {
            const env = app.pm2_env || {};
            return String(app.name || env.name || "") === wantedName;
        });
        if (!matches.length) {
            failures.push(`brak procesu PM2 ${wantedName}`);
            continue;
        }
        const online = matches.filter(app => String((app.pm2_env || {}).status || "") === "online");
        if (!online.length) {
            failures.push(`proces PM2 ${wantedName} nie jest online`);
            continue;
        }
        for (const app of online) {
            const env = app.pm2_env || {};
            const instance = `${wantedName}#${app.pm_id}`;
            for (const [stream, field] of [["out", "pm_out_log_path"], ["error", "pm_err_log_path"]]) {
                const path = String(env[field] || "").trim();
                if (!path) {
                    failures.push(`brak ${field} dla ${instance}`);
                    continue;
                }
                output.push([instance, stream, path].join("\t"));
            }
            const debugStdout = /^(1|true|yes|on)$/i.test(
                String(env.CHAOS_BACKEND_DEBUG_STDOUT || "")
            );
            if (wantedName === "chaos" && !debugStdout) {
                const cwd = String(env.pm_cwd || env.cwd || process.cwd());
                const configured = String(
                    env.CHAOS_BACKEND_DEBUG_LOG || "data/logs/backend_debug.log"
                ).trim();
                const debugPath = pathModule.isAbsolute(configured)
                    ? configured
                    : pathModule.resolve(cwd, configured);
                output.push([instance, "app-flow", debugPath].join("\t"));
            }
        }
    }
    if (failures.length) {
        console.error(failures.join("; "));
        process.exitCode = 3;
        return;
    }
    process.stdout.write(output.join("\n"));
});
')"; then
    exit 2
fi

pm2_state_lines() {
    local phase="$1"
    local state_json="$2"
    { printf '%s' "$state_json"; } | \
    MONITOR_PM2_NAMES="$PM2_NAMES" MONITOR_PM2_PHASE="$phase" node -e '
let raw = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", chunk => { raw += chunk; });
process.stdin.on("end", () => {
    const apps = JSON.parse(raw);
    const phase = String(process.env.MONITOR_PM2_PHASE || "unknown");
    const wanted = new Set(
        String(process.env.MONITOR_PM2_NAMES || "")
            .split(",")
            .map(value => value.trim())
            .filter(Boolean)
    );
    for (const app of apps) {
        const env = app.pm2_env || {};
        const name = String(app.name || env.name || "");
        if (!wanted.has(name)) continue;
        const fields = {
            phase,
            name,
            pm_id: app.pm_id,
            pid: app.pid || 0,
            status: env.status || "unknown",
            restart_time: env.restart_time || 0,
            unstable_restarts: env.unstable_restarts || 0,
            profile_metrics: env.CHAOS_PROFILE_WRITE_METRICS || "0",
            db_lock_metrics: env.CHAOS_DB_LOCK_METRICS || "0",
            backend_debug_stdout: env.CHAOS_BACKEND_DEBUG_STDOUT || "0"
        };
        console.log("# pm2_state " + Object.entries(fields)
            .map(([key, value]) => `${key}=${String(value).replace(/\\s+/g, "_")}`)
            .join(" "));
    }
});
'
}

declare -a LOG_PATHS=()
declare -a LOG_METADATA=()
declare -A SEEN_LOG_PATHS=()
while IFS=$'\t' read -r process_name stream_name log_path; do
    [[ -n "$process_name" && -n "$stream_name" && -n "$log_path" ]] || continue
    LOG_METADATA+=("$process_name"$'\t'"$stream_name"$'\t'"$log_path")
    if [[ -z "${SEEN_LOG_PATHS[$log_path]+present}" ]]; then
        SEEN_LOG_PATHS["$log_path"]=1
        LOG_PATHS+=("$log_path")
    fi
done <<< "$LOG_SPECS"

if (( ${#LOG_PATHS[@]} == 0 )); then
    printf 'PM2 nie zwrocil zadnej sciezki logu do monitorowania.\n' >&2
    exit 2
fi

mkdir -p -- "$(dirname -- "$OUTPUT_FILE")"
OUTPUT_FILE="$(realpath -m -- "$OUTPUT_FILE")"
for log_path in "${LOG_PATHS[@]}"; do
    if [[ "$OUTPUT_FILE" == "$(realpath -m -- "$log_path")" ]]; then
        printf 'Plik wynikowy nie moze byc monitorowanym logiem: %s\n' "$OUTPUT_FILE" >&2
        exit 2
    fi
done

existing_logs=0
for log_path in "${LOG_PATHS[@]}"; do
    if [[ -e "$log_path" ]]; then
        ((existing_logs += 1))
    else
        printf 'Uwaga: log jeszcze nie istnieje; tail -F poczeka na plik: %s\n' "$log_path" >&2
    fi
done
if (( existing_logs == 0 )); then
    printf 'Zaden wykryty log PM2 obecnie nie istnieje. Przerwano monitor.\n' >&2
    exit 2
fi

umask 077
if ! (set -o noclobber; : > "$OUTPUT_FILE") 2>/dev/null; then
    printf 'Nie utworzono pliku wynikowego (juz istnieje albo jest niedostepny): %s\n' \
        "$OUTPUT_FILE" >&2
    exit 2
fi

{
    printf '# sprint=130.10\n'
    printf '# monitor_started_at=%s\n' "$STARTED_AT"
    printf '# timestamp_source=monitor_ingest_utc\n'
    printf '# start_lines=%s\n' "$START_LINES"
    pm2_state_lines "start" "$PM2_JSON"
    for metadata in "${LOG_METADATA[@]}"; do
        IFS=$'\t' read -r process_name stream_name log_path <<< "$metadata"
        printf '# pm2_process=%s stream=%s path=%s\n' "$process_name" "$stream_name" "$log_path"
    done
    printf '# data_begin\n'
} >> "$OUTPUT_FILE"

MONITOR_REASON="setup_error"
STREAM_DIR=""
STREAM_FIFO=""
TAIL_PID=""
AWK_PID=""

stop_stream_processes() {
    local pid
    for pid in "$TAIL_PID" "$AWK_PID"; do
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid" 2>/dev/null || true
        fi
    done
    for pid in "$TAIL_PID" "$AWK_PID"; do
        if [[ -n "$pid" ]]; then
            wait "$pid" 2>/dev/null || true
        fi
    done
    TAIL_PID=""
    AWK_PID=""
    if [[ -n "$STREAM_FIFO" ]]; then
        rm -f -- "$STREAM_FIFO" || true
        STREAM_FIFO=""
    fi
    if [[ -n "$STREAM_DIR" ]]; then
        rmdir -- "$STREAM_DIR" 2>/dev/null || true
        STREAM_DIR=""
    fi
}

finalize_monitor() {
    local exit_code="$1"
    local ended_at line_count final_pm2_json
    trap - EXIT
    trap '' INT TERM
    stop_stream_processes
    ended_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf '# data_end\n' >> "$OUTPUT_FILE"
    if final_pm2_json="$(pm2 jlist 2>/dev/null)" && \
            pm2_state_lines "stop" "$final_pm2_json" >> "$OUTPUT_FILE" 2>/dev/null; then
        :
    else
        printf '# pm2_state phase=stop unavailable=true\n' >> "$OUTPUT_FILE"
    fi
    printf '# monitor_stopped_at=%s reason=%s exit_code=%s\n' \
        "$ended_at" "$MONITOR_REASON" "$exit_code" >> "$OUTPUT_FILE"
    line_count="$(wc -l < "$OUTPUT_FILE" | tr -d '[:space:]')"
    printf '\nMonitor zakonczony. Gotowy plik: %s\nLiczba linii: %s\n' \
        "$OUTPUT_FILE" "$line_count" >&2
}

handle_signal() {
    local reason="$1"
    local exit_code="$2"
    MONITOR_REASON="$reason"
    trap '' INT TERM
    stop_stream_processes
    exit "$exit_code"
}

trap 'finalize_monitor "$?"' EXIT
trap 'handle_signal ctrl_c 130' INT
trap 'handle_signal terminated 143' TERM

printf 'Sprint 130.10 monitoruje %s unikalnych logow PM2.\n' "${#LOG_PATHS[@]}"
printf 'Wynik: %s\n' "$OUTPUT_FILE"
printf 'Wykonaj manual. Zakoncz przez Ctrl+C.\n\n'

# Keep the default focused on integrity/session/GN/territory signals and on
# relevant HTTP/error lines. A traceback is copied as one block (up to 80 lines)
# so its frames are not lost by line-oriented filtering.
FILTER_REGEX='(\[PROFILE_WRITE\]|\[PROFILE\]|\[SESSION\]|\[DB_LOCK\]|\[GHOSTNETWORK\]|\[ghostnetwork\]|\[TERRITORY[^]]*\]|\[STRATEGIC_PROGRESSION\]|\[PROGRESSION_SETTLEMENT\]|\[GONNA_WIN[^]]*\]|\[CAPTURED_OBJECT_MENU\]|\[HACK_ACTION_FORBIDDEN\]|\[APP_FLOW_BE |\[PERF\]|\[DELTA\]|\[WARN\]|\[EXCEPTION\]|\[(ERROR|CRITICAL)\]|Profile(Write|Recovery|Validation|Destructive)|Wallet(NotInitialized|Write|Idempotency|Insufficient)|[[:alnum:]_.]+(Error|Exception):|session_generation|database is locked|OperationalError|WORKER TIMEOUT|Worker exiting|Booting worker|SIGKILL|SystemExit|Traceback \(most recent call last\):|"(GET|POST|PUT|PATCH|DELETE) /(desktop|map|logout|gonna-win|api/profile|api/wallet|api/apps|api/ghostnetwork|api/state/changes|api/map|api/ghost-control|api/pro-system|command)([ ?/]| HTTP)|"POST / HTTP/|" [45][0-9][0-9] |^tail:)'

STREAM_DIR="$(mktemp -d "${TMPDIR:-/tmp}/chaos-13010-monitor.XXXXXX")"
STREAM_FIFO="$STREAM_DIR/log-stream"
mkfifo -- "$STREAM_FIFO"

tail -n "$START_LINES" -F -v -- "${LOG_PATHS[@]}" > "$STREAM_FIFO" 2>&1 &
TAIL_PID=$!

MONITOR_FILTER_REGEX="$FILTER_REGEX" \
MONITOR_OUTPUT_FILE="$OUTPUT_FILE" \
TZ=UTC \
awk '
BEGIN {
    source = "pm2";
    trace = 0;
    trace_lines = 0;
    filter = ENVIRON["MONITOR_FILTER_REGEX"];
    output = ENVIRON["MONITOR_OUTPUT_FILE"];
}

function emit(message, stamp, record) {
    stamp = strftime("%Y-%m-%dT%H:%M:%SZ");
    record = stamp " [" source "] " message;
    print record;
    print record >> output;
    fflush();
    fflush(output);
}

/^==> .* <==$/ {
    source = $0;
    sub(/^==> /, "", source);
    sub(/ <==$/, "", source);
    gsub(/\\/, "/", source);
    count = split(source, path_parts, "/");
    source = path_parts[count];
    next;
}

/Traceback \(most recent call last\):/ {
    trace = 1;
    trace_lines = 1;
    emit($0);
    next;
}

trace {
    trace_lines += 1;
    emit($0);
    if ($0 ~ /(^|[[:space:]])[[:alnum:]_.]+(Error|Exception|Interrupt|Exit)(:|$)/ || trace_lines >= 80) {
        trace = 0;
        trace_lines = 0;
    }
    next;
}

$0 ~ filter {
    emit($0);
}
' < "$STREAM_FIFO" &
AWK_PID=$!
MONITOR_REASON="stream_error"

if wait "$AWK_PID"; then
    stream_status=0
else
    stream_status=$?
fi
AWK_PID=""
tail_status=0
if [[ -n "$TAIL_PID" ]]; then
    if kill -0 "$TAIL_PID" 2>/dev/null; then
        kill -TERM "$TAIL_PID" 2>/dev/null || true
    fi
    if wait "$TAIL_PID" 2>/dev/null; then
        tail_status=0
    else
        tail_status=$?
    fi
    TAIL_PID=""
fi
stop_stream_processes
if (( stream_status != 0 )); then
    exit "$stream_status"
fi
if (( tail_status != 0 )); then
    exit "$tail_status"
fi
exit 1
