# Gotowość CHAOS do publikacji dokumentów Google OAuth

Stan 2026-10-18. Raport przed wdrożeniem, bez zmiany Identity Gateway, statusu Google OAuth ani flag wieku. `CHAOS_ADULT_POLICY_ENABLED=0` ma pozostać bez zmian; nie odczytywano prywatnego środowiska VPS.

## Wynik

Publiczna dostępność: PASS. Gotowość do ponownego zgłoszenia Google: jeszcze nie — produkcja udostępnia stary projekt `157-16-draft-1`, nie przygotowaną propozycję `157-legal-proposal-6`.

Sprawdzono Playwright MCP w niezalogowanej przeglądarce:

| Adres | Wynik |
| --- | --- |
| https://chaos.re/ | Dostępna brama logowania, widoczne odnośniki do obu dokumentów |
| https://chaos.re/privacy?locale=pl | HTTP 200, język PL, bez logowania |
| https://chaos.re/privacy?locale=en | HTTP 200, język EN, bez logowania |
| https://chaos.re/terms?locale=pl | HTTP 200, język PL, bez logowania |
| https://chaos.re/terms?locale=en | HTTP 200, język EN, bez logowania |

Linki bramy używają osadzonego okna dialogowego z iframe. Nie wymagają otwierania konta ani korzystania z OAuth. Bezpośrednie adresy dokumentów pozostają niezależnie dostępne.

Produkcja nadal zawiera brak adresu operatora, nieuzupełnione ustalenia retencji i AI oraz opis aktywnego wymogu wieku. Przygotowana lokalnie wersja podaje potwierdzone dane i wyraźnie rozróżnia planowane 16+ od nieaktywnego mechanizmu. Nie aktywujemy ani nie zmieniamy zasad wieku przez wdrożenie dokumentów.

## Zgodność opisu Google z kodem

Sprawdzono `identity_gateway/providers.py` i przygotowane sekcje polityki: zakresy `openid email`, identyfikator `sub`, adres e-mail i `email_verified`, uwierzytelnienie po stronie serwera. Opis nie obiecuje dostępu do Gmaila, Dysku, Kontaktów ani Kalendarza. Dokument wyjaśnia cel powiązania, odłączenie dostawcy, usunięcie konta, zachowane dane i kontakt do realizacji praw. Nie zmieniano działającej integracji. Nie logowano się na produkcji ani nie sprawdzano panelu Google Cloud; bieżący status Testing/Production nie został ponownie potwierdzony.

## Zakres do wdrożenia po zgodzie

1. Zastąpić stary projekt przygotowanymi dokumentami PL/EN. Przed wydaniem nadać datę obowiązywania, usunąć komunikat o nieobowiązującym projekcie i zmienić zdania warunkowe dotyczące wdrożonych zabezpieczeń na opis faktycznego stanu. Status otwartych umów zachować wyłącznie w dokumentacji administracyjnej. Publiczne dokumenty opisują rzeczywisty hosting, odbiorców i przepływy danych, bez statusu prac nad umowami.
2. Opis braku ip-api i wstrzymanej wysyłki narracji Mistrala wymaga równoczesnego wdrożenia przygotowanych zmian albo potwierdzenia ich obecności na VPS. Sama publikacja tekstu nie wdraża zabezpieczeń. Nie odblokowywać Mistrala w ramach publikacji dokumentów.
3. Zachować Identity Gateway i `CHAOS_ADULT_POLICY_ENABLED=0`. Nie wykonywać migracji wieku ani wymuszać nowych oświadczeń.
4. Po wdrożeniu ponownie sprawdzić cztery publiczne wersje i linki bramy, następnie zgłosić w Google kanoniczne adresy: https://chaos.re, https://chaos.re/privacy, https://chaos.re/terms. Callback pozostaje https://chaos.re/auth/google/callback. Nie zmieniać klienta OAuth.

Lokalna propozycja ma wcześniejsze sprawdzenie ośmiu wariantów PL/EN desktop/mobile, 41 testów zmian prywatności PASS. To nie jest dowód wdrożenia ani akceptacji dokumentów przez Google.

## Pilne zadanie formalne poza wdrożeniem

Umowy powierzenia między administratorem CHAOS, DMD Inwestycje i cyber_Folks pozostają otwarte i wymagają pilnego uregulowania. Nie potwierdzono ich zawarcia ani dokładnego podziału ról i dostępu DMD Inwestycje; nie określamy go automatycznie jako procesora lub administratora. Nie deklarujemy pełnej zgodności prawnej. Zatwierdzenie aplikacji przez Google nie jest potwierdzeniem zgodności z RODO i nie zamyka zadania dotyczącego umów. Publikacja polityki nie zastępuje umów ani ustalenia rzeczywistych ról. Jeśli DMD faktycznie otrzymuje dane lub dostęp, zakres ten musi zostać opisany rzetelnie, bez wymyślania roli na podstawie samej nazwy.

## Decyzja

Oczekujemy zgody operatora na wdrożenie opisanego zakresu. Niczego nie opublikowano, nie zmieniono środowiska VPS ani statusu aplikacji Google. Raport nie gwarantuje wyniku weryfikacji marki.

## Zatwierdzenie treści do publikacji

Operator przeczytał dokumenty i zatwierdził zdjęcie oznaczeń projektu. Wersja 157-legal-1: usunięto baner projektu, wewnętrzne uwagi wdrożeniowe i odsyłacz do oferty technicznej hostingu; dokumenty pozwalają na indeksowanie. Pozostawiono fakty o odbiorcach, retencji, braku potwierdzonego ZDR i nieaktywnym mechanizmie wieku. Status umów pozostaje administracyjny. Playwright lokalnie: 8 wariantów PL/EN desktop/mobile PASS, bez błędów JS/konsoli. Zmiana treści nie potwierdza jej wdrożenia na VPS. Wersję należy wdrożyć razem z już przygotowanym usunięciem ip-api i blokadą Mistrala; sprawdzić po restarcie, zanim ponownie zgłosi się Google. Nie zmieniono Identity Gateway ani flag wieku.

## Kontrola przed publikacją — aktualizacja

Usunięto język audytu z §11 i §13 PL/EN. Nie potwierdzamy nieznanego użycia proxy ani podstaw transferów: ustalenia organizacyjne pozostają otwarte w administracji. Operator potwierdził, że nie ustanawiamy żadnego nowego progu wieku; 13+ było projektem, 18+ nieaktywnym mechanizmem, 16+ kierunkiem przyszłej zmiany. §2 opisuje brak nowego ograniczenia, nie ogłasza gry bez limitu wieku. Kod zwykłej akceptacji 157-v1 nie zawiera progu; 157-16-v1 jest powiązany z flagą. Faktycznie zaakceptowane wersje wymagają odczytu produkcyjnego. Historyczna publiczna wersja 157-16-draft-1 była projektem, sam jej odczyt nie dowodzi akceptacji.

SSH odrzucone przez VPS (publickey,password). Nie potwierdzono aktywności zabezpieczeń na produkcji. Przygotowano tools/privacy_production_check.py: odczyt plików, środowiska uruchomionych procesów i zbiorczych wersji akceptacji, bez sekretów i danych graczy. Uruchomić na VPS: .venv/bin/python tools/privacy_production_check.py. Wynik trzeba ocenić przed publikacją; nie jest śledzeniem ruchu sieciowego. Lokalna kontrola czterech stron PL/EN w Playwright PASS. Bez zmian Identity Gateway i flagi wieku.
