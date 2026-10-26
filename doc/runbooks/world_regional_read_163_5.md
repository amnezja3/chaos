# 163.5.2 — regionalny odczyt Overpass przez aktywny router

Status 26.10.2026: kod i testy lokalne PASS, aktywacja produkcyjna OFF.
Kontynuacja [pakietu exact](world_global_exact_163_5.md), nie zamknięcie wszystkich
regionalnych profili MapLark/Geoapify.

## Przygotowane zachowanie

Wykorzystujemy istniejące `CoveredGeometry`, `GeometrySnapshot`, `fill_plan` oraz
world_snapshot/member/coverage. Nowy profil `routed-overpass-closure-v1` izoluje
dane od starej ścieżki bez rewizji i od canonical GeoJSON. Nie ma nowej bazy ani
migracji schematu. Pełna topologia OSM pozostaje zachowana w snapshotcie.

Opcjonalne pobranie pełnej geometrii ma promień 1500 m, zgodnie z istniejącym
planem 160; zasięg skanu gracza pozostaje bez zmian. Jeden snapshot może obsłużyć
różne zapytania całkowicie mieszczące się w jego pokryciu. Nie łączymy snapshotów.
Niepewna granica, brak członków relacji, nieobsługiwany przypadek lub zapytanie poza
pokryciem oznacza MISS / fallback; nigdy pozornie kompletny wynik.

Wyniki lokalne sprawdzane są względem źródła, rewizji, decyzji storage, terminów,
skrótu danych i metadanych pokrycia oraz bieżącej aktywności skanera. Publikacja
sprawdza lease i aktualny registry wewnątrz tej samej transakcji. Odczyt jest
ograniczony do 64 kandydatów, 8 MiB payloadu i kontrolowanego czasu 2 s.
Siedmiodniowa retencja nie przedłuża 300/1800 s świeżości/dopuszczalnego stale.

Wspólny lease regionu łączy żądania kilku procesów. Niepowodzenie szerszego
pobrania zużywa próbę tego źródła; router może przejść do kolejnego źródła w
istniejącym terminie. Nie dodajemy drugiej automatycznej próby tego samego API.

## Testy offline na VPS — jeden pakiet

Po pobraniu ustalonego wydania, z czystej powłoki bez eksportowanych flag testowych:

```bash
cd ~/app/chaos
bash tools/world_local_read_acceptance_163_5.sh
```

Pakiet nie zmienia produkcyjnej bazy, registry ani konfiguracji PM2 i nie wywołuje
dostawców. Test infrastruktury używa lokalnego serwera loopback. Test czterech
procesów ma własne bazy i transport. Nie wymaga kluczy API.

## Warunki przed oddzielnym testem sieciowym

- Wszystkie warunki exact z poprzedniego runbooka, poprawny backup i HTTP 200.
- Wybrane źródło Overpass ma ważne `normal_scan`, `wide_fetch`, `storage`,
  `world_storage`, jest włączone i obecne w zatwierdzonej trasie live.
- Zgoda na tło VK nie przyznaje tych zakresów. Ten pakiet nie zmienia decyzji.
- W `ecosystem.web.config.js` dopiero podczas kontrolowanego odbioru:
  `CHAOS_POI_WORLD_ACCESS_MODE=global`, ingest/read=1,
  `CHAOS_POI_WORLD_REGIONAL_READ_ENABLED=1`, `CHAOS_POI_WIDE_FETCH_ENABLED=1`,
  routing=1. Domyślnie nowe przełączniki pozostają 0.

Na VPS wykonywać zbiorczo: pierwszy skan → zapis pełnej geometrii → sąsiedni
skan z innego konta (inny klucz, `source=world`) → restart i powtórzenie → punkt
poza pokryciem z normalnym fallbackiem. Powiązać log źródła z operacją transportu;
sam marker ani globalny stan budżetu nie dowodzą 0 HTTP dla danego skanu.
Aktualna dostępność Overpass jest zewnętrzną zależnością testu, nie powodem
automatycznego powtarzania zapytań ani zmiany zaakceptowanego wyniku testów lokalnych.

Rollback regionalny: regional_read=0 i wide_fetch=0 w ecosystemie, reload,
HTTP 200. Exact local-read może pozostać aktywny, jeśli został osobno odebrany.
Nie czyścić bazy ani księgi. Całkowity rollback: procedura exact.

## Zapotrzebowanie i otwarte elementy

Zapis sektora przeniesiono do `Service.fetch`, przed wyborem dostawcy i cache.
Jeden skan zapisuje popyt jeden raz; trafienia Overpass/cache/world są uwzględnione.
To nie jest jeszcze hook samego poruszania się ani halo — te zadania nadal otwarte.

MapLark: obecne capture roads/water nie potwierdzają pełnego regionalnego POI.
Geoapify: profil commercial pozostaje niepełnym zamiennikiem skanera. Nie
przepinamy ich do regionalnego gameplayu pod profilem Overpass. Zapisane dane
GeoJSON nie zastępują oryginalnych członków i węzłów potrzebnych temu selektorowi.
