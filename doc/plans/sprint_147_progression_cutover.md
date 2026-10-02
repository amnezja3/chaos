# 147 — integracja progresji wymagająca zatwierdzenia

**Aktualizacja 2 X 2026:** autor zatwierdził integrację pod warunkiem audytu.
[Audyt](../audits/sprint_147_progression_risk_2026_10_02.md) wykonano i zastosowano
w kodzie. Integracja `database.py` została dopuszczona i wykonana lokalnie:
checkpointy, małe projekcje, guarded writers i obie metody rozliczeń korzystają
z nowego magazynu. Test wcześniej pominięty jest aktywny i przechodzi.
Poniższy opis odrzucenia dokumentuje stan z 1 X, nie aktualną blokadę uprawnień.
Cutover przejęć i workerów wykonano lokalnie 2 X. Aktualne wymagania migracji
i granice odbioru opisuje runbook 147.

Stan 1 X 2026: przygotowany moduł izolowany; **integracja nie została zastosowana**.
Automatyczna kontrola dwukrotnie odrzuciła patch wspólnej warstwy profili.
Powód: globalny zakres (inicjalizacja bazy, odczyty/zapisy profilu, projekcje
wszystkich użytkowników) oraz ryzyko niespójności lub podwójnego naliczania nagród.

## Przygotowany kod

- `player_progression.py`: osobny magazyn przyrostów LVL/RSP oraz stanu terytorium.
  Nagroda, receipt i komunikaty systemowe zapisują się w jednej transakcji.
  Powtórzony receipt zwraca poprzedni wynik, bez kolejnej nagrody/wiadomości.
  Brak migracji lub poprawnych małych projekcji kończy się recovery.
- `tools/migrate_player_progression.py`: migracja offline z jawną listą maksymalnie
  100 kont na przebieg, domyślny dry-run, walidacja checksumy i rewizji. Istniejący
  zapis nagród nie jest nadpisywany. Zmiana profilu podczas migracji cofa transakcję.
- `tests/test_player_progression.py`: testy atomowości, ponowień, równoległych
  nagród, rollbacku po błędzie komunikatu, brakujących projekcji i migracji.
  SQL pełnego profilu jest blokowany podczas rozliczania nagrody.

Moduł nie jest podłączony do produkcyjnego runtime. Nie uruchamiać migracji
produkcyjnej przed wdrożeniem zatwierdzonej i przetestowanej integracji.

## Konkretny zakres odrzuconego patcha w `database.py`

1. Utworzenie pustej tabeli `player_progression` w `init_db`.
2. Inicjalizacja wpisu wyłącznie przy tworzeniu nowego konta; stare konta przez
   osobną migrację offline. Bez leniwej odbudowy w requestach.
3. Odczyt profilu dodaje przyrosty nagród, których nie obejmuje zapisany checkpoint.
   Ponowny odczyt tego samego checkpointu nie dodaje ich drugi raz.
4. Zapis innych ustawień najpierw uwzględnia aktualne nagrody i zapisuje checkpoint.
   Pole checkpointu nie może być dowolnie zmieniane przez zwykły patch profilu.
5. Małe projekcje zachowują checkpoint przy odświeżaniu, żeby poziom i respekt
   używane przez gameplay odpowiadały naliczonym nagrodom.

Zapis samej nagrody nie modyfikuje `users.profile_json` ani jego checksumy.
Zmienia metadane rewizji, aby starszy pełny zapis z nieaktualną rewizją przegrał CAS.
Główne ryzyko to współpraca z pozostałymi writerami profilu — stąd niezbędne
testy zapisu ustawień, wydawania respektu, awansu i równoległego przejęcia.

## Warunki dalszej integracji

Test `test_profile_write_preserves_reward_once_and_later_award` jest przygotowany,
ale jawnie pominięty do czasu zastosowania integracji. Nie jest PASS ani dowodem
zgodności starej warstwy. Po zatwierdzeniu należy włączyć go, uzupełnić odczyty
małych projekcji o przyrosty i uruchomić regresję pełnych guarded writers.

Dopiero potem zastąpić ciężkie `TerritoryProgressionReceiptStore.settle` i
`settle_strategic`, ich callery w requestach i workerach oraz projekcje utraty
terytorium. Zachować nagrody, komunikaty, przejęcia i finalizację konfliktów.
Sam nowy moduł nie zamyka bramki zero-heavy sprintu 147.

## Weryfikacja izolowana

```powershell
$env:PYTHONPATH='.;tests'
python -m unittest tests.test_player_progression
```

Migrację sprawdzać wyłącznie na kopii stagingowej bazy:

```sh
python -m tools.migrate_player_progression --db /path/to/staging.sqlite3 --owner main
python -m tools.migrate_player_progression --db /path/to/staging.sqlite3 --owner main --apply
```

W razie odrzucenia integracji nie omijać kontroli innym narzędziem ani skryptem.
Nowa ścieżka kreatorów pozostaje wyłączona; brak gotowości do wdrożenia/PASS.
