# Identity Gateway i POI / Overpass — UX, 26.10.2026

## Zmiany

- Wspólny, ograniczony do tych paneli styl: sekcje zwijane natywnym `details`,
  nagłówki i podpowiedzi, karty statusów, formularze dopasowane do szerokości.
- Identity: osobno stan usług, potwierdzenie operatora, SMTP/test dostarczania,
  wyszukiwanie połączeń, historia oraz usunięcie własnego konta operatora.
  JSON zastąpiony tabelami z pustymi stanami i datami. Komunikaty przy operacji,
  bez powielania powiadomień toast w administracji.
- POI: hierarchia, archiwum, dostawcy, edycja, zakres użycia oraz historia.
  Edycja i zakres otwierają odpowiedni formularz, wypełniają go i przenoszą fokus.
  Szczegóły endpointu i dowodów pozostają dostępne po rozwinięciu karty.
- Usunięty nieprawdziwy wniosek „tło wyłączone” na podstawie flagi skanera.
  Stan procesu kolektora nie jest potwierdzany przez ten endpoint panelu.
- Statystyki źródeł bez JSON-a, statusy i zakresy z opisami PL/EN, tytuły kart
  przeglądarki odpowiadają otwartemu panelowi.

Bez zmian backendu, uprawnień, limitów, routingu produkcji i flag wieku.

## Weryfikacja

Izolowane serwery `tools/poi_admin_fixture.py --routing --world` oraz
`tools/identity_gateway_browser_fixture.py`; Playwright MCP, 1440×1000 i 390×844.

- POI: odświeżanie, edycja i zapis nazwy testowego źródła, wypełnienie zakresów,
  odrzucenie powtórzonego źródła w kolejności, zapis i przywrócenie kolejności,
  rozwinięcie atlasu, odczyt szczegółów obserwacji, PL/EN.
- Identity: wyszukiwanie konta, zapis konfiguracji po reautoryzacji, obsługa błędu
  SMTP przy przycisku, stan globalnych przełączników i dostawców, PL/EN.
- Tabele Identity z niepustym kontraktem odpowiedzi sprawdzone przez przechwycenie
  odpowiedzi testowej w Playwright z zachowaniem nagłówków sesji. Tekst zawierający
  znacznik `img` pozostał tekstem; nie utworzono elementu HTML.
- Brak poziomego overflow dokumentu na obu szerokościach. Oglądnięte zrzuty ekranu.
- Brak błędów JavaScript. W fixture Identity: 404 favicon oraz oczekiwana odpowiedź
  błędu API podczas próby SMTP bez konfiguracji; nie są błędami renderowania.
- Istniejące testy: Identity Gateway 15, POI admin 4, World dashboard 13 — PASS.

## Wdrożenie

Po push/pull restart wyłącznie procesu web (zmienione szablony są cache'owane).
Nie wymaga migracji ani restartu kolektora. Odświeżyć stronę administracji;
wersje adresów zmienionych skryptów zaktualizowane.
