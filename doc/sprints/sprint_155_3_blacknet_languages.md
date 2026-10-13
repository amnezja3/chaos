# Sprint 155.3 — BlackNet: język źródła i naturalna rotacja sygnałów

Status: ZAPLANOWANY, 13 X 2026. Osobny podsprint [155](sprint_155_ghost_system_content_acceptance.md).
Nie blokuje dostępności rozgrywki. To zakres do implementacji, nie deklaracja PASS.

## Cel i ustalenia

BlackNet to wskazówki, tropy i ślady z różnych źródeł. Jedna publikacja ma jeden
język. Nie tworzymy automatycznie pary PL/EN tego samego sygnału. Kolejne sygnały
mogą naturalnie zmieniać język spośród zatwierdzonych języków narracji.
Zmiana języka interfejsu nie przepisuje wcześniej opublikowanego sygnału.

- Radio PL → sygnał PL; radio EN → sygnał EN. Używamy języka kanału/źródła,
  nie aktualnego filtra widza ani języka jego interfejsu. ANY jest filtrem lub
  deklaracją neutralności językowej, nigdy językiem generacji ani tłumaczeniem audio.
- Kreatory otrzymają deklarację PL/EN/ANY dla narzędzia/produktu. PL i EN
  określają język źródła sygnału. ANY pozwala wybrać zatwierdzony język dla
  systemowego tekstu sygnału, ale nie uprawnia do tłumaczenia treści autora.
- Sygnały neutralne językowo/heurystyczne GN korzystają z rotacji zatwierdzonych
  języków. Wyboru dokonujemy przy utworzeniu zadania; zapisujemy go trwale.
  Retry, fallback, restart i publikacja nie losują języka ponownie.
- Nazwy, opisy produktów Googleplexa i inne UGC zachowują oryginał. Systemowe
  otoczenie sygnału i etykiety są lokalizowane. Jawne wersje autora są oddzielnymi
  danymi, nie efektem automatycznego tłumaczenia.
- Radio „KANAŁY ONLINE”, „TRACKÓW W ETERZE” i pozostałe systemowe etykiety kart
  muszą mieć PL/EN; także tekst zaszyty w grafice lub szablonie heurystycznym.
- Jeden zestaw faktów, jeden cel/CTA, jeden identyfikator i efekt gameplayu.
  Fallback systemowy zachowuje wybrany język; brak wymogu kreatywności Ollamy.

## Etapy

1. **Inwentarz i kontrakt:** wszystkie producenty GN/radio/Googleplex/GX/narzędzi,
   heurystyki, prompt, fallback, szablony i grafiki. Udokumentować źródło języka,
   brak metadanych i rozstrzyganie konfliktów. Pierwszeństwo rzeczywistego źródła
   radiowego; rozbieżność deklaracji ma być jawna, nie cicha zmiana publikacji.
2. **Język zadania i renderer:** trwałe przypisanie locale, rotacja sygnałów
   neutralnych bez głodzenia języka, idempotencja, parametryzowane etykiety kart,
   krótkie nagłówki bez urywania nazw. Prefiksy stylistyczne obsłużyć systemowo
   w uzgodnionym kontrakcie, nie kolejnymi próbami wymuszania ich przez model.
3. **Kreatory i katalog:** PL/EN/ANY w odpowiednich formularzach, walidacja API,
   zapis metadanych i przeniesienie przez publikację Googleplexa, zakup, instalację
   oraz sygnał BN. Język nie zmienia dopasowania celu, uprawnień ani ceny narzędzia.
4. **Historia i odbiór:** inventory/dry-run dla brakujących metadanych;
   bez przepisywania starych tekstów lub republish. Odbiór mobile/desktop i próbek
   Mistrala oraz deterministycznego fallbacku, z raportem per źródło.

## Kryteria PASS

- PL radio zawsze daje PL sygnał, EN radio EN; ANY nigdy nie trafia jako locale
  do modelu. Dziewięć potwierdzonych polskich audycji zachowuje oznaczenie PL.
- Rotacja neutralnych źródeł działa po restarcie i retry bez zdublowania sygnału.
- Produkty PL/EN/ANY przechodzą pełną ścieżkę; UGC pozostaje identyczne.
- Karty radia, GN, GGPL i GX nie mają polskich systemowych etykiet w wariancie EN.
- Brak tytułów skopiowanych z instrukcji i uciętych nazw typu „Can” zamiast
  „Canary Station”. Odrzucona generacja przechodzi do zatwierdzonego szablonu.
- Zmiana UI nie zmienia ID, celu, faktów, nagród, consumed ani języka publikacji.
- Dodanie zatwierdzonego języka korzysta z rejestru, nie z kolejnej gałęzi PL/EN.
- Brak nowej infrastruktury i zatrzymywania gry na czas strojenia narracji.

## Poza tym podsprintem

Automatyczne tłumaczenie UGC, dubbing nagrań, wymiana modelu Ollamy i odblokowanie
zamrożonych sprintów 149–152. Historyczne treści bez udokumentowanego pochodzenia
wymagają przeglądu, nie automatycznego zgadywania języka.
