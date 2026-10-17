# 157.2 — fundament danych, 16 X 2026

Zapis etapu historycznego. Aktualny stan i dodatkowe tabele przepływów:
[macierz 157](sprint_157_evidence.md), `identity_gateway/schema.py`.

Status: W REALIZACJI, lokalnie. Schemat i prymitywy transakcyjne gotowe;
nie jest to jeszcze pełny odbiór rejestracji zewnętrznej.

## Zakres

`identity_gateway/store.py` dodaje cztery tabele:

- `user_identities`: unikalne provider/subject oraz user/provider, FK do users.
- `identity_account_security`: jawny stan hasła i weryfikacji e-maila.
  Istniejące niepuste hasło pozostaje włączone; brak hasła jest wyłączony.
  Migracja nie zmienia haseł/profili i nie potwierdza historycznych e-maili.
- `identity_consents`: wersja i czas zgody. Brak automatycznych zgód legacy.
- `identity_intents`: losowy jednorazowy token przechowywany jako SHA-256,
  cel, dostawca, powiązanie klienta, konta/generacji, czas i wygaśnięcie.
  Link, reauth i email wymagają konta oraz generacji. Cleanup usuwa wygasłe wpisy.

Wywołujący otwiera transakcję z aktywnymi FK i odpowiada za commit/rollback.
Zużycie tokenu oraz zapis konta/tożsamości muszą odbywać się na tym samym
połączeniu. `BEGIN IMMEDIATE` serializuje konkurencyjne zapisy. Sama intencja
nie jest dowodem zweryfikowania dostawcy lub świeżego reauth: osobny wynik
protokołu i uprawnienie po jego weryfikacji pozostają do implementacji.

## Migracja

`python tools/identity_157_migrate.py --db <baza-testowa>`
→ `ok: true`, `status: dry_run`, `original_data_unchanged: true`, integralność/FK OK.

Dry-run otwiera źródło read-only i wykonuje migrację na spójnym snapshotcie
SQLite w pamięci, uwzględniając WAL. Nie uruchamia drugiej instancji gry.
Potrzebna pamięć rośnie z rozmiarem bazy; nie uruchamiano tego na produkcji.

`python tools/identity_157_migrate.py --db <baza-testowa> --apply`
→ `migrated`; ponowienie → `already_migrated`.

Apply: jedna transakcja, integralność/FK przed i po, porównanie skrótów
wszystkich pierwotnych tabel/kolumn, rollback przy niezgodności. Przed użyciem
produkcyjnym nadal wymagany spójny backup i pełny runbook 157.9.
Nie ma automatycznego downgrade/drop: nowe tożsamości nie mogą zostać utracone
przez rollback kodu. Wyłączone flagi i powrót kodu poprzedzają decyzję o DB.

## Dowody i granice

- Pakiet foundation/store + poświadczenia + rejestracja: 25/25 PASS.
- Po dodaniu testu dwóch połączeń i rozszerzeniu rollbacku: store 7/7 PASS.
- Potwierdzono dokładnie jedno zużycie tokenu, odrzucenie błędnych powiązań,
  wygasanie, FK, unikalność, brak zmiany źródła przez dry-run i idempotencję.
- Błąd po insercie konta i konsumpcji intencji cofa oba zapisy.
- Nie testowano callbacków/UI, nie włączono adapterów ani flag produkcyjnych.

Do pełnego 157.2 pozostają: atomowa usługa tworzenia właściwego profilu CHAOS
z projekcją/LKG, normalizowane rezerwacje nick/e-mail, wynik tożsamości
rejestracyjnej i osobne uprawnienia świeżego reauth. Nowy stan hasła musi być
wpięty w login i zmiany hasła przed tworzeniem kont external-only.
Otwarte warunki audytu 157.1 pozostają zapisane w `sprint_157_1_foundation.md`.
