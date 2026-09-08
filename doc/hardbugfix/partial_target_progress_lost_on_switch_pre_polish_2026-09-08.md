# Utrata częściowego postępu celu po zmianie zaznaczenia

**Etap:** pre-polish po `138.getway.4`  
**Data:** 2026-09-08  
**Severity:** P1 gameplay  
**Status:** `IMPLEMENTED / LOCAL PASS / SERVER E2E PENDING`

## Problem

Gracz mógł rozbroić część akcji celu i część jego zabezpieczeń, przejść do innego
obiektu, a następnie wrócić do pierwszego celu. Po powrocie cel był tworzony od
stanu początkowego zamiast kontynuować od zapamiętanego miejsca.

Przykładowy utracony stan: trzy odblokowane kropki oraz 60% rozbrojonego paska.
Defekt uniemożliwiał przygotowywanie kilku obiektów i ich późniejsze, strategiczne
dokończenie.

## Root cause

`player_target_runtime` jest celowo lekkim magazynem bieżącego wyboru i posiada
jedną linię na gracza (`username` jako klucz główny). Ustawienie celu B poprawnie
zastępowało aktywny cel A, ale nie istniała osobna projekcja zachowująca ostatni
postęp A. Ciężki profil nie był już źródłem prawdy dla tej ścieżki i nie należy go
przywracać do hot path mapy.

## Rozwiązanie

Dodano kompaktową projekcję `player_target_progress`, identyfikowaną przez:

```text
(username, target_key)
```

Przechowuje ona wyłącznie stan potrzebny do kontynuacji:

- kanoniczny snapshot celu;
- `actions_allowed` — zapalone kropki;
- `security` i wynikający z niego `disarm_progress` — stan paska;
- status, wersję i czas aktualizacji.

Przy zmianie A → B aktywny snapshot A jest utrwalany. Przy powrocie do A backend
odnajduje exact/canonical identity, wykonuje monotoniczny merge i zwraca zdarzenie
`target.resumed`. `False` pozostaje wygrywającym stanem zabezpieczenia, a `True`
wygrywającym stanem odblokowanej akcji, więc świeży payload mapy nie cofa wpływu
gracza.

Exact key i stabilna tożsamość zwykłego POI mają indeksy. Nowy marker nie powoduje
pełnego skanowania historii gracza; szerszy fallback pozostał wyłącznie dla
rzadkiego przypadku zmiany lineage filaru podczas przebudowy konfliktu.

Aktualizacje realizera GhostNetwork (`hack_actions`, `target_security`) również
synchronizują tę projekcję. Nadal obowiązuje CAS aktywnego celu: spóźniony wynik
aplikacji dla A nie może zmodyfikować B.

Stan jest prywatny dla gracza. Ten sam obiekt zaatakowany przez inną osobę zaczyna
od jej własnego stanu.

## Polityka retencji

Na tym etapie postęp częściowy nie ma arbitralnego TTL ani mnożnika poziomu.
Pozostaje zapisany do terminalnego przejęcia/resetu celu. To najbezpieczniejszy
kontrakt gameplayowy: nie usuwa pracy gracza bez czytelnego zdarzenia i nie miesza
naprawy integralności z późniejszym balancingiem.

Po oznaczeniu celu jako `captured` terminalny snapshot blokuje wznowienie starszego
aliasu. Ewentualny czas zaniku zależny od poziomu jest osobnym balansem i wymaga
jawnej decyzji produktowej oraz komunikatu w UI.

## Testy

Automatyczna regresja obejmuje:

- A częściowo schakowane → B → powrót do A;
- trzy kropki i 60% paska zachowane przez pełną ścieżkę `/api/map/aim-target`;
- przetrwanie jawnego wyczyszczenia wyboru i ponownego utworzenia store;
- izolację stanu między dwoma graczami;
- brak wznowienia po terminalnym `captured`;
- istniejące kontrakty stale result, konfliktów i realizerów celu.

## Invariant

```text
aktywny cel = player_target_runtime(username)
ostatni wpływ gracza na obiekt = player_target_progress(username, target_key)
świeży snapshot mapy nie może cofnąć zapisanego postępu
terminalny cel nie może wznowić starszego snapshotu
```

## Pliki

- `database.py`
- `tests/test_target_persistence.py`
- `doc/history/project_journal.md`

## Bramka

`LOCAL PASS / SERVER E2E PENDING`
