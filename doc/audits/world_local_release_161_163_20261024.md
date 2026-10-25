# 161–163 — lokalny pakiet do wspólnego odbioru VPS

Decyzja operatora: przygotowanie kodu, testów i instrukcji bez przerywania na
pojedyncze działania serwerowe. Nie wykonano pusha, wdrożenia, prób API ani ON.

## Zmiany

- land_water: offline adapter gotowego regionalnego produktu, jawne role
  land/sea i wersjonowane pochodzenie; polygony, otwory, wyspy, zależności.
- Wspólny magazyn v2: opcjonalny LandWaterOrigin w payloadzie. Bez migracji,
  drugiej bazy ani zmiany kodowania istniejących zwykłych obiektów.
- Odczyt obszarowy wymaga dowodu, wersji datasetu i aktualnych dependency hashes.
  Brak/zmiana zależności daje MISS; nie wystarcza to, że plik nadal jest świeży.
- Topologia: cały mały region pokryty bez luk; overlap land–sea odrzucony,
  overlap tej samej klasy dopuszczony dla split produktów; brak automatycznej
  naprawy, domyślnego oceanu lub rekonstrukcji z niepełnego brzegu.
- Panel nie deklaruje dopuszczenia land_water do lokalnego odczytu bez
  sprawdzenia aktualnych zależności; źródłowy dowód i prawo storage są osobne.
- CLI inspekcji produktu: ograniczone pliki, hash manifestu, zero HTTP/DB writes.
- CLI stanu PM2: tylko allowlista flag, ukrycie sekretów i nieznanych wartości;
  brak wartości nie jest domyślnym PASS. Zero zmian runtime.
- tools/world_vps_acceptance.sh: jeden zestaw testów + read-only storage/runtime,
  prywatne raporty, stop przy błędzie; bez aktywacji, restartów i prób dostawców.

## Wykonana walidacja

| Sprawdzenie | Wynik |
| --- | --- |
| test_world_*.py po poprawce wymogu wersji | 272 PASS / 198.143 s |
| test_poi_*.py | 92 PASS / 127.118 s |
| Land/water po dodaniu zabezpieczenia projekcji panelu | 9 PASS / 3.289 s |
| Dashboard po tej zmianie | 13 PASS / 17.357 s |
| Bash -n narzędzia odbioru | PASS (Git Bash lokalnie) |
| git diff --check | PASS |

Pierwszy pełny przebieg World miał 269 testów i jeden FAIL: konstruktor dowodu
land_water nie wymagał wersji datasetu. Dodano wymóg, zachowano istniejący test
odmowy i powtórzono cały World. Nie pominięto błędu. Finalny test panelu dodano
po pełnym przebiegu; liczba 272 nie obejmuje tego dodatkowego testu.

Playwright MCP, izolowany tools/poi_admin_fixture.py --world --routing:
- tests/browser/world_atlas.js: PL/EN × 1440/390 px, lista warstw, pusty dowód,
  szczegóły, warning budżetu, zoom/fit, brak overflow; zero pageErrors i zero
  externalRequests w zarejestrowanym scenariuszu;
- tests/browser/poi_routing.js: te same cztery warianty, zapis hierarchii i
  przywrócenie, Geoapify nadal oznaczony unverified, brak overflow/pageErrors.
Przeglądarkę i lokalny serwer fixture zamknięto. Nie użyto kont produkcyjnych.
Scenariusze UI wykonano przed końcowym warunkiem land_water w projekcji;
ten warunek odebrano dodatkowym testem dashboardu i produktu.

Benchmark Windows, tracemalloc, dane syntetyczne, brak konkurencyjnego obciążenia:

| Obiekty | Publikacja s | Odczyt s | Max hold+close s | Post-commit WAL B |
| --- | ---: | ---: | ---: | ---: |
| 50 | 0.1674 | 0.0524 | 0.016914 | 107152 |
| 680 | 3.5401 | 0.3702 | 0.196951 | 1042392 |

To nie są SLO VPS ani szczyty WAL/RSS. RSS null na tym systemie. Nie podniesiono
limitów na podstawie tych pomiarów. Testy używają fixtures/mocked transport;
odczytano jedynie publiczną dokumentację źródeł, bez pobierania geografii.

## Co jest gotowe, a co nie jest odbiorem końcowym

| Obszar | Stan lokalny | Zależność przed ON / pełnym odbiorem |
| --- | --- | --- |
| MapLark, budżet, exact/local | Regresja PASS; wcześniejsze piloty VPS PASS | Sprawdzenie aktualnego runtime i gameplay w jednym odbiorze |
| Roads | Rzeczywiste fixtures i ograniczony pilot VPS PASS | Szersza kwalifikacja/regiony i obserwacja rolloutu |
| Waterways / inland_water | Rzeczywiste dane i restore lokalny PASS | Regionalna kwalifikacja i rzeczywista próbka otworu/multipart |
| Land–sea | Kontrakt, magazyn i odczyt syntetyczny PASS | Dopuszczony regionalny produkt z wersją/dependencies; brak takiego wycinka |
| Geoapify/hierarchia | Routing/UI/adapter testowane; unverified pomijany | Pełność profilu, geometria i uzgodnienie 4 niepewnych operacji |
| Worker/discovery | Lease/budżet/priorytet testowane, wcześniejszy bounded pilot VPS | Zatwierdzony zakres czasu/regionów/warstw i obserwacja po ON |
| Panel/metadane | PL/EN desktop/mobile PASS lokalnie | Produkcyjna konfiguracja i odbiór serwera |

Brak źródła nie jest implementowany jako fałszywe COMPLETE. Nie twierdzimy,
że pełny zakres 161–163 został ukończony. Warunki zależne od danych i decyzji
zostały zebrane w jednym planie, bez żądania kolejnych działań operatora teraz.

## Odbiór VPS — faza 1, 2026-10-24

Operator dostarczył wynik `tools/world_vps_acceptance.sh` po aktualizacji do
`9927254`. Raporty: `/home/johndoe/chaos-world-acceptance-KGe8to`.

- World: 273 testy PASS (121.880 s); POI: 92 PASS (68.584 s), łącznie 365.
- Kontrola kopii bazy: integrity/foreign_keys OK, schema 2, metryki gotowe,
  2 snapshoty, 135186 logical bytes; zero zapytań do dostawców i zapisów produkcyjnych.
- Jedno zadanie COMMITTED, brak unresolved i wygasłych lease.
- Pilot regionalny roads (75 obiektów) jest EXPIRED i niedopuszczony do odczytu;
  to oczekiwany upływ TTL. Starsze 29 obserwacji roads pozostaje UNKNOWN.
- MapLark: 52/800 dziennie, 76/24000 rolling; brak niepewnych operacji.
  Geoapify: nadal 4 niepewne operacje i 20 zarezerwowanych kredytów, bez resetu.
- PM2: baseline_matches; web online, MapLark ON, ingest/read/routing OFF,
  discovery passive, age=0; discovery worker stopped.

Faza 1 PASS. Wynik nie potwierdza załadowania nowego kodu do procesów web:
skrypt nie wykonuje restartu. Pozostaje faza 2 (przeładowanie web i odbiór gry)
oraz otwarte kwalifikacje źródeł i kontrolowany rollout z powyższej tabeli.
Pojedynczy udany skan w metrykach nie stanowi pomiaru SLO.

## Odbiór runtime i gry — faza 2 PASS, potwierdzenie 2026-10-25

Po poleceniach wdrożeniowych operator przekazał `baseline_matches`, HTTP 200
na /launch oraz udane `pm2 save`. Konfiguracja pozostaje bez zmian:
MapLark ON, world ingest/read/routing OFF, discovery passive, age=0,
worker discovery stopped. Odczyt PM2 jest kontrolą metadanych, nie pamięci workerów.

2026-10-25 operator potwierdził poprawne skanowanie, hakowanie i łączenie
w terytorium na nowym koncie testowym oraz na istniejącym koncie.
Źródło dowodu: test manualny operatora na produkcji; nie test wykonany przez
agenta. Odbiór wdrożonego pakietu zamknięty PASS, bez potrzeby ponawiania skanów.
Nie rozszerzamy tego potwierdzenia na pozostałe scenariusze ani kwalifikację
Geoapify, warstw wodnych/ląd–morze czy aktywację regionalnego discovery.
Te pozycje pozostają otwarte zgodnie z planem faz 3–4.

Instrukcja wspólnego przejścia: [world_final_acceptance_161_163.md](../runbooks/world_final_acceptance_161_163.md).
Źródła i kontrakt produktu: [world_land_water_product.md](../runbooks/world_land_water_product.md).
