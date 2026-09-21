# Historycznie przejęty filar blokuje odbicie — 403 aim-target

## Potwierdzony przypadek

21 IX 2026: robot nie może oznaczyć ostatniego celu po około 20 poprawnych
hackach. Konflikt `territory_conflict_3212cccd8a589e32` jest active, uczestnicy
main/robot, geometria clean. Cel `map:52.09989:21.06022:POI-6AC002` należy do
main (canonical ownership version 2, 15 IX). Rejestr aktualnego konfliktu
zawiera captured=true, captured_by=main, previous_owner=robot; zagnieżdżony
snapshot zachował stary konflikt `territory_conflict_2dd48c56fc1ffbdd`
i expected_owner_username=robot. Dane odczytane przez autora read-only.

Mapa pokazuje przejęty przez przeciwnika filar jako contested względem widza.
Store capture_pillar obsługuje recapture i idempotencję. Natomiast resolver
contested_targets_from_active_conflicts pomijał wszystkie captured oraz
wszystkie cele, których poprzednim właścicielem był bieżący gracz. Dlatego
aim-target nie odnajdywał celu konfliktu i stosował foreign_territory_protected.
Nie był to brak miejsca w ekwipunku ani błąd sesji.

## Poprawka

Wspólny resolver aim/hack wyznacza aktualnego właściciela z istniejącego
ownership_by_target_id, z fallbackiem do canonical rekordu konfliktu.
Historia captured/previous_owner nie blokuje odbicia aktualnego wrogiego
celu. Zachowane: członkostwo konfliktu/engagement, relacja hostile,
ochrona własnego i klanowego celu oraz zwykłego obcego terenu. Historyczny
captured bez określonego właściciela przejęcia i bez ownership jest odrzucany.
Zwracany cel ma aktualny konflikt, expected_owner i ownership_version;
świeże oznaczenie nie dziedziczy ukończonych actions_allowed poprzednika.

Podczas diagnozy odtworzono drugi, niezależny błąd: canonical filar
podtrzymujący front może leżeć poza overlapem, lecz geometryczny filtr
resolvera odrzucał go jak inner. Wyjątek dotyczy tylko item z rolą pillar
z rejestru aktywnego konfliktu, nigdy flagi klienta ani dowolnego obiektu
z enumeracji obcego klastra. To nie jest potwierdzona przyczyna pozycji POI-6AC002.

Brak migracji/resetu danych i brak nowych odczytów pełnych profili.
Historyczne captured i ledger pozostają niezmienione. Dotychczasowe odczyty
relacji/profile w starszym resolverze nie są w tym hotfixie przebudowywane.

## Walidacja i odbiór

Reprodukcja HTTP: supporting pillar dawał 403 przed poprawką i 200 po niej.
Test historycznego przejęcia z danymi robot/main potwierdza 200, aktualny
conflict_id, owner=main, ownership_version=2 i pusty postęp akcji.
Sprawdzono ochronę własnego celu, klanu, nieuczestnika, inner poza frontem,
sfałszowanego członkostwa i niepełnego historycznego wpisu.
35 testów resolvera/identity/recapture PASS; szerszy zestaw 71 testów
gate/control/map PASS (zestawy częściowo się pokrywają). Naprawiono dwa nieaktualne testy
statyczne: ścieżkę HTML zależną od cwd oraz liczbę handlerów po wcześniejszym
scaleniu obsługi scan markerów (bez zmian frontendowego runtime).

Po wdrożeniu kodu zrestartować web/worker zgodnie z 142.7, odświeżyć mapę,
kontem robot oznaczyć ten sam POI-6AC002 i wykonać końcowy hack.
Oczekiwane: brak 403, canonical przejęcie przez robot i normalne przeliczenie
konfliktu. Nie resetować konfliktu, captured ani ownership ręcznie.
Status: **PASS AUTORA — 21 IX 2026**. Po wdrożeniu 5a0e404 autor potwierdził:
„poszło konflikt rozwiązany bez problemów”. Robot oznaczył i przejął filar;
konflikt zakończył się bez ręcznego resetowania bazy.
