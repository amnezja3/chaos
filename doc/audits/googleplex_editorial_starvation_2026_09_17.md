# 142.3 — odświeżanie pozostałych publikacji GooglePlex News

Hero potwierdzone przez użytkownika na produkcji. Pozostałe istniejące
publikacje Ollamy blokował warunek w `enqueue_blacknet_world_narrative_digest`:
Stage II działał tylko, gdy hero nie zwrócił `created` ani `slot_busy`.
Warunek jest obecny również w rewizji zamykającej 138.2 (`c8bbaee`);
nie ma podstaw do przypisania jego wprowadzenia do tego sprintu.

Scheduler teraz niezależnie sprawdza hero i jedno zadanie Stage II.
Sześć istniejących slotów: featured, blacknet, operations, packages, storage,
clans. Zadania używają istniejących polityk, expiry, priorytetów, claim,
walidacji, publishera i slot CAS. Zachowano okresy odświeżania 6/12/24 h
oraz blokadę kolejnej generacji dla slotu z niezakończonym zadaniem.
Przy interwale 900 s dochodzi najwyżej jedno zadanie redakcyjne co 15 minut;
pełne odświeżenie sześciu kart jest stopniowe, nie natychmiastowe.

Log workera zawiera teraz `editorial_status`, `editorial_slot` i
`editorial_task`. Odczyt nie wymaga profili użytkowników ani wywołania modelu
w żądaniu HTTP.

Exchange, mapa i WORLD są w obecnym rejestrze statycznymi odnośnikami;
integrity/protocol to stałe informacje systemowe. Nie miały kontraktów
odświeżania Stage II i nie są objęte przywracaniem istniejących publikacji.

Test schedulerowy sprawdza wszystkie sześć slotów przy naprzemiennych
`created`/`slot_busy` hero, limit jednego dodatkowego zadania na przebieg,
brak duplikatów i brak pełnego odczytu profilu. Test serializacji hero
sprawdza osobno zadania świata i niezależne zadania redakcyjne.
Walidacja: 27 testów narrative_publications PASS; po aktualizacji oczekiwania
liczby niezależnych zadań wszystkie 23 testy llm_event_producers PASS (17,229 s).
Testy uruchomiono przez `tools/run_isolated_tests.py` na tymczasowych bazach.

Po deployu przeładować `ecosystem.web.config.js` oraz
`ecosystem.territory-worker.config.js` z `--update-env`.
Gameplay: sprawdzić kolejno nowe teksty kart i zachowanie ich właściwych
akcji. Hero pozostaje PASS; odbiór pozostałych publikacji wymaga deployu.
