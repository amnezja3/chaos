# Tabela kar i kartoteka — consequences-v1

Progi i wspólny licznik zatwierdzone przez autora 20 IX 2026.
Źródło konfiguracji: `config.py: RESPONSE_CONSEQUENCE_TABLE`.
Jest to konfiguracja i przygotowanie kartoteki, nie włączenie wykonania kar.

| Stopień | Mandat | Konfiskata | Areszt |
|---|---|---|---|
| 1 | ×1 | — | — |
| 2 | ×2 | — | — |
| 3 | — | 1 narzędzie | — |
| 4 | — | 2 narzędzia | — |
| 5 | ×3 | 3 narzędzia | — |
| 6 | — | — | 5 min |
| 7 | — | — | 10 min |
| 8 | — | — | 15 min |
| 9 | — | — | 20 min |

| Poziom incydentu | Stopień początkowy |
|---|---|
| L2 | 1 |
| L3 | 3 |
| L4 | 5 |
| L5 | 6 |

`stopień = min(9, początkowy_stopień_poziomu + liczba_wykonanych_kar_gracza)`.
Licznik jest wspólny dla incydentów i poziomów, trwały, bez automatycznego
resetu. Przykład: dwie wykonane kary, następny incydent L3 → stopień 5.
L1 pozostaje obserwacją (w konfiguracji entry=None); nie promujemy go samą
historią do kary. Nie dodajemy generowania L5 w ramach zmiany tabeli.
Szansa 80/30 z 142.5 jest osobnym etapem, nie mnożnikiem stopnia.

## Kwota mandatu i ochrona zasobów

Zachowana baza starego MVP: `max(10, floor(risk/2)) HC`.
Mnożnik tabeli stosowany przed limitem portfela: maksymalnie 18% salda,
z dotychczasową rezerwą `min(50, floor(10% salda))`. Procentowy limit starego
MVP ma minimum 1 HC dla niepustego portfela. Zatem mnożnik nie gwarantuje
kwoty dokładnie ×2/×3 przy małym saldzie. Wszystkie parametry są w configu.
Konfiskata ma zachować co najmniej jedno narzędzie zdolne do operacji.
Dobór konkretnych narzędzi i wykonanie ochrony w kanonicznym inventory
należą do executora 142.6. Nie stosować starej mutacji profile.apps.

## Kartoteka

`response_criminal_records`: actor_id, executed_count, updated_at.
`response_penalty_history`: encounter_id UNIQUE, actor_id, incident_id,
kolejny numer kary, wersja polityki, stopień, plan i faktyczne skutki.
`CriminalRecordStore.prepare` korzysta tylko z małego licznika.
`record_executed` wymaga istniejącej transakcji, receipt selected/executed,
co najmniej jednego faktycznego skutku i niezmienionego licznika.
Retry tego samego encounter nie zwiększa kartoteki. Awaria przed commit
cofa historię i licznik razem z efektami. Brak profili i wewnętrznego commit.

Executor 142.6 ma użyć BEGIN IMMEDIATE: recheck obecności i source, ponowne
przygotowanie planu, wykonanie skutków, zmiana execution_status, zapis
kartoteki oraz outbox w jednej transakcji. Jeśli inna kara zmieni licznik,
starego planu nie wolno wykonać. avoided, sam OBS i not_enabled nie zwiększają
licznika; istniejące receipts 142.5 nie są migrowane na wykonaną karę.
142.6 podpina moduł do kanonicznego executora. Kontrolowany rollout na main
opisuje `sprint_142_6_canonical_consequences.md`; gameplay PASS pozostaje otwarty.

## Areszt: zatwierdzone online/offline

Wykonanie wymaga statusu online. Czas rozlicza serwer na podstawie obecności.
Offline zamraża pozostały czas; reconnect wznawia, nie resetuje ani nie
odbywa kary za czas nieobecności. Nie używać samego wall-clock expires_at.
Reguły są zapisane w configu i kopiowane do planu kary. Właściwy zegar,
transport i ograniczenia pozostają implementacją 143.
Do czasu obsługi aresztu nie wolno stopni 6–9 zamieniać na mandat ani uznawać
za wykonane. Rollout 142.6 musi jawnie obsłużyć nieobsługiwany rodzaj sankcji.

Walidacja: 14 testów PASS — tabela, granice poziomów, wspólny licznik,
limity mandatu, retry, rollback, odrzucenie avoided/not_enabled oraz regresja
spotkań 142.5. Test reguł zegara sprawdza konfigurację, nie gotowy timer.
