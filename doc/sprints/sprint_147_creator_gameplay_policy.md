# Sprint 147 — kreatory: jedno przeznaczenie i serwerowa polityka możliwości

Status: **ZAPLANOWANY**, 24 IX 2026. Bez rozpoczęcia implementacji.
Podstawa: [audyt kreatorów](../audits/creators_gameplay_audit_2026_09_24.md).
Kontynuacja: [148 — UX, wykonanie i opłaty](sprint_148_creator_ux_runtime_completion.md).
Kolejność po 144–146; reuse fundamentów publikacji z 144, bez przebudowy GhostLaba.

## Bramka: zero ciężkiego profilu

Wykryte naruszenie naprawiamy od razu w bieżącym etapie, z testem regresji;
nie odkładamy go do następnego sprintu ani jako długu technicznego.

Obowiązuje [wspólny zakaz ciężkiego profilu](../plans/creator_ghostlab_zero_heavy_profile_contract.md).
Policy/quote/preview/generator pobierają poziom i wymagane dane autora z małej
projekcji; zakaz `user_store.get_profile()` i `sync_session_profile()` także wewnątrz
quality/price. Projekty kreatorów przechodzą do wydzielonego zapisu zamiast
`profile.files.projects`. „Profil działania” to przepis aplikacji, nie profil gracza.
PASS wymaga testów zero-heavy również na błędnym payloadzie i brakujących danych.

## Rezultat

Każdy z czterech kreatorów produkuje aplikację o jednym konkretnym przeznaczeniu:
**rodzina → cel → start → efekt → wynik**. Autor ustala nazwę, ikonę, opis,
cel, rodzinę, informacje katalogowe, treści prezentacji i sugerowane ceny.
Backend ustala dopuszczone możliwości, moc, warunki i profil ryzyka.

## 147.1 — wspólny katalog profili działania

- Wersjonowany katalog łączy rodzinę, semantyczną grupę celu, dozwolony sposób
  uruchomienia, akcję, executor, efekty i wynik/pliki. Nie generować niezależnych
  kombinacji z szerokich list map_actions/operation_types/resource_types.
- Jeden produkt ma jeden profil działania. Przyciski mogą proponować warianty tego
  samego celu, ale nie dodają kolejnych niepowiązanych zastosowań.
- Obiekty świata: POI/serwer/router/filar tylko jako zgodne techniczne warianty
  danego profilu. Kamery, miejsca/venue i cele specjalne mają własne profile.
- Katalog uwzględnia istniejące wykonawce: scan/recon, exploit, implant, sniff,
  śledzenie ruchu/urządzenia/pojazdu, stream i zakłócenie kamery, audio/mikrofon,
  Wi-Fi i pliki. Pokazywać tylko faktycznie zaimplementowane kombinacje.
- Sporządzić mapowanie włączenia i wyłączenia kamer na realny stan i ryzyko
  incydentu; brakujący executor nie może być zastąpiony obietnicą w opisie.

## 147.2 — możliwości od poziomu twórcy

- Osobna, konfigurowalna i wersjonowana policy dla tych czterech kreatorów.
  Backend pobiera poziom autora; klient nie podaje wiążącego poziomu ani mocy.
- Poziom 40 i wyższy: 100% możliwości oraz dopuszczonego wpływu w wybranym profilu.
  Respekt i bogactwo nie pozwalają wcześniej obejść progów poziomu.
- Przed kodowaniem executorów przygotować tabelę L1–L40: wpływ procentowy,
  odblokowane możliwości, ograniczenia, warunki celu i ekspozycja. Roboczy wariant
  wpływu to min(level,40)/40; dokładne progi odblokowań i balans do przeglądu autora,
  nie są zatwierdzone samym zapisaniem planu.
- Oddzielić moc, dozwolone efekty, niezawodność i ryzyko użycia. L40 nie oznacza
  zerowego ryzyka, ominięcia aresztu, własności, dostępu ani gwarancji przejęcia
  każdego obiektu. Scanner osiąga pełny odczyt, nie przejmuje celu jako exploit.
- Proponowany kontrakt: poziom i policy zapisywane przy publikacji; awans autora
  wymaga świadomej nowej wersji produktu, nie zmienia kupionych aplikacji w tle.
  Jawnie opisać aktualizację istniejącej instalacji.
- Docelowe pola techniczne wylicza backend; przesłane ręcznie przez klienta
  sprzeczne uprawnienia/efekty są odrzucane, także dla payloadu custom/bez rodziny.

## 147.3 — semantyka efektu, ryzyka i progresu

- Wycofać autorstwo ręcznych macierzy requires_off/interferes_with/disables/affects
  w nowym kontrakcie. Rozdzielić warunki uruchomienia od faktycznej zmiany celu.
- Wspólny wynik zawiera: wykonana akcja, zmienione parametry, pliki/operacje,
  przyczyna odmowy, stan zabezpieczeń i ewentualne przejęcie. Log autora nie jest
  dowodem wykonania efektu.
- Zbudować reprodukcję „wszystkie opcje, pasek nie dochodzi do 100%” na kontrolowanym
  celu. Uzgodnić źródło progresu z executorami, a nie z animacją.
- Test L40 dla profilu rozbrajania: osiągnięcie pełnego deklarowanego wpływu przy
  spełnionych warunkach; osobny test odmowy i profilu odczytowego bez przejęcia.
- Ryzyko incydentu integruje istniejące kamery, ekspozycję i służby; jedna akcja
  nie tworzy zdublowanych zdarzeń. Backend uwzględnia aktualny kontekst świata.

## 147.4 — efekty przycisków, akcje i wycena

- Button Maker zachowuje effect, lecz pola, typy i zakresy wynikają z profilu
  i poziomu. Nie dopuszczać arbitralnego security key lub wartości poza policy.
- Window Maker otrzymuje mały katalog nazwanych akcji; `run_generated` oznacza
  uruchomienie tego profilu, `close` zamknięcie. Nieznane identyfikatory (np.
  rank_generated) wymagają mapowania lub błędu, nie domyślnej mutacji celu.
- Rozdzielić cenę zakupu i cenę pojedynczego użycia opcji. Dla obu jawne zero
  oznacza bezpłatność danej czynności; darmowy zakup nie znaczy darmowe użycia.
- Dla ceny dodatniej funkcja quote ogranicza sugestię do [minimum, maksimum]
  zależnych od profilu, zatwierdzonego efektu i mocy. Ujemne/niefinitywne wartości
  odrzucać. Dokładne widełki w configu, do kalibracji z autorem przed aktywacją.
- Quote pokazuje sugerowaną i końcową cenę oraz powód korekty. Ceny opcji nie wolno
  wyprowadzać z arbitralnego tekstu autora ani losować w momencie płatności.

## 147.5 — wersjonowanie i kompatybilność

- Zrobić inwentaryzację istniejących aplikacji; dry-run kwalifikuje je do profilu
  albo zgłasza niejednoznaczność. Nie zmieniać masowo efektów, cen i możliwości
  kupionych produktów bez raportu migracji i jasnego kontraktu dla graczy.
- Oddzielić legacy od nowego generatora. Nie pozwalać tworzyć nowych aplikacji
  starym payloadem omijającym policy. Istniejące niebezpieczne efekty muszą mieć
  kontrolę wykonania i czytelny powód blokady, nie cichy bypass kompatybilności.
- Reuse spójnej publikacji z 144; zachować tożsamość autora, instalacje i zakupione
  wersje. Nie zmieniać globalnie formuł GhostLaba bez osobnej decyzji.

## 147.6 — warunki PASS

Testy poziomów 1/39/40/41 oraz granic wszystkich unlocków; monotoniczne możliwości,
brak wpływu respektu/HC na obejście poziomu, odrzucanie podrobionych pól. Testy
jednego profilu, kombinacji niedozwolonych i wszystkich wspieranych par cel/akcja.
Testy quote: zero, poniżej minimum, w przedziale, powyżej maksimum, wartości błędne.
Test progresu oparty na zapisanym stanie, nie wyłącznie tekstach i animacji.

Dostarczyć katalog, tabelę policy, fixture z canonical odbiorcą płatności oraz
raport migracji i runbook rollback. Nowego formularza i pobierania opłat nie
aktywować przed gotowością Sprintu 148; istniejąca gra zachowuje spójny kontrakt.
