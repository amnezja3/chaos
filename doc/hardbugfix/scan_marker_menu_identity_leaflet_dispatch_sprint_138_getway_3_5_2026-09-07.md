# Błędna tożsamość menu markerów po dużym skanie

**Sprint:** 138.getway.3.5  
**Data zamknięcia:** 2026-09-07  
**Severity:** P1  
**Status menu:** `RESOLVED — MANUAL SERVER VALIDATION PASSED`  
**Status tooltipów:** `ACCEPTED LIMITATION — PRESENTATION ONLY`

## Problem i wpływ

Po większym skanie kliknięcie jednego markera mogło otworzyć kompletne menu innego
celu. Przykładowo marker Żabki uruchamiał menu Topaza. Menu Topaza było wewnętrznie
poprawne i należało do prawdziwego markera Topaza; błędne było powiązanie
`kliknięta ikona → warstwa obsługująca contextmenu`.

Cele mogły być od siebie oddalone o wiele kilometrów. Wykluczyło to nakładanie
hitboxów jako końcową przyczynę. Ponowienie skanu w tym samym miejscu przenosiło
problem na inne markery, co wskazywało na wyścig lifecycle warstw, a nie wadliwy
rekord POI.

Podatności utworzone z takich wyników dziedziczyły symptom. U właściciela i
sojusznika menu zwykle było poprawne. U intruza początkowo nawet siedem markerów
mogło reagować jak jeden lub otwierać menu z innej ikony, po czym stan stabilizował
się po zakończeniu asynchronicznego odświeżenia publicznych podatności.

Wpływ na gameplay był krytyczny: gracz mógł oznaczyć albo zaatakować inny cel niż
ten, który świadomie wybrał na mapie.

## Warunki reprodukcji

1. Wykonać scan zwracający wiele markerów.
2. Otwierać menu kolejnych markerów, szczególnie przed i podczas odświeżania
   innych warstw mapy.
3. Porównać etykietę klikniętej ikony z nazwą, współrzędnymi i akcjami menu.
4. Powtórzyć scan w tej samej lokalizacji.
5. W wariancie `territory_defense` opublikować rój i natychmiast sprawdzić menu
   jako właściciel, sojusznik oraz intruz.

Wadliwy przebieg nie był deterministycznie przypisany do konkretnego POI. Po
ponownym skanie mógł wystąpić na innym markerze.

## Evidence rozstrzygające

- menu zawierało prawidłową tożsamość odległego celu, zamiast pomieszanych pól;
- błędny marker i cel menu często znajdowały się daleko od siebie;
- zamiana rozmiaru hitboxu nie odpowiadała obserwowanemu przebiegowi;
- `normalizeMapMenuTarget()` tworzył osobny, zamrożony snapshot, a pętla używała
  `const menuTarget`, więc klasyczne współdzielenie zmiennej closure zostało
  wykluczone;
- podatności samoczynnie stabilizowały menu po zakończeniu refreshu warstw;
- kolejne wykonanie skanu zmieniało zestaw błędnych powiązań.

Historyczny wpis z 02.07.2026 wymagał dla każdego interaktywnego obiektu własnego
rejestru, cleanupu, snapshotu, hitboxu i ścieżki menu. Późniejszy cleanup race
został naprawiony w `e0b8a30`, lecz routing nadal pozostawał zależny od callbacku
warstwy wybranego przez Leafleta.

## Root cause

Snapshot danych celu był poprawny, ale nie był ostatecznym źródłem wyboru warstwy.
Natywne zdarzenie DOM trafiało do routera Leafleta, który podczas dużej rotacji
markerów lub równoległego refreshu podatności mógł wywołać callback starej albo
obcej warstwy. Callback następnie legalnie używał własnego, poprawnego snapshotu —
tyle że należącego do innego markera.

Dlatego efekt wyglądał jak błędne dane menu, mimo że faktyczny błąd znajdował się
wcześniej, na granicy `DOM event → Leaflet layer dispatch`.

## Próby naprawy i odrzucone hipotezy

### Nakładające się hitboxy

Pierwsza hipoteza zakładała zbyt duże obszary klikalne markerów. Dodano kontrolę
własności DOM i eksperymentalnie zmniejszono hitbox. Obserwacja markerów oddalonych
o kilometry jednoznacznie wykluczyła tę przyczynę; rozmiary ikon zostały
przywrócone.

### Snapshot przypięty do ikony

Marker i jego element DOM otrzymały własny `_chaosContextBinding` zawierający
zamrożony target, rodzaj źródła i opcjonalny raport podatności. To zabezpieczyło
dane i pozwoliło odzyskać prawidłowy cel z faktycznie klikniętej ikony, ale samo
nie gwarantowało pierwszeństwa przed routerem zdarzeń Leafleta.

### Finalne rozwiązanie

- kontener mapy instaluje jeden delegowany listener natywnego `contextmenu`;
- listener działa w fazie capture;
- przechodzi od faktycznie klikniętego elementu DOM do jego
  `_chaosContextBinding`;
- rozstrzyga marker, target, typ menu i raport podatności przed uruchomieniem
  routingu warstw Leafleta;
- zatrzymuje obsłużone zdarzenie, więc callback obcej lub stale warstwy nie może
  otworzyć drugiego menu;
- callback per marker pozostaje fallbackiem dla zdarzeń syntetycznych;
- ten sam kontrakt obowiązuje markery skanu i publiczne podatności.

## Tooltipy — świadomie pozostawione ograniczenie

Po naprawie menu sporadycznie pozostaje tooltip przypisany przez Leafleta do
niewłaściwej warstwy. Tooltip nie jest źródłem akcji, nie zmienia target identity,
nie przechodzi do aimed target i nie wpływa na hakowanie ani publikację
podatności.

Po manualnym teście dziesięciu kolejnych skanów nie wystąpiło ani jedno błędne
menu. Pozostały symptom tooltipu został zaakceptowany jako defekt wyłącznie
prezentacyjny i nie blokuje zamknięcia `138.getway.3.5`. Jego ewentualna naprawa
powinna być osobnym polish/fixem, bez ponownego otwierania kontraktu realizera.

## Testy i weryfikacja

Automatyczna regresja obejmuje:

- własny zamrożony snapshot każdego markera;
- wybór klikniętego DOM markera mimo callbacku przekazanego dla innej warstwy;
- instalację delegacji `contextmenu` w fazie capture;
- jednakowe zachowanie markerów skanu i podatności;
- frontendowy kontrakt map loadera i hot path markerów;
- brak regresji lifecycle `territory_defense`.

Walidacja lokalna:

- 40/40 testów P5 i mapy — PASS;
- behawioralny test Node routingu menu — PASS;
- `node --check static/js/terminal.js` — PASS;
- `py_compile` — PASS;
- `git diff --check` — PASS.

Walidacja serwerowa:

- dziesięć kolejnych skanów bez błędnego przypisania menu;
- mechanika roju `territory_defense` dla właściciela, sojusznika i intruza
  potwierdzona jako gameplay PASS;
- błędne tooltipy pozostają zaakceptowanym ograniczeniem prezentacyjnym.

## Invariant na przyszłość

```text
tożsamość akcji menu = binding fizycznie klikniętej ikony DOM
tożsamość akcji menu ≠ callback warstwy wybranej przez Leaflet
```

Nie należy naprawiać nawrotu przez powiększanie/zmniejszanie hitboxów, opóźnienia,
ponowne ładowanie profilu ani kopiowanie targetu z tooltipu. Heavy profile i
bounceback nie są źródłem tożsamości menu.

## Powiązane pliki, commity i sprinty

- `templates/map_template.html` — marker binding, capture delegation i menu;
- `tests/js/test_map_target_hitbox.js`;
- `tests/test_marked_target_hot_path.py`;
- `doc/history/project_journal_13082026.md` — historyczny przypadek z 02.07.2026;
- `e0b8a30` — wcześniejszy cleanup race markerów skanu;
- `82177d0` — snapshot DOM i lifecycle roju;
- `9e2edb0` — routing menu przed Leaflet layer dispatch;
- Sprint `138.getway.3.5` — P5 Mirror Kernel / Odbicie.

## Status końcowy

`MENU RESOLVED / 10-SCAN SERVER PASS / TOOLTIP ACCEPTED LIMITATION`
