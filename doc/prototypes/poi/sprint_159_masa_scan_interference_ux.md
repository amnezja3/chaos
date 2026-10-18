# CHAOS — Sprint 159
## MASA / zakłócenia rozpoznania — komunikacja stanu skanera

**Identyfikator:** `159.masa.scan.interference.ux`  
**Data:** 18.10.2026  
**Status:** SPECYFIKACJA DO IMPLEMENTACJI — brak potwierdzonego PASS / brak autoryzacji automatycznego wdrożenia  
**Zależność:** Sprint 158 — POI Infrastructure v1 (zaimplementowany lokalnie; wg raportu zespołu: 41 testów Python PASS, 24 testy przeglądarkowe PASS; nowa warstwa domyślnie OFF).  
**Środowisko produkcyjne wg ostatniego potwierdzenia:** 4 workery Gunicorn, timeout 120 s.  
**Obszar:** mapa, skanowanie POI, komunikaty użytkownika, lokalizacje PL/EN, GhostLab, UX statusów infrastruktury.  
**Decyzja:** *realną niedostępność rozpoznania opowiadamy jako zakłócenia MASA; nie tworzymy nowej losowej mechaniki ani nowych przyczyn blokowania skanu*.

---

## 1. Cel

Kiedy CHAOS nie może uzyskać danych mapowych, gracz ma zrozumieć, **co aktualnie dzieje się ze skanerem i kiedy może sensownie spróbować ponownie**, bez technicznych komunikatów o Overpass API, statusach HTTP, bazie czy workerach. Źródłem fabularnym zakłóceń jest **MASA**. Jednocześnie kliknięcia graczy podczas potwierdzonej blokady nie mogą inicjować kolejnych prób pobrania danych, a system ma uczciwie informować o pracy na ostatnim dostępnym zapisie terenu.

**Efekt docelowy:** awaria staje się czytelnym, klimatycznym stanem świata CHAOS, a nie „zepsutym przyciskiem skanowania”.

**Istotne rozróżnienie:** Sprint 158 buduje infrastrukturę (cache, single-flight, limity, retry, circuit breaker). Sprint 159 jest warstwą **kontraktu stanu i jego prezentacji** oraz zabezpieczeniem klienta przed wielokrotnymi próbami; nie duplikuje mechanizmów infrastruktury.

---

## 2. Założenia i granice

1. **MASA jest interpretacją fabularną stanu infrastruktury**, a nie nowym systemem ataków MASA, terytoriów, nagród, uszkodzeń sprzętu czy rozgrywki klanowej.
2. Używamy **rzeczywistego sygnału backendu**, nie heurystyk frontendu, tekstu wyjątku ani samego faktu, że żądanie trwa długo.
3. Przy braku danych ze źródła, lecz dostępności **kompletnego, dopuszczonego do użycia cache**, skan działa dalej; komunikujemy jedynie jego tryb awaryjny.
4. Blokada zewnętrznego źródła jest **wspólna dla 4 workerów i wszystkich graczy** w zakresie polityki dostawcy z 158; blokada w samym JS służy wyłącznie UX.
5. **Zero nowych zapytań Overpass** od kliknięć przy otwartym circuit breakerze; po końcu cooldownu jedynie skoordynowany probe, zgodny z 158, nigdy po jednym probe na gracza.
6. Brak kosztów i kar za skan, który nie został wykonany z powodu infrastruktury; weryfikujemy punkt naliczenia w istniejącej implementacji, nie zgadujemy, gdzie on jest.
7. Nie zmieniamy zasad GhostLab (ulepszenia mają sens, gdy źródło jest dostępne, ale nie obchodzą breakerów ani limitów globalnych), zasięgów, markerów, NPC, kamer, losowości ani prywatnych celów gracza.
8. Nie włączamy zmian na produkcji przed osobną bramką 158: pakiet wdrożony z flagą OFF, zebrany baseline, testy i kontrolowane włączenie. Same lokalne PASS-y **nie oznaczają** zakończenia 158 na produkcji.

---

## 3. Doświadczenie gracza — stany, nie tylko teksty

| Stan UI | Warunek prawdy po stronie backendu | Co widzi gracz | Co robi przycisk SCAN |
|---|---|---|---|
| **READY** | Dostępna świeża, poprawna odpowiedź OSM / API działa | Zwykły ekran skanera, bez MASA | Normalne działanie |
| **DEGRADED** | Skan wykonany na kompletnym stale cache zgodnie z polityką 158 | Dyskretny alert: „MASA zakłóca kanały. Odczytano ostatni zapis terenu.” | Skan pozostaje poprawny, bez blokady |
| **BLOCKED** | Brak dopuszczalnych danych; polityka źródła zabrania nowych prób | Wyraźny komunikat MASA i informacja, że kolejna próba jest możliwa po ustąpieniu blokady; orientacyjne odliczanie **tylko gdy czas znany** | W UI zablokowany do terminu; backend niezależnie odrzuca z 0 żądań do źródła |
| **RECOVERING** | Backend naprawdę wszedł w stan kontrolowanego sprawdzenia dostawcy / half-open | „Trwa odzyskiwanie kanału rozpoznania…” | Brak równoległych prób inicjowanych przez UI; nie mylić z obietnicą sukcesu |
| **RESTORED** | Backend faktycznie potwierdził sukces przywrócenia połączenia lub aktualny udany skan | „Zakłócenia MASA ustąpiły. Kanał rozpoznania przywrócony.” | Ponownie normalne działanie |
| **OTHER_ERROR** | Błąd aplikacji, sesji, walidacji, uprawnień albo inny nierozpoznany błąd | Właściwy dotychczasowy komunikat błędu; **bez MASA** | Zgodnie z istniejącym kontraktem |

**Ważne dla UX:** samo dojście licznika do `00:00` **nie dowodzi**, że połączenie wróciło. Znika wyłącznie gwarantowany czas blokady; weryfikacja dostępności pozostaje po stronie serwera. Nie pokazujemy „sygnał odzyskany” bez potwierdzenia backendu.

### 3.1. Przebieg A — rzeczywista blokada

```text
SCAN → brak fresh/stale → upstream niedostępny → stan BLOCKED
     → MASA / komunikat i cooldown (jeżeli znany)
     → kolejne kliknięcia i odświeżenia: brak nowych requestów do Overpass
     → po upływie blokady backend dopuszcza 1 skoordynowane sprawdzenie
     → wynik pozytywny: RESTORED / READY
     → wynik negatywny: BLOCKED z nowym terminem.
```

### 3.2. Przebieg B — awaria, ale istnieje mapa archiwalna

```text
SCAN → brak fresh → upstream niedostępny → poprawny stale cache
     → normalne przetwarzanie indywidualnego skanu
     → stan DEGRADED / dyskretna informacja o historycznym odczycie
     → bez błędnego `api_error`, bez zerowania markerów.
```

### 3.3. Przebieg C — awaria nie jest zakłóceniem MASA

```text
SCAN → gracz poza zasięgiem / błędny token GhostLab / wygasła sesja /
       niepoprawna akcja / bug aplikacji / poprawna pusta mapa
     → normalny stan gry lub właściwy błąd; NIE pokazywać MASA.
```

---

## 4. Copywriting: komunikaty PL / EN

Zasada stylistyczna: język systemu CHAOS — techniczno-fabularny, krótki, czytelny. Nie opisujemy awarii jako ataku na konkretny klan, utraty terytorium, uszkodzenia urządzenia ani celowego sabotażu konkretnych graczy.

| Klucz lokalizacji (propozycja) | Polski | English |
|---|---|---|
| `map.scan.masa.blocked` | **MASA zakłóca sieć rozpoznania. Skanowanie jest chwilowo zablokowane.** | **MASA is disrupting the recon network. Scanning is temporarily blocked.** |
| `map.scan.masa.cooldown` | **Blokada MASA trwa. Kolejna próba możliwa za {time}.** | **MASA interference persists. Another attempt is possible in {time}.** |
| `map.scan.masa.unknown_time` | **Kanał rozpoznania pozostaje niedostępny. Nie znamy jeszcze czasu przywrócenia.** | **The recon channel remains unavailable. Restoration time is not yet known.** |
| `map.scan.masa.degraded` | **Zakłócenia MASA. Odczytano ostatni dostępny zapis terenu.** | **MASA interference. The latest available terrain snapshot was loaded.** |
| `map.scan.masa.recovering` | **Trwa odzyskiwanie kanału rozpoznania…** | **Restoring the recon channel…** |
| `map.scan.masa.restored` | **Zakłócenia MASA ustąpiły. Kanał rozpoznania przywrócony.** | **MASA interference has cleared. Recon channel restored.** |
| `map.scan.masa.retry_ready` | **Blokada czasowa minęła. Możesz sprawdzić sygnał ponownie.** | **The temporary block has expired. You can check the signal again.** |

**Czas:** wyświetlać format użytkowy `1 min 40 s` / `1m 40s`, bez żargonu `Retry-After`, `circuit breaker`, `HTTP 502`. Jeśli backend nie zna terminu, nie generować fikcyjnego licznika i nie obiecywać konkretnych sekund.

**Ostrożność semantyczna:** `retry_ready` nie oznacza `restored`. `degraded` jest udanym skanem z nieświeżymi danymi, a nie „brakiem sygnału”. `recovering` można wyświetlić wyłącznie na podstawie realnego stanu backendu, nie automatycznie po odliczeniu do zera.

### 4.1. Warstwa wizualna (bez nowego show)

- W obrębie istniejącego panelu skanera dodać niewielki **status kanału rozpoznania**: `AKTYWNY`, `ZAKŁÓCENIA MASA`, `PRZYWRACANIE`.
- Przy `BLOCKED`: jedno czytelne ostrzeżenie, subtelny efekt sygnałowego zakłócenia/glitch; nie zasłaniać mapy, nie wyświetlać technicznych surowych logów.
- Przy `DEGRADED`: dyskretny badge, bez fałszywego czerwonego stanu nieudanego skanu.
- Przy `RESTORED`: krótkie, jednorazowe potwierdzenie; nie odtwarzać na każdym renderze/refresh.
- Na mobile całość czytelna na wąskim ekranie; brak nakładania komunikatu na krytyczne kontrolki mapy.
- Animacje respektują `prefers-reduced-motion`; bez obowiązkowej długiej animacji zanim gracz zrozumie stan.

---

## 5. Kontrakt API — wymagania dla Codexa

**Nie zakładać, że Sprint 158 już wystawia konkretne pola.** Najpierw sprawdzić istniejące wyjątki/statusy/metadane serwisu i dopasować małe, kompatybilne rozszerzenie na granicy `run.py` ↔ POI Service ↔ klient mapy.

Obecny kontrakt błędu z wcześniejszego kodu zawiera `scan_outcome: "api_error"`, `message_i18n`, `status`, `markers: []`. **Zachować kompatybilność**: nie przemianowywać istniejących wartości `scan_outcome` i nie podmieniać kodów HTTP bez weryfikacji odbiorców.

### 5.1. Przykład — brak dostępnych danych

```json
{
  "scan_outcome": "api_error",
  "failure_reason": "poi_upstream_unavailable",
  "interference": {
    "type": "masa",
    "state": "blocked",
    "blocked_until": "2026-10-18T10:00:00Z",
    "server_now": "2026-10-18T09:58:00Z",
    "retry_after_seconds": 120
  },
  "message_i18n": {
    "key": "map.scan.masa.cooldown",
    "params": {"time": "2 min"}
  },
  "markers": []
}
```

**To przykład docelowego kształtu, nie informacja o istniejącej implementacji ani prawdziwym czasie blokady.** Nazwy pól dopasować do realnego kontraktu z 158; wybór obiektu `interference` zamiast rozproszonych pól powinien zostać przeanalizowany pod kątem kompatybilności. `blocked_until`/`retry_after_seconds` są opcjonalne: nie zawsze znamy termin. Jeśli oba występują, muszą dotyczyć tego samego stanu źródła. `server_now` pozwala oszacować odliczanie mimo różnicy zegara klienta.

### 5.2. Przykład — udany skan z cache awaryjnego

```json
{
  "scan_outcome": "success",
  "poi_data_mode": "stale",
  "interference": {"type": "masa", "state": "degraded"},
  "message_i18n": {
    "key": "map.scan.masa.degraded",
    "params": {}
  },
  "markers": ["... istniejące markery, bez modyfikacji ich kontraktu ..."]
}
```

**`scan_outcome: "success"` jest wartością ilustracyjną — Codex ma zachować faktyczny, aktualny sposób oznaczania powodzenia skanu.** Nie wolno zastępować istniejących właściwych markerów przykładową tablicą z tekstem; powyższy przykład dokumentuje wyłącznie metadane.

### 5.3. Źródło prawdy i bezpieczeństwo

- Publiczny payload prezentacyjny: semantyczny status i termin (jeśli istnieje), bez URL-i dostawców i surowych wyjątków.
- Telemetria/logi admina: prawdziwa klasa błędu (np. timeout, 429/502/503/504, niepoprawny JSON, problem konfiguracji), identyfikator próby i czas.
- Decyzja `blocked` pochodzi z istniejącego **globalnego provider policy/circuit breaker**, a nie z komunikatu `status`, parsing-u tekstu czy liczby kolejnych kliknięć.
- Dane o dostępności mogą różnić się między dostawcami: MASA oznacza **brak możliwości obsłużenia żądanego skanu**, nie pojedynczy 502 jednego endpointu, jeśli pozostałe źródła lub pełny cache pozwalają kontynuować.
- Nie ujawniać w publicznym API diagnostyki, sekretów, surowych endpointów, tokenów skanera, współrzędnych cudzych graczy lub technicznych identyfikatorów sesji.

---

## 6. Antyspam i synchronizacja (4 workery)

**Backend jest autorytetem.** Gdy `BLOCKED`, kolejne żądanie skanu kończy się od razu odpowiedzią semantyczną, a nie nowym wywołaniem Overpass. Sam disabled button w JS nie wystarczy; można odświeżyć kartę, wywołać endpoint ręcznie albo mieć kilka sesji.

- Po uzyskaniu blokady klient wyłącza ponowne wysłanie akcji `scan` do czasu wskazanego przez backend, **jeśli termin istnieje**. Bez terminu klient oferuje czytelny status, ale nie stosuje nieograniczonego automatycznego odpytywania.
- Dopuszczalny jest **lokalny** timer UI aktualizujący napis bez wywołań sieciowych. Nie planować periodycznych żądań do Overpass/SCAN co sekundę.
- Po wygaśnięciu terminu UI może ponownie dopuścić *ręczne* sprawdzenie stanu, ale **nie** uruchamia automatycznie wielu skanów; backend może nadal zwrócić nową blokadę.
- W stanie half-open prawo do probe należy do współdzielonej polityki z 158, nie do klienta. Jednoczesne kliknięcia przez wielu graczy nie wymuszają osobnych prób.
- Respektować `Retry-After`, globalne limity, `extra_retries`/`extra_timeout` GhostLab i `still_active`, zgodnie z 158. Ulepszenia skanera nie obchodzą globalnej blokady.
- Powtórzone odpowiedzi `blocked` nie powinny spamować toastami ani rozpoczynać od nowa agresywnej animacji skanu.
- Nie blokować całej mapy ani innych interakcji, które nie zależą od zewnętrznego pobrania POI.
- Nie wprowadzać nowej operacji sieciowej do UI tylko po to, by odświeżać napis „MASA”; jeśli potrzebny endpoint diagnostyczny, musi być **lekki i lokalny**, bez dodatkowych żądań upstream, z limitowaniem i uzasadnieniem.

---

## 7. Żywotność i koszty akcji

### 7.1. Scenariusze bez obciążenia zasobów gracza

- `BLOCKED` przed pobraniem danych: **brak zużycia** waluty, energii, limitów skanów i przedmiotów, jeśli dotychczasowe zasady naliczają je za realny skan.
- `api_error` spowodowany niedostępnością źródła po rozpoczęciu akcji: **bez kary za awarię infrastruktury**; stan nie powinien być rozliczony jako udany skan.
- `DEGRADED` z poprawnym stale cache: pełna normalna ścieżka skanowania i dotychczasowa ekonomia gry — to skan wykonany, nie automatyczny „darmowy” wyjątek.
- Odległość poza zasięgiem, anulowanie lub błędny token: zachowują dotychczasowe zasady i komunikaty.

**Wymagana kontrola kodu:** znaleźć miejsce naliczania kosztu/nagród po stronie `run.py` i zależnych modułów; dopilnować spójności przy błędzie, zwłaszcza gdy próba zdążyła rozpocząć procedurę. Żadnych „rollbacków na oko”.

### 7.2. Lokalizacja i błąd bezpieczeństwa

Nie pokazywać graczowi błędu konfiguracji, crasha Python, błędu autoryzacji lub odmowy akcji jako „MASA blokuje skanowanie”. Inny problem = inny komunikat. Administracja musi mieć możliwość diagnozy prawdziwej przyczyny.

---

## 8. Zakres prac dla Codexa

### 159.1 — Audyt kontraktu Sprintu 158 (bez zmian gameplay)

- Odczytać implementację 158, flagę OFF, kształt telemetryki i stany: fresh/upstream/stale, breaker closed/open/half-open, błąd dostawcy, błąd aplikacji.
- Znaleźć handler `action == "scan"` i klientów UI (desktop i mobile), mapowanie `message_i18n` oraz bieżący rendering `scan_outcome`.
- Sprawdzić, **kiedy** aktualnie naliczane są koszty skanu i gdzie powstają markery.
- Dostarczyć mapę istniejących kontraktów i plan minimalnych zmian, bez zgadywania nazw plików/funkcji.

**Bramka:** nie mieszać error class `upstream_unavailable` z pozostałymi wyjątkami.

### 159.2 — Backendowy semantyczny stan skanera

- Ujednolicić mapowanie faktycznych stanów 158 na `ready / degraded / blocked / recovering / restored` tylko tam, gdzie jest dowód stanu.
- Rozszerzyć odpowiedź skanu o kompatybilny, strukturalny kontekst prezentacyjny + klucz lokalizacji + termin blokady, gdy istnieje.
- Nie wyciekać surowych wyjątków API do gracza; zachować szczegóły w logach.
- Nie zmieniać wyniku, statusu operacji ani listy POI tylko po to, żeby wyświetlić fabułę.

**Bramka:** `api_error` + MASA wyłącznie przy realnie niedostępnych danych; `stale` zachowuje udany skan.

### 159.3 — Klient mapy, desktop i mobile

- Dodać czytelny stan kanału rozpoznania w istniejącym UI (badge/inline alert, nie globalny modal).
- Zapewnić brak automatycznych retry i spamowania toasts; kontrolować interakcję `SCAN` podczas blokady.
- Timer oprzeć na czasie serwera; rozróżnić „można sprawdzić” od „już przywrócono”.
- Nie przenosić lokalnego stanu błędu między niezależnymi sesjami lub akcjami, jeśli backend tego nie potwierdzi.
- Dopiąć PL/EN w istniejącym systemie tłumaczeń, bez hardcode.

**Bramka:** wąski ekran mobile oraz desktop pokazują tę samą semantykę i nie ograniczają innych funkcji mapy.

### 159.4 — Telemetria, testy i wdrożenie

- Dodać liczniki zdarzeń warstwy prezentacji: `masa_blocked_shown`, `masa_degraded_shown`, `masa_restored_shown`, `scan_short_circuited` (nazwy dopasować do projektu), bez nadmiernej kardynalności.
- Testy jednostkowe/mapowania + browser E2E + integracyjne przy 4 workerach z symulacją 502/429, stale cache i half-open.
- Wdrażać za **osobną, domyślnie wyłączoną** flagą UX (nazwa do dopasowania, proponowana `CHAOS_POI_MASA_UX_ENABLED`), zależną od aktywnej i zaakceptowanej infrastruktury 158.
- Udokumentować rollback ograniczony do flagi UI/kontraktu, bez czyszczenia wspólnego cache.

**Bramka:** testy masowe potwierdzają brak wzrostu requestów upstream spowodowanego nowym UI.

---

## 9. Scenariusze testowe / macierz dowodów

| ID | Scenariusz | Oczekiwany wynik |
|---|---|---|
| M159-01 | 502/timeout, brak dopuszczalnego cache | `BLOCKED` + MASA, zero HTTP/stacktrace w UI, poprawny `scan_outcome` zgodny z istniejącym kontraktem |
| M159-02 | 10 kliknięć podczas `BLOCKED` w jednym kliencie | Brak lawiny toastów/animacji; **0 zapytań Overpass** z tych kliknięć |
| M159-03 | 20 klientów na 4 workerach podczas `BLOCKED` | Jeden współdzielony stan ochronny, **0 dodatkowych prób upstream** |
| M159-04 | Koniec cooldownu, współbieżne żądania | Maksymalnie jeden globalnie dopuszczony probe; UI nie obiecuje przywrócenia |
| M159-05 | Probe kończy się ponownym 502 i nowym `Retry-After` | Wspólny nowy termin; prawidłowy stan `BLOCKED`; brak sztucznego odliczania |
| M159-06 | Poprawny complete stale cache | Udany skan na danych cache + `DEGRADED`; markery, NPC i stan gracza bez regresji |
| M159-07 | Fresh/upstream sukces | Zwykły skan bez alertu MASA |
| M159-08 | Pozytywny probe | `RESTORED` tylko po potwierdzeniu; odpowiednia jednorazowa informacja |
| M159-09 | `out_of_range`, 401 sesji, brak tokenu GhostLab | Dotychczasowe komunikaty; zero MASA |
| M159-10 | Poprawne puste `elements: []` | Brak POI != awaria; brak MASA |
| M159-11 | `extra_retries=3`, `extra_timeout=10` w GhostLab | Żadnego ominięcia blokady; poza blokadą funkcjonalność ulepszenia zachowana |
| M159-12 | Powrót/odświeżenie klienta w trakcie blokady | Poprawny stan z backendu; brak automatycznego skanowania i dodatkowego upstream |
| M159-13 | Frontend z niewłaściwym zegarem | Timer poprawnie wykorzystuje `server_now` lub relatywny TTL z backendu |
| M159-14 | Brak terminu blokady | Bez zmyślonego czasu, bez automatycznych prób |
| M159-15 | Błąd Pythona lub walidacji danych | Bez fabuły MASA; techniczna przyczyna widoczna operatorowi |
| M159-16 | Skan niedostępny przed i po pobraniu kosztu | Brak nieuzasadnionego zużycia zasobów / zdublowanych operacji |
| M159-17 | Klient mobilny, desktop, PL i EN | Właściwa lokalizacja, dostępność tekstu, brak kolizji UI |
| M159-18 | Flaga UX OFF, flaga infrastruktury 158 OFF | Brak regresji legacy skanowania, rollback odwracalny |
| M159-19 | Circuit breaker na jednym dostawcy, drugi działa | Brak fałszywej globalnej blokady MASA, jeśli skan może zostać obsłużony |
| M159-20 | Skan anulowany (`still_active == false`) | Bez nadpisania przez „MASA”; bez nowego retry |

**Dowody do dołączenia:** logi/syntetyczne liczniki żądań, testy 4-worker, screenshoty desktop/mobile dla stanów, przykłady PL/EN, porównanie flag ON/OFF, audyt ekonomii skanu i rollback.

---

## 10. Kryteria akceptacji (Definition of Done)

Sprint 159 można oznaczyć **PASS** dopiero po udowodnieniu, że:

1. Gracz rozumie: **skan działa**, **skan działa na ostatnim zapisie**, **MASA blokuje kanał**, **trwa sprawdzanie połączenia**, **połączenie zostało faktycznie przywrócone**.
2. Komunikaty MASA pojawiają się tylko dla właściwych stanów infrastruktury; nie są uniwersalną etykietą wszystkich błędów.
3. Stan blokady jest wspólny dla 4 workerów, a powtarzane kliknięcia nie powodują dodatkowego ruchu Overpass.
4. Powrót do działania wymaga potwierdzenia backendu; kończący się countdown sam nie staje się „sukcesem”.
5. Istniejący gameplay — GhostLab, koszty, skanowane POI, markery, kamery, NPC i prywatny stan gracza — działa bez regresji.
6. Desktop/mobile i PL/EN są spójne; operator nadal widzi realne przyczyny awarii.
7. Istnieje flaga niezależnego włączenia/wyłączenia UX, testy regresyjne i udokumentowany rollback.
8. **Bramka 158** (baseline OFF, wdrożenie, kontrolowane ON, produkcyjny odbiór) została spełniona przed produkcyjnym uruchomieniem 159.

---

## 11. Poza zakresem sprintu

- Nowe, losowo generowane „ataki MASA” niezwiązane z rzeczywistą dostępnością POI.
- Nowe skutki gospodarcze, społeczne lub terytorialne MASA.
- Własny serwer Overpass / pełny import OSM.
- Rozszerzanie cache na sąsiadujące obszary bez dowodu poprawności geometrii.
- Zmiana zachowania skanera GhostLab i wyników fabularnych NPC.
- Przebudowa całego interfejsu mapy czy pełnoekranowe show.

---

## 12. Polecenie startowe dla Codexa

> Realizujemy Sprint 159 — `MASA / zakłócenia rozpoznania`. Sprint 158 zawiera lokalnie zaimplementowaną infrastrukturę POI (trwały cache, single-flight, limity, retry, circuit breaker, telemetria), ale jej pełny odbiór produkcyjny jest osobną bramką. Najpierw przeczytaj tę specyfikację, istniejący kod 158 oraz runbook/evidence dla 158. Zinwentaryzuj faktyczne kształty wyjątków, metadanych cache/breakera, handlera `action=scan`, klientów mapy, GhostLab i systemu i18n. Przygotuj minimalny plan zmian. Następnie wprowadź semantyczne stany READY/DEGRADED/BLOCKED/RECOVERING/RESTORED, lokalizowane komunikaty MASA i kontrolę UX bez agresywnego retry; nie zmieniaj mechaniki skanowania ani jej kosztów. Gdy backend odmawia skanu z powodu blokady upstream, dodatkowe kliknięcia mają powodować 0 nowych żądań Overpass; po cooldownie prawo do jednego probe pozostaje w infrastrukturze 158. Zachowaj kompatybilność payloadów, sprawdź ścieżki błędów bez MASA, testuj desktop/mobile i PL/EN, 4 workery oraz flagi OFF/ON. Nie włączaj flag produkcyjnych ani nie wykonuj wdrożenia bez oddzielnej decyzji. Podaj wyniki testów, ryzyka i dowody PASS/FAIL.

---

## 13. Materiały odniesienia

- `CHAOS_POI_INFRASTRUCTURE_V1_CONCEPT.md`, rozdział 17 — „MASA / zakłócenia skanowania”.
- Kod analizowany przed Sprintem 158: `poiFetchClass.py`, `run.py` (`POIFetcher`, `action == "scan"`), `ghostlab_scanner.py`.
- Zgłoszony stan 158: 4 workery, timeout 120 s, 41 testów Python PASS, 24 browser tests PASS, nowa warstwa domyślnie OFF.
- Przywołane przez zespół artefakty w repo (do odczytu przez Codexa, nie były dostarczone tutaj): `doc/runbooks/poi_infrastructure_158.md`, `doc/audits/sprint_158_evidence.md`.

**Główna zasada sprintu 159:** *MASA może zakłócić rozpoznanie w opowieści CHAOS; nie może służyć jako zasłona dla błędów aplikacji ani uzasadnienie spamowania przeciążonego API.*
