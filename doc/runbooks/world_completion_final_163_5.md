# 163.5 — końcowy pakiet wdrożenia, 28.10.2026

Ten pakiet zastępuje poprzednie instrukcje aktywacji dla obecnej konfiguracji.
Wymaga już działającego `world_maplark_region` i kolektora `regular_halo`.
Nie uruchamia ponownie Paryża ani nie przywraca VK na pierwsze miejsce.
Odbiór dwóch przesuniętych skanów regionalnych na różnych workerach pozostaje PASS.

## Zmiana działania

- Archiwum geometrii zachowuje retencję 7 dni. Dane skanera mają nadal świeżość
  300 s i dopuszczalny stale do 1800 s. Archiwum nie staje się wiecznie świeżym skanem.
- Pełny regionalny profil POI MapLark może być pobrany ponownie po co najmniej
  godzinie od poprzedniego sukcesu, jeżeli po nim pojawiła się nowa bezpośrednia
  wizyta lub skan. Sam restart, upływ godziny ani halo nie wystarczają.
  Godzina jest minimalnym odstępem, nie gwarantowanym terminem wykonania.
- Nadal maksymalnie 1 próba sieciowa/cykl, odstęp 60 s, priorytet gracza,
  wspólna księga i dotychczasowe limity. Podlimit tła MapLark i Geoapify wynosi
  po 200 kredytów/dzień. Panel i monitor pokazują go osobno od limitu konta.
- Import lokalnego, przypiętego produktu Natural Earth 5.1.1 zachowuje wersję,
  pochodzenie i zależności. To jeden regionalny produkt ląd–morze w skali
  1:10 mln, nie dokładna linia brzegowa OSM ani źródło skanera. Import nie pobiera
  danych i nie kosztuje kredytów. Powtórzenie istniejącego importu nie odnawia dat.

## Jedno wdrożenie

Po pushu lokalnego commita wykonaj na VPS:

```bash
cd ~/app/chaos &&
git pull --ff-only &&
bash tools/world_completion_acceptance.sh preflight &&
bash tools/world_completion_acceptance.sh deploy &&
bash tools/world_completion_acceptance.sh post
```

`preflight`: 210 testów na izolowanych bazach, plan importu offline, inspekcja
integralności/FK, schematu, metryk i PM2. Zero diagnostycznych zapytań do dostawców.

`deploy`: ponowna kontrola stanu, spójny backup przed importem, publikacja lokalnego
produktu oraz reload `ecosystem.web.config.js --env world_maplark_region` i
`ecosystem.discovery.config.js --env regular_halo`. Sekrety już działających
procesów pozostają w PM2; nie trzeba wpisywać ich ponownie. Kolektor po reload
kontynuuje zatwierdzoną politykę i może normalnie pobierać dane.

`post`: inspekcja read-only, monitor i kontrola HTTP 200. Każdy etap wypisuje
osobny katalog raportów `~/chaos-world-completion-*` oraz zapisuje commit.
Brak zgodności preflight zatrzymuje etap przed importem/reload.
Brak świeżej polityki lub kluczy jest błędem konfiguracji, nie powodem resetu księgi.

Oczekiwane: testy OK, `imported_verified` z `local_state=COMPLETE_FRESH`
(lub `already_imported` przy powtórzeniu), `baseline_matches`, HTTP 200.
W panelu World Discovery widać wyjaśnienie retencji oraz osobny budżet tła.
Po poprawnym sprawdzeniu:

```bash
pm2 save
```

## Zbiorczy odbiór działania

1. Zachowujemy wcześniejsze dowody: exact-world, wizyty, halo, regionalny
   MapLark na dwóch workerach oraz zgłoszony przez operatora poprawny skan,
   hakowanie i terytoria na starym i nowym koncie. Nie powtarzamy płatnego Paryża.
2. Podczas normalnej gry wykonaj jeden skan i sprawdź wynik. Fallback upstream
   jest poprawny przy braku świeżego, pełnego regionu; nie jest dowodem world hit.
3. Po jednym naturalnym cyklu kolektora zbierz razem:

```bash
cd ~/app/chaos
.venv/bin/python tools/world_collection_monitor.py
pm2 logs chaos-world-discovery-worker --lines 15 --nostream
pm2 logs chaos --lines 100 --nostream 2>&1 | grep -E 'poi_maplark_region|poi_route|poi_scan'
```

   `waiting/idle` jest dopuszczalne bez nowego popytu. `committed` potwierdza
   publikację; powtarzający się ten sam region bez nowego popytu wymaga sprawdzenia.
   `*_background_scope_exhausted` oznacza osiągnięcie podlimitu tła, nawet jeśli
   całe konto ma środki. Nie zwiększamy automatycznie limitów.
4. Godzinne odświeżanie, restart, cofnięcie uprawnień i brak sieci przy dwóch
   przesuniętych skanach sprawdzają testy deterministyczne. Nie trzeba czekać
   na VPS godzinę ani kasować cache/receipt, aby wymusić ten scenariusz.

Granice źródeł: MapLark geometry-v2 obsługuje skaner; Overpass wyłącznie według
aktualnych praw i zdrowia; Geoapify commercial to archiwum obserwacji POI, nie
pełny zamiennik skanu. Kwalifikacja pełnego Geoapify pozostaje otwarta — obecny
materiał nie dowodzi pełnej geometrii, wszystkich kategorii i kompletności.

## Monitoring i rollback

Cele obserwacji: poprawny heartbeat (bez przekroczenia jego expires_at), zero
naruszeń budżetu i p95 lokalnego odczytu poniżej 2 s. Ocena czasu wymaga minimum
20 próbek w oknie dobowym; dwa wcześniejsze szybkie skany nie dowodzą p95.
Brak próbek/limitu/zdrowego dostawcy raportujemy oddzielnie od błędu systemu.
Naturalna obserwacja 7 dni biegnie po wdrożeniu, nie wymaga kolejnych probe.

W razie regresji kolektora: `pm2 stop chaos-world-discovery-worker` zatrzymuje
nowe cykle, pozostawiając działający skaner. Zachowaj raporty i przygotuj revert
commita tego pakietu, następnie reload tych samych profili. Nie cofaj całej bazy
na działającej produkcji: backup sprzed wdrożenia nie zawiera późniejszych opłat.
Nie usuwaj historycznych rezerwacji Geoapify. Import Natural Earth nie jest
routowalny, więc nie trzeba go usuwać, aby zachować skaner.

Pełny status: kod tego pakietu i testy lokalne gotowe; wdrożenie/odbiór tych zmian
czekają na powyższe raporty. Nie oznaczamy niezweryfikowanego Geoapify jako PASS.
