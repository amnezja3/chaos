# SPRINT 135.4 — CODEX IMPLEMENTATION BRIEF
## Ollama Outbox/Inbox Daemon on Existing CHAOS Server

Status of this brief: implementation handoff for Codex.

Purpose: build the first real Ollama worker for CHAOS using the Ollama instance that is already installed, running and verified on the production server.

This document is intentionally split into:
1. confirmed server/runtime facts,
2. existing CHAOS contracts that must be preserved,
3. implementation requirements for `chaos-ollama-worker`,
4. operational constraints and test gates.

The worker must be lightweight, fail-safe and isolated from gameplay. Reuse the same operational discipline already used by the existing dedicated CHAOS worker processes: small responsibility surface, bounded DB work, explicit lifecycle, idempotency, controlled retries, observability, no heavy profile reads and no hidden side effects.

---

# 1. CONFIRMED SERVER STATE

## 1.1 Host

Confirmed production host characteristics:

```text
architecture        x86_64
kernel              Linux 5.15.0-186-generic
virtual CPUs        8
CPU model           Intel Core Processor (Broadwell, IBRS)
threads/core        1
RAM total           ~11 GiB
RAM available       ~7.9 GiB at audit time
swap total          8 GiB
swap used           ~1.7 GiB at audit time
root filesystem     158 GiB
root used           66 GiB
root available      86 GiB
GPU                  none
NVIDIA               none / nvidia-smi unavailable
```

This is a CPU-only host.

Do not design the worker assuming CUDA, ROCm, GPU offload or multiple concurrent model generations.

Initial concurrency must remain:

```text
concurrency = 1
```

---

# 2. CONFIRMED OLLAMA RUNTIME

## 2.1 Binary and service

```text
binary              /usr/local/bin/ollama
Ollama version      0.15.4
systemd service     ollama.service
service state       active
service enabled     yes
service user        ollama
service group       ollama
ExecStart           /usr/local/bin/ollama serve
restart policy      always
RestartSec          3
```

Service has been running stably for approximately one month at the time of audit.

Observed service memory before loading the LLM:

```text
~688 MB
```

Do not replace the existing systemd Ollama service.

Do not run `ollama serve` from PM2.

`chaos-ollama-worker` must connect to the already-running local Ollama service.

---

# 3. NETWORK / SECURITY STATE

Confirmed listener:

```text
127.0.0.1:11434
```

This is correct and must stay local-only.

Canonical base URL:

```text
http://127.0.0.1:11434
```

Confirmed:

- no Apache reverse proxy for Ollama,
- no nginx reverse proxy for Ollama,
- no UFW rule opening TCP/11434 publicly,
- Ollama API is not intended to be internet-facing.

Hard invariant:

```text
OLLAMA_BASE_URL == http://127.0.0.1:11434
```

The worker must fail configuration verification if a configured Ollama base URL points to:

- `0.0.0.0`,
- a public IP,
- a DNS hostname,
- HTTPS cloud endpoints,
- any address other than explicit local loopback allowed by policy.

No Ollama Cloud.

No remote LLM.

No fallback to external providers.

---

# 4. INSTALLED MODEL

Exactly one model was confirmed during audit:

```text
model               llama3.1:8b
family              llama
base                 Meta-Llama-3.1
variant              Instruct
parameters           8,030,261,312
size                 ~4.9 GB
format               GGUF
quantization         Q4_K_M
native context       131072
capabilities         completion, tools
```

Installed model digest reported by `/api/tags`:

```text
46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e
```

The model was not loaded at audit time:

```text
ollama ps -> empty
```

Do not automatically pull another model.

Do not silently switch tags.

Do not use the model's full native 131072-token context.

Initial CHAOS policy:

```text
model               llama3.1:8b
num_ctx             4096
num_predict         512
temperature         0
concurrency         1
keep_alive          5m
connect_timeout     2s
read_timeout        120s
stream              false
think               false
tools               none
```

These are initial bounded production-safe values for Sprint 135.4.

They may later be benchmarked, but 135.4 must start conservatively.

---

# 5. EXISTING, VERIFIED OLLAMA TRANSPORT PATTERN

A previously working local wrapper already exists conceptually and has been confirmed against this server/model.

Known-good transport pattern:

```python
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_FALLBACK_MODEL = "llama3.1:8b"
OLLAMA_TIMEOUT = (2, 120)

def _ollama_chat(
    messages,
    model=OLLAMA_FALLBACK_MODEL,
    max_tokens=512,
    temperature=0.7,
    total_timeout=120.0,
    fail_silently=True,
    logger=None,
):
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"

    payload = {
        "model": model,
        "stream": False,
        "keep_alive": "10m",
        "messages": messages,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
        },
    }
```

This proves that local `/api/chat` with `llama3.1:8b` is a known working integration path.

For Sprint 135.4 do NOT copy this wrapper blindly.

Use it only as proof of transport compatibility.

The new domain adapter must be stricter.

Required internal interface:

```text
ChaosOllamaClient.generate(task_package, policy)
    -> OllamaGenerationResult
```

Do not expose raw Ollama API details to the rest of CHAOS.

---

# 6. OLLAMA API CONTRACT FOR 135.4

The worker only needs these local endpoints:

```text
GET  /api/version
GET  /api/tags
POST /api/show
POST /api/chat
```

Production generation uses:

```text
POST http://127.0.0.1:11434/api/chat
```

Required request properties:

```json
{
  "model": "llama3.1:8b",
  "stream": false,
  "think": false,
  "keep_alive": "5m",
  "messages": [
    {
      "role": "system",
      "content": "VERSIONED CHAOS SYSTEM PROMPT"
    },
    {
      "role": "user",
      "content": "BOUNDED DETERMINISTIC TASK PACKAGE"
    }
  ],
  "format": {
    "...": "CHAOS narrative output JSON Schema v1"
  },
  "options": {
    "temperature": 0,
    "num_ctx": 4096,
    "num_predict": 512
  }
}
```

Never send:

```text
tools
tool definitions
database credentials
player profile
full world state
external URLs
arbitrary user system prompts
gameplay mutation instructions
```

---

# 7. CHAOS DOMAIN BOUNDARY

Ollama is a narrative processor only.

Ollama is NOT:

- source of truth,
- gameplay authority,
- database agent,
- tool executor,
- world-state mutator,
- profile mutator,
- wallet mutator,
- GhostNetwork mutator,
- territory mutator,
- operation mutator,
- reward engine,
- publisher to UI.

Hard invariant:

```text
GAMEPLAY EVENT
    -> canonical safe facts
    -> Outbox
    -> Ollama
    -> Inbox candidate
    -> validator
    -> ACCEPTED / QUARANTINED / REJECTED
```

Sprint 135.4 stops there.

There is NO player-visible publication in 135.4.

Publishing belongs to Sprint 135.5.

---

# 8. EXISTING CANONICAL OUTBOX

The single canonical runtime queue already exists in SQLite:

```text
ghost_narrative_outbox
```

It is the only source of truth for Ollama work.

Do not create another runtime queue.

Do not make `instance/blacknet_ollama_outbox/*.json` a queue.

Legacy BlackNet JSON files remain diagnostics/export only.

The queue already contains the Sprint 135.2 lifecycle concepts:

```text
READY
CLAIMED
PROCESSING
MODEL_COMPLETED
INBOX_RECORDED
RETRY_WAIT
DEAD_LETTER
```

Exact implementation must follow the repository contract already present in the codebase rather than inventing competing state names.

---

# 9. REQUIRED WORKER PROCESS

Create a separate PM2 process:

```text
chaos-ollama-worker
```

Do not add Ollama processing loops to:

```text
chaos
chaos-territory-worker
```

The worker must have one responsibility:

```text
consume eligible canonical Ollama Outbox tasks
-> call local Ollama
-> persist canonical Inbox candidate
-> validate
-> finalize Outbox state
```

It must not serve HTTP traffic.

It must not publish content.

It must not scan profiles.

It must not rebuild GhostNetwork.

It must not perform territory logic.

---

# 10. REUSE EXISTING WORKER BEST PRACTICES

The new worker must intentionally follow the good operational patterns already used by the existing dedicated CHAOS worker architecture.

## 10.1 Process isolation

Use a dedicated long-running process.

A crash in Ollama processing must not crash:

```text
web runtime
territory worker
gameplay requests
```

The process should be independently restartable by PM2.

---

## 10.2 Lightweight idle loop

When no task is available:

- perform no expensive scans,
- perform no profile reads,
- perform no whole-world rebuild,
- perform no hot-loop polling,
- sleep for a bounded poll interval,
- optionally add small jitter to avoid synchronized wakeups.

Recommended initial idle polling:

```text
1-2 seconds
```

Do not busy-loop.

---

## 10.3 Bounded repository access

Every iteration should operate on:

```text
0 or 1 claimed task
```

Initial concurrency is one.

Never load the entire task backlog into memory just to find work.

Use indexed repository queries.

---

## 10.4 Atomic claim + lease

Task ownership must use the queue's atomic claim/lease mechanism.

Two worker instances racing for the same task must produce:

```text
exactly one lease owner
```

The worker must have a stable instance identity, for example:

```text
hostname + pid + boot nonce
```

Do not use process ID alone as permanent task ownership identity.

---

## 10.5 Heartbeat / lease renew

Model generation can last significantly longer than normal DB operations.

While `/api/chat` is running:

- renew the lease on a bounded interval,
- renew only if the current worker still owns the lease,
- stop work if lease ownership is lost,
- never allow a stale owner to finalize a task.

Required invariant:

```text
old lease owner cannot persist a valid result after task takeover
```

Lease renewal should not hammer SQLite.

Use a heartbeat comfortably shorter than lease duration.

Example policy to benchmark:

```text
lease duration      180s
heartbeat           30s
```

Do not hard-code these without configuration.

---

## 10.6 Graceful shutdown

Handle at minimum:

```text
SIGTERM
SIGINT
```

On shutdown:

- stop claiming new work,
- finish or safely abandon current work,
- do not leave a task falsely completed,
- do not overwrite ownership after lease loss,
- close DB resources cleanly,
- allow PM2 restart without queue corruption.

If generation cannot be cancelled safely, rely on lease semantics and CAS on finalization.

---

## 10.7 Fail-open gameplay / fail-closed narration

If Ollama is:

```text
offline
slow
crashed
out of memory
returning invalid output
```

gameplay must continue.

Narrative processing may retry or stop.

No gameplay request waits for Ollama.

No game mutation is rolled back because Ollama failed.

On the other side:

```text
invalid / unvalidated output
```

must never progress to publishable state.

---

## 10.8 Idempotency everywhere

Required identities include:

```text
task_id
attempt_id
candidate_id
publication identity later in 135.5
```

A crash after Inbox insert but before Outbox completion must NOT create a second candidate.

The worker must be able to resume by discovering the already-persisted candidate/attempt and finalizing idempotently.

---

## 10.9 Small logs, strong metrics

Do not log:

```text
full prompt
full model output
hidden facts
owner-private facts
emails
session data
profile JSON
arbitrary raw payloads
```

Logs should carry identifiers and bounded diagnostics:

```text
task_id
attempt_id
source_scope
target_medium
audience_scope
model
model_digest
prompt_version
schema_version
duration_ms
prompt_eval_count
eval_count
result
error_code
retry_count
lease_owner
```

Raw model output may be stored only in the bounded canonical Inbox/audit structure allowed by the Sprint 135.4 contract.

---

# 11. HARD BAN ON HEAVY PROFILE ACCESS

The worker must never call:

```text
get_profile()
list_profiles()
profile_json
profile_bytes
```

Required runtime metrics must remain:

```text
profile_full_read = 0
profile_full_write = 0
profile_bytes = 0
all_user_profile_scan = 0
per_recipient_profile_read = 0
```

The worker reads only the already-projected task payload from Outbox plus the queue/Inbox repositories required for processing.

Audience projection already happened before enqueue in Sprint 135.3.

The worker must not repeat visibility logic.

---

# 12. TASK ELIGIBILITY / FAIL-CLOSED POLICY

A task may be claimed only if:

```text
processor == ollama
status is claimable
prompt_version is assigned and registered
output_schema_version is assigned and registered
model_policy_version is assigned and registered
target_medium is supported by registry
audience identity is valid
```

Historical or malformed tasks containing values such as:

```text
prompt_version = unassigned
output_schema_version = unassigned
model_policy_version = unassigned
```

must NOT be silently processed.

Fail closed.

Do not backfill these by ad-hoc SQL.

Do not invent fallback prompt policies.

---

# 13. PROMPT / SCHEMA / MODEL POLICY REGISTRY

Implement a versioned internal registry mapping task semantics to processing policy.

Conceptual mapping:

```text
source_scope
+ task_variant
+ target_medium
    ->
prompt_version
output_schema_version
model_policy_version
```

Example:

```text
blacknet_world + world_digest + blacknet
    -> blacknet-world-prompt-v1
    -> chaos-narrative-output-v1
    -> chaos-local-narrator-v1
```

Registry must be code-owned and explicit.

No dynamic prompts loaded from user input.

No arbitrary model selection from task payload.

---

# 14. MODEL OUTPUT SCHEMA V1

The model should only generate narrative fields.

It must NOT generate canonical backend identity fields.

Recommended output:

```json
{
  "title": "string",
  "body": "string",
  "tone": "warning",
  "fact_refs": ["fact_ref_1"],
  "cta_ref": "cta_1"
}
```

JSON Schema v1:

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "title": {
      "type": "string",
      "minLength": 1,
      "maxLength": 96
    },
    "body": {
      "type": "string",
      "minLength": 1,
      "maxLength": 800
    },
    "tone": {
      "type": "string",
      "enum": [
        "info",
        "warning",
        "critical",
        "victory",
        "mystery",
        "system",
        "clan"
      ]
    },
    "fact_refs": {
      "type": "array",
      "minItems": 1,
      "maxItems": 16,
      "uniqueItems": true,
      "items": {
        "type": "string",
        "maxLength": 128
      }
    },
    "cta_ref": {
      "type": ["string", "null"],
      "maxLength": 64
    }
  },
  "required": [
    "title",
    "body",
    "tone",
    "fact_refs",
    "cta_ref"
  ]
}
```

---

# 15. BACKEND-OWNED FIELDS

Never ask the model to echo or choose:

```text
task_id
candidate_id
source
source_scope
source_event_id
source_receipt_id
audience
target_medium
truth_class
prompt_version
output_schema_version
model_policy_version
CTA payload
gameplay outcome
authenticity
canonical sender
```

These are copied/resolved by backend policy.

The model only writes narrative presentation.

---

# 16. CANONICAL INBOX

Sprint 135.4 must introduce or finalize a durable canonical Inbox.

Minimum candidate information:

```text
candidate_id
task_id
attempt_id

output_schema_version
prompt_version
model_policy_version

model_name
model_digest
ollama_runtime_version

target_medium
audience identity copied from Outbox

title
body
tone
fact_refs
cta_ref

bounded_raw_output
output_hash

validation_status
validation_errors
quarantine_reason

created_at
validated_at
```

There must be at most one accepted candidate for a task.

Attempts may be multiple.

The canonical candidate must survive worker restart.

---

# 17. ATTEMPT HISTORY

Persist attempt history separately or additively so operational retry is observable.

Recommended fields:

```text
attempt_id
task_id
worker_id
started_at
completed_at
model
model_digest

request_hash
response_hash

total_duration
load_duration
prompt_eval_count
eval_count

result
error_code
error_message_bounded
retryable
```

Never use logs as the only attempt history.

---

# 18. VALIDATOR

JSON Schema validation from Ollama is not sufficient.

Backend validator must independently verify:

1. output is valid JSON,
2. output matches schema,
3. output size is bounded,
4. every `fact_ref` exists in the task,
5. no unknown fact can be introduced,
6. `cta_ref` exists in allowed actions,
7. model cannot invent arbitrary CTA payload,
8. tone is allowed by the selected prompt/template policy,
9. no forbidden URL,
10. no hidden value is reproduced,
11. no audience escalation,
12. no truth escalation,
13. no gameplay mutation instruction,
14. no canonical sender/authenticity/outcome change.

Validation result:

```text
ACCEPTED
QUARANTINED
REJECTED
```

`ACCEPTED` is still invisible to players during Sprint 135.4.

---

# 19. ERROR CLASSIFICATION

Use explicit error classes.

Recommended policy:

| Failure | Action |
|---|---|
| connection refused | retry |
| connect timeout | retry |
| read timeout | retry |
| HTTP 429 | retry |
| HTTP 500 | retry |
| HTTP 502 | retry |
| HTTP 404 missing model | bounded retry then operational dead-letter |
| HTTP 400 invalid policy/request | configuration error, no blind retry |
| response `done != true` | retry |
| empty `message.content` | retry |
| invalid JSON | one bounded technical retry then reject/quarantine according to policy |
| schema violation | reject/quarantine |
| unknown fact ref | quarantine |
| unknown CTA | quarantine |
| forbidden URL/hidden data | quarantine |
| lease lost before commit | discard result / CAS reject |
| Inbox already persisted | idempotent recovery; do not duplicate candidate |

Do not use `fail_silently=True` in the production worker.

Errors must become explicit queue/attempt state.

---

# 20. OUTBOX COMPLETION ORDER

Critical durability rule:

```text
1. claim task
2. persist attempt start
3. generate
4. parse
5. persist Inbox candidate
6. validate candidate
7. persist validation result
8. finalize Outbox transition
```

Never mark Outbox completed before Inbox durability is confirmed.

Crash boundary:

```text
Inbox insert succeeded
Outbox completion failed
```

must recover without producing a second candidate.

---

# 21. LOCAL CLIENT RESULT TYPE

Do not return only a string.

Conceptual result:

```text
OllamaGenerationResult
    model
    content
    done
    done_reason

    total_duration
    load_duration
    prompt_eval_count
    eval_count

    runtime_version
    model_digest

    raw_response_hash
```

Only bounded/necessary raw data should survive.

---

# 22. PRE-FLIGHT VERIFY MODE

Before enabling real consumption, the worker must support a safe verification mode.

Recommended CLI / module modes:

```text
status
verify
dry-run
run
```

`status`:
- does not claim work,
- reports configured endpoint/model/policies,
- reports queue counts,
- reports whether worker execution is enabled.

`verify`:
- checks `127.0.0.1:11434`,
- GET `/api/version`,
- GET `/api/tags`,
- confirms `llama3.1:8b`,
- confirms expected digest or reports mismatch,
- POST `/api/show`,
- confirms required capability,
- validates DB schema/repositories,
- does NOT claim production tasks,
- does NOT publish.

`dry-run`:
- may process explicitly selected/synthetic test input according to implementation design,
- persists no player-visible publication,
- must not mutate gameplay.

`run`:
- enables normal queue consumption.

Worker should default fail-closed unless explicitly enabled by configuration.

---

# 23. PM2 EXPECTATIONS

Add `chaos-ollama-worker` to the project PM2 ecosystem in the same operational style as existing CHAOS worker processes.

Requirements:

```text
autorestart       true
single instance    1
separate logs      yes
bounded memory     yes / reasonable restart threshold after measurement
cwd                CHAOS project root
environment        explicit
```

Do not fork multiple Ollama worker instances.

Do not use PM2 cluster mode.

Configuration should be through explicit environment variables with sane defaults.

Suggested names:

```text
CHAOS_OLLAMA_WORKER_ENABLED
CHAOS_OLLAMA_BASE_URL
CHAOS_OLLAMA_MODEL
CHAOS_OLLAMA_MODEL_DIGEST
CHAOS_OLLAMA_NUM_CTX
CHAOS_OLLAMA_NUM_PREDICT
CHAOS_OLLAMA_CONNECT_TIMEOUT_SEC
CHAOS_OLLAMA_READ_TIMEOUT_SEC
CHAOS_OLLAMA_KEEP_ALIVE
CHAOS_OLLAMA_CONCURRENCY
CHAOS_OLLAMA_POLL_INTERVAL_SEC
CHAOS_OLLAMA_LEASE_SEC
CHAOS_OLLAMA_HEARTBEAT_SEC
CHAOS_OLLAMA_MAX_ATTEMPTS
```

Secrets are not required for the local Ollama API.

Do not add fake API keys.

---

# 24. RESOURCE SAFETY

The server has approximately 11 GiB RAM and no GPU.

The model file itself is ~4.9 GB.

At runtime there must be enough headroom for:

```text
CHAOS web
territory worker
Ollama service
llama3.1:8b loaded model
OS/cache
SQLite
```

Therefore:

- concurrency remains one,
- keep_alive begins at 5m, not permanent,
- context begins at 4096,
- output begins at 512 tokens,
- no parallel warmup,
- no automatic multiple models,
- no large prompt history,
- no full backlog batching.

Observe real RSS after first model load before increasing anything.

---

# 25. BACKPRESSURE

If task production becomes faster than CPU generation:

- do not spawn more model requests,
- allow canonical Outbox backlog to grow within operational limits,
- expose backlog age/count telemetry,
- optionally prioritize queue tasks using existing queue priority,
- preserve gameplay responsiveness.

Narration is asynchronous and non-critical.

Do not trade game health for narrative latency.

---

# 26. OBSERVABILITY

Minimum operational metrics/status data:

```text
worker_alive
worker_id
worker_enabled
current_task_id
current_attempt_id

ollama_reachable
ollama_version
ollama_model
ollama_model_digest

queue_ready
queue_retry_wait
queue_processing
queue_dead_letter
oldest_ready_age

tasks_claimed_total
tasks_completed_total
tasks_retry_total
tasks_quarantined_total
tasks_rejected_total
lease_lost_total

last_generation_ms
last_prompt_tokens
last_output_tokens
last_error_code
last_success_at
```

Avoid high-cardinality metric labels based on arbitrary content.

---

# 27. TEST MATRIX

## Queue / lease

- two worker instances race -> one lease owner,
- worker crashes after claim -> task recovered after lease expiry,
- heartbeat keeps a long generation owned,
- stale owner response -> CAS reject,
- duplicate retry -> no duplicate candidate,
- crash after Inbox insert -> recovery finalizes same candidate.

## Ollama transport

- API offline -> retry, gameplay healthy,
- connect timeout -> retry,
- generation timeout -> retry,
- model missing -> bounded operational failure,
- wrong digest -> verify failure / policy decision,
- invalid HTTP body -> classified failure,
- `done=false` -> retry,
- empty content -> retry.

## Structured output

- valid JSON/schema -> candidate created,
- invalid JSON -> technical retry policy,
- extra field -> schema reject,
- title/body too long -> reject,
- unknown fact_ref -> quarantine,
- unknown cta_ref -> quarantine,
- URL injection -> quarantine,
- hidden fact reproduction -> quarantine.

## Profiles / performance

Mandatory 35 MB profile fixture regression:

```text
profile_full_read = 0
profile_full_write = 0
profile_bytes = 0
all_user_profile_scan = 0
per_recipient_profile_read = 0
```

## Isolation

- kill Ollama service -> web healthy,
- kill chaos-ollama-worker -> web healthy,
- territory worker healthy,
- restart Ollama -> tasks resume after retry,
- restart PM2 worker -> no duplicate accepted candidate.

---

# 28. DO NOT IMPLEMENT IN 135.4

Absolutely outside this sprint:

```text
BlackNet ollama_enriched publication
Googleplex News publication
Cyberner AGI-2108 publication
BlackNet Radio publication
player-visible content
Googleplex purchased app UI
public publisher receipts
model tools
internet access
gameplay action execution
```

Those belong to later sprint(s), primarily 135.5.

---

# 29. IMPLEMENTATION PRIORITIES

Codex should optimize for:

1. correctness of queue ownership,
2. durability,
3. idempotency,
4. isolation from gameplay,
5. bounded memory/CPU,
6. deterministic structured output,
7. explicit validation,
8. observability,
9. graceful recovery,
10. simplicity.

Do not optimize first for throughput.

Do not add abstractions that are not required for one local model and one worker.

---

# 30. DEFINITION OF DONE

Sprint 135.4 can be considered complete only when this full path is proven:

```text
READY canonical Outbox task
-> atomic claim
-> lease
-> versioned bounded prompt package
-> local 127.0.0.1:11434 /api/chat
-> structured JSON
-> durable canonical Inbox candidate
-> backend validation
-> ACCEPTED / QUARANTINED / REJECTED
-> durable Outbox finalization
```

while simultaneously proving:

```text
NO gameplay mutation
NO player-visible publication
NO profile heavy access
NO second queue
NO external LLM
NO duplicate accepted candidate
NO stale lease owner commit
```

Final sprint gate:

```text
OUTBOX
-> LOCAL OLLAMA
-> INBOX
-> VALIDATED CANDIDATE
-> STILL NOT PUBLISHED
```

---

# 31. SERVER VALIDATION AFTER IMPLEMENTATION

Before enabling normal processing on production:

1. deploy code,
2. do not immediately consume production backlog,
3. start `chaos-ollama-worker` disabled or verify-only,
4. run `status`,
5. run `verify`,
6. confirm:
   - Ollama 0.15.4,
   - `127.0.0.1:11434`,
   - `llama3.1:8b`,
   - expected digest,
   - DB schema healthy,
   - no heavy profile access,
7. perform one controlled dry-run,
8. inspect CPU/RAM while model is loaded,
9. verify lease heartbeat,
10. verify Inbox durability,
11. verify no publication,
12. only then enable normal queue consumption.

Do not combine deployment, queue cutover and publisher activation into one action.

---

# 32. CURRENT KNOWN GOOD CONFIGURATION SUMMARY

```text
HOST
  x86_64
  8 vCPU
  ~11 GiB RAM
  CPU only

OLLAMA
  /usr/local/bin/ollama
  version 0.15.4
  systemd active/enabled
  localhost only
  127.0.0.1:11434

MODEL
  llama3.1:8b
  ~4.9 GB
  8B
  Q4_K_M
  native ctx 131072
  chosen worker ctx 4096
  chosen output max 512
  concurrency 1

WORKER
  chaos-ollama-worker
  PM2
  async from gameplay
  canonical Outbox only
  canonical Inbox only
  no publication
  no profiles
  no tools
  no internet
```

This is the implementation baseline for Sprint 135.4.
