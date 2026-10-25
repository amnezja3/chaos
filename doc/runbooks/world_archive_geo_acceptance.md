# Odbiór archiwum i przygotowanie Geoapify — 161–163

Operator zaakceptował 25.10.2026 następny etap: retencja geometrii 7 dni oraz
jeden test kolektora Geoapify z rezerwacją 5 kredytów. Wcześniejsze nierozliczone
operacje pozostają zachowane. Nie oznacza to automatycznej aktywacji źródła,
rutingu ani ciągłego pobierania.

## Kod → wdrożenie → zbiorczy test

Na VPS:

```bash
cd ~/app/chaos &&
git pull --ff-only &&
bash tools/world_archive_geo_acceptance.sh
```

Nie wymaga restartu, kluczy API, migracji ani `pm2 save`. Zmiany tego pakietu
obejmują diagnostykę, testy i instrukcje; działający skaner pozostaje bez zmian.

Pakiet sprawdza na izolowanych bazach: publikację przez worker z retencją 7 dni,
ponowne otwarcie repozytorium, wygaśnięcie dostępności dla skanera po 30 minutach,
zachowanie archiwum do jego terminu oraz usunięcie bez osieroconych rekordów.
Upływ czasu jest symulowany w testach, nie zmieniamy zegara VPS ani terminów danych
produkcyjnych. Testy Geoapify i routingu używają atrap transportu.

Raport produkcyjny powstaje z tymczasowej, spójnej kopii SQLite, źródło otwierane
jest przez `mode=ro`. Nie zmienia ledgerów, snapshotów, uprawnień, kolejek, tras
ani PM2. Pokazuje:

- faktyczne brakujące uprawnienia MapLark/Geoapify i termin ich przeglądu;
- aktywne okna budżetu oraz zachowane nierozliczone operacje;
- blokadę przeniesienia nierozliczonych kosztów ze starego okresu;
- zapisane lub domyślne trasy, także celowo puste, i powody pominięcia źródeł;
- rzeczywiste rekordy dłuższej retencji.

`PASS` skryptu oznacza przejście testów i wykonanie raportu. Nie oznacza, że lista
`blockers` jest pusta ani że endpoint działa. `execution_authorized=false` jest
celowe: sam raport nigdy nie udziela zgody na zapytanie.

## Następny krok po raporcie

Na podstawie aktualnego rejestru przygotowujemy jeden ograniczony permit
Geoapify oraz budżet uwzględniający poprzednie rezerwacje. Nie zwiększamy starego
okna diagnostycznego, nie zerujemy 20 kredytów i nie wnioskujemy o koszcie
pojedynczego zapytania z sum w panelu dostawcy. Brak potwierdzonego kosztu nowego
zapytania zachowa pełną rezerwację 5 kredytów.

Geoapify zbiera obserwacje `commercial` / Point; nie zastępuje pełnego skanu
CHAOS, geometrii dróg ani dowodu pokrycia regionu. Po raporcie technicznym nadal
pozostają osobne etapy aktywacji routingu i ciągłego kolektora. Nie powtarzamy
udanego trzylayerowego pobrania MapLark tylko dla odtworzenia PASS.

Retencja 7 dni dotyczy nowej, jawnie dopuszczonej publikacji archiwalnej;
bieżący pakiet nie przedłuża już wygasłych snapshotów i nie zmienia świeżości
skanera (300/1800 s). Nie oznacza bezterminowego archiwum ani certyfikacji regionów.
