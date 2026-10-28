# 163.5 — regionalny odczyt MapLark

## Zmiana zachowania

Zatwierdzony profil `chaos-maplark-region-geometry-v2` korzysta z kompletnego
bbox POI zapisanego przez istniejący kolektor. Nie jest deklaracją identyczności
ze wszystkimi przypadkami natywnego API radius. W otrzymanej niezależnej parze
odtwarza 18/18 ID, tagi i markery. Dotychczasowe mechaniki gry pozostają.

Kolejność: fresh cache → exact world → regional world → API → dopuszczalny stale.
Jeden snapshot musi obejmować cały promień; nie łączymy regionów. Wszystkie filtry
POI, kompletność, rewizja, prawa, digest i wiek muszą pasować. Geometria decyduje
o selekcji, dotychczasowy eksport o markerze. Obsługiwane Point, LineString,
Polygon i MultiPolygon; otwory zachowuje Shapely. Lokalna metryka płaska ma
jawne ograniczenia: |lat|≤60°, promień≤500 m, geometrie w odległości kątowej
≤0,1° od środka. Selekcja v2: odległość pełnej geometrii ≤ promień.
Metryka: x=(lon-lon0)*111195*cos(lat0), y=(lat-lat0)*111195, lat0 w radianach
w funkcji cos. Nie odrzucamy całego skanu przez obiekt blisko granicy koła.
Pozostaje margines max(5 m, 1% promienia) przy sprawdzaniu, czy całe koło
mieści się w bbox; to kontrola pokrycia, a nie wykluczanie obiektów.
Profil jest jawną selekcją CHAOS, nie obietnicą identyczności z API radius.

Niepełna lub za stara odpowiedź, zmiana rewizji, cofnięcie praw i brak pokrycia
również dają MISS. Archiwum 7 dni nie staje się świeżym skanem: nadal 300/1800 s.
Nie zmieniamy budżetów, kolejności źródeł ani historycznych rozliczeń Geoapify.
Geoapify pozostaje źródłem obserwacji commercial, nie pełnym fallbackiem gry.

## Wdrożenie i odbiór

Aktualizacja v2 została zaakceptowana przez operatora po analizie kompletnej
odpowiedzi Paryża. Reload poniższego profilu ecosystem ustawia wersję v2.
Pozostawiona wersja v1 nie aktywuje nowej selekcji. Exact cache i dokładny
world reader pozostają bez zmian; wyników regionalnych nie zapisujemy jako
nowych odpowiedzi exact ani nie odnawiamy wieku snapshotów.

Regresja zapisanej próbki Paryża daje pozycje 48.861/2.338 (479 obiektów)
i 48.861/2.3378 (465 obiektów), przed limitem gry 60. Jest to dowód offline,
nie potwierdzenie aktualnej świeżości na VPS. Nie ponawiać zużytej operacji
compact-v3, nie zmieniać timestampów w bazie. Można odtworzyć wynik bez sieci:
`python tools/world_paris_positions.py <katalog-zapisanej-diagnostyki>`.
Nowe pobrania odbiorowe nie zostały automatycznie zatwierdzone przez zmianę
kontraktu. Normalny kolektor i skaner działają w istniejących budżetach.

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

### Wynik v2 na VPS i analiza zapisanego capture

Operator przekazał `instance/provider-captures/paris-poi-v2`. Nagłówki:
X-Returned=1000, X-Has-More=true, X-Usage-Units-Charged=12. Operacja
rozliczona, completeness=partial, reasons=[truncated], world_published=false.
SHA-256 body: e2d4b27b1883d5001625cec5db71479b8ac7565e85c7b337e4f7026f7059cc66.

Analiza offline: 1000 Point, brak LineString/Polygon/MultiPolygon w otrzymanej
części. Nie dowodzi to braku takich obiektów w regionie. 999 punktów przecina
pierwotny bbox; jeden leży poza nim. Nie wykorzystujemy częściowej odpowiedzi
do wyznaczenia kompletnego pustego regionu ani do certyfikacji podobszarów.

Rozważany mniejszy bbox [2.3335,48.858,2.3425,48.864] obejmuje 478 otrzymanych
punktów. To dolna granica, nie prognoza całkowitego wyniku ani dowód, że zmieści
się w limicie 1000. Nie wykonano nowego HTTP, nie zmieniono limitów ani flag.
Ponowne płatne pobranie wymaga osobnego zatwierdzenia; v2 nie wolno resetować.

### Zatwierdzony mniejszy bbox v3

Operator zatwierdził jedno pobranie [2.3335,48.858,2.3425,48.864], pełny filtr,
limit 1000, bez klipowania. Uruchomienie po push/pull:
`bash tools/world_paris_region_acceptance.sh --compact-v3`.
Stałe ID `region:paris-poi-1635-compact-v3`, osobna rezerwacja 20 w istniejącym
budżecie konta. Koszty i operacje v1/v2 pozostają bez zmian. Nie gwarantujemy,
że mniejszy bbox mieści się w limicie; niepełny wynik nadal nie jest publikowany.
Zachowujemy diagnostykę v2, backup i blokadę ponownego HTTP.

Przy acceptance_ready=true użyć dwóch zwróconych positions do skanów 300 m
w ciągu 5 minut. Przy false lub błędzie przekazać raport bez ponawiania.
8 testów lokalnych PASS obejmuje zgodność bbox w planie, parametrach żądania
i opublikowanym observation_context, zachowanie kosztu v2 oraz brak ponowienia.

### Odebrana v3: kompletność PASS, regionalny odczyt FAIL

826 obiektów, X-Has-More=false, koszt 11 rozliczony. Snapshot na VPS zapisany.
Lokalny capture: instance/provider-captures/paris-poi-v3. SHA-256 body:
2d62d5317470f7db5897499884bf5e491a679afab3b495427a6bfe593e215441.
706 Point, 2 LineString, 116 Polygon, 2 MultiPolygon.

`python tools/world_paris_positions.py instance/provider-captures/paris-poi-v3`
odtwarza 16 regional_circle_not_contained i 9 regional_boundary_ambiguous.
To offline analiza geometrii, nie odnowienie świeżości ani zaliczenie VPS.
Raport odbioru odtąd zawiera position_rejections zamiast samego pustego positions.
9 testów PASS, bez nowych wywołań dostawcy.

Dodatkowe przeszukanie offline 2585 punktów (siatka metrowa, środek
48.861/2.338, dx=-23..23 m, dy=-27..27 m) dało maksymalny odstęp geometrii
od promienia 300 m około 1.4795 m. Kandydatów powyżej wymaganego 5 m: zero.
Ranking używał projekcji ustalonej w środku, pięć najlepszych punktów sprawdzono
ponownie produkcyjnym select; wszystkie dały regional_boundary_ambiguous.
Nie jest to dowód niemożliwości dla każdego punktu ciągłego obszaru.

Nie pobieramy następnego bbox wyłącznie w poszukiwaniu PASS. Potrzebna jest
decyzja o docelowym kontrakcie selekcji w gęstym mieście: obecny wariant
konserwatywnie odrzuca cały skan przy dowolnym obiekcie w pasie 5 m. Ewentualny
deterministyczny profil geometrii CHAOS musi być jawnie wersjonowany, testowany
i opisany jako własna selekcja, bez zapewnienia pełnej zgodności radius dostawcy.
Nie zmieniono reguły produkcyjnej ani jej marginesu w tym pakiecie.

Lokalny PASS nie jest odbiorem VPS. Ten pakiet dostarcza runtime regionalnego
MapLark; nie zamyka automatycznie pełnej kwalifikacji Geoapify, dostępności VK
ani wszystkich A01–A12. Zachowujemy istniejące dowody; nowych nie deklarujemy
bez wykonania. Nie nazywamy UNKNOWN globalnym certyfikowanym pokryciem.
