# Ważność i priorytety narracji — 17 IX 2026

## Ustalenia przed zmianą

- `claim_next_narrative_task` sortował po priority, ale zadanie nie miało
  własnego expires_at. Lease chronił właściciela pracy, nie aktualność tematu.
- Retry i odtwarzanie zadań pozwalały obsługiwać historyczne źródła; kontrola
  incident_context obejmowała publikację nowych incydentów, nie całą kolejkę.
- Publisher pobierał receipts FIFO, bez kolejności priorytetów zleceń.
- Źródła konfliktów nie przekazywały wersji canonical konfliktu do guardu.
- Po włączeniu publishera zaległe zadania mogły stać się nowymi wpisami.
  Sam napis LIVE ani czas publikacji nie dowodzi aktualności źródła.

## Kontrakt po zmianie

| Klasa | Ważność od utworzenia źródła/zlecenia | Priorytet kolejki |
|---|---|---|
| Incydenty i konflikty | 1800 s | 300 + ważność 0–99 |
| Pozostałe bieżące narracje | 7200 s | 200 + ważność 0–99 |
| Redakcja i promocje | 21600 s | 100 + ważność 0–99 |

Wartości są jawne we wszystkich czterech produkcyjnych ecosystemach:
CHAOS_NARRATIVE_TTL_{URGENT,NORMAL,EDITORIAL}_SECONDS oraz
CHAOS_NARRATIVE_PRIORITY_{URGENT,NORMAL,EDITORIAL}.
Wygaśnięcie źródła może jedynie skrócić termin. Retry, idempotent replay,
restart procesu i migracja starego zadania go nie odnawiają. Odtworzony event
GhostNetwork korzysta z canonical created_at eventu.

1. Enqueue zapisuje expires_at i priorytet klasy. Nowa wersja tego samego
   źródła BlackNet wycofuje oczekujące starsze wersje (po 32).
2. Claim utrzymuje indeksowaną kolejkę priority; zadanie wygasłe lub źródło
   zamknięte/zmienione nie trafia do modelu. Legacy expiry jest uzupełniane
   po 32 rekordy, od oryginalnego created_at, bez hydratacji profili.
3. Po modelu aktualność jest sprawdzana ponownie; spóźniony wynik jest odrzucany.
4. Publisher wybiera według priorytetu i w transakcji ponownie sprawdza
   deadline, status oraz wersję canonical źródła.
5. Wygasłe zadania i bieżące publikacje świata są wycofywane partiami;
   pozostają audytowalne rekordy, nie ma kasowania historii bazy.

Incydent przekazuje incident_context; konflikt przekazuje do 8 par
conflict_key/conflict_version. Stary konflikt bez tych danych jest nieweryfikowalny
i nie może być ponownie opublikowany. Nadal aktualne źródło może dostać nowe
zlecenie w kolejnym oknie ważności, bez przedłużania istniejącego zadania.

## Koszt i granice

Nie przyspieszamy samego modelu i nie uruchamiamy równoległych generacji.
Pilny task wyprzedza oczekujące mniej pilne zadania, ale nie przerywa już
trwającego żądania HTTP. Jeśli źródło straci ważność podczas tego żądania,
wynik zostaje odrzucony. Duży napływ różnych pilnych źródeł może nadal
przekraczać przepustowość — część wygaśnie bez publikacji, zgodnie z kontraktem.
Pominięcie narracji nie cofa incydentu ani mechaniki gry.

## Odbiór i diagnostyka

Walidacja lokalna: **95 testów Python PASS (84,942 s)** w izolowanych bazach.
Zakres: freshness, task queue, incident retirement/lifecycle, publication,
event producers i incident pipeline. Test JS czterech ecosystemów PASS.
Sprawdzono m.in. brak claim starego zadania, pierwszeństwo pilnego, replay/retry,
wygaśnięcie podczas generacji i po niej, zmianę źródła w trakcie pracy,
zamknięty konflikt oraz read-only raport bez zmiany statusu kolejki.
Nie wykonano wdrożenia ani pomiaru przepustowości produkcyjnej Ollamy.

Po wdrożeniu ponownie wczytać wszystkie ecosystemy z `--update-env` i zapisać PM2.
Diagnostyka bez inicjalizacji aplikacji, zmian bazy i wywołań Ollamy:

```bash
.venv/bin/python tools/audit_narrative_freshness.py --db data/game.sqlite3
```

Raport pokazuje liczności, najstarsze oczekujące zadania i pierwszych 20
kandydatów wraz z expiry, priorytetem i canonical kontekstem. Nie zawiera
profili ani tekstów prywatnych wiadomości. Czas zakończenia obecnego żądania
modelu pozostaje niezależny od opróżniania starej kolejki.

Konkretny historyczny rekord Abacus wymaga potwierdzenia raportem serwera;
zrzut ekranu sam nie rozstrzyga, czy stare było zadanie, opublikowany rekord,
czy status konfliktu w canonical store.
