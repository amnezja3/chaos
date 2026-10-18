# Ręczna obsługa usunięcia danych CHAOS

Procedura operatora, 2026-10-18. Nie jest automatycznym kasowaniem całej historii świata. Kanał: year2108@chaos.re. Wykonawca: operator CHAOS. Bez wysyłania dokumentów tożsamości, haseł i kodów w zgłoszeniu.

1. Zapisz datę odbioru, identyfikator sprawy, zakres żądania i termin odpowiedzi. Potwierdź kontrolę nad kontem istniejącym mechanizmem ponownego uwierzytelnienia; sam nick w e-mailu nie wystarcza. Przy utracie dostępu wyjaśnij sprawę indywidualnie, nie usuwaj konta na podstawie niepotwierdzonego maila. Odpowiedź zasadniczo w ciągu miesiąca; uzasadnione przedłużenie wymaga powiadomienia w tym terminie.
2. Ustal zakres: zamknięcie konta czy usunięcie określonych danych. Dla zamknięcia użyj istniejącego `/api/account/delete` przez interfejs Identity i świeże potwierdzenie tożsamości. Nie zastępuj tego samym SQL DELETE: endpoint usuwa powiązania i unieważnia sesję. Administrator potwierdza własną tożsamość przy obsłudze innego konta.
3. Przejrzyj pozostałe kopie wiadomości, publikacje, zdarzenia świata, zgłoszenia, pliki i korespondencję. Narzędzie `tools/privacy_redact.py --inventory` szuka dosłownych identyfikatorów w bazie, zwracając tylko lokalizacje i liczby. Nie wykrywa wszystkich aliasów, zakodowanych danych, hashy ani plików. Brak trafień nie dowodzi anonimizacji. W sprawie odnotuj osobno dane usuwane, ograniczane i zachowane wraz z konkretną potrzebą. Historia świata nie uzasadnia bezterminowego zachowania wszystkich danych.
4. Na prywatnej kopii roboczej przygotuj plan redakcji treści. Nie zmieniaj kluczy, właścicieli, sald, PvP ani odwołań do kont w ciemno. Narzędzie obejmuje wyłącznie wskazane pola treści wiadomości, zdarzeń i zgłoszeń; pozostałe trafienia wymagają indywidualnej obsługi. Hash wycofanego dostawcy i blokada ponownego użycia nazwy pozostają danymi wymagającymi oceny, nie anonimowymi statystykami.
5. Po sprawdzeniu planu wykonaj dry-run i apply. Wynik `content_changed_review_again` oznacza ponowny przegląd, nie wymianę hasha bez czytania. Cały plan jest transakcyjny. Nie uruchamiaj operacji na produkcji bez sprawdzonej kopii bezpieczeństwa i uzgodnionego zakresu sprawy.

Przykład prywatnego pliku sprawy (poza Git, uprawnienia tylko operatora):

```json
{
  "case_id": "ERASURE-YYYY-NNN",
  "username": "konto",
  "reason": "Zweryfikowane żądanie; usunięcie adresu z kopii wiadomości",
  "search_terms": ["adres@example.test", "konto"],
  "redactions": [{
    "table": "chat_messages",
    "id": 123,
    "column": "body",
    "expected_sha256": "SHA256 dokładnej aktualnej treści w UTF-8",
    "replacement": "[dane osobowe usunięte]"
  }]
}
```

Hash oblicza `tools.privacy_redact.digest(tekst)`; pobierz tekst parametryzowanym odczytem wskazanego rekordu w prywatnej sesji operatora. Nie wklejaj oryginalnej treści do ticketów publicznych lub logów. Przy JSON zachowaj poprawną strukturę i pozostałe potrzebne pola. Pusty plan nie wymaga uruchamiania redakcji.

```bash
.venv/bin/python tools/privacy_redact.py --db data/game.sqlite3 --case /prywatna/sciezka/sprawa.json --inventory
.venv/bin/python tools/privacy_redact.py --db data/game.sqlite3 --case /prywatna/sciezka/sprawa.json
.venv/bin/python tools/privacy_redact.py --db data/game.sqlite3 --case /prywatna/sciezka/sprawa.json --apply --confirm-case ERASURE-YYYY-NNN
```

6. Sprawdź wynik i integralność bazy; potwierdź brak dostępu usuniętego konta. Odpowiedz, co wykonano, co pozostało i dlaczego, oraz że kopie zapasowe wygasają po 28 dniach. Nie obiecuj natychmiastowego usunięcia wszystkich kopii. Przy odmowie podaj uzasadnienie i drogę skargi. Sprawę i korespondencję przechowuj tylko w zakresie potrzebnym do realizacji i wykazania obsługi; oceniaj dalszą potrzebę, nie ustanawiaj fikcyjnej retencji.
7. Backupów nie przepisujemy. Przy odtworzeniu utrzymuj usługę offline, ponownie zastosuj usunięcia kont i plany redakcji wykonane po dacie kopii, unieważnij stare sesje odtworzonych usuniętych kont i sprawdź wyniki przed uruchomieniem ruchu. Plan zawiera identyfikatory rekordów i hashe, nie oryginalną treść. Gdy kopia nie zawiera rekordu albo treść różni się, wykonaj ponowny przegląd. Nie pomijaj błędu. Rejestr wykonanych spraw musi przetrwać przywrócenie starszej bazy. Kopie robocze i wdrożeniowe także trzeba objąć potwierdzoną retencją 28 dni.

## Dowód i ograniczenia

`tests/test_privacy_manual_erasure.py`: rzeczywisty endpoint usuwa konto i połączenie Google, blokuje sesję; dane osobowe w kopii odbiorcy i zdarzeniu są redagowane, profil drugiego gracza i odwołania świata pozostają. Test obejmuje dry-run, rollback przy nieaktualnej treści, idempotencję, zakaz zmiany pola strukturalnego oraz odtworzenie kopii i ponowne wykonanie usunięć. Dwa testy PASS na izolowanej bazie.

To dowód działania ścieżki technicznej dla sprawdzonych przypadków, nie potwierdzenie obsługi rzeczywistego e-maila, kompletności dowolnego żądania ani fizycznego wygaśnięcia backupów po 28 dniach. Retencję podał operator. Nie usunięto żadnych kont produkcyjnych.
