# 154.8 — wdrożenie dostawców narracji

Stan: pakiet przedwdrożeniowy, testy lokalne PASS. Nie wykonano wdrożenia,
restartu produkcji ani wywołania prawdziwego Mistrala. Start produkcyjny
pozostaje na Ollamie; włączenie Mistrala jest osobną zmianą w panelu.

## Co trafia na serwer

- Wspólny adapter narracji, Mistral REST i dotychczasowa Ollama.
- Addytywne pola provider/requested_model/provider_request_id w attempts/candidates.
- Tabele `narrative_provider_config`, `narrative_provider_config_audit`,
  `narrative_provider_state`, `narrative_provider_budget`, `narrative_provider_calls`.
- Panel `/admin?tab=narrative` (wejście przez zalogowaną na admina nawigację).
- Bez nowych zależności SDK. Używane istniejące `requests`, standardowy Python
  i oficjalne [Chat Completions](https://docs.mistral.ai/api/endpoint/chat)
  oraz [Models](https://docs.mistral.ai/api/endpoint/models).

Endpoint jest stały: `https://api.mistral.ai/v1`. Panel nie przyjmuje URL.
Przed aktywacją sprawdzić, czy konto/klucz CHAOS ma działać na tym endpointcie.
Nie zmieniamy drugiej aplikacji na serwerze ani jej zależności.

## Przygotowanie

Komenda, po dostarczeniu i wypchnięciu zatwierdzonego commita:

```bash
cd ~/app/chaos
git status --short
git pull --ff-only
git rev-parse --short HEAD
```

Spodziewane: czysty checkout, pobrany zatwierdzony commit. Nie kontynuować
przy nieznanych zmianach lokalnych lub innym commicie niż zatwierdzony.

Backup SQLite przez API SQLite (obejmuje dane z WAL):

```bash
.venv/bin/python -c 'import sqlite3,datetime; p="data/game-before-154-8-"+datetime.datetime.now().strftime("%Y%m%d-%H%M%S")+".sqlite3"; src=sqlite3.connect("data/game.sqlite3"); dst=sqlite3.connect(p); src.backup(dst); dst.close(); src.close(); print(p)'
```

Spodziewane: ścieżka nowego pliku backupu. Zachować konfigurację PM2/usług
według obecnej procedury operatora; nie dołączać dumpów środowiska do zgłoszeń.

## Testy i migracja

```bash
.venv/bin/python tools/run_isolated_tests.py test_mistral_runtime test_narrative_provider_admin test_narrative_provider test_ollama_client test_ollama_worker test_ollama_policy test_ollama_ecosystem_shutdown_contract test_narrative_cutover test_llm_publishers test_narrative_support test_narrative_publications test_admin_panel_lazy
.venv/bin/python scripts/narrative_provider_control.py migrate --db data/game.sqlite3
.venv/bin/python scripts/narrative_provider_control.py status --db data/game.sqlite3
```

Spodziewane: testy `OK`; raport `ok: true`, domyślnie `primary: ollama`,
`revision: 1` przy pierwszej instalacji. Ponowna migracja zachowuje ustawienia
i historię. Lista `active_policies` jest aktualną macierzą odbioru, nie listą
deklarowanych z góry modeli Mistrala. Raport nie zwraca sekretu ani promptów.

## Restart w trybie Ollama-only

```bash
pm2 restart chaos --update-env
pm2 startOrReload ecosystem.ollama-worker.config.js --update-env
.venv/bin/python scripts/ollama_narrative_worker.py verify
.venv/bin/python scripts/ollama_narrative_worker.py status
```

Spodziewane: `verify.ok: true`, działający `chaos-ollama-worker`, `primary: ollama`.
Publisher nie zmienia konfiguracji. Nie restartujemy usługi Ollamy ani drugiej
aplikacji. Potwierdzić bieżące CPUQuota Ollamy — ta łatka nie znosi ograniczenia.

## Sekret i aktywacja Mistrala

`CHAOS_MISTRAL_API_KEY` musi być sekretem środowiska **web oraz workera**.
Użyć istniejącego mechanizmu sekretów operatora. Przy jednorazowym wprowadzeniu
w interaktywnej powłoce można użyć ukrytego odczytu, bez wartości w historii:

```bash
read -r -s -p "Mistral API key: " CHAOS_MISTRAL_API_KEY
printf '\n'
export CHAOS_MISTRAL_API_KEY
pm2 restart chaos --update-env
pm2 startOrReload ecosystem.ollama-worker.config.js --update-env
.venv/bin/python scripts/narrative_provider_control.py status --db data/game.sqlite3
```

Spodziewane: `secret_configured: true`. Zapewnić trwałe dostarczanie sekretu po
reboocie według mechanizmu hosta; interaktywny `export` sam tego nie gwarantuje.
Nie zapisywać klucza w repozytorium, panelu, JSON konfiguracji ani raporcie.

W panelu **Modele narracji**:

1. Pobierz modele — lista tylko modeli z `completion_chat`.
2. Wybierz dostępny model; zapisz najpierw z primary Ollama, aby wykonać test.
3. Sprawdź/odblokuj Mistrala i uruchom test generacji. Test jest ograniczony do
   8 sekund i nie publikuje treści. Jego timeout nie rozstrzyga jeszcze o jakości
   normalnej generacji (domyślnie 25 sekund).
4. Włącz Mistrala i zapisz. Nowa rewizja obowiązuje przed następnym claimem;
   zadanie w toku zachowuje poprzednią konfigurację.
5. Potwierdź normalne zdarzenie → task → Mistral → accepted candidate → publikacja.
   Wynik naprawiony przez deterministic support nie zalicza jakości Mistrala.

## Granice i diagnostyka

Domyślnie Mistral ma 25 s, lokalna próba maksymalnie 242 s, a cała generacja
270 s (konfiguracja do 280 s). Każde żądanie działa w odrębnym procesie Python
`spawn`; deadline/cancel kończy proces i zamyka połączenie. Nie zostają porzucone
wątki HTTP. PM2 ma `kill_timeout: 360000` na zakończenie workera i zapis metadanych.
Przerwanie połączenia nie gwarantuje anulowania rozliczenia po stronie API.

Jedna generacja na dostawcę w CHAOS, także między workerami i diagnostyką.
Blokady są trwałe, wygasają po awarii procesu. Zajęta Ollama powoduje dotychczasowe
retry/backpressure kolejki, bez dodatkowego równoległego wywołania lokalnego.
Nie jest to limiter wspólny z drugą aplikacją korzystającą z Ollamy.

403/401/402 i rozpoznany błąd quota wstrzymują API do zmiany konfiguracji lub
udanego ręcznego probe (wpis ma ochronny horyzont jednego roku). Pozostałe błędy
transportu otwierają circuit na co najmniej 60 s; Retry-After do 24 h wydłuża
ten okres. Po jego końcu jedna generacja może sprawdzić powrót API, pozostałe
respektują wspólną blokadę. Primary nie jest automatycznie przepisywany.

Dzienny budżet jest lokalną, konserwatywną **rezerwacją**: bajty wejścia UTF-8,
narzut 128 oraz limit wyjścia. Nie jest odczytem salda Mistrala ani dokładnym
licznikiem billingowym. Niepewne/nieudane wywołania zachowują rezerwację. Dzień
zmienia się o północy UTC; `0` wyłącza limit. Inna aplikacja ma osobne zużycie.

```bash
.venv/bin/python scripts/narrative_provider_control.py status --db data/game.sqlite3
pm2 logs chaos-ollama-worker --lines 50 --nostream
```

Raport: ostatnie 30 subprób, task/attempt ID, rewizja, provider/model,
request hash, prompt/schema, request ID, tokeny gdy znane, czas i kod błędu.
p50/p95 odnoszą się tylko do tej próbki, nie są raportem całego ruchu produkcji.
Wpis `started` po twardym zabiciu procesu może pozostać w historii; sam nie
oznacza działającego wywołania. O aktualnej pracy decydują lease i stan kolejki.

## Odbiór serwerowy przed PASS

- Każda aktywna polityka i obecnie obsługiwany język; lista w raporcie status.
- Co najmniej 30 min normalnego mieszanego ruchu, idle/resume, backlog,
  odsetek accepted/support/retry, opóźnienia oraz CPU/RAM współdzielonej Ollamy.
- Kontrolowane przejście na lokalny fallback i powrót. Bez celowego wyczerpywania
  płatnego limitu; 403/409/429/billing są objęte lokalnymi testami wstrzykniętych błędów.
- Potwierdzić utrzymanie workerów, brak duplikacji publikacji i zgodność faktów.
- Nie przenosić tego etapu do 155: pełny PASS 154.8 wymaga tego odbioru.

## Rollback bez utraty historii

W panelu wybierz Ollamę i zapisz albo:

```bash
.venv/bin/python scripts/narrative_provider_control.py use-ollama --db data/game.sqlite3
.venv/bin/python scripts/narrative_provider_control.py status --db data/game.sqlite3
```

Spodziewane: primary Ollama, rewizja wzrasta. Zadanie w toku kończy swoją
zamrożoną próbę; kolejne korzysta z Ollamy. W razie wycofania kodu najpierw
przełączyć primary, zatrzymać/odczekać worker, dopiero przywrócić poprzedni commit.
Nie usuwać nowych tabel, kolumn, kolejki ani publikacji. Stary kod ignoruje
addytywne metadane. Backup służy do awarii migracji, nie do cofania bieżącej gry.
