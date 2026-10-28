# 163.5 — kwalifikacja MapLark po odbiorze fallbacku, 28.10.2026

Stan przyjęty: live POI revision 3, tylko MapLark, sukces upstream. VK po
odblokowaniu przekroczył timeout; jego regionalny odczyt nie został odebrany.
Nie aktywujemy go ponownie tym pakietem. Nie zmieniamy ecosystemów ani budżetów.

## Co rzeczywiście jeszcze trzeba ustalić

1. Czy na VPS są już pełne bbox POI MapLark, czy tylko skany exact i commercial
   Geoapify. Kategorie pełnego profilu: shop, amenity, office, healthcare,
   atm=yes, man_made=surveillance. Brak kategorii w jednym regionie nie oznacza
   braku jej obsługi przez dostawcę.
2. Predykat radius MapLark i reguły kompletności bbox: istniejący profil gry
   powierza selekcję dostawcy. Nie wolno zastąpić go lokalnym przecięciem
   geometrii z okręgiem i nazwać identycznym bez dowodu. Punkt markera to dla
   ways/relations środek bounds, nie dowód przynależności do promienia.
3. Niezależna odpowiedź radius wewnątrz kompletnego bbox, z geometrią i tagami.
   Porównanie jednego wycinka tego samego snapshotu ze sobą nie jest takim dowodem.
4. Geoapify commercial nie odpowiada pełnemu profilowi powyżej. OSM ID i Point
   nie wystarczają do zrekonstruowania pełnych geometrii oraz skanu relacji.

## Jeden pakiet na VPS

Po pushu:

```bash
cd ~/app/chaos &&
git pull --ff-only &&
bash tools/world_poi_evidence_acceptance.sh
```

Bez restartów, migracji, API i zmiany konfiguracji. Testy mają własne bazy.
Eksporter otwiera produkcyjne SQLite przez mode=ro, bada najwyżej 100 ostatnich
kanonicznych snapshotów MapLark/Geoapify i 8 MiB payloadów. Limit czasu SQL 5 s.
Wynik truncated nie uprawnia do wniosku, że starszych danych nie ma.
Wybiera maksymalnie sześć próbek, po jednej dla profilu źródła/selekcji/pozyskania.
Sprawdza digest i dekoduje kontrakt geometrii. Eksport zawiera geografię,
identyfikatory obiektów, markery i sześć tagów klasyfikacji; nie zawiera
kont graczy, kluczy API, nagłówków ani tagów kontaktowych miejsc.
Nie jest surową odpowiedzią dostawcy. Source digest identyfikuje źródłowy
snapshot, export digest identyfikuje ograniczoną projekcję.

Raport zawiera aktywne podlimity, w tym powód możliwego wstrzymania kolektora
mimo wolnego budżetu konta. Nie kasuje rezerwacji ani nie zwiększa limitów.

Wklej report.json. Do lokalnej analizy geometrii skopiuj wskazany katalog
do ignorowanego `instance/provider-captures` (podstaw rzeczywistą ścieżkę):

```powershell
scp -O -r 'johndoe@185.201.114.123:/home/johndoe/chaos-poi-evidence-1635-XXXXXX' '.\instance\provider-captures\'
```

## Dalszy krok po wyniku, bez automatycznego ruchu sieciowego

- Jeżeli istnieje pełne bbox POI, analizujemy tę próbkę i porównujemy z zapisanym
  exact. Hash klucza exact nie pozwala odzyskać środka zapytania; jeżeli brakuje
  metadanych lokalizacji, nie dopasowujemy go na podstawie samych markerów.
- Jeśli brak pełnego bbox, najpierw sprawdzamy bieżący zakres kolektora i jego
  limit. Dostępny jest plan jednej próby `tools/world_region_probe.py --profile poi`.
  Wykonanie wymaga osobnego etapu z jawnym kosztem: maksymalnie jedno HTTP,
  rezerwacja 20 z istniejącego budżetu (nie twardy limit ceny dostawcy).
- Nowy komplet porównawczy radius/bbox dobierzemy dopiero do realnego braku;
  nie ponawiamy historycznych operacji ani nie odświeżamy niepotrzebnie geometrii.
- Dopiero potwierdzony kontrakt lub jawnie zaakceptowany nowy profil gry może
  otworzyć regionalny reader MapLark. Ten pakiet nie wystawia certyfikatu.

Warunek tego etapu: wiemy, jakie próbki i metadane istnieją oraz czego dokładnie
brakuje do porównania. Nie jest to deklaracja zakończenia całego 163.5.
