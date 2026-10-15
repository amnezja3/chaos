# 156.4.1 — korekta odbioru instalacji

15 X 2026, lokalnie; wymaga publikacji i wdrożenia.

Zgłoszenie: panel instalacji ściskał formularz logowania w bocznej kolumnie;
ogólna instrukcja menu przeglądarki była niezrozumiała mimo dostępnego prompta.

- Formularz i panel ustawione pionowo, na pełną szerokość prawej kolumny.
- Osobny przycisk „Zainstaluj na tym urządzeniu” korzysta bezpośrednio z eventu
  przeglądarki, niezależnie od heurystycznego rozpoznania platformy.
- Przy dostępnym prompcie komunikat wyjaśnia kliknięcie przycisku; podczas
  instalacji nie pokazujemy równocześnie instrukcji menu.
- Katalogi 156.4.1; publiczne zasoby i cache SW 156-4-1, zgodnie z zasadą
  niewymuszania aktualizacji na otwartych oknach.

10 testów Python installation+i18n PASS, Node izolacji SW PASS.
Chrome/Playwright (MCP niedostępny): PL desktop 1280 i EN mobile 390 PASS,
pełny formularz plus geometryczny test braku nakładania, nowy przycisk z
symulowanym promptem accepted/dismissed, offline, settings i rollback.
Brak błędów JS/nieoczekiwanych błędów konsoli. Bez dowodu instalacji systemowej.
