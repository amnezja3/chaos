# 163.5 — regionalny odczyt MapLark

## Zmiana zachowania

Nowy, jawny profil `chaos-maplark-region-geometry-v1` korzysta z kompletnego
bbox POI zapisanego przez istniejący kolektor. Nie jest deklaracją identyczności
ze wszystkimi przypadkami natywnego API radius. W otrzymanej niezależnej parze
odtwarza 18/18 ID, tagi i markery. Dotychczasowe mechaniki gry pozostają.

Kolejność: fresh cache → exact world → regional world → API → dopuszczalny stale.
Jeden snapshot musi obejmować cały promień; nie łączymy regionów. Wszystkie filtry
POI, kompletność, rewizja, prawa, digest i wiek muszą pasować. Geometria decyduje
o selekcji, dotychczasowy eksport o markerze. Obsługiwane Point, LineString,
Polygon i MultiPolygon; otwory zachowuje Shapely. Lokalna metryka płaska ma
jawne ograniczenia: |lat|≤60°, promień≤500 m, geometrie w odległości kątowej
≤0,1° od środka. Pas niepewności max(5 m, 1% promienia) daje MISS i API.
Ten margines jest regułą ostrożności, nie dowodem równoważności metryk dostawcy.

Niepełna lub za stara odpowiedź, zmiana rewizji, cofnięcie praw i brak pokrycia
również dają MISS. Archiwum 7 dni nie staje się świeżym skanem: nadal 300/1800 s.
Nie zmieniamy budżetów, kolejności źródeł ani historycznych rozliczeń Geoapify.
Geoapify pozostaje źródłem obserwacji commercial, nie pełnym fallbackiem gry.

## Wdrożenie i odbiór

Po pushu lokalnego pakietu, na VPS:

```bash
cd ~/app/chaos && git pull --ff-only &&
bash tools/world_maplark_region_acceptance.sh
```

Pakiet nie wykonuje HTTP do dostawców ani nie zmienia konfiguracji. Migracja
nie jest potrzebna: wykorzystujemy istniejące snapshoty z metadanymi bbox.
Po PASS aktywacja **nowego profilu selekcji**:

```bash
pm2 startOrReload ecosystem.web.config.js --only chaos --env world_maplark_region --update-env
curl --silent --show-error --connect-timeout 3 --max-time 10 -o /dev/null -w 'Launch HTTP: %{http_code}\n' https://chaos.re/launch
```

Przy przejściowym 502 po reload sprawdzić gotowość ponownie przed testem gry.
Kolektora nie restartujemy, kluczy nie wpisujemy do repo. Nie zmieniamy routingu
MapLark-first ani nie przywracamy VK-first.

Zbiorczy odbiór: nowy i stary gracz skanują, hakują i tworzą terytorium.
Dla świeżego pełnego bbox wykonać przesunięty skan, którego koło mieści się
w regionie. Nie należy teleportować w nieznany sektor i oczekiwać trafienia.
Potwierdzenie: `poi_maplark_region` z `source=world`, a następnie udany skan.
Sam log `poi_maplark_cache source=world` może oznaczać wcześniejszy exact reader.

```bash
pm2 logs chaos --lines 100 --nostream 2>&1 | grep -E 'poi_maplark_region|poi_route|poi_scan'
.venv/bin/python tools/world_collection_monitor.py
```

Brak świeżego regionu oznacza poprawny fallback, nie zaliczony test regionalny.
W takim przypadku zbieramy monitor i log jednego skanu; nie uruchamiamy serii
płatnych prób. Po potwierdzeniu działania: `pm2 save`.

Rollback tylko nowego odczytu, bez usuwania danych:

```bash
pm2 startOrReload ecosystem.web.config.js --only chaos --env world_regional --update-env
pm2 save
```

## Granice odbioru

### Jednorazowy odbiór w Paryżu

Gdy inspekcja wykazała brak bbox w okolicy Luwru, przygotowano jeden jawny
request: bbox [2.333,48.856,2.343,48.866], pełny filtr POI, limit 1000,
clipGeometry=false. Uruchomienie: `bash tools/world_paris_region_acceptance.sh`.
Skrypt wykonuje 3 izolowane testy, pokazuje plan, odczytuje klucz bez echa,
tworzy backup SQLite, rezerwuje 20 w istniejącym budżecie konta i osobnym
jednorazowym zakresie. Nie resetuje podlimitu kolektora; jest to jawna,
oddzielna operacja odbiorowa. Rezerwacja nie jest twardym limitem ceny API.
Stałe operation ID zabrania ponowienia płatnego requestu.

Po zapisie wynik zawiera `positions` (dwie pozycje wybrane lokalnie z 25
kandydatów) i `acceptance_ready`. Jeśli true, przenieść main i neo1 na różne
podane pozycje i wykonać skany w ciągu 300 s od pobrania, bez hakowania.
Wymagany log poi_maplark_region source=world. Rzeczywisty środek skanu musi
odpowiadać wybranej pozycji; przesunięcie lub inny promień może dać fallback.
Jeżeli false lub błąd, przekazać wynik bez kolejnego uruchomienia requestu.
Gęsta zabudowa może spowodować niejednoznaczność granic dla wszystkich
kandydatów; nie zmniejszamy marginesu bezpieczeństwa tylko na potrzeby PASS.

### Osobno zatwierdzona diagnostyka v2

Po błędzie provider_response_incomplete operator zatwierdził jedno nowe
pobranie tego samego bbox z rezerwacją 20. Nie znamy przyczyny poprzedniego
braku kompletności, więc nie zmieniamy jednocześnie limitu ani geometrii zapytania.
Polecenie: `bash tools/world_paris_region_acceptance.sh --diagnostic-v2`.
Osobne stałe ID `region:paris-poi-1635-diagnostic-v2`; operacja v1, jej zakres
i koszty pozostają bez zmian. Brak automatycznych ponowień, także po błędzie.

W prywatnym katalogu obok nowego backupu zapisujemy request.json (parametry,
nie nagłówki), http.json, body.json, allowlistę headers.json oraz report.json
lub failure.json. Odpowiedź zapisujemy przed normalizacją, również gdy później
zostanie odrzucona. Niepełne dane nie trafiają do world. Sekret jest redagowany;
nie zapisujemy nagłówków autoryzacji. Przy timeout przed odpowiedzią nie ma body;
pozostaje raport błędu i księga operacji. Artefakty ograniczone do 8 MiB na plik.
6 testów lokalnych PASS: zapis niepełnej odpowiedzi i błędu normalizatora,
rozliczenie, zachowanie v1, brak ponowienia i brak sekretów.

Lokalny PASS nie jest odbiorem VPS. Ten pakiet dostarcza runtime regionalnego
MapLark; nie zamyka automatycznie pełnej kwalifikacji Geoapify, dostępności VK
ani wszystkich A01–A12. Zachowujemy istniejące dowody; nowych nie deklarujemy
bez wykonania. Nie nazywamy UNKNOWN globalnym certyfikowanym pokryciem.
