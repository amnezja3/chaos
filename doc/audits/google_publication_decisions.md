# Domknięcie prywatności CHAOS — decyzje i wdrożenie

2026-10-18, propozycja `157-legal-proposal-6`, bez publikacji i zmian produkcyjnych.

## Zrealizowane decyzje

- Usunięto zapytanie ip-api.com. Rejestracja korzysta z istniejącego losowania miasta i nadal omija kontrolowane terytoria. 8 testów PASS.
- Cała wysyłka narracji do Mistrala jest domyślnie zablokowana w routerze i adapterze. Istniejąca ścieżka przechodzi na lokalną Ollamę, a jej awarie obsługuje dotychczasowy bezpieczny fallback. 31 testów PASS, w tym brak wywołania zewnętrznego wykonawcy i pojedyncza publikacja. GET listy modeli może pozostać dostępny, bez pakietu gracza.
- Przygotowano [ręczną procedurę usuwania](privacy_manual_erasure.md) i narzędzie redakcji. 2 testy PASS, w tym odtworzenie kopii i ponowne usunięcie. Nie usunięto danych produkcyjnych.
- [Polityka PL/EN](../proposals/chaos_privacy_PL_EN.md) i [Regulamin PL/EN](../proposals/chaos_terms_PL_EN.md) pozostają projektami do zatwierdzenia. Nie aktywowano polityki wieku.

## Mistral: co wiemy

Operator potwierdza płatny plan API i model `mistral-small-latest`. Wyłączenie trenowania na danych API i wyłączenie Labs potwierdzone w panelu. ZDR pozostaje niepotwierdzone; nie deklarujemy braku retencji. Domyślna lokalizacja UE nie wyklucza określonych transferów poza UE. Potwierdzenie ustawień nie zwalnia automatycznie blokady wysyłki. Nie wysyłamy testowej narracji do dostawcy.

[Warunki komercyjne](https://legal.mistral.ai/terms/commercial-terms-of-service/) rozróżniają zasady trenowania i wyjątki, m.in. feedback oraz Labs/Preview. [Polityka prywatności](https://legal.mistral.ai/terms/privacy-policy/) opisuje standardową retencję wejść/wyjść stateless API do monitorowania nadużyć (30 dni, z wyjątkami, w tym ZDR). [ZDR](https://docs.mistral.ai/admin/monitor-comply/zero-data-retention) jest odrębny od opt-out trenowania. Sam płatny plan nie dowodzi konfiguracji tych opcji.

[DPA](https://legal.mistral.ai/terms/data-processing-addendum/) dopuszcza transfery z odpowiednimi zabezpieczeniami. [Informacja o lokalizacji](https://help.mistral.ai/en/articles/347629-where-do-you-store-my-data-or-my-organization-s-data) opisuje domyślne przetwarzanie w UE i warianty usług. Nie dowodzi to przetwarzania wyłącznie w EOG w każdym przepływie. Dopasowanie umowy i ustawień do konta pozostaje konieczne przed odblokowaniem Mistrala. Blokada nowych wywołań nie usuwa wcześniej wysłanych danych.

## Krótka lista przed publikacją

1. Wdrożyć i potwierdzić działanie przygotowanych zmian: brak ip-api, blokada Mistrala oraz dostępność procedury dla operatora. Obecny kod lokalny nie zmienia uruchomionych procesów VPS.
2. Operator zatwierdza końcowe teksty i datę obowiązywania. Przy publikacji usunąć oznaczenia projektu i zdania warunkowe o niewdrożonych zmianach dopiero po ich potwierdzeniu. Nie publikować automatycznie.
3. Umowa cyber_Folks nadal niezawarta, w przygotowaniu; rozliczyć powierzenie osobno. Dokumenty nie zastępują umowy. Potwierdzenie Mistrala jest warunkiem jego ponownego uruchomienia, a nie wymogiem budowy kolejnej funkcji ani obowiązkowego ZDR od Google.

Po publikacji: sprawdzić publiczne PL/EN `/privacy`, `/terms`, kanoniczną domenę https://chaos.re i ponownie zgłosić markę w Google. Nie zmieniono statusu OAuth. Akceptacja przez Google zależy od ich oceny, nie gwarantujemy wyniku.

## Wdrożenie blokady AI

Po pobraniu zatwierdzonego kodu ustaw `CHAOS_MISTRAL_DATA_REVIEW_APPROVED=0` w trwałej konfiguracji uruchamiania. Brak zmiennej również blokuje wysyłkę. Zrestartuj procesy CHAOS korzystające z nowego kodu; stary proces może nadal wykonywać zewnętrzne wywołania.

```bash
CHAOS_MISTRAL_DATA_REVIEW_APPROVED=0 pm2 restart chaos chaos-ollama-worker chaos-narrative-publisher chaos-territory-worker --update-env
```

Nie ustawiaj `1` do czasu osobnego zatwierdzenia przeglądu ustawień i warunków. Nie zmieniaj istniejących flag wieku/OAuth. Zmiany nie wymagają migracji schematu. Procedura usuwania jest wykonywana wyłącznie dla zweryfikowanej sprawy; wdrożenie nie uruchamia kasowania.

## Osobny backlog

Automatyzacja porządkowania danych i obsługi spraw; dodatkowa minimalizacja promptów; lokalne biblioteki map zamiast CDN; dalsze testy odtwarzania różnych danych produkcyjnych; osobne uruchomienie ochrony komunikacji i 16+. Nie są to automatyczne wymagania Google. Test odtworzenia izolowanego przypadku jest już wykonany.

Weryfikacja propozycji 6: Playwright MCP, osiem wariantów /privacy i /terms (PL/EN, 1440 i 390 px): HTTP 200, prawidłowy język, brak poziomego przepełnienia, przełącznik języka działa, brak błędów JS i konsoli. Test używa parametru locale zgodnego z aplikacją. Przeglądarka i lokalny serwer zamknięte. 41 testów Python PASS (31 Mistral, 8 spawn, 2 usuwanie).

Status umów powierzenia pozostaje wyłącznie w dokumentacji administracyjnej. Publiczna polityka opisuje faktyczny hosting i odbiorców danych. Weryfikacja Google nie potwierdza zgodności z RODO ani nie zastępuje uregulowania umów.
