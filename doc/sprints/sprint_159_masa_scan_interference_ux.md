# Sprint 159 — MASA / stan kanału rozpoznania

Data: 2026-10-18. Status: implementacja i weryfikacja lokalna gotowe; pakiet oczekuje publikacji i odbioru na VPS. Bez produkcyjnego PASS. [Dowody](../audits/sprint_159_evidence.md).

Źródło: [koncepcja](../prototypes/poi/sprint_159_masa_scan_interference_ux.md). Operator polecił realizację przed wznowieniem testów POI. Pakiet można wdrożyć z flagami OFF; włączenie 159 zależy od kontrolowanego odbioru infrastruktury 158. Nie zmieniamy samodzielnie konfiguracji VPS.

## 159.1 — rzeczywisty kontrakt i ekonomia

- `poi_infrastructure/service.py`: cache fresh/upstream/stale, wyjątki POIError/Cancelled, współdzielony slot i cooldown dostawcy. Dotąd brak metadanych zwracanych mapie. Breaker nie otwiera się po każdym timeout; Retry-After i 429 mają własny czas.
- `repository.py`: współdzielone tabele providers/leases. Nie tworzymy drugiego licznika blokad. Oznaczenie `@probe:<grupa>` jest atomowo zapisywane razem z istniejącym slotem HTTP; opisuje próbę, nie przyznaje dodatkowego budżetu.
- `run.py`, `/map-action`, `action=scan`: sesja, projekcje pozycji, zasięg, teren i token GhostLab przed POI; markery i snapshot po sukcesie. Brak pobrania waluty/energii za sam skan. Nie dodajemy refundu ani nowych nagród. Aktywacja GhostLab nadal podlega własnym zasadom.
- `templates/map_template.html`, `mapAction`: wspólny klient desktop/mobile; przy api_error wraca przed czyszczeniem warstw. `ghostlab_scanner_map.js` dekoruje ten sam przycisk.
- Lokalizacje `static/locales/{pl,en}/map_actions.json`; istniejący GhostLocale i message_i18n. Wersja treści historycznych bez zmian, rewizja assetów do odświeżenia katalogów.

## 159.2 — semantyczny stan backendu

Request-local ContextVar przekazuje dowody do handlera, bez współdzielonego `last_result` i bez danych gracza w cache. Odpowiedź zachowuje scan_outcome/markers i dodaje poi_data_mode/interference/failure_reason. Źródłowe wyjątki pozostają w logach, nie w publicznym status.

| Stan | Dowód |
| --- | --- |
| ready | aktualny udany fetch lub kompletny fresh, także pusta odpowiedź |
| degraded | kompletny dopuszczony stale; normalne przetwarzanie markerów |
| blocked | brak dopuszczonego cache i wszystkie źródła dostępne dla tej polityki skanu mają otwarty cooldown |
| recovering | istnieje aktywny znacznik rzeczywistej próby po awarii, współdzielony slot już przyznany |
| restored | udana odpowiedź kontrolowanej próby, zapis do cache i reset błędu dostawcy |
| brak MASA | sesja, zasięg, walidacja, anulowanie, storage, błędy aplikacji; również brak dowodu blokady po pojedynczej awarii |

To doprecyzowuje M159-01: sam HTTP 502 bez otwartej polityki nie uzasadnia BLOCKED ani licznika. Nie zmieniamy progu breaker tylko dla narracji. Trwałe odmowy HTTP i błędy walidacji nie są podstawą MASA. Inny dostępny dostawca lub poprawny cache mają pierwszeństwo przed prezentacją blokady.

## 159.3 — mapa PL/EN

Niewielki panel statusu, bez modala, z zachowaniem mapy i markerów. SCAN blokuje ponowne wysłanie tego samego punktu tylko przez znany relatywny czas z backendu; inny punkt może mieć poprawny cache. Jeden aktywny skan klienta. Licznik lokalny, bez polling/retry. Zero sekund oznacza możliwość ręcznego sprawdzenia, nie sukces. Brak przenoszenia blokady przez localStorage między sesjami.

Odświeżenie nie uruchamia skanu: dopiero ręczna akcja odczytuje współdzieloną politykę. Ten odczyt nie wywołuje Overpass przy aktywnej blokadzie. Nie dodajemy endpointu tylko do napisu MASA. RESTORED wygasa po 5 s; powtórzone blocked nie wysyła toastów. prefers-reduced-motion wyłącza efekt.

## 159.4 — dowody i wdrożenie

- Testy cache/stanów, oba OFF i ON, różne źródła, brak MASA dla innych błędów, izolacja dowodów między żądaniami.
- 20 żądań na 4 procesach przy blokadzie: 0 HTTP. 4 równoczesne żądania po cooldownie: 1 probe, pozostałe widzą recovering.
- Testy realnego `/map-action` na izolowanych kontach, bez zapisu do produkcyjnej bazy.
- Playwright: desktop/mobile, PL/EN, zachowanie markerów, spam kliknięć, countdown, nieprawidłowy zegar, brak auto-retry, reduced motion i flagi.
- Telemetria UI: zdarzenia `poi-ux` / console `poi_ux` (shown i scan_short_circuited), bez współrzędnych i kont. Log backendu poi_fetch pozostaje autorytatywnym dowodem liczby prób; nie nazywamy wygenerowanej odpowiedzi dowodem wyświetlenia.

## Rollout i rollback

Flaga `CHAOS_POI_MASA_UX_ENABLED=1` działa wyłącznie razem z `CHAOS_POI_INFRASTRUCTURE_ENABLED=1`. Obie domyślnie OFF. Brak migracji bazy gry. Najpierw testy pakietu na VPS i restart OFF, potem uzgodnione kontrolowane włączenie 158/159 i odbiór. Zależność od 158 pozostaje; same lokalne testy jej nie zamykają.

Rollback samego UX: `CHAOS_POI_MASA_UX_ENABLED=0 pm2 restart chaos --update-env` i ponowne otwarcie mapy. Cache pozostaje. Rollback infrastruktury: istniejący runbook 158. Utrwalić uzgodnione flagi w konfiguracji procesu. Nie deklarować przywrócenia dostawcy na podstawie samego upływu czasu.
