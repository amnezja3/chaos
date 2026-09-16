# Panel administracyjny — układ i odczyty na żądanie

Stan lokalny 16 IX 2026. Zakres zamówiony przez autora po odbiorze poprawki
zmiany profesji. Bez nowego sprintu, migracji ani działań na produkcji.

## Układ

Wspólny `admin_base.html` i `admin_panel.css`: nagłówek 70 px, cztery sekcje
Użytkownicy / Terytoria / Podatności / Zgłoszenia błędów. Paleta i podział
paneli nawiązują do archiwum transmisji GhostSignal (transmission.html,
ghost_signal_archive.css) i istniejącego Bug Reports. Bez animacji show,
globalnego CSS pulpitu i danych logowania w nagłówku.

JSON zastąpiono listami, tabelami i opisami pól. Zgłoszenia zachowują filtry,
edycję statusu i pełny eksport TXT; kontekst ma zagnieżdżone pola opisowe.
Użytkownik ma sekcję zarządzania z obecną zmianą profesji, przygotowaną do
dodawania dalszych rzeczywistych akcji bez fikcyjnych przycisków.

## Kontrakt danych

- `/admin` renderuje wyłącznie szkielet; nie wywołuje list_profiles.
- `/api/admin/panel/list`: strona do 50 rekordów + jeden rekord wykrywający
  kolejną stronę, filtr do 100 znaków, offset ograniczony do miliona.
- Lista kont: użytkownicy + identity projection; brak profili i inventory.
- `/api/admin/panel/user?username=…`: identity integrity gate i wąski odczyt
  wybranego konta z identity/capability, wallet, pozycji i storage; bez credentials.
- Zasoby wybranego konta pobierane dopiero po wybraniu kategorii: aplikacje,
  tools, pliki danych, operacje, przejęte cele. Projekcje SQL zamiast pełnych
  app_json/operation_json/file_json. Security to istniejąca bounded projection.
- Terytoria i podatności mają osobne strony, bez hydratacji profili właścicieli.
  Lista podatności obejmuje również historyczne statusy, pokazane w kolumnie.
- Każdy endpoint wymaga admina. Zmiana profesji zachowuje katalog klanu,
  guarded write/CAS, session generation i Ghost epoch. Brak nowego wyjątku.
- `/api/admin/dashboard` pozostaje kompatybilnym adresem diagnostycznym, lecz
  zwraca lekką pierwszą stronę użytkowników; nie zwraca już agregatu profili/świata.
- Usunięto niewykorzystywany renderer kart z raw_profile i blokami JSON.
- Liczniki żądań frontendowych odrzucają spóźnione listy/szczegóły/zasoby
  po zmianie wybranego użytkownika lub kategorii.

## Walidacja

16 testów Python PASS: leniwe endpointy na profilach ≥35 MiB obu kont,
paginacja, filtr, separacja zasobów, autoryzacja, brak sekretów/profili w HTML,
wszystkie kategorie zasobów, profesje i Bug Reports. Test JS PASS: tylko lista
na starcie, A→B ze spóźnionym A, zasoby dopiero po kliknięciu, zapis profesji
dla właściwego konta. Składnia JS i diff check PASS.

Browser runtime zgłosił brak dostępnych przeglądarek (lista pusta). Nie wykonano
wizualnego odbioru ani pomiaru czasu renderu w przeglądarce. Po wdrożeniu odebrać
układ desktop/mobile, wybór kont, profesję, zakładki zasobów i zgłoszenia.
