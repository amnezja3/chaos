# Wygaszanie kartoteki — przed dalszą realizacją sprintu 145

Historia `response_penalty_history` i `executed_count` pozostają trwałe.
Nowa mała tabela `response_record_decay` przechowuje liczbę wygaszonych stopni,
postęp i ostatnią próbkę obecności. Obciążenie to executed_count minus forgiven.
Istniejące konta zaczynają bez wygaszonych stopni i bez wstecznego naliczania czasu.
L1 nadal nie wykonuje kary; pozostałe poziomy zachowują własny próg wejściowy.

Każde 3600 sekund potwierdzonej obecności online obniża obciążenie o jeden.
Wykonana kara zwiększa licznik historyczny i obciążenie, zeruje postęp do spadku.
Uniknięcie, obserwacja i niewykonana kara nie zerują postępu.
Areszt wstrzymuje naliczanie, a kaucja nie zmniejsza obciążenia.
Sesja, heartbeat i czas pochodzą z serwera. Przerwy ponad 90 sekund, zmiany sesji,
duplikaty próbek i okresy offline nie otrzymują czasu. Brak wstecznego kredytu.
Obecność ma tę samą semantykę co zegar aresztu: aktywna sesja z heartbeatami;
nie jest dodatkowym pomiarem ruchów myszą ani liczby akcji gameplayowych.

Integracja używa istniejącego odpytywania delt i stanu aresztu, bez nowego pollera.
Brak odczytów lub zapisów pełnego profilu. Zmiana kary i reset postępu odbywają się
w jednej transakcji; wygaszanie również jest serializowane przez SQLite.
UI nie pokazuje stałego licznika. Każdy spadek generuje pojedynczą wiadomość
System Messaging wyświetlaną przez istniejący toast. Nadawca zależy od poziomu
po redukcji: 10+ Prokuratura cyberbezpieczeństwa, 5–9 Centrum cyberbezpieczeństwa,
1–4 Policja. Przy 0 Policja informuje o zakończeniu dozoru, bez usuwania historii.

## Wdrożenie i test serwerowy

Standardowa kopia SQLite przed wdrożeniem. Restart procesu web tworzy nową tabelę
i indeks zwolnień automatycznie, bez migracji profili i resetowania istniejących kar.

1. Odczytaj `/api/response/detention`: `criminal_record.executed_count`,
   `active_burden`, `remaining_seconds`, `paused` (gdy obciążenie dodatnie).
2. Po minucie online pozostały czas powinien spaść o około minutę.
3. Wyloguj się i wróć: postęp zachowany, czas offline pominięty.
4. W areszcie postęp stoi. Po zwolnieniu/kaucji wraca naliczanie.
5. Po pełnej godzinie: obciążenie -1, historia i executed_count bez zmiany,
   jeden komunikat. Nowa wykonana kara: obciążenie +1, czas znów 3600 s.
6. Sprawdź show na zwykłej mapie i w więzieniu: efektywnie 80% czerni,
   20% widoczności mapy; długość nadal wynika z SFX.

Nie zamykać testów runtime 145 na podstawie samego wdrożenia tej zmiany.
