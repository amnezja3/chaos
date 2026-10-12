# Sprint 154.8 — dostawcy narracji: Mistral API i fallback Ollama

Status: **LOCAL PASS — PAKIET PRZEDWDROŻENIOWY**, 11 X 2026.
Kolejność: **154 PASS → 154.8 (odbiór serwerowy) → 155**.

Etapy 154.8.1–4 zaimplementowane lokalnie: kontrakt, migracja metadanych,
proces z deadline, Mistral REST, panel PL/EN, circuit i automatyczny fallback.
154.8.5: regresja 160 testów PASS + cztery celowane PASS (163 unikalne przypadki),
Playwright PL/EN/mobile PASS, gotowe komendy migracji/status/rollback.
Brak sekretu Mistrala lokalnie: rzeczywisty API/live traffic pozostaje do odbioru
serwerowego. Domyślnie primary Ollama; nie wykonano wdrożenia.
[Raport](../audits/sprint_154_8_predeployment.md),
[runbook wdrożenia](../runbooks/narrative_providers_154_8.md).
To sprint infrastruktury generowania, nie ponowne otwarcie odbioru 154.
149–152 pozostają zamrożone. Dokument opisuje prace i warunki odbioru;
Integracja jest zaimplementowana; test rzeczywistego Mistrala nie został wykonany.

## Cel i granica zmiany

Odłączyć kontrakt generowania narracji od konkretnego dostawcy. Administrator
wybiera Ollamę albo Mistral API i model dostępny na koncie Mistrala. Przy awarii,
braku uprawnień, wyczerpaniu limitu lub budżetu zewnętrznego API zadanie przechodzi
automatycznie na istniejący lokalny executor Ollamy. Worker dalej obsługuje kolejkę.

Zachować obecny przebieg: zdarzenie → kanoniczny task/outbox → semantic input
i prompt registry → generacja → walidacja i narrative support → candidate/inbox
→ publisher → widoczna publikacja. Podmianie podlega dostawca generacji oraz
niezbędna obsługa konfiguracji, błędów i metryk. Nie tworzymy osobnej kolejki,
publikatora ani alternatywnej logiki świata dla Mistrala.

Te same fakty, identyfikatory, prompt, schemat wyniku, język zadania, TTL i reguły
publikacji obowiązują po fallbacku. Oczekujemy zgodności faktów i kontraktu,
nie identycznych zdań z dwóch modeli. Model nie wykonuje akcji gameplayowych.
Lokalizacja treści, historia i narracje z planu 155 pozostają w 155.

## Stan wejściowy potwierdzony w repozytorium

| Obszar | Obecne miejsce i ograniczenie |
| --- | --- |
| Klient | `ghostnetwork/ollama_client.py`: `ChaosOllamaClient`, `generate(package, policy)`, `verify()`, ograniczona odpowiedź HTTP; przypięty loopback, model, digest i wersja runtime |
| Polityka | `ghostnetwork/ollama_policy.py`, `ghostnetwork/llm/policies/chaos_local_narrator_v1.py`: rozdzielić reguły narracji od poświadczenia lokalnego modelu |
| Worker | `ghostnetwork/ollama_worker.py`: klient wstrzykiwany do konstruktora, preflight przed claim, heartbeat, retry, walidacja i deterministyczny support |
| Trwałość | `ghostnetwork/repository.py`: task, attempt, candidate, lease i deduplikacja; początek próby zapisuje dziś model z polityki Ollamy |
| Wejście/wyjście | `ghostnetwork/llm/semantic_input.py`, `registry.py`, `schemas/`, `output_safety.py`, `narrative_support.py` |
| Uruchamianie | `scripts/ollama_narrative_worker.py`, `ecosystem.ollama-worker.config.js`; publisher uruchamiany oddzielnie |
| Administrator | `admin_panel.py`, `templates/admin_dashboard.html`, `static/js/admin_panel.js`, `static/css/admin_panel.css`; zachować lazy loading i ograniczone odczyty |
| Ograniczenia hosta | [Hardbugfix CPU Ollamy](../hardbugfix/ollama_cpu_quota_2026-10-05.md): operator zastosował runtime `CPUQuota=300%`; trwałość ustawienia wymaga osobnego potwierdzenia |

Obecny klient lokalny ma read timeout 240 s, worker lease 180 s odnawiany co
30 s, a PM2 kill timeout 300 s. Dołożenie wywołania zewnętrznego wymaga jawnego
budżetu całego zadania i shutdownu; timeout odczytu HTTP nie jest sam w sobie
limitem całkowitego czasu przy powolnym przesyłaniu odpowiedzi.

## 154.8.1 — kontrakt dostawcy i zgodność Ollamy

### Przykład z drugiej aplikacji na tym samym serwerze

Autor dostarczył 11 X 2026 kod `MistralChatManager` jako referencję istniejącego
użycia. W kodzie: SDK `mistralai`, `Mistral(..., server="eu")`, domyślny model
`mistral-saba-2502`, `chat.complete`, role system/user, `stream=False` oraz lokalny
`http://127.0.0.1:11434` z `llama3.1:8b`. Są to wartości z przykładu, nie wynik
naszej weryfikacji wersji SDK, dostępności modelu czy uprawnień konta na serwerze.

Przy implementacji adaptera najpierw sprawdzić wersję `mistralai` używaną przez
tę aplikację, jej endpoint regionalny i modele dostępne dla klucza CHAOS.
Decyzja implementacyjna: bezpośredni REST przez istniejące `requests`, bez SDK
i jego retry. Deadline egzekwuje nadrzędny proces. Nie dodano zależności ani
nie zmieniono konfiguracji drugiej aplikacji. Lokalnie nie ma dostępu do jej
środowiska; zgodność konta/regionu sprawdzić przy odbiorze serwerowym.
Panel powinien pokazywać zatwierdzony region/endpoint, a listę modeli pobierać
z tego samego endpointu, którego używa generacja. Nie wymuszać modelu Saba
ani regionu na podstawie samej wartości domyślnej w przykładzie.

Różnice wymagające świadomej adaptacji:

- `_post(..., mistral=False)` wybiera lokalną Ollamę. Wyjątek w gałęzi Mistrala
  zwraca `""` przy `fail_silently=True` albo jest rzucany dalej. `_is_retryable`
  istnieje, ale nie jest wywoływane przez `_post`; przykład nie realizuje
  automatycznego Mistral → Ollama. Obsługa 403 również nie jest jawna w helperze.
- `total_timeout` nie jest przekazywany do wywołania Mistrala. Parametry
  pozycyjnego `BackoffStrategy` trzeba zweryfikować dla przypiętej wersji SDK;
  nie opierać budżetu czasu na komentarzach w przykładzie. Retry SDK, retry
  Ollamy po read timeout i retry zadania nie mogą mnożyć się poza deadline.
- Do narracji CHAOS nie przenosić `fail_silently`, pustych sukcesów ani
  `str(res)` jako zastępczej treści. Normalizować wyłącznie udokumentowane
  elementy tekstowe odpowiedzi, w tym obiekty chunków SDK; brak treści to
  typowany błąd. Zachować usage, finish reason i identyfikację dostawcy.
- Zostają istniejące parsery/schematy/fakty i output safety CHAOS. Pomocniczy
  parser liczący nawiasy w przykładzie nie rozróżnia nawiasów wewnątrz JSON
  strings. Nie przejmować też temperatur 0.7/0.9 ani funkcji tłumaczenia,
  klasyfikacji spamu i rozmów jako nowego zakresu narratora.
- Druga aplikacja może równolegle generować na tej samej Ollamie. Jedna
  lokalna generacja w CHAOS nie ogranicza globalnej liczby wywołań hosta.
  Odbiór obciążenia obejmuje współdzielenie usługi: CPU/RAM, oczekiwanie,
  timeouty i kolejkę podczas aktywności drugiej aplikacji. Nie zmieniać jej
  ustawień; ewentualny wspólny limiter/gateway wymaga osobnej decyzji.
- Nie zakładać wspólnego klucza API. Jeśli operator wybierze wspólny workspace
  Mistrala, uwzględnić współdzielone limity konta: lokalny licznik CHAOS nie zna
  zużycia drugiej aplikacji i nie zastępuje odpowiedzi quota/rate-limit dostawcy.

Testy adaptera uzupełnić o string/listę chunków SDK, brak choices/content,
błąd 403/409 przy domyślnym wyborze Mistrala, rzeczywisty deadline przy retry
oraz zajętą Ollamę obsługującą inne żądanie. Sam fakt używania SDK przez drugą
aplikację nie zalicza live testów narracji CHAOS.

### Zakres wspólnego kontraktu

- Wspólny interfejs `verify`, `list_models` tam, gdzie wspierane, oraz
  `generate(package, policy, deadline)`; adaptery `ollama` i `mistral`.
  Rozszerzenie o następnego dostawcę nie wymaga zmiany workerów/publisherów.
- Wspólny wynik: treść, provider, żądany i zwrócony model, powód zakończenia,
  usage jeśli dostępne, czas, hash odpowiedzi oraz identyfikator wywołania API.
  Parametry lokalne, np. digest/runtime version, pozostają metadanymi Ollamy;
  nie wpisujemy fałszywego digestu lokalnego modelu dla odpowiedzi Mistrala.
- Wspólny błąd: provider, kategoria, kod HTTP, retryability, `retry_after`,
  zredagowany opis. Brak kluczy API i pełnych promptów w zwykłych logach.
- Odseparować reguły faktów/schematu od model-specific constraints. Zachować
  istniejące schematy wyników, limity treści i walidację. Zmiany metadanych
  prób/candidates są addytywne i czytelne dla starej historii.
- Domyślna konfiguracja po migracji: `primary=ollama`. Bez klucza Mistrala
  lokalna ścieżka zachowuje dotychczasowe działanie. Istniejące nazwy procesów,
  zmienne `CHAOS_OLLAMA_*` i komendy pozostają kompatybilne.

Odbiór etapu: regresje obecnego klienta/workera/publisherów PASS bez API Mistrala.

## 154.8.2 — adapter Mistral

Użyć `POST /v1/chat/completions`, wiadomości system/user, `stream=false`, jednej
odpowiedzi oraz kontrolowanego limitu wyjścia. Obsługę JSON dobrać do możliwości
wybranego modelu; odpowiedź zawsze przechodzi walidator CHAOS, także przy JSON
schema po stronie API. [Kontrakt Chat Completions](https://docs.mistral.ai/api/endpoint/chat).

Listę modeli odczytywać z API konta; udostępniać tylko modele obsługujące wymagany
typ generacji. Nie wpisywać jednego modelu na stałe w kodzie. Preferować wersję
przypiętą; przy aliasie zapisywać również model zwrócony w odpowiedzi.
[API Models](https://docs.mistral.ai/api/endpoint/models).

- Przekazywać istniejący pakiet narracji, bez pobierania pełnych profili graczy
  i bez rozszerzania danych wysyłanych do dostawcy o sesje, sekrety lub prywatne wiadomości.
- Autoryzacja wyłącznie na backendzie; endpoint HTTPS z zatwierdzonej listy,
  bez dowolnego URL z panelu i przekazywania nagłówka autoryzacji przez redirect.
- Ograniczyć rozmiar odpowiedzi, połączenie, całkowity czas wywołania, liczbę
  równoległych żądań i użycie tokenów. Brak niejawnych retry w SDK/HTTP.
- Osobno rozpoznawać limit konta/billing, rate limit oraz `max_tokens` odpowiedzi.
  Ucięta odpowiedź nie jest dowodem wyczerpania środków; nie publikować niepełnego JSON.
- Preflight sprawdza osiągalność, autoryzację, dostępność wybranego modelu i
  zgodność kontraktu. Test generacji jest jawną, ograniczoną operacją diagnostyczną,
  bez publikacji i bez tworzenia zdarzeń świata.

## 154.8.3 — konfiguracja w panelu administratora

Sekcja „Modele narracji” / „Narrative models”, PL/EN, dostępna tylko dla
administratora, z istniejącą ochroną sesji i żądań modyfikujących.

| Kontrolka | Zachowanie |
| --- | --- |
| Dostawca główny | Ollama / Mistral API; w trybie Mistrala fallback Ollama obowiązkowy |
| Model Mistrala | Odświeżana lista dostępnych modeli i walidacja wyboru |
| Klucz API | Tylko status skonfigurowania sekretu serwera; bez pola edycji klucza |
| Limity | Timeouty i całkowity deadline, max output tokens, współbieżność, opcjonalny lokalny budżet API |
| Diagnostyka | Test połączenia/modelu oraz ograniczony test generacji, bez publikowania wyniku |
| Stan | Wybrany provider, faktycznie używany provider, zdrowie obu, przyczyna fallbacku, circuit breaker i termin próby powrotu |
| Operacje | Zapisz konfigurację, test ponownego połączenia, przełącz na lokalną Ollamę |

Konfiguracja ma rewizję i zapis atomowy z kontrolą konfliktu. Zgodnie z decyzją
autora klucz API dostarczamy wyłącznie jako sekret serwera
(`CHAOS_MISTRAL_API_KEY`), poza bazą i repozytorium. Panel i jego endpointy
nie przyjmują ani nie zwracają klucza. Pokazują jedynie stan skonfigurowania.

Workery odczytują nową rewizję przed kolejnym claimem, bez restartu. Rozpoczęta
próba ma zamrożoną konfigurację. Zmiana panelu nie przerywa trwającej generacji
ani nie powoduje ponownej publikacji. Rotacja sekretu środowiskowego wymaga
przeładowania środowiska procesów zgodnie z runbookiem; zmiana modelu w panelu
tego nie wymaga. Już wysłanego żądania API nie można cofnąć.
Zmiana ustawień audytowana bez sekretu. Diagnostyka i lista modeli nie blokują UI.

## 154.8.4 — fallback i ciągłość workerów

Fallback jest próbą drugiego dostawcy dla **tego samego taska**, nie nowym
zdarzeniem. Nie reenqueue'ować osobnej kopii taska między Mistralem a Ollamą.
Zapisać obie próby dostawców, ich wynik, konfigurację i przyczynę przełączenia.
Zachować dotychczasowy globalny limit prób zadania; subpróby dostawców mają
osobny ograniczony budżet. Jedno przejście Mistral → Ollama na próbę, bez pętli.

| Sytuacja | Wymagane zachowanie |
| --- | --- |
| Mistral zwraca poprawny wynik | Walidacja i publikacja istniejącym pipeline; bez wywołania Ollamy |
| Sieć/DNS/TLS, timeout, HTTP 408/5xx | Zakończyć wywołanie zewnętrzne i przejść do Ollamy w budżecie zadania |
| HTTP 401/403 | Fallback; błąd klucza/uprawnień widoczny administratorowi, circuit otwarty do zmiany konfiguracji lub kontrolowanego testu |
| HTTP 409 od Mistrala | Fallback zgodnie z wymaganiem; zachować kod i ograniczony opis, nie zakładać, że oznacza brak środków |
| HTTP 429 | Fallback teraz; `Retry-After` wyznacza najwcześniejszy powrót do API, nie blokujący sleep workera |
| Wyczerpanie kredytów, kwoty tokenów lub lokalnego budżetu | Fallback; rozpoznać sygnał dostawcy, nie jeden sztywny status HTTP; stan do resetu limitu/uzupełnienia i weryfikacji |
| Model niedostępny/404 | Fallback i sygnał konfiguracji; bez przełączenia na arbitralny inny płatny model |
| Wadliwy request/400/422 | Zarejestrować błąd adaptera/konfiguracji, bez ponawiania tego samego requestu; fallback tylko jeśli kanoniczny pakiet nadal jest prawidłowy |
| Pusta/ucięta odpowiedź, niepoprawny JSON/schemat | Nie traktować jako sukcesu; ograniczona lokalna próba z tym samym pakietem, potem istniejący support/retry |
| Odrzucone fakty/bezpieczeństwo treści | Zachować domenowe odrzucenie/support; nie używać zmiany modelu do obchodzenia walidacji |
| Błąd bazy, utrata lease, anulowanie lub wygaśnięcie źródła | Nie uruchamiać drugiego modelu; obecna ścieżka spójności i wygaszania zadania |
| Obaj dostawcy niedostępni | Worker nie kończy procesu; dotychczasowy ograniczony retry/backoff/support/dead-letter. Panel pokazuje degradację, nie fałszywy sukces |

403/409 są tutaj regułą routingu CHAOS, nie deklaracją, że dokumentacja Mistrala
wiąże je z brakiem tokenów. Kategoryzacja transportu nie może przechwytywać np.
konfliktu rewizji zapisu ustawień jako błędu dostawcy.

Circuit breaker jest wspólny dla workerów i ogranicza ponawianie uszkodzonego
API. Po przerwie jeden kontrolowany probe w stanie half-open; sukces przywraca
Mistrala dla następnych zadań. Zmiana klucza/modelu unieważnia właściwy stan
awarii. Przelotna awaria nie przepisuje administratorowi wybranego providera.

Preflight musi być świadomy dostawców: niedostępny Mistral i zdrowa Ollama
oznaczają działanie zdegradowane, nie `preflight_failed` zatrzymujący pobieranie
zadań. Zdrowy Mistral może pracować przy chwilowo niedostępnej Ollamie, z alarmem
braku fallbacku. Niedostępność obu oznacza okresowe sprawdzanie zdrowia, bez
zabijania procesu i bez masowego zużywania prób kolejki samymi testami zdrowia.

Heartbeat obejmuje obie generacje oraz oczekiwanie na limit równoległości;
po utracie lease nie wolno rozpocząć fallbacku ani zatwierdzić wyniku.
Przed fallbackiem i zapisem ponownie sprawdzić TTL/aktualność zdarzenia.
Timeout Mistrala rezerwuje czas na lokalne wykonanie. Ustalić i przetestować
całkowity deadline oraz zgodny z nim PM2 shutdown budget; nie wydłużać go bez końca.
Opóźniona odpowiedź API po fallbacku nie ma prawa zapisać drugiego candidate.

Ollama zachowuje obecne limity modelu/CPU. Fallback ma ograniczoną współbieżność
(startowo jedna lokalna generacja), aby awaria API nie spowodowała skoku CPU.
Pozostałe zadania oczekują z backpressure, nie blokują procesu ani heartbeatów.

## 154.8.5 — odbiór rzeczywistej ścieżki i wdrożenie

Najpierw testy automatyczne na izolowanej bazie i atrapach dostawców, następnie
pełny przebieg przez prawdziwe API Mistrala. Sam mock ani endpoint diagnostyczny
nie wystarcza do PASS. Wymagane: skonfigurowany klucz, dostępny model, quota,
łączność z API i sprawna Ollama. Przy ich braku etap live ma status BLOCKED,
bez deklaracji zaliczenia; nie zapisujemy sekretów w raporcie.

Macierz obowiązkowa:

1. Regresja Ollama-only: obecne event producers, kolejka, validation/support,
   publikatory, świeżość, retirement, retry i restart. Żadnych zmian efektów gry.
2. Wszystkie aktywne media/polityki z registry, w tym BlackNet, Googleplex,
   Cyberner/AGI, GhostNetwork i Ghost Signal: naturalne zdarzenie → task →
   Mistral → zaakceptowany candidate → normalny publisher → widoczny odbiorca.
   Zinwentaryzować aktywne polityki na początku; nie pomijać rzadziej uruchamianych.
3. Co najmniej jeden rzeczywisty pełny sukces Mistrala dla każdej aktywnej
   polityki oraz dla każdego obsługiwanego dziś języka; nie dodawać tutaj zakresu
   tłumaczeń 155. Osobno minimum 30 minut mieszanego ruchu z okresami bezczynności
   i wznowieniem, bez ręcznego drainowania kolejki czy restartowania workerów.
4. Wymusić każdą kategorię błędu z tabeli, w tym 403, 409, 429, wyczerpanie
   budżetu i timeout. Błędy billingowe symulować — nie zużywać środków celowo.
   Potwierdzić automatyczną lokalną generację i normalną publikację tego taska.
5. Niedostępność obu dostawców, restart podczas fallbacku, SIGTERM, utrata
   lease, spóźniony wynik API, duplikat delivery, nieaktualne źródło i zmiana
   konfiguracji w trakcie generacji. Najwyżej jedna publikacja logiczna na task;
   nie obiecujemy dokładnie jednego płatnego wywołania po awarii sieci.
6. Circuit open → half-open → recovery oraz powrót ręczny do Ollamy bez
   restartu workerów, utraty kolejki i ponownej emisji starych publikacji.
7. Playwright MCP: uprawnienia administratora, PL/EN, zapis/konflikt rewizji,
   brak sekretu w API panelu, lista modeli, diagnostyka, degradacja i zmiana providera.
8. Pomiar throughput, wieku najstarszego zadania, backlogu, p50/p95 generacji,
   odsetka poprawnych wyników/support/retry, czasu przełączenia, tokenów i CPU/RAM.
   Raport pokazuje baseline Ollamy i Mistrala; brak stale rosnącego backlogu przy
   ustalonym normalnym obciążeniu. Większy koszt/opóźnienie wymaga jawnej oceny.

Dowód każdego live przebiegu: zanonimizowane task/attempt/candidate/publication
ID, provider/model, revision, prompt/schema/request hash, locale, czasy, usage,
wynik walidacji i przyczyna fallbacku. Rozróżnić wynik modelu od deterministycznego
supportu; support nie zalicza testu poprawnej generacji Mistrala.

Wdrożenie etapowe: backup konfiguracji/metadanych → migracja addytywna →
regresja Ollama-only → konfiguracja sekretu serwera i test Mistrala → kontrolowana partia
normalnych zadań → pełny wybór Mistrala → test awarii i powrotu → PASS autora.
Rollback: przełączyć primary na Ollamę, odczekać ograniczone próby w toku,
zachować kolejkę, attempts i opublikowane dane. Stary kod musi tolerować nowe
metadane; nie usuwać nowej historii przy rollbacku.

## Definition of Done i zależność 155

- Administrator konfiguruje Mistrala i wybiera model, bez edycji kodu.
- Dostawca jest wymienny; działają adaptery Ollama/Mistral i kompatybilność historii.
- Pełny normalny pipeline przeszedł live z Mistralem, bez zmian publisherów
  i bez osłabienia walidacji faktów, języka, świeżości czy deduplikacji.
- Awaria Mistrala przełącza zadanie na Ollamę; worker przeżywa awarie obu,
  a zaległe zadania podlegają istniejącej polityce retry/TTL/dead-letter.
- Panel i metryki odróżniają primary od fallbacku; limity zasobów są utrzymane.
- Testy, audyt bezpieczeństwa sekretu, raport live, runbook i rollback PASS.
- README, journal i zakres 155 wskazują zakończenie 154.8. Dopiero wtedy start 155.

Źródła integracji zweryfikowane 11 X 2026: oficjalne
[pierwsze żądanie API](https://docs.mistral.ai/getting-started/quickstarts/developer/first-api-request),
[Chat Completions](https://docs.mistral.ai/api/endpoint/chat),
[Models](https://docs.mistral.ai/api/endpoint/models).
Konkretny model i limity konta sprawdzić podczas konfiguracji, nie zakładać ich z góry.
