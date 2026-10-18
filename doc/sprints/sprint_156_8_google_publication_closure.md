# 156.8 — zamknięcie publikacji dokumentów i publicznego Google OAuth

Status: **ZAMKNIĘTE / PASS**, 18 października 2026, na podstawie odbioru operatora: „mamy pass google działa już dla wszystkich userów publicznie”.

Numer 156.8 zachowano zgodnie z poleceniem operatora dla zamykanego etapu publikacji. Implementacja Identity Gateway i wcześniejsze dowody znajdują się w Sprincie 157. Ten odbiór nie zamyka odrębnego zakresu 157.8 dotyczącego polityki wieku i bezpieczeństwa komunikacji.

## Zakres odbioru

- Operator potwierdził PASS Google oraz publiczne działanie logowania, poza ograniczeniem do kont testowych. Nie wykonywano niezależnego odczytu panelu Google Cloud.
- Dokumenty prywatności i regulamin PL/EN zostały dopracowane; publiczna dostępność HTTP 200 i linki bramy sprawdzone w Playwright. Źródło szczegółów: [raport gotowości](../audits/google_publication_readiness_20261018.md).
- Wynik diagnostyki VPS przekazany przez operatora: losowanie miasta bez dotychczasowego ip-api, obecna blokada Mistrala, wszystkie cztery procesy online, uruchomione po zmianie plików i we właściwym katalogu. Odblokowanie Mistrala wyłączone.
- Polityka wieku bez aktywacji: we wszystkich czterech procesach `CHAOS_ADULT_POLICY_ENABLED=0`. Cztery akceptacje `157-v1`, bez oświadczeń wieku. Nie wywodzimy z tego obowiązywania progu 13+, 16+ ani 18+.

## Zadania pozostające poza zamkniętym etapem

- Pilne uregulowanie umów i ról administratora CHAOS, DMD Inwestycje oraz cyber_Folks. Status wyłącznie administracyjny. PASS Google nie potwierdza zgodności z RODO.
- Osobne zatwierdzenie i wdrożenie zasad 16+ oraz zabezpieczeń komunikacji w 157.8.
- Osobna decyzja o ewentualnym odblokowaniu Mistrala; ZDR pozostaje niepotwierdzone.
- Wcześniejsze nieodebrane scenariusze instalacji Linux/iOS nie otrzymują PASS na podstawie odbioru Google.

Nie zmieniono kodu aplikacji, flag ani konfiguracji dostawców podczas zamknięcia dokumentacyjnego.
