# Dodanie języka Ghost Systemu

Stan kontraktów: 155.1.0. Gotowe tłumaczenia RU/ES nie należą do tego wydania.
Nie dodawać gałęzi `if locale == ...` w aplikacjach ani tłumaczyć treści graczy.

## Pakiet interfejsu

1. Uzgodnić tag języka, nazwę, kierunek pisma i glosariusz. Wpis w
   `static/locales/manifest.json` ma status testowy, formaty liczb/dat/jednostek,
   reguły liczby mnogiej oraz jawne `approved_for`. `interface`, `radio` i
   `narration` są oddzielnymi dopuszczeniami. `ANY` pozostaje filtrem radia.
2. Utworzyć komplet 13 domen w `static/locales/<tag>/`, zgodnie z manifestem.
   Zachować semantyczne klucze, typy i nazwy parametrów; przetłumaczyć wszystkie
   formy pluralizacji. Tekst nie zawiera HTML. Wartości parametrów, nicki, nazwy
   produktów, dokumenty i wiadomości graczy pozostają oryginalne.
3. Podnieść wspólny `content_version` manifestu i wszystkich pakietów. Nie zmieniać
   `format_version` bez zmiany obu runtime'ów. Loader sprawdza cały pakiet przed
   zmianą widoku i zapisem wyboru konta; uszkodzony pakiet nie staje się aktywny.
4. Sprawdzić fonty/glyphy, długie teksty, inputy, mobile i kierunek pisma. Samo
   ustawienie `dir=rtl` nie jest dowodem poprawności układu RTL. Nie przerywać
   operacji, transmisji, filmu, draftu ani edytowanego projektu podczas zmiany.
5. Edycje `/about` i `tips-tricks` dodawać jako osobne pliki z oznaczeniem języka
   i wersji źródła. Nie podmieniać tekstu dokumentu otwartego przez gracza.

## Pakiet narracji

Po osobnym zatwierdzeniu języka narracji dodać jego wpis do
`ghostnetwork/llm/narrative_languages.v1.json`:

- wersjonowany system prompt oraz instrukcje wszystkich aktywnych polityk;
- prefiksy i fallbacki wymagane przez głos medium, w tym wszystkie rodziny GN;
- reguły kontroli urwanego tekstu;
- dla News sekcję `news`: wersję, dwie ścieżki promptów i konserwatywne reguły
  odrzucania tekstu w niewłaściwym języku. Filtr słów wymaga doboru do języka;
  nie stanowi oceny semantycznej ani gotowego rozwiązania dla każdego pisma.

Pierwsza linia pliku promptu to `prompt-version: <wersja>`, następnie pusta linia
i treść. Obie warstwy instrukcji muszą wymagać tego samego języka. Fakty świata
w wejściu mogą zachowywać oryginalną pisownię; to dane, nie nadrzędne polecenia.
Nowe locale wybieramy tylko przed zapisaniem zadania. Nie zmieniać wersji promptu
pod istniejącymi zadaniami bez planu ich obsługi: kontrola wersji odrzuca taką
podmianę, zamiast generować inny tekst pod tym samym kontraktem.

`CHAOS_NARRATIVE_LOCALES` określa języki nowych automatycznych sygnałów BN.
Jedna publikacja BN zachowuje jeden język. News kolejkuje zarejestrowane warianty
zatwierdzonych języków, wiążąc je z wersją źródła. Oryginał, ID, CTA i nagrody
pozostają wspólne. Po dodaniu locale ponownie oszacować koszt wariantów News:
limit 50 dotyczy źródeł, a każde dodatkowe locale może dodać osobne zadanie.
Radio wymaga oznaczenia języka audycji, nie automatycznego dubbingu.

## Kontrola i dopuszczenie

```sh
.venv/bin/python tools/run_isolated_tests.py test_ghost_i18n test_narrative_locale test_news_generation test_news_locales test_system_message_i18n
node tests/js/test_ghost_i18n.js
node tests/js/test_ghost_i18n_runtime.js
node tests/js/test_googleplex_news.js
```

Testy demonstrują dodatkowy pakiet interfejsu oraz syntetyczny `zz` w rejestrze
narracji i News bez nowej gałęzi aplikacji. `zz` kopiuje dane EN wyłącznie jako
test rozszerzalności; nie jest tłumaczeniem ani językiem do opublikowania.
Po testach kontraktu wymagane są próbki rzeczywistych dostawców, ocena faktów,
języka i CTA, historia/migracja oraz Playwright i fizyczne urządzenia.
Status kompletnego języka nadaje się dopiero po zamknięciu macierzy pokrycia.

## Glosariusz i granice tłumaczenia PL/EN

| PL | EN | Zasada |
| --- | --- | --- |
| Instalacja zakończona | Installation complete | Systemowe zdarzenie; nazwa aplikacji to parametr. |
| Awans poziomu | Level up | Ta sama nagroda i receipt. |
| Terytorium | Territory | Nie tłumaczyć autorskiej nazwy celu. |
| Wtargnięcie | Intrusion | Ta sama tożsamość zdarzenia. |
| Przechwyt | Intercept | Głos publikacji BN, nie tłumaczenie sygnału przy odczycie. |
| Wiadomość systemowa | System message | Wymaga wiarygodnego pochodzenia. |
| Edycja angielska | English edition | Osobny dokument pomocy FM. |

Ghost System, GhostNetwork, BlackNet, Cyberner, Googleplex oraz nazwy aplikacji
i walut pozostają nazwami własnymi. Mistral/Ollama są informacją diagnostyczną,
nie etykietą narracji dla gracza. Dokładne copy jest w katalogach; glosariusz
nie służy do globalnego zastępowania słów w danych.
