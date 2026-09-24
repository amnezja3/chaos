# Sprint 148 — kreatory: prosty UX, rozliczenie użycia i pełny odbiór

Status: **ZAPLANOWANY**, 24 IX 2026. Implementacja po PASS 147.
Podstawa: [audyt](../audits/creators_gameplay_audit_2026_09_24.md),
[147 — serwerowy kontrakt](sprint_147_creator_gameplay_policy.md).

## Bramka: zero ciężkiego profilu

Wykryte naruszenie naprawiamy od razu w bieżącym etapie, z testem regresji;
nie odkładamy go do następnego sprintu ani jako długu technicznego.

Obowiązuje [wspólny zakaz ciężkiego profilu](../plans/creator_ghostlab_zero_heavy_profile_contract.md).
Wizard i podgląd używają małych endpointów, nie pełnego `/profile`. Zakup, instalacja,
przycisk, płatność i efekt korzystają z canonical stores i receipts; po wykonaniu
UI odświeża tylko właściwe zakresy. Nie wolno zapisywać ani synchronizować ciężkiego
profilu użytkownika, celu czy twórcy. Odbiór wszystkich czterech kreatorów zawiera
pomiar zero-heavy dla całej ścieżki wraz z middleware, błędami i retry.

## Rezultat

Gracz rozumie, co tworzy, gdzie uruchomi aplikację, co zmieni i jaki otrzyma wynik.
Nie konfiguruje macierzy ryzyka. Cztery kreatory różnią się prezentacją, korzystając
z jednego kontraktu gameplayowego. Opłata za użycie przycisku rzeczywiście trafia
od użytkownika do twórcy, zgodnie z widoczną ceną i bez podwójnych obciążeń.

## 148.1 — skrócona wspólna ścieżka

Docelowe kroki:

1. **Pomysł:** nazwa, ikona, opis, rodzina i konkretny cel aplikacji.
2. **Działanie:** wybór jednego zgodnego profilu/celu; opis startu, efektu i wyniku.
   Jeśli start wynika jednoznacznie z profilu, system ustawia go automatycznie.
3. **Wygląd:** treść charakterystyczna dla kreatora.
4. **Podgląd i możliwości:** zachowany preview oraz czytelne podsumowanie poziomu,
   dostępnego wpływu, warunków, ryzyka i ograniczeń; bez technicznych checkboxów.
5. **Publikacja:** dane katalogowe, sugerowana i zatwierdzona cena zakupu,
   ewentualne ceny użycia, końcowy przegląd i publikacja.

Stan i walidacja pochodzą z katalogu/quote backendu. Zmiana rodziny lub celu usuwa
sprzeczne ustawienia i wyjaśnia zmianę. Niedostępne możliwości mają krótki opis
progu poziomu. Nie pokazywać surowych map_actions, operation_types ani flag.

## 148.2 — gdzie uruchomić i czego oczekiwać

- Nazwy dla gracza: „Z menu obiektu na mapie” i „Z pulpitu na oznaczonym celu”.
  Mapa to miejsce wyboru celu, desktop to okno narzędzia; wyjaśnić to na przykładzie.
- Jeśli profil dopuszcza obie drogi, prowadzą do tego samego executora, warunków
  i ceny. Nie są dwiema osobnymi możliwościami gameplayowymi.
- Każdy profil pokazuje krótko: cel, co zrobi, co powstanie, co może zablokować
  akcję, jakie pozostawia ryzyko. Bez obietnic funkcji nieobecnych w backendzie.
- Brak celu, utrata dostępu, konflikt ustawień, areszt i konfiskata mają spójne
  komunikaty. Podgląd aplikacji nie wykonuje mutacji ani nie pobiera HC.

## 148.3 — cztery formy prezentacji

| Kreator | Kontrola autora | Ograniczenie systemowe |
| --- | --- | --- |
| AppForge | Kroki postępu i treści wyniku | Animacja nie nadaje sukcesu; decyduje backend. |
| Window Maker | Tytuł, lista logów, opcjonalne przyciski | Nazwane akcje z katalogu, bez dowolnych flag; brak przycisków ma jawne zachowanie, bez ukrytego auto-hacku. |
| Button Maker | Tytuł, opis, label, effect, sugerowana price każdej opcji | Effect w profilu/policy; widoczna końcowa opłata za użycie. |
| Term Creator | Wiele par komenda–output | Zachować losowanie pary i animację; komenda jest prezentacją, nie wykonywalnym kodem użytkownika. |

Wariant tekstowy Term Creatora nie losuje ponownie efektu operacji. Treści autora
są bezpiecznie renderowane, a autorytatywny wynik wyraźnie oddzielony od narracji.
Window Maker bez własnych przycisków może być widokiem informacyjnym; sposób
uruchomienia gameplayowego profilu musi pozostać widoczny w podglądzie.

## 148.4 — opłata Button Makera za każde użycie

- Przed kliknięciem widać końcową kwotę HC i odbiorcę; zero oznacza „Bezpłatnie”.
  Cena zakupu aplikacji jest prezentowana osobno.
- Backend pobiera opcję, cenę, autora i efekt z zainstalowanej wersji, nigdy
  z klienta. Nie wolno zmienić kwoty po akceptacji bez ponownego potwierdzenia.
- Jedno zaakceptowane użycie = jeden receipt, jeden transfer, jeden efekt.
  Retry/timeout/reconnect zwracają ten sam wynik. Nowe użycie ma nową tożsamość
  i ponownie podlega cenie, limitom oraz cooldownom.
- Proponowana reguła rozliczenia: odmowa walidacji, brak HC/celu/dostępu lub
  błąd techniczny przed wykonaniem nie pobierają opłaty. Prawidłowo wykonana próba
  gameplayowa jest płatna także przy losowym braku efektu; tę regułę pokazać w UI
  i zatwierdzić przy odbiorze policy przed aktywacją płatności.
- Wspólna księga HC i atomowy transfer do twórcy z efektem albo trwały mechanizm
  odzyskiwania/finalizacji dla executora wieloetapowego; brak sukcesu zapisu
  jednego elementu nie może zostawiać drugiego bez rozliczenia.
- Obsłużyć użycie własnej aplikacji (brak sztucznego przychodu), brak odbiorcy,
  zmianę ceny wersji i konkurencyjne wydatki. Proponowany fallback dla brakującego
  odbiorcy: konto `admin` zgodnie z zasadą systemowego skarbca, z jawnym powodem
  w księdze; nigdy ciche zniszczenie HC. Brak konta skarbca blokuje transakcję.

## 148.5 — regresje i migracja UI

- Naprawić fixture czterech istniejących testów kończących się
  `payment_recipient_unavailable`, zapewniając canonical konta i salda;
  nie wyłączać zabezpieczeń płatniczych dla uzyskania PASS.
- Pełna macierz czterech kreatorów: utworzenie → preview → quote → publikacja →
  zakup przez innego gracza → instalacja → wybór celu → użycie → zapisany efekt/wynik.
- Pokryć obiekt/filar, kamerę, venue/Wi-Fi/mikrofon i obsługiwane cele specjalne
  przez poprawne profile. Nie wymagać, by jedna aplikacja obsługiwała wszystkie.
- Testy poziomów poniżej progu i L40; rzeczywisty progres celu, pliki/operacje
  i wpływ na ryzyko incydentu. Sukces prezentacji nie zastępuje tych dowodów.
- Testy płatności: free, min/max, korekta sugestii, brak HC, autor=wykonawca,
  fallback admin, retry, dwie karty, awaria i aktualizacja aplikacji.
- Desktop/mobile, klawiatura, zachowanie danych formularza, wielokrotne wejście
  w preview. Starsze aplikacje mają jawny status kompatybilności i nie znikają.

## 148.6 — wdrożenie i PASS

Kontrolowane włączenie nowego kontraktu i czterech formularzy, potem płatnych opcji
po potwierdzeniu księgi na kontach testowych. Zmienne procesów w ecosystemach,
policy i cenniki w backendowym configu. Cofnięcie aktywacji zachowuje opublikowane
wersje i receipts; nie cofa samoczynnie poprawnych transferów/skutków.

PASS: gracz bez znajomości kluczy runtime tworzy aplikację o jednym celu;
L40 daje pełny dopuszczony wpływ; backend odrzuca obejścia; wszystkie cztery
prezentacje uruchamiają deklarowane efekty; każda płatna opcja ma zgodny receipt
i saldo obu stron. Odbiór ręczny i testy wymagane, nie sam wygląd formularza.

Poza zakresem: kursy efektów w Googleplexie, nowe rodziny gameplayowe, dowolny kod,
GhostLab Research/Community/AI oraz zmiana reguł incydentów i aresztu.
