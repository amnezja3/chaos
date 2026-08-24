Ja bym to zamknął teraz, bo to jest dokładnie ten moment. Masz świeżo w głowie architekturę, testerzy grają, a później znowu wejdzie gameplay i będzie "a kiedyś do tego wrócimy..." 😄

Proponuję trzy krótkie sprinty, każdy do zrobienia w 1–2 godziny.

---

# Sprint A — Resource Architecture Audit (dokumentacja)

**Cel**

Ustalić i udokumentować jednoznacznie, gdzie jest Source of Truth każdego rodzaju danych.

### Do wykonania

* `doc/architecture/resource_architecture.md`
* wpis do `doc/history/project_journal.md`

### Dokument

Opisać warstwy:

```text
Repository Content
        │
        ▼
static/*.json
        │
        ▼
JsonResourceStore Import
        │
        ▼
SQLite json_resources
        │
        ▼
Backend Runtime
        │
        ▼
Profile Runtime
```

Tabela:

| Warstwa           | Source of Truth                  |
| ----------------- | -------------------------------- |
| App Catalog       | SQLite json_resources.app_config |
| User Template     | SQLite                           |
| User Security     | SQLite                           |
| Terminal Commands | SQLite                           |
| Profiles          | SQLite                           |
| Runtime           | profile                          |

oraz

```text
static/*.json

↓

seed/reference

↓

NIE runtime
```

---

# Sprint B — Resource Sync

**Cel**

Dodać oficjalny mechanizm synchronizacji.

### Powstaje

```text
tools/
    sync_static_json_resources.py
```

Tryby

```text
dry-run

apply
```

Raport

```text
added

changed

removed

unchanged
```

Nie dotyka profili.

Nie dotyka runtime.

Tylko

```text
json_resources
```

---

# Sprint C — Legacy Cleanup

**Cel**

Oznaczyć co jest legacy.

Nie usuwać.

Nie ryzykować.

### Zrobić

README

```text
static/

app_config.json
    seed

user_template.json
    seed

user_security.json
    seed

terminal_command.json
    seed

resources.json
    legacy

targets.json
    legacy

system_messages.json
    legacy

system_status.json
    legacy

users-a.json
    legacy
```

Dodatkowo:

komentarz w

```python
JsonResourceStore.seed_static_directory()
```

że

```text
To jest seed.

Runtime korzysta z SQLite.
```

---

# Efekt końcowy

Po tych trzech sprintach nie będzie już pytań:

> "czy mam edytować JSON?"

odpowiedź:

```text
Nie.

Edytujesz JSON tylko jako content.

Potem robisz sync.

Gra działa na SQLite.
```

---

## I ja bym dopisał jeszcze jeden punkt.

### Sprint A.1

Sprawdzić czy

```text
JsonResourceStore.seed_static_directory()
```

nie powinien importować

wszystkich

```text
static/*.json
```

😁

Bo to jest chyba największa rzecz, która mnie zastanawia.

Ja bym zrobił whitelistę.

Na przykład:

```python
SEED_RESOURCES = [
    "app_config",
    "user_template",
    "user_security",
    "terminal_command",
    "messages",
    "friends",
]
```

a nie:

```python
for *.json
```

Dlaczego?

Bo dzisiaj wrzucisz do `static/` przypadkiem:

```text
notes.json
```

i...

on wyląduje w SQLite.

To jest moim zdaniem jedyny element architektury, który naprawdę chciałbym jeszcze uporządkować. 
Reszta wygląda już bardzo spójnie.
