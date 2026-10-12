# 154.8 — odbiór lokalny przed wdrożeniem

Data: 11 X 2026. Status: **LOCAL PASS / pakiet przedwdrożeniowy**.
Pełny sprint: **SERVER LIVE ACCEPTANCE PENDING**, nie PASS produkcyjny.

## Zaimplementowano

- Wspólny kontrakt, odseparowana tożsamość modelu, migracja historii.
- Mistral REST: stały HTTPS endpoint, brak redirect/retry, ograniczenie odpowiedzi,
  tekst/string chunks, usage, stop/length, redagowane błędy, rozpoznawanie quota.
- Proces wywołania z deadline i sprzątaniem; SIGTERM zatrzymuje nową pracę
  i anuluje aktywne wywołanie, lease i aktualność źródła kontrolowane przed fallbackiem.
- Jeden task, do dwóch subprób; brak przełączania modelu dla odrzucenia faktów.
- Wspólne blokady, circuit, probe/recovery, lokalna rezerwacja budżetu UTC.
- Panel PL/EN: model, primary, limity, kontrola rewizji, diagnostyka i historia.
- Klucz tylko w środowisku; status boolean w panelu, brak pola zapisującego sekret.
- Migracja/status/rollback CLI i [runbook](../runbooks/narrative_providers_154_8.md).

## Wyniki automatyczne

Pełny przebieg 12 modułów: **160 testów PASS**. Następnie cztery testy celowane
PASS: rozszerzony test publikacji, nowa natychmiastowa kontrola lease, odebranie
wyniku procesu spawn oraz migracja/status/rollback CLI. Trzy z nich to nowe testy
(łącznie 163 unikalne przypadki w aktualnym zestawie).

Weryfikowano: błędy 400/401/402/403/404/408/409/422/429/5xx, redakcję danych,
truncation vs quota, niepoprawny JSON vs odrzucenie faktów, niedostępność obu,
następne zadanie po awarii, brak claimu przy niesprawnych providerach, circuit
wspólny dla instancji, automatyczne i ręczne recovery, limity i konflikt rewizji.

Sprawdzono też: brak procesu potomnego po deadline, zakończenie poprawnego procesu,
migrację legacy, odczyt po ponownym otwarciu bazy, brak fikcyjnego digestu Ollamy,
normalny worker → candidate → publisher → jedna widoczna publikacja oraz replay
bez drugiej publikacji. Mistral w tych scenariuszach jest atrapą, nie płatnym API.

## Playwright MCP

Lokalny fixture `tools/sprint_154_8_browser_fixture.py`, izolowana baza i admin:

- PL: odczyt ustawień, pobranie listy modeli, wybór Mistrala/modelu i zapis rewizji 2.
- Diagnostyka pokazuje osobno niesprawnego Mistrala i sprawną Ollamę.
- EN: ustawienia zachowane po przeładowaniu; brak pola sekretu.
- Mobile 390×844: brak poziomego overflow dokumentu, dostępne kontrolki.
- Zmiana z drugiego okna → 409 z czytelnym komunikatem konfliktu; odświeżenie
  i przełączenie primary z powrotem na Ollamę działają.
- Konsola: oczekiwany 409 symulowanego konfliktu i 404 favicon fixture;
  brak wyjątków JS panelu. Przeglądarka i fixture zamknięte po teście.

## Niewykonane / wymagane na serwerze

W środowisku brak `CHAOS_MISTRAL_API_KEY`; nie wywołano prawdziwego Mistrala,
nie potwierdzono modelu/konta ani regionu drugiej aplikacji. Nie wykonano
30-minutowego ruchu, jakości narracji każdej polityki/języka, pomiarów CPU/RAM
współdzielonej Ollamy ani odbioru produkcyjnego PM2/SIGTERM.

Nowa ścieżka pozostaje domyślnie Ollama-only. Gotowość do dostarczenia kodu
nie oznacza zatwierdzenia Mistrala jako głównego dostawcy ani odblokowania 155.
